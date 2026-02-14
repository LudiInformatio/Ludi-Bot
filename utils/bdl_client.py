import os
import time
import requests
import logging
from typing import Optional, Dict, List, Union, Any
from functools import lru_cache

# Configure logging
logger = logging.getLogger(__name__)

class BDLClient:
    """
    Ball Don't Lie API Client (v1)
    
    Tier: GOAT ($39.99/mo)
    Rate Limit: 600 requests/minute
    Docs: https://docs.balldontlie.io/
    """
    
    BASE_URL = "https://api.balldontlie.io/v1"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("BALLDONTLIE_KEY")
        if not self.api_key:
            logger.warning("BALLDONTLIE_KEY not found in environment variables.")
            
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        })
        
        # Rate Limiting: 600 req/min = 10 req/sec
        self.last_request_time = 0
        self.min_interval = 0.11  # Slightly above 0.1s to be safe
        
    def _wait_for_rate_limit(self):
        """Enforce rate limits between calls."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """Internal GET wrapper with error handling and rate limiting."""
        self._wait_for_rate_limit()
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("BDL Rate Limit Exceeded (429).")
            elif e.response.status_code == 401:
                logger.error("BDL Unauthorized (401). Check API Key.")
            else:
                logger.error(f"BDL HTTP Error: {e}")
            return {}
        except requests.exceptions.RequestException as e:
            logger.error(f"BDL Connection Error: {e}")
            return {}

    # -------------------------------------------------------------------------
    # Core Data Methods
    # -------------------------------------------------------------------------

    def get_all_players(self, search: str = None, page: int = 1, per_page: int = 100) -> Dict:
        """Fetch players with optional search."""
        params = {"page": page, "per_page": per_page}
        if search:
            params["search"] = search
        return self._get("players", params)

    @lru_cache(maxsize=1000)
    def get_player_by_id(self, player_id: int) -> Dict:
        """Fetch single player details by ID."""
        data = self._get(f"players/{player_id}")
        return data.get("data", {}) if data else {}

    def get_all_teams(self) -> List[Dict]:
        """Fetch all NBA teams."""
        data = self._get("teams")
        return data.get("data", []) if data else []

    def get_team_by_id(self, team_id: int) -> Dict:
        """Fetch team details by ID."""
        data = self._get(f"teams/{team_id}")
        return data.get("data", {}) if data else {}

    def get_games(self, 
                 date: str = None, 
                 season: int = None, 
                 team_ids: List[int] = None, 
                 per_page: int = 100) -> Dict:
        """Fetch games based on filters."""
        params = {"per_page": per_page}
        if date:
            params["dates[]"] = date
        if season:
            params["seasons[]"] = season
        if team_ids:
            params["team_ids[]"] = team_ids
            
        return self._get("games", params)

    def get_game_by_id(self, game_id: int) -> Dict:
        """Fetch single game details."""
        data = self._get(f"games/{game_id}")
        return data.get("data", {}) if data else {}

    def get_stats(self, 
                 game_ids: List[int] = None, 
                 player_ids: List[int] = None, 
                 season: int = None,
                 date: str = None) -> Dict:
        """Fetch box score stats."""
        params = {"per_page": 100}
        if game_ids:
            params["game_ids[]"] = game_ids
        if player_ids:
            params["player_ids[]"] = player_ids
        if season:
            params["seasons[]"] = season
        if date:
            params["dates[]"] = date
            
        return self._get("stats", params)

    def get_season_averages(self, season: int, player_ids: List[int]) -> List[Dict]:
        """Fetch season averages for specific players."""
        params = {"season": season, "player_ids[]": player_ids}
        data = self._get("season_averages", params)
        return data.get("data", []) if data else []

    def get_stats_for_game(self, game_id: int) -> List[Dict]:
        """Helper to get all stats for a specific game."""
        data = self.get_stats(game_ids=[game_id])
        return data.get("data", [])

    def get_player_props(self, game_id: int) -> List[Dict]:
        """
        Fetch player props from BDL v2 Odds API.
        
        Note: Requires paid subscription.
        """
        # Temporarily switch base URL for v2 endpoint
        original_base = self.BASE_URL
        try:
            # Construct v2 URL (assuming standard pattern)
            v2_url = "https://api.balldontlie.io/v2/odds/player_props"
            
            # We use session directly to avoid _get's v1 prefixing, 
            # but we still want rate limiting
            self._wait_for_rate_limit()
            
            response = self.session.get(v2_url, params={"game_id": game_id}, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"BDL Props Error: {e}")
            return []

    # -------------------------------------------------------------------------
    # Utility / Helper Methods
    # -------------------------------------------------------------------------

    def search_player(self, name: str) -> List[Dict]:
        """Search for a player by name string."""
        data = self.get_all_players(search=name)
        return data.get("data", [])

    def map_player_id(self, name: str) -> Optional[int]:
        """Resolve Ludi player name to BDL ID."""
        # Clean name logic could be added here (suffix removal etc)
        candidates = self.search_player(name)
        for p in candidates:
            # Construct full name
            full = f"{p['first_name']} {p['last_name']}"
            if full.lower() == name.lower():
                return p['id']
        return None

    def get_active_injuries(self) -> List[Dict]:
        """Fetch current injuries (if endpoint available in tier)."""
        # Note: BDL specific endpoint for injuries might differ or require specific tier
        # Checking docs, 'injuries' is a valid endpoint in paid tiers
        data = self._get("injuries")
        return data.get("data", []) if data else []

    def check_api_status(self) -> bool:
        """Simple health check of the API connection."""
        try:
            teams = self.get_all_teams()
            return len(teams) > 0
        except Exception:
            return False
