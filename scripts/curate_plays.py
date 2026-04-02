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
import random
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
from utils.claude_prompts import ROLE_PHILOSOPHY, ROSTER_RULES, ANALYSIS_PROTOCOL, ANALYSIS_PROTOCOL_CURATION
from utils.telegram_notifier import send_message, send_solomon_message
from utils.player_id_resolver import resolve_canonical_name
from utils.game_dossier import build_game_dossier
from utils.slack_notifier import send_slack_failure_alert

# ─── Constants ────────────────────────────────────────────────────────────────
PROMPT_VERSION = 'v2.1-preflight'
# Stats where an OUT/DOUBTFUL player bet OVER is clearly wrong
VOLUME_STATS = {'PTS', 'REB', 'AST', 'MIN'}
SANITY_FAIL_STATUSES = {'OUT', 'DOUBTFUL'}

SANITY_GATE_SYSTEM = """You are a bet sanity checker for an NBA analytics model. TEAM SOURCE RULE: The "Team (DB):" field in each prompt is the authoritative source for player team assignment. Do NOT use any external knowledge about where players play.
VALID OUTPUT ONLY: {"result": "PASS", "reason": ""} {"result": "FLAG", "reason": "<one sentence describing the contradiction>"}
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
    "ALTER TABLE bet_recommendations ADD COLUMN curation_grade TEXT",
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
              AND snapshot_time >= datetime('now', '-14 days')
              AND (days_out IS NULL OR days_out < 75)
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


def _fetch_player_team(conn: sqlite3.Connection, player_name: str) -> str:
    """Fetch team from players table — injected into Haiku + Sonnet prompts as authoritative."""
    canonical_name = resolve_canonical_name(conn, player_name)
    try:
        row = conn.execute(
            "SELECT team FROM players WHERE name = ? LIMIT 1", (canonical_name,)
        ).fetchone()
        return row[0] if row else ''
    except sqlite3.OperationalError:
        return ''



# ─── Stage 1: Haiku Sanity Gate ───────────────────────────────────────────────

def _format_player_block(
    player_name: str,
    team: str,
    archetype: str,
    bets: list[dict],
    injury: dict | None,
    dossier: dict,
) -> str:
    """Serializes one player's full context into a canonical text block."""
    lines = []
    
    # Header
    lines.append(f"=== {player_name} | Team (DB): {team} | Archetype: {archetype} ===")

    # Injury
    if injury:
        status = injury.get('status', 'UNKNOWN')
        days_out = injury.get('days_out', '??')
        desc = injury.get('description', 'No description')
        gdr = 'Yes' if injury.get('is_game_day_report') else 'No'
        lines.append(f"Injury: Status={status} | Days Out={days_out} | Desc={desc} | GameDayReport={gdr}")
    else:
        lines.append(f"Injury: No active record | Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC")

    # Exempt combos: confirmed high WR at high edge — skip HIGH_DIVERGENCE flag
    _HIGH_DIV_EXEMPT = {('BLK', 'UNDER'), ('3PM', 'UNDER'), ('REB', 'UNDER'), ('TOV', 'UNDER')}

    # Bets
    lines.append(f"Bets ({len(bets)}):")
    for bet in bets:
        if bet.get('bet_side', '').upper() == 'OVER':
            odds = bet.get('odds_over')
        else:
            odds = bet.get('odds_under')
        odds_str = f"@ {odds}" if odds else ""

        line = (
            f"  [{bet['id']}] {bet['stat_category']} {bet['bet_side']} {bet['line']} {odds_str} | "
            f"Tier={bet.get('confidence_tier', 'N/A')} | Edge=+{bet.get('true_edge', 0):.1f}% | "
            f"Proj={bet.get('projection', 'N/A')}"
        )
        lines.append(line)

        # HIGH_DIVERGENCE: flag bets where model edge diverges strongly from market consensus
        _stat = bet.get('stat_category', '').upper()
        _side = bet.get('bet_side', '').upper()
        if (bet.get('true_edge') or 0) >= 20.0 and (_stat, _side) not in _HIGH_DIV_EXEMPT:
            lines.append(
                f"  [HIGH_DIVERGENCE] Edge={bet.get('true_edge', 0):.1f}% >= 20% — MANDATORY CHECK: "
                f"name the specific reason this model probability is not overconfident before grading STRONG. "
                f"If no structural reason can be named (injury vacuum, confirmed steam, scheme edge confirmed in WR data), "
                f"downgrade to LEAN."
            )

    # Game Context & Dossier Signals
    if bets:
        game_bet = bets[0]
        game_id = game_bet.get('game_id')
        lines.append(
            f"Game: {game_bet.get('matchup', 'N/A')} | Spread={game_bet.get('spread', 'N/A')} | Total={game_bet.get('total', 'N/A')}"
        )
        if dossier and game_id in dossier and player_name in dossier[game_id]['players']:
            signals = dossier[game_id]['players'][player_name]
            lines.append(f"Dossier Signals: {signals}")
            
    return "\n".join(lines)


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


