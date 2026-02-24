"""
LUDI INFORMATIO | PHASE 8.5: PLAY CURATION ENGINE
===================================================
Two-stage AI gate running after main.py writes bets to bet_recommendations.

Stage 1 — Haiku Sanity Gate: Per-bet injury contradiction check (~$0.02/day)
Stage 2 — Sonnet Top 5 Curation: Correlation-aware portfolio selection (~$0.06/day)

Design principle: Claude reasons about selection — NEVER recalculates edge.
true_edge is the authoritative number from Module F's deterministic math.

Graceful degradation: if Claude is unavailable → edge-sorted deterministic fallback.

Usage:
  python scripts/curate_plays.py                         # today's date
  python scripts/curate_plays.py --run-date 2026-02-19   # specific date
  python scripts/curate_plays.py --dry-run               # no DB writes, no Telegram
  python scripts/curate_plays.py --verbose               # debug output

Created: February 2026 | Phase 8.5
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import date, datetime

# ─── Path Setup ───────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

DB_PATH = os.path.join(_PROJECT_ROOT, 'ludi.db')

import config

# ─── Reused Infrastructure (do NOT rewrite these) ─────────────────────────────
from utils.claude_client import get_claude_analysis, HAIKU_MODEL, SONNET_MODEL
from utils.claude_prompts import ROSTER_RULES, ANALYSIS_PROTOCOL
from utils.telegram_notifier import send_message
from utils.player_id_resolver import resolve_canonical_name

# ─── Constants ────────────────────────────────────────────────────────────────
# Stats where an OUT/DOUBTFUL player bet OVER is clearly wrong
VOLUME_STATS = {'PTS', 'REB', 'AST', 'MIN'}
SANITY_FAIL_STATUSES = {'OUT', 'DOUBTFUL'}

SANITY_GATE_SYSTEM = """You are a bet sanity checker for an NBA analytics model.
VALID OUTPUT ONLY:
  {"result": "PASS", "reason": ""}
  {"result": "FLAG", "reason": "<one sentence describing the contradiction>"}
No other values are valid for "result". Return JSON only."""

TIER_EMOJI = {
    'DIAMOND': '💎',
    'BLUE CHIP': '🔷',
    'CORE ASSET': '🔹',
    'THE STEAL': '⭐',
}

# ─── Schema Migrations ────────────────────────────────────────────────────────
# Curation columns added here, not in database.py (per architecture decision)
MIGRATIONS = [
    "ALTER TABLE bet_recommendations ADD COLUMN is_curated BOOLEAN DEFAULT 0",
    "ALTER TABLE bet_recommendations ADD COLUMN curated_rank INTEGER",
    "ALTER TABLE bet_recommendations ADD COLUMN sanity_flagged BOOLEAN DEFAULT 0",
    "ALTER TABLE bet_recommendations ADD COLUMN sanity_flag_reason TEXT",
]


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Add curation columns to bet_recommendations if not already present."""
    for sql in MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # column already exists — safe to skip
    conn.commit()


# ─── Data Fetching ────────────────────────────────────────────────────────────
def _fetch_todays_bets(conn: sqlite3.Connection, run_date: str) -> list[dict]:
    """Fetch all unsettled bets for the given run_date."""
    cursor = conn.execute("""
        SELECT id, player_name, team, opponent, stat_category, bet_side, line,
               true_edge, projection, confidence_tier, game_id, matchup,
               home_team, away_team, spread, total, archetype, odds_over, odds_under
        FROM bet_recommendations
        WHERE run_date = ?
          AND outcome IS NULL
        ORDER BY true_edge DESC
    """, (run_date,))
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def _fetch_player_injury(conn: sqlite3.Connection, player_name: str) -> dict | None:
    """Fetch most recent active injury record for a player. Returns None if table missing.

    Uses canonical name resolution so that non-accented names from bet_recommendations
    (e.g. 'Nikola Jokic' from Odds API) correctly match accented canonical names
    (e.g. 'Nikola Jokić') stored in player_injuries. Without this, Haiku receives
    'No injury on record' for OUT players and passes bad bets.
    """
    # Resolve to canonical full_name (e.g. 'Nikola Jokic' → 'Nikola Jokić')
    canonical_name = resolve_canonical_name(conn, player_name)
    try:
        cursor = conn.execute("""
            SELECT status, days_out, description, is_game_day_report
            FROM player_injuries
            WHERE player_name = ?
              AND resolved_at IS NULL
            ORDER BY snapshot_time DESC
            LIMIT 1
        """, (canonical_name,))
        row = cursor.fetchone()
        if row:
            return {
                'status': row[0],
                'days_out': row[1],
                'description': row[2],
                'is_game_day_report': row[3],
            }
    except sqlite3.OperationalError:
        pass  # player_injuries table not yet deployed (8.0-A pending) — skip gracefully
    return None


