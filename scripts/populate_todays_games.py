#!/usr/bin/env python3
"""
Populate Today's Games — 4-Source Fallback Chain
=================================================
Fetches today's NBA schedule and inserts into the games table.

Source priority:
  1. The Odds API  (current — real-time lines exist = games are on)
  2. Tank01        (getNBAGamesForDate — gameID already in YYYYMMDD_AWAY@HOME format)
  3. BDL           (get_games with date filter — home_team/visitor_team nested objects)
  4. ESPN          (free, no auth, no quota — DraftKings scoreboard via ESPNClient)

If all sources return 0 games, sends a Slack alert and exits with code 1
so downstream steps (Module H, simulation) don't run on an empty slate.
"""

import sys
import os
import sqlite3
import requests
from datetime import datetime
import pytz

# Add project root so we can import config and utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.mappings import TEAM_MAP, normalize_bdl_abbr

DB_PATH = 'ludi.db'
EST_TZ = pytz.timezone('US/Eastern')


def resolve_team(name: str) -> str:
    """Map full team name → 3-letter abbreviation. Falls back to first 3 chars."""
    return TEAM_MAP.get(name, name[:3].upper())


def normalize_abbrev(abbrev: str) -> str:
    """Normalize short-code abbreviations (Tank01/BDL) to standard NBA abbreviations."""
    return normalize_bdl_abbr(abbrev)


# ---------------------------------------------------------------------------
# Source 1: The Odds API
# ---------------------------------------------------------------------------

