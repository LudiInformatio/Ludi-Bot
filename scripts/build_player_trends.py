#!/usr/bin/env python3
"""
Phase 8.15 — Build Player Trends
Pre-computes L7/L10/L15 averages, season averages, trend labels, and
streak-vs-season-avg for all active players across 12 stat types.

Writes to: player_trends table (UPSERT via INSERT OR REPLACE)
Runs: Daily at 3 AM in data_sync.yml (after game log sync)
Pattern: Zero API calls — pure SQL against player_game_logs.

Usage:
  python scripts/build_player_trends.py             # full run
  python scripts/build_player_trends.py --dry-run   # print only, no writes
  python scripts/build_player_trends.py --min-games 3  # lower minimum (default 5)
"""

import argparse
import sqlite3
import sys
import os
from datetime import datetime

# Allow running from repo root or scripts/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')

# Stat column mapping — matches player_game_logs schema exactly
STAT_COL = {
    'PTS': 'pts', 'REB': 'reb', 'AST': 'ast', '3PM': 'fg3m',
    'BLK': 'blk', 'STL': 'stl', 'TOV': 'tov',
}

# Combo stat SQL expressions
COMBO_EXPR = {
    'PRA': '(pts + reb + ast)',
    'PA': '(pts + ast)',
    'PR': '(pts + reb)',
    'RA': '(reb + ast)',
}

# All stat types to compute (single + combo + minutes)
ALL_STATS = list(STAT_COL.keys()) + list(COMBO_EXPR.keys()) + ['MIN']

# Trend thresholds
TREND_UP_THRESHOLD = 1.5    # l7 - l15 >= 1.5 → "UP"
TREND_DOWN_THRESHOLD = -1.5  # l7 - l15 <= -1.5 → "DOWN"


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _get_active_players(conn):
    """Get active players who have recent game logs (last 21 days)."""
    rows = conn.execute("""
        SELECT DISTINCT p.player_id, p.name, p.team
        FROM players p
        JOIN player_game_logs pgl ON pgl.player_id = p.player_id
        WHERE pgl.game_date >= date('now', '-21 days')
          AND pgl.minutes > 0
          AND p.team IS NOT NULL
    """).fetchall()
    return [(r['player_id'], r['name'], r['team']) for r in rows]


def _get_stat_expr(stat: str) -> str:
    """Return SQL expression for a stat type."""
    if stat == 'MIN':
        return 'minutes'
    if stat in COMBO_EXPR:
        return COMBO_EXPR[stat]
    if stat in STAT_COL:
        return STAT_COL[stat]
    raise ValueError(f"Unknown stat: {stat}")