# ─── Stage 1: Haiku Sanity Gate ───────────────────────────────────────────────
def _deterministic_sanity_check(bet: dict, injury: dict | None) -> tuple[str, str]:
    """
    Fast rule-based check that runs before calling Haiku.
    Catches the obvious cases without spending API tokens.
    Returns ('PASS', '') or ('FLAG', reason).
    """
    if injury and injury['status'] in SANITY_FAIL_STATUSES:
        if bet['bet_side'].upper() == 'OVER' and bet['stat_category'].upper() in VOLUME_STATS:
            reason = (
                f"{bet['player_name']} is {injury['status']} "
                f"but bet is OVER {bet['stat_category']}"
            )
            return 'FLAG', reason

    # Catch statistically impossible lines (projection < 40% or > 250% of line)
    if bet.get('projection') and bet.get('line'):
        try:
            ratio = float(bet['projection']) / float(bet['line'])
            if ratio < 0.4 or ratio > 2.5:
                reason = (
                    f"Line {bet['line']} inconsistent with "
                    f"projection {bet['projection']:.1f} (ratio {ratio:.2f})"
                )
                return 'FLAG', reason
        except (TypeError, ZeroDivisionError):
            pass

    return 'PASS', ''


def _haiku_sanity_check(bet: dict, injury: dict | None, verbose: bool = False) -> tuple[str, str]:
    """
    Ask Haiku to sanity-check a single bet against injury data.
    Returns ('PASS'|'FLAG', reason_string).

    Strategy:
    - Deterministic check first (no API cost)
    - If injury exists → ask Haiku for nuanced assessment
    - If no injury → auto-PASS (saves tokens)
    - On any parse failure → conservative PASS (never drop a bet on parse error)
    """
    # Fast path: deterministic check first
    result, reason = _deterministic_sanity_check(bet, injury)
    if result == 'FLAG':
        if verbose:
            print(f"  [HAIKU-SKIP] Deterministic FLAG: {reason}")
        return result, reason

    # No injury record → try Perplexity for soft-scratch detection
    perp_news = ""
    if not injury:
        if getattr(config, 'PERPLEXITY_API_KEY', None):
            try:
                from utils.perplexity_client import PerplexityClient
                perp_news = PerplexityClient().search_player_news(
                    bet['player_name'], bet['team']
                )
            except Exception:
                pass

        if not perp_news:
            return 'PASS', ''

        injury_text = f"RECENT NEWS (from Perplexity, fetched today):\n{perp_news}"
    else:
        injury_text = (
            f"Status: {injury['status']}\n"
            f"Days Out: {injury['days_out'] if injury['days_out'] is not None else 'Unknown'}\n"
            f"Description: {injury['description'] or 'None provided'}\n"
            f"Game Day Report: {'Yes' if injury['is_game_day_report'] else 'No'}"
        )

    system_prompt = f"{SANITY_GATE_SYSTEM}\n\n{ROSTER_RULES}\n\n{ANALYSIS_PROTOCOL}"

    perplexity_block = f"\n\nRECENT NEWS (Perplexity):\n{perp_news}" if perp_news else ""
    
    env = config.get_scoring_environment()
    env_note = f"\nSCORING ENVIRONMENT: {env.get('environment','NEUTRAL')} — OVER bets hitting {env.get('over_hit_rate_14d',0):.0%} last 14 days.\n" if env else ""

    user_prompt = f"""Sanity check this bet. Return JSON only, no other text:
{{"result": "PASS" or "FLAG", "reason": "<one sentence max>"}}

BET:
- Player: {bet['player_name']} ({bet['team']})
- Stat: {bet['stat_category']} {bet['bet_side']} {bet['line']}
- Model Projection: {bet.get('projection', 'N/A')}
- True Edge: {bet.get('true_edge', 'N/A')}%

INJURY DATA (from official report, fetched today):
{injury_text}{perplexity_block}{env_note}

FLAG this bet ONLY if:
1. Player is OUT or DOUBTFUL AND bet_side is OVER a volume stat (PTS, REB, AST, MIN)
2. The line appears statistically impossible given the injury context
Otherwise PASS. When in doubt, PASS."""

    response = get_claude_analysis(
        prompt=user_prompt,
        system_prompt=system_prompt,
        model=HAIKU_MODEL,
        temperature=0.1,
        max_tokens=100,
    )

    if not response:
        if verbose:
            print(f"  [HAIKU] No response for {bet['player_name']} — defaulting PASS")
        return 'PASS', ''

    # Parse JSON — Claude may wrap in ```json``` blocks
    try:
        clean = response.strip()
        if '```' in clean:
            clean = clean.split('```')[1]
            if clean.startswith('json'):
                clean = clean[4:]
        clean = clean.strip()
        data = json.loads(clean)
        result = str(data.get('result', 'PASS')).upper()
        reason = str(data.get('reason', ''))
        if result not in ('PASS', 'FLAG'):
            result = 'PASS'
        if verbose:
            print(f"  [HAIKU] {bet['player_name']}: {result} — {reason}")
        return result, reason
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        raw_preview = response[:200] if response else "empty"
        print(f"[HAIKU PARSE FAIL] {bet['player_name']}: {type(e).__name__} | raw={raw_preview}")
        if verbose:
            print(f"  [HAIKU] Parse error for {bet['player_name']}: {e} — defaulting PASS")
        return 'PASS', ''


