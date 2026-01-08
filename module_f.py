import pandas as pd
from datetime import datetime
import config
from utils.devig import get_fair_probability, calculate_true_edge, american_to_implied
from utils.bet_logger import get_bet_logger

# ==============================================================================
# LUDI INFORMATIO | MODULE F: THE ALCHEMIST
# V4.4 - DEVIGGED EDGE CALCULATION | 2026 PRO-SHARP META
# ==============================================================================
# CHANGELOG V4.4:
# - Added devigging to calculate TRUE edge against fair market probability
# - Edge calculation now removes bookmaker vig (~2-5%) for accurate EV
# - Supports fallback to raw odds if over/under pair not available
# ==============================================================================

class LudiReporter:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE F (V4.5) ONLINE")
        print(f"   >>> DETERMINISTIC REPORTING | NO SPECULATION")
        print(f"   >>> BET LOGGING ENABLED")
        print(f"{'='*40}")

        # Initialize bet logger (singleton pattern)
        try:
            self.bet_logger = get_bet_logger()
            print(f"✅ Bet logger connected")
        except Exception as e:
            print(f"⚠️  Bet logger unavailable: {e}")
            self.bet_logger = None

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
                    for stat_key, prop_data in p['sportsbook_props'].items():
                        # Handle both old format (line only) and new format (dict with odds)
                        if isinstance(prop_data, dict):
                            line = prop_data.get('line', 0)
                            odds_over = prop_data.get('odds_over', -110)
                            odds_under = prop_data.get('odds_under', -110)
                        else:
                            # Legacy format: just the line value
                            line = prop_data
                            odds_over = -110  # Assume standard juice
                            odds_under = -110

                        # Map internal projection keys to common sportsbook prop keys
                        raw_val = self._map_stat(p, stat_key)

                        # Apply Final 2026 Blowout Modifier
                        final_proj = raw_val * blowout_mult

                        # --- DEVIGGED EDGE CALCULATION (V4.4) ---
                        # Calculate our model's probability of going OVER the line
                        # Using projection vs line difference scaled by typical variance
                        our_prob = self._estimate_over_probability(final_proj, line, stat_key)

                        # Determine bet direction
                        bet_direction = 'over' if final_proj > line else 'under'
                        model_prob = our_prob if bet_direction == 'over' else (1 - our_prob)

                        # Calculate TRUE edge using devigged fair probability
                        edge = calculate_true_edge(
                            model_prob,
                            odds_over,
                            odds_under,
                            side=bet_direction
                        )
                        edge = round(edge, 1)

                        # Store fair probability for reporting
                        fair_prob = get_fair_probability(odds_over, odds_under, bet_direction)

                        # --- 2. THE SHARP FILTER (5% Minimum Edge) ---
                        if abs(edge) >= 5.0:
                            # Use our model probability directly (already calculated)
                            win_prob = min(max(model_prob, 0.51), 0.75)

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

                            # --- BET LOGGING (V4.5) ---
                            if self.bet_logger:
                                try:
                                    run_date = datetime.now().strftime('%Y-%m-%d')
                                    rec_data = {
                                        'run_date': run_date,
                                        'game_id': game.get('game_id', ''),
                                        'game_date': game.get('game_date', run_date),
                                        'matchup': game.get('matchup', ''),
                                        'home_team': game.get('home_team', ''),
                                        'away_team': game.get('away_team', ''),
                                        'spread': game.get('spread', 0),
                                        'total': game.get('total', 0),
                                        'player_name': p['name'],
                                        'team': p['team'],
                                        'opponent': game.get('opponent', ''),
                                        'archetype': p.get('archetype', ''),
                                        'status': p.get('status', 'Active'),
                                        'scenario': p.get('scenario', 'BASE'),
                                        'stat_category': stat_key.upper(),
                                        'bet_side': 'OVER' if edge > 0 else 'UNDER',
                                        'line': line,
                                        'odds_over': odds_over,
                                        'odds_under': odds_under,
                                        'projection': round(final_proj, 2),
                                        'fair_prob': round(fair_prob, 4),
                                        'model_prob': round(model_prob, 4),
                                        'true_edge': edge,
                                        'ev': ev,
                                        'units': units,
                                        'confidence_tier': 'DIAMOND',  # TODO: tiering logic
                                        'note': " | ".join(note_elements),
                                        'referee_impact': game.get('ref_impact', 1.0),
                                        'blowout_modifier': round(blowout_mult, 3),
                                        'run_type': 'production',
                                        'bookmaker': 'consensus'
                                    }
                                    bet_id = self.bet_logger.log_recommendation(rec_data)
                                except Exception as e:
                                    print(f"⚠️  Failed to log bet: {e}")

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

        # --- DAILY SUMMARY LOGGING ---
        if self.bet_logger and all_props:
            try:
                run_date = datetime.now().strftime('%Y-%m-%d')
                summary_data = {
                    'run_date': run_date,
                    'total_bets': len(all_props),
                    'total_units': sum(p['units'] for p in all_props),
                    'pending': len(all_props),  # All bets start as pending
                    'avg_edge': sum(p.get('true_edge', 0) for p in all_props) / len(all_props) if all_props else 0,
                    'avg_ev': sum(p['ev'] for p in all_props) / len(all_props),
                    'games_analyzed': len(processed_slate)
                }
                self.bet_logger.calculate_daily_summary(run_date, summary_data)
                print(f"📊 Daily summary logged: {len(all_props)} bets, {summary_data['total_units']:.1f} units")
            except Exception as e:
                print(f"⚠️  Failed to log daily summary: {e}")

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

    def _estimate_over_probability(self, projection: float, line: float, stat_key: str) -> float:
        """
        Estimate the probability of going OVER the line based on projection.

        Uses stat-specific standard deviations to convert the projection-line
        difference into a probability using a simplified normal CDF approximation.

        This is a heuristic until Module C (Oracle) provides explicit probabilities
        from its Poisson simulations.

        Args:
            projection: Our projected value for the stat
            line: The sportsbook line
            stat_key: The stat category (pts, reb, ast, etc.)

        Returns:
            Probability of going OVER the line (0.0 to 1.0)
        """
        # Typical standard deviations by stat category (from historical NBA data)
        # These represent "one sigma" of typical game-to-game variance
        stat_stdev = {
            'pts': 6.5,    # Points: ~6.5 point standard deviation
            'reb': 3.2,    # Rebounds: ~3.2 boards
            'ast': 2.5,    # Assists: ~2.5 assists
            '3pm': 1.3,    # Three-pointers made: ~1.3
            'oreb': 1.5,   # Offensive rebounds: ~1.5
            'stl': 0.9,    # Steals: ~0.9
            'blk': 1.0,    # Blocks: ~1.0
            'tov': 1.2,    # Turnovers: ~1.2
            'pra': 8.0,    # Pts+Reb+Ast combo: ~8.0
        }

        # Get standard deviation for this stat (default to pts if unknown)
        stdev = stat_stdev.get(stat_key.lower(), 6.5)

        # Calculate z-score: how many standard deviations above/below line
        if stdev == 0:
            return 0.5
        z_score = (projection - line) / stdev

        # Simplified normal CDF approximation (accurate to ~0.01)
        # Using logistic approximation: P(X > line) ≈ 1 / (1 + exp(-1.7 * z))
        import math
        try:
            prob_over = 1 / (1 + math.exp(-1.7 * z_score))
        except OverflowError:
            prob_over = 1.0 if z_score > 0 else 0.0

        # Clamp to reasonable bounds (no bet should be 99%+ or 1%-)
        return max(0.05, min(0.95, prob_over))

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

    # Real-world data handshake test with DEVIGGED ODDS
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
                # NEW FORMAT: Props with odds for devigging
                "sportsbook_props": {
                    "pts": {
                        "line": 13.5,
                        "odds_over": -115,
                        "odds_under": -105
                    }
                },
                "status": "Active",
                "archetype": "SLASHER"
            }
        ]
    }]

    print("\n" + "=" * 60)
    print("DEVIG TEST: Amen Thompson 19.5 proj vs 13.5 line")
    print("Odds: Over -115 / Under -105")
    print("=" * 60)

    # Show the devig calculation
    from utils.devig import get_fair_probability, calculate_vig
    fair_over = get_fair_probability(-115, -105, 'over')
    vig = calculate_vig(-115, -105)
    print(f"Fair probability (over): {fair_over:.4f} ({fair_over*100:.1f}%)")
    print(f"Vig removed: {vig*100:.2f}%")
    print("=" * 60)

    print(rep.generate_report(test_data))

    # Legacy format test (backwards compatibility)
    print("\n" + "=" * 60)
    print("LEGACY FORMAT TEST (line only, assumes -110/-110)")
    print("=" * 60)
    legacy_test = [{
        "game_id": "LAL_GSW",
        "spread": 2.5,
        "players": [
            {
                "name": "LeBron James",
                "team": "LAL",
                "proj_pts": 28.5,
                "proj_min": 35.0,
                "sportsbook_props": {"pts": 24.5},  # Legacy format
                "status": "Active"
            }
        ]
    }]
    print(rep.generate_report(legacy_test))