"""
Tank01 API Client — Centralized client for all Tank01 (RapidAPI) requests.
Follows utils/bdl_client.py pattern: requests.Session, monitoring, lazy singleton.

Tier: PAID (1K requests/day)
Host: tank01-fantasy-stats.p.rapidapi.com
Docs: https://rapidapi.com/tank01/api/tank01-fantasy-stats

Usage:
    from utils.tank01_client import get_client
    client = get_client()
    injuries = client.get_injury_list()
"""

import requests
from datetime import date
from typing import List, Dict, Optional

import config
from utils.api_monitor import APIMonitor


class Tank01Client:
    """
    Centralized Tank01 (RapidAPI) client.

    All Tank01 calls in the codebase should route through here instead of
    constructing ad-hoc requests with inline headers. This gives us:
      - Single place to rotate the API key
      - Automatic request monitoring and quota alerts
      - Consistent error handling (returns {} or [] on failure — never raises)
      - requests.Session for connection reuse (faster in pipeline loops)
    """

    HOST = "tank01-fantasy-stats.p.rapidapi.com"
    BASE_URL = f"https://{HOST}"

    def __init__(self):
        self.api_key = config.TANK01_KEY
        if not self.api_key:
            print("[Tank01Client] WARNING: TANK01_KEY not set — all requests will fail auth.")

        # Session reuse: one TCP connection per pipeline run instead of per-call
        self.session = requests.Session()
        self.session.headers.update({
            "X-RapidAPI-Key": self.api_key or "",
            "X-RapidAPI-Host": self.HOST,
        })

        self.monitor = APIMonitor()

    # ------------------------------------------------------------------
    # Internal HTTP helper
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """
        Single GET with error handling and monitoring.

        Returns the parsed JSON dict on success, or {} on any failure.
        Callers extract 'body' from the result (Tank01 wraps data in {'body': ...}).
        """
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        try:
            r = self.session.get(url, params=params, timeout=15)
            # Log BEFORE raise_for_status so we capture the headers on 4xx/5xx too
            self.monitor.log_request("tank01", endpoint, r.headers)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            self.monitor.log_failed_request("tank01", endpoint, str(e))
            return {}

    # ------------------------------------------------------------------
    # EXISTING ENDPOINTS (wrapping current inline calls across codebase)
    # ------------------------------------------------------------------

    def get_injury_list(self) -> List[Dict]:
        """
        GET /getNBAInjuryList — full league injury list.

        Used by: module_d.py (LudiYak), scripts/sync_injuries.py
        Returns list of dicts with keys: playerID, playerName, injDate,
        description, designation, teamAbv, etc.
        """
        data = self._get("getNBAInjuryList")
        return data.get("body", [])

    def get_games_for_date(self, game_date: str) -> List[Dict]:
        """
        GET /getNBAGamesForDate — all game IDs for a date.

        Args:
            game_date: YYYYMMDD string (e.g. '20260220')

        Used by: module_a.py, scripts/populate_todays_games.py
        Returns list of game dicts with gameID, home/away teams, status.
        """
        data = self._get("getNBAGamesForDate", {"gameDate": game_date})
        return data.get("body", [])

    def get_box_score(self, game_id: str, fantasy_points: bool = True) -> Dict:
        """
        GET /getNBABoxScore — full player stats for one game.

        Args:
            game_id:       Tank01 game ID string (e.g. '20260220_BOS@MIA')
            fantasy_points: True = include fantasy point calculations (default).
                            NOTE: old codebase defaulted to False — corrected here.

        Used by: module_h_historian.py (LudiHistorian)
        Returns dict with 'playerStats' array and game metadata.
        """
        params = {
            "gameID": game_id,
            "fantasyPoints": "true" if fantasy_points else "false",
        }
        data = self._get("getNBABoxScore", params)
        return data.get("body", {})

    def get_teams(self) -> List[Dict]:
        """
        GET /getNBATeams — all 30 NBA teams with metadata.

        Returns list of team dicts: teamAbv, teamName, teamID, conference, etc.
        Low-churn data — safe to cache at call site for 24h.
        """
        data = self._get("getNBATeams")
        return data.get("body", [])

    def get_team_roster(self, team_abv: str) -> Dict:
        """
        GET /getNBATeamRoster — current players for one team.

        Args:
            team_abv: Standard NBA abbreviation (e.g. 'BOS', 'LAL')

        Used by: RosterValidator, scripts that detect newly-traded players.
        Returns dict with 'roster' list of player dicts.
        """
        data = self._get("getNBATeamRoster", {"teamAbv": team_abv})
        return data.get("body", {})

    def get_depth_charts(self) -> Dict:
        """
        GET /getNBADepthCharts — depth charts for all 30 teams.

        Useful for: starter/bench classification, minutes projection priors.
        Returns dict keyed by team abbreviation, each with ordered player lists.
        """
        data = self._get("getNBADepthCharts")
        return data.get("body", {})

    # ------------------------------------------------------------------
    # NEW ENDPOINTS (Phase 0 expansion)
    # ------------------------------------------------------------------

    def get_betting_odds(
        self,
        game_date: str = None,
        game_id: str = None,
        player_props: bool = False,
        item_format: str = "list",
    ) -> List[Dict]:
        """
        GET /getNBABettingOdds — game lines + (optionally) player prop lines.

        Args:
            game_date:    YYYYMMDD string — filter to one date
            game_id:      Tank01 game ID string — filter to one game
            player_props: True = include 'playerProps' array in each game dict
            item_format:  'list' (default) or 'map'

        IMPORTANT: propBets values are LINE VALUES ONLY — there are no
        over/under odds attached. Use The-Odds-API or BDL for actual odds.
        Tank01 odds are useful as a secondary line-shopping reference.

        Returns list of game odds dicts.
        """
        params: dict = {"itemFormat": item_format}
        if game_date:
            params["gameDate"] = game_date
        if game_id:
            params["gameID"] = game_id
        if player_props:
            params["playerProps"] = "true"
        data = self._get("getNBABettingOdds", params)
        return data.get("body", [])

    def get_projections(
        self,
        num_days: int = 7,
        pts: float = 1,
        reb: float = 1.25,
        ast: float = 1.5,
        stl: float = 3,
        blk: float = 3,
        tov: float = -1,
        mins: float = 0,
    ) -> Dict:
        """
        GET /getNBAProjections — fantasy point projections for all players.

        Default weights match FanDuel / our internal FANTASY_PTS formula.

        POLICY: Use as READ-ONLY sanity benchmark ONLY.
        Never feed Tank01 projections into our simulation model — our
        S.A.V.A.G.E. engine (Module C) is the authoritative projection source.

        Args:
            num_days: How many upcoming days to project (max 7)
            pts/reb/ast/stl/blk/tov/mins: Fantasy scoring weights

        Returns dict keyed by playerID with projection dicts.
        """
        params = {
            "numOfDays": num_days,
            "pts": pts,
            "reb": reb,
            "ast": ast,
            "stl": stl,
            "blk": blk,
            "TOV": tov,   # Tank01 uses uppercase TOV
            "mins": mins,
        }
        data = self._get("getNBAProjections", params)
        # Actual response: body = {"playerProjections": {playerID: {...}}}
        # Values are CUMULATIVE over numOfDays (not per-game averages)
        return data.get("body", {}).get("playerProjections", {})

    def get_current_info(self, date: str) -> Dict:
        """
        GET /getNBACurrentInfo — standings + streak + roster for ALL 30 teams.

        ONE call returns every team's context simultaneously — this is the
        most credit-efficient way to get standings/streaks (1 call vs 30).

        Args:
            date: YYYYMMDD string (e.g. '20260220')

        Returns dict keyed by team abbreviation with keys like:
          currentStreak, wins, losses, last10, homeRecord, roadRecord, etc.
        """
        data = self._get("getNBACurrentInfo", {"date": date})
        return data.get("body", {})

    def get_top_news(self, team_abv: str = None, recent: bool = True) -> List[Dict]:
        """
        GET /getNBANews — player/team news headlines.

        NOTE: Correct endpoint is getNBANews (not getNBATopNews which doesn't exist).
        Requires either recentNews=true (50 player-level items, has playerIDs)
        or topNews=true (16 general NBA headlines, no playerIDs).

        Args:
            team_abv: Optional — filter to one team's news
            recent:   True (default) = recentNews=true (player-level injury/news items)
                      False = topNews=true (general NBA headlines only)

        USAGE RULE: Fetch ONCE per day and cache to player_news_cache.
        Do NOT call this per-player — it returns all news and burns credits fast.

        Returns list of news dicts with playerIDs, title, link, image.
        """
        params: dict = {"recentNews": "true"} if recent else {"topNews": "true"}
        if team_abv:
            params["teamAbv"] = team_abv
        data = self._get("getNBANews", params)
        return data.get("body", [])

    def get_games_for_player(
        self,
        player_id: str,
        season: str = "2024-25",
    ) -> List[Dict]:
        """
        GET /getNBAGamesForPlayer — single player's game log for a season.

        Args:
            player_id: Tank01 player ID string
            season:    Season string in 'YYYY-YY' format (e.g. '2024-25')

        USE CASE: Targeted backfills for 1-5 players (e.g. after trade detection).
        Do NOT use for nightly bulk sync — module_h_historian.py handles that
        more efficiently via get_box_score() across all games.

        Returns list of game log dicts with standard box score stats.
        """
        data = self._get(
            "getNBAGamesForPlayer",
            {"playerID": player_id, "season": season},
        )
        return data.get("body", [])


