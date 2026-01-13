import pandas as pd
from datetime import datetime
import config
from utils.devig import get_fair_probability, calculate_true_edge, american_to_implied
from utils.bet_logger import get_bet_logger
from utils.tag_classifier import get_tag_classifier

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

        # Initialize tag classifier (Week 2, Days 3-4)
        try:
            self.tag_classifier = get_tag_classifier()
            print(f"✅ Tag classifier connected")
        except Exception as e:
            print(f"⚠️  Tag classifier unavailable: {e}")
            self.tag_classifier = None

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
                        # Ensure line is numeric
                        if not isinstance(line, (int, float)):
                            continue

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

                            # Calculate Decimal Odds for accurate EV
                            bet_odds = odds_over if bet_direction == 'over' else odds_under
                            if bet_odds > 0:
                                decimal_odds = 1 + (bet_odds / 100)
                            else:
                                decimal_odds = 1 + (100 / abs(bet_odds))

                            # EV Calculation using actual odds
                            ev = round(((win_prob * decimal_odds) - 1) * 100, 2)
                            
                            # Bankroll Unit Sizing (0.25u to 1.5u)
                            units = min(max(round(ev / 8.0, 2), 0.25), 1.5) if ev >= 1.0 else 0

                            # --- 3. DYNAMIC NOTE GENERATION (The Ludi Lens) ---
                            note_elements = []
                            
                            # A) Narrative from Module E (Matchups/Boosts)
                            # This captures the "Why": e.g. "[HELIOCENTRIC] | Trap Scheme (Pass-First)"
                            if 'notes' in p:
                                raw_notes = p['notes'].strip()
                                # Clean up leading pipes if they exist
                                if raw_notes.startswith('|'): raw_notes = raw_notes[1:].strip()
                                if raw_notes: note_elements.append(raw_notes)

                            # B) Blowout Context (The "Game Script")
                            if blowout_mult < 0.95:
                                pct_cut = int((1 - blowout_mult) * 100)
                                note_elements.append(f"📉 BLOWOUT TAX (-{pct_cut}% Volume)")

                            # C) Scenario Resolver (from Module X)
                            scenario_raw = p.get('scenario', 'BASE')
                            if "WITHOUT" in scenario_raw:
                                absent_star = scenario_raw.replace("WITHOUT ", "")
                                note_elements.append(f"🚀 VACUUM: {absent_star} OUT")
                            
                            # D) Status Flag (from Module D)
                            if p.get('status') in ['Q', 'GTD']:
                                note_elements.append(f"🚨 GTD Risk")

                            # E) Referee Context (from Module G)
                            if abs(game.get('ref_impact', 1.0) - 1.0) > 0.04:
                                ref_val = game.get('ref_impact')
                                ref_note = f"⚖️ Refs Boost Overs ({ref_val}x)" if ref_val > 1.0 else f"⚖️ Refs Drag Unders ({ref_val}x)"
                                note_elements.append(ref_note)

                            # --- TAG CLASSIFICATION (V4.6 - Week 2, Days 3-4) ---
                            tags_formatted = "[]"  # Default empty tags
                            if self.tag_classifier:
                                try:
                                    # Build game context for classifier
                                    game_ctx = {
                                        'opponent': game.get('opponent', ''),
                                        'spread': game.get('spread', 0),
                                        'players': game.get('players', [])
                                    }

                                    # Build yak report (injury status)
                                    yak_report = {
                                        'status': p.get('status', 'ACTIVE'),
                                        'note': ''
                                    }

                                    # Collect all game props for correlation detection
                                    # Note: player_props list is built incrementally, so we use the partial list
                                    all_game_props = player_props.copy()

                                    # Assign tags
                                    tags_list = self.tag_classifier.assign_all_tags(
                                        player_packet=p,
                                        game_context=game_ctx,
                                        yak_report=yak_report,
                                        all_game_props=all_game_props
                                    )

                                    # Format for database
                                    tags_formatted = self.tag_classifier.format_tags_for_db(tags_list)

                                except Exception as e:
                                    print(f"⚠️  Tag classification failed for {p['name']}: {e}")
                                    tags_formatted = "[]"  # Empty array fallback

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
                                        'bet_side': bet_direction.upper(),
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
                                        'tags': tags_formatted,  # Week 2, Days 3-4: Tag classification
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
                                "matchup": game.get('matchup', ''),
                                "stat": stat_key.upper(),
                                "bet_on": bet_direction.upper(),
                                "line": line,
                                "proj": round(final_proj, 2),
                                "ev": ev,
                                "units": units,
                                "note": " | ".join(note_elements),
                                "tags": tags_formatted  # Week 2, Days 3-4: Tag classification
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

        # Generate visual card (V4.6 - Visual Upgrade)
        image_path = self.generate_image_card(all_props)
        
        return self.create_daily_briefing(all_props), image_path

    def generate_image_card(self, props: list) -> str:
        """
        Generate a visual briefing card PNG from props data.
        
        Args:
            props: List of prop dictionaries from generate_report
            
        Returns:
            Path to generated PNG file
        """
        try:
            from utils.render_full_report import create_briefing_card
            image_path = create_briefing_card(props)
            return image_path
        except Exception as e:
            print(f"⚠️  Visual card generation failed: {e}")
            return None

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
        
        # 1. Group by Game
        # We need game info which might not be in the flat 'props' list?
        # Ah, 'props' only has player/team. We need to pass game context or infer it.
        # Wait, the generate_report loop builds 'all_props'. It loses game_id.
        # I need to modify generate_report to attach game_id/matchup to each prop first.
        # But 'all_props' is a list of dicts. I can add 'matchup' there easily.
        
        # ... Wait, I can't modify generate_report in this replace block easily.
        # Let's assume I modify generate_report to add 'matchup' to player_props.
        
        # Wait, I'll do this in two steps. First, let's just group by TEAM for now as a proxy for game.
        # Or better: Group by "Team vs Opponent" if opponent is available.
        # 'player_props' has 'team'. It doesn't have 'opponent' or 'matchup'.
        
        # I will regroup by Team for now, then sort.
        # Actually, let's just sort by EV and take top 3 per TEAM.
        
        grouped = {}
        for p in props:
            matchup = p.get('matchup', 'Unknown')
            if matchup not in grouped: grouped[matchup] = []
            grouped[matchup].append(p)
            
        report += f"💎 TOP TARGETS BY GAME\n"
        
        # Sort games alphabetically
        for matchup in sorted(grouped.keys()):
            plays = grouped[matchup]
            # Sort by EV descending
            plays.sort(key=lambda x: x['ev'], reverse=True)
            
            # Filter for Diamond (1.2u+) or High Gold (0.8u+)
            top_plays = [p for p in plays if p['units'] >= 0.8][:3] # Top 3 per GAME
            
            if not top_plays: continue
            
            report += f"\n🏀 {matchup}\n"
            for bet in top_plays:
                report += f"   💎 {bet['name']} | {bet['bet_on']} {bet['line']} {bet['stat']}\n"
                report += f"      Proj: {bet['proj']} | EV: +{bet['ev']}% | {bet['units']}u\n"
                
                # Display tags
                if bet.get('tags') and self.tag_classifier:
                    try:
                        tags_list = self.tag_classifier.parse_tags_from_db(bet['tags'])
                        if tags_list:
                            tags_display = " | ".join(tags_list)
                            report += f"      🏷️  {tags_display}\n"
                    except: pass

                if bet['note']:
                    report += f"      📝 {bet['note']}\n"
        
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