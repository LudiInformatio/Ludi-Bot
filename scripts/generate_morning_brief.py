#!/usr/bin/env python3
"""
LUDI INFORMATIO | DAILY MORNING BRIEF
Generates the complete morning briefing with referee intelligence

Usage:
    python scripts/generate_morning_brief.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module_a import Gatekeeper
from module_g import LudiRefEngine
from utils.referee_briefing import generate_whistle_watch
from datetime import datetime


def generate_morning_brief():
    """
    Generate the complete morning brief including:
    1. Game slate overview
    2. Referee intelligence (Whistle Watch)
    3. Key betting opportunities (if available)
    """
    
    print("=" * 60)
    print("LUDI INFORMATIO | MORNING BRIEF")
    print(f"Date: {datetime.now().strftime('%A, %B %d, %Y')}")
    print("=" * 60)
    
    # Initialize modules
    print("\n[1/2] Initializing Gatekeeper...")
    gate = Gatekeeper()
    
    print("[2/2] Initializing Zebras...")
    zebras = LudiRefEngine()
    zebras.build_ref_database()
    
    # Fetch today's slate
    print("\nFetching today's NBA slate...")
    gate.fetch_live_slate()
    
    # Convert games dict to list for referee briefing
    games_list = []
    for game_id, game_data in gate.games.items():
        games_list.append(game_data)
    
    if not games_list:
        print("\n⚠️  No games scheduled for today.")
        return
    
    print(f"\n✅ Found {len(games_list)} games\n")
    
    # Generate sections
    print("=" * 60)
    print("📅 TODAY'S SLATE")
    print("=" * 60)
    
    for game in games_list:
        matchup = game.get('matchup', 'N/A')
        spread = game.get('vegas', {}).get('spread', 'N/A')
        total = game.get('vegas', {}).get('total', 'N/A')
        time_str = game.get('start_time')
        
        if time_str and hasattr(time_str, 'strftime'):
            time_str = time_str.strftime('%I:%M %p ET')
        else:
            time_str = "TBD"
        
        print(f"🏀 {matchup}")
        print(f"   Time: {time_str} | Spread: {spread} | Total: {total}")
        print()
    
    # Generate Whistle Watch
    print(generate_whistle_watch(zebras, games_list))
    
    print("\n" + "=" * 60)
    print("💡 TIP: Lenient crews favor flow; Strict crews favor FTA props")
    print("=" * 60)


if __name__ == "__main__":
    generate_morning_brief()
