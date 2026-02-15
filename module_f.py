import pandas as pd
from datetime import datetime
import config
from utils.devig import get_fair_probability, calculate_true_edge, american_to_implied
from utils.bet_logger import get_bet_logger
from utils.tag_classifier import get_tag_classifier
from utils.time_utils import get_est_today, format_est_date

# WOWY & Smart Blowout Tax (V4.7)
try:
    from utils.blowout_tax import calculate_blowout_tax
    BLOWOUT_TAX_AVAILABLE = True
except ImportError:
    BLOWOUT_TAX_AVAILABLE = False
    print("⚠️ [Module F] utils/blowout_tax.py not found - using fallback")

# ==============================================================================
# LUDI INFORMATIO | MODULE F: THE ALCHEMIST
# V5.2 - CONFIDENCE TIER SYSTEM | FEB 2026
# ==============================================================================
# CHANGELOG V5.2 (Feb 2026):
# - Fixed negative edge leak (abs(edge) → edge in sharp filter)
# - Added edge dampening for 20%+ edges (diminishing returns)
# - Implemented composite confidence tier (edge + gold combos)
# - Switched to tier-based unit sizing (DIAMOND=1.0, BLUE CHIP=0.75, etc.)
# - Gold combos: BLK/3PM/TOV/STL UNDER (+1 tier)
# - Archetype modifiers DISABLED (audit needed first)
#
# CHANGELOG V5.1 (Feb 2, 2026):
# - Added REB OVER filter (skip until calibration - was -198u leak)
# - Added 3PM OVER filter for low-volume shooters (<5 3PA)
# - Reduced max unit sizing from 1.5u to 1.0u for conservative testing
# - Widened stdevs by 30% to reduce probability overconfidence
#
# CHANGELOG V4.4:
# - Added devigging to calculate TRUE edge against fair market probability
# - Edge calculation now removes bookmaker vig (~2-5%) for accurate EV
# - Supports fallback to raw odds if over/under pair not available
# ==============================================================================

