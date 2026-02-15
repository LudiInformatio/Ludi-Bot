import requests
import json
import time

PLAYTYPES = [
    'Isolation',
    'PRBallHandler',
    'PRRollMan',
    'Postup',
    'Spotup',
    'Transition',
    'Cut',
    'OffRebound' # Putbacks
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.nba.com/',
    'Origin': 'https://www.nba.com',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive'
}

def fetch_synergy(playtype):
    url = "https://stats.nba.com/stats/synergyplaytypes"
    params = {
        'LeagueID': '00',
        'Season': '2025-26',
        'PerMode': 'PerGame',
        'PlayerOrTeam': 'P',
        'PlayType': playtype,
        'TypeGrouping': 'offensive',
        'SeasonType': 'Regular Season'
    }
    
    print(f"[{playtype}] Fetching...")
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            rows = data['resultSets'][0]['rowSet']
            print(f"[{playtype}] ✅ Success: {len(rows)} players found.")
            # Print top 3 by poss fraction (usually index 6 or 7) - check headers?
            # headers: [PlayerID, PlayerName, TeamID, TeamNameAbbreviation, GP, Poss, Time, Points, PPP, Rank, Rating]
            # Just print first row example
            if rows:
                print(f"   Example: {rows[0][1]} - {rows[0][7]} pts/game")
            return len(rows) > 0
        else:
            print(f"[{playtype}] ❌ Failed: {resp.status_code}")
    except Exception as e:
        print(f"[{playtype}] ⚠️ Error: {e}")
    return False

def run():
    success_count = 0
    for pt in PLAYTYPES:
        if fetch_synergy(pt):
            success_count += 1
        time.sleep(2) # Respect rate limits
    
    print(f"\nSummary: {success_count}/{len(PLAYTYPES)} endpoints reachable.")

if __name__ == "__main__":
    run()
