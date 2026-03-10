import sys
import os
import pandas as pd
import time
import logging
import argparse
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

# EST timezone handling
from utils.time_utils import get_est_today
from utils.daily_lock import get_target_config, filter_slate_by_config, apply_filters

# --- IMPORT ARCHITECTURE (MODULES A-H) ---
try:
    import config
    from module_a import Gatekeeper        # The Gatekeeper (Lines)
    from module_b import LudiEngine  # The Engine (Trends/Streaks/Hit Rates)
    from module_c import LudiOracle        # The Simulator (Math)
    from module_d import LudiYak           # The Yak (News)
    from module_e import LudiCalibrator    # The Calibrator (Adjustments)
    from module_f import LudiReporter      # The Reporter (Briefing)
    from module_g import LudiRefEngine     # The Zebras (Referees)
    from module_h_historian import LudiHistorian  # Database/Historical Data
    from module_x_scenario import ScenarioBuilder # The Architect (Scenarios)
    
    # Utilities
    from utils.pm_bot import ProjectManagerBot
    from utils.api_monitor import get_monitor
    from utils.telegram_notifier import send_message
except ImportError as e:
    print(f"CRITICAL ERROR: Missing a Ludi Module. {e}")
    sys.exit(1)

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format="[LUDI-CORE] %(message)s")