def _haiku_player_sanity_check(
    player_name: str,
    team: str,
    bets: list[dict],
    injury: dict | None,
    verbose: bool = False,
) -> tuple[str, str]:
    """
    Ask Haiku to sanity-check all bets for a single player.
    One API call per player.
    """
    # Run deterministic checks on each bet first. If any fails, hard-flag the player.
    for bet in bets:
        result, reason = _deterministic_sanity_check(bet, injury)
        if result == 'FLAG':
            if verbose:
                print(f"  [HAIKU-SKIP] Deterministic FLAG for {player_name}: {reason}")
            return 'FLAG', reason

    # If no injury, no need for nuanced check, pass all bets for this player.
    # Perplexity is not used here to keep Haiku gate minimal.
    if not injury:
        return 'PASS', ''
        
    injury_text = (
        f"Status: {injury['status']}\n"
        f"Days Out: {injury['days_out'] if injury['days_out'] is not None else 'Unknown'}\n"
        f"Description: {injury['description'] or 'None provided'}\n"
        f"Game Day Report: {'Yes' if injury['is_game_day_report'] else 'No'}"
    )

    bets_to_review_text = []
    for bet in bets:
        bets_to_review_text.append(
            f"  [{bet['id']}] {bet['stat_category']} {bet['bet_side']} {bet['line']} | "
            f"Proj: {bet.get('projection', 'N/A')} | Edge: +{bet.get('true_edge', 0):.1f}%"
        )
    
    system_prompt = f"{SANITY_GATE_SYSTEM}\n\n{ROSTER_RULES}\n\n{ANALYSIS_PROTOCOL}"
    
    user_prompt = f"""Sanity check all bets for this player. Team (DB) is authoritative.

PLAYER: {player_name}
Team (DB): {team}
INJURY (from official report, fetched today):
{injury_text}

BETS TO REVIEW ({len(bets)} total):
{chr(10).join(bets_to_review_text)}

FLAG this player ONLY if:
1. Player is OUT or DOUBTFUL and any bet is OVER a volume stat (PTS, REB, AST, MIN)
2. Injury context makes all their props unreliable (e.g., minutes restriction affects all)
Otherwise PASS. When in doubt, PASS. Return JSON only.
"""

    response = get_claude_analysis(
        prompt=user_prompt,
        system_prompt=system_prompt,
        model=HAIKU_MODEL,
        temperature=0.1,
        max_tokens=100,
        call_type='sanity_gate_player',
        player_name=player_name,
        game_date=bets[0].get('game_date') if bets else None,
    )

    if not response:
        if verbose:
            print(f"  [HAIKU] No response for {player_name} — defaulting PASS")
        return 'PASS', ''

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
            print(f"  [HAIKU] {player_name}: {result} — {reason}")
        return result, reason
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        raw_preview = response[:200] if response else "empty"
        print(f"[HAIKU PARSE FAIL] {player_name}: {type(e).__name__} | raw={raw_preview}")
        if verbose:
            print(f"  [HAIKU] Parse error for {player_name}: {e} — defaulting PASS")
        return 'PASS', ''


# ─── Stage 2: Sonnet Top 5 Curation ──────────────────────────────────────────
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
            HAVING COUNT(*) >= 5
            ORDER BY wr DESC
        """).fetchall()
    except Exception as e:
        print(f"[WR CONTEXT] DB query failed — Sonnet will curate without win rate context: {e}")
        return ""

    z = 1.96  # 95% confidence
    lines = [
        "LUDI-BOT EMPIRICAL WIN RATES (this season, Wilson 95% confidence floor):",
        "",
        "NOTE: The win rate data below is MEASURED historical outcome data from our settled bet database",
        "(4,207 bets). It is NOT generated or estimated. ANALYSIS_PROTOCOL rule 7 ('Do NOT generate",
        "win rates') does not apply here — these are injected empirical facts, not model-produced claims.",
        "Treat this table with the same authority as a stat injected from player_game_logs.",
        "",
        "WEIGHTING RULE — read WR grade FIRST, before edge%, before matchup:",
        "  A+ grade (floor >= 60%, n >= 500): WR is the primary signal. STRONG unless injury or",
        "      extreme correlation conflict overrides. Edge% is confirming evidence, not deciding factor.",
        "  A  grade (floor >= 55%, n >= 150): Prefer STRONG. Edge% must be >= 5% to confirm.",
        "  B  grade (floor >= 50%, n >= 50):  Default LEAN. Needs edge% >= 10% + clean matchup for STRONG.",
        "  C  grade (floor >= 45%):           Neutral. Grade by edge% and matchup normally.",
        "  D  grade (floor >= 40%):           Default LEAN. Needs overwhelming evidence for STRONG.",
        "  F  grade (floor < 40%):            Default FADE. Only structural factors can override to LEAN.",
        "",
        "WHY THIS MATTERS: Our data shows 4,207 settled bets. True_edge has near-zero correlation with",
        "outcome for high-edge bets (Amen Thompson PTS OVER 109.2% edge → LOSS). Wilson floor is the",
        "only statistically validated predictor we have. Edge% measures model conviction, not market",
        "efficiency. Grade WR first.",
    ]
    for stat, side, n, wr, wins in rows:
        p = wins / n
        denom = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denom
        margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
        lb = max(0.0, center - margin)

        if lb >= 0.60 and n >= 500:    grade, flag = "A+", " ← PRIORITIZE"
        elif lb >= 0.55 and n >= 150:  grade, flag = "A",  " ← PREFER"
        elif lb >= 0.50 and n >= 50:   grade, flag = "B",  ""
        elif lb >= 0.42:               grade, flag = "C",  " ← DEPRIORITIZE"
        elif lb >= 0.40:               grade, flag = "D",  " ← AVOID"
        else:                          grade, flag = "F",  " ← AVOID"

        # Tiered n-guard: ESTABLISHED (n >= 100) / EMERGING (20-99) / WATCH (< 20)
        if n >= 100:
            lines.append(f"  {stat} {side}: {wr:.0f}% WR (95% floor={lb*100:.0f}%, n={n}) [{grade}]{flag}")
        elif n >= 20:
            direction = "above" if wr >= 50 else "below"
            lines.append(f"  {stat} {side}: {wr:.0f}% WR (EMERGING — n={n}, direction={direction} 50%, treat as supporting signal) [{grade}*]")
        else:
            lines.append(f"  {stat} {side}: {wr:.0f}% WR (WATCH — n={n}, too small for statistical grade)")

    lines += [
        "",
        "KEY CALIBRATION NOTES:",
        "- BLOCKS UNDER: structural book edge — book lines are consistently set too high; prioritize even at lower edge",
        "- PTS/REB/PRA OVER: model OVERSTATES edge by 18-21%; require higher edge threshold before selecting",
        "- STEALS UNDER: improving trend — confidence growing as sample builds",
        "- REB OVER: actively degrading (WR falling late-season) — deprioritize unless edge >10%",
        "- PRA OVER: structural avoid — 25% WR on 80 bets, should be filtered before curation",
        "- EMERGING (*) signals: directional only — use to confirm an otherwise strong grade, not to create one.",
        "- WATCH signals: count too small for any statistical inference — note only, do not weight.",
    ]
    return "\n".join(lines)


def _sonnet_curate(
    passing_bets: list[dict],
    player_bets: dict[str, list[dict]],
    player_team: dict[str, str],
    player_injury: dict[str, dict | None],
    dossier: dict,
    verbose: bool = False,
) -> list[dict] | None:
    """
    Ask Sonnet to grade EVERY bet as STRONG/LEAN/FADE.
    Bets are sent in chunks of BATCH_SIZE to avoid 32k token overflow.
    game_counts is shared across all batches to enforce max-2-STRONG-per-game
    across the full day (not just per batch).
    """
    BATCH_SIZE = 50

    if not passing_bets:
        return None

    dossier_text = ""
    for gid, data in dossier.items():
        dossier_text += data['game_context'] + "\n\n"

    try:
        conn_wr = sqlite3.connect(DB_PATH)
        wr_context = _get_system_wr_context(conn_wr)
        conn_wr.close()
    except Exception as e:
        print(f"[WARN] WR context query failed — curation will proceed without empirical WR data: {e}")
        wr_context = ""

    system_prompt = f"{ROLE_PHILOSOPHY}\n\n{ROSTER_RULES}\n\n{ANALYSIS_PROTOCOL_CURATION}"
    system_prompt += "\n\nPrefer UNDER bets on BLK, 3PM, and STL — these have historically outperformed. Be conservative selecting OVER bets on PTS, AST, and 3PM unless the edge and injury context are compelling."

    if wr_context:
        system_prompt += f"\n\n{wr_context}"

    system_prompt += """

