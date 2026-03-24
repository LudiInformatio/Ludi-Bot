#!/usr/bin/env python3
"""
LUDI INFORMATIO | EMPIRICAL MODIFIERS COMPUTE SCRIPT
=====================================================
Nightly compute script (1-3 AM window).
Reads player_game_logs, team_lineups, player_canonical_ids.
Writes player_empirical_modifiers table.

Usage:
    .venv/bin/python scripts/compute_empirical_modifiers.py
    .venv/bin/python scripts/compute_empirical_modifiers.py --dry-run
    .venv/bin/python scripts/compute_empirical_modifiers.py --player "Jayson Tatum"
    .venv/bin/python scripts/compute_empirical_modifiers.py --season 2025-26

Guards:
    Item 1 (starter/bench): N >= 10 per role; fallback to unconditional L10 if < 10.
    Item 3 (stdev): N >= 30 total games; rare-stat fallback uses season-wide stdev.
    Item 4 (WOWY): N >= 10 WITH and N >= 10 WITHOUT; skip if either below threshold.
"""

import sys
import os
import argparse
import logging
import sqlite3
import statistics
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import DB_PATH

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

SEASON = '2025-26'
PROMPT_VERSION = 'v1.3-empirical-mods'

# N-gate thresholds (Lena guards)
MIN_ROLE_GAMES = 10      # Item 1: minimum games in each role (starter OR bench)
MIN_STDEV_GAMES = 30     # Item 3: minimum total games for empirical stdev
MIN_WOWY_GAMES  = 10     # Item 4: minimum WITH and WITHOUT games for WOWY delta

# Stat columns in player_game_logs mapped to empirical mod keys
STAT_MAP = {
    'pts':  'pts',
    'reb':  'reb',
    'ast':  'ast',
    'fta':  'fta',
    'stl':  'stl',
    'blk':  'blk',
    'fg3m': 'fg3m',
}

# Rare stats that may have very low values in <18 min games
# Fallback: use season-wide stdev if cell N < MIN_STDEV_GAMES
RARE_STATS = {'stl', 'blk', 'fg3m'}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.row_factory = sqlite3.Row
    return conn


# --- Item 1: Starter/Bench Role Split ----------------------------------------

def compute_role_modifiers(conn, player_name: str, season: str) -> dict:
    """
    Compute starter vs bench stat modifiers.

    Modifier = role_avg / unconditional_l10_avg for each stat.
    Returns 1.0 for any stat where N < MIN_ROLE_GAMES in that role.
    Returns unconditional L10 fallback if a role has < MIN_ROLE_GAMES.
    """
    # Unconditional L10 baseline
    baseline = conn.execute("""
        SELECT AVG(pts) as pts, AVG(reb) as reb, AVG(ast) as ast,
               AVG(fta) as fta, AVG(stl) as stl, AVG(blk) as blk,
               AVG(fg3m) as fg3m, COUNT(*) as n
        FROM (
            SELECT pts, reb, ast, fta, stl, blk, fg3m
            FROM player_game_logs
            WHERE player_name = ?
              AND season_id = ?
              AND minutes >= 5
            ORDER BY game_date DESC
            LIMIT 10
        )
    """, (player_name, season)).fetchone()

    if not baseline or baseline['n'] == 0:
        logger.warning(f"[empirical] {player_name}: no game logs found for baseline")
        return {}

    result = {}

    for role_flag, prefix in [(1, 'starter'), (0, 'bench')]:
        role_rows = conn.execute("""
            SELECT pts, reb, ast, fta, stl, blk, fg3m, COUNT(*) as n
            FROM player_game_logs
            WHERE player_name = ?
              AND season_id = ?
              AND minutes >= 5
              AND started = ?
        """, (player_name, season, role_flag)).fetchone()

        n = role_rows['n'] if role_rows else 0

        if n < MIN_ROLE_GAMES:
            # Fallback: use 1.0 modifier (unconditional baseline)
            logger.warning(
                f"[empirical] {player_name}: {prefix} role N={n} < {MIN_ROLE_GAMES} "
                f"-- using 1.0 fallback for all {prefix} mods"
            )
            for stat in STAT_MAP:
                result[f"{prefix}_{stat}_mod"] = 1.0
            result[f"{prefix}_n"] = n
            continue

        for stat in STAT_MAP:
            role_avg = role_rows[stat] or 0.0
            base_avg = baseline[stat] or 0.0
            if base_avg > 0:
                result[f"{prefix}_{stat}_mod"] = round(role_avg / base_avg, 4)
            else:
                result[f"{prefix}_{stat}_mod"] = 1.0
        result[f"{prefix}_n"] = n

    return result


# --- Item 3: Per-Stat Empirical Standard Deviation ----------------------------

