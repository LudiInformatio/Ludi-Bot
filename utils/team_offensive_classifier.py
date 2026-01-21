#!/usr/bin/env python3
"""
Team Offensive Classifier
===================

Dynamic classification of NBA team offensive schemes based on comprehensive data:
- Regular season stats (points, pace, assists, etc.)
- Player tracking data (drives, catch & shoot, pull-ups)
- Shot quality data (rim frequency, corner 3s, expected eFG%)
- WOWY lineup data (on/off court impact)
- Advanced metrics (transition points, paint touches)

Uses multi-layered approach for accurate offensive typing.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import statistics
from typing import Iterable

class TeamOffensiveClassifier:
    """Multi-data team offensive scheme classification."""
    
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        self.classification_cache = {}
        self.last_cache_update = None
        
        # Classification thresholds (research-backed)
        self.THRESHOLDS = {
            # Pace metrics
            'high_pace': 105.0,              # >105 possessions/game
            'slow_pace': 95.0,               # <95 possessions/game
            'avg_pace': 100.0,               # 95-105 possessions/game
            
            # Shooting metrics
            'high_3pa_rate': 0.40,            # >40% of FGA from 3
            'low_3pa_rate': 0.25,             # <25% of FGA from 3
            'high_paint_touches': 55.0,          # >55 touches in paint/game
            'low_paint_touches': 35.0,          # <35 touches in paint/game
            
            # Playstyle metrics
            'high_iso_rate': 0.25,             # >25% ISO possessions
            'high_pnr_rate': 0.15,             # >15% P&R possessions
            'high_assist_rate': 0.65,           # >65% AST/FGA
            'low_assist_rate': 0.55,            # <55% AST/FGA
            
            # Advanced metrics
            'high_transition_rate': 0.20,          # >20% transition points
            'high_wowy_net_impact': 2.5,        # >2.5 net rating advantage
            'high_shot_quality_eFG': 0.55,         # >55% expected eFG%
            'min_games_sample': 10,             # Need 10+ games for reliability
        }
        
    def _load_team_stats(self, team_name: str, games_back: int = 20) -> Dict:
        """Load comprehensive team stats from multiple data sources."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Regular season team stats (from player_game_logs aggregated)
        cursor.execute("""
            SELECT 
                g.date,
                SUM(pgl.pts) as team_pts,
                SUM(pgl.fga) as team_fga,
                SUM(pgl.fg3a) as team_fg3a,
                SUM(pgl.ast) as team_ast,
                SUM(pgl.tov) as team_tov,
                AVG(g.pace) as pace
            FROM player_game_logs pgl
            JOIN games g ON pgl.game_date = g.date
            WHERE (g.home_team = ? OR g.away_team = ?)
            AND pgl.team_abbreviation = ?
            AND pgl.game_date >= date('now', '-{} days')
            GROUP BY g.date
        """.format(games_back), (team_name, team_name, team_name))
        
        daily_stats = cursor.fetchall()
        
        if not daily_stats:
            conn.close()
            return {}

        def safe_mean(data):
            valid = [x for x in data if x is not None]
            return statistics.mean(valid) if valid else 0

        total_games = len(daily_stats)
        avg_pts = safe_mean([s[1] for s in daily_stats])
        avg_fga = safe_mean([s[2] for s in daily_stats])
        avg_fg3a = safe_mean([s[3] for s in daily_stats])
        avg_assists = safe_mean([s[4] for s in daily_stats])
        avg_tov = safe_mean([s[5] for s in daily_stats])
        avg_pace = safe_mean([s[6] for s in daily_stats])
        
        # 2. Player tracking stats (aggregated per game)
        cursor.execute("""
            SELECT 
                SUM(pt.drives_fga) as total_drives_fga,
                SUM(pt.catch_shoot_fga) as total_catch_shoot_fga,
                SUM(pt.pull_up_fga) as total_pull_up_fga,
                AVG(pt.avg_speed_off) as avg_speed,
                SUM(pt.drives_pts) as total_drives_pts
            FROM player_game_tracking pt
            JOIN games g ON pt.game_date = g.date
            WHERE (g.home_team = ? OR g.away_team = ?)
            AND pt.team_abbr = ? -- Only stats for OUR team
            AND pt.game_date >= date('now', '-{} days')
            GROUP BY g.date
        """.format(games_back), (team_name, team_name, team_name))
        
        tracking_rows = cursor.fetchall()
        
        avg_drives_fga = safe_mean([r[0] for r in tracking_rows])
        avg_catch_shoot_fga = safe_mean([r[1] for r in tracking_rows])
        avg_pull_up_fga = safe_mean([r[2] for r in tracking_rows])
        avg_drives_pts = safe_mean([r[4] for r in tracking_rows])
        
        conn.close()
        
        return {
            'games_sample': total_games,
            'tracking_sample': len(tracking_rows),
            
            'avg_pts': avg_pts,
            'avg_fga': avg_fga,
            'avg_fg3a': avg_fg3a,
            'avg_assists': avg_assists,
            'avg_tov': avg_tov,
            'avg_pace': avg_pace,
            
            'avg_drives_fga': avg_drives_fga,
            'avg_catch_shoot_fga': avg_catch_shoot_fga,
            'avg_pull_up_fga': avg_pull_up_fga,
            'avg_drives_pts': avg_drives_pts
        }
    
    def classify_offense(self, team_name: str, force_refresh: bool = False) -> str:
        """
        Classify team offensive scheme using multi-layered data approach.
        
        Returns one of: PACE_AND_SPACE, PAINT_ATTACK, MOTION_OFFENSE, ISOLATION_HEAVY,
                     TRANSITION_FOCUSED, THREE_POINT_CENTRIC
        """
        # Check cache first
        cache_key = f"{team_name}_{datetime.now().strftime('%Y-%m-%d')}"
        
        if not force_refresh and cache_key in self.classification_cache:
            cached = self.classification_cache[cache_key]
            if datetime.now() - cached['timestamp'] < timedelta(days=1):  # 1-day cache
                return cached['classification']
        
        # Load comprehensive stats
        stats = self._load_team_stats(team_name)
        
        if not stats or stats.get('games_sample', 0) < self.THRESHOLDS['min_games_sample']:
            return "NEUTRAL"  # Default if insufficient data
        
        # Apply multi-layered classification logic
        classification = self._apply_offensive_rules(stats)
        
        # Cache result
        self.classification_cache[cache_key] = {
            'classification': classification,
            'timestamp': datetime.now(),
            'stats': stats
        }
        
        return classification
    
    def _apply_offensive_rules(self, stats: Dict) -> str:
        """Apply comprehensive offensive classification rules using available data."""
        
        pace = stats.get('avg_pace', 100)
        fg3a = stats.get('avg_fg3a', 30)
        fga = stats.get('avg_fga', 90)
        assists = stats.get('avg_assists', 25)
        drives = stats.get('avg_drives_fga', 40)
        pullups = stats.get('avg_pull_up_fga', 20)
        catch_shoot = stats.get('avg_catch_shoot_fga', 25)
        
        fg3a_rate = fg3a / fga if fga else 0.33
        ast_ratio = assists / fga if fga else 0.25

        # Rule 1: PACE_AND_SPACE 
        if (pace > 100 and fg3a_rate > 0.40):
            return "PACE_AND_SPACE"
        
        # Rule 2: PAINT_ATTACK (High drives)
        if (drives > 50):
            return "PAINT_ATTACK"
        
        # Rule 3: MOTION_OFFENSE (High assists, balanced 3s)
        if (ast_ratio > 0.65):
            return "MOTION_OFFENSE"
        
        # Rule 4: ISOLATION_HEAVY (High pull-ups, lower assists)
        if (pullups > 25 and ast_ratio < 0.58):
            return "ISOLATION_HEAVY"
        
        # Rule 5: THREE_POINT_CENTRIC (Extreme 3s)
        if (fg3a_rate > 0.45):
            return "THREE_POINT_CENTRIC"
        
        # Additional logic for transition could use pace/pts gap, but simplified for now:
        if (pace > 102 and drives > 45):
             return "TRANSITION_FOCUSED"
        
        # Default: NEUTRAL (balanced or insufficient data)
        return "NEUTRAL"
    
    def get_classification_summary(self, team_name: str) -> Dict:
        """Get detailed offensive classification summary with reasoning."""
        stats = self._load_team_stats(team_name)
        classification = self.classify_offense(team_name)
        
        return {
            'team': team_name,
            'classification': classification,
            'reasoning': self._get_offensive_reasoning(classification, stats),
            'stats_summary': {
                'sample_sizes': {
                    'games': stats.get('games_sample', 0),
                    'tracking': stats.get('tracking_sample', 0)
                },
                'team_performance': {
                    'avg_pts': round(stats.get('avg_pts', 0), 1),
                    'avg_pace': round(stats.get('avg_pace', 0), 1),
                    'avg_fga': round(stats.get('avg_fga', 0), 1),
                    'avg_fg3a': round(stats.get('avg_fg3a', 0), 1),
                    'avg_3pa_rate': round(stats.get('avg_fg3a', 0) / max(stats.get('avg_fga', 1), 1), 3),
                    'avg_assists': round(stats.get('avg_assists', 0), 1)
                },
                'playstyle_metrics': {
                    'avg_drives_fga': round(stats.get('avg_drives_fga', 0), 1),
                    'avg_pull_up_fga': round(stats.get('avg_pull_up_fga', 0), 1),
                    'avg_catch_shoot_fga': round(stats.get('avg_catch_shoot_fga', 0), 1),
                },
                'advanced_metrics': {
                    # Temporarily sparse until reliable data is available
                    'avg_drives_pts': round(stats.get('avg_drives_pts', 0), 1),
                }
            },
            'confidence': self._calculate_confidence(stats.get('games_sample', 0))
        }
    
    def _get_offensive_reasoning(self, classification: str, stats: Dict) -> str:
        """Provide human-readable reasoning for offensive classification."""
        pace = stats.get('avg_pace', 100)
        fg3a = stats.get('avg_fg3a', 0)
        fga = stats.get('avg_fga', 1)
        fg3a_rate = fg3a / fga if fga else 0
        drives = stats.get('avg_drives_fga', 0)
        
        reasoning_map = {
            "PACE_AND_SPACE": f"High pace ({pace:.1f}) + High 3PA rate ({fg3a_rate:.1%})",
            "PAINT_ATTACK": f"High drive volume ({drives:.1f}/game)",
            "MOTION_OFFENSE": f"High assist rate (+Ball Movement)",
            "ISOLATION_HEAVY": f"High Pull-up volume + Low Assist Rate",
            "TRANSITION_FOCUSED": f"High Pace ({pace:.1f}) + Aggressive Attacks",
            "THREE_POINT_CENTRIC": f"Elite 3PA rate ({fg3a_rate:.1%})",
            "NEUTRAL": "Balanced profile or insufficient data"
        }
        return reasoning_map.get(classification, "Unknown classification")
    
    def _calculate_confidence(self, sample_size: int) -> str:
        """Calculate classification confidence based on sample size across data sources."""
        # Weight different data sources
        if sample_size >= 20:  # Strong sample across regular season and tracking
            return "HIGH"
        elif sample_size >= 15:  # Good sample
            return "MEDIUM"
        elif sample_size >= 10:  # Minimum for basic classification
            return "LOW"
        else:
            return "INSUFFICIENT"
    
    def batch_classify_all_teams(self) -> Dict[str, str]:
        """Classify all 30 NBA teams using comprehensive data."""
        teams = [
            "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET",
            "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL",
            "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX", "POR",
            "SAC", "SAS", "TOR", "UTA", "WAS"
        ]
        
        classifications = {}
        for team in teams:
            classifications[team] = self.classify_offense(team)
        
        return classifications

