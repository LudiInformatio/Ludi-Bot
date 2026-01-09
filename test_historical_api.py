import requests
import json
import os
import config # Loads env vars

API_KEY = os.getenv("ODDS_API_KEY")
SPORT = "basketball_nba"
DATE = "2026-01-07T12:00:00Z" # Mid-day to look for games

def test_historical_fetch():
    print(f"Checking historical events for {DATE}...")
    
    # 1. Get Events for that day
    # Historical parameters are different. We need to look at docs or try 'historical/sports/{sport}/events'
    # Actually, The-Odds-API docs say: 
    # GET /v4/historical/sports/{sport_key}/odds?date={date}&markets={markets}&regions={regions}
    
    url = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals", # Just basics to find matches first
        "date": DATE
    }
    
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()
        
        print(f"Status: {res.status_code}")
        print(f"Timestamp: {data['timestamp']}")
        print(f"Events found: {len(data['data'])}")
        
        for event in data['data']:
            print(f" - {event['home_team']} vs {event['away_team']} (ID: {event['id']})")
            
        # If we have events, let's look at player props for ONE of them
        if data['data']:
            event_id = data['data'][0]['id']
            print(f"\nChecking Player Props for {data['data'][0]['home_team']} (Event: {event_id})...")
            
            # Historical Player Props
            url_props = f"https://api.the-odds-api.com/v4/historical/sports/{SPORT}/events/{event_id}/odds"
            params_props = {
                "apiKey": API_KEY,
                "regions": "us",
                "markets": "player_points,player_rebounds,player_assists",
                "date": params['date'] # Same timestamp
            }
            
            res_props = requests.get(url_props, params=params_props)
            if res_props.status_code == 200:
                props_data = res_props.json()
                print(f"  Props Timestamp: {props_data['timestamp']}")
                print(f"  Bookmakers: {len(props_data['data']['bookmakers'])}")
            else:
                print(f"  Failed: {res_props.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if not API_KEY:
        print("❌ No API Key found.")
    else:
        test_historical_fetch()
