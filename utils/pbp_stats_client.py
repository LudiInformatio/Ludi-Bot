"""
PBP Stats API Client
Fetches shot quality, WOWY, leverage, and on/off data from api.pbpstats.com

Based on official OpenAPI spec: https://api.pbpstats.com/openapi.json
No API key required.
"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, List, Optional
import os
import json
import hashlib
from datetime import datetime, timedelta


BASE_URL = "https://api.pbpstats.com"
CURRENT_SEASON = "2025-26"
CACHE_DIR = "cache/pbp_stats"
CACHE_TTL_HOURS = 24  # Cache expires after 24 hours

def _get_session():
    session = requests.Session()
    # Add browser-like headers to avoid 403 Forbidden
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.pbpstats.com/',
        'Origin': 'https://www.pbpstats.com'
    })
    retry = Retry(
        total=3,  # Reduced from 5 (faster failure, less wasted time)
        backoff_factor=2,  # Increased from 1 (exponential: 2s, 4s, 8s)
        status_forcelist=[429, 500, 502, 503, 504],  # Added 429 rate limit
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

_session = _get_session()


def _get_cache_path(endpoint: str, params: Dict) -> str:
    """
    Generate cache file path based on endpoint and params.

    Uses MD5 hash of sorted params for deterministic cache keys.
    This ensures same query always maps to same cache file.

    Args:
        endpoint: API endpoint name (e.g., 'get_on_off')
        params: Request parameters dict

    Returns:
        Path to cache file
    """
    # Sort params for consistent hashing
    param_str = json.dumps(params, sort_keys=True)
    param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]

    # Create cache filename: endpoint_hash.json
    cache_file = f"{endpoint}_{param_hash}.json"
    return os.path.join(CACHE_DIR, cache_file)


def _read_cache(cache_path: str) -> Optional[Dict]:
    """
    Read from cache if file exists and is not expired.

    TTL-based expiration: Files older than CACHE_TTL_HOURS are ignored.

    Args:
        cache_path: Path to cache file

    Returns:
        Cached data dict or None if expired/missing
    """
    if not os.path.exists(cache_path):
        return None

    # Check if cache is expired (TTL = 24 hours)
    file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
    if datetime.now() - file_time > timedelta(hours=CACHE_TTL_HOURS):
        # Cache expired - could delete here but leave for debugging
        return None

    try:
        with open(cache_path, 'r') as f:
            return json.load(f)
    except Exception:
        # Corrupt cache file - ignore and fetch fresh
        return None


def _write_cache(cache_path: str, data: Dict) -> None:
    """
    Write data to cache file.

    Creates cache directory if it doesn't exist.
    Failures are silent (cache is optional, not critical).

    Args:
        cache_path: Path to cache file
        data: Data dict to cache
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        with open(cache_path, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        # Silent failure - cache is performance optimization, not critical
        print(f"[PBP_STATS] Warning: Failed to write cache: {e}")




def get_game_stats(game_id: str, stat_type: str = "Player") -> Optional[Dict]:
    """
    Get game stats by player or lineup.
    
    Args:
        game_id: NBA.com game ID (e.g., "0022500500")
        stat_type: "Player" or "Lineup"
    
    Returns:
        Dict with game stats
    """
    url = f"{BASE_URL}/get-game-stats"
    params = {
        "GameId": game_id,
        "Type": stat_type
    }
    
    try:
        response = _session.get(url, params=params, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching game stats for {game_id}: {e}")
        return None


def get_game_logs(entity_id: str, entity_type: str = "Player", 
                  season: str = CURRENT_SEASON, season_type: str = "Regular Season") -> Optional[Dict]:
    """
    Get game logs for player/team/lineup.
    
    Args:
        entity_id: Player ID, Team ID, or Lineup ID (dash-separated player IDs)
        entity_type: "Player", "Team", or "Lineup"
        season: Season string (e.g., "2025-26")
        season_type: "Regular Season" or "Playoffs"
    
    Returns:
        Dict with game log data
    """
    url = f"{BASE_URL}/get-game-logs/nba"
    params = {
        "Season": season,
        "SeasonType": season_type,
        "EntityType": entity_type,
        "EntityId": entity_id
    }
    
    try:
        response = _session.get(url, params=params, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching game logs for {entity_id}: {e}")
        return None


def get_totals(entity_type: str = "Player", team_id: str = None,
               season: str = CURRENT_SEASON, season_type: str = "Regular Season",
               leverage: str = None) -> Optional[Dict]:
    """
    Get season totals for players/teams/lineups.
    
    Args:
        entity_type: "Player", "Team", "Lineup", or "Opponent"
        team_id: NBA.com team ID (optional filter)
        season: Season string
        season_type: "Regular Season" or "Playoffs"
        leverage: Filter by leverage ("Low", "Medium", "High", "VeryHigh")
    
    Returns:
        Dict with totals data
    """
    url = f"{BASE_URL}/get-totals/nba"
    params = {
        "Season": season,
        "SeasonType": season_type,
        "Type": entity_type
    }
    
    if team_id:
        params["TeamId"] = team_id
    if leverage:
        params["Leverage"] = leverage
    
    try:
        response = _session.get(url, params=params, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching totals: {e}")
        return None


def get_wowy_stats(team_id: str, player_ids: List[str],
                   season: str = CURRENT_SEASON, season_type: str = "Regular Season",
                   entity_type: str = "Team", use_cache: bool = True) -> Optional[Dict]:
    """
    Get WOWY (With-Or-Without-You) stats for given players with optional caching.

    This endpoint shows team/lineup stats when specific players are on/off.

    Args:
        team_id: NBA.com team ID
        player_ids: List of player IDs to analyze
        season: Season string
        season_type: "Regular Season" or "Playoffs"
        entity_type: "Team" or "Player"
        use_cache: Enable local caching (default: True)

    Returns:
        Dict with WOWY stats
    """
    params = {
        "Season": season,
        "SeasonType": season_type,
        "TeamId": team_id,
        "Type": entity_type,
        # Player filters are added as special params
        "0Exactly1OnFloor": ",".join(player_ids)
    }

    # Check cache first
    if use_cache:
        cache_path = _get_cache_path("get_wowy_stats", params)
        cached = _read_cache(cache_path)
        if cached:
            return cached

    url = f"{BASE_URL}/get-wowy-stats/nba"

    # Try with 120s timeout first, fallback to 180s on timeout
    for timeout in [120, 180]:
        try:
            response = _session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            # Write to cache
            if use_cache:
                _write_cache(cache_path, data)

            return data
        except requests.exceptions.Timeout:
            if timeout == 120:
                print(f"[PBP_STATS] Timeout at 120s, retrying with 180s...")
                continue  # Try next timeout
            print(f"[PBP_STATS] Final timeout at 180s for WOWY stats")
            return None
        except requests.RequestException as e:
            print(f"[PBP_STATS] Error fetching WOWY stats: {e}")
            return None

    return None


def get_wowy_combination_stats(team_id: str, player_ids: List[str],
                               season: str = CURRENT_SEASON,
                               season_type: str = "Regular Season",
                               use_cache: bool = True) -> Optional[Dict]:
    """
    Get all on/off combinations for selected players with optional caching.

    Args:
        team_id: NBA.com team ID
        player_ids: List of player IDs (comma-separated in request)
        season: Season string
        season_type: "Regular Season" or "Playoffs"
        use_cache: Enable local caching (default: True)

    Returns:
        Dict with all combination stats (on/off efficiency)
    """
    params = {
        "Season": season,
        "SeasonType": season_type,
        "TeamId": team_id,
        "PlayerIds": ",".join(player_ids)
    }

    # Check cache first
    if use_cache:
        cache_path = _get_cache_path("get_wowy_combination_stats", params)
        cached = _read_cache(cache_path)
        if cached:
            return cached

    url = f"{BASE_URL}/get-wowy-combination-stats/nba"

    # Try with 120s timeout first, fallback to 180s on timeout
    for timeout in [120, 180]:
        try:
            response = _session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            # Write to cache
            if use_cache:
                _write_cache(cache_path, data)

            return data
        except requests.exceptions.Timeout:
            if timeout == 120:
                print(f"[PBP_STATS] Timeout at 120s, retrying with 180s...")
                continue  # Try next timeout
            print(f"[PBP_STATS] Final timeout at 180s for WOWY combo stats")
            return None
        except requests.RequestException as e:
            print(f"[PBP_STATS] Error fetching WOWY combo stats: {e}")
            return None

    return None


def get_on_off(team_id: str, player_id: str, stat_type: str = "player",
               season: str = CURRENT_SEASON, season_type: str = "Regular Season",
               leverage: str = None, use_cache: bool = True) -> Optional[Dict]:
    """
    Get on/off data for a player with optional caching and timeout fallback.

    Args:
        team_id: NBA.com team ID
        player_id: NBA.com player ID
        stat_type: "player", "team", or "stat"
        season: Season string
        season_type: "Regular Season" or "Playoffs"
        leverage: Optional filter ("Medium,High,VeryHigh")
        use_cache: Enable local caching (default: True)

    Returns:
        Dict with on/off stats
    """
    url = f"{BASE_URL}/get-on-off/nba/{stat_type}"
    params = {
        "Season": season,
        "SeasonType": season_type,
        "TeamId": team_id,
        "PlayerId": player_id
    }

    if leverage:
        params["Leverage"] = leverage

    # Check cache first
    if use_cache:
        cache_path = _get_cache_path("get_on_off", params)
        cached = _read_cache(cache_path)
        if cached:
            return cached

    # Try with 120s timeout first, fallback to 180s on timeout
    for timeout in [120, 180]:
        try:
            response = _session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            # Write to cache for future requests
            if use_cache:
                _write_cache(cache_path, data)

            return data
        except requests.exceptions.Timeout:
            if timeout == 120:
                print(f"[PBP_STATS] Timeout at 120s, retrying with 180s...")
                continue  # Try next timeout
            print(f"[PBP_STATS] Final timeout at 180s for on/off data")
            return None
        except requests.RequestException as e:
            print(f"[PBP_STATS] Error fetching on/off data: {e}")
            return None

    return None


def get_assist_combo_summary(season: str = CURRENT_SEASON,
                             season_type: str = "Regular Season") -> Optional[Dict]:
    """Get all passer-to-scorer assist combinations for the season."""
    cache_path = _get_cache_path("assist_combo_summary", {"season": season, "season_type": season_type})
    cached = _read_cache(cache_path)
    if cached:
        return cached

    try:
        response = _session.get(
            f"{BASE_URL}/get-assist-combo-summary/nba",
            params={"Season": season, "SeasonType": season_type},
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        _write_cache(cache_path, data)
        return data
    except Exception as e:
        print(f"[PBP_STATS] Error fetching assist combos: {e}")
        return None


def get_shots(entity_id: str, entity_type: str = "Player",
              season: str = CURRENT_SEASON, season_type: str = "Regular Season") -> Optional[Dict]:
    """
    Get all shots for a player/team.
    
    Args:
        entity_id: Player ID or Team ID
        entity_type: "Player" or "Team"
        season: Season string
        season_type: "Regular Season" or "Playoffs"
    
    Returns:
        Dict with shot data including distance, location, result
    """
    url = f"{BASE_URL}/get-shots/nba"
    params = {
        "Season": season,
        "SeasonType": season_type,
        "EntityType": entity_type,
        "EntityId": entity_id
    }
    
    try:
        response = _session.get(url, params=params, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching shots: {e}")
        return None


def get_team_leverage_summary(season: str = CURRENT_SEASON, 
                              leverage: str = None) -> Optional[Dict]:
    """
    Get team stats broken down by leverage state.
    
    Args:
        season: Season string
        leverage: Filter ("Low", "Medium", "High", "VeryHigh" or comma-separated)
    
    Returns:
        Dict with team leverage summary
    """
    url = f"{BASE_URL}/get-team-leverage-summary/nba"
    params = {"Season": season}
    
    if leverage:
        params["Leverage"] = leverage
    
    try:
        response = _session.get(url, params=params, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching leverage summary: {e}")
        return None


def get_live_games() -> Optional[Dict]:
    """
    Get all today's NBA games.
    
    Returns:
        Dict with today's game list
    """
    url = f"{BASE_URL}/live/games/nba"
    
    try:
        response = _session.get(url, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching live games: {e}")
        return None


def get_all_players() -> Optional[Dict]:
    """
    Get all NBA players.
    
    Returns:
        Dict with all player IDs and names
    """
    url = f"{BASE_URL}/get-all-players-for-league/nba"
    
    try:
        response = _session.get(url, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching all players: {e}")
        return None


def get_team_players(team_id: str, season: str = CURRENT_SEASON,
                     season_type: str = "Regular Season") -> Optional[Dict]:
    """
    Get all players who played for a team in a season.
    
    Args:
        team_id: NBA.com team ID
        season: Season string
        season_type: "Regular Season" or "Playoffs"
    
    Returns:
        Dict with player list
    """
    url = f"{BASE_URL}/get-team-players-for-season"
    params = {
        "Season": season,
        "SeasonType": season_type,
        "TeamId": team_id
    }
    
    try:
        response = _session.get(url, params=params, timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching team players: {e}")
        return None


# --- Helper functions for Ludi Bot integration ---

def get_player_shot_quality(player_id: str, season: str = CURRENT_SEASON) -> Optional[Dict]:
    """
    Calculate shot quality metrics for a player.
    
    Returns dict with:
        - at_rim_pct: % of shots at rim
        - mid_range_pct: % of shots in mid-range
        - three_pt_pct: % of shots from 3
        - shot_quality_score: Weighted quality score (0-1)
    """
    shots_data = get_shots(player_id, "Player", season)
    if not shots_data:
        return None
    
    shots = shots_data.get('multi_row_table_data', [])
    if not shots:
        return None
    
    # Count by zone
    at_rim = sum(1 for s in shots if s.get('ShotType') == 'AtRim')
    short_mid = sum(1 for s in shots if s.get('ShotType') == 'ShortMidRange')
    long_mid = sum(1 for s in shots if s.get('ShotType') == 'LongMidRange')
    corner_3 = sum(1 for s in shots if s.get('ShotType') == 'Corner3')
    arc_3 = sum(1 for s in shots if s.get('ShotType') == 'Arc3')
    
    total = len(shots)
    
    # Quality scoring (at-rim and corner 3s are highest value)
    quality_score = (at_rim * 0.65 + corner_3 * 0.40 + arc_3 * 0.36 + 
                     short_mid * 0.40 + long_mid * 0.38) / (total or 1)
    
    return {
        'player_id': player_id,
        'total_shots': total,
        'at_rim_pct': at_rim / total if total else 0,
        'mid_range_pct': (short_mid + long_mid) / total if total else 0,
        'three_pt_pct': (corner_3 + arc_3) / total if total else 0,
        'corner_3_pct': corner_3 / total if total else 0,
        'shot_quality_score': round(quality_score, 3)
    }


def get_player_on_off_impact(player_id: str, team_id: str, 
                              season: str = CURRENT_SEASON) -> Optional[Dict]:
    """
    Get player's on/off court impact.
    
    Returns dict with:
        - on_court_off_rtg: Team offensive rating with player on
        - off_court_off_rtg: Team offensive rating with player off
        - on_off_diff: Difference (positive = player helps)
    """
    on_off = get_on_off(team_id, player_id, "player", season)
    if not on_off:
        return None
    
    data = on_off.get('multi_row_table_data', [])
    if len(data) < 2:
        return None
    
    # First row is typically "On", second is "Off"
    on_row = next((d for d in data if d.get('OnOff') == 'On'), data[0])
    off_row = next((d for d in data if d.get('OnOff') == 'Off'), data[1] if len(data) > 1 else {})
    
    return {
        'player_id': player_id,
        'team_id': team_id,
        'on_court_off_rtg': on_row.get('OffRtg', 0),
        'off_court_off_rtg': off_row.get('OffRtg', 0),
        'on_court_def_rtg': on_row.get('DefRtg', 0),
        'off_court_def_rtg': off_row.get('DefRtg', 0),
        'on_off_diff': on_row.get('OffRtg', 0) - off_row.get('OffRtg', 0),
        'on_court_poss': on_row.get('OffPoss', 0),
        'off_court_poss': off_row.get('OffPoss', 0)
    }


def get_shot_quality(game_id: str) -> Optional[List[Dict]]:
    """
    Get shot quality data for all players in a specific game.

    Uses native ShotQualityAvg from PBP Stats API (expected field goal value
    based on shot distance, defender proximity, etc).

    Args:
        game_id: NBA.com game ID (e.g., "0022500500")

    Returns:
        List of dicts with player shot quality data:
            - player_id
            - player_name
            - shot_quality_avg (native from API - expected FG%)
            - shot_distance_avg (weighted avg of 2pt/3pt distances)
            - shots_taken (FGA)
            - shots_made (FGM)
    """
    game_data = get_game_stats(game_id, "Player")
    if not game_data:
        return None

    # Parse stats structure: stats.Away.1[] + stats.Home.1[]
    stats = game_data.get('stats', {})
    away_players = stats.get('Away', {}).get('1', [])
    home_players = stats.get('Home', {}).get('1', [])

    all_players = away_players + home_players
    if not all_players:
        return None

    result = []
    for p in all_players:
        # Skip team totals row
        if p.get('EntityId') == '0' or p.get('Name') == 'Team':
            continue

        # Get native shot quality and distance from API
        shot_quality = p.get('ShotQualityAvg', 0) or 0
        avg_2pt_dist = p.get('Avg2ptShotDistance', 8) or 8
        avg_3pt_dist = p.get('Avg3ptShotDistance', 24) or 24

        # Calculate FGA/FGM from component attempts
        fg2a = p.get('FG2A', 0) or 0
        fg3a = p.get('FG3A', 0) or 0
        fg2m = p.get('FG2M', 0) or 0
        fg3m = p.get('FG3M', 0) or 0
        fga = fg2a + fg3a
        fgm = fg2m + fg3m

        # Calculate weighted average shot distance
        if fga > 0:
            avg_distance = (fg2a * avg_2pt_dist + fg3a * avg_3pt_dist) / fga
        else:
            avg_distance = 0

        result.append({
            'player_id': p.get('EntityId'),
            'player_name': p.get('Name'),
            'shot_quality_avg': round(shot_quality, 4),
            'shot_distance_avg': round(avg_distance, 1),
            'shots_taken': fga,
            'shots_made': fgm
        })

    return result


if __name__ == "__main__":
    print("[PBP_STATS] Testing API client (using official spec)...\n")
    
    # Test live games
    print("1. Fetching today's games...")
    games = get_live_games()
    if games:
        print(f"   ✅ Found data: {type(games)}")
    
    # Test all players
    print("\n2. Fetching all players...")
    players = get_all_players()
    if players:
        print(f"   ✅ Found player data")
    
    # Test team totals
    print("\n3. Fetching team totals (Lakers: 1610612747)...")
    totals = get_totals("Team", "1610612747", CURRENT_SEASON)
    if totals:
        print(f"   ✅ Got totals data")
    
    print("\n✅ API client tests complete")
