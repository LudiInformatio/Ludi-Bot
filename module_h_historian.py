import sqlite3
import json
import os
import requests
import time
import argparse
from datetime import datetime, timedelta
import config

# [PAID TIER] Import monitoring utilities
from utils.api_monitor import get_monitor
from utils.player_id_resolver import PlayerIDResolver

# =========================================================
# LUDI INFORMATIO | MODULE H: THE HISTORIAN
# V2.0 - DIRECT SQLITE WRITES (Eliminates JSON anti-pattern)
# =========================================================

HISTORIAN_DAILY_BUDGET = 200  # Leave headroom for other modules
DB_PATH = "ludi.db"

class LudiHistorian:
    def __init__(self, budget=None, db_path=DB_PATH):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE H (HISTORIAN) ONLINE")
        print(f"{'='*40}")

        # Rate Limiting
        self.request_budget = budget if budget is not None else HISTORIAN_DAILY_BUDGET
        self.requests_made = 0
        print(f"   🛡️ API Budget: {self.request_budget} requests")

        # Database path
        self.db_path = db_path

        # Tank01 API Configuration
        self.TANK_KEY = getattr(config, 'TANK01_KEY', '')
        self.TANK_HOST = "tank01-fantasy-stats.p.rapidapi.com"

        # API-Sports (Historical)
        self.APISPORTS_KEY = getattr(config, 'APISPORTS_KEY', '')
        self.APISPORTS_HOST = getattr(config, 'APISPORTS_HOST', 'v2.nba.api-sports.io')

        # [PAID TIER] Initialize API Monitor
        self.monitor = get_monitor()

        # Initialize Player ID Resolver (Phase 6.5b Step 5.5)
        self.resolver = PlayerIDResolver(db_path=self.db_path)

        # Ensure unique index exists for upsert operations
        self._ensure_unique_index()

    def get_db_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with WAL mode enabled."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_unique_index(self):
        """Ensure unique constraint exists on (game_id, player_id) for upsert operations."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_player_game_logs_unique
                ON player_game_logs(player_id, game_date)
            """)
            conn.commit()
        except sqlite3.Error as e:
            print(f"   ⚠️ Index creation note: {e}")
        finally:
            conn.close()

    def _resolve_player_id(self, tank01_id: str, player_name: str) -> str:
        """
        Resolve Tank01 composite ID to canonical NBA ID.

        Phase 6.5b Step 5.5: Prevents dirty ID pollution by resolving
        Tank01's composite IDs to canonical NBA IDs before writing to database.

        Lookup priority:
        1. Try Tank01 ID directly (might already be canonical)
        2. Try Tank01 ID as alias (composite format)
        3. Try player name match
        4. Fallback to original ID if no match

        Args:
            tank01_id: Raw player ID from Tank01 API
            player_name: Player full name for fallback matching

        Returns:
            Canonical NBA player ID (clean format)
        """
        if not tank01_id:
            return '0'  # Default for missing IDs

        tank01_id = str(tank01_id).strip()

        try:
            # Try ID-based resolution (handles both canonical + composite aliases)
            canonical_id = self.resolver.resolve_to_canonical_id(tank01_id)
            return canonical_id
        except ValueError:
            # No match by ID - try by name
            try:
                canonical_id = self.resolver.resolve_to_canonical_id(player_name)
                return canonical_id
            except ValueError:
                # No match at all - log warning and return original
                # This is expected for rookies or recently added players
                print(f"   ⚠️ No canonical ID for: {player_name} ({tank01_id})")
                return tank01_id

    def _check_budget(self):
        """
        Checks if the daily API budget has been exceeded.
        Returns: True if budget remaining, False if exhausted.
        """
        if self.requests_made >= self.request_budget:
            print(f"\n   ⚠️ Budget exhausted ({self.request_budget} requests). Stopping sync gracefully.")
            return False

        self.requests_made += 1
        return True

    # =========================================================
    # DIRECT SQLITE WRITE METHOD (Step 5 Implementation)
    # =========================================================

    def _write_game_logs_to_db(self, records: list) -> int:
        """
        Write game log records directly to SQLite.
        
        Uses ON CONFLICT upsert pattern to handle duplicates gracefully.
        
        Args:
            records: List of record dicts from Tank01 API
            
        Returns:
            Number of records successfully inserted/updated
        """
        if not records:
            return 0
            
        conn = self.get_db_connection()
        cursor = conn.cursor()
        success_count = 0

        for record in records:
            try:
                # Handle GAME_DATE formatting
                game_date = record.get('GAME_DATE')
                if isinstance(game_date, datetime):
                    game_date = game_date.strftime('%Y-%m-%d')
                elif isinstance(game_date, str) and len(game_date) == 8:
                    # Convert YYYYMMDD to YYYY-MM-DD
                    game_date = f"{game_date[:4]}-{game_date[4:6]}-{game_date[6:8]}"

                # Resolve player ID to canonical format (Phase 6.5b Step 5.5)
                canonical_player_id = self._resolve_player_id(
                    str(record['PLAYER_ID']),
                    record.get('PLAYER_NAME', 'Unknown')
                )

                cursor.execute("""
                    INSERT INTO player_game_logs (
                        game_id, game_date, player_id, player_name,
                        team_abbreviation, pts, ast, reb, minutes,
                        stl, blk, tov, fgm, fga, fg3m, fg3a,
                        ftm, fta, oreb, dreb, pf, fantasy_pts, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(player_id, game_date) DO UPDATE SET
                        pts = excluded.pts,
                        ast = excluded.ast,
                        reb = excluded.reb,
                        minutes = excluded.minutes,
                        stl = excluded.stl,
                        blk = excluded.blk,
                        tov = excluded.tov,
                        fgm = excluded.fgm,
                        fga = excluded.fga,
                        fg3m = excluded.fg3m,
                        fg3a = excluded.fg3a,
                        ftm = excluded.ftm,
                        fta = excluded.fta,
                        oreb = excluded.oreb,
                        dreb = excluded.dreb,
                        pf = excluded.pf,
                        fantasy_pts = excluded.fantasy_pts,
                        created_at = excluded.created_at
                """, (
                    record['GAME_ID'],
                    game_date,
                    canonical_player_id,
                    record.get('PLAYER_NAME', 'Unknown'),
                    record.get('TEAM_ABBREVIATION', 'UNK'),
                    int(record.get('PTS', 0)),
                    int(record.get('AST', 0)),
                    int(record.get('REB', 0)),
                    int(record.get('MIN', 0)),
                    int(record.get('STL', 0)),
                    int(record.get('BLK', 0)),
                    int(record.get('TOV', 0)),
                    int(record.get('FGM', 0)),
                    int(record.get('FGA', 0)),
                    int(record.get('FG3M', 0)),
                    int(record.get('FG3A', 0)),
                    int(record.get('FTM', 0)),
                    int(record.get('FTA', 0)),
                    int(record.get('OREB', 0)),
                    int(record.get('DREB', 0)),
                    int(record.get('PF', 0)),
                    float(record.get('FANTASY_PTS', 0) or 0),
                    datetime.now().isoformat()
                ))
                success_count += 1
            except Exception as e:
                print(f"   ⚠️ Failed to insert record for {record.get('PLAYER_NAME', 'unknown')}: {e}")

        conn.commit()
        conn.close()
        return success_count

    def _get_current_record_count(self) -> int:
        """Get current record count from player_game_logs table."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM player_game_logs")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _get_last_game_date(self) -> datetime:
        """Get the most recent game date from player_game_logs table."""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(game_date) FROM player_game_logs")
        result = cursor.fetchone()[0]
        conn.close()
        
        if result:
            return datetime.strptime(result, '%Y-%m-%d')
        return None

    # =========================================================
    # RESUME STATE MANAGEMENT (Phase 6.5b Step 4)
    # =========================================================

    def _save_sync_state(self, completed, remaining, status, reason=None):
        """
        Save current sync state to JSON file for resume capability.

        Args:
            completed: List of completed date strings (YYYY-MM-DD)
            remaining: List of remaining date strings (YYYY-MM-DD)
            status: "in_progress", "paused", or "complete"
            reason: Optional pause reason (e.g., "budget_exhausted")
        """
        state = {
            "last_run": datetime.now().isoformat(),
            "source_file": "cache/pending_sync_dates.json",
            "total_dates": len(completed) + len(remaining),
            "completed_dates": completed,
            "remaining_dates": remaining,
            "last_completed_date": completed[-1] if completed else None,
            "status": status,
            "pause_reason": reason
        }

        # Ensure cache directory exists
        os.makedirs("cache", exist_ok=True)

        state_file = "cache/historian_sync_state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

        print(f"   💾 State saved: {len(completed)}/{state['total_dates']} dates completed")

    def _load_sync_state(self):
        """
        Load existing sync state from JSON file.

        Returns:
            dict: State data if valid, None if file missing or corrupt
        """
        state_file = "cache/historian_sync_state.json"

        if not os.path.exists(state_file):
            return None

        try:
            with open(state_file) as f:
                state = json.load(f)

            # Validate required fields
            required_fields = ['status', 'remaining_dates', 'completed_dates']
            if all(field in state for field in required_fields):
                return state
            else:
                print(f"   ⚠️ State file missing required fields. Ignoring.")
                return None

        except json.JSONDecodeError as e:
            print(f"   ⚠️ Corrupt state file: {e}. Ignoring.")
            return None
        except Exception as e:
            print(f"   ⚠️ Error loading state: {e}. Ignoring.")
            return None

    def _load_audit_file(self):
        """
        Load audit file containing dates to sync.

        Returns:
            list: Date strings (YYYY-MM-DD) or None if file missing
        """
        audit_file = "cache/pending_sync_dates.json"

        if not os.path.exists(audit_file):
            return None

        try:
            with open(audit_file) as f:
                audit_data = json.load(f)

            dates = audit_data.get('dates_to_sync', [])
            if dates:
                print(f"   📋 Loaded {len(dates)} dates from audit file")
                return dates
            else:
                print(f"   ℹ️ Audit file is empty")
                return None

        except json.JSONDecodeError as e:
            print(f"   ⚠️ Corrupt audit file: {e}")
            return None
        except Exception as e:
            print(f"   ⚠️ Error loading audit: {e}")
            return None

    def update_database(self):
        """
        Main Routine: Checks for resume state, audit file, or runs incremental sync.

        Priority Order:
        1. Resume from paused state (cache/historian_sync_state.json)
        2. Start from audit file (cache/pending_sync_dates.json)
        3. Incremental sync (existing behavior: last_date to yesterday)
        """
        # Show current DB status
        current_count = self._get_current_record_count()
        print(f"   📂 Current Database: {current_count} game log records")

        # MODE 1: Resume from state file (highest priority)
        state = self._load_sync_state()
        if state and state.get('status') == 'paused':
            print(f"   🔄 Resuming sync: {len(state['remaining_dates'])} dates remaining")
            return self._resume_from_state(state)

        # MODE 2: Start from audit file (second priority)
        audit_dates = self._load_audit_file()
        if audit_dates:
            print(f"   📋 Starting audit-based sync: {len(audit_dates)} dates to process")
            return self._sync_from_audit(audit_dates)

        # MODE 3: Incremental sync (existing behavior)
        print(f"   🔄 Running incremental sync")
        return self._incremental_sync()

    def _resume_from_state(self, state):
        """Resume sync from paused state."""
        from utils.telegram_notifier import send_message

        completed = state['completed_dates']
        remaining = state['remaining_dates']

        print(f"   📊 Progress so far: {len(completed)}/{state['total_dates']} dates")

        return self._process_date_list(remaining, completed)

    def _sync_from_audit(self, dates_to_sync):
        """Start fresh sync from audit file."""
        return self._process_date_list(dates_to_sync, [])

    def _process_date_list(self, dates_to_sync, completed_dates):
        """
        Process a list of dates with resume capability.
        
        V2.0: Writes directly to SQLite instead of JSON.

        Args:
            dates_to_sync: List of date strings (YYYY-MM-DD) to process
            completed_dates: List of already completed dates

        Returns:
            Number of dates successfully processed
        """
        from utils.telegram_notifier import send_message

        all_new_records = []
        dates_processed = 0

        for i, date_str in enumerate(dates_to_sync):
            print(f"   📅 Processing {date_str} ({i+1}/{len(dates_to_sync)})...", end=" ")

            # Check budget before processing
            if not self._check_budget():
                # Budget exhausted - save state and pause
                remaining = dates_to_sync[i:]  # Rest of the list
                self._save_sync_state(
                    completed=completed_dates,
                    remaining=remaining,
                    status="paused",
                    reason="budget_exhausted"
                )

                # Write any pending records to DB before pausing
                if all_new_records:
                    inserted = self._write_game_logs_to_db(all_new_records)
                    print(f"\n   💾 Saved {inserted} records before pause")

                # Send Telegram alert
                try:
                    progress_pct = len(completed_dates) / (len(completed_dates) + len(remaining)) * 100
                    send_message(
                        f"⚠️ *Historian Sync Paused*\n"
                        f"Progress: {len(completed_dates)}/{len(completed_dates) + len(remaining)} ({progress_pct:.0f}%)\n"
                        f"Remaining: {len(remaining)} dates\n"
                        f"Last completed: `{completed_dates[-1] if completed_dates else 'N/A'}`\n"
                        f"_Will resume on next workflow run_"
                    )
                except Exception as e:
                    print(f"\n   ⚠️ Failed to send Telegram alert: {e}")

                print(f"\n   ⏸️ Paused at {date_str}. Resume on next run.")
                break

            # Process this date
            date_tank_format = date_str.replace("-", "")  # "2025-10-20" -> "20251020"
            daily_stats = self._fetch_tank01_boxscores(date_tank_format)

            if daily_stats:
                print(f"✅ {len(daily_stats)} records")
                all_new_records.extend(daily_stats)
            else:
                print("No games")

            # Mark as completed
            completed_dates.append(date_str)
            dates_processed += 1

            # Update state after each successful date
            remaining = dates_to_sync[i+1:]
            self._save_sync_state(
                completed=completed_dates,
                remaining=remaining,
                status="in_progress"
            )

        # Write all new records to SQLite (DIRECT WRITE - no JSON!)
        if all_new_records:
            inserted = self._write_game_logs_to_db(all_new_records)
            new_total = self._get_current_record_count()
            print(f"\n   💾 SUCCESS: Added {inserted} new rows to database.")
            print(f"   📈 New Total: {new_total} rows.")

        # Check if fully complete
        if dates_processed == len(dates_to_sync):
            # All dates processed - mark as complete
            self._finalize_sync(completed_dates, len(all_new_records))

        return dates_processed

    def _finalize_sync(self, completed_dates, total_records):
        """Clean up after successful completion."""
        from utils.telegram_notifier import send_message

        # Send completion alert
        try:
            send_message(
                f"✅ *Historian Sync Complete*\n"
                f"Dates synced: {len(completed_dates)}\n"
                f"Records added: {total_records}\n"
                f"_Database is now up to date_"
            )
        except Exception as e:
            print(f"   ⚠️ Failed to send completion alert: {e}")

        # Delete state file (self-cleaning)
        state_file = "cache/historian_sync_state.json"
        if os.path.exists(state_file):
            os.remove(state_file)
            print(f"   🧹 Cleaned up state file")

        # Delete audit file (no longer needed)
        audit_file = "cache/pending_sync_dates.json"
        if os.path.exists(audit_file):
            os.remove(audit_file)
            print(f"   🧹 Cleaned up audit file")

    def _incremental_sync(self):
        """
        Original incremental sync behavior: sync from last_date to yesterday.
        
        V2.0: Uses SQLite as source of truth instead of JSON file.
        """
        # 1. GET LAST DATE FROM SQLITE (was: JSON file)
        last_date = self._get_last_game_date()
        
        if not last_date:
            print("   ⚠️ No game logs found in database. Please run a backfill first.")
            return

        today = datetime.now()

        # Calculate days gap
        days_diff = (today - last_date).days

        # If last date is today or yesterday, we are likely fine.
        if days_diff < 1:
            print(f"   ✅ [HISTORIAN] Database is already up to date. (Last Game: {last_date.date()})")
            return

        print(f"   🗓️ Last recorded game: {last_date.strftime('%Y-%m-%d')}")
        print(f"   🔄 Fetching missing games for {days_diff} days...")

        # 2. FETCH & ACCUMULATE
        new_records = []

        # Iterate from (Last Date + 1 Day) up to (Yesterday)
        current_check = last_date + timedelta(days=1)
        while current_check.date() < today.date():
            date_str = current_check.strftime('%Y%m%d') # Tank01 format: 20231025
            print(f"      > Checking Date: {date_str}...", end=" ")

            daily_stats = self._fetch_tank01_boxscores(date_str)
            if daily_stats:
                print(f"Found {len(daily_stats)} stat lines.")
                new_records.extend(daily_stats)
            else:
                print("No games.")

            current_check += timedelta(days=1)

        # 3. WRITE DIRECTLY TO SQLITE (was: JSON file)
        if new_records:
            inserted = self._write_game_logs_to_db(new_records)
            new_total = self._get_current_record_count()
            print(f"\n   💾 SUCCESS: Added {inserted} new rows to database.")
            print(f"   📈 New Total: {new_total} rows.")
        else:
            print("\n   ℹ️ No new data found to append.")

    def _fetch_tank01_boxscores(self, date_str):
        """
        Fetches all box scores for a specific date using Tank01.
        """
        if not self._check_budget():
            return []

        url_games = f"https://{self.TANK_HOST}/getNBAGamesForDate"
        params_games = {"gameDate": date_str}
        headers = {
            "X-RapidAPI-Key": self.TANK_KEY,
            "X-RapidAPI-Host": self.TANK_HOST
        }
        
        clean_stats = []
        
        try:
            r = requests.get(url_games, headers=headers, params=params_games)
            data = r.json()
            games = data.get('body', [])
            
            if not games: return []

            # Loop through games
            for game in games:
                game_id = game.get('gameID')
                if not game_id: continue
                self._fetch_single_game_box(game_id, date_str, clean_stats, headers)
                
            return clean_stats

        except Exception as e:
            print(f"Error fetching date {date_str}: {e}")
            return []

    def _fetch_single_game_box(self, game_id, date_str, storage_list, headers):
        """
        Helper to get full stats for one gameID.
        """
        if not self._check_budget():
            return

        url_box = f"https://{self.TANK_HOST}/getNBABoxScore"
        # fantasyPoints=true enables the fantasyPoints field per player in the response
        params_box = {"gameID": game_id, "fantasyPoints": "true"}
        
        try:
            r = requests.get(url_box, headers=headers, params=params_box)

            # [PAID TIER] Log API usage
            self.monitor.log_request('tank01', 'box_score', r.headers)

            body = r.json().get('body', {})
            player_stats = body.get('playerStats', {})

            # Parse Players
            for p_id, stats in player_stats.items():

                # --- VARS ---
                tov = stats.get('TOV', stats.get('to', 0))

                # --- MAPPING: TANK01 -> NBA API SCHEMA ---
                # This ensures your new data matches the 'Initializer' columns
                record = {
                    "GAME_ID": game_id,  # Critical: Required for SQLite unique constraint
                    "GAME_DATE": datetime.strptime(date_str, '%Y%m%d'),
                    "PLAYER_ID": p_id,
                    "PLAYER_NAME": stats.get('longName', 'Unknown'),
                    "TEAM_ABBREVIATION": stats.get('teamAbv', 'UNK'),

                    # Core Stats
                    "PTS": float(stats.get('pts', 0)),
                    "AST": float(stats.get('ast', 0)),
                    "REB": float(stats.get('reb', 0)),
                    "MIN": self._clean_minutes(stats.get('mins', 0)),

                    # Defense
                    "STL": float(stats.get('stl', 0)),
                    "BLK": float(stats.get('blk', 0)),
                    "TOV": float(tov),

                    # Shooting (Added to match nba_api)
                    "FGM": float(stats.get('fgm', 0)),
                    "FGA": float(stats.get('fga', 0)),
                    "FG3M": float(stats.get('tptfgm', 0)), # Tank01 weird key
                    "FG3A": float(stats.get('tptfga', 0)), # Tank01 weird key
                    "FTM": float(stats.get('ftm', 0)),
                    "FTA": float(stats.get('fta', 0)),

                    # Rebounding Splits
                    "OREB": float(stats.get('oreb', stats.get('OffReb', 0))),
                    "DREB": float(stats.get('dreb', stats.get('DefReb', 0))),

                    # Personal Fouls (Tank01 uses uppercase 'PF')
                    "PF": float(stats.get('PF', 0)),

                    # Fantasy Points (available when fantasyPoints=true in request)
                    "FANTASY_PTS": float(stats.get('fantasyPoints', 0) or 0),
                }
                storage_list.append(record)

            # Phase 6 Bridge: write game result to games table so downstream modules
            # (Module A, referee sync) can find it even when Odds API is down.
            try:
                team_stats = body.get('teamStats', {})
                home_data = team_stats.get('home', {})
                away_data = team_stats.get('away', {})
                home_team = home_data.get('teamAbv')
                away_team = away_data.get('teamAbv')
                home_score = home_data.get('pts') or home_data.get('totalPts')
                away_score = away_data.get('pts') or away_data.get('totalPts')

                if home_team and away_team and home_score is not None and away_score is not None:
                    # Convert date from YYYYMMDD to YYYY-MM-DD for games table
                    game_date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                    bridge_conn = self.get_db_connection()
                    bridge_cursor = bridge_conn.cursor()
                    bridge_cursor.execute("""
                        INSERT INTO games (game_id, date, home_team, away_team, home_score, away_score)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(game_id) DO UPDATE SET
                            home_score = excluded.home_score,
                            away_score = excluded.away_score
                    """, (game_id, game_date_fmt, home_team, away_team, int(home_score), int(away_score)))
                    bridge_conn.commit()
                    bridge_conn.close()
            except Exception as bridge_err:
                print(f"   [Module H] Games bridge warning for {game_id}: {bridge_err}")

            time.sleep(0.1)

        except Exception as e:
            # [PAID TIER] Replace silent failure with error logging
            error_msg = f"{type(e).__name__}: {str(e)[:100]}"
            print(f"   [HISTORIAN] ❌ Box score fetch failed for game {game_id}: {error_msg}")
            self.monitor.log_failed_request('tank01', 'box_score', error_msg)
            
    def _clean_minutes(self, min_val):
        """Handles MM:SS, float, or int inputs for minutes."""
        if not min_val: return 0.0
        try:
            return float(min_val)
        except ValueError:
            if isinstance(min_val, str) and ":" in min_val:
                try:
                    parts = min_val.split(":")
                    return int(parts[0]) + (int(parts[1]) / 60.0)
                except Exception as e:
                    print(f"[TAG] Context: {e}")
                    return 0.0

    def fetch_historical_apisports(self, season, date_str):
        """ [SECONDARY] API-Sports Backfill Source """
        if not self.APISPORTS_KEY:
            return []

        print(f"      > [APISPORTS] Backfilling {date_str}...")
        url = f"https://{self.APISPORTS_HOST}/games"
        headers = {
            "x-rapidapi-host": self.APISPORTS_HOST,
            "x-rapidapi-key": self.APISPORTS_KEY
        }
        params = {"season": season, "date": date_str}
        
        try:
            # Placeholder implementation until key is live
            # r = requests.get(url, headers=headers, params=params)
            # return r.json()
            return []
        except Exception as e:
            print(f"      ⚠️ [APISPORTS] Error: {e}")
            return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ludi Historian Module")
    parser.add_argument("--budget", type=int, help="Override daily API request budget")
    args = parser.parse_args()

    config.validate_config()
    h = LudiHistorian(budget=args.budget)
    h.update_database()