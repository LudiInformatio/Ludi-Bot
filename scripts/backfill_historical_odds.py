#!/usr/bin/env python3
"""
Historical CLV Backfill Script v1.0

Populates closing_odds_over, closing_odds_under, clv_cents, closing_time,
and line_movement for all settled bets missing CLV data.

Uses The-Odds-API /v4/historical/ endpoint (10 credits/call).
Raw JSON is cached to cache/historical_odds/{date}_{event_id}.json so
re-runs after partial failures cost zero additional credits.

Credit budget:
    ~3,000 credits for full 2025-26 CLV gap (Jan 7 – Feb 22, ~47 dates)
    3,000 reserve held for live pipeline — script stops when quota < QUOTA_RESERVE

Key difference vs live capture (capture_closing_lines.py):
    - Base URL: /v4/historical/  (not /v4/sports/)
    - Events response: resp.json()['data']  (wrapped in 'data' key)
    - Props response: resp.json()['data']['bookmakers']
    - Props call uses date=commence_time → snapshot at game start = closing line
    - Cost: 10 credits/call  (vs 1 credit live)

Usage:
    python scripts/backfill_historical_odds.py               # All settled bets missing CLV
    python scripts/backfill_historical_odds.py --dry-run     # Preview, no DB writes
    python scripts/backfill_historical_odds.py --date 2026-01-07
    python scripts/backfill_historical_odds.py --from 2026-01-07 --to 2026-01-31
    python scripts/backfill_historical_odds.py --verbose
"""

import argparse
import json
import sqlite3
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Project root setup
# ---------------------------------------------------------------------------
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import config

# ---------------------------------------------------------------------------
# API key — use dedicated backfill key if set, fall back to primary key.
# Set ODDS_API_KEY_BACKFILL in .env to isolate backfill quota from live pipeline.
# When using a temp/trial key for backfill, set --reserve 0 (no live pipeline on that key).
# ---------------------------------------------------------------------------
import os as _os
_BACKFILL_KEY = _os.getenv('ODDS_API_KEY_BACKFILL') or config.ODDS_API_KEY
_KEY_SOURCE    = 'ODDS_API_KEY_BACKFILL' if _os.getenv('ODDS_API_KEY_BACKFILL') else 'ODDS_API_KEY (primary)'

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL = 'https://api.the-odds-api.com/v4/historical'
CACHE_DIR = project_root / 'cache' / 'historical_odds'

# Stop if quota drops below this — protect the live pipeline reserve.
# Override with --reserve 0 when using a dedicated backfill key (ODDS_API_KEY_BACKFILL).
QUOTA_RESERVE = 3000

# Bookmaker priority for CLV benchmark — sharp/P2P first, NC Legal as coverage fallback
# Pinnacle (eu region) = sharpest global market-maker, ~3-4% vig (CLV slightly understated)
# Novig/ProphetX (us_ex region) = zero-vig exchanges — market price IS fair price
# NC Legal books (us/us2 region) only fire when sharp/P2P have no data for that prop
PREFERRED_BOOKS = [
    'pinnacle',         # Sharp Tier — sharpest market-maker globally (eu region)
    'novig',            # P2P Tier — zero-vig exchange (us_ex region)
    'prophetx',         # P2P Tier — zero-vig exchange (us_ex region)
    'bovada',           # Sharp Tier fallback (eu region)
    'fanduel',          # NC Legal — coverage fallback only (FD before DK — sharper lines)
    'draftkings',
    'betmgm',
    'williamhill_us',
    'caesars',
]

# ---------------------------------------------------------------------------
# Constants copied verbatim from capture_closing_lines.py
# ---------------------------------------------------------------------------

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

PLAYER_PROP_MARKETS = (
    'player_points,player_rebounds,player_assists,player_threes,'
    'player_steals,player_blocks,player_turnovers,'
    'player_points_rebounds_assists,player_points_rebounds,'
    'player_points_assists,player_rebounds_assists'
)