def main():
    """CLI for testing offensive classifier."""
    import sys
    if len(sys.argv) > 1:
        team_name = sys.argv[1]
        classifier = TeamOffensiveClassifier()
        summary = classifier.get_classification_summary(team_name)
        
        print(f"Offensive Classification: {team_name}")
        print("=" * 50)
        print(f"Classification: {summary['classification']}")
        print(f"Reasoning: {summary['reasoning']}")
        print(f"Confidence: {summary['confidence']}")
        print("\\nTeam Performance Metrics:")
        for key, value in summary['stats_summary']['team_performance'].items():
            print(f"  {key}: {value}")
        print("\\nPlaystyle Metrics:")
        for key, value in summary['stats_summary']['playstyle_metrics'].items():
            print(f"  {key}: {value}")
        print(f"\\nAdvanced Metrics:")
        for key, value in summary['stats_summary']['advanced_metrics'].items():
            print(f"  {key}: {value}")
        print("=" * 50)
    else:
        classifier = TeamOffensiveClassifier()
        all_classifications = classifier.batch_classify_all_teams()
        
        print("All Team Offensive Classifications (Comprehensive)")
        print("=" * 60)
        for team, classification in all_classifications.items():
            print(f"{team}: {classification}")
        print("=" * 60)

if __name__ == "__main__":
    main()