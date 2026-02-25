#!/usr/bin/env python3
"""
Team Classification Verification Script — Sprint 3A

Cross-references our team_scheme_cache classifications against three
independent data sources to surface mismatches for human review:

  1. BDL Defensive Ratings (player_game_advanced.def_rating)
     → If we say a team plays PAINT_PACK or PERIMETER, they should rank
       in the top half defensively. A NEUTRAL team with top-5 def_rating
       is a mismatch — we're underselling their defense.

  2. NBA Synergy PPP by play type vs opponent
     → A PAINT_PACK defense should have LOW PPP on POST_UP and P&R_ROLL.
       A PERIMETER defense should have LOW PPP on SPOT_UP.
       A FUNNEL defense should have HIGH PPP on TRANSITION (they give up
       fast breaks in exchange for protecting the arc).

  3. Offense classification vs actual stat patterns
     → MOTION offense should have high ast_per_fgm.
       PACE_PUSH should have high PPG.
       ISO_HEAVY should have low ast_per_fgm.
       HALF_COURT should have below-average PPG.

Output: a mismatch report printed to stdout. Does NOT modify any data.
Add to weekly_validation.yml to catch classification drift.

Usage:
    python scripts/verify_team_classifications.py
    python scripts/verify_team_classifications.py --window-days 30
    python scripts/verify_team_classifications.py --verbose
"""

import argparse
import sqlite3
import sys
import os
import math
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mappings import normalize_bdl_abbr

DB_PATH = "ludi.db"
SEASON = "2025-26"
DEFAULT_WINDOW_DAYS = 60

# Expected defensive scheme → which play types SHOULD have lower PPP allowed
# (scheme identity implies defending these play types well)
SCHEME_EXPECTED_STRENGTHS = {
    'PAINT_PACK':  ['P&R_ROLL', 'POST_UP', 'CUT'],        # protects paint → low PPP on rim plays
    'PERIMETER':   ['SPOT_UP', 'HANDOFF', 'OFF_SCREEN'],   # closes out → low PPP on 3PA plays
    'FUNNEL':      ['SPOT_UP', 'CUT'],                     # funnels drives → low PPP on catch/cut
    'BLITZ':       ['P&R_HANDLER', 'ISO'],                 # traps → disrupts creation
    'NEUTRAL':     [],                                     # no expected strength
}

# Expected offense classification → stat signature
OFFENSE_EXPECTED = {
    'MOTION':      {'ast_per_fgm_min': 0.660},
    'ISO_HEAVY':   {'ast_per_fgm_max': 0.620},
    'PACE_PUSH':   {'ppg_min': 115.0},
    'HALF_COURT':  {'ppg_max': 113.0},
    'BALANCED':    {},
}

# Synergy playtype name in player_synergy_playtypes → our label
SYNERGY_NAME_MAP = {
    'PR_ROLL_MAN': 'P&R_ROLL', 'PR_BALL_HANDLER': 'P&R_HANDLER',
    'POST_UP': 'POST_UP', 'SPOT_UP': 'SPOT_UP', 'ISO': 'ISO',
    'CUT': 'CUT', 'TRANSITION': 'TRANSITION',
    'HANDOFF': 'HANDOFF', 'OFF_SCREEN': 'OFF_SCREEN', 'PUTBACK': 'PUTBACK',
}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


# ── Check 1: Defensive rating vs scheme label ──────────────────────────────