# ---------------------------------------------------------------------------
# Math helpers — copied verbatim from capture_closing_lines.py
# ---------------------------------------------------------------------------

def american_to_decimal(american_odds: Optional[int]) -> Optional[float]:
    """Convert American odds to decimal. Returns None for None input."""
    if american_odds is None:
        return None
    if american_odds >= 0:
        return 1 + (american_odds / 100)
    return 1 + (100 / abs(american_odds))


def calculate_clv(bet_decimal: Optional[float], closing_decimal: Optional[float]) -> Optional[float]:
    """CLV in cents: (your_decimal - closing_decimal) × 100.
    Returns None when either input is missing — NULL in DB means 'no data',
    not 'broke even' (0.0 is a real signal; NULL is unknown).
    """
    if bet_decimal is None or closing_decimal is None:
        return None
    return (bet_decimal - closing_decimal) * 100


def _strip_accents(s: str) -> str:
    """Remove accents/diacritics from string for matching across APIs."""
    if not s:
        return s
    return ''.join(c for c in unicodedata.normalize('NFKD', s)
                   if unicodedata.category(c) != 'Mn')


# ---------------------------------------------------------------------------
# Migration guard — copied verbatim from capture_closing_lines.py
# ---------------------------------------------------------------------------

def ensure_clv_columns(conn: sqlite3.Connection) -> None:
    """Add CLV capture columns to bet_recommendations if they don't exist.
    Safe to run every time — silently skips columns that already exist.
    """
    columns_to_add = [
        ("closing_odds_over",  "INTEGER"),
        ("closing_odds_under", "INTEGER"),
        ("clv_cents",          "REAL"),
        ("closing_time",       "TEXT"),
        ("line_movement",      "REAL"),
        ("closing_book",       "TEXT"),   # Which book provided the CLV benchmark (pinnacle/novig/draftkings/etc)
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
# Cache helpers
# ---------------------------------------------------------------------------

def _load_cache(date_str: str, event_id: str) -> Optional[List]:
    """Return cached bookmakers list for this event, or None if not cached."""
    path = CACHE_DIR / f"{date_str}_{event_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def _save_cache(date_str: str, event_id: str, bookmakers: List) -> None:
    """Cache raw bookmakers list for this event to disk.
    Called BEFORE any DB writes so re-runs after crashes cost zero credits.
    """
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{date_str}_{event_id}.json").write_text(
            json.dumps(bookmakers, indent=2)
        )
    except Exception as e:
        print(f"  [CACHE] Write failed for {date_str}_{event_id}: {e}")


