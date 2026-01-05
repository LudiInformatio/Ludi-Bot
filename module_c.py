import numpy as np
import pandas as pd
import pickle
import os
import config

# =========================================================
# LUDI INFORMATIO | MODULE C: THE ORACLE 
# V3.1 - LIVE PRODUCTION STATE (2025-26)
# =========================================================

class LudiRLAgent:
    def __init__(self, brain_file="ludi_brain.pkl"):
        self.brain_file = brain_file
        self.q_table = self._load_brain()

    def _load_brain(self):
        if os.path.exists(self.brain_file):
            try:
                with open(self.brain_file, 'rb') as f:
                    return pickle.load(f)
            except: return {}
        return {}

    def get_confidence_adjustment(self, state):
        q_val = self.q_table.get(state, 0.0)
        return max(0.85, min(1.15, 1.0 + (q_val * 0.1)))

class LudiOracle:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE C (ORACLE V3.1) LIVE")
        print(f"{'='*40}")
        
        self.brain = LudiRLAgent()
        self.STAT_MAP = {
            'points': 'PTS', 'rebounds': 'REB', 'assists': 'AST',
            'threes': 'FG3M', 'blocks': 'BLK', 'steals': 'STL',
            'turnovers': 'TOV', 'fga': 'FGA', 'fta': 'FTA',
            'offensive_rebounds': 'OREB', 'defensive_rebounds': 'DREB'
        }

    def run_simulation_batch(self, scenarios_list):
        simulated_results = []
        
        for scenario in scenarios_list:
            scen_name = scenario.get('scenario_name', 'BASE')
            
            # --- UPSTREAM DATA INGESTION ---
            ref_factor = scenario.get('ref_impact', 1.0)
            whistle_factor = scenario.get('ref_whistle', 1.0) 
            days_rest = scenario.get('days_rest', 1)
            fatigue_tax = self._calculate_fatigue_tax(days_rest)
            
            macro_mods = {
                "pace": scenario.get('pace_factor', 1.0) * ref_factor * fatigue_tax,
                "def_rtg": scenario.get('def_factor', 1.0),
                "whistle": whistle_factor,
                "fatigue": fatigue_tax,
                "team_min": 240
            }
            
            team_totals = self._sum_team_projections(scenario['players'])
            
            for player in scenario['players']:
                # STATUS & MINUTE GUARDRAIL
                if player.get('injury', 'Active') in ['Out', 'Doubtful'] or player.get('MIN', 0) == 0:
                    continue

                # VOLUME SIMULATION (ATTEMPTS)
                vol_profile = self._simulate_volume(player, macro_mods)
                
                # OUTCOME SIMULATION (ACCOUNTING)
                sim_profile = self._simulate_outcomes(player, vol_profile, macro_mods)
                
                # ADVANCED METRICS
                sim_profile['USG_PCT'] = self._calculate_usage(sim_profile, player, team_totals, macro_mods)
                sim_profile['FANTASY_PTS'] = self._calculate_fantasy_score(sim_profile)
                
                # METADATA BINDING
                sim_profile.update({
                    "PLAYER_NAME": player.get('PLAYER_NAME'),
                    "TEAM": player.get('TEAM_ABBREVIATION'),
                    "SCENARIO": scen_name,
                    "PACE_MOD": round(macro_mods['pace'], 3),
                    "REST": f"{days_rest}D",
                    "MIN": round(player.get('MIN', 0), 1)
                })
                
                simulated_results.append(sim_profile)
                    
        return simulated_results

    def _calculate_fatigue_tax(self, days_rest):
        if days_rest == 0: return 0.965 
        if days_rest >= 4: return 0.985 
        return 1.0

    def _simulate_volume(self, player, mods):
        vol = {}
        for stat in ['FGA', 'FG3A', 'FTA']:
            base = player.get(stat, 0.0)
            stat_mod = mods['pace']
            if stat == 'FTA': stat_mod *= mods['whistle']
            
            adj_base = base * stat_mod
            res = np.random.normal(adj_base, adj_base * 0.12, 25000)
            vol[stat] = round(np.mean(np.maximum(res, 0)), 1)
        return vol

    def _simulate_outcomes(self, player, vol, mods):
        out = vol.copy()
        
        # EFFICIENCY TAXES
        fg_pct = player.get('FG_PCT', 0.45) * mods['def_rtg'] * mods['fatigue']
        fg3_pct = player.get('FG3_PCT', 0.35) * mods['fatigue']
        ft_pct = player.get('FT_PCT', 0.75)
        
        out['FGM'] = round(out['FGA'] * fg_pct, 1)
        out['FG3M'] = round(out['FG3A'] * fg3_pct, 1)
        out['FTM'] = round(out['FTA'] * ft_pct, 1)
        
        # SCORING
        out['PTS'] = round(((out['FGM'] - out['FG3M']) * 2) + (out['FG3M'] * 3) + out['FTM'], 1)
        
        # POSSESSION-BASED ACCOUNTING
        for stat in ['AST', 'REB', 'OREB', 'DREB', 'STL', 'BLK', 'TOV']:
            base = player.get(stat, 0.0) * mods['pace']
            res = np.random.normal(base, base * 0.28, 25000)
            out[stat] = round(np.mean(np.maximum(res, 0)), 1)
            
        return out

    def _calculate_usage(self, sim, player, team, mods):
        try:
            p_pos = sim['FGA'] + (0.44 * sim['FTA']) + sim['TOV']
            t_pos = team['FGA'] + (0.44 * team['FTA']) + team['TOV']
            return round(100 * (p_pos * (mods['team_min'] / 5)) / (player['MIN'] * t_pos), 1)
        except: return 0.0

    def _calculate_fantasy_score(self, sim):
        return round((sim['PTS'] * 1) + (sim['FG3M'] * 0.5) + (sim['REB'] * 1.25) + 
                     (sim['AST'] * 1.5) + (sim['STL'] * 2) + (sim['BLK'] * 2) - (sim['TOV'] * 0.5), 2)

    def _sum_team_projections(self, players):
        return {
            "FGA": sum(p.get('FGA', 0) for p in players),
            "FTA": sum(p.get('FTA', 0) for p in players),
            "TOV": sum(p.get('TOV', 0) for p in players)
        }

if __name__ == "__main__":
    oracle = LudiOracle()