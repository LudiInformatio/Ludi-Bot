"""
Team Offensive Type Classifier

Automated classification system using real box score data from ludi.db.
Classifications based on 2025-26 season aggregates.

Updated: Feb 2, 2026
"""

import sqlite3
from typing import Dict
from pathlib import Path

# Team abbreviation normalization
TEAM_ABBR_MAP = {
    'GS': 'GSW', 'PHO': 'PHX', 'NO': 'NOP', 'SA': 'SAS', 'NY': 'NYK',
    'GSW': 'GSW', 'PHX': 'PHX', 'NOP': 'NOP', 'SAS': 'SAS', 'NYK': 'NYK',
    'BOS': 'BOS', 'LAL': 'LAL', 'MIA': 'MIA', 'DEN': 'DEN', 'MIL': 'MIL',
    'CLE': 'CLE', 'OKC': 'OKC', 'MIN': 'MIN', 'DAL': 'DAL', 'MEM': 'MEM',
    'HOU': 'HOU', 'ATL': 'ATL', 'CHI': 'CHI', 'TOR': 'TOR', 'IND': 'IND',
    'WAS': 'WAS', 'SAC': 'SAC', 'UTA': 'UTA', 'ORL': 'ORL', 'CHA': 'CHA',
    'DET': 'DET', 'POR': 'POR', 'BKN': 'BKN', 'LAC': 'LAC', 'PHI': 'PHI',
}

class TeamOffensiveClassifier:
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        self.TEAM_OFFENSIVE_TYPES = {}
        # Auto-run classification on init
        self.classify_all_teams()

    def classify_all_teams(self) -> Dict[str, str]:
        """
        Classify all 30 NBA teams by offensive identity.

        Returns:
            Dict mapping team_abbr -> offensive_type
        """
        team_stats = self._fetch_team_stats()

        for team_abbr, stats in team_stats.items():
            normalized = TEAM_ABBR_MAP.get(team_abbr, team_abbr)
            off_type = self._classify_team(normalized, stats)
            self.TEAM_OFFENSIVE_TYPES[normalized] = off_type

        return self.TEAM_OFFENSIVE_TYPES

    def _fetch_team_stats(self) -> Dict:
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
                WHERE game_date >= '2025-10-01'
                AND team_abbreviation IS NOT NULL
                GROUP BY team_abbreviation
                HAVING COUNT(DISTINCT game_id) >= 30
            ''')

            team_stats = {}
            for row in c.fetchall():
                team, games, ppg, apg, t3pa, t3pm, fga, spg, ast_per_fgm = row
                normalized = TEAM_ABBR_MAP.get(team, team)

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

        Types (based on NBA offensive identities):
        - THREE_POINT_CENTRIC: High volume 3PT teams (BOS, CHA, POR)
        - MOTION_OFFENSE: High ball movement (GSW, ATL, CHI, UTA)
        - PACE_PUSH: Fast pace, transition heavy (OKC, PHX)
        - PAINT_ATTACK: Drive-heavy, low 3PA (HOU, ORL)
        - ISOLATION_HEAVY: Low assists, star-driven (MIA, CLE)
        - BALANCED: No strong identity
        """
        # Extract stats with defaults
        ppg = stats.get('ppg', 115)
        ast = stats.get('ast', 28)
        t3pa = stats.get('3pa', 40)
        t3pm = stats.get('3pm', 14)
        t3pa_rate = stats.get('3pa_rate', 0.40)
        ast_per_fgm = stats.get('ast_per_fgm', 0.62)
        stls = stats.get('steals', 7)

        # THREE_POINT_CENTRIC: Heavy 3PT volume (top quartile)
        # Threshold: 3PA > 46 OR (3PM > 16 AND 3PA_rate > 0.45)
        if t3pa > 46 or (t3pm > 16 and t3pa_rate > 0.45):
            return "THREE_POINT_CENTRIC"

        # MOTION_OFFENSE: High ball movement (top quartile assists/FGM)
        # Threshold: ast_per_fgm > 0.68 AND ast > 32
        if ast_per_fgm > 0.68 and ast > 32:
            return "MOTION_OFFENSE"

        # PACE_PUSH: High scoring, transition-focused
        # Threshold: ppg > 138 AND steals > 8 (leads to fast breaks)
        if ppg > 138 and stls > 8:
            return "PACE_PUSH"

        # PAINT_ATTACK: Low 3PA, drive-heavy
        # Threshold: 3PA < 38 AND ppg > 130
        if t3pa < 38 and ppg > 130:
            return "PAINT_ATTACK"

        # ISOLATION_HEAVY: Low ball movement, star-dependent
        # Threshold: ast_per_fgm < 0.60 AND ppg > 130
        if ast_per_fgm < 0.60 and ppg > 130:
            return "ISOLATION_HEAVY"

        return "BALANCED"
    
    def get_offensive_type(self, team_abbr: str) -> str:
        """Get cached offensive type for team"""
        return self.TEAM_OFFENSIVE_TYPES.get(team_abbr, "BALANCED")


# Singleton instance
_classifier = TeamOffensiveClassifier()
TEAM_OFFENSIVE_TYPES = _classifier.classify_all_teams()
