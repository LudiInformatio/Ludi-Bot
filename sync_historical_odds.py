import sqlite3
import requests
import json
import os
import time
from datetime import datetime, timedelta
try:
    import config
except ImportError:
    pass

# CONFIG
API_KEY = os.getenv("ODDS_API_KEY")
SPORT = "basketball_nba"
DB_PATH = "ludi.db"
REGIONS = "us" # us, uk, eu, au - US for NBA props
MARKETS = "player_points,player_rebounds,player_assists,player_threes,player_steals,player_blocks,player_points_rebounds_assists" 

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def sync_historical_odds():
    print("==================================================")
    print("LUDI INFORMATIO: HISTORICAL ODDS SYNC (CLV)")
    print("==================================================")
    
    if not API_KEY:
        print("❌ CRITICAL: ODDS_API_KEY not found in environment.")
        return

    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Get dates with bets and teams involved
    c.execute('''
        SELECT DISTINCT game_date FROM bet_recommendations
        ORDER BY game_date DESC
    ''')
    dates = [row['game_date'] for row in c.fetchall()]
    
    print(f"📅 Found bets on {len(dates)} dates: {dates}")
    
    total_updates = 0
    total_cost = 0 # Track credits conservatively (approx)
    
    for date_str in dates:
        print(f"\nProcessing {date_str}...")
        
        # Determine "Closing Time" - roughly 7 PM ET (00:00 UTC next day) + a few hours?
        # A better way: Look for the game's actual start time if we had it.
        # Approximation: Use 23:55:00 local time (end of day) to ensure we capture the whole day's history?
        # NO. The-Odds-API historical 'odds' endpoint returns a SNAPSHOT at the requested time.
        # To get the closing line, we want the odds at GAME START.
        # Since we don't have exact game start times in `bet_recommendations` handy (we have game_id but not time),
        # we'll approximate by checking at 11:59 PM UTC of the game day?
        # Most NBA games start 7-10 PM ET. 
        # 7 PM ET = 00:00 UTC (next day).
        # Let's target looking up the events list first, which gives us 'commence_time'.
        
        # 1. Fetch Events for this date
        # Use a time late in the day to ensure all games are listed? 
        # Actually, events are listed regardless of time usually, but let's pick noon UTC
        lookup_time = f"{date_str}T12:00:00Z"
        
        url_events = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/odds"
        params = {
            "apiKey": API_KEY,
            "regions": REGIONS,
            "markets": "h2h", # Minimal cost to get event IDs
            "date": lookup_time
        }
        
        try:
            res = requests.get(url_events, params=params)
            res.raise_for_status()
            data = res.json()
            events = data['data']
            # Credits: ~10?
            total_cost += 10
        except Exception as e:
            print(f"❌ Failed to fetch events for {date_str}: {e}")
            continue
            
        print(f"   Found {len(events)} events.")
        
        # 2. Get Bets for this date
        c.execute('SELECT * FROM bet_recommendations WHERE game_date = ?', (date_str,))
        bets = c.fetchall()
        
        # Group bets by Game (Home/Away team)
        bets_by_game = {}
        for bet in bets:
            # key by team names (careful with normalization)
            # Use home_team identifier if available, else infer?
            # We have home_team in DB!
            h_team = bet['home_team']
            if h_team not in bets_by_game:
                bets_by_game[h_team] = []
            bets_by_game[h_team].append(bet)
            
        # 3. Match Events -> Bets
        for event in events:
            ev_home = event['home_team'] # e.g. "Boston Celtics"
            ev_id = event['id']
            commence_time = event['commence_time']
            
            # Find matching bets
            # We store "BOS" or "Boston". Gatekeeper usually stores Abbr "BOS".
            # We need a mapper. Tank01 uses Abbr. The-Odds-API uses Full Name.
            # Lazy match: Check if known abbr map or fuzzy match?
            # Let's fetch the bets first and see if we match.
            
            # Simple Abbr Mapper (Hardcoded for top teams or generic check)
            # Better: Map full names to Abbrs.
            matched_bets = []
            
            for h_abbr, bet_list in bets_by_game.items():
                # Check if 'Boston Celtics' contains 'BOS' ? No.
                # We need a proper map. 
                # Let's rely on the user being consistent or build a map.
                # For now, let's try to match basic strings.
                
                # Check if Mapping exists in utils?
                # Let's create a quick map here or check Gatekeeper
                # Assuming Gatekeeper has it, but I can't import instance easily.
                pass 
                
            # --- QUICK MAPPER ---
            # Constructing a mini-map based on standard NBA names
            # If we fail to match, we skip.
            # Strategy: look for common substrings or just match known Abbrs
            
            # Just do full Prop Fetch for ALL events on dates where we have bets?
            # Costly if we have many games. 
            # Optimization: Only fetch if we have bets for those teams.
            
            # Let's assume we proceed.
            # Closing Line Query: Use the commence_time!
            
            # Check if we have ANY bets for this event's teams
            teams_in_event = [event['home_team'], event['away_team']]
            relevant_bets = [b for b in bets if any(t in str(b['team']) or t in str(b['opponent']) or t in str(b['home_team']) for t in teams_in_event)]
            # Note: This string matching is weak. 'LAL' in 'Los Angeles Lakers'? No.
            
            # SKIP optimization for now to ensure correctness on small sample.
            # We will fetch props for this event regardless, then parse.
            
            print(f"   > Fetching Props for {ev_home} vs {event['away_team']} (Start: {commence_time})...")
            
            url_props = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/events/{ev_id}/odds"
            params_props = {
                "apiKey": API_KEY,
                "regions": REGIONS,
                "markets": MARKETS,
                "date": commence_time # DATA AT KICKOFF = CLOSING LINE
            }
            
            try:
                res_props = requests.get(url_props, params=params_props)
                res_props.raise_for_status()
                props_data = res_props.json()
                total_cost += 10
                
                # PARSE BOOKMAKERS
                # We want the average line? Or best line?
                # CLV usually compares against 'Pinnacle' or aggregate.
                # Let's take the first available bookmaker or average.
                
                # Build lookup: Player -> Stat -> Lines
                lines_map = {} # player_name -> { 'points': 25.5, ... }
                
                for bookie in props_data['data']['bookmakers']:
                    # Prefer 'fanduel' or 'draftkings' or 'pinnacle'?
                    if bookie['key'] in ['pinnacle', 'draftkings', 'fanduel', 'mgm']:
                        for market in bookie['markets']:
                            m_key = market['key'] # player_points
                            for outcome in market['outcomes']:
                                p_name = outcome['description']
                                line = outcome.get('point')
                                if not line: continue
                                
                                if p_name not in lines_map: lines_map[p_name] = {}
                                lines_map[p_name][m_key] = line
                        
                        # Break after one good bookie? Or average? 
                        # Let's use the first major bookie found as "Market consensus"
                        break 
                
                # UPDATE BETS
                # Iterate through all bets for this date and try to match player
                count_updated = 0
                for bet in bets:
                    p_name = bet['player_name']
                    # Fuzzy match player name?
                    # The-Odds-API: "LeBron James"
                    # DB: "LeBron James" (usually matches)
                    
                    if p_name in lines_map:
                        stat = bet['stat_category'] # PTS, REB, etc.
                        # Map stat to API market key
                        m_key = None
                        if stat in ['PTS', 'Points']: m_key = 'player_points'
                        elif stat in ['REB', 'Rebounds']: m_key = 'player_rebounds'
                        elif stat in ['AST', 'Assists']: m_key = 'player_assists'
                        elif stat in ['THREES', '3pm', 'FG3M', '3PM']: m_key = 'player_threes'
                        elif stat in ['STEALS', 'Steals', 'STL']: m_key = 'player_steals'
                        elif stat in ['BLOCKS', 'Blocks', 'BLK']: m_key = 'player_blocks'
                        elif stat in ['PRA', 'Pts+Reb+Ast']: m_key = 'player_points_rebounds_assists'
                        
                        if m_key and m_key in lines_map[p_name]:
                            clv_line = lines_map[p_name][m_key]
                            
                            # Update DB
                            c.execute('UPDATE bet_recommendations SET clv = ? WHERE id = ?', (clv_line, bet['id']))
                            count_updated += 1
                
                if count_updated > 0:
                    print(f"     ✅ Updated CLV for {count_updated} bets.")
                    
            except Exception as e:
                print(f"     ❌ Error fetching props: {e}")
            
            # Be nice to API limits
            time.sleep(0.5)

    conn.commit()
    conn.close()
    print("==================================================")
    print(f"✅ SYNC COMPLETE. Est Cost: {total_cost} credits.")

if __name__ == "__main__":
    sync_historical_odds()
