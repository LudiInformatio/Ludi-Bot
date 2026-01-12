import pandas as pd

# ==========================================
# LUDI INFORMATIO | MODULE E: THE CALIBRATOR
# V6.0 - 2025-26 LIVE DEFENSIVE MAPPING (Restored & Enhanced)
# ==========================================

class LudiCalibrator:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE E (CALIBRATOR V6.0) ONLINE")
        print(f"   >>> LIVE 2025-26 DEFENSIVE SCHEMES ACTIVE")
        print(f"{ '='*40}")
        
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

    def _fetch_missing_stats(self, player_name, team_abbr=None):
        """Database fallback for missing stats."""
        import sqlite3
        try:
            conn = sqlite3.connect('/home/mnprice86/ludi_bot/ludi.db')
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

    def calibrate_player(self, player_packet, yak_report):
        calibrated = player_packet.copy()
        if 'notes' not in calibrated: calibrated['notes'] = "" 
        
        # 1. ASSIGN ARCHETYPE
        archetype, secondary = self._assign_archetype(calibrated)
        
        if archetype:
            calibrated['archetype'] = archetype
            calibrated['notes'] += f" [{archetype}]"
        if secondary:
            calibrated['secondary_archetype'] = secondary
            calibrated['notes'] += f" / {secondary}"

        # 2. NEWS CALIBRATION
        status = yak_report.get('status', 'ACTIVE')
        if status == "OUT":
            self._zero_out(calibrated)
            calibrated['notes'] += " | Official OUT"
            return calibrated
        elif status == "MINUTES_LIMIT":
            self._apply_factor(calibrated, self.ADJUSTMENT_RULES["MINUTES_LIMIT"])
            calibrated['notes'] += f" | 15-min Update: Limit Applied"

        # 3. GAME SCRIPT
        odds = calibrated.get('odds', {})
        total = float(odds.get('total', 0)) if odds.get('total') else 0
        spread = abs(float(odds.get('spread', 0))) if odds.get('spread') else 0
        
        if spread > 12.5 and calibrated.get('base_min', 0) > 30.0:
            self._apply_factor(calibrated, 0.94)
            calibrated['notes'] += f" | Spread {spread} Blowout Risk"
        if total > 238.0: self._apply_factor(calibrated, 1.03)
        elif total > 0 and total < 218.0: self._apply_factor(calibrated, 0.97)

        # 4. MATCHUP LOGIC
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

        # === 5. NUANCE CHECKS ===
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