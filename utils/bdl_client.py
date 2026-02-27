"""
Ball Don't Lie API Client
GOAT tier ($39.99/mo) — 600 req/min
Docs: https://docs.balldontlie.io/

Provides BDLClient class (used by Module A/D) and module-level convenience
functions for quick access via a singleton instance.
"""

import os
import json
import time
import hashlib
import sqlite3
import logging
import requests
import pytz
from datetime import datetime
from typing import Optional, Dict, List, Any
from functools import lru_cache
from utils.mappings import normalize_bdl_abbr

_BDL_EST = pytz.timezone('US/Eastern')

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache infrastructure
# ---------------------------------------------------------------------------
CACHE_DIR = "cache/bdl"
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_cache_path(endpoint: str, params: dict = None) -> str:
    """Generate deterministic cache file path from endpoint + params."""
    key = endpoint
    if params:
        key += "_" + json.dumps(params, sort_keys=True)
    digest = hashlib.md5(key.encode()).hexdigest()[:12]
    safe_endpoint = endpoint.replace("/", "_").replace("?", "_")
    return os.path.join(CACHE_DIR, f"{safe_endpoint}_{digest}.json")


def _read_cache(path: str, ttl_hours: float = 1.0) -> Optional[Any]:
    """Read cached response if fresh enough."""
    try:
        if not os.path.exists(path):
            return None
        age_hours = (time.time() - os.path.getmtime(path)) / 3600
        if age_hours > ttl_hours:
            return None
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


