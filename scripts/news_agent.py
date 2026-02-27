#!/usr/bin/env python3
"""
News Catalyst Agent — Pre-game news research tool

Fetches relevant non-injury news for players and classifies betting impact.
Can target specific games or players.

Usage:
    python scripts/news_agent.py --game CLE@DET
    python scripts/news_agent.py --player "Shai Gilgeous-Alexander"
    python scripts/news_agent.py --game CLE@DET --verbose

Author: Phase 8 Module D Audit
Date: February 27, 2026
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from module_d import LudiYak


def parse_game_arg(game_str: str) -> tuple:
    """Parse game string like 'CLE@DET' into (away, home)."""
    if '@' not in game_str:
        raise ValueError("Game format must be 'AWAY@HOME' (e.g., CLE@DET)")
    parts = game_str.split('@')
    if len(parts) != 2:
        raise ValueError("Game format must be 'AWAY@HOME' (e.g., CLE@DET)")
    return parts[0].strip().upper(), parts[1].strip().upper()


def get_team_players(conn: sqlite3.Connection, team_abbr: str) -> list:
    """Get active players for a team from the database."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM players 
        WHERE team = ? AND is_active = 1
    """, (team_abbr,))
    return [row[0] for row in cursor.fetchall()]


def main():
    parser = argparse.ArgumentParser(description="News Catalyst Agent — Pre-game news research")
    parser.add_argument("--game", type=str, help="Game to analyze (e.g., CLE@DET)")
    parser.add_argument("--player", type=str, help="Specific player to analyze")
    parser.add_argument("--verbose", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    if not args.game and not args.player:
        parser.error("Must specify --game or --player")

    yak = LudiYak()
    today = datetime.now().strftime("%b %d, %Y")

    print(f"\nNEWS CATALYST REPORT — {today}")
    print("=" * 50)

    players_to_check = []
    game_info = None

    if args.game:
        away, home = parse_game_arg(args.game)
        game_info = (away, home)
        
        db_path = getattr(config, 'DB_PATH', 'ludi.db')
        conn = sqlite3.connect(db_path)
        
        away_players = get_team_players(conn, away)
        home_players = get_team_players(conn, home)
        conn.close()
        
        players_to_check = away_players + home_players
        print(f"Game: {away} @ {home}")
        print(f"Players: {len(players_to_check)} ({away}: {len(away_players)}, {home}: {len(home_players)})")
        print()

    elif args.player:
        players_to_check = [args.player]
        print(f"Player: {args.player}")
        print()

    over_signals = []
    under_signals = []
    neutral_signals = []

    for player in players_to_check:
        if args.verbose:
            print(f"Checking: {player}...", end=" ")
        
        if game_info:
            away, home = game_info
            db_path = getattr(config, 'DB_PATH', 'ludi.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT team FROM players WHERE name = ?", (player,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                if args.verbose:
                    print("skipped (not in DB)")
                continue
            
            player_team = row[0]
            opponent = home if player_team == away else away
        else:
            player_team = "NBA"
            opponent = "Opponent"
        
        result = yak._check_news_catalyst(player, player_team, opponent)
        
        if result:
            if args.verbose:
                print(f"FOUND: {result.get('catalyst_type')} ({result.get('bet_direction')}, conf: {result.get('confidence')})")
            
            signal_entry = {
                'player': player,
                'type': result.get('catalyst_type'),
                'signal': result.get('signal'),
                'confidence': result.get('confidence')
            }
            
            direction = result.get('bet_direction')
            if direction == 'OVER':
                over_signals.append(signal_entry)
            elif direction == 'UNDER':
                under_signals.append(signal_entry)
            else:
                neutral_signals.append(signal_entry)
        else:
            if args.verbose:
                print("no relevant news")

    print()
    print("OVER signals:")
    if over_signals:
        for s in over_signals:
            print(f"  * {s['player']} — {s['type']}: {s['signal']} (conf: {s['confidence']:.2f})")
    else:
        print("  (none)")

    print()
    print("UNDER signals:")
    if under_signals:
        for s in under_signals:
            print(f"  * {s['player']} — {s['type']}: {s['signal']} (conf: {s['confidence']:.2f})")
    else:
        print("  (none)")

    print()
    print("Neutral:")
    if neutral_signals:
        for s in neutral_signals:
            print(f"  * {s['player']} — {s['type']}: {s['signal']} (conf: {s['confidence']:.2f})")
    else:
        print(f"  ({len(players_to_check)} players — no relevant news found)")

    print()
    print(f"Total players checked: {len(players_to_check)}")


if __name__ == "__main__":
    main()
