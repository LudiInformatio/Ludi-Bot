"""
Team Offensive Type Classifier

Automated classification system using real box score data from ludi.db.
Classifications based on 2025-26 season aggregates.

Updated: Feb 2, 2026
"""

import sqlite3
from typing import Dict
from pathlib import Path
from utils.mappings import normalize_bdl_abbr

class TeamOffensiveClassifier:
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        self.TEAM_OFFENSIVE_TYPES = {}
        # Auto-run classification on init
        self.classify_all_teams()

    def _resolve_window_end(self, end_date: str = None) -> str:
        if end_date:
            return end_date
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT MAX(date) FROM games")
            row = c.fetchone()
            if row and row[0]:
                conn.close()
                return row[0]
            c.execute("SELECT MAX(game_date) FROM player_game_logs")
            row = c.fetchone()
            conn.close()
            if row and row[0]:
                return row[0]
        except Exception:
            pass
        return "2026-02-12"

    def classify_all_teams(self, start_date: str = None, end_date: str = None, min_games: int = 30) -> Dict[str, str]:
        """
        Classify all 30 NBA teams by offensive identity.

        Returns:
            Dict mapping team_abbr -> offensive_type
        """
        if start_date is None:
            start_date = "2025-10-01"
        end_date = self._resolve_window_end(end_date)
        team_stats = self._fetch_team_stats(start_date, end_date, min_games)

        for team_abbr, stats in team_stats.items():
            normalized = normalize_bdl_abbr(team_abbr)
            off_type = self._classify_team(normalized, stats)
            self.TEAM_OFFENSIVE_TYPES[normalized] = off_type

        return self.TEAM_OFFENSIVE_TYPES

    def _fetch_team_stats(self, start_date: str, end_date: str, min_games: int) -> Dict:
        """Fetch team stats from ludi.db box scores"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()

            # Aggregate team stats from player game logs
            c.execute('''
                SELECT
                    team_abbreviation as team,
                    COUNT(DISTINCT game_id) as games,
                    SUM(pts) * 1.0 / COUNT(DISTINCT game_id) as ppg,
                    SUM(ast) * 1.0 / COUNT(DISTINCT game_id) as apg,
                    SUM(fg3a) * 1.0 / COUNT(DISTINCT game_id) as t3pa,
                    SUM(fg3m) * 1.0 / COUNT(DISTINCT game_id) as t3pm,
                    SUM(fga) * 1.0 / COUNT(DISTINCT game_id) as fga,
                    SUM(stl) * 1.0 / COUNT(DISTINCT game_id) as spg,
                    CASE WHEN SUM(fgm) > 0 THEN 1.0 * SUM(ast) / SUM(fgm) ELSE 0.6 END as ast_per_fgm
                FROM player_game_logs
                WHERE game_date >= ?
                AND game_date <= ?
                AND team_abbreviation IS NOT NULL
                GROUP BY team_abbreviation
                HAVING COUNT(DISTINCT game_id) >= ?
            ''', (start_date, end_date, min_games))

            team_stats = {}
            for row in c.fetchall():
                team, games, ppg, apg, t3pa, t3pm, fga, spg, ast_per_fgm = row
                normalized = normalize_bdl_abbr(team)

                # Calculate derived metrics
                t3pa_rate = t3pa / fga if fga > 0 else 0.35

                team_stats[normalized] = {
                    'games': games,
                    'ppg': ppg,
                    'ast': apg,
                    '3pa': t3pa,
                    '3pm': t3pm,
                    'fga': fga,
                    'steals': spg,
                    'ast_per_fgm': ast_per_fgm,
                    '3pa_rate': t3pa_rate,
                    # Estimate pace from PPG (rough approximation)
                    'pace': 98 + (ppg - 110) * 0.15,
                }

            conn.close()
            return team_stats

        except Exception as e:
            print(f"⚠️ Team stats fetch failed: {e}")
            return self._get_fallback_stats()

    def _get_fallback_stats(self) -> Dict:
        """Fallback hardcoded stats if DB query fails"""
        return {
            "BOS": {"ppg": 136, "ast": 28, "3pa": 49, "3pm": 18, "3pa_rate": 0.46, "ast_per_fgm": 0.56, "pace": 98},
            "OKC": {"ppg": 140, "ast": 29, "3pa": 43, "3pm": 15, "3pa_rate": 0.42, "ast_per_fgm": 0.58, "pace": 102},
            "CLE": {"ppg": 137, "ast": 32, "3pa": 47, "3pm": 16, "3pa_rate": 0.45, "ast_per_fgm": 0.66, "pace": 100},
        }
    
    def _classify_team(self, team_abbr: str, stats: Dict) -> str:
        """
        Classify single team using 2025-26 data-driven thresholds.

        Types (matching module_e boost function expectations):
        - MOTION: High ball movement (GSW, ATL, CHI, UTA)
        - PACE_PUSH: Fast pace, transition heavy (OKC, PHX)
        - ISO_HEAVY: Low assists, star-driven (MIA, CLE)
        - HALF_COURT: Methodical, low pace (<97)
        - BALANCED: No strong identity

        NOTE: module_e expects MOTION, ISO_HEAVY, PACE_PUSH, HALF_COURT (NOT MOTION_OFFENSE, ISOLATION_HEAVY, etc.)
        """
        # Extract stats with defaults
        ppg = stats.get('ppg', 115)
        ast = stats.get('ast', 28)
        t3pa = stats.get('3pa', 40)
        t3pm = stats.get('3pm', 14)
        t3pa_rate = stats.get('3pa_rate', 0.40)
        ast_per_fgm = stats.get('ast_per_fgm', 0.62)
        stls = stats.get('steals', 7)
        pace = stats.get('pace', 98)

        # MOTION: High ball movement (top quartile assists/FGM)
        # Threshold: ast_per_fgm > 0.675 (top ~20% based on 2025-26 distribution)
        if ast_per_fgm > 0.675:
            return "MOTION"

        # ISO_HEAVY: Low ball movement, star-dependent — guards against false positives.
        # ppg < 117 guard: high-scoring teams (OKC, DEN) with low ast_per_fgm are
        # PACE_PUSH (they score through tempo/transition), NOT isolation-dominant.
        # True ISO-HEAVY teams are Luka-style: low assists AND below high-tempo scoring.
        if ast_per_fgm < 0.600 and ppg < 117:
            return "ISO_HEAVY"

        # PACE_PUSH: Transition-heavy, high-tempo offense (top ~25% scorers not caught above).
        # Replaces broken pace estimation formula (98 + (ppg-110)*0.15 required ppg>130 to fire).
        # Captures: OKC, DEN, MIA, MIN, CLE, NYK — teams running high-scoring, fast offenses.
        if ppg >= 117:
            return "PACE_PUSH"

        # HALF_COURT: Methodical, below-average scoring offense.
        # Teams below 112 PPG tend to play deliberate, set-piece basketball.
        if ppg < 112:
            return "HALF_COURT"

        return "BALANCED"
    
    def get_offensive_type(self, team_abbr: str) -> str:
        """Get cached offensive type for team"""
        return self.TEAM_OFFENSIVE_TYPES.get(team_abbr, "BALANCED")


# Singleton instance
_classifier = TeamOffensiveClassifier()
TEAM_OFFENSIVE_TYPES = _classifier.classify_all_teams()
