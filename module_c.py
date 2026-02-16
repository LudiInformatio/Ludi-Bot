import numpy as np
import sqlite3

import config

# =========================================================
# LUDI INFORMATIO | MODULE C: THE ORACLE
# V4.0 - MODULE C OVERHAUL (2025-26)
# =========================================================

"""
DATA CONTRACT
Input player dict keys:
  PLAYER_NAME, player_id, TEAM_ABBREVIATION, MIN,
  FGA, FG3A, FTA, FG_PCT, FG3_PCT, FT_PCT,
  PTS, REB, AST, OREB, DREB, STL, BLK, TOV,
  injury_status/status/injury (optional), days_rest (optional)

Input scenario keys:
  scenario_name, ref_data, pace_factor, def_factor,
  days_rest, players, home_team, away_team

Output sim_profile keys:
  PTS, REB, AST, FGA, FG3A, FTA, FGM, FG3M, FTM,
  OREB, DREB, STL, BLK, TOV, USG_PCT, FANTASY_PTS,
  PLAYER_NAME, TEAM, SCENARIO, PACE_MOD, REST, MIN,
  _distributions
"""


class LudiOracle:
    def __init__(self, sim_count=None):
        self.sim_count = sim_count or config.SIM_COUNT
        print(f"\n{'='*40}")
        print("LUDI INFORMATIO: MODULE C (ORACLE V4.0) LIVE")
        print("   >>> Hybrid Engine: Normal (High-Vol) + Poisson (Rare)")
        print(f"   >>> Sim Count: {self.sim_count}")
        print(f"{'='*40}")

        self.db_path = 'ludi.db'
        self.STAT_MAP = {
            'points': 'PTS', 'rebounds': 'REB', 'assists': 'AST',
            'threes': 'FG3M', 'blocks': 'BLK', 'steals': 'STL',
            'turnovers': 'TOV', 'fga': 'FGA', 'fta': 'FTA',
            'offensive_rebounds': 'OREB', 'defensive_rebounds': 'DREB'
        }

        self.shot_quality_data = {}
        self.rolling_ts_data = {}
        self.drives_data = {}
        self.team_defense = {}

        self._load_shot_quality_data()
        self._load_rolling_ts_data()
        self._load_drives_data()
        self._load_team_defense_data()

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

    def _load_team_defense_data(self):
        """Load opponent FG% allowed by each team for the last 30 days."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                SELECT team_abbrev, AVG(opp_fg_pct) as avg_opp_fg
                FROM player_game_opponent
                WHERE game_date >= date('now', '-30 days') AND opp_fg_pct IS NOT NULL
                GROUP BY team_abbrev
                HAVING COUNT(DISTINCT game_date) >= 5
            """)
            rows = c.fetchall()
            conn.close()

            if not rows:
                self.team_defense = {}
                print("   >>> Team defense data loaded: 0 teams")
                return

            league_avg = sum(row[1] for row in rows) / len(rows)
            self.team_defense = {row[0]: row[1] / league_avg for row in rows}
            print(f"   >>> Team defense data loaded: {len(self.team_defense)} teams")
        except Exception as e:
            print(f"   >>> Team defense data unavailable: {e}")
            self.team_defense = {}

    def _calculate_efficiency_modifier(self, player):
        """Blend shot quality and rolling TS% into a capped FG efficiency modifier."""
        player_id = str(player.get('player_id', ''))
        player_name = player.get('PLAYER_NAME', '')

        sq_mod = 1.0
        sq = self.shot_quality_data.get(player_id)
        if sq is not None:
            sq_mod = max(0.95, min(1.05, sq / 0.55))

        ts_mod = 1.0
        ts = self.rolling_ts_data.get(player_name)
        if ts is not None:
            ts_mod = max(0.95, min(1.05, ts / config.LEAGUE_AVG_TS_PCT))

        if sq is not None and ts is not None:
            combined = (sq_mod * 0.5) + (ts_mod * 0.5)
        elif sq is not None:
            combined = sq_mod
        elif ts is not None:
            combined = ts_mod
        else:
            combined = 1.0

        return max(0.92, min(1.08, combined))

    def run_simulation_batch(self, scenarios_list):
        simulated_results = []

        for scenario in scenarios_list:
            scen_name = scenario.get('scenario_name', 'BASE')
            players = scenario.get('players', [])
            sample_player = players[0] if players else {}
            expected_keys = ['FG_PCT', 'FG3_PCT', 'FT_PCT', 'FGA', 'FG3A', 'FTA', 'MIN', 'PLAYER_NAME']
            missing = [k for k in expected_keys if k not in sample_player]
            if missing:
                print(f"   >>> WARNING: Player dict missing keys: {missing} - using defaults")

            ref_data = scenario.get('ref_data', {})
            ref_pace = ref_data.get('pace_impact', 1.0) if isinstance(ref_data, dict) else scenario.get('ref_impact', 1.0)
            ref_whistle = ref_data.get('whistle_impact', 1.0) if isinstance(ref_data, dict) else scenario.get('ref_whistle', 1.0)

            base_pace = scenario.get('pace_factor', 1.0) * ref_pace
            team_totals = self._sum_team_projections(players, base_pace)

            for player in players:
                status = player.get('injury_status', player.get('status', player.get('injury', 'Active')))
                if status in ['Out', 'Doubtful', 'OUT', 'DOUBTFUL'] or player.get('MIN', 0) == 0:
                    continue

                player_days_rest = int(player.get('days_rest', scenario.get('days_rest', 1)))
                fatigue_tax = self._calculate_fatigue_tax(player_days_rest)

                player_team = player.get('TEAM_ABBREVIATION', '')
                if player_team == scenario.get('home_team'):
                    opp_team = scenario.get('away_team')
                else:
                    opp_team = scenario.get('home_team')
                opp_def = self.team_defense.get(opp_team, scenario.get('def_factor', 1.0))
                player_def_factor = max(0.92, min(1.08, opp_def))

                player_mods = {
                    "pace": base_pace * fatigue_tax,
                    "def_rtg": player_def_factor,
                    "whistle": ref_whistle,
                    "fatigue": fatigue_tax,
                    "team_min": 240
                }

                vol_profile = self._simulate_volume(player, player_mods)
                sim_profile = self._simulate_outcomes(player, vol_profile, player_mods)
                sim_profile['USG_PCT'] = self._calculate_usage(sim_profile, player, team_totals, player_mods)
                sim_profile['FANTASY_PTS'] = self._calculate_fantasy_score(sim_profile)

                sim_profile.update({
                    "PLAYER_NAME": player.get('PLAYER_NAME'),
                    "TEAM": player.get('TEAM_ABBREVIATION'),
                    "SCENARIO": scen_name,
                    "PACE_MOD": round(player_mods['pace'], 3),
                    "REST": f"{player_days_rest}D",
                    "MIN": round(player.get('MIN', 0), 1)
                })

                simulated_results.append(sim_profile)

        return simulated_results

    def _calculate_fatigue_tax(self, days_rest):
        if days_rest == 0:
            return config.FATIGUE_B2B_TAX
        if days_rest >= 4:
            return config.FATIGUE_RUST_TAX
        return 1.0

    def _simulate_volume(self, player, mods):
        """Returns full distribution arrays for FGA/FG3A/FTA."""
        vol = {}
        for stat in ['FGA', 'FG3A', 'FTA']:
            base = player.get(stat, 0.0)
            stat_mod = mods['pace']
            if stat == 'FTA':
                stat_mod *= mods['whistle']

            adj_base = max(base * stat_mod, 0.0)
            if adj_base < config.SIM_POISSON_THRESHOLD:
                vol[stat] = np.random.poisson(adj_base, self.sim_count).astype(float)
            else:
                vol[stat] = np.maximum(
                    np.random.normal(adj_base, adj_base * config.SIM_VARIANCE, self.sim_count),
                    0.0
                )

        return vol

    def _simulate_outcomes(self, player, vol_dist, mods):
        """Simulates outcomes and returns means plus full distributions."""
        out = {}
        distributions = {}

        fg_pct = player.get('FG_PCT', 0.45) * mods['def_rtg'] * mods['fatigue']
        fg3_pct = player.get('FG3_PCT', 0.35) * mods['fatigue']
        ft_pct = player.get('FT_PCT', 0.75)

        efficiency_mod = self._calculate_efficiency_modifier(player)
        fg_pct *= efficiency_mod
        fg3_pct *= efficiency_mod

        fgm_dist = vol_dist['FGA'] * fg_pct
        fg3m_dist = vol_dist['FG3A'] * fg3_pct
        ftm_dist = vol_dist['FTA'] * ft_pct

        distributions['FGM'] = fgm_dist
        distributions['FG3M'] = fg3m_dist
        distributions['FTM'] = ftm_dist

        two_pt_dist = np.maximum(fgm_dist - fg3m_dist, 0.0)
        pts_dist = (two_pt_dist * 2) + (fg3m_dist * 3) + ftm_dist

        out['FGA'] = round(np.mean(vol_dist['FGA']), 1)
        out['FG3A'] = round(np.mean(vol_dist['FG3A']), 1)
        out['FTA'] = round(np.mean(vol_dist['FTA']), 1)
        out['FGM'] = round(np.mean(fgm_dist), 1)
        out['FG3M'] = round(np.mean(fg3m_dist), 1)
        out['FTM'] = round(np.mean(ftm_dist), 1)

        player_name = player.get('PLAYER_NAME', '')
        drives = self.drives_data.get(player_name, {})
        drives_pts_boost = 1.0
        drives_ast_boost = 1.0

        if drives:
            pass_pct = drives.get('pass_pct', 0)
            drives_pts = drives.get('drives_pts', 0)

            if pass_pct > 40:
                drives_ast_boost = 1.05 + min((pass_pct - 40) / 200, 0.05)
            elif pass_pct < 20:
                drives_ast_boost = 0.97

            if drives_pts > 6:
                drives_pts_boost = 1.03 + min((drives_pts - 6) / 100, 0.02)
            elif drives_pts < 2:
                drives_pts_boost = 0.97

        if drives_pts_boost != 1.0:
            pts_dist = pts_dist * drives_pts_boost

        distributions['PTS'] = pts_dist
        out['PTS'] = round(np.mean(pts_dist), 1)

        for stat in ['AST', 'REB', 'OREB', 'DREB', 'STL', 'BLK', 'TOV']:
            base = max(player.get(stat, 0.0) * mods['pace'], 0.0)
            if stat == 'AST' and drives_ast_boost != 1.0:
                base *= drives_ast_boost

            if stat in ['STL', 'BLK'] or base < config.SIM_POISSON_THRESHOLD:
                res = np.random.poisson(base, self.sim_count).astype(float)
            else:
                res = np.maximum(
                    np.random.normal(base, base * config.SIM_VARIANCE, self.sim_count),
                    0.0
                )

            distributions[stat] = res
            out[stat] = round(np.mean(res), 1)

        out['_distributions'] = distributions
        return out

    def calculate_hit_rates(self, sim_profile, sportsbook_lines):
        """Calculate probability of going over each sportsbook line."""
        hit_rates = {}
        distributions = sim_profile.get('_distributions', {})

        stat_key_map = {
            'pts': 'PTS', 'reb': 'REB', 'ast': 'AST',
            '3pm': 'FG3M', 'oreb': 'OREB', 'stl': 'STL', 'blk': 'BLK',
            'tov': 'TOV'
        }

        for prop_key, line in sportsbook_lines.items():
            if line is None or line == 'N/A':
                continue

            stat_key = stat_key_map.get(prop_key.lower())
            if stat_key and stat_key in distributions:
                dist = distributions[stat_key]
                hit_rate = np.mean(dist > float(line))
                hit_rates[prop_key] = round(hit_rate, 4)

        return hit_rates

    def _calculate_usage(self, sim, player, team, mods):
        try:
            p_pos = sim['FGA'] + (0.44 * sim['FTA']) + sim['TOV']
            t_pos = team['FGA'] + (0.44 * team['FTA']) + team['TOV']
            return round(100 * (p_pos * (mods['team_min'] / 5)) / (player['MIN'] * t_pos), 1)
        except Exception as e:
            print(f"   >>> Usage calc error for {player.get('PLAYER_NAME', '?')}: {e}")
            return 0.0

    def _calculate_fantasy_score(self, sim):
        return round((sim['PTS'] * 1) + (sim['FG3M'] * 0.5) + (sim['REB'] * 1.25) +
                     (sim['AST'] * 1.5) + (sim['STL'] * 2) + (sim['BLK'] * 2) - (sim['TOV'] * 0.5), 2)

    def _sum_team_projections(self, players, pace=1.0):
        return {
            "FGA": sum(p.get('FGA', 0) for p in players) * pace,
            "FTA": sum(p.get('FTA', 0) for p in players) * pace,
            "TOV": sum(p.get('TOV', 0) for p in players) * pace
        }


if __name__ == "__main__":
    oracle = LudiOracle()