# ─── Stage 2: Sonnet Top 5 Curation ──────────────────────────────────────────
def _format_bets_for_prompt(bets: list[dict]) -> str:
    """Format bet list as readable text block for Sonnet's context."""
    lines = []
    for bet in bets:
        tier_emoji = TIER_EMOJI.get(bet.get('confidence_tier', ''), '📌')
        injury_note = bet.get('_injury_note', 'No injury on record')
        # Show odds for the side being bet
        if bet.get('bet_side', '').upper() == 'OVER':
            odds = bet.get('odds_over')
        else:
            odds = bet.get('odds_under')
        odds_str = f"@ {odds}" if odds else ""

        lines.append(
            f"[{bet['id']}] {bet['player_name']} | "
            f"{bet['stat_category']} {bet['bet_side']} {bet['line']} {odds_str}\n"
            f"      {tier_emoji} {bet.get('confidence_tier', 'N/A')} | "
            f"Edge: +{bet.get('true_edge', 0):.1f}% | "
            f"Proj: {bet.get('projection', 'N/A')}\n"
            f"      Game: {bet.get('matchup', 'N/A')} "
            f"(game_id: {bet.get('game_id', 'N/A')}) | "
            f"Spread: {bet.get('spread', 'N/A')} | "
            f"Total: {bet.get('total', 'N/A')}\n"
            f"      Injury: {injury_note}"
        )
    return '\n\n'.join(lines)


def _get_system_wr_context(conn: sqlite3.Connection) -> str:
    """Build empirical win rate context for Sonnet curation — Pattern 6 (BERT domain pre-training).

    Uses Wilson 95% lower bound instead of raw WR — statistically conservative and
    sample-size adjusted. Grades: A+ (iron-clad) → F (avoid). Auto-updates as bets settle.

    See: best-practices/data/STAT_CONFIDENCE_FRAMEWORK.md
    """
    import math
    try:
        rows = conn.execute("""
            SELECT stat_category, bet_side,
                   COUNT(*) as n,
                   ROUND(100.0 * SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) / COUNT(*), 1) as wr,
                   SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins
            FROM bet_recommendations
            WHERE outcome IN ('WIN','LOSS')
            GROUP BY stat_category, bet_side
            HAVING COUNT(*) >= 50
            ORDER BY wr DESC
        """).fetchall()
    except Exception:
        return ""

    z = 1.96  # 95% confidence
    lines = [
        "LUDI-BOT EMPIRICAL WIN RATES (this season, Wilson 95% confidence floor):",
        "Use these to break selection ties. High raw edge ≠ reliable bet for high-variance stats.",
    ]
    for stat, side, n, wr, wins in rows:
        p = wins / n
        denom = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denom
        margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
        lb = max(0.0, center - margin)

        if lb >= 0.60 and n >= 500:    grade, flag = "A+", " ← PRIORITIZE"
        elif lb >= 0.55 and n >= 150:  grade, flag = "B",  " ← PREFER"
        elif lb >= 0.50:               grade, flag = "C",  ""
        elif lb >= 0.42:               grade, flag = "D",  " ← DEPRIORITIZE"
        else:                          grade, flag = "F",  " ← AVOID"

        lines.append(f"  {stat} {side}: {wr:.0f}% WR (95% floor={lb*100:.0f}%, n={n}) [{grade}]{flag}")

    lines += [
        "",
        "KEY CALIBRATION NOTES:",
        "- BLOCKS UNDER: structural book edge — book lines are consistently set too high; prioritize even at lower edge",
        "- PTS/REB/PRA OVER: model OVERSTATES edge by 18-21%; require higher edge threshold before selecting",
        "- STEALS UNDER: improving trend — confidence growing as sample builds",
        "- REB OVER: actively degrading (WR falling late-season) — deprioritize unless edge >10%",
        "- PRA OVER: structural avoid — 25% WR on 80 bets, should be filtered before curation",
    ]
    return "\n".join(lines)


