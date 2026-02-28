#!/usr/bin/env python3
"""
Team Betting Trends Sync

Computes per-team H/A records, scoring averages, and ATS splits from internal ludi.db data.
No external API calls needed.

Sources:
- canonical_games: game pairings (home_team / away_team per date)
- player_game_logs: team scores (SUM(pts) per team per game_date)
- bet_recommendations: spread lines (AVG spread per game for ATS computation)

Run: daily after data_sync.yml game log step, or manually.
Designed for GitHub Actions automation (data_sync.yml step).

ATS convention: positive spread = home team is underdog (getting points)
- Home covers if: (home_score - away_score) + spread > 0
- Away covers if: (home_score - away_score) + spread < 0  (push = 0, excluded)
"""

import sqlite3
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SEASON_START = '2025-10-01'


def _build_game_scores(conn):
    """
    Build complete game-level score pairs from canonical_games + player_game_logs.
    Returns list of dicts: {date, home_team, away_team, home_score, away_score, margin}

    Uses canonical_games as the join anchor to ensure exactly one row per game
    (avoids the 3× row inflation from games table's 3 game_id formats).
    """
    rows = conn.execute('''
        SELECT cg.date, cg.home_team, cg.away_team,
               h.home_score, a.away_score,
               h.home_score - a.away_score AS margin
        FROM canonical_games cg
        JOIN (
            SELECT game_date, team_abbreviation, SUM(pts) AS home_score
            FROM player_game_logs
            WHERE pts IS NOT NULL
            GROUP BY game_date, team_abbreviation
        ) h ON cg.date = h.game_date AND cg.home_team = h.team_abbreviation
        JOIN (
            SELECT game_date, team_abbreviation, SUM(pts) AS away_score
            FROM player_game_logs
            WHERE pts IS NOT NULL
            GROUP BY game_date, team_abbreviation
        ) a ON cg.date = a.game_date AND cg.away_team = a.team_abbreviation
        WHERE cg.date >= ?
        AND h.home_score >= 60   -- sanity: exclude DNP/empty box scores
        AND a.away_score >= 60
        ORDER BY cg.date
    ''', (SEASON_START,)).fetchall()

    return [
        {'date': r[0], 'home': r[1], 'away': r[2],
         'home_score': r[3], 'away_score': r[4], 'margin': r[5]}
        for r in rows
    ]


def _build_spread_lookup(conn):
    """
    Build per-game spread lookup from bet_recommendations.
    Returns dict: {(date, home_team): avg_spread}

    Multiple bets per game → AVG spread (accounts for line movement during day).
    """
    rows = conn.execute('''
        SELECT game_date, home_team, AVG(spread) AS avg_spread
        FROM bet_recommendations
        WHERE spread IS NOT NULL AND home_team IS NOT NULL AND home_team != ''
        GROUP BY game_date, home_team
    ''').fetchall()

    return {(r[0], r[1]): r[2] for r in rows}


def compute_team_trends(conn, season_start=SEASON_START):
    """
    Main computation. Returns dict: {team_abbr: trend_dict}
    """
    print(f"   [TRENDS] Building game scores from canonical_games + player_game_logs...")
    games = _build_game_scores(conn)
    print(f"   [TRENDS] {len(games)} complete game scores found for {season_start}+")

    print(f"   [TRENDS] Loading spread lookup from bet_recommendations...")
    spread_lookup = _build_spread_lookup(conn)
    print(f"   [TRENDS] {len(spread_lookup)} games have spread data")

    # Per-team accumulators
    trends = {}

    def _init(team):
        if team not in trends:
            trends[team] = {
                'team': team,
                'home_wins': 0, 'home_losses': 0,
                'away_wins': 0, 'away_losses': 0,
                'home_ats_wins': 0, 'home_ats_losses': 0,
                'away_ats_wins': 0, 'away_ats_losses': 0,
                'home_scores': [], 'home_allowed': [],
                'away_scores': [], 'away_allowed': [],
                'game_totals': [],
                'ats_games_tracked': 0,
            }

    for g in games:
        home = g['home']
        away = g['away']
        _init(home)
        _init(away)

        home_score = g['home_score']
        away_score = g['away_score']
        margin = g['margin']     # positive = home won
        game_total = home_score + away_score

        # H/A win-loss records
        if margin > 0:
            trends[home]['home_wins'] += 1
            trends[away]['away_losses'] += 1
        elif margin < 0:
            trends[home]['home_losses'] += 1
            trends[away]['away_wins'] += 1
        # Push (margin=0): excluded from W-L

        # Scoring averages
        trends[home]['home_scores'].append(home_score)
        trends[home]['home_allowed'].append(away_score)
        trends[away]['away_scores'].append(away_score)
        trends[away]['away_allowed'].append(home_score)
        trends[home]['game_totals'].append(game_total)
        trends[away]['game_totals'].append(game_total)

        # ATS (requires spread data for this game)
        spread = spread_lookup.get((g['date'], home))
        if spread is not None:
            # Home covers if: margin + spread > 0
            # Away covers if: margin + spread < 0
            ats_result = margin + spread
            if ats_result > 0:
                trends[home]['home_ats_wins'] += 1
                trends[away]['away_ats_losses'] += 1
            elif ats_result < 0:
                trends[home]['home_ats_losses'] += 1
                trends[away]['away_ats_wins'] += 1
            # Push (ats_result=0): excluded from ATS W-L
            trends[home]['ats_games_tracked'] += 1
            trends[away]['ats_games_tracked'] += 1

    # Convert lists to averages
    results = {}
    for team, t in trends.items():
        total_games = len(t['home_scores']) + len(t['away_scores'])
        results[team] = {
            'team': team,
            'home_wins': t['home_wins'],
            'home_losses': t['home_losses'],
            'away_wins': t['away_wins'],
            'away_losses': t['away_losses'],
            'home_ats_wins': t['home_ats_wins'],
            'home_ats_losses': t['home_ats_losses'],
            'away_ats_wins': t['away_ats_wins'],
            'away_ats_losses': t['away_ats_losses'],
            'home_avg_score': round(sum(t['home_scores']) / len(t['home_scores']), 1) if t['home_scores'] else None,
            'home_avg_allowed': round(sum(t['home_allowed']) / len(t['home_allowed']), 1) if t['home_allowed'] else None,
            'away_avg_score': round(sum(t['away_scores']) / len(t['away_scores']), 1) if t['away_scores'] else None,
            'away_avg_allowed': round(sum(t['away_allowed']) / len(t['away_allowed']), 1) if t['away_allowed'] else None,
            'avg_game_total': round(sum(t['game_totals']) / len(t['game_totals']), 1) if t['game_totals'] else None,
            'games_tracked': total_games,
            'ats_games_tracked': t['ats_games_tracked'],
        }

    return results