def _compute_trends_for_player(conn, player_id, player_name, team_abbr, stat, min_games):
    """Compute trend data for one player/stat combination."""
    expr = _get_stat_expr(stat)

    # Query last 15 games for windowed averages
    rows = conn.execute(f"""
        SELECT {expr} as val, game_date
        FROM player_game_logs
        WHERE player_id = ? AND team_abbreviation = ?
          AND minutes > 0
        ORDER BY game_date DESC
        LIMIT 15
    """, (str(player_id), team_abbr)).fetchall()

    if len(rows) < min_games:
        return None

    values = [r['val'] for r in rows if r['val'] is not None]
    if len(values) < min_games:
        return None

    games_found = len(values)

    # Windowed averages
    l7 = sum(values[:min(7, len(values))]) / min(7, len(values)) if values else 0
    l10 = sum(values[:min(10, len(values))]) / min(10, len(values)) if values else 0
    l15 = sum(values) / len(values) if values else 0

    # Season average (all games on current team this season)
    season_row = conn.execute(f"""
        SELECT AVG({expr}) as avg_val
        FROM player_game_logs
        WHERE player_id = ? AND team_abbreviation = ? AND minutes > 0
          AND season_id = '2025-26'
    """, (str(player_id), team_abbr)).fetchone()
    season_avg = season_row['avg_val'] if season_row and season_row['avg_val'] else l15

    # Prior season average (Phase 2A — cross-season BREAKOUT/REGRESSION signal)
    prior_row = conn.execute(f"""
        SELECT AVG({expr}) as avg_val
        FROM player_game_logs
        WHERE player_id = ? AND minutes > 0
          AND season_id = '2024-25'
    """, (str(player_id),)).fetchone()
    prior_season_avg = prior_row['avg_val'] if prior_row and prior_row['avg_val'] else None

    # Season-over-season signal (only meaningful for stats with real volume, not BLK/STL for guards)
    trend_signal = None
    season_delta_pct = None
    if prior_season_avg and prior_season_avg >= 1.0 and season_avg:
        season_delta_pct = round((season_avg - prior_season_avg) / prior_season_avg, 3)
        if season_delta_pct >= 0.20:
            trend_signal = 'BREAKOUT'
        elif season_delta_pct <= -0.20:
            trend_signal = 'REGRESSION'
        else:
            trend_signal = 'STABLE'

    # Trend delta and label (within-season: L7 vs L15)
    trend_delta = round(l7 - l15, 1)
    if trend_delta >= TREND_UP_THRESHOLD:
        trend_label = f"UP +{trend_delta}"
    elif trend_delta <= TREND_DOWN_THRESHOLD:
        trend_label = f"DOWN {trend_delta}"
    else:
        trend_label = "STABLE"

    # Streak vs season average: consecutive games above(+) or below(-) season avg
    # Skip streak calc for stats with very low averages (e.g. 3PM for centers) — not meaningful
    streak = 0
    if values and season_avg and season_avg >= 1.0:
        first_above = values[0] > season_avg
        for v in values:
            if first_above and v > season_avg:
                streak += 1
            elif not first_above and v <= season_avg:
                streak -= 1
            else:
                break

    return {
        'player_id': str(player_id),
        'player_name': player_name,
        'team_abbreviation': team_abbr,
        'stat': stat,
        'l7_avg': round(l7, 2),
        'l10_avg': round(l10, 2),
        'l15_avg': round(l15, 2),
        'season_avg': round(season_avg, 2),
        'trend_delta': trend_delta,
        'trend_label': trend_label,
        'streak_vs_avg': streak,
        'games_found': games_found,
        'prior_season_avg': round(prior_season_avg, 2) if prior_season_avg else None,
        'season_delta_pct': season_delta_pct,
        'trend_signal': trend_signal,
        'computed_at': datetime.now().isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Build Player Trends")
    parser.add_argument("--dry-run", action="store_true", help="Print only, no DB writes")
    parser.add_argument("--min-games", type=int, default=5, help="Minimum games required (default 5)")
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"   📈 BUILD PLAYER TRENDS (Phase 8.15)")
    print(f"   Stats: {len(ALL_STATS)} types | Min games: {args.min_games}")
    print(f"{'='*50}\n")

    conn = _get_conn()
    players = _get_active_players(conn)
    print(f"📋 Active players with recent logs: {len(players)}")

    results = []
    errors = 0

    for player_id, player_name, team_abbr in players:
        for stat in ALL_STATS:
            try:
                trend = _compute_trends_for_player(
                    conn, player_id, player_name, team_abbr, stat, args.min_games
                )
                if trend:
                    results.append(trend)
            except Exception as e:
                errors += 1
                if errors <= 5:
                    print(f"   ⚠️ Error {player_name}/{stat}: {e}")

    print(f"\n📊 Computed {len(results)} trend rows ({errors} errors)")

    if args.dry_run:
        # Print sample trends
        up_trends = [r for r in results if r['trend_label'].startswith('UP')]
        down_trends = [r for r in results if r['trend_label'].startswith('DOWN')]
        streaks = sorted(results, key=lambda x: abs(x['streak_vs_avg']), reverse=True)

        print(f"\n🔥 TRENDING UP ({len(up_trends)} total):")
        for r in sorted(up_trends, key=lambda x: x['trend_delta'], reverse=True)[:8]:
            print(f"   {r['player_name']:<25} {r['stat']:<4} L7:{r['l7_avg']:.1f} vs L15:{r['l15_avg']:.1f} ({r['trend_label']})")

        print(f"\n❄️ TRENDING DOWN ({len(down_trends)} total):")
        for r in sorted(down_trends, key=lambda x: x['trend_delta'])[:8]:
            print(f"   {r['player_name']:<25} {r['stat']:<4} L7:{r['l7_avg']:.1f} vs L15:{r['l15_avg']:.1f} ({r['trend_label']})")

        print(f"\n🔥 LONGEST STREAKS (vs season avg):")
        for r in streaks[:10]:
            direction = "above" if r['streak_vs_avg'] > 0 else "below"
            print(f"   {r['player_name']:<25} {r['stat']:<4} {abs(r['streak_vs_avg'])}g {direction} avg (avg:{r['season_avg']:.1f})")

        breakouts = [r for r in results if r.get('trend_signal') == 'BREAKOUT']
        regressions = [r for r in results if r.get('trend_signal') == 'REGRESSION']
        if breakouts or regressions:
            print(f"\n📈 SEASON-OVER-SEASON BREAKOUTS ({len(breakouts)}):")
            for r in sorted(breakouts, key=lambda x: x.get('season_delta_pct', 0), reverse=True)[:8]:
                print(f"   {r['player_name']:<25} {r['stat']:<4} {r['season_avg']:.1f} vs prior {r['prior_season_avg']:.1f} (+{r['season_delta_pct']*100:.0f}%)")
            print(f"\n📉 SEASON-OVER-SEASON REGRESSIONS ({len(regressions)}):")
            for r in sorted(regressions, key=lambda x: x.get('season_delta_pct', 0))[:8]:
                print(f"   {r['player_name']:<25} {r['stat']:<4} {r['season_avg']:.1f} vs prior {r['prior_season_avg']:.1f} ({r['season_delta_pct']*100:.0f}%)")
    else:
        # Write to DB
        written = 0
        for r in results:
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO player_trends
                    (player_id, player_name, team_abbreviation, stat,
                     l7_avg, l10_avg, l15_avg, season_avg,
                     trend_delta, trend_label, streak_vs_avg, games_found,
                     prior_season_avg, season_delta_pct, trend_signal, computed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    r['player_id'], r['player_name'], r['team_abbreviation'], r['stat'],
                    r['l7_avg'], r['l10_avg'], r['l15_avg'], r['season_avg'],
                    r['trend_delta'], r['trend_label'], r['streak_vs_avg'], r['games_found'],
                    r.get('prior_season_avg'), r.get('season_delta_pct'), r.get('trend_signal'),
                    r['computed_at'],
                ))
                written += 1
            except Exception as e:
                print(f"   ⚠️ Write error {r['player_name']}/{r['stat']}: {e}")

        conn.commit()
        signals = sum(1 for r in results if r.get('trend_signal') in ('BREAKOUT', 'REGRESSION'))
        print(f"✅ Wrote {written} rows to player_trends ({signals} cross-season signals)")

    conn.close()
    print("Done.")


if __name__ == '__main__':
    main()
