# ARCHIVED: 2026-03-03 — Replaced by sync_bdl_season_averages.py (BDL V2, Feb 22 2026)
#!/usr/bin/env python3
"""
Synergy Playtype Scraper (Ghost Protocol)

Scrapes NBA.com Synergy playtype data using visible browser mode
to bypass WAF protection. Supports all 8 offensive playtypes.

Usage:
    python3 scripts/sync_synergy_playtypes.py --all
    python3 scripts/sync_synergy_playtypes.py --playtype isolation
"""

import asyncio
import sqlite3
import argparse
import time
import re
import sys
import os
from datetime import datetime

# Add project root to path FIRST
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from utils.browser_utils_async import close_popups_async, simulate_human_interaction_async
from utils.player_id_resolver import normalize_player_name

# Playtype configurations
PLAYTYPES = {
    # Original Synergy Playtypes
    'isolation': {'url': 'isolation', 'tag': 'ISO'},
    'transition': {'url': 'transition', 'tag': 'TRANSITION'},
    'ball-handler': {'url': 'ball-handler', 'tag': 'PR_BALL_HANDLER'},
    'roll-man': {'url': 'roll-man', 'tag': 'PR_ROLL_MAN'},
    'post-up': {'url': 'playtype-post-up', 'tag': 'POST_UP'},
    'spot-up': {'url': 'spot-up', 'tag': 'SPOT_UP'},
    'cut': {'url': 'cut', 'tag': 'CUT'},
    'putbacks': {'url': 'putbacks', 'tag': 'PUTBACK'},
    
    # New Tracking Data Endpoints
    'drives': {'url': 'drives', 'tag': 'DRIVES', 'table': 'player_drives'},
    'touches': {'url': 'touches', 'tag': 'TOUCHES', 'table': 'player_touches'},
    'speed': {'url': 'speed-distance', 'tag': 'SPEED', 'table': 'player_speed'},
    'defense': {'url': 'defense-dash-overall', 'tag': 'DEFENSE', 'table': 'player_defense'}
}

DEFENSIVE_PLAYTYPES = {
    'def-isolation': {'url': 'isolation?TypeGrouping=Defensive', 'tag': 'ISO', 'defensive': True},
    'def-ball-handler': {'url': 'ball-handler?TypeGrouping=Defensive', 'tag': 'PR_BALL_HANDLER', 'defensive': True},
    'def-roll-man': {'url': 'roll-man?TypeGrouping=Defensive', 'tag': 'PR_ROLL_MAN', 'defensive': True},
    'def-spot-up': {'url': 'spot-up?TypeGrouping=Defensive', 'tag': 'SPOT_UP', 'defensive': True},
    'def-post-up': {'url': 'playtype-post-up?TypeGrouping=Defensive', 'tag': 'POST_UP', 'defensive': True},
    'def-cut': {'url': 'cut?TypeGrouping=Defensive', 'tag': 'CUT', 'defensive': True},
}

DB_PATH = 'ludi.db'


def ensure_defensive_synergy_table():
    """Create defensive synergy table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS player_defensive_synergy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            team_abbr TEXT,
            season TEXT DEFAULT '2025-26',
            playtype TEXT NOT NULL,
            games_played INTEGER,
            poss_per_game REAL,
            freq_pct REAL,
            ppp_allowed REAL,
            fg_pct_allowed REAL,
            percentile INTEGER,
            synced_at TEXT,
            UNIQUE(player_name, playtype, season)
        )
    """)
    conn.commit()
    conn.close()

