import pandas as pd
import requests
import sqlite3
import time
from datetime import datetime, timedelta
from io import StringIO
import sys
import os
import config
from utils.mappings import resolve_team_abbr
from database import sync_canonical_games
from utils.browser_utils import close_popups, simulate_human_interaction

# ==============================================================================
# LUDI INFORMATIO | MODULE G: THE ZEBRAS
# V3.0 - DATABASE-DRIVEN OFFICIATING IMPACT ENGINE (Jan 15, 2026)
# ==============================================================================

DB_PATH = "ludi.db"

class LudiRefEngine:
    def __init__(self, db_path=DB_PATH):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE G (ZEBRAS) V3.0 ONLINE")
        print(f"{'='*40}")
        
        self.db_path = db_path
        self.daily_assignments = {}
        
        # League average baseline (per referee: 37.5 game total / 3 crew = 12.5)
        # Verified from 806 team-game samples: 18.74 per team × 2 = 37.48 total / 3 = 12.49
        self.LEAGUE_AVG_FOULS = 12.5
        
        # Ensure today's games exist before any referee operations
        self._ensure_todays_games()
        
        # Check database connectivity and referee count
        self._verify_database()

    def _ensure_todays_games(self):
        """Auto-populate today's games if missing (before any referee operations)"""
        print("   [ZEBRAS] 🔍 Checking today's games in database...")
        
        if not self._check_todays_games_exist():
            print("   [ZEBRAS] 📡 No games found - auto-populating today's slate...")
            self._populate_todays_games()
            print("   [ZEBRAS] ✅ Games populated successfully")
        else:
            print("   [ZEBRAS] ✅ Today's games already exist")

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
            print(f"   [ZEBRAS] ⚠️ Error checking games: {e}")
            return False

    def _populate_todays_games(self):
        """Populate today's games using The-Odds API (mirrors populate_todays_games.py logic)"""
        try:
            # Import config to access API key
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            import config
            
            # Fetch schedule from The-Odds API
            url = 'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
            params = {
                'api_key': config.ODDS_API_KEY,
                'regions': 'us',
                'markets': 'h2h',  # We just need event info
                'oddsFormat': 'american'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Get today's date in EST
            import pytz
            EST_TZ = pytz.timezone('US/Eastern')
            today_str = datetime.now(EST_TZ).strftime('%Y-%m-%d')
            
            games_to_insert = []
            for game in data:
                # Convert UTC start time to EST date string
                utc_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                est_time = utc_time.astimezone(EST_TZ)
                game_date = est_time.strftime('%Y-%m-%d')
                
                if game_date == today_str:
                    game_id = game['id']  # Use API ID as unique identifier
                    home_team = resolve_team_abbr(game['home_team'])
                    away_team = resolve_team_abbr(game['away_team'])
                    
                    # Construct ludi_game_id format: YYYYMMDD_AWAY@HOME
                    ludi_game_id = f"{est_time.strftime('%Y%m%d')}_{away_team}@{home_team}"
                    
                    games_to_insert.append((ludi_game_id, game_date, home_team, away_team))
            
            # Insert into database
            if games_to_insert:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                for g in games_to_insert:
                    g_id, g_date, home, away = g
                    print(f"   [ZEBRAS] 🏀 {away} @ {home}")
                    
                    cursor.execute("""
                        INSERT INTO games (game_id, date, home_team, away_team)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(game_id) DO UPDATE SET
                            date=excluded.date,
                            home_team=excluded.home_team,
                            away_team=excluded.away_team
                    """, (g_id, g_date, home, away))
                
                conn.commit()
                # Keep canonical_games in sync after any games INSERT.
                sync_canonical_games(conn)
                conn.close()
                print(f"   [ZEBRAS] ✅ Inserted {len(games_to_insert)} games")
            else:
                print("   [ZEBRAS] ⚠️ No games found for today")
                
        except Exception as e:
            print(f"   [ZEBRAS] ❌ Error populating games: {e}")

    def _verify_database(self):
        """Verify referee_profiles table exists and has data."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM referee_profiles")
            count = c.fetchone()[0]
            conn.close()
            print(f"   [ZEBRAS] 📊 Database: {count} referees loaded")
        except Exception as e:
            print(f"   [ZEBRAS] ⚠️ Database error: {e}")
            print(f"   [ZEBRAS] 💡 Run: python scripts/scrape_referee_roster.py")

    def _get_referee_profile(self, ref_name):
        """
        Query database for referee profile by name.
        Uses fuzzy matching (LIKE) to handle name variations.
        
        Returns:
            dict with pace_impact, whistle_impact, style, or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Extended SELECT includes rolling window + season stats + O/U/ATS signals (Feb 2026)
            # COALESCE falls back to season avg if rolling window not yet computed.
            _select = """
                SELECT referee_name, avg_fouls_per_game, avg_pace_impact, style,
                       COALESCE(rolling_21d_fouls, avg_fouls_per_game) AS rolling_21d_fouls,
                       COALESCE(rolling_21d_games, 0) AS rolling_21d_games,
                       COALESCE(games_worked, 0) AS games_worked,
                       COALESCE(ou_percentage, 0.5) AS ou_pct,
                       COALESCE(avg_total, 0) AS avg_total,
                       COALESCE(home_ats_bias, 0.5) AS home_ats_pct,
                       ou_record,
                       home_ats_record
                FROM referee_profiles
                WHERE referee_name = ?
            """
            try:
                c.execute(_select, (ref_name,))
                result = c.fetchone()
            except sqlite3.OperationalError:
                # Columns not yet migrated (run python database.py to add them)
                c.execute("SELECT referee_name, avg_fouls_per_game, avg_pace_impact, style"
                          " FROM referee_profiles WHERE referee_name = ?", (ref_name,))
                raw = c.fetchone()
                result = (raw[0], raw[1], raw[2], raw[3], raw[1], 0, 0, 0.5, 0, 0.5, None, None) if raw else None

            # If no exact match, try fuzzy match (last name)
            if not result and ' ' in ref_name:
                last_name = ref_name.split()[-1]
                try:
                    c.execute(_select.replace("WHERE referee_name = ?",
                                              "WHERE referee_name LIKE ?"),
                              (f'%{last_name}%',))
                    result = c.fetchone()
                except sqlite3.OperationalError:
                    c.execute("SELECT referee_name, avg_fouls_per_game, avg_pace_impact, style"
                              " FROM referee_profiles WHERE referee_name LIKE ?",
                              (f'%{last_name}%',))
                    raw = c.fetchone()
                    result = (raw[0], raw[1], raw[2], raw[3], raw[1], 0, 0, 0.5, 0, 0.5, None, None) if raw else None

            conn.close()

            if result:
                avg_fouls = result[1]
                pace_impact = result[2]
                style = result[3]
                rolling_21d_fouls = result[4]   # COALESCE → avg_fouls if NULL
                rolling_21d_games = result[5]
                games_worked = result[6]
                ou_pct = result[7]              # % games going OVER (0.5=neutral, >0.55=over-heavy)
                avg_total = result[8]           # avg game total when this ref officiates
                home_ats_pct = result[9]        # home cover rate (>0.5=home-friendly ref)
                ou_record = result[10]          # raw record e.g. "23-21"
                home_ats_record = result[11]    # raw record e.g. "21-23"

                # Defensive fallback: if avg_pace_impact is stale or missing,
                # recompute from avg_fouls_per_game / LEAGUE_AVG_FOULS
                if not pace_impact or pace_impact < 0.5:
                    pace_impact = round(avg_fouls / self.LEAGUE_AVG_FOULS, 3) if avg_fouls else 1.0

                # whistle_impact uses rolling window when available (short-term trend beats season avg)
                # Falls back to season avg via COALESCE above
                whistle_impact = round(rolling_21d_fouls / self.LEAGUE_AVG_FOULS, 3)

                return {
                    'name': result[0],
                    'pace_impact': pace_impact,
                    'whistle_impact': whistle_impact,
                    'style': style,
                    'season_fouls_avg': avg_fouls,           # full-season EMA baseline
                    'rolling_21d_fouls': rolling_21d_fouls,  # recent 21-day trend
                    'rolling_21d_games': rolling_21d_games,  # games in window (confidence)
                    'games_worked': games_worked,            # total season games (sample size)
                    'ou_pct': ou_pct,                        # over rate (0.5=neutral)
                    'avg_total': avg_total,                  # avg game total officiated
                    'home_ats_pct': home_ats_pct,            # home cover rate
                    'ou_record': ou_record,                  # raw "23-21" string
                    'home_ats_record': home_ats_record,      # raw "21-23" string
                }
            return None
            
        except Exception as e:
            print(f"   [ZEBRAS] DB Error: {e}")
            return None

    def build_ref_database(self):
        """
        Loads referee assignments for today. Checks the database first (populated by
        referee_sync.yml at 9:30 AM) and skips the Playwright scrape if refs are already
        present. Falls back to web scraping when the DB is empty (e.g. manual trigger
        before 9:30 AM, or if referee_sync.yml failed).
        """
        # DB-FIRST: If referee_sync.yml already ran today, load from games.referee_crew.
        # Eliminates redundant Playwright scrapes during morning brief + evening lock.
        try:
            import sqlite3
            from datetime import date
            _conn = sqlite3.connect(self.db_path)
            today_str = date.today().strftime('%Y-%m-%d')
            _rows = _conn.execute(
                "SELECT home_team, referee_crew FROM games "
                "WHERE date = ? AND referee_crew IS NOT NULL AND referee_crew != ''",
                (today_str,)
            ).fetchall()
            _conn.close()
            if _rows:
                for _home, _crew in _rows:
                    self.daily_assignments[_home] = [r.strip() for r in _crew.split(',')]
                print(f"   [ZEBRAS] ✅ Loaded {len(_rows)} ref crew(s) from DB (skip scrape)")
                return self.daily_assignments
        except Exception as _e:
            print(f"   [ZEBRAS] DB-first check failed ({_e}), falling back to scraper")

        url = "https://official.nba.com/referee-assignments/"
        print("   [ZEBRAS] 🦓 Scraping Official NBA Assignments (Playwright)...", end=" ")
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                # User requested visible browser window
                browser = p.chromium.launch(headless=False)
                # Use a standard user agent
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                try:
                    # Looser timeout and wait condition to handle heavy scripts
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
                    # --- UNIFIED POPUP & STEALTH HANDLING ---
                    print("   [ZEBRAS] 🛡️ Cleaning UI and simulating human...", end=" ")
                    close_popups(page)
                    simulate_human_interaction(page)
                    print("Done.")
                    # ----------------------------------------
                    
                    # 1. Open Date Dropdown (MANDATORY)
                    print("   [ZEBRAS] 🔽 Opening date dropdown...", end=" ")
                    try:
                        dropdown = page.wait_for_selector('button.dropdown-toggle', timeout=10000)
                        if dropdown:
                            dropdown.click(force=True)
                            # Wait for input to become visible
                            page.wait_for_selector('input#ref-date', state='visible', timeout=5000)
                            print("Done.")
                        else:
                            print("Failed (not found).")
                    except Exception as e:
                        print(f"   [ZEBRAS] ⚠️ Error opening dropdown: {e}")
                        # Continue anyway, maybe it's already open?

                    # Essential: Click "GO" isn't enough. We must "jiggle" the date.
                    # 1. Set to Yesterday -> Click GO
                    # 2. Set to Today -> Click GO
                    print("   [ZEBRAS] 🔄 Toggling date to force refresh...", end=" ")
                    
                    yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    
                    # Step 1: Yesterday
                    # Ensure element is visible before filling. If hidden, re-open dropdown.
                    if not page.is_visible('input#ref-date'):
                        print("(Re-opening dropdown)...", end=" ")
                        page.click('button.dropdown-toggle', force=True)
                        page.wait_for_selector('input#ref-date', state='visible', timeout=5000)

                    page.fill('input#ref-date', yesterday_str)
                    
                    # Click GO (ensure we click the button not the input if they overlap, but usage here matches script)
                    # Note: We might need to re-click dropdown if it closes? 
                    # Usually fill doesn't close it. 
                    page.click('input#date-filter', force=True)
                    page.wait_for_timeout(1000)
                    
                    # Step 2: Today (Target)
                    # Re-open dropdown if needed? The site behavior implies filter closes it.
                    if not page.is_visible('input#ref-date'):
                         page.click('button.dropdown-toggle', force=True)
                         page.wait_for_selector('input#ref-date', state='visible', timeout=5000)

                    page.fill('input#ref-date', today_str)
                    page.click('input#date-filter', force=True)
                    print("Done.")

                    # Wait for the table to actually populate with rows
                    try:
                        # Specific class found by browser agent: .nba-refs-content table
                        page.wait_for_selector(".nba-refs-content table tbody tr", timeout=15000)
                    except Exception as e:
                        print(f"   [ZEBRAS] ⚠️ Timeout waiting for table rows: {e}")
                        
                    content = page.content()
                    
                except Exception as e:
                    print(f"❌ Browser Error: {e}")
                    # CAPTURE SCREENSHOT ON ERROR
                    try:
                        page.screenshot(path="error_state.png")
                        print("   [ZEBRAS] 📸 Screenshot saved to 'error_state.png'")
                    except Exception as e:
                        print(f"[TAG] Context: {e}")
                        pass
                    
                    browser.close()
                    return {}
                    
                browser.close()

            # Parse Tables with StringIO fix applied
            dfs = pd.read_html(StringIO(content))
            
            if not dfs:
                print("⚠️ No tables found on page.")
                return {}

            df = dfs[0]
            df.columns = [c.upper() for c in df.columns]
            
            count = 0
            for _, row in df.iterrows():
                game_str = str(row.get('GAME', ''))
                
                if '@' in game_str:
                    parts = game_str.split('@')
                    if len(parts) > 1:
                        raw_home = parts[1].strip()
                        
                        if '(' in raw_home:
                            raw_home = raw_home.split('(')[0].strip()
                            
                        home_abbr = resolve_team_abbr(raw_home)
                        
                        crew = []
                        for col in df.columns:
                            if 'CHIEF' in col or 'REFEREE' in col or 'UMPIRE' in col:
                                if pd.notna(row[col]):
                                    raw_ref = str(row[col]).split('(')[0].strip()
                                    crew.append(raw_ref)
                        
                        if home_abbr:
                            self.daily_assignments[home_abbr] = crew
                            count += 1
            
            print(f"✅ Success. Found assignments for {count} games.")

            # Perplexity bulk fallback — single query instead of N per-game queries
            if count == 0 and getattr(config, 'PERPLEXITY_API_KEY', None):
                try:
                    from utils.perplexity_client import PerplexityClient
                    perp = PerplexityClient()
                    today_str = datetime.now().strftime('%Y-%m-%d')

                    # Load known referee roster for fuzzy matching
                    known_refs = []
                    today_games = []
                    try:
                        conn = sqlite3.connect(self.db_path)
                        known_refs = [r[0] for r in conn.execute(
                            "SELECT referee_name FROM referee_profiles"
                        ).fetchall()]
                        today_games = conn.execute(
                            "SELECT game_id, home_team, away_team FROM games WHERE date = ?",
                            (today_str,)
                        ).fetchall()
                        conn.close()
                    except Exception:
                        pass

                    if today_games:
                        bulk_result = perp.search_referee_assignments(
                            today_str, today_games, known_refs=known_refs
                        )

                        perp_count = 0
                        if bulk_result:
                            conn = sqlite3.connect(self.db_path)
                            for game_id, home_team, away_team in today_games:
                                matched = bulk_result.get(home_team, [])
                                if matched:
                                    self.daily_assignments[home_team] = matched
                                    conn.execute(
                                        "UPDATE games SET referee_crew = ? WHERE game_id = ?",
                                        (', '.join(matched), game_id)
                                    )
                                    print(f"   [ZEBRAS] 🔍 Perplexity crew ({home_team}): {', '.join(matched)}")
                                    perp_count += 1
                            conn.commit()
                            conn.close()

                        if perp_count > 0:
                            print(f"   [ZEBRAS] ✅ Perplexity bulk fallback populated {perp_count} crew(s)")
                        else:
                            print(f"   [ZEBRAS] ⚠️ Perplexity bulk fallback returned no matchable refs")
                except Exception as e:
                    print(f"   [ZEBRAS] Perplexity referee fallback failed: {e}")

            return self.daily_assignments

        except Exception as e:
            print(f"❌ Error scraping refs: {e}")
            return {}



    def get_team_trends(self, team_abbr):
        """
        Look up team betting trends from team_betting_trends table.

        Returns dict with H/A records, scoring averages, and ATS splits.
        Returns None if table not populated or team not found.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            row = conn.execute('''
                SELECT team, home_wins, home_losses, away_wins, away_losses,
                       home_ats_wins, home_ats_losses, away_ats_wins, away_ats_losses,
                       home_avg_score, home_avg_allowed, away_avg_score, away_avg_allowed,
                       avg_game_total, games_tracked, ats_games_tracked
                FROM team_betting_trends WHERE team = ?
            ''', (team_abbr,)).fetchone()
            conn.close()

            if not row:
                return None

            hw, hl = row[1], row[2]
            aw, al = row[3], row[4]
            return {
                'team': row[0],
                'home_record': f"{hw}-{hl}",          # e.g. "25-7"
                'away_record': f"{aw}-{al}",
                'home_win_pct': round(hw / (hw + hl), 3) if (hw + hl) > 0 else 0.5,
                'away_win_pct': round(aw / (aw + al), 3) if (aw + al) > 0 else 0.5,
                'home_ats_record': f"{row[5]}-{row[6]}",
                'away_ats_record': f"{row[7]}-{row[8]}",
                'home_ats_pct': round(row[5] / (row[5] + row[6]), 3) if (row[5] + row[6]) > 0 else 0.5,
                'away_ats_pct': round(row[7] / (row[7] + row[8]), 3) if (row[7] + row[8]) > 0 else 0.5,
                'home_avg_score': row[9],
                'home_avg_allowed': row[10],
                'away_avg_score': row[11],
                'away_avg_allowed': row[12],
                'avg_game_total': row[13],
                'games_tracked': row[14],
                'ats_games_tracked': row[15],
            }
        except Exception as e:
            print(f"   [ZEBRAS] team_trends lookup failed for {team_abbr}: {e}")
            return None

    def get_player_crew_bias(self, player_name: str, crew: list) -> dict:
        """
        Returns aggregate ref-player bias for a player vs a given referee crew.

        Queries referee_player_bias (populated daily by analyze_star_bias.py) for
        each ref in the crew, weighted by games_officiated. Complements the
        crew-level whistle_impact in get_game_impact() — this is the player-specific
        layer on top of the crew aggregate.

        Args:
            player_name: Player's display name (exact match, then last-name fuzzy)
            crew: List of referee names from daily_assignments

        Returns:
            dict: {
                'avg_fta_awarded': float,  # avg FTA this player gets vs this crew
                'avg_pf_called':   float,  # avg PF called on this player vs crew
                'points_impact':   float,  # avg PPG delta vs player's base_ppg
                'games_total':     int,    # total sample size across crew refs
                'games_per_ref':   float,  # avg games per ref (confidence proxy)
                'label':           str,    # 'STAR_KILLER' | 'PROTECTOR' | 'NEUTRAL'
            }
            or None if crew is empty, refs unresolved, or < 5 games total
        """
        GAMES_MIN = 5          # Minimum total games to surface any signal
        IMPACT_THRESHOLD = 3.5 # PPG delta threshold for KILLER / PROTECTOR label

        if not crew:
            return None

        try:
            conn = sqlite3.connect(self.db_path)

            # Resolve crew names → referee_ids
            placeholders = ','.join('?' * len(crew))
            ref_rows = conn.execute(
                f"SELECT referee_id FROM referee_profiles WHERE referee_name IN ({placeholders})",
                crew
            ).fetchall()

            if not ref_rows:
                conn.close()
                return None

            ref_ids = [r[0] for r in ref_rows]
            id_ph = ','.join('?' * len(ref_ids))

            # Exact name match first
            rows = conn.execute(
                f"""SELECT games_officiated, avg_pf_called, avg_fta_awarded, points_impact_vs_avg
                    FROM referee_player_bias
                    WHERE referee_id IN ({id_ph}) AND player_name = ?""",
                (*ref_ids, player_name)
            ).fetchall()

            # Last-name fuzzy fallback
            if not rows and ' ' in player_name:
                last_name = player_name.split()[-1]
                rows = conn.execute(
                    f"""SELECT games_officiated, avg_pf_called, avg_fta_awarded, points_impact_vs_avg
                        FROM referee_player_bias
                        WHERE referee_id IN ({id_ph}) AND player_name LIKE ?""",
                    (*ref_ids, f'%{last_name}%')
                ).fetchall()

            conn.close()

            if not rows:
                return None

            total_games = sum(r[0] for r in rows)
            if total_games < GAMES_MIN:
                return None

            # Weighted averages (weighted by each ref's games_officiated sample)
            avg_pf     = sum(r[0] * r[1] for r in rows) / total_games
            avg_fta    = sum(r[0] * r[2] for r in rows) / total_games
            avg_impact = sum(r[0] * r[3] for r in rows) / total_games
            games_per_ref = total_games / len(ref_rows)

            label = 'NEUTRAL'
            if avg_impact <= -IMPACT_THRESHOLD:
                label = 'STAR_KILLER'
            elif avg_impact >= IMPACT_THRESHOLD:
                label = 'PROTECTOR'

            return {
                'avg_fta_awarded': round(avg_fta, 2),
                'avg_pf_called':   round(avg_pf, 2),
                'points_impact':   round(avg_impact, 2),
                'games_total':     total_games,
                'games_per_ref':   round(games_per_ref, 1),
                'label':           label,
            }

        except Exception as e:
            print(f"   [ZEBRAS] star bias lookup failed ({player_name}): {e}")
            return None

    def get_game_impact(self, home_team_abbr):
        """
        Calculate referee impact for a game, now returning a dict with
        separate pace and whistle impact factors.

        Returns:
            dict: {
                'pace_impact': float,      # Multiplier for game pace
                'whistle_impact': float,   # Multiplier for FTA projections
                'crew': list,              # List of referee names
                'confidence': float,       # 0.0-1.0, how many refs we have data for
                'home_trends': dict|None,  # Team H/A record + scoring (from team_betting_trends)
                'ref_ou_avg': float|None,  # Avg ref O/U percentage across crew
                'ref_home_ats_avg': float|None,  # Avg ref home ATS % across crew
            }
        """
        crew = self.daily_assignments.get(home_team_abbr, [])

        # Look up team H/A trends (always — not dependent on having a crew)
        home_trends = self.get_team_trends(home_team_abbr)

        # Default neutral response
        neutral_response = {
            'pace_impact': 1.0,
            'whistle_impact': 1.0,
            'crew': crew,
            'confidence': 0.0,
            'home_trends': home_trends,
            'ref_ou_avg': None,
            'ref_home_ats_avg': None,
        }

        if not crew:
            return neutral_response

        pace_factors = []
        whistle_factors = []
        ou_pcts = []
        home_ats_pcts = []
        known_count = 0

        for ref in crew:
            profile = self._get_referee_profile(ref)
            if profile:
                pace_factors.append(profile['pace_impact'])
                whistle_factors.append(profile['whistle_impact'])
                known_count += 1
                # Collect O/U and ATS signals (only when OddsShark data available)
                if profile.get('ou_pct') and profile['ou_pct'] != 0.5:
                    ou_pcts.append(profile['ou_pct'])
                if profile.get('home_ats_pct') and profile['home_ats_pct'] != 0.5:
                    home_ats_pcts.append(profile['home_ats_pct'])
            else:
                # Unknown ref, use neutral
                pace_factors.append(1.0)
                whistle_factors.append(1.0)

        # Calculate crew averages
        avg_pace = sum(pace_factors) / len(pace_factors)
        avg_whistle = sum(whistle_factors) / len(whistle_factors)
        confidence = known_count / len(crew)

        # Apply safety caps (MAX 10% deviation from baseline)
        avg_pace = max(0.90, min(1.10, avg_pace))
        avg_whistle = max(0.90, min(1.10, avg_whistle))

        return {
            'pace_impact': round(avg_pace, 3),
            'whistle_impact': round(avg_whistle, 3),
            'crew': crew,
            'confidence': round(confidence, 2),
            'home_trends': home_trends,
            'ref_ou_avg': round(sum(ou_pcts) / len(ou_pcts), 3) if ou_pcts else None,
            'ref_home_ats_avg': round(sum(home_ats_pcts) / len(home_ats_pcts), 3) if home_ats_pcts else None,
        }


if __name__ == "__main__":
    zebras = LudiRefEngine()
    assignments = zebras.build_ref_database()
    
    if assignments:
        print("\n--- TEST: First 3 Games (New V3.0 Output) ---")
        for team in list(assignments.keys())[:3]:
            impact = zebras.get_game_impact(team)
            print(f"\n🏀 {team}:")
            print(f"   Crew: {impact['crew']}")
            print(f"   Pace Impact: {impact['pace_impact']}x")
            print(f"   Whistle Impact: {impact['whistle_impact']}x")
            print(f"   Confidence: {impact['confidence'] * 100:.0f}%")