def _write_cache(path: str, data: Any) -> None:
    """Write data to cache file. Silent failure."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# BDLClient class
# ---------------------------------------------------------------------------
class BDLClient:
    """
    Ball Don't Lie API Client

    Tier: GOAT ($39.99/mo)
    Rate Limit: 600 requests/minute
    Docs: https://docs.balldontlie.io/
    """

    # BDL NBA endpoints use /nba/ prefix
    BASE_URL_V1 = "https://api.balldontlie.io/nba/v1"
    BASE_URL_V2 = "https://api.balldontlie.io/nba/v2"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("BALLDONTLIE_KEY")
        if not self.api_key:
            logger.warning("BALLDONTLIE_KEY not found in environment variables.")

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.api_key or "",
            "Content-Type": "application/json",
        })

        # Rate limiting: 600 req/min = 10 req/sec
        self.last_request_time = 0
        self.min_interval = 0.11  # slightly above 0.1s

    # ------------------------------------------------------------------
    # Internal HTTP
    # ------------------------------------------------------------------

    def _normalize_team_data(self, data: Any) -> Any:
        """Recursively normalize team abbreviations in API response data."""
        if isinstance(data, dict):
            if 'abbreviation' in data:
                data['abbreviation'] = normalize_bdl_abbr(data['abbreviation'])
            if 'team_abbreviation' in data:
                data['team_abbreviation'] = normalize_bdl_abbr(data['team_abbreviation'])  # A2: was calling nonexistent self._normalize_team_abbreviation()
            # Recursively process nested dicts
            for key, value in data.items():
                data[key] = self._normalize_team_data(value)
        elif isinstance(data, list):
            return [self._normalize_team_data(item) for item in data]
        return data

    def _wait_for_rate_limit(self):
        """Enforce rate limits between calls."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def _get(self, url: str, params: Dict = None) -> Dict:
        """Single-page GET with error handling and rate limiting."""
        self._wait_for_rate_limit()
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Normalize team abbreviations in response
            return self._normalize_team_data(data)
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

    def _get_all_pages(self, url: str, params: Dict = None) -> List[Dict]:
        """Paginated GET — follows cursor until exhausted."""
        params = dict(params or {})
        all_data: List[Dict] = []
        while True:
            resp = self._get(url, params)
            data = resp.get("data")
            if data is None:
                break
            if isinstance(data, list):
                all_data.extend(data)
            else:
                all_data.append(data)

            # Cursor-based pagination
            meta = resp.get("meta", {})
            next_cursor = meta.get("next_cursor")
            if not next_cursor:
                break
            params["cursor"] = next_cursor
        return all_data

    # ------------------------------------------------------------------
    # Core Data Methods (v1)
    # ------------------------------------------------------------------

    def get_all_players(self, search: str = None, page: int = 1, per_page: int = 100) -> Dict:
        """Fetch players with optional search."""
        params: Dict[str, Any] = {"per_page": per_page}
        if search:
            params["search"] = search
        if page > 1:
            params["cursor"] = page
        return self._get(f"{self.BASE_URL_V1}/players", params)

    @lru_cache(maxsize=1000)
    def get_player_by_id(self, player_id: int) -> Dict:
        """Fetch single player details by ID."""
        data = self._get(f"{self.BASE_URL_V1}/players/{player_id}")
        return data.get("data", {}) if data else {}

    def get_all_teams(self) -> List[Dict]:
        """Fetch all NBA teams."""
        data = self._get(f"{self.BASE_URL_V1}/teams")
        return data.get("data", []) if data else []

    def get_team_by_id(self, team_id: int) -> Dict:
        """Fetch team details by ID."""
        data = self._get(f"{self.BASE_URL_V1}/teams/{team_id}")
        return data.get("data", {}) if data else {}

    def get_games(self, date: str = None, season: int = None,
                  team_ids: List[int] = None, per_page: int = 100) -> Dict:
        """Fetch games based on filters. Returns raw response dict."""
        params: Dict[str, Any] = {"per_page": per_page}
        if date:
            params["dates[]"] = date
        if season:
            params["seasons[]"] = season
        if team_ids:
            for tid in team_ids:
                params.setdefault("team_ids[]", [])
                # requests handles list params
            params["team_ids[]"] = team_ids
        return self._get(f"{self.BASE_URL_V1}/games", params)

    def get_game_by_id(self, game_id: int) -> Dict:
        """Fetch single game details."""
        data = self._get(f"{self.BASE_URL_V1}/games/{game_id}")
        return data.get("data", {}) if data else {}

    def get_stats(self, game_ids: List[int] = None,
                  player_ids: List[int] = None,
                  season: int = None, date: str = None) -> Dict:
        """Fetch box score stats."""
        params: Dict[str, Any] = {"per_page": 100}
        if game_ids:
            params["game_ids[]"] = game_ids
        if player_ids:
            params["player_ids[]"] = player_ids
        if season:
            params["seasons[]"] = season
        if date:
            params["dates[]"] = date
        return self._get(f"{self.BASE_URL_V1}/stats", params)

    def get_season_averages(self, player_ids: List[int] = None,
                            season: int = 2025,
                            category: str = "general",
                            season_type: str = "regular",
                            stat_type: str = None) -> List[Dict]:
        """
        Fetch season averages.

        Categories: general, advanced, scoring, usage, per_36, per_48,
                    opponent, defense
        season_type: regular, playoffs
        stat_type: subtype filter (e.g. "drives", "isolation") — maps to API param "type"
        """
        params: Dict[str, Any] = {
            "season": season,
            "season_type": season_type,   # FIXED: was "type": season_type (caused collision)
            "per_page": 100,
        }
        if stat_type:
            params["type"] = stat_type    # subtype (e.g. "drives", "isolation")
        if player_ids:
            params["player_ids[]"] = player_ids

        cache_path = _get_cache_path(f"season_averages_{category}", params)
        cached = _read_cache(cache_path, ttl_hours=24.0)
        if cached is not None:
            return cached

        data = self._get(f"{self.BASE_URL_V1}/season_averages/{category}", params)
        result = data.get("data", []) if data else []

        if result:
            _write_cache(cache_path, result)
        return result

    def get_team_season_averages(self, team_ids: List[int] = None,
                                  season: int = 2025,
                                  category: str = "general") -> List[Dict]:
        """Fetch team season averages."""
        params: Dict[str, Any] = {"season": season}
        if team_ids:
            params["team_ids[]"] = team_ids

        cache_path = _get_cache_path(f"team_season_averages_{category}", params)
        cached = _read_cache(cache_path, ttl_hours=24.0)
        if cached is not None:
            return cached

        data = self._get(f"{self.BASE_URL_V1}/team_season_averages/{category}", params)
        result = data.get("data", []) if data else []

        if result:
            _write_cache(cache_path, result)
        return result

    def get_standings(self, season: int = 2025) -> List[Dict]:
        """Fetch team standings. Returns 30 teams with wins, losses, conference/division rank."""
        params: Dict[str, Any] = {"season": season}
        cache_path = _get_cache_path(f"standings_{season}", params)
        cached = _read_cache(cache_path, ttl_hours=6.0)
        if cached is not None:
            return cached
        data = self._get(f"{self.BASE_URL_V1}/standings", params)
        result = data.get("data", []) if isinstance(data, dict) else (data or [])
        if result:
            _write_cache(cache_path, result)
        return result

    def get_stats_for_game(self, game_id: int) -> List[Dict]:
        """Helper to get all stats for a specific game."""
        data = self.get_stats(game_ids=[game_id])
        return data.get("data", [])

    # ------------------------------------------------------------------
    # Injuries (v1)
    # ------------------------------------------------------------------

    def get_active_injuries(self) -> List[Dict]:
        """Fetch current injury list."""
        cache_path = _get_cache_path("player_injuries", {})
        cached = _read_cache(cache_path, ttl_hours=0.25)  # 15 min TTL
        if cached is not None:
            return cached

        data = self._get(f"{self.BASE_URL_V1}/player_injuries")
        result = data.get("data", []) if data else []

        if result:
            _write_cache(cache_path, result)
        return result

    # ------------------------------------------------------------------
    # Box Scores (v1)
    # ------------------------------------------------------------------

    def get_box_scores(self, date: str = None, live: bool = False) -> List[Dict]:
        """
        Fetch box scores.
        date: YYYY-MM-DD format
        live: if True, fetch live box scores instead
        """
        if live:
            url = f"{self.BASE_URL_V1}/box_scores/live"
            params = {}
        else:
            url = f"{self.BASE_URL_V1}/box_scores"
            params = {"date": date} if date else {}

        data = self._get(url, params)
        return data.get("data", []) if data else []

    # ------------------------------------------------------------------
    # Props & Odds (v2)
    # ------------------------------------------------------------------

    def get_player_props(self, game_id: int, vendors: List[str] = None) -> List[Dict]:
        """Fetch player props from BDL v2 Odds API.
        
        Args:
            game_id: BDL game ID
            vendors: Optional list of vendor keys to filter (e.g., ['draftkings', 'fanduel'])
        """
        if not self.api_key:
            return []

        cache_path = _get_cache_path(f"player_props_{game_id}", {"vendors": vendors})
        cached = _read_cache(cache_path, ttl_hours=0.5)  # 30 min TTL
        if cached is not None:
            return cached

        self._wait_for_rate_limit()
        try:
            url = f"{self.BASE_URL_V2}/odds/player_props"
            params: Dict[str, Any] = {"game_id": game_id}
            # Vendor quality filter: only high-quality books
            if vendors:
                params["vendors[]"] = vendors
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            result = data.get("data", [])
            if result:
                _write_cache(cache_path, result)
            return result
        except Exception as e:
            logger.error(f"BDL Props Error: {e}")
            return []

    def get_odds(self, date: str = None) -> List[Dict]:
        """Fetch game odds from BDL v2. Defaults to today (EST) if no date provided."""
        # Default to today in EST — prevents accidentally fetching multi-day results
        if not date:
            date = datetime.now(_BDL_EST).strftime('%Y-%m-%d')
        params: Dict[str, Any] = {"dates[]": date}

        cache_path = _get_cache_path("odds", params)
        cached = _read_cache(cache_path, ttl_hours=0.5)
        if cached is not None:
            return cached

        self._wait_for_rate_limit()
        try:
            url = f"{self.BASE_URL_V2}/odds"
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            result = data.get("data", [])
            if result:
                _write_cache(cache_path, result)
            return result
        except Exception as e:
            logger.error(f"BDL Odds Error: {e}")
            return []

    # ------------------------------------------------------------------
    # Advanced Stats (v2)
    # ------------------------------------------------------------------

    def get_advanced_stats(self, player_ids: List[int] = None,
                           game_ids: List[int] = None,
                           season: int = None,
                           dates: List[str] = None) -> List[Dict]:
        """Fetch advanced stats from BDL v2."""
        params: Dict[str, Any] = {"per_page": 100}
        if dates:
            params["dates[]"] = dates
        if player_ids:
            params["player_ids[]"] = player_ids
        if game_ids:
            params["game_ids[]"] = game_ids
        if season:
            params["seasons[]"] = season

        cache_path = _get_cache_path("stats_advanced", params)
        cached = _read_cache(cache_path, ttl_hours=6.0)
        if cached is not None:
            return cached

        result = self._get_all_pages(f"{self.BASE_URL_V2}/stats/advanced", params)

        if result:
            _write_cache(cache_path, result)
        return result

    # ------------------------------------------------------------------
    # Utility / ID Mapping
    # ------------------------------------------------------------------

    def search_player(self, name: str) -> List[Dict]:
        """Search for a player by name string."""
        data = self.get_all_players(search=name)
        return data.get("data", [])

    def map_player_id(self, name: str) -> Optional[int]:
        """Resolve Ludi player name to BDL ID."""
        candidates = self.search_player(name)
        for p in candidates:
            full = f"{p['first_name']} {p['last_name']}"
            if full.lower() == name.lower():
                return p["id"]
        return None

    def check_api_status(self) -> bool:
        """Simple health check of the API connection."""
        try:
            teams = self.get_all_teams()
            return len(teams) > 0
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Canonical ID Mapping (links BDL data to Ludi's player_canonical_ids)
    # ------------------------------------------------------------------

    @staticmethod
    def _map_bdl_player_to_canonical(bdl_player: Dict) -> Optional[str]:
        """
        Match a BDL player dict to our canonical NBA player ID.
        Uses name matching against player_canonical_ids table.
        """
        first = bdl_player.get("first_name", "")
        last = bdl_player.get("last_name", "")
        if not first or not last:
            return None

        full_name = f"{first} {last}"
        try:
            conn = sqlite3.connect("ludi.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT nba_id FROM player_canonical_ids WHERE LOWER(player_name) = ?",
                (full_name.lower(),),
            )
            row = cursor.fetchone()
            conn.close()
            return str(row[0]) if row else None
        except Exception:
            return None

    @staticmethod
    def _map_bdl_game_to_internal(bdl_game: Dict) -> Optional[str]:
        """
        Match a BDL game dict to our internal game_id.
        Uses date + home team abbreviation.
        """
        game_date = bdl_game.get("date", "")[:10]  # YYYY-MM-DD
        home_team = bdl_game.get("home_team", {})
        abbr = home_team.get("abbreviation", "")
        if not game_date or not abbr:
            return None

        try:
            conn = sqlite3.connect("ludi.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT game_id FROM games WHERE game_date = ? AND home_team = ?",
                (game_date, abbr),
            )
            row = cursor.fetchone()
            conn.close()
            return str(row[0]) if row else None
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Module-level singleton + convenience functions
# ---------------------------------------------------------------------------
_client: Optional[BDLClient] = None


def _get_client() -> BDLClient:
    """Lazy singleton for module-level functions."""
    global _client
    if _client is None:
        _client = BDLClient()
    return _client


def is_available() -> bool:
    """Check if BDL API key is configured."""
    return bool(_get_client().api_key)


def get_games(date: str = None, season: int = None,
              team_ids: List[int] = None) -> Dict:
    return _get_client().get_games(date=date, season=season, team_ids=team_ids)


def get_injuries() -> List[Dict]:
    return _get_client().get_active_injuries()


def get_odds(date: str = None) -> List[Dict]:
    return _get_client().get_odds(date=date)


def get_player_props(game_id: int) -> List[Dict]:
    return _get_client().get_player_props(game_id)


def get_box_scores(date: str = None, live: bool = False) -> List[Dict]:
    return _get_client().get_box_scores(date=date, live=live)


def get_advanced_stats(player_ids: List[int] = None,
                       game_ids: List[int] = None,
                       season: int = None,
                       dates: List[str] = None) -> List[Dict]:
    return _get_client().get_advanced_stats(
        player_ids=player_ids, game_ids=game_ids, season=season, dates=dates
    )


def get_season_averages(player_ids: List[int] = None,
                        season: int = 2025,
                        category: str = "general",
                        season_type: str = "regular",
                        stat_type: str = None) -> List[Dict]:
    return _get_client().get_season_averages(
        player_ids=player_ids, season=season,
        category=category, season_type=season_type, stat_type=stat_type
    )


def get_team_season_averages(team_ids: List[int] = None,
                              season: int = 2025,
                              category: str = "general") -> List[Dict]:
    return _get_client().get_team_season_averages(
        team_ids=team_ids, season=season, category=category
    )


def get_player_stats(game_ids: List[int] = None,
                     player_ids: List[int] = None,
                     season: int = None, date: str = None) -> Dict:
    return _get_client().get_stats(
        game_ids=game_ids, player_ids=player_ids,
        season=season, date=date
    )


def get_standings(season: int = 2025) -> List[Dict]:
    """Module-level convenience: fetch team standings."""
    return _get_client().get_standings(season=season)