def fetch_from_odds_api(today_str: str, date_compact: str):
    """
    Fetch today's NBA games from The Odds API (/v4/sports/basketball_nba/odds).

    The Odds API only returns games that have active markets — so if it returns
    games, those are definitively real games scheduled today.

    Returns list of (game_id, game_date, home_team, away_team) tuples,
    or [] on failure / quota exhaustion.
    """
    print("[populate_games] Source 1: The Odds API...")
    url = 'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
    params = {
        'api_key': config.ODDS_API_KEY,
        'regions': 'us',
        'markets': 'h2h',   # Cheapest market — just need event metadata
        'oddsFormat': 'american',
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        games_to_insert = []
        for game in data:
            # Odds API timestamps are UTC — convert to EST date for our filter
            utc_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
            est_time = utc_time.astimezone(EST_TZ)
            game_date = est_time.strftime('%Y-%m-%d')

            if game_date == today_str:
                home_team = resolve_team(game['home_team'])
                away_team = resolve_team(game['away_team'])
                ludi_game_id = f"{est_time.strftime('%Y%m%d')}_{away_team}@{home_team}"
                games_to_insert.append((ludi_game_id, game_date, home_team, away_team))

        return games_to_insert

    except Exception as e:
        print(f"   [Odds API] Failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 2: Tank01
# ---------------------------------------------------------------------------

def fetch_from_tank01(today_str: str, date_compact: str):
    """
    Fetch today's NBA games from Tank01 getNBAGamesForDate.

    Tank01 gameID is already in YYYYMMDD_AWAY@HOME format (e.g. 20260220_BOS@MIA),
    so we parse it directly instead of rebuilding from team fields.

    Returns list of (game_id, game_date, home_team, away_team) tuples,
    or [] on failure.
    """
    print("[populate_games] Source 2: Tank01...")
    try:
        from utils.tank01_client import get_client
        client = get_client()
        raw_games = client.get_games_for_date(date_compact)  # YYYYMMDD format

        if not raw_games:
            print("   [Tank01] No games returned.")
            return []

        games_to_insert = []
        for game in raw_games:
            game_id = game.get('gameID', '')
            if not game_id:
                continue

            # gameID format: YYYYMMDD_AWAY@HOME (e.g. 20260220_BOS@MIA or 20260220_MIL@NO)
            # Normalize short codes (Tank01 uses NO/GS/SA etc.) then rebuild the ID
            # so our games table stays consistent with the rest of the codebase.
            try:
                date_part, matchup_part = game_id.split('_', 1)
                raw_away, raw_home = matchup_part.split('@', 1)
                home_team = normalize_abbrev(raw_home)
                away_team = normalize_abbrev(raw_away)
                game_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
                # Rebuild ludi_game_id with normalized abbreviations
                ludi_game_id = f"{date_part}_{away_team}@{home_team}"
                games_to_insert.append((ludi_game_id, game_date, home_team, away_team))
            except ValueError:
                # Unexpected format — fall back to top-level 'home'/'away' fields
                # (Tank01 game dicts have: {'gameID':..., 'home': 'ATL', 'away': 'MIA', ...})
                raw_home = game.get('home', '')
                raw_away = game.get('away', '')
                home_team = normalize_abbrev(raw_home)
                away_team = normalize_abbrev(raw_away)
                if home_team and away_team:
                    ludi_game_id = f"{date_compact}_{away_team}@{home_team}"
                    games_to_insert.append((ludi_game_id, today_str, home_team, away_team))
                else:
                    print(f"   [Tank01] Skipping malformed game entry: {game}")

        return games_to_insert

    except Exception as e:
        print(f"   [Tank01] Failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 3: Ball Don't Lie (BDL)
# ---------------------------------------------------------------------------

def fetch_from_bdl(today_str: str, date_compact: str):
    """
    Fetch today's NBA games from Ball Don't Lie v1 /games endpoint.

    BDL get_games(date='YYYY-MM-DD') returns a dict with a 'data' list.
    Each game dict has:
      - 'date': 'YYYY-MM-DDTHH:MM:SS.000Z'
      - 'home_team': {'abbreviation': 'BOS', 'full_name': 'Boston Celtics', ...}
      - 'visitor_team': {'abbreviation': 'MIA', 'full_name': 'Miami Heat', ...}

    BDL abbreviations are normalized by BDLClient automatically
    (GS→GSW, NO→NOP, NY→NYK, PHO→PHX, SA→SAS).

    Returns list of (game_id, game_date, home_team, away_team) tuples,
    or [] on failure.
    """
    print("[populate_games] Source 3: BDL...")
    try:
        from utils.bdl_client import get_games
        # BDL date filter uses YYYY-MM-DD format (same as today_str)
        raw = get_games(date=today_str)

        # get_games() returns the raw response dict: {'data': [...], 'meta': {...}}
        game_list = raw.get('data', []) if isinstance(raw, dict) else []

        if not game_list:
            print("   [BDL] No games returned.")
            return []

        games_to_insert = []
        for game in game_list:
            home_obj = game.get('home_team', {})
            away_obj = game.get('visitor_team', {})

            # BDLClient normalizes in _normalize_team_data(); we apply ours too as defense-in-depth
            home_team = normalize_abbrev(home_obj.get('abbreviation', ''))
            away_team = normalize_abbrev(away_obj.get('abbreviation', ''))

            if not home_team or not away_team:
                continue

            ludi_game_id = f"{date_compact}_{away_team}@{home_team}"
            games_to_insert.append((ludi_game_id, today_str, home_team, away_team))

        return games_to_insert

    except Exception as e:
        print(f"   [BDL] Failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Source 4: ESPN Scoreboard
# ---------------------------------------------------------------------------

def fetch_from_espn(today_str: str, date_compact: str):
    """
    Fetch today's NBA games from ESPN Scoreboard (free, no auth, no quota).

    Uses ESPNClient.get_scoreboard() which returns DraftKings game lines
    and already handles team ID → standard abbreviation mapping via canonical_teams.

    Returns list of (game_id, game_date, home_team, away_team) tuples,
    or [] on failure.
    """
    print("[populate_games] Source 4: ESPN...")
    try:
        from utils.espn_client import ESPNClient
        client = ESPNClient()
        scoreboard = client.get_scoreboard(date_str=date_compact)

        if not scoreboard:
            print("   [ESPN] No games returned.")
            return []

        games_to_insert = []
        for _game_key, game_data in scoreboard.items():
            home = game_data.get('home_abbr', '')
            away = game_data.get('away_abbr', '')
            if home and away:
                ludi_game_id = f"{date_compact}_{away}@{home}"
                games_to_insert.append((ludi_game_id, today_str, home, away))

        print(f"   [ESPN] {len(games_to_insert)} games found.")
        return games_to_insert

    except Exception as e:
        print(f"   [ESPN] Failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Database upsert
# ---------------------------------------------------------------------------

def update_database(games: list) -> int:
    """
    Upsert games into the games table.

    ON CONFLICT(game_id) updates home/away and date so stale rows get corrected.
    Returns the number of rows successfully written.
    """
    if not games:
        return 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    inserted = 0

    for g_id, g_date, home, away in games:
        print(f"   {away} @ {home}  ({g_id})")
        try:
            cursor.execute("""
                INSERT INTO games (game_id, date, home_team, away_team)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    date       = excluded.date,
                    home_team  = excluded.home_team,
                    away_team  = excluded.away_team
            """, (g_id, g_date, home, away))
            inserted += 1
        except Exception as e:
            print(f"   DB Error for {g_id}: {e}")

    conn.commit()
    conn.close()
    return inserted


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """
    Try each source in order. Insert the first successful result.
    Returns the count of games inserted (0 = failure).
    """
    now_est = datetime.now(EST_TZ)
    today_str = now_est.strftime('%Y-%m-%d')       # YYYY-MM-DD  (for DB + BDL)
    date_compact = now_est.strftime('%Y%m%d')      # YYYYMMDD    (for Tank01)

    print(f"[populate_games] Target date: {today_str}")

    # --- Source priority chain ---
    sources = [
        ("The Odds API", fetch_from_odds_api),
        ("Tank01",       fetch_from_tank01),
        ("BDL",          fetch_from_bdl),
        ("ESPN",         fetch_from_espn),   # Source 4: free, no quota
    ]

    games = []
    source_used = None

    for source_name, fetch_fn in sources:
        result = fetch_fn(today_str, date_compact)
        if result:
            games = result
            source_used = source_name
            break
        print(f"   [{source_name}] returned 0 games — trying next source...")

    # --- Banner ---
    print(f"[populate_games] Source: {source_used or 'NONE'} — {len(games)} games for {today_str}")

    if not games:
        msg = (
            f"*populate_todays_games.py FAILED*\n"
            f"All 4 sources returned 0 games for {today_str}.\n"
            f"Sources tried: The Odds API, Tank01, BDL, ESPN.\n"
            f"Downstream simulation pipeline may fail."
        )
        print(f"\n[populate_games] ERROR: {msg}")
        try:
            from utils.slack_notifier import send_slack_alert
            send_slack_alert("Games Table Empty", msg)
        except Exception as slack_err:
            print(f"[populate_games] Slack alert failed: {slack_err}")
        return 0

    # --- Write to DB ---
    print(f"[populate_games] Inserting {len(games)} games into games table...")
    inserted = update_database(games)
    print(f"[populate_games] Done. {inserted}/{len(games)} rows written.")
    return inserted


if __name__ == "__main__":
    count = main()
    if count == 0:
        sys.exit(1)
    sys.exit(0)
