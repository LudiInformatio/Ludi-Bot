import pandas as pd
import sqlite3
import json
from pathlib import Path

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
    
    def _select_top_playtypes(self, player_data: dict) -> tuple:
        """
        Select top 1-2 secondary playtypes for a player.
        Uses position filtering + priority scoring (Week 1 validated).
        
        Returns:
            (primary_playtype, secondary_playtype) - secondary may be None
        """
        position = player_data.get('position', 'UNK')
        
        # Step 1: Get eligible playtypes for this position
        eligible = self._get_eligible_playtypes(position)
        
        # Step 2: Calculate match scores for eligible playtypes
        scores = {}
        for pt in eligible:
            score = self._calculate_playtype_score(player_data, pt)
            if score > 0:
                scores[pt] = score
        
        # Step 3: Select top 1-2 tags based on thresholds
        sorted_tags = sorted(scores.items(), key=lambda x: -x[1])
        
        primary = sorted_tags[0][0] if len(sorted_tags) > 0 and sorted_tags[0][1] >= self.PRIMARY_THRESHOLD else None
        secondary = sorted_tags[1][0] if len(sorted_tags) > 1 and sorted_tags[1][1] >= self.SECONDARY_THRESHOLD else None
        
        return primary, secondary
    
    def _get_tracking_stats(self, player_name: str, days: int = 60) -> dict:
        """
        Get tracking stats for a player from database.
        Uses player_id joins to handle accented names (Jokić, Dončić).
        Returns empty dict if not found.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Step 1: Get player_id from players table
            # Note: Some players have duplicate entries - this gets the first match
            # TODO: Clean up duplicate player_id entries in database
            cursor.execute('''
                SELECT player_id, position 
                FROM players 
                WHERE name = ? 
                ORDER BY updated_at DESC 
                LIMIT 1
            ''', (player_name,))
            player_row = cursor.fetchone()
            
            if not player_row or not player_row[0]:
                conn.close()
                return {}
            
            player_id = player_row[0]
            position = player_row[1] if player_row[1] and player_row[1] != 'UNK' else None
            
            # Step 2: Query tracking data by nba_player_id (eliminates accent issues)
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
            WHERE nba_player_id = ? AND game_date >= date('now', ?)
            """
            cursor.execute(tracking_query, (player_id, f'-{days} days'))
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
            
            # Step 3: Get shot quality (rim_freq) - also by player_id for consistency
            shot_query = """
            SELECT at_rim_freq, corner_3_freq 
            FROM player_shot_quality 
            WHERE player_id = ? AND season = '2025-26'
            """
            cursor.execute(shot_query, (player_id,))
            shot_row = cursor.fetchone()
            
            if shot_row:
                tracking_stats['rim_freq'] = shot_row[0] or 0
                tracking_stats['corner_3_freq'] = shot_row[1] or 0
            
            # Add position if found (UNK positions will get all playtypes)
            if position:
                tracking_stats['position'] = position
            
            conn.close()
            return tracking_stats
            
        except Exception as e:
            return {}


    def calibrate_player(self, player_packet, yak_report):
        calibrated = player_packet.copy()
        if 'notes' not in calibrated: calibrated['notes'] = "" 
        
        # 1. ASSIGN PRIMARY ARCHETYPE
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
            if 'position' in tracking_data:
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

        # 6. SECONDARY PLAYTYPE MATCHUPS (Week 2 Integration)
        sec_playtypes = calibrated.get('secondary_playtypes', [])
        
        for sec_pt in sec_playtypes:
            if sec_pt == 'SPOT_UP' and def_style == 'PAINT_PACK':
                self._boost_stat(calibrated, 'proj_3pm', 1.15)
                calibrated['notes'] += " | Spot-Up vs Pack"
            elif sec_pt == 'OFF_BALL_CUTTER' and def_style == 'BLITZ':
                self._boost_stat(calibrated, 'proj_pts', 1.12)
                calibrated['notes'] += " | Cutter vs Blitz"
            elif sec_pt == 'ISO_SCORER' and def_style == 'PERIMETER':
                self._boost_stat(calibrated, 'proj_pts', 1.10)
                calibrated['notes'] += " | ISO vs Perimeter"
            elif sec_pt == 'P&R_HANDLER' and def_style == 'FUNNEL':
                self._boost_stat(calibrated, 'proj_ast', 1.12)
                calibrated['notes'] += " | PnR Handler vs Funnel"
            elif sec_pt == 'P&R_ROLL_MAN' and def_style == 'PERIMETER':
                self._boost_stat(calibrated, 'proj_reb', 1.15)
                self._boost_stat(calibrated, 'proj_pts', 1.10)
                calibrated['notes'] += " | Roll Man vs Small Ball"
            elif sec_pt == 'TRANSITION' and def_style == 'HACKERS':
                self._boost_stat(calibrated, 'proj_pts', 1.08)
                calibrated['notes'] += " | Fast Break Edge"
            elif sec_pt == 'PUTBACK' and def_style == 'PERIMETER':
                self._boost_stat(calibrated, 'proj_oreb', 1.25)
                calibrated['notes'] += " | Putback vs Small"
            elif sec_pt == 'POST_UP' and def_style == 'PERIMETER':
                self._boost_stat(calibrated, 'proj_pts', 1.15)
                calibrated['notes'] += " | Post vs Small Ball"

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
        
        # Priority: Heliocentric > Hub/Jumbo > Elite Scorer > Specialists
        return matches[0], (matches[1] if len(matches) > 1 else None)

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