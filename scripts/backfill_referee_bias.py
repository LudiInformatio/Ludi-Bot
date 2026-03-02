#!/usr/bin/env python3
"""
Historical backfill for referee_player_bias table.

Iterates all game dates with referee crew data and runs the same bias
analysis that analyze_star_bias.py does daily. Uses ON CONFLICT upsert,
so it's safe to re-run — running averages are rebuilt from scratch each time.

Usage:
    python scripts/backfill_referee_bias.py [--dry-run]
"""

import sys
import os
import argparse
import sqlite3
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH

# League avg fouls per referee: ~37.5 total game fouls / 3 crew = 12.5
LEAGUE_AVG_FOULS = 12.5


def main():
    parser = argparse.ArgumentParser(description="Backfill referee_player_bias from historical data")
    parser.add_argument('--dry-run', action='store_true', help='Print stats without writing')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)

    # Get all dates with referee crew data
    dates = [r[0] for r in conn.execute(
        "SELECT DISTINCT date FROM games "
        "WHERE referee_crew IS NOT NULL AND referee_crew != '' "
        "ORDER BY date"
    ).fetchall()]

    print(f"=== Referee Bias Backfill ===")
    print(f"Dates with crew data: {len(dates)}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()

    if not args.dry_run:
        # Wipe existing data so running averages are rebuilt cleanly
        conn.execute("DELETE FROM referee_player_bias")
        conn.commit()
        print("Cleared existing bias data (will rebuild from all dates)")

    # Pre-compute per-player baseline FTA and PF (same minutes filter as analysis)
    print("Pre-loading player baselines (FTA, PF)...")
    player_baselines = {}
    for row in conn.execute('''
        SELECT player_id, AVG(fta), AVG(pf)
        FROM player_game_logs
        WHERE minutes >= 20
        GROUP BY player_id
    ''').fetchall():
        player_baselines[row[0]] = {'base_fta': row[1] or 0.0, 'base_pf': row[2] or 0.0}
    print(f"Baselines loaded for {len(player_baselines)} players")

    # Build referee_name → referee_id lookup
    ref_lookup = {}
    for row in conn.execute("SELECT referee_id, referee_name FROM referee_profiles").fetchall():
        ref_lookup[row[1]] = row[0]

    total_pairs = 0
    total_dates_with_data = 0

    for i, target_date in enumerate(dates):
        # Query player performances for this date (same logic as analyze_star_bias)
        rows = conn.execute('''
            SELECT g.referee_crew, l.player_id, l.player_name, l.pts, l.pf, l.fta,
                   p.base_ppg
            FROM player_game_logs l
            JOIN games g ON l.game_id = g.game_id
            JOIN players p ON l.player_id = p.player_id
            WHERE DATE(g.date) = ?
            AND l.minutes >= 20          -- exclude garbage-time appearances
            AND p.usg_pct >= 0.12        -- exclude low-touch role players (<12% USG)
            AND g.referee_crew IS NOT NULL
            AND g.referee_crew != ''
            AND p.base_ppg IS NOT NULL AND p.base_ppg > 0
        ''', (target_date,)).fetchall()

        if not rows:
            continue

        total_dates_with_data += 1
        date_pairs = 0

        for crew_str, pid, pname, pts, pf, fta, base_ppg in rows:
            crew = [r.strip() for r in crew_str.split(',') if r.strip()]
            ppg_dev = pts - base_ppg
            baseline = player_baselines.get(pid, {})
            fta_dev = (fta or 0) - baseline.get('base_fta', 0.0)
            pf_dev  = (pf  or 0) - baseline.get('base_pf',  0.0)

            for ref_name in crew:
                ref_id = ref_lookup.get(ref_name)
                if not ref_id:
                    continue

                if args.dry_run:
                    date_pairs += 1
                    continue

                # Upsert with running average
                existing = conn.execute(
                    "SELECT games_officiated, avg_pf_called, avg_fta_awarded, "
                    "points_impact_vs_avg, fta_impact_vs_avg, pf_impact_vs_avg "
                    "FROM referee_player_bias WHERE referee_id = ? AND player_id = ?",
                    (ref_id, pid)
                ).fetchone()

                if existing:
                    n, old_pf, old_fta, old_impact, old_fta_dev, old_pf_dev = existing
                    new_n      = n + 1
                    new_pf     = ((old_pf * n) + (pf or 0)) / new_n
                    new_fta    = ((old_fta * n) + (fta or 0)) / new_n
                    new_impact = ((old_impact * n) + ppg_dev) / new_n
                    new_fta_dev = (((old_fta_dev or 0) * n) + fta_dev) / new_n
                    new_pf_dev  = (((old_pf_dev  or 0) * n) + pf_dev)  / new_n
                else:
                    new_n       = 1
                    new_pf      = pf or 0
                    new_fta     = fta or 0
                    new_impact  = ppg_dev
                    new_fta_dev = fta_dev
                    new_pf_dev  = pf_dev

                conn.execute('''
                    INSERT INTO referee_player_bias
                        (referee_id, player_id, player_name,
                         games_officiated, avg_pf_called, avg_fta_awarded,
                         points_impact_vs_avg, fta_impact_vs_avg, pf_impact_vs_avg,
                         last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(referee_id, player_id) DO UPDATE SET
                        games_officiated    = excluded.games_officiated,
                        avg_pf_called       = excluded.avg_pf_called,
                        avg_fta_awarded     = excluded.avg_fta_awarded,
                        points_impact_vs_avg = excluded.points_impact_vs_avg,
                        fta_impact_vs_avg   = excluded.fta_impact_vs_avg,
                        pf_impact_vs_avg    = excluded.pf_impact_vs_avg,
                        last_updated        = excluded.last_updated
                ''', (ref_id, pid, pname, new_n,
                      round(new_pf, 2), round(new_fta, 2), round(new_impact, 2),
                      round(new_fta_dev, 2), round(new_pf_dev, 2),
                      target_date))

                date_pairs += 1

        total_pairs += date_pairs

        # Commit every 10 dates to avoid huge transactions
        if not args.dry_run and (i + 1) % 10 == 0:
            conn.commit()

        # Progress every 20 dates
        if (i + 1) % 20 == 0 or (i + 1) == len(dates):
            print(f"  [{i+1}/{len(dates)}] {target_date} — {date_pairs} pairs this date, {total_pairs} total")

    if not args.dry_run:
        conn.commit()

    # Summary
    stats = conn.execute(
        "SELECT COUNT(*), MAX(games_officiated) FROM referee_player_bias"
    ).fetchone()
    print(f"\n=== Complete ===")
    print(f"Dates processed: {total_dates_with_data}/{len(dates)}")
    print(f"Total ref-player pairs updated: {total_pairs}")
    print(f"Rows in referee_player_bias: {stats[0]}")
    print(f"Max games_officiated: {stats[1]}")

    conn.close()


if __name__ == "__main__":
    main()
