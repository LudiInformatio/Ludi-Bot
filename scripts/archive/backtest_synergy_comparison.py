#!/usr/bin/env python3
"""
SYNERGY INTEGRATION BACKTEST VALIDATION (Extended Production Grade)
Compares baseline (WITHOUT Synergy) vs enhanced (WITH Synergy) projections.

Features:
- Batch processing (saves memory, prevents data loss)
- CSV checkpointing (saves progress to disk immediately)
- 2000 Monte Carlo Simulations per player-game (Production Standard)
"""

import sys
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import pandas as pd
import numpy as np
import os
import time
from module_e import LudiCalibrator
from module_c import LudiOracle
from datetime import datetime, timedelta

class SynergyBacktester:
    def __init__(self, db_path='ludi.db', sim_count=2000):
        self.db_path = db_path
        self.calibrator = LudiCalibrator()
        self.oracle = LudiOracle(sim_count=sim_count)
        self.sim_count = sim_count

    def fetch_test_data(self, start_date, end_date):
        """Fetch actual game results from player_game_logs."""
        conn = sqlite3.connect(self.db_path)
        # Join with games table to ensure we have opponent info
        query = """
        SELECT
            pgl.player_name, 
            pgl.game_date, 
            pgl.team_abbreviation,
            CASE 
                WHEN pgl.team_abbreviation = g.home_team THEN g.away_team 
                ELSE g.home_team 
            END as opponent_team,
            pgl.pts, pgl.ast, pgl.reb, pgl.fga, pgl.fg3a, pgl.fta, pgl.minutes
        FROM player_game_logs pgl
        JOIN games g ON pgl.game_date = g.date 
            AND (pgl.team_abbreviation = g.home_team OR pgl.team_abbreviation = g.away_team)
        WHERE pgl.game_date BETWEEN ? AND ?
          AND pgl.minutes >= 15
        ORDER BY pgl.game_date, pgl.player_name
        """
        try:
            df = pd.read_sql_query(query, conn, params=(start_date, end_date))
            print(f"\n✅ Loaded {len(df)} player-games from {start_date} to {end_date}")
            return df
        finally:
            conn.close()

    def get_rolling_stats(self, player_name, game_date, window=30):
        """Get L30 averages for baseline projection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff = (datetime.strptime(game_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT AVG(pts), AVG(ast), AVG(reb),
                   AVG(fga), AVG(fg3a), AVG(fta),
                   AVG(CAST(fgm AS FLOAT) / NULLIF(fga, 0)),
                   AVG(CAST(fg3m AS FLOAT) / NULLIF(fg3a, 0)),
                   AVG(CAST(ftm AS FLOAT) / NULLIF(fta, 0))
            FROM player_game_logs
            WHERE player_name = ? AND game_date < ?
            ORDER BY game_date DESC
            LIMIT ?
        """, (player_name, cutoff, window))

        row = cursor.fetchone()
        conn.close()

        if not row or row[0] is None:
            return None

        return {
            'name': player_name,
            'base_pts': row[0] or 0,
            'base_ast': row[1] or 0,
            'base_reb': row[2] or 0,
            'base_fga': row[3] or 0,
            'base_fg3a': row[4] or 0,
            'base_fta': row[5] or 0,
            'base_fg_pct': row[6] or 0.45,
            'base_fg3_pct': row[7] or 0.35,
            'base_ft_pct': row[8] or 0.75
        }

    def process_batch(self, batch_df, use_synergy=True):
        """Process a batch of player games."""
        results = []
        
        for _, row in batch_df.iterrows():
            player_name = row['player_name']
            game_date = row['game_date']
            opponent = row['opponent_team']

            player_packet = self.get_rolling_stats(player_name, game_date, window=30)
            if not player_packet:
                continue

            game_context = {
                'opponent': opponent,
                'spread': 0, 'total': 220, 
                'is_home': True, 'is_b2b': False, 'status': 'ACTIVE'
            }

            calibrated = self.calibrator.calibrate_player(
                player_packet.copy(),
                game_context,
                use_synergy=use_synergy
            )
            
            scenario = {
                'scenario_name': 'BACKTEST',
                'pace_factor': 1.0, 'ref_impact': 1.0, 'ref_whistle': 1.0, 'days_rest': 1,
                'players': [{
                    'PLAYER_NAME': player_name,
                    'TEAM_ABBREVIATION': row['team_abbreviation'],
                    'MIN': row['minutes'],
                    'FGA': calibrated.get('proj_fga', player_packet['base_fga']),
                    'FG3A': calibrated.get('proj_3pa', player_packet['base_fg3a']),
                    'FTA': calibrated.get('proj_fta', player_packet['base_fta']),
                    'FG_PCT': calibrated.get('proj_fg_pct', player_packet['base_fg_pct']),
                    'FG3_PCT': player_packet['base_fg3_pct'],
                    'FT_PCT': player_packet['base_ft_pct'],
                    'AST': calibrated.get('proj_ast', player_packet['base_ast']),
                    'REB': calibrated.get('proj_reb', player_packet['base_reb']),
                    'OREB': 1.0, 'DREB': 3.0, 'STL': 1.0, 'BLK': 0.5, 'TOV': 2.0
                }]
            }

            sim_results = self.oracle.run_simulation_batch([scenario])
            proj = sim_results[0]

            results.append({
                'player_name': player_name,
                'game_date': game_date,
                'opponent': opponent,
                'system': 'Enhanced' if use_synergy else 'Baseline',
                'proj_pts': proj.get('PTS', 0),
                'proj_ast': proj.get('AST', 0),
                'proj_reb': proj.get('REB', 0),
                'actual_pts': row['pts'],
                'actual_ast': row['ast'],
                'actual_reb': row['reb'],
                'notes': calibrated.get('notes', '')
            })
            
        return pd.DataFrame(results)

    def run(self, start_date, end_date, output_dir='backtest_results'):
        """Main workflow with batching."""
        os.makedirs(output_dir, exist_ok=True)
        test_df = self.fetch_test_data(start_date, end_date)
        
        # Output Files
        baseline_file = os.path.join(output_dir, f'synergy_baseline_60d.csv')
        enhanced_file = os.path.join(output_dir, f'synergy_enhanced_60d.csv')
        
        # Clear old files if exist
        if os.path.exists(baseline_file): os.remove(baseline_file)
        if os.path.exists(enhanced_file): os.remove(enhanced_file)

        # Process in batches of 5 to save memory and allow checkpointing
        BATCH_SIZE = 5
        total_batches = (len(test_df) // BATCH_SIZE) + 1
        
        print(f"\nProcessing {len(test_df)} records in {total_batches} batches...", flush=True)

        for i in range(0, len(test_df), BATCH_SIZE):
            batch = test_df.iloc[i:i+BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            print(f"  Batch {batch_num}/{total_batches} ({len(batch)} records)...", flush=True)
            
            # Baseline (No Synergy)
            res_base = self.process_batch(batch, use_synergy=False)
            res_base.to_csv(baseline_file, mode='a', header=not os.path.exists(baseline_file), index=False)
            
            # Enhanced (With Synergy)
            res_enh = self.process_batch(batch, use_synergy=True)
            res_enh.to_csv(enhanced_file, mode='a', header=not os.path.exists(enhanced_file), index=False)

        duration = time.time() - start_time
        print(f"\n✅ Processing Complete in {duration/60:.1f} minutes.")
        print("📊 Calculating Metrics...")
        self.compare_results(baseline_file, enhanced_file)

    def compare_results(self, baseline_path, enhanced_path):
        """Compare full result sets."""
        df_base = pd.read_csv(baseline_path)
        df_enh = pd.read_csv(enhanced_path)
        
        print(f"\n{'='*70}")
        print(f"60-DAY BACKTEST RESULTS (n={len(df_base)})")
        print(f"{ '='*70}\n")
        
        for stat in ['pts', 'ast', 'reb']:
            self._print_stat_metrics(df_base, df_enh, stat)

    def _print_stat_metrics(self, df_base, df_enh, stat):
        p_col = f'proj_{stat}'
        a_col = f'actual_{stat}'
        
        rmse_b = np.sqrt(((df_base[p_col] - df_base[a_col])**2).mean())
        rmse_e = np.sqrt(((df_enh[p_col] - df_enh[a_col])**2).mean())
        
        # Hit rate (within 2.0 for pts, 1.0 for others)
        thresh = 2.0 if stat == 'pts' else 1.0
        hit_b = ((df_base[p_col] - df_base[a_col]).abs() <= thresh).mean()
        hit_e = ((df_enh[p_col] - df_enh[a_col]).abs() <= thresh).mean()
        
        print(f"{stat.upper()} Metrics:")
        print(f"  RMSE: {rmse_b:.2f} -> {rmse_e:.2f} ({(rmse_b - rmse_e):+.3f})")
        print(f"  Hit%: {hit_b:.1%} -> {hit_e:.1%} ({(hit_e - hit_b)*100:+.1f} pts)")
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', type=str, default='2025-11-20')
    parser.add_argument('--end', type=str, default='2026-01-20')
    parser.add_argument('--sims', type=int, default=2000)
    args = parser.parse_args()
    
    bt = SynergyBacktester(sim_count=args.sims)
    bt.run(args.start, args.end)