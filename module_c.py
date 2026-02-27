import json
import unicodedata

import numpy as np
import sqlite3

import config

# DB tables use 'YYYY-YY' format, NOT config.CURRENT_SEASON ('YYYY-YYYY')
_DB_SEASON = '2025-26'

BASELINE_SHOT_QUALITY = 0.55   # League-average expected eFG% (PBP Stats)
TEAM_TOTAL_MINUTES = 240       # 5 players x 48 minutes per game

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
  GAMES_PLAYED (int, from get_active_roster for season-blend confidence),
  injury_status/status/injury (optional), days_rest (optional)

Input scenario keys:
  scenario_name, ref_data, pace_factor, def_factor,
  days_rest, players, home_team, away_team

Output sim_profile keys:
  PTS, REB, AST, FGA, FG3A, FTA, FGM, FG3M, FTM,
  OREB, DREB, STL, BLK, TOV, USG_PCT, FANTASY_PTS,
  PLAYER_NAME, TEAM, SCENARIO, PACE_MOD, REST, MIN,
  MIN_SCALE (float, stored as metadata — not applied to volume),
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

        self.db_path = config.DB_PATH

        # Pre-loaded data dicts — zero DB queries during 10K simulation loops
        self.shot_quality_data = {}
        self.rolling_ts_data = {}
        self.drives_data = {}
        self.team_defense = {}
        self.foul_splits_data = {}
        self.rotation_data = {}      # A1: pre-loaded rotation_profiles
        self.season_baselines = {}   # G2: season averages for thin-sample blend
        self.return_status = {}      # G3: injury return ramp-up detection

        self._load_shot_quality_data()
        self._load_rolling_ts_data()
        self._load_drives_data()
        self._load_team_defense_data()
        self._load_foul_splits_data()
        self._load_rotation_data()
        self._load_season_baselines()
        self._load_return_status()

    # ── DATA LOADERS ──────────────────────────────────────────────────────────

    def _load_shot_quality_data(self):
        """Load shot quality averages from PBP Stats (player_shot_quality table)."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "SELECT player_id, shot_quality_avg FROM player_shot_quality WHERE season = ?",
                (_DB_SEASON,)
            )
            rows = c.fetchall()
            conn.close()
            self.shot_quality_data = {row[0]: row[1] for row in rows if row[1] is not None}
            print(f"   >>> Shot quality data loaded: {len(self.shot_quality_data)} players")
        except Exception as e:
            print(f"   >>> Shot quality data unavailable: {e}")
            self.shot_quality_data = {}

    def _load_rolling_ts_data(self):
        """Load rolling TS% from player_game_advanced (last 25 games per player, min 3 games).
        G4: game-count window replaces calendar-day window to avoid All-Star/injury gaps.
        Uses CTE with ROW_NUMBER() rather than correlated subquery — single-pass, no per-row scans.
        Names normalized at load time so accent variants resolve correctly (C4).
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # CTE ranks each player's games newest-first; outer query takes top 25 per player
            c.execute("""
                WITH ranked AS (
                    SELECT player_name, ts_pct,
                           ROW_NUMBER() OVER (
                               PARTITION BY player_name ORDER BY game_date DESC
                           ) AS rn
                    FROM player_game_advanced
                    WHERE ts_pct IS NOT NULL AND ts_pct > 0
                )
                SELECT player_name, AVG(ts_pct) as avg_ts
                FROM ranked
                WHERE rn <= 25
                GROUP BY player_name
                HAVING COUNT(*) >= 3
            """)
            rows = c.fetchall()
            conn.close()
            # Normalize names at load time — accent variants resolve correctly (C4)
            self.rolling_ts_data = {self._normalize_name(row[0]): row[1] for row in rows}
            print(f"   >>> Rolling TS% data loaded: {len(self.rolling_ts_data)} players")
        except Exception as e:
            print(f"   >>> Rolling TS% data unavailable: {e}")
            self.rolling_ts_data = {}

    def _load_drives_data(self):
        """Load drives context from player_game_tracking (last 25 games per player, min 3 games).
        G4: game-count window replaces calendar-day window.
        Names normalized at load time for accent consistency (C4).
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                WITH ranked AS (
                    SELECT player_name, drives_pass_pct, drives_pts,
                           ROW_NUMBER() OVER (
                               PARTITION BY player_name ORDER BY game_date DESC
                           ) AS rn
                    FROM player_game_tracking
                    WHERE drives_pass_pct IS NOT NULL AND drives_pts IS NOT NULL
                )
                SELECT player_name, AVG(drives_pass_pct) as avg_pass_pct, AVG(drives_pts) as avg_drives_pts
                FROM ranked
                WHERE rn <= 25
                GROUP BY player_name
                HAVING COUNT(*) >= 3
            """)
            rows = c.fetchall()
            conn.close()
            self.drives_data = {
                self._normalize_name(row[0]): {'pass_pct': row[1], 'drives_pts': row[2]}
                for row in rows
            }
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

    def _load_foul_splits_data(self):
        """Pre-load player foul splits for fast per-player dampener lookup.
        Follows the same pattern as _load_shot_quality_data().
        Keyed by player_id (int) → {min_dampener, data_confidence}.
        """
        self.foul_splits_data = {}
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT player_id, min_dampener, data_confidence FROM player_foul_splits WHERE season = ?",
                (_DB_SEASON,)
            ).fetchall()
            conn.close()
            for row in rows:
                self.foul_splits_data[int(row['player_id'])] = {
                    'min_dampener': row['min_dampener'],
                    'data_confidence': row['data_confidence']
                }
            print(f"   >>> Foul splits loaded: {len(self.foul_splits_data)} players")
        except Exception as e:
            print(f"   ⚠️ Foul splits load failed (dampener inactive): {e}")
            self.foul_splits_data = {}

    def _load_rotation_data(self):
        """A1: Pre-load rotation_profiles at init — eliminates per-player DB queries
        during simulation loop. Previously opened sqlite3.connect() for every player.
        Keyed by str(player_id) → sqlite3.Row-compatible dict.
        """
        self.rotation_data = {}
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM rotation_profiles WHERE window_days = 21"
            ).fetchall()
            conn.close()
            for row in rows:
                self.rotation_data[str(row['player_id'])] = dict(row)
            print(f"   >>> Rotation profiles loaded: {len(self.rotation_data)} players")
        except Exception as e:
            print(f"   >>> Rotation profiles unavailable: {e}")
            self.rotation_data = {}

    def _load_season_baselines(self):
        """G2: Load full-season averages from BDL as blending baseline for thin-sample players.
        Thin sample = <15 games in the recent window (get_active_roster L25).
        Season baseline prevents a 3-game sample from dominating projections.
        """
        self.season_baselines = {}
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                SELECT player_name, stats_json
                FROM player_season_averages_bdl
                WHERE category = 'general' AND stat_type = 'base' AND season = 2025
            """)
            for row in c.fetchall():
                name = self._normalize_name(row[0])
                stats = json.loads(row[1]).get('stats', {})
                self.season_baselines[name] = {
                    'PTS': stats.get('pts', 0),
                    'REB': stats.get('reb', 0),
                    'AST': stats.get('ast', 0),
                    'FGA': stats.get('fga', 0),
                    'FG3A': stats.get('fg3a', 0),
                    'FTA': stats.get('fta', 0),
                    'STL': stats.get('stl', 0),
                    'BLK': stats.get('blk', 0),
                    'TOV': stats.get('tov', 0),
                    'OREB': stats.get('oreb', 0),
                    'DREB': stats.get('dreb', 0),
                    'MIN': stats.get('min', 0),
                    'FG_PCT': stats.get('fg_pct', 0.45),
                    'FG3_PCT': stats.get('fg3_pct', 0.35),
                    'FT_PCT': stats.get('ft_pct', 0.75),
                    'GP': stats.get('gp', 0),
                }
            conn.close()
            print(f"   >>> Season baselines loaded: {len(self.season_baselines)} players")
        except Exception as e:
            print(f"   >>> Season baselines unavailable: {e}")
            self.season_baselines = {}

    def _load_return_status(self):
        """G3: Detect players recently returned from absence (gap > 7 days in last 5 games).
        Returns dict: str(player_id) → games_since_return (int, 1-5).
        Uses game log gaps — no dependency on player_injuries table.
        """
        self.return_status = {}
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            # LAG with ASC order gets the chronologically previous game date.
            # ROW_NUMBER with DESC order counts from most-recent (rn=1 = most recent game).
            # Gap detection: julianday(current) - julianday(prev) > 7 = 7+ day absence.
            # MIN(rn) per player captures the MOST RECENT return event.
            c.execute("""
                WITH ranked AS (
                    SELECT player_id, game_date,
                           LAG(game_date) OVER (
                               PARTITION BY player_id ORDER BY game_date ASC
                           ) AS prev_date,
                           ROW_NUMBER() OVER (
                               PARTITION BY player_id ORDER BY game_date DESC
                           ) AS rn
                    FROM player_game_logs
                    WHERE minutes > 0 AND game_date >= date('now', '-60 days')
                )
                SELECT player_id, MIN(rn) as games_since_return
                FROM ranked
                WHERE prev_date IS NOT NULL
                  AND julianday(game_date) - julianday(prev_date) > 7
                  AND rn <= 5
                GROUP BY player_id
            """)
            for row in c.fetchall():
                self.return_status[str(row[0])] = row[1]
            conn.close()
            if self.return_status:
                print(f"   >>> Injury return detection: {len(self.return_status)} players recently returned")
        except Exception as e:
            print(f"   >>> Injury return detection unavailable: {e}")
            self.return_status = {}

    # ── HELPERS ───────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_name(name):
        """C4: Strip accents via NFKD so 'Jokić' and 'Jokic' resolve to the same key.
        Matches Module B's _normalize_name() pattern exactly.
        """
        if not name:
            return ''
        return ''.join(
            c for c in unicodedata.normalize('NFKD', name)
            if unicodedata.category(c) != 'Mn'
        ).strip()

    def _calculate_efficiency_modifier(self, player):
        """Blend shot quality and rolling TS% into a capped FG efficiency modifier."""
        player_id = str(player.get('player_id', ''))
        # C4: normalize name for accent-safe lookup into rolling_ts_data
        player_name = self._normalize_name(player.get('PLAYER_NAME', ''))

        sq_mod = 1.0
        sq = self.shot_quality_data.get(player_id)
        if sq is not None:
            # BASELINE_SHOT_QUALITY = 0.55 (league-average expected eFG% from PBP Stats)
            sq_mod = max(0.95, min(1.05, sq / BASELINE_SHOT_QUALITY))

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

    # ── SIMULATION ────────────────────────────────────────────────────────────

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

                # ── G2: Season baseline blend (thin-sample confidence correction) ───────
                # Applies when a player has <15 recent games — blends toward season average
                # to prevent a 3-game sample (e.g., injury return) from dominating projections.
                # Weight formula: w = games_recent / 15, so 3 games = 20% recent / 80% season.
                # Threshold 15 matches PropsMadness L15 stability threshold (competitive research).
                player_name_norm = self._normalize_name(player.get('PLAYER_NAME', ''))
                season_base = self.season_baselines.get(player_name_norm, {})
                games_recent = player.get('GAMES_PLAYED', 25)

                if season_base and games_recent < 15:
                    w = min(games_recent / 15.0, 1.0)
                    for stat in ['PTS', 'REB', 'AST', 'FGA', 'FG3A', 'FTA',
                                 'STL', 'BLK', 'TOV', 'OREB', 'DREB']:
                        recent_val = player.get(stat, 0)
                        season_val = season_base.get(stat, recent_val)
                        player[stat] = round(w * recent_val + (1 - w) * season_val, 1)
                    for pct in ['FG_PCT', 'FG3_PCT', 'FT_PCT']:
                        recent_pct = player.get(pct, 0)
                        season_pct = season_base.get(pct, recent_pct)
                        player[pct] = round(w * recent_pct + (1 - w) * season_pct, 4)

                # ── G3: Injury return ramp-up (first 4 games back from 7+ day absence) ─
                # Scales ALL stats proportionally. Game 1=70%, Game 2=80%, Game 3=90%, Game 4=95%.
                # Applied before simulation so _simulate_volume uses dampened values.
                player_id_key = str(player.get('player_id') or player.get('PLAYER_ID') or '')
                games_back = self.return_status.get(player_id_key, 99)
                if games_back <= 4:
                    ramp_factors = {1: 0.70, 2: 0.80, 3: 0.90, 4: 0.95}
                    ramp = ramp_factors.get(games_back, 1.0)
                    for stat in ['FGA', 'FG3A', 'FTA', 'MIN', 'PTS', 'REB',
                                 'AST', 'STL', 'BLK', 'TOV', 'OREB', 'DREB']:
                        player[stat] = round(player.get(stat, 0) * ramp, 1)
                    print(f"   >>> [Ramp-Up] {player.get('PLAYER_NAME')}: Game {games_back} back "
                          f"— all stats dampened to {ramp*100:.0f}%")

                player_days_rest = int(player.get('days_rest', scenario.get('days_rest', 1)))
                fatigue_tax = self._calculate_fatigue_tax(player_days_rest)

                # Phase 8.9: build game_context for minutes projection
                game_context = {
                    'spread': scenario.get('spread', 0.0),
                    'is_b2b': player_days_rest == 0,
                    'is_starter': player.get('is_starter', None),
                }

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
                    # TEAM_TOTAL_MINUTES = 5 players x 48 min; pace cancels in USG% ratio
                    "team_min": TEAM_TOTAL_MINUTES
                }

                vol_profile = self._simulate_volume(player, player_mods)
                sim_profile = self._simulate_outcomes(player, vol_profile, player_mods)
                sim_profile['USG_PCT'] = self._calculate_usage(sim_profile, player, team_totals, player_mods)
                sim_profile['FANTASY_PTS'] = self._calculate_fantasy_score(sim_profile)

                # Phase 8.9: situational minutes projection
                if getattr(config, 'USE_MINUTES_PROJECTION', True):
                    proj_min, min_conf = self._get_projected_minutes(player, game_context)
                    if proj_min > 0 and player.get('MIN', 0) > 0:
                        min_scale = proj_min / player['MIN']
                        min_scale = max(0.70, min(1.30, min_scale))  # cap at ±30%
                        # A2: Store min_scale as metadata — do NOT mutate player['FGA'] etc.
                        # Simulation already completed above; post-hoc stat mutation had no effect
                        # on sim results (confirmed via build_reporter_input reads sim dict only).
                        sim_profile['MIN_SCALE'] = round(min_scale, 3)
                    else:
                        proj_min = player.get('MIN', 0)
                        min_conf = 'LOW'
                else:
                    proj_min = player.get('MIN', 0)
                    min_conf = 'OFF'

                sim_profile.update({
                    "PLAYER_NAME": player.get('PLAYER_NAME'),
                    "TEAM": player.get('TEAM_ABBREVIATION'),
                    "SCENARIO": scen_name,
                    "PACE_MOD": round(player_mods['pace'], 3),
                    "REST": f"{player_days_rest}D",
                    "MIN": round(proj_min, 1),
                    "MIN_CONF": min_conf
                })

                simulated_results.append(sim_profile)

        return simulated_results

    def _calculate_fatigue_tax(self, days_rest):
        if days_rest == 0:
            return config.FATIGUE_B2B_TAX
        if days_rest >= 4:
            return config.FATIGUE_RUST_TAX
        return 1.0

    def _get_projected_minutes(self, player: dict, game_context: dict) -> tuple:
        """
        Phase 8.9 — Situational minutes projection.
        A1: Uses pre-loaded self.rotation_data dict instead of per-player DB queries.
        Applies spread/B2B/starter context and foul-splits dampener.

        Args:
            player:       Player dict (must have 'MIN' and 'player_id' / 'PLAYER_ID')
            game_context: Dict with optional 'spread' (float) and 'is_b2b' (bool)

        Returns:
            (projected_minutes: float, confidence: str)  where confidence in HIGH/MEDIUM/LOW
        """
        historical_avg = player.get('MIN', 0.0)
        if not historical_avg:
            return (0.0, 'LOW')

        player_id = str(player.get('player_id') or player.get('PLAYER_ID') or '')
        if not player_id:
            print(f"   >>> [MinProj] {player.get('PLAYER_NAME', '?')}: No player_id — using historical avg")
            return (historical_avg, 'LOW')

        # A1: dict lookup replaces per-player sqlite3.connect()
        row = self.rotation_data.get(player_id)

        if not row:
            return (historical_avg, 'LOW')

        games_played = row.get('games_played') or 0
        if games_played >= 10:
            confidence = 'HIGH'
        elif games_played >= 5:
            confidence = 'MEDIUM'
        else:
            confidence = 'LOW'

        # Phase 8.12: downgrade confidence for recently-traded players (< 5 games on current team)
        newly_traded = False
        try:
            games_on_team = row.get('games_on_current_team')
            if games_on_team is not None and games_on_team < 5:
                confidence = 'LOW'
                newly_traded = True
                print(f"   [NEW TO TEAM] {player.get('PLAYER_NAME', '?')}: "
                      f"{games_on_team} games on current team — LOW confidence, 5% dampener")
        except (IndexError, KeyError):
            pass  # Column not yet in DB; silently skip
        except Exception as e:
            print(f"   >>> [MinProj] {player.get('PLAYER_NAME', '?')}: games_on_current_team lookup error: {e}")

        spread = game_context.get('spread', 0.0) or 0.0
        is_b2b = game_context.get('is_b2b', False)
        is_close = abs(spread) < 3.0

        # Pick situational column; fall back to avg_minutes if column is NULL
        chosen = None
        if spread < -12:
            chosen = row.get('avg_min_blowout_win')
        elif spread > 12:
            chosen = row.get('avg_min_blowout_loss')
        elif is_close:
            chosen = row.get('avg_min_close_game')

        if is_b2b and row.get('avg_min_b2b'):
            # B2B overrides other situational contexts (most predictive for fatigue)
            chosen = row.get('avg_min_b2b')

        # Sprint 3: Use real starter/bench splits when starter context is known.
        is_starter_context = game_context.get('is_starter', None)
        try:
            if is_starter_context is True and not chosen and row.get('avg_min_as_starter'):
                chosen = row.get('avg_min_as_starter')
            elif is_starter_context is False and not chosen and row.get('avg_min_off_bench'):
                chosen = row.get('avg_min_off_bench')
        except (KeyError, TypeError) as e:
            print(f"   >>> [MinProj] {player.get('PLAYER_NAME', '?')}: starter/bench split column missing: {e}")

        proj = chosen if chosen else row.get('avg_minutes')
        if not proj:
            return (historical_avg, 'LOW')

        # Phase 8.12: apply 5% dampener for players new to their current team
        if newly_traded:
            proj = float(proj) * 0.95

        # Phase 8.17 — Foul Intelligence dampener
        # Pre-loaded at init — zero DB connections during simulation
        foul_dampener = 1.0
        try:
            foul_row = self.foul_splits_data.get(int(player_id))
            if foul_row and foul_row['data_confidence'] in ('HIGH', 'MEDIUM'):
                foul_dampener = foul_row['min_dampener']
        except (ValueError, TypeError):
            pass  # Non-numeric player_id; skip foul dampener

        proj = float(proj) * foul_dampener

        return (float(proj), confidence)

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

        # NOTE: fg_pct gets def_rtg + fatigue adjustments.
        # fg3_pct gets fatigue only — team-level opp FG% is a blended metric that
        # over-penalizes 3P shooters. Module E applies archetype-level 3P matchup
        # adjustments separately (e.g., STRETCH_BIG vs PAINT_PACK defense).
        fg_pct = player.get('FG_PCT', 0.45) * mods['def_rtg'] * mods['fatigue']
        fg3_pct = player.get('FG3_PCT', 0.35) * mods['fatigue']
        ft_pct = player.get('FT_PCT', 0.75)

        efficiency_mod = self._calculate_efficiency_modifier(player)
        fg_pct *= efficiency_mod
        fg3_pct *= efficiency_mod

        # NOTE: FGM = FGA * FG_PCT (expected-value method, not per-attempt Bernoulli).
        # Understates variance slightly but runs ~50x faster at 10K iterations.
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

        # C4: normalize player name for accent-safe drives lookup
        player_name = self._normalize_name(player.get('PLAYER_NAME', ''))
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

        # NOTE: REB/AST/STL/BLK/TOV only get pace modifier.
        # Defense adjustment deferred to Module E which applies player-level
        # archetype matchup modifiers (e.g., RIM_RUNNER vs PERIMETER defense).
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

        combo_map = {
            'pra': ['PTS', 'REB', 'AST'],
            'pa': ['PTS', 'AST'],
            'pr': ['PTS', 'REB'],
            'ra': ['REB', 'AST'],
        }

        for prop_key, line in sportsbook_lines.items():
            if line is None or line == 'N/A':
                continue

            prop_key_lower = prop_key.lower()
            combo_keys = combo_map.get(prop_key_lower)
            if combo_keys and all(ck in distributions for ck in combo_keys):
                combo_dist = sum(distributions[ck] for ck in combo_keys)
                hit_rate = np.mean(combo_dist > float(line))
                hit_rates[prop_key] = round(hit_rate, 4)
                continue

            stat_key = stat_key_map.get(prop_key_lower)
            if stat_key and stat_key in distributions:
                dist = distributions[stat_key]
                hit_rate = np.mean(dist > float(line))
                hit_rates[prop_key] = round(hit_rate, 4)

        return hit_rates

    def _calculate_usage(self, sim, player, team, mods):
        # NOTE: USG% = player possessions / (team possessions * 5).
        # Both sim FGA and team FGA already include pace, so pace cancels in the ratio.
        # USG% is correctly pace-independent — this is intentional.
        try:
            p_pos = sim['FGA'] + (0.44 * sim['FTA']) + sim['TOV']
            t_pos = team['FGA'] + (0.44 * team['FTA']) + team['TOV']
            return round(100 * (p_pos * (mods['team_min'] / 5)) / (player['MIN'] * t_pos), 1)
        except Exception as e:
            print(f"   >>> Usage calc error for {player.get('PLAYER_NAME', '?')}: {e}")
            return 0.0

    def _calculate_fantasy_score(self, sim):
        return round((sim['PTS'] * 1) + (sim['FG3M'] * 0.5) + (sim['REB'] * 1.25) +
                     (sim['AST'] * 1.5) + (sim['STL'] * 3) + (sim['BLK'] * 3) - (sim['TOV'] * 0.5), 2)

    def _sum_team_projections(self, players, pace=1.0):
        return {
            "FGA": sum(p.get('FGA', 0) for p in players) * pace,
            "FTA": sum(p.get('FTA', 0) for p in players) * pace,
            "TOV": sum(p.get('TOV', 0) for p in players) * pace
        }


if __name__ == "__main__":
    oracle = LudiOracle()