class LudiOrchestrator:
    def __init__(self, target_teams=None, send_telegram=False):
        print("\n" + "="*50)
        print("   LUDI INFORMATIO | SYSTEM INITIALIZATION")
        print("   Architecture: Modules A-H (Production v2.0)")
        print("="*50)

        self.target_teams = target_teams # List of team abbrs (e.g. ['CLE', 'SAC'])
        self.send_telegram = send_telegram

        # Phase 7.4: Respect IS_PRODUCTION flag
        # Only send Telegram if explicitly enabled AND in production
        import config
        production_mode = getattr(config, 'IS_PRODUCTION', False)
        self._telegram_enabled = send_telegram and production_mode

        # 1. INITIALIZE ALL SYSTEMS
        debug_mode = os.getenv('DEBUG_LOG', 'false').lower() == 'true'
        # In production, default DEBUG_LOG to False
        if production_mode and not os.getenv('DEBUG_LOG'):
            debug_mode = False
        self.gate = Gatekeeper()
        self.historian = LudiHistorian()
        self.engine = LudiEngine()  # Pre-loads trends, game values, name map
        self.sim = LudiOracle()
        self.yak = LudiYak()
        self.calib = LudiCalibrator(debug_log=debug_mode)
        self.reporter = LudiReporter()
        self.zebras = LudiRefEngine()
        self.scenario_builder = ScenarioBuilder()
        
        # Build Ref DB immediately
        self.zebras.build_ref_database()
        
        # Database path
        self.db_path = "ludi.db"

    def get_active_roster(self, team_abbr: str, limit: int = 12) -> List[Dict]:
        """Query database for top N players by minutes, joined with PBP Shot Quality.
        G1: Game-count window (last 25 played games) replaces calendar-day window.
        Calendar windows shrink to 1-4 games during All-Star break/injuries — game-count is stable.
        G2c: Returns GAMES_PLAYED count (row[21]) for Module C season-blend confidence weighting.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = '''
            SELECT pgl.player_id, pgl.player_name, pgl.team_abbreviation,
                   AVG(pgl.pts), AVG(pgl.reb), AVG(pgl.ast),
                   AVG(pgl.fga), AVG(pgl.fg3a), AVG(pgl.fta),
                   AVG(pgl.oreb), AVG(pgl.dreb), AVG(pgl.stl), AVG(pgl.blk),
                   AVG(pgl.tov), AVG(pgl.minutes),
                   MAX(psq.shot_quality_avg), MAX(psq.at_rim_frequency), MAX(psq.corner3_frequency),
                   CASE WHEN SUM(pgl.fga) > 0 THEN ROUND(1.0 * SUM(pgl.fgm) / SUM(pgl.fga), 4) ELSE 0.45 END,
                   CASE WHEN SUM(pgl.fg3a) > 0 THEN ROUND(1.0 * SUM(pgl.fg3m) / SUM(pgl.fg3a), 4) ELSE 0.35 END,
                   CASE WHEN SUM(pgl.fta) > 0 THEN ROUND(1.0 * SUM(pgl.ftm) / SUM(pgl.fta), 4) ELSE 0.75 END,
                   COUNT(pgl.player_id) as games_played
            FROM player_game_logs pgl
            LEFT JOIN player_season_quality psq ON pgl.player_id = psq.player_id AND psq.season = '2025-26'
            WHERE pgl.team_abbreviation = ? AND pgl.minutes > 0
              AND pgl.game_date IN (
                  SELECT game_date FROM player_game_logs sub
                  WHERE sub.player_id = pgl.player_id AND sub.minutes > 0
                  ORDER BY game_date DESC LIMIT 25
              )
            GROUP BY pgl.player_id, pgl.player_name, pgl.team_abbreviation
            HAVING COUNT(pgl.player_id) >= 3
            ORDER BY AVG(pgl.minutes) DESC LIMIT ?
        '''
        cursor.execute(query, (team_abbr, limit))
        rows = cursor.fetchall()
        conn.close()

        roster = []
        for row in rows:
            fga, fta, tov, mins = row[6] or 0, row[8] or 0, row[13] or 0, row[14] or 0
            base_usg = round(((fga + 0.44*fta + tov)/mins)/2.1, 3) if mins > 0 else 0

            # Extract PBP Stats
            shot_quality = row[15] if row[15] is not None else 0.53  # League avg fallback
            at_rim_freq = row[16] if row[16] is not None else 0.0
            corner3_freq = row[17] if row[17] is not None else 0.0

            roster.append({
                'player_id': row[0], 'PLAYER_NAME': row[1], 'TEAM_ABBREVIATION': row[2],
                'PTS': round(row[3] or 0, 1), 'REB': round(row[4] or 0, 1), 'AST': round(row[5] or 0, 1),
                'FGA': round(fga, 1), 'FG3A': round(row[7] or 0, 1), 'FTA': round(fta, 1),
                'OREB': round(row[9] or 0, 1), 'DREB': round(row[10] or 0, 1),
                'STL': round(row[11] or 0, 1), 'BLK': round(row[12] or 0, 1), 'TOV': round(tov, 1),
                'MIN': round(mins, 1), 'base_usg': base_usg, 'base_min': round(mins, 1),
                'FG_PCT': row[18], 'FG3_PCT': row[19], 'FT_PCT': row[20],
                'pbp_shot_quality': round(shot_quality, 3),
                'pbp_rim_freq': round(at_rim_freq, 3),
                'pbp_corner3_freq': round(corner3_freq, 3),
                # G2c: game count for Module C season-baseline blend confidence
                # <15 games → blend with season avg; ≥15 games → use recent data only
                'GAMES_PLAYED': row[21] if row[21] is not None else 25,
                # Sprint 3: starter context for Module C minutes projection
                # Source: players.is_starter (1=starter, 0=bench, NULL=unknown)
                'is_starter': None,  # populated below from players table
            })

        # Sprint 3: Populate is_starter for each roster player from players table
        # This lets Module C choose avg_min_as_starter or avg_min_off_bench appropriately.
        if roster:
            try:
                conn_s = sqlite3.connect(self.db_path)
                cursor_s = conn_s.cursor()
                ids = [p['player_id'] for p in roster]
                placeholders = ','.join('?' * len(ids))
                cursor_s.execute(
                    f"SELECT player_id, is_starter FROM players WHERE player_id IN ({placeholders})",
                    ids
                )
                starter_map = {str(r[0]): r[1] for r in cursor_s.fetchall()}
                conn_s.close()
                for p in roster:
                    raw = starter_map.get(str(p['player_id']))
                    p['is_starter'] = bool(raw) if raw is not None else None
            except Exception:
                pass  # Silently fall back to None (Module C will use avg_minutes)

        # --- Tier 1.5: Freshly Traded (on team per players table but no new-team logs yet) ---
        # Phase 8.12: catch players traded in last 1-2 days who haven't played for new team
        tier1_ids = {p['player_id'] for p in roster}
        try:
            conn15 = sqlite3.connect(self.db_path)
            cursor15 = conn15.cursor()
            cursor15.execute("""
                SELECT p.player_id, p.name
                FROM players p
                WHERE p.team = ?
                  AND p.is_active = 1
                  AND p.player_id NOT IN (
                      SELECT player_id FROM player_game_logs
                      WHERE team_abbreviation = ? AND game_date >= date('now', '-30 days')
                  )
                  AND EXISTS (
                      SELECT 1 FROM player_game_logs pgl2
                      WHERE pgl2.player_id = p.player_id
                        AND pgl2.game_date >= date('now', '-30 days')
                  )
            """, (team_abbr, team_abbr))
            traded_players = cursor15.fetchall()

            for pid, pname in traded_players:
                if pid in tier1_ids:
                    continue
                # Pull L10 from their most recent (old) team's game logs
                cursor15.execute("""
                    SELECT AVG(pts), AVG(reb), AVG(ast), AVG(fga), AVG(fg3a), AVG(fta),
                           AVG(oreb), AVG(dreb), AVG(stl), AVG(blk), AVG(tov), AVG(minutes),
                           CASE WHEN SUM(fga)>0 THEN ROUND(1.0*SUM(fgm)/SUM(fga),4) ELSE 0.45 END,
                           CASE WHEN SUM(fg3a)>0 THEN ROUND(1.0*SUM(fg3m)/SUM(fg3a),4) ELSE 0.35 END,
                           CASE WHEN SUM(fta)>0 THEN ROUND(1.0*SUM(ftm)/SUM(fta),4) ELSE 0.75 END,
                           team_abbreviation
                    FROM (
                        SELECT pts, reb, ast, fga, fg3a, fta, fgm, fg3m, ftm,
                               oreb, dreb, stl, blk, tov, minutes, team_abbreviation
                        FROM player_game_logs
                        WHERE player_id = ? AND game_date >= date('now', '-30 days')
                        ORDER BY game_date DESC LIMIT 10
                    )
                """, (pid,))
                row = cursor15.fetchone()
                if not row or row[0] is None:
                    continue
                fga, fta, tov, mins = row[3] or 0, row[5] or 0, row[10] or 0, row[11] or 0
                base_usg = round(((fga + 0.44*fta + tov)/mins)/2.1, 3) if mins > 0 else 0
                old_team = row[15] or 'UNK'

                roster.append({
                    'player_id': pid, 'PLAYER_NAME': pname, 'TEAM_ABBREVIATION': team_abbr,
                    'PTS': round(row[0] or 0, 1), 'REB': round(row[1] or 0, 1), 'AST': round(row[2] or 0, 1),
                    'FGA': round(fga, 1), 'FG3A': round(row[4] or 0, 1), 'FTA': round(fta, 1),
                    'OREB': round(row[6] or 0, 1), 'DREB': round(row[7] or 0, 1),
                    'STL': round(row[8] or 0, 1), 'BLK': round(row[9] or 0, 1), 'TOV': round(tov, 1),
                    'MIN': round(mins, 1), 'base_usg': base_usg, 'base_min': round(mins, 1),
                    'FG_PCT': row[12], 'FG3_PCT': row[13], 'FT_PCT': row[14],
                    'pbp_shot_quality': 0.53, 'pbp_rim_freq': 0.0, 'pbp_corner3_freq': 0.0,
                    'tier': 'NEWLY_TRADED',
                    'NEWLY_TRADED': True,
                    'NEW_TEAM_GAMES': 0,
                })
                tier1_ids.add(pid)
                print(f"[ROSTER] Tier 1.5 (freshly traded): {pname} → {team_abbr} (pre-trade stats from {old_team})")
            conn15.close()
        except Exception as e:
            print(f"[ROSTER] Tier 1.5 lookup error: {e}")

        # --- Tier 2: Recently returned players (from player_injuries, last 7 days) ---
        try:
            conn2 = sqlite3.connect(self.db_path)
            cursor2 = conn2.cursor()
            cursor2.execute("""
                SELECT DISTINCT p.player_id
                FROM player_injuries pi
                JOIN players p ON p.name = pi.player_name
                WHERE pi.resolved_at >= date('now', '-7 days')
                  AND pi.resolved_at IS NOT NULL
                  AND p.team = ?
                  AND NOT EXISTS (
                      SELECT 1 FROM player_injuries pi2
                      WHERE pi2.player_name = pi.player_name
                        AND pi2.resolved_at IS NULL
                        AND pi2.status IN ('OUT', 'DOUBTFUL')
                  )
            """, (team_abbr,))
            returned_ids = [r[0] for r in cursor2.fetchall() if r[0] not in tier1_ids]

            for pid in returned_ids:
                cursor2.execute("""
                    SELECT pgl.player_id, pgl.player_name, pgl.team_abbreviation,
                           AVG(pgl.pts), AVG(pgl.reb), AVG(pgl.ast),
                           AVG(pgl.fga), AVG(pgl.fg3a), AVG(pgl.fta),
                           AVG(pgl.oreb), AVG(pgl.dreb), AVG(pgl.stl), AVG(pgl.blk),
                           AVG(pgl.tov), AVG(pgl.minutes),
                           NULL, NULL, NULL,
                           CASE WHEN SUM(pgl.fga) > 0 THEN ROUND(1.0*SUM(pgl.fgm)/SUM(pgl.fga),4) ELSE 0.45 END,
                           CASE WHEN SUM(pgl.fg3a) > 0 THEN ROUND(1.0*SUM(pgl.fg3m)/SUM(pgl.fg3a),4) ELSE 0.35 END,
                           CASE WHEN SUM(pgl.fta) > 0 THEN ROUND(1.0*SUM(pgl.ftm)/SUM(pgl.fta),4) ELSE 0.75 END
                    FROM player_game_logs pgl
                    WHERE pgl.player_id = ? AND pgl.game_date >= date('now', '-30 days')
                    GROUP BY pgl.player_id, pgl.player_name, pgl.team_abbreviation
                    HAVING COUNT(pgl.player_id) >= 1
                """, (pid,))
                row = cursor2.fetchone()
                if row:
                    fga, fta, tov, mins = row[6] or 0, row[8] or 0, row[13] or 0, row[14] or 0
                    base_usg = round(((fga + 0.44*fta + tov)/mins)/2.1, 3) if mins > 0 else 0
                    roster.append({
                        'player_id': row[0], 'PLAYER_NAME': row[1], 'TEAM_ABBREVIATION': row[2],
                        'PTS': round(row[3] or 0, 1), 'REB': round(row[4] or 0, 1), 'AST': round(row[5] or 0, 1),
                        'FGA': round(fga, 1), 'FG3A': round(row[7] or 0, 1), 'FTA': round(fta, 1),
                        'OREB': round(row[9] or 0, 1), 'DREB': round(row[10] or 0, 1),
                        'STL': round(row[11] or 0, 1), 'BLK': round(row[12] or 0, 1), 'TOV': round(tov, 1),
                        'MIN': round(mins, 1), 'base_usg': base_usg, 'base_min': round(mins, 1),
                        'FG_PCT': row[18], 'FG3_PCT': row[19], 'FT_PCT': row[20],
                        'pbp_shot_quality': 0.53, 'pbp_rim_freq': 0.0, 'pbp_corner3_freq': 0.0,
                        'tier': 'WELCOME_BACK'
                    })
                    print(f"[ROSTER] Tier 2 (recently returned): {row[1]} ({row[2]})")
            conn2.close()
        except Exception:
            print(f"[ROSTER] player_injuries table not ready — using Tier 1 only")

        # --- Tier 3: Long-term injured (>14 days out) — log only, skip simulation ---
        try:
            conn3 = sqlite3.connect(self.db_path)
            cursor3 = conn3.cursor()
            cursor3.execute("""
                SELECT p.name, p.team, p.days_out_current
                FROM players p
                JOIN player_injuries pi ON p.name = pi.player_name
                WHERE pi.resolved_at IS NULL
                  AND p.days_out_current > 14
                GROUP BY p.player_id
            """)
            for row in cursor3.fetchall():
                name, team, days_out = row[0], row[1] or 'UNK', row[2] or 0
                print(f"[INJURY-TIER3] {name} ({team}) — {days_out}d out, skipped")
            conn3.close()
        except Exception:
            pass  # Tier 3 is informational only — never blocks simulation

        return roster

    def get_opponent_stats(self, opponent_abbr: str) -> Dict:
        """Query database for team-wide opponent stats."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = '''
            SELECT SUM(tov), SUM(fga), SUM(fg3a), SUM(fta)
            FROM player_game_logs
            WHERE team_abbreviation = ? AND game_date >= date('now', '-30 days')
        '''
        cursor.execute(query, (opponent_abbr,))
        row = cursor.fetchone()
        conn.close()

        if not row or not row[0]:
            return {'tov_rate': 0, 'two_pa_rate': 0}

        total_tov, total_fga, total_fg3a, total_fta = row
        
        possessions = total_fga + 0.44 * total_fta + total_tov
        tov_rate = total_tov / possessions if possessions else 0

        two_pa_rate = (total_fga - total_fg3a) / total_fga if total_fga else 0

        return {'tov_rate': tov_rate, 'two_pa_rate': two_pa_rate}

    def fetch_props_for_game(self, game_id: str) -> Dict[str, Dict]:
        return self.gate.games.get(game_id, {}).get('props', {})

    def _get_days_rest(self, team_abbr: str, game_date: str) -> int:
        """Return days since last recorded game for a team abbreviation."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT MAX(date) FROM games
                WHERE (home_team = ? OR away_team = ?) AND date < ?
                """,
                (team_abbr, team_abbr, game_date)
            )
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                last_game = datetime.strptime(row[0], '%Y-%m-%d').date()
                target_date = datetime.strptime(game_date, '%Y-%m-%d').date()
                return (target_date - last_game).days
        except Exception as e:
            print(f"⚠️  Rest lookup failed for {team_abbr} on {game_date}: {e}")

        return 2

    def match_props_to_roster(self, props_data: Dict, roster: List[Dict]) -> List[Dict]:
        matched = []
        for p in roster:
            if p['PLAYER_NAME'] in props_data:
                pc = p.copy()
                pc['sportsbook_props'] = props_data[p['PLAYER_NAME']]
                matched.append(pc)
        return matched

    def build_simulation_scenario(self, game_data: Dict, home_roster: List[Dict], away_roster: List[Dict]) -> Dict:
        # Get referee data (now a dict with pace_impact, whistle_impact, crew, confidence)
        ref_data = game_data.get('archetypes', {}).get('ref_data', {
            'pace_impact': 1.0, 'whistle_impact': 1.0, 'crew': [], 'confidence': 0.0
        })
        vegas_total = game_data.get('vegas', {}).get('total', config.LEAGUE_AVG_TOTAL)
        if isinstance(vegas_total, (int, float)) and vegas_total > 0:
            pace_factor = vegas_total / config.LEAGUE_AVG_TOTAL
            pace_factor = max(0.90, min(1.10, pace_factor))
        else:
            pace_factor = 1.0

        home_team = home_roster[0].get('TEAM_ABBREVIATION', '') if home_roster else ''
        away_team = away_roster[0].get('TEAM_ABBREVIATION', '') if away_roster else ''
        game_date = game_data.get('date', get_est_today())
        home_days_rest = self._get_days_rest(home_team, game_date) if home_team else 2
        away_days_rest = self._get_days_rest(away_team, game_date) if away_team else 2

        players = []
        for p in home_roster:
            pc = p.copy()
            pc['days_rest'] = home_days_rest
            players.append(pc)
        for p in away_roster:
            pc = p.copy()
            pc['days_rest'] = away_days_rest
            players.append(pc)

        # Phase 8.9: include spread so module_c._get_projected_minutes() can apply blowout context
        vegas_spread = game_data.get('vegas', {}).get('spread', 0)
        try:
            vegas_spread = float(vegas_spread) if vegas_spread not in (None, 'N/A', '') else 0.0
        except (ValueError, TypeError):
            vegas_spread = 0.0

        return {
            'scenario_name': game_data.get('matchup', 'UNKNOWN').replace(' @ ', '_vs_').replace(' ', '_'),
            'ref_data': ref_data,  # Pass full dict for pace AND whistle impact
            'pace_factor': pace_factor,
            'def_factor': 1.0,
            'days_rest': min(home_days_rest, away_days_rest),
            'home_team': home_team,
            'away_team': away_team,
            'spread': vegas_spread,   # Phase 8.9: situational minutes context
            'players': players
        }

    def build_reporter_input(self, sim_results: List[Dict], game_data: Dict, props_data: Dict) -> List[Dict]:
        STAT_MAPPING = {
            'PTS': 'proj_pts', 'REB': 'proj_reb', 'AST': 'proj_ast',
            'FG3M': 'proj_3pm', 'OREB': 'proj_oreb', 'MIN': 'proj_min',
            'FGA': 'proj_fga', 'FTA': 'proj_fta',
            'STL': 'proj_stl', 'BLK': 'proj_blk', 'DREB': 'proj_dreb'
        }
        home, away = self.gate._get_abbr(game_data.get('home')), self.gate._get_abbr(game_data.get('away'))
        
        vegas_data = game_data.get('vegas', {})
        try:
            spread = float(vegas_data.get('spread', 0)) if vegas_data.get('spread') not in (None, 'N/A', '') else 0.0
        except (ValueError, TypeError):
            spread = 0.0
        try:
            total = float(vegas_data.get('total', 0)) if vegas_data.get('total') not in (None, 'N/A', '') else 0.0
        except (ValueError, TypeError):
            total = 0.0
        team_total_home = vegas_data.get('team_total_home')
        team_total_away = vegas_data.get('team_total_away')
        home_team = vegas_data.get('home_team', home)

        home_stats = self.get_opponent_stats(home)
        away_stats = self.get_opponent_stats(away)
        
        players = []
        for sim in sim_results:
            p_name = sim.get('PLAYER_NAME')
            if not p_name: continue  # BUG A3: guard against None player name
            if p_name not in props_data: continue

            is_home = sim.get('TEAM') == home
            opponent_stats = away_stats if is_home else home_stats
            
            p_dict = {
                'name': p_name, 'team': sim.get('TEAM'), 'opponent': away if is_home else home,
                'status': sim.get('status', 'Active'), 
                'scenario': sim.get('SCENARIO', 'BASE'),  # Propagate scenario name
                'wowy_confidence': sim.get('wowy_confidence'),  # Propagate WOWY confidence (if exists)
                'decision_note': sim.get('decision_note', ''),  # Captured from Yak
                'notes': '', 'odds': {
                    'spread': spread, 
                    'total': total,
                    'team_total_home': team_total_home,
                    'team_total_away': team_total_away,
                    'home_team': home_team
                },
                'base_pts': sim.get('PTS', 0), 'base_reb': sim.get('REB', 0), 
                'base_ast': sim.get('AST', 0), 'base_3pm': sim.get('FG3M', 0),
                # H2: Fix USG% key - Module C outputs USG_PCT as percentage (e.g., 28.5 not 0.285)
                'base_min': sim.get('MIN', 0), 'base_usg': sim.get('USG_PCT', 0) / 100.0,
                'opponent_stats': opponent_stats,
                'games_since_return': sim.get('GAMES_SINCE_RETURN'),
                'effective_starter': sim.get('effective_starter', False)
            }
            
            # Map stats
            for c_key, f_key in STAT_MAPPING.items(): p_dict[f_key] = sim.get(c_key, 0)
            
            # Format props
            props_fmt = {}
            for k, v in props_data[p_name].items():
                try: 
                    # Handle both new format (dict with odds) and old format (line only)
                    if isinstance(v, dict):
                        # Module A v9.3+ format (with line shopping)
                        line = v.get('line')
                        if not line or float(line) <= 0:
                            print(f"   >>> [main] Skipping prop {k}: no real market line (line={line})")
                            continue
                        line = float(line)
                        
                        # Fix: Handle explicit None values (key exists but value is None)
                        val_over = v.get('odds_over')
                        val_under = v.get('odds_under')
                        
                        o_over = val_over if val_over not in (None, 0) else -110  # D1: guard 0 odds
                        o_under = val_under if val_under not in (None, 0) else -110  # D1: guard 0 odds
                        
                        # NEW: Extract bookmaker sources (Line Shopping V2.0)
                        book_over = v.get('book_over', 'consensus')
                        book_under = v.get('book_under', 'consensus')
                    else:
                        # Legacy fallback
                        line = float(v)
                        o_over = -110
                        o_under = -110
                        book_over = 'legacy'
                        book_under = 'legacy'

                    mk = {
                        'points': 'pts', 'rebounds': 'reb', 'assists': 'ast',
                        'threes': '3pm', 'offensive_rebounds': 'oreb',
                        'steals': 'stl', 'blocks': 'blk', 'turnovers': 'tov',
                        'points_rebounds_assists': 'pra',
                        'points_assists': 'pa',
                        'points_rebounds': 'pr',
                        'rebounds_assists': 'ra',
                    }.get(k, k)
                    props_fmt[mk] = {
                        'line': line, 
                        'odds_over': o_over, 
                        'odds_under': o_under,
                        'book_over': book_over,
                        'book_under': book_under,
                        'sharp_odds_over': v.get('sharp_odds_over') if isinstance(v, dict) else None,
                        'sharp_odds_under': v.get('sharp_odds_under') if isinstance(v, dict) else None,
                        'sharp_book_over':  v.get('sharp_book_over')  if isinstance(v, dict) else None,
                        'sharp_book_under': v.get('sharp_book_under') if isinstance(v, dict) else None
                    }
                except Exception as e:
                    print(f"   >>> [main] Prop format error for {k}: {e}")
                    continue
            
            if props_fmt:
                p_dict['sportsbook_props'] = props_fmt
                
                # NEW: Calculate hit rates from simulation distributions
                # This is the CORRECT probability from 5000 Monte Carlo runs
                if '_distributions' in sim:
                    lines_for_calc = {k: v.get('line') for k, v in props_fmt.items() if isinstance(v, dict)}
                    hit_rates = self.sim.calculate_hit_rates(sim, lines_for_calc)
                    p_dict['sim_hit_rates'] = hit_rates  # e.g. {'pts': 0.62, 'reb': 0.55}
                
                # Module G: Per-player star bias vs today's ref crew
                _ref_data = game_data.get('archetypes', {}).get('ref_data', {})
                _crew = _ref_data.get('crew', []) if isinstance(_ref_data, dict) else []
                if _crew:
                    _crew_bias = self.zebras.get_player_crew_bias(p_name, _crew)
                    if _crew_bias:
                        p_dict['crew_bias'] = _crew_bias

                # Module B: Enrich with trends, hit rates, streak scores
                self.engine.enrich_player(p_dict, props_fmt)
                
                yak = {'status': sim.get('status', 'ACTIVE'), 'note': sim.get('injury_note', '')}
                # BUG A4: validate Module E output before appending
                result = self.calib.calibrate_player(p_dict, yak)
                if result:
                    players.append(result)

        # Use the game's actual start_time for game_date — not today's date.
        # This prevents tomorrow's games (visible after 9 PM) from being logged
        # with today's date in bet_recommendations.
        _start_time = game_data.get('start_time')
        if _start_time and hasattr(_start_time, 'strftime'):
            _actual_game_date = _start_time.strftime('%Y-%m-%d')
        elif isinstance(_start_time, str) and len(_start_time) >= 10:
            _actual_game_date = _start_time[:10] # ISO string from games cache
        else:
            _actual_game_date = get_est_today()

        return [{
            'game_id': game_data.get('matchup', 'UNKNOWN').replace(' @ ', '_vs_'),
            'matchup': game_data.get('matchup', 'UNKNOWN'),
            'game_date': _actual_game_date,
            'home_team': home, 'away_team': away, 'opponent': '',
            'spread': float(spread) if spread != 'N/A' else 0,
            'total': float(total) if isinstance(total, (int, float)) else 0,
            'team_total_home': team_total_home,
            'team_total_away': team_total_away,
            'ref_data': game_data.get('archetypes', {}).get('ref_data', {'pace_impact': 1.0, 'whistle_impact': 1.0, 'crew': [], 'confidence': 0.0}),
            # Sprint 4: alt lines captured by Module A Phase 2B → consumed by Module F EV sweep
            # Structure: {stat_key: {player_name: {alt_line: {odds_over, book_over, odds_under, book_under}}}}
            'alt_props': game_data.get('alt_props', {}),
            'players': players
        }]

    def run_daily_cycle(self):
        print("\n" + "="*50)
        print("   >>> STARTING DAILY SIMULATION CYCLE <<<")
        print("   Mode: Production v2.0")
        print("="*50)

        # STEP 0: LOAD DAILY LOCK CONFIG
        lock_config = get_target_config()
        if lock_config:
            mode = lock_config.get('mode', 'LIVE')
            print(f"   📋 Daily Lock: {lock_config.get('lock_date')} | Mode: {mode}")

        # STEP 1: FETCH SLATE
        self.gate.fetch_live_slate()

        # --- APPLY GAME LIMIT (for testing) ---
        limit_games = os.getenv('LIMIT_GAMES')
        if limit_games:
            limit_games = int(limit_games)
            games_list = list(self.gate.games.items())
            if len(games_list) > limit_games:
                print(f"🧪 TEST MODE: Limiting to {limit_games} game(s) (found {len(games_list)})")
                # Keep only the first N games
                limited_games = dict(games_list[:limit_games])
                self.gate.games = limited_games

        # --- APPLY DAILY LOCK FILTERING (if TESTING mode) ---
        if lock_config:
            # Convert games dict to list for filtering
            games_list = [{'game_id': gid, **gdata} for gid, gdata in self.gate.games.items()]
            
            # Apply matchup filtering
            games_list = filter_slate_by_config(games_list, lock_config)
            
            # Apply spread/total filters
            games_list = apply_filters(games_list, lock_config)
            
            # Convert back to dict
            self.gate.games = {g['game_id']: g for g in games_list}
        
        # --- LEGACY: CLI TARGET TEAMS FILTER (still supported) ---
        if self.target_teams:
            targets = [t.upper() for t in self.target_teams]
            print(f"   🎯 TARGET FILTER ACTIVE: {targets}")
            
            filtered = {}
            for gid, gdata in self.gate.games.items():
                h = self.gate._get_abbr(gdata.get('home', ''))
                a = self.gate._get_abbr(gdata.get('away', ''))
                if h in targets or a in targets:
                    filtered[gid] = gdata
                    print(f"      ✅ LOCKED: {gdata.get('matchup', gid)}")
            
            self.gate.games = filtered
            print(f"   ✅ Slate reduced to {len(self.gate.games)} games.")

        if not self.gate.games:
            print("❌ No games found. Exiting.")
            return

        # STEP 2: FETCH PROPS
        self.gate.fetch_comprehensive_props(limit_games=len(self.gate.games))
        print("✅ Props loaded.")
        self.gate.save_games_cache()  # Cache odds so morning_brief/evening_lock skip API re-fetch

        # STEP 2.5: Snapshot opening lines for line history (Module B)
        from datetime import datetime
        game_date = datetime.now().strftime('%Y-%m-%d')
        self.engine.snapshot_opening_lines(self.gate.games, game_date)

        all_scenarios = []
        
        # STEP 3: BUILD SCENARIOS
        print("[step 3] Building Scenarios & Rosters...")
        for game_id, game_data in self.gate.games.items():
            if not game_data.get('props'): continue
            
            h_abbr = self.gate._get_abbr(game_data['home'])
            a_abbr = self.gate._get_abbr(game_data['away'])
            
            print(f"   > Processing {game_data['matchup']}...")
            
            h_roster = self.get_active_roster(h_abbr)
            a_roster = self.get_active_roster(a_abbr)
            h_matched = self.match_props_to_roster(self.fetch_props_for_game(game_id), h_roster)
            a_matched = self.match_props_to_roster(self.fetch_props_for_game(game_id), a_roster)
            
            if not h_matched and not a_matched: continue

            # Yak Filter
            final_h, final_a = [], []
            for p in h_matched:
                status = self.yak.get_player_status(p['PLAYER_NAME'], h_abbr)
                p['status'], p['injury_status'], p['injury_note'] = status['status'], status['status'], status.get('note', '')
                if (status['status'] or 'ACTIVE').upper() not in ('OUT', 'DOUBTFUL'): final_h.append(p)

            for p in a_matched:
                status = self.yak.get_player_status(p['PLAYER_NAME'], a_abbr)
                p['status'], p['injury_status'], p['injury_note'] = status['status'], status['status'], status.get('note', '')
                if (status['status'] or 'ACTIVE').upper() not in ('OUT', 'DOUBTFUL'): final_a.append(p)

            # Build Base & Fork Scenarios
            base = self.build_simulation_scenario(game_data, final_h, final_a)
            forks = self.scenario_builder.generate_scenarios([base])
            print(f"      ↳ Generated {len(forks)} scenarios")
            
            for sc in forks:
                all_scenarios.append({'scenario': sc, 'game_data': game_data, 'props_data': self.fetch_props_for_game(game_id)})

        # STEP 4: RUN SIMS & RESOLVE SCENARIOS
        print(f"[step 4] Running Monte Carlo Simulations ({len(all_scenarios)} scenarios)...")
        
        # Group scenarios by game to handle forks correctly
        games_batch = {}
        for item in all_scenarios:
            gid = item['game_data']['matchup']
            if gid not in games_batch: games_batch[gid] = []
            games_batch[gid].append(item)
            
        processed_slate = []
        
        for gid, items in games_batch.items():
            try:
                # 1. Run all sims for this game (Base + Forks)
                game_sim_results = []
                for item in items:
                    res = self.sim.run_simulation_batch([item['scenario']])
                    scenario_name = item['scenario']['scenario_name']
                    
                    # Propagate scenario name AND wowy_confidence from scenario player data
                    for r in res:
                        r['SCENARIO'] = scenario_name
                        
                        # Find original player data in scenario to preserve wowy_confidence
                        for scenario_player in item['scenario']['players']:
                            if scenario_player.get('PLAYER_NAME') == r.get('PLAYER_NAME'):
                                if 'wowy_confidence' in scenario_player:
                                    r['wowy_confidence'] = scenario_player['wowy_confidence']
                                break
                    
                    game_sim_results.extend(res)
                
                # 2. Resolve Scenarios via Yak (Handle Injuries)
                # This picks the correct scenario for each player based on live status
                final_game_results = self.yak.resolve_scenarios(game_sim_results)
                
                # 3. Build Report
                # Use game/props data from the first item (same for all in batch)
                first = items[0]
                processed_slate.extend(self.build_reporter_input(final_game_results, first['game_data'], first['props_data']))
                
            except Exception as e:
                print(f"⚠️  Sim failed for {gid}: {e}")

        # STEP 5: REPORT
        print("[step 5] Generating Daily Briefing (Module F)...")
        # Pass BDL fallback status so Module F can display the appropriate banner
        self.reporter._bdl_fallback_active = getattr(self.gate, '_using_bdl_fallback', False)
        briefing, image_path, _ = self.reporter.generate_report(processed_slate)
        print("\n" + "="*50)
        print("DAILY BRIEFING GENERATED")
        print("="*50)
        print(briefing)
        
        with open("daily_briefing.txt", "w") as f: f.write(briefing)
        print("\n✅ Saved to daily_briefing.txt")
        print(f"✅ Visual Card saved to: {image_path}")
        
        if self._telegram_enabled:
            print("[step 6] Sending Telegram Briefing...")
            send_message(f"📊 **LUDI SIMULATION RESULTS** 📊\n\n{briefing}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=str, default="interactive")
    parser.add_argument("--games", nargs='+', help="Target teams (e.g. CLE SAC)")
    parser.add_argument("--send-telegram", action='store_true', help="Send results via Telegram")
    args = parser.parse_args()

    if args.mode in ("pm_briefing", "morning_brief", "morning"):
        ProjectManagerBot().generate_briefing(mode="morning")
    elif args.mode in ("pm_debrief", "nightly_brief", "nightly", "debrief"):
        # Automated nightly P&L debrief — uses nightly graphic (header_nightly.png)
        ProjectManagerBot().generate_briefing(mode="nightly")
    elif args.mode in ("pm_session", "session_debrief", "pm_break", "break", "break_notes", "state_preserve", "pause"):
        ProjectManagerBot().send_break_message()
    else:
        app = LudiOrchestrator(target_teams=args.games, send_telegram=args.send_telegram)
        app.run_daily_cycle()
