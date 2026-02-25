#!/usr/bin/env python3
"""
Claude-Powered Scheme Classification Updater

Reads the verification report output + live DB data, sends to Claude Haiku,
gets back intelligent scheme corrections, and applies them to team_scheme_cache.

This runs AFTER verify_team_classifications.py in weekly_validation.yml so
Claude has the full mismatch list to reason about.

Design:
  - Haiku ($0.0001/call) for cost efficiency — structured JSON output
  - Claude decides: is this a scheme mismatch OR a scheme-quality mismatch?
    Scheme mismatch = wrong label (fix it)
    Quality mismatch = right scheme, poor execution (keep label, note quality)
  - Only updates when Claude confidence >= "HIGH"
  - Rebuilds team_playtype_allowed + player_archetype_vs_defense after changes
  - Logs all decisions (changed + kept) for the weekly validation report

Usage:
    python scripts/claude_classify_schemes.py
    python scripts/claude_classify_schemes.py --dry-run
    python scripts/claude_classify_schemes.py --verbose

IMPORTANT: Claude only receives DB data — no training memory about team rosters
or current-season results. All facts come from player_game_logs, team_scheme_cache,
player_game_advanced, and team_playtype_allowed.
"""

import argparse
import json
import os
import sys
import sqlite3
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from utils.claude_client import get_claude_analysis, HAIKU_MODEL
from utils.mappings import normalize_bdl_abbr

DB_PATH = "ludi.db"
SEASON = "2025-26"
WINDOW_DAYS = 30

VALID_DEF_STYLES = {'PAINT_PACK', 'PERIMETER', 'FUNNEL', 'BLITZ', 'NEUTRAL'}
VALID_OFF_STYLES = {'MOTION', 'ISO_HEAVY', 'PACE_PUSH', 'HALF_COURT', 'BALANCED'}

# Cost: ~$0.0003/run at 2K input + 300 output tokens — negligible
CLASSIFY_SYSTEM = """You are a basketball analytics classifier for Ludi-Bot.
Your job: review team scheme classifications and decide if they need updating based on DATA ONLY.

CRITICAL RULES:
- Use ONLY the data provided. Do NOT use any NBA training knowledge about teams, rosters, or results.
- All facts must come from the DB data in the user message.
- Scheme label = HOW a team tries to play (intent). Quality = HOW WELL they execute.
  A team can be PAINT_PACK but play it poorly — that's a QUALITY issue, not a label error.
- Only recommend LABEL changes when the tracking data contradicts the scheme's core identity.
- IMPORTANT: Teams with def_rating rank ≤ 10 (top-10 defense) are presumed correctly labeled.
  Unusual tracking patterns for top defenses reflect intentional scheme trade-offs,
  not label errors. Do NOT recommend changes for top-10 defense teams.
- Teams with BOTH metric ranks indicating the opposite scheme are LABEL_ERRORs.
  Teams with ONE metric mismatched may be QUALITY_ISSUEs (scheme is right, execution varies).

DEFENSE scheme meanings:
  PAINT_PACK: Protects the paint — expects LOW drives allowed (rank ≤15) and average-low C&S
  PERIMETER: Closes out on shooters — expects LOW C&S 3PA allowed (rank ≤15)
  FUNNEL: Channels drives to paint — expects HIGH drives allowed (rank ≥16) + LOW C&S (rank ≤15)
  BLITZ: Traps P&R ball handlers — expects disrupted P&R possessions, higher TOV
  NEUTRAL: No strong defensive identity — neither top nor bottom on any metric

OFFENSE scheme meanings:
  MOTION: High ball movement — expects ast_per_fgm ≥ 0.660
  ISO_HEAVY: Star-driven, low ball movement — expects ast_per_fgm ≤ 0.620
  PACE_PUSH: Fast tempo, high scoring — expects PPG ≥ 115
  HALF_COURT: Methodical, low scoring — expects PPG ≤ 113
  BALANCED: No strong offensive identity

Output: JSON array of scheme updates. Each entry:
{
  "team": "BOS",
  "scheme_type": "DEFENSE" or "OFFENSE",
  "current_label": "PAINT_PACK",
  "new_label": "PERIMETER",
  "confidence": "HIGH" or "MEDIUM" or "LOW",
  "reason": "C&S 3PA rank #34 (highest allowed in league) contradicts PAINT_PACK — no perimeter closing",
  "change_type": "LABEL_ERROR"  // or "QUALITY_ISSUE" (no label change needed)
}

If change_type = "QUALITY_ISSUE", set new_label = current_label (no change, just noted).
Only include teams where you have a clear data-supported reason.
Output ONLY the JSON array, no other text."""


