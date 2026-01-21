#!/usr/bin/env python3
"""
SYNERGY INTEGRATION BACKTEST VALIDATION (Phase 1 - Day 3)
Compares baseline (WITHOUT Synergy) vs enhanced (WITH Synergy) projections.

Target: Jan 15-20, 2026 (937 player-games)
Metrics: RMSE, hit rate, bias improvements
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import sqlite3
import pandas as pd
import numpy as np
from module_e import LudiCalibrator
from module_c import LudiOracle
from datetime import datetime, timedelta

class SynergyBacktester:
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        self.calibrator = LudiCalibrator()
        self.oracle = LudiOracle(sim_count=2000) # Faster for backtest

    def fetch_test_data(self, start_date='2026-01-15', end_date='2026-01-20'):
        """Fetch actual game results from player_game_logs."""
        conn = sqlite3.connect(self.db_path)
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
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()

        print(f"\n✅ Loaded {len(df)} player-games from {start_date} to {end_date}")
        return df

    def get_rolling_stats(self, player_name, game_date, window=30):
        """Get L30 averages for baseline projection."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get games before target date
        cutoff = (datetime.strptime(game_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT AVG(pts) as avg_pts, AVG(ast) as avg_ast, AVG(reb) as avg_reb,
                   AVG(fga) as avg_fga, AVG(fg3a) as avg_fg3a, AVG(fta) as avg_fta,
                   AVG(CAST(fgm AS FLOAT) / NULLIF(fga, 0)) as fg_pct,
                   AVG(CAST(fg3m AS FLOAT) / NULLIF(fg3a, 0)) as fg3_pct,
                   AVG(CAST(ftm AS FLOAT) / NULLIF(fta, 0)) as ft_pct
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

    def run_projections(self, test_df, use_synergy=True):
        """Run projections for all players with Synergy ON or OFF."""
        results = []
        mode = "ENHANCED (WITH Synergy)" if use_synergy else "BASELINE (WITHOUT Synergy)"

        print(f"\n{'='*70}")
        print(f"RUNNING {mode} PROJECTIONS")
        print(f"{ '='*70}")

        for idx, row in test_df.iterrows():
            player_name = row['player_name']
            game_date = row['game_date']
            opponent = row['opponent_team']

            # Get L30 stats
            player_packet = self.get_rolling_stats(player_name, game_date, window=30)
            if not player_packet:
                continue

            # Build game context
            game_context = {
                'opponent': opponent,
                'spread': 0,  # Default neutral
                'total': 220,  # Default total
                'is_home': True,  # Simplified
                'is_b2b': False, # Simplified
                'status': 'ACTIVE'
            }

            # CRITICAL: Toggle Synergy functions here
            calibrated = self.calibrator.calibrate_player(
                player_packet.copy(),
                game_context,
                use_synergy=use_synergy  # ← THE KEY DIFFERENCE
            )
            
            # Setup scenario for Oracle
            scenario = {
                'scenario_name': 'BACKTEST',
                'pace_factor': 1.0,
                'ref_impact': 1.0,
                'ref_whistle': 1.0,
                'days_rest': 1,
                'players': [{
                    'PLAYER_NAME': player_name,
                    'TEAM_ABBREVIATION': row['team_abbreviation'],
                    'MIN': row['minutes'], # Use actual minutes for apple-to-apples comparison of efficiency
                    'FGA': calibrated.get('proj_fga', player_packet['base_fga']),
                    'FG3A': calibrated.get('proj_3pa', player_packet['base_fg3a']),
                    'FTA': calibrated.get('proj_fta', player_packet['base_fta']),
                    'FG_PCT': calibrated.get('proj_fg_pct', player_packet['base_fg_pct']),
                    'FG3_PCT': player_packet['base_fg3_pct'],
                    'FT_PCT': player_packet['base_ft_pct'],
                    'AST': calibrated.get('proj_ast', player_packet['base_ast']),
                    'REB': calibrated.get('proj_reb', player_packet['base_reb']),
                    'OREB': 1.0, # Dummy
                    'DREB': 3.0, # Dummy
                    'STL': 1.0, # Dummy
                    'BLK': 0.5, # Dummy
                    'TOV': 2.0   # Dummy
                }]
            }

            # Run Monte Carlo simulation
            sim_results = self.oracle.run_simulation_batch([scenario])

            proj = sim_results[0]

            results.append({
                'player_name': player_name,
                'game_date': game_date,
                'opponent': opponent,
                'proj_pts': proj.get('PTS', 0),
                'proj_ast': proj.get('AST', 0),
                'proj_reb': proj.get('REB', 0),
                'actual_pts': row['pts'],
                'actual_ast': row['ast'],
                'actual_reb': row['reb']
            })

            if (idx + 1) % 100 == 0:
                print(f"  Processed {idx + 1}/{len(test_df)} players...")

        print(f"✅ {mode} Complete: {len(results)} projections generated\n")
        return pd.DataFrame(results)

    def calculate_metrics(self, df, stat='pts'):
        """Calculate RMSE, bias, and hit rate for a stat."""
        proj_col = f'proj_{stat}'
        actual_col = f'actual_{stat}'

        # RMSE
        mse = (df[proj_col] - df[actual_col]) ** 2
        rmse = np.sqrt(mse.mean())

        # Bias (positive = overprojecting)
        bias = (df[proj_col] - df[actual_col]).mean()

        # Hit rate (assumes prop line = projection, measures directional accuracy)
        # Simplified: measures if projection was within ±2.0 of actual (PTS) or ±1.0 (AST/REB)
        threshold = 2.0 if stat == 'pts' else 1.0
        within_range = (df[proj_col] - df[actual_col]).abs() <= threshold
        hit_rate = within_range.mean()

        return {
            'rmse': rmse,
            'bias': bias,
            'hit_rate': hit_rate
        }

    def compare_systems(self, baseline_df, enhanced_df):
        """Compare baseline vs enhanced metrics."""
        print(f"\n{'='*70}")
        print("BACKTEST RESULTS: BASELINE vs ENHANCED")
        print(f"{ '='*70}\n")

        stats = ['pts', 'ast', 'reb']
        improvements = []

        for stat in stats:
            baseline_metrics = self.calculate_metrics(baseline_df, stat)
            enhanced_metrics = self.calculate_metrics(enhanced_df, stat)

            rmse_improvement = baseline_metrics['rmse'] - enhanced_metrics['rmse']
            rmse_pct = (rmse_improvement / baseline_metrics['rmse']) * 100

            hit_rate_improvement = enhanced_metrics['hit_rate'] - baseline_metrics['hit_rate']
            hit_rate_pct = hit_rate_improvement * 100

            print(f"{stat.upper()} Metrics:")
            print(f"  Baseline RMSE: {baseline_metrics['rmse']:.2f}")
            print(f"  Enhanced RMSE: {enhanced_metrics['rmse']:.2f}")
            print(f"  Improvement:   {rmse_improvement:+.2f} ({rmse_pct:+.1f}%)")
            print(f"")
            print(f"  Baseline Bias: {baseline_metrics['bias']:+.2f}")
            print(f"  Enhanced Bias: {enhanced_metrics['bias']:+.2f}")
            print(f"")
            print(f"  Baseline Hit Rate: {baseline_metrics['hit_rate']:.1%}")
            print(f"  Enhanced Hit Rate: {enhanced_metrics['hit_rate']:.1%}")
            print(f"  Improvement:       {hit_rate_improvement:+.1%} ({hit_rate_pct:+.1f} pts)")
            print(f"")

            improvements.append({
                'stat': stat.upper(),
                'baseline_rmse': baseline_metrics['rmse'],
                'enhanced_rmse': enhanced_metrics['rmse'],
                'rmse_improvement': rmse_improvement,
                'rmse_improvement_pct': rmse_pct,
                'baseline_hit_rate': baseline_metrics['hit_rate'],
                'enhanced_hit_rate': enhanced_metrics['hit_rate'],
                'hit_rate_improvement': hit_rate_improvement
            })

        # Summary
        print(f"{ '='*70}")
        avg_rmse_improvement = np.mean([i['rmse_improvement_pct'] for i in improvements])
        avg_hit_rate_improvement = np.mean([i['hit_rate_improvement'] for i in improvements])

        print(f"\n✅ OVERALL IMPROVEMENT:")
        print(f"   RMSE: {avg_rmse_improvement:+.1f}% (average across PTS/AST/REB)")
        print(f"   Hit Rate: {avg_hit_rate_improvement:+.1%} (average)")
        print(f"\n{'='*70}\n")

        return pd.DataFrame(improvements)

    def run(self):
        """Main backtest workflow."""
        print("\n🏀 SYNERGY INTEGRATION BACKTEST VALIDATION")
        print("Phase 1 - Day 3 Deliverable")
        print("="*70)

        # 1. Fetch test data
        test_df = self.fetch_test_data()

        # 2. Run baseline projections (WITHOUT Synergy)
        baseline_df = self.run_projections(test_df, use_synergy=False)

        # 3. Run enhanced projections (WITH Synergy)
        enhanced_df = self.run_projections(test_df, use_synergy=True)

        # 4. Compare metrics
        comparison_df = self.compare_systems(baseline_df, enhanced_df)

        # 5. Save results
        baseline_df.to_csv('backtest_results/synergy_baseline.csv', index=False)
        enhanced_df.to_csv('backtest_results/synergy_enhanced.csv', index=False)
        comparison_df.to_csv('backtest_results/synergy_comparison.csv', index=False)

        print("✅ Results saved to backtest_results/")
        print("   - synergy_baseline.csv (WITHOUT Synergy projections)")
        print("   - synergy_enhanced.csv (WITH Synergy projections)")
        print("   - synergy_comparison.csv (Metrics comparison)")

        return comparison_df

if __name__ == "__main__":
    backtester = SynergyBacktester(db_path='ludi.db')
    results = backtester.run()

    print("\n✅ BACKTEST VALIDATION COMPLETE")
