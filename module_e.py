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
            "LAL": "PAINT_PACK",  # Lakers - help-heavy rim protection
            "CLE": "PAINT_PACK",  # Cavaliers - Mobley+Allen interior
            "MEM": "PAINT_PACK",  # Grizzlies - JJJ rim protection
            "MIL": "PAINT_PACK",  # Bucks - Brook Lopez drop coverage
            "PHI": "PAINT_PACK",  # 76ers - Embiid deep drop

            # HIGH PRESSURE / TURNOVER GENERATORS (Blitz)
            "HOU": "BLITZ", "TOR": "BLITZ", "MIA": "BLITZ",
            "PHX": "BLITZ",  # Fixed typo: was PHO
            "BKN": "BLITZ",  # Nets - aggressive trap schemes

            # SWITCH-HEAVY / PERIMETER FOCUS (Small Ball / Perimeter)
            "GSW": "PERIMETER", "DAL": "PERIMETER", "NYK": "PERIMETER",
            "LAC": "PERIMETER",  # Clippers - switch-heavy wings
            "NOP": "PERIMETER",  # Pelicans - Herb Jones perimeter focus

            # VOLUMETRIC VULNERABILITY (Funnel / High Pace)
            "WAS": "FUNNEL", "ATL": "FUNNEL", "CHI": "FUNNEL", "UTA": "FUNNEL", "SAC": "FUNNEL",
            "DEN": "FUNNEL",  # Nuggets - porous defense, high pace

            # FOUL-PRONE / PHYSICAL (Hackers)
            "IND": "HACKERS", "CHA": "HACKERS", "POR": "HACKERS"
        }

    def _fetch_missing_stats(self, player_name, team_abbr=None):
        """
        Database fallback for missing STL/BLK/USG stats.
        Queries player_game_logs for 20-day averages.

        Args:
            player_name: Full player name (e.g., "LeBron James")
            team_abbr: Optional team filter for disambiguation

        Returns:
            dict with base_stl, base_blk, base_usg (0 if not found)
        """
        import sqlite3

        try:
            conn = sqlite3.connect('/home/mnprice86/ludi_bot/ludi.db')
            cursor = conn.cursor()

            # Query for recent game averages
            if team_abbr:
                query = '''
                    SELECT
                        AVG(stl) as avg_stl,
                        AVG(blk) as avg_blk,
                        AVG(fga) as avg_fga,
                        AVG(fta) as avg_fta,
                        AVG(tov) as avg_tov,
                        COUNT(*) as games_played
                    FROM player_game_logs
                    WHERE player_name = ? AND team_abbreviation = ?
                    AND game_date >= date('now', '-20 days')
                '''
                cursor.execute(query, (player_name, team_abbr))
            else:
                query = '''
                    SELECT
                        AVG(stl) as avg_stl,
                        AVG(blk) as avg_blk,
                        AVG(fga) as avg_fga,
                        AVG(fta) as avg_fta,
                        AVG(tov) as avg_tov,
                        COUNT(*) as games_played
                    FROM player_game_logs
                    WHERE player_name = ?
                    AND game_date >= date('now', '-20 days')
                '''
                cursor.execute(query, (player_name,))

            row = cursor.fetchone()
            conn.close()

            if row and row[5] >= 3:  # At least 3 games played
                stl = row[0] or 0
                blk = row[1] or 0
                fga = row[2] or 0
                fta = row[3] or 0
                tov = row[4] or 0

                # Estimate usage % using simplified formula
                # USG% ≈ (FGA + 0.44*FTA + TOV) / 100
                estimated_usg = (fga + 0.44 * fta + tov) / 100

                return {
                    'base_stl': round(stl, 2),
                    'base_blk': round(blk, 2),
                    'base_usg': round(estimated_usg, 3)
                }
            else:
                # No data found - return defaults
                return {'base_stl': 0, 'base_blk': 0, 'base_usg': 0.20}

        except Exception as e:
            print(f"⚠️  Database fallback failed for {player_name}: {e}")
            return {'base_stl': 0, 'base_blk': 0, 'base_usg': 0.20}

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

        # === NEW MATCHUP MODIFIERS (Week 2 Day 5) ===

        # E) TWO_WAY_WING vs FUNNEL (perimeter volume opportunities)
        elif archetype == "TWO_WAY_WING" and def_style == "FUNNEL":
            self._boost_stat(calibrated, 'proj_3pa', 1.12)
            self._boost_stat(calibrated, 'proj_3pm', 1.08)
            self._boost_stat(calibrated, 'proj_stl', 1.15)
            calibrated['notes'] += " | High Pace Target (Transition)"

        # F) TWO_WAY_WING vs PERIMETER (switch mismatch exploitation)
        elif archetype == "TWO_WAY_WING" and def_style == "PERIMETER":
            self._boost_stat(calibrated, 'proj_pts', 1.10)
            self._boost_stat(calibrated, 'proj_stl', 1.12)
            calibrated['notes'] += " | Mismatch Hunter"

        # G) FACILITATOR vs BLITZ (pressure creates assists)
        elif archetype == "FACILITATOR" and def_style == "BLITZ":
            self._boost_stat(calibrated, 'proj_ast', 1.25)
            self._boost_stat(calibrated, 'proj_tov', 0.95)
            calibrated['notes'] += " | Pressure Solver"

        # H) FACILITATOR vs HACKERS (foul-drawing drives)
        elif archetype == "FACILITATOR" and def_style == "HACKERS":
            self._boost_stat(calibrated, 'proj_fta', 1.15)
            self._boost_stat(calibrated, 'proj_ast', 1.08)
            calibrated['notes'] += " | Rim Attack Setup"

        return calibrated

    def _assign_archetype(self, p):
        """
        8-Archetype Classification System (v2.0 - Week 2 Day 5)
        Evaluates in priority order to prevent false positives.
        Uses database fallback if STL/BLK/USG are missing.
        """
        # Extract stats
        pts = p.get('base_pts', 0)
        reb = p.get('base_reb', 0)
        ast = p.get('base_ast', 0)
        tpm = p.get('base_3pm', 0)
        usg = p.get('base_usg', 0)
        stl = p.get('base_stl', 0)
        blk = p.get('base_blk', 0)

        # Database fallback if stats are missing
        if stl == 0 and blk == 0 and usg == 0:
            player_name = p.get('name', p.get('PLAYER_NAME', ''))
            team = p.get('team', p.get('TEAM_ABBREVIATION', ''))
            if player_name:
                missing_stats = self._fetch_missing_stats(player_name, team)
                stl = missing_stats['base_stl']
                blk = missing_stats['base_blk']
                usg = missing_stats['base_usg']
                # Update player packet for downstream use
                p['base_stl'] = stl
                p['base_blk'] = blk
                p['base_usg'] = usg

        stocks = stl + blk

        # === TIER 1: HIGH-USAGE SPECIALISTS (Check first to avoid overlap) ===

        # 1. BALL_HOG: High usage + high assists (primary ball-handlers)
        if usg > 0.30 and ast > 6.0:
            return "BALL_HOG"

        # 2. SLASHER: High scoring + high usage + low 3PM (interior scorers)
        if pts > 22.0 and usg > 0.30 and tpm < 2.0:
            return "SLASHER"

        # === TIER 2: SPECIALISTS (Specific skill combinations) ===

        # 3. STRETCH_BIG: Rebounding + floor spacing (modern bigs)
        if reb > 6.5 and tpm > 1.8:
            return "STRETCH_BIG"

        # 4. RIM_RUNNER: Elite rebounding + no perimeter game (traditional bigs)
        if reb > 8.0 and tpm < 0.6:
            return "RIM_RUNNER"

        # 5. SNIPER: Elite 3PM + low assists (catch-and-shoot specialists)
        if tpm > 2.8 and ast < 3.5:
            return "SNIPER"

        # === TIER 3: ROLE PLAYERS (NEW - Balanced contributors) ===

        # 6. TWO_WAY_WING: Defensive versatility + floor spacing (NEW)
        if stocks >= 1.8 and tpm >= 1.5 and pts < 22.0:
            return "TWO_WAY_WING"

        # 7. FACILITATOR: High assists + low usage + low scoring (NEW)
        if ast >= 5.0 and pts < 15.0 and usg < 0.28:
            return "FACILITATOR"

        # === TIER 4: DEFAULT ===

        # 8. GENERALIST: All others (balanced or undefined roles)
        return "GENERALIST"

    def _boost_stat(self, d, key, factor):
        if key in d: d[key] = round(d[key] * factor, 2)

    def _apply_factor(self, d, factor):
        keys = ['proj_pts', 'proj_ast', 'proj_reb', 'proj_3pm', 'proj_min',
                'proj_fga', 'proj_3pa', 'proj_fta', 'proj_oreb', 'proj_dreb',
                'proj_stl', 'proj_blk']  # NEW - Week 2 Day 5
        for k in keys:
            if k in d: d[k] = round(d[k] * factor, 2)

    def _zero_out(self, d):
        keys = ['proj_pts', 'proj_ast', 'proj_reb', 'proj_3pm', 'proj_min',
                'proj_fga', 'proj_3pa', 'proj_fta', 'proj_oreb', 'proj_dreb',
                'proj_stl', 'proj_blk']  # NEW - Week 2 Day 5
        for k in keys: d[k] = 0.0

if __name__ == "__main__":
    calib = LudiCalibrator()
    print("Module E (2025-26 Season) Calibrator Loaded.")