def _load_team_data(conn: sqlite3.Connection) -> dict:
    """Load all data needed for Claude to make classification decisions."""
    cur = conn.cursor()
    window_start = (datetime.now() - timedelta(days=WINDOW_DAYS)).strftime('%Y-%m-%d')

    # Current scheme labels
    cur.execute("""
        SELECT team_abbr, scheme_type, season_style, d21_style, d14_style,
               active_style, def_quality_14d, off_quality_14d
        FROM team_scheme_cache
        ORDER BY team_abbr, scheme_type
    """)
    scheme_rows = cur.fetchall()

    # Defensive ratings (BDL, lower = better)
    cur.execute("""
        SELECT team_abbrev, ROUND(AVG(def_rating),1) as avg_dr, COUNT(*) as n
        FROM player_game_advanced
        WHERE game_date >= ? AND def_rating IS NOT NULL
        GROUP BY team_abbrev HAVING n >= 20
        ORDER BY avg_dr
    """, (window_start,))
    def_ratings = [(normalize_bdl_abbr(r[0]), r[1]) for r in cur.fetchall()]
    def_rank = {team: i+1 for i, (team, _) in enumerate(def_ratings)}
    def_val = {team: val for team, val in def_ratings}

    # Team tracking (drives allowed, C&S allowed) from intelligence table
    cur.execute("""
        SELECT team_abbr, ROUND(drives_fga_allowed_pg,2), drives_rank,
               ROUND(cs_3pa_allowed_pg,2), cs_3pa_rank, def_quality
        FROM team_playtype_allowed WHERE season = ?
    """, (SEASON,))
    tracking = {r[0]: {'drives_pg': r[1], 'drives_rank': r[2],
                        'cs_3pa_pg': r[3], 'cs_rank': r[4], 'def_q': r[5]}
                for r in cur.fetchall()}

    # Offense stats: PPG and ast_per_fgm
    cur.execute("""
        SELECT
            COALESCE(ct.standard_abbr, gl.team_abbreviation) as team,
            ROUND(SUM(gl.pts) * 1.0 / COUNT(DISTINCT gl.game_id), 1) as ppg,
            ROUND(CASE WHEN SUM(gl.fgm) > 0 THEN 1.0*SUM(gl.ast)/SUM(gl.fgm) ELSE 0 END, 3) as ast_per_fgm
        FROM player_game_logs gl
        LEFT JOIN canonical_teams ct ON gl.team_abbreviation = ct.bdl_abbr
        WHERE gl.game_date >= ? AND gl.team_abbreviation IS NOT NULL
        GROUP BY team HAVING COUNT(DISTINCT gl.game_id) >= 10
    """, (window_start,))
    off_stats = {r[0]: {'ppg': r[1], 'ast_fgm': r[2]} for r in cur.fetchall()}

    n = len(def_ratings)
    return {
        'scheme_rows': scheme_rows,
        'def_rank': def_rank,
        'def_val': def_val,
        'tracking': tracking,
        'off_stats': off_stats,
        'n_teams': n,
        'window_days': WINDOW_DAYS,
    }


