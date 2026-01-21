#!/usr/bin/env python3
"""
backtest_week3_full.py
======================
Week 3 Validation Script

Goal: Backtest full calibration pipeline (Week 3 features) against actual game outcomes.
Metrics: RMSE (Projections), B2B Tax Accuracy.
"""

import sys
import os
import sqlite3
import pandas as pd
import numpy as np
import argparse
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from module_e import LudiCalibrator
from module_c import LudiOracle

DB_PATH = 'ludi.db'

class Backtester:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.conn = sqlite3.connect(DB_PATH)
        self.calibrator = LudiCalibrator()
        self.oracle = LudiOracle(sim_count=2000) # Lower sim count for speed
        
    def fetch_games(self):
        query = f"""
        SELECT date, home_team, away_team 
        FROM games 
        WHERE date BETWEEN '{self.start_date}' AND '{self.end_date}'
        """
        return pd.read_sql_query(query, self.conn)
        
    def fetch_player_logs(self):
        query = f"""
        SELECT 
            pgl.game_date, 
            pgl.player_name, 
            pgl.team_abbreviation, 
            pgl.pts, 
            pgl.reb, 
            pgl.ast, 
            pgl.fga, 
            pgl.fg3a, 
            pgl.fta, 
            pgl.minutes,
            CASE 
                WHEN pgl.team_abbreviation = g.home_team THEN g.away_team 
                ELSE g.home_team 
            END as opponent_team
        FROM player_game_logs pgl
        JOIN games g ON pgl.game_date = g.date 
            AND (pgl.team_abbreviation = g.home_team OR pgl.team_abbreviation = g.away_team)
        WHERE pgl.game_date BETWEEN '{self.start_date}' AND '{self.end_date}'
        """
        return pd.read_sql_query(query, self.conn)
        
    def get_rolling_stats(self, player_name, game_date, days=30):
        # Fetch L30 average for base stats
        query = f"""
        SELECT AVG(pts), AVG(reb), AVG(ast), AVG(fga), AVG(fg3a), AVG(fta), AVG(minutes)
        FROM player_game_logs
        WHERE player_name = ? AND game_date < ? AND game_date >= date(?, '-{days} days')
        """
        cursor = self.conn.cursor()
        cursor.execute(query, (player_name, game_date, game_date))
        row = cursor.fetchone()
        
        if not row or row[0] is None:
            # Fallback to season avg if L30 missing
            return None
            
        # Approx USG: (FGA + 0.44*FTA + TOV) / MIN (simplified)
        # Using fixed 0.20 for backtest speed
        
        return {
            'base_pts': row[0], 'base_reb': row[1], 'base_ast': row[2],
            'base_fga': row[3], 'base_3pm': row[4] * 0.35 if row[4] else 0, # approx makes
            'base_fta': row[5], 'base_min': row[6], 'base_usg': 0.20
        }

    
    def get_schedule_context(self, team, date):
        # Check B2B
        cursor = self.conn.cursor()
        prev_date = (datetime.strptime(date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        
        cursor.execute("SELECT 1 FROM games WHERE (home_team=? OR away_team=?) AND date=?", (team, team, prev_date))
        is_b2b = cursor.fetchone() is not None
        
        # Check Road
        cursor.execute("SELECT away_team FROM games WHERE (home_team=? OR away_team=?) AND date=?", (team, team, date))
        row = cursor.fetchone()
        is_road = (row and row[0] == team)
        
        return {
            'is_back_to_back': is_b2b,
            'is_road': is_road,
            'status': 'ACTIVE' # Assume active if they played
        }

    def run(self):
        print(f"Starting Backtest: {self.start_date} to {self.end_date}")
        logs = self.fetch_player_logs()
        print(f"Loaded {len(logs)} player-games.")
        
        results = []
        
        # Group by game/date for batch processing? No, process row by row for simplicity in validation
        # Optimization: Process only top players (starter minutes > 20) to save time?
        # Let's filter min > 15
        
        logs = logs[logs['minutes'] > 15]
        print(f"Filtered to {len(logs)} rotation player-games (>15 min).")
        
        counter = 0
        for idx, row in logs.iterrows():
            player_name = row['player_name']
            date = row['game_date']
            team = row['team_abbreviation']
            
            # 1. Get Base Stats (Rolling)
            base_stats = self.get_rolling_stats(player_name, date)
            if not base_stats: continue
            
            # 2. Construct Packet
            packet = {
                'name': player_name,
                'team': team,
                'opponent': row['opponent_team'],
                **base_stats
            }
            
            # 3. Get Context
            yak_report = self.get_schedule_context(team, date)
            
            # 4. Calibrate (Module E)
            calibrated = self.calibrator.calibrate_player(packet, yak_report)
            
            # 5. Simulate (Module C)
            # Need to mock 'scenario' structure for Oracle
            scenario = {
                'scenario_name': 'BACKTEST',
                'ref_data': {'pace_impact': 1.0, 'whistle_impact': 1.0}, # Neutral refs for now
                'days_rest': 0 if yak_report['is_back_to_back'] else 1,
                'pace_factor': 1.0,
                'players': [{
                    'PLAYER_NAME': player_name,
                    'TEAM_ABBREVIATION': team,
                    'MIN': base_stats['base_min'], # Use rolling avg minutes
                    'FGA': calibrated.get('proj_fga', base_stats['base_fga']),
                    'FG3A': calibrated.get('proj_3pa', 0),
                    'FTA': calibrated.get('proj_fta', base_stats['base_fta']),
                    'FG_PCT': 0.47, # Mock
                    'FG3_PCT': 0.36, # Mock
                    'FT_PCT': 0.78, # Mock
                    'AST': calibrated.get('proj_ast', 0),
                    'REB': calibrated.get('proj_reb', 0),
                    'TOV': 2.0
                }]
            }
            
            sim_results = self.oracle.run_simulation_batch([scenario])
            
            if sim_results:
                proj = sim_results[0]
                results.append({
                    'player': player_name,
                    'date': date,
                    'is_b2b': yak_report['is_back_to_back'],
                    'proj_pts': proj['PTS'],
                    'actual_pts': row['pts'],
                    'diff': proj['PTS'] - row['pts'],
                    'notes': calibrated.get('notes', '')
                })
                
            counter += 1
            if counter % 100 == 0:
                print(f"Processed {counter}...")
                
        # Analysis
        df_res = pd.DataFrame(results)
        mse = (df_res['diff'] ** 2).mean()
        rmse = np.sqrt(mse)
        
        print("\n=== RESULTS ===")
        print(f"Samples: {len(df_res)}")
        print(f"RMSE (PTS): {rmse:.2f}")
        
        # B2B Analysis
        b2b_df = df_res[df_res['is_b2b'] == True]
        rested_df = df_res[df_res['is_b2b'] == False]
        
        print("\nB2B Accuracy:")
        print(f"  B2B RMSE: {np.sqrt((b2b_df['diff']**2).mean()):.2f} (n={len(b2b_df)})")
        print(f"  Rested RMSE: {np.sqrt((rested_df['diff']**2).mean()):.2f} (n={len(rested_df)})")
        
        # Bias Check (Are we over/under projecting?)
        print(f"  B2B Mean Error: {b2b_df['diff'].mean():.2f} (Pos = Overprojecting)")
        print(f"  Rested Mean Error: {rested_df['diff'].mean():.2f}")
        
        # Save results
        os.makedirs('backtest_results', exist_ok=True)
        df_res.to_csv('backtest_results/week3_full.csv', index=False)
        print("Results saved to backtest_results/week3_full.csv")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', type=str, default='2025-12-20')
    parser.add_argument('--end-date', type=str, default='2026-01-16')
    args = parser.parse_args()
    
    bt = Backtester(args.start_date, args.end_date)
    bt.run()