THREE-LENS ANALYTICAL PROTOCOL — apply in order before grading every bet:

LENS 1 — VALUE: Identify the structural mispricing reason.
  Valid VALUE reasons: injury vacuum (absent player redistributes usage), public overreaction
  (line moved against sharp book signal), line set on small sample (first 5 games of season),
  scheme edge (archetype vs opponent defense confirmed in wr_context), or referee tilt.
  If you cannot name a structural reason — the edge number alone is NOT a VALUE reason —
  apply downgrade pressure toward LEAN or FADE.

LENS 2 — MOMENTUM: Measure the player's current regime.
  Primary signal: L5 average vs L10 average for the relevant stat category.
  Rising trend (L5 > L10 by 10%+): momentum confirmation — use as supporting STRONG signal.
  Flat trend (L5 within 10% of L10): neutral — does not add or subtract.
  Cold streak (L5 < L10 by 10%+): yellow flag — downgrade pressure even on high-edge bets.
    A cold streak does NOT auto-force FADE, but it must be named and weighed against
    the VALUE lens before grading STRONG.
  If L5/L10 data is not present in the dossier: note as "momentum: data absent" and treat
  as neutral.

LENS 3 — CONTRARIAN: State the single most obvious bear case for this bet.
  Every bet gets a bear case named explicitly. Format: "[specific scenario] → [data response]."
  Examples of bear cases: opponent posts highest defensive rating against this archetype,
  player just returned from injury and may be on minutes restriction, game environment
  is high-spread blowout risk that caps volume, or correlated loss risk with other STRONG picks.
  Grade only reaches STRONG if the bear case is named AND dismissed with data.
  Grade stays LEAN if the bear case is real and cannot be fully dismissed.
  Grade becomes FADE if the bear case is the dominant signal.

STRONG PRE-FLIGHT (required before any STRONG grade):
  Before marking STRONG, answer all three:
  (1) Loss mechanism: name the specific scenario that makes this bet lose — not "bad game" or "off night."
      Cannot name a specific mechanism → downgrade to LEAN.
  (2) Steam check: if STEAM_MOVE tag is present, is it toward or against this bet direction?
      Steam against → name it in CONTRARIAN bear case. Steam toward → note as confirming.
  (3) Edge range check: does the WR grade hold at this exact edge level (per CALIBRATION SIGNAL below)?
      WR grade D/F at this edge range with no structural exception → downgrade to LEAN.

CONTRARIAN LENS — CALIBRATION SIGNAL (Sprint 4-A empirical finding):
  Kelly signal compresses above these thresholds — name a narrative reason or downgrade to LEAN:
  - PTS, AST, REB, STL: flag at true_edge > 14%
  - PRA, PA, PR, RA combos: flag at true_edge > 20%
  - BLK and 3PM (either side): EXEMPT at any edge

THREE-LENS GRADE LOGIC:
  STRONG: VALUE lens names a clear structural reason + MOMENTUM is flat or rising +
          CONTRARIAN bear case is named and dismissed with data + WR grade confirms.
  LEAN:   VALUE lens is present but weak, OR MOMENTUM is cold, OR bear case is real
          but not dominant. WR grade is B or below.
  FADE:   No clear VALUE reason, OR bear case is dominant, OR calibration flag fires
          with no narrative override, OR WR grade is D/F with no structural exception.
"""

    system_prompt += "\n\nOUTPUT SCHEMA — return ONLY valid JSON, no other text:\n[{\"bet_id\": 123, \"thinking\": \"VALUE: [structural mispricing reason or 'none identified']. MOMENTUM: [L5 vs L10 status — rising/flat/cold/data absent]. CONTRARIAN: [bear case stated] → [dismissed/sustained + data]. Final: [one-sentence decision].\", \"grade\": \"STRONG|LEAN|FADE\", \"reasoning\": \"one sentence\"}]"

    env = config.get_scoring_environment()
    over_rate = env.get('over_hit_rate_14d', 0)
    env_label = env.get('environment', 'NEUTRAL')
    env_context = f"\nSCORING ENVIRONMENT TODAY: {env_label} ({over_rate:.0%} 14d OVER hit rate). When in doubt between two OVER plays, prefer the one with stronger UNDER characteristics.\n" if env else ""

    # NOTE: Examples below use real players/teams as of 2026-03-09 for illustrative reasoning patterns only.
    # These are NOT live roster lookups. Refresh examples if featured players change teams.
    # Replace Example 4 (Claxton BKN) with a settled LEAN bet once one is available in claude_analysis_log.
    curate_examples = """
=== CURATION EXAMPLES ===

NOTE: All examples use the v2.0 Three-Lens thinking format (VALUE/MOMENTUM/CONTRARIAN/Final).
New bets being evaluated should follow this format as instructed in the THREE-LENS ANALYTICAL PROTOCOL above.

