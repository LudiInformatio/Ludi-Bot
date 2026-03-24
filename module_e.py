import sqlite3
import json
import unicodedata
import logging
from pathlib import Path
import config
from utils.player_id_resolver import PlayerIDResolver
from utils.team_offensive_classifier import TEAM_OFFENSIVE_TYPES
from utils.team_defensive_classifier import TeamDefensiveClassifier

try:
    from utils.pbp_stats_client import get_team_leverage_summary
    PBP_STATS_AVAILABLE = True
except ImportError:
    PBP_STATS_AVAILABLE = False

# ==========================================
# LUDI INFORMATIO | MODULE E: THE CALIBRATOR
# V7.0 - SECONDARY PLAYTYPE SYSTEM (Week 2 Integration)
# ==========================================

# Game environment thresholds (Phase 8.18)
GAME_TOTAL_HIGH_THRESHOLD = 238.0
GAME_TOTAL_LOW_THRESHOLD = 218.0
TEAM_TOTAL_RATIO_MIN = 0.93
TEAM_TOTAL_RATIO_MAX = 1.07

# Archetype/playtype thresholds
SECONDARY_PLAYTYPE_SCORE_MIN = 0.60
SYNERGY_MIN_POSSESSIONS = 75


def _canonical_key(name: str) -> str:
    """NFD-normalize + strip accents + lowercase + remove spaces/dots/apostrophes.
    Matches player_canonical_ids.normalized_name format exactly."""
    nfd = unicodedata.normalize('NFD', name or '')
    ascii_only = nfd.encode('ascii', 'ignore').decode()
    return ascii_only.lower().replace(' ', '').replace('.', '').replace("'", '')


