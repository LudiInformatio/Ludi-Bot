import pandas as pd
import numpy as np
import config

# ==========================================
# LUDI INFORMATIO | MODULE X: SCENARIO BUILDER
# V3.7 - LIVE SCHEMA COMPATIBLE (UPPERCASE KEYS)
# ==========================================

class ScenarioBuilder:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE X (SCENARIO V3.7) ONLINE")
        print(f"   >>> DYNAMIC ROSTERS | LIVE SCHEMA ACTIVE")
        print(f"{'='*40}")
        
        self.rotation_cache = {}
        self.TANK_KEY = getattr(config, 'TANK01_KEY', '')

    def generate_scenarios(self, processed_slate):
        """
        Input: List of Game Objects from Module B/Sim Engine.
        Output: Enhanced list containing Base AND Contingency scenarios.
        """
        final_scenarios = []
        
        for game in processed_slate:
            # 1. Base Scenario
            base_scenario = game.copy()
            base_scenario['scenario_name'] = "BASE"
            final_scenarios.append(base_scenario)
            
            # 2. Contingency Scenarios (Player OUT)
            for player in game['players']:
                # Threshold: Only simulate if a KEY PLAYER sits
                # (Usage > 18% and Minutes > 24) to avoid noise
                if player.get('base_usg', 0) > 0.18 and player.get('base_min', 0) > 24.0:
                    contingency = self._build_out_scenario(game, player)
                    if contingency:
                        final_scenarios.append(contingency)
                        
        return final_scenarios

    def _build_out_scenario(self, game, starter_out):
        scenario = game.copy()
        scenario['scenario_name'] = f"WITHOUT {starter_out['PLAYER_NAME']}"
        scenario['players'] = [] 
        
        # DYNAMIC: Find the backup from the current roster
        minutes_matrix = self._infer_dynamic_backup(game['players'], starter_out)
        
        vacated_usage = starter_out.get('base_usg', 0)
        vacated_mins = starter_out.get('base_min', 0)
        
        raw_players = []
        
        for p in game['players']:
            new_p = p.copy()
            
            # --- CASE A: The Player Who Is Out ---
            if p['PLAYER_ID'] == starter_out['PLAYER_ID']:
                # KILL LIST: Updated to match LIVE SCHEMA (Uppercase)
                keys_to_zero = [
                    'MIN', 'PTS', 'AST', 'REB', 'FG3M',
                    'STL', 'BLK', 'TOV', 
                    'FGA', 'FG3A', 'FTA',
                    'OREB', 'DREB'
                ]
                for k in keys_to_zero:
                    if k in new_p:
                        new_p[k] = 0.0
            
            # --- CASE B: The Beneficiaries (Dynamic Matrix) ---
            elif p['PLAYER_NAME'] in minutes_matrix:
                absorption_rate = minutes_matrix[p['PLAYER_NAME']]
                added_min = vacated_mins * absorption_rate
                
                old_min = p.get('base_min', 0)
                # Cap minutes reasonable (max 38 or +12 bump)
                new_min = min(old_min + added_min, 38.0, old_min + 12.0)
                
                scale_ratio = new_min / old_min if old_min > 0 else 1.0
                
                new_p['MIN'] = new_min
                
                # Efficiency Tax (10% decay on volume efficiency)
                dampened_ratio = 1.0 + ((scale_ratio - 1.0) * 0.90)
                
                # SCALE LIST: Updated to match LIVE SCHEMA (Uppercase)
                stats_to_scale = [
                    'PTS', 'AST', 'REB', 'FG3M', 
                    'STL', 'BLK', 'TOV',
                    'FGA', 'FG3A', 'FTA',
                    'OREB', 'DREB'
                ]
                for stat in stats_to_scale:
                    if stat in new_p:
                        new_p[stat] = round(new_p[stat] * dampened_ratio, 1)

            # --- CASE C: The Alpha Stars (Usage Vacuum) ---
            elif p.get('TEAM_ABBREVIATION') == starter_out.get('TEAM_ABBREVIATION') and p.get('base_usg', 0) > 0.22:
                # Stars don't play more minutes, but they shoot more
                boost = 1 + (vacated_usage * 0.15)
                scoring_keys = ['PTS', 'AST', 'FGA', 'FTA']
                for k in scoring_keys:
                    if k in new_p:
                        new_p[k] = round(new_p[k] * boost, 1)

            # --- CASE D: Everyone Else ---
            else:
                pass 
                
            raw_players.append(new_p)
            
        final_players = self._apply_vegas_guardrail(raw_players, game.get('odds', {}))
        scenario['players'] = final_players
        
        return scenario

    def _infer_dynamic_backup(self, all_players, starter_out):
        """
        Scans the game roster to find the most likely backup
        based on Minutes and Team alignment.
        """
        team_abbr = starter_out.get('TEAM_ABBREVIATION')
        bench_candidates = []
        
        for p in all_players:
            # Must be same team, different player
            if p.get('TEAM_ABBREVIATION') == team_abbr and p['PLAYER_ID'] != starter_out['PLAYER_ID']:
                # Bench Player Criteria: plays between 10 and 28 minutes
                p_min = p.get('base_min', 0)
                if 10.0 < p_min < 28.0:
                    bench_candidates.append(p)
        
        if not bench_candidates:
            return {}
            
        # Sort candidates by Usage Rate (Best proxy for "Sixth Man")
        bench_candidates.sort(key=lambda x: x.get('base_usg', 0), reverse=True)
        
        # The primary backup gets 60% of minutes, secondary gets 30%
        matrix = {}
        if len(bench_candidates) >= 1:
            matrix[bench_candidates[0]['PLAYER_NAME']] = 0.60
        if len(bench_candidates) >= 2:
            matrix[bench_candidates[1]['PLAYER_NAME']] = 0.30
            
        return matrix

    def _apply_vegas_guardrail(self, players, odds):
        spread = odds.get('spread', 0)
        total = odds.get('total', 0)
        
        # Guardrail: Need valid Vegas data
        if not total or total == 'N/A' or total == 0: 
            return players 
        
        # Ensure numeric types
        try:
            total = float(total)
            spread = float(spread) if spread != 'N/A' else 0
        except:
            return players

        implied_total = (total / 2) - (spread / 2)
        
        # Sum projected points in this new scenario
        raw_sum = sum(p.get('PTS', 0) for p in players)
        
        if raw_sum == 0: return players
        
        correction = implied_total / raw_sum
        
        normalized = []
        for p in players:
            # Apply correction to main stats
            if 'PTS' in p: p['PTS'] = round(p['PTS'] * correction, 2)
            if 'REB' in p: p['REB'] = round(p['REB'] * correction, 2)
            if 'AST' in p: p['AST'] = round(p['AST'] * correction, 2)
            normalized.append(p)
            
        return normalized

if __name__ == "__main__":
    print("Module X (V3.7 - Live Schema) Loaded.")