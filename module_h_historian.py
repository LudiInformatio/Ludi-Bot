import pandas as pd
import json
import os
import requests
import time
from datetime import datetime, timedelta
import config

# [PAID TIER] Import monitoring utilities
from utils.api_monitor import get_monitor

# =========================================================
# LUDI INFORMATIO | MODULE H: THE HISTORIAN
# V1.3 - HYBRID SYNC (Matches nba_api Schema with Tank01)
# =========================================================

class LudiHistorian:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE H (HISTORIAN) ONLINE")
        print(f"{'='*40}")

        self.history_file = "ludi_history_db.json"
        self.TANK_KEY = getattr(config, 'TANK01_KEY', '')
        self.TANK_HOST = "tank01-fantasy-stats.p.rapidapi.com"

        # API-Sports (Historical)
        self.APISPORTS_KEY = getattr(config, 'APISPORTS_KEY', '')
        self.APISPORTS_HOST = getattr(config, 'APISPORTS_HOST', 'v2.nba.api-sports.io')

        # [PAID TIER] Initialize API Monitor
        self.monitor = get_monitor()

    def update_database(self):
        """
        Main Routine: Checks last update date, fetches missing days from Tank01,
        and appends new rows to the JSON database.
        """
        # 1. LOAD EXISTING DB
        if not os.path.exists(self.history_file):
            print("   ⚠️ No database found. Please run your Initializer (nba_api) first.")
            return

        try:
            df = pd.read_json(self.history_file)
            # Ensure Date column is datetime
            df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
            print(f"   📂 Loaded Database: {len(df)} rows.")
        except Exception as e:
            print(f"   ❌ Error loading DB: {e}")
            return

        # 2. DETERMINE MISSING DATES
        if df.empty:
            print("   ⚠️ Database is empty.")
            return

        last_date = df['GAME_DATE'].max()
        today = datetime.now()
        
        # Calculate days gap
        days_diff = (today - last_date).days
        
        # If last date is today or yesterday, we are likely fine.
        if days_diff < 1:
            print(f"   ✅ [HISTORIAN] Database is already up to date. (Last Game: {last_date.date()})")
            return
            
        print(f"   🗓️ Last recorded game: {last_date.strftime('%Y-%m-%d')}")
        print(f"   🔄 Fetching missing games for {days_diff} days...")

        # 3. FETCH & APPEND
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

        # 4. SAVE UPDATES
        if new_records:
            new_df = pd.DataFrame(new_records)
            
            # Smart Concat: Aligns columns automatically
            combined_df = pd.concat([df, new_df], ignore_index=True)
            
            # Format Date back to String for JSON safety
            combined_df['GAME_DATE'] = combined_df['GAME_DATE'].dt.strftime('%Y-%m-%d')
            
            # Save
            combined_df.to_json(self.history_file, orient='records', indent=4)
            print(f"\n   💾 SUCCESS: Added {len(new_records)} new rows to database.")
            print(f"   📈 New Total: {len(combined_df)} rows.")
        else:
            print("\n   ℹ️ No new data found to append.")

    def _fetch_tank01_boxscores(self, date_str):
        """
        Fetches all box scores for a specific date using Tank01.
        """
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
        url_box = f"https://{self.TANK_HOST}/getNBABoxScore"
        # We need fantasyPoints=true or false, doesn't matter, but standard box is safer
        params_box = {"gameID": game_id, "fantasyPoints": "false"}
        
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
                    "OREB": float(stats.get('oreb', 0)),
                    "DREB": float(stats.get('dreb', 0)),
                }
                storage_list.append(record)

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
                except:
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
    h = LudiHistorian()
    h.update_database()