def compute_stdev_modifiers(conn, player_name: str, season: str) -> dict:
    """
    Compute per-stat standard deviation from season game logs.

    N >= MIN_STDEV_GAMES required. Returns None for stats with < MIN_STDEV_GAMES
    games OR where the cell value is NULL/0 for rare stats.
    """
    rows = conn.execute("""
        SELECT pts, reb, ast, fta, stl, blk, fg3m, minutes
        FROM player_game_logs
        WHERE player_name = ?
          AND season_id = ?
          AND minutes >= 5
        ORDER BY game_date DESC
    """, (player_name, season)).fetchall()

    n = len(rows)
    result = {'stdev_n': n}

    if n < MIN_STDEV_GAMES:
        logger.warning(
            f"[empirical] {player_name}: stdev N={n} < {MIN_STDEV_GAMES} "
            f"-- all stdev values set to NULL (module_f fallback to _STAT_RMSE)"
        )
        for stat in STAT_MAP:
            result[f"stdev_{stat}"] = None
        return result

    for stat in STAT_MAP:
        values = [r[stat] for r in rows if r[stat] is not None]

        # Lena guard: rare stats in <18 min bracket need larger sample
        if stat in RARE_STATS:
            full_min_values = [r[stat] for r in rows if r[stat] is not None and r['minutes'] >= 18]
            if len(full_min_values) < MIN_STDEV_GAMES:
                logger.warning(
                    f"[empirical] {player_name}: {stat} in >=18min games N={len(full_min_values)} "
                    f"< {MIN_STDEV_GAMES} -- falling back to all-minutes stdev"
                )
                # Fall through to all-minutes stdev below

        if len(values) >= 2:
            result[f"stdev_{stat}"] = round(statistics.stdev(values), 4)
        else:
            result[f"stdev_{stat}"] = None

    return result


# --- Item 4: WOWY Lineup Delta -----------------------------------------------

def compute_wowy_modifiers(conn, player_name: str) -> dict:
    """
    Compute WOWY (With Or Without You) net rating delta from team_lineups.

    Requires:
    - lineup_id column populated (Step 2 prerequisite)
    - canonical_id JOIN to player_canonical_ids
    - N >= MIN_WOWY_GAMES for both WITH and WITHOUT groups

    Uses .get('GROUP_ID') pattern -- lineup_id is the stored GROUP_ID value.
    """
    # Resolve canonical_id for this player
    canon_row = conn.execute("""
        SELECT canonical_id FROM player_canonical_ids
        WHERE normalized_name = LOWER(?)
           OR full_name = ?
        LIMIT 1
    """, (player_name, player_name)).fetchone()

    if not canon_row:
        logger.warning(f"[empirical] {player_name}: no canonical_id found -- skipping WOWY")
        return {}

    canonical_id = str(canon_row['canonical_id'])

    # Lineups containing this player (WITH)
    with_rows = conn.execute("""
        SELECT AVG(net_rating) as avg_net, COUNT(*) as n
        FROM team_lineups
        WHERE lineup_id LIKE ?
          AND lineup_id != ''
    """, (f'%-{canonical_id}-%',)).fetchone()

    with_n = with_rows['n'] if with_rows else 0
    with_avg = with_rows['avg_net'] if with_rows and with_rows['avg_net'] is not None else None

    # Lineups NOT containing this player (WITHOUT)
    # Restrict to same team to avoid cross-team noise
    team_row = conn.execute(
        "SELECT team FROM players WHERE name = ? LIMIT 1", (player_name,)
    ).fetchone()
    team = team_row['team'] if team_row else None

    if team:
        without_rows = conn.execute("""
            SELECT AVG(net_rating) as avg_net, COUNT(*) as n
            FROM team_lineups
            WHERE team_abbreviation = ?
              AND (lineup_id NOT LIKE ? OR lineup_id = '' OR lineup_id IS NULL)
        """, (team, f'%-{canonical_id}-%')).fetchone()
    else:
        without_rows = conn.execute("""
            SELECT AVG(net_rating) as avg_net, COUNT(*) as n
            FROM team_lineups
            WHERE lineup_id NOT LIKE ?
              AND lineup_id != ''
        """, (f'%-{canonical_id}-%',)).fetchone()

    without_n = without_rows['n'] if without_rows else 0
    without_avg = without_rows['avg_net'] if without_rows and without_rows['avg_net'] is not None else None

    if with_n < MIN_WOWY_GAMES or without_n < MIN_WOWY_GAMES:
        logger.warning(
            f"[empirical] {player_name}: WOWY gate N_with={with_n} N_without={without_n} "
            f"(need >= {MIN_WOWY_GAMES} each) -- WOWY values set to NULL"
        )
        return {
            'wowy_with_avg': None,
            'wowy_without_avg': None,
            'wowy_delta': None,
            'wowy_with_n': with_n,
            'wowy_without_n': without_n,
        }

    delta = round(with_avg - without_avg, 4) if (with_avg is not None and without_avg is not None) else None

    return {
        'wowy_with_avg': round(with_avg, 4) if with_avg is not None else None,
        'wowy_without_avg': round(without_avg, 4) if without_avg is not None else None,
        'wowy_delta': delta,
        'wowy_with_n': with_n,
        'wowy_without_n': without_n,
    }


# --- Item 5: Tank01 Depth Chart Slot -----------------------------------------