=== EXAMPLE 1 — BLK UNDER: A+ WR grade overrides yellow matchup flag (→ STRONG) ===
Input:
  Player: Jayson Tatum [BOS]
  Bet: BLK UNDER 0.5
  True edge: 34.9% | Tier: DIAMOND
  Archetype: TWO_LEVEL_SCORER
  Injury status: No active record
  Game context: BOS vs MIA, spread BOS -4.5, total 222.5
  Note in dossier: MIA ranks 3rd in rim frequency this season

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: BLK UNDER = A+ (Wilson floor 67.1%, n=918). Primary signal.
           Action: Default to STRONG unless hard override applies.
  Step 2 — Edge confirms: 34.9% DIAMOND edge. Strongly confirms the WR signal.
  Step 3 — Matchup flag: MIA high rim frequency could produce 1 block. Yellow flag, not red.
           At A+ WR grade, a yellow flag does NOT override to LEAN. Would need proven block
           frequency in Tatum's own log (he averages 0.5 BLK/g — structural UNDER holds).
  Step 4 — Grade: STRONG. WR primary signal + DIAMOND edge + acceptable matchup risk.

thinking: "VALUE: BLK UNDER A+ WR structural floor (67.1%, n=918) — category-level mispricing. MOMENTUM: no streak signal in BLK context. CONTRARIAN: MIA high rim freq → 1-block risk → dismissed (structural UNDER survives vs 0.5 line). Final: STRONG."
Grade: STRONG
Reasoning: BLK UNDER A+ empirical signal (67.1% floor, 918 bets) + DIAMOND edge confirms. Opponent rim frequency is a yellow flag but does not override A+ WR grade.
=== END EXAMPLE 1 ===

=== EXAMPLE 2 — PTS OVER: extreme edge% does NOT override absent WR (→ FADE) ===
Input:
  Player: Amen Thompson [HOU]
  Bet: PTS OVER 16.5
  True edge: 109.2% | Tier: DIAMOND
  Archetype: SLASHING_CREATOR
  Injury status: No active record
  Game context: HOU vs CLE, spread HOU -2.5, total 228.0
  Note in dossier: CLE defensive scheme = PERIMETER

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: PTS OVER does NOT appear in the A+/A/B section of the WR table.
           Absent from established WR table = D grade. No confirmed empirical edge.
  Step 2 — Edge check: 109.2% is an extreme outlier. ALERT: edge outliers >= 50% indicate
           volatile market conditions. They do NOT indicate a high-probability outcome.
  Step 3 — Matchup: CLE scheme is PERIMETER. Thompson is SLASHING_CREATOR — perimeter
           defense is neutral-to-negative for slash + drive volume. Neutral matchup signal.
  Step 4 — Grade: FADE. D-grade WR + extreme edge outlier flag. Edge% alone never makes STRONG.

thinking: "VALUE: no structural reason — D-grade WR, absent from A/A+ table. Edge 109.2% = market volatility flag, not signal. MOMENTUM: no trend data provided. CONTRARIAN: CLE PERIMETER neutral for SLASHING_CREATOR → bear case sustained (no WR floor). Final: FADE."
Grade: FADE
Reasoning: PTS OVER has no confirmed empirical edge in this system (absent from WR table). Extreme edge outlier (109.2%) signals market volatility, not probability certainty.
=== END EXAMPLE 2 ===

=== EXAMPLE 3 — PR UNDER: emerging signal, small n, handled correctly (→ STRONG with note) ===
Input:
  Player: Cooper Flagg [DAL]
  Bet: PR UNDER 25.5
  True edge: 38.8% | Tier: DIAMOND
  Archetype: TWO_LEVEL_SCORER
  Injury status: No active record
  Game context: DAL vs BKN, spread DAL -6.5, total 224.0

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: PR UNDER = C grade overall (Wilson floor 45.9%, n=404).
           HOWEVER: PR UNDER STRONG grade cases show 85.7% WR (EMERGING, n=7).
           This is a curation-conditional signal — grading LEAN destroys it (38.5% WR, n=26).
           Grading STRONG when factors align is the correct behavior.
  Step 2 — Edge confirms: 38.8% DIAMOND. Strong model conviction.
  Step 3 — Matchup: BKN is PERIMETER scheme. Flagg TWO_LEVEL_SCORER attacks paint + mid.
           Perimeter defense = neutral for Flagg volume. Blowout risk: DAL -6.5, below 7.5 threshold.
  Step 4 — n-guard: PR UNDER STRONG n=7 is WATCH-tier. Apply uncertainty note in reasoning.

thinking: "VALUE: STRONG-grade PR UNDER cases = 85.7% WR (WATCH n=7) — curation-conditional mispricing. MOMENTUM: no trend degradation noted. CONTRARIAN: WATCH-tier n=7 is wide CI → risk noted, not sustained. Final: STRONG (EMERGING note)."
Grade: STRONG
Reasoning: PR UNDER with STRONG curation shows 85.7% WR (WATCH, n=7) — grading LEAN destroys signal. DIAMOND edge + neutral matchup confirm. EMERGING signal — confidence interval wide, verify context.
=== END EXAMPLE 3 ===

=== EXAMPLE 4 — 3PM UNDER: A-grade WR, DIAMOND edge, but TREND OVERRIDE caps to LEAN ===
Input:
  Player: Jalen Suggs [ORL]
  Bet: 3PM UNDER 2.5 @ -154 (DraftKings)
  True edge: +18.2% | Tier: DIAMOND
  Projection: 1.90 | Line: 2.5 (gap: -0.60)
  Archetype: FACILITATOR
  Tags: FACILITATOR, vs_PAINT_PACK
  Injury status: Active
  Game context: ORL @ OKC, spread 10.0 (ORL big underdog), total 223.5

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: 3PM UNDER = A (56% floor, n=960). Default to STRONG.
  Step 2 — MOMENTUM check: L5 3PM hit rate: 1/5 (20%). L10: 3/10 (30%). Trend: DOWN.
           Rising 3PM shooter at line 2.5 might hold. Falling shooter in a blowout = risk.
  Step 3 — Edge: +18.2% DIAMOND. Real edge, projection 1.9 vs line 2.5 is a clean gap.
  Step 4 — CONTRARIAN: ORL down 10.0 — blowout scenario likely. Suggs min restriction in
           garbage time caps volume. Cold streak (L5 1/5) means he may not find rhythm.
  Step 5 — Grade: LEAN. A-grade WR + DIAMOND edge confirmed — but cold trend + blowout
           exposure reduce conviction. LEAN correctly captures: real edge, real concern.
           NOTE: Model thinking below computed "STRONG" — the trend flag and game context
           override applied AFTER thinking output. Final grade diverges from raw model call.

