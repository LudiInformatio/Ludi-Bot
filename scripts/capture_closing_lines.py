#!/usr/bin/env python3
"""
Forward CLV Capture Script v2.0

Captures closing odds before/near tipoff for CLV (Closing Line Value) calculation.
Runs 5 times per night (7:30–11:30 PM EST) and processes ALL uncaptured bets
on tonight's slate each run.

Sources:
    Primary:  The-Odds-API /odds endpoint (all 11 player prop markets, 1 call)
    Fallback: BDL /v2/odds/player_props per game (30-70% coverage)

Usage:
    python scripts/capture_closing_lines.py [--dry-run] [--verbose]
    python scripts/capture_closing_lines.py --game-date 2026-02-22
"""

import argparse
import json
import sqlite3
import sys
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import pytz

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import config

EST = pytz.timezone('US/Eastern')


def _game_is_on_slate(ev: Dict, game_date: str) -> bool:
    """
    Return True only if this Odds API event belongs on today's EST slate
    AND the game has not yet started (or started within the last 15 min grace window).

    Rejects:
    - Games with a commence_time date != game_date in EST (tomorrow's slate, yesterday)
    - Games that started >15 minutes ago (in-game odds are not closing lines)
    """
    ct = ev.get('commence_time', '')
    if not ct:
        return True  # No time data — allow through conservatively
    try:
        game_utc = datetime.fromisoformat(ct.replace('Z', '+00:00'))
        game_est_date = game_utc.astimezone(EST).strftime('%Y-%m-%d')
        if game_est_date != game_date:
            return False  # Different date (tomorrow or yesterday) — skip
        now_utc = datetime.now(timezone.utc)
        if game_utc < now_utc - timedelta(minutes=15):
            return False  # Game started >15 min ago — lines are live/already closed
        return True
    except Exception:
        return True  # Parse error — allow through conservatively


# Quota cache — persists x-requests-remaining between runs to skip Odds API when exhausted
QUOTA_CACHE_PATH = project_root / 'cache' / 'odds_api_quota.json'


def _cache_quota(remaining: str) -> None:
    """Write quota remaining to disk so next run skips Odds API if exhausted."""
    try:
        QUOTA_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(QUOTA_CACHE_PATH, 'w') as f:
            json.dump({"remaining": str(remaining), "at": datetime.now().isoformat()}, f)
    except Exception:
        pass


def _read_cached_quota() -> Optional[str]:
    """Read last known quota remaining. Returns None if cache missing or unreadable."""
    try:
        if QUOTA_CACHE_PATH.exists():
            return str(json.loads(QUOTA_CACHE_PATH.read_text()).get("remaining", "unknown"))
    except Exception:
        pass
    return None


# High-quality vendor filter — matches module_a.py BDL quality gate
HIGH_QUALITY_VENDORS = ['draftkings', 'fanduel', 'caesars', 'betrivers', 'betmgm']

# Odds API market key → internal stat code
ODDS_API_MARKET_TO_STAT = {
    'player_points':                    'pts',
    'player_rebounds':                  'reb',
    'player_assists':                   'ast',
    'player_threes':                    '3pm',
    'player_steals':                    'stl',
    'player_blocks':                    'blk',
    'player_turnovers':                 'tov',
    'player_points_rebounds_assists':   'pra',
    'player_points_rebounds':           'pr',
    'player_points_assists':            'pa',
    'player_rebounds_assists':          'ra',
}

# BDL prop_type → internal stat code
BDL_PROP_TO_STAT = {
    'points':                   'pts',
    'rebounds':                 'reb',
    'assists':                  'ast',
    'threes':                   '3pm',
    'steals':                   'stl',
    'blocks':                   'blk',
    'turnovers':                'tov',
    'points_rebounds_assists':  'pra',
    'points_rebounds':          'pr',
    'points_assists':           'pa',
    'rebounds_assists':         'ra',
}


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def american_to_decimal(american_odds: Optional[int]) -> Optional[float]:
    """Convert American odds to decimal. Returns None for None input."""
    if american_odds is None:
        return None
    if american_odds >= 0:
        return 1 + (american_odds / 100)
    return 1 + (100 / abs(american_odds))


