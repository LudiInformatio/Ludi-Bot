#!/usr/bin/env python3
"""
BDL Clutch Usage Sync Script (Sprint Phase 3 Fix)

Populates player_leverage_usage table from Ball Don't Lie clutch season averages.
This replaces the broken PBP Stats get_possessions endpoint for 2025-26.

BDL clutch definition: Last 5 minutes of 4th quarter/OT, score within 5 points
(matches NBA official clutch definition).

Data source: BDL /nba/v1/season_averages/clutch (GOAT tier, 600 req/min)

Usage:
    python scripts/sync_bdl_clutch_usage.py
    python scripts/sync_bdl_clutch_usage.py --verbose
    python scripts/sync_bdl_clutch_usage.py --backfill  # Also pull from player_clutch_stats

Author: Ludi Informatio
Date: February 14, 2026 (Sprint Phase 3 - API Fix)
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from utils.bdl_client import BDLClient


CURRENT_SEASON = "2025-26"  # Default; overridden by --season arg in main()
BDL_SEASON = 2025  # Default; overridden by --season arg in main()


def get_db_connection(db_path: str = "ludi.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn


def _build_team_lookup(conn: sqlite3.Connection) -> Dict[str, str]:
    """
    Build player name → team_abbr lookup from our players table.

    BDL clutch endpoint doesn't include team info, so we resolve
    team assignments from our local database.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT LOWER(name), team
        FROM players
        WHERE team IS NOT NULL AND team != ''
    """)
    return {row[0]: row[1] for row in cursor.fetchall()}


def fetch_bdl_clutch_data(client: BDLClient, conn: sqlite3.Connection,
                          verbose: bool = False) -> List[Dict]:
    """
    Fetch clutch base + usage stats from BDL for all players.

    BDL clutch endpoint doesn't include team info — we resolve team
    from our local players table.

    Returns list of dicts with player name, team, clutch FGA, usage%, etc.
    """
    all_players = []

    # Build team lookup from local DB
    team_lookup = _build_team_lookup(conn)
    if verbose:
        print(f"[BDL Clutch] Team lookup: {len(team_lookup)} players mapped")

    # Fetch clutch/base for counting stats (FGA, PTS, MIN, GP)
    if verbose:
        print("[BDL Clutch] Fetching clutch base stats...")

    base_data = client._get_all_pages(
        f"{client.BASE_URL_V1}/season_averages/clutch",
        {"season": BDL_SEASON, "season_type": "regular", "type": "base", "per_page": 100}
    )

    if verbose:
        print(f"[BDL Clutch] Received {len(base_data)} clutch base records")

    # Fetch clutch/usage for usage% in clutch
    if verbose:
        print("[BDL Clutch] Fetching clutch usage stats...")

    usage_data = client._get_all_pages(
        f"{client.BASE_URL_V1}/season_averages/clutch",
        {"season": BDL_SEASON, "season_type": "regular", "type": "usage", "per_page": 100}
    )

    if verbose:
        print(f"[BDL Clutch] Received {len(usage_data)} clutch usage records")

    # Build usage lookup by player ID
    usage_lookup = {}
    for rec in usage_data:
        player = rec.get('player', {})
        pid = player.get('id')
        if pid:
            usage_lookup[pid] = rec.get('stats', {})

    # Also fetch overall base stats to calculate clutch_usage_rate
    if verbose:
        print("[BDL Clutch] Fetching overall base stats for rate calculation...")

    overall_data = client._get_all_pages(
        f"{client.BASE_URL_V1}/season_averages/general",
        {"season": BDL_SEASON, "season_type": "regular", "type": "base", "per_page": 100}
    )

    overall_lookup = {}
    for rec in overall_data:
        player = rec.get('player', {})
        pid = player.get('id')
        if pid:
            overall_lookup[pid] = rec.get('stats', {})

    if verbose:
        print(f"[BDL Clutch] Received {len(overall_data)} overall base records")

    # Merge clutch base + usage + overall
    unmatched = 0
    for rec in base_data:
        player = rec.get('player', {})
        stats = rec.get('stats', {})
        pid = player.get('id')

        first = player.get('first_name', '')
        last = player.get('last_name', '')

        if not first or not last:
            continue

        player_name = f"{first} {last}"

        # Resolve team from local DB (BDL clutch doesn't include team)
        team_abbr = team_lookup.get(player_name.lower(), '')
        if not team_abbr:
            unmatched += 1
            continue

        clutch_fga = stats.get('fga', 0) or 0
        clutch_gp = stats.get('gp', 0) or 0
        clutch_min = stats.get('min', 0) or 0

        # Get usage% from clutch usage data
        usage_stats = usage_lookup.get(pid, {})
        clutch_usg_pct = usage_stats.get('usg_pct', 0) or 0

        # Get overall FGA for rate calculation
        overall_stats = overall_lookup.get(pid, {})
        overall_fga = overall_stats.get('fga', 0) or 0
        overall_gp = overall_stats.get('gp', 0) or 0

        # Calculate clutch_usage_rate: clutch FGA total / overall FGA total
        # This measures what % of a player's shots come in clutch time
        if overall_fga > 0 and overall_gp > 0 and clutch_gp > 0:
            clutch_fga_total = clutch_fga * clutch_gp
            overall_fga_total = overall_fga * overall_gp
            clutch_usage_rate = clutch_fga_total / overall_fga_total if overall_fga_total > 0 else 0
        else:
            clutch_usage_rate = 0

        # Estimate VH possessions from clutch minutes and games
        # BDL clutch min is per-game average; total clutch possessions ≈ min * gp * 2
        vh_possessions = int(clutch_min * clutch_gp * 2) if clutch_min and clutch_gp else 0
        vh_shot_attempts = int(clutch_fga * clutch_gp) if clutch_fga and clutch_gp else 0
        total_possessions = int(overall_stats.get('min', 0) * overall_gp * 2) if overall_gp else 0
        total_shot_attempts = int(overall_fga * overall_gp) if overall_fga and overall_gp else 0

        all_players.append({
            'player_name': player_name,
            'team_abbr': team_abbr,
            'vh_possessions': vh_possessions,
            'vh_shot_attempts': vh_shot_attempts,
            'total_possessions': total_possessions,
            'total_shot_attempts': total_shot_attempts,
            'clutch_usage_rate': round(clutch_usage_rate, 4),
            'clutch_usg_pct': clutch_usg_pct,
            'clutch_gp': clutch_gp,
        })

    if unmatched > 0:
        print(f"[CLUTCH] WARNING: {unmatched} players skipped (no team match)")

    return all_players


def backfill_from_clutch_stats(conn: sqlite3.Connection, verbose: bool = False) -> Dict[str, Dict]:
    """
    Derive clutch usage from existing player_clutch_stats table (Ghost Protocol data).
    Returns {player_name: {vh_fga, total_games, avg_clutch_fga}}.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT player_name, team_abbr,
               COUNT(*) as clutch_games,
               ROUND(AVG(clutch_fga), 2) as avg_clutch_fga,
               ROUND(SUM(clutch_fga), 0) as total_clutch_fga,
               ROUND(AVG(clutch_pts), 2) as avg_clutch_pts
        FROM player_clutch_stats
        WHERE clutch_min > 0
        GROUP BY nba_player_id
        HAVING COUNT(*) >= 5
        ORDER BY avg_clutch_fga DESC
    """)

    results = {}
    for row in cursor.fetchall():
        # Normalize name (Ghost Protocol stores UPPERCASE)
        name = row[0].title() if row[0] else ''
        results[name] = {
            'team_abbr': row[1],
            'clutch_games': row[2],
            'avg_clutch_fga': row[3],
            'total_clutch_fga': row[4],
            'avg_clutch_pts': row[5],
        }

    if verbose:
        print(f"[Backfill] Found {len(results)} players with 5+ clutch games in player_clutch_stats")

    return results


def save_player_leverage(conn: sqlite3.Connection, players: List[Dict],
                         verbose: bool = False) -> int:
    """Save player leverage usage data to database."""
    cursor = conn.cursor()
    saved = 0

    for p in players:
        # Skip players with no clutch data
        if p['vh_possessions'] == 0 and p['total_possessions'] == 0:
            continue

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO player_leverage_usage (
                    player_name, team_abbr, season,
                    vh_possessions, vh_shot_attempts,
                    total_possessions, total_shot_attempts,
                    clutch_usage_rate, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p['player_name'], p['team_abbr'], CURRENT_SEASON,
                p['vh_possessions'], p['vh_shot_attempts'],
                p['total_possessions'], p['total_shot_attempts'],
                p['clutch_usage_rate'], datetime.now().isoformat()
            ))
            saved += 1
        except sqlite3.Error as e:
            print(f"[ERROR] Error saving {p['player_name']}: {e}")

    conn.commit()
    return saved


def main():
    parser = argparse.ArgumentParser(description="Sync BDL Clutch Usage → player_leverage_usage")
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--backfill', action='store_true',
                        help="Also enrich from player_clutch_stats (Ghost Protocol)")
    parser.add_argument('--dry-run', action='store_true', help="Don't write to DB")
    parser.add_argument('--season', type=int, default=2025,
                        help="BDL season start year (default: 2025 = 2025-26)")
    args = parser.parse_args()

    # Derive season constants from --season arg
    global BDL_SEASON, CURRENT_SEASON
    BDL_SEASON = args.season
    CURRENT_SEASON = f"{args.season}-{str(args.season + 1)[-2:]}"

    client = BDLClient(api_key=os.getenv('BALLDONTLIE_KEY'))
    if not client.api_key:
        print("❌ BALLDONTLIE_KEY not set. Cannot sync clutch data.")
        return

    conn = get_db_connection()

    print(f"[BDL Clutch] Syncing clutch usage data for {CURRENT_SEASON}...")

    # Primary: BDL clutch season averages
    players = fetch_bdl_clutch_data(client, conn, verbose=args.verbose)
    print(f"[BDL Clutch] Processed {len(players)} players from BDL")

    # Optional: Enrich with Ghost Protocol clutch stats
    if args.backfill:
        backfill_data = backfill_from_clutch_stats(conn, verbose=args.verbose)
        # Merge: if BDL has the player, keep BDL data (more current)
        # If Ghost Protocol has data BDL doesn't, add it
        bdl_names = {p['player_name'] for p in players}
        for name, data in backfill_data.items():
            if name not in bdl_names:
                # Use Ghost Protocol data as supplement
                players.append({
                    'player_name': name,
                    'team_abbr': data['team_abbr'],
                    'vh_possessions': int(data['clutch_games'] * 5),  # ~5 poss/clutch game
                    'vh_shot_attempts': int(data['total_clutch_fga']),
                    'total_possessions': 0,
                    'total_shot_attempts': 0,
                    'clutch_usage_rate': 0,
                })
        if args.verbose:
            print(f"[BDL Clutch] After backfill merge: {len(players)} total players")

    if not args.dry_run:
        saved = save_player_leverage(conn, players, verbose=args.verbose)
        print(f"[BDL Clutch] Saved {saved} player leverage records")
    else:
        print(f"[BDL Clutch] Dry run — would save {len(players)} records")

    # Show top clutch users
    if not args.dry_run:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT player_name, team_abbr, clutch_usage_rate, vh_possessions, vh_shot_attempts
            FROM player_leverage_usage
            WHERE season = ? AND clutch_usage_rate > 0
            ORDER BY clutch_usage_rate DESC
            LIMIT 15
        """, (CURRENT_SEASON,))
        rows = cursor.fetchall()
        if rows:
            print(f"\nTop 15 Clutch Usage Players:")
            for row in rows:
                print(f"  {row[0]} ({row[1]}): {row[2]:.1%} clutch rate, {row[3]} VH poss, {row[4]} VH shots")

    conn.close()
    print(f"\n{'='*50}")
    print(f"BDL Clutch Sync Complete")


if __name__ == "__main__":
    main()
