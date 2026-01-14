"""
PBP Stats API Client
Fetches shot quality, WOWY, and leverage data from api.pbpstats.com
"""
import requests
from typing import Dict, List, Optional


BASE_URL = "https://api.pbpstats.com"


def get_game_stats(game_id: str, stat_type: str = "Player") -> Optional[Dict]:
    """
    Fetch player or team stats for a specific game.
    
    Args:
        game_id: NBA game ID (e.g., "0022500XXX")
        stat_type: "Player" or "Team"
    
    Returns:
        Dict with game stats or None if error
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


def get_shot_quality(game_id: str) -> Optional[List[Dict]]:
    """
    Fetch shot quality data for all players in a game.
    
    Returns list of dicts with:
        - player_id
        - shot_quality_avg (0-1 score, higher = better shot selection)
        - shot_distance_avg
    """
    url = f"{BASE_URL}/get-shots"
    params = {
        "GameId": game_id
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Aggregate by player
        player_shots = {}
        for shot in data.get('shots', []):
            player_id = shot.get('PlayerId')
            if player_id not in player_shots:
                player_shots[player_id] = {
                    'player_id': player_id,
                    'player_name': shot.get('PlayerName', ''),
                    'shots': [],
                    'made': 0,
                    'total': 0
                }
            
            player_shots[player_id]['shots'].append(shot)
            player_shots[player_id]['total'] += 1
            if shot.get('Made', False):
                player_shots[player_id]['made'] += 1
        
        # Calculate shot quality averages
        results = []
        for player_id, data in player_shots.items():
            shots = data['shots']
            if not shots:
                continue
            
            # Calculate average shot distance and quality
            distances = [s.get('ShotDistance', 0) for s in shots if s.get('ShotDistance')]
            avg_distance = sum(distances) / len(distances) if distances else 0
            
            # Shot quality approximation (closer to basket = higher quality, except for 3s)
            quality_scores = []
            for s in shots:
                dist = s.get('ShotDistance', 0)
                if dist <= 4:  # At rim
                    quality_scores.append(0.65)
                elif dist <= 10:  # Mid-range short
                    quality_scores.append(0.45)
                elif dist <= 16:  # Mid-range long
                    quality_scores.append(0.40)
                elif dist <= 24:  # 3-pointer
                    quality_scores.append(0.38)
                else:  # Deep 3
                    quality_scores.append(0.35)
            
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            results.append({
                'player_id': player_id,
                'player_name': data['player_name'],
                'shot_quality_avg': round(avg_quality, 3),
                'shot_distance_avg': round(avg_distance, 1),
                'shots_taken': data['total'],
                'shots_made': data['made']
            })
        
        return results
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching shot quality for {game_id}: {e}")
        return None


def get_game_logs(player_id: str, season: str = "2025-26", league: str = "nba") -> Optional[List[Dict]]:
    """
    Fetch game logs for a player for the season.
    
    Args:
        player_id: PBP Stats player ID
        season: Season string (e.g., "2025-26")
        league: League identifier
    
    Returns:
        List of game log entries
    """
    url = f"{BASE_URL}/get-game-logs/{league}"
    params = {
        "Season": season,
        "PlayerId": player_id
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json().get('multi_row_table_data', [])
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching game logs for {player_id}: {e}")
        return None


def get_wowy_data(player_id: str, teammate_id: str, season: str = "2025-26") -> Optional[Dict]:
    """
    Fetch With-Or-Without-You data for a player pair.
    
    Args:
        player_id: Primary player ID
        teammate_id: Teammate to compare (e.g., star player)
        season: Season string
    
    Returns:
        Dict with on/off court efficiency differentials
    """
    # Note: PBP Stats WOWY requires specific endpoint structure
    # This is a simplified implementation - may need adjustment based on actual API
    url = f"{BASE_URL}/get-lineups/nba"
    params = {
        "Season": season,
        "PlayerId": player_id
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Parse lineup data to find with/without teammate scenarios
        with_teammate = []
        without_teammate = []
        
        for lineup in data.get('multi_row_table_data', []):
            players = lineup.get('PlayerIds', [])
            if teammate_id in players:
                with_teammate.append(lineup)
            else:
                without_teammate.append(lineup)
        
        # Calculate averages
        def calc_avg(lineups, key):
            vals = [l.get(key, 0) for l in lineups if l.get(key)]
            return sum(vals) / len(vals) if vals else 0
        
        return {
            'player_id': player_id,
            'teammate_id': teammate_id,
            'with_teammate': {
                'minutes': sum(l.get('Minutes', 0) for l in with_teammate),
                'off_rtg': calc_avg(with_teammate, 'OffRtg'),
                'def_rtg': calc_avg(with_teammate, 'DefRtg')
            },
            'without_teammate': {
                'minutes': sum(l.get('Minutes', 0) for l in without_teammate),
                'off_rtg': calc_avg(without_teammate, 'OffRtg'),
                'def_rtg': calc_avg(without_teammate, 'DefRtg')
            }
        }
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching WOWY data: {e}")
        return None


def get_leverage_stats(game_id: str) -> Optional[List[Dict]]:
    """
    Fetch leverage/clutch stats for a game.
    
    Returns player performance in high-pressure situations.
    """
    url = f"{BASE_URL}/get-possessions"
    params = {
        "GameId": game_id
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Filter for clutch possessions (last 5 min, within 5 points)
        clutch = []
        for poss in data.get('possessions', []):
            remaining = poss.get('SecondsRemaining', 300)
            margin = abs(poss.get('ScoreMargin', 0))
            
            if remaining <= 300 and margin <= 5:
                clutch.append(poss)
        
        # Aggregate by player
        player_clutch = {}
        for poss in clutch:
            player_id = poss.get('PrimaryPlayerId')
            if player_id:
                if player_id not in player_clutch:
                    player_clutch[player_id] = {'possessions': 0, 'points': 0}
                player_clutch[player_id]['possessions'] += 1
                player_clutch[player_id]['points'] += poss.get('Points', 0)
        
        return [
            {
                'player_id': pid,
                'clutch_possessions': data['possessions'],
                'clutch_points': data['points'],
                'leverage_score': data['points'] / max(data['possessions'], 1)
            }
            for pid, data in player_clutch.items()
        ]
    except requests.RequestException as e:
        print(f"[PBP_STATS] Error fetching leverage stats: {e}")
        return None


if __name__ == "__main__":
    # Test the client
    print("[PBP_STATS] Testing API client...")
    
    # Test with a sample game ID (use a real one for actual testing)
    test_game = "0022500500"
    
    print(f"\nFetching game stats for {test_game}...")
    stats = get_game_stats(test_game)
    if stats:
        print(f"Got stats: {len(stats)} entries")
    
    print(f"\nFetching shot quality for {test_game}...")
    shots = get_shot_quality(test_game)
    if shots:
        print(f"Got shot quality for {len(shots)} players")
        for s in shots[:3]:
            print(f"  {s['player_name']}: SQ={s['shot_quality_avg']}")
