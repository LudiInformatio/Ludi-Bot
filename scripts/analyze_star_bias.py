#!/usr/bin/env python3
"""
LUDI INFORMATIO | STAR BIAS ANALYZER
Phase 4: Forward Learning Engine

Purpose:
    - Runs daily (post-game)
    - Correlates Star Player performance vs. Specific Referees
    - Updates 'referee_player_bias' table
    - Detects "Star Killers" (Refs who suppress specific stars)
    - Detects "Protectors" (Refs who boost specific stars)

Usage:
    python scripts/analyze_star_bias.py [--date YYYY-MM-DD] [--dry-run]
"""

import sys
import os
import argparse
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH


def load_player_baselines(conn: sqlite3.Connection) -> dict:
    """Pre-compute per-player baseline FTA and PF from qualifying game logs."""
    rows = conn.execute('''
        SELECT player_id, AVG(fta), AVG(pf)
        FROM player_game_logs
        WHERE minutes >= 20
        GROUP BY player_id
    ''').fetchall()
    return {r[0]: {'base_fta': r[1] or 0.0, 'base_pf': r[2] or 0.0} for r in rows}


def get_star_matchups(conn: sqlite3.Connection, target_date: str, baselines: dict) -> List[Dict]:
    """
    Find significant player-referee interactions for a given date.
    Criteria: Player Minutes > 20 (to ensure valid sample).
    """
    c = conn.cursor()

    # Join Games, Logs, and Players
    c.execute('''
        SELECT
            g.game_id, g.referee_crew,
            l.player_id, l.player_name, l.pts, l.pf, l.fta, l.minutes,
            p.base_ppg
        FROM player_game_logs l
        JOIN games g ON l.game_id = g.game_id
        JOIN players p ON l.player_id = p.player_id
        WHERE DATE(g.date) = ?
        AND l.minutes >= 20          -- exclude garbage-time appearances
        AND p.usg_pct >= 0.12        -- exclude low-touch role players (<12% USG)
        AND p.base_ppg IS NOT NULL AND p.base_ppg > 0
        AND g.referee_crew IS NOT NULL
        AND g.referee_crew != ''
    ''', (target_date,))

    matchups = []
    for row in c.fetchall():
        game_id, crew_str, pid, name, pts, pf, fta, mins, base_ppg = row

        # Skip if no base PPG (can't calculate meaningful deviation)
        if not base_ppg or base_ppg <= 0:
            continue

        crew = [r.strip() for r in crew_str.split(',') if r.strip()]
        bl = baselines.get(pid, {})

        matchups.append({
            'game_id': game_id,
            'crew': crew,
            'player_id': pid,
            'player_name': name,
            'stats': {
                'pts': pts,
                'pf': pf,
                'fta': fta or 0,
                'ppg_deviation': pts - base_ppg,
                'fta_deviation': (fta or 0) - bl.get('base_fta', 0.0),
                'pf_deviation':  (pf  or 0) - bl.get('base_pf',  0.0),
            }
        })

    return matchups


def update_bias_metrics(conn: sqlite3.Connection, ref_name: str, player_data: Dict, dry_run: bool = False):
    """
    Update the rolling average bias stats for a Ref-Player pair.
    """
    c = conn.cursor()
    
    # Resolve Ref ID
    c.execute("SELECT referee_id FROM referee_profiles WHERE referee_name = ?", (ref_name,))
    ref_row = c.fetchone()
    
    if not ref_row:
        # If ref unknown, we skip tracking for now (Learning Engine handles new refs separately)
        return
        
    ref_id = ref_row[0]
    pid = player_data['player_id']
    stats = player_data['stats']
    
    # Get existing bias record
    c.execute('''
        SELECT games_officiated, avg_pf_called, avg_fta_awarded,
               points_impact_vs_avg, fta_impact_vs_avg, pf_impact_vs_avg
        FROM referee_player_bias
        WHERE referee_id = ? AND player_id = ?
    ''', (ref_id, pid))

    existing = c.fetchone()

    if existing:
        n, old_pf, old_fta, old_impact, old_fta_dev, old_pf_dev = existing
        new_n = n + 1

        # Moving averages
        new_pf      = ((old_pf * n) + stats['pf']) / new_n
        new_fta     = ((old_fta * n) + stats['fta']) / new_n
        new_impact  = ((old_impact * n) + stats['ppg_deviation']) / new_n
        new_fta_dev = (((old_fta_dev or 0) * n) + stats['fta_deviation']) / new_n
        new_pf_dev  = (((old_pf_dev  or 0) * n) + stats['pf_deviation'])  / new_n
    else:
        new_n       = 1
        new_pf      = stats['pf']
        new_fta     = stats['fta']
        new_impact  = stats['ppg_deviation']
        new_fta_dev = stats['fta_deviation']
        new_pf_dev  = stats['pf_deviation']

    if dry_run:
        if abs(new_impact) > 5.0 and new_n > 0:
            print(f"   🚩 {ref_name} vs {player_data['player_name']}: Impact {new_impact:+.1f} PPG ({new_n} gms)")
        return

    c.execute('''
        INSERT INTO referee_player_bias (
            referee_id, player_id, player_name,
            games_officiated, avg_pf_called, avg_fta_awarded,
            points_impact_vs_avg, fta_impact_vs_avg, pf_impact_vs_avg,
            last_updated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(referee_id, player_id) DO UPDATE SET
            games_officiated     = excluded.games_officiated,
            avg_pf_called        = excluded.avg_pf_called,
            avg_fta_awarded      = excluded.avg_fta_awarded,
            points_impact_vs_avg = excluded.points_impact_vs_avg,
            fta_impact_vs_avg    = excluded.fta_impact_vs_avg,
            pf_impact_vs_avg     = excluded.pf_impact_vs_avg,
            last_updated         = excluded.last_updated
    ''', (
        ref_id, pid, player_data['player_name'],
        new_n, new_pf, new_fta, new_impact, new_fta_dev, new_pf_dev,
        datetime.now().strftime('%Y-%m-%d')
    ))


def run_analysis(target_date: str = None, dry_run: bool = False):
    if not target_date:
        target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
    print("\n" + "=" * 60)
    print("LUDI INFORMATIO | STAR BIAS ANALYZER")
    print(f"Processing Date: {target_date}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)

    try:
        baselines = load_player_baselines(conn)
        matchups = get_star_matchups(conn, target_date, baselines)
        
        if not matchups:
            print(f"   ⚠️  No valid matchups found for {target_date} (Missing logs or crew data?)")
            return
            
        print(f"   📊 Analyzing {len(matchups)} player performances...")
        
        processed_pairs = 0
        
        for m in matchups:
            crew = m['crew']
            # Update bias for each ref in the crew
            for ref in crew:
                update_bias_metrics(conn, ref, m, dry_run)
                processed_pairs += 1
        
        if not dry_run:
            conn.commit()
            print(f"\n   ✅ Updated {processed_pairs} Referee-Player bias records.")
        else:
            print(f"\n   🔍 Dry run complete. Analyzed {processed_pairs} interactions.")
            
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str, help='YYYY-MM-DD')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    
    run_analysis(args.date, args.dry_run)