async def scrape_playtype(page, playtype_key: str, season: str = '2025-26'):
    """Scrape a single playtype page and return player data."""
    config = PLAYTYPES[playtype_key]
    url = f"https://www.nba.com/stats/players/{config['url']}"
    
    print(f"[{config['tag']}] Navigating to {url}...")
    
    try:
        # Use domcontentloaded instead of networkidle
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await close_popups_async(page)
        await simulate_human_interaction_async(page)
        
        # Wait for table with retries
        for attempt in range(3):
            try:
                await page.wait_for_selector('table.Crom_table__p1iZz', timeout=15000)
                break
            except Exception:
                print(f"[{config['tag']}] Waiting for table (attempt {attempt + 1}/3)...")
                await asyncio.sleep(3)
        
        # Additional wait for dynamic data
        await asyncio.sleep(2)
        
        # Try to click "All" in pagination to get all rows
        try:
            # Find the dropdown that contains the "All" option (page selector)
            # It's usually the last dropdown, but we'll search for the one with "All"
            await page.evaluate("""
                () => {
                    const selects = document.querySelectorAll('select.DropDown_select__4pIg9');
                    
                    // Find the dropdown that has "All" option
                    let pageSelector = null;
                    for (let i = 0; i < selects.length; i++) {
                        const options = Array.from(selects[i].options);
                        if (options.some(opt => opt.text === 'All')) {
                            pageSelector = selects[i];
                            break;
                        }
                    }
                    
                    if (pageSelector) {
                        pageSelector.value = "-1";
                        pageSelector.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
            """)
            await asyncio.sleep(6)  # Wait longer for table to reload with ALL rows (500+)
            print(f"[{config['tag']}] Expanded to show all rows")
        except Exception as e:
            print(f"[{config['tag']}] ⚠️ Could not expand pagination: {e}")
        
        # Get all table rows
        rows = await page.query_selector_all('table.Crom_table__p1iZz tbody tr')
        
        if not rows:
            print(f"[{config['tag']}] ❌ No data rows found")
            return []
        
        players = []
        for row in rows:
            cells = await row.query_selector_all('td')
            # Tracking pages often have >20 columns, Synergy usually 17
            if len(cells) < 10:
                continue
            
            try:
                # Extract cell text
                ct = []
                for cell in cells:
                    text = await cell.inner_text()
                    ct.append(text.strip())
                
                player = {}
                
                # Parsing logic based on tag type
                if config['tag'] == 'DRIVES':
                    # PLAYER, TEAM, GP, W, L, MIN, DRIVES, FGM, FGA, FG%, FTM, FTA, FT%, PTS, PTS%, PASS, PASS%, AST, AST%, TO, TOV%, PF, PF%
                    # Before inserting, normalize the name
                    raw_player_name = ct[0]
                    player_name = normalize_player_name(raw_player_name)
                    player = {
                        'player_name': player_name, 'team_abbr': ct[1], 'season': season,
                        'gp': parse_int(ct[2]), 'min_per_game': parse_float(ct[5]),
                        'drives_per_game': parse_float(ct[6]), 'fgm_per_game': parse_float(ct[7]),
                        'fga_per_game': parse_float(ct[8]), 'fg_pct': parse_float(ct[9]),
                        'pts_per_game': parse_float(ct[13]), 'pts_pct': parse_float(ct[14]),
                        'pass_per_game': parse_float(ct[15]), 'pass_pct': parse_float(ct[16]),
                        'ast_per_game': parse_float(ct[17]), 'ast_pct': parse_float(ct[18]),
                        'tov_per_game': parse_float(ct[19]), 'tov_pct': parse_float(ct[20]),
                        'pf_per_game': parse_float(ct[21]), 'pf_pct': parse_float(ct[22])
                    }
                    
                elif config['tag'] == 'TOUCHES':
                    # PLAYER, TEAM, GP, W, L, MIN, PTS, TOUCHES, FRONT CT, TIME POSS, SEC/TOUCH, DRIB/TOUCH, PTS/TOUCH, ELBOW, POST, PAINT, PTS/ELBOW, PTS/POST, PTS/PAINT
                    # Before inserting, normalize the name
                    raw_player_name = ct[0]
                    player_name = normalize_player_name(raw_player_name)
                    player = {
                        'player_name': player_name, 'team_abbr': ct[1], 'season': season,
                        'gp': parse_int(ct[2]), 'min_per_game': parse_float(ct[5]),
                        'pts_per_game': parse_float(ct[6]), 'touches_per_game': parse_float(ct[7]),
                        'front_ct_touches_per_game': parse_float(ct[8]), 'time_of_poss_per_game': parse_float(ct[9]),
                        'avg_sec_per_touch': parse_float(ct[10]), 'avg_drib_per_touch': parse_float(ct[11]),
                        'pts_per_touch': parse_float(ct[12]), 'elbow_touches_per_game': parse_float(ct[13]),
                        'post_ups_per_game': parse_float(ct[14]), 'paint_touches_per_game': parse_float(ct[15]),
                        'pts_per_elbow_touch': parse_float(ct[16]), 'pts_per_post_touch': parse_float(ct[17]),
                        'pts_per_paint_touch': parse_float(ct[18])
                    }
                    
                elif config['tag'] == 'SPEED':
                    # PLAYER, TEAM, GP, W, L, MIN, DIST FT, DIST MI, DIST OFF, DIST DEF, AVG SPD, AVG OFF, AVG DEF
                    # Before inserting, normalize the name
                    raw_player_name = ct[0]
                    player_name = normalize_player_name(raw_player_name)
                    player = {
                        'player_name': player_name, 'team_abbr': ct[1], 'season': season,
                        'gp': parse_int(ct[2]), 'min_per_game': parse_float(ct[5]),
                        'dist_feet_per_game': parse_float(ct[6]), 'dist_miles_per_game': parse_float(ct[7]),
                        'dist_miles_off': parse_float(ct[8]), 'dist_miles_def': parse_float(ct[9]),
                        'avg_speed': parse_float(ct[10]), 'avg_speed_off': parse_float(ct[11]),
                        'avg_speed_def': parse_float(ct[12])
                    }
                    
                elif config['tag'] == 'DEFENSE':
                    # PLAYER, TEAM, AGE, POS, GP, G, FREQ%, DFGM, DFGA, DFG%, FG%, DIFF%
                    # Before inserting, normalize the name
                    raw_player_name = ct[0]
                    player_name = normalize_player_name(raw_player_name)
                    player = {
                        'player_name': player_name, 'team_abbr': ct[1], 'season': season,
                        'age': parse_int(ct[2]), 'position': ct[3],
                        'gp': parse_int(ct[4]), 'freq_pct': parse_percent(ct[6]),
                        'dfgm': parse_float(ct[7]), 'dfga': parse_float(ct[8]),
                        'dfg_pct': parse_float(ct[9]), 'fg_pct': parse_float(ct[10]),
                        'diff_pct': parse_float(ct[11])
                    }
                    
                else:
                    # Original Synergy Logic
                    # PLAYER | TEAM | GP | POSS | FREQ% | PPP | PTS | ...
                    # Before inserting, normalize the name
                    raw_player_name = ct[0]
                    player_name = normalize_player_name(raw_player_name)
                    player = {
                        'player_name': player_name,
                        'team_abbr': ct[1] if len(ct) > 1 else None,
                        'games_played': parse_int(ct[2]),
                        'poss_per_game': parse_float(ct[3]),
                        'freq_pct': parse_percent(ct[4]),
                        'ppp': parse_float(ct[5]),
                        'pts_per_game': parse_float(ct[6]),
                        'fgm': parse_float(ct[7]),
                        'fga': parse_float(ct[8]),
                        'fg_pct': parse_float(ct[9]),
                        'efg_pct': parse_float(ct[10]),
                        'ft_freq_pct': parse_percent(ct[11]),
                        'tov_freq_pct': parse_percent(ct[12]),
                        'sf_freq_pct': parse_percent(ct[13]),
                        'and_one_freq_pct': parse_percent(ct[14]),
                        'score_freq_pct': parse_percent(ct[15]),
                        'percentile': parse_int(ct[16]),
                        'playtype': config['tag'],
                        'season': season,
                        'defensive': config.get('defensive', False)
                    }
                
                players.append(player)
                
            except Exception as e:
                print(f"[{config['tag']}] ⚠️ Error parsing row: {e}")
                continue
        
        print(f"[{config['tag']}] ✅ Scraped {len(players)} players")
        return players
        
    except Exception as e:
        print(f"[{config['tag']}] ❌ Error: {e}")
        return []


