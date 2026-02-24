"""
SportsDataIO Discovery Lab API Client
Fantasy API tier (free) — 100 calls/day
Docs: https://discoverylab.sportsdata.io/developers/api-documentation/nba

Confirmed working endpoints (Feb 22, 2026):
  /teams, /Players, /PlayerGameStatsByDate/{date}, /PlayerSeasonStats/{season},
  /Standings/{season}, /PlayerGameProjectionStatsByDate/{date},
  /DfsSlatesByDate/{date}, /CurrentSeason

Base URL: https://api.sportsdata.io/api/nba/fantasy/json
Auth: Ocp-Apim-Subscription-Key header (NOT query param)
Date format: YYYY-MMM-DD  (e.g. 2025-FEB-20)

NOT available on free tier:
  - Referee assignments (Scores API, $99/mo)
  - Starting lineups / depth charts (Scores API, $99/mo)
  - Current season (2025-26) game stats (paid Fantasy, $99/mo)
  - Player props / odds (Odds API, $99/mo)
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime
from typing import Optional, Any

import requests

from utils.mappings import normalize_bdl_abbr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache infrastructure
# ---------------------------------------------------------------------------
CACHE_DIR = "cache/sportsdata"
os.makedirs(CACHE_DIR, exist_ok=True)


def _get_cache_path(method: str, param: str = "") -> str:
    """Generate deterministic cache file path from method + param."""
    key = f"{method}_{param}"
    digest = hashlib.md5(key.encode()).hexdigest()[:12]
    safe = method.replace("/", "_")
    return os.path.join(CACHE_DIR, f"{safe}_{digest}.json")


def _read_cache(path: str, ttl_hours: float) -> Optional[Any]:
    """Return cached data if it exists and is within TTL."""
    try:
        if not os.path.exists(path):
            return None
        age_hours = (time.time() - os.path.getmtime(path)) / 3600
        if age_hours > ttl_hours:
            return None
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def _write_cache(path: str, data: Any) -> None:
    """Write data to cache. Silent failure — never block the caller."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# SportsDataClient class
