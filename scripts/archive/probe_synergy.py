import requests
import json

def probe_synergy(endpoint):
    url = f"https://stats.nba.com/stats/{endpoint}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.nba.com/',
        'Origin': 'https://www.nba.com',
        'Accept': 'application/json, text/plain, */*'
    }
    params = {
        'LeagueID': '00',
        'Season': '2025-26',  # Trying current season
        'PerMode': 'PerGame',
        'PlayerOrTeam': 'P',
        'PlayType': 'PRRollMan', # Guessing parameter value based on endpoint logic
        'TypeGrouping': 'offensive',
        'SeasonType': 'Regular Season'
    }
    
    # Some endpoints are just /stats/synergyplaytypes with PlayType param
    # Others are /stats/playerplaytypepickandrollrollman
    
    print(f"Probing {url}...")
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            # print(json.dumps(data, indent=2)[:500]) # First 500 chars
            result_count = len(data['resultSets'][0]['rowSet'])
            print(f"Success! Found {result_count} rows.")
            if result_count > 0:
                print("Headers:", data['resultSets'][0]['headers'])
                print("First Row:", data['resultSets'][0]['rowSet'][0])
            return True
        else:
            print("Failed.")
            print(resp.text[:200])
    except Exception as e:
        print(f"Error: {e}")
    return False

if __name__ == "__main__":
    # Attempt 1: Specific endpoint style
    probe_synergy("synergyplaytypes") 
    
    # Attempt 2: Explicit endpoints seen in docs
    # params would need adjustment potentially, removing 'PlayType' if it's in URL
    # But usually synergyplaytypes is the master endpoint