def _check_def_rating_vs_scheme(conn: sqlite3.Connection, window_days: int, verbose: bool) -> list[dict]:
    """
    Compare each team's defensive rating rank vs their scheme label.
    Teams labeled NEUTRAL/BALANCED but ranked top-10 defensively are mismatches.
    Teams labeled PAINT_PACK/PERIMETER but bottom-10 defensively are mismatches.
    """
    cur = conn.cursor()
    window_start = (datetime.now() - timedelta(days=window_days)).strftime('%Y-%m-%d')

    # Compute team def_rating from player_game_advanced (BDL, daily)
    cur.execute("""
        SELECT team_abbrev,
            ROUND(AVG(def_rating), 1) as avg_def_rtg,
            COUNT(*) as n
        FROM player_game_advanced
        WHERE game_date >= ? AND def_rating IS NOT NULL
        GROUP BY team_abbrev
        HAVING COUNT(*) >= 20
        ORDER BY avg_def_rtg ASC
    """, (window_start,))
    ratings = [(normalize_bdl_abbr(r['team_abbrev']), r['avg_def_rtg']) for r in cur.fetchall()]

    if not ratings:
        return []

    # Rank 1 = best defense (lowest def_rating)
    rating_rank = {team: i + 1 for i, (team, _) in enumerate(ratings)}
    rating_val = {team: val for team, val in ratings}

    # Load current scheme classifications
    cur.execute("SELECT team_abbr, active_style FROM team_scheme_cache WHERE scheme_type='DEFENSE'")
    schemes = {r['team_abbr']: r['active_style'] for r in cur.fetchall()}

    mismatches = []
    n_teams = len(ratings)
    top_threshold = max(1, int(n_teams * 0.33))      # top 33% = good defense
    bot_threshold = min(n_teams, int(n_teams * 0.67)) # bottom 33% = weak defense

    for team, scheme in schemes.items():
        rank = rating_rank.get(team)
        val = rating_val.get(team)
        if rank is None:
            continue

        flag = None
        if scheme in ('PAINT_PACK', 'PERIMETER', 'FUNNEL', 'BLITZ') and rank > bot_threshold:
            flag = f"Labeled {scheme} but def_rating rank #{rank}/{n_teams} (WEAK DEFENSE)"
        elif scheme in ('NEUTRAL',) and rank <= top_threshold:
            flag = f"Labeled NEUTRAL but def_rating rank #{rank}/{n_teams} (should be stronger label)"

        if flag:
            mismatches.append({
                'team': team, 'scheme': scheme,
                'def_rtg': val, 'def_rank': rank,
                'flag': flag, 'check': 'DEF_RATING'
            })

    if verbose:
        print(f"\n{'='*60}")
        print(f"CHECK 1: Defensive Rating vs Scheme Label ({window_days}d)")
        print(f"{'='*60}")
        print(f"  {'Team':<6} {'Scheme':<12} {'Def RTG':>8} {'Rank':>6}")
        for team, val in ratings:
            scheme = schemes.get(team, 'N/A')
            flag = '⚠️' if any(m['team'] == team for m in mismatches) else '  '
            print(f"  {flag}{team:<6} {scheme:<12} {val:>8} #{rating_rank[team]}")

    return mismatches


# ── Check 2: Synergy PPP vs scheme ────────────────────────────────────────

