"""
PBP Stats API Client
Fetches shot quality, WOWY, leverage, and on/off data from api.pbpstats.com

Based on official OpenAPI spec: https://api.pbpstats.com/openapi.json
No API key required.
"""
import requests
from typing import Dict, List, Optional


BASE_URL = "https://api.pbpstats.com"
CURRENT_SEASON = "2025-26"


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
        response = requests.get(url, params=params, timeout=30)
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
        response = requests.get(url, params=params, timeout=30)
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
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching totals: {e}")
        return None


def get_wowy_stats(team_id: str, player_ids: List[str],
                   season: str = CURRENT_SEASON, season_type: str = "Regular Season",
                   entity_type: str = "Team") -> Optional[Dict]:
    """
    Get WOWY (With-Or-Without-You) stats for given players.
    
    This endpoint shows team/lineup stats when specific players are on/off.
    
    Args:
        team_id: NBA.com team ID
        player_ids: List of player IDs to analyze
        season: Season string
        season_type: "Regular Season" or "Playoffs"
        entity_type: "Team" or "Player"
    
    Returns:
        Dict with WOWY stats
    """
    url = f"{BASE_URL}/get-wowy-stats/nba"
    params = {
        "Season": season,
        "SeasonType": season_type,
        "TeamId": team_id,
        "Type": entity_type,
        # Player filters are added as special params
        "0Exactly1OnFloor": ",".join(player_ids)
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching WOWY stats: {e}")
        return None


def get_wowy_combination_stats(team_id: str, player_ids: List[str],
                               season: str = CURRENT_SEASON, 
                               season_type: str = "Regular Season") -> Optional[Dict]:
    """
    Get all on/off combinations for selected players.
    
    Args:
        team_id: NBA.com team ID
        player_ids: List of player IDs (comma-separated in request)
        season: Season string
        season_type: "Regular Season" or "Playoffs"
    
    Returns:
        Dict with all combination stats (on/off efficiency)
    """
    url = f"{BASE_URL}/get-wowy-combination-stats/nba"
    params = {
        "Season": season,
        "SeasonType": season_type,
        "TeamId": team_id,
        "PlayerIds": ",".join(player_ids)
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching WOWY combo stats: {e}")
        return None


def get_on_off(team_id: str, player_id: str, stat_type: str = "player",
               season: str = CURRENT_SEASON, season_type: str = "Regular Season",
               leverage: str = None) -> Optional[Dict]:
    """
    Get on/off data for a player.
    
    Args:
        team_id: NBA.com team ID
        player_id: NBA.com player ID
        stat_type: "player", "team", or "stat"
        season: Season string
        season_type: "Regular Season" or "Playoffs"
        leverage: Optional filter ("Medium,High,VeryHigh")
    
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
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching on/off data: {e}")
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
        response = requests.get(url, params=params, timeout=30)
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
        response = requests.get(url, params=params, timeout=30)
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
        response = requests.get(url, timeout=30)
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
        response = requests.get(url, timeout=30)
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
        response = requests.get(url, params=params, timeout=30)
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
