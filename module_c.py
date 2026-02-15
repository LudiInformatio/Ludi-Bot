import numpy as np
import pickle
import os
import sqlite3

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
    def __init__(self, sim_count=5000):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE C (ORACLE V3.2) LIVE")
        print(f"   >>> Hybrid Engine: Normal (High-Vol) + Poisson (Rare)")
        print(f"   >>> Sim Count: {sim_count}")
        print(f"{'='*40}")
        
        self.sim_count = sim_count
        self.brain = LudiRLAgent()
        self.db_path = 'ludi.db'
        self.STAT_MAP = {
            'points': 'PTS', 'rebounds': 'REB', 'assists': 'AST',
            'threes': 'FG3M', 'blocks': 'BLK', 'steals': 'STL',
            'turnovers': 'TOV', 'fga': 'FGA', 'fta': 'FTA',
            'offensive_rebounds': 'OREB', 'defensive_rebounds': 'DREB'
        }

        # Dormant data activation: load efficiency + drives context
        self.shot_quality_data = {}   # {player_id: shot_quality_avg}
        self.rolling_ts_data = {}     # {player_name: avg_ts_pct}
        self.drives_data = {}         # {player_name: {pass_pct, drives_pts}}
        self._load_shot_quality_data()
        self._load_rolling_ts_data()
        self._load_drives_data()

    def _load_shot_quality_data(self):
        """Load shot quality averages from PBP Stats (player_shot_quality table)."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT player_id, shot_quality_avg FROM player_shot_quality WHERE season = '2025-26'")
            rows = c.fetchall()
            conn.close()
            self.shot_quality_data = {row[0]: row[1] for row in rows if row[1] is not None}
            print(f"   >>> Shot quality data loaded: {len(self.shot_quality_data)} players")
        except Exception as e:
            print(f"   >>> Shot quality data unavailable: {e}")
            self.shot_quality_data = {}

    def _load_rolling_ts_data(self):
        """Load rolling TS% from player_game_advanced (last 30 days, min 5 games)."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # TS% stored as 0-100 scale in DB (league avg ~60.4)
            c.execute("""
                SELECT player_name, AVG(ts_pct) as avg_ts
                FROM player_game_advanced
                WHERE game_date >= date('now', '-30 days') AND ts_pct IS NOT NULL AND ts_pct > 0
                GROUP BY player_name
                HAVING COUNT(*) >= 5
            """)
            rows = c.fetchall()
            conn.close()
            self.rolling_ts_data = {row[0]: row[1] for row in rows}
            print(f"   >>> Rolling TS% data loaded: {len(self.rolling_ts_data)} players")
        except Exception as e:
            print(f"   >>> Rolling TS% data unavailable: {e}")
            self.rolling_ts_data = {}

    def _load_drives_data(self):
        """Load drives context from player_game_tracking (last 30 days, min 5 games)."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                SELECT player_name, AVG(drives_pass_pct) as avg_pass_pct, AVG(drives_pts) as avg_drives_pts
                FROM player_game_tracking
                WHERE game_date >= date('now', '-30 days')
                  AND drives_pass_pct IS NOT NULL AND drives_pts IS NOT NULL
                GROUP BY player_name
                HAVING COUNT(*) >= 5
            """)
            rows = c.fetchall()
            conn.close()
            self.drives_data = {row[0]: {'pass_pct': row[1], 'drives_pts': row[2]} for row in rows}
            print(f"   >>> Drives context data loaded: {len(self.drives_data)} players")
        except Exception as e:
            print(f"   >>> Drives context data unavailable: {e}")
            self.drives_data = {}

    def _calculate_efficiency_modifier(self, player):
        """
        Blend shot quality + rolling TS% into a single FG% efficiency modifier.
        - Shot quality signal: does this player take good shots? (PBP Stats)
        - Rolling TS% signal: is this player shooting well recently? (game-level advanced)
        Returns modifier centered at 1.0, capped at ±8%.
        """
        player_id = str(player.get('player_id', ''))
        player_name = player.get('PLAYER_NAME', '')

        # Shot quality modifier: league avg ~0.55 eFG for shot quality metric
        sq_mod = 1.0
        sq = self.shot_quality_data.get(player_id)
        if sq is not None:
            # Ratio vs league avg, capped at ±5%
            sq_mod = max(0.95, min(1.05, sq / 0.55))

        # Rolling TS% modifier: league avg ~60.4 on 0-100 scale
        ts_mod = 1.0
        ts = self.rolling_ts_data.get(player_name)
        if ts is not None:
            ts_mod = max(0.95, min(1.05, ts / 60.4))

        # Blend 50/50 when both available, use whichever is available otherwise
        if sq is not None and ts is not None:
            combined = (sq_mod * 0.5) + (ts_mod * 0.5)
        elif sq is not None:
            combined = sq_mod
        elif ts is not None:
            combined = ts_mod
        else:
            combined = 1.0

        # Final cap at ±8% to prevent overcalibration
        return max(0.92, min(1.08, combined))

    def run_simulation_batch(self, scenarios_list):
        simulated_results = []
        
        for scenario in scenarios_list:
            scen_name = scenario.get('scenario_name', 'BASE')
            
            # --- UPSTREAM DATA INGESTION ---
            # V3.0: Unpack ref_data dict (pace_impact, whistle_impact, crew, confidence)
            ref_data = scenario.get('ref_data', {})
            ref_pace = ref_data.get('pace_impact', 1.0) if isinstance(ref_data, dict) else scenario.get('ref_impact', 1.0)
            ref_whistle = ref_data.get('whistle_impact', 1.0) if isinstance(ref_data, dict) else scenario.get('ref_whistle', 1.0)
            
            days_rest = scenario.get('days_rest', 1)
            fatigue_tax = self._calculate_fatigue_tax(days_rest)
            
            macro_mods = {
                "pace": scenario.get('pace_factor', 1.0) * ref_pace * fatigue_tax,
                "def_rtg": scenario.get('def_factor', 1.0),
                "whistle": ref_whistle,  # Applied to FTA in _simulate_volume
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
        """Returns FULL distribution arrays, not just means."""
        vol = {}
        for stat in ['FGA', 'FG3A', 'FTA']:
            base = player.get(stat, 0.0)
            stat_mod = mods['pace']
            if stat == 'FTA': stat_mod *= mods['whistle']
            
            adj_base = base * stat_mod
            # Normal Dist for Volume - KEEP FULL DISTRIBUTION
            # Increased variance to 0.40 for conservative/realistic NBA volatility
            vol[stat] = np.maximum(np.random.normal(adj_base, adj_base * 0.40, self.sim_count), 0)
        return vol

    def _simulate_outcomes(self, player, vol_dist, mods):
        """Simulates outcomes and returns both mean AND full distributions."""
        out = {}
        distributions = {}  # NEW: Store full distributions for hit rate calculation
        
        # EFFICIENCY TAXES
        fg_pct = player.get('FG_PCT', 0.45) * mods['def_rtg'] * mods['fatigue']
        fg3_pct = player.get('FG3_PCT', 0.35) * mods['fatigue']
        ft_pct = player.get('FT_PCT', 0.75)

        # DORMANT DATA: Shot quality + rolling TS% efficiency modifier
        # Blends two signals: shot selection quality (PBP Stats) and recent shooting efficiency (TS%)
        efficiency_mod = self._calculate_efficiency_modifier(player)
        fg_pct *= efficiency_mod
        fg3_pct *= efficiency_mod
        
        # Field goals - use distribution
        fgm_dist = vol_dist['FGA'] * fg_pct
        fg3m_dist = vol_dist['FG3A'] * fg3_pct
        ftm_dist = vol_dist['FTA'] * ft_pct
        
        # Store distributions for hit rate calculation
        distributions['FGM'] = fgm_dist
        distributions['FG3M'] = fg3m_dist
        distributions['FTM'] = ftm_dist
        
        # SCORING - full distribution (PTS assigned after drives boost below)
        pts_dist = ((fgm_dist - fg3m_dist) * 2) + (fg3m_dist * 3) + ftm_dist

        # Store volume means
        out['FGA'] = round(np.mean(vol_dist['FGA']), 1)
        out['FG3A'] = round(np.mean(vol_dist['FG3A']), 1)
        out['FTA'] = round(np.mean(vol_dist['FTA']), 1)
        out['FGM'] = round(np.mean(fgm_dist), 1)
        out['FG3M'] = round(np.mean(fg3m_dist), 1)
        out['FTM'] = round(np.mean(ftm_dist), 1)
        
        # DORMANT DATA: Drives context boost for PTS (rim pressure from drives)
        player_name = player.get('PLAYER_NAME', '')
        drives = self.drives_data.get(player_name, {})
        drives_pts_boost = 1.0
        drives_ast_boost = 1.0
        if drives:
            # High drives_pass_pct (>40%) = playmaker who creates for others -> AST boost
            if drives.get('pass_pct', 0) > 40:
                drives_ast_boost = 1.05 + min((drives['pass_pct'] - 40) / 200, 0.05)  # +5-10% AST
            # High drives_pts (>6 per game) = rim pressure scorer -> PTS boost
            if drives.get('drives_pts', 0) > 6:
                drives_pts_boost = 1.03 + min((drives['drives_pts'] - 6) / 100, 0.02)  # +3-5% PTS

        # Apply drives PTS boost to scoring distribution
        if drives_pts_boost > 1.0:
            pts_dist = pts_dist * drives_pts_boost

        distributions['PTS'] = pts_dist
        out['PTS'] = round(np.mean(pts_dist), 1)

        # POSSESSION-BASED STATS - keep distributions
        for stat in ['AST', 'REB', 'OREB', 'DREB', 'STL', 'BLK', 'TOV']:
            base = player.get(stat, 0.0) * mods['pace']

            # DORMANT DATA: Apply drives AST boost
            if stat == 'AST' and drives_ast_boost > 1.0:
                base *= drives_ast_boost

            if stat in ['STL', 'BLK']:
                # POISSON for Rare Events
                res = np.random.poisson(max(base, 0.1), self.sim_count)
            else:
                # NORMAL for High-Volume stats
                # Variance 0.40 matches volume variance (conservative)
                res = np.maximum(np.random.normal(base, base * 0.40, self.sim_count), 0)

            distributions[stat] = res
            out[stat] = round(np.mean(res), 1)
        
        # Store distributions for hit rate calculation
        out['_distributions'] = distributions
        
        return out

    def calculate_hit_rates(self, sim_profile, sportsbook_lines):
        """
        NEW: Calculate probability of going OVER each sportsbook line.
        This is the CORRECT way to get probabilities from Monte Carlo.
        
        Args:
            sim_profile: Result from _simulate_outcomes (contains _distributions)
            sportsbook_lines: Dict like {'pts': 25.5, 'reb': 8.5, 'ast': 6.5}
            
        Returns:
            Dict of hit rates like {'pts': 0.62, 'reb': 0.55, 'ast': 0.48}
        """
        hit_rates = {}
        distributions = sim_profile.get('_distributions', {})
        
        stat_key_map = {
            'pts': 'PTS', 'reb': 'REB', 'ast': 'AST',
            '3pm': 'FG3M', 'oreb': 'OREB', 'stl': 'STL', 'blk': 'BLK'
        }
        
        for prop_key, line in sportsbook_lines.items():
            if line is None or line == 'N/A':
                continue
                
            stat_key = stat_key_map.get(prop_key.lower())
            if stat_key and stat_key in distributions:
                dist = distributions[stat_key]
                # THE MAGIC: What % of 5000 simulations went OVER the line?
                hit_rate = np.mean(dist > float(line))
                hit_rates[prop_key] = round(hit_rate, 4)
        
        return hit_rates

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