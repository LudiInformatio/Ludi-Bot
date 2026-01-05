import pandas as pd
from datetime import datetime
import config

# ==============================================================================
# LUDI INFORMATIO | MODULE F: THE ALCHEMIST
# V4.3 - FULL PRODUCTION | 2026 PRO-SHARP META
# ==============================================================================

class LudiReporter:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE F (V4.3) ONLINE")
        print(f"   >>> DETERMINISTIC REPORTING | NO SPECULATION")
        print(f"{'='*40}")

    def generate_report(self, processed_slate):
        """
        Final synthesis of the simulation results into actionable alerts.
        Processes the slate and applies 2026 sharp-market filters.
        """
        all_props = []
        
        for game in processed_slate:
            # --- 1. SLIDING SCALE BLOWOUT TAX ---
            # Logic: Starter volume decays as spread widens beyond 7 pts.
            spread = abs(game.get('spread', 0))
            blowout_mult = 1.0 - (max(0, spread - 7.0) * 0.015)

            for p in game['players']:
                # UPSTREAM GUARDRAIL: Skip players with zero projected minutes 
                # or those explicitly ruled OUT by Module D (The Yak).
                if p.get('proj_min', 0) <= 0 or p.get('status') == 'OUT':
                    continue
                
                player_props = []
                if 'sportsbook_props' in p:
                    for stat_key, line in p['sportsbook_props'].items():
                        # Map internal projection keys to common sportsbook prop keys
                        raw_val = self._map_stat(p, stat_key)
                        
                        # Apply Final 2026 Blowout Modifier
                        final_proj = raw_val * blowout_mult
                        
                        # Calculate Edge Percentage
                        edge = round(((final_proj - line) / line) * 100, 1) if line > 0 else 0
                        
                        # --- 2. THE SHARP FILTER (5% Minimum Edge) ---
                        if abs(edge) >= 5.0:
                            # 2026 Win Probability Mapping
                            win_prob = min(max(0.50 + (abs(edge) / 140.0), 0.51), 0.65)
                            
                            # Standardized -110 (1.91) EV Calculation
                            ev = round(((win_prob * 1.91) - 1) * 100, 2)
                            
                            # Bankroll Unit Sizing (0.25u to 1.5u)
                            units = min(max(round(ev / 8.0, 2), 0.25), 1.5) if ev >= 1.0 else 0
                            
                            # --- 3. DYNAMIC NOTE GENERATION (Deterministic Only) ---
                            note_elements = []
                            
                            # A) Archetype Label (from Module E)
                            if p.get('archetype'):
                                note_elements.append(f"[{p['archetype']}]")

                            # B) Scenario Resolver (from Module X)
                            scenario_raw = p.get('scenario', 'BASE')
                            if "WITHOUT" in scenario_raw:
                                absent_star = scenario_raw.replace("WITHOUT ", "")
                                note_elements.append(f"🚀 BENEFICIARY: Scaling for {absent_star} OUT")
                            
                            # C) Status Flag (from Module D)
                            if p.get('status') in ['Q', 'GTD']:
                                note_elements.append(f"🚨 GTD: Proj assumes {p['name']} PLAYS")

                            # D) Referee Context (from Module G)
                            if abs(game.get('ref_impact', 1.0) - 1.0) > 0.04:
                                note_elements.append(f"⚖️ Ref Impact: {game.get('ref_impact', 1.0)}")

                            player_props.append({
                                "name": p['name'], 
                                "team": p['team'], 
                                "stat": stat_key.upper(),
                                "bet_on": "OVER" if edge > 0 else "UNDER",
                                "line": line, 
                                "proj": round(final_proj, 2),
                                "ev": ev, 
                                "units": units, 
                                "note": " | ".join(note_elements)
                            })

                # --- 4. CORRELATION CHECK (SGP TARGETS) ---
                if len([x for x in player_props if x['units'] >= 1.2]) >= 2:
                    for x in player_props: 
                        x['note'] += " [🔥 CORRELATED SGP]"
                
                all_props.extend(player_props)

        # Sort by EV descending for the "Diamond" ranking
        all_props.sort(key=lambda x: x['ev'], reverse=True)
        return self.create_daily_briefing(all_props)

    def _map_stat(self, p, key):
        """Maps internal projection keys to common sportsbook prop keys."""
        m = {
            'pts': 'proj_pts', 
            'reb': 'proj_reb', 
            'ast': 'proj_ast', 
            '3pm': 'proj_3pm', 
            'oreb': 'proj_oreb'
        }
        return p.get(m.get(key.lower(), ''), 0)

    def create_daily_briefing(self, props):
        """Formats the final briefing output for bot and console display."""
        report = f"\n📰 LUDI ELITE BRIEFING ({datetime.now().strftime('%b %d, %Y')})\n"
        report += "================================\n"
        
        # Filter for Tier 1 Diamonds (Top 5 high-conviction plays)
        diamonds = [p for p in props if p['units'] >= 1.2][:5]
        
        if not diamonds:
            return report + "⚠️ Market is efficient. No Diamond Edges detected for this refresh.\n"
        
        report += f"💎 DIAMOND PLAYS\n"
        for bet in diamonds:
            report += f"🏀 {bet['name']} ({bet['team']}) | {bet['bet_on']} {bet['line']} {bet['stat']}\n"
            report += f"   Sharp Proj: {bet['proj']} | EV: +{bet['ev']}% | {bet['units']}u\n"
            if bet['note']: 
                report += f"   📝 {bet['note']}\n\n"
        
        return report

# --- STANDALONE PRODUCTION TEST ---
if __name__ == "__main__":
    rep = LudiReporter()
    
    # Real-world data handshake test
    test_data = [{
        "game_id": "HOU_BKN",
        "spread": 4.0,
        "ref_impact": 1.06,
        "players": [
            {
                "name": "Amen Thompson", 
                "team": "HOU",
                "proj_pts": 19.5, 
                "proj_min": 32.0,
                "scenario": "WITHOUT Alperen Sengun",
                "sportsbook_props": {"pts": 13.5},
                "status": "Active",
                "archetype": "SLASHER"
            }
        ]
    }]
    print(rep.generate_report(test_data))