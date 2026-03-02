#!/usr/bin/env python3
"""
Daily Referee Assignment Sync - "Day Forward" Intelligence System

Captures referee crews from official.nba.com/referee-assignments/ and:
1. Populates games.referee_crew for today's slate
2. Auto-registers new referees to referee_profiles
3. Enables learning engines (learn_daily_trends.py, analyze_star_bias.py)

Designed for GitHub Actions automation (9:30 AM ET daily).
"""

import argparse
import sqlite3
import pandas as pd
import re
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple
from io import StringIO
import sys
import os

# Add project root to path to allow imports from utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.mappings import resolve_team_abbr
from utils.browser_utils import close_popups, simulate_human_interaction


def _parse_ref_name(raw: str) -> tuple:
    """
    Split 'Josh Tiven (#58)' → ('Josh Tiven', 58).
    Returns (clean_name, badge_number). badge_number is None if no # present.
    """
    m = re.search(r'\(#(\d+)\)\s*$', raw.strip())
    if m:
        badge = int(m.group(1))
        name = raw[:m.start()].strip()
        return name, badge
    return raw.strip(), None

class DailyRefereeSync:
    """Daily capture system for referee intelligence."""
    
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        
        # Ensure today's games exist before any referee operations
        self._ensure_todays_games()
    
    def _ensure_todays_games(self):
        """Auto-populate today's games if missing. Delegates to Module G which
        handles game insertion + sync_canonical_games() correctly."""
        print("   🔍 Checking today's games in database...")

        if not self._check_todays_games_exist():
            print("   📡 No games found — delegating to Module G populate...")
            try:
                from module_g import LudiRefEngine
                # LudiRefEngine.__init__ calls _ensure_todays_games internally,
                # but we just need _populate_todays_games directly
                engine = LudiRefEngine.__new__(LudiRefEngine)
                engine.db_path = self.db_path
                engine.LEAGUE_AVG_FOULS = 12.5
                engine.daily_assignments = {}
                engine._populate_todays_games()
                print("   ✅ Games populated via Module G")
            except Exception as e:
                print(f"   ⚠️ Module G populate failed: {e}")
        else:
            print("   ✅ Today's games already exist")

    def _check_todays_games_exist(self) -> bool:
        """Check if any games exist for today's date"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) FROM games WHERE date = ?", (today,))
            count = cursor.fetchone()[0]
            
            conn.close()
            return count > 0
            
        except Exception as e:
            print(f"   ⚠️ Error checking games: {e}")
            return False

    def scrape_assignments(self) -> Dict[str, List[str]]:
        """
        Scrape today's referee assignments from NBA official site.
        Uses Playwright to handle dynamic JS rendering.

        DB-FIRST: If games.referee_crew is already populated for today (e.g., morning brief
        already scraped via LudiRefEngine.build_ref_database()), return immediately and skip
        Playwright entirely. Mirrors the caching pattern in module_g.build_ref_database().

        Returns:
            dict: {team_abbr: [ref1, ref2, ref3]}
        """
        # ── DB-first cache check ────────────────────────────────────────────────
        today_str = date.today().strftime('%Y-%m-%d')
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute(
                "SELECT home_team, referee_crew FROM games "
                "WHERE date = ? AND referee_crew IS NOT NULL AND referee_crew != ''",
                (today_str,)
            ).fetchall()
            conn.close()
            if rows:
                result = {home: [r.strip() for r in crew.split(',')]
                          for home, crew in rows}
                print(f"   [SYNC] ✅ {len(result)} ref crew(s) already in DB — skipping Playwright")
                return result
        except Exception as e:
            print(f"   [SYNC] DB-first check failed ({e}), falling through to scraper")

        url = "https://official.nba.com/referee-assignments/"

        try:
            from playwright.sync_api import sync_playwright

            print(f"   [SYNC] Launching Playwright for {url}...")
            with sync_playwright() as p:
                # User requested visible browser
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                try:
                    # Retry logic for navigation
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            print(f"   [SYNC] Attempt {attempt+1}: Navigating to {url}...")
                            page.goto(url, wait_until="domcontentloaded", timeout=60000)
                            close_popups(page)  # now handles consent buttons via browser_utils
                            simulate_human_interaction(page)
                            break
                        except Exception as e:
                            if attempt == max_retries - 1: raise e
                            print(f"   ⚠️ Navigation attempt {attempt+1} failed, retrying...")
                    
                    
                    # FIX 2: Skip date toggle when fetching today's date
                    # The page loads today's assignments by default at 9 AM
                    today_str = date.today().strftime('%Y-%m-%d')
                    target_date = datetime.now().strftime('%Y-%m-%d')
                    
                    if target_date and target_date != today_str:
                        # Only toggle date when fetching a non-today date
                        try:
                            # Step 1: Yesterday
                            page.wait_for_selector('button.dropdown-toggle', timeout=5000)
                            page.click('button.dropdown-toggle', force=True)
                            
                            page.wait_for_selector('input#ref-date', timeout=10000)
                            page.fill('input#ref-date', yesterday_str)
                            page.click('input#date-filter', force=True)
                            page.wait_for_timeout(1000)
                            
                            # Step 2: Today (Target)
                            # Re-open dropdown
                            try:
                                 page.click('button.dropdown-toggle', force=True)
                            except Exception as e:
                                print(f"[TAG] Context: {e}")
                                pass
                                
                            page.fill('input#ref-date', today_str)
                            page.click('input#date-filter', force=True)
                        except Exception as e:
                             print(f"   ⚠️ Date toggle issue: {e}")
                    else:
                        print(f"   [SYNC] Today's date — skipping date toggle, page loads current assignments")

                    # Wait for table to populate
                    print("   [SYNC] Waiting for table rows...")
                    try:
                        page.wait_for_selector(".nba-refs-content table tbody tr", timeout=30000)
                    except Exception as e:
                        print(f"[TAG] Context: {e}")
                        print("   ⚠️ Timeout waiting for table rows (page might be empty or slow)")
                    
                    content = page.content()
                except Exception as e:
                    print(f"   ❌ Browser Navigation Error: {e}")
                    browser.close()
                    return {}
                
                browser.close()

            # Parse Tables
            dfs = pd.read_html(StringIO(content))
            
            if not dfs:
                print("   ⚠️ No tables found on page.")
                return {}

            df = dfs[0]
            df.columns = [c.upper() for c in df.columns]
            
            assignments = {}
            print(f"   [SYNC] Parsing {len(df)} rows from table...")
            for _, row in df.iterrows():
                game_str = str(row.get('GAME', ''))
                
                if '@' in game_str:
                    parts = game_str.split('@')
                    if len(parts) > 1:
                        raw_home = parts[1].strip()
                        
                        if '(' in raw_home:
                            raw_home = raw_home.split('(')[0].strip()
                            
                        home_abbr = resolve_team_abbr(raw_home)
                        print(f"   [SYNC] Found Game: {game_str} | Raw Home: '{raw_home}' | Resolved: '{home_abbr}'")
                        
                        crew = []
                        for col in df.columns:
                            if 'CHIEF' in col or 'REFEREE' in col or 'UMPIRE' in col:
                                if pd.notna(row[col]):
                                    raw_ref = str(row[col]).strip()
                                    # Keep raw ref with badge for now, will parse in run()
                                    if raw_ref:
                                        crew.append(raw_ref)
                        
                        if home_abbr and crew:
                            assignments[home_abbr] = crew
            
            return assignments
            
        except ImportError:
            print("   ❌ Playwright not installed. Run: pip install playwright && playwright install")
            return {}
        except Exception as e:
            print(f"   ❌ Scrape failed: {e}")
            return {}
    

    
    def get_todays_games(self) -> List[Tuple[int, str, str]]:
        """
        Query today's games from database.
        
        Returns:
            list: [(game_id, home_team, away_team), ...] 
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        # Fallback to test date if needed during dev (can remove later)
        # today = '2026-01-14' # Uncomment to test with last known date if wanted
        
        cursor.execute("""
            SELECT game_id, home_team, away_team
            FROM games
            WHERE date = ?
        """, (today,))
        
        games = cursor.fetchall()
        conn.close()
        
        return games
    
    def update_game_crew(self, game_id: str, crew_list: List[str], dry_run=False):
        """
        Populate games.referee_crew column.
        
        Args:
            game_id: Database game_id
            crew_list: List of referee names
            dry_run: If True, print but don't execute
        """
        crew_string = ', '.join(crew_list)
        
        if dry_run:
            print(f"   [DRY RUN] Would update game {game_id}: {crew_string}")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE games
            SET referee_crew = ?
            WHERE game_id = ?
        """, (crew_string, game_id))

        # Also write to crosswalk — keyed by (date, home_team), not game_id
        # Ensures BDL fallback game rows can find ref data even with NULL referee_crew
        cw_row = conn.execute(
            "SELECT date, home_team FROM games WHERE game_id = ?", (game_id,)
        ).fetchone()
        if cw_row:
            conn.execute(
                """INSERT OR REPLACE INTO referee_game_assignments
                   (game_date, home_team, crew, source)
                   VALUES (?, ?, ?, 'nba_official')""",
                (cw_row[0], cw_row[1], crew_string)
            )

        conn.commit()
        conn.close()

        print(f"✅ Updated game {game_id}: {crew_string}")
    
    def register_new_referee(self, ref_name: str, badge_number: int = None, dry_run=False):
        """
        Auto-register new referee if not in database.
        
        Uses neutral baseline (per-ref average: 12.5):
        - avg_fouls_per_game: 12.5 (verified per-ref average: 37.5 game total / 3)
        - avg_pace_impact: 1.0 (neutral)
        - style: 'NEUTRAL'
        - data_source: 'daily_capture'
        
        Args:
            ref_name: Clean referee name (without badge number)
            badge_number: NBA badge number if available
            dry_run: If True, print but don't execute
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if ref exists by badge_number first, then by name
        if badge_number:
            cursor.execute("""
                SELECT referee_id FROM referee_profiles 
                WHERE badge_number = ?
            """, (badge_number,))
            if cursor.fetchone():
                conn.close()
                return  # Already exists by badge
        
        cursor.execute("""
            SELECT referee_id FROM referee_profiles 
            WHERE referee_name = ?
        """, (ref_name,))
        
        if cursor.fetchone():
            conn.close()
            return  # Already exists by name
        
        if dry_run:
            print(f"   [DRY RUN] Would register new ref: {ref_name} (badge: {badge_number})")
            conn.close()
            return
        
        # Insert with neutral baseline (per-ref average: 12.5)
        cursor.execute("""
            INSERT INTO referee_profiles (
                referee_name, 
                badge_number,
                avg_fouls_per_game, 
                avg_pace_impact, 
                style, 
                data_source,
                last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ref_name, badge_number, 12.5, 1.0, 'NEUTRAL', 'daily_capture', datetime.now()))
        
        conn.commit()
        conn.close()
        
        print(f"🆕 Registered new referee: {ref_name} (badge: {badge_number})")
    
    def run(self, dry_run=False):
        """
        Main orchestration: scrape, match, update.
        """
        print("🦓 Daily Referee Sync - Day Forward Intelligence")
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"🧪 Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print()
        
        # Step 1: Scrape assignments
        print("📡 Scraping official.nba.com/referee-assignments/...")
        assignments = self.scrape_assignments()
        print(f"✅ Found assignments for {len(assignments)} teams\n")
        
        # Step 2: Get today's games
        print("🔍 Querying today's games from database...")
        games = self.get_todays_games()
        print(f"✅ Found {len(games)} games scheduled today ({datetime.now().strftime('%Y-%m-%d')})\n")
        
        # Step 3: Match and update
        print("🔗 Matching crews to games...")
        matched = 0
        
        for game_id, home_team, away_team in games:
            crew = assignments.get(home_team)
            
            if crew:
                self.update_game_crew(game_id, crew, dry_run)
                
                # Auto-register new refs (parse badge numbers from names)
                for raw_ref in crew:
                    clean_name, badge_number = _parse_ref_name(raw_ref)
                    self.register_new_referee(clean_name, badge_number, dry_run)
                
                matched += 1
            else:
                print(f"⚠️  No crew found for {home_team} (game {game_id})")
        
        print()
        print(f"✅ Summary: {matched}/{len(games)} games updated")
        
        # --- PERPLEXITY FALLBACK — delegate to module_g (single authority) ---
        if matched == 0 and len(games) > 0 and not dry_run:
            print("\n⚠️  Playwright returned 0 assignments — delegating to Module G fallback...")
            try:
                from module_g import LudiRefEngine
                engine = LudiRefEngine.__new__(LudiRefEngine)
                engine.db_path = self.db_path
                engine.LEAGUE_AVG_FOULS = 12.5
                engine.daily_assignments = {}
                result = engine.build_ref_database()
                matched = len(result)
                if matched:
                    print(f"   ✅ Module G fallback populated {matched} game crew(s)")
            except Exception as e:
                print(f"   ⚠️ Module G fallback failed: {e}")
        # ---------------------------------------------------------------

        # --- VALIDATION GUARDRAIL ---
        if not dry_run and len(games) > 0 and matched == 0:
            error_msg = f"CRITICAL: Found 0 referee assignments for {len(games)} games.\nPlaywright and Perplexity both failed. Check official.nba.com for changes or blocking."
            print(f"\n❌ {error_msg}")
            
            # Send Telegram Alert
            try:
                from utils.telegram_notifier import send_alert
                send_alert("Referee Sync Failed", error_msg)
            except ImportError:
                print("   ⚠️ Could not import telegram_notifier for alert")
            except Exception as e:
                print(f"   ⚠️ Failed to send alert: {e}")
                
            # FIX 3: Use exit(0) instead of exit(1) - referee data is useful but
            # NOT required for the pipeline to run (bets generate with neutral ref factors)
            # This prevents the workflow from failing and sending ops alerts for a non-critical issue
            sys.exit(0)
        # ----------------------------
        
        if not dry_run:
            print("🎯 Referee learning engines can now run!")


def main():
    parser = argparse.ArgumentParser(
        description='Daily Referee Assignment Sync - Day Forward Intelligence'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Test mode - print actions without database writes'
    )
    parser.add_argument(
        '--db-path',
        default='ludi.db',
        help='Path to database (default: ludi.db)'
    )
    
    args = parser.parse_args()
    
    syncer = DailyRefereeSync(db_path=args.db_path)
    syncer.run(dry_run=args.dry_run)


if __name__ == '__main__':
    main()