def _sonnet_curate(passing_bets: list[dict], verbose: bool = False) -> list[dict] | None:
    """
    Ask Sonnet to select and rank top 5 bets from passing bets.

    Claude reasons about portfolio quality — correlation, diversity, tier.
    It does NOT recalculate edges. true_edge is authoritative.

    Returns list of {'bet_id', 'rank', 'reasoning'} dicts, or None on failure.
    None triggers the deterministic fallback in the caller.
    """
    if not passing_bets:
        return None

    bets_text = _format_bets_for_prompt(passing_bets)

    # Build domain WR context from live DB (Pattern 6: domain pre-training proxy)
    # Wilson-adjusted WR grades auto-update as bets settle each night.
    try:
        conn_wr = sqlite3.connect(DB_PATH)
        wr_context = _get_system_wr_context(conn_wr)
        conn_wr.close()
    except Exception:
        wr_context = ""

    system_prompt = f"{ROSTER_RULES}\n\n{ANALYSIS_PROTOCOL}"
    if wr_context:
        system_prompt += f"\n\n{wr_context}"

    env = config.get_scoring_environment()
    over_rate = env.get('over_hit_rate_14d', 0)
    env_label = env.get('environment', 'NEUTRAL')
    env_context = f"\nSCORING ENVIRONMENT TODAY: {env_label} ({over_rate:.0%} 14d OVER hit rate). When in doubt between two OVER plays, prefer the one with stronger UNDER characteristics.\n" if env else ""

    user_prompt = f"""You are selecting the TOP 5 plays from today's NBA player prop slate.

HARD RULES:
- Maximum 2 bets from the same game_id (avoid correlated losses in one game)
- Diversify across stat types (do not pick 5 PTS bets)
- Rank by overall confidence — weight tier quality, injury clarity, and edge together
- DO NOT recalculate, adjust, or question any edge/probability/projection values — they are authoritative outputs from a deterministic simulation model
- Return ONLY a valid JSON array, no other text:
  [{{"bet_id": 123, "rank": 1, "reasoning": "one sentence explaining the pick"}}]

{env_context}

TODAY'S CLEAN BETS ({len(passing_bets)} total, already passed injury sanity gate):
{bets_text}

Select the best 5 (or all available if fewer than 5 passed the gate). Return JSON array only."""

    if verbose:
        print(f"  [SONNET] Sending {len(passing_bets)} bets for curation...")

    response = get_claude_analysis(
        prompt=user_prompt,
        system_prompt=system_prompt,
        model=SONNET_MODEL,
        temperature=0.1,
        max_tokens=800,
    )

    if not response:
        if verbose:
            print("  [SONNET] No response — will use deterministic fallback")
        return None

    try:
        clean = response.strip()
        if '```' in clean:
            clean = clean.split('```')[1]
            if clean.startswith('json'):
                clean = clean[4:]
        clean = clean.strip()
        data = json.loads(clean)
        if not isinstance(data, list):
            raise ValueError("Expected JSON array")

        # Parse and validate max-2-per-game constraint
        result = []
        game_counts: dict[str, int] = {}
        bet_id_to_game_map = {b['id']: b.get('game_id', '') for b in passing_bets}

        for item in data:
            if 'bet_id' in item and 'rank' in item:
                bet_id = int(item['bet_id'])
                game_id = bet_id_to_game_map.get(bet_id, '')

                # Enforce max-2-per-game in code (not just prompt)
                if game_counts.get(game_id, 0) >= 2:
                    if verbose:
                        print(f"  [SONNET] Skipping bet_id {bet_id} - already 2 bets from game {game_id}")
                    continue

                result.append({
                    'bet_id': bet_id,
                    'rank': int(item['rank']),
                    'reasoning': str(item.get('reasoning', '')),
                })
                game_counts[game_id] = game_counts.get(game_id, 0) + 1

                if len(result) >= 5:
                    break

        if not result:
            raise ValueError("No valid picks parsed from response")
        if verbose:
            print(f"  [SONNET] Successfully selected {len(result)} bets (max-2-per-game enforced)")
        return result
    except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
        raw_preview = response[:200] if response else "empty"
        print(f"[SONNET PARSE FAIL] {type(e).__name__} | raw={raw_preview}")
        if verbose:
            print(f"  [SONNET] Parse error: {e} — will use deterministic fallback")
        return None


