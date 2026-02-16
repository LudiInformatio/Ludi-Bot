#!/usr/bin/env python3
"""
Hybrid WOWY Data Fetcher - 3-Tier Fallback Strategy

Tier 1: Direct NBA Stats API (Fast, but rate-limited)
Tier 2: Playwright Browser Scraping (Reliable, slower)
Tier 3: Cached/Manual fallback

Why not Beautiful Soup?
NBA.com uses client-side JavaScript rendering. Beautiful Soup can't execute
JavaScript, so it would only see empty HTML shells. We need either:
- Playwright (executes JS in real browser)
- Direct API calls (bypasses browser entirely)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import sqlite3
import time
import json
from datetime import datetime
from database import DB_PATH

# NBA Stats API endpoints (undocumented but stable)
NBA_STATS_API = {
    'lineups': {
        'endpoint': 'https://stats.nba.com/stats/leaguedashlineups',
        'params': {
            'DateFrom': '',
            'DateTo': '',
            'GameSegment': '',
            'GroupQuantity': 5,  # 5-man lineups
            'LastNGames': 0,
            'LeagueID': '00',
            'Location': '',
            'MeasureType': 'Advanced',
            'Month': 0,
            'OpponentTeamID': 0,
            'Outcome': '',
            'PORound': 0,
            'PaceAdjust': 'N',
            'PerMode': 'Totals',
            'Period': 0,
            'PlusMinus': 'N',
            'Rank': 'N',
            'Season': '2025-26',
            'SeasonSegment': '',
            'SeasonType': 'Regular Season',
            'ShotClockRange': '',
            'VsConference': '',
            'VsDivision': ''
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
            'Accept': 'application/json',
            'x-nba-stats-origin': 'stats',
            'x-nba-stats-token': 'true'
        }
    },
    'on_off': {
        'endpoint': 'https://stats.nba.com/stats/leaguedashplayeronoffdetails',
        'params': {
            'DateFrom': '',
            'DateTo': '',
            'GameSegment': '',
            'LastNGames': 0,
            'LeagueID': '00',
            'Location': '',
            'MeasureType': 'Advanced',
            'Month': 0,
            'OpponentTeamID': 0,
            'Outcome': '',
            'PORound': 0,
            'PaceAdjust': 'N',
            'PerMode': 'Totals',
            'Period': 0,
            'PlusMinus': 'N',
            'Rank': 'N',
            'Season': '2025-26',
            'SeasonSegment': '',
            'SeasonType': 'Regular Season',
            'TeamID': 0,
            'VsConference': '',
            'VsDivision': ''
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
            'Accept': 'application/json',
            'x-nba-stats-origin': 'stats',
            'x-nba-stats-token': 'true'
        }
    }
}

def fetch_api_tier1(data_type, date_str):
    """
    Tier 1: Direct API call to NBA Stats API
    Fast but may be rate-limited
    """
    config = NBA_STATS_API.get(data_type)
    if not config:
        return None, "Unknown data type"
    
    # Update params with date
    params = config['params'].copy()
    params['DateFrom'] = date_str.replace('-', '')  # Format: 01/17/2026 → 01172026
    params['DateTo'] = date_str.replace('-', '')
    
    try:
        print(f"  🚀 Tier 1 (API): {config['endpoint']}...", end=" ", flush=True)
        
        response = requests.get(
            config['endpoint'],
            params=params,
            headers=config['headers'],
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # NBA Stats API returns: {resultSets: [{headers: [...], rowSet: [...]}]}
            if 'resultSets' in data and data['resultSets']:
                result_set = data['resultSets'][0]
                headers = result_set.get('headers', [])
                rows = result_set.get('rowSet', [])
                
                print(f"✅ {len(rows)} records")
                
                # Convert to dict format
                records = []
                for row in rows:
                    record = dict(zip(headers, row))
                    record['game_date'] = date_str
                    record['created_at'] = datetime.now().isoformat()
                    records.append(record)
                
                return records, None
            else:
                print("❌ Empty response")
                return None, "Empty result set"
        else:
            print(f"❌ HTTP {response.status_code}")
            return None, f"HTTP {response.status_code}"
            
    except Exception as e:
        print(f"❌ {type(e).__name__}: {str(e)[:50]}")
        return None, str(e)

def fetch_browser_tier2(data_type, date_str):
    """
    Tier 2: Playwright browser scraping
    Slower but more reliable
    """
    print(f"  🌐 Tier 2 (Browser): Launching Playwright...")
    
    try:
        from playwright.sync_api import sync_playwright
        
        # Import scraping logic from ghost_wowy_scraper
        # (Would move the scraping function here in production)
        
        print("  ⚠️  Browser scraping not yet implemented (see ghost_wowy_scraper.py)")
        return None, "Not implemented"
        
    except ImportError:
        return None, "Playwright not available"
    except Exception as e:
        return None, str(e)

def fetch_wowy_data(data_type, date_str, use_tier2=True):
    """
    Hybrid fetcher with 3-tier fallback
    
    Args:
        data_type: 'lineups' or 'on_off'
        date_str: Date in YYYY-MM-DD format
        use_tier2: If True, fall back to browser scraping
    
    Returns:
        (records, error) tuple
    """
    print(f"\n📊 Fetching {data_type} for {date_str}:")
    
    # Tier 1: Try API first
    records, error = fetch_api_tier1(data_type, date_str)
    if records:
        return records, None
    
    print(f"  ⚠️  Tier 1 failed: {error}")
    
    # Tier 2: Fall back to browser
    if use_tier2:
        records, error = fetch_browser_tier2(data_type, date_str)
        if records:
            return records, None
        print(f"  ⚠️  Tier 2 failed: {error}")
    
    # Tier 3: No fallback (return error)
    return None, f"All tiers failed. Last error: {error}"

def main():
    """Test hybrid fetcher"""
    test_date = "2026-01-17"
    
    print(f"🎯 Hybrid WOWY Fetcher - 3-Tier Test")
    print(f"📅 Date: {test_date}")
    print("=" * 60)
    
    # Test lineups
    lineup_data, error = fetch_wowy_data('lineups', test_date, use_tier2=False)
    if lineup_data:
        print(f"\n✅ Lineups: {len(lineup_data)} records")
        # Show sample
        if lineup_data:
            sample = lineup_data[0]
            print(f"   Sample: {list(sample.keys())[:10]}")
    else:
        print(f"\n❌ Lineups failed: {error}")
    
    # Test on/off
    on_off_data, error = fetch_wowy_data('on_off', test_date, use_tier2=False)
    if on_off_data:
        print(f"\n✅ On/Off: {len(on_off_data)} records")
    else:
        print(f"\n❌ On/Off failed: {error}")
    
    print("\n" + "=" * 60)
    print("💡 Note: NBA API may require rate limiting (1-2 sec between calls)")

if __name__ == '__main__':
    main()
