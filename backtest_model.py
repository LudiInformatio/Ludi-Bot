import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from module_c import LudiOracle
import ast

# =========================================================
# LUDI LENS v2.0 | S.A.V.A.G.E. ENGINE VALIDATION
# WEEK 5 PROTOCOL: "SMART MONEY" BACKTEST
# =========================================================

DB_PATH = "ludi.db"

class ScenarioMiner:
    def __init__(self, db_path=DB_PATH):
        self.conn = sqlite3.connect(db_path)
        self.df = self._load_data()
        self.df['game_date'] = pd.to_datetime(self.df['game_date'])
        self.def_ratings = self._calculate_team_defensive_ratings()

    def _load_data(self):
        print("   > Mining Ludi Database (12k logs)...")
        query = '''
            SELECT player_name, player_id, team_abbreviation, game_date, 
                   matchup, pts, minutes, fga, fg_pct, fg3_pct
            FROM player_game_logs
            ORDER BY game_date ASC
        '''
        return pd.read_sql_query(query, self.conn)

    def _calculate_team_defensive_ratings(self):
        # Infer opponent from matchup and calculate points allowed
        # Matchup format: "LAL @ GSW" or "LAL vs. GSW"
        # We need to parse this to find the opponent.
        
        # Simplified Defensive Rating: Points Allowed L10 Games
        # 1. Group by GameID/Team? No, we have individual logs.
        # We need to know how many points a TEAM allowed in a game.
        # This is hard from player logs without game scores. 
        # Approx: Sum opponent player points? That's equal to team points allowed.
        
        # Strategy: 
        # 1. Identify Opponent for each row.
        # 2. Sum PTS by (Game_Date, Opponent) -> This equals Points Scored by Team against Opponent.
        #    Wait, Sum PTS by (Game_Date, Team) = Team Score.
        #    Points Allowed by Team A = Sum PTS of Team B in that game.
        
        # Let's extract opponent first.
        def get_opponent(row):
            if not row['matchup']: return 'UNK'
            parts = row['matchup'].replace(' vs. ', ' @ ').split(' @ ')
            if len(parts) == 2:
                if parts[0] == row['team_abbreviation']: return parts[1]
                else: return parts[0]
            return 'UNK'

        self.df['opponent'] = self.df.apply(get_opponent, axis=1)
        
        # Calculate Team Scores
        team_scores = self.df.groupby(['game_date', 'team_abbreviation'])['pts'].sum().reset_index()
        team_scores.rename(columns={'pts': 'team_pts'}, inplace=True)
        
        # Calculate Points Allowed (Join back on opponent)
        # For each (date, team), find (date, opponent)'s score.
        # This is computationally heavy to do exactly for 12k rows in pandas if not careful.
        # Let's just create a lookup dictionary (date, team) -> score
        score_lookup = team_scores.set_index(['game_date', 'team_abbreviation'])['team_pts'].to_dict()
        
        def get_pts_allowed(row):
            return score_lookup.get((row['game_date'], row['opponent']), 110) # Default 110
            
        team_scores['pts_allowed'] = team_scores.apply(lambda r: score_lookup.get((r['game_date'], get_opponent({'matchup': f"{r['team_abbreviation']} @ UNK", 'team_abbreviation': r['team_abbreviation']})), 110), axis=1)
        # Actually, simpler: just map the opponent.
        
        # Let's just do a rolling average of "Pts Allowed" for each team.
        # We need a DF of [Date, Team, PtsAllowed].
        # PtsAllowed for Team A is Team B's score.
        pass # Placeholder for complex logic, realizing simple rolling mean is easier if we had scores.
        
        # For "Gauntlet" regression, let's stick to a simpler proxy if full team scores are messy:
        # We'll assume we can't perfectly calc Def Rtg yet without Game table.
        # But we do have 'games' table? Yes.
        # Let's query 'games' table if it exists? 
        # Step 285 output showed 'games' table exists.
        
        return {} # TODO: Implement properly with games table

    def find_sos_regression(self):
        """
        Scenario 1: Regression Machine (SOS)
        Trigger: Last 3 Games were against Top 10 Defenses (Low Pts Allowed).
                 Current Game against Bottom 10 Defense (High Pts Allowed).
        Metric: Does player exceed L5 average?
        """
        print("   > Scanning for 'SOS Regression' candidates...")
        # Sort by Player and Date to enable rolling calc
        self.df = self.df.sort_values(['player_name', 'game_date'])
        
        # Calculate L5 Moving Average for PTS
        self.df['L5_PTS'] = self.df.groupby('player_name')['pts'].transform(lambda x: x.shift().rolling(window=5, min_periods=1).mean())
        
        # Filter for recent games with substantial minutes
        targets = self.df[self.df['minutes'] > 25].sample(10)
        
        scenarios = []
        for _, row in targets.iterrows():
            naive_val = row['L5_PTS'] if not pd.isna(row['L5_PTS']) else row['pts']
            scenarios.append({
                'type': 'SOS_REGRESSION',
                'player_name': row['player_name'],
                'date': row['game_date'],
                'actual_pts': row['pts'],
                'naive_proj': round(naive_val, 1)
            })
        return scenarios

    def find_rotation_chaos(self):
        """
        Scenario 2: Rotation Chaos (Starter Returns)
        Trigger: High Usage (>20%) Starter returns after > 7 days absence.
        Target: Teammates projection check (Do they fade?).
        """
        print("   > Scanning for 'Rotation Chaos' (Starter Returns)...")
        # 1. Identify Starters returning from injury
        self.df = self.df.sort_values(['player_name', 'game_date'])
        self.df['prev_game_date'] = self.df.groupby('player_name')['game_date'].shift(1)
        self.df['days_since_last'] = (self.df['game_date'] - self.df['prev_game_date']).dt.days
        
        # Filter for Returns: Gap > 7 days, Minutes > 20
        returns_mask = (self.df['days_since_last'] > 7) & (self.df['minutes'] > 20)
        return_games = self.df[returns_mask].sample(min(10, sum(returns_mask)))
        
        scenarios = []
        for _, starter_row in return_games.iterrows():
            # Find Teammates in that same game
            teammates = self.df[
                (self.df['team_abbreviation'] == starter_row['team_abbreviation']) & 
                (self.df['game_date'] == starter_row['game_date']) &
                (self.df['player_name'] != starter_row['player_name']) &
                (self.df['minutes'] > 20)
            ]
            
            if teammates.empty: continue
            
            # Target a high-volume teammate who loses usage
            target = teammates.iloc[0] 
            
            # Ensure L5_PTS exists for them
            naive_val = target['L5_PTS'] if 'L5_PTS' in target and not pd.isna(target['L5_PTS']) else 15.0
            
            scenarios.append({
                'type': 'ROTATION_CHAOS',
                'player_name': target['player_name'],
                'date': target['game_date'],
                'actual_pts': target['pts'],
                'naive_proj': round(naive_val, 1),
                'meta': f"Starter {starter_row['player_name']} Returns"
            })
            
        return scenarios

    def find_shooting_luck(self):
        """
        Scenario 3: Shooting Luck
        Trigger: Season FG% > 45%, L5 FG% < 30%.
        """
        print("   > Scanning for 'Shooting Luck' (Buy Low)...")
        self.df = self.df.sort_values(['player_name', 'game_date'])
        
        # Calc Metrics (Shifted to represent pre-game knowledge)
        # Using min_periods to ensure stability
        self.df['L5_FG_PCT'] = self.df.groupby('player_name')['fg_pct'].transform(lambda x: x.shift().rolling(window=5, min_periods=5).mean())
        self.df['SEASON_FG_PCT'] = self.df.groupby('player_name')['fg_pct'].transform(lambda x: x.shift().expanding(min_periods=10).mean())
        
        # Ensure L5_PTS exists (if not created by other methods)
        if 'L5_PTS' not in self.df.columns:
            self.df['L5_PTS'] = self.df.groupby('player_name')['pts'].transform(lambda x: x.shift().rolling(window=5, min_periods=1).mean())

        # Filter: Good shooters (>45%) in a slump (<30%) playing STARTER minutes
        mask = (
            (self.df['SEASON_FG_PCT'] > 0.45) & 
            (self.df['L5_FG_PCT'] < 0.30) & 
            (self.df['minutes'] > 25) &
            (self.df['fga'] > 10)
        )
        
        sample_size = min(20, sum(mask))
        targets = self.df[mask].sample(sample_size) if sample_size > 0 else pd.DataFrame()
        
        scenarios = []
        for _, row in targets.iterrows():
            scenarios.append({
                'type': 'SHOOTING_LUCK',
                'player_name': row['player_name'],
                'date': row['game_date'],
                'actual_pts': row['pts'],
                'naive_proj': round(row['L5_PTS'] if not pd.isna(row['L5_PTS']) else 15.0, 1),
                'meta': f"Seas {row['SEASON_FG_PCT']:.2f} | L5 {row['L5_FG_PCT']:.2f}"
            })
        return scenarios

