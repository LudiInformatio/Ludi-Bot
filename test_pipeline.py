#!/usr/bin/env python
"""
test_pipeline.py - Full End-to-End Integration Test
Week 1, Day 7 - Final Validation

Tests complete pipeline: Module A → C → F with real API calls
Target: 3 games (LAC-NYK, LAL-SAS, HOU-POR)
Budget: $0.15 maximum (~100 credits)
Output: daily_briefing.txt with betting recommendations
"""

import json
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional

# Core modules
from module_a import Gatekeeper
from module_c import LudiOracle
from module_f import LudiReporter

# Utilities
from utils.api_monitor import get_monitor

# Constants
DB_PATH = "/home/mnprice86/ludi_bot/ludi.db"
MAX_BUDGET = 0.15  # $0.15
CREDITS_PER_DOLLAR = 20000 / 30.0  # 666.67 credits per dollar
MAX_CREDITS = int(MAX_BUDGET * CREDITS_PER_DOLLAR)  # ~100 credits


# ============================================================================
# DATABASE HELPER FUNCTIONS
# ============================================================================

def get_active_roster(team_abbr: str, limit: int = 5) -> List[Dict]:
    """
    Query database for top N players by minutes played in last 20 days.
    Returns list of player dicts with season averages.

    SQL Strategy:
    1. Filter by team and recent games (20 days lookback)
    2. Group by player_id to aggregate stats
    3. Order by average minutes (identifies starters/rotation)
    4. Limit to top 5 to control API costs
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = '''
        SELECT
            player_id,
            player_name,
            team_abbreviation,
            AVG(pts) as avg_pts,
            AVG(reb) as avg_reb,
            AVG(ast) as avg_ast,
            AVG(fga) as avg_fga,
            AVG(fg3a) as avg_fg3a,
            AVG(fta) as avg_fta,
            AVG(oreb) as avg_oreb,
            AVG(dreb) as avg_dreb,
            AVG(stl) as avg_stl,
            AVG(blk) as avg_blk,
            AVG(tov) as avg_tov,
            AVG(minutes) as avg_min,
            AVG(fg_pct) as fg_pct,
            AVG(fg3_pct) as fg3_pct,
            AVG(ft_pct) as ft_pct,
            COUNT(*) as games_played
        FROM player_game_logs
        WHERE team_abbreviation = ?
        AND game_date >= date('now', '-20 days')
        GROUP BY player_id, player_name, team_abbreviation
        HAVING COUNT(*) >= 3
        ORDER BY AVG(minutes) DESC
        LIMIT ?
    '''

    cursor.execute(query, (team_abbr, limit))
    rows = cursor.fetchall()
    conn.close()

    roster = []
    for row in rows:
        roster.append({
            'player_id': row[0],
            'PLAYER_NAME': row[1],
            'TEAM_ABBREVIATION': row[2],
            'PTS': round(row[3], 1) if row[3] else 0,
            'REB': round(row[4], 1) if row[4] else 0,
            'AST': round(row[5], 1) if row[5] else 0,
            'FGA': round(row[6], 1) if row[6] else 0,
            'FG3A': round(row[7], 1) if row[7] else 0,
            'FTA': round(row[8], 1) if row[8] else 0,
            'OREB': round(row[9], 1) if row[9] else 0,
            'DREB': round(row[10], 1) if row[10] else 0,
            'STL': round(row[11], 1) if row[11] else 0,
            'BLK': round(row[12], 1) if row[12] else 0,
            'TOV': round(row[13], 1) if row[13] else 0,
            'MIN': round(row[14], 1) if row[14] else 0,
            'FG_PCT': round(row[15], 3) if row[15] else 0.450,
            'FG3_PCT': round(row[16], 3) if row[16] else 0.350,
            'FT_PCT': round(row[17], 3) if row[17] else 0.750,
            'games_played': row[18]
        })

    return roster


# ============================================================================
# PROPS & MATCHING FUNCTIONS
# ============================================================================

def fetch_props_for_game(gate: Gatekeeper, game_id: str) -> Dict[str, Dict]:
    """
    Extract player props from Gatekeeper.games[game_id]['props'].

    Returns dict mapping player_name to prop lines:
    {
        "LeBron James": {
            "points": 24.5,
            "rebounds": 7.5,
            "assists": 7.5,
            "threes": 2.5
        }
    }
    """
    if game_id not in gate.games:
        return {}

    game_data = gate.games[game_id]
    props = game_data.get('props', {})

    return props


def match_props_to_roster(props_data: Dict, roster: List[Dict]) -> List[Dict]:
    """
    Match sportsbook props to roster players by name.

    Challenge: Props use full names, roster uses player_name from DB.
    Solution: Direct string match (data is clean).

    Returns roster list with 'sportsbook_props' added for matched players.
    Only returns players with props (saves simulation credits).
    """
    matched_roster = []

    for player in roster:
        player_name = player['PLAYER_NAME']

        if player_name in props_data:
            # Found props for this player
            player_copy = player.copy()
            player_copy['sportsbook_props'] = props_data[player_name]
            matched_roster.append(player_copy)

    return matched_roster


# ============================================================================
# SIMULATION SCENARIO BUILDER
# ============================================================================

def build_simulation_scenario(
    game_data: Dict,
    home_roster: List[Dict],
    away_roster: List[Dict],
    gate: Gatekeeper
) -> Dict:
    """
    Build Module C input scenario from game data and rosters.

    Module C expects:
    {
        'scenario_name': 'LAC_NYK',
        'ref_impact': 1.05,
        'pace_factor': 1.0,
        'def_factor': 1.0,
        'days_rest': 1,
        'players': [
            {
                'PLAYER_NAME': 'LeBron James',
                'TEAM_ABBREVIATION': 'LAL',
                'MIN': 35.0,
                'FGA': 20.0,
                'FG_PCT': 0.515,
                ...
            }
        ]
    }
    """
    matchup = game_data.get('matchup', 'UNKNOWN')
    ref_impact = game_data.get('archetypes', {}).get('ref_impact', 1.0)

    # Combine rosters
    all_players = home_roster + away_roster

    # Create scenario name from matchup
    scenario_name = matchup.replace(' @ ', '_vs_').replace(' ', '_')

    scenario = {
        'scenario_name': scenario_name,
        'ref_impact': ref_impact,
        'pace_factor': 1.0,  # Default pace (Module E would adjust)
        'def_factor': 1.0,   # Default defense rating
        'days_rest': 1,      # Assume 1 day rest (typical)
        'players': all_players
    }

    return scenario


# ============================================================================
# REPORTER INPUT BUILDER
# ============================================================================

def build_reporter_input(
    sim_results: List[Dict],
    game_data: Dict,
    props_data: Dict
) -> List[Dict]:
    """
    Transform Module C output + props into Module F input format.

    Module F expects:
    [
        {
            'game_id': 'LAC_NYK',
            'spread': 5.5,
            'ref_impact': 1.05,
            'players': [
                {
                    'name': 'LeBron James',
                    'team': 'LAL',
                    'proj_pts': 25.3,
                    'proj_reb': 7.8,
                    'proj_ast': 7.2,
                    'proj_3pm': 2.1,
                    'proj_min': 35.0,
                    'status': 'Active',
                    'scenario': 'BASE',
                    'sportsbook_props': {
                        'pts': {'line': 24.5, 'odds_over': -110, 'odds_under': -110},
                        'reb': {'line': 7.5, 'odds_over': -115, 'odds_under': -105}
                    }
                }
            ]
        }
    ]
    """
    # Map Module C stat keys to Module F projection keys
    STAT_MAPPING = {
        'PTS': 'proj_pts',
        'REB': 'proj_reb',
        'AST': 'proj_ast',
        'FG3M': 'proj_3pm',
        'OREB': 'proj_oreb',
        'MIN': 'proj_min'
    }

    # Build player list for reporter
    players = []
    for sim in sim_results:
        player_name = sim.get('PLAYER_NAME')
        team = sim.get('TEAM')

        # Map simulation output to reporter input
        player_dict = {
            'name': player_name,
            'team': team,
            'status': 'Active',  # Default (Module D would override)
            'scenario': sim.get('SCENARIO', 'BASE')
        }

        # Map stats
        for c_key, f_key in STAT_MAPPING.items():
            player_dict[f_key] = sim.get(c_key, 0)

        # Add props if available
        if player_name in props_data:
            # Convert simple line format to odds format
            props_formatted = {}
            for stat_key, line_value in props_data[player_name].items():
                # Skip props with N/A or invalid lines
                if line_value == 'N/A' or line_value is None:
                    continue

                # Convert line to float if it's a string number
                try:
                    line_float = float(line_value)
                except (ValueError, TypeError):
                    continue

                # Map prop keys: 'points' → 'pts', 'rebounds' → 'reb', etc.
                mapped_key = {
                    'points': 'pts',
                    'rebounds': 'reb',
                    'assists': 'ast',
                    'threes': '3pm',
                    'offensive_rebounds': 'oreb'
                }.get(stat_key, stat_key)

                props_formatted[mapped_key] = {
                    'line': line_float,
                    'odds_over': -110,  # Assume standard juice (Module A may provide actual)
                    'odds_under': -110
                }

            # Only add if we have at least one valid prop
            if props_formatted:
                player_dict['sportsbook_props'] = props_formatted
            else:
                # Skip if no valid props after filtering
                continue
        else:
            # Skip players without props (no bets to generate)
            continue

        players.append(player_dict)

    # Build game-level structure
    spread = game_data.get('vegas', {}).get('spread', 0)
    if spread == 'N/A':
        spread = 0
    ref_impact = game_data.get('archetypes', {}).get('ref_impact', 1.0)

    return [{
        'game_id': game_data.get('matchup', 'UNKNOWN').replace(' @ ', '_vs_'),
        'spread': abs(spread) if spread else 0,
        'ref_impact': ref_impact,
        'players': players
    }]


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def test_pipeline():
    """
    Full end-to-end pipeline test.

    Pipeline Steps:
    1. Initialize modules and API monitor
    2. Fetch live slate and props (Module A)
    3. Query database for active rosters
    4. Match props to players
    5. Build simulation scenarios
    6. Run Monte Carlo simulations (Module C)
    7. Build reporter input from sim results
    8. Generate daily briefing (Module F)
    9. Validate costs and output
    """
    print("\n" + "="*70)
    print("LUDI INFORMATIO - FULL PIPELINE TEST")
    print("Week 1, Day 7 - Final Integration Validation")
    print("="*70)
    print(f"Target Games: 3")
    print(f"Budget: ${MAX_BUDGET:.2f} (~{MAX_CREDITS} credits)")
    print("="*70 + "\n")

    # Track initial state
    monitor = get_monitor()
    initial_credits = None

    if os.path.exists('api_usage_log.json'):
        with open('api_usage_log.json', 'r') as f:
            logs = json.load(f)
            if logs:
                initial_credits = int(logs[-1]['rate_limit_info']['requests_remaining'])
                print(f"[INIT] Starting credits: {initial_credits:,}\n")

    # === STEP 1: Initialize Modules ===
    print("[STEP 1] Initializing Modules...")
    try:
        gate = Gatekeeper()
        oracle = LudiOracle()
        reporter = LudiReporter()
        print("    ✅ All modules initialized\n")
    except Exception as e:
        print(f"    ❌ Module initialization failed: {e}\n")
        return False

    # === STEP 2: Fetch Live Slate ===
    print("[STEP 2] Fetching Live Slate...")
    try:
        gate.fetch_live_slate()
        print(f"    ✅ Slate fetch complete ({len(gate.games)} games found)\n")
    except Exception as e:
        print(f"    ❌ Slate fetch failed: {e}\n")
        return False

    # === STEP 3: Fetch Props for 3 Games ===
    print("[STEP 3] Fetching Props for 3 Games...")
    try:
        gate.fetch_comprehensive_props(limit_games=3)
        print("    ✅ Props fetch complete\n")
    except Exception as e:
        print(f"    ❌ Props fetch failed: {e}\n")
        return False

    # === STEP 4: Build Scenarios from Database ===
    print("[STEP 4] Querying Database for Active Rosters...")
    all_scenarios = []
    games_processed = 0

    for game_id, game_data in gate.games.items():
        if games_processed >= 3:
            break

        # Skip games without props
        if not game_data.get('props'):
            continue

        home_team = gate._get_abbr(game_data['home'])
        away_team = gate._get_abbr(game_data['away'])

        if not home_team or not away_team:
            print(f"    ⚠️  Skipping {game_data['matchup']} (team abbreviation not found)")
            continue

        print(f"    > {game_data['matchup']}")

        # Query rosters
        try:
            home_roster = get_active_roster(home_team, limit=5)
            away_roster = get_active_roster(away_team, limit=5)
            print(f"      - Home ({home_team}): {len(home_roster)} players")
            print(f"      - Away ({away_team}): {len(away_roster)} players")
        except Exception as e:
            print(f"      ❌ Roster query failed: {e}")
            continue

        # Match props to players
        props_data = fetch_props_for_game(gate, game_id)
        home_matched = match_props_to_roster(props_data, home_roster)
        away_matched = match_props_to_roster(props_data, away_roster)

        print(f"      - Players with props: {len(home_matched) + len(away_matched)}")

        if len(home_matched) + len(away_matched) == 0:
            print(f"      ⚠️  No players matched with props - skipping game")
            continue

        # Build scenario
        scenario = build_simulation_scenario(
            game_data,
            home_matched,
            away_matched,
            gate
        )

        all_scenarios.append({
            'scenario': scenario,
            'game_data': game_data,
            'game_id': game_id,
            'props_data': props_data
        })

        games_processed += 1

    print(f"    ✅ Built {len(all_scenarios)} scenarios\n")

    if not all_scenarios:
        print("    ❌ No scenarios built - cannot continue")
        return False

    # === STEP 5: Run Simulations ===
    print("[STEP 5] Running Monte Carlo Simulations...")
    all_sim_results = []

    for item in all_scenarios:
        scenario = item['scenario']
        print(f"    > Simulating {scenario['scenario_name']}...")

        try:
            sim_results = oracle.run_simulation_batch([scenario])
            print(f"      ✅ Simulated {len(sim_results)} players")
            all_sim_results.extend(sim_results)

            # Store for reporter
            item['sim_results'] = sim_results
        except Exception as e:
            print(f"      ❌ Simulation failed: {e}")
            continue

    print(f"    ✅ Total projections: {len(all_sim_results)}\n")

    # === STEP 6: Build Reporter Input ===
    print("[STEP 6] Building Reporter Input...")
    processed_slate = []

    for item in all_scenarios:
        if 'sim_results' not in item:
            continue

        reporter_input = build_reporter_input(
            item['sim_results'],
            item['game_data'],
            item['props_data']
        )

        processed_slate.extend(reporter_input)

    print(f"    ✅ Reporter input built ({len(processed_slate)} games)\n")

    # === STEP 7: Generate Briefing ===
    print("[STEP 7] Generating Daily Briefing...")
    try:
        briefing, _, _ = reporter.generate_report(processed_slate)

        # Write to file
        with open('daily_briefing.txt', 'w') as f:
            f.write(briefing)

        print("    ✅ Briefing generated → daily_briefing.txt\n")
        print("\n" + "="*70)
        print("DAILY BRIEFING OUTPUT:")
        print("="*70)
        print(briefing)
        print("="*70 + "\n")
    except Exception as e:
        print(f"    ❌ Briefing generation failed: {e}\n")
        return False

    # === STEP 8: Cost Validation ===
    print("[STEP 8] Validating API Costs...")

    if os.path.exists('api_usage_log.json'):
        with open('api_usage_log.json', 'r') as f:
            logs = json.load(f)

        final_credits = int(logs[-1]['rate_limit_info']['requests_remaining'])
        credits_used = initial_credits - final_credits if initial_credits else 0

        cost_per_credit = 30.0 / 20000
        total_cost = credits_used * cost_per_credit

        print(f"    - Credits used: {credits_used}")
        print(f"    - Remaining: {final_credits:,}")
        print(f"    - Total cost: ${total_cost:.4f}")

        if total_cost <= MAX_BUDGET:
            print(f"    ✅ UNDER BUDGET (${total_cost:.4f} < ${MAX_BUDGET:.2f})\n")
        else:
            print(f"    ⚠️  OVER BUDGET (${total_cost:.4f} > ${MAX_BUDGET:.2f})\n")
    else:
        print("    ⚠️  Could not read api_usage_log.json\n")

    print("="*70)
    print("PIPELINE TEST COMPLETE ✅")
    print("="*70)

    return True


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    success = test_pipeline()

    if success:
        print("\n✅ All systems operational - Ready for Week 2")
    else:
        print("\n❌ Pipeline test failed - Review errors above")
