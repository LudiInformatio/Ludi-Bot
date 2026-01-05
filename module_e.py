import pandas as pd

# ==========================================
# LUDI INFORMATIO | MODULE E: THE CALIBRATOR
# V5.6 - 2025-26 LIVE DEFENSIVE MAPPING
# ==========================================

class LudiCalibrator:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE E (CALIBRATOR V5.6) ONLINE")
        print(f"   >>> LIVE 2025-26 DEFENSIVE SCHEMES ACTIVE")
        print(f"{'='*40}")
        
        self.ADJUSTMENT_RULES = {
            "MINUTES_LIMIT": 0.75,   
            "PROMOTION": 1.50,       
            "OUT": 0.0              
        }
        
        # 2025-26 UPDATED DEFENSIVE STYLES (Based on Dec 2025 Efficiency)
        self.DEFENSIVE_STYLES = {
            # THE ELITE WALLS (Paint Pack / Elite Interior)
            "OKC": "PAINT_PACK", "BOS": "PAINT_PACK", "DET": "PAINT_PACK", 
            "MIN": "PAINT_PACK", "SAS": "PAINT_PACK", "ORL": "PAINT_PACK",
            
            # HIGH PRESSURE / TURNOVER GENERATORS (Blitz)
            "HOU": "BLITZ", "TOR": "BLITZ", "MIA": "BLITZ", "PHO": "BLITZ",
            
            # SWITCH-HEAVY / PERIMETER FOCUS (Small Ball / Perimeter)
            "GSW": "PERIMETER", "DAL": "PERIMETER", "NYK": "PERIMETER",
            
            # VOLUMETRIC VULNERABILITY (Funnel / High Pace)
            "WAS": "FUNNEL", "ATL": "FUNNEL", "CHI": "FUNNEL", "UTA": "FUNNEL", "SAC": "FUNNEL",
            
            # FOUL-PRONE / PHYSICAL (Hackers)
            "IND": "HACKERS", "CHA": "HACKERS", "POR": "HACKERS"
        }

    def calibrate_player(self, player_packet, yak_report):
        calibrated = player_packet.copy()
        if 'notes' not in calibrated: calibrated['notes'] = "" 
        
        # 1. ASSIGN ARCHETYPE (Standardized Logic)
        archetype = self._assign_archetype(calibrated)
        if archetype:
            calibrated['archetype'] = archetype
            calibrated['notes'] += f" [{archetype}]"

        # 2. NEWS CALIBRATION (Module D Handshake)
        status = yak_report.get('status', 'ACTIVE')
        note = yak_report.get('note', '')
        
        calibration_factor = 1.0
        
        if status == "OUT":
            self._zero_out(calibrated)
            calibrated['notes'] += " | Official OUT"
            return calibrated
        elif status == "MINUTES_LIMIT":
            calibration_factor = self.ADJUSTMENT_RULES["MINUTES_LIMIT"]
            calibrated['notes'] += f" | 15-min Update: Limit Applied"

        if calibration_factor != 1.0:
            self._apply_factor(calibrated, calibration_factor)

        # 3. GAME SCRIPT (Vegas context for 2025 Totals)
        odds = calibrated.get('odds', {})
        total = float(odds.get('total', 0)) if odds.get('total') else 0
        spread = abs(float(odds.get('spread', 0))) if odds.get('spread') else 0
        
        # 2025-26 Blowout Risk Management
        if spread > 12.5 and calibrated.get('base_min', 0) > 30.0:
            self._apply_factor(calibrated, 0.94)
            calibrated['notes'] += f" | Spread {spread} Blowout Risk"

        # League Avg Total in 2025 is ~228.0
        if total > 238.0:
            self._apply_factor(calibrated, 1.03) # High Octane
        elif total > 0 and total < 218.0:
            self._apply_factor(calibrated, 0.97) # Grind

        # 4. MATCHUP LOGIC (Style vs Style)
        opponent = calibrated.get('opponent', 'UNK') 
        def_style = self.DEFENSIVE_STYLES.get(opponent, "NEUTRAL")
        
        # A) STRETCH BIG vs PAINT PACK (e.g. Porzingis vs OKC)
        if archetype == "STRETCH_BIG" and def_style == "PAINT_PACK":
            self._boost_stat(calibrated, 'proj_3pm', 1.15)
            self._boost_stat(calibrated, 'proj_3pa', 1.15)
            calibrated['notes'] += f" | {opponent} Paint Pack Edge"

        # B) SLASHER vs HACKERS (e.g. Edwards vs IND)
        elif archetype == "SLASHER" and def_style == "HACKERS":
            self._boost_stat(calibrated, 'proj_fta', 1.20)
            self._boost_stat(calibrated, 'proj_pts', 1.05)
            calibrated['notes'] += " | Foul Drawn Magnet"

        # C) RIM RUNNER vs PERIMETER (e.g. Gobert vs GSW)
        elif archetype == "RIM_RUNNER" and def_style == "PERIMETER":
            self._boost_stat(calibrated, 'proj_oreb', 1.30)
            self._boost_stat(calibrated, 'proj_reb', 1.15)
            calibrated['notes'] += " | Size Advantage (O-Boards)"

        # D) BALL HOG vs BLITZ (e.g. Luka vs HOU)
        elif archetype == "BALL_HOG" and def_style == "BLITZ":
            self._boost_stat(calibrated, 'proj_ast', 1.18)
            self._boost_stat(calibrated, 'proj_pts', 0.92)
            self._boost_stat(calibrated, 'proj_tov', 1.10)
            calibrated['notes'] += " | Trap Scheme (Pass-First)"

        return calibrated

    def _assign_archetype(self, p):
        # Using the base stats from the upstream historian (Module H)
        reb = p.get('base_reb', 0); pts = p.get('base_pts', 0)
        ast = p.get('base_ast', 0); usg = p.get('base_usg', 0)
        tpm = p.get('base_3pm', 0)

        if reb > 6.5 and tpm > 1.8: return "STRETCH_BIG"
        if pts > 22.0 and usg > 0.30 and tpm < 2.0: return "SLASHER"
        if tpm > 2.8 and ast < 3.5: return "SNIPER"
        if reb > 8.0 and tpm < 0.6: return "RIM_RUNNER"
        if usg > 0.30 and ast > 6.0: return "BALL_HOG"
        return "GENERALIST"

    def _boost_stat(self, d, key, factor):
        if key in d: d[key] = round(d[key] * factor, 2)

    def _apply_factor(self, d, factor):
        keys = ['proj_pts', 'proj_ast', 'proj_reb', 'proj_3pm', 'proj_min', 
                'proj_fga', 'proj_3pa', 'proj_fta', 'proj_oreb', 'proj_dreb']
        for k in keys:
            if k in d: d[k] = round(d[k] * factor, 2)

    def _zero_out(self, d):
        keys = ['proj_pts', 'proj_ast', 'proj_reb', 'proj_3pm', 'proj_min', 
                'proj_fga', 'proj_3pa', 'proj_fta', 'proj_oreb', 'proj_dreb']
        for k in keys: d[k] = 0.0

if __name__ == "__main__":
    calib = LudiCalibrator()
    print("Module E (2025-26 Season) Calibrator Loaded.")