class LudiCalibrator:
    def __init__(self, db_path='ludi.db', debug_log=False):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE E (CALIBRATOR V7.0) ONLINE")
        print(f"   >>> SECONDARY PLAYTYPE SYSTEM ACTIVE")
        if debug_log:
            print(f"   >>> DEBUG LOGGING ENABLED")
        print(f"{'='*40}")
        
        self.db_path = db_path
        self.debug_log = debug_log
        
        # Initialize debug logger if enabled
        if debug_log:
            logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            self.logger = logging.getLogger('module_e')
            self.logger.info("=== Module E Debug Logging Initialized ===")
        
        self.id_resolver = PlayerIDResolver()
        
        # Phase 7.4: Load clutch/leverage data for close game boosts
        self.clutch_teams = {}  # {team_abbr: {'clutch_ortg': float, 'overall_ortg': float, 'is_clutch': bool}}
        self._load_clutch_data()

        # Sprint 1: Load speed/fatigue data for hustle and fatigue context
        self.speed_data = {}  # {player_name: {speed, distance, speed_recent}}
        self._load_speed_fatigue_data()

        # Sprint 2: Load touches data for usage refinement
        self.touches_data = {}  # {player_name: {touches_per_game, avg_sec_per_touch, ...}}
        self._load_touches_data()

        # Sprint 3: Load team leverage profiles for game state intelligence
        self.leverage_profiles = {}  # {team_abbr: {vh_pace, l_pace, pace_variance, ...}}
        self._load_leverage_profiles()

        # Sprint 3: Load player leverage usage for crunch time identification
        self.player_leverage = {}  # {player_name: {clutch_usage_rate, vh_possessions}}
        self._load_player_leverage_usage()

        # Step 8/9: Load cached data for archetype and opponent context wiring
        self.hustle_profiles = {}
        self.defense_profiles = {}
        self.tracking_profiles = {}
        self.opponent_profiles = {}
        self._load_hustle_profiles()
        self._load_defense_profiles()
        self._load_tracking_profiles()
        self._load_opponent_defense_profiles()

        # Audit Sprint: Bulk pre-loads for performance (eliminates 160 DB connections/slate)
        self.synergy_playtypes_cache = self._load_synergy_playtypes_bulk()
        self.tracking_stats_cache = self._load_tracking_stats_bulk()
        self.player_type_profiles = self._load_player_type_profiles()
        self.dvp_by_archetype = self._load_dvp_by_archetype()
        self.archetype_vs_defense_matrix = self._load_archetype_vs_defense_matrix()
        self.b2b_splits = self._load_b2b_splits()
        self.shot_quality_cache = self._load_shot_quality_bulk()

        self.ADJUSTMENT_RULES = {
            "MINUTES_LIMIT": 0.75,   
            "PROMOTION": 1.50,       
            "OUT": 0.0              
        }
        
        # 2025-26 VERIFIED DEFENSIVE STYLES
        # Season-long dynamic alignment (2025-10-01 to 2026-03-04), updated pre-Sprint 2
        self.DEFENSIVE_STYLES = {
            "ATL": "BLITZ",
            "BOS": "PAINT_PACK",
            "BKN": "PERIMETER",
            "CHA": "PERIMETER",
            "CHI": "PAINT_PACK",
            "CLE": "PAINT_PACK",
            "DAL": "NEUTRAL",
            "DEN": "PAINT_PACK",
            "DET": "NEUTRAL",
            "GSW": "PERIMETER",
            "HOU": "NEUTRAL",
            "IND": "PAINT_PACK",
            "LAC": "PAINT_PACK",
            "LAL": "NEUTRAL",
            "MEM": "PAINT_PACK",
            "MIA": "PAINT_PACK",
            "MIL": "NEUTRAL",
            "MIN": "PAINT_PACK",
            "NOP": "NEUTRAL",
            "NYK": "PAINT_PACK",
            "OKC": "NEUTRAL",
            "ORL": "PERIMETER",
            "PHI": "PAINT_PACK",
            "PHX": "PERIMETER",
            "POR": "NEUTRAL",
            "SAC": "PERIMETER",
            "SAS": "PAINT_PACK",
            "TOR": "PERIMETER",
            "UTA": "NEUTRAL",
            "WAS": "PERIMETER"
        }
        cache_loaded = self._load_cached_defensive_styles()
        if not cache_loaded:
            self._load_dynamic_defensive_styles()

        # OFFENSIVE_STYLES: loaded from team_scheme_cache (Feb 25, 2026)
        # Falls back to team_offensive_classifier.py (in-memory) if cache is empty
        self.OFFENSIVE_STYLES = {}
        self._load_cached_offensive_styles()

        # MANUAL OVERRIDES (The "Scout's Eye")
        self.MANUAL_OVERRIDES = {
            "domantassabonis": "HUB_BIG",
            "draymondgreen": "HUB_BIG"
        }

        # === POSITION-ARCHETYPE AFFINITY MATRIX (Week 2 Enhancement) ===
        # Position refines archetype selection when multiple stat matches exist
        # Higher score = stronger affinity for that position
        self.POSITION_ARCHETYPE_AFFINITY = {
            # Centers: Prioritize big archetypes
            'C': {
                'HUB_BIG': 1.0,
                'STRETCH_BIG': 0.9,
                'ROLL_MAN': 0.8,
                'HELIOCENTRIC_MAESTRO': 0.3,  # Rare for centers
                'JUMBO_FACILITATOR': 0.2,
            },

            # Forwards: Balanced
            'F': {
                'JUMBO_FACILITATOR': 1.0,
                'SLASHING_CREATOR': 0.9,
                'ISO_ASSASSIN': 0.9,
                'TWO_LEVEL_SCORER': 0.8,
                'STRETCH_BIG': 0.7,
            },

            # Guards: Prioritize ball-handler archetypes
            'G': {
                'HELIOCENTRIC_MAESTRO': 1.0,
                'JUMBO_FACILITATOR': 0.9,
                'FACILITATOR': 0.9,
                'SNIPER_ELITE': 0.8,
                'ISO_ASSASSIN': 0.8,
                'HUB_BIG': 0.1,  # Very rare for guards
            },

            # Unknown: No preference (existing logic)
            'UNK': {}  # Empty dict = no affinity bonuses
        }

        # === SECONDARY PLAYTYPE SYSTEM (Week 2 Integration) ===
        # Position-based filtering: Guards create, wings cut/shoot, bigs finish
        self.POSITION_ELIGIBILITY = {
            'G': ['ISO_SCORER', 'P&R_HANDLER', 'SPOT_UP', 'TRANSITION', 'HANDOFF', 'OFF_SCREEN'],
            'G-F': ['ISO_SCORER', 'P&R_HANDLER', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION', 'HANDOFF', 'OFF_SCREEN'],
            'F': ['ISO_SCORER', 'P&R_HANDLER', 'P&R_ROLL_MAN', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION', 'HANDOFF', 'OFF_SCREEN'],
            'F-C': ['P&R_ROLL_MAN', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION', 'PUTBACK', 'POST_UP', 'OFF_SCREEN'],
            'C': ['P&R_ROLL_MAN', 'OFF_BALL_CUTTER', 'PUTBACK', 'POST_UP', 'SPOT_UP', 'TRANSITION'],
            'UNK': ['ISO_SCORER', 'P&R_HANDLER', 'P&R_ROLL_MAN', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION', 'PUTBACK', 'POST_UP', 'HANDOFF', 'OFF_SCREEN']
        }
        
        # Position bonuses for priority scoring (validated in Week 1)
        self.POSITION_BONUSES = {
            ('OFF_BALL_CUTTER', 'F'): 0.15,
            ('OFF_BALL_CUTTER', 'G-F'): 0.15,
            ('P&R_ROLL_MAN', 'C'): 0.10,
            ('P&R_ROLL_MAN', 'F-C'): 0.10,
            ('POST_UP', 'C'): 0.10,
            ('SPOT_UP', 'F'): 0.05,
            ('SPOT_UP', 'G-F'): 0.05,
            ('ISO_SCORER', 'G'): 0.05,
            ('ISO_SCORER', 'G-F'): 0.05
        }
        
        # Qualification thresholds (Week 1 validated)
        self.PRIMARY_THRESHOLD = 0.66
        self.SECONDARY_THRESHOLD = 0.50
        
        # Load playtype thresholds from config
        self.db_path = Path(db_path)
        self.config_path = Path(__file__).parent / 'config' / 'playtype_thresholds.json'
        self.playtype_thresholds = self._load_playtype_thresholds()

    def _get_conn(self):
        """Get database connection with WAL mode (Phase 6.1)"""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

    def _fetch_missing_stats(self, player_name, team_abbr=None):
        """Database fallback for missing stats."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            query = '''SELECT AVG(stl), AVG(blk), AVG(fga), AVG(fta), AVG(tov), COUNT(*) 
                       FROM player_game_logs WHERE player_name = ? AND game_date >= date('now', '-20 days')'''
            cursor.execute(query, (player_name,))
            row = cursor.fetchone()
            conn.close()
            if row and row[5] >= 3:
                stl, blk, fga, fta, tov = row[0] or 0, row[1] or 0, row[2] or 0, row[3] or 0, row[4] or 0
                return {'base_stl': round(stl, 2), 'base_blk': round(blk, 2), 'base_usg': round((fga + 0.44*fta + tov)/100, 3)}
            return {'base_stl': 0, 'base_blk': 0, 'base_usg': 0.20}
        except Exception as e:
            if self.debug_log and hasattr(self, 'logger'):
                self.logger.debug(f"ERROR | {player_name} | MISSING_STATS | {str(e)}")
            return {'base_stl': 0, 'base_blk': 0, 'base_usg': 0.20}

    def _load_hustle_profiles(self):
        """Load 30-day hustle profiles for contested rebounding proxies."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                """
                SELECT h.player_name,
                       AVG(COALESCE(h.box_outs, 0)) AS box_outs,
                       AVG(COALESCE(h.contested_shots, 0)) AS contested_shots,
                       AVG(COALESCE(pgl.reb, 0)) AS reb
                FROM player_game_hustle h
                LEFT JOIN player_game_logs pgl
                  ON pgl.player_name = h.player_name
                 AND pgl.game_date = h.game_date
                WHERE h.game_date >= date('now', '-30 days')
                GROUP BY h.player_name
                HAVING COUNT(*) >= 5
                """
            )
            rows = c.fetchall()
            conn.close()

            self.hustle_profiles = {}
            for player_name, box_outs, contested_shots, reb in rows:
                reb = reb or 0.0
                box_outs = box_outs or 0.0
                contested_shots = contested_shots or 0.0
                proxy = (0.06 * box_outs) + (0.02 * contested_shots) + (0.015 * reb)
                self.hustle_profiles[player_name] = {
                    'contested_reb_pct': max(0.18, min(0.65, proxy))
                }
        except Exception as e:
            print(f"[Module E] Hustle profiles unavailable: {e}")
            self.hustle_profiles = {}

    def _load_defense_profiles(self):
        """Load defensive differential proxies used for defender archetypes."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                """
                SELECT
                    d.player_name,
                    AVG(COALESCE(d.diff_pct, 0)),
                    AVG(COALESCE(d.freq_pct, 0)),
                    AVG(COALESCE(d.dfga, 0)),
                    MAX(COALESCE(d.position, 'UNK')),
                    AVG(COALESCE(s.dist_miles_def, 0))
                FROM player_defense d
                LEFT JOIN player_speed s
                  ON s.player_name = d.player_name
                 AND s.season = d.season
                WHERE d.season = '2025-26'
                GROUP BY d.player_name
                """
            )
            rows = c.fetchall()
            conn.close()

            self.defense_profiles = {
                row[0]: {
                    'def_diff_vs_screen': row[1] or 0.0,
                    'def_diff_vs_iso': row[1] or 0.0,
                    'def_diff_pct': row[1] or 0.0,
                    'def_freq_pct': row[2] or 0.0,
                    'def_dfga': row[3] or 0.0,
                    'def_position': row[4] or 'UNK',
                    'def_distance_miles': row[5] or 0.0,
                }
                for row in rows
            }
        except Exception as e:
            print(f"[Module E] Defense profiles unavailable: {e}")
            self.defense_profiles = {}

    def _load_tracking_profiles(self):
        """Preload tracking aggregates once to avoid repeated per-player queries."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                """
                SELECT
                    player_name,
                    AVG(drives_fga) AS avg_drives,
                    AVG(drives_pass_pct) AS avg_drives_pass_pct,
                    AVG(catch_shoot_fga) AS avg_cs_fga,
                    AVG(CAST(catch_shoot_fgm AS FLOAT) / NULLIF(catch_shoot_fga, 0)) AS cs_pct,
                    AVG(catch_shoot_3pa) AS avg_cs_3pa,
                    AVG(pull_up_fga) AS avg_pu_fga,
                    AVG(CAST(pull_up_fgm AS FLOAT) / NULLIF(pull_up_fga, 0)) AS pu_pct,
                    AVG(avg_speed_off) AS avg_speed,
                    AVG(dist_miles_off) AS avg_distance,
                    AVG(contested_fga) AS avg_contested_fga,
                    AVG(tight_fga) AS avg_tight_fga,
                    AVG(open_fga) AS avg_open_fga,
                    AVG(wide_open_fga) AS avg_wide_open_fga,
                    AVG(avg_defender_dist) AS avg_defender_dist,
                    COUNT(*) AS games
                FROM player_game_tracking
                WHERE game_date >= date('now', '-60 days')
                GROUP BY player_name
                HAVING COUNT(*) >= 3
                """
            )
            rows = c.fetchall()
            conn.close()

            self.tracking_profiles = {
                row[0]: {
                    'avg_drives': row[1] or 0.0,
                    'avg_drives_pass_pct': row[2] or 0.0,
                    'avg_cs_fga': row[3] or 0.0,
                    'cs_pct': row[4] or 0.0,
                    'avg_cs_3pa': row[5] or 0.0,
                    'avg_pu_fga': row[6] or 0.0,
                    'pu_pct': row[7] or 0.0,
                    'avg_speed': row[8] or 0.0,
                    'avg_distance': row[9] or 0.0,
                    'avg_contested_fga': row[10] or 0.0,
                    'avg_tight_fga': row[11] or 0.0,
                    'avg_open_fga': row[12] or 0.0,
                    'avg_wide_open_fga': row[13] or 0.0,
                    'avg_defender_dist': row[14] or 0.0,
                    'tracking_games': row[15] or 0,
                    'shot_difficulty_games': row[15] or 0,
                }
                for row in rows
            }
        except Exception as e:
            print(f"[Module E] Tracking profile preload unavailable: {e}")
            self.tracking_profiles = {}

    def _load_opponent_defense_profiles(self):
        """Load 30-day opponent context from player_game_opponent."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                """
                SELECT team_abbrev,
                       AVG(opp_fg_pct) AS avg_opp_fg_pct,
                       AVG(opp_3p_pct) AS avg_opp_3p_pct,
                       AVG(opp_stl) AS avg_opp_stl,
                       AVG(opp_blk) AS avg_opp_blk,
                       AVG(opp_tov) AS avg_opp_tov
                FROM player_game_opponent
                WHERE game_date >= date('now', '-30 days')
                GROUP BY team_abbrev
                HAVING COUNT(DISTINCT game_date) >= 5
                """
            )
            rows = c.fetchall()
            conn.close()

            self.opponent_profiles = {
                row[0]: {
                    'opp_fg_pct': row[1] or 0.0,
                    'opp_3p_pct': row[2] or 0.0,
                    'opp_stl': row[3] or 0.0,
                    'opp_blk': row[4] or 0.0,
                    'opp_tov': row[5] or 0.0,
                }
                for row in rows
            }
        except Exception as e:
            print(f"[Module E] Opponent profiles unavailable: {e}")
            self.opponent_profiles = {}

    # === SECONDARY PLAYTYPE METHODS (Week 2 Integration) ===
    
    def _load_playtype_thresholds(self):
        """Load playtype thresholds from config file."""
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"⚠️ Warning: Could not load playtype thresholds: {e}")
            return {}
    
    def _get_eligible_playtypes(self, position: str) -> list:
        """
        Get list of playtypes this position can qualify for.
        Implements Week 1's validated position filtering logic.
        """
        return self.POSITION_ELIGIBILITY.get(position, self.POSITION_ELIGIBILITY['UNK'])
    
    def _check_playtype_criteria(self, player_data: dict, playtype: str) -> tuple:
        """
        Check criteria for a playtype. Returns (criteria_met_list, min_required).
        Uses validated v1.2 thresholds from config.
        """
        t = self.playtype_thresholds.get('playtypes', {}).get(playtype, {}).get('criteria', {})
        
        if playtype == 'ISO_SCORER':
            c1 = player_data.get('avg_drives', 0) > t.get('drives_per_game', 6.0)
            c2 = player_data.get('avg_pu_fga', 0) > t.get('pull_up_fga_per_game', 5.0)
            c3 = player_data.get('avg_pu_fga', 0) > player_data.get('avg_cs_fga', 0) * 1.5
            return [c1, c2, c3], 2
            
        elif playtype == 'P&R_HANDLER':
            c1 = player_data.get('avg_drives', 0) > t.get('drives_per_game', 5.0)
            c2 = player_data.get('avg_drives_pass_pct', 0) > t.get('drives_pass_pct', 35.0)
            c3 = player_data.get('avg_pu_fga', 0) > t.get('pull_up_fga_per_game', 3.0)
            return [c1, c2, c3], 2
            
        elif playtype == 'P&R_ROLL_MAN':
            c1 = player_data.get('rim_freq', 0) > t.get('rim_freq', 0.40)
            c2 = player_data.get('avg_cs_fga', 0) >= t.get('catch_shoot_fga_min', 1.5)
            c3 = player_data.get('avg_drives', 0) < t.get('drives_per_game_max', 2.0)
            c4 = player_data.get('avg_pu_fga', 0) < t.get('pull_up_fga_max', 1.5)
            return [c1, c2, c3, c4], 3
            
        elif playtype == 'SPOT_UP':
            c1 = player_data.get('avg_cs_fga', 0) > t.get('catch_shoot_fga_per_game', 4.0)
            c2 = player_data.get('cs_pct', 0) > t.get('catch_shoot_pct', 0.38)
            c3 = player_data.get('avg_cs_3pa', 0) > t.get('catch_shoot_3pa_per_game', 3.5)
            c4 = player_data.get('avg_cs_fga', 0) > player_data.get('avg_pu_fga', 0) * 1.5
            return [c1, c2, c3, c4], 3
            
        elif playtype == 'OFF_BALL_CUTTER':
            c1 = player_data.get('rim_freq', 0) > t.get('rim_freq', 0.45)
            c2 = player_data.get('avg_cs_fga', 0) < t.get('catch_shoot_fga_max', 1.5)
            c3 = player_data.get('avg_drives', 0) < t.get('drives_per_game_max', 1.5)
            c4 = player_data.get('avg_pu_fga', 0) < t.get('pull_up_fga_max', 0.5)
            return [c1, c2, c3, c4], 3
            
        elif playtype == 'TRANSITION':
            c1 = player_data.get('avg_speed', 0) > t.get('avg_speed', 4.8)
            c2 = player_data.get('avg_distance', 0) > t.get('distance_per_game', 1.1)
            c3 = player_data.get('avg_drives', 0) > t.get('drives_per_game', 4.0)
            return [c1, c2, c3], 2
            
        elif playtype == 'PUTBACK':
            c1 = player_data.get('rim_freq', 0) > t.get('rim_freq', 0.55)
            c2 = player_data.get('avg_cs_fga', 0) < t.get('catch_shoot_fga_max', 1.0)
            c3 = player_data.get('avg_drives', 0) < t.get('drives_per_game_max', 0.8)
            c4 = player_data.get('avg_pu_fga', 0) < t.get('pull_up_fga_max', 0.3)
            return [c1, c2, c3, c4], 3
            
        elif playtype == 'POST_UP':
            c1 = player_data.get('rim_freq', 0) > t.get('rim_freq', 0.40)
            c2 = player_data.get('avg_speed', 0) < t.get('avg_speed_max', 4.2)
            c3 = player_data.get('avg_drives', 0) < t.get('drives_per_game_max', 1.5)
            c4 = player_data.get('avg_cs_fga', 0) < t.get('catch_shoot_fga_max', 2.5)
            return [c1, c2, c3, c4], 3
        
        return [], 2
    
    def _calculate_playtype_score(self, player_data: dict, playtype: str) -> float:
        """
        Calculate match score for a playtype (0.0 to 1.0).
        Uses Week 1's validated priority scoring with position bonuses.
        """
        criteria_met, min_required = self._check_playtype_criteria(player_data, playtype)
        
        if len(criteria_met) == 0:
            return 0.0
        
        # Base score: percentage of criteria met
        base_score = sum(criteria_met) / len(criteria_met)
        
        # Apply position bonus
        position = player_data.get('position', 'UNK')
        bonus = self.POSITION_BONUSES.get((playtype, position), 0.0)
        
        final_score = min(1.0, base_score + bonus)
        
        # Only return score if minimum criteria met
        if sum(criteria_met) >= min_required:
            return final_score
        return 0.0
    
    # === SYNERGY DATA MAPPING ===
    SYNERGY_TO_TAG = {
        'ISO': 'ISO_SCORER',
        'TRANSITION': 'TRANSITION',
        'PR_BALL_HANDLER': 'P&R_HANDLER',
        'PR_ROLL_MAN': 'P&R_ROLL_MAN',
        'POST_UP': 'POST_UP',
        'SPOT_UP': 'SPOT_UP',
        'CUT': 'OFF_BALL_CUTTER',
        'PUTBACK': 'PUTBACK',
        'HANDOFF': 'HANDOFF',
        'OFF_SCREEN': 'OFF_SCREEN',
        'OFFSCREEN': 'OFF_SCREEN',
    }

    DEFENSIVE_STYLE_MAP = {
        'DROP_COVERAGE': 'PAINT_PACK',
        'RIM_FORTRESS': 'PAINT_PACK',
        'SWITCH_HEAVY': 'PERIMETER',
        'PERIMETER_FUNNEL': 'FUNNEL',
        'ZONE_FLUID': 'BLITZ',
        'NEUTRAL': 'NEUTRAL'
    }

    def _load_cached_defensive_styles(self) -> bool:
        """Load active defensive schemes from team_scheme_cache if available."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT team_abbr, active_style
                FROM team_scheme_cache
                WHERE scheme_type = 'DEFENSE'
                """
            )
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return False
            for team, style in rows:
                if not style or style == "INSUFFICIENT":
                    self.DEFENSIVE_STYLES[team] = "NEUTRAL"
                else:
                    self.DEFENSIVE_STYLES[team] = style
            return True
        except Exception as e:
            print(f"[Module E] Defensive scheme cache unavailable: {e}")
            return False

    def _load_cached_offensive_styles(self) -> bool:
        """Load active offensive schemes from team_scheme_cache if available."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT team_abbr, active_style
                FROM team_scheme_cache
                WHERE scheme_type = 'OFFENSE'
                """
            )
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return False
            for team, style in rows:
                if not style or style == "INSUFFICIENT" or style == "BALANCED":
                    continue  # Leave BALANCED/empty out so classify_team_offense() falls back to classifier
                self.OFFENSIVE_STYLES[team] = style
            print(f"[Module E] Offensive styles loaded from cache: {len(self.OFFENSIVE_STYLES)} teams")
            return len(self.OFFENSIVE_STYLES) > 0
        except Exception as e:
            print(f"[Module E] Offensive scheme cache unavailable: {e}")
            return False

    def _load_dynamic_defensive_styles(self) -> None:
        """Overlay data-driven defensive styles; keep static mapping as fallback."""
        try:
            classifier = TeamDefensiveClassifier(db_path=str(self.db_path))
            dynamic = classifier.batch_classify_all_teams()
            for team, dyn_style in dynamic.items():
                mapped = self.DEFENSIVE_STYLE_MAP.get(dyn_style, 'NEUTRAL')
                if mapped != 'NEUTRAL':
                    self.DEFENSIVE_STYLES[team] = mapped
        except Exception as e:
            print(f"[Module E] Dynamic defensive styles unavailable: {e}")

    def _get_player_defensive_synergy(self, player_name: str) -> dict:
        """Return defensive synergy percentile/ppp by playtype for a player."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT playtype, percentile, ppp_allowed
                FROM player_defensive_synergy
                WHERE player_name = ?
                  AND season = '2025-26'
                """,
                (player_name,),
            )
            rows = cursor.fetchall()
            conn.close()
            return {
                (pt or '').upper(): {
                    'percentile': perc or 0.0,
                    'ppp_allowed': ppp or 0.0,
                }
                for pt, perc, ppp in rows
            }
        except Exception as e:
            print(f"[Module E] Defensive synergy query error for {player_name}: {e}")
            return {}

    def _get_synergy_playtypes(self, player_name: str, min_freq: float = 5.0) -> list:
        """
        Get official Synergy playtypes from pre-loaded cache.
        Falls back to DB query on cache miss.

        Args:
            player_name: Player name to lookup
            min_freq: Minimum frequency % to qualify (default 5%)

        Note: Applies best practice filter: (poss_per_game * games_played) >= 75
        to ensure statistical significance of playtype data.
        """
        key = _canonical_key(player_name)
        if key in self.synergy_playtypes_cache:
            cached = self.synergy_playtypes_cache[key]
            playtypes = []
            for item in cached:
                if item['frequency'] and item['frequency'] >= min_freq:
                    if item['possession_count'] and item['possession_count'] >= 75:
                        our_tag = self.SYNERGY_TO_TAG.get(item['playtype'])
                        if our_tag:
                            playtypes.append((our_tag, item['frequency'], item['ppp'], 0))
            return playtypes

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT playtype, freq_pct, ppp, percentile
                FROM player_synergy_playtypes
                WHERE player_name = ?
                AND season = '2025-26'
                AND freq_pct >= ?
                AND (poss_per_game * games_played) >= 75
                ORDER BY freq_pct DESC
                LIMIT 4
            """, (player_name, min_freq))

            results = cursor.fetchall()
            conn.close()

            playtypes = []
            for row in results:
                synergy_tag, freq, ppp, percentile = row
                our_tag = self.SYNERGY_TO_TAG.get(synergy_tag)
                if our_tag:
                    playtypes.append((our_tag, freq, ppp, percentile))

            return playtypes

        except Exception as e:
            if self.debug_log:
                print(f"   [CAL] Synergy lookup error: {e}")
            return []
    
    def _select_top_playtypes(self, player_data: dict) -> tuple:
        """
        HYBRID APPROACH: Select top 1-2 secondary playtypes for a player.
        
        Priority:
        1. Synergy ground truth (if available, >=5% freq)
        2. Fall back to tracking-based estimation
        3. Apply position filtering to both
        
        Returns:
            (primary_playtype, secondary_playtype) - secondary may be None
        """
        position = player_data.get('position', 'UNK')
        player_name = player_data.get('name', player_data.get('player_name', ''))
        
        # Step 1: Try Synergy ground truth first
        synergy_data = self._get_synergy_playtypes(player_name)
        
        if synergy_data:
            # Use Synergy data - filter by position eligibility
            eligible = self._get_eligible_playtypes(position)
            
            valid_tags = []
            for tag, freq, ppp, percentile in synergy_data:
                # Skip if position doesn't allow this playtype
                if tag not in eligible:
                    continue
                valid_tags.append(tag)
                if len(valid_tags) >= 2:
                    break
            
            if valid_tags:
                primary = valid_tags[0]
                secondary = valid_tags[1] if len(valid_tags) > 1 else None
                return primary, secondary
        
        # Step 2: Fall back to tracking-based estimation (Week 1 logic)
        eligible = self._get_eligible_playtypes(position)
        
        # Calculate match scores for eligible playtypes
        scores = {}
        for pt in eligible:
            score = self._calculate_playtype_score(player_data, pt)
            if score > 0:
                scores[pt] = score
        
        # Select top 1-2 tags based on thresholds
        sorted_tags = sorted(scores.items(), key=lambda x: -x[1])
        
        primary = sorted_tags[0][0] if len(sorted_tags) > 0 and sorted_tags[0][1] >= self.PRIMARY_THRESHOLD else None
        secondary = sorted_tags[1][0] if len(sorted_tags) > 1 and sorted_tags[1][1] >= self.SECONDARY_THRESHOLD else None
        
        return primary, secondary
    
    def _get_tracking_stats(self, player_name_or_id: str, days: int = 60) -> dict:
        """
        Get tracking stats for a player from pre-loaded cache.
        Uses PlayerIDResolver to handle accents and ID changes.
        Returns empty dict if not found.
        """
        try:
            try:
                canonical_id = self.id_resolver.resolve_to_canonical_id(player_name_or_id)
                player_info = self.id_resolver.get_player_info(canonical_id)
                canonical_name = player_info.get('full_name', player_name_or_id)
            except ValueError:
                return {}

            key = _canonical_key(canonical_name)
            if key in self.tracking_stats_cache:
                cached = self.tracking_stats_cache[key]
                if cached.get('games', 0) >= 3:
                    cached_copy = dict(cached)
                    if player_info.get('position'):
                        cached_copy['position'] = player_info['position']
                    return cached_copy

            tracking_stats = dict(self.tracking_profiles.get(canonical_name, {}))
            if not tracking_stats:
                return {}

            if tracking_stats.get('tracking_games', 0) < 3:
                return {}

            shot_row = self.shot_quality_cache.get(_canonical_key(canonical_name))
            if shot_row:
                tracking_stats['rim_freq'] = shot_row.get('rim_freq', 0)
                tracking_stats['corner_3_freq'] = shot_row.get('corner_3_freq', 0)

            if player_info.get('position'):
                tracking_stats['position'] = player_info['position']

            return tracking_stats

        except Exception as e:
            if self.debug_log:
                print(f"   [CAL] Tracking stats error: {e}")
            return {}

    def _get_shot_difficulty_stats(self, player_name_or_id: str, days: int = 60) -> dict:
        """
        Get shot difficulty stats for a player from the database.
        """
        try:
            canonical_id = self.id_resolver.resolve_to_canonical_id(player_name_or_id)
            player_info = self.id_resolver.get_player_info(canonical_id)
            canonical_name = player_info.get('full_name', player_name_or_id)

            profile = self.tracking_profiles.get(canonical_name, {})
            if not profile or profile.get('shot_difficulty_games', 0) < 3:
                return {}

            stats = {
                'avg_contested_fga': profile.get('avg_contested_fga', 0),
                'avg_tight_fga': profile.get('avg_tight_fga', 0),
                'avg_open_fga': profile.get('avg_open_fga', 0),
                'avg_wide_open_fga': profile.get('avg_wide_open_fga', 0),
                'avg_defender_dist': profile.get('avg_defender_dist', 0),
                'shot_difficulty_games': profile.get('shot_difficulty_games', 0)
            }
            return stats
        except Exception as e:
            if self.debug_log:
                print(f"   [CAL] Shot difficulty stats error for {player_name_or_id}: {e}")
            return {}

    def _assign_secondary_playtypes(self, p, tracking_data, synergy_data):
        """
        Assign up to 2 secondary playtypes using Synergy-led hybrid scoring.
        If Synergy data exists: 70% Synergy + 30% tracking proxy.
        Else: 100% tracking fallback.
        """
        drives = tracking_data.get('avg_drives', 0)
        cs_fga = tracking_data.get('avg_cs_fga', 0)
        cs_pct = tracking_data.get('cs_pct', 0)
        pu_fga = tracking_data.get('avg_pu_fga', 0)
        speed = tracking_data.get('avg_speed', 0)
        distance = tracking_data.get('avg_distance', 0)
        
        ast = p.get('base_ast', 0)
        # Calculate approximate usage if not present
        fga = p.get('base_fga', 0)
        fta = p.get('base_fta', 0)
        tov = p.get('base_tov', 0)
        mins = p.get('base_min', 1)
        usg = p.get('base_usg', 0)
        if usg == 0 and mins > 0:
             usg = ((fga + 0.44*fta + tov)/mins)/2.1
             
        oreb = p.get('base_oreb', 0)
        tpm = p.get('base_3pm', 0)
        rim_freq = tracking_data.get('rim_freq', 0)
        rim_fg_pct = p.get('pbp_rim_fg_pct', 0.60)
        paint_pts = p.get('base_pts', 0) * 0.45
        team_pace = p.get('team_pace', 100)
        rim_fga = p.get('base_fga', 0) * rim_freq if rim_freq > 0 else 0
        position = p.get('position', 'UNK')
        if position in ('PG', 'SG'):
            position = 'G'
        elif position in ('SF', 'PF'):
            position = 'F'
        elif position in ('C',):
            position = 'C'
        eligible = set(self._get_eligible_playtypes(position))

        synergy_freq = {}
        if isinstance(synergy_data, dict):
            for tag, value in synergy_data.items():
                if isinstance(value, tuple):
                    synergy_freq[tag] = float(value[0] or 0.0)
                else:
                    synergy_freq[tag] = float(value or 0.0)

        def _bool_score(criteria):
            if not criteria:
                return 0.0
            return sum(1 for c in criteria if c) / len(criteria)

        def _ratio(value, threshold):
            if threshold <= 0:
                return 0.0
            return min(1.0, (value or 0.0) / threshold)

        definitions = {
            'ISO_SCORER': {
                'synergy_tag': 'ISO_SCORER', 'synergy_thr': 8.0,
                'tracking': _bool_score([drives > 8, pu_fga > 4.5, usg > 0.28]),
            },
            'P&R_HANDLER': {
                'synergy_tag': 'P&R_HANDLER', 'synergy_thr': 12.0,
                'tracking': _bool_score([drives > 5, ast > 6.0, cs_fga < pu_fga]),
            },
            'P&R_ROLL_MAN': {
                'synergy_tag': 'P&R_ROLL_MAN', 'synergy_thr': 8.0,
                'tracking': _bool_score([rim_freq > 0.40, cs_fga > pu_fga, ast < 3.0]),
            },
            'SPOT_UP': {
                'synergy_tag': 'SPOT_UP', 'synergy_thr': 12.0,
                'tracking': _bool_score([cs_fga > 3.5, cs_pct > 0.38, tpm > 1.5]),
            },
            'OFF_BALL_CUTTER': {
                'synergy_tag': 'OFF_BALL_CUTTER', 'synergy_thr': 8.0,
                'tracking': _bool_score([rim_fg_pct > 0.65, cs_fga > pu_fga, drives < 4]),
            },
            'TRANSITION': {
                'synergy_tag': 'TRANSITION', 'synergy_thr': 10.0,
                'tracking': _bool_score([speed > 4.5, distance > 2.3, team_pace > 102]),
            },
            'PUTBACK': {
                'synergy_tag': 'PUTBACK', 'synergy_thr': 5.0,
                'tracking': _bool_score([oreb > 2.2, rim_freq > 0.45, rim_fga > 4]),
            },
            'POST_UP': {
                'synergy_tag': 'POST_UP', 'synergy_thr': 8.0,
                'tracking': _bool_score([paint_pts > 10, rim_freq > 0.40, speed < 4.0]),
            },
            'HANDOFF': {
                'synergy_tag': 'HANDOFF', 'synergy_thr': 6.0,
                'tracking': _bool_score([cs_fga > 2.5, speed > 4.0, drives < 5]),
            },
            'OFF_SCREEN': {
                'synergy_tag': 'OFF_SCREEN', 'synergy_thr': 5.0,
                'tracking': _bool_score([cs_fga > 3.0, distance > 2.5, tpm > 1.2]),
            },
        }

        scored = []
        for playtype, spec in definitions.items():
            if playtype not in eligible:
                continue
            sy_tag = spec['synergy_tag']
            s_freq = synergy_freq.get(sy_tag, 0.0)
            s_score = _ratio(s_freq, spec['synergy_thr'])
            t_score = spec['tracking']
            if s_freq > 0:
                score = (0.7 * s_score) + (0.3 * t_score)
            else:
                score = t_score
            if score >= 0.60:
                scored.append((playtype, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [tag for tag, _ in scored[:2]]

    def calibrate_player(self, player_packet, yak_report, use_synergy=True):
        calibrated = player_packet.copy()
        if 'notes' not in calibrated: calibrated['notes'] = ""

        # Extract WOWY confidence for boost weighting (Phase 6.3)
        wowy_confidence = player_packet.get('wowy_confidence', None)

        # Preserve cross-module keys for downstream (Module F)
        calibrated['games_since_return'] = player_packet.get('games_since_return', None)
        calibrated['effective_starter'] = player_packet.get('effective_starter', False)

        # If effective_starter flag set but is_starter not, elevate calibration
        if calibrated.get('effective_starter') and not calibrated.get('is_starter'):
            calibrated['is_starter'] = True

        # INITIALIZE PROJECTION KEYS from BASE KEYS if missing
        # This ensures subsequent _boost_stat calls work correctly
        mappings = {
            'base_pts': 'proj_pts',
            'base_ast': 'proj_ast',
            'base_reb': 'proj_reb',
            'base_fga': 'proj_fga',
            'base_fg3a': 'proj_3pa',
            'base_fta': 'proj_fta',
            'base_3pm': 'proj_3pm',
            'base_min': 'proj_min',
            'base_stl': 'proj_stl',
            'base_blk': 'proj_blk',
            'base_tov': 'proj_tov'
        }
        for base_k, proj_k in mappings.items():
            if base_k in calibrated and proj_k not in calibrated:
                calibrated[proj_k] = calibrated[base_k]

        # 0. FETCH POSITION DATA (Week 2 Enhancement - needed for archetype assignment)
        player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))

        # Try to get position from PlayerIDResolver
        try:
            player_info = self.id_resolver.get_player_info(player_name)
            if player_info and player_info.get('position') and player_info['position'] != 'UNK':
                calibrated['position'] = player_info['position']
        except (ValueError, Exception):
            # Player not found or error - will use 'UNK' position
            pass

        # Wire archetype context from loaded data tables (Step 8)
        hustle = self.hustle_profiles.get(player_name, {})
        defense = self.defense_profiles.get(player_name, {})
        if 'contested_reb_pct' not in calibrated:
            calibrated['contested_reb_pct'] = hustle.get('contested_reb_pct', 0.5)
        if 'def_diff_vs_screen' not in calibrated:
            calibrated['def_diff_vs_screen'] = defense.get('def_diff_vs_screen', 0.0)
        if 'def_diff_vs_iso' not in calibrated:
            calibrated['def_diff_vs_iso'] = defense.get('def_diff_vs_iso', 0.0)
        if 'def_diff_pct' not in calibrated:
            calibrated['def_diff_pct'] = defense.get('def_diff_pct', 0.0)
        if 'def_freq_pct' not in calibrated:
            calibrated['def_freq_pct'] = defense.get('def_freq_pct', 0.0)
        if 'def_dfga' not in calibrated:
            calibrated['def_dfga'] = defense.get('def_dfga', 0.0)
        if 'def_position' not in calibrated:
            calibrated['def_position'] = defense.get('def_position', 'UNK')
        if 'def_distance_miles' not in calibrated:
            calibrated['def_distance_miles'] = defense.get('def_distance_miles', 0.0)

        # 1. ASSIGN UNIFIED ARCHETYPE (returns archetype + synergy dict)
        archetype, synergy_dict, def_syn = self._assign_unified_archetype(calibrated)

        if archetype:
            calibrated['archetype'] = archetype
            calibrated['notes'] += f" [{archetype}]"

            # Store synergy modifiers for later application
            calibrated['synergy_modifiers'] = synergy_dict

            # Add archetype confidence from player_type_profiles (G2)
            profile = self.player_type_profiles.get(_canonical_key(player_name), {})
            archetype_confidence = 'HIGH' if profile.get('archetype_validated') else 'LOW'
            calibrated['archetype_confidence'] = archetype_confidence

        # --- Defensive tag assignment (Phase 7.9.5 — hybrid off/def system) ---
        def_stl = float(calibrated.get('base_stl', 0) or 0)
        def_blk = float(calibrated.get('base_blk', 0) or 0)
        def_diff = float(calibrated.get('def_diff_pct', 0) or 0.0)
        def_freq = float(calibrated.get('def_freq_pct', 0) or 0.0)
        position = str(calibrated.get('position', 'UNK') or 'UNK').upper()

        # Extract def_syn percentiles (empty dict if no synergy data)
        pr_roll_def = (def_syn.get('PR_ROLL_MAN') or {}).get('percentile', 0.0)
        post_def    = (def_syn.get('POST_UP')    or {}).get('percentile', 0.0)
        iso_def     = (def_syn.get('ISO')        or {}).get('percentile', 0.0)
        spot_def    = (def_syn.get('SPOT_UP')    or {}).get('percentile', 0.0)

        # Speed/distance from tracking (use 0.0 defaults safely)
        speed        = float(calibrated.get('speed', 0.0) or 0.0)
        def_distance = float(calibrated.get('def_distance', 0.0) or 0.0)

        # Count strong defensive synergy types (percentile >= 70)
        strong_def_tags = sum(1 for v in def_syn.values()
                              if isinstance(v, dict) and v.get('percentile', 0) >= 70)

        # Assign tag — priority order: RIM_GUARDIAN > PERIMETER_HAWK > SWITCHABLE_ANCHOR >
        #                               HUSTLE_DISRUPTOR > WEAK_LINK > None
        if ((def_blk >= 1.1 and position in ('F', 'C', 'UNK'))
                or (pr_roll_def >= 75 and post_def >= 70)):
            calibrated['defensive_tag'] = 'RIM_GUARDIAN'
        elif ((def_stl >= 1.2 and position in ('G', 'F', 'UNK'))
                or (iso_def >= 75 and spot_def >= 70)):
            calibrated['defensive_tag'] = 'PERIMETER_HAWK'
        elif (((def_stl + def_blk) >= 2.0 and speed > 3.9) or strong_def_tags >= 3):
            calibrated['defensive_tag'] = 'SWITCHABLE_ANCHOR'
        elif (def_stl > 1.15 or (def_stl > 0.9 and def_distance > 2.3)):
            calibrated['defensive_tag'] = 'HUSTLE_DISRUPTOR'
        elif ((def_diff > 1.5 and def_freq > 8.0)
                or (def_diff > 2.0 and (def_stl + def_blk) < 1.0)):
            calibrated['defensive_tag'] = 'WEAK_LINK'
        else:
            calibrated['defensive_tag'] = None

        # Ensure secondary playtypes are always populated for matchup layer
        if not calibrated.get('secondary_playtypes'):
            tracking_data = self._get_tracking_stats(player_name)
            calibrated['secondary_playtypes'] = self._assign_secondary_playtypes(
                calibrated,
                tracking_data if tracking_data else {},
                synergy_dict,
            )

        # 3. NEWS CALIBRATION
        status = yak_report.get('status', 'ACTIVE')
        if status == "OUT":
            self._zero_out(calibrated)
            calibrated['notes'] += " | Official OUT"
            return calibrated
        elif status == "MINUTES_LIMIT":
            minutes_limit = player_packet.get('minutes_limit')
            if minutes_limit:
                base_min = calibrated.get('MIN', calibrated.get('proj_min', 30))
                scale_factor = min(minutes_limit / base_min, 1.0) if base_min > 0 else 0.75
                scale_factor = max(0.50, min(0.90, scale_factor))
                self._apply_factor(calibrated, scale_factor)
                calibrated['notes'] += f" | MIN_LIMIT:{minutes_limit:.0f}"
            else:
                self._apply_factor(calibrated, self.ADJUSTMENT_RULES["MINUTES_LIMIT"])
                calibrated['notes'] += f" | 15-min Update: Limit Applied"

        # ROLE_CHANGE: Starter elevation or bench demotion
        elif status == "ROLE_CHANGE":
            starter_info = self.get_starter_status(
                calibrated['PLAYER_NAME'],
                calibrated.get('TEAM_ABBREVIATION')
            )

            if starter_info:
                base_min = calibrated.get('MIN', 28)

                if starter_info['is_starter'] and starter_info['depth_order'] == 1:
                    # Promoted to starter: +8 minutes
                    min_adjustment = 1 + (8 / base_min)
                    volume_stats = ['proj_fga', 'proj_3pa', 'proj_fta', 'proj_reb', 'proj_ast', 'proj_stl', 'proj_blk', 'proj_tov']
                    for stat in volume_stats:
                        self._boost_stat(calibrated, stat, min_adjustment)
                    calibrated['notes'] += " | 📈 Elevated to Starter (+8 min)"

                elif starter_info['depth_order'] >= 2:
                    # Demoted to bench: -8 minutes
                    min_adjustment = 1 - (8 / base_min)
                    volume_stats = ['proj_fga', 'proj_3pa', 'proj_fta', 'proj_reb', 'proj_ast', 'proj_stl', 'proj_blk', 'proj_tov']
                    for stat in volume_stats:
                        self._boost_stat(calibrated, stat, min_adjustment)
                    calibrated['notes'] += " | 📉 Moved to Bench (-8 min)"

        # 3.5 SCHEDULE FATIGUE (Phase 4 Integration - Jan 21, 2026)
        if config.MODIFIER_FLAGS.get('fatigue_e', True):
            self._apply_fatigue_adjustments(calibrated, yak_report)

        # Pre-fetch odds dict (needed by 3.6 and 4)
        odds = calibrated.get('odds', {})
        total = float(odds.get('total', 0)) if odds.get('total') else 0
        spread = abs(float(odds.get('spread', 0))) if odds.get('spread') else 0

        # 3.6 TEAM TOTALS MODIFIER (Phase 8.18)
        if getattr(config, 'USE_TEAM_TOTALS_MODIFIER', False):
            team_total_home = odds.get('team_total_home')
            team_total_away = odds.get('team_total_away')
            home_team = odds.get('home_team', '')
            player_team = calibrated.get('team', player_packet.get('TEAM_ABBREVIATION', ''))
            
            team_total = None
            if player_team and home_team:
                is_home = player_team == home_team
                if is_home and team_total_home:
                    try:
                        team_total = float(team_total_home)
                    except (ValueError, TypeError):
                        team_total = None
                elif not is_home and team_total_away:
                    try:
                        team_total = float(team_total_away)
                    except (ValueError, TypeError):
                        team_total = None
            
            if team_total and team_total > 0:
                ratio = team_total / (config.LEAGUE_AVG_TOTAL / 2)
                ratio = max(0.93, min(1.07, ratio))
                self._apply_factor(calibrated, ratio)
                calibrated['notes'] += f" | TeamTotal:{team_total:.1f}"
            elif total > 0 and spread > 0:
                implied_team_total = (total + spread) / 2 if player_team != home_team else (total - spread) / 2
                ratio = implied_team_total / (config.LEAGUE_AVG_TOTAL / 2)
                ratio = max(0.93, min(1.07, ratio))
                self._apply_factor(calibrated, ratio)
                calibrated['notes'] += f" | ImpliedTT:{implied_team_total:.1f}"

        # 4. GAME SCRIPT
        # (odds/total/spread already extracted above in section 3.6 pre-fetch)
        # REMOVED: Blowout tax consolidated to Module F (smart blowout_tax.py)
        # Old logic: if spread > 12.5 → -6% for starters
        # New logic: Context-aware (favorite/underdog, starter/bench) in Module F
        
        if config.MODIFIER_FLAGS.get('game_total', True):
            if total > 238.0: self._apply_factor(calibrated, 1.03)
            elif total > 0 and total < 218.0: self._apply_factor(calibrated, config.GAME_TOTAL_LOW_FACTOR)

        _scoring_env = config.get_scoring_environment()
        _over_rate = _scoring_env.get('over_hit_rate_14d', 0.50)
        if 0 < _over_rate < config.SCORING_ENV_OVER_THRESHOLD:
            self._apply_factor(calibrated, config.SCORING_ENV_DAMPENER)

        # 5. MATCHUP LOGIC (Primary Archetypes)
        opponent = calibrated.get('opponent', 'UNK') 
        def_style = self.DEFENSIVE_STYLES.get(opponent, "NEUTRAL")
        
        # Get team offensive style
        player_team = calibrated.get('team', player_packet.get('TEAM_ABBREVIATION', ''))
        team_offense = self.classify_team_offense(player_team)
        
        # Apply offensive style matchup
        self._apply_offensive_style_boost(calibrated, team_offense, def_style)

        # === NEW 16-ARCHETYPE MATCHUP MATRIX ===
        # Phase 6.3: Key boosts use _boost_stat_with_confidence for WOWY weighting
        trans_freq_primary = calibrated.get('synergy_modifiers', {}).get('TRANSITION', (0, 0))[0]

        if config.MODIFIER_FLAGS.get('matchup_scheme', True):
          if archetype == "HELIOCENTRIC_MAESTRO":
            if def_style == "BLITZ":
                self._boost_stat_with_confidence(calibrated, 'proj_ast', 1.18, wowy_confidence)
                self._boost_stat_with_confidence(calibrated, 'proj_pts', 0.92, wowy_confidence)
                self._boost_stat(calibrated, 'proj_tov', 1.10)
                calibrated['notes'] += " | Maestro vs Trap (Pass-First)"
            elif def_style == "PAINT_PACK":
                self._boost_stat_with_confidence(calibrated, 'proj_ast', 1.08, wowy_confidence)
                calibrated['notes'] += " | P&R Drop Edge"

          elif archetype == "SLASHING_CREATOR":
            if def_style == "FUNNEL":
                funnel_mod = 1.08 if trans_freq_primary >= 14.0 else 1.02
                self._boost_stat_with_confidence(calibrated, 'proj_pts', funnel_mod, wowy_confidence)
                calibrated['notes'] += " | Transition Chaos" if funnel_mod > 1.03 else " | Funnel Minor Edge"
            elif def_style == "PAINT_PACK":
                self._boost_stat_with_confidence(calibrated, 'proj_pts', 0.95, wowy_confidence)
                self._boost_stat_with_confidence(calibrated, 'proj_fta', 0.92, wowy_confidence)
                calibrated['notes'] += " | Paint Congestion"

          elif archetype == "JUMBO_FACILITATOR":
            if def_style == "PERIMETER":
                self._boost_stat_with_confidence(calibrated, 'proj_ast', 1.12, wowy_confidence)
                self._boost_stat_with_confidence(calibrated, 'proj_reb', 1.15, wowy_confidence)
                calibrated['notes'] += " | Size Mismatch Hub"

          elif archetype == "SNIPER_ELITE":
            if def_style == "PAINT_PACK":
                self._boost_stat_with_confidence(calibrated, 'proj_3pm', 1.12, wowy_confidence)
                calibrated['notes'] += " | Spot-Up vs Helpers"
            elif def_style == "PERIMETER":
                self._boost_stat_with_confidence(calibrated, 'proj_3pm', 0.92, wowy_confidence)
                calibrated['notes'] += " | Sniper Tax vs Perimeter"

          elif archetype == "TWO_LEVEL_SCORER":
            if def_style == "PERIMETER":
                self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.08, wowy_confidence)
                calibrated['notes'] += " | Mid-Range Mismatch"

          elif archetype == "WARRIOR_BIG":
            if def_style == "PERIMETER":
                self._boost_stat_with_confidence(calibrated, 'proj_reb', 1.20, wowy_confidence)
                self._boost_stat_with_confidence(calibrated, 'proj_oreb', 1.20, wowy_confidence)
                calibrated['notes'] += " | Warrior Boards vs Small Ball"
            elif def_style == "PAINT_PACK":
                self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.15, wowy_confidence)
                self._boost_stat(calibrated, 'proj_fg_pct', 1.10)
                calibrated['notes'] += " | Roll Man vs Drop"

          elif archetype == "STRETCH_BIG":
            if def_style == "PAINT_PACK":
                self._boost_stat_with_confidence(calibrated, 'proj_3pm', 1.15, wowy_confidence)
                self._boost_stat_with_confidence(calibrated, 'proj_3pa', 1.15, wowy_confidence)
                calibrated['notes'] += f" | {opponent} Paint Pack Edge"

          elif archetype == "ROLL_MAN":
            if def_style == "PERIMETER":
                self._boost_stat_with_confidence(calibrated, 'proj_oreb', 1.30, wowy_confidence)
                self._boost_stat_with_confidence(calibrated, 'proj_reb', 1.15, wowy_confidence)
                calibrated['notes'] += " | Size Advantage (O-Boards)"
            elif def_style == "PAINT_PACK":
                self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.12, wowy_confidence)
                calibrated['notes'] += " | Roll Man vs Drop"

          elif archetype == "CUTTER_SPECIALIST":
            if def_style == "PERIMETER":
                self._boost_stat(calibrated, 'proj_pts', 1.12)
                calibrated['notes'] += " | Cutter vs Small Ball"
            elif def_style == "BLITZ":
                self._boost_stat(calibrated, 'proj_pts', 1.12)
                calibrated['notes'] += " | Cutting Lanes"

          elif archetype == "FACILITATOR":
            if def_style == "PAINT_PACK":
                self._boost_stat(calibrated, 'proj_ast', 1.08)
                calibrated['notes'] += " | Playmaking vs Drop"

          elif archetype == "CONNECTOR":
            if def_style == "PAINT_PACK":
                self._boost_stat(calibrated, 'proj_ast', 1.05)
                calibrated['notes'] += " | Connector vs Pack"

          elif archetype == "ENERGY_BIG":
            if def_style == "PERIMETER":
                self._boost_stat(calibrated, 'proj_reb', 1.08)
                calibrated['notes'] += " | Energy Big Boards"

          # Defensive tag matchup boosts (independent of offensive archetype)
          d_tag = calibrated.get('defensive_tag')
          if d_tag == 'RIM_GUARDIAN':
            if def_style == "FUNNEL":
                self._boost_stat(calibrated, 'proj_blk', 1.12)
                calibrated['notes'] += " | Rim Guardian vs Funnel"
            elif def_style == "BLITZ":
                self._boost_stat(calibrated, 'proj_blk', 1.08)
                self._boost_stat(calibrated, 'proj_reb', 1.05)
                calibrated['notes'] += " | Rim Guardian Help Side"
          if d_tag == 'PERIMETER_HAWK':
            if def_style == "PERIMETER":
                self._boost_stat(calibrated, 'proj_stl', 1.02)
                calibrated['notes'] += " | Hawk Passing Lanes"
          if d_tag == 'SWITCHABLE_ANCHOR':
            if def_style == "BLITZ":
                self._boost_stat(calibrated, 'proj_stl', 1.02)
                self._boost_stat(calibrated, 'proj_blk', 1.04)
                calibrated['notes'] += " | Switchable Pressure"
          if d_tag == 'HUSTLE_DISRUPTOR':
            if def_style == "FUNNEL":
                self._boost_stat(calibrated, 'proj_stl', 1.02)
                calibrated['notes'] += " | Hustle vs Funnel"

        # B1: Apply DVP data-driven modulation on top of hardcoded boosts
        if archetype and opponent and def_style:
            dvp_mod = self._get_dvp_modulator(opponent, archetype, def_style)
            confidence_scale = 1.0 if calibrated.get('archetype_confidence') == 'HIGH' else 0.70
            if dvp_mod != 1.0 or confidence_scale < 1.0:
                dvp_log = f"DVP:{dvp_mod:.2f}x" if dvp_mod != 1.0 else ""
                conf_log = f"_conf:{confidence_scale:.0%}" if confidence_scale < 1.0 else ""
                calibrated['notes'] += f" | {dvp_mod * confidence_scale:.2f}x{conf_log}"

        # Apply archetype-specific synergy modifiers
        synergy_dict = calibrated.get('synergy_modifiers', {})
        if synergy_dict:
            self._apply_archetype_synergy_weights(calibrated, archetype, synergy_dict)

        # 6. SECONDARY PLAYTYPE MATCHUPS (Week 2 - 14 Total Modifiers)
        # Extracted to separate method for Phase 3 implementation
        # Phase 6.3: Pass wowy_confidence for BENEFICIARY weighting
        if config.MODIFIER_FLAGS.get('secondary_playtype', True):
            self._apply_secondary_playtype_matchups(calibrated, def_style, wowy_confidence)
        if config.MODIFIER_FLAGS.get('weak_link_boost', True):
            self._apply_opponent_weak_link_boost(calibrated, opponent, def_style)

        # 6b. CLUTCH PERFORMER BOOST (Phase 7.4)
        # Apply +3% PTS boost for players on clutch-strong teams in close games
        spread = calibrated.get('spread', 10.0)
        try:
            spread = float(spread)
        except (ValueError, TypeError):
            spread = 10.0
        if config.MODIFIER_FLAGS.get('clutch_boost', True):
            self._apply_clutch_boost(calibrated, spread)

        # 6c. SPEED/FATIGUE CONTEXT (Sprint 1 - Dormant Data Activation)
        # Guards with high speed get hustle boosts; declining speed signals fatigue
        if config.MODIFIER_FLAGS.get('speed_fatigue', True):
            self._apply_speed_fatigue_context(calibrated)

        # 6d. TOUCHES CONTEXT (Sprint 2 - Dormant Data Activation)
        # Quick decision-makers, paint presence, post-ups, efficient scorers
        if config.MODIFIER_FLAGS.get('touches_context', True):
            self._apply_touches_context(calibrated, def_style)

        # 6e. LEVERAGE GAME STATE CONTEXT (Sprint 3)
        # Pace by game state, crunch time usage, OREB adjustments
        if config.MODIFIER_FLAGS.get('leverage_context', True):
            self._apply_leverage_context(calibrated, spread)

        # 6.5. SYNERGY PLAYTYPE EFFICIENCY (Phase 1 Integration - Jan 21, 2026)
        if use_synergy:
            # Apply PPP-based efficiency adjustments, defensive matchup adjustments, and assist profile mods
            self._apply_synergy_ppp_efficiency(calibrated, opponent)
            self._apply_defensive_diff_adjustment(calibrated, opponent)
            self._apply_drives_assist_profile(calibrated)

        # 7. PBP SHOT QUALITY
        # Using 2025-26 Season Data from scripts/sync_pbp_totals.py
        pbp_sq = calibrated.get('pbp_shot_quality', 0.53)
        rim_freq = calibrated.get('pbp_rim_freq', 0.0)
        corner_freq = calibrated.get('pbp_corner3_freq', 0.0)

        if config.MODIFIER_FLAGS.get('pbp_shot_quality', True):
            # A) Efficiency Boost for High Quality Shot Takers
            # League Avg SQ is ~0.53. Players > 0.55 get easy looks.
            if pbp_sq > 0.55:
                self._boost_stat(calibrated, 'proj_pts', 1.04)
                self._boost_stat(calibrated, 'proj_fg_pct', 1.03)
                calibrated['notes'] += " | High SQ Efficiency"
            elif pbp_sq < 0.48:
                # Bad shot selection penalty (Only hit efficiency/points, not hustle stats)
                self._boost_stat(calibrated, 'proj_pts', 0.96)
                self._boost_stat(calibrated, 'proj_fg_pct', 0.96)
                calibrated['notes'] += " | Low SQ Tax"

            # B) Slasher Validation (Rim Pressure)
            # If Rim Freq > 40%, they are legitimate paint threats -> Foul magnets
            if rim_freq > 0.40:
                self._boost_stat(calibrated, 'proj_fta', 1.15)
                if archetype == "SLASHING_CREATOR":
                    calibrated['notes'] += " | Confirmed Rim Pressure"
            elif rim_freq < 0.15:
                self._boost_stat(calibrated, 'proj_fta', 0.92)
                calibrated['notes'] += " | Low Rim Pressure"

            # C) Corner Specialist Logic
            # Corner 3s are counter to 'PAINT_PACK' defenses
            if corner_freq > 0.20 and def_style == "PAINT_PACK":
                self._boost_stat(calibrated, 'proj_3pm', 1.12)
                calibrated['notes'] += " | Corner Specialist vs Pack"
            elif corner_freq < 0.05:
                self._boost_stat(calibrated, 'proj_3pm', 0.95)
                calibrated['notes'] += " | Low Corner Volume"

        # === NEW: FT% SHOOTING TOUCH INDICATOR ===
        # Research: Free throw ability indicates shooting touch (ShotQualityBets)
        # Elite FT shooters (>85%) rarely regress as jump shooters
        ft_pct = calibrated.get('base_ft_pct', 0)

        if ft_pct > 0.85:
            # Elite FT shooter = elite shooting touch → boost 3PM
            self._boost_stat(calibrated, 'proj_3pm', 1.05)
            calibrated['notes'] += " | Elite Touch"
            self._log_adjustment(player_name, 'FT_TOUCH', 1.05, 
                f"Elite FT: {ft_pct:.1%}")
        elif ft_pct < 0.65 and ft_pct > 0:
            # Poor FT% = poor touch → regress 3PT expectations
            self._boost_stat(calibrated, 'proj_3pm', 0.95)
            calibrated['notes'] += " | Poor Touch"
            self._log_adjustment(player_name, 'FT_TOUCH', 0.95, 
                f"Poor FT: {ft_pct:.1%}")
        # === END FT% SHOOTING TOUCH ===

        # === NEW: SHOT CREATION SPLIT ===
        # Research: Off-dribble 3s made ~4% less often than catch-and-shoot (ShotQualityBets)
        # Use tracking data to adjust expectations based on shot creation type
        tracking_data = self._get_tracking_stats(player_name)

        if tracking_data:
            cs_fga = tracking_data.get('avg_cs_fga', 0)
            pu_fga = tracking_data.get('avg_pu_fga', 0)
            
            if cs_fga > 0 and pu_fga > 0:
                total_3s = cs_fga + pu_fga
                shot_creation_ratio = pu_fga / total_3s
                
                if shot_creation_ratio > 0.65:
                    # Pull-up dominant = off-dribble shooter (harder shots)
                    self._boost_stat(calibrated, 'proj_3pm', config.SHOT_CREATION_PULLUP_TAX)
                    calibrated['notes'] += " | Off-Dribble 3s"
                    self._log_adjustment(player_name, 'SHOT_CREATION', config.SHOT_CREATION_PULLUP_TAX, 
                        f"Pull-up: {shot_creation_ratio:.0%} of 3s")
                elif shot_creation_ratio < 0.25:
                    # Catch-and-shoot dominant = easier shots
                    self._boost_stat(calibrated, 'proj_3pm', 1.03)
                    calibrated['notes'] += " | Spot-Up 3s"
                    self._log_adjustment(player_name, 'SHOT_CREATION', 1.03, 
                        f"Catch-shoot: {1-shot_creation_ratio:.0%} of 3s")
        # === END SHOT CREATION SPLIT ===

        # === NEW: SHOT DIFFICULTY MODIFIER ===
        self._apply_shot_difficulty_modifier(calibrated)
        # === END SHOT DIFFICULTY MODIFIER ===

        # === NEW: OPPONENT CONTEXT MODIFIER ===
        self._apply_opponent_context_modifiers(calibrated)
        # === END OPPONENT CONTEXT MODIFIER ===

        # === 8. NUANCE CHECKS ===
        # Westbrook/Giddey Rule: Guards who crash boards
        if archetype in ["FACILITATOR", "GENERALIST", "JUMBO_FACILITATOR"] and calibrated.get('base_reb', 0) > 5.5:
            self._boost_stat(calibrated, 'proj_reb', 1.10)

        # --- GLOBAL MODIFIER CAP ---
        stat_pairs = [
            ('proj_pts', 'base_pts'),
            ('proj_reb', 'base_reb'),
            ('proj_ast', 'base_ast'),
            ('proj_3pm', 'base_3pm'),
            ('proj_stl', 'base_stl'),
            ('proj_blk', 'base_blk'),
            ('proj_oreb', 'base_oreb'),
            ('proj_dreb', 'base_dreb'),
            ('proj_fta', 'base_fta'),
            ('proj_fga', 'base_fga'),
        ]
        stat_overrides = {
            'proj_stl': {'max': 1.10, 'min': 0.85},  # Phase 7.9.5: Tightened cap to reduce STL over-projection
            'proj_pts': {'max': 1.15, 'min': 0.85},  # Hotfix 5: tightened from ±25% to ±15%
            'proj_ast': {'max': 1.15, 'min': 0.85},  # Hotfix 5: tightened from ±25% to ±15%
        }
        for proj_key, base_key in stat_pairs:
            base_val = calibrated.get(base_key, 0) or 0
            if base_val <= 0 or proj_key not in calibrated:
                continue
            max_mod = stat_overrides.get(proj_key, {}).get('max', config.MAX_MODIFIER)
            min_mod = stat_overrides.get(proj_key, {}).get('min', config.MIN_MODIFIER)
            ratio = calibrated[proj_key] / base_val
            if ratio > max_mod:
                calibrated[proj_key] = round(base_val * max_mod, 2)
                calibrated['notes'] += f" | CAP({proj_key}:{ratio:.2f}->{max_mod})"
            elif ratio < min_mod:
                calibrated[proj_key] = round(base_val * min_mod, 2)
                calibrated['notes'] += f" | FLOOR({proj_key}:{ratio:.2f}->{min_mod})"

        return calibrated


    def _assign_unified_archetype(self, p):
        """
        Assign 1 of 16 unified archetypes that combine style + specialization.
        Synergy playtypes now become modifier weights, not separate classifications.

        Returns: (archetype_str, synergy_dict, def_syn_dict)
        """
        # 0. MANUAL OVERRIDE
        raw_name = p.get('name', p.get('PLAYER_NAME', ''))
        clean_name = raw_name.lower().replace(' ', '').replace('.', '').replace("'", "").replace('-', '')
        if clean_name in self.MANUAL_OVERRIDES:
            return self.MANUAL_OVERRIDES[clean_name], {}, {}

        # Extract Position
        position = p.get('position', 'UNK')
        if position in ('G-F', 'SG', 'PG'):
            position = 'G'
        elif position in ('F-C', 'SF', 'PF'):
            position = 'F'
        elif position in ('C',):
            position = 'C'
        else:
            position = 'UNK'

        # Extract Stats
        pts = float(p.get('base_pts', 0) or 0)
        reb = float(p.get('base_reb', 0) or 0)
        ast = float(p.get('base_ast', 0) or 0)
        tpm = float(p.get('base_3pm', 0) or 0)
        usg = float(p.get('base_usg', 0) or 0)
        stl = float(p.get('base_stl', 0) or 0)
        blk = float(p.get('base_blk', 0) or 0)
        mins = float(p.get('base_min', 0) or 0)

        # Fallback Logic
        if stl == 0 and blk == 0 and usg == 0:
            team = p.get('team', p.get('TEAM_ABBREVIATION', ''))
            if raw_name:
                miss = self._fetch_missing_stats(raw_name, team)
                stl = miss.get('base_stl', 0)
                blk = miss.get('base_blk', 0)
                usg = miss.get('base_usg', 0)

        # Get tracking data & synergy data
        tracking = self._get_tracking_stats(raw_name)
        synergy = self._get_synergy_playtypes(raw_name)

        # Extract tracking stats
        drives = tracking.get('avg_drives', 0)
        speed = tracking.get('avg_speed', 0)

        # Get synergy frequencies - create dict for easy lookup
        synergy_dict = {}
        for tag, freq, ppp, percentile in synergy:
            synergy_dict[tag] = (freq, ppp)

        # Get PBP shot quality data
        rim_freq = p.get('pbp_rim_freq', 0)

        # === TIER 1: ENGINES (High-Usage Creators) ===

        # HELIOCENTRIC_MAESTRO
        prh_freq = synergy_dict.get('P&R_HANDLER', (0, 0))[0]
        if (usg > 0.30 and ast > 6.0 and prh_freq > 15.0):
            return 'HELIOCENTRIC_MAESTRO', synergy_dict, {}

        # SLASHING_CREATOR
        trans_freq = synergy_dict.get('TRANSITION', (0, 0))[0]
        if (pts > 22.0 and drives > 8.0 and tpm < 2.0 and trans_freq > 10.0):
            return 'SLASHING_CREATOR', synergy_dict, {}

        # JUMBO_FACILITATOR
        if (reb > 6.0 and ast > 5.0 and prh_freq > 10.0):
            return 'JUMBO_FACILITATOR', synergy_dict, {}

        # === TIER 2: SCORING SPECIALISTS ===

        # SNIPER_ELITE
        spot_freq = synergy_dict.get('SPOT_UP', (0, 0))[0]
        if (tpm > 2.8 and spot_freq > 15.0 and ast < 3.5):
            return 'SNIPER_ELITE', synergy_dict, {}

        # TWO_LEVEL_SCORER
        iso_freq = synergy_dict.get('ISO_SCORER', (0, 0))[0]
        if (pts > 22.0 and 1.5 < tpm < 2.5 and iso_freq > 8.0):
            return 'TWO_LEVEL_SCORER', synergy_dict, {}

        # === TIER 3: BIG MEN (Rebounding & Rim) ===

        # Get rebounding data (future enhancement - use defaults for now)
        contested_reb_pct = p.get('contested_reb_pct', 0.5)

        # WARRIOR_BIG
        prr_freq = synergy_dict.get('P&R_ROLL_MAN', (0, 0))[0]
        if (reb > 8.0 and contested_reb_pct > 0.40 and prr_freq > 8.0):
            return 'WARRIOR_BIG', synergy_dict, {}

        # STRETCH_BIG
        if (reb > 6.5 and tpm > 1.8 and ast < 4.0):
            return 'STRETCH_BIG', synergy_dict, {}

        # ROLL_MAN
        if (rim_freq > 0.50 and prr_freq > 12.0 and ast < 3.0):
            return 'ROLL_MAN', synergy_dict, {}

        # === TIER 4: ROLE PLAYERS & DEFENDERS ===

        # Defensive profile and defensive Synergy fallback.
        # Pull from loaded defense table when caller packet is sparse (e.g. batch reclassify scripts).
        defense_profile = self.defense_profiles.get(raw_name, {})
        def_diff = float(
            p.get(
                'def_diff_pct',
                defense_profile.get('def_diff_pct', p.get('def_diff_vs_screen', 0))
            ) or 0.0
        )
        def_freq = float(p.get('def_freq_pct', defense_profile.get('def_freq_pct', 0)) or 0.0)
        def_distance = float(
            p.get('def_distance_miles', defense_profile.get('def_distance_miles', 0)) or 0.0
        )
        def_syn = self._get_player_defensive_synergy(raw_name)

        pr_roll_def = (def_syn.get('PR_ROLL_MAN') or {}).get('percentile', 0.0)
        post_def = (def_syn.get('POST_UP') or {}).get('percentile', 0.0)
        iso_def = (def_syn.get('ISO') or {}).get('percentile', 0.0)
        spot_def = (def_syn.get('SPOT_UP') or {}).get('percentile', 0.0)
        strong_def_tags = sum(
            1
            for pt in ('ISO', 'PR_BALL_HANDLER', 'PR_ROLL_MAN', 'SPOT_UP', 'POST_UP', 'CUT')
            if (def_syn.get(pt) or {}).get('percentile', 0.0) >= 70.0
        )

        # CUTTER_SPECIALIST
        cut_freq = synergy_dict.get('OFF_BALL_CUTTER', (0, 0))[0]
        if (rim_freq > 0.55 and cut_freq > 10.0 and drives < 2.0):
            return 'CUTTER_SPECIALIST', synergy_dict, def_syn

        # FACILITATOR
        if (ast >= 5.0 and pts < 15.0 and usg < 0.28):
            return 'FACILITATOR', synergy_dict, def_syn

        # === FALLBACK: Try relaxed thresholds to reduce GENERALIST % ===

        # Relaxed HELIOCENTRIC_MAESTRO (high usage + assists)
        if (usg > 0.28 and ast > 8.0):
            return 'HELIOCENTRIC_MAESTRO', synergy_dict, def_syn

        # Relaxed SLASHING_CREATOR (high pts, low 3s)
        if (pts > 20.0 and tpm < 1.5 and usg > 0.28):
            return 'SLASHING_CREATOR', synergy_dict, def_syn

        # Relaxed SNIPER_ELITE (just high 3PM)
        if (tpm > 2.5 and ast < 4.0):
            return 'SNIPER_ELITE', synergy_dict, def_syn

        # Relaxed STRETCH_BIG (reb + some 3s)
        if (reb > 5.5 and tpm > 1.5 and position in ['F', 'C', 'UNK']):
            return 'STRETCH_BIG', synergy_dict, def_syn

        # Relaxed ROLL_MAN (big with high rim freq)
        if (reb > 7.0 and rim_freq > 0.45 and tpm < 1.0):
            return 'ROLL_MAN', synergy_dict, def_syn

        # Relaxed FACILITATOR (focus on passing)
        if (ast > 4.0 and pts < 18.0):
            return 'FACILITATOR', synergy_dict, def_syn

        # === ADDITIONAL FALLBACKS (Feb 2026 Calibration) ===

        # TWO_LEVEL_SCORER fallback: Scoring guards/wings who don't fit other categories
        if (pts > 10.0 and tpm > 0.8 and usg > 0.19):
            return 'TWO_LEVEL_SCORER', synergy_dict, def_syn

        if (ast > 2.0 and pts < 14.0 and usg < 0.24):
            return 'CONNECTOR', synergy_dict, def_syn

        if (reb > 3.5 and (stl + blk) > 0.8 and pts < 12.0 and position in ['F', 'C', 'UNK']):
            return 'ENERGY_BIG', synergy_dict, def_syn

        # SNIPER_ELITE relaxed further: High 3PM shooters regardless of assists
        if (tpm > 2.2):
            return 'SNIPER_ELITE', synergy_dict, def_syn

        # CUTTER_SPECIALIST fallback: Role players with high rim freq
        if (rim_freq > 0.40 and pts < 15.0):
            return 'CUTTER_SPECIALIST', synergy_dict, def_syn

        # ROLL_MAN fallback: Bigs without many stats
        if (reb > 5.0 and position in ['C', 'F-C', 'F'] and pts < 12.0):
            return 'ROLL_MAN', synergy_dict, def_syn

        # FACILITATOR relaxed: Any player with decent assists
        if (ast > 3.5):
            return 'FACILITATOR', synergy_dict, def_syn

        # Synergy-dominant fallback: classify low-usage role players by clear action profile.
        if (spot_freq >= 20.0 and tpm >= 0.7 and ast < 3.0):
            return 'SNIPER_ELITE', synergy_dict, def_syn

        if (prh_freq >= 14.0 and ast >= 2.5 and usg < 0.26):
            return 'CONNECTOR', synergy_dict, def_syn

        if (prr_freq >= 10.0 and reb >= 4.0 and position in ['F', 'C', 'UNK']):
            return 'ENERGY_BIG', synergy_dict, def_syn

        # === FINAL CATCH-ALL: NBA-level production (Phase 7.9.5 Conservative Thresholds) ===
        # Tighter thresholds to avoid false positives on deep bench players
        if pts > 6.0 or ast > 2.0 or reb > 3.5:
            if tpm > 0.8 and usg > 0.18:
                return 'TWO_LEVEL_SCORER', synergy_dict, def_syn
            elif ast > 2.5 and pts < 14.0:
                return 'CONNECTOR', synergy_dict, def_syn
            elif reb > 4.0 and position in ('F', 'C', 'UNK'):
                return 'ENERGY_BIG', synergy_dict, def_syn

        # Minutes-based fallback: keep rotation players out of GENERALIST
        if mins > 15.0:
            if position in ('F', 'C', 'PF', 'SF', 'F-C', 'C-F'):
                return 'ENERGY_BIG', synergy_dict, def_syn
            if position == 'UNK':
                return ('ENERGY_BIG' if reb >= ast else 'CONNECTOR'), synergy_dict, def_syn
            return 'CONNECTOR', synergy_dict, def_syn

        # GENERALIST (final fallback - low usage role players)
        return 'GENERALIST', synergy_dict, def_syn

    def _log_adjustment(self, player_name: str, function: str, 
                        modifier: float, reason: str) -> None:
        """
        Log calibration adjustment if debug mode enabled.
        
        Args:
            player_name: Player being calibrated
            function: Name of the calibration function
            modifier: Adjustment factor applied (e.g., 1.07 for +7%)
            reason: Human-readable explanation
        """
        if self.debug_log and hasattr(self, 'logger'):
            self.logger.debug(
                f"ADJUST | {player_name} | {function} | "
                f"Modifier: {modifier:.3f} | {reason}"
            )

    def _log_skip(self, player_name: str, function: str, reason: str) -> None:
        """
        Log when a calibration adjustment is skipped.
        
        Args:
            player_name: Player being calibrated
            function: Name of the calibration function
            reason: Why adjustment was skipped
        """
        if self.debug_log and hasattr(self, 'logger'):
            self.logger.debug(
                f"SKIP | {player_name} | {function} | {reason}"
            )

    def _apply_shot_difficulty_modifier(self, calibrated: dict) -> None:
        """
        Adjusts shooting efficiency based on defender distance and shot quality.
        """
        player_name = calibrated.get('name', '')
        if not player_name:
            return

        shot_difficulty_stats = self._get_shot_difficulty_stats(player_name)

        if not shot_difficulty_stats or shot_difficulty_stats['shot_difficulty_games'] < 3:
            self._log_skip(player_name, 'SHOT_DIFFICULTY', 'Insufficient tracking data')
            return

        total_fga = shot_difficulty_stats['avg_tight_fga'] + shot_difficulty_stats['avg_open_fga'] + shot_difficulty_stats['avg_wide_open_fga']
        if total_fga == 0:
            self._log_skip(player_name, 'SHOT_DIFFICULTY', 'No tracked FGA')
            return
            
        wide_open_ratio = shot_difficulty_stats['avg_wide_open_fga'] / total_fga

        if wide_open_ratio > 0.5:
            # High Quality Shot Selection
            fg_pct_mod = 1.03
            tpm_mod = 1.05
            self._boost_stat(calibrated, 'proj_fg_pct', fg_pct_mod)
            self._boost_stat(calibrated, 'proj_3pm', tpm_mod)
            calibrated['notes'] += " | High Quality Shots"
            self._log_adjustment(player_name, 'SHOT_DIFFICULTY', fg_pct_mod, f"Wide Open Ratio: {wide_open_ratio:.1%}")
        elif wide_open_ratio < 0.2:
            # Low Quality Shot Selection
            fg_pct_mod = 0.97
            tpm_mod = 0.95
            self._boost_stat(calibrated, 'proj_fg_pct', fg_pct_mod)
            self._boost_stat(calibrated, 'proj_3pm', tpm_mod)
            calibrated['notes'] += " | Low Quality Shots"
            self._log_adjustment(player_name, 'SHOT_DIFFICULTY', fg_pct_mod, f"Wide Open Ratio: {wide_open_ratio:.1%}")

    def _apply_opponent_context_modifiers(self, calibrated: dict) -> None:
        """
        Adjusts defensive stats based on opponent tendencies.
        """
        player_name = calibrated.get('name', '')
        if not player_name:
            return

        opponent_stats = calibrated.get('opponent_stats', {})
        if not opponent_stats:
            self._log_skip(player_name, 'OPPONENT_CONTEXT', 'No opponent stats found')
            return

        tov_rate = opponent_stats.get('tov_rate', 0)
        two_pa_rate = opponent_stats.get('two_pa_rate', 0)
        opponent_abbr = calibrated.get('opponent')
        opponent_profile = self.opponent_profiles.get(opponent_abbr, {})

        # STL boost vs high-turnover teams (Phase 7.9.5: threshold raised to 0.17, boost reduced to 1.05)
        if tov_rate > 0.17:
            stl_mod = 1.05
            self._boost_stat(calibrated, 'proj_stl', stl_mod)
            calibrated['notes'] += " | STL Boost (High TOV%)"
            self._log_adjustment(player_name, 'OPPONENT_CONTEXT', stl_mod, f"Opponent TOV Rate: {tov_rate:.1%}")

        # BLK boost vs paint-heavy teams
        if two_pa_rate > 0.65:
            blk_mod = 1.10
            self._boost_stat(calibrated, 'proj_blk', blk_mod)
            calibrated['notes'] += " | BLK Boost (High 2PA%)"
            self._log_adjustment(player_name, 'OPPONENT_CONTEXT', blk_mod, f"Opponent 2PA Rate: {two_pa_rate:.1%}")

        # Richer opponent profile signals from player_game_opponent
        if opponent_profile:
            opp_stl = opponent_profile.get('opp_stl', 0)
            opp_blk = opponent_profile.get('opp_blk', 0)
            opp_fg_pct = opponent_profile.get('opp_fg_pct', 0)

            if opp_stl > 8.5:
                self._boost_stat(calibrated, 'proj_tov', 1.05)
                calibrated['notes'] += " | Ball Pressure"
            elif opp_stl < 6.5:
                self._boost_stat(calibrated, 'proj_tov', 0.97)

            if opp_blk > 5.5 and calibrated.get('pbp_rim_freq', 0) > 0.35:
                self._boost_stat(calibrated, 'proj_pts', 0.97)
                calibrated['notes'] += " | Rim Deterrence"

            if opp_fg_pct > 0 and opp_fg_pct < 0.455:
                self._boost_stat(calibrated, 'proj_fg_pct', 0.98)

    def classify_team_offense(self, team_abbr: str) -> str:
        """
        Classify team offensive style. Priority order:
        1. team_scheme_cache (DB, updated daily via data_sync)
        2. team_offensive_classifier.py (in-memory, computed from player_game_logs at import)
        3. BALANCED fallback
        """
        return self.OFFENSIVE_STYLES.get(team_abbr) or TEAM_OFFENSIVE_TYPES.get(team_abbr, "BALANCED")

    def _apply_offensive_style_boost(self, calibrated: dict, team_offense: str, 
                                      opponent_defense: str) -> None:
        """
        Apply modifiers based on team offensive style vs opponent defense.
        
        Research basis:
        - MOTION offense beats BLITZ defense (ball movement beats pressure)
        - ISO_HEAVY struggles vs PAINT_PACK (limited driving lanes)
        - PACE_PUSH exploits slow teams in transition
        """
        player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))
        sec_playtypes = calibrated.get('secondary_playtypes', [])
        
        # MOTION offense bonuses
        if team_offense == "MOTION":
            if opponent_defense == "BLITZ":
                # Ball movement beats aggressive traps
                if 'SPOT_UP' in sec_playtypes or 'OFF_BALL_CUTTER' in sec_playtypes:
                    self._boost_stat(calibrated, 'proj_pts', 1.05)
                    self._boost_stat(calibrated, 'proj_ast', 1.05)
                    calibrated['notes'] += " | Motion vs Blitz"
                    self._log_adjustment(player_name, 'OFF_STYLE', 1.05, 
                        "MOTION vs BLITZ: ball movement advantage")
        
        # ISO_HEAVY penalties
        elif team_offense == "ISO_HEAVY":
            if opponent_defense == "PAINT_PACK":
                # Limited driving lanes
                if 'ISO_SCORER' in sec_playtypes or 'P&R_HANDLER' in sec_playtypes:
                    self._boost_stat(calibrated, 'proj_pts', 0.96)
                    calibrated['notes'] += " | ISO vs Paint Pack"
                    self._log_adjustment(player_name, 'OFF_STYLE', 0.96, 
                        "ISO_HEAVY vs PAINT_PACK: clogged lanes")
        
        # PACE_PUSH bonuses
        elif team_offense == "PACE_PUSH":
            if opponent_defense == "FUNNEL":
                # Transition exploits slow recovery
                if 'TRANSITION' in sec_playtypes:
                    self._boost_stat(calibrated, 'proj_pts', 1.03)
                    calibrated['notes'] += " | Pace Push"
                    self._log_adjustment(player_name, 'OFF_STYLE', 1.03, 
                        "PACE_PUSH vs weak transition defense")
        
        # HALF_COURT specific
        elif team_offense == "HALF_COURT":
            if opponent_defense == "PERIMETER":
                # Methodical offense finds gaps
                if 'P&R_ROLL_MAN' in sec_playtypes or 'POST_UP' in sec_playtypes:
                    self._boost_stat(calibrated, 'proj_pts', 1.04)
                    calibrated['notes'] += " | Half-Court Advantage"
                    self._log_adjustment(player_name, 'OFF_STYLE', 1.04, 
                        "HALF_COURT exploits perimeter D")

    # === SYNERGY EFFICIENCY CALIBRATIONS (Phase 1 - Jan 21, 2026) ===

    def _apply_synergy_ppp_efficiency(self, calibrated: dict, opponent_abbr: str) -> None:
        """
        Apply Synergy PPP (Points Per Possession) efficiency modifier.

        Uses weighted PPP across player's primary playtypes to calibrate points projection.
        High-efficiency players (PPP > 1.10) get boost, low-efficiency get penalty.
        
        Volume Floor: Only applies PPP boost if player meets minimum scoring volume
        (10 FGA/game OR 12 PPG over last 60 days) to prevent over-projection
        of low-volume, high-efficiency role players.

        Args:
            calibrated: Player packet with projections
            opponent_abbr: Opponent team abbreviation (not used yet, for future matchup logic)
        """
        player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # === NEW: VOLUME FLOOR CHECK ===
            # Step 1: Query player's scoring volume (last 60 days)
            volume_query = """
                SELECT AVG(pts) as avg_pts, AVG(fga) as avg_fga
                FROM player_game_logs
                WHERE player_name = ? 
                AND game_date >= date('now', '-60 days')
                HAVING COUNT(*) >= 5
            """
            cursor.execute(volume_query, (player_name,))
            volume_row = cursor.fetchone()

            # Step 2: Apply volume floor
            MIN_FGA = 10.0
            MIN_PTS = 12.0

            if not volume_row or (volume_row[0] < MIN_PTS and volume_row[1] < MIN_FGA):
                # Player doesn't meet volume threshold - skip PPP boost
                conn.close()
                self._log_skip(player_name, 'PPP_EFFICIENCY', 
                    f"Volume floor: {volume_row[0] if volume_row else 0:.1f} PPG, "
                    f"{volume_row[1] if volume_row else 0:.1f} FGA")
                return
            # === END VOLUME FLOOR CHECK ===

            # Get player's primary playtypes (freq >= 5%)
            cursor.execute("""
                SELECT playtype, freq_pct, ppp
                FROM player_synergy_playtypes
                WHERE player_name = ? AND season = '2025-26' AND freq_pct >= 5.0
                ORDER BY freq_pct DESC
                LIMIT 4
            """, (player_name,))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                self._log_skip(player_name, 'PPP_EFFICIENCY', 'No Synergy playtype data')
                return  # No data, no adjustment

            # Calculate weighted PPP
            total_freq = sum(r[1] for r in rows)
            weighted_ppp = sum(r[1] * r[2] for r in rows) / total_freq

            # Compare to league average PPP from config
            efficiency_ratio = weighted_ppp / config.LEAGUE_AVG_PPP

            # Cap at ±12% adjustment (avoid over-calibration)
            modifier = max(0.88, min(1.12, efficiency_ratio))

            # Apply to points projection
            self._boost_stat(calibrated, 'proj_pts', modifier)
            
            # Log adjustment
            self._log_adjustment(player_name, 'PPP_EFFICIENCY', modifier,
                f"Weighted PPP: {weighted_ppp:.3f}")

            # Add note if significant adjustment (>5%)
            if abs(modifier - 1.0) > 0.05:
                direction = "Efficient" if modifier > 1.0 else "Inefficient"
                pct_change = int((modifier - 1.0) * 100)
                calibrated['notes'] += f" | {direction} ({pct_change:+d}% PPP)"

        except Exception as e:
            if self.debug_log and hasattr(self, 'logger'):
                self.logger.debug(f"ERROR | {player_name} | PPP_EFFICIENCY | {str(e)}")

    def _apply_opponent_weak_link_boost(self, calibrated: dict, opponent_abbr: str, def_style: str) -> None:
        """
        Boost offensive projections when opponent has a targeted weak-link defender.
        """
        archetype = calibrated.get('archetype', '')
        player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))
        position = (calibrated.get('position') or 'UNK').upper()

        if archetype not in ('SLASHING_CREATOR', 'WARRIOR_BIG', 'ROLL_MAN'):
            return

        pos_filter = "AND (position LIKE 'G%' OR position LIKE 'F%')" if position.startswith('G') else "AND (position LIKE 'F%' OR position LIKE 'C%')"
        if position.startswith('C'):
            pos_filter = "AND position LIKE 'C%'"

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT player_name, diff_pct, freq_pct, position
                FROM player_defense
                WHERE team_abbr = ?
                  AND season = '2025-26'
                  AND COALESCE(diff_pct, 0) > 2.0
                  AND COALESCE(freq_pct, 0) >= 10.0
                  {pos_filter}
                ORDER BY diff_pct DESC, freq_pct DESC
                LIMIT 1
                """,
                (opponent_abbr,),
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                return

            weak_name, _, _, weak_pos = row
            if archetype in ('SLASHING_CREATOR',):
                self._boost_stat(calibrated, 'proj_pts', 1.05)
                calibrated['notes'] += f" | Weak Link ({weak_pos}/{weak_name[:10]})"
            elif archetype in ('WARRIOR_BIG', 'ROLL_MAN'):
                self._boost_stat(calibrated, 'proj_pts', 1.05)
                self._boost_stat(calibrated, 'proj_reb', 1.05)
                calibrated['notes'] += f" | Weak Link Big ({weak_name[:10]})"
        except Exception as e:
            if self.debug_log:
                print(f"   [CAL] Weak-link boost failed: {e}")
            return

    def _apply_defensive_diff_adjustment(self, calibrated: dict, opponent_abbr: str) -> None:
        """
        Apply opponent defensive adjustment, preferring playtype-specific defensive Synergy.
        Falls back to aggregate player_defense diff_pct when defensive Synergy is unavailable.
        """
        player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))
        sec_playtypes = calibrated.get('secondary_playtypes', [])
        if not sec_playtypes:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Phase 4 path: use playtype-specific opponent defensive Synergy if available.
            try:
                cursor.execute(
                    """
                    SELECT playtype, MAX(percentile) AS top_percentile
                    FROM player_defensive_synergy
                    WHERE team_abbr = ?
                      AND season = '2025-26'
                      AND playtype IN ('ISO', 'PR_ROLL_MAN', 'SPOT_UP')
                    GROUP BY playtype
                    """,
                    (opponent_abbr,),
                )
                by_playtype = {row[0]: row[1] for row in cursor.fetchall()}
            except Exception:
                by_playtype = {}

            applied = False
            if by_playtype:
                rim_based = {'P&R_ROLL_MAN', 'OFF_BALL_CUTTER', 'PUTBACK', 'POST_UP'}
                if any(pt in rim_based for pt in sec_playtypes) and by_playtype.get('PR_ROLL_MAN', 0) >= 75:
                    self._boost_stat(calibrated, 'proj_pts', 0.94)
                    self._boost_stat(calibrated, 'proj_fg_pct', 0.96)
                    calibrated['notes'] += " | Elite Roll-Man D"
                    applied = True

                if 'ISO_SCORER' in sec_playtypes and by_playtype.get('ISO', 0) >= 75:
                    self._boost_stat(calibrated, 'proj_pts', 0.94)
                    calibrated['notes'] += " | Elite ISO D"
                    applied = True

                if 'SPOT_UP' in sec_playtypes and by_playtype.get('SPOT_UP', 0) >= 75:
                    self._boost_stat(calibrated, 'proj_3pm', 0.94)
                    calibrated['notes'] += " | Elite Spot-Up D"
                    applied = True

            if applied:
                conn.close()
                return

            # Fallback: aggregate best diff_pct against rim-based players.
            rim_based = {'P&R_ROLL_MAN', 'OFF_BALL_CUTTER', 'PUTBACK', 'POST_UP'}
            if not any(pt in rim_based for pt in sec_playtypes):
                conn.close()
                self._log_skip(player_name, 'DEFENSIVE_DIFF', f"No rim playtype (has: {sec_playtypes})")
                return

            cursor.execute(
                """
                SELECT player_name, diff_pct
                FROM player_defense
                WHERE team_abbr = ? AND diff_pct IS NOT NULL
                ORDER BY diff_pct ASC
                LIMIT 1
                """,
                (opponent_abbr,),
            )
            row = cursor.fetchone()
            conn.close()
            if not row:
                self._log_skip(player_name, 'DEFENSIVE_DIFF', f"No defensive data for {opponent_abbr}")
                return

            rim_protector_name, diff_pct = row
            modifier = max(0.88, min(1.12, 1.0 + (diff_pct / 100)))
            self._boost_stat(calibrated, 'proj_pts', modifier)
            self._log_adjustment(player_name, 'DEFENSIVE_DIFF', modifier, f"vs {rim_protector_name}: {diff_pct:.1f}% diff")
        except Exception as e:
            if self.debug_log and hasattr(self, 'logger'):
                self.logger.debug(f"ERROR | {player_name} | DEFENSIVE_DIFF | {str(e)}")

    def _apply_drives_assist_profile(self, calibrated: dict) -> None:
        """
        Apply assist profile modifier based on drives pass%.

        High pass% (>40%) = true playmaker → boost assists
        Low pass% (<25%) = score-first driver → slight assist penalty

        Args:
            calibrated: Player packet with projections
        """
        player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))

        try:
            profile = self.tracking_profiles.get(player_name, {})
            games = profile.get('tracking_games', 0)
            drives = profile.get('avg_drives', 0)
            pass_pct = profile.get('avg_drives_pass_pct', 0)

            if games < 5:  # Need at least 5 games for reliable sample
                self._log_skip(player_name, 'DRIVES_AST', 
                    f"Insufficient data ({games} games)")
                return  # No drives data or insufficient sample

            # High volume + high pass% = elite playmaker
            if drives >= 8 and pass_pct >= 40:
                modifier = 1.10  # +10% assist boost
                tag = "Elite Playmaker"
                calibrated['notes'] += f" | {tag}"
            elif drives >= 6 and pass_pct >= 35:
                modifier = 1.05  # +5% assist boost
                tag = "High Pass Rate"
                calibrated['notes'] += f" | {tag}"
            elif pass_pct < 25:
                modifier = 0.95  # -5% penalty (score-first)
                tag = "Score-First Driver"
                calibrated['notes'] += f" | {tag}"
            else:
                self._log_skip(player_name, 'DRIVES_AST', 
                    f"Neutral profile ({drives:.1f} drives, {pass_pct:.1f}% pass)")
                return  # Neutral profile, no adjustment

            # Apply to assist projection
            self._boost_stat(calibrated, 'proj_ast', modifier)
            
            # Log adjustment
            self._log_adjustment(player_name, 'DRIVES_AST', modifier,
                f"{tag}: {drives:.1f} drives, {pass_pct:.1f}% pass")

        except Exception as e:
            if self.debug_log and hasattr(self, 'logger'):
                self.logger.debug(f"ERROR | {player_name} | DRIVES_AST | {str(e)}")

    def _apply_fatigue_adjustments(self, calibrated: dict, yak_report: dict) -> None:
        """
        Apply research-backed fatigue modifiers for B2B and schedule spots.

        Research:
        - García et al. (2020): -1.27 effect size Q4 performance in B2B games
        - TopEndSports: 2-3 point decline on Road B2B games (travel + fatigue)
        - Positional: Guards suffer most (cover 2.5+ miles/game)

        Logic:
        - Road B2B: -6% volume (Travel + Fatigue)
        - Home B2B: -3% volume (Fatigue only)
        - Guard Tax: Extra penalty for active guards on B2B
        - Rested Advantage: +3% volume (Home + 3+ days rest)
        - Schedule Density: 4-in-5 nights tax

        BACKTEST NOTE (Jan 21, 2026):
        Dec 20-Jan 16 backtest shows B2B players OUTPERFORMED by +2.7% PTS.
        Current tax (-3%/-6%) resulted in under-projection (-3.36 mean error).
        Monitor closely - may need to reduce modifiers if trend continues.
        """
        player_name = calibrated.get('name', '')

        # Extract Schedule Context
        is_b2b = yak_report.get('is_back_to_back', False)
        is_road = yak_report.get('is_road', False)
        rest_days = yak_report.get('rest_days', 2)
        next_game_tomorrow = yak_report.get('next_game_tomorrow', False)
        density_5day = yak_report.get('games_in_last_5_days', 0)
        position = calibrated.get('position', 'UNK')

        # === BACK-TO-BACK LOGIC (I1: Player-specific B2B splits) ===
        # Use actual B2B performance data when available, fall back to hardcoded values
        if is_b2b:
            key = _canonical_key(player_name)
            b2b_data = self.b2b_splits.get(key)

            if b2b_data:
                pts_mod = 1.0 + b2b_data['pts_delta']
                min_mod = 1.0 + b2b_data['min_delta']
                confidence = b2b_data['confidence']
                self._apply_factor(calibrated, pts_mod)
                calibrated['proj_min'] *= min_mod
                self._log_adjustment(player_name, 'FATIGUE_B2B', pts_mod, f"actual-data ({confidence})")
                calibrated['notes'] += f" | B2B Actual ({confidence})"
            else:
                if is_road:
                    self._apply_factor(calibrated, 0.952)
                    calibrated['notes'] += " | B2B Road Tax"
                    self._log_adjustment(player_name, 'FATIGUE', 0.952, "Road B2B schedule loss (fallback)")
                else:
                    self._apply_factor(calibrated, 0.985)
                    calibrated['notes'] += " | B2B Home Tax"
                    self._log_adjustment(player_name, 'FATIGUE', 0.985, "Home B2B fatigue (fallback)")

            # Guard Specific Tax (High cardio load) - still apply for guards
            if any(g in position for g in ['PG', 'SG', 'G']):
                self._boost_stat(calibrated, 'proj_pts', 0.98)
                self._boost_stat(calibrated, 'proj_fg_pct', 0.99)
                calibrated['notes'] += " (Guard Fatigue)"
                self._log_adjustment(player_name, 'FATIGUE', 0.98, "Guard active movement penalty")

        # === REST ADVANTAGE LOGIC ===
        elif rest_days >= 3 and not is_road:
            # Rested Home Game
            self._apply_factor(calibrated, 1.03)
            calibrated['notes'] += " | Rested Home Edge"
            self._log_adjustment(player_name, 'FATIGUE', 1.03, f"Rested ({rest_days} days) at Home")

        # === SCHEDULE DENSITY (4-in-5 Nights) ===
        # If played 3 games in last 4 days (density=3) + Today = 4 games in 5 nights
        # Adjusted from -2.0% to -1.0% based on backtest findings (+0.63 pts error)
        if density_5day >= 3:
            self._apply_factor(calibrated, 0.99)
            calibrated['notes'] += " | 4-in-5 Density Tax"
            self._log_adjustment(player_name, 'FATIGUE', 0.99, "4-in-5 schedule density")

        # === FRONT-END LOAD MANAGEMENT (Star Players) ===
        # If playing today AND game tomorrow (Front End of B2B)
        is_star = calibrated.get('base_pts', 0) > 22.0 or calibrated.get('base_usg', 0) > 0.28
        if next_game_tomorrow and is_star:
            # Stars often play slightly less or conserve energy on front end
            self._boost_stat(calibrated, 'proj_min', 0.96) # -4% minutes (~1.5 min)
            calibrated['notes'] += " | B2B Front-End (Load Mgmt)"
            self._log_adjustment(player_name, 'FATIGUE', 0.96, "Front-end B2B load management")

    def _apply_secondary_playtype_matchups(self, calibrated: dict, def_style: str, wowy_confidence: str = None) -> None:
        """
        Apply modifiers based on player's secondary playtypes vs opponent defense.

        Research basis:
        - ISO vs BLITZ: Pressure forces turnovers
        - SPOT_UP vs PAINT_PACK: Open shooters feast on helpers
        - P&R_ROLL_MAN vs DROP: Lobs and dunks available

        Phase 3 Enhancement: Added debug logging for all adjustments
        Phase 6.3 Enhancement: WOWY confidence weighting on key boosts
        """
        player_name = calibrated.get('name', '')
        secondary_types = calibrated.get('secondary_playtypes', [])
        
        for playtype in secondary_types:
            # === ISO_SCORER MATCHUPS (3 total) ===
            if playtype == 'ISO_SCORER':
                if def_style == 'BLITZ':
                    # Blitz defense disrupts isolation (research: +15% TOV rate)
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 0.92, wowy_confidence)
                    self._boost_stat(calibrated, 'proj_tov', 1.12)
                    calibrated['notes'] += " | ISO Tax vs Blitz"
                    self._log_adjustment(player_name, 'PLAYTYPE', 0.92,
                        "ISO_SCORER vs BLITZ: pressure forces mistakes")
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.12,
                        "ISO_SCORER vs BLITZ: increased turnovers")
                elif def_style == 'PERIMETER':
                    # ISO mismatch vs perimeter switching
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.10, wowy_confidence)
                    calibrated['notes'] += " | ISO vs Perimeter"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.10,
                        "ISO_SCORER vs PERIMETER: space to operate")

            # === P&R_HANDLER MATCHUPS (3 total) ===
            elif playtype == 'P&R_HANDLER':
                if def_style == 'PAINT_PACK':
                    # Drop coverage gives P&R handlers easy assists
                    self._boost_stat_with_confidence(calibrated, 'proj_ast', 1.08, wowy_confidence)
                    calibrated['notes'] += " | P&R Drop Edge"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.08,
                        "P&R_HANDLER vs PAINT_PACK: passing lanes open")
                elif def_style == 'BLITZ':
                    # Blitz forces tough passes, more turnovers
                    self._boost_stat_with_confidence(calibrated, 'proj_ast', 0.90, wowy_confidence)
                    self._boost_stat(calibrated, 'proj_tov', 1.15)
                    calibrated['notes'] += " | P&R Blitz Tax"
                    self._log_adjustment(player_name, 'PLAYTYPE', 0.90,
                        "P&R_HANDLER vs BLITZ: traps disrupt passing")
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.15,
                        "P&R_HANDLER vs BLITZ: increased turnovers")
                elif def_style == 'FUNNEL':
                    # Funnel defense creates passing lanes
                    self._boost_stat_with_confidence(calibrated, 'proj_ast', 1.12, wowy_confidence)
                    calibrated['notes'] += " | PnR Handler vs Funnel"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.12,
                        "P&R_HANDLER vs FUNNEL: easy passing lanes")

            # === SPOT_UP MATCHUPS (2 total - HIGHEST ROI) ===
            elif playtype == 'SPOT_UP':
                if def_style == 'PAINT_PACK':
                    # Paint-pack leaves shooters open (strongest edge)
                    if "Paint Pack Edge" not in calibrated.get('notes', ''):
                        self._boost_stat_with_confidence(calibrated, 'proj_3pm', 1.08, wowy_confidence)
                        calibrated['notes'] += " | Spot-Up vs Pack"
                        self._log_adjustment(player_name, 'PLAYTYPE', 1.08,
                            "SPOT_UP vs PAINT_PACK: open 3s from help D")
                elif def_style == 'PERIMETER':
                    # Perimeter switching closes out shooters
                    self._boost_stat_with_confidence(calibrated, 'proj_3pm', 0.95, wowy_confidence)
                    calibrated['notes'] += " | Spot-Up Tax"
                    self._log_adjustment(player_name, 'PLAYTYPE', 0.95,
                        "SPOT_UP vs PERIMETER: contested shots")

            # === TRANSITION MATCHUPS (3 total) ===
            elif playtype == 'TRANSITION':
                if def_style == 'FUNNEL':
                    # Funnel defense vulnerable in transition
                    if "Transition Chaos" not in calibrated.get('notes', ''):
                        self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.05, wowy_confidence)
                        calibrated['notes'] += " | Transition Edge (sec)"
                        self._log_adjustment(player_name, 'PLAYTYPE', 1.05,
                            "TRANSITION vs FUNNEL: fast break chaos")
                elif def_style == 'PAINT_PACK':
                    # Set defense slows transition
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 0.92, wowy_confidence)
                    calibrated['notes'] += " | Transition Tax"
                    self._log_adjustment(player_name, 'PLAYTYPE', 0.92,
                        "TRANSITION vs PAINT_PACK: set defense stops breaks")

            # === HANDOFF MATCHUPS (2 total) ===
            elif playtype == 'HANDOFF':
                if def_style == 'BLITZ':
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 0.95, wowy_confidence)
                    calibrated['notes'] += " | Handoff Tax vs Blitz"
                    self._log_adjustment(player_name, 'PLAYTYPE', 0.95,
                        "HANDOFF vs BLITZ: pressure disrupts dribble handoffs")
                elif def_style == 'PAINT_PACK':
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.08, wowy_confidence)
                    calibrated['notes'] += " | Handoff vs Drop"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.08,
                        "HANDOFF vs PAINT_PACK: drop creates pull-up space")

            # === OFF_SCREEN MATCHUPS (2 total) ===
            elif playtype == 'OFF_SCREEN':
                if def_style == 'PAINT_PACK':
                    self._boost_stat_with_confidence(calibrated, 'proj_3pm', 1.10, wowy_confidence)
                    calibrated['notes'] += " | Off-Screen vs Pack"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.10,
                        "OFF_SCREEN vs PAINT_PACK: late closeouts")
                elif def_style == 'PERIMETER':
                    self._boost_stat_with_confidence(calibrated, 'proj_3pm', 0.95, wowy_confidence)
                    calibrated['notes'] += " | Off-Screen Tax"
                    self._log_adjustment(player_name, 'PLAYTYPE', 0.95,
                        "OFF_SCREEN vs PERIMETER: tight screen navigation")

            # === P&R_ROLL_MAN MATCHUPS (3 total) ===
            elif playtype == 'P&R_ROLL_MAN':
                if def_style == 'PAINT_PACK':
                    # Drop coverage = easy dunks for roll man
                    if "Roll Man vs Drop" in calibrated.get('notes', ''):
                        continue
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.08, wowy_confidence)
                    self._boost_stat(calibrated, 'proj_fg_pct', 1.10)
                    calibrated['notes'] += " | Roll Man vs Drop"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.08,
                        "P&R_ROLL_MAN vs PAINT_PACK: lobs and dunks")
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.10,
                        "P&R_ROLL_MAN vs PAINT_PACK: increased FG%")
                elif def_style == 'BLITZ':
                    # Blitz limits roll opportunities
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 0.88, wowy_confidence)
                    calibrated['notes'] += " | Roll Man Tax"
                    self._log_adjustment(player_name, 'PLAYTYPE', 0.88,
                        "P&R_ROLL_MAN vs BLITZ: no space at rim")
                elif def_style == 'PERIMETER':
                    # Small ball = boards + mismatches
                    self._boost_stat_with_confidence(calibrated, 'proj_reb', 1.15, wowy_confidence)
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.10, wowy_confidence)
                    calibrated['notes'] += " | Roll Man vs Small Ball"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.15,
                        "P&R_ROLL_MAN vs PERIMETER: rebound advantage")
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.10,
                        "P&R_ROLL_MAN vs PERIMETER: mismatch scoring")

            # === OFF_BALL_CUTTER MATCHUPS (3 total) ===
            elif playtype == 'OFF_BALL_CUTTER':
                if def_style == 'PERIMETER':
                    # Small ball vulnerable to cutters
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.12, wowy_confidence)
                    calibrated['notes'] += " | Cutter vs Small Ball"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.12,
                        "OFF_BALL_CUTTER vs PERIMETER: backdoor cuts")
                elif def_style == 'PAINT_PACK':
                    # Rim protection reduces cutter efficiency
                    self._boost_stat(calibrated, 'proj_fg_pct', 0.90)
                    calibrated['notes'] += " | Cutter Tax"
                    self._log_adjustment(player_name, 'PLAYTYPE', 0.90,
                        "OFF_BALL_CUTTER vs PAINT_PACK: clogged lanes")
                elif def_style == 'BLITZ':
                    # Blitz creates cutting lanes
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.12, wowy_confidence)
                    calibrated['notes'] += " | Cutter vs Blitz"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.12,
                        "OFF_BALL_CUTTER vs BLITZ: cutting lanes")

            # === PUTBACK MATCHUP (1 total) ===
            elif playtype == 'PUTBACK':
                if def_style == 'PERIMETER':
                    # Small ball = offensive glass dominance + putback points
                    if "Warrior Boards vs Small Ball" in calibrated.get('notes', ''):
                        continue
                    self._boost_stat_with_confidence(calibrated, 'proj_oreb', 1.08, wowy_confidence)
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.15, wowy_confidence)
                    calibrated['notes'] += " | Putback vs Small"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.08,
                        "PUTBACK vs PERIMETER: size advantage on glass")
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.15,
                        "PUTBACK vs PERIMETER: putback scoring")

            # === POST_UP MATCHUP (1 total) ===
            elif playtype == 'POST_UP':
                if def_style == 'PERIMETER':
                    # Post mismatch vs small ball
                    self._boost_stat_with_confidence(calibrated, 'proj_pts', 1.15, wowy_confidence)
                    calibrated['notes'] += " | Post vs Small Ball"
                    self._log_adjustment(player_name, 'PLAYTYPE', 1.15,
                        "POST_UP vs PERIMETER: size mismatch")

    def _apply_archetype_synergy_weights(self, calibrated, archetype, synergy_dict):
        """
        Apply synergy PPP/frequency as modifier weights based on archetype.
        Replaces old secondary playtype matchup system with archetype-specific modifiers.
        """
        if not synergy_dict:
            return  # No synergy data available

        player_name = calibrated.get('name', '')

        # Map archetypes to their primary synergy playtype for PPP efficiency weighting.
        # Stat routing (in the apply block below):
        #   P&R_HANDLER    → proj_ast  (facilitators, including HUB_BIG/CONNECTOR bigs)
        #   ISO_SCORER/POST_UP/TRANSITION → proj_pts
        #   SPOT_UP        → proj_3pm
        #   P&R_ROLL_MAN/OFF_BALL_CUTTER → proj_pts + proj_fg_pct
        archetype_synergy_map = {
            'HELIOCENTRIC_MAESTRO': 'P&R_HANDLER',   # Guard engine, P&R handler → AST
            'SLASHING_CREATOR': 'TRANSITION',          # Drive-and-score, transition → PTS
            'ISO_ASSASSIN': 'ISO_SCORER',              # Pure ISO scorer → PTS
            'JUMBO_FACILITATOR': 'P&R_HANDLER',        # Big PG-type → AST
            'SNIPER_ELITE': 'SPOT_UP',                 # Catch-and-shoot → 3PM
            'TWO_LEVEL_SCORER': 'ISO_SCORER',          # Mid-range + 3 → PTS
            'WARRIOR_BIG': 'P&R_ROLL_MAN',             # Roll man → PTS + FG%
            'STRETCH_BIG': 'SPOT_UP',                  # Pop-and-shoot big → 3PM
            'ROLL_MAN': 'P&R_ROLL_MAN',                # Pure roll man → PTS + FG%
            'HUB_BIG': 'P&R_HANDLER',                  # Facilitating big (Jokić) → AST
            'CUTTER_SPECIALIST': 'OFF_BALL_CUTTER',    # Off-ball cutter → PTS + FG%
            'ENERGY_BIG': 'P&R_ROLL_MAN',              # Roll/putback energy → PTS + FG%
            'CONNECTOR': 'P&R_HANDLER',                # Ball-movement connector → AST
            'FACILITATOR': 'P&R_HANDLER',              # Secondary facilitator → AST
        }

        primary_playtype = archetype_synergy_map.get(archetype)
        if not primary_playtype or primary_playtype not in synergy_dict:
            return  # No modifier for this archetype

        freq, ppp = synergy_dict[primary_playtype]

        # Apply PPP efficiency modifier
        league_avg_ppp = config.LEAGUE_AVG_PPP
        ppp_mod = 1.0 + ((ppp - league_avg_ppp) / league_avg_ppp * 0.5)  # Max ±50% of diff
        ppp_mod = max(0.90, min(ppp_mod, 1.12))  # Cap at ±12%

        # Apply frequency weight (higher freq = more impact)
        freq_weight = min(freq / 20.0, 1.0)  # Scale to 1.0 at 20% freq

        final_mod = 1.0 + ((ppp_mod - 1.0) * freq_weight)

        # Apply to relevant stats based on playtype
        if primary_playtype in ['ISO_SCORER', 'TRANSITION', 'POST_UP']:
            self._boost_stat(calibrated, 'proj_pts', final_mod)
            if self.debug_log:
                self._log_adjustment(player_name, 'SYNERGY_EFFICIENCY', final_mod,
                    f"{primary_playtype} PPP: {ppp:.2f} ({freq:.0f}%)")
        elif primary_playtype == 'P&R_HANDLER':
            self._boost_stat(calibrated, 'proj_ast', final_mod)
            if self.debug_log:
                self._log_adjustment(player_name, 'SYNERGY_EFFICIENCY', final_mod,
                    f"{primary_playtype} PPP: {ppp:.2f} ({freq:.0f}%)")
        elif primary_playtype == 'SPOT_UP':
            self._boost_stat(calibrated, 'proj_3pm', final_mod)
            if self.debug_log:
                self._log_adjustment(player_name, 'SYNERGY_EFFICIENCY', final_mod,
                    f"{primary_playtype} PPP: {ppp:.2f} ({freq:.0f}%)")
        elif primary_playtype in ['P&R_ROLL_MAN', 'OFF_BALL_CUTTER']:
            self._boost_stat(calibrated, 'proj_pts', final_mod)
            self._boost_stat(calibrated, 'proj_fg_pct', final_mod)
            if self.debug_log:
                self._log_adjustment(player_name, 'SYNERGY_EFFICIENCY', final_mod,
                    f"{primary_playtype} PPP: {ppp:.2f} ({freq:.0f}%)")

        calibrated['notes'] += f" | {primary_playtype} PPP: {ppp:.2f} ({freq:.0f}%)"

    def _boost_stat(self, d, key, factor):
        if key in d: d[key] = round(d[key] * factor, 2)

    def _boost_stat_with_confidence(self, d, key, factor, wowy_confidence=None):
        """
        Apply stat boost weighted by WOWY confidence level.

        For BENEFICIARY scenarios, reduces boost impact when WOWY data is weak.

        Args:
            d: Player dict containing projections
            key: Stat key to boost (e.g., 'proj_pts')
            factor: Base boost factor (e.g., 1.15 for +15%)
            wowy_confidence: 'high', 'medium', 'low', or None
        """
        if key not in d:
            return

        # If no WOWY scenario, apply full boost
        if not wowy_confidence:
            d[key] = round(d[key] * factor, 2)
            return

        # Weight boost by confidence (Phase 6.3 Enhancement)
        confidence_weights = {
            'high': 1.0,     # Full boost
            'medium': 0.85,  # 15% reduction in boost magnitude
            'low': 0.70,     # 30% reduction in boost magnitude
        }
        weight = confidence_weights.get(wowy_confidence, 0.70)

        # Apply weighted boost: factor=1.15 with low confidence becomes 1.105
        # Formula: 1 + ((factor - 1) * weight)
        weighted_factor = 1.0 + ((factor - 1.0) * weight)
        d[key] = round(d[key] * weighted_factor, 2)

    def _apply_factor(self, d, factor):
        keys = ['proj_pts', 'proj_ast', 'proj_reb', 'proj_3pm', 'proj_min', 'proj_fga', 'proj_3pa', 'proj_fta', 'proj_oreb', 'proj_dreb', 'proj_stl', 'proj_blk']
        for k in keys:
            if k in d: d[k] = round(d[k] * factor, 2)

    def _zero_out(self, d):
        keys = ['proj_pts', 'proj_ast', 'proj_reb', 'proj_3pm', 'proj_min', 'proj_fga', 'proj_3pa', 'proj_fta', 'proj_oreb', 'proj_dreb', 'proj_stl', 'proj_blk']
        for k in keys: d[k] = 0.0

    def _load_clutch_data(self):
        """
        Load team clutch performance data from PBP Stats.
        Teams with clutch ORtg 15%+ higher than overall areCH_PERFORMER tagged as CLUT.
        """
        self.clutch_teams = {}
        if PBP_STATS_AVAILABLE:
            try:
                from utils.pbp_stats_client import get_team_leverage_summary
                data = get_team_leverage_summary("2025-26", "VeryHigh")
                if data and 'results' in data:
                    for row in data.get('results', []):
                        team = row.get('team')
                        overall_ortg = row.get('offRating', {}).get('overall', 0) or 0
                        clutch_ortg = row.get('offRating', {}).get('veryHigh', 0) or 0
                        if overall_ortg and clutch_ortg:
                            clutch_diff_pct = ((clutch_ortg - overall_ortg) / overall_ortg) * 100
                            self.clutch_teams[team] = {
                                'clutch_ortg': clutch_ortg,
                                'overall_ortg': overall_ortg,
                                'is_clutch': clutch_diff_pct >= 15.0,
                                'diff_pct': clutch_diff_pct,
                            }
                if self.clutch_teams:
                    clutch_count = sum(1 for t in self.clutch_teams.values() if t['is_clutch'])
                    print(f"[Module E] Loaded clutch data for {len(self.clutch_teams)} teams, {clutch_count} CLUTCH_PERFORMERs")
                    return
            except Exception as e:
                print(f"[Module E] Live clutch load failed, using DB fallback: {e}")

        # DB fallback: derive team clutch performers from player_clutch_stats
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                """
                SELECT team_abbr,
                       SUM(clutch_pts) * 1.0 / NULLIF(SUM(clutch_fga) + 0.44 * SUM(clutch_fta), 0) AS clutch_ppp
                FROM player_clutch_stats
                WHERE game_date >= date('now', '-60 days')
                  AND team_abbr IS NOT NULL
                GROUP BY team_abbr
                HAVING COUNT(*) >= 20
                """
            )
            rows = c.fetchall()
            conn.close()

            for team, clutch_ppp in rows:
                clutch_ppp = clutch_ppp or 0.0
                diff_pct = ((clutch_ppp - config.LEAGUE_AVG_PPP) / config.LEAGUE_AVG_PPP) * 100 if config.LEAGUE_AVG_PPP else 0.0
                self.clutch_teams[team] = {
                    'clutch_ortg': clutch_ppp * 100.0,
                    'overall_ortg': config.LEAGUE_AVG_PPP * 100.0,
                    'is_clutch': diff_pct >= 8.0,
                    'diff_pct': diff_pct,
                }
            print(f"[Module E] DB clutch fallback loaded: {len(self.clutch_teams)} teams")
        except Exception as e:
            print(f"[Module E] Error loading clutch fallback data: {e}")
            self.clutch_teams = {}

    def _apply_clutch_boost(self, calibrated: dict, spread: float):
        """
        Apply +3% PTS boost for players on CLUTCH_PERFORMER teams in close games (spread < 5.0).
        """
        if not self.clutch_teams:
            return
        
        team = calibrated.get('team') or calibrated.get('TEAM_ABBREVIATION')
        if not team or spread >= 5.0:
            return
        
        clutch_data = self.clutch_teams.get(team)
        if clutch_data and clutch_data.get('is_clutch'):
            self._boost_stat(calibrated, 'proj_pts', 1.03)
            calibrated['notes'] += f" | CLUTCH_PERFORMER (+3%)"

    # ============================================================================
    # SPRINT 3: LEVERAGE GAME STATE INTELLIGENCE
    # ============================================================================

    def _load_leverage_profiles(self):
        """Load team leverage profiles from team_leverage_profiles table."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute("""
                SELECT team_abbr, vh_pace, h_pace, l_pace, overall_pace,
                       vh_efg_pct, l_efg_pct, overall_efg_pct,
                       vh_oreb_pct, l_oreb_pct, overall_oreb_pct,
                       garbage_time_boost, clutch_factor, pace_variance
                FROM team_leverage_profiles
                WHERE season = '2025-26'
            """)
            rows = c.fetchall()

            for row in rows:
                self.leverage_profiles[row[0]] = {
                    'vh_pace': row[1],
                    'h_pace': row[2],
                    'l_pace': row[3],
                    'overall_pace': row[4],
                    'vh_efg_pct': row[5],
                    'l_efg_pct': row[6],
                    'overall_efg_pct': row[7],
                    'vh_oreb_pct': row[8],
                    'l_oreb_pct': row[9],
                    'overall_oreb_pct': row[10],
                    'garbage_time_boost': row[11],
                    'clutch_factor': row[12],
                    'pace_variance': row[13]
                }

            conn.close()
            print(f"[Module E] Leverage profiles loaded: {len(self.leverage_profiles)} teams")
        except Exception as e:
            print(f"[Module E] Leverage profiles unavailable: {e}")
            self.leverage_profiles = {}

    def _load_player_leverage_usage(self):
        """Load player leverage usage from player_leverage_usage table."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            c.execute("""
                SELECT player_name, clutch_usage_rate, vh_possessions
                FROM player_leverage_usage
                WHERE season = '2025-26'
            """)
            rows = c.fetchall()

            for row in rows:
                self.player_leverage[row[0]] = {
                    'clutch_usage_rate': row[1],
                    'vh_possessions': row[2]
                }

            conn.close()
            print(f"[Module E] Player leverage usage loaded: {len(self.player_leverage)} players")
        except Exception as e:
            print(f"[Module E] Player leverage usage unavailable: {e}")
            self.player_leverage = {}

    def _apply_leverage_context(self, calibrated: dict, spread: float):
        """
        Apply game-state intelligence based on leverage profiles.

        Uses team leverage data + player leverage usage to:
        1. Adjust pace factor based on expected game state
        2. Boost crunch-time scorers in close games
        3. Adjust REB projections using OREB by leverage
        4. Validate/refine blowout expectations
        """
        team = calibrated.get('team') or calibrated.get('TEAM_ABBREVIATION')
        player_name = calibrated.get('name', '')

        if not team or team not in self.leverage_profiles:
            return

        profile = self.leverage_profiles[team]
        player_lev = self.player_leverage.get(player_name, {})
        abs_spread = abs(spread) if spread else 0

        # 1. PACE ADJUSTMENT by expected game state
        if abs_spread < 5.0 and profile.get('vh_pace') and profile.get('overall_pace'):
            pace_ratio = profile['vh_pace'] / profile['overall_pace']
            pace_mod = max(0.95, min(1.05, pace_ratio))
            if pace_mod != 1.0:
                self._boost_stat(calibrated, 'proj_pts', pace_mod)
                self._boost_stat(calibrated, 'proj_ast', pace_mod)
                self._boost_stat(calibrated, 'proj_reb', pace_mod)
                calibrated['notes'] += f" | Clutch Pace ({pace_mod:.2f})"

        elif abs_spread >= 10.0 and profile.get('l_pace') and profile.get('overall_pace'):
            pace_ratio = profile['l_pace'] / profile['overall_pace']
            pace_mod = max(0.95, min(1.05, pace_ratio))
            if pace_mod != 1.0:
                self._boost_stat(calibrated, 'proj_pts', pace_mod)
                self._boost_stat(calibrated, 'proj_ast', pace_mod)
                self._boost_stat(calibrated, 'proj_reb', pace_mod)
                calibrated['notes'] += f" | Blowout Pace ({pace_mod:.2f})"

        # 2. CRUNCH TIME USAGE BOOST
        clutch_rate = player_lev.get('clutch_usage_rate', 0) or 0
        vh_poss = player_lev.get('vh_possessions', 0) or 0
        if abs_spread < 5.0 and clutch_rate > 0.12 and vh_poss >= 30:
            boost = 1.0 + min((clutch_rate - 0.10) * 0.15, 0.03)
            self._boost_stat(calibrated, 'proj_pts', boost)
            calibrated['notes'] += f" | Crunch Time ({clutch_rate:.0%})"

        # 3. OREB BY GAME STATE
        if abs_spread >= 10.0 and profile.get('l_oreb_pct') and profile.get('overall_oreb_pct'):
            oreb_ratio = profile['l_oreb_pct'] / profile['overall_oreb_pct']
            oreb_mod = max(0.95, min(1.05, oreb_ratio))
            if oreb_mod != 1.0:
                self._boost_stat(calibrated, 'proj_reb', oreb_mod)
                self._boost_stat(calibrated, 'proj_oreb', oreb_mod)
                calibrated['notes'] += f" | Blowout REB ({oreb_mod:.2f})"

    # ============================================================================
    # SPRINT 1: SPEED/FATIGUE CONTEXT (Dormant Data Activation)
    # ============================================================================

    def _load_speed_fatigue_data(self):
        """Load speed/distance data for fatigue context from player_game_tracking."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # 30-day rolling speed/distance (baseline)
            c.execute("""
                SELECT player_name, AVG(avg_speed_off) as speed, AVG(dist_miles_off) as distance
                FROM player_game_tracking
                WHERE game_date >= date('now', '-30 days')
                  AND avg_speed_off IS NOT NULL AND dist_miles_off IS NOT NULL
                GROUP BY player_name
                HAVING COUNT(*) >= 5
            """)
            rows = c.fetchall()

            # Also load recent 5-game speed for trend detection
            c.execute("""
                SELECT player_name, AVG(avg_speed_off) as speed_recent
                FROM (
                    SELECT player_name, avg_speed_off,
                           ROW_NUMBER() OVER (PARTITION BY player_name ORDER BY game_date DESC) as rn
                    FROM player_game_tracking
                    WHERE avg_speed_off IS NOT NULL
                )
                WHERE rn <= 5
                GROUP BY player_name
                HAVING COUNT(*) >= 3
            """)
            recent_rows = c.fetchall()
            conn.close()

            recent_map = {row[0]: row[1] for row in recent_rows}

            self.speed_data = {}
            for row in rows:
                name = row[0]
                self.speed_data[name] = {
                    'speed': row[1],
                    'distance': row[2],
                    'speed_recent': recent_map.get(name)  # None if no recent data
                }

            print(f"[Module E] Speed/fatigue data loaded: {len(self.speed_data)} players")
        except Exception as e:
            print(f"[Module E] Speed/fatigue data unavailable: {e}")
            self.speed_data = {}

    def _apply_speed_fatigue_context(self, calibrated: dict):
        """
        Apply speed/fatigue modifiers based on tracking data.
        - Fast guards: +3% AST, +2% STL (hustle plays)
        - Declining speed trend: -3% across stats (fatigue flag)
        - Active bigs with high distance: +2% REB (active positioning)
        """
        if not self.speed_data:
            return

        player_name = calibrated.get('name', '')
        data = self.speed_data.get(player_name)
        if not data:
            return

        position = calibrated.get('position', '')
        speed = data.get('speed', 0)
        distance = data.get('distance', 0)
        speed_recent = data.get('speed_recent')

        is_guard = position in ('PG', 'SG', 'G', 'G-F')
        is_big = position in ('C', 'PF', 'F-C')

        # Guards with high offensive speed (>4.5 mph) = hustle plays
        if is_guard and speed > 4.5:
            self._boost_stat(calibrated, 'proj_ast', 1.03)
            # Phase 7.9.5: Removed STL boost - speed doesn't causally predict steals
            # self._boost_stat(calibrated, 'proj_stl', 1.02)
            calibrated['notes'] += " | Speed Hustle"

        # Declining speed trend: last 5 games slower than 30-day avg by >5%
        if speed_recent is not None and speed > 0:
            speed_decline = (speed - speed_recent) / speed
            if speed_decline > 0.05:
                # Fatigue flag: -3% across all stats
                self._boost_stat(calibrated, 'proj_pts', 0.97)
                self._boost_stat(calibrated, 'proj_ast', 0.97)
                self._boost_stat(calibrated, 'proj_reb', 0.97)
                calibrated['notes'] += " | Fatigue Flag"

        # Active bigs with high offensive distance (>2.0 miles) = active positioning
        if is_big and distance > 2.0:
            self._boost_stat(calibrated, 'proj_reb', 1.02)
            calibrated['notes'] += " | Active Big"

    # ============================================================================
    # SPRINT 2: TOUCHES CONTEXT (Dormant Data Activation)
    # ============================================================================

    def _load_touches_data(self):
        """Load touches data for usage refinement from player_touches table."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                SELECT player_name, touches_per_game, avg_sec_per_touch,
                       paint_touches_per_game, post_ups_per_game, pts_per_touch
                FROM player_touches
                WHERE season = '2025-26'
            """)
            rows = c.fetchall()
            conn.close()

            self.touches_data = {
                row[0]: {
                    'touches_per_game': row[1],
                    'avg_sec_per_touch': row[2],
                    'paint_touches_per_game': row[3],
                    'post_ups_per_game': row[4],
                    'pts_per_touch': row[5]
                }
                for row in rows
            }
            print(f"[Module E] Touches data loaded: {len(self.touches_data)} players")
        except Exception as e:
            print(f"[Module E] Touches data unavailable: {e}")
            self.touches_data = {}

    def _apply_touches_context(self, calibrated: dict, def_style: str = "NEUTRAL"):
        """
        Apply touches-based modifiers for usage refinement.
        - Quick decision makers (low sec/touch): +3% AST
        - Paint presence (high paint touches): +3% REB, +2% FTA
        - Post players in favorable matchups: +3% PTS
        - Efficient scorers (high pts/touch): +2% PTS
        All modifiers capped at ±5%.
        """
        if not self.touches_data:
            return

        player_name = calibrated.get('name', '')
        data = self.touches_data.get(player_name)
        if not data:
            return

        touches = data.get('touches_per_game', 0) or 0
        sec_per_touch = data.get('avg_sec_per_touch', 99) or 99
        paint_touches = data.get('paint_touches_per_game', 0) or 0
        post_ups = data.get('post_ups_per_game', 0) or 0
        pts_per_touch = data.get('pts_per_touch', 0) or 0

        # Quick decision maker: high touches + low time per touch
        if touches > 40 and sec_per_touch < 2.0:
            self._boost_stat(calibrated, 'proj_ast', 1.03)
            calibrated['notes'] += " | Quick Touch"

        # Inside presence: high paint touches
        if paint_touches > 3.0:
            self._boost_stat(calibrated, 'proj_reb', 1.03)
            self._boost_stat(calibrated, 'proj_fta', 1.02)
            calibrated['notes'] += " | Paint Presence"

        # Post player in favorable matchup (FUNNEL or PERIMETER defenses)
        if post_ups > 2.0 and def_style in ('FUNNEL', 'PERIMETER'):
            self._boost_stat(calibrated, 'proj_pts', 1.03)
            calibrated['notes'] += " | Post Mismatch"

        # Efficient scorer: high points per touch
        if pts_per_touch > 0.4:
            self._boost_stat(calibrated, 'proj_pts', 1.02)
            calibrated['notes'] += " | Efficient Touch"

    # ============================================================================
    # PHASE 6.1: DEPTH CHART INTEGRATION (Feb 2, 2026)
    # ============================================================================

    def get_starter_status(self, player_name, team_abbr=None):
        """
        Get player's depth chart status (BASIC LOOKUP - no historical analysis).

        This is a foundation method for Phase 6.1. Phase 6.2 will add
        get_effective_beneficiaries() that combines this with historical data.

        Args:
            player_name: Player's full name
            team_abbr: Team abbreviation (optional, for disambiguation)

        Returns:
            {
                "is_starter": bool,           # depth_order == 1
                "position": str,              # PG, SG, SF, PF, C
                "depth_order": int,           # 1, 2, or 3
                "team": str,                  # Team abbreviation
                "confidence": str             # "official" (from Tank01)
            }

            Returns None if player not found in depth charts
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            if team_abbr:
                # Query with team filter
                cursor.execute('''
                    SELECT team_abbr, position, depth_order
                    FROM depth_charts
                    WHERE player_name = ? AND team_abbr = ?
                    ORDER BY depth_order
                    LIMIT 1
                ''', (player_name, team_abbr))
            else:
                # Query without team filter (get first match)
                cursor.execute('''
                    SELECT team_abbr, position, depth_order
                    FROM depth_charts
                    WHERE player_name = ?
                    ORDER BY depth_order
                    LIMIT 1
                ''', (player_name,))

            row = cursor.fetchone()

            if row:
                team, position, depth_order = row
                return {
                    "is_starter": (depth_order == 1),
                    "position": position,
                    "depth_order": depth_order,
                    "team": team,
                    "confidence": "official"  # From Tank01 depth charts
                }
            else:
                return None

        except Exception as e:
            if self.debug_log:
                print(f"⚠️  Error fetching starter status for {player_name}: {e}")
            return None

        finally:
            conn.close()

    def get_backup_at_position(self, team_abbr, position, depth=2):
        """
        Get the backup player at a specific position.

        Useful for identifying who steps up when a starter is OUT.

        Args:
            team_abbr: Team abbreviation (e.g., "ATL")
            position: Position code (PG, SG, SF, PF, C)
            depth: Depth order to retrieve (default=2 for first backup)

        Returns:
            {
                "player_name": str,
                "player_id": str,
                "depth_order": int
            }

            Returns None if no player at that depth
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT player_name, player_id, depth_order
                FROM depth_charts
                WHERE team_abbr = ? AND position = ? AND depth_order = ?
                LIMIT 1
            ''', (team_abbr, position, depth))

            row = cursor.fetchone()

            if row:
                player_name, player_id, depth_order = row
                return {
                    "player_name": player_name,
                    "player_id": player_id,
                    "depth_order": depth_order
                }
            else:
                return None

        except Exception as e:
            if self.debug_log:
                print(f"⚠️  Error fetching backup at {team_abbr} {position}{depth}: {e}")
            return None

        finally:
            conn.close()

    # ========== AUDIT SPRINT: BULK PRE-LOADS ==========

    def _load_synergy_playtypes_bulk(self):
        """Pre-load all player synergy playtypes at init.
        Keyed by _canonical_key(player_name). Uses player_canonical_ids for name resolution."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT normalized_name, full_name FROM player_canonical_ids")
            canonical_map = {row[0]: row[1] for row in c.fetchall()}
            c.execute("""
                SELECT player_name, playtype, freq_pct, ppp, poss_per_game
                FROM player_synergy_playtypes
                WHERE season = '2025-26'
            """)
            data = {}
            for raw_name, playtype, freq, ppp, poss in c.fetchall():
                key = _canonical_key(raw_name)
                resolved = canonical_map.get(key, raw_name)
                canonical_key = _canonical_key(resolved)
                if canonical_key not in data:
                    data[canonical_key] = []
                data[canonical_key].append({
                    'playtype': playtype, 'frequency': freq,
                    'ppp': ppp, 'possession_count': poss
                })
            conn.close()
            print(f"   [CAL] Synergy cache: {len(data)} players loaded")
            return data
        except Exception as e:
            print(f"   [CAL] Synergy pre-load error: {e}")
            return {}

    def _load_shot_quality_bulk(self) -> dict:
        """Pre-load player_shot_quality into {canonical_key: {rim_freq, corner_3_freq}} dict."""
        out = {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT player_name, at_rim_freq, corner_3_freq "
                    "FROM player_shot_quality"
                ).fetchall()
            for player_name, at_rim, corner_3 in rows:
                out[_canonical_key(player_name)] = {
                    'rim_freq': at_rim or 0,
                    'corner_3_freq': corner_3 or 0,
                }
            print(f"   [CAL] Shot quality bulk load: {len(out)} players")
        except Exception as e:
            print(f"[Module E] shot_quality bulk load failed: {e}")
        return out

    def _load_tracking_stats_bulk(self):
        """Pre-load player tracking stats (last 15 games) at init.
        Uses CTE game-count window — NOT days — to handle schedule density variation."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT normalized_name, full_name FROM player_canonical_ids")
            canonical_map = {row[0]: row[1] for row in c.fetchall()}
            c.execute("""
                WITH ranked AS (
                    SELECT player_name, avg_speed_off, distance, drives_fga,
                           catch_shoot_fga, pull_up_fga,
                           ROW_NUMBER() OVER (
                               PARTITION BY player_name
                               ORDER BY game_date DESC
                           ) as rn
                    FROM player_game_tracking
                    WHERE game_date >= date('now', '-90 days')
                )
                SELECT player_name,
                       AVG(avg_speed_off)  as avg_speed,
                       AVG(distance)       as avg_dist,
                       AVG(drives_fga)    as avg_drives,
                       AVG(catch_shoot_fga) as avg_cs,
                       AVG(pull_up_fga)   as avg_pu,
                       COUNT(*)           as games_count
                FROM ranked
                WHERE rn <= 15
                GROUP BY player_name
                HAVING games_count >= 3
            """)
            data = {}
            for name, speed, dist, drives, cs, pu, g in c.fetchall():
                key = _canonical_key(name)
                resolved = canonical_map.get(key, name)
                canonical_key = _canonical_key(resolved)
                data[canonical_key] = {
                    'speed_mph': speed or 0, 'dist_miles': dist or 0,
                    'drives': drives or 0, 'catch_shoot_fga': cs or 0,
                    'pull_up_fga': pu or 0, 'games': g
                }
            conn.close()
            print(f"   [CAL] Tracking cache: {len(data)} players loaded (last 15 games)")
            return data
        except Exception as e:
            print(f"   [CAL] Tracking pre-load error: {e}")
            return {}

    def _load_player_type_profiles(self):
        """Pre-load unified player profiles. Keyed by _canonical_key(player_name).
        archetype_in_top3=1 = archetype validates against synergy (HIGH confidence)."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT normalized_name, full_name FROM player_canonical_ids")
            canonical_map = {row[0]: row[1] for row in c.fetchall()}
            c.execute("""
                SELECT tp.player_name, tp.archetype, tp.defensive_tag,
                       tp.synergy_type_1, tp.synergy_freq_1,
                       tp.archetype_in_top3, tp.position_synergy_match,
                       tp.synergy_dominance
                FROM player_type_profiles tp
                WHERE tp.season = '2025-26'
            """)
            data = {}
            for raw_name, arch, def_tag, syn1, freq1, in_top3, pos_match, dominance in c.fetchall():
                key = _canonical_key(raw_name)
                resolved = canonical_map.get(key, raw_name)
                canonical_key = _canonical_key(resolved)
                data[canonical_key] = {
                    'archetype': arch,
                    'defensive_tag': def_tag,
                    'primary_synergy': syn1,
                    'primary_freq': freq1,
                    'archetype_validated': bool(in_top3),
                    'position_match': bool(pos_match),
                    'dominance': dominance
                }
            conn.close()
            print(f"   [CAL] TypeProfiles cache: {len(data)} players loaded")
            return data
        except Exception as e:
            print(f"   [CAL] TypeProfiles load error: {e}")
            return {}

    def _load_dvp_by_archetype(self):
        """Pre-load team DVP by archetype for data-driven matchup modulation."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                SELECT opponent_team, archetype, pts_vs_baseline, rank_pts, data_confidence
                FROM team_dvp_by_archetype
                WHERE data_confidence IN ('HIGH', 'MEDIUM')
            """)
            data = {}
            for team, arch, baseline, rank, conf in c.fetchall():
                data[(team.upper(), arch)] = {
                    'pts_vs_baseline': float(baseline or 0),
                    'rank_pts': int(rank or 15),
                    'conf': conf
                }
            conn.close()
            print(f"   [CAL] DVP by archetype: {len(data)} team-archetype combos loaded")
            return data
        except Exception as e:
            print(f"   [CAL] DVP pre-load error: {e}")
            return {}

    def _load_archetype_vs_defense_matrix(self):
        """Pre-load system bet performance by archetype × defense type.
        Confidence tiers: HIGH > 100 bets, MEDIUM 30-100, LOW < 30."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                SELECT archetype, defense_type, win_rate, avg_edge,
                       pts_vs_baseline, games
                FROM player_archetype_vs_defense
            """)
            data = {}
            for arch, def_type, wr, edge, baseline, g in c.fetchall():
                tier = 'HIGH' if g >= 100 else ('MEDIUM' if g >= 30 else 'LOW')
                data[(arch, def_type)] = {
                    'win_rate': float(wr or 0.5),
                    'avg_edge': float(edge or 0),
                    'pts_vs_baseline': float(baseline or 0),
                    'games': int(g or 0),
                    'confidence': tier
                }
            conn.close()
            print(f"   [CAL] ArchVsDef matrix: {len(data)} matchup combos loaded")
            return data
        except Exception as e:
            print(f"   [CAL] ArchVsDef load error: {e}")
            return {}

    def _load_b2b_splits(self):
        """Pre-load player-specific B2B performance deltas (last 90 days).
        Delta = (avg stats on B2B games) / (avg stats on rested games) - 1.0"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                WITH tagged AS (
                    SELECT
                        pgl.player_name,
                        pgl.pts, pgl.minutes,
                        pgl.game_date,
                        LAG(pgl.game_date) OVER (
                            PARTITION BY pgl.player_name ORDER BY pgl.game_date
                        ) as prev_date
                    FROM player_game_logs pgl
                    WHERE pgl.game_date >= date('now', '-90 days')
                      AND pgl.minutes >= 10
                )
                SELECT
                    player_name,
                    AVG(CASE WHEN julianday(game_date) - julianday(prev_date) <= 1.5
                             THEN pts END) as b2b_pts,
                    AVG(CASE WHEN julianday(game_date) - julianday(prev_date) > 1.5
                             THEN pts END) as rest_pts,
                    AVG(CASE WHEN julianday(game_date) - julianday(prev_date) <= 1.5
                             THEN minutes END) as b2b_min,
                    AVG(CASE WHEN julianday(game_date) - julianday(prev_date) > 1.5
                             THEN minutes END) as rest_min,
                    SUM(CASE WHEN julianday(game_date) - julianday(prev_date) <= 1.5
                             THEN 1 ELSE 0 END) as b2b_games,
                    COUNT(*) as total_games
                FROM tagged
                WHERE prev_date IS NOT NULL
                GROUP BY player_name
                HAVING b2b_games >= 3
            """)
            data = {}
            for name, b2b_pts, rest_pts, b2b_min, rest_min, b2b_g, total_g in c.fetchall():
                if rest_pts and rest_pts > 0:
                    pts_delta = (b2b_pts / rest_pts) - 1.0
                else:
                    pts_delta = -0.04
                if rest_min and rest_min > 0:
                    min_delta = (b2b_min / rest_min) - 1.0
                else:
                    min_delta = -0.02
                key = _canonical_key(name)
                data[key] = {
                    'pts_delta': max(-0.15, min(0.05, pts_delta)),
                    'min_delta': max(-0.12, min(0.05, min_delta)),
                    'b2b_games': b2b_g,
                    'confidence': 'HIGH' if b2b_g >= 8 else 'MEDIUM'
                }
            conn.close()
            print(f"   [CAL] B2B splits: {len(data)} players with actual data")
            return data
        except Exception as e:
            print(f"   [CAL] B2B splits load error: {e}")
            return {}

    def _get_dvp_modulator(self, opponent_team: str, archetype: str, def_style: str) -> float:
        """Returns a multiplier to apply ON TOP of the base hardcoded boost.
        If DVP data shows opponent is truly weak vs this archetype → amplify boost.
        If DVP data shows opponent is strong → dampen boost.
        Cap at ±8% total modulation to prevent overcorrection."""
        dvp = self.dvp_by_archetype.get((opponent_team.upper(), archetype))
        if not dvp:
            return 1.0
        baseline = dvp['pts_vs_baseline']
        raw_modulation = baseline * 0.005
        clamped = max(-0.08, min(0.08, raw_modulation))
        avd = self.archetype_vs_defense_matrix.get((archetype, def_style))
        if avd and avd['confidence'] == 'LOW':
            clamped = clamped * 0.5
        return 1.0 + clamped


if __name__ == "__main__":
    calib = LudiCalibrator()
    print("Module E (2025-26 Season) Calibrator Loaded.")
