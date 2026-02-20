#!/usr/bin/env python
"""
send_single_game_notes.py - Targeted Game Analysis

Uses full LudiOrchestrator pipeline (A→D→C→E→F) to generate
game-specific notes with referee crew and archetype insights.

Default: Gets first game of the day
Usage: ./venv/bin/python send_single_game_notes.py [HOME_TEAM] [AWAY_TEAM]
"""

import sys
from datetime import datetime
from main import LudiOrchestrator
from utils.telegram_notifier import send_message

def send_specific_game_notes(home_team=None, away_team=None):
    """Generate and send game notes for a specific matchup"""
    
    # Initialize full orchestrator (gets all modules A-H)
    print("\n🚀 Initializing Ludi Orchestrator...")
    app = LudiOrchestrator()
    
    # Fetch today's slate
    print("[1] Fetching Live Slate...")
    app.gate.fetch_live_slate()
    
    if not app.gate.games:
        print("❌ No games found today")
        return
    
    # Fetch props for all games (or target if specified)
    print("[2] Fetching Player Props...")
    app.gate.fetch_comprehensive_props(limit_games=5)
    
    # Find target game
    target_game = None
    target_game_id = None
    
    if home_team and away_team:
        print(f"\n🔎 SEARCHING FOR: {away_team} @ {home_team}")
        for game_id, game in app.gate.games.items():
            h = app.gate._get_abbr(game['home'])
            a = app.gate._get_abbr(game['away'])
            
            if (h == home_team and a == away_team) or (h == away_team and a == home_team):
                target_game = game
                target_game_id = game_id
                break
    else:
        # Default: Get first game with props
        print("\n🔎 Using first game of the day")
        for game_id, game in app.gate.games.items():
            if game.get('props'):
                target_game = game
                target_game_id = game_id
                home_team = app.gate._get_abbr(game['home'])
                away_team = app.gate._get_abbr(game['away'])
                break
    
    if not target_game:
        print(f"❌ Game not found in current slate.")
        print("   Current Slate:")
        for g in app.gate.games.values():
            print(f"   - {g['matchup']}")
        return
    
    print(f"✅ FOUND: {target_game['matchup']}")
    print(f"   Refs: {target_game.get('archetypes', {}).get('ref_crew', 'Pending')}")
    
    # Get rosters
    print("[3] Building Rosters...")
    home_roster = app.get_active_roster(home_team)
    away_roster = app.get_active_roster(away_team)
    
    # Match props
    props_data = app.fetch_props_for_game(target_game_id)
    home_matched = app.match_props_to_roster(props_data, home_roster)
    away_matched = app.match_props_to_roster(props_data, away_roster)
    
    if not home_matched and not away_matched:
        print("❌ No players with props found")
        return
    
    # Apply injury filtering (Module D)
    print("[4] Checking Injury Status (Module D)...")
    filtered_home = []
    filtered_away = []
    
    for player in home_matched:
        status_info = app.yak.get_player_status(player['PLAYER_NAME'], home_team)
        if status_info['status'] in ['OUT', 'DOUBTFUL']:
            print(f"   ⚠️  {player['PLAYER_NAME']}: {status_info['status']} - Skipping")
        else:
            player['injury_status'] = status_info['status']
            player['injury_note'] = status_info.get('note', '')
            filtered_home.append(player)
    
    for player in away_matched:
        status_info = app.yak.get_player_status(player['PLAYER_NAME'], away_team)
        if status_info['status'] in ['OUT', 'DOUBTFUL']:
            print(f"   ⚠️  {player['PLAYER_NAME']}: {status_info['status']} - Skipping")
        else:
            player['injury_status'] = status_info['status']
            player['injury_note'] = status_info.get('note', '')
            filtered_away.append(player)
    
    if not filtered_home and not filtered_away:
        print("❌ All players filtered out by injury status")
        return
    
    # Build scenario
    scenario = app.build_simulation_scenario(target_game, filtered_home, filtered_away)
    
    # Run simulation (Module C)
    print(f"[5] Running Simulations...")
    sim_results = app.sim.run_simulation_batch([scenario])
    
    # Build reporter input (includes Module E calibration)
    print("[6] Applying Calibration (Module E)...")
    processed_slate = app.build_reporter_input(sim_results, target_game, props_data)
    
    # Generate report (Module F)
    print("[7] Generating Report (Module F)...")
    report_result = app.reporter.generate_report(processed_slate)
    
    # Handle tuple return (text, image_path) from updated Module F
    if isinstance(report_result, tuple):
        standard_report, image_path, _ = report_result
    else:
        standard_report = report_result
        image_path = None
    
    # Custom header with ref info
    header = f"📋 **GAME NOTES: {away_team} @ {home_team}**\\n"
    header += f"📅 {datetime.now().strftime('%b %d, %Y')} | ⏰ {datetime.now().strftime('%I:%M %p')} EST\\n"
    
    refs = target_game.get('archetypes', {}).get('ref_crew', [])
    ref_impact = target_game.get('archetypes', {}).get('ref_impact', 1.0)
    
    if refs and refs != "Unknown":
        header += f"🦓 **Ref Crew:** {', '.join(refs)}\\n"
        header += f"⚖️ **Ref Impact:** {ref_impact:.2f}x (Avg: 1.0)\\n"
    else:
        header += f"🦓 **Ref Crew:** Pending\\n"
    
    header += "──────────────\\n"
    
    full_message = header + standard_report
    
    # Send to Telegram (Visual Card Only - No Redundant Text)
    print("\\n📨 Sending Game Notes to Telegram...")
    
    if image_path:
        from utils.telegram_notifier import send_photo
        send_photo(image_path, caption=f"🏀 {away_team} @ {home_team} | Sharp Brief")
        print("✅ Visual card sent!")
    else:
        # Fallback to text only if image generation failed
        send_message(full_message)
        print("✅ Text fallback sent!")
    
    print("✅ Done!")

if __name__ == "__main__":
    # Parse command line args
    if len(sys.argv) == 3:
        home = sys.argv[1].upper()
        away = sys.argv[2].upper()
        send_specific_game_notes(home, away)
    else:
        # Default: First game of the day
        send_specific_game_notes()
