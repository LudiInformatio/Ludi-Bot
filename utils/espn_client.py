"""
espn_client.py — ESPN Public API Client

Provides a clean interface to ESPN's public site API for NBA game data.
No auth required. No quota. Free.

Current capabilities:
  - get_scoreboard(): Today's NBA games with DraftKings spread/total/ML
    Used as Tier 3 game lines fallback when Odds-API + BDL both fail.

ESPN API details:
  Base: https://site.api.espn.com/apis/site/v2/sports/basketball/nba
  Scoreboard endpoint: /scoreboard?dates=YYYYMMDD
  Odds are nested under competitions[].odds[] (DraftKings pickcenter).
  Team mapping: ESPN numeric team.id → canonical_teams.espn_id → standard_abbr

Note: ESPN provides game-level lines only (spread, O/U, ML).
No player props are available in any ESPN endpoint.
"""

import requests
import sqlite3
import time
import os
from datetime import datetime


# Fallback team ID map if canonical_teams isn't populated yet.
# {espn_id: standard_abbr} — reverse of the existing _ESPN_TEAM_IDS_FALLBACK in sync scripts.
_ESPN_ID_TO_ABBR_FALLBACK = {
    1: 'ATL', 2: 'BOS', 3: 'NOP', 4: 'CHI', 5: 'CLE',
    6: 'DAL', 7: 'DEN', 8: 'DET', 9: 'GSW', 10: 'HOU',
    11: 'IND', 12: 'LAC', 13: 'LAL', 14: 'MIA', 15: 'MIL',
    16: 'MIN', 17: 'BKN', 18: 'NYK', 19: 'ORL', 20: 'PHI',
    21: 'PHX', 22: 'POR', 23: 'SAC', 24: 'SAS', 25: 'OKC',
    26: 'UTA', 27: 'WAS', 28: 'TOR', 29: 'MEM', 30: 'CHA',
}


class ESPNClient:
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
    TIMEOUT = 10
    _HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
    }

    def _build_team_map(self) -> dict:
        """
        Build {espn_id (int): standard_abbr} from canonical_teams table.
        Falls back to hardcoded map if DB unavailable.
        """
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT espn_id, standard_abbr FROM canonical_teams WHERE espn_id IS NOT NULL"
            ).fetchall()
            conn.close()
            if rows:
                # espn_id stored as integer in DB; ESPN API returns team.id as string
                return {int(row[0]): row[1] for row in rows}
        except Exception as e:
            print(f"   [ESPNClient] DB team map failed: {e}. Using fallback.")
        return _ESPN_ID_TO_ABBR_FALLBACK

    def get_scoreboard(self, date_str: str = None) -> dict:
        """
        Fetch today's NBA scoreboard with DraftKings game lines.

        Args:
            date_str: 'YYYYMMDD'. Defaults to today (local time).

        Returns:
            {game_key: {spread, total, ml_home, ml_away, home_abbr, away_abbr}}
            game_key format: "{away_abbr}_{home_abbr}" (matches module_a game_id convention)

        Spread sign convention: negative = home team favored (matches existing system).
        Silent failure: any exception returns {}.
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')

        try:
            team_map = self._build_team_map()

            url = f"{self.BASE_URL}/scoreboard"
            resp = requests.get(
                url,
                params={'dates': date_str},
                headers=self._HEADERS,
                timeout=self.TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"   [ESPNClient] Scoreboard fetch failed: {e}")
            return {}

        results = {}

        for event in data.get('events', []):
            for competition in event.get('competitions', []):
                # --- Extract team abbreviations via ESPN numeric ID ---
                home_abbr = None
                away_abbr = None

                for competitor in competition.get('competitors', []):
                    team = competitor.get('team', {})
                    # ESPN team.id is a string; convert to int for dict lookup
                    team_id = int(team.get('id', 0))
                    # Prefer DB-mapped abbreviation; fall back to ESPN's own abbr string
                    abbr = team_map.get(team_id) or team.get('abbreviation', '')
                    if competitor.get('homeAway') == 'home':
                        home_abbr = abbr
                    else:
                        away_abbr = abbr

                if not home_abbr or not away_abbr:
                    continue

                # --- Find DraftKings pickcenter odds ---
                # Live API: provider.name = "Draft Kings" (with space)
                dk_odds = None
                for odds_entry in competition.get('odds', []):
                    provider_name = odds_entry.get('provider', {}).get('name', '')
                    # Match both "Draft Kings" (live) and "DraftKings" (documented) defensively
                    if provider_name.replace(' ', '').lower() == 'draftkings':
                        dk_odds = odds_entry
                        break

                if dk_odds is None:
                    continue

                # --- Parse spread ---
                # Live API: odds.spread is a float directly (e.g., -10.5 = home favored by 10.5)
                # Matches our sign convention: negative = home favored
                spread = None
                try:
                    spread = float(dk_odds.get('spread', 0))
                except (TypeError, ValueError):
                    spread = 0.0

                # --- Parse over/under ---
                total = None
                try:
                    over_under = dk_odds.get('overUnder')
                    total = float(over_under) if over_under is not None else None
                except (TypeError, ValueError):
                    total = None

                # --- Parse moneylines ---
                # Live API: odds.moneyline.home.close.odds (string like "-440", "+340")
                ml_home = None
                ml_away = None
                try:
                    ml_home_str = dk_odds.get('moneyline', {}).get('home', {}).get('close', {}).get('odds')
                    ml_home = int(ml_home_str) if ml_home_str is not None else None
                except (TypeError, ValueError):
                    ml_home = None
                try:
                    ml_away_str = dk_odds.get('moneyline', {}).get('away', {}).get('close', {}).get('odds')
                    ml_away = int(ml_away_str) if ml_away_str is not None else None
                except (TypeError, ValueError):
                    ml_away = None

                game_key = f"{away_abbr}_{home_abbr}"
                results[game_key] = {
                    'spread': spread,
                    'total': total,
                    'ml_home': ml_home,
                    'ml_away': ml_away,
                    'home_abbr': home_abbr,
                    'away_abbr': away_abbr,
                }

                # Rate limit guard for multiple calls in a loop
                time.sleep(0.3)

        return results