# ---------------------------------------------------------------------------
# Lazy singleton — same pattern as bdl_client.py _get_client()
# One shared instance per process; avoids re-creating Session on every import.
# ---------------------------------------------------------------------------
_client_instance: Optional[Tank01Client] = None


def get_client() -> Tank01Client:
    """
    Return the shared Tank01Client singleton.

    Usage:
        from utils.tank01_client import get_client
        client = get_client()
        injuries = client.get_injury_list()
    """
    global _client_instance
    if _client_instance is None:
        _client_instance = Tank01Client()
    return _client_instance


# ---------------------------------------------------------------------------
# Module-level convenience functions (mirrors bdl_client.py top-level API)
# ---------------------------------------------------------------------------

def get_injury_list() -> List[Dict]:
    return get_client().get_injury_list()


def get_games_for_date(game_date: str) -> List[Dict]:
    return get_client().get_games_for_date(game_date)


def get_box_score(game_id: str, fantasy_points: bool = True) -> Dict:
    return get_client().get_box_score(game_id, fantasy_points=fantasy_points)


def get_teams() -> List[Dict]:
    return get_client().get_teams()


def get_team_roster(team_abv: str) -> Dict:
    return get_client().get_team_roster(team_abv)


def get_depth_charts() -> Dict:
    return get_client().get_depth_charts()


def get_current_info(game_date: str = None) -> Dict:
    if game_date is None:
        game_date = date.today().strftime("%Y%m%d")
    return get_client().get_current_info(game_date)


def get_top_news(team_abv: str = None, recent: bool = True) -> List[Dict]:
    return get_client().get_top_news(team_abv=team_abv, recent=recent)


# ---------------------------------------------------------------------------
# Smoke test — run directly: python utils/tank01_client.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    client = Tank01Client()

    print("=== Tank01Client Smoke Test ===\n")

    # Test 1: Injury list (safe, read-only, no params needed)
    print("[1/2] get_injury_list()...")
    injuries = client.get_injury_list()
    print(f"      Injury list: {len(injuries)} players")

    # Test 2: Current info (standings + streaks, 1 call = 30 teams)
    print("[2/2] get_current_info()...")
    today = date.today().strftime("%Y%m%d")
    info = client.get_current_info(today)
    top_keys = list(info.keys())[:5]
    print(f"      Current info top-level keys: {top_keys}")
    print(f"      Total teams returned: {len(info)}")

    print("\nSmoke test complete.")