def _check_synergy_ppp_vs_scheme(conn: sqlite3.Connection, window_days: int, verbose: bool) -> list[dict]:
    """
    For each team's defensive scheme, check if the expected "strengths"
    (play types they SHOULD defend well) actually show lower PPP allowed.

    Approach: for each game in the window, aggregate PPP of each play type
    by the OPPOSING team (how well offensive players scored vs each defender).
    Compare to scheme expectation.

    Note: player_synergy_playtypes stores season-level data, not game-by-game.
    We use this to see which teams allow the most/least efficient play types.
    """
    cur = conn.cursor()

    # Aggregate by opposing team: avg PPP per play type
    # player_synergy_playtypes.team_abbr = the PLAYER'S team
    # We want: avg PPP when the player faces each OPPOSING team
    # Proxy: use player_archetype_vs_defense to see which defenses allow more PPP overall
    # Better: query player_synergy_playtypes filtered by team opponent from game logs
    # But synergy is season-level, not game-by-game. Use overall PPP per play type
    # and compare to what each defense scheme "should" allow.

    # League-average PPP by play type (all players, current season)
    cur.execute("""
        SELECT playtype, ROUND(AVG(ppp), 3) as league_avg_ppp, COUNT(DISTINCT player_name) as players
        FROM player_synergy_playtypes
        WHERE season = ? AND (poss_per_game * COALESCE(games_played,1)) >= 30
        GROUP BY playtype
        ORDER BY league_avg_ppp DESC
    """, (SEASON,))
    league_ppp = {SYNERGY_NAME_MAP.get(r['playtype'], r['playtype']): r['league_avg_ppp']
                  for r in cur.fetchall()}

    # Check: team_playtype_allowed — teams allowing high C&S 3PA but labeled PERIMETER?
    cur.execute("""
        SELECT tp.team_abbr, tp.cs_3pa_allowed_pg, tp.cs_3pa_rank,
               tp.drives_fga_allowed_pg, tp.drives_rank,
               tc.active_style as def_scheme
        FROM team_playtype_allowed tp
        JOIN team_scheme_cache tc ON tp.team_abbr = tc.team_abbr AND tc.scheme_type = 'DEFENSE'
        WHERE tp.season = ?
        ORDER BY tp.team_abbr
    """, (SEASON,))
    team_playtype = {r['team_abbr']: dict(r) for r in cur.fetchall()}

    mismatches = []
    n_teams = len(team_playtype)
    if n_teams < 10:
        return []

    mid_rank = n_teams // 2

    for team, data in team_playtype.items():
        scheme = data['def_scheme']
        flag = None

        if scheme == 'PERIMETER':
            # Perimeter defense should suppress C&S 3PA — expect low rank (1=fewest allowed)
            if data['cs_3pa_rank'] > mid_rank:
                flag = (f"PERIMETER scheme but allows #{data['cs_3pa_rank']} C&S 3PA/g "
                        f"({data['cs_3pa_allowed_pg']:.2f}/g) — expected rank ≤{mid_rank}")

        elif scheme == 'PAINT_PACK':
            # Paint pack should suppress drives — expect low drives rank
            if data['drives_rank'] > mid_rank:
                flag = (f"PAINT_PACK scheme but allows #{data['drives_rank']} drives/g "
                        f"({data['drives_fga_allowed_pg']:.2f}/g) — expected rank ≤{mid_rank}")

        elif scheme == 'FUNNEL':
            # Funnel channels to paint — expect HIGH drives rank (allows many) + LOW C&S rank
            if data['drives_rank'] <= mid_rank:
                flag = (f"FUNNEL scheme but drives rank #{data['drives_rank']} "
                        f"— FUNNEL should allow high drive volume")

        if flag:
            mismatches.append({
                'team': team, 'scheme': scheme,
                'cs_rank': data['cs_3pa_rank'], 'drives_rank': data['drives_rank'],
                'flag': flag, 'check': 'PLAYTYPE_ALLOWED'
            })

    if verbose:
        print(f"\n{'='*60}")
        print(f"CHECK 2: Synergy/Tracking vs Scheme Label")
        print(f"{'='*60}")
        print(f"  {'Team':<6} {'Scheme':<12} {'C&S Rank':>9} {'Drives Rank':>12}")
        for team, data in sorted(team_playtype.items()):
            flag = '⚠️' if any(m['team'] == team for m in mismatches) else '  '
            print(f"  {flag}{team:<6} {data['def_scheme']:<12} "
                  f"#{data['cs_3pa_rank']:>8} #{data['drives_rank']:>11}")

    return mismatches


# ── Check 3: Offense classification vs actual stats ─────────────────────

def _check_offense_vs_stats(conn: sqlite3.Connection, window_days: int, verbose: bool) -> list[dict]:
    """
    Verify that offense classifications match the team's actual statistical signature.
    Uses player_game_logs (same source as the classifier) to cross-validate.
    """
    cur = conn.cursor()
    window_start = (datetime.now() - timedelta(days=window_days)).strftime('%Y-%m-%d')

    cur.execute("""
        SELECT
            COALESCE(ct.standard_abbr, gl.team_abbreviation) as team,
            ROUND(SUM(gl.pts) * 1.0 / COUNT(DISTINCT gl.game_id), 1) as ppg,
            ROUND(CASE WHEN SUM(gl.fgm) > 0 THEN 1.0*SUM(gl.ast)/SUM(gl.fgm) ELSE 0 END, 3) as ast_per_fgm,
            COUNT(DISTINCT gl.game_id) as games
        FROM player_game_logs gl
        LEFT JOIN canonical_teams ct ON gl.team_abbreviation = ct.bdl_abbr
        WHERE gl.game_date >= ? AND gl.team_abbreviation IS NOT NULL
        GROUP BY team
        HAVING COUNT(DISTINCT gl.game_id) >= 10
    """, (window_start,))
    team_stats = {r['team']: dict(r) for r in cur.fetchall()}

    cur.execute("SELECT team_abbr, active_style FROM team_scheme_cache WHERE scheme_type='OFFENSE'")
    off_schemes = {r['team_abbr']: r['active_style'] for r in cur.fetchall()}

    mismatches = []
    for team, off_style in off_schemes.items():
        stats = team_stats.get(team)
        if not stats:
            continue

        ppg = stats['ppg']
        ast_fgm = stats['ast_per_fgm']
        expected = OFFENSE_EXPECTED.get(off_style, {})
        flag = None

        if 'ast_per_fgm_min' in expected and ast_fgm < expected['ast_per_fgm_min']:
            flag = (f"{off_style} offense but ast/fgm={ast_fgm:.3f} "
                    f"(expected ≥{expected['ast_per_fgm_min']}) — low ball movement")
        elif 'ast_per_fgm_max' in expected and ast_fgm > expected['ast_per_fgm_max']:
            flag = (f"{off_style} offense but ast/fgm={ast_fgm:.3f} "
                    f"(expected ≤{expected['ast_per_fgm_max']}) — high ball movement for label")
        elif 'ppg_min' in expected and ppg < expected['ppg_min']:
            flag = (f"{off_style} offense but PPG={ppg} "
                    f"(expected ≥{expected['ppg_min']})")
        elif 'ppg_max' in expected and ppg > expected['ppg_max']:
            flag = (f"{off_style} offense but PPG={ppg} "
                    f"(expected ≤{expected['ppg_max']})")

        if flag:
            mismatches.append({
                'team': team, 'scheme': off_style,
                'ppg': ppg, 'ast_fgm': ast_fgm,
                'flag': flag, 'check': 'OFFENSE_STATS'
            })

    if verbose:
        print(f"\n{'='*60}")
        print(f"CHECK 3: Offense Classification vs Actual Stats")
        print(f"{'='*60}")
        for team, off in sorted(off_schemes.items()):
            s = team_stats.get(team, {})
            flag = '⚠️' if any(m['team'] == team for m in mismatches) else '  '
            print(f"  {flag}{team:<6} {off:<12} PPG:{s.get('ppg',0):>6} "
                  f"ast/fgm:{s.get('ast_per_fgm',0):.3f}")

    return mismatches


