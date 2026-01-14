"""
Daily Lock Configuration Helper
Reads and validates config/daily_locks.json for targeted game filtering.
"""
import json
import os
from typing import Dict, List, Optional
from utils.time_utils import get_est_today


CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'daily_locks.json')


def get_target_config() -> Optional[Dict]:
    """
    Read the daily_locks.json configuration file.
    
    Returns:
        Dict with lock_date, mode, target_matchups, filters
        None if file doesn't exist or is invalid
    """
    if not os.path.exists(CONFIG_PATH):
        print("[DAILY_LOCK] No config file found, running in LIVE mode (all games)")
        return None
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # Validate required fields
        if 'lock_date' not in config or 'mode' not in config:
            print("[DAILY_LOCK] WARNING: Config missing required fields, running LIVE mode")
            return None
        
        return config
    except json.JSONDecodeError as e:
        print(f"[DAILY_LOCK] ERROR: Invalid JSON in config file: {e}")
        return None


def validate_lock_date(config: Dict) -> bool:
    """
    Verify the lock_date matches today's EST date.
    Prevents using stale configurations.
    
    Returns:
        True if valid, False if stale
    """
    if not config:
        return True  # No config = LIVE mode, always valid
    
    today = get_est_today()
    lock_date = config.get('lock_date', '')
    
    if lock_date != today:
        print(f"[DAILY_LOCK] WARNING: Config date ({lock_date}) != Today ({today})")
        print("[DAILY_LOCK] Running in LIVE mode (ignoring stale config)")
        return False
    
    return True


def filter_slate_by_config(slate: List[Dict], config: Optional[Dict]) -> List[Dict]:
    """
    Filter the slate based on daily_locks.json configuration.
    
    Args:
        slate: List of game dictionaries with 'game_id' key
        config: Configuration from get_target_config()
    
    Returns:
        Filtered slate (or full slate if LIVE mode)
    """
    if not config:
        return slate  # LIVE mode - process all games
    
    if not validate_lock_date(config):
        return slate  # Stale config - process all games
    
    mode = config.get('mode', 'LIVE')
    target_matchups = config.get('target_matchups', [])
    
    if mode == 'TESTING' and target_matchups:
        # Filter to only target matchups
        filtered = [g for g in slate if g.get('game_id') in target_matchups]
        print(f"[DAILY_LOCK] TESTING MODE: Filtering to {len(filtered)} target games")
        return filtered
    
    if mode == 'LIVE' and target_matchups:
        # Mark target games as priority but process all
        for game in slate:
            if game.get('game_id') in target_matchups:
                game['priority'] = True
        print(f"[DAILY_LOCK] LIVE MODE: {len(target_matchups)} games marked as priority")
    
    return slate


def apply_filters(slate: List[Dict], config: Optional[Dict]) -> List[Dict]:
    """
    Apply spread/total filters from configuration.
    
    Args:
        slate: List of game dictionaries
        config: Configuration with 'filters' key
    
    Returns:
        Filtered slate
    """
    if not config or 'filters' not in config:
        return slate
    
    filters = config.get('filters', {})
    max_spread = filters.get('max_spread')
    min_total = filters.get('min_total')
    
    filtered = slate
    
    if max_spread is not None:
        filtered = [g for g in filtered if abs(g.get('spread', 0)) <= max_spread]
        print(f"[DAILY_LOCK] Applied max_spread filter ({max_spread}): {len(filtered)} games remain")
    
    if min_total is not None:
        filtered = [g for g in filtered if g.get('total', 0) >= min_total]
        print(f"[DAILY_LOCK] Applied min_total filter ({min_total}): {len(filtered)} games remain")
    
    return filtered


if __name__ == "__main__":
    # Test the configuration loader
    config = get_target_config()
    if config:
        print(f"Loaded config: {json.dumps(config, indent=2)}")
        print(f"Date valid: {validate_lock_date(config)}")
    else:
        print("No valid config found, would run in LIVE mode")