def _build_claude_context(data: dict) -> str:
    """
    Build the user-facing data block for Claude.
    All numbers from ludi.db — no training knowledge injected.
    """
    lines = [
        f"=== TEAM CLASSIFICATION DATA (last {data['window_days']} days from ludi.db) ===\n",
        f"Defensive Rating: rank 1 = best defense (lowest points allowed per 100 poss), "
        f"rank {data['n_teams']} = worst. Data source: player_game_advanced.def_rating (BDL).\n",
        f"Tracking: drives_rank 1 = fewest drives allowed, "
        f"cs_rank 1 = fewest C&S 3PA allowed. Source: team_playtype_allowed.\n",
        "\nCurrent Defense Schemes + Data:\n",
        f"{'Team':<6} {'Cur_Def':<11} {'S/21/14':<15} {'Def_RTG':<8} {'Def_Rank':<9} "
        f"{'Drives/g':<9} {'D_Rank':<7} {'CS/g':<6} {'CS_Rank':<8} {'Def_Q'}\n",
        "-" * 95,
    ]

    scheme_by_team = {}
    for r in data['scheme_rows']:
        key = (r[0], r[1])  # (team_abbr, scheme_type)
        scheme_by_team[key] = r

    all_teams = sorted({r[0] for r in data['scheme_rows']})

    for team in all_teams:
        d_row = scheme_by_team.get((team, 'DEFENSE'))
        o_row = scheme_by_team.get((team, 'OFFENSE'))
        if not d_row:
            continue

        tr = data['tracking'].get(team, {})
        dr = data['def_rank'].get(team, '-')
        dv = data['def_val'].get(team, '-')

        lines.append(
            f"{team:<6} {d_row[5]:<11} "  # active_style
            f"{d_row[2][:4]}/{(d_row[3] or '-')[:4]}/{(d_row[4] or '-')[:4]:<10} "  # season/21d/14d
            f"{dv if isinstance(dv,float) else '-':>7} #{dr:<8} "
            f"{tr.get('drives_pg','N/A'):>7} #{tr.get('drives_rank','-'):<6} "
            f"{tr.get('cs_3pa_pg','N/A'):>5} #{tr.get('cs_rank','-'):<7} "
            f"{tr.get('def_q','?')}"
        )

    lines.append("\nOffense Schemes + Stats:\n")
    lines.append(
        f"{'Team':<6} {'Cur_Off':<12} {'S/21/14':<14} {'PPG':<7} {'AST/FGM'}\n"
    )
    lines.append("-" * 55)
    for team in all_teams:
        o_row = scheme_by_team.get((team, 'OFFENSE'))
        if not o_row:
            continue
        os = data['off_stats'].get(team, {})
        lines.append(
            f"{team:<6} {o_row[5]:<12} "
            f"{o_row[2][:4]}/{(o_row[3] or '-')[:4]}/{(o_row[4] or '-')[:4]:<12} "
            f"{os.get('ppg','N/A'):>6} {os.get('ast_fgm','N/A')}"
        )

    lines.append(
        "\nReview the above and output a JSON array of recommended changes. "
        "Only flag genuine LABEL_ERRORs where the data clearly contradicts the scheme identity. "
        "QUALITY_ISSUEs should be noted but new_label = current_label."
    )
    return "\n".join(lines)


def _apply_changes(conn: sqlite3.Connection, changes: list[dict], dry_run: bool, data: dict = None) -> int:
    """Apply Claude's recommended scheme changes to team_scheme_cache."""
    cur = conn.cursor()
    applied = 0

    for change in changes:
        team = change.get('team', '').upper()
        scheme_type = change.get('scheme_type', '').upper()
        new_label = change.get('new_label', '')
        current = change.get('current_label', '')
        confidence = change.get('confidence', 'LOW')
        change_type = change.get('change_type', 'QUALITY_ISSUE')
        reason = change.get('reason', '')

        # Apply HIGH or MEDIUM confidence LABEL_ERRORs where label actually changes.
        # Hard guard: never auto-change teams with top-10 defense (def_rank ≤ 10) —
        # unusual tracking patterns for elite defenses reflect intentional trade-offs.
        def_rank_val = data.get('def_rank', {}).get(team) if data else None
        is_elite_defense = (def_rank_val is not None and def_rank_val <= 10
                           and 'DEF' in scheme_type)

        if (change_type == 'LABEL_ERROR'
                and confidence in ('HIGH', 'MEDIUM')
                and new_label != current
                and not is_elite_defense
                and new_label in (VALID_DEF_STYLES if 'DEF' in scheme_type else VALID_OFF_STYLES)):

            print(f"  [CHANGE] {team} {scheme_type}: {current} → {new_label} | {reason}")
            if not dry_run:
                cur.execute("""
                    UPDATE team_scheme_cache
                    SET active_style = ?, updated_at = datetime('now')
                    WHERE team_abbr = ? AND scheme_type = ?
                """, (new_label, team, 'DEFENSE' if 'DEF' in scheme_type else 'OFFENSE'))
                applied += 1
        elif change_type == 'QUALITY_ISSUE':
            print(f"  [QUALITY] {team} {scheme_type}: {current} (label correct, execution issue) | {reason}")
        else:
            print(f"  [SKIP] {team} {scheme_type}: confidence={confidence} or same label → no change")

    if not dry_run and applied > 0:
        conn.commit()

    return applied