# ---------------------------------------------------------------------------
class SportsDataClient:
    """
    SportsDataIO Discovery Lab API Client

    Tier: Free Discovery Lab (100 calls/day)
    Auth: Ocp-Apim-Subscription-Key header
    Base URL: https://api.sportsdata.io/api/nba/fantasy/json
    """

    BASE_URL = "https://api.sportsdata.io/api/nba/fantasy/json"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SPORTSDATA_API_KEY")
        if not self.api_key:
            logger.warning("SPORTSDATA_API_KEY not set — SportsDataIO calls will be skipped.")

        self.session = requests.Session()
        self.session.headers.update({
            "Ocp-Apim-Subscription-Key": self.api_key or "",
            "Accept": "application/json",
        })

        # Conservative rate limiting: 100 calls/day → 1s minimum interval
        # We don't retry on 429 because retries burn our daily quota
        self.last_request_time = 0.0
        self.min_interval = 1.0

        # Lazy-loaded api_monitor (optional — won't fail if not importable)
        self._monitor = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_monitor(self):
        """Lazy-load api_monitor to avoid circular imports."""
        if self._monitor is None:
            try:
                from utils.api_monitor import get_monitor
                self._monitor = get_monitor()
            except Exception:
                pass  # api_monitor unavailable — continue without tracking
        return self._monitor

    def _normalize_team_data(self, data: Any) -> Any:
        """Recursively normalize team abbreviations in response data."""
        if isinstance(data, dict):
            for field in ('Team', 'HomeTeam', 'AwayTeam', 'team_abbreviation'):
                if field in data and isinstance(data[field], str):
                    data[field] = normalize_bdl_abbr(data[field])
            for key, val in data.items():
                data[key] = self._normalize_team_data(val)
        elif isinstance(data, list):
            return [self._normalize_team_data(item) for item in data]
        return data

    def _wait_for_rate_limit(self):
        """Enforce minimum interval between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def _get(self, path: str) -> Any:
        """
        Single GET request with error handling.
        Returns [] or {} on any failure — never raises.
        Does NOT retry on 429 (would burn daily quota).
        """
        if not self.api_key:
            return []

        self._wait_for_rate_limit()
        url = f"{self.BASE_URL}/{path}"
        try:
            response = self.session.get(url, timeout=15)

            # Log every request through api_monitor (informational — no header data)
            monitor = self._get_monitor()
            if monitor:
                try:
                    monitor.log_request('sportsdata', path, dict(response.headers))
                except Exception:
                    pass

            if response.status_code == 401:
                logger.error(f"SportsDataIO 401 Unauthorized on {path}. "
                             "Check API key or endpoint availability on your tier.")
                return []
            if response.status_code == 403:
                logger.error(f"SportsDataIO 403 Forbidden on {path}. Endpoint requires paid tier.")
                return []
            if response.status_code == 404:
                logger.warning(f"SportsDataIO 404 on {path}. Endpoint not on Fantasy API path.")
                return []
            if response.status_code == 429:
                logger.warning("SportsDataIO 429 — daily quota (100 calls) exhausted. "
                               "Not retrying to preserve tomorrow's quota.")
                return []

            response.raise_for_status()
            data = response.json()
            return self._normalize_team_data(data)

        except requests.exceptions.Timeout:
            logger.error(f"SportsDataIO timeout on {path}")
            return []
        except requests.exceptions.ConnectionError as e:
            logger.error(f"SportsDataIO connection error on {path}: {e}")
            return []
        except Exception as e:
            logger.error(f"SportsDataIO unexpected error on {path}: {e}")
            return []

    # ------------------------------------------------------------------
    # Public API methods (all confirmed working on free tier)
    # ------------------------------------------------------------------

    def get_teams(self) -> list:
        """
        Fetch all 30 NBA teams.
        Returns: list of dicts with TeamID, Key (abbrev), City, Name, Conference
        TTL: 24h (teams never change mid-season)
        Cost: 1 API call
        """
        cache_path = _get_cache_path("teams")
        cached = _read_cache(cache_path, ttl_hours=24)
        if cached is not None:
            return cached
        data = self._get("teams")
        result = data if isinstance(data, list) else []
        if result:
            _write_cache(cache_path, result)
        return result

    def get_players(self) -> list:
        """
        Fetch all active players with LIVE 2025-26 injury status + current rosters.
        Unique: returns current-season data even on free tier.

        Returns: list of dicts including:
          PlayerID, FirstName, LastName, Team (normalized), Status, InjuryStatus,
          InjuryBodyPart, InjuryNotes, InjuryStartDate, DraftKingsPlayerID,
          FanDuelPlayerID, FantasyAlarmPlayerID, RotowirePlayerID
        TTL: 1h (injuries change frequently)
        Cost: 1 API call
        """
        cache_path = _get_cache_path("Players")
        cached = _read_cache(cache_path, ttl_hours=1)
        if cached is not None:
            return cached
        data = self._get("Players")
        result = data if isinstance(data, list) else []
        if result:
            _write_cache(cache_path, result)
        return result

    def get_player_game_stats(self, date: str) -> list:
        """
        Fetch player box scores for a given date (2024-25 season only on free tier).
        Date format: YYYY-MMM-DD  e.g. '2025-FEB-20' or '2025-JAN-15'

        Returns: list of 46-field player game stat dicts including:
          PTS, REB, AST, STL, BLK, TOV, FGM, FGA, FG3M, FG3A, FTM, FTA,
          PlusMinus, Started, DoubleDoubles, TripleDoubles, FantasyPointsFanDuel,
          FantasyPointsDraftKings, Minutes
        TTL: 6h
        Cost: 1 API call
        """
        cache_path = _get_cache_path("PlayerGameStatsByDate", date)
        cached = _read_cache(cache_path, ttl_hours=6)
        if cached is not None:
            return cached
        data = self._get(f"PlayerGameStatsByDate/{date}")
        result = data if isinstance(data, list) else []
        if result:
            _write_cache(cache_path, result)
        return result

    def get_player_season_stats(self, season: int = 2025) -> list:
        """
        Fetch player season averages.
        Free tier: season=2025 (2024-25) only. season=2026 requires paid Fantasy tier.

        TTL: 12h
        Cost: 1 API call
        """
        cache_path = _get_cache_path("PlayerSeasonStats", str(season))
        cached = _read_cache(cache_path, ttl_hours=12)
        if cached is not None:
            return cached
        data = self._get(f"PlayerSeasonStats/{season}")
        result = data if isinstance(data, list) else []
        if result:
            _write_cache(cache_path, result)
        return result

    def get_standings(self, season: int = 2025) -> list:
        """
        Fetch conference standings.
        Free tier: season=2025 (2024-25) only. season=2026 returns 401.

        TTL: 6h
        Cost: 1 API call
        """
        cache_path = _get_cache_path("Standings", str(season))
        cached = _read_cache(cache_path, ttl_hours=6)
        if cached is not None:
            return cached
        data = self._get(f"Standings/{season}")
        result = data if isinstance(data, list) else []
        if result:
            _write_cache(cache_path, result)
        return result

    def get_projections(self, date: str) -> list:
        """
        Fetch pre-game stat projections for all players on a given date.
        Date format: YYYY-MMM-DD  e.g. '2026-FEB-22'
        Available on free tier for current-season dates (confirmed working).

        Returns: list of projection dicts with same schema as get_player_game_stats()
        TTL: 4h (projections update through the day as news breaks)
        Cost: 1 API call
        """
        cache_path = _get_cache_path("PlayerGameProjectionStatsByDate", date)
        cached = _read_cache(cache_path, ttl_hours=4)
        if cached is not None:
            return cached
        data = self._get(f"PlayerGameProjectionStatsByDate/{date}")
        result = data if isinstance(data, list) else []
        if result:
            _write_cache(cache_path, result)
        return result

    def get_dfs_slates(self, date: str) -> list:
        """
        Fetch DFS slate info (FanDuel, DraftKings, Yahoo slates + salaries).
        Date format: YYYY-MMM-DD

        TTL: 4h
        Cost: 1 API call
        """
        cache_path = _get_cache_path("DfsSlatesByDate", date)
        cached = _read_cache(cache_path, ttl_hours=4)
        if cached is not None:
            return cached
        data = self._get(f"DfsSlatesByDate/{date}")
        result = data if isinstance(data, list) else []
        if result:
            _write_cache(cache_path, result)
        return result

    def get_current_season(self) -> dict:
        """
        Fetch current season metadata (ApiSeason, Season, StartYear, EndYear, etc.)
        Note: returns 2025-26 season info even on free tier.

        TTL: 24h
        Cost: 1 API call
        """
        cache_path = _get_cache_path("CurrentSeason")
        cached = _read_cache(cache_path, ttl_hours=24)
        if cached is not None:
            return cached
        data = self._get("CurrentSeason")
        result = data if isinstance(data, dict) else {}
        if result:
            _write_cache(cache_path, result)
        return result

    def check_api_status(self) -> bool:
        """
        Lightweight health check — hits /teams (1 API call).
        Returns True if API is responding, False otherwise.
        Uses cache so repeated calls don't burn quota.
        """
        teams = self.get_teams()
        ok = isinstance(teams, list) and len(teams) > 0
        if ok:
            logger.info(f"SportsDataIO status: OK ({len(teams)} teams returned)")
        else:
            logger.warning("SportsDataIO status: FAIL (no teams returned)")
        return ok

    @staticmethod
    def format_date(dt: datetime) -> str:
        """
        Convert a datetime object to SportsDataIO date format: YYYY-MMM-DD
        e.g. datetime(2025, 2, 20) → '2025-FEB-20'
        """
        return dt.strftime("%Y-%b-%d").upper()


# ---------------------------------------------------------------------------
# Lazy singleton + module-level convenience functions
# ---------------------------------------------------------------------------

_client_instance: Optional[SportsDataClient] = None


def get_client() -> SportsDataClient:
    """Return the shared SportsDataClient singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = SportsDataClient()
    return _client_instance


def get_teams() -> list:
    """Module-level convenience: fetch all 30 NBA teams."""
    return get_client().get_teams()


def get_players() -> list:
    """Module-level convenience: fetch all players with live injury status."""
    return get_client().get_players()


def get_player_game_stats(date: str) -> list:
    """Module-level convenience: fetch player box scores for a date (YYYY-MMM-DD)."""
    return get_client().get_player_game_stats(date)


def get_projections(date: str) -> list:
    """Module-level convenience: fetch pre-game stat projections (YYYY-MMM-DD)."""
    return get_client().get_projections(date)