thinking: "VALUE: 3PM UNDER structural edge — projection 1.9 vs line 2.5, A-grade WR category (56% floor). MOMENTUM: L5 1/5 (20%) vs L10 3/10 (30%) — cold streak, trend DOWN. CONTRARIAN: ORL -10 underdog → blowout risk, starters sit Q4, Suggs loses volume opportunities → dismissed partially (gap is 0.6, structural edge survives), but cold trend sustained. Final: LEAN. Edge real but trend + game context reduce conviction."
Grade: LEAN
Reasoning: A-grade 3PM UNDER with DIAMOND edge, but cold shooting trend (L5 1/5) + blowout exposure (spread 10.0) reduce conviction below STRONG threshold.
=== END EXAMPLE 4 ===

=== EXAMPLE 5 — PTS OVER: DIAMOND edge + HOT_STREAK looks STRONG but WR grade + Kelly gate = LEAN ===
Input:
  Player: [STAR_PG] [TEAM]    ← placeholder per CLAUDE.md hygiene rule
  Bet: PTS OVER 24.5
  True edge: +52.0% | Tier: DIAMOND
  Projection: 27.8 | Line: 24.5 (gap: +3.3)
  Archetype: TWO_LEVEL_SCORER
  Tags: TWO_LEVEL_SCORER, HOT_STREAK, vs_NEUTRAL
  Injury status: Active
  Game context: Home game, spread 4.5 (home favored), total 228.0

Reasoning chain (consult WR grade FIRST):
  Step 1 — WR grade: PTS OVER = D (no A/A+ floor exists for PTS OVER in calibration data).
           PTS is the highest-variance stat category — no sustained Kelly-positive WR band.
           Cannot default to STRONG on WR context alone. WR grade D = treat as LEAN base.
  Step 2 — MOMENTUM check: HOT_STREAK tag present. L5 avg: 27.1, L10 avg: 24.3 (+11.5% rising).
           Rising trend is a positive signal — noted, but does not override WR grade concern.
  Step 3 — Edge: +52.0% DIAMOND. Edge is extreme. Note: ⚠️ VERIFY LINE flag applies above 25%
           edge. Extreme edges on PTS often indicate stale or soft market line, not model alpha.
  Step 4 — CONTRARIAN: Sprint 4-A calibration finding — PTS OVER above 14% edge: Kelly signal
           degrades or inverts. WR at 14%+ edge in PTS collapses to ~46-50% (below breakeven).
           HOT_STREAK + DIAMOND tier signal is real, but edge-to-WR mapping breaks down here.
           The model projects +3.3 gap, but that gap lives in the same collapsed WR pool.
  Step 5 — Grade: LEAN. HOT_STREAK + DIAMOND tier are real signals. But D-grade WR on PTS OVER
           + edge compression above 14% = stat_kelly_gate fires → SIZE_DOWN to 0.5u.
           LEAN, not STRONG. The model's confidence is higher than the calibration data supports.

thinking: "VALUE: HOT_STREAK + rising L5 (27.1 vs L10 24.3) + home game. Structural edge exists. MOMENTUM: rising trend confirmed +11.5%. CONTRARIAN: PTS OVER WR = D-grade, no calibration floor. Sprint 4-A — edge > 14% on PTS inverts Kelly. 52% edge extreme — verify line flag. HOT_STREAK masked the WR weakness. Bear case sustained: no calibration data supports PTS OVER STRONG above 14%. Final: LEAN. stat_kelly_gate applied (0.5u cap)."
Grade: LEAN
Reasoning: DIAMOND edge and HOT_STREAK are real, but PTS OVER WR grade is D (no calibration floor) and Sprint 4-A Kelly gate fires above 14% edge — size down to LEAN, not STRONG.
=== END EXAMPLE 5 ===

=== END EXAMPLES ===
"""

    # Split bets into chunks to avoid 32k token overflow on large slates.
    # game_counts is initialized ONCE here so max-2-STRONG-per-game applies
    # across ALL batches (not reset per batch).
    batches = [passing_bets[i:i + BATCH_SIZE] for i in range(0, len(passing_bets), BATCH_SIZE)]
    bet_id_to_game_map = {b['id']: b.get('game_id', '') for b in passing_bets}
    game_counts: dict[str, int] = {}
    all_results: list[dict] = []

    for batch_idx, batch in enumerate(batches):
        batch_set = {b['id'] for b in batch}
        bets_text = '\n\n'.join(
            _format_player_block(
                player_name=pname,
                team=player_team.get(pname, ''),
                archetype=pbets[0].get('archetype', 'UNKNOWN'),
                bets=pbets,
                injury=player_injury.get(pname),
                dossier=dossier,
            )
            for pname, pbets in player_bets.items()
            if any(b['id'] in batch_set for b in pbets)
        )

        user_prompt = f"""You are grading EVERY bet on today's NBA player prop slate as STRONG, LEAN, or FADE using the Three-Lens protocol in your system instructions.

HARD RULES:
- Maximum 2 STRONG bets from the same game_id (avoid correlated losses in one game)
- Diversify STRONG picks across stat types (do not pick 5 PTS bets)
- DO NOT recalculate, adjust, or question any edge/probability/projection values — they are authoritative outputs from a deterministic simulation model
- Return JSON array only

{env_context}
{curate_examples}

=== GAME DOSSIER ===
{dossier_text}

TODAY'S CLEAN BETS ({len(batch)} in this batch, already passed injury sanity gate):
{bets_text}