def calculate_clv(bet_decimal: Optional[float], closing_decimal: Optional[float]) -> float:
    """CLV in cents: (your_decimal - closing_decimal) × 100. Returns 0.0 on missing data."""
    if bet_decimal is None or closing_decimal is None:
        return 0.0
    return (bet_decimal - closing_decimal) * 100


# ---------------------------------------------------------------------------
# Step 1: One-time database migration — add CLV columns if missing
# ---------------------------------------------------------------------------

def ensure_clv_columns(conn: sqlite3.Connection) -> None:
    """
    Add CLV capture columns to bet_recommendations if they don't exist.

    The table was created before these columns were added to the schema,
    so they need to be added via ALTER TABLE. Safe to run every time —
    the except block silently ignores 'duplicate column' errors.
    """
    columns_to_add = [
        ("closing_odds_over",  "INTEGER"),
        ("closing_odds_under", "INTEGER"),
        ("clv_cents",          "REAL"),
        ("closing_time",       "TEXT"),
    ]
    c = conn.cursor()
    for col_name, col_type in columns_to_add:
        try:
            c.execute(f"ALTER TABLE bet_recommendations ADD COLUMN {col_name} {col_type}")
            print(f"  [MIGRATION] Added: bet_recommendations.{col_name} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists — expected on every run after first
    conn.commit()


# ---------------------------------------------------------------------------
# Step 2: Fetch closing data — two-step Odds API call (primary)
# ---------------------------------------------------------------------------

PLAYER_PROP_MARKETS = (
    'player_points,player_rebounds,player_assists,player_threes,'
    'player_steals,player_blocks,player_turnovers,'
    'player_points_rebounds_assists,player_points_rebounds,'
    'player_points_assists,player_rebounds_assists'
)


def _odds_api_get(url: str, params: dict) -> Optional[dict]:
    """
    Single Odds API GET with quota header logging and 401 guard.
    Returns parsed JSON or None on any failure.
    """
    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 401:
            remaining = response.headers.get('x-requests-remaining', 'unknown')
            print(f"  Odds API 401 — quota exhausted or key invalid "
                  f"(quota remaining: {remaining})")
            return None

        response.raise_for_status()
        remaining = response.headers.get('x-requests-remaining', 'unknown')
        used = response.headers.get('x-requests-used', 'unknown')
        print(f"  Odds API quota: {remaining} remaining, {used} used")
        _cache_quota(remaining)  # persist so next run can skip if exhausted
        return response.json()

    except Exception as e:
        print(f"  Odds API request failed: {e}")
        return None


def fetch_all_closing_data(pending_bets: List[Dict], verbose: bool = False) -> List[Dict]:
    """
    Two-step Odds API fetch for player prop closing lines.

    Step 1: GET /sports/basketball_nba/events → game list with Odds API UUIDs
            (cheap — 1 API credit, game-level only)
    Step 2: GET /events/{id}/odds with player prop markets, only for games
            that have pending bets (1 credit/game, typically 2-6 games/night)

    Player prop markets are ONLY available via the per-event endpoint —
    NOT from the bulk /odds endpoint (which returns game-level markets only).
    This matches the pattern in module_a.py:397.

    Returns: list of normalized game dicts.
    """
    # Pre-flight: skip Odds API entirely if last run reported quota = 0
    cached_quota = _read_cached_quota()
    if cached_quota == "0":
        print("  Odds API: quota exhausted (cached) — skipping to BDL fallback")
        return []

    base = f"https://api.the-odds-api.com/v4/sports/basketball_nba"

    # Build set of tonight's (away, home) pairs from pending bets for matching
    tonight_pairs = set()
    for bet in pending_bets:
        parts = bet.get('game_id', '').split('_vs_')
        if len(parts) == 2:
            tonight_pairs.add((parts[0].strip(), parts[1].strip()))  # (away, home)

    # Step 1: Get game event IDs
    events_data = _odds_api_get(
        f"{base}/events",
        {'api_key': config.ODDS_API_KEY}
    )
    if not events_data:
        return []

    # Match events to tonight's pending games — reject live games and future-date games
    matched_events = [
        ev for ev in events_data
        if (ev.get('away_team', ''), ev.get('home_team', '')) in tonight_pairs
        and _game_is_on_slate(ev, game_date)
    ]

    # Log any live/future-date games that were filtered out (verbose only)
    if verbose:
        skipped_live = [
            ev for ev in events_data
            if (ev.get('away_team', ''), ev.get('home_team', '')) in tonight_pairs
            and not _game_is_on_slate(ev, game_date)
        ]
        for ev in skipped_live:
            print(f"  Odds API: SKIPPED live/future game — "
                  f"{ev.get('away_team')} @ {ev.get('home_team')} "
                  f"(commence: {ev.get('commence_time', 'unknown')})")

    if not matched_events:
        print(f"  Odds API: no events matched tonight's {len(tonight_pairs)} pending game(s)")
        return []

    print(f"  Odds API: matched {len(matched_events)} event(s) to pending bets")

    # Step 2: Fetch player props per matched game
    normalized = []
    for ev in matched_events:
        game_id   = ev['id']
        away_team = ev.get('away_team', '')
        home_team = ev.get('home_team', '')

        props_data = _odds_api_get(
            f"{base}/events/{game_id}/odds",
            {
                'api_key':    config.ODDS_API_KEY,
                'regions':    'us,us2',
                'markets':    PLAYER_PROP_MARKETS,
                'oddsFormat': 'american',
            }
        )

        if props_data:
            normalized.append(normalize_odds_api_game(props_data))
            if verbose:
                n_players = len(normalized[-1].get('players', {}))
                print(f"    {away_team} @ {home_team}: {n_players} players with props")
        else:
            print(f"    {away_team} @ {home_team}: props fetch failed, skipping")

    return normalized


# ---------------------------------------------------------------------------
# Step 9: BDL fallback — correct player props endpoint
# ---------------------------------------------------------------------------

def _get_bdl_player_names(bdl_client) -> Dict[int, str]:
    """
    Build {bdl_player_id: full_name} map for prop matching.
    Paginates through BDL /v1/players. File-cached for 24h.
    """
    cache_path = Path("cache/bdl/player_name_cache.json")

    # Try disk cache first (24h TTL)
    if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < 86400:
        try:
            with open(cache_path) as f:
                return {int(k): v for k, v in json.load(f).items()}
        except Exception:
            pass

    # Fetch from BDL — paginate (100 players/page, max 20 pages = 2000 players)
    all_players: Dict[int, str] = {}
    cursor = None

    for _ in range(20):
        params: Dict = {"per_page": 100}
        if cursor:
            params["cursor"] = cursor
        try:
            resp = bdl_client.session.get(
                f"{bdl_client.BASE_URL_V1}/players", params=params, timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            for p in data.get("data", []):
                full_name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
                all_players[p["id"]] = full_name
            cursor = data.get("meta", {}).get("next_cursor")
            if not cursor:
                break
        except Exception as e:
            print(f"  BDL players page failed: {e}")
            break

    if all_players:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_path, "w") as f:
                json.dump(all_players, f)
        except Exception:
            pass

    print(f"  BDL player name map: {len(all_players)} players")
    return all_players


def fetch_bdl_games_today(game_date: str) -> Tuple[List[Dict], Optional[object]]:
    """Get today's BDL games + return the BDLClient instance for reuse."""
    try:
        from utils.bdl_client import BDLClient
        bdl = BDLClient()
        resp = bdl.get_games(date=game_date)
        all_games = resp.get('data', [])
        games = []
        for g in all_games:
            # BDL V2 uses numeric status codes: "1"=upcoming, "2"=in-progress, "3"=final
            # (NOT string names like "Scheduled" or "Pre-Game")
            if str(g.get('status', '1')) in ('2', '3'):
                continue
            games.append(g)
        skipped_count = len(all_games) - len(games)
        if skipped_count > 0:
            print(f"  BDL: {skipped_count} in-progress/final game(s) skipped "
                  f"(status 2/3 — lines already closed)")
        print(f"  BDL: {len(games)} scheduled game(s) for {game_date}")
        return games, bdl
    except Exception as e:
        print(f"  BDL games fetch failed: {e}")
        return [], None


# ---------------------------------------------------------------------------
# Normalization — convert both sources to flat player lookup format
# ---------------------------------------------------------------------------

def normalize_odds_api_game(api_game: Dict) -> Dict:
    """
    Convert Odds API game structure to normalized format:
      {home_team, away_team, source, players: {name: {stat: {line, over_odds, under_odds}}}}

    Iterates all bookmakers and accumulates the first over AND under odds found
    for each player/stat/line combo. First bookmaker with real odds wins.
    """
    players: Dict[str, Dict] = {}

    for bookmaker in api_game.get('bookmakers', []):
        for market in bookmaker.get('markets', []):
            stat_key = ODDS_API_MARKET_TO_STAT.get(market.get('key', ''))
            if not stat_key:
                continue

            for outcome in market.get('outcomes', []):
                player_name = outcome.get('description', '').strip()
                if not player_name:
                    continue

                line  = outcome.get('point')
                price = outcome.get('price')
                side  = outcome.get('name', '').lower()

                if player_name not in players:
                    players[player_name] = {}
                if stat_key not in players[player_name]:
                    players[player_name][stat_key] = {
                        'line': line, 'over_odds': None, 'under_odds': None
                    }

                slot = players[player_name][stat_key]
                if line == slot['line']:
                    if side == 'over'  and slot['over_odds']  is None:
                        slot['over_odds']  = price
                    elif side == 'under' and slot['under_odds'] is None:
                        slot['under_odds'] = price

    return {
        'home_team': api_game.get('home_team', ''),
        'away_team': api_game.get('away_team', ''),
        'source':    'odds_api',
        'players':   players,
    }


def normalize_bdl_game(bdl_props: List[Dict], home_team: str, away_team: str,
                       player_name_map: Dict[int, str]) -> Dict:
    """
    Convert BDL player props list to normalized format.
    Applies same vendor/market-type/odds-range guards as module_a._parse_bdl_props().
    """
    players: Dict[str, Dict] = {}

    for prop in bdl_props:
        # Market type guard: skip milestone markets (have corrupt single odds)
        if prop.get('market', {}).get('type') != 'over_under':
            continue

        player_id   = prop.get('player_id')
        player_name = player_name_map.get(player_id, '')
        if not player_name:
            continue

        stat_key = BDL_PROP_TO_STAT.get(prop.get('prop_type', ''))
        if not stat_key:
            continue

        line       = float(prop.get('line_value', 0))
        over_odds  = prop.get('market', {}).get('over_odds')
        under_odds = prop.get('market', {}).get('under_odds')

        # Odds range guard: abs < 100 means truncated/corrupt (known BDL bug)
        if over_odds is None or under_odds is None:
            continue
        if abs(over_odds) < 100 or abs(under_odds) < 100:
            continue

        if player_name not in players:
            players[player_name] = {}
        # First prop entry per stat wins (already vendor-filtered upstream)
        if stat_key not in players[player_name]:
            players[player_name][stat_key] = {
                'line': line, 'over_odds': over_odds, 'under_odds': under_odds
            }

    return {
        'home_team': home_team,
        'away_team': away_team,
        'source':    'bdl',
        'players':   players,
    }


# ---------------------------------------------------------------------------
# Step 3: Match normalized games to pending bets by team name
# ---------------------------------------------------------------------------

def match_games_to_bets(normalized_games: List[Dict], pending_bets: List[Dict]) -> Dict[int, List]:
    """
    Match normalized game dicts to pending bets by parsing game_id.

    bet_recommendations.game_id format: "{away}_vs_{home}" (full team names)
    e.g. "Los Angeles Lakers_vs_Golden State Warriors"

    This matches against normalized_game['away_team'] and ['home_team'].
    No time window — captures lines for ALL uncaptured bets on the slate.
    """
    matched: Dict[int, List] = {}

    for i, game in enumerate(normalized_games):
        api_home = game.get('home_team', '')
        api_away = game.get('away_team', '')

        game_bets = []
        for bet in pending_bets:
            parts = bet.get('game_id', '').split('_vs_')
            if len(parts) == 2:
                bet_away = parts[0].strip()
                bet_home = parts[1].strip()
                if bet_home == api_home and bet_away == api_away:
                    game_bets.append(bet)

        if game_bets:
            matched[i] = game_bets

    return matched


# ---------------------------------------------------------------------------
# Database operations
# ---------------------------------------------------------------------------

def get_pending_bets(conn: sqlite3.Connection, game_date: str = None) -> List[Dict]:
    """Get bets that haven't had closing lines captured yet."""
    c = conn.cursor()
    if game_date:
        c.execute('''
            SELECT id, player_name, team, stat_category, bet_side,
                   line, odds_over, odds_under, game_id, game_date
            FROM bet_recommendations
            WHERE outcome IS NULL
              AND game_date = ?
              AND (closing_odds_over IS NULL OR closing_odds_over = 0)
            ORDER BY player_name
        ''', (game_date,))
    else:
        c.execute('''
            SELECT id, player_name, team, stat_category, bet_side,
                   line, odds_over, odds_under, game_id, game_date
            FROM bet_recommendations
            WHERE outcome IS NULL
              AND (closing_odds_over IS NULL OR closing_odds_over = 0)
            ORDER BY game_date, player_name
        ''')
    cols = [d[0] for d in c.description]
    return [dict(zip(cols, row)) for row in c.fetchall()]


def update_bet_with_closing_lines(conn: sqlite3.Connection, bet_id: int,
                                   closing_over: Optional[int], closing_under: Optional[int],
                                   clv_cents: float, closing_time: str) -> None:
    c = conn.cursor()
    c.execute('''
        UPDATE bet_recommendations
        SET closing_odds_over  = ?,
            closing_odds_under = ?,
            clv_cents          = ?,
            closing_time       = ?
        WHERE id = ?
    ''', (closing_over, closing_under, clv_cents, closing_time, bet_id))
    conn.commit()


# ---------------------------------------------------------------------------
# Steps 4–6: Fixed match + CLV calculation
# ---------------------------------------------------------------------------

def match_closing_lines(bet: Dict, normalized_game: Dict) -> Tuple[Optional[int], Optional[int]]:
    """
    Look up closing odds for this bet from normalized game data.
    Returns (closing_over_odds, closing_under_odds).

    Improvement over original: O(1) dict lookup instead of O(n³) nested loop.
    Includes case-insensitive fallback for name mismatches.
    """
    player_name = bet['player_name'].strip()
    stat_cat    = bet['stat_category'].lower()
    bet_line    = bet['line']

    players = normalized_game.get('players', {})

    # Exact match first
    player_data = players.get(player_name)

    # Case-insensitive fallback (handles e.g. "Nikola Jokić" vs "Nikola Jokic")
    if not player_data:
        player_name_lower = player_name.lower()
        for pname, pdata in players.items():
            if pname.lower() == player_name_lower:
                player_data = pdata
                break

    if not player_data:
        return None, None

    stat_data = player_data.get(stat_cat)
    if not stat_data:
        return None, None

    # Verify line matches (float tolerance for 27.5 == 27.5 comparisons)
    if abs((stat_data.get('line') or -999) - bet_line) > 0.01:
        return None, None

    return stat_data.get('over_odds'), stat_data.get('under_odds')


def process_game(conn: sqlite3.Connection, normalized_game: Dict, bets: List[Dict],
                 dry_run: bool = False, verbose: bool = False) -> Dict:
    """Process closing lines for all bets in one game."""
    updated      = 0
    skipped      = 0
    closing_time = datetime.now(EST).isoformat()
    source       = normalized_game.get('source', 'unknown')

    for bet in bets:
        closing_over, closing_under = match_closing_lines(bet, normalized_game)

        if closing_over is None and closing_under is None:
            skipped += 1
            if verbose:
                print(f"  SKIP  {bet['player_name']} {bet['stat_category']} "
                      f"{bet['bet_side']} {bet['line']} — no match [{source}]")
            continue

        # Step 5: Use the correct side's bet odds for CLV (not always over_odds)
        if bet['bet_side'] == 'OVER':
            bet_decimal = american_to_decimal(bet.get('odds_over'))
        elif bet['bet_side'] == 'UNDER':
            bet_decimal = american_to_decimal(bet.get('odds_under'))
        else:
            bet_decimal = None

        if bet['bet_side'] == 'OVER' and closing_over is not None:
            clv = calculate_clv(bet_decimal, american_to_decimal(closing_over))
        elif bet['bet_side'] == 'UNDER' and closing_under is not None:
            clv = calculate_clv(bet_decimal, american_to_decimal(closing_under))
        else:
            clv = 0.0

        if not dry_run:
            update_bet_with_closing_lines(
                conn, bet['id'], closing_over, closing_under, clv, closing_time
            )

        updated += 1
        if verbose:
            print(f"  ✅    {bet['player_name']} {bet['stat_category']} "
                  f"{bet['bet_side']} {bet['line']} | CLV: {clv:+.2f}c [{source}]")

    return {'updated': updated, 'skipped': skipped}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Capture closing lines for CLV tracking')
    parser.add_argument('--dry-run',   action='store_true', help='Simulate — no DB writes')
    parser.add_argument('--verbose',   action='store_true', help='Print per-bet detail')
    parser.add_argument('--game-date', type=str, default=None,
                        help='Process bets for specific date (YYYY-MM-DD). Defaults to today EST.')
    args = parser.parse_args()

    print("=" * 60)
    print("CLV CAPTURE SCRIPT v2.0 | Forward Line Capture")
    print("=" * 60)
    if args.dry_run:
        print("⚠️  DRY RUN — no database writes")

    db_path = project_root / 'ludi.db'
    if not db_path.exists():
        print("❌ Database not found")
        sys.exit(1)

    # Use today's EST date unless explicitly provided
    game_date = args.game_date or datetime.now(EST).strftime('%Y-%m-%d')
    print(f"  Game date: {game_date}")

    # Step 7: Context manager ensures connection is always closed cleanly
    with sqlite3.connect(str(db_path)) as conn:

        # Step 1: Ensure CLV columns exist (safe one-time migration)
        ensure_clv_columns(conn)

        # Get all pending uncaptured bets for today
        pending_bets = get_pending_bets(conn, game_date=game_date)
        if not pending_bets:
            print("No pending uncaptured bets — nothing to do")
            return  # exit 0, not an error

        print(f"Found {len(pending_bets)} uncaptured bets")

        # Step 2: Fetch closing data — Odds API primary
        normalized_games: List[Dict] = []
        api_games = fetch_all_closing_data(pending_bets, verbose=args.verbose)

        if api_games:
            normalized_games = api_games  # Already normalized inside fetch_all_closing_data()
            print(f"  Using {len(normalized_games)} game(s) from Odds API")

        else:
            # Step 9: BDL fallback — uses correct /v2/odds/player_props endpoint
            print("Falling back to BDL player props...")
            bdl_games, bdl = fetch_bdl_games_today(game_date)

            if bdl_games and bdl:
                player_name_map = _get_bdl_player_names(bdl)

                for bdl_game in bdl_games:
                    bdl_game_id = bdl_game.get('id')
                    props = bdl.get_player_props(bdl_game_id, vendors=HIGH_QUALITY_VENDORS)

                    if props:
                        home_name = bdl_game.get('home_team', {}).get('full_name', '')
                        away_name = bdl_game.get('visitor_team', {}).get('full_name', '')
                        normalized = normalize_bdl_game(props, home_name, away_name, player_name_map)
                        if normalized['players']:
                            normalized_games.append(normalized)
                            if args.verbose:
                                print(f"    BDL: {away_name} @ {home_name} "
                                      f"— {len(normalized['players'])} players")

        # Step 8: Exit non-zero if we have bets but couldn't get any source data
        if not normalized_games:
            if _read_cached_quota() == "0":
                # Odds API quota exhausted is a known monthly event (documented in ROADMAP.md).
                # BDL had no upcoming games with props — all games likely completed.
                # Exit cleanly — this is expected noise, not a real pipeline failure.
                print("Odds API quota exhausted (expected monthly event) — "
                      "no BDL props available for completed games. Exiting cleanly.")
                sys.exit(0)
            print("ERROR: Could not fetch closing data from Odds API or BDL")
            sys.exit(1)

        # Step 3: Match normalized games to pending bets by team name
        game_bet_map = match_games_to_bets(normalized_games, pending_bets)

        if not game_bet_map:
            if _read_cached_quota() == "0":
                print("Odds API quota exhausted — BDL game(s) found but none matched "
                      "pending bets (games likely already completed). Exiting cleanly.")
                sys.exit(0)
            print(f"WARNING: No API games matched to pending bets "
                  f"(checked {len(normalized_games)} games)")
            if args.verbose:
                print("  First 3 pending bet game_ids:")
                for b in pending_bets[:3]:
                    print(f"    {b['game_id']}")
                print("  First 3 API games:")
                for ng in normalized_games[:3]:
                    print(f"    {ng['away_team']} @ {ng['home_team']}")
            sys.exit(1)

        print(f"Matched {len(game_bet_map)} game(s)")

        # Process each matched game — Step 7: try/except per game
        total_updated = 0
        total_skipped = 0

        for game_idx, bets in game_bet_map.items():
            game = normalized_games[game_idx]
            print(f"\nGame: {game['away_team']} @ {game['home_team']} "
                  f"[{game['source']}] — {len(bets)} bets")
            try:
                result = process_game(
                    conn, game, bets, dry_run=args.dry_run, verbose=args.verbose
                )
                total_updated += result['updated']
                total_skipped += result['skipped']
                print(f"  → {result['updated']} updated, {result['skipped']} skipped")
            except Exception as e:
                print(f"  ERROR processing game: {e}")
                total_skipped += len(bets)

        print("\n" + "=" * 60)
        print(f"SUMMARY | Updated: {total_updated} | Skipped: {total_skipped}")
        print("=" * 60)

        # Step 8: Non-zero exit when we had bets but captured nothing
        if total_updated == 0 and len(pending_bets) > 0:
            if _read_cached_quota() == "0":
                # BDL props matched a game but no individual bet lines aligned —
                # BDL coverage is 30-70% and props may not be available for all markets.
                # Quota exhaustion is a known monthly event — exit cleanly.
                print("Odds API quota exhausted — matched game(s) had no prop line "
                      "matches (BDL coverage ~30-70%). Exiting cleanly.")
                sys.exit(0)
            print("WARNING: Had pending bets but captured 0 closing lines")
            print("  This likely means the game lines don't match our bet game_ids,")
            print("  or all props were filtered out. Run with --verbose for details.")
            sys.exit(1)


if __name__ == "__main__":
    main()
