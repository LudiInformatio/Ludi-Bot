import pandas as pd
import sqlite3
import json
from pathlib import Path
from utils.player_id_resolver import PlayerIDResolver

# ==========================================
# LUDI INFORMATIO | MODULE E: THE CALIBRATOR
# V7.0 - SECONDARY PLAYTYPE SYSTEM (Week 2 Integration)
# ==========================================

class LudiCalibrator:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE E (CALIBRATOR V7.0) ONLINE")
        print(f"   >>> SECONDARY PLAYTYPE SYSTEM ACTIVE")
        print(f"{'='*40}")
        
        self.id_resolver = PlayerIDResolver()
        
        self.ADJUSTMENT_RULES = {
            "MINUTES_LIMIT": 0.75,   
            "PROMOTION": 1.50,       
            "OUT": 0.0              
        }
        
        # 2025-26 UPDATED DEFENSIVE STYLES
        self.DEFENSIVE_STYLES = {
            "OKC": "PAINT_PACK", "BOS": "PAINT_PACK", "DET": "PAINT_PACK",
            "MIN": "PAINT_PACK", "SAS": "PAINT_PACK", "ORL": "PAINT_PACK",
            "LAL": "PAINT_PACK", "CLE": "PAINT_PACK", "MEM": "PAINT_PACK",
            "MIL": "PAINT_PACK", "PHI": "PAINT_PACK",
            "HOU": "BLITZ", "TOR": "BLITZ", "MIA": "BLITZ", "PHX": "BLITZ", "BKN": "BLITZ",
            "GSW": "PERIMETER", "DAL": "PERIMETER", "NYK": "PERIMETER", "LAC": "PERIMETER", "NOP": "PERIMETER",
            "WAS": "FUNNEL", "ATL": "FUNNEL", "CHI": "FUNNEL", "UTA": "FUNNEL", "SAC": "FUNNEL", "DEN": "FUNNEL",
            "IND": "HACKERS", "CHA": "HACKERS", "POR": "HACKERS"
        }

        # MANUAL OVERRIDES (The "Scout's Eye")
        self.MANUAL_OVERRIDES = {
            "domantassabonis": "HUB_BIG",
            "draymondgreen": "HUB_BIG"
        }

        # === POSITION-ARCHETYPE AFFINITY MATRIX (Week 2 Enhancement) ===
        # Position refines archetype selection when multiple stat matches exist
        # Higher score = stronger affinity for that position
        self.POSITION_ARCHETYPE_AFFINITY = {
            # Centers: Prioritize big archetypes over guard archetypes
            'C': {
                'HUB_BIG': 1.0,        # Strongest affinity (Jokic, Sabonis)
                'STRETCH_BIG': 0.9,    # High affinity (KAT, Porzingis)
                'RIM_RUNNER': 0.8,     # Natural fit (Capela, Gobert)
                'HELIOCENTRIC': 0.3,   # Low affinity (rare center ballhandlers)
                'JUMBO_CREATOR': 0.2,  # Very rare (penalize)
            },

            # Forwards: Balanced, slight preference for versatile archetypes
            'F': {
                'JUMBO_CREATOR': 1.0,  # LeBron, Giannis (when passing)
                'SLASHER': 0.9,        # Giannis, Zion
                'ELITE_SCORER': 0.9,   # Tatum, Durant
                'STRETCH_BIG': 0.7,    # Forwards who play big
                'TWO_WAY_WING': 0.8,   # Kawhi, Butler
            },

            # Guards: Prioritize ball-handler archetypes
            'G': {
                'HELIOCENTRIC': 1.0,   # Luka, Trae (guard engines)
                'JUMBO_CREATOR': 0.9,  # LeBron-like guards (tall creators)
                'FACILITATOR': 0.9,    # CP3, Rondo
                'SNIPER': 0.8,         # Curry, Dame (shooters)
                'ELITE_SCORER': 0.8,   # Scoring guards
                'HUB_BIG': 0.1,        # Very rare (penalize heavily)
            },

            # Unknown: No preference (existing logic)
            'UNK': {}  # Empty dict = no affinity bonuses
        }

        # === SECONDARY PLAYTYPE SYSTEM (Week 2 Integration) ===
        # Position-based filtering: Guards create, wings cut/shoot, bigs finish
        self.POSITION_ELIGIBILITY = {
            'G': ['ISO_SCORER', 'P&R_HANDLER', 'SPOT_UP', 'TRANSITION'],
            'G-F': ['ISO_SCORER', 'P&R_HANDLER', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION'],
            'F': ['ISO_SCORER', 'P&R_HANDLER', 'P&R_ROLL_MAN', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION'],
            'F-C': ['P&R_ROLL_MAN', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION', 'PUTBACK', 'POST_UP'],
            'C': ['P&R_ROLL_MAN', 'OFF_BALL_CUTTER', 'PUTBACK', 'POST_UP', 'SPOT_UP', 'TRANSITION'],
            'UNK': ['ISO_SCORER', 'P&R_HANDLER', 'P&R_ROLL_MAN', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION', 'PUTBACK', 'POST_UP']
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
        self.db_path = Path(__file__).parent / 'ludi.db'
        self.config_path = Path(__file__).parent / 'config' / 'playtype_thresholds.json'
        self.playtype_thresholds = self._load_playtype_thresholds()

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
        except: return {'base_stl': 0, 'base_blk': 0, 'base_usg': 0.20}

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
        'PUTBACK': 'PUTBACK'
    }
    
    def _get_synergy_playtypes(self, player_name: str, min_freq: float = 5.0) -> list:
        """
        Get official Synergy playtypes from database.
        Returns list of (playtype_tag, freq_pct, ppp) sorted by frequency.
        
        Args:
            player_name: Player name to lookup
            min_freq: Minimum frequency % to qualify (default 5%)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT playtype, freq_pct, ppp, percentile
                FROM player_synergy_playtypes
                WHERE player_name = ? 
                AND season = '2025-26'
                AND freq_pct >= ?
                ORDER BY freq_pct DESC
                LIMIT 4
            """, (player_name, min_freq))
            
            results = cursor.fetchall()
            conn.close()
            
            # Convert Synergy tags to our format
            playtypes = []
            for row in results:
                synergy_tag, freq, ppp, percentile = row
                our_tag = self.SYNERGY_TO_TAG.get(synergy_tag)
                if our_tag:
                    playtypes.append((our_tag, freq, ppp, percentile))
            
            return playtypes
            
        except Exception as e:
            # print(f"⚠️ Synergy lookup error: {e}")
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
        Get tracking stats for a player from database.
        Uses PlayerIDResolver to handle accents and ID changes.
        Returns empty dict if not found.
        """
        try:
            # Step 1: Resolve to canonical NBA ID and get player info
            try:
                canonical_id = self.id_resolver.resolve_to_canonical_id(player_name_or_id)
                player_info = self.id_resolver.get_player_info(canonical_id)
                canonical_name = player_info.get('full_name', player_name_or_id)
            except ValueError:
                # Player not found in canonical system
                return {}

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Step 2: Query tracking data by player_name (not nba_player_id - that contains slugs)
            tracking_query = """
            SELECT
                AVG(drives_fga) as avg_drives,
                AVG(drives_pass_pct) as avg_drives_pass_pct,
                AVG(catch_shoot_fga) as avg_cs_fga,
                AVG(CAST(catch_shoot_fgm AS FLOAT) / NULLIF(catch_shoot_fga, 0)) as cs_pct,
                AVG(catch_shoot_3pa) as avg_cs_3pa,
                AVG(pull_up_fga) as avg_pu_fga,
                AVG(CAST(pull_up_fgm AS FLOAT) / NULLIF(pull_up_fga, 0)) as pu_pct,
                AVG(avg_speed_off) as avg_speed,
                AVG(dist_miles_off) as avg_distance,
                COUNT(*) as games
            FROM player_game_tracking
            WHERE player_name = ? AND game_date >= date('now', ?)
            """
            cursor.execute(tracking_query, (canonical_name, f'-{days} days'))
            row = cursor.fetchone()
            
            if not row or row[9] < 3:  # Need at least 3 games
                conn.close()
                return {}
            
            tracking_stats = {
                'avg_drives': row[0] or 0,
                'avg_drives_pass_pct': row[1] or 0,
                'avg_cs_fga': row[2] or 0,
                'cs_pct': row[3] or 0,
                'avg_cs_3pa': row[4] or 0,
                'avg_pu_fga': row[5] or 0,
                'pu_pct': row[6] or 0,
                'avg_speed': row[7] or 0,
                'avg_distance': row[8] or 0,
                'tracking_games': row[9]
            }
            
            # Step 3: Get shot quality (rim_freq)
            # Query by canonical_id (stored as player_id in this table for now, or ensure mapping)
            # The original code queried by player_id from players table. 
            # Now we use canonical_id which maps to NBA ID.
            shot_query = """
            SELECT at_rim_freq, corner_3_freq 
            FROM player_shot_quality 
            WHERE player_id = ? AND season = '2025-26'
            """
            cursor.execute(shot_query, (canonical_id,))
            shot_row = cursor.fetchone()
            
            if shot_row:
                tracking_stats['rim_freq'] = shot_row[0] or 0
                tracking_stats['corner_3_freq'] = shot_row[1] or 0
            
            # Step 4: Get Position (from canonical table - already fetched earlier)
            if player_info.get('position'):
                tracking_stats['position'] = player_info['position']
            
            conn.close()
            return tracking_stats
            
        except Exception as e:
            # print(f"DEBUG: Error in _get_tracking_stats: {e}")
            return {}


    def calibrate_player(self, player_packet, yak_report, use_synergy=True):
        calibrated = player_packet.copy()
        if 'notes' not in calibrated: calibrated['notes'] = ""

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

        # 1. ASSIGN PRIMARY ARCHETYPE (now has position field)
        archetype, secondary_arch = self._assign_archetype(calibrated)
        
        if archetype:
            calibrated['archetype'] = archetype
            calibrated['notes'] += f" [{archetype}]"
        if secondary_arch:
            calibrated['secondary_archetype'] = secondary_arch
            calibrated['notes'] += f" / {secondary_arch}"

        # 2. ASSIGN SECONDARY PLAYTYPES (Week 2 Integration)
        player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))
        tracking_data = self._get_tracking_stats(player_name)
        
        if tracking_data:
            # Merge position into calibrated if found
            if 'position' in tracking_data and tracking_data['position'] != 'UNK':
                calibrated['position'] = tracking_data['position']
            
            # Select top 1-2 secondary playtypes
            sec_primary, sec_secondary = self._select_top_playtypes(tracking_data)
            
            if sec_primary or sec_secondary:
                secondary_tags = [t for t in [sec_primary, sec_secondary] if t]
                calibrated['secondary_playtypes'] = secondary_tags
                
                # Format: PRIMARY + SECONDARY for notes
                if sec_primary and sec_secondary:
                    calibrated['notes'] += f" +{sec_primary}+{sec_secondary}"
                elif sec_primary:
                    calibrated['notes'] += f" +{sec_primary}"

        # 3. NEWS CALIBRATION
        status = yak_report.get('status', 'ACTIVE')
        if status == "OUT":
            self._zero_out(calibrated)
            calibrated['notes'] += " | Official OUT"
            return calibrated
        elif status == "MINUTES_LIMIT":
            self._apply_factor(calibrated, self.ADJUSTMENT_RULES["MINUTES_LIMIT"])
            calibrated['notes'] += f" | 15-min Update: Limit Applied"

        # 3.5 SCHEDULE FATIGUE (Week 3 Integration)
        is_b2b = yak_report.get('is_back_to_back', False)
        is_road = yak_report.get('is_road', False)
        next_game_tomorrow = yak_report.get('next_game_tomorrow', False)
        density_5day = yak_report.get('games_in_last_5_days', 0)
        
        # B2B Penalties (Back End)
        if is_b2b:
            b2b_factor = 0.97 # Base Home B2B (-3%)
            note = " | Home B2B"
            
            if is_road:
                b2b_factor = 0.94 # Road B2B (-6%)
                note = " | Road B2B (Fatigue)"
                
            # Guard Tax (High active output requires legs)
            pos = calibrated.get('position', 'UNK')
            # print(f"DEBUG: Checking Guard Tax for {calibrated.get('name')} | Pos: {pos}")
            if any(x in pos for x in ['G', 'PG', 'SG']):
                b2b_factor *= 0.96 # Additional -4%
                note += " + Guard Tax"
                
            self._apply_factor(calibrated, b2b_factor)
            calibrated['notes'] += note

        # Schedule Density (4-in-5 Nights)
        # If played 3 games in last 4 days (density=3) + Today = 4 games in 5 nights
        if density_5day >= 3:
            self._apply_factor(calibrated, 0.98)
            calibrated['notes'] += " | 4-in-5 Density Tax"
            
        # Front-End Load Management (Star Players)
        # If playing today AND game tomorrow (Front End of B2B)
        is_star = calibrated.get('base_pts', 0) > 22.0 or calibrated.get('base_usg', 0) > 0.28
        if next_game_tomorrow and is_star:
            # Stars often play slightly less or conserve energy on front end
            self._boost_stat(calibrated, 'proj_min', 0.96) # -4% minutes (~1.5 min)
            calibrated['notes'] += " | B2B Front-End (Load Mgmt)"

        # 4. GAME SCRIPT
        odds = calibrated.get('odds', {})
        total = float(odds.get('total', 0)) if odds.get('total') else 0
        spread = abs(float(odds.get('spread', 0))) if odds.get('spread') else 0
        
        # REMOVED: Blowout tax consolidated to Module F (smart blowout_tax.py)
        # Old logic: if spread > 12.5 → -6% for starters
        # New logic: Context-aware (favorite/underdog, starter/bench) in Module F
        
        if total > 238.0: self._apply_factor(calibrated, 1.03)
        elif total > 0 and total < 218.0: self._apply_factor(calibrated, 0.97)

        # 5. MATCHUP LOGIC (Primary Archetypes)
        opponent = calibrated.get('opponent', 'UNK') 
        def_style = self.DEFENSIVE_STYLES.get(opponent, "NEUTRAL")
        
        if archetype == "STRETCH_BIG" and def_style == "PAINT_PACK":
            self._boost_stat(calibrated, 'proj_3pm', 1.15)
            self._boost_stat(calibrated, 'proj_3pa', 1.15)
            calibrated['notes'] += f" | {opponent} Paint Pack Edge"
        elif archetype == "SLASHER" and def_style == "HACKERS":
            self._boost_stat(calibrated, 'proj_fta', 1.20)
            self._boost_stat(calibrated, 'proj_pts', 1.05)
            calibrated['notes'] += " | Foul Drawn Magnet"
        elif archetype == "RIM_RUNNER" and def_style == "PERIMETER":
            self._boost_stat(calibrated, 'proj_oreb', 1.30)
            self._boost_stat(calibrated, 'proj_reb', 1.15)
            calibrated['notes'] += " | Size Advantage (O-Boards)"
        elif archetype == "HELIOCENTRIC" and def_style == "BLITZ":
            self._boost_stat(calibrated, 'proj_ast', 1.18)
            self._boost_stat(calibrated, 'proj_pts', 0.92)
            self._boost_stat(calibrated, 'proj_tov', 1.10)
            calibrated['notes'] += " | Trap Scheme (Pass-First)"
        elif archetype == "TWO_WAY_WING" and def_style == "FUNNEL":
            self._boost_stat(calibrated, 'proj_3pa', 1.12)
            self._boost_stat(calibrated, 'proj_stl', 1.15)
            calibrated['notes'] += " | High Pace Target"
        elif archetype == "ELITE_SCORER" and def_style == "PERIMETER":
            self._boost_stat(calibrated, 'proj_pts', 1.08)
            self._boost_stat(calibrated, 'proj_3pm', 1.10)
            calibrated['notes'] += " | ISO Mismatch"
        elif archetype == "HUB_BIG" and def_style == "PERIMETER":
            self._boost_stat(calibrated, 'proj_ast', 1.12)
            self._boost_stat(calibrated, 'proj_reb', 1.15)
            calibrated['notes'] += " | Size Mismatch Hub"
        elif archetype == "JUMBO_CREATOR" and def_style == "PERIMETER":
            self._boost_stat(calibrated, 'proj_pts', 1.08)
            self._boost_stat(calibrated, 'proj_reb', 1.10)
            calibrated['notes'] += " | Size Mismatch (Guard)"

        # 6. SECONDARY PLAYTYPE MATCHUPS (Week 2 - 14 Total Modifiers)
        # Research-validated matchups from NBA.com, Basketball Index, FanSided
        sec_playtypes = calibrated.get('secondary_playtypes', [])

        for sec_pt in sec_playtypes:
            # === ISO_SCORER MATCHUPS (3 total) ===
            if sec_pt == 'ISO_SCORER':
                if def_style == 'BLITZ':
                    # Blitz defense disrupts isolation (research: +15% TOV rate)
                    self._boost_stat(calibrated, 'proj_pts', 0.92)
                    self._boost_stat(calibrated, 'proj_tov', 1.12)
                    calibrated['notes'] += " | ISO Tax vs Blitz"
                elif def_style == 'PERIMETER':
                    # ISO mismatch vs perimeter switching
                    self._boost_stat(calibrated, 'proj_pts', 1.10)
                    calibrated['notes'] += " | ISO vs Perimeter"

            # === P&R_HANDLER MATCHUPS (3 total) ===
            elif sec_pt == 'P&R_HANDLER':
                if def_style == 'PAINT_PACK':
                    # Drop coverage gives P&R handlers easy assists
                    self._boost_stat(calibrated, 'proj_ast', 1.08)
                    calibrated['notes'] += " | P&R Drop Edge"
                elif def_style == 'BLITZ':
                    # Blitz forces tough passes, more turnovers
                    self._boost_stat(calibrated, 'proj_ast', 0.90)
                    self._boost_stat(calibrated, 'proj_tov', 1.15)
                    calibrated['notes'] += " | P&R Blitz Tax"
                elif def_style == 'FUNNEL':
                    # Funnel defense creates passing lanes
                    self._boost_stat(calibrated, 'proj_ast', 1.12)
                    calibrated['notes'] += " | PnR Handler vs Funnel"

            # === SPOT_UP MATCHUPS (2 total - HIGHEST ROI) ===
            elif sec_pt == 'SPOT_UP':
                if def_style == 'PAINT_PACK':
                    # Paint-pack leaves shooters open (strongest edge)
                    self._boost_stat(calibrated, 'proj_3pm', 1.15)
                    calibrated['notes'] += " | Spot-Up vs Pack"
                elif def_style == 'PERIMETER':
                    # Perimeter switching closes out shooters
                    self._boost_stat(calibrated, 'proj_3pm', 0.95)
                    calibrated['notes'] += " | Spot-Up Tax"

            # === TRANSITION MATCHUPS (3 total) ===
            elif sec_pt == 'TRANSITION':
                if def_style == 'FUNNEL':
                    # Funnel defense vulnerable in transition
                    self._boost_stat(calibrated, 'proj_pts', 1.15)
                    calibrated['notes'] += " | Transition Chaos"
                elif def_style == 'PAINT_PACK':
                    # Set defense slows transition
                    self._boost_stat(calibrated, 'proj_pts', 0.92)
                    calibrated['notes'] += " | Transition Tax"
                elif def_style == 'HACKERS':
                    # Hackers create fast break opportunities
                    self._boost_stat(calibrated, 'proj_pts', 1.08)
                    calibrated['notes'] += " | Fast Break Edge"

            # === P&R_ROLL_MAN MATCHUPS (3 total) ===
            elif sec_pt == 'P&R_ROLL_MAN':
                if def_style == 'PAINT_PACK':
                    # Drop coverage = easy dunks for roll man
                    self._boost_stat(calibrated, 'proj_pts', 1.15)
                    self._boost_stat(calibrated, 'proj_fg_pct', 1.10)
                    calibrated['notes'] += " | Roll Man vs Drop"
                elif def_style == 'BLITZ':
                    # Blitz limits roll opportunities
                    self._boost_stat(calibrated, 'proj_pts', 0.88)
                    calibrated['notes'] += " | Roll Man Tax"
                elif def_style == 'PERIMETER':
                    # Small ball = boards + mismatches
                    self._boost_stat(calibrated, 'proj_reb', 1.15)
                    self._boost_stat(calibrated, 'proj_pts', 1.10)
                    calibrated['notes'] += " | Roll Man vs Small Ball"

            # === OFF_BALL_CUTTER MATCHUPS (3 total) ===
            elif sec_pt == 'OFF_BALL_CUTTER':
                if def_style == 'PERIMETER':
                    # Small ball vulnerable to cutters
                    self._boost_stat(calibrated, 'proj_pts', 1.12)
                    calibrated['notes'] += " | Cutter vs Small Ball"
                elif def_style == 'PAINT_PACK':
                    # Rim protection reduces cutter efficiency
                    self._boost_stat(calibrated, 'proj_fg_pct', 0.90)
                    calibrated['notes'] += " | Cutter Tax"
                elif def_style == 'BLITZ':
                    # Blitz creates cutting lanes
                    self._boost_stat(calibrated, 'proj_pts', 1.12)
                    calibrated['notes'] += " | Cutter vs Blitz"

            # === PUTBACK MATCHUP (1 total) ===
            elif sec_pt == 'PUTBACK':
                if def_style == 'PERIMETER':
                    # Small ball = offensive glass dominance
                    self._boost_stat(calibrated, 'proj_oreb', 1.25)
                    calibrated['notes'] += " | Putback vs Small"

            # === POST_UP MATCHUP (1 total) ===
            elif sec_pt == 'POST_UP':
                if def_style == 'PERIMETER':
                    # Post mismatch vs small ball
                    self._boost_stat(calibrated, 'proj_pts', 1.15)
                    calibrated['notes'] += " | Post vs Small Ball"

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
            if archetype == "SLASHER":
                calibrated['notes'] += " | Confirmed Rim Pressure"

        # C) Corner Specialist Logic
        # Corner 3s are the counter to 'PAINT_PACK' defenses
        if corner_freq > 0.20 and def_style == "PAINT_PACK":
            self._boost_stat(calibrated, 'proj_3pm', 1.12)
            calibrated['notes'] += " | Corner Specialist vs Pack"

        # === 8. NUANCE CHECKS ===
        # Westbrook/Giddey Rule: Guards who crash boards
        if archetype in ["FACILITATOR", "GENERALIST", "JUMBO_CREATOR"] and calibrated.get('base_reb', 0) > 5.5:
            self._boost_stat(calibrated, 'proj_reb', 1.10)
            calibrated['notes'] += " | Hustle Guard"

        return calibrated


    def _assign_archetype(self, p):
        # 0. MANUAL OVERRIDE
        raw_name = p.get('name', p.get('PLAYER_NAME', ''))
        clean_name = raw_name.lower().replace(' ', '').replace('.', '').replace("'", "").replace('-', '')
        if clean_name in self.MANUAL_OVERRIDES:
            return self.MANUAL_OVERRIDES[clean_name], None

        # Extract Position (NEW - Week 2 Enhancement)
        position = p.get('position', 'UNK')

        # Normalize multi-position to primary (G-F → G, F-C → F)
        if position in ('G-F', 'SG', 'PG'):
            position = 'G'
        elif position in ('F-C', 'SF', 'PF'):
            position = 'F'
        elif position in ('C',):
            position = 'C'
        else:
            position = 'UNK'  # Missing data or unrecognized

        # Extract Stats
        pts = float(p.get('base_pts', 0) or 0)
        reb = float(p.get('base_reb', 0) or 0)
        ast = float(p.get('base_ast', 0) or 0)
        tpm = float(p.get('base_3pm', 0) or 0)
        usg = float(p.get('base_usg', 0) or 0)
        stl = float(p.get('base_stl', 0) or 0)
        blk = float(p.get('base_blk', 0) or 0)
        
        # Fallback Logic
        if stl == 0 and blk == 0 and usg == 0:
            team = p.get('team', p.get('TEAM_ABBREVIATION', ''))
            if raw_name:
                miss = self._fetch_missing_stats(raw_name, team)
                stl = miss.get('base_stl', 0)
                blk = miss.get('base_blk', 0)
                usg = miss.get('base_usg', 0)

        stocks = stl + blk
        matches = []

        # === TIER 1: ENGINES ===
        # HELIOCENTRIC: Usage > 30% OR (Usage > 28% and High Assists)
        if (usg > 0.30 and ast > 6.0) or (usg > 0.28 and ast > 8.0):
            matches.append("HELIOCENTRIC")

        # SLASHER: High PTS, Low 3PM
        if pts > 22.0 and usg > 0.30 and tpm < 2.0:
            matches.append("SLASHER")

        # ELITE_SCORER: High PTS, High 3PM
        if pts > 24.5 and tpm > 2.4:
            matches.append("ELITE_SCORER")

        # === TIER 2: REBOUNDING CREATORS ===
        
        # HUB_BIG: Elite Reb, Elite Pass, BIG Traits (Reb > Ast OR High Blk)
        if reb > 7.5 and ast > 4.2 and (reb > ast or blk > 0.6):
            matches.append("HUB_BIG")

        # JUMBO_CREATOR: High Reb, High Pass, GUARD Traits (Ast >= Reb OR Low Blk)
        if reb > 6.0 and ast > 5.0 and (ast >= reb or blk <= 0.5):
            matches.append("JUMBO_CREATOR")

        # === TIER 3: SPECIALISTS ===
        
        # STRETCH_BIG: Reb + 3PM, Low Assist (Not a creator)
        if reb > 6.5 and tpm > 1.8 and ast < 4.0:
            matches.append("STRETCH_BIG")

        # RIM_RUNNER: Elite Reb, No 3s
        if reb > 8.0 and tpm < 0.6 and ast < 3.0:
            matches.append("RIM_RUNNER")

        # SNIPER: High 3PM
        if tpm > 2.8 and ast < 3.5:
            matches.append("SNIPER")

        # === TIER 4: ROLE PLAYERS ===
        
        # TWO_WAY_WING: Defense + 3s
        if stocks >= 1.8 and tpm >= 1.5 and pts < 22.0:
            matches.append("TWO_WAY_WING")

        # FACILITATOR: High Ast, Low Usg
        if ast >= 5.0 and pts < 15.0 and usg < 0.28:
            matches.append("FACILITATOR")

        # === SELECTION ===
        if not matches:
            return "GENERALIST", None

        # Apply position-based priority if multiple matches (Week 2 Enhancement)
        if len(matches) > 1 and position in self.POSITION_ARCHETYPE_AFFINITY:
            affinity_scores = []
            for archetype in matches:
                # Get affinity score, default to 0.5 if archetype not in position's affinity map
                affinity = self.POSITION_ARCHETYPE_AFFINITY[position].get(archetype, 0.5)
                affinity_scores.append((archetype, affinity))

            # Sort by affinity (highest first)
            affinity_scores.sort(key=lambda x: x[1], reverse=True)

            primary = affinity_scores[0][0]
            secondary = affinity_scores[1][0] if len(affinity_scores) > 1 else None

            return primary, secondary
        else:
            # No position data or single match - use existing priority
            return matches[0], (matches[1] if len(matches) > 1 else None)

    # === SYNERGY EFFICIENCY CALIBRATIONS (Phase 1 - Jan 21, 2026) ===

    def _apply_synergy_ppp_efficiency(self, calibrated: dict, opponent_abbr: str) -> None:
        """
        Apply Synergy PPP (Points Per Possession) efficiency modifier.

        Uses weighted PPP across player's primary playtypes to calibrate points projection.
        High-efficiency players (PPP > 1.10) get boost, low-efficiency get penalty.

        Args:
            calibrated: Player packet with projections
            opponent_abbr: Opponent team abbreviation (not used yet, for future matchup logic)
        """
        player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

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
                return  # No data, no adjustment

            # Calculate weighted PPP
            total_freq = sum(r[1] for r in rows)
            weighted_ppp = sum(r[1] * r[2] for r in rows) / total_freq

            # Compare to league average (1.05 PPP = average NBA efficiency)
            LEAGUE_AVG_PPP = 1.05
            efficiency_ratio = weighted_ppp / LEAGUE_AVG_PPP

            # Cap at ±15% adjustment (avoid over-calibration)
            modifier = max(0.85, min(1.15, efficiency_ratio))

            # Apply to points projection
            self._boost_stat(calibrated, 'proj_pts', modifier)

            # Add note if significant adjustment (>5%)
            if abs(modifier - 1.0) > 0.05:
                direction = "Efficient" if modifier > 1.0 else "Inefficient"
                pct_change = int((modifier - 1.0) * 100)
                calibrated['notes'] += f" | {direction} ({pct_change:+d}% PPP)"

        except Exception as e:
            # Silently fail - don't break pipeline if Synergy data unavailable
            pass

    def _apply_defensive_diff_adjustment(self, calibrated: dict, opponent_abbr: str) -> None:
        """
        Apply opponent defensive adjustment using diff_pct (FG% allowed vs expected).

        Focuses on rim protection for rim-based playtypes (roll men, cutters, putbacks).
        Elite rim protectors (diff% < -5) penalize interior scoring.

        Args:
            calibrated: Player packet with projections
            opponent_abbr: Opponent team abbreviation
        """
        player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))
        sec_playtypes = calibrated.get('secondary_playtypes', [])

        # Only apply to rim-based playtypes
        RIM_BASED = ['P&R_ROLL_MAN', 'OFF_BALL_CUTTER', 'PUTBACK', 'POST_UP']
        has_rim_playtype = any(pt in RIM_BASED for pt in sec_playtypes)

        if not has_rim_playtype:
            return  # Not a rim scorer, skip adjustment

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get opponent's best rim protector (lowest diff_pct = most impact)
            cursor.execute("""
                SELECT player_name, diff_pct
                FROM player_defense
                WHERE team_abbr = ? AND diff_pct IS NOT NULL
                ORDER BY diff_pct ASC
                LIMIT 1
            """, (opponent_abbr,))

            row = cursor.fetchone()
            conn.close()

            if not row:
                return  # No defensive data for opponent

            rim_protector_name, diff_pct = row

            # Elite rim protection = negative diff% (opponents shoot WORSE than expected)
            # diff_pct of -10% → opponents shoot 10% worse → penalty for our player
            # diff_pct of +5% → weak rim D → boost for our player

            # Convert diff_pct to modifier: -10% diff → 0.90 modifier (10% penalty)
            modifier = 1.0 + (diff_pct / 100)

            # Cap adjustment at ±12%
            modifier = max(0.88, min(1.12, modifier))

            # Apply to points projection
            self._boost_stat(calibrated, 'proj_pts', modifier)

            # Add note if significant (>3% adjustment)
            if abs(modifier - 1.0) > 0.03:
                pct_change = int((modifier - 1.0) * 100)
                if diff_pct < -5:
                    calibrated['notes'] += f" | Elite Rim D ({rim_protector_name[:10]}, {pct_change:+d}%)"
                elif diff_pct > 3:
                    calibrated['notes'] += f" | Weak Rim D ({pct_change:+d}%)"

        except Exception as e:
            # Silently fail
            pass

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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Aggregate drives data from game logs (season avg)
            cursor.execute("""
                SELECT
                    COUNT(*) as games,
                    AVG(drives_fga + drives_fgm) as avg_drives,
                    AVG(drives_pass_pct) as avg_pass_pct
                FROM player_game_tracking
                WHERE player_name = ? AND (drives_fga > 0 OR drives_fgm > 0)
                GROUP BY player_name
            """, (player_name,))

            row = cursor.fetchone()
            conn.close()

            if not row or row[0] < 5:  # Need at least 5 games for reliable sample
                return  # No drives data or insufficient sample

            games, drives, pass_pct = row

            # High volume + high pass% = elite playmaker
            if drives >= 8 and pass_pct >= 40:
                modifier = 1.10  # +10% assist boost
                calibrated['notes'] += " | Elite Playmaker"
            elif drives >= 6 and pass_pct >= 35:
                modifier = 1.05  # +5% assist boost
                calibrated['notes'] += " | High Pass Rate"
            elif pass_pct < 25:
                modifier = 0.95  # -5% penalty (score-first)
                calibrated['notes'] += " | Score-First Driver"
            else:
                return  # Neutral profile, no adjustment

            # Apply to assist projection
            self._boost_stat(calibrated, 'proj_ast', modifier)

        except Exception as e:
            # Silently fail
            pass

    def _boost_stat(self, d, key, factor):
        if key in d: d[key] = round(d[key] * factor, 2)

    def _apply_factor(self, d, factor):
        keys = ['proj_pts', 'proj_ast', 'proj_reb', 'proj_3pm', 'proj_min', 'proj_fga', 'proj_3pa', 'proj_fta', 'proj_oreb', 'proj_dreb', 'proj_stl', 'proj_blk']
        for k in keys:
            if k in d: d[k] = round(d[k] * factor, 2)

    def _zero_out(self, d):
        keys = ['proj_pts', 'proj_ast', 'proj_reb', 'proj_3pm', 'proj_min', 'proj_fga', 'proj_3pa', 'proj_fta', 'proj_oreb', 'proj_dreb', 'proj_stl', 'proj_blk']
        for k in keys: d[k] = 0.0

if __name__ == "__main__":
    calib = LudiCalibrator()
    print("Module E (2025-26 Season) Calibrator Loaded.")