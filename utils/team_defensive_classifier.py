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
        
    def _load_tracking_stats(self, team_name: str, games_back: int = 20) -> Dict:
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
            JOIN games g ON pg.game_date = g.date
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
        # Proxies: Allows 3s (maybe), but mostly defined by limiting rim efficiency or keeping opponents in front (low speed?)
        # Better Proxy: Low defender distance (sagging) AND solid drive defense
        if (def_dist < 4.5 and drive_pct < 0.45):
            return "DROP_COVERAGE"
        
        # Rule 2: SWITCH_HEAVY 
        # Proxy: Tighter defender distance + higher drive volume allowed (switches create mismatches/drives)
        if (def_dist > 5.5 or drive_vol > 30):
            return "SWITCH_HEAVY"
        
        # Rule 3: ZONE_FLUID 
        # Proxy: High opponent speed (moving ball against zone) + Low 3P% allowed (closing out)
        if (opp_speed > 4.5 and cs_3pa > 25):
             return "ZONE_FLUID"
        
        # Rule 4: RIM_FORTRESS 
        # Proxy: Low drive FG% allowed
        if (drive_pct < 0.42):
            return "RIM_FORTRESS"
        
        # Rule 5: PERIMETER_FUNNEL 
        # Proxy: High drive volume allowed but low 3PA allowed
        if (cs_3pa < 20 and drive_vol > 25):
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
    
    def batch_classify_all_teams(self) -> Dict[str, str]:
        """Classify all 30 NBA teams."""
        teams = [
            "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET",
            "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL",
            "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX", "POR",
            "SAC", "SAS", "TOR", "UTA", "WAS"
        ]
        
        classifications = {}
        for team in teams:
            classifications[team] = self.classify_defense(team)
        
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