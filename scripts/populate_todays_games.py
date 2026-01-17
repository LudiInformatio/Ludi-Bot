#!/usr/bin/env python3
"""
Populate Today's Games
======================
Fetches live schedule from The Odds API and inserts into Ludi database.
This bridges the gap between the static schedule and real-time games.
"""

import sys
import os
import sqlite3
import requests
from datetime import datetime
import pytz

# Add project root to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

DB_PATH = 'ludi.db'
EST_TZ = pytz.timezone('US/Eastern')

# Standardize Team Abbreviations (Copied from module_g.py/sync_daily_referees.py)
TEAM_MAP = {
    "Atlanta Hawks": "ATL",
    "Boston Celtics": "BOS",
    "Brooklyn Nets": "BKN",
    "Charlotte Hornets": "CHA",
    "Chicago Bulls": "CHI",
    "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL",
    "Denver Nuggets": "DEN",
    "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW",
    "Houston Rockets": "HOU",
    "Indiana Pacers": "IND",
    "Los Angeles Clippers": "LAC",
    "LA Clippers": "LAC",
    "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM",
    "Miami Heat": "MIA",
    "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN",
    "New Orleans Pelicans": "NOP",
    "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC",
    "Orlando Magic": "ORL",
    "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX",
    "Portland Trail Blazers": "POR",
    "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS",
    "Toronto Raptors": "TOR",
    "Utah Jazz": "UTA",
    "Washington Wizards": "WAS"
}

def resolve_team(name):
    return TEAM_MAP.get(name, name[:3].upper())

def fetch_todays_schedule():
    print("📡 Fetching schedule from The Odds API...")
    url = 'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
    params = {
        'api_key': config.ODDS_API_KEY,
        'regions': 'us',
        'markets': 'h2h', # We just need the event info
        'oddsFormat': 'american'
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        today_str = datetime.now(EST_TZ).strftime('%Y-%m-%d')
        print(f"   Date Filter: {today_str}")
        
        games_to_insert = []
        
        for game in data:
            # Convert UTC start time to EST date string
            utc_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            est_time = utc_time.astimezone(EST_TZ)
            game_date = est_time.strftime('%Y-%m-%d')
            
            if game_date == today_str:
                game_id = game['id'] # Use API ID as unique identifier
                home_team = resolve_team(game['home_team'])
                away_team = resolve_team(game['away_team'])
                
                # Construct a readable ID if needed, or use API ID
                # Ludi uses text IDs sometimes like 20260117_BOS@NYK
                # Let's stick to a format compatible with our systems
                # Format: YYYYMMDD_AWAY@HOME
                ludi_game_id = f"{est_time.strftime('%Y%m%d')}_{away_team}@{home_team}"
                
                games_to_insert.append((ludi_game_id, game_date, home_team, away_team))
                
        return games_to_insert

    except Exception as e:
        print(f"❌ Error fetching schedule: {e}")
        return []

def update_database(games):
    if not games:
        print("⚠️ No games found for today.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print(f"💾 Inserting/Updating {len(games)} games...")
    
    for g in games:
        g_id, g_date, home, away = g
        print(f"   🏀 {away} @ {home} ({g_id})")
        
        # Upsert logic
        try:
            cursor.execute("""
                INSERT INTO games (game_id, date, home_team, away_team)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    date=excluded.date,
                    home_team=excluded.home_team,
                    away_team=excluded.away_team
            """, (g_id, g_date, home, away))
        except Exception as e:
            print(f"   ❌ DB Error: {e}")
            
    conn.commit()
    conn.close()
    print("✅ Database updated.")

if __name__ == "__main__":
    games = fetch_todays_schedule()
    update_database(games)
