import json
import re
import pandas as pd
from datetime import datetime
import config
from utils.devig import get_fair_probability, calculate_true_edge, american_to_implied
from utils.bet_logger import get_bet_logger
from utils.tag_classifier import get_tag_classifier
from utils.time_utils import get_est_today, format_est_date, get_time_context

# WOWY & Smart Blowout Tax (V4.7)
try:
    from utils.blowout_tax import calculate_blowout_tax
    BLOWOUT_TAX_AVAILABLE = True
except ImportError:
    BLOWOUT_TAX_AVAILABLE = False
    print("⚠️ [Module F] utils/blowout_tax.py not found - using fallback")

# ==============================================================================
# LUDI INFORMATIO | MODULE F: THE ALCHEMIST
# V5.3 - STAT CONFIDENCE & EDGE CALIBRATION | FEB 2026
# ==============================================================================
# CHANGELOG V5.3 (Feb 20, 2026):
# - Added _apply_stat_calibration(): deflates edge for PTS/REB/AST (19% overconfident)
#   and boosts BLOCKS UNDER (structural book inefficiency, underestimated by model)
# - Added _rmse_sizing_modifier(): RMSE-based unit penalty (PTS/PRA high-variance)
# - See: best-practices/data/STAT_CONFIDENCE_FRAMEWORK.md for full methodology
# - Data source: 14,000+ settled bets (Jan 7 – Feb 20, 2026)
#
# CHANGELOG V5.2 (Feb 2026):
# - Fixed negative edge leak (abs(edge) → edge in sharp filter)
# - Added edge dampening for 20%+ edges (diminishing returns)
# - Implemented composite confidence tier (edge + gold combos)
# - Switched to tier-based unit sizing (DIAMOND=1.0, BLUE CHIP=0.75, etc.)
# - Gold combos: BLK/3PM/TOV/STL UNDER (+1 tier)
# - Archetype modifiers re-enabled after Phase 7.9 archetype overhaul

# --- STAT CALIBRATION CONSTANTS (V5.3) ---
# Edge multipliers: calibration_gap analysis from 14k+ settled bets.
# BLOCKS UNDER: model avg_edge=-2.8% but WR=66.4% → books set lines too high → boost.
# PTS/REB/PRA: model avg_edge=33-40% but WR=46-52% → model overconfident → deflate.
_STAT_EDGE_CALIBRATION = {
    'blk':      {'under': 1.25, 'over': 1.00},
    'blocks':   {'under': 1.25, 'over': 1.00},   # same stat, different label era
    'tov':      {'under': 1.10, 'over': 1.00},
    'turnovers':{'under': 1.10, 'over': 1.00},
    'stl':      {'under': 1.00, 'over': 1.00},
    'steals':   {'under': 1.00, 'over': 1.00},   # improving trend, well-calibrated
    '3pm':      {'under': 0.90, 'over': 0.90},   # 11% overconfident
    'ast':      {'under': 0.87, 'over': 0.87},   # 13% overconfident
    'reb':      {'under': 0.82, 'over': 0.80},   # 18% overconfident + degrading
    'pts':      {'under': 0.80, 'over': 0.78},   # 19.5% overconfident
    'pra':      {'under': 0.85, 'over': 0.70},   # most volatile; OVER is structural avoid
    'pa':       {'under': 0.90, 'over': 0.72},   # PA OVER 36.9% WR (D grade)
    'pr':       {'under': 0.88, 'over': 0.75},   # PR OVER 38.2% WR
    'ra':       {'under': 0.92, 'over': 0.92},   # moderate, small sample
}

# RMSE of projection vs market line by stat (absolute units, Feb 2026).
# Low RMSE = projection reliable = no sizing penalty.
# High RMSE = projection uncertain = reduce units even at same edge/tier.
_STAT_RMSE = {
    'blk': 0.35,  'blocks': 0.35,
    'stl': 0.46,  'steals': 0.46,
    '3pm': 0.67,
    'ast': 1.24,
    'reb': 1.87,
    'pts': 4.93,
    'pa':  4.80,  'pr': 4.96,  'pra': 5.51,
}
#
# --- STAT EDGE MINIMUMS (V5.5 Calibration) ---
STAT_EDGE_MINIMUMS = {
    'blk':   3.0,   # Blocks UNDER — structural edge, even 3% wins 70.7%
    'blocks': 3.0,
    'pts':   {'over': 12.0, 'under': 7.0},  # raised: 8→12 (49.9% OVER WR, 33% avg edge)
    'reb':   {'over': 999.0, 'under': 6.0}, # safety net — already hard-filtered
    'ast':   {'over': 10.0, 'under': 5.0},  # directional split (was flat 6.0)
    'stl':   {'over': 8.0, 'under': 4.0},   # added: STL OVER 49% WR, avg_edge only 4.8%
    '3pm':   {'over': 8.0, 'under': 4.0},   # added: 3PM OVER 45% WR (supplements volume filter)
    'pra':   {'over': 999.0, 'under': 6.0}, # PRA OVER = skip (STRUCTURAL_LOSERS covers this)
    'pa':    {'over': 999.0, 'under': 6.0},
}
DEFAULT_EDGE_MIN = 5.0

# --- STRUCTURAL LOSERS (V5.4) ---
# Stat+direction combos with no recoverable edge — skip entirely before threshold check.
STRUCTURAL_LOSERS = {
    ('pra', 'over'),   # 25.0% WR — F grade
    ('pa',  'over'),   # 36.9% WR — F grade
}

def _get_stat_edge_min(stat_key, direction):
    floor = STAT_EDGE_MINIMUMS.get(stat_key.lower(), DEFAULT_EDGE_MIN)
    if isinstance(floor, dict):
        return floor.get(direction.lower(), DEFAULT_EDGE_MIN)
    return floor

# --- CANONICAL STAT CATEGORY MAP (Feb 25, 2026) ────────────────────────────
# All prop market names normalize to these canonical keys at write time.
# This prevents BLOCKS vs BLK split in analytics (same prop, two names across
# pipeline versions). Applied at bet_recommendations write + player_props dict.
_STAT_CATEGORY_CANONICAL = {
    # Verbose → short
    'POINTS': 'PTS',       'REBOUNDS': 'REB',      'ASSISTS': 'AST',
    'BLOCKS': 'BLK',       'STEALS': 'STL',         'TURNOVERS': 'TOV',
    'THREES': '3PM',       'THREE_POINTERS': '3PM', 'THREE_POINT_FIELD_GOALS': '3PM',
    'DEFENSIVE_REBOUNDS': 'DREB',
    'OFFENSIVE_REBOUNDS': 'OREB',
    # Already canonical — pass through unchanged
    'PTS': 'PTS', 'REB': 'REB', 'AST': 'AST',
    'BLK': 'BLK', 'STL': 'STL', 'TOV': 'TOV', '3PM': '3PM',
    'PRA': 'PRA', 'PA': 'PA',   'PR': 'PR',   'RA': 'RA',
    'DREB': 'DREB', 'OREB': 'OREB',
}