class LudiReporter:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE F (V5.2) ONLINE")
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

    def generate_report(self, processed_slate, title="LUDI GAME BRIEF"):
        """
        Final synthesis of the simulation results into actionable alerts.
        Processes the slate and applies 2026 sharp-market filters.
        """
        all_props = []
        
        for game in processed_slate:
            # --- 1. SMART BLOWOUT TAX (V4.7) ---
            # Context-aware: Favorites get taxed, underdogs neutral, bench gets boost
            spread = game.get('spread', 0)  # Positive = underdog, Negative = favorite
            
            # Determine favorite status: negative spread = favorite
            game_is_favorite = spread < 0
            
            # For fallback (old logic if utility not available)
            if not BLOWOUT_TAX_AVAILABLE:
                blowout_mult_fallback = 1.0 - (max(0, abs(spread) - 10.0) * 0.02)
            
            for p in game['players']:
                # UPSTREAM GUARDRAIL: Skip players with zero projected minutes 
                # or those explicitly ruled OUT by Module D (The Yak).
                if p.get('proj_min', 0) <= 0 or p.get('status') == 'OUT':
                    continue
                
                # Calculate player-specific blowout tax
                if BLOWOUT_TAX_AVAILABLE:
                    # Player on home team: spread is from home perspective
                    # Player on away team: flip the spread
                    player_team = p.get('TEAM_ABBREVIATION', '')
                    home_team = game.get('home_team', '')
                    player_is_favorite = game_is_favorite if player_team == home_team else not game_is_favorite
                    player_is_starter = p.get('base_min', 0) >= 28.0
                    blowout_mult = calculate_blowout_tax(
                        spread=abs(spread),  # Use absolute spread
                        is_favorite=player_is_favorite,
                        is_starter=player_is_starter,
                        base_min=p.get('base_min', 0)
                    )
                else:
                    blowout_mult = blowout_mult_fallback
                
                player_props = []
                if 'sportsbook_props' in p:
                    for stat_key, prop_data in p['sportsbook_props'].items():
                        # Handle both old format (line only) and new format (dict with odds + books)
                        if isinstance(prop_data, dict):
                            line = prop_data.get('line', 0)
                            odds_over = prop_data.get('odds_over', -110)
                            odds_under = prop_data.get('odds_under', -110)
                            book_over = prop_data.get('book_over', 'consensus')  # NEW: Line Shopping V2.0
                            book_under = prop_data.get('book_under', 'consensus')
                        else:
                            # Legacy format: just the line value
                            line = prop_data
                            odds_over = -110  # Assume standard juice
                            odds_under = -110
                            book_over = 'consensus'
                            book_under = 'consensus'

                        # Map internal projection keys to common sportsbook prop keys
                        # Ensure line is numeric
                        if not isinstance(line, (int, float)):
                            continue

                        raw_val = self._map_stat(p, stat_key)

                        # Apply Final 2026 Blowout Modifier
                        final_proj = raw_val * blowout_mult

                        # --- V5.0: SIMULATION-BASED PROBABILITY (CORRECT) ---
                        # Use ACTUAL hit rate from 5000 Monte Carlo simulations
                        sim_hit_rates = p.get('sim_hit_rates', {})
                        
                        if stat_key in sim_hit_rates:
                            # USE REAL SIMULATION DATA
                            our_prob = sim_hit_rates[stat_key]
                        else:
                            # Fallback to heuristic
                            our_prob = self._estimate_over_probability(final_proj, line, stat_key)

                        # Determine bet direction
                        bet_direction = 'over' if final_proj > line else 'under'
                        model_prob = our_prob if bet_direction == 'over' else (1 - our_prob)

                        # --- V5.1: CALIBRATION FILTERS (Feb 2026) ---
                        # Skip bets that historically underperform based on Jan 2026 analysis

                        # Filter 1: REB OVER (-198 units leak in backtest)
                        # Model over-projects rebounds by ~1.65 per bet
                        if stat_key.lower() == 'reb' and bet_direction == 'over':
                            continue  # Skip until REB calibration complete

                        # Filter 2: 3PM OVER on low-volume shooters
                        # Only bet 3PM OVER on players with 5+ 3PA average
                        if stat_key.lower() == '3pm' and bet_direction == 'over':
                            player_3pa_avg = p.get('base_3pa', 0) or p.get('season_3pa', 0)
                            if player_3pa_avg < 5.0:
                                continue  # Skip low-volume shooters

                        # --- END CALIBRATION FILTERS ---

                        # Calculate TRUE edge using devigged fair probability
                        edge = calculate_true_edge(
                            model_prob,
                            odds_over,
                            odds_under,
                            side=bet_direction
                        )
                        edge = round(edge, 1)

                        # WOWY Confidence Penalty (Phase 6.3 Enhancement)
                        # Reduce edge for low-confidence BENEFICIARY plays
                        wowy_confidence = p.get('wowy_confidence', None)
                        if wowy_confidence:
                            wowy_edge_multipliers = {
                                'high': 1.0,      # Full edge - strong WOWY data
                                'medium': 0.90,   # 10% penalty - moderate data
                                'low': 0.75,      # 25% penalty - weak data
                            }
                            edge = round(edge * wowy_edge_multipliers.get(wowy_confidence, 0.75), 1)

                        # --- V5.2: EDGE DAMPENING (Feb 2026 Calibration) ---
                        # 20%+ edge bets are overconfident by ~10% (backtest Jan 7-29)
                        # Apply diminishing returns above 20% to align with actual win rates
                        if edge >= 20.0:
                            excess = edge - 20.0
                            edge = round(20.0 + (excess * 0.5), 1)  # Half-credit above 20%
                        # --- END EDGE DAMPENING ---

                        # Store fair probability for reporting
                        fair_prob = get_fair_probability(odds_over, odds_under, bet_direction)

                        # --- 2. THE SHARP FILTER (5% Minimum Edge) ---
                        if edge >= 5.0:
                            # V4.6: Use real model probability (removed 0.51-0.75 clamp)
                            win_prob = model_prob

                            # Calculate Decimal Odds for accurate EV
                            bet_odds = odds_over if bet_direction == 'over' else odds_under
                            if bet_odds > 0:
                                decimal_odds = 1 + (bet_odds / 100)
                            else:
                                decimal_odds = 1 + (100 / abs(bet_odds))

                            # EV Calculation using actual odds
                            ev = round(((win_prob * decimal_odds) - 1) * 100, 2)

                            # V4.6: Sanity check - flag unrealistic EV
                            ev_flag = ""
                            if ev > 25:
                                ev_flag = "⚠️ VERIFY LINE"
                            elif ev > 15:
                                ev_flag = "📊 EXCEPTIONAL"

                            # V5.2: Composite confidence tier (edge + gold combos)
                            confidence_tier = self._calculate_confidence_tier(
                                edge=edge,
                                archetype=p.get('archetype', ''),
                                stat_key=stat_key,
                                bet_direction=bet_direction
                            )

                            # V5.2: Tier-based unit sizing (replaces EV-formula sizing)
                            TIER_UNITS = {
                                'DIAMOND': 1.0,
                                'BLUE CHIP': 0.75,
                                'CORE ASSET': 0.5,
                                'THE STEAL': 0.25,
                            }
                            units = TIER_UNITS.get(confidence_tier, 0.25)

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
                                
                                # C2) WOWY Confidence Note (V4.7)
                                wowy_conf = p.get('wowy_confidence', None)
                                if wowy_conf in ['high', 'medium']:
                                    conf_emoji = "✅" if wowy_conf == 'high' else "📊"
                                    note_elements.append(f"{conf_emoji} WOWY: {wowy_conf.upper()} confidence")
                            
                            # D) Status Flag (from Module D)
                            if p.get('status') in ['Q', 'GTD']:
                                note_elements.append(f"🚨 GTD Risk")

                            # E) Referee Context (from Module G)
                            if abs(game.get('ref_impact', 1.0) - 1.0) > 0.04:
                                ref_val = game.get('ref_impact')
                                ref_note = f"⚖️ Refs Boost Overs ({ref_val}x)" if ref_val > 1.0 else f"⚖️ Refs Drag Unders ({ref_val}x)"
                                note_elements.append(ref_note)

                            # F) Yak Decision Note (V2.0 - Explicit Injury Confirmation)
                            if p.get('decision_note'):
                                note_elements.append(p['decision_note'])

                            # G) EV Sanity Flag (V4.6)
                            if ev_flag:
                                note_elements.append(ev_flag)

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
                                    run_date = get_est_today()
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
                                        'confidence_tier': confidence_tier,
                                        'note': " | ".join(note_elements),
                                        'tags': tags_formatted,  # Week 2, Days 3-4: Tag classification
                                        'referee_impact': game.get('ref_impact', 1.0),
                                        'blowout_modifier': round(blowout_mult, 3),
                                        'run_type': 'production',
                                        'bookmaker': book_over if bet_direction == 'over' else book_under  # Line Shopping V2.0
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
                                "ev": edge,  # V2.1: Now using devigged edge (not inflated ev)
                                "units": units,
                                "note": " | ".join(note_elements),
                                "tags": tags_formatted  # Week 2, Days 3-4: Tag classification
                            })

                # --- 4. CORRELATION CHECK (SGP TARGETS) ---
                if len([x for x in player_props if x['units'] >= 1.2]) >= 2:
                    for x in player_props: 
                        x['note'] += " [🔥 CORRELATED SGP]"
                
                all_props.extend(player_props)

        # --- DEDUPLICATION (Best Bet Per Player/Stat) ---
        # Prioritize highest EV if multiple lines exist (e.g. 8.5 vs 9.5)
        unique_props = {}
        for p in all_props:
            key = (p['name'], p['stat'])
            if key not in unique_props:
                unique_props[key] = p
            else:
                # Keep the one with higher EV
                if p['ev'] > unique_props[key]['ev']:
                    unique_props[key] = p
        
        all_props = list(unique_props.values())

        # Sort by EV descending for the "Diamond" ranking
        all_props.sort(key=lambda x: x['ev'], reverse=True)

        # --- DAILY SUMMARY LOGGING ---
        if self.bet_logger and all_props:
            try:
                run_date = get_est_today()
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

        # --- PREPARE VISUALS (CURATED TOP 3 PER GAME) ---
        visual_props = []
        grouped = {}
        for p in all_props:
            m = p.get('matchup', 'Unknown')
            if m not in grouped: grouped[m] = []
            grouped[m].append(p)
            
        for m in sorted(grouped.keys()):
            # Sort by EV and take top 3
            grouped[m].sort(key=lambda x: x['ev'], reverse=True)
            visual_props.extend(grouped[m][:3])

        # Generate visual card (V4.6 - Visual Upgrade)
        image_path = self.generate_image_card(visual_props, title=title)
        
        return self.create_daily_briefing(all_props), image_path

    def generate_image_card(self, props: list, title: str = "LUDI GAME BRIEF") -> str:
        """
        Generate a visual briefing card PNG from props data.
        
        Args:
            props: List of prop dictionaries from generate_report
            title: Title text for the card
            
        Returns:
            Path to generated PNG file
        """
        try:
            from utils.render_full_report import create_briefing_card
            image_path = create_briefing_card(props, title=title)
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
            'oreb': 'proj_oreb',
            'steals': 'proj_stl',
            'blocks': 'proj_blk',
            'defensive_rebounds': 'proj_dreb'
        }
        return p.get(m.get(key.lower(), ''), 0)

    def _calculate_confidence_tier(self, edge, archetype='', stat_key='', bet_direction=''):
        """
        Composite confidence tier using edge + historical performance signals.

        Factors:
        1. True edge % (primary — determines base tier)
        2. Stat-direction performance (±1 tier for "gold combos")

        Data source: Jan 7-29, 2026 backtest (6,344 bets, +292u, 55.7% WR)
        See: reports/CALIBRATION_RECOMMENDATIONS_FEB2.md
        """
        # --- Base tier from edge (matches docs/METHODOLOGY.md) ---
        if edge >= 15.0:
            tier_score = 3     # DIAMOND zone
        elif edge >= 10.0:
            tier_score = 2     # BLUE CHIP zone
        elif edge >= 7.0:
            tier_score = 1     # CORE ASSET zone
        else:
            tier_score = 0     # THE STEAL zone

        # --- Archetype modifier (DISABLED until archetype audit complete) ---
        # KNOWN ISSUE: 3 inconsistent archetype systems exist in codebase.
        # Misclassifications found: Turner/Lopez/Porzingis → TWO_WAY_WING,
        # Westbrook → STRETCH_BIG, etc. Position-agnostic thresholds cause this.
        # DO NOT enable until classification is fixed.

        # --- Stat-direction modifier (gold combos from backtest) ---
        GOLD_COMBOS = {
            'BLK_UNDER',   # +122.6u, 71.9% WR
            '3PM_UNDER',   # +151.1u, 68.1% WR
            'TOV_UNDER',   # +79.8u, 71.1% WR
            'STL_UNDER',   # +114.5u, 53.4% WR
        }
        stat_dir = f"{stat_key}_{bet_direction}".upper()
        if stat_dir in GOLD_COMBOS:
            tier_score += 1

        # Clamp to valid range [0, 3]
        tier_score = max(0, min(3, tier_score))

        TIER_NAMES = ['THE STEAL', 'CORE ASSET', 'BLUE CHIP', 'DIAMOND']
        return TIER_NAMES[tier_score]

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
        # Typical standard deviations by stat category
        # V5.1 (Feb 2026): Widened by ~30% to reduce overconfidence
        # Based on analysis showing model probabilities were too extreme
        # Research: FiveThirtyEight uses wider bands; props have high variance
        stat_stdev = {
            'pts': 8.5,    # Points: widened from 6.5 to 8.5
            'reb': 4.2,    # Rebounds: widened from 3.2 to 4.2
            'ast': 3.3,    # Assists: widened from 2.5 to 3.3
            '3pm': 1.7,    # Three-pointers made: widened from 1.3 to 1.7
            'oreb': 2.0,   # Offensive rebounds: widened from 1.5 to 2.0
            'stl': 1.2,    # Steals: widened from 0.9 to 1.2
            'blk': 1.3,    # Blocks: widened from 1.0 to 1.3
            'tov': 1.6,    # Turnovers: widened from 1.2 to 1.6
            'pra': 10.4,   # Pts+Reb+Ast combo: widened from 8.0 to 10.4
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
        report = f"\n📰 LUDI ELITE BRIEFING ({format_est_date('%b %d, %Y')})\n"
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