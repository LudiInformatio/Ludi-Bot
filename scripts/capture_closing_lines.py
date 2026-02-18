#!/usr/bin/env python3
"""
Forward CLV Capture Script

Captures closing odds before tipoff for CLV (Closing Line Value) calculation.
Runs 5-15 minutes before game start to capture the sharpest closing lines.

Usage:
    python scripts/capture_closing_lines.py [--dry-run] [--verbose]

Workflow: Runs 30 mins before tipoff (7:30 PM EST on game nights)
"""

import argparse
import sqlite3
import sys
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import pytz

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import config

EST = pytz.timezone('US/Eastern')


def american_to_decimal(american_odds: int) -> float:
    """Convert American odds to decimal odds."""
    if american_odds is None:
        return 1.0
    if american_odds >= 0:
        return 1 + (american_odds / 100)
    return 1 + (100 / abs(american_odds))


def calculate_clv(bet_decimal: float, closing_decimal: float) -> float:
    """Calculate CLV in cents: (your_decimal - closing_decimal) * 100"""
    if bet_decimal is None or closing_decimal is None:
        return 0.0
    return (bet_decimal - closing_decimal) * 100


def fetch_today_games() -> List[Dict]:
    """Fetch today's games. Primary: The-Odds-API. Fallback: BDL."""
    # Try The-Odds-API first
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/scores"
    params = {
        'api_key': config.ODDS_API_KEY,
        'daysFrom': 1
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        games = []
        for game in data:
            if game.get('status') != 'Scheduled':
                continue
            commence = game.get('commence_time')
            if not commence:
                continue
            commence_dt = datetime.fromisoformat(commence.replace('Z', '+00:00')).astimezone(EST)
            games.append({
                'game_id': game.get('id'),
                'commence_time': commence_dt,
                'home_team': game.get('home_team'),
                'away_team': game.get('away_team'),
            })
        
        if games:
            return games
    except Exception as e:
        print(f"The-Odds-API failed: {e}")
    
    # Fallback: BDL
    print("Falling back to BDL for today's games...")
    try:
        from utils.bdl_client import BDLClient
        bdl = BDLClient()
        today = datetime.now(EST).strftime('%Y-%m-%d')
        resp = bdl.get_games(date=today)
        games = []
        for g in resp.get('data', []):
            # Skip non-scheduled games
            status = g.get('status', '')
            if status not in ['Scheduled', 'Pre-Game', '']:
                continue
            games.append({
                'game_id': str(g['id']),  # Convert to string for consistency
                'commence_time': datetime.fromisoformat(g.get('datetime', today).replace('Z', '+00:00')).astimezone(EST) if g.get('datetime') else datetime.now(EST),
                'home_team': g.get('home_team', {}).get('full_name'),
                'away_team': g.get('visitor_team', {}).get('full_name'),
            })
        return games
    except Exception as e2:
        print(f"BDL fallback also failed: {e2}")
        return []


def fetch_closing_lines(game_id: str) -> Dict:
    """Fetch closing odds for a specific game. Primary: The-Odds-API. Fallback: BDL."""
    # Try The-Odds-API first
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{game_id}/odds"
    params = {
        'api_key': config.ODDS_API_KEY,
        'regions': 'us',
        'markets': 'player_points,player_rebounds,player_assists,player_threes,player_steals,player_blocks,player_turnovers,player_points_rebounds_assists,player_points_rebounds,player_points_assists,player_rebounds_assists',
        'oddsFormat': 'american'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"The-Odds-API closing lines failed: {e}")
    
    # Fallback: BDL odds
    print(f"Falling back to BDL for closing lines on game {game_id}...")
    try:
        from utils.bdl_client import BDLClient
        bdl = BDLClient()
        today = datetime.now(EST).strftime('%Y-%m-%d')
        odds = bdl.get_odds(date=today)
        
        # Transform BDL odds format to match The-Odds-API structure for match_closing_lines() compatibility
        # BDL odds are game-level, not event-level, so we need to find matching game
        for odd in odds:
            if str(odd.get('game_id')) == str(game_id):
                # Convert BDL format to a The-Odds-API-like structure
                return {
                    'bookmakers': [{
                        'key': odd.get('vendor', 'bdl'),
                        'markets': [
                            {
                                'key': 'player_points',
                                'outcomes': []  # BDL doesn't have player props in odds endpoint
                            },
                            {
                                'key': 'player_rebounds',
                                'outcomes': []
                            },
                            {
                                'key': 'player_assists',
                                'outcomes': []
                            }
                        ]
                    }],
                    'home_team': '',  # Not available in BDL odds
                    'away_team': '',
                }
        return {}
    except Exception as e2:
        print(f"BDL closing lines fallback failed: {e2}")
        return {}


def find_imminent_games(games: List[Dict], minutes: int = 15) -> List[Dict]:
    """Find games starting in the next N minutes."""
    now = datetime.now(EST)
    imminent = []
    
    for game in games:
        time_diff = (game['commence_time'] - now).total_seconds() / 60
        if 0 <= time_diff <= minutes:
            imminent.append(game)
    
    return imminent


def get_pending_bets(conn: sqlite3.Connection, game_date: str = None) -> List[Dict]:
    """Get pending bets from database."""
    c = conn.cursor()
    
    if game_date:
        c.execute('''
            SELECT id, player_name, team, stat_category, bet_side, 
                   line, odds_over, odds_under, game_id, game_date
            FROM bet_recommendations
            WHERE outcome IS NULL 
              AND game_date = ?
              AND (closing_odds_over IS NULL OR closing_odds_over = 0)
            ORDER BY game_date
        ''', (game_date,))
    else:
        c.execute('''
            SELECT id, player_name, team, stat_category, bet_side, 
                   line, odds_over, odds_under, game_id, game_date
            FROM bet_recommendations
            WHERE outcome IS NULL 
              AND (closing_odds_over IS NULL OR closing_odds_over = 0)
            ORDER BY game_date
        ''')
    
    columns = [desc[0] for desc in c.description]
    return [dict(zip(columns, row)) for row in c.fetchall()]


def update_bet_with_closing_lines(conn: sqlite3.Connection, bet_id: int, 
                                   closing_over: int, closing_under: int,
                                   clv_cents: float, closing_time: str) -> None:
    """Update a bet with closing line data."""
    c = conn.cursor()
    c.execute('''
        UPDATE bet_recommendations
        SET closing_odds_over = ?,
            closing_odds_under = ?,
            clv_cents = ?,
            closing_time = ?
        WHERE id = ?
    ''', (closing_over, closing_under, clv_cents, closing_time, bet_id))
    conn.commit()


def match_closing_lines(bet: Dict, closing_data: Dict) -> Tuple[Optional[int], Optional[int]]:
    """Match bet to closing lines from API response."""
    player_name = bet['player_name'].lower()
    stat_cat = bet['stat_category'].lower()
    
    market_map = {
        'pts': 'player_points',
        'reb': 'player_rebounds',
        'ast': 'player_assists',
        '3pm': 'player_threes',
        'stl': 'player_steals',
        'blk': 'player_blocks',
        'tov': 'player_turnovers',
        'pra': 'player_points_rebounds_assists',
        'pr': 'player_points_rebounds',
        'pa': 'player_points_assists',
        'ra': 'player_rebounds_assists',
    }
    
    market_key = market_map.get(stat_cat, f'player_{stat_cat}')
    
    for bookmaker in closing_data.get('bookmakers', []):
        for market in bookmaker.get('markets', []):
            if market.get('key') != market_key:
                continue
            
            for outcome in market.get('outcomes', []):
                player = outcome.get('description', '').lower()
                if player != player_name:
                    continue
                
                point = outcome.get('point')
                price = outcome.get('price')
                
                if point == bet['line']:
                    if outcome.get('name', '').lower() == 'over':
                        return price, None
                    elif outcome.get('name', '').lower() == 'under':
                        return None, price
    
    return None, None


def process_game(conn: sqlite3.Connection, game_id: str, bets: List[Dict],
                 dry_run: bool = False, verbose: bool = False) -> Dict:
    """Process closing lines for a single game."""
    closing_data = fetch_closing_lines(game_id)
    
    if not closing_data:
        if verbose:
            print(f"  No closing data found for {game_id}")
        return {'updated': 0, 'skipped': 0}
    
    updated = 0
    skipped = 0
    closing_time = datetime.now(EST).isoformat()
    
    for bet in bets:
        closing_over, closing_under = match_closing_lines(bet, closing_data)
        
        if closing_over is None and closing_under is None:
            skipped += 1
            print(f"  SKIP bet {bet['id']}: {bet['player_name']} {bet['stat_category']} — no closing line match found")
            continue
        
        bet_decimal = american_to_decimal(bet.get('odds_over') or bet.get('odds_under'))
        
        if closing_over and bet['bet_side'] == 'OVER':
            closing_decimal = american_to_decimal(closing_over)
            clv = calculate_clv(bet_decimal, closing_decimal)
        elif closing_under and bet['bet_side'] == 'UNDER':
            closing_decimal = american_to_decimal(closing_under)
            clv = calculate_clv(bet_decimal, closing_decimal)
        else:
            clv = 0.0
        
        if not dry_run:
            update_bet_with_closing_lines(
                conn, bet['id'], closing_over, closing_under, clv, closing_time
            )
        
        updated += 1
        if verbose:
            print(f"  Updated bet {bet['id']}: {bet['player_name']} {bet['stat_category']} "
                  f"{bet['bet_side']} {bet['line']} | CLV: {clv:.2f}c")
    
    return {'updated': updated, 'skipped': skipped}


def main():
    parser = argparse.ArgumentParser(description='Capture closing lines for pending bets')
    parser.add_argument('--dry-run', action='store_true', help='Simulate without updating database')
    parser.add_argument('--verbose', action='store_true', help='Print detailed output')
    parser.add_argument('--game-date', type=str, default=None, 
                        help='Process bets for specific game date (YYYY-MM-DD)')
    args = parser.parse_args()
    
    print("="*60)
    print("CLV CAPTURE SCRIPT | Forward Line Capture")
    print("="*60)
    
    if args.dry_run:
        print("⚠️  DRY RUN MODE - No database changes will be made")
    
    db_path = project_root / 'ludi.db'
    if not db_path.exists():
        print("❌ Database not found")
        sys.exit(1)
    
    conn = sqlite3.connect(str(db_path))
    
    if args.game_date:
        pending_bets = get_pending_bets(conn, args.game_date)
    else:
        games = fetch_today_games()
        
        if not games:
            print("No games found for today")
            conn.close()
            return
        
        imminent = find_imminent_games(games, minutes=15)
        
        if not imminent:
            print(f"No games starting in next 15 minutes")
            for g in games:
                print(f"  {g['away_team']} @ {g['home_team']} - {g['commence_time'].strftime('%I:%M %p EST')}")
            conn.close()
            return
        
        print(f"Found {len(imminent)} game(s) starting soon:")
        for g in imminent:
            print(f"  {g['away_team']} @ {g['home_team']} - {g['commence_time'].strftime('%I:%M %p EST')}")
        
        game_ids = [g['game_id'] for g in imminent]
        pending_bets = [b for b in get_pending_bets(conn) if b['game_id'] in game_ids]
    
    if not pending_bets:
        print("No pending bets found")
        conn.close()
        return
    
    print(f"Found {len(pending_bets)} pending bet(s) to process")
    
    by_game = {}
    for bet in pending_bets:
        gid = bet['game_id']
        if gid not in by_game:
            by_game[gid] = []
        by_game[gid].append(bet)
    
    total_updated = 0
    total_skipped = 0
    
    for game_id, bets in by_game.items():
        print(f"\nProcessing game {game_id}...")
        result = process_game(conn, game_id, bets, dry_run=args.dry_run, verbose=args.verbose)
        total_updated += result['updated']
        total_skipped += result['skipped']
    
    conn.close()
    
    print("\n" + "="*60)
    print(f"SUMMARY")
    print(f"  Bets updated: {total_updated}")
    print(f"  Bets skipped: {total_skipped}")
    print("="*60)


if __name__ == "__main__":
    main()