def upsert_team_trends(conn, trends, dry_run=False):
    """Upsert team trends to team_betting_trends table."""
    now = datetime.now().isoformat()
    count = 0

    for team, t in trends.items():
        if dry_run:
            h_rec = f"{t['home_wins']}-{t['home_losses']}"
            a_rec = f"{t['away_wins']}-{t['away_losses']}"
            h_ats = f"{t['home_ats_wins']}-{t['home_ats_losses']}"
            print(f"   [DRY RUN] {team}: H={h_rec} A={a_rec} H-ATS={h_ats} "
                  f"h_avg={t['home_avg_score']}/{t['home_avg_allowed']} "
                  f"a_avg={t['away_avg_score']}/{t['away_avg_allowed']} "
                  f"g_total={t['avg_game_total']}")
            count += 1
            continue

        conn.execute('''
            INSERT INTO team_betting_trends (
                team, home_wins, home_losses, away_wins, away_losses,
                home_ats_wins, home_ats_losses, away_ats_wins, away_ats_losses,
                home_avg_score, home_avg_allowed, away_avg_score, away_avg_allowed,
                avg_game_total, games_tracked, ats_games_tracked, last_updated
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(team) DO UPDATE SET
                home_wins=excluded.home_wins, home_losses=excluded.home_losses,
                away_wins=excluded.away_wins, away_losses=excluded.away_losses,
                home_ats_wins=excluded.home_ats_wins, home_ats_losses=excluded.home_ats_losses,
                away_ats_wins=excluded.away_ats_wins, away_ats_losses=excluded.away_ats_losses,
                home_avg_score=excluded.home_avg_score, home_avg_allowed=excluded.home_avg_allowed,
                away_avg_score=excluded.away_avg_score, away_avg_allowed=excluded.away_avg_allowed,
                avg_game_total=excluded.avg_game_total, games_tracked=excluded.games_tracked,
                ats_games_tracked=excluded.ats_games_tracked, last_updated=excluded.last_updated
        ''', (
            t['team'], t['home_wins'], t['home_losses'], t['away_wins'], t['away_losses'],
            t['home_ats_wins'], t['home_ats_losses'], t['away_ats_wins'], t['away_ats_losses'],
            t['home_avg_score'], t['home_avg_allowed'], t['away_avg_score'], t['away_avg_allowed'],
            t['avg_game_total'], t['games_tracked'], t['ats_games_tracked'], now
        ))
        count += 1

    if not dry_run:
        conn.commit()

    return count


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Sync team betting trends from internal DB data')
    parser.add_argument('--db-path', default='ludi.db', help='Path to database')
    parser.add_argument('--dry-run', action='store_true', help='Print but do not write')
    parser.add_argument('--season-start', default=SEASON_START, help='Season start date')
    args = parser.parse_args()

    print("🏀 Team Betting Trends Sync")
    print(f"📅 Season start: {args.season_start}")
    print(f"🧪 Mode: {'DRY RUN' if args.dry_run else 'LIVE'}\n")

    conn = sqlite3.connect(args.db_path)

    try:
        trends = compute_team_trends(conn, season_start=args.season_start)
        count = upsert_team_trends(conn, trends, dry_run=args.dry_run)

        if not args.dry_run:
            print(f"\n✅ Updated {count} teams in team_betting_trends")
            # Spot-check top H/A teams
            rows = conn.execute('''
                SELECT team, home_wins, home_losses, away_wins, away_losses,
                       home_avg_score, away_avg_score, ats_games_tracked
                FROM team_betting_trends
                ORDER BY (home_wins + away_wins) DESC LIMIT 5
            ''').fetchall()
            print("\nTop 5 by total wins:")
            for r in rows:
                print(f"  {r[0]}: H={r[1]}-{r[2]} A={r[3]}-{r[4]} "
                      f"pts_H={r[5]} pts_A={r[6]} (ATS: {r[7]} games)")
        else:
            print(f"\n[DRY RUN] Would update {count} teams")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
