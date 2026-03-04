"""
Game Intelligence Cache Module

Provides caching for game notes, lineups, and injury data to avoid
redundant Claude calls and enable faster re-runs.

Cache Schema per game_key (e.g. "IND@WAS"):
{
    "game_date": "2026-02-25",
    "tip_time_et": "19:00",
    "lineup_confirmed": false,
    "starters": {"IND": [...], "WAS": [...]},
    "key_angle": "",
    "injuries": {},             # {player: {status, reason, confirmed_at}}
    "player_snapshots": {},     # {player: status} for injury delta check
    "notes_text": "",           # Claude narrative output
    "projections_summary": {},  # top props for this game
    "generated_at": null,
    "refreshed_at": null
}
"""

import json
import sqlite3
import unicodedata
import os
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from pathlib import Path as _Path


CACHE_DIR = _Path(__file__).parent.parent / "cache"


def _normalize_for_lookup(name: str) -> str:
    nfkd = unicodedata.normalize('NFKD', name)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def get_cache_path(date_str: Optional[str] = None) -> str:
    """
    Returns the path to the game intelligence cache file.
    
    Args:
        date_str: Optional date string (YYYY-MM-DD). Defaults to today.
        
    Returns:
        Full path to cache file: cache/game_intelligence_YYYY-MM-DD.json
    """
    if date_str is None:
        date_str = date.today().strftime('%Y-%m-%d')
    
    CACHE_DIR.mkdir(exist_ok=True)
    return str(CACHE_DIR / f"game_intelligence_{date_str}.json")


def load_game_cache(game_key: str, date_str: Optional[str] = None) -> Optional[Dict]:
    """
    Load cached data for a specific game.
    
    Args:
        game_key: Game key (e.g., "IND@WAS")
        date_str: Optional date string (YYYY-MM-DD). Defaults to today.
        
    Returns:
        Cache dict for the game, or None if not found.
    """
    cache_path = get_cache_path(date_str)
    cache_file = Path(cache_path)
    
    if not cache_file.exists():
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        return cache_data.get(game_key)
    except (json.JSONDecodeError, IOError):
        return None


def write_game_cache(game_key: str, data: Dict, date_str: Optional[str] = None) -> bool:
    """
    Write cache data for a specific game.
    
    Args:
        game_key: Game key (e.g., "IND@WAS")
        data: Cache data dict to write
        date_str: Optional date string (YYYY-MM-DD). Defaults to today.
        
    Returns:
        True if successful, False otherwise.
    """
    cache_path = get_cache_path(date_str)
    cache_file = Path(cache_path)
    
    cache_data = {}
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    cache_data[game_key] = data
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        return True
    except IOError:
        return False


def check_cache_valid(game_key: str, conn: sqlite3.Connection, date_str: Optional[str] = None) -> Tuple[bool, List[str]]:
    """
    Check if game cache is valid for reuse.
    
    Validation checks:
    1. game_date matches today
    2. lineup_confirmed=True
    3. No injury delta vs player_snapshots
    
    Args:
        game_key: Game key (e.g., "IND@WAS")
        conn: SQLite database connection
        date_str: Optional date string. Defaults to today.
        
    Returns:
        Tuple of (is_valid, list_of_changed_players)
    """
    cache_data = load_game_cache(game_key, date_str)
    
    if not cache_data:
        return False, []
    
    today = date.today().strftime('%Y-%m-%d')
    if cache_data.get('game_date') != today:
        return False, []
    
    if not cache_data.get('lineup_confirmed', False):
        return False, []
    
    cached_snapshots = cache_data.get('player_snapshots', {})
    if not cached_snapshots:
        return False, []
    
    changed_players = []
    
    cursor = conn.cursor()
    
    for player, cached_status in cached_snapshots.items():
        cursor.execute("""
            SELECT status FROM player_injuries
            WHERE LOWER(player_name) = ?
              AND resolved_at IS NULL
            ORDER BY snapshot_time DESC
            LIMIT 1
        """, (_normalize_for_lookup(player),))
        
        row = cursor.fetchone()
        
        if row is None:
            if cached_status not in ['ACTIVE', 'HEALTHY', None]:
                changed_players.append(player)
        else:
            current_status = row[0]
            if current_status != cached_status:
                changed_players.append(player)
    
    return len(changed_players) == 0, changed_players


def mark_lineup_confirmed(game_key: str, starters: Dict[str, List[str]], date_str: Optional[str] = None) -> bool:
    """
    Mark a game's lineup as confirmed.
    
    Args:
        game_key: Game key (e.g., "IND@WAS")
        starters: Dict mapping team_abbr -> list of starter names
        date_str: Optional date string. Defaults to today.
        
    Returns:
        True if successful.
    """
    cache_data = load_game_cache(game_key, date_str)
    
    if cache_data is None:
        cache_data = {}
    
    cache_data['lineup_confirmed'] = True
    cache_data['starters'] = starters
    cache_data['refreshed_at'] = datetime.now().isoformat()
    
    return write_game_cache(game_key, cache_data, date_str)


def invalidate_game(game_key: str, reason: str, date_str: Optional[str] = None) -> bool:
    """
    Invalidate a game's cache entry.
    
    Args:
        game_key: Game key (e.g., "IND@WAS")
        reason: Reason for invalidation
        date_str: Optional date string. Defaults to today.
        
    Returns:
        True if successful.
    """
    cache_data = load_game_cache(game_key, date_str)
    
    if cache_data is None:
        return False
    
    cache_data['lineup_confirmed'] = False
    cache_data['invalidation_reason'] = reason
    cache_data['refreshed_at'] = datetime.now().isoformat()
    
    return write_game_cache(game_key, cache_data, date_str)


def get_all_game_keys(date_str: Optional[str] = None) -> List[str]:
    """
    Get all game keys in the cache.
    
    Args:
        date_str: Optional date string. Defaults to today.
        
    Returns:
        List of game keys.
    """
    cache_data = load_game_cache("__ALL__", date_str)
    
    if cache_data is None:
        cache_path = get_cache_path(date_str)
        cache_file = Path(cache_path)
        
        if not cache_file.exists():
            return []
        
        try:
            with open(cache_file, 'r') as f:
                return list(json.load(f).keys())
        except (json.JSONDecodeError, IOError):
            return []
    
    return list(cache_data.keys()) if cache_data else []


def cleanup_old_caches(days_to_keep: int = 1) -> int:
    """
    Delete old cache files, keeping only the specified number of days.
    
    Args:
        days_to_keep: Number of days to keep. Defaults to 1 (only today).
        
    Returns:
        Number of files deleted.
    """
    if not CACHE_DIR.exists():
        return 0
    
    deleted = 0
    today = date.today()
    
    for cache_file in CACHE_DIR.glob("game_intelligence_*.json"):
        try:
            date_str = cache_file.stem.replace("game_intelligence_", "")
            file_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            if (today - file_date).days > days_to_keep:
                cache_file.unlink()
                deleted += 1
        except ValueError:
            pass
    
    return deleted
