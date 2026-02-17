"""
LUDI INFORMATIO | NBA API CLIENT WRAPPER
=========================================
Wraps nba_api library with caching, rate limiting, and error handling.

Features:
- 1 req/sec rate limiting (NBA.com throttling prevention)
- 24-hour JSON cache in /cache/nba_api/
- Retry with exponential backoff
- Integration with API monitoring

Usage:
    from utils.nba_api_client import get_nba_client

    client = get_nba_client()
    splits = client.get_player_shooting_splits(player_id=203507, season="2025-26")

    # Or look up player ID first
    player_id = client.get_player_id("Giannis Antetokounmpo")
    difficulty = client.get_player_shot_difficulty(player_id, season="2025-26")
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from functools import wraps

# Unicode normalization for international player names
from unidecode import unidecode

# nba_api imports
from nba_api.stats.endpoints import (
    playerdashboardbyshootingsplits,
    playerdashptshots,
    playerdashptshotdefend,
    playervsplayer,
    playerdashptreb,
    playerdashptpass,
    commonplayerinfo,
    boxscorematchupsv3,
    leaguegamefinder,
    playbyplayv3
)
from nba_api.stats.static import players as nba_players
from nba_api.stats.static import teams as nba_teams

# Ludi utilities
from utils.api_helpers import retry_with_backoff, get_circuit_breaker
from utils.api_monitor import get_monitor


class NBAAPIClient:
    """
    Client wrapper for nba_api with caching and rate limiting.

    Rate Limit: 1 request per second (NBA.com enforced)
    Cache: 24 hours for historical data
    """

    def __init__(self, cache_dir: str = "cache/nba_api"):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: NBA API CLIENT ONLINE")
        print(f"   >>> Rate Limit: 1 req/sec")
        print(f"   >>> Cache TTL: 24 hours")
        print(f"{'='*40}")

        self.cache_dir = cache_dir
        self.last_request_time = 0.0
        self.rate_limit_delay = 1.0  # 1 second between requests

        # Standard headers required for NBA.com
        self.headers = {
            'Host': 'stats.nba.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.nba.com/',
            'Origin': 'https://www.nba.com',
            'x-nba-stats-origin': 'stats',
            'x-nba-stats-token': 'true'
        }

        # Initialize monitoring and circuit breaker
        self.monitor = get_monitor()
        self.circuit_breaker = get_circuit_breaker('nba_api')

        # Ensure cache directory exists
        self._ensure_cache_dir()

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        os.makedirs(self.cache_dir, exist_ok=True)
        if not os.path.exists(self.cache_dir):
             print(f"   [NBA-API] Created cache directory: {self.cache_dir}")

    def _rate_limit(self):
        """Enforce 1 request per second rate limit."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - elapsed
            time.sleep(sleep_time)
        self.last_request_time = time.time()

    def _get_cache_key(self, endpoint: str, player_id: int, season: str, **kwargs) -> str:
        """Generate unique cache key for request."""
        # Include any additional parameters that affect results
        # Sanitize values to be filename-safe (replace / with -)
        extra_parts = []
        for k, v in sorted(kwargs.items()):
            if v:
                # Replace slashes with dashes for dates
                safe_v = str(v).replace('/', '-')
                extra_parts.append(f"{k}={safe_v}")

        extra = "_".join(extra_parts)
        if extra:
            return f"{endpoint}_{player_id}_{season}_{extra}.json"
        return f"{endpoint}_{player_id}_{season}.json"

    def _get_cache_path(self, cache_key: str) -> str:
        """Get full path to cache file."""
        return os.path.join(self.cache_dir, cache_key)

    def _is_cache_valid(self, cache_path: str, ttl_hours: int = 24) -> bool:
        """Check if cache file exists and is not expired."""
        if not os.path.exists(cache_path):
            return False

        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)

            cached_time = datetime.fromisoformat(data.get('cached_at', '2000-01-01'))
            if datetime.now() - cached_time > timedelta(hours=ttl_hours):
                return False

            return True
        except (json.JSONDecodeError, KeyError, ValueError):
            return False

    def _read_cache(self, cache_path: str) -> Optional[Dict]:
        """Read data from cache file."""
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            return data.get('data')
        except (json.JSONDecodeError, FileNotFoundError):
            return None

    def _write_cache(self, cache_path: str, data: Any):
        """Write data to cache file with timestamp."""
        cache_data = {
            'cached_at': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2, default=str)

    # =========================================================================
    # PLAYER ID LOOKUP (Static - No API Call)
    # =========================================================================

    def get_player_id(self, player_name: str) -> Optional[int]:
        """
        Look up NBA.com player ID by name.

        Uses nba_api's static player database (no API call needed).
        Handles international characters (e.g., "Luka Doncic" matches "Luka Dončić").

        Args:
            player_name: Full player name (e.g., "LeBron James" or "Luka Doncic")

        Returns:
            Player ID or None if not found
        """
        all_players = nba_players.get_players()

        # Normalize search - both lowercase and ASCII-only
        search_name = unidecode(player_name.lower().strip())

        # Exact match first (with Unicode normalization)
        for player in all_players:
            full_name = unidecode(player['full_name'].lower())
            if search_name == full_name:
                return player['id']

        # Partial match fallback (handles "LeBron" -> "LeBron James")
        for player in all_players:
            full_name = unidecode(player['full_name'].lower())
            if search_name in full_name or full_name in search_name:
                return player['id']

        return None

    def get_player_team_id(self, player_id: int) -> Optional[int]:
        """
        Get the current team ID for a player.

        Makes an API call to get player's current team.

        Args:
            player_id: NBA.com player ID

        Returns:
            Team ID or None if not found
        """
        self._rate_limit()
        try:
            info = commonplayerinfo.CommonPlayerInfo(
                player_id=player_id,
                league_id="00",
                headers=self.headers,
                timeout=30
            )
            data = info.common_player_info.get_dict()
            if data and data.get('data'):
                # TEAM_ID is typically at index 16 in common_player_info
                headers = data.get('headers', [])
                if 'TEAM_ID' in headers:
                    idx = headers.index('TEAM_ID')
                    return data['data'][0][idx]
            return None
        except Exception as e:
            print(f"   [NBA-API] Could not get team_id for player {player_id}: {e}")
            return None

    def get_player_info(self, player_name: str) -> Optional[Dict]:
        """
        Get full player info dictionary by name.

        Args:
            player_name: Full player name

        Returns:
            Dict with id, full_name, first_name, last_name, is_active
        """
        all_players = nba_players.get_players()
        search_name = player_name.lower().strip()

        for player in all_players:
            if search_name == player['full_name'].lower():
                return player

        # Partial match
        for player in all_players:
            if search_name in player['full_name'].lower():
                return player

        return None

    # =========================================================================
    # PUBLIC API METHODS
    # =========================================================================

    @retry_with_backoff(max_attempts=3, backoff=2.0)
    def get_player_shooting_splits(
        self,
        player_id: int,
        season: str = "2025-26",
        per_mode: str = "PerGame",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        last_n_games: int = 0
    ) -> Dict[str, Any]:
        """
        Get player shooting splits by shot type.

        Returns breakdown of:
        - Shot area (paint, mid-range, 3PT)
        - Shot type (catch & shoot, pull-up, drives)
        - Assisted vs unassisted

        Args:
            player_id: NBA.com player ID (e.g., 203507 for Giannis)
            season: Season string (e.g., "2025-26")
            per_mode: "PerGame" or "Totals"
            date_from: Start date filter (MM/DD/YYYY format)
            date_to: End date filter (MM/DD/YYYY format)
            last_n_games: Filter to last N games (0 = all)

        Returns:
            Dict with keys: 'shot_area', 'shot_type', 'assisted_by', 'overall'
        """
        # Build cache key including date range if specified
        cache_key = self._get_cache_key(
            "shooting_splits", player_id, season,
            per_mode=per_mode,
            date_from=date_from or "",
            date_to=date_to or "",
            last_n=last_n_games
        )
        cache_path = self._get_cache_path(cache_key)

        # Check cache first
        if self._is_cache_valid(cache_path):
            print(f"   [NBA-API] Cache hit: {cache_key}")
            return self._read_cache(cache_path)

        # Rate limit and fetch
        self._rate_limit()
        print(f"   [NBA-API] Fetching shooting splits for player {player_id}...")

        try:
            response = playerdashboardbyshootingsplits.PlayerDashboardByShootingSplits(
                player_id=player_id,
                season=season,
                league_id="00",
                per_mode_detailed=per_mode,
                date_from_nullable=date_from or "",
                date_to_nullable=date_to or "",
                last_n_games=last_n_games,
                headers=self.headers,
                timeout=30
            )

            # Extract relevant data frames
            result = {
                'shot_area': response.shot_area_player_dashboard.get_dict(),
                'shot_type': response.shot_type_player_dashboard.get_dict(),
                'assisted_by': response.assisted_by.get_dict(),
                'overall': response.overall_player_dashboard.get_dict()
            }

            # Cache the result
            self._write_cache(cache_path, result)
            self.monitor.log_request('nba_api', 'shooting_splits', {})

            return result

        except Exception as e:
            error_msg = f"Shooting splits failed for player {player_id}: {str(e)}"
            print(f"   [NBA-API] {error_msg}")

            # Return empty on 404 (player not found)
            if "404" in str(e):
                return {}

            # Handle rate limit with extended wait
            if "429" in str(e) or "rate limit" in str(e).lower():
                print(f"   [NBA-API] Rate limited. Waiting 60s...")
                time.sleep(60)

            raise

    @retry_with_backoff(max_attempts=3, backoff=2.0)
    def get_player_shot_difficulty(
        self,
        player_id: int,
        season: str = "2025-26",
        team_id: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        last_n_games: int = 0
    ) -> Dict[str, Any]:
        """
        Get player shot difficulty metrics.

        Returns:
        - Closest defender distance brackets (0-2ft, 2-4ft, 4-6ft, 6ft+)
        - Shot difficulty by dribbles (0, 1, 2, 3-6, 7+)
        - Touch time breakdown

        Args:
            player_id: NBA.com player ID
            season: Season string
            team_id: Team ID (optional, will be looked up if not provided)
            date_from: Start date filter (MM/DD/YYYY format)
            date_to: End date filter (MM/DD/YYYY format)
            last_n_games: Filter to last N games (0 = all)

        Returns:
            Dict with keys: 'closest_defender', 'closest_defender_10ft_plus',
                           'dribbles', 'general'
        """
        cache_key = self._get_cache_key(
            "shot_difficulty", player_id, season,
            date_from=date_from or "",
            date_to=date_to or "",
            last_n=last_n_games
        )
        cache_path = self._get_cache_path(cache_key)

        if self._is_cache_valid(cache_path):
            print(f"   [NBA-API] Cache hit: {cache_key}")
            return self._read_cache(cache_path)

        # Get team_id if not provided
        if team_id is None:
            team_id = self.get_player_team_id(player_id)
            if team_id is None:
                team_id = 0  # Use 0 as fallback (wildcard)

        self._rate_limit()
        print(f"   [NBA-API] Fetching shot difficulty for player {player_id} (team {team_id})...")

        try:
            response = playerdashptshots.PlayerDashPtShots(
                player_id=player_id,
                team_id=team_id,
                season=season,
                league_id="00",
                date_from_nullable=date_from or "",
                date_to_nullable=date_to or "",
                last_n_games=last_n_games,
                headers=self.headers,
                timeout=30
            )

            result = {
                'closest_defender': response.closest_defender_shooting.get_dict(),
                'closest_defender_10ft_plus': response.closest_defender10ft_plus_shooting.get_dict(),
                'dribbles': response.dribble_shooting.get_dict(),
                'general': response.general_shooting.get_dict()
            }

            self._write_cache(cache_path, result)
            self.monitor.log_request('nba_api', 'shot_difficulty', {})

            return result

        except Exception as e:
            error_msg = f"Shot difficulty failed for player {player_id}: {str(e)}"
            print(f"   [NBA-API] {error_msg}")

            if "404" in str(e):
                return {}

            if "429" in str(e) or "rate limit" in str(e).lower():
                print(f"   [NBA-API] Rate limited. Waiting 60s...")
                time.sleep(60)

            raise

    @retry_with_backoff(max_attempts=3, backoff=2.0)
    def get_player_matchups(
        self,
        player_id: int,
        vs_player_id: Optional[int] = None,
        season: str = "2025-26"
    ) -> Dict[str, Any]:
        """
        Get player matchup statistics.

        If vs_player_id provided: Head-to-head comparison
        Otherwise: Defensive matchup summary (who guards this player)

        Args:
            player_id: NBA.com player ID
            vs_player_id: Optional opponent player ID for H2H
            season: Season string

        Returns:
            Dict with matchup data including on/off court splits
        """
        cache_key = self._get_cache_key(
            "matchups", player_id, season,
            vs_player_id=vs_player_id or "all"
        )
        cache_path = self._get_cache_path(cache_key)

        if self._is_cache_valid(cache_path):
            print(f"   [NBA-API] Cache hit: {cache_key}")
            return self._read_cache(cache_path)

        self._rate_limit()

        if vs_player_id:
            print(f"   [NBA-API] Fetching H2H: {player_id} vs {vs_player_id}...")
            result = self._fetch_player_vs_player(player_id, vs_player_id, season)
        else:
            print(f"   [NBA-API] Fetching defensive matchups for player {player_id}...")
            result = self._fetch_defensive_matchups(player_id, season)

        self._write_cache(cache_path, result)
        return result

    def _fetch_player_vs_player(
        self,
        player_id: int,
        vs_player_id: int,
        season: str
    ) -> Dict[str, Any]:
        """Fetch head-to-head player comparison."""
        try:
            response = playervsplayer.PlayerVsPlayer(
                player_id=player_id,
                vs_player_id=vs_player_id,
                season=season,
                league_id="00",
                headers=self.headers,
                timeout=30
            )

            result = {
                'overall': response.overall.get_dict(),
                'on_off_court': response.on_off_court.get_dict(),
                'shot_area_overall': response.shot_area_overall.get_dict(),
                'shot_distance_overall': response.shot_distance_overall.get_dict(),
                'player_info': response.player_info.get_dict(),
                'vs_player_info': response.vs_player_info.get_dict()
            }

            self.monitor.log_request('nba_api', 'player_vs_player', {})
            return result

        except Exception as e:
            error_msg = f"Player vs Player failed: {str(e)}"
            print(f"   [NBA-API] {error_msg}")

            if "404" in str(e):
                return {}

            if "429" in str(e) or "rate limit" in str(e).lower():
                print(f"   [NBA-API] Rate limited. Waiting 60s...")
                time.sleep(60)

            raise

    def _fetch_defensive_matchups(self, player_id: int, season: str, team_id: Optional[int] = None) -> Dict[str, Any]:
        """Fetch defensive matchup summary."""
        # Get team_id if not provided
        if team_id is None:
            team_id = self.get_player_team_id(player_id)
            if team_id is None:
                team_id = 0  # Fallback

        try:
            response = playerdashptshotdefend.PlayerDashPtShotDefend(
                player_id=player_id,
                team_id=team_id,
                season=season,
                league_id="00",
                headers=self.headers,
                timeout=30
            )

            result = {
                'defending_shots': response.defending_shots.get_dict()
            }

            self.monitor.log_request('nba_api', 'defensive_matchups', {})
            return result

        except Exception as e:
            error_msg = f"Defensive matchups failed: {str(e)}"
            print(f"   [NBA-API] {error_msg}")

            if "404" in str(e):
                return {}

            if "429" in str(e) or "rate limit" in str(e).lower():
                print(f"   [NBA-API] Rate limited. Waiting 60s...")
                time.sleep(60)

            raise

    @retry_with_backoff(max_attempts=3, backoff=2.0)
    def get_player_tracking(
        self,
        player_id: int,
        season: str = "2025-26",
        team_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get player tracking/workload data.

        Returns:
        - Rebounding tracking (contested, deferred, etc.)
        - Passing tracking (time of possession, touches)

        Args:
            player_id: NBA.com player ID
            season: Season string
            team_id: Team ID (optional, will be looked up if not provided)

        Returns:
            Dict with tracking data across multiple categories
        """
        cache_key = self._get_cache_key("tracking", player_id, season)
        cache_path = self._get_cache_path(cache_key)

        if self._is_cache_valid(cache_path):
            print(f"   [NBA-API] Cache hit: {cache_key}")
            return self._read_cache(cache_path)

        # Get team_id if not provided
        if team_id is None:
            team_id = self.get_player_team_id(player_id)
            if team_id is None:
                team_id = 0  # Use 0 as fallback (wildcard)

        print(f"   [NBA-API] Fetching tracking data for player {player_id} (team {team_id})...")

        result = {}

        # Rebounding tracking
        self._rate_limit()
        try:
            reb_response = playerdashptreb.PlayerDashPtReb(
                player_id=player_id,
                team_id=team_id,
                season=season,
                league_id="00",
                headers=self.headers,
                timeout=30
            )
            result['rebounding'] = {
                'overall': reb_response.overall_rebounding.get_dict(),
                'shot_type': reb_response.shot_type_rebounding.get_dict(),
                'reb_distance': reb_response.reb_distance_rebounding.get_dict(),
                'contested': reb_response.num_contested_rebounding.get_dict()
            }
            self.monitor.log_request('nba_api', 'tracking_rebound', {})
        except Exception as e:
            result['rebounding'] = {'error': str(e)}
            print(f"   [NBA-API] Rebounding tracking error: {e}")

        # Passing tracking
        self._rate_limit()
        try:
            pass_response = playerdashptpass.PlayerDashPtPass(
                player_id=player_id,
                team_id=team_id,
                season=season,
                league_id="00",
                headers=self.headers,
                timeout=30
            )
            result['passing'] = {
                'passes_made': pass_response.passes_made.get_dict(),
                'passes_received': pass_response.passes_received.get_dict()
            }
            self.monitor.log_request('nba_api', 'tracking_passing', {})
        except Exception as e:
            result['passing'] = {'error': str(e)}
            print(f"   [NBA-API] Passing tracking error: {e}")

        self._write_cache(cache_path, result)
        return result

    # =========================================================================
    # GAME-LEVEL METHODS (Matchups & Box Scores)
    # =========================================================================

    @retry_with_backoff(max_attempts=3, backoff=2.0)
    def get_game_matchups(self, game_id: str) -> Dict[str, Any]:
        """
        Get detailed player matchup data from a specific game.

        Uses boxscorematchupsv3 endpoint which provides:
        - Offensive player (who shot)
        - Defensive player (who was guarding)
        - Matchup minutes, possessions, FGM/FGA/FG%

        The API structure is: defenders -> [matchups they defended against]
        We invert this to: offensive player -> [defenders who guarded them]

        Args:
            game_id: NBA.com game ID in format "0022500XXX" (10 digits)
                    Example: "0022500123" for a 2025-26 regular season game

        Returns:
            Dict with keys:
            - 'matchups': List of matchup dicts with OFF_PLAYER, DEF_PLAYER, stats
            - 'game_id': The queried game ID
            - 'total_matchups': Count of matchup records
        """
        cache_key = f"game_matchups_{game_id}.json"
        cache_path = self._get_cache_path(cache_key)

        if self._is_cache_valid(cache_path):
            print(f"   [NBA-API] Cache hit: {cache_key}")
            return self._read_cache(cache_path)

        self._rate_limit()
        print(f"   [NBA-API] Fetching game matchups for {game_id}...")

        try:
            response = boxscorematchupsv3.BoxScoreMatchupsV3(
                game_id=game_id,
                headers=self.headers,
                timeout=30
            )

            # Get the matchups data
            raw_data = response.get_dict()

            # V3 structure: boxScoreMatchups.{homeTeam,awayTeam}.players[].matchups[]
            box_score = raw_data.get('boxScoreMatchups', {})

            matchups_list = []

            # Process both teams
            for team_key in ['homeTeam', 'awayTeam']:
                team_data = box_score.get(team_key, {})
                team_id = team_data.get('teamId')
                team_name = team_data.get('teamTricode', '')

                # Each player in the "players" list is a DEFENDER
                for defender in team_data.get('players', []):
                    def_id = defender.get('personId')
                    def_first = defender.get('firstName', '')
                    def_last = defender.get('familyName', '')
                    def_name = f"{def_first} {def_last}".strip()

                    # "matchups" contains offensive players this defender guarded
                    for off_player in defender.get('matchups', []):
                        off_id = off_player.get('personId')
                        off_first = off_player.get('firstName', '')
                        off_last = off_player.get('familyName', '')
                        off_name = f"{off_first} {off_last}".strip()

                        stats = off_player.get('statistics', {})

                        matchup_record = {
                            # Offensive player info
                            'off_player_id': off_id,
                            'off_player_name': off_name,
                            # Defensive player info
                            'def_player_id': def_id,
                            'def_player_name': def_name,
                            'def_team_id': team_id,
                            'def_team': team_name,
                            # Stats (when OFF player was guarded by DEF player)
                            'matchup_minutes': stats.get('matchupMinutes', '0:00'),
                            'matchup_minutes_sort': stats.get('matchupMinutesSort', 0),
                            'partial_possessions': stats.get('partialPossessions', 0),
                            'fgm': stats.get('matchupFieldGoalsMade', 0),
                            'fga': stats.get('matchupFieldGoalsAttempted', 0),
                            'fg_pct': stats.get('matchupFieldGoalsPercentage', 0.0),
                            'fg3m': stats.get('matchupThreePointersMade', 0),
                            'fg3a': stats.get('matchupThreePointersAttempted', 0),
                            'fg3_pct': stats.get('matchupThreePointersPercentage', 0.0),
                            'ftm': stats.get('matchupFreeThrowsMade', 0),
                            'fta': stats.get('matchupFreeThrowsAttempted', 0),
                            'assists': stats.get('matchupAssists', 0),
                            'turnovers': stats.get('matchupTurnovers', 0),
                            'blocks': stats.get('matchupBlocks', 0),
                            'player_points': stats.get('playerPoints', 0)
                        }

                        matchups_list.append(matchup_record)

            result = {
                'game_id': game_id,
                'home_team': box_score.get('homeTeam', {}).get('teamTricode', ''),
                'away_team': box_score.get('awayTeam', {}).get('teamTricode', ''),
                'matchups': matchups_list,
                'total_matchups': len(matchups_list)
            }

            self._write_cache(cache_path, result)
            self.monitor.log_request('nba_api', 'game_matchups', {})

            return result

        except Exception as e:
            error_msg = f"Game matchups failed for {game_id}: {str(e)}"
            print(f"   [NBA-API] {error_msg}")

            if "404" in str(e):
                return {'game_id': game_id, 'matchups': [], 'error': 'Game not found'}

            if "429" in str(e) or "rate limit" in str(e).lower():
                print(f"   [NBA-API] Rate limited. Waiting 60s...")
                time.sleep(60)

            raise

    @retry_with_backoff(max_attempts=3, backoff=2.0)
    def get_play_by_play(self, game_id: str, season: str = "2025-26") -> Optional[Dict]:
        """
        Get play-by-play data including substitution events.

        Used for rotation tracking (Phase 8.0 Rotation Intelligence).

        Args:
            game_id: NBA game ID (e.g., "0022300001")
            season: Season string (e.g., "2025-26")

        Returns:
            Dict with PBP data or None if fetch fails

        Example:
            pbp = client.get_play_by_play("0022300001")
            subs = [e for e in pbp['PlayByPlay'] if e['EVENTMSGTYPE'] == 8]
        """
        cache_key = f"playbyplay_{game_id}.json"
        cache_path = self._get_cache_path(cache_key)

        # Check cache (24-hour TTL)
        if self._is_cache_valid(cache_path, ttl_hours=24):
            print(f"   [NBA-API] Using cached PBP for {game_id}")
            return self._read_cache(cache_path)

        # Rate limit and fetch
        self._rate_limit()
        print(f"   [NBA-API] Fetching PBP for game {game_id}...")

        try:
            response = playbyplayv3.PlayByPlayV3(
                game_id=game_id,
                league_id="00"
            )

            result = response.get_dict()

            # Cache the result
            self._write_cache(cache_path, result)
            self.monitor.log_request('nba_api', 'playbyplay', {})

            return result

        except Exception as e:
            print(f"   [NBA-API] Error fetching PBP: {e}")
            return None

    @retry_with_backoff(max_attempts=3, backoff=2.0)
    def get_recent_game_ids(
        self,
        player_id: int,
        season: str = "2025-26",
        last_n_games: int = 10
    ) -> List[str]:
        """
        Get recent NBA.com game IDs for a player.

        This is useful for fetching matchup data, as we need the NBA game ID
        format (0022500XXX) rather than Tank01 format (20260112_BKN@DAL).

        Args:
            player_id: NBA.com player ID
            season: Season string (e.g., "2025-26")
            last_n_games: Number of recent games to return (max 100)

        Returns:
            List of game IDs in NBA.com format (e.g., ["0022500456", "0022500421", ...])
        """
        cache_key = f"player_game_ids_{player_id}_{season}_last{last_n_games}.json"
        cache_path = self._get_cache_path(cache_key)

        # Short TTL for game IDs (4 hours) since we want fresh data
        if self._is_cache_valid(cache_path, ttl_hours=4):
            print(f"   [NBA-API] Cache hit: {cache_key}")
            data = self._read_cache(cache_path)
            return data.get('game_ids', []) if data else []

        self._rate_limit()
        print(f"   [NBA-API] Fetching recent game IDs for player {player_id}...")

        try:
            response = leaguegamefinder.LeagueGameFinder(
                player_id_nullable=player_id,
                season_nullable=season,
                season_type_nullable="Regular Season",
                headers=self.headers,
                timeout=30
            )

            games = response.league_game_finder_results.get_dict()

            game_ids = []
            if games and games.get('data'):
                headers = games.get('headers', [])
                # Find GAME_ID column index
                if 'GAME_ID' in headers:
                    game_id_idx = headers.index('GAME_ID')
                    for row in games['data'][:last_n_games]:
                        game_ids.append(row[game_id_idx])

            result = {
                'player_id': player_id,
                'season': season,
                'game_ids': game_ids,
                'count': len(game_ids)
            }

            self._write_cache(cache_path, result)
            self.monitor.log_request('nba_api', 'player_game_ids', {})

            return game_ids

        except Exception as e:
            error_msg = f"Game ID lookup failed for player {player_id}: {str(e)}"
            print(f"   [NBA-API] {error_msg}")

            if "404" in str(e):
                return []

            if "429" in str(e) or "rate limit" in str(e).lower():
                print(f"   [NBA-API] Rate limited. Waiting 60s...")
                time.sleep(60)

            raise

    def get_player_offensive_matchups(
        self,
        player_id: int,
        season: str = "2025-26",
        last_n_games: int = 5
    ) -> Dict[str, Any]:
        """
        Aggregate offensive matchup data for a player across recent games.

        This fetches game matchups and filters/aggregates for the target player
        as the offensive player (shooter).

        Args:
            player_id: NBA.com player ID
            season: Season string
            last_n_games: Number of recent games to analyze

        Returns:
            Dict with:
            - 'games_analyzed': Number of games with matchup data
            - 'primary_defenders': List of most common defenders with stats
            - 'matchup_summary': Aggregated stats vs each defender
        """
        game_ids = self.get_recent_game_ids(player_id, season, last_n_games)

        if not game_ids:
            return {
                'player_id': player_id,
                'games_analyzed': 0,
                'primary_defenders': [],
                'matchup_summary': {},
                'error': 'No game IDs found'
            }

        # Aggregate matchups across games
        defender_stats = {}  # {defender_id: {name, fgm, fga, minutes, games}}

        games_with_data = 0
        for game_id in game_ids:
            try:
                matchups = self.get_game_matchups(game_id)

                if not matchups.get('matchups'):
                    continue

                games_with_data += 1

                # Filter for our player as offensive player
                for m in matchups['matchups']:
                    # Use standardized field names from get_game_matchups()
                    off_player_id = m.get('off_player_id')
                    if off_player_id != player_id:
                        continue

                    def_player_id = m.get('def_player_id')
                    def_name = m.get('def_player_name', '')

                    # matchup_minutes_sort is in seconds (e.g., 101.3 = 1:41)
                    matchup_min = float(m.get('matchup_minutes_sort', 0)) / 60.0  # Convert to minutes
                    fgm = int(m.get('fgm', 0))
                    fga = int(m.get('fga', 0))

                    if def_player_id not in defender_stats:
                        defender_stats[def_player_id] = {
                            'name': def_name,
                            'player_id': def_player_id,
                            'total_minutes': 0,
                            'total_fgm': 0,
                            'total_fga': 0,
                            'games': 0
                        }

                    defender_stats[def_player_id]['total_minutes'] += matchup_min
                    defender_stats[def_player_id]['total_fgm'] += fgm
                    defender_stats[def_player_id]['total_fga'] += fga
                    defender_stats[def_player_id]['games'] += 1

            except Exception as e:
                print(f"   [NBA-API] Error processing game {game_id}: {e}")
                continue

        # Calculate FG% and sort by minutes
        primary_defenders = []
        for def_id, stats in defender_stats.items():
            fg_pct = stats['total_fgm'] / stats['total_fga'] if stats['total_fga'] > 0 else 0.0
            primary_defenders.append({
                'defender_id': def_id,
                'defender_name': stats['name'],
                'matchup_minutes': round(stats['total_minutes'], 1),
                'fgm': stats['total_fgm'],
                'fga': stats['total_fga'],
                'fg_pct': round(fg_pct, 3),
                'games': stats['games']
            })

        # Sort by matchup minutes (most time guarding = primary defender)
        primary_defenders.sort(key=lambda x: x['matchup_minutes'], reverse=True)

        return {
            'player_id': player_id,
            'games_analyzed': games_with_data,
            'total_games_requested': len(game_ids),
            'primary_defenders': primary_defenders[:10],  # Top 10 defenders
            'all_defenders': len(primary_defenders)
        }

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def clear_cache(self, player_id: Optional[int] = None):
        """
        Clear cache files.

        Args:
            player_id: If provided, only clear cache for this player.
                      Otherwise, clear all cache files.
        """
        if not os.path.exists(self.cache_dir):
            return

        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                if player_id is None or str(player_id) in filename:
                    os.remove(os.path.join(self.cache_dir, filename))
                    count += 1

        print(f"   [NBA-API] Cleared {count} cache files")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        if not os.path.exists(self.cache_dir):
            return {'files': 0, 'size_mb': 0}

        files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        total_size = sum(
            os.path.getsize(os.path.join(self.cache_dir, f))
            for f in files
        )

        return {
            'files': len(files),
            'size_mb': round(total_size / (1024 * 1024), 2)
        }


# =============================================================================
# SINGLETON PATTERN (matches api_monitor.py)
# =============================================================================

_nba_client_instance = None


def get_nba_client() -> NBAAPIClient:
    """Get or create the global NBA API client instance."""
    global _nba_client_instance
    if _nba_client_instance is None:
        _nba_client_instance = NBAAPIClient()
    return _nba_client_instance


# =============================================================================
# QUICK TEST (if run directly)
# =============================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("   NBA API CLIENT - QUICK TEST")
    print("="*60)

    client = get_nba_client()

    # Test player lookup (no API call)
    print("\n[TEST 1] Player ID Lookup:")
    test_players = ["LeBron James", "Giannis Antetokounmpo", "Stephen Curry"]
    for name in test_players:
        pid = client.get_player_id(name)
        print(f"   {name}: {pid}")

    # Test shooting splits (API call)
    print("\n[TEST 2] Shooting Splits (Giannis):")
    splits = client.get_player_shooting_splits(203507, season="2024-25")
    if splits:
        print(f"   Keys: {list(splits.keys())}")
        print(f"   Shot areas: {len(splits.get('shot_area', {}).get('data', []))} rows")
    else:
        print("   No data returned")

    # Cache stats
    print("\n[TEST 3] Cache Stats:")
    stats = client.get_cache_stats()
    print(f"   Files: {stats['files']}, Size: {stats['size_mb']} MB")

    print("\n" + "="*60)
    print("   QUICK TEST COMPLETE")
    print("="*60)
