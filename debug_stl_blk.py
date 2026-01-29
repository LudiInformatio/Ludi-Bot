#!/usr/bin/env python3
"""
Debug script to trace STL/BLK data flow through the pipeline
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import LudiOrchestrator

# Initialize system
system = LudiOrchestrator()

# Fetch MIL vs WAS game data
system.gate.fetch_live_slate()
games = system.gate.games

# Find MIL game
mil_game_id = None
mil_game_data = None
for game_id, game_data in games.items():
    home = game_data.get('home', '')
    away = game_data.get('away', '')
    matchup = game_data.get('matchup', '')
    if 'MIL' in game_id or 'MIL' in home or 'MIL' in away or 'Milwaukee' in matchup:
        mil_game_id = game_id
        mil_game_data = game_data
        break

if not mil_game_id:
    print("No MIL game found")
    print("Available games:")
    for game_id, game_data in games.items():
        print(f"  {game_id}: {game_data.get('home', '')} @ {game_data.get('away', '')}")
    exit(1)

print(f"Found game: {mil_game_id}")
print(f"  Home: {mil_game_data.get('home', '')}")
print(f"  Away: {mil_game_data.get('away', '')}")
game_data = mil_game_data

# Get rosters - use team abbreviations since get_active_roster expects abbreviations
print(f"\nTrying team abbreviations...")
home_roster = system.get_active_roster('WAS')  # Washington Wizards
away_roster = system.get_active_roster('MIL')  # Milwaukee Bucks

print(f"Home roster players: {len(home_roster)}")
print(f"Away roster players: {len(away_roster)}")

# Check for Ryan Rollins specifically
all_players = home_roster + away_roster
for player in all_players:
    if 'Ryan Rollins' in player.get('PLAYER_NAME', ''):
        print(f"\nFound Ryan Rollins:")
        print(f"  Team: {player.get('TEAM_ABBREVIATION')}")
        print(f"  STL: {player.get('STL', 'MISSING')}")
        print(f"  BLK: {player.get('BLK', 'MISSING')}")
        print(f"  PTS: {player.get('PTS', 'MISSING')}")
        print(f"  MIN: {player.get('MIN', 'MISSING')}")