def compute_depth_slot(conn, player_name: str) -> dict:
    """
    Read depth chart slot from Tank01 data stored in players table.
    depth_slot: 1 = starter, 2 = first reserve, 3+ = deep bench, NULL = unknown.

    Note: Tank01 depth chart sync must have run before this script.
    The players.depth_chart_position column is the source (if it exists).
    If the column does not exist, returns {} (no data, no error).
    """
    try:
        row = conn.execute("""
            SELECT depth_chart_position FROM players
            WHERE name = ?
            LIMIT 1
        """, (player_name,)).fetchone()

        if row and row['depth_chart_position'] is not None:
            return {
                'depth_slot': int(row['depth_chart_position']),
                'depth_synced_at': datetime.now().isoformat(),
            }
    except Exception as e:
        # depth_chart_position column may not exist yet -- soft fail
        logger.warning(f"[empirical] {player_name}: depth_slot lookup failed: {e}")

    return {}


# --- Main Compute Loop -------------------------------------------------------

def compute_all_players(conn, season: str, dry_run: bool = False,
                        player_filter: Optional[str] = None) -> int:
    """
    Compute empirical modifiers for all active players (or one player).
    Returns number of rows upserted.
    """
    if player_filter:
        players = conn.execute(
            "SELECT name FROM players WHERE name = ? AND is_active = 1",
            (player_filter,)
        ).fetchall()
    else:
        players = conn.execute(
            "SELECT name FROM players WHERE is_active = 1"
        ).fetchall()

    if not players:
        logger.warning("[empirical] No active players found -- check players.status column")
        return 0

    logger.info(f"[empirical] Computing modifiers for {len(players)} players")
    upserted = 0

    for p_row in players:
        player_name = p_row['name']
        try:
            # Resolve the name as stored in player_game_logs (may differ in accent encoding)
            # player_game_logs may store non-accented names (e.g. "Nikola Jokic" vs "Nikola Jokić")
            log_name_row = conn.execute(
                "SELECT player_name FROM player_game_logs WHERE player_name = ? AND season_id = ? LIMIT 1",
                (player_name, season)
            ).fetchone()
            if log_name_row:
                log_player_name = log_name_row[0]
            else:
                # Try non-accented fallback via player_canonical_ids
                canon_row = conn.execute(
                    "SELECT full_name FROM player_canonical_ids WHERE full_name = ? OR normalized_name = LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(?, 'č','c'),'ć','c'),'ž','z'),'š','s'),'đ','d')) LIMIT 1",
                    (player_name, player_name)
                ).fetchone()
                if canon_row:
                    log_name_row2 = conn.execute(
                        "SELECT player_name FROM player_game_logs WHERE player_name = ? AND season_id = ? LIMIT 1",
                        (canon_row[0], season)
                    ).fetchone()
                    log_player_name = log_name_row2[0] if log_name_row2 else player_name
                else:
                    log_player_name = player_name

            row_data = {
                'player_name': player_name,
                'season': season,
            }

            # Item 1: Role split
            role_mods = compute_role_modifiers(conn, log_player_name, season)
            row_data.update(role_mods)

            # Item 3: Stdev
            stdev_mods = compute_stdev_modifiers(conn, log_player_name, season)
            row_data.update(stdev_mods)

            # Item 4: WOWY
            wowy_mods = compute_wowy_modifiers(conn, player_name)
            row_data.update(wowy_mods)

            # Item 5: Depth slot
            depth_mods = compute_depth_slot(conn, player_name)
            row_data.update(depth_mods)

            row_data['computed_at'] = datetime.now().isoformat()

            if dry_run:
                logger.info(f"[DRY RUN] {player_name}: {row_data}")
                upserted += 1
                continue

            # UPSERT
            cols = ', '.join(row_data.keys())
            placeholders = ', '.join(['?'] * len(row_data))
            update_clause = ', '.join(
                f"{k} = excluded.{k}"
                for k in row_data
                if k not in ('player_name', 'season')
            )
            conn.execute(f"""
                INSERT INTO player_empirical_modifiers ({cols})
                VALUES ({placeholders})
                ON CONFLICT(player_name, season) DO UPDATE SET {update_clause}
            """, list(row_data.values()))
            upserted += 1

        except Exception as e:
            logger.warning(f"[empirical] {player_name}: compute failed: {e}")
            continue

    if not dry_run:
        conn.commit()

    logger.info(f"[empirical] Done. {upserted}/{len(players)} players upserted.")
    return upserted


def main():
    parser = argparse.ArgumentParser(description="Compute empirical player modifiers")
    parser.add_argument('--dry-run', action='store_true',
                        help='Compute but do not write to DB')
    parser.add_argument('--player', type=str, default=None,
                        help='Run for a single player name (for testing)')
    parser.add_argument('--season', type=str, default=SEASON,
                        help=f'Season string (default: {SEASON})')
    args = parser.parse_args()

    conn = get_db_connection()
    try:
        n = compute_all_players(conn, args.season, dry_run=args.dry_run,
                                player_filter=args.player)
        sys.exit(0 if n > 0 else 1)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