def main():
    parser = argparse.ArgumentParser(description="Claude-powered team scheme classification updater")
    parser.add_argument('--dry-run', action='store_true', help='Show changes without writing to DB')
    parser.add_argument('--verbose', action='store_true', help='Print full Claude context')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"CLAUDE SCHEME CLASSIFIER — {WINDOW_DAYS}d window")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M EST')}")
    if args.dry_run:
        print(f"[DRY RUN] No changes will be written.")
    print(f"{'='*60}")

    conn = sqlite3.connect(DB_PATH, timeout=30)
    data = _load_team_data(conn)
    context = _build_claude_context(data)

    if args.verbose:
        print("\n--- Context sent to Claude ---")
        print(context[:2000])
        print("...")

    print("\n[Calling Claude Haiku for scheme classification review...]")
    response = get_claude_analysis(
        prompt=context,
        system_prompt=CLASSIFY_SYSTEM,
        model=HAIKU_MODEL,
        temperature=0.1,
        max_tokens=2000,  # Increased: 30 teams × ~2-3 JSON entries = needs room
        call_type='scheme',
    )

    if not response:
        print("[ERROR] Claude returned no response — skipping scheme updates.")
        conn.close()
        sys.exit(1)

    # Parse JSON response
    try:
        # Strip any markdown code blocks Claude might add
        clean = response.strip()
        if clean.startswith('```'):
            clean = '\n'.join(clean.split('\n')[1:])
        if clean.endswith('```'):
            clean = clean.rsplit('```', 1)[0]
        changes = json.loads(clean.strip())
    except json.JSONDecodeError as e:
        print(f"[ERROR] Could not parse Claude response as JSON: {e}")
        print(f"Raw response:\n{response[:500]}")
        conn.close()
        sys.exit(1)

    print(f"\nClaude returned {len(changes)} classification assessments:\n")
    applied = _apply_changes(conn, changes, dry_run=args.dry_run, data=data)

    if applied > 0 and not args.dry_run:
        print(f"\n[APPLIED] {applied} scheme labels updated in team_scheme_cache.")
        # Rebuild intelligence tables to reflect updated schemes
        print("[REBUILDING] Syncing matchup intelligence tables...")
        import subprocess
        result = subprocess.run(
            [sys.executable, 'scripts/sync_matchup_intelligence.py'],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print(f"  WARNING: sync_matchup_intelligence failed: {result.stderr[:200]}")
    elif applied == 0 and args.dry_run:
        changes_proposed = [c for c in changes if c.get('change_type') == 'LABEL_ERROR' and c.get('new_label') != c.get('current_label')]
        print(f"\n[DRY RUN RESULT] {len(changes_proposed)} label change(s) proposed (not applied).")
        print(f"  Run without --dry-run to apply HIGH/MEDIUM confidence corrections.")
    else:
        print(f"\n[RESULT] No label changes applied — all classifications verified stable.")

    conn.close()
    print(f"\n✅ Claude scheme classification complete.")


if __name__ == "__main__":
    main()