Grade every bet listed above. Return JSON array only."""

        if verbose:
            print(f"  [SONNET] Batch {batch_idx + 1}/{len(batches)}: sending {len(batch)} bets...")

        response = get_claude_analysis(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=SONNET_MODEL,
            temperature=0.1,
            max_tokens=16000,
            call_type='curation',
        )

        if not response:
            if verbose:
                print(f"  [SONNET] Batch {batch_idx + 1}: no response — will use deterministic fallback")
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

            for item in data:
                if 'bet_id' in item and 'grade' in item:
                    bet_id = int(item['bet_id'])
                    grade = str(item['grade']).upper()
                    game_id = bet_id_to_game_map.get(bet_id, '')

                    # Enforce max-2-STRONG-per-game across the ENTIRE day (shared game_counts)
                    if grade == 'STRONG':
                        if game_counts.get(game_id, 0) >= 2:
                            if verbose:
                                print(f"  [SONNET] Downgrading {bet_id} to LEAN - already 2 STRONG from game {game_id}")
                            grade = 'LEAN'
                        else:
                            game_counts[game_id] = game_counts.get(game_id, 0) + 1

                    all_results.append({
                        'bet_id': bet_id,
                        'grade': grade,
                        'thinking': str(item.get('thinking', '')),  # CoT trace — logged to claude_analysis_log for audit
                        'reasoning': str(item.get('reasoning', '')),
                    })

        except (json.JSONDecodeError, ValueError, KeyError, IndexError) as e:
            raw_preview = response[:200] if response else "empty"
            print(f"[SONNET PARSE FAIL] Batch {batch_idx + 1} | {type(e).__name__} | raw={raw_preview}")
            if verbose:
                print(f"  [SONNET] Parse error on batch {batch_idx + 1}: {e} — will use deterministic fallback")
            return None

    if not all_results:
        print("[SONNET PARSE FAIL] No valid picks parsed from any batch response")
        return None

    strong_bets = [r for r in all_results if r['grade'] == 'STRONG']
    id_to_edge = {b['id']: b.get('true_edge', 0) for b in passing_bets}
    strong_bets.sort(key=lambda x: id_to_edge.get(x['bet_id'], 0), reverse=True)

    for i, bet in enumerate(strong_bets):
        bet['rank'] = i + 1

    if verbose:
        print(f"  [SONNET] Successfully graded {len(all_results)} bets ({len(strong_bets)} STRONG) across {len(batches)} batch(es)")
    return all_results


# ─── Deterministic Fallback ───────────────────────────────────────────────────
def _deterministic_top(passing_bets: list[dict]) -> list[dict]:
    """
    Fallback curation when Claude is unavailable or fails to parse.
    Sorts by true_edge DESC, enforces max-2-per-game constraint.
    Returns top 10 by edge.
    """
    selected = []
    game_counts: dict[str, int] = {}

    for bet in sorted(passing_bets, key=lambda b: b.get('true_edge') or 0, reverse=True):
        if len(selected) >= 10:
            break
        game_id = bet.get('game_id', '')
        if game_counts.get(game_id, 0) < 2:
            selected.append(bet)
            game_counts[game_id] = game_counts.get(game_id, 0) + 1

    return [
        {'bet_id': b['id'], 'grade': 'STRONG', 'rank': i + 1, 'reasoning': ''}
        for i, b in enumerate(selected)
    ]


# ─── DB Writes ────────────────────────────────────────────────────────────────
def _write_curation_results(
    conn: sqlite3.Connection,
    graded_picks: list[dict],
    flagged_bets: list[dict],
    bet_map: dict,
    run_date: str,
    verbose: bool = False,
) -> None:
    """Write curated grades and rankings back to bet_recommendations."""
    for pick in graded_picks:
        conn.execute("""
            UPDATE bet_recommendations
            SET curation_grade = ?,
                is_curated = ?,
                curated_rank = ?
            WHERE id = ?
        """, (
            pick['grade'],
            1 if pick['grade'] == 'STRONG' else 0,
            pick.get('rank') if pick['grade'] == 'STRONG' else None,
            pick['bet_id']
        ))
        if verbose:
            print(f"  [DB] Marked bet {pick['bet_id']} as {pick['grade']} rank {pick.get('rank', 'N/A')}")

    for bet in flagged_bets:
        conn.execute("""
            UPDATE bet_recommendations
            SET sanity_flagged = 1, sanity_flag_reason = ?
            WHERE id = ?
        """, (bet['_flag_reason'], bet['id']))
        if verbose:
            print(f"  [DB] Flagged bet {bet['id']}: {bet['_flag_reason']}")

    # Phase 8.23-F: Per-bet logging in claude_analysis_log
    for pick in graded_picks:
        bet = bet_map.get(pick.get('bet_id'), {})
        try:
            conn.execute(
                """
                INSERT INTO claude_analysis_log
                    (call_type, model, game_date, player_name,
                     stat_category, bet_side, curation_grade, bet_id,
                     true_edge, thinking_text, prompt_version,
                     input_tokens, output_tokens, estimated_cost_usd, response_text,
                     signal_available_at, acted_on_at)
                VALUES ('curation_per_bet', 'batch', ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0.0, '', NULL, NULL)
                """,
                (
                    run_date,
                    bet.get('player_name'),
                    bet.get('stat_category'),
                    bet.get('bet_side'),
                    pick.get('grade'),
                    pick.get('bet_id'),
                    bet.get('true_edge'),
                    str(pick.get('thinking', ''))[:2000],
                    PROMPT_VERSION,
                )
            )
        except Exception as e:
            print(f"[WARN] claude_analysis_log per-bet insert failed for bet_id={pick.get('bet_id')}: {e}")

    conn.commit()


# ─── Phase 8.26: Same-Game Pair Correlation Detection ────────────────────────
# Stats that are component/subset relationships — betting both is high risk in SGP
CORRELATED_STAT_PAIRS = {
    frozenset(['PTS', 'PRA']), frozenset(['REB', 'PRA']), frozenset(['AST', 'PRA']),
    frozenset(['PTS', 'PA']),  frozenset(['REB', 'PR']),  frozenset(['AST', 'PA']),
    frozenset(['PTS', 'PR']),
}


def _detect_same_game_pairs(strong_picks: list[dict], bet_map: dict) -> list[dict]:
    """
    Scan STRONG picks for same-game pairs and assess SGP correlation risk.
    """
    from collections import defaultdict
    game_groups: dict[str, list] = defaultdict(list)
    for pick in strong_picks:
        bet = bet_map.get(pick['bet_id'])
        if not bet:
            continue
        game_id = bet.get('game_id', '')
        if game_id:
            game_groups[game_id].append(bet)

    flags = []
    for game_id, bets in game_groups.items():
        if len(bets) < 2:
            continue
        for i in range(len(bets)):
            for j in range(i + 1, len(bets)):
                b1, b2 = bets[i], bets[j]
                stat1 = (b1.get('stat_category') or '').upper()
                stat2 = (b2.get('stat_category') or '').upper()
                same_player = b1.get('player_name') == b2.get('player_name')
                same_side = b1.get('bet_side', '').upper() == b2.get('bet_side', '').upper()
                stat_pair = frozenset([stat1, stat2])

                if same_player:
                    risk = 'HIGH'
                    reason = 'Same player — performances are correlated'
                elif stat_pair in CORRELATED_STAT_PAIRS:
                    risk = 'HIGH'
                    reason = (
                        f'{stat1} is a component of {stat2}'
                        if 'PRA' in [stat1, stat2]
                        else f'{stat1}+{stat2} highly correlated'
                    )
                elif same_side and b1.get('team') == b2.get('team'):
                    risk = 'MODERATE'
                    reason = 'Same team, same direction — blowout/pace affects both'
                else:
                    risk = 'LOW'
                    reason = 'Different players, different teams in same game'

                matchup = b1.get('matchup', game_id)
                flags.append({
                    'players': f"{b1['player_name']} {stat1} + {b2['player_name']} {stat2}",
                    'matchup': matchup,
                    'risk': risk,
                    'reason': reason,
                })
    return flags


# ─── Telegram Card ────────────────────────────────────────────────────────────
def _escape_markdown_v2(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2."""
    # Order matters: backslash first, then others
    chars_to_escape = ['\\', '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    return text


def _send_telegram_card(
    graded_picks: list[dict],
    bet_map: dict[int, dict],
    dossier: dict,
    run_date: str,
    flagged_count: int,
    claude_available: bool,
    sgp_flags: list[dict] | None = None,
) -> None:
    """Send formatted Top Plays card to Telegram."""
    date_str = datetime.strptime(run_date, '%Y-%m-%d').strftime('%b %d, %Y')
    mode_tag = 'AI-Curated' if claude_available else 'Edge-Sorted (AI unavailable)'

    # Filter to STRONG only for the main card, limit to top 10
    strong_picks = [p for p in graded_picks if p['grade'] == 'STRONG']
    strong_picks.sort(key=lambda p: p.get('rank', 999))
    strong_picks = strong_picks[:10]

    header = f"🎯 *TOP PLAYS — {_escape_markdown_v2(date_str)}*"
    subheader = f"_{_escape_markdown_v2(mode_tag)} \\| S\\.A\\.V\\.A\\.G\\.E\\. Protocol_"
    
    rank_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

    def _build_card(picks_slice):
        lines = [header, subheader, ""]
        for pick in picks_slice:
            bet = bet_map.get(pick['bet_id'])
            if not bet: continue
            
            rank = pick.get('rank', 0)
            rank_emoji = rank_emojis[rank - 1] if 1 <= rank <= 10 else f"{rank}\\."
            tier = bet.get('confidence_tier', 'N/A')
            tier_emoji = TIER_EMOJI.get(tier, '📌')

            if bet.get('bet_side', '').upper() == 'OVER':
                odds = bet.get('odds_over')
            else:
                odds = bet.get('odds_under')
            odds_str = f" @ {odds}" if odds else ""

            # Escape strings
            pname_esc = _escape_markdown_v2(bet['player_name'])
            stat_esc = _escape_markdown_v2(bet['stat_category'])
            side_esc = _escape_markdown_v2(str(bet['bet_side']))
            line_esc = _escape_markdown_v2(str(bet['line']))
            odds_esc = _escape_markdown_v2(odds_str)
            matchup_esc = _escape_markdown_v2(bet.get('matchup', 'Unknown'))
            edge_esc = _escape_markdown_v2(f"{bet.get('true_edge', 0):.1f}")
            proj_esc = _escape_markdown_v2(str(bet.get('projection', 'N/A')))
            tier_esc = _escape_markdown_v2(tier)

            lines.append(f"{rank_emoji} *{pname_esc}* — {stat_esc} {side_esc} {line_esc}{odds_esc}")
            lines.append(f"{tier_emoji} {tier_esc} \\| Edge: \\+{edge_esc}% \\| Proj: {proj_esc} \\| {matchup_esc}")
            
            # Game context from dossier
            gid = bet.get('game_id')
            if gid in dossier:
                ctx = dossier[gid]['game_context'].split('\n')[1] # Get the NEWS line or first relevant line
                if 'NEWS:' in ctx:
                    ctx = ctx.replace('NEWS:', '').strip()
                lines.append(f"📋 _{_escape_markdown_v2(ctx[:100])}\\.\\.\\._")

            if pick.get('reasoning'):
                reason_esc = _escape_markdown_v2(pick['reasoning'])
                lines.append(f"💬 _{reason_esc}_")
            lines.append("")
        
        return "\n".join(lines)

    # Split into multiple sends if more than 5
    if len(strong_picks) > 5:
        cards = [_build_card(strong_picks[:5]), _build_card(strong_picks[5:])]
    else:
        cards = [_build_card(strong_picks)]

    for i, message in enumerate(cards):
        # Add footer only to last card
        if i == len(cards) - 1:
            footer = []
            if sgp_flags:
                risk_emoji = {'HIGH': '🔴', 'MODERATE': '🟡', 'LOW': '🟢'}
                footer.append("🔗 *SGP RISK:*")
                for flag in sgp_flags:
                    emoji = risk_emoji.get(flag['risk'], '⚠️')
                    p_esc = _escape_markdown_v2(flag['players'])
                    m_esc = _escape_markdown_v2(flag['matchup'])
                    r_esc = _escape_markdown_v2(flag['reason'])
                    footer.append(f"{emoji} {p_esc} \\({m_esc}\\)")
                    footer.append(f"   _{r_esc}_")
                footer.append("")

            if flagged_count > 0:
                footer.append(f"⚠️ *Flagged:* {flagged_count} bet\\(s\\) removed by injury sanity gate")
            footer.append("_Edge is model output\\. Not financial advice\\._")
            message += "\n" + "\n".join(footer)

        success = send_message(message, parse_mode="MarkdownV2")
        if not success:
            send_message(message, parse_mode=None)


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
        from collections import defaultdict
        # ── Schema migrations (safe, idempotent)
        _run_migrations(conn)

        # ── Fetch today's unsettled bets
        bets = _fetch_todays_bets(conn, run_date)
        if not bets:
            print(f"[INFO] No unsettled bets found for {run_date}. Nothing to curate.")
            return

        print(f"[INFO] Found {len(bets)} bets to process\n")

        # ── Build game dossier (NEW)
        dossier = build_game_dossier(conn, run_date, bets)

        # ─────────────────────────────────────────────────────────
        # STAGE 1: Haiku Sanity Gate (Player-Grouped)
        # ─────────────────────────────────────────────────────────
        print(f"[STAGE 1] Haiku Sanity Gate — grouping {len(bets)} bets by player...")
        
        player_bets: dict[str, list[dict]] = defaultdict(list)
        player_injury: dict[str, dict | None] = {}
        player_team: dict[str, str] = {}

        for bet in bets:
            pname = bet['player_name']
            player_bets[pname].append(bet)
            if pname not in player_injury:
                player_injury[pname] = _fetch_player_injury(conn, pname)
                player_team[pname] = _fetch_player_team(conn, pname)
            
            # Annotate injury note on each bet for deterministic fallback + informational purposes
            if player_injury[pname]:
                inj = player_injury[pname]
                days_str = f"{inj['days_out']}d " if inj['days_out'] is not None else ""
                note = f"{inj.get('status', '??')}, {days_str}({inj.get('description') or 'no description'})"
            else:
                note = 'No injury on record'
            bet['_injury_note'] = note

        passing_bets: list[dict] = []
        flagged_bets: list[dict] = []
        
        print(f"[STAGE 1] Checking {len(player_bets)} unique players...")
        for pname, pbets in player_bets.items():
            result, reason = _haiku_player_sanity_check(
                player_name=pname,
                team=player_team.get(pname, ''),
                bets=pbets,
                injury=player_injury.get(pname),
                verbose=verbose,
            )

            if result == 'FLAG':
                for bet in pbets:
                    bet['_flag_reason'] = reason
                flagged_bets.extend(pbets)
                if verbose:
                    print(f"  ❌ FLAGGED ({len(pbets)} bets): {pname} — {reason}")
            else:
                passing_bets.extend(pbets)

        print(
            f"\n[STAGE 1] Complete: {len(passing_bets)} passing, "
            f"{len(flagged_bets)} flagged\n"
        )

        if not passing_bets:
            print("[WARNING] All bets flagged by sanity gate — nothing left to curate")
            send_slack_failure_alert(
                "Curation: Zero bets passed sanity gate",
                f"Date: {date.today()}\nAll {len(flagged_bets)} bets were flagged — nothing reached Sonnet curation. Check injury flags or bet_recommendations table."
            )
            if not dry_run:
                _write_curation_results(conn, [], flagged_bets, bet_map={}, run_date=run_date, verbose=verbose)
            return

        # ─────────────────────────────────────────────────────────
        # STAGE 2: Sonnet Curation
        # ─────────────────────────────────────────────────────────
        print(f"[STAGE 2] Sonnet Curation — grading {len(passing_bets)} passing bets...")

        # Shuffle to eliminate position bias — LLM-as-Judge research shows earlier items rated systematically higher
        random.shuffle(passing_bets)

        sonnet_result = _sonnet_curate(
            passing_bets=passing_bets,
            player_bets=player_bets,
            player_team=player_team,
            player_injury=player_injury,
            dossier=dossier,
            verbose=verbose,
        )
        claude_available = sonnet_result is not None

        if not claude_available:
            print("[WARNING] Claude unavailable — using edge-sorted deterministic fallback")
            send_slack_failure_alert(
                "Curation: Claude API unavailable",
                f"Date: {date.today()}\nSonnet curation failed — fell back to edge-sorted deterministic ranking for {len(passing_bets)} bets. Check Anthropic API status or quota."
            )
            graded_picks = _deterministic_top(passing_bets)
        else:
            graded_picks = sonnet_result

        # Build ID → bet lookup for output and Telegram
        bet_map: dict[int, dict] = {b['id']: b for b in bets}

        # ── Print summary
        strong_picks = [p for p in graded_picks if p['grade'] == 'STRONG']
        print(f"\n[RESULT] {len(strong_picks)} STRONG plays found:")
        for pick in sorted(strong_picks, key=lambda p: p.get('rank', 999)):
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
            _write_curation_results(conn, graded_picks, flagged_bets, bet_map=bet_map, run_date=run_date, verbose=verbose)

            print("[INFO] Sending curation card to Telegram...")
            # Detect same-game correlation pairs for STRONG picks
            sgp_flags = _detect_same_game_pairs(strong_picks, bet_map)
            if sgp_flags:
                print(f"[SGP] {len(sgp_flags)} same-game pair(s) detected for warning")
            
            _send_telegram_card(
                graded_picks=graded_picks,
                bet_map=bet_map,
                dossier=dossier,
                run_date=run_date,
                flagged_count=len(flagged_bets),
                claude_available=claude_available,
                sgp_flags=sgp_flags,
            )

        # ── Print token cost estimate
        try:
            # Attempt to get token usage from api_monitor if available
            from utils.api_monitor import get_monitor  # noqa: F401 (imported for side-effects/future use)

            haiku_calls = len(player_bets) # One call per player
            sonnet_calls = 1 if claude_available else 0

            # Rough estimates based on typical usage
            haiku_tokens_est = haiku_calls * 1200
            sonnet_tokens_est = sonnet_calls * 35000 

            # Cost estimates (Haiku: $0.25/$1.25 per 1M, Sonnet: $3/$15 per 1M)
            haiku_cost_est = (haiku_tokens_est / 1_000_000 * 0.25) + (haiku_tokens_est / 1_000_000 * 1.25)
            sonnet_cost_est = (sonnet_tokens_est / 1_000_000 * 3) + (sonnet_tokens_est / 1_000_000 * 15)
            total_cost_est = haiku_cost_est + sonnet_cost_est

            print(f"\n[TOKEN COST] Estimated usage this run:")
            print(f"  Haiku: {haiku_calls} calls, ~{haiku_tokens_est:,} tokens, ~${haiku_cost_est:.4f}")
            print(f"  Sonnet: {sonnet_calls} calls, ~{sonnet_tokens_est:,} tokens, ~${sonnet_cost_est:.4f}")
            print(f"  Total: ~${total_cost_est:.4f}")
        except Exception:
            pass

        print(
            f"\n[DONE] Phase 8.5 complete — "
            f"{len(strong_picks)} curated, {len(flagged_bets)} flagged"
        )

    finally:
        conn.close()


if __name__ == '__main__':
    main()
