#!/usr/bin/env python3
"""
Team Defensive Classifier
====================

Dynamic classification of NBA team defensive schemes based on tracking data.
Replaces hardcoded "PAINT_PACK" lists with data-driven approach.

New Defensive Archetypes (Week 3):
- DROP_COVERAGE: High opp_rim_fg_pct (Good), Low blitz_freq
- SWITCH_HEAVY: High switch_freq OR High iso_freq_allowed
- ZONE_FLUID: High zone_freq (Synergy) OR Low opp_assist_rate
- RIM_FORTRESS: opp_rim_fg_pct < 60% (Elite)
- PERIMETER_FUNNEL: Low opp_3p_rate allowed, High opp_drive_rate
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Optional

class TeamDefensiveClassifier:
    """Dynamic team defensive scheme classification based on tracking data."""
    
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        self.classification_cache = {}
        self.last_cache_update = None
        
        # Classification thresholds (research-backed)
        self.THRESHOLDS = {
            'high_rim_fg_pct_allowed': 0.45,      # >45% = permissive inside
            'low_blitz_freq': 15,               # <15 blitzes/game = not blitz-heavy
            'high_switch_freq': 25,               # >25 switches/game = switch-heavy
            'high_iso_freq_allowed': 20,           # >20 ISO possessions = allows ISO
            'high_zone_freq': 30,                 # >30 zone possessions = zone-heavy
            'low_opp_assist_rate': 0.18,           # <18% = poor ball movement
            'low_opp_3p_rate_allowed': 0.32,     # <32% 3P allowed = perimeter funnel
            'high_opp_drive_rate': 28,               # >28 drives/game = funnel defense
            'min_games_sample': 10                  # Need 10+ games for reliable stats
        }

    def _resolve_window_end(self, end_date: str = None) -> str:
        if end_date:
            return end_date
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM games")
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                return row[0]
        except Exception:
            pass
        return "2026-02-12"

    @staticmethod
    def _percentile(values, pct):
        """Return the pct percentile from a list of numeric values."""
        if not values:
            return 0
        values_sorted = sorted(values)
        if len(values_sorted) == 1:
            return values_sorted[0]
        idx = int(round((len(values_sorted) - 1) * pct))
        return values_sorted[max(0, min(idx, len(values_sorted) - 1))]

    def _compute_relative_thresholds(self, stats_by_team):
        """Compute relative thresholds across teams for a given window."""
        def_dist_vals = [s.get('opp_avg_defender_dist', 0) for s in stats_by_team.values() if s]
        drive_vol_vals = [s.get('opp_drives_fga', 0) for s in stats_by_team.values() if s]
        drive_pct_vals = [s.get('opp_drive_fg_pct', 0) for s in stats_by_team.values() if s]
        cs_3pa_vals = [s.get('opp_catch_shoot_3pa', 0) for s in stats_by_team.values() if s]
        speed_vals = [s.get('opp_speed', 0) for s in stats_by_team.values() if s]

        return {
            'def_dist_low': self._percentile(def_dist_vals, 0.25),
            'def_dist_high': self._percentile(def_dist_vals, 0.75),
            'drive_vol_low': self._percentile(drive_vol_vals, 0.25),
            # Q60 (down from Q75): PERIMETER_FUNNEL needs high-ish drives, not extreme —
            # the Q75+Q25 combo never co-occurs because high-drive teams also allow high C&S 3PA.
            'drive_vol_high': self._percentile(drive_vol_vals, 0.60),
            'drive_pct_low': self._percentile(drive_pct_vals, 0.25),
            'drive_pct_med': self._percentile(drive_pct_vals, 0.50),
            # Q40 (down from Q25): captures teams that suppress C&S below-average, not extreme.
            'cs_3pa_low': self._percentile(cs_3pa_vals, 0.40),
            'cs_3pa_high': self._percentile(cs_3pa_vals, 0.75),
            'speed_high': self._percentile(speed_vals, 0.75),
        }

    def _apply_relative_rules(self, stats: Dict, thresholds: Dict) -> str:
        """Apply relative thresholds (percentile-based) to classify defense."""
        cs_3pa = stats.get('opp_catch_shoot_3pa', 0)
        drive_vol = stats.get('opp_drives_fga', 0)
        drive_pct = stats.get('opp_drive_fg_pct', 0)
        def_dist = stats.get('opp_avg_defender_dist', 0)
        opp_speed = stats.get('opp_speed', 0)

        # RIM_FORTRESS: bottom quartile drive FG% allowed
        if drive_pct <= thresholds['drive_pct_low']:
            return "RIM_FORTRESS"

        # PERIMETER_FUNNEL: high drive volume but low catch-and-shoot 3PA allowed
        if drive_vol >= thresholds['drive_vol_high'] and cs_3pa <= thresholds['cs_3pa_low']:
            return "PERIMETER_FUNNEL"

        # ZONE_FLUID: high opponent speed + high C&S volume
        if opp_speed >= thresholds['speed_high'] and cs_3pa >= thresholds['cs_3pa_high']:
            return "ZONE_FLUID"

        # DROP_COVERAGE: low defender distance + decent drive defense
        if def_dist <= thresholds['def_dist_low'] and drive_pct <= thresholds['drive_pct_med']:
            return "DROP_COVERAGE"

        # SWITCH_HEAVY: high defender distance or high drive volume
        if def_dist >= thresholds['def_dist_high'] or drive_vol >= thresholds['drive_vol_high']:
            return "SWITCH_HEAVY"

        return "NEUTRAL"
        
    def _load_tracking_stats(self, team_name: str, games_back: int = 40) -> Dict:
        """Load team defensive stats from player_game_tracking table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate defensive stats from opponent tracking data
        cursor.execute("""
            SELECT 
                pg.game_date,
                SUM(pg.catch_shoot_3pa) as opp_catch_shoot_3pa,
                SUM(pg.catch_shoot_3pm) as opp_catch_shoot_3pm,
                SUM(pg.drives_fga) as opp_drives_fga,
                SUM(pg.drives_fgm) as opp_drives_fgm,
                AVG(pg.avg_speed_off) as opp_speed,
                AVG(pg.avg_defender_dist) as opp_avg_defender_dist
            FROM player_game_tracking pg
            JOIN canonical_games g ON pg.game_date = g.date
            WHERE (g.home_team = ? OR g.away_team = ?) -- Game involves target team
            AND pg.team_abbr != ? -- tracking stats for NON-target team (the opponent)
            AND pg.game_date >= date('now', '-' || ? || ' days')
            GROUP BY pg.game_date
            ORDER BY pg.game_date DESC
            LIMIT ?
        """, (team_name, team_name, team_name, games_back, games_back))
        
        stats = cursor.fetchall()
        conn.close()
        
        if not stats or len(stats) < self.THRESHOLDS['min_games_sample']:
            return {}
            
        # Calculate averages from opponent tracking
        total_games = len(stats)
        
        # Helper to safely average
        def safe_avg(idx):
             vals = [s[idx] for s in stats if s[idx] is not None]
             return sum(vals) / len(vals) if vals else 0

        avg_opp_cs_3pa = safe_avg(1)
        avg_opp_cs_3pm = safe_avg(2)
        avg_opp_drives_fga = safe_avg(3) 
        avg_opp_drives_fgm = safe_avg(4)
        avg_opp_speed = safe_avg(5)
        avg_opp_def_dist = safe_avg(6)
        
        # Derived metrics
        opp_drive_fg_pct = (avg_opp_drives_fgm / avg_opp_drives_fga) if avg_opp_drives_fga > 0 else 0
        opp_cs_3p_pct = (avg_opp_cs_3pm / avg_opp_cs_3pa) if avg_opp_cs_3pa > 0 else 0

        return {
            'opp_catch_shoot_3pa': avg_opp_cs_3pa,
            'opp_catch_shoot_3p_pct': opp_cs_3p_pct,
            'opp_drives_fga': avg_opp_drives_fga,
            'opp_drive_fg_pct': opp_drive_fg_pct,
            'opp_speed': avg_opp_speed,
            'opp_avg_defender_dist': avg_opp_def_dist,
            'sample_size': total_games
        }

    def _load_tracking_stats_range(self, team_name: str, start_date: str, end_date: str) -> Dict:
        """Load team defensive stats for a specific date range.

        Uses a self-referential subquery to find game_dates rather than joining
        to the games table. This avoids INSUFFICIENT results when games is stale
        (e.g. after the All-Star break or when recent entries haven't synced yet).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                pg.game_date,
                SUM(pg.catch_shoot_3pa) as opp_catch_shoot_3pa,
                SUM(pg.catch_shoot_3pm) as opp_catch_shoot_3pm,
                SUM(pg.drives_fga) as opp_drives_fga,
                SUM(pg.drives_fgm) as opp_drives_fgm,
                AVG(pg.avg_speed_off) as opp_speed,
                AVG(pg.avg_defender_dist) as opp_avg_defender_dist
            FROM player_game_tracking pg
            WHERE pg.game_date IN (
                SELECT DISTINCT game_date
                FROM player_game_tracking
                WHERE team_abbr = ?
                  AND game_date >= ?
                  AND game_date <= ?
            )
            AND pg.team_abbr != ?
            AND pg.game_date >= ?
            AND pg.game_date <= ?
            GROUP BY pg.game_date
            ORDER BY pg.game_date DESC
        """, (team_name, start_date, end_date, team_name, start_date, end_date))

        stats = cursor.fetchall()
        conn.close()

        if not stats:
            return {}

        total_games = len(stats)

        def safe_avg(idx):
            vals = [s[idx] for s in stats if s[idx] is not None]
            return sum(vals) / len(vals) if vals else 0

        avg_opp_cs_3pa = safe_avg(1)
        avg_opp_cs_3pm = safe_avg(2)
        avg_opp_drives_fga = safe_avg(3)
        avg_opp_drives_fgm = safe_avg(4)
        avg_opp_speed = safe_avg(5)
        avg_opp_def_dist = safe_avg(6)

        opp_drive_fg_pct = (avg_opp_drives_fgm / avg_opp_drives_fga) if avg_opp_drives_fga > 0 else 0
        opp_cs_3p_pct = (avg_opp_cs_3pm / avg_opp_cs_3pa) if avg_opp_cs_3pa > 0 else 0

        return {
            'opp_catch_shoot_3pa': avg_opp_cs_3pa,
            'opp_catch_shoot_3p_pct': opp_cs_3p_pct,
            'opp_drives_fga': avg_opp_drives_fga,
            'opp_drive_fg_pct': opp_drive_fg_pct,
            'opp_speed': avg_opp_speed,
            'opp_avg_defender_dist': avg_opp_def_dist,
            'sample_size': total_games
        }
    
    def classify_defense(self, team_name: str, force_refresh: bool = False) -> str:
        """
        Classify team defensive scheme based on tracking data.
        
        Args:
            team_name: NBA team abbreviation (e.g., 'LAL', 'BOS')
            force_refresh: Force reclassification bypassing cache
            
        Returns:
            str: Defensive archetype classification
        """
        # Check cache first
        cache_key = f"{team_name}_{datetime.now().strftime('%Y-%m-%d')}"
        
        if not force_refresh and cache_key in self.classification_cache:
            cached = self.classification_cache[cache_key]
            if datetime.now() - cached['timestamp'] < timedelta(days=1):  # 1-day cache
                return cached['classification']
        
        # Load tracking stats
        stats = self._load_tracking_stats(team_name)
        
        if not stats:
            return "NEUTRAL"  # Default if insufficient data
        
        # Apply classification logic
        classification = self._apply_classification_rules(stats)
        
        # Cache result
        self.classification_cache[cache_key] = {
            'classification': classification,
            'timestamp': datetime.now(),
            'stats': stats
        }
        
        return classification
    
    def _apply_classification_rules(self, stats: Dict) -> str:
        """Apply research-backed classification rules using available data proxies."""
        
        # Extract stats with defaults
        cs_3pa = stats.get('opp_catch_shoot_3pa', 0)
        drive_vol = stats.get('opp_drives_fga', 0)
        drive_pct = stats.get('opp_drive_fg_pct', 0)
        def_dist = stats.get('opp_avg_defender_dist', 0)
        opp_speed = stats.get('opp_speed', 0)
        
        # Rule 1: DROP_COVERAGE
        # Proxy: Low defender distance (sagging) + solid drive defense
        # NOTE: Thresholds calibrated to team-aggregated tracking totals (not per-player rates).
        if (def_dist < 4.0 and drive_pct < 0.487):
            return "DROP_COVERAGE"
        
        # Rule 2: SWITCH_HEAVY
        # Proxy: Higher defender distance and/or high drive volume allowed
        if (def_dist > 4.23 or drive_vol > 370):
            return "SWITCH_HEAVY"
        
        # Rule 3: ZONE_FLUID
        # Proxy: High opponent speed + high catch-and-shoot volume allowed
        if (opp_speed > 4.56 and cs_3pa > 470):
             return "ZONE_FLUID"
        
        # Rule 4: RIM_FORTRESS
        # Proxy: Low drive FG% allowed
        if (drive_pct < 0.486):
            return "RIM_FORTRESS"
        
        # Rule 5: PERIMETER_FUNNEL
        # Proxy: High drive volume allowed but low 3PA allowed
        if (cs_3pa < 380 and drive_vol > 340):
            return "PERIMETER_FUNNEL"
        
        # Default: NEUTRAL (no clear pattern)
        return "NEUTRAL"
    
    def get_classification_summary(self, team_name: str) -> Dict:
        """Get detailed classification summary with reasoning."""
        stats = self._load_tracking_stats(team_name)
        classification = self.classify_defense(team_name)
        
        return {
            'team': team_name,
            'classification': classification,
            'reasoning': self._get_reasoning(classification, stats),
            'stats': stats,
            'sample_size': stats.get('sample_size', 0),
            'confidence': self._calculate_confidence(stats.get('sample_size', 0))
        }
    
    def _get_reasoning(self, classification: str, stats: Dict) -> str:
        """Provide human-readable reasoning for classification."""
        cs_3pa = stats.get('opp_catch_shoot_3pa', 0)
        drive_vol = stats.get('opp_drives_fga', 0)
        drive_pct = stats.get('opp_drive_fg_pct', 0)
        def_dist = stats.get('opp_avg_defender_dist', 0)

        reasoning_map = {
            "DROP_COVERAGE": f"Conservative positioning (Avg Dist: {def_dist:.1f}ft) + Solid paint D (Drive FG%: {drive_pct:.1%})",
            "SWITCH_HEAVY": f"Aggressive positioning (Avg Dist: {def_dist:.1f}ft) or High Drive Vol ({drive_vol:.1f})",
            "ZONE_FLUID": f"Forces ball movement (Opp Speed high) + Allows volume 3s ({cs_3pa:.1f}/game)",
            "RIM_FORTRESS": f"Elite rim protection (Drive FG% allowed: {drive_pct:.1%})",
            "PERIMETER_FUNNEL": f"Limits 3s ({cs_3pa:.1f}/game) + Funnels to paint (Drive Vol: {drive_vol:.1f})",
            "NEUTRAL": "Balanced profile or insufficient data"
        }
        return reasoning_map.get(classification, "Unknown classification")
    
    def _calculate_confidence(self, sample_size: int) -> str:
        """Calculate classification confidence based on sample size."""
        if sample_size >= 25:
            return "HIGH"
        elif sample_size >= 15:
            return "MEDIUM"
        elif sample_size >= 10:
            return "LOW"
        else:
            return "INSUFFICIENT"
    
    def _load_tracking_stats_by_games(self, team_name: str, last_n_games: int, end_date: str) -> Dict:
        """Load team defensive stats using game-count window (robust against schedule gaps)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            WITH team_game_dates AS (
                SELECT game_date,
                       ROW_NUMBER() OVER (ORDER BY game_date DESC) as game_num
                FROM (
                    SELECT DISTINCT game_date
                    FROM player_game_tracking
                    WHERE team_abbr = ?
                      AND game_date <= ?
                )
            )
            SELECT
                pg.game_date,
                SUM(pg.catch_shoot_3pa) as opp_catch_shoot_3pa,
                SUM(pg.catch_shoot_3pm) as opp_catch_shoot_3pm,
                SUM(pg.drives_fga) as opp_drives_fga,
                SUM(pg.drives_fgm) as opp_drives_fgm,
                AVG(pg.avg_speed_off) as opp_speed,
                AVG(pg.avg_defender_dist) as opp_avg_defender_dist
            FROM player_game_tracking pg
            JOIN team_game_dates tgd ON pg.game_date = tgd.game_date
            WHERE tgd.game_num <= ?
              AND pg.team_abbr != ?
            GROUP BY pg.game_date
            ORDER BY pg.game_date DESC
        """, (team_name, end_date, last_n_games, team_name))

        stats = cursor.fetchall()
        conn.close()

        if not stats:
            return {}

        total_games = len(stats)

        def safe_avg(idx):
            vals = [s[idx] for s in stats if s[idx] is not None]
            return sum(vals) / len(vals) if vals else 0

        avg_opp_cs_3pa = safe_avg(1)
        avg_opp_cs_3pm = safe_avg(2)
        avg_opp_drives_fga = safe_avg(3)
        avg_opp_drives_fgm = safe_avg(4)
        avg_opp_speed = safe_avg(5)
        avg_opp_def_dist = safe_avg(6)

        opp_drive_fg_pct = (avg_opp_drives_fgm / avg_opp_drives_fga) if avg_opp_drives_fga > 0 else 0
        opp_cs_3p_pct = (avg_opp_cs_3pm / avg_opp_cs_3pa) if avg_opp_cs_3pa > 0 else 0

        return {
            'opp_catch_shoot_3pa': avg_opp_cs_3pa,
            'opp_catch_shoot_3p_pct': opp_cs_3p_pct,
            'opp_drives_fga': avg_opp_drives_fga,
            'opp_drive_fg_pct': opp_drive_fg_pct,
            'opp_speed': avg_opp_speed,
            'opp_avg_defender_dist': avg_opp_def_dist,
            'sample_size': total_games
        }

    def batch_classify_all_teams_by_games(self, last_n_games: int = 30, end_date: str = None,
                                           min_games: int = 8, return_stats: bool = False):
        """Classify all 30 teams using game-count windows (robust against schedule gaps).

        Args:
            last_n_games: Number of most recent games per team to include
            end_date: Latest game date to consider
            min_games: Minimum games for valid classification
            return_stats: If True, return (classifications, stats_by_team) tuple
        """
        teams = [
            "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET",
            "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL",
            "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX", "POR",
            "SAC", "SAS", "TOR", "UTA", "WAS"
        ]

        end_date = self._resolve_window_end(end_date)
        raw_stats = {team: self._load_tracking_stats_by_games(team, last_n_games, end_date) for team in teams}

        stats_by_team = {}
        for team, stats in raw_stats.items():
            if not stats or stats.get('sample_size', 0) < min_games:
                stats_by_team[team] = {}
            else:
                stats_by_team[team] = stats
        thresholds = self._compute_relative_thresholds(stats_by_team)

        classifications = {}
        for team in teams:
            stats = stats_by_team.get(team, {})
            if not stats:
                classifications[team] = "NEUTRAL"
            else:
                classifications[team] = self._apply_relative_rules(stats, thresholds)

        if return_stats:
            return classifications, stats_by_team
        return classifications

    def batch_classify_all_teams(self, start_date: str = None, end_date: str = None,
                                 min_games: int = 10, return_stats: bool = False) -> Dict[str, str]:
        """Classify all 30 NBA teams."""
        teams = [
            "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET",
            "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL",
            "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX", "POR",
            "SAC", "SAS", "TOR", "UTA", "WAS"
        ]

        range_requested = start_date is not None or end_date is not None
        if range_requested:
            if start_date is None:
                start_date = "2025-10-01"
            end_date = self._resolve_window_end(end_date)
            raw_stats = {team: self._load_tracking_stats_range(team, start_date, end_date) for team in teams}
        else:
            raw_stats = {team: self._load_tracking_stats(team) for team in teams}

        stats_by_team = {}
        for team, stats in raw_stats.items():
            if not stats or stats.get('sample_size', 0) < min_games:
                stats_by_team[team] = {}
            else:
                stats_by_team[team] = stats
        thresholds = self._compute_relative_thresholds(stats_by_team)

        classifications = {}
        for team in teams:
            stats = stats_by_team.get(team, {})
            if not stats:
                classifications[team] = "NEUTRAL"
            else:
                classifications[team] = self._apply_relative_rules(stats, thresholds)

        if return_stats:
            return classifications, stats_by_team
        return classifications

def main():
    """CLI for testing defensive classifier."""
    import sys
    if len(sys.argv) > 1:
        team_name = sys.argv[1]
        classifier = TeamDefensiveClassifier()
        summary = classifier.get_classification_summary(team_name)
        
        print(f"Defensive Classification: {team_name}")
        print("=" * 40)
        print(f"Classification: {summary['classification']}")
        print(f"Reasoning: {summary['reasoning']}")
        print(f"Sample Size: {summary['sample_size']} games")
        print(f"Confidence: {summary['confidence']}")
        print(f"Stats: {summary['stats']}")
        print("=" * 40)
    else:
        classifier = TeamDefensiveClassifier()
        all_classifications = classifier.batch_classify_all_teams()
        
        print("All Team Defensive Classifications")
        print("=" * 50)
        for team, classification in all_classifications.items():
            print(f"{team}: {classification}")
        print("=" * 50)

if __name__ == "__main__":
    main()