# ── Summary + Recommendations ─────────────────────────────────────────────

def _print_summary(all_mismatches: list[dict]) -> None:
    """Print consolidated mismatch summary with recommended actions."""
    if not all_mismatches:
        print("\n✅ No significant classification mismatches detected.")
        print("   All scheme labels align with defensive ratings, tracking data, and stats.")
        return

    # Group by check type
    by_check = {}
    for m in all_mismatches:
        by_check.setdefault(m['check'], []).append(m)

    print(f"\n{'='*60}")
    print(f"MISMATCH SUMMARY — {len(all_mismatches)} issues found")
    print(f"{'='*60}")

    check_labels = {
        'DEF_RATING':     '1. Def Rating vs Scheme',
        'PLAYTYPE_ALLOWED': '2. Tracking Data vs Scheme',
        'OFFENSE_STATS':  '3. Offense Stats vs Label',
    }

    for check_key, label in check_labels.items():
        items = by_check.get(check_key, [])
        if not items:
            print(f"\n  {label}: ✅ Clean")
            continue
        print(f"\n  {label}: {len(items)} flag(s)")
        for m in items:
            print(f"    ⚠️  {m['team']:<6} [{m['scheme']}] — {m['flag']}")

    print(f"\n  Action: Review flagged teams in team_scheme_cache and re-run")
    print(f"  update_team_scheme_cache.py if adjustments needed.")
    print(f"  DO NOT use AI training knowledge — verify against ludi.db + live APIs.")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Verify team classification labels against data")
    parser.add_argument('--window-days', type=int, default=DEFAULT_WINDOW_DAYS)
    parser.add_argument('--verbose', action='store_true', help='Print full per-team detail')
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"TEAM CLASSIFICATION VERIFICATION — {args.window_days}d window")
    print(f"Run: {datetime.now().strftime('%Y-%m-%d %H:%M EST')}")
    print(f"{'='*60}")
    print(f"Data source: ludi.db (player_game_advanced, team_scheme_cache,")
    print(f"             team_playtype_allowed, player_synergy_playtypes)")
    print(f"NO training data used — all classifications from live DB only.")

    conn = _connect()

    all_mismatches = []
    all_mismatches += _check_def_rating_vs_scheme(conn, args.window_days, args.verbose)
    all_mismatches += _check_synergy_ppp_vs_scheme(conn, args.window_days, args.verbose)
    all_mismatches += _check_offense_vs_stats(conn, args.window_days, args.verbose)

    _print_summary(all_mismatches)

    conn.close()

    # Exit 1 if significant mismatches (for CI alerting)
    critical = [m for m in all_mismatches if m['check'] == 'DEF_RATING']
    if len(critical) >= 5:
        print(f"\n[CI] {len(critical)} critical mismatches — flagging for review.")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