# ─── Deterministic Fallback ───────────────────────────────────────────────────
def _deterministic_top5(passing_bets: list[dict]) -> list[dict]:
    """
    Fallback curation when Claude is unavailable or fails to parse.
    Sorts by true_edge DESC, enforces max-2-per-game constraint.
    """
    selected = []
    game_counts: dict[str, int] = {}

    for bet in sorted(passing_bets, key=lambda b: b.get('true_edge') or 0, reverse=True):
        if len(selected) >= 5:
            break
        game_id = bet.get('game_id', '')
        if game_counts.get(game_id, 0) < 2:
            selected.append(bet)
            game_counts[game_id] = game_counts.get(game_id, 0) + 1

    return [
        {'bet_id': b['id'], 'rank': i + 1, 'reasoning': ''}
        for i, b in enumerate(selected)
    ]


# ─── DB Writes ────────────────────────────────────────────────────────────────
def _write_curation_results(
    conn: sqlite3.Connection,
    top5_picks: list[dict],
    flagged_bets: list[dict],
    verbose: bool = False,
) -> None:
    """Write curated rankings and sanity flags back to bet_recommendations."""
    for pick in top5_picks:
        conn.execute("""
            UPDATE bet_recommendations
            SET is_curated = 1, curated_rank = ?
            WHERE id = ?
        """, (pick['rank'], pick['bet_id']))
        if verbose:
            print(f"  [DB] Marked bet {pick['bet_id']} as curated rank {pick['rank']}")

    for bet in flagged_bets:
        conn.execute("""
            UPDATE bet_recommendations
            SET sanity_flagged = 1, sanity_flag_reason = ?
            WHERE id = ?
        """, (bet['_flag_reason'], bet['id']))
        if verbose:
            print(f"  [DB] Flagged bet {bet['id']}: {bet['_flag_reason']}")

    conn.commit()