def parse_float(text: str) -> float:
    """Parse float from text, handling percentages and dashes."""
    if not text or text == '-' or text == '':
        return 0.0
    # Remove % sign
    text = text.replace('%', '').strip()
    try:
        return float(text)
    except (ValueError, TypeError):
        return 0.0


def parse_percent(text: str) -> float:
    """
    Parse percentage-like values to canonical 0-100 scale.

    If source includes '%' we trust it is already percent-scaled.
    If source has no '%' and is a strict fraction (0-1), convert to 0-100.
    """
    if not text or text == '-' or text == '':
        return 0.0
    has_pct = '%' in text
    val = parse_float(text)
    if has_pct:
        return val
    if 0 < val < 1.0:
        return val * 100.0
    return val


def parse_int(text: str) -> int:
    """Parse integer from text."""
    if not text or text == '-' or text == '':
        return 0
    # Extract just digits
    match = re.search(r'\d+', text)
    if match:
        return int(match.group())
    return 0


def save_to_database(players: list):
    """Save player data to SQLite database."""
    if not players:
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    saved = 0
    for p in players:
        try:
            # Determine which table to save to based on keys
            if p.get('defensive'):
                cursor.execute("""
                    INSERT INTO player_defensive_synergy (
                        player_name, team_abbr, season, playtype,
                        games_played, poss_per_game, freq_pct, ppp_allowed,
                        fg_pct_allowed, percentile, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(player_name, playtype, season) DO UPDATE SET
                        team_abbr=excluded.team_abbr,
                        games_played=excluded.games_played,
                        poss_per_game=excluded.poss_per_game,
                        freq_pct=excluded.freq_pct,
                        ppp_allowed=excluded.ppp_allowed,
                        fg_pct_allowed=excluded.fg_pct_allowed,
                        percentile=excluded.percentile,
                        synced_at=excluded.synced_at
                """, (
                    p['player_name'], p['team_abbr'], p['season'], p['playtype'],
                    p['games_played'], p['poss_per_game'], p['freq_pct'], p['ppp'],
                    p['fg_pct'], p['percentile'], datetime.now().isoformat()
                ))
            elif 'drives_per_game' in p:
                cursor.execute("""
                    INSERT OR REPLACE INTO player_drives (
                        player_name, team_abbr, season, gp, min_per_game,
                        drives_per_game, fgm_per_game, fga_per_game, fg_pct,
                        pts_per_game, pts_pct, pass_per_game, pass_pct,
                        ast_per_game, ast_pct, tov_per_game, tov_pct,
                        pf_per_game, pf_pct, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p['player_name'], p['team_abbr'], p['season'], p['gp'], p['min_per_game'],
                    p['drives_per_game'], p['fgm_per_game'], p['fga_per_game'], p['fg_pct'],
                    p['pts_per_game'], p['pts_pct'], p['pass_per_game'], p['pass_pct'],
                    p['ast_per_game'], p['ast_pct'], p['tov_per_game'], p['tov_pct'],
                    p['pf_per_game'], p['pf_pct'], datetime.now().isoformat()
                ))
            
            elif 'touches_per_game' in p:
                cursor.execute("""
                    INSERT OR REPLACE INTO player_touches (
                        player_name, team_abbr, season, gp, min_per_game,
                        pts_per_game, touches_per_game, front_ct_touches_per_game,
                        time_of_poss_per_game, avg_sec_per_touch, avg_drib_per_touch,
                        pts_per_touch, elbow_touches_per_game, post_ups_per_game,
                        paint_touches_per_game, pts_per_elbow_touch, pts_per_post_touch,
                        pts_per_paint_touch, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p['player_name'], p['team_abbr'], p['season'], p['gp'], p['min_per_game'],
                    p['pts_per_game'], p['touches_per_game'], p['front_ct_touches_per_game'],
                    p['time_of_poss_per_game'], p['avg_sec_per_touch'], p['avg_drib_per_touch'],
                    p['pts_per_touch'], p['elbow_touches_per_game'], p['post_ups_per_game'],
                    p['paint_touches_per_game'], p['pts_per_elbow_touch'], p['pts_per_post_touch'],
                    p['pts_per_paint_touch'], datetime.now().isoformat()
                ))
            
            elif 'dist_miles_per_game' in p:
                cursor.execute("""
                    INSERT OR REPLACE INTO player_speed (
                        player_name, team_abbr, season, gp, min_per_game,
                        dist_feet_per_game, dist_miles_per_game, dist_miles_off,
                        dist_miles_def, avg_speed, avg_speed_off, avg_speed_def,
                        synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p['player_name'], p['team_abbr'], p['season'], p['gp'], p['min_per_game'],
                    p['dist_feet_per_game'], p['dist_miles_per_game'], p['dist_miles_off'],
                    p['dist_miles_def'], p['avg_speed'], p['avg_speed_off'], p['avg_speed_def'],
                    datetime.now().isoformat()
                ))

            elif 'diff_pct' in p:
                cursor.execute("""
                    INSERT OR REPLACE INTO player_defense (
                        player_name, team_abbr, season, age, position, gp,
                        freq_pct, dfgm, dfga, dfg_pct, fg_pct, diff_pct,
                        synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p['player_name'], p['team_abbr'], p['season'], p['age'], p['position'], p['gp'],
                    p['freq_pct'], p['dfgm'], p['dfga'], p['dfg_pct'], p['fg_pct'], p['diff_pct'],
                    datetime.now().isoformat()
                ))
            
            else:
                # Default: Synergy Playtype
                # HYBRID UPSERT: Preserve BDL core stats (ppp, poss_per_game, fg_pct, efg_pct, fgm, fga)
                # Only update Playwright-provided fields (ft_freq_pct, tov_freq_pct, sf_freq_pct,
                # and_one_freq_pct, score_freq_pct, percentile)
                cursor.execute("""
                    INSERT INTO player_synergy_playtypes (
                        player_name, team_abbr, season, playtype,
                        games_played, poss_per_game, freq_pct, ppp, pts_per_game,
                        fgm, fga, fg_pct, efg_pct,
                        ft_freq_pct, tov_freq_pct, sf_freq_pct, and_one_freq_pct,
                        score_freq_pct, percentile, synced_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(player_name, season, playtype) DO UPDATE SET
                        team_abbr=excluded.team_abbr,
                        games_played=excluded.games_played,
                        ft_freq_pct=excluded.ft_freq_pct,
                        tov_freq_pct=excluded.tov_freq_pct,
                        sf_freq_pct=excluded.sf_freq_pct,
                        and_one_freq_pct=excluded.and_one_freq_pct,
                        score_freq_pct=excluded.score_freq_pct,
                        percentile=excluded.percentile,
                        synced_at=excluded.synced_at
                        -- DO NOT UPDATE: ppp, poss_per_game, freq_pct, pts_per_game,
                        --                fgm, fga, fg_pct, efg_pct (preserve BDL core stats)
                """, (
                    p['player_name'], p['team_abbr'], p['season'], p['playtype'],
                    p['games_played'], p['poss_per_game'], p['freq_pct'], p['ppp'], p['pts_per_game'],
                    p['fgm'], p['fga'], p['fg_pct'], p['efg_pct'],
                    p['ft_freq_pct'], p['tov_freq_pct'], p['sf_freq_pct'], p['and_one_freq_pct'],
                    p['score_freq_pct'], p['percentile'], datetime.now().isoformat()
                ))
                
            saved += 1
        except Exception as e:
            print(f"⚠️ Error saving {p['player_name']}: {e}")
    
    conn.commit()
    conn.close()
    return saved