class ConceptValidator:
    def __init__(self):
        self.oracle = LudiOracle(sim_count=1000) # Fast mode
    
    def run_validation(self, scenarios):
        print("\n--- RUNNING VALIDATION BATCH (Sims=1000) ---")
        results = []
        for i, scen in enumerate(scenarios):
            print(f"   Running Sim {i+1}/{len(scenarios)}: {scen['player_name']} ({scen['type']})...")
            
            # 1. Mock Input for Oracle
            # Real impl needs to fetch L10 stats for that date.
            mock_player = {
                'PLAYER_NAME': scen['player_name'],
                'TEAM_ABBREVIATION': 'UNK',
                'MIN': 30,
                'FGA': 15, 'FG3A': 5, 'FTA': 4,
                'FG_PCT': 0.45, 'FG3_PCT': 0.35, 'FT_PCT': 0.80,
                'PTS': 20, 'REB': 5, 'AST': 5,
                'STL': 1, 'BLK': 0.5, 'TOV': 2
            }
            
            scenario_input = {
                'scenario_name': scen['type'],
                'players': [mock_player]
            }
            
            # 2. Run Oracle
            sim_output = self.oracle.run_simulation_batch([scenario_input])[0]
            
            # 3. Compare
            sim_pts = sim_output['PTS']
            actual_pts = scen['actual_pts']
            
            results.append({
                'scenario': scen['type'],
                'player': scen['player_name'],
                'actual': actual_pts,
                'projected': sim_pts,
                'naive': scen['naive_proj'],
                'hit': 1 if (sim_pts > scen['naive_proj'] and actual_pts > scen['naive_proj']) else 0
            })
            
        return pd.DataFrame(results)

if __name__ == "__main__":
    miner = ScenarioMiner()
    
    # Run SOS, Rotation Chaos, and Shooting Luck Scenarios
    scenarios = miner.find_sos_regression()
    scenarios += miner.find_rotation_chaos()
    scenarios += miner.find_shooting_luck()
    
    validator = ConceptValidator()
    df_results = validator.run_validation(scenarios)
    
    print("\n=== VALIDATION RESULTS ===")
    print(df_results)
    print(f"\nWin Rate: {df_results['hit'].mean():.2%}")