def _normalize_stat_category(raw: str) -> str:
    """Map any prop market name → canonical short form. Falls back to raw.upper()."""
    return _STAT_CATEGORY_CANONICAL.get((raw or '').upper(), (raw or '').upper())


# --- ARCHETYPE SANITIZATION (Feb 25, 2026) ───────────────────────────────────
# Prevents defensive tags (RIM_GUARDIAN, PERIMETER_HAWK, etc.) and legacy
# pre-Phase-7 archetype names from propagating into bet_recommendations.archetype.
# Root cause: players.archetype was historically set to defensive tags for some
# players before the Phase 7 hybrid off/def split; those snapshots froze in bets.
_VALID_OFFENSIVE_ARCHETYPES = frozenset({
    'GENERALIST', 'SNIPER_ELITE', 'CONNECTOR', 'ENERGY_BIG', 'CUTTER_SPECIALIST',
    'STRETCH_BIG', 'HELIOCENTRIC_MAESTRO', 'ROLL_MAN', 'TWO_LEVEL_SCORER', 'WARRIOR_BIG',
    'SLASHING_CREATOR', 'JUMBO_FACILITATOR', 'ISO_ASSASSIN', 'FACILITATOR', 'HUB_BIG',
})
_DEFENSIVE_TAGS = frozenset({
    'RIM_GUARDIAN', 'PERIMETER_HAWK', 'SWITCHABLE_ANCHOR', 'HUSTLE_DISRUPTOR', 'WEAK_LINK'
})
# Pre-Phase-7 archetype names → current equivalents
_LEGACY_ARCHETYPE_MAP = {
    'POST_ANCHOR': 'HUB_BIG',      'RIM_RUNNER': 'ROLL_MAN',
    'HELIOCENTRIC': 'HELIOCENTRIC_MAESTRO',
    'SNIPER': 'SNIPER_ELITE',      'ELITE_SCORER': 'ISO_ASSASSIN',
    'TWO_WAY_WING': 'TWO_LEVEL_SCORER', 'JUMBO_CREATOR': 'JUMBO_FACILITATOR',
    'SLASHER': 'SLASHING_CREATOR', 'STRETCH_BIG_SHOOTER': 'STRETCH_BIG',
}

def _sanitize_archetype(raw: str) -> str:
    """Return a valid offensive archetype. Rejects defensive tags + maps legacy names."""
    arch = (raw or '').upper().strip()
    if arch in _VALID_OFFENSIVE_ARCHETYPES:
        return arch
    if arch in _DEFENSIVE_TAGS:
        return 'GENERALIST'  # Defensive identity ≠ offensive role for prop betting
    return _LEGACY_ARCHETYPE_MAP.get(arch, 'GENERALIST')


