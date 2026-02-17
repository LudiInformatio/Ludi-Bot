#!/usr/bin/env python3
"""
BDL Tracking + Playtype Sync Script

Replaces Playwright scraping of NBA.com with BDL API calls for 5 tables:
- player_defense (defensive matchup stats)
- player_drives (drives to basket tracking)
- player_touches (ball touches and possessions)
- player_speed (speed and distance traveled)
- player_synergy_playtypes (playtype breakdown - core stats only)

BDL GOAT tier: 600 req/min, no browser needed, CI-safe.

Usage:
    python scripts/sync_bdl_tracking.py --all --verbose
    python scripts/sync_bdl_tracking.py --table defense
    python scripts/sync_bdl_tracking.py --table synergy --dry-run

Author: Ludi Informatio
Date: February 15, 2026 (Phase 7 - BDL Migration)
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
from utils.player_id_resolver import normalize_player_name


CURRENT_SEASON = "2025-26"
BDL_SEASON = 2025  # BDL uses start year

BDL_TO_PLAYTYPE = {
    'isolation': 'ISO',
    'transition': 'TRANSITION',
    'handoff': 'HANDOFF',
    'cut': 'CUT',
    'postup': 'POST_UP',
    'spotup': 'SPOT_UP',
    'offscreen': 'OFF_SCREEN',
    'misc': 'MISC'
}


def get_db_connection(db_path: str = "ludi.db") -> sqlite3.Connection:
    """Create database connection with WAL mode."""
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.row_factory = sqlite3.Row
    return conn


def normalize_pct_value(raw_value: Optional[float]) -> float:
    """
    Normalize mixed-scale percentages to canonical 0-100 storage.

    Some BDL endpoints return proportions (0-1), while others return already
    percent-scaled values (0-100). We normalize only strict fractions.
    """
    if raw_value is None:
        return 0.0
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return 0.0
    if value < 0:
        return 0.0
    if 0 < value < 1.0:
        return round(value * 100.0, 4)
    return round(value, 4)


def _build_team_lookup(conn: sqlite3.Connection) -> Dict[str, str]:
    """
    Build player name → team_abbr lookup from our players table.

    BDL endpoints don't include team info, so we resolve team
    assignments from our local database.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT LOWER(name), team
        FROM players
        WHERE team IS NOT NULL AND team != ''
    """)
    return {row[0]: row[1] for row in cursor.fetchall()}


def _detect_stats_format(stats: Dict, gp: int) -> bool:
    """
    Auto-detect if BDL returns totals or per-game stats.

    Returns True if per-game, False if totals (need division).

    Heuristic:
    - If high-volume stat (drives, possessions, etc.) > 50 but GP < 20 → likely totals
    - If high-volume stat < 15 and GP > 10 → likely per-game
    """
    # Use a representative stat (drives, possessions, or points)
    sample = stats.get('drives') or stats.get('poss') or stats.get('points', 0)

    if sample == 0:
        return True  # Empty data, doesn't matter

    if sample > 50 and gp < 20:
        return False  # Likely totals

    if sample < 15 and gp > 10:
        return True  # Likely per-game

    # Fallback: if sample/gp < 10, assume per-game
    return (sample / gp < 10) if gp > 0 else True


# ========================================
# DEFENSE SYNC
# ========================================

def fetch_defense_data(client: BDLClient, team_lookup: Dict[str, str],
                       verbose: bool = False) -> List[Dict]:
    """Fetch player defensive stats from BDL defense/overall endpoint."""
    if verbose:
        print("[Defense] Fetching from BDL defense/overall...")

    data = client._get_all_pages(
        f"{client.BASE_URL_V1}/season_averages/defense",
        {"season": BDL_SEASON, "season_type": "regular", "type": "overall", "per_page": 100}
    )

    if verbose:
        print(f"[Defense] Received {len(data)} player records")

    players = []
    unmatched = 0

    for rec in data:
        player = rec.get('player', {})
        stats = rec.get('stats', {})

        first = player.get('first_name', '')
        last = player.get('last_name', '')

        if not first or not last:
            continue

        player_name = normalize_player_name(f"{first} {last}")
        team_abbr = team_lookup.get(player_name.lower(), '')

        if not team_abbr:
            unmatched += 1
            # Don't skip - allow NULL team_abbr

        players.append({
            'player_name': player_name,
            'team_abbr': team_abbr,
            'season': CURRENT_SEASON,
            'gp': stats.get('gp', 0) or 0,
            'freq_pct': normalize_pct_value(stats.get('freq', 0.0) or 0.0),
            'dfgm': stats.get('d_fgm', 0.0) or 0.0,
            'dfga': stats.get('d_fga', 0.0) or 0.0,
            'dfg_pct': stats.get('d_fg_pct', 0.0) or 0.0,
            'fg_pct': stats.get('normal_fg_pct', 0.0) or 0.0,
            'diff_pct': stats.get('pct_plusminus', 0.0) or 0.0,
            'synced_at': datetime.now().isoformat()
        })

    if verbose and unmatched > 0:
        print(f"[Defense] {unmatched} players not matched to local DB (traded/inactive)")

    return players


def save_defense_data(conn: sqlite3.Connection, players: List[Dict],
                      verbose: bool = False) -> int:
    """Save defensive stats to player_defense table."""
    cursor = conn.cursor()
    saved = 0

    for p in players:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO player_defense (
                    player_name, team_abbr, season, gp, freq_pct,
                    dfgm, dfga, dfg_pct, fg_pct, diff_pct, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p['player_name'], p['team_abbr'], p['season'], p['gp'], p['freq_pct'],
                p['dfgm'], p['dfga'], p['dfg_pct'], p['fg_pct'], p['diff_pct'], p['synced_at']
            ))
            saved += 1
        except sqlite3.Error as e:
            if verbose:
                print(f"   ⚠️ Error saving {p['player_name']}: {e}")

    conn.commit()
    return saved


# ========================================
# DRIVES SYNC
# ========================================

def fetch_drives_data(client: BDLClient, team_lookup: Dict[str, str],
                      verbose: bool = False) -> List[Dict]:
    """Fetch player drives tracking stats from BDL tracking/drives endpoint."""
    if verbose:
        print("[Drives] Fetching from BDL tracking/drives...")

    data = client._get_all_pages(
        f"{client.BASE_URL_V1}/season_averages/tracking",
        {"season": BDL_SEASON, "season_type": "regular", "type": "drives", "per_page": 100}
    )

    if verbose:
        print(f"[Drives] Received {len(data)} player records")

    players = []
    unmatched = 0

    for rec in data:
        player = rec.get('player', {})
        stats = rec.get('stats', {})

        first = player.get('first_name', '')
        last = player.get('last_name', '')

        if not first or not last:
            continue

        player_name = normalize_player_name(f"{first} {last}")
        team_abbr = team_lookup.get(player_name.lower(), '')

        if not team_abbr:
            unmatched += 1

        gp = stats.get('gp', 0) or 0
        is_per_game = _detect_stats_format(stats, gp)

        # Field mapping: BDL → our schema
        drives = stats.get('drives', 0.0) or 0.0
        fga = stats.get('drive_fga', 0.0) or 0.0
        fgm = stats.get('drive_fgm', 0.0) or 0.0
        pts = stats.get('drive_pts', 0.0) or 0.0
        passes = stats.get('drive_passes', 0.0) or 0.0
        ast = stats.get('drive_ast', 0.0) or 0.0
        tov = stats.get('drive_tov', 0.0) or 0.0
        pf = stats.get('drive_pf', 0.0) or 0.0

        # Convert to per-game if needed
        if not is_per_game and gp > 0:
            drives = drives / gp
            fga = fga / gp
            fgm = fgm / gp
            pts = pts / gp
            passes = passes / gp
            ast = ast / gp
            tov = tov / gp
            pf = pf / gp

        players.append({
            'player_name': player_name,
            'team_abbr': team_abbr,
            'season': CURRENT_SEASON,
            'gp': gp,
            'drives_per_game': drives,
            'fga_per_game': fga,
            'fgm_per_game': fgm,
            'fg_pct': stats.get('drive_fg_pct', 0.0) or 0.0,
            'pts_per_game': pts,
            'pts_pct': stats.get('drive_pts_pct', 0.0) or 0.0,  # May be missing - BDL provides
            'pass_per_game': passes,
            'pass_pct': stats.get('drive_passes_pct', 0.0) or 0.0,
            'ast_per_game': ast,
            'ast_pct': stats.get('drive_ast_pct', 0.0) or 0.0,
            'tov_per_game': tov,
            'tov_pct': stats.get('drive_tov_pct', 0.0) or 0.0,
            'pf_per_game': pf,
            'pf_pct': stats.get('drive_pf_pct', 0.0) or 0.0,
            'synced_at': datetime.now().isoformat()
        })

    if verbose and unmatched > 0:
        print(f"[Drives] {unmatched} players not matched to local DB")

    return players


def save_drives_data(conn: sqlite3.Connection, players: List[Dict],
                     verbose: bool = False) -> int:
    """Save drives tracking stats to player_drives table."""
    cursor = conn.cursor()
    saved = 0

    for p in players:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO player_drives (
                    player_name, team_abbr, season, gp, drives_per_game,
                    fga_per_game, fgm_per_game, fg_pct, pts_per_game, pts_pct,
                    pass_per_game, pass_pct, ast_per_game, ast_pct,
                    tov_per_game, tov_pct, pf_per_game, pf_pct, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p['player_name'], p['team_abbr'], p['season'], p['gp'], p['drives_per_game'],
                p['fga_per_game'], p['fgm_per_game'], p['fg_pct'], p['pts_per_game'], p['pts_pct'],
                p['pass_per_game'], p['pass_pct'], p['ast_per_game'], p['ast_pct'],
                p['tov_per_game'], p['tov_pct'], p['pf_per_game'], p['pf_pct'], p['synced_at']
            ))
            saved += 1
        except sqlite3.Error as e:
            if verbose:
                print(f"   ⚠️ Error saving {p['player_name']}: {e}")

    conn.commit()
    return saved


# ========================================
# TOUCHES SYNC
# ========================================

def fetch_touches_data(client: BDLClient, team_lookup: Dict[str, str],
                       verbose: bool = False) -> List[Dict]:
    """Fetch player touches tracking stats from BDL tracking/possessions endpoint."""
    if verbose:
        print("[Touches] Fetching from BDL tracking/possessions...")

    data = client._get_all_pages(
        f"{client.BASE_URL_V1}/season_averages/tracking",
        {"season": BDL_SEASON, "season_type": "regular", "type": "possessions", "per_page": 100}
    )

    if verbose:
        print(f"[Touches] Received {len(data)} player records")

    players = []
    unmatched = 0

    for rec in data:
        player = rec.get('player', {})
        stats = rec.get('stats', {})

        first = player.get('first_name', '')
        last = player.get('last_name', '')

        if not first or not last:
            continue

        player_name = normalize_player_name(f"{first} {last}")
        team_abbr = team_lookup.get(player_name.lower(), '')

        if not team_abbr:
            unmatched += 1

        gp = stats.get('gp', 0) or 0
        is_per_game = _detect_stats_format(stats, gp)

        # Field mapping
        touches = stats.get('touches', 0.0) or 0.0
        front_ct_touches = stats.get('front_ct_touches', 0.0) or 0.0
        time_of_poss = stats.get('time_of_poss', 0.0) or 0.0
        elbow_touches = stats.get('elbow_touches', 0.0) or 0.0
        post_touches = stats.get('post_touches', 0.0) or 0.0
        paint_touches = stats.get('paint_touches', 0.0) or 0.0
        pts = stats.get('points', 0.0) or 0.0

        # Convert to per-game if needed
        if not is_per_game and gp > 0:
            touches = touches / gp
            front_ct_touches = front_ct_touches / gp
            time_of_poss = time_of_poss / gp
            elbow_touches = elbow_touches / gp
            post_touches = post_touches / gp
            paint_touches = paint_touches / gp
            pts = pts / gp

        players.append({
            'player_name': player_name,
            'team_abbr': team_abbr,
            'season': CURRENT_SEASON,
            'gp': gp,
            'pts_per_game': pts,
            'touches_per_game': touches,
            'front_ct_touches_per_game': front_ct_touches,
            'time_of_poss_per_game': time_of_poss,
            'avg_sec_per_touch': stats.get('avg_sec_per_touch', 0.0) or 0.0,
            'avg_drib_per_touch': stats.get('avg_drib_per_touch', 0.0) or 0.0,
            'pts_per_touch': stats.get('pts_per_touch', 0.0) or 0.0,
            'elbow_touches_per_game': elbow_touches,
            'post_ups_per_game': post_touches,
            'paint_touches_per_game': paint_touches,
            'pts_per_elbow_touch': stats.get('pts_per_elbow_touch', 0.0) or 0.0,
            'pts_per_post_touch': stats.get('pts_per_post_touch', 0.0) or 0.0,
            'pts_per_paint_touch': stats.get('pts_per_paint_touch', 0.0) or 0.0,
            'synced_at': datetime.now().isoformat()
        })

    if verbose and unmatched > 0:
        print(f"[Touches] {unmatched} players not matched to local DB")

    return players


def save_touches_data(conn: sqlite3.Connection, players: List[Dict],
                      verbose: bool = False) -> int:
    """Save touches tracking stats to player_touches table."""
    cursor = conn.cursor()
    saved = 0

    for p in players:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO player_touches (
                    player_name, team_abbr, season, gp, pts_per_game,
                    touches_per_game, front_ct_touches_per_game, time_of_poss_per_game,
                    avg_sec_per_touch, avg_drib_per_touch, pts_per_touch,
                    elbow_touches_per_game, post_ups_per_game, paint_touches_per_game,
                    pts_per_elbow_touch, pts_per_post_touch, pts_per_paint_touch, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p['player_name'], p['team_abbr'], p['season'], p['gp'], p['pts_per_game'],
                p['touches_per_game'], p['front_ct_touches_per_game'], p['time_of_poss_per_game'],
                p['avg_sec_per_touch'], p['avg_drib_per_touch'], p['pts_per_touch'],
                p['elbow_touches_per_game'], p['post_ups_per_game'], p['paint_touches_per_game'],
                p['pts_per_elbow_touch'], p['pts_per_post_touch'], p['pts_per_paint_touch'], p['synced_at']
            ))
            saved += 1
        except sqlite3.Error as e:
            if verbose:
                print(f"   ⚠️ Error saving {p['player_name']}: {e}")

    conn.commit()
    return saved


# ========================================
# SPEED SYNC
# ========================================

def fetch_speed_data(client: BDLClient, team_lookup: Dict[str, str],
                     verbose: bool = False) -> List[Dict]:
    """Fetch player speed/distance tracking stats from BDL tracking/speeddistance endpoint."""
    if verbose:
        print("[Speed] Fetching from BDL tracking/speeddistance...")

    data = client._get_all_pages(
        f"{client.BASE_URL_V1}/season_averages/tracking",
        {"season": BDL_SEASON, "season_type": "regular", "type": "speeddistance", "per_page": 100}
    )

    if verbose:
        print(f"[Speed] Received {len(data)} player records")

    players = []
    unmatched = 0

    for rec in data:
        player = rec.get('player', {})
        stats = rec.get('stats', {})

        first = player.get('first_name', '')
        last = player.get('last_name', '')

        if not first or not last:
            continue

        player_name = normalize_player_name(f"{first} {last}")
        team_abbr = team_lookup.get(player_name.lower(), '')

        if not team_abbr:
            unmatched += 1

        gp = stats.get('gp', 0) or 0
        is_per_game = _detect_stats_format(stats, gp)

        # Field mapping
        dist_feet = stats.get('dist_feet', 0.0) or 0.0
        dist_miles = stats.get('dist_miles', 0.0) or 0.0

        # Convert to per-game if needed
        if not is_per_game and gp > 0:
            dist_feet = dist_feet / gp
            dist_miles = dist_miles / gp

        players.append({
            'player_name': player_name,
            'team_abbr': team_abbr,
            'season': CURRENT_SEASON,
            'gp': gp,
            'dist_feet_per_game': dist_feet,
            'dist_miles_per_game': dist_miles,
            'dist_miles_off': stats.get('dist_miles_off', 0.0) or 0.0,
            'dist_miles_def': stats.get('dist_miles_def', 0.0) or 0.0,
            'avg_speed': stats.get('avg_speed', 0.0) or 0.0,
            'avg_speed_off': stats.get('avg_speed_off', 0.0) or 0.0,
            'avg_speed_def': stats.get('avg_speed_def', 0.0) or 0.0,
            'synced_at': datetime.now().isoformat()
        })

    if verbose and unmatched > 0:
        print(f"[Speed] {unmatched} players not matched to local DB")

    return players


def save_speed_data(conn: sqlite3.Connection, players: List[Dict],
                    verbose: bool = False) -> int:
    """Save speed/distance tracking stats to player_speed table."""
    cursor = conn.cursor()
    saved = 0

    for p in players:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO player_speed (
                    player_name, team_abbr, season, gp, dist_feet_per_game,
                    dist_miles_per_game, dist_miles_off, dist_miles_def,
                    avg_speed, avg_speed_off, avg_speed_def, synced_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p['player_name'], p['team_abbr'], p['season'], p['gp'], p['dist_feet_per_game'],
                p['dist_miles_per_game'], p['dist_miles_off'], p['dist_miles_def'],
                p['avg_speed'], p['avg_speed_off'], p['avg_speed_def'], p['synced_at']
            ))
            saved += 1
        except sqlite3.Error as e:
            if verbose:
                print(f"   ⚠️ Error saving {p['player_name']}: {e}")

    conn.commit()
    return saved


# ========================================
# SYNERGY PLAYTYPES SYNC (CORE STATS ONLY)
# ========================================

def fetch_synergy_data(client: BDLClient, team_lookup: Dict[str, str],
                       verbose: bool = False) -> List[Dict]:
    """
    Fetch player synergy playtype stats from BDL playtype endpoints.

    NOTE: This only populates core stats (ppp, poss, fg_pct, efg_pct, etc.).
    The 6 frequency fields (ft_freq_pct, tov_freq_pct, sf_freq_pct, and_one_freq_pct,
    score_freq_pct, percentile) will be populated by Playwright scraping in Phase 5.
    """
    all_players = []

    for bdl_type, playtype_tag in BDL_TO_PLAYTYPE.items():
        if verbose:
            print(f"[Synergy] Fetching playtype '{bdl_type}'...")

        data = client._get_all_pages(
            f"{client.BASE_URL_V1}/season_averages/playtype",
            {"season": BDL_SEASON, "season_type": "regular", "type": bdl_type, "per_page": 100}
        )

        if verbose:
            print(f"[Synergy] {bdl_type}: {len(data)} player records")

        unmatched = 0

        for rec in data:
            player = rec.get('player', {})
            stats = rec.get('stats', {})

            first = player.get('first_name', '')
            last = player.get('last_name', '')

            if not first or not last:
                continue

            player_name = normalize_player_name(f"{first} {last}")
            team_abbr = team_lookup.get(player_name.lower(), '')

            if not team_abbr:
                unmatched += 1

            gp = stats.get('gp', 0) or 0
            poss = stats.get('poss', 0.0) or 0.0
            pts = stats.get('pts', 0.0) or 0.0

            # Auto-detect if BDL returns totals or per-game
            is_per_game = _detect_stats_format(stats, gp)

            # Convert to per-game if needed
            poss_per_game = poss if is_per_game else (poss / gp if gp > 0 else 0)
            pts_per_game = pts if is_per_game else (pts / gp if gp > 0 else 0)

            all_players.append({
                'player_name': player_name,
                'team_abbr': team_abbr,
                'season': CURRENT_SEASON,
                'playtype': playtype_tag,
                'games_played': gp,
                'poss_per_game': poss_per_game,
                'freq_pct': normalize_pct_value(stats.get('poss_pct', 0.0) or 0.0),
                'ppp': stats.get('ppp', 0.0) or 0.0,
                'pts_per_game': pts_per_game,
                'fgm': stats.get('fgm', 0) or 0,
                'fga': stats.get('fga', 0) or 0,
                'fg_pct': stats.get('fg_pct', 0.0) or 0.0,
                'efg_pct': stats.get('efg_pct', 0.0) or 0.0,
                'synced_at': datetime.now().isoformat()
            })

        if verbose and unmatched > 0:
            print(f"[Synergy] {bdl_type}: {unmatched} players not matched to local DB")

    return all_players


def save_synergy_data(conn: sqlite3.Connection, players: List[Dict],
                      verbose: bool = False) -> int:
    """
    Save synergy playtype stats to player_synergy_playtypes table.

    IMPORTANT: Uses partial UPSERT to preserve Playwright-populated fields
    (ft_freq_pct, tov_freq_pct, sf_freq_pct, and_one_freq_pct, score_freq_pct, percentile).
    """
    cursor = conn.cursor()
    saved = 0

    for p in players:
        try:
            # Hybrid UPSERT: Only update BDL-provided core stats
            # Do NOT update the 6 frequency fields that come from Playwright
            cursor.execute("""
                INSERT INTO player_synergy_playtypes (
                    player_name, team_abbr, season, playtype, games_played,
                    poss_per_game, freq_pct, ppp, pts_per_game, fgm, fga,
                    fg_pct, efg_pct, synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_name, season, playtype) DO UPDATE SET
                    team_abbr=excluded.team_abbr,
                    games_played=excluded.games_played,
                    poss_per_game=excluded.poss_per_game,
                    freq_pct=excluded.freq_pct,
                    ppp=excluded.ppp,
                    pts_per_game=excluded.pts_per_game,
                    fgm=excluded.fgm,
                    fga=excluded.fga,
                    fg_pct=excluded.fg_pct,
                    efg_pct=excluded.efg_pct,
                    synced_at=excluded.synced_at
                    -- DO NOT UPDATE: ft_freq_pct, tov_freq_pct, sf_freq_pct,
                    --                and_one_freq_pct, score_freq_pct, percentile
            """, (
                p['player_name'], p['team_abbr'], p['season'], p['playtype'], p['games_played'],
                p['poss_per_game'], p['freq_pct'], p['ppp'], p['pts_per_game'], p['fgm'], p['fga'],
                p['fg_pct'], p['efg_pct'], p['synced_at']
            ))
            saved += 1
        except sqlite3.Error as e:
            if verbose:
                print(f"   ⚠️ Error saving {p['player_name']} ({p['playtype']}): {e}")

    conn.commit()
    return saved


# ========================================
# MAIN
# ========================================

def main():
    parser = argparse.ArgumentParser(description="Sync BDL Tracking + Playtype Data")
    parser.add_argument('--all', action='store_true', help="Sync all 5 tables")
    parser.add_argument('--table', choices=['defense', 'drives', 'touches', 'speed', 'synergy'],
                        help="Sync specific table only")
    parser.add_argument('--verbose', '-v', action='store_true')
    parser.add_argument('--dry-run', action='store_true', help="Don't write to DB")
    parser.add_argument('--season', type=int, default=2025, help="BDL season year (default: 2025)")
    args = parser.parse_args()

    global BDL_SEASON
    BDL_SEASON = args.season

    client = BDLClient(api_key=os.getenv('BALLDONTLIE_KEY'))
    if not client.api_key:
        print("❌ BALLDONTLIE_KEY not set. Cannot sync BDL tracking data.")
        return

    conn = get_db_connection()
    team_lookup = _build_team_lookup(conn)

    if args.verbose:
        print(f"[BDL Tracking] Team lookup: {len(team_lookup)} players mapped")

    total_saved = 0

    # Determine which tables to sync
    tables = []
    if args.all:
        tables = ['defense', 'drives', 'touches', 'speed', 'synergy']
    elif args.table:
        tables = [args.table]
    else:
        print("❌ Must specify --all or --table [name]")
        return

    # Execute syncs
    for table in tables:
        if table == 'defense':
            players = fetch_defense_data(client, team_lookup, verbose=args.verbose)
            if not args.dry_run:
                saved = save_defense_data(conn, players, verbose=args.verbose)
                total_saved += saved
                print(f"[Defense] Saved {saved} records")
            else:
                print(f"[Defense] Dry run — would save {len(players)} records")

        elif table == 'drives':
            players = fetch_drives_data(client, team_lookup, verbose=args.verbose)
            if not args.dry_run:
                saved = save_drives_data(conn, players, verbose=args.verbose)
                total_saved += saved
                print(f"[Drives] Saved {saved} records")
            else:
                print(f"[Drives] Dry run — would save {len(players)} records")

        elif table == 'touches':
            players = fetch_touches_data(client, team_lookup, verbose=args.verbose)
            if not args.dry_run:
                saved = save_touches_data(conn, players, verbose=args.verbose)
                total_saved += saved
                print(f"[Touches] Saved {saved} records")
            else:
                print(f"[Touches] Dry run — would save {len(players)} records")

        elif table == 'speed':
            players = fetch_speed_data(client, team_lookup, verbose=args.verbose)
            if not args.dry_run:
                saved = save_speed_data(conn, players, verbose=args.verbose)
                total_saved += saved
                print(f"[Speed] Saved {saved} records")
            else:
                print(f"[Speed] Dry run — would save {len(players)} records")

        elif table == 'synergy':
            players = fetch_synergy_data(client, team_lookup, verbose=args.verbose)
            if not args.dry_run:
                saved = save_synergy_data(conn, players, verbose=args.verbose)
                total_saved += saved
                print(f"[Synergy] Saved {saved} records (8 playtypes, core stats only)")
            else:
                print(f"[Synergy] Dry run — would save {len(players)} records")

    conn.close()
    print(f"\n{'='*50}")
    if not args.dry_run:
        print(f"BDL Tracking Sync Complete. Total records saved: {total_saved}")
    else:
        print(f"BDL Tracking Dry Run Complete. No data written to database.")


if __name__ == "__main__":
    main()