# ─── Telegram Card ────────────────────────────────────────────────────────────
def _escape_markdown_v2(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2."""
    # Order matters: backslash first, then others
    chars_to_escape = ['\\', '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    return text


def _send_telegram_card(
    top5_picks: list[dict],
    bet_map: dict[int, dict],
    run_date: str,
    flagged_count: int,
    claude_available: bool,
) -> None:
    """Send formatted Top 5 card to Telegram via send_message()."""
    date_str = datetime.strptime(run_date, '%Y-%m-%d').strftime('%b %d, %Y')
    mode_tag = 'AI-Curated' if claude_available else 'Edge-Sorted (AI unavailable)'

    lines = [
        f"🎯 *TOP 5 PLAYS — {_escape_markdown_v2(date_str)}*",
        f"_{_escape_markdown_v2(mode_tag)} \\| S\\.A\\.V\\.A\\.G\\.E\\. Protocol_",
        "",
    ]

    rank_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']

    for pick in sorted(top5_picks, key=lambda p: p['rank']):
        bet = bet_map.get(pick['bet_id'])
        if not bet:
            continue

        rank_emoji = rank_emojis[pick['rank'] - 1] if 1 <= pick['rank'] <= 5 else f"{pick['rank']}\\."
        tier = bet.get('confidence_tier', 'N/A')
        tier_emoji = TIER_EMOJI.get(tier, '📌')

        if bet.get('bet_side', '').upper() == 'OVER':
            odds = bet.get('odds_over')
        else:
            odds = bet.get('odds_under')
        odds_str = f" @ {odds}" if odds else ""

        # Escape all user-content strings
        player_name_escaped = _escape_markdown_v2(bet['player_name'])
        stat_escaped = _escape_markdown_v2(bet['stat_category'])
        bet_side_escaped = _escape_markdown_v2(str(bet['bet_side']))
        line_escaped = _escape_markdown_v2(str(bet['line']))
        odds_str_escaped = _escape_markdown_v2(odds_str) if odds_str else ""

        matchup = bet.get('matchup') or (
            f"{bet.get('away_team', '?')} @ {bet.get('home_team', '?')}"
        )
        matchup_escaped = _escape_markdown_v2(matchup)

        edge = bet.get('true_edge') or 0
        tier_escaped = _escape_markdown_v2(tier)
        proj_escaped = _escape_markdown_v2(str(bet.get('projection', 'N/A')))

        lines.append(
            f"{rank_emoji} *{player_name_escaped}* — "
            f"{stat_escaped} {bet_side_escaped} {line_escaped}{odds_str_escaped}"
        )
        lines.append(
            f"{tier_emoji} {tier_escaped} \\| Edge: \\+{_escape_markdown_v2(f'{edge:.1f}')}% \\| "
            f"Proj: {proj_escaped} \\| {matchup_escaped}"
        )
        if pick.get('reasoning'):
            reasoning_escaped = _escape_markdown_v2(pick['reasoning'])
            lines.append(f"💬 _{reasoning_escaped}_")
        lines.append("")

    if flagged_count > 0:
        lines.append(
            f"⚠️ *Flagged \\(not in top 5\\):* {flagged_count} bet\\(s\\) removed by injury sanity gate"
        )
    lines.append("_Edge is model output\\. Not financial advice\\._")

    message = '\n'.join(lines)
    success = send_message(message, parse_mode="MarkdownV2")
    if not success:
        print("[WARNING] MarkdownV2 Telegram card failed to send — retrying as plain text")
        success = send_message(message, parse_mode=None)
        if not success:
            print("[CRITICAL] Plain text retry failed. Telegram notifications are down. Exiting to trigger Ops Hub.")
            import sys
            sys.exit(1)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description='Phase 8.5: Curate top plays via two-stage Claude AI gate'
    )
    parser.add_argument(
        '--run-date',
        default=date.today().isoformat(),
        help='Date to curate bets for (YYYY-MM-DD). Defaults to today.'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run all logic but skip DB writes and Telegram sends.'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print debug output for each bet and Claude call.'
    )
    args = parser.parse_args()

    run_date = args.run_date
    dry_run = args.dry_run
    verbose = args.verbose

    print(f"\n{'='*60}")
    print(f"PHASE 8.5: PLAY CURATION ENGINE")
    print(f"Run date : {run_date}")
    print(f"Dry run  : {dry_run}")
    print(f"DB path  : {DB_PATH}")
    print(f"{'='*60}\n")

    conn = sqlite3.connect(DB_PATH)
    try:
        # ── Schema migrations (safe, idempotent)
        _run_migrations(conn)

        # ── Fetch today's unsettled bets
        bets = _fetch_todays_bets(conn, run_date)
        if not bets:
            print(f"[INFO] No unsettled bets found for {run_date}. Nothing to curate.")
            return

        print(f"[INFO] Found {len(bets)} bets to process\n")

        # ─────────────────────────────────────────────────────────
        # STAGE 1: Haiku Sanity Gate
        # ─────────────────────────────────────────────────────────
        print(f"[STAGE 1] Haiku Sanity Gate — checking {len(bets)} bets...")
        passing_bets: list[dict] = []
        flagged_bets: list[dict] = []

        for bet in bets:
            # Fetch injury context (used in both sanity check and Stage 2 prompt)
            injury = _fetch_player_injury(conn, bet['player_name'])

            # Annotate injury summary for Stage 2 prompt formatting
            if injury:
                days_str = f"{injury['days_out']}d " if injury['days_out'] is not None else ""
                desc = injury['description'] or 'no description'
                bet['_injury_note'] = f"{injury['status']}, {days_str}({desc})"
            else:
                bet['_injury_note'] = 'No injury on record'

            if verbose:
                print(
                    f"  Checking: {bet['player_name']} "
                    f"{bet['stat_category']} {bet['bet_side']} {bet['line']} | "
                    f"injury: {bet['_injury_note']}"
                )

            result, reason = _haiku_sanity_check(bet, injury, verbose=verbose)

            if result == 'FLAG':
                bet['_flag_reason'] = reason
                flagged_bets.append(bet)
                print(f"  ❌ FLAGGED: {bet['player_name']} — {reason}")
            else:
                passing_bets.append(bet)

        print(
            f"\n[STAGE 1] Complete: {len(passing_bets)} passing, "
            f"{len(flagged_bets)} flagged\n"
        )

        if not passing_bets:
            print("[WARNING] All bets flagged by sanity gate — nothing left to curate")
            if not dry_run:
                _write_curation_results(conn, [], flagged_bets, verbose=verbose)
            return

        # ─────────────────────────────────────────────────────────
        # STAGE 2: Sonnet Top 5 Curation
        # ─────────────────────────────────────────────────────────
        print(f"[STAGE 2] Sonnet Top 5 — curating from {len(passing_bets)} passing bets...")

        sonnet_result = _sonnet_curate(passing_bets, verbose=verbose)
        claude_available = sonnet_result is not None

        if not claude_available:
            print("[WARNING] Claude unavailable — using edge-sorted deterministic fallback")
            top5_picks = _deterministic_top5(passing_bets)
        else:
            top5_picks = sonnet_result

        # Build ID → bet lookup for output and Telegram
        bet_map: dict[int, dict] = {b['id']: b for b in bets}

        # ── Print summary
        print(f"\n[RESULT] Top {len(top5_picks)} curated plays:")
        for pick in sorted(top5_picks, key=lambda p: p['rank']):
            bet = bet_map.get(pick['bet_id'], {})
            tier = bet.get('confidence_tier', 'N/A')
            edge = bet.get('true_edge') or 0
            print(
                f"  #{pick['rank']} [{pick['bet_id']}] "
                f"{bet.get('player_name', '?')} — "
                f"{bet.get('stat_category', '?')} {bet.get('bet_side', '?')} "
                f"{bet.get('line', '?')} | {tier} | Edge: +{edge:.1f}%"
            )
            if pick.get('reasoning'):
                print(f"      → {pick['reasoning']}")

        # ── Write results and send Telegram
        if dry_run:
            print("\n[DRY RUN] Skipping DB writes and Telegram send")
        else:
            print("\n[INFO] Writing curation results to DB...")
            _write_curation_results(conn, top5_picks, flagged_bets, verbose=verbose)

            print("[INFO] Sending Top 5 card to Telegram...")
            _send_telegram_card(
                top5_picks=top5_picks,
                bet_map=bet_map,
                run_date=run_date,
                flagged_count=len(flagged_bets),
                claude_available=claude_available,
            )

        # ── Print token cost estimate
        try:
            # Attempt to get token usage from api_monitor if available
            from utils.api_monitor import get_monitor  # noqa: F401 (imported for side-effects/future use)

            # Get current session's Claude usage (if any)
            haiku_calls = len([b for b in bets if b.get('_injury_note', 'No injury') != 'No injury on record'])
            sonnet_calls = 1 if claude_available else 0

            # Rough estimates based on typical usage
            haiku_tokens_est = haiku_calls * 150  # ~100 in, ~50 out per call
            sonnet_tokens_est = sonnet_calls * 1200  # ~800 in, ~400 out

            # Cost estimates (Haiku: $0.80/$4 per 1M, Sonnet: $3/$15 per 1M)
            haiku_cost_est = (haiku_tokens_est * 0.80 / 1_000_000) + (haiku_tokens_est * 4 / 1_000_000)
            sonnet_cost_est = (sonnet_tokens_est * 3 / 1_000_000) + (sonnet_tokens_est * 15 / 1_000_000)
            total_cost_est = haiku_cost_est + sonnet_cost_est

            print(f"\n[TOKEN COST] Estimated usage this run:")
            print(f"  Haiku: {haiku_calls} calls, ~{haiku_tokens_est:,} tokens, ~${haiku_cost_est:.4f}")
            print(f"  Sonnet: {sonnet_calls} calls, ~{sonnet_tokens_est:,} tokens, ~${sonnet_cost_est:.4f}")
            print(f"  Total: ~${total_cost_est:.4f} (target: $0.08/day)")
        except Exception:
            # If api_monitor not available, skip token reporting
            pass

        print(
            f"\n[DONE] Phase 8.5 complete — "
            f"{len(top5_picks)} curated, {len(flagged_bets)} flagged"
        )

    finally:
        conn.close()


if __name__ == '__main__':
    main()