def _load_events_cache(date_str: str) -> Optional[List]:
    """Return cached events list for this date, or None if not cached.
    Events for past dates are static — safe to cache indefinitely.
    """
    path = CACHE_DIR / f"{date_str}_events.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def _save_events_cache(date_str: str, events: List) -> None:
    """Cache events list for this date to disk (10 credits saved on every re-run)."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / f"{date_str}_events.json").write_text(
            json.dumps(events, indent=2)
        )
    except Exception as e:
        print(f"  [CACHE] Events write failed for {date_str}: {e}")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _build_team_map(conn: sqlite3.Connection) -> Dict[str, str]:
    """Returns {full_name: standard_abbr}, e.g. {'Boston Celtics': 'BOS'}.
    Queried from canonical_teams — the single source of truth for team mappings.
    """
    rows = conn.execute(
        "SELECT standard_abbr, full_name FROM canonical_teams"
    ).fetchall()
    return {row['full_name']: row['standard_abbr'] for row in rows}


def _get_pending_dates(conn: sqlite3.Connection,
                        from_date: Optional[str] = None,
                        to_date: Optional[str] = None) -> List[Tuple[str, int]]:
    """Returns [(game_date, bet_count)] for settled bets missing CLV, oldest-first."""
    query = '''
        SELECT game_date, COUNT(*) as cnt
        FROM bet_recommendations
        WHERE closing_odds_over IS NULL
          AND outcome IN ('WIN', 'LOSS', 'PUSH')
          AND game_date < date('now')
    '''
    params = []
    if from_date:
        query += " AND game_date >= ?"
        params.append(from_date)
    if to_date:
        query += " AND game_date <= ?"
        params.append(to_date)
    query += " GROUP BY game_date ORDER BY game_date ASC"
    return [(row['game_date'], row['cnt'])
            for row in conn.execute(query, params).fetchall()]


# ---------------------------------------------------------------------------
# Quota guard
# ---------------------------------------------------------------------------

def _check_quota(remaining) -> bool:
    """Return True if safe to continue using the default QUOTA_RESERVE."""
    return _check_quota_with_reserve(remaining, QUOTA_RESERVE)


def _check_quota_with_reserve(remaining, reserve: int) -> bool:
    """Return True if safe to continue (quota above reserve), False if not.
    Returns True on unknown quota — proceed conservatively rather than stalling.
    """
    try:
        return int(remaining) >= reserve
    except (TypeError, ValueError):
        return True  # Unknown quota — proceed conservatively


# ---------------------------------------------------------------------------
# Odds API helpers
# ---------------------------------------------------------------------------

def _fetch_events(date_str: str, session: requests.Session) -> Tuple[List, str]:
    """
    Fetch NBA events for a date via the historical endpoint.
    GET /v4/historical/sports/basketball_nba/events?date={noon_utc}

    Using noon UTC captures all events visible for that calendar date regardless
    of timezone. Cost: 10 credits.

    Returns: (events_list, quota_remaining_str)
    """
    resp = session.get(
        f'{BASE_URL}/sports/basketball_nba/events',
        params={
            'apiKey':  _BACKFILL_KEY,
            'date':    f'{date_str}T12:00:00Z',  # noon UTC — full day visible
            'regions': 'us',
            'markets': 'h2h',                    # minimal — just need IDs + commence_times
        },
        timeout=20
    )
    remaining = resp.headers.get('x-requests-remaining', 'unknown')
    resp.raise_for_status()
    # Historical endpoint wraps the data: resp.json() = {'data': [...], 'timestamp': ...}
    return resp.json().get('data', []), remaining


def _fetch_props(event_id: str, commence_time: str,
                 session: requests.Session) -> Tuple[List, str]:
    """
    Fetch player prop closing lines for one event via the historical endpoint.
    GET /v4/historical/sports/basketball_nba/events/{id}/odds?date={commence_time}

    date=commence_time is critical: it requests the odds snapshot AT game start,
    which is the true closing line (most efficient market price before tip-off).

    Cost: 10 credits.
    Returns: (bookmakers_list, quota_remaining_str)
    """
    resp = session.get(
        f'{BASE_URL}/sports/basketball_nba/events/{event_id}/odds',
        params={
            'apiKey':     _BACKFILL_KEY,
            'date':       commence_time,    # CRITICAL: game-start snapshot = closing line
            'regions':    'us,us2,eu,us_ex',  # eu=Pinnacle, us_ex=Novig/ProphetX — flat 10c/game regardless
            'markets':    PLAYER_PROP_MARKETS,
            'oddsFormat': 'american',
        },
        timeout=20
    )
    remaining = resp.headers.get('x-requests-remaining', 'unknown')
    resp.raise_for_status()
    # Historical per-event endpoint: resp.json() = {'data': {'bookmakers': [...]}, ...}
    data = resp.json().get('data', {})
    return data.get('bookmakers', []), remaining


# ---------------------------------------------------------------------------
# Closing odds lookup builder
# ---------------------------------------------------------------------------

def _build_closing_lookup(bookmakers: List) -> Dict:
    """
    Build a player→stat→odds lookup from raw bookmakers data.

    Returns: {accent_stripped_lowercase_player: {stat_code: {over, under, line, book, last_update}}}
    First preferred vendor (Pinnacle > Novig > ProphetX > ... > DK) wins per player/stat combo.
    'book' and 'last_update' stored so _match_and_update can write closing_book + exact line-freeze time.
    """
    lookup: Dict[str, Dict] = {}

    # Sort preferred books first; unknown books go last (index 99)
    sorted_books = sorted(
        bookmakers,
        key=lambda b: (PREFERRED_BOOKS.index(b['key'])
                       if b['key'] in PREFERRED_BOOKS else 99)
    )

    for bk in sorted_books:
        bk_key = bk.get('key', '')
        for market in bk.get('markets', []):
            stat_code = ODDS_API_MARKET_TO_STAT.get(market.get('key', ''))
            if not stat_code:
                continue

            last_update = market.get('last_update')  # Pinnacle's exact line-freeze timestamp

            # Collect both sides per player for this market
            player_data: Dict[str, Dict] = {}
            for outcome in market.get('outcomes', []):
                p = _strip_accents(outcome.get('description', '')).lower()
                if not p:
                    continue
                side = outcome.get('name', '').lower()  # 'over' or 'under'
                if p not in player_data:
                    player_data[p] = {}
                player_data[p][side]   = outcome.get('price')
                player_data[p]['line'] = outcome.get('point')

            # Merge into lookup — first preferred vendor wins per player/stat
            for p, sides in player_data.items():
                if p not in lookup:
                    lookup[p] = {}
                if stat_code not in lookup[p]:
                    lookup[p][stat_code] = {
                        'over':        sides.get('over'),
                        'under':       sides.get('under'),
                        'line':        sides.get('line'),
                        'book':        bk_key,        # Which book provided this CLV benchmark
                        'last_update': last_update,   # Exact line-freeze time (ISO 8601 UTC)
                    }

    return lookup


# ---------------------------------------------------------------------------
# Match bets to closing lookup and write CLV
# ---------------------------------------------------------------------------

def _match_and_update(conn: sqlite3.Connection, bets: List,
                       closing_lookup: Dict,
                       dry_run: bool = False,
                       verbose: bool = False) -> Tuple[int, int]:
    """
    Match each bet to the closing lookup by player name + stat category,
    then write all 5 CLV columns.

    Returns: (matched_count, missed_count)
    """
    matched = 0
    missed  = 0
    now_utc = datetime.now(timezone.utc).isoformat()

    for bet in bets:
        p_key = _strip_accents(bet['player_name']).lower()
        stat  = (bet['stat_category'] or '').lower()
        side  = (bet['bet_side'] or 'over').lower()

        # Skip if player or stat not in closing data
        if p_key not in closing_lookup or stat not in closing_lookup[p_key]:
            missed += 1
            if verbose:
                print(f"    SKIP {bet['player_name']} {stat.upper()} "
                      f"— not in closing lookup")
            continue

        cl            = closing_lookup[p_key][stat]
        closing_over  = cl.get('over')
        closing_under = cl.get('under')
        closing_line  = cl.get('line')
        closing_book  = cl.get('book')
        # Use market.last_update (Pinnacle's exact line-freeze time) if available; else script time
        closing_time  = cl.get('last_update') or now_utc

        # Use the correct side's odds for CLV calculation
        bet_odds     = bet['odds_over']  if side == 'over'  else bet['odds_under']
        closing_odds = closing_over      if side == 'over'  else closing_under

        clv_cents = calculate_clv(
            american_to_decimal(bet_odds),
            american_to_decimal(closing_odds)
        )

        line_movement = (
            round(closing_line - bet['line'], 2)
            if closing_line is not None and bet['line'] is not None
            else None
        )

        if not dry_run:
            conn.execute('''
                UPDATE bet_recommendations
                SET closing_odds_over  = ?,
                    closing_odds_under = ?,
                    clv_cents          = ?,
                    closing_time       = ?,
                    line_movement      = ?,
                    closing_book       = ?
                WHERE id = ?
            ''', (closing_over, closing_under, clv_cents, closing_time,
                  line_movement, closing_book, bet['id']))

        matched += 1
        if verbose:
            clv_str  = f"{clv_cents:+.2f}c" if clv_cents is not None else "N/A (no odds)"
            book_str = f" [{closing_book}]" if closing_book else ""
            print(f"    ✅ {bet['player_name']} {stat.upper()} {side.upper()} "
                  f"@ {bet['line']} | CLV: {clv_str}{book_str}")

    if not dry_run:
        conn.commit()

    return matched, missed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Historical CLV Backfill — populate closing odds for settled bets'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview only — no DB writes')
    parser.add_argument('--yesterday', action='store_true',
                        help='Process all bets from yesterday EST — covers day games + overnight run')
    parser.add_argument('--date', type=str, default=None,
                        help='Process single date (YYYY-MM-DD)')
    parser.add_argument('--from', dest='from_date', type=str, default=None,
                        help='Start date, inclusive (YYYY-MM-DD)')
    parser.add_argument('--to',   dest='to_date',   type=str, default=None,
                        help='End date, inclusive (YYYY-MM-DD)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print per-bet CLV detail')
    parser.add_argument('--reserve', type=int, default=QUOTA_RESERVE,
                        help=f'Minimum quota to keep for live pipeline (default: {QUOTA_RESERVE})')
    args = parser.parse_args()

    # --yesterday is sugar for --date <yesterday_EST>
    if args.yesterday:
        from datetime import timedelta
        import pytz as _pytz
        _est = _pytz.timezone('America/New_York')
        _yesterday = (datetime.now(_est) - timedelta(days=1)).strftime('%Y-%m-%d')
        args.date = _yesterday
        print(f"  --yesterday → {_yesterday} (EST)")

    # --date is shorthand for --from X --to X (single-date run)
    if args.date:
        args.from_date = args.date
        args.to_date   = args.date

    print("=" * 60)
    print("HISTORICAL CLV BACKFILL v1.0")
    print("=" * 60)
    print(f"  API key: {_KEY_SOURCE}")
    if args.dry_run:
        print("⚠️  DRY RUN — no database writes")

    db_path = project_root / 'ludi.db'
    if not db_path.exists():
        print("❌ Database not found at", db_path)
        sys.exit(1)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # One-time migration guard (safe no-op if columns already exist)
    ensure_clv_columns(conn)

    # Build team name → abbreviation map from canonical_teams
    team_map = _build_team_map(conn)
    print(f"  Team map loaded: {len(team_map)} teams")

    # Find all dates with settled bets missing CLV
    pending_dates = _get_pending_dates(conn, args.from_date, args.to_date)
    if not pending_dates:
        print("✅ No settled bets missing CLV data — nothing to do")
        conn.close()
        return

    total_bets = sum(cnt for _, cnt in pending_dates)
    print(f"  Pending: {len(pending_dates)} dates | {total_bets} bets missing CLV")
    if args.from_date or args.to_date:
        print(f"  Range:   {args.from_date or 'beginning'} → {args.to_date or 'end'}")

    quota_reserve = args.reserve
    if quota_reserve != QUOTA_RESERVE:
        print(f"  Reserve override: {quota_reserve} (default: {QUOTA_RESERVE})")

    session          = requests.Session()
    total_matched    = 0
    total_credits    = 0
    quota_remaining: str = 'unknown'

    for date_str, bet_count in pending_dates:

        # Quota guard — stop if near live pipeline reserve
        if not _check_quota_with_reserve(quota_remaining, quota_reserve):
            print(f"\n⚠️  Quota near reserve ({quota_remaining} remaining) — stopping.")
            break

        print(f"\n[{date_str}] {bet_count} bets pending")

        # ── Step 1: Fetch event list (IDs + commence_times) ───────────────
        events = _load_events_cache(date_str)
        if events is not None:
            if args.verbose:
                print(f"  Events: {len(events)} found [cache hit — 0 credits]")
        else:
            try:
                events, quota_remaining = _fetch_events(date_str, session)
                _save_events_cache(date_str, events)
            except Exception as e:
                print(f"  ❌ Events fetch failed: {e} — skipping date")
                continue
            total_credits += 1  # events call: h2h only = 1 credit (props = 10 credits)
            if args.verbose:
                print(f"  Events: {len(events)} found | quota: {quota_remaining}")
            time.sleep(1.0)  # Rate limit between API calls

        # ── Step 2: Load settled bets for this date (still missing CLV) ───
        bets = conn.execute('''
            SELECT id, player_name, stat_category, bet_side, line,
                   odds_over, odds_under, home_team, away_team
            FROM bet_recommendations
            WHERE game_date = ?
              AND closing_odds_over IS NULL
              AND outcome IN ('WIN', 'LOSS', 'PUSH')
        ''', (date_str,)).fetchall()

        date_matched = 0

        # ── Step 3: Per-game props fetch ───────────────────────────────────
        for event in events:
            # Map Odds API full name → our abbreviation (e.g. 'Detroit Pistons' → 'DET')
            home_abbr = team_map.get(event.get('home_team', ''))
            if not home_abbr:
                if args.verbose:
                    print(f"  ⚠️  No abbr mapped for '{event.get('home_team')}' — skipping")
                continue

            # Filter bets that belong to this game
            # b['home_team'] stores our abbreviation — match against home_abbr
            game_bets = [b for b in bets
                         if b['home_team'] in (home_abbr, event.get('home_team', ''))]
            if not game_bets:
                continue  # No bets for this game — skip props call (save 10 credits)

            if args.verbose:
                print(f"  {event.get('away_team')} @ {event.get('home_team')} "
                      f"— {len(game_bets)} bets")

            # Cache check: use cached JSON if available (costs 0 credits on re-run)
            bookmakers = _load_cache(date_str, event['id'])
            if bookmakers is None:
                # Quota guard before each props call
                if not _check_quota_with_reserve(quota_remaining, quota_reserve):
                    print(f"  ⚠️  Quota guard — stopping mid-date ({date_str})")
                    break
                try:
                    bookmakers, quota_remaining = _fetch_props(
                        event['id'], event['commence_time'], session
                    )
                    # Cache raw JSON BEFORE any DB writes — protects against crash mid-run
                    _save_cache(date_str, event['id'], bookmakers)
                except Exception as e:
                    print(f"  ❌ Props fetch failed ({event.get('home_team')}): {e}")
                    continue
                total_credits += 10
                time.sleep(1.0)
            else:
                if args.verbose:
                    print(f"    [cache hit — 0 credits]")

            # Build lookup and match bets
            closing_lookup = _build_closing_lookup(bookmakers)
            matched, missed = _match_and_update(
                conn, game_bets, closing_lookup, args.dry_run, args.verbose
            )
            date_matched += matched

            if not args.verbose:
                print(f"  {event.get('away_team')} @ {event.get('home_team')}: "
                      f"{matched}/{len(game_bets)} matched, {missed} missed")

        total_matched += date_matched
        print(f"  [{date_str}] subtotal: {date_matched} updated | "
              f"~{total_credits} credits used | quota: {quota_remaining}")

    conn.close()

    print("\n" + "=" * 60)
    action = "would update" if args.dry_run else "updated"
    print(f"✅  CLV backfill complete")
    print(f"    Bets {action}: {total_matched}")
    print(f"    Credits used:  ~{total_credits}")
    print(f"    Quota remaining: {quota_remaining}")
    print("=" * 60)


if __name__ == '__main__':
    main()
