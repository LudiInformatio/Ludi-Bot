#!/usr/bin/env python3
"""
Sync Tank01 box scores directly to SQLite for Jan 16-18, 2026

Uses Module H's proven API parsing logic - just writes to SQLite instead of JSON
"""
import sqlite3
import requests
import config
from datetime import datetime
import time

# Tank01 API setup (same as Module H)
TANK_KEY = config.TANK01_KEY
TANK_HOST = 'tank01-fantasy-stats.p.rapidapi.com'
HEADERS = {
    "X-RapidAPI-Key": TANK_KEY,
    "X-RapidAPI-Host": TANK_HOST
}

def clean_minutes(min_val):
    """Handles MM:SS, float, or int inputs for minutes."""
    if not min_val:
        return 0.0
    try:
        return float(min_val)
    except ValueError:
        if isinstance(min_val, str) and ":" in min_val:
            parts = min_val.split(":")
            return float(parts[0]) + float(parts[1]) / 60
        return 0.0

def get_games_for_date(date_str):
    """Fetch all games for a date"""
    url = f"https://{TANK_HOST}/getNBAGamesForDate"
    params = {"gameDate": date_str}
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    data = r.json()
    return data.get('body', [])

def sync_date_to_sqlite(date_str, conn):
    """
    Sync all games for a date to SQLite.
    Uses same parsing logic as Module H's _fetch_single_game_box()
    """
    cursor = conn.cursor()
    
    # Get games for date
    games = get_games_for_date(date_str)
    if not games:
        print(f"  No games found for {date_str}")
        return 0
    
    print(f"  Found {len(games)} games for {date_str}")
    
    records_added = 0
    for game in games:
        game_id = game.get('gameID')
        if not game_id:
            continue
        
        print(f"    Processing game {game_id}...")
        
        # Get box score
        url = f"https://{TANK_HOST}/getNBABoxScore"
        params = {"gameID": game_id, "fantasyPoints": "false"}
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = r.json()
        body = data.get('body', {})
        
        # Get team abbreviations for matchup string
        away_team = body.get('away', 'UNK')
        home_team = body.get('home', 'UNK')
        matchup = f"{away_team} @ {home_team}"
        
        # playerStats is at body level, keyed by player ID (Module H pattern)
        player_stats = body.get('playerStats', {})
        
        game_records = 0
        for p_id, stats in player_stats.items():
            # Map Tank01 fields to our schema (exact Module H mapping)
            tov = stats.get('TOV', stats.get('to', 0))
            
            try:
                cursor.execute('''
                    INSERT INTO player_game_logs 
                    (season_id, player_id, player_name, team_id, team_abbreviation, team_name,
                     game_id, game_date, matchup, win_loss, minutes, fgm, fga, fg_pct,
                     fg3m, fg3a, fg3_pct, ftm, fta, ft_pct, oreb, dreb, reb, ast, stl, blk,
                     tov, pf, pts, plus_minus, fantasy_pts, video_available, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    '2025-26',  # season_id
                    p_id,  # player_id  
                    stats.get('longName', 'Unknown'),  # player_name
                    '',  # team_id
                    stats.get('teamAbv', 'UNK'),  # team_abbreviation
                    '',  # team_name
                    game_id,  # game_id
                    datetime.strptime(date_str, '%Y%m%d').strftime('%Y-%m-%d'),  # game_date
                    matchup,  # matchup
                    '',  # win_loss
                    clean_minutes(stats.get('mins', 0)),  # minutes
                    float(stats.get('fgm', 0)),  # fgm
                    float(stats.get('fga', 0)),  # fga
                    0,  # fg_pct
                    float(stats.get('tptfgm', 0)),  # fg3m (Tank01 weird key)
                    float(stats.get('tptfga', 0)),  # fg3a (Tank01 weird key)
                    0,  # fg3_pct
                    float(stats.get('ftm', 0)),  # ftm
                    float(stats.get('fta', 0)),  # fta
                    0,  # ft_pct
                    float(stats.get('oreb', 0)),  # oreb
                    float(stats.get('dreb', 0)),  # dreb
                    float(stats.get('reb', 0)),  # reb
                    float(stats.get('ast', 0)),  # ast
                    float(stats.get('stl', 0)),  # stl
                    float(stats.get('blk', 0)),  # blk
                    float(tov),  # tov
                    float(stats.get('pf', 0)),  # pf
                    float(stats.get('pts', 0)),  # pts
                    float(stats.get('plusMinus', 0)),  # plus_minus
                    0,  # fantasy_pts
                    0,  # video_available
                    datetime.now().isoformat()  # created_at
                ))
                game_records += 1
            except Exception as e:
                print(f"      Error inserting {stats.get('longName', 'Unknown')}: {e}")
        
        conn.commit()
        records_added += game_records
        print(f"      ✅ Added {game_records} player records")
        time.sleep(0.1)  # Rate limit
    
    return records_added

def main():
    # Dates to sync: Jan 16, 17, 18
    dates = ['20260116', '20260117', '20260118']
    
    conn = sqlite3.connect('ludi.db')
    
    total = 0
    for date_str in dates:
        print(f"\n📅 Syncing {date_str}...")
        count = sync_date_to_sqlite(date_str, conn)
        total += count
        print(f"  Subtotal: {count} records")
    
    conn.close()
    print(f"\n✅ TOTAL: Added {total} records to player_game_logs")
    
    # Verify
    print("\n📊 Verification:")
    conn = sqlite3.connect('ludi.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT game_date, COUNT(*) as count 
        FROM player_game_logs 
        WHERE game_date >= '2026-01-16' 
        GROUP BY game_date 
        ORDER BY game_date
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} records")
    conn.close()

if __name__ == '__main__':
    main()