def _classify_edge_type(scenario: str, note_elements: list, tags_formatted: str, games_since_return: int = None, player_name: str = None) -> str:
    """Phase 8.24 — Classify primary edge driver for bet labeling."""
    scenario_str = (scenario or '').upper()
    note_str = ' | '.join(note_elements).lower() if note_elements else ''
    tags_str = (tags_formatted or '').lower()

    # Injury-Vacuum: beneficiary scenario or usage vacuum
    if 'WITHOUT' in scenario_str or 'beneficiary' in note_str or 'usage_vacuum' in tags_str:
        return 'Injury-Vacuum'

    # Injury return ramp-up (Module C G3) — players returning from 7+ day absence
    # main.py:465 passes sim.get('GAMES_SINCE_RETURN') — no DB fallback needed.
    gsr = games_since_return
    if gsr is None:
        gsr = note_elements[0].get('games_since_return') if note_elements and isinstance(note_elements[0], dict) else None

    if gsr and int(gsr) <= 4:
        return 'Injury-Return'

    # Hot-Streak: explicit streak signal in tags or note
    if 'hot_streak' in tags_str or 'streak' in note_str:
        return 'Hot-Streak'

    # Matchup: archetype vs defense scheme signal
    matchup_signals = ['paint_pack', 'blitz', 'perimeter', 'funnel', 'hackers',
                       'matchup', 'scheme', 'archetype', '+%']
    if any(signal in note_str for signal in matchup_signals):
        return 'Matchup'

    return 'Projection'


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
        print(f"LUDI INFORMATIO: MODULE F (V5.3) ONLINE")
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

        # Phase 8.20: BDL fallback flag (set externally by Gatekeeper)
        self._bdl_fallback_active = False

        # Phase 8.20: Load stat confidence cache (built nightly by build_stat_confidence.py)
        # When sample_n >= 200, live calibration_gap + RMSE override hardcoded constants.
        # Falls back to _STAT_EDGE_CALIBRATION / _STAT_RMSE when cache is missing or thin.
        self._stat_conf = self._load_stat_confidence_cache()

        # C1: Hit rate cache — {(player_name, stat_key, line, direction): (l5_hr, l10_hr)}
        # Populated lazily during generate_report(); avoids duplicate DB queries per player.
        self._hit_rate_cache = {}
        live_count = sum(1 for v in self._stat_conf.values() if v.get('sample_n', 0) >= 200)
        print(f"✅ Stat confidence cache: {len(self._stat_conf)} entries ({live_count} with live calibration)")

    def generate_report(self, processed_slate, title="LUDI GAME BRIEF"):
        """
        Final synthesis of the simulation results into actionable alerts.
        Processes the slate and applies 2026 sharp-market filters.
        """
        all_props = []
        # Time-context mode for this pipeline run — written to each bet_recommendation row.
        # Drives confidence framing in downstream consumers (Ask Ludi, Ludi Lens, bet cards).
        # EARLY_LOOK (<noon) → AFTERNOON (noon-5 PM) → PRE_GAME (5-7 PM) → LOCK_TIME (>7 PM)
        _run_time_context = get_time_context()['mode']

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
                if p.get('proj_min', 0) <= 0 or p.get('status', '').upper() in ('OUT', 'DOUBTFUL'):
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

                        # Filter 3: TWO_LEVEL_SCORER OVER — systematically over-projected (35.7%, n=314)
                        # FIXME: Calibration window — verify if this still holds post-ASB (Feb 2026 data)
                        if p.get('archetype') == 'TWO_LEVEL_SCORER' and bet_direction == 'over':
                            continue

                        # Filter: BLK OVER hard skip (33.6% WR on 378 bets — books price this well)
                        if stat_key.lower() in ('blk', 'blocks') and bet_direction == 'over':
                            continue

                        # Filter 4: PTS OVER on high lines — high-scorer over-projection
                        if stat_key.lower() == 'pts' and bet_direction == 'over' and line >= 25.0:
                            model_prob = model_prob * 0.85

                        # Filter 5: SAC/IND/CLE — OVER graveyard defenders (26-34% hit rate, 700+ bets combined)
                        _OVER_KILL_DEFENSES = {'SAC', 'IND', 'CLE'}
                        _opp = p.get('opponent', '')
                        if bet_direction == 'over' and _opp in _OVER_KILL_DEFENSES:
                            continue

                        # --- END CALIBRATION FILTERS ---

                        # --- Filter 3: PROJECTION/LINE SANITY GATE (BDL Fallback) ---
                        # BDL posts the full alt-line ladder. If our projection is >40% away
                        # from the line, it's almost certainly an alt line (e.g. 14.5 PR when
                        # the player projects at 9.75). These produce 60%+ edges that aren't real.
                        # Only applies in BDL fallback mode — Odds-API lines are market consensus.
                        _src_quality = prop_data.get('source_quality', 'UNKNOWN') if isinstance(prop_data, dict) else 'UNKNOWN'
                        _gap = abs(final_proj - line) / final_proj if final_proj > 0 else 0
                        if _gap > 0.40 and _src_quality == 'BDL_FALLBACK':
                            continue  # Skip: projection vs line gap >40% in BDL fallback = alt line

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

                        # --- V5.3: STAT CALIBRATION (Feb 20, 2026) ---
                        # Deflates edge for high-variance stats (PTS/REB 19% overconfident)
                        # Boosts edge for BLOCKS UNDER (structural book inefficiency)
                        # See: best-practices/data/STAT_CONFIDENCE_FRAMEWORK.md
                        edge = self._apply_stat_calibration(edge, stat_key, bet_direction)
                        # --- END STAT CALIBRATION ---

                        # Store fair probability for reporting
                        fair_prob = get_fair_probability(odds_over, odds_under, bet_direction)

                        # --- STRUCTURAL LOSERS FILTER ---
                        if (stat_key.lower(), bet_direction.lower()) in STRUCTURAL_LOSERS:
                            continue

                        # --- 2. THE SHARP FILTER (Stat-Specific Minimum Edge) ---
                        min_edge = _get_stat_edge_min(stat_key, bet_direction)
                        if edge >= min_edge:
                            # V4.6: Use real model probability (removed 0.51-0.75 clamp)
                            win_prob = model_prob

                            # Calculate Decimal Odds for accurate EV
                            bet_odds = odds_over if bet_direction == 'over' else odds_under
                            if bet_odds > 0:
                                decimal_odds = 1 + (bet_odds / 100)
                            else:
                                decimal_odds = 1 + (100 / abs(bet_odds))

                            # EV Calculation using actual odds
                            ev_raw = round(((win_prob * decimal_odds) - 1) * 100, 2)

                            # Line source quality and consensus tracking (from prop_data dict)
                            source_quality = prop_data.get('source_quality', 'UNKNOWN') if isinstance(prop_data, dict) else 'UNKNOWN'
                            vendor_count = prop_data.get('vendor_count', 0) if isinstance(prop_data, dict) else 0

                            # Sanity gate: if EV > 100%, line quality is suspect
                            # Cap display at 99.9% — math is preserved in DB, display is readable
                            ev_capped = ev_raw > 100
                            ev = min(ev_raw, 99.9)

                            # EV quality flags (updated per industry thresholds)
                            ev_flag = ""
                            if ev_capped:
                                ev_flag = "⚠️ DATA QUALITY"  # >100% EV → line source issue
                            elif ev_raw > 25:
                                ev_flag = "⚠️ VERIFY LINE"   # 25-100% EV → review before betting
                            elif ev_raw > 15:
                                ev_flag = "📊 EXCEPTIONAL"   # 15-25% → strong edge

                            # V5.2: Composite confidence tier (edge + gold combos)
                            # Prefer stat-specific streak from Module B hit_rates_by_market
                            _hrm = p.get('hit_rates_by_market') or {}
                            _stat_hrm = _hrm.get(stat_key, {}) if isinstance(_hrm, dict) else {}
                            confidence_tier, confirmation_score = self._calculate_confidence_tier(
                                edge=edge,
                                archetype=p.get('archetype', ''),
                                stat_key=stat_key,
                                bet_direction=bet_direction,
                                model_prob=model_prob,
                                player_name=p['name'],
                                line=line,
                                hit_rates_by_market=p.get('hit_rates_by_market'),
                                streak_score=_stat_hrm.get('streak_score', p.get('streak_score', 0.5)),
                                matchup_modifier=p.get('scheme_modifier', 0.0),
                                dvp_rank=p.get('dvp_rank', None),
                                odds_over=odds_over,
                                odds_under=odds_under,
                                sharp_odds_over=p.get('sportsbook_props', {}).get(stat_key, {}).get('sharp_odds_over') if isinstance(p.get('sportsbook_props', {}).get(stat_key), dict) else None,
                                sharp_odds_under=p.get('sportsbook_props', {}).get(stat_key, {}).get('sharp_odds_under') if isinstance(p.get('sportsbook_props', {}).get(stat_key), dict) else None,
                                wowy_confidence=p.get('wowy_confidence'),
                                crew_bias=p.get('crew_bias', {}).get('label') if isinstance(p.get('crew_bias'), dict) else None
                            )
                            # Let's save sharp values for DB logging
                            sharp_odds_over_at_bet = p.get('sportsbook_props', {}).get(stat_key, {}).get('sharp_odds_over') if isinstance(p.get('sportsbook_props', {}).get(stat_key), dict) else None
                            sharp_odds_under_at_bet = p.get('sportsbook_props', {}).get(stat_key, {}).get('sharp_odds_under') if isinstance(p.get('sportsbook_props', {}).get(stat_key), dict) else None
                            sharp_book_at_bet = (
                                p.get('sportsbook_props', {}).get(stat_key, {}).get('sharp_book_over')
                                if bet_direction == 'over' else
                                p.get('sportsbook_props', {}).get(stat_key, {}).get('sharp_book_under')
                            ) if isinstance(p.get('sportsbook_props', {}).get(stat_key), dict) else None

                            # Compute sharp_consensus for DB logging (same calc as inside _calculate_confidence_tier)
                            _bet_sharp_odds = sharp_odds_over_at_bet if bet_direction == 'over' else sharp_odds_under_at_bet
                            _bet_actual_odds = odds_over if bet_direction == 'over' else odds_under
                            sharp_consensus = self._sharp_consensus(_bet_actual_odds, _bet_sharp_odds, bet_direction)

                            # V5.2: Tier-based unit sizing (replaces EV-formula sizing)
                            TIER_UNITS = {
                                'DIAMOND': 1.25,
                                'BLUE CHIP': 1.00,
                                'CORE ASSET': 0.65,
                                'THE STEAL': 0.35,
                            }
                            units = TIER_UNITS.get(confidence_tier, 0.25)
                            if confidence_tier not in TIER_UNITS:
                                print(f"⚠️  Unknown confidence_tier '{confidence_tier}' — defaulting to 0.25u")

                            # V5.3: RMSE-based sizing modifier
                            # High projection uncertainty (PTS/PRA) → smaller bet at same tier
                            units = round(units * self._rmse_sizing_modifier(stat_key), 2)

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
                            ref_data = game.get('ref_data', {})
                            ref_pace = ref_data.get('pace_impact', 1.0) if isinstance(ref_data, dict) else 1.0
                            if abs(ref_pace - 1.0) > 0.04:
                                ref_note = f"⚖️ Refs Boost Overs ({ref_pace}x)" if ref_pace > 1.0 else f"⚖️ Refs Drag Unders ({ref_pace}x)"
                                note_elements.append(ref_note)

                            # E2) Star Bias — per-player historical vs this specific crew
                            # Only fires for STAR_KILLER / PROTECTOR labels (≥3.5 PPG delta, ≥5 games)
                            _crew_bias = p.get('crew_bias')
                            if _crew_bias and _crew_bias.get('label') in ('STAR_KILLER', 'PROTECTOR'):
                                _impact = _crew_bias['points_impact']
                                _fta    = _crew_bias['avg_fta_awarded']
                                _sign   = '+' if _impact > 0 else ''
                                _lbl    = '🔥 PROTECTOR' if _crew_bias['label'] == 'PROTECTOR' else '🩸 STAR_KILLER'
                                note_elements.append(
                                    f"{_lbl}: {_sign}{_impact:.1f} PPG / {_fta:.1f} FTA avg ({_crew_bias['games_total']}g)"
                                )

                            # F) Yak Decision Note (V2.0 - Explicit Injury Confirmation)
                            if p.get('decision_note'):
                                note_elements.append(p['decision_note'])

                            # G) EV Sanity Flag + Consensus Quality Note
                            if ev_flag:
                                note_elements.append(ev_flag)
                            # H) Line Source & Consensus Strength
                            if source_quality == 'BDL_FALLBACK':
                                consensus_note = f"[BDL:{vendor_count}bk]" if vendor_count else "[BDL]"
                                note_elements.append(consensus_note)
                            elif source_quality == 'ODDS_API' and vendor_count >= 4:
                                note_elements.append(f"[{vendor_count}bk consensus]")
                            elif source_quality == 'ODDS_API' and vendor_count > 0:
                                note_elements.append(f"[{vendor_count}bk]")

                            # I) Multi-window hit rates (CR1 — Outlier/PropsMadness pattern)
                            # Module B pre-computes L5/L10/L15/L20 in hit_rates_by_market — zero DB cost.
                            # Keys: over_l5, over_l10, over_l15, over_l20 (same for under_).
                            # Sample sizes are fixed by window, so counts are derivable.
                            _hr_by_mkt = p.get('hit_rates_by_market')
                            if _hr_by_mkt:
                                _hr_entry = _hr_by_mkt.get(stat_key.lower())
                                if _hr_entry:
                                    _dir = bet_direction  # 'over' or 'under'
                                    _l5 = _hr_entry.get(f'{_dir}_l5')
                                    _l10 = _hr_entry.get(f'{_dir}_l10')
                                    _l15 = _hr_entry.get(f'{_dir}_l15')
                                    _l20 = _hr_entry.get(f'{_dir}_l20')
                                    _hr_parts = []
                                    if _l5 is not None:
                                        _hr_parts.append(f"L5: {int(round(_l5 * 5))}/5 ({int(_l5 * 100)}%)")
                                    if _l10 is not None:
                                        _hr_parts.append(f"L10: {int(round(_l10 * 10))}/10 ({int(_l10 * 100)}%)")
                                    if _l15 is not None:
                                        _hr_parts.append(f"L15: {int(round(_l15 * 15))}/15 ({int(_l15 * 100)}%)")
                                    if _l20 is not None:
                                        _hr_parts.append(f"L20: {int(round(_l20 * 20))}/20 ({int(_l20 * 100)}%)")
                                    if _hr_parts:
                                        note_elements.append(" | ".join(_hr_parts))
                                    # vs-scheme L5: how this player performs against TODAY's opponent
                                    # defense type (e.g. PAINT_PACK, BLITZ). From Module B vs_scheme_cache
                                    # which uses team_scheme_cache.active_style — live DB data, not hardcoded.
                                    _vs_scheme = _hr_entry.get('vs_scheme')
                                    _vs_l5 = _hr_entry.get(f'{_dir}_vs_scheme_l5')
                                    _vs_n = _hr_entry.get('vs_scheme_sample', 0)
                                    if _vs_scheme and _vs_l5 is not None and _vs_n:
                                        _vs_hits = int(round(_vs_l5 * _vs_n))
                                        note_elements.append(
                                            f"vs {_vs_scheme} L{_vs_n}: {_vs_hits}/{_vs_n} ({int(_vs_l5 * 100)}%)"
                                        )

                            # BUG B2: Trend context (HOT/COLD only, not STABLE)
                            trend_label = p.get('trend_label')
                            trend_delta = p.get('trend_delta')
                            if trend_label and trend_delta and trend_label not in ('STABLE', 'NEUTRAL'):
                                note_elements.append(f"Trend: {trend_label} ({trend_delta:+.1f} vs season)")

                            # Sprint 4 — Alt line sweep
                            # Module A Phase 2B wrote alt_props[stat_key][player_name][alt_line]
                            # Read: game → stat_key → player name → dict of {line: {odds}}
                            _alt_lines = (
                                game.get('alt_props', {})
                                .get(stat_key, {})
                                .get(p['name'], {})
                            )
                            if _alt_lines:
                                _best_alt_note = None
                                _best_alt_ev = ev  # Only surface if strictly better than main EV
                                for _alt_line, _alt_data in _alt_lines.items():
                                    _alt_odds = (
                                        _alt_data.get('odds_over') if bet_direction == 'over'
                                        else _alt_data.get('odds_under')
                                    )
                                    _alt_book = (
                                        _alt_data.get('book_over') if bet_direction == 'over'
                                        else _alt_data.get('book_under')
                                    )
                                    if not _alt_odds:
                                        continue
                                    _alt_dec = (
                                        1 + (_alt_odds / 100) if _alt_odds > 0
                                        else 1 + (100 / abs(_alt_odds))
                                    )
                                    _alt_ev = round((win_prob * _alt_dec - 1) * 100, 2)
                                    if _alt_ev > _best_alt_ev:
                                        _best_alt_ev = _alt_ev
                                        _sign = '+' if _alt_odds > 0 else ''
                                        _best_alt_note = (
                                            f"Alt: {bet_direction.upper()} {_alt_line} "
                                            f"@ {_sign}{_alt_odds} ({_alt_book})"
                                        )
                                if _best_alt_note:
                                    note_elements.append(_best_alt_note)

                            # --- TAG CLASSIFICATION (V4.6 - Week 2, Days 3-4) ---
                            tags_formatted = "[]"  # Default empty tags
                            if self.tag_classifier:
                                try:
                                    # Build game context for classifier
                                    game_ctx = {
                                        'opponent': p.get('opponent', game.get('opponent', '')),
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
                                        'opponent': p.get('opponent', game.get('opponent', '')),
                                        'archetype': _sanitize_archetype(p.get('archetype', '')),
                                        'status': p.get('status', 'Active'),
                                        'scenario': p.get('scenario', 'BASE'),
                                        'stat_category': _normalize_stat_category(stat_key),
                                        'bet_side': bet_direction.upper(),
                                        'line': line,
                                        'odds_over': odds_over,
                                        'odds_under': odds_under,
                                        'projection': round(final_proj, 2),
                                        'fair_prob': round(fair_prob, 4),
                                        'model_prob': round(model_prob, 4),
                                        'true_edge': edge,
                                        'ev': ev_raw,   # Store raw EV in DB (not capped)
                                        'units': units,
                                        'confidence_tier': confidence_tier,
                                        'confirmation_score': round(confirmation_score, 3),  # C1
                                        'sharp_odds_over_at_bet': sharp_odds_over_at_bet,
                                        'sharp_odds_under_at_bet': sharp_odds_under_at_bet,
                                        'sharp_book_at_bet': sharp_book_at_bet,
                                        'sharp_consensus': round(sharp_consensus, 3),
                                        'note': " | ".join(note_elements),
                                        'tags': tags_formatted,  # Week 2, Days 3-4: Tag classification
                                        'edge_type': _classify_edge_type(  # Phase 8.24: Edge driver label
                                            p.get('scenario', 'BASE'),
                                            note_elements,
                                            tags_formatted,
                                            p.get('games_since_return'),
                                            p.get('name')  # B3: fallback player_name for DB lookup
                                        ),
                                        'referee_impact': ref_pace,
                                        'blowout_modifier': round(blowout_mult, 3),
                                        'run_type': 'production',
                                        'source_quality': source_quality,
                                        'vendor_count': vendor_count,
                                        'bookmaker': book_over if bet_direction == 'over' else book_under,  # Line Shopping V2.0
                                        'time_context': _run_time_context,  # EARLY_LOOK/AFTERNOON/PRE_GAME/LOCK_TIME
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
                                "edge": edge,  # True devigged edge percentage
                                "ev": ev,      # Expected value for sorting
                                "units": units,
                                "note": " | ".join(note_elements),
                                "tags": tags_formatted,  # Week 2, Days 3-4: Tag classification
                                "game_id": game.get('game_id', ''),
                                "home_team": game.get('home_team', ''),
                                "away_team": game.get('away_team', ''),
                                "spread": game.get('spread', 0),
                                "total": game.get('total', 0),
                                "team_total_home": game.get('team_total_home'),
                                "team_total_away": game.get('team_total_away'),
                                "confidence_tier": confidence_tier,
                                "archetype": _sanitize_archetype(p.get('archetype', '')),
                                "opponent": game.get('opponent', ''),
                                "book_over": book_over,
                                "book_under": book_under,
                                "odds_over": odds_over,
                                "odds_under": odds_under,
                                "source_quality": source_quality,
                                "vendor_count": vendor_count,
                                "scenario": p.get('scenario', 'BASE'),
                                "sharp_odds_over_at_bet": sharp_odds_over_at_bet,
                                "sharp_odds_under_at_bet": sharp_odds_under_at_bet,
                                "sharp_book_at_bet": sharp_book_at_bet,
                                "sharp_consensus": round(sharp_consensus, 3),
                            })

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
                if p['edge'] > unique_props[key]['edge']:
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
                    'avg_edge': sum(p.get('edge', 0) for p in all_props) / len(all_props) if all_props else 0,
                    'avg_ev': sum(p.get('ev', 0) for p in all_props) / len(all_props) if all_props else 0,
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
        
        return self.create_daily_briefing(all_props, title=title), image_path, all_props

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
        COMBOS = {
            'pra': ('proj_pts', 'proj_reb', 'proj_ast'),
            'pa': ('proj_pts', 'proj_ast'),
            'pr': ('proj_pts', 'proj_reb'),
            'ra': ('proj_reb', 'proj_ast'),
        }
        k = key.lower()
        if k in COMBOS:
            return sum(p.get(c, 0) for c in COMBOS[k])
        m = {
            'pts': 'proj_pts', 'reb': 'proj_reb', 'ast': 'proj_ast',
            '3pm': 'proj_3pm', 'oreb': 'proj_oreb', 'dreb': 'proj_dreb',
            'stl': 'proj_stl', 'blk': 'proj_blk', 'tov': 'proj_tov'
        }
        return p.get(m.get(k, ''), 0)

    # C1: stat_key → SQL expression mapping for player_game_logs hit rate queries
    _STAT_COL_MAP = {
        'points': 'pts', 'rebounds': 'reb', 'assists': 'ast',
        'steals': 'stl', 'blocks': 'blk', 'turnovers': 'tov',
        'threes': 'fg3m', 'pts': 'pts', 'reb': 'reb', 'ast': 'ast',
        'stl': 'stl', 'blk': 'blk', 'tov': 'tov', '3pm': 'fg3m', 'fg3m': 'fg3m',
        'pra': 'pts + reb + ast', 'pa': 'pts + ast',
        'pr': 'pts + reb', 'ra': 'reb + ast',
        'fg': 'fgm', 'fga': 'fga', 'fta': 'fta', 'ftm': 'ftm',
        'oreb': 'oreb', 'dreb': 'dreb', 'pf': 'pf',
    }

    def _get_hit_rates_vs_line(self, player_name: str, stat_key: str, line: float, direction: str):
        """Calculate L5 and L10 historical hit rates vs a specific line.

        C1: Used to build confirmation_score for tier promotion/demotion.
        Opens its own DB connection — called at most ~80 times per pipeline run.
        Results cached in self._hit_rate_cache to avoid duplicate queries.

        Returns:
            (l5_hit_rate, l10_hit_rate) — floats 0.0-1.0.
            Returns (0.5, 0.5) on any error (neutral — no modifier applied).
        """
        cache_key = (player_name, stat_key, line, direction)
        if cache_key in self._hit_rate_cache:
            return self._hit_rate_cache[cache_key]

        stat_expr = self._STAT_COL_MAP.get(stat_key.lower())
        if not stat_expr:
            self._hit_rate_cache[cache_key] = (0.5, 0.5)
            return (0.5, 0.5)

        try:
            import sqlite3
            conn = sqlite3.connect(config.DB_PATH)
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT {stat_expr} AS stat_val
                FROM player_game_logs
                WHERE player_name = ? AND minutes > 0
                ORDER BY game_date DESC
                LIMIT 10
            """, (player_name,))
            rows = [r[0] for r in cursor.fetchall() if r[0] is not None]
            conn.close()
        except Exception as e:
            print(f"⚠️  Hit rate query failed for {player_name}/{stat_key}: {e}")
            self._hit_rate_cache[cache_key] = (0.5, 0.5)
            return (0.5, 0.5)

        MIN_SAMPLE = 3
        if len(rows) < MIN_SAMPLE:
            self._hit_rate_cache[cache_key] = (0.5, 0.5)
            return (0.5, 0.5)

        def _hit(val):
            return (val > line) if direction == 'over' else (val <= line)

        l10_hits = sum(1 for v in rows if _hit(v))
        l10_hr = l10_hits / len(rows)
        l5_rows = rows[:5]
        if len(l5_rows) < MIN_SAMPLE:
            l5_hr = l10_hr
        else:
            l5_hr = sum(1 for v in l5_rows if _hit(v)) / len(l5_rows)

        result = (round(l5_hr, 3), round(l10_hr, 3))
        self._hit_rate_cache[cache_key] = result
        return result

    def _sharp_consensus(self, nc_odds, sharp_odds, bet_direction):
        if not nc_odds or not sharp_odds: return 0.50
        nc_dec    = 1 + 100/abs(nc_odds)    if nc_odds > 0 else 1 + abs(nc_odds)/100
        sharp_dec = 1 + 100/abs(sharp_odds) if sharp_odds > 0 else 1 + abs(sharp_odds)/100
        delta = sharp_dec - nc_dec
        if   delta >= 0.10: return 0.90
        elif delta >= 0.05: return 0.75
        elif delta >= 0.00: return 0.60
        elif delta >= -0.05: return 0.40
        elif delta >= -0.10: return 0.25
        else:                return 0.10

    def _historical_clv_signal(self, stat_key, direction, player_name):
        try:
            import sqlite3 as _sqlite3
            conn = _sqlite3.connect(config.DB_PATH)
            conn.row_factory = _sqlite3.Row
            stat_sql = '''
                SELECT AVG(clv_cents) as avg_clv, COUNT(*) as n
                FROM bet_recommendations
                WHERE stat_category = ? AND bet_side = ?
                  AND clv_cents IS NOT NULL
                  AND closing_book IN ('pinnacle','novig','prophetx')
                  AND outcome IN ('WIN','LOSS')
            '''
            player_sql = stat_sql + " AND player_name = ?"
            stat_row   = conn.execute(stat_sql, [stat_key, direction]).fetchone()
            player_row = conn.execute(player_sql, [stat_key, direction, player_name]).fetchone()
            conn.close()
            stat_clv   = stat_row['avg_clv']   if stat_row   and stat_row['n']   >= 50 else None
            player_clv = player_row['avg_clv'] if player_row and player_row['n'] >= 10 else None
            if   player_clv is not None and stat_clv is not None:
                avg_clv = 0.60 * player_clv + 0.40 * stat_clv
            elif player_clv is not None:
                avg_clv = player_clv
            elif stat_clv is not None:
                avg_clv = stat_clv
            else:
                return 0.50
            return max(0.0, min(1.0, 0.50 + (avg_clv / 16.0)))
        except Exception:
            return 0.50

    def _calculate_confidence_tier(self, edge, archetype='', stat_key='', bet_direction='',
                                   model_prob=0.5, player_name='', line=0.0,
                                   hit_rates_by_market=None,
                                   streak_score=0.5, matchup_modifier=0.0, dvp_rank=None,
                                   odds_over=-110, odds_under=-110,
                                   sharp_odds_over=None, sharp_odds_under=None,
                                   wowy_confidence=None, crew_bias=None):
        """
        Composite confidence tier using edge + historical performance signals.

        Factors:
        1. True edge % (primary — determines base tier)
        2. Stat-direction performance (±1 tier for "gold combos")
        3. Hit rate confirmation modifier (from Module B pre-computed data or DB fallback)

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

        # --- Archetype modifier (re-enabled after Phase 7.9 overhaul) ---
        positive_archetypes = {
            'HELIOCENTRIC_MAESTRO', 'SLASHING_CREATOR',
            'SNIPER_ELITE', 'WARRIOR_BIG'
        }
        # Phase 7.9.5: Removed GENERALIST and WEAK_LINK penalties
        # GENERALIST = neutral (no strong playtype signal, but not a bad bet)
        # WEAK_LINK = moved to defensive_tag column (not a primary archetype)
        # negative_archetypes = set()  # Reserved for future negative modifiers
        if archetype in positive_archetypes:
            tier_score += 1

        # --- Stat-direction modifier (gold combos from backtest) ---
        GOLD_COMBOS = {
            'BLK_UNDER':  1,    # +1 tier — A+ structural edge (70.7% WR)
            'TOV_UNDER':  1,    # +1 tier — B solid (72.2% WR)
            '3PM_UNDER':  1,    # +1 tier — B reliable (61.4% WR)
            'STL_UNDER':  0,    # Demote to 0 — C grade (54.8% WR), better handled by calibration
        }
        STAT_SHORT = {'steals': 'stl', 'blocks': 'blk', 'turnovers': 'tov', 'defensive_rebounds': 'dreb', 'threes': '3pm'}
        norm_key = STAT_SHORT.get(stat_key.lower(), stat_key.lower())
        stat_dir = f"{norm_key}_{bet_direction}".upper()
        tier_score += GOLD_COMBOS.get(stat_dir, 0)

        # --- PART 2: Prop Confidence Score (8 signals) ---
        prop_confidence_score = 0.5  # Neutral default if no player/line data provided
        
        # 1. hit_rate_signal (0.20)
        hit_rate_signal = 0.5
        if player_name and line > 0:
            l5_hr, l10_hr = 0.5, 0.5
            stat_key_norm = stat_key.lower()
            hr = (hit_rates_by_market or {}).get(stat_key_norm)
            if hr:
                direction_key = f'{bet_direction}_l5'
                l5_hr = hr.get(direction_key, 0.5)
                l10_hr = hr.get(direction_key.replace('_l5', '_l10'), 0.5)
            else:
                l5_hr, l10_hr = self._get_hit_rates_vs_line(player_name, stat_key, line, bet_direction)
            hit_rate_signal = 0.60 * l5_hr + 0.40 * l10_hr

        # 2. streak_signal (0.20)
        streak_sig_val = 0.50
        if streak_score >= 0.7: streak_sig_val = 1.0
        elif streak_score >= 0.5: streak_sig_val = 0.65
        elif streak_score >= 0.3: streak_sig_val = 0.50
        elif streak_score >= 0.1: streak_sig_val = 0.35
        else: streak_sig_val = 0.20
        
        # 3. matchup_signal (0.15)
        matchup_score_val = max(0.0, min(1.0, 0.50 + (matchup_modifier / 60.0)))
        dvp_score_val = (30 - dvp_rank) / 29.0 if dvp_rank is not None else 0.5
        matchup_sig = 0.60 * matchup_score_val + 0.40 * dvp_score_val if dvp_rank is not None else matchup_score_val
        
        # 4. sharp_consensus_signal (0.15)
        bet_odds = sharp_odds_over if bet_direction == 'over' else sharp_odds_under
        actual_odds = odds_over if bet_direction == 'over' else odds_under
        sharp_consensus_sig = self._sharp_consensus(actual_odds, bet_odds, bet_direction)

        # 5. clv_track_record (0.15)
        clv_sig = self._historical_clv_signal(stat_key.lower(), bet_direction.upper(), player_name)
        
        # 6. model_signal (0.10)
        model_sig = model_prob
        
        # 7. wowy_signal (0.05)
        wowy_sig = 0.50
        if wowy_confidence == 'high': wowy_sig = 0.85
        elif wowy_confidence == 'medium': wowy_sig = 0.60
        elif wowy_confidence == 'low': wowy_sig = 0.40
        
        # 8. referee_signal (0.05)
        ref_sig = 0.50
        if crew_bias == 'PROTECTOR': ref_sig = 0.80
        elif crew_bias == 'STAR_KILLER': ref_sig = 0.20
        
        prop_confidence_score = (
            0.20 * hit_rate_signal
          + 0.20 * streak_sig_val
          + 0.15 * matchup_sig
          + 0.15 * sharp_consensus_sig
          + 0.15 * clv_sig
          + 0.10 * model_sig
          + 0.05 * wowy_sig
          + 0.05 * ref_sig
        )

        if prop_confidence_score >= 0.65:      # Same signal required for promotion (V5.5)
            tier_score += 1
        elif prop_confidence_score <= 0.45:    # Demote more mid-range bets (was 0.38)
            tier_score -= 1

        # Clamp to valid range [0, 3]
        tier_score = max(0, min(3, tier_score))

        # Minimum edge floors — bonuses cannot promote a bet above its edge ceiling.
        # Prevents composite bonus abuse (e.g. 7% edge BLK_UNDER for RIM_GUARDIAN
        # getting double-bumped to DIAMOND). Gold combos are high-WR signals but
        # only meaningful when the underlying edge is also real.
        if tier_score == 3 and edge < 15.0:   # DIAMOND floor: must have ≥15% edge
            tier_score = 2
        elif tier_score == 2 and edge < 10.0:  # BLUE CHIP floor: must have ≥10% edge
            tier_score = 1

        TIER_NAMES = ['THE STEAL', 'CORE ASSET', 'BLUE CHIP', 'DIAMOND']
        return TIER_NAMES[tier_score], prop_confidence_score  # C1: tuple (tier_name, confirmation_score)

    @staticmethod
    def _load_stat_confidence_cache() -> dict:
        """Load cache/stat_confidence.json built nightly by build_stat_confidence.py.

        Returns dict keyed by '{STAT}_{SIDE}' (e.g. 'BLOCKS_UNDER').
        Returns {} on any error — hardcoded constants will be used as fallback.
        """
        import os, json as _json
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache', 'stat_confidence.json')
        try:
            with open(cache_path) as f:
                return _json.load(f)
        except Exception:
            return {}

    def _apply_stat_calibration(self, edge: float, stat_key: str, bet_direction: str) -> float:
        """V5.3: Apply stat-specific edge calibration — live cache when data is sufficient,
        hardcoded fallback otherwise.

        LIVE (sample_n >= 200): derives multiplier from calibration_gap in stat_confidence.json.
          factor = clamp(1.0 + calibration_gap / 150, 0.65, 1.40)
          Dampening of 150 means a +23.6 gap (BLOCKS UNDER) → 1.157x boost.
          A -19.8 gap (PTS OVER) → 0.868x deflation.
          As sample grows each night, factors self-correct without code changes.

        FALLBACK (thin sample): uses _STAT_EDGE_CALIBRATION hardcoded dict —
          our manually-tuned starting estimates.

        See: best-practices/data/STAT_CONFIDENCE_FRAMEWORK.md
        """
        cache_key = f"{stat_key.upper()}_{bet_direction.upper()}"
        entry = self._stat_conf.get(cache_key, {})

        if entry.get('sample_n', 0) >= 200 and entry.get('calibration_gap') is not None:
            # Live: derive factor from this season's actual calibration gap
            gap = entry['calibration_gap']
            factor = max(0.65, min(1.40, 1.0 + gap / 150.0))
            return round(edge * factor, 1)

        # Fallback: hardcoded initial estimates
        norm = stat_key.lower()
        factors = _STAT_EDGE_CALIBRATION.get(norm, {})
        multiplier = factors.get(bet_direction.lower(), 1.0)
        return round(edge * multiplier, 1)

    def _rmse_sizing_modifier(self, stat_key: str) -> float:
        """V5.3: RMSE-based unit sizing modifier — live cache when available, hardcoded fallback.

        LIVE (sample_n >= 50): uses RMSE from DB projection vs line analysis in cache.
        FALLBACK: uses _STAT_RMSE hardcoded dict.

        RMSE ≤ 1.0: no penalty. 1.0–2.0: 5% cut. >4.0: 15% cut.
        BLOCKS/STEALS/3PM are precise projections → full sizing.
        PTS/PRA projections have 5x more absolute error → reduce sizing.
        """
        # Try cache (either side has the RMSE value — it's stat-level, not side-level)
        for side in ('UNDER', 'OVER'):
            entry = self._stat_conf.get(f"{stat_key.upper()}_{side}", {})
            if entry.get('rmse') is not None and entry.get('sample_n', 0) >= 50:
                rmse = entry['rmse']
                break
        else:
            # Fallback to hardcoded
            rmse = _STAT_RMSE.get(stat_key.lower(), 2.0)

        if rmse <= 1.0:   return 1.00
        elif rmse <= 2.0: return 0.95
        elif rmse <= 4.0: return 0.90
        else:             return 0.85   # PTS, PA, PR, PRA — high uncertainty

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
        # NOTE: These are static fallback values. Live calibration should come from
        #       Module C's Monte Carlo sim_hit_rates (actual distribution), not this heuristic.
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
            'pa': 9.2,     # Pts+Ast combo
            'pr': 9.5,     # Pts+Reb combo
            'ra': 5.3,     # Reb+Ast combo
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

    # --- S.A.V.A.G.E. Card Formatting Helpers ---
    # Promoted from nested functions for reuse by format_bet_card(), Phase 8.13 bot, Ludi Lens.

    @staticmethod
    def _tier_icon(tier: str) -> str:
        return {
            'DIAMOND': '💎', 'BLUE CHIP': '🔷',
            'CORE ASSET': '🔹', 'THE STEAL': '⭐',
        }.get(tier, '⭐')

    @staticmethod
    def _format_units(units) -> str:
        try:
            u = float(units)
            return f"{u:.1f}" if u.is_integer() else f"{u:.2f}".rstrip('0').rstrip('.')
        except (TypeError, ValueError):
            return str(units)

    @staticmethod
    def _format_edge(edge) -> str:
        try:
            e = float(edge)
            edge_str = f"{e:+.1f}".rstrip('0').rstrip('.')
            return f"{edge_str}%"
        except (TypeError, ValueError):
            return f"{edge}%"

    @staticmethod
    def _format_proj(proj) -> str:
        try:
            p = float(proj)
            return f"{p:.2f}".rstrip('0').rstrip('.')
        except (TypeError, ValueError):
            return str(proj)

    @staticmethod
    def _format_odds(odds) -> str:
        try:
            o = float(odds)
            if o > 0:
                return f"+{int(o)}" if o.is_integer() else f"+{o:g}"
            return f"{int(o)}" if o.is_integer() else f"{o:g}"
        except (TypeError, ValueError):
            return ""

    def _parse_tags(self, tags_str: str) -> list:
        if not tags_str:
            return []
        if self.tag_classifier:
            try:
                return self.tag_classifier.parse_tags_from_db(tags_str)
            except Exception:
                pass
        try:
            return json.loads(tags_str)
        except (json.JSONDecodeError, TypeError):
            return []

    @staticmethod
    def _extract_scheme(tags_list: list, note_str: str) -> str:
        for tag in tags_list:
            if isinstance(tag, str) and tag.startswith('vs_'):
                return tag.replace('vs_', '').replace('_', ' ')
        for token in ['PERIMETER', 'PAINT_PACK', 'FUNNEL', 'BLITZ', 'NEUTRAL']:
            if token.lower() in (note_str or '').lower():
                return token.replace('_', ' ')
        return "STANDARD"

    @staticmethod
    def _extract_key_signals(note_str: str) -> list:
        if not note_str:
            return []
        parts = [p.strip() for p in note_str.split('|') if p.strip()]
        skip_phrases = [
            "low rim pressure", "low corner volume",
            "low rim frequency", "low corner 3", "low corner 3s",
        ]
        skip_flags = ["DATA QUALITY", "VERIFY LINE", "EXCEPTIONAL"]
        signals = []
        seen = set()
        for part in parts:
            cleaned = re.sub(r"^[^A-Za-z0-9\[]+\s*", "", part).strip()
            cleaned = re.sub(r"\s*\[[^\]]+\]\s*", "", cleaned).strip()
            if not cleaned:
                continue
            lower = cleaned.lower()
            if any(phrase in lower for phrase in skip_phrases):
                continue
            if any(flag in cleaned for flag in skip_flags):
                continue
            if "bdl" in lower or "consensus" in lower or re.search(r"\bbk\b", lower):
                continue
            if re.fullmatch(r"[A-Z0-9_\-]+", cleaned):
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            signals.append(cleaned)
            if len(signals) >= 2:
                break
        return signals

    @staticmethod
    def _scenario_tag(tags_list: list, scenario: str):
        for tag in tags_list:
            if not isinstance(tag, str):
                continue
            if tag == "NEW_TO_TEAM" or tag.startswith("BENEFICIARY"):
                return tag
        if "NEW_TO_TEAM" in (scenario or ""):
            return "NEW_TO_TEAM"
        if "WITHOUT" in (scenario or ""):
            return "BENEFICIARY"
        return None

    def format_bet_card(self, bet: dict) -> str:
        """Format a single bet as a S.A.V.A.G.E. structured card.

        Reusable by: create_daily_briefing(), Phase 8.13 bot, Ludi Lens.
        """
        tier_icon = self._tier_icon(bet.get('confidence_tier', 'THE STEAL'))
        player_name = (bet.get('name') or '').upper()
        bet_on = (bet.get('bet_on') or '').upper()
        stat = (bet.get('stat') or '').upper()
        line = bet.get('line', '')
        matchup = bet.get('matchup', '')

        card = f"   {tier_icon} {player_name} — {bet_on} {line} {stat}\n"
        card += (
            f"   📊 {matchup}  |  Proj: {self._format_proj(bet.get('proj'))}  |  "
            f"Edge: {self._format_edge(bet.get('edge'))}  |  {self._format_units(bet.get('units'))}u\n"
        )

        bet_book = bet.get('book_under') if bet_on == 'UNDER' else bet.get('book_over')
        bet_odds = bet.get('odds_under') if bet_on == 'UNDER' else bet.get('odds_over')
        book_label = bet_book if bet_book and bet_book != 'consensus' else "Consensus"
        odds_label = self._format_odds(bet_odds)
        price_str = f"{book_label} {odds_label}".strip()

        consensus_tag = ""
        source_quality = bet.get('source_quality', '')
        vendor_count = bet.get('vendor_count', 0)
        if source_quality == 'BDL_FALLBACK':
            consensus_tag = f"[BDL:{vendor_count}bk]" if vendor_count else "[BDL]"
        elif source_quality == 'ODDS_API' and vendor_count >= 4:
            consensus_tag = f"[{vendor_count}bk consensus]"
        elif source_quality == 'ODDS_API' and vendor_count > 0:
            consensus_tag = f"[{vendor_count}bk]"

        line3 = f"   💰 Best Bet: {price_str}".rstrip()
        if consensus_tag:
            line3 += f"  |  {consensus_tag}"
        card += f"{line3}\n"

        tags_list = self._parse_tags(bet.get('tags', ''))
        archetype = (bet.get('archetype') or 'GENERALIST').upper()
        scheme = self._extract_scheme(tags_list, bet.get('note', '')).upper()
        card += f"   🎯 Archetype: {archetype} vs {scheme} defense\n"

        key_signals = self._extract_key_signals(bet.get('note', ''))
        if key_signals:
            card += f"   📝 Key Signal: {', '.join(key_signals)}\n"
        else:
            card += "   📝 Key Signal: None\n"

        scenario_tag = self._scenario_tag(tags_list, bet.get('scenario', ''))
        if scenario_tag:
            card += f"   ⚡ SCENARIO: {scenario_tag}\n"

        edge_type = bet.get('edge_type', 'Projection')
        edge_type_emoji = {
            'Projection': '📊',
            'Matchup': '🎯',
            'Injury-Vacuum': '🚀',
            'Injury-Return': '🩹',
            'Hot-Streak': '🔥',
        }.get(edge_type, '📊')
        card += f"   {edge_type_emoji} EDGE: {edge_type}\n"

        return card

    def create_daily_briefing(self, props, title="LUDI GAME BRIEF"):
        """Formats the final briefing output for bot and console display."""
        report = f"\n📰 {title} ({format_est_date('%b %d, %Y')})\n"
        report += "================================\n"

        # BDL Fallback notice — set by Gatekeeper when Odds-API quota is exhausted.
        if getattr(self, '_bdl_fallback_active', False):
            report += "⚠️  ODDS SOURCE: BDL Fallback (Odds-API quota exhausted)\n"
            report += "   Lines estimated — verify at your book before betting.\n"
            report += "   Full accuracy resumes March 1.\n"
            report += "================================\n"

        # 1. Group by Game
        grouped = {}
        for p in props:
            matchup = p.get('matchup', 'Unknown')
            if matchup not in grouped: grouped[matchup] = []
            grouped[matchup].append(p)

        report += f"💎 TOP TARGETS BY GAME\n"

        for matchup in sorted(grouped.keys()):
            plays = grouped[matchup]
            plays.sort(key=lambda x: x['ev'], reverse=True)
            top_plays = plays[:3]
            if not top_plays: continue

            report += f"\n🏀 {matchup}\n"
            for bet in top_plays:
                report += self.format_bet_card(bet)

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
                "archetype": "SLASHING_CREATOR"
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

    briefing, _, _ = rep.generate_report(test_data)
    print(briefing)

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
    briefing, _, _ = rep.generate_report(legacy_test)
    print(briefing)