async def run_scraper(playtypes_to_scrape: list, season: str = '2025-26'):
    """Main scraper entry point."""
    print(f"\n{'='*60}")
    print(f"SYNERGY PLAYTYPE SYNC - Ghost Protocol")
    print(f"Season: {season}")
    print(f"Playtypes: {', '.join(playtypes_to_scrape)}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        # Launch visible browser (Ghost Protocol)
        browser = await p.chromium.launch(
            headless=False,  # Visible mode bypasses WAF
            slow_mo=100
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        total_players = 0
        
        for playtype_key in playtypes_to_scrape:
            if playtype_key not in PLAYTYPES:
                print(f"⚠️ Unknown playtype: {playtype_key}")
                continue
            
            players = await scrape_playtype(page, playtype_key, season)
            
            if players:
                saved = save_to_database(players)
                total_players += saved
                print(f"   → Saved {saved} records to database")
            
            # Human-like delay between pages
            await asyncio.sleep(3)
        
        await browser.close()
    
    print(f"\n{'='*60}")
    print(f"SYNC COMPLETE")
    print(f"Total records: {total_players}")
    print(f"{'='*60}")
    
    return total_players


def main():
    parser = argparse.ArgumentParser(description='Sync NBA Synergy playtype data')
    parser.add_argument('--all', action='store_true', help='Scrape all playtypes')
    parser.add_argument('--playtype', type=str, help='Specific playtype to scrape')
    parser.add_argument('--defensive', action='store_true', help='Scrape defensive Synergy playtypes')
    parser.add_argument('--season', type=str, default='2025-26', help='NBA season (e.g., 2025-26)')
    
    args = parser.parse_args()
    ensure_defensive_synergy_table()
    
    if args.all and args.defensive:
        playtypes = list(DEFENSIVE_PLAYTYPES.keys())
        PLAYTYPES.update(DEFENSIVE_PLAYTYPES)
    elif args.all:
        playtypes = list(PLAYTYPES.keys())
    elif args.playtype:
        if args.defensive:
            PLAYTYPES.update(DEFENSIVE_PLAYTYPES)
        playtypes = [args.playtype]
    else:
        print("Usage: --all or --playtype <name>")
        available = list(PLAYTYPES.keys()) + list(DEFENSIVE_PLAYTYPES.keys())
        print(f"Available: {available}")
        return
    
    asyncio.run(run_scraper(playtypes, args.season))


if __name__ == '__main__':
    main()
