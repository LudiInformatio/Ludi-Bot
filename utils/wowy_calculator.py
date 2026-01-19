"""
WOWY (With Or Without You) Calculator

Queries team_lineups table (scraped from NBA.com/stats) to find:
- Player impact on lineup efficiency (ORtg, DRtg, NetRtg)
- Beneficiaries when a player is OUT (usage vacuum)
- Best/worst lineups for a team

Uses 350 possession threshold as reliable sample size (industry midpoint).

Confidence tiers:
- HIGH: 500+ possessions (very reliable)
- MEDIUM: 350-499 possessions (reliable)
- LOW: 150-349 possessions (marginal)
- INSUFFICIENT: <150 possessions (do not use)

Integrates with Module X (Scenario Builder) for data-driven usage vacuum.

Author: Ludi Informatio
Date: January 2026
"""

import argparse
import sqlite3
import sys
from typing import Dict, List, Optional, Tuple


class WOWYCalculator:
    """WOWY calculator for NBA lineup analysis."""
    
    # Possession thresholds for confidence tiers
    THRESHOLD_HIGH = 500
    THRESHOLD_MEDIUM = 350
    THRESHOLD_LOW = 150
    
    def __init__(self, db_path: str = "ludi.db"):
        """Initialize calculator with database connection."""
        self.db_path = db_path
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Establish database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Access columns by name
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            sys.exit(1)
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def get_confidence_tier(self, possessions: float) -> str:
        """
        Determine confidence tier based on possession sample size.
        
        Args:
            possessions: Total possessions played
            
        Returns:
            'high', 'medium', 'low', or 'insufficient'
        """
        if possessions >= self.THRESHOLD_HIGH:
            return 'high'
        elif possessions >= self.THRESHOLD_MEDIUM:
            return 'medium'
        elif possessions >= self.THRESHOLD_LOW:
            return 'low'
        else:
            return 'insufficient'
    
    def get_confidence_weight(self, confidence: str) -> float:
        """
        Get multiplier weight for confidence tier.
        
        Args:
            confidence: Tier ('high', 'medium', 'low', 'insufficient')
            
        Returns:
            Weight (1.0 = full confidence, 0.0 = no confidence)
        """
        weights = {
            'high': 1.0,
            'medium': 0.7,
            'low': 0.4,
            'insufficient': 0.0
        }
        return weights.get(confidence, 0.0)
    
    def get_player_impact(self, player_name: str, team: str, min_possessions: float = 350) -> Optional[Dict]:
        """
        Get player's impact on lineup efficiency (WITH vs WITHOUT).
        
        Args:
            player_name: Player's full name
            team: 3-letter team abbreviation
            min_possessions: Minimum possessions required (default: 350)
            
        Returns:
            Dict with WITH/WITHOUT stats and confidence, or None if insufficient data
        """
        cursor = self.conn.cursor()
        
        # Query lineups WITH player (player in lineup_players)
        cursor.execute("""
            SELECT 
                AVG(off_rating) as with_ortg,
                AVG(def_rating) as with_drtg,
                AVG(net_rating) as with_netrtg,
                SUM(possessions) as with_poss,
                COUNT(*) as with_games
            FROM team_lineups
            WHERE team_abbreviation = ?
                AND lineup_players LIKE ?
                AND possessions >= 10
        """, (team, f'%{player_name}%'))
        
        with_row = cursor.fetchone()
        
        # Query lineups WITHOUT player (player NOT in lineup_players)
        cursor.execute("""
            SELECT 
                AVG(off_rating) as without_ortg,
                AVG(def_rating) as without_drtg,
                AVG(net_rating) as without_netrtg,
                SUM(possessions) as without_poss,
                COUNT(*) as without_games
            FROM team_lineups
            WHERE team_abbreviation = ?
                AND lineup_players NOT LIKE ?
                AND possessions >= 10
        """, (team, f'%{player_name}%'))
        
        without_row = cursor.fetchone()
        
        # Check if sufficient data
        with_poss = with_row['with_poss'] or 0
        without_poss = without_row['without_poss'] or 0
        
        if with_poss < min_possessions or without_poss < min_possessions:
            return None
        
        # Calculate impact
        with_ortg = with_row['with_ortg'] or 0
        without_ortg = without_row['without_ortg'] or 0
        with_drtg = with_row['with_drtg'] or 0
        without_drtg = without_row['without_drtg'] or 0
        with_netrtg = with_row['with_netrtg'] or 0
        without_netrtg = without_row['without_netrtg'] or 0
        
        return {
            'player': player_name,
            'team': team,
            'with': {
                'ortg': with_ortg,
                'drtg': with_drtg,
                'netrtg': with_netrtg,
                'poss': with_poss,
                'games': with_row['with_games']
            },
            'without': {
                'ortg': without_ortg,
                'drtg': without_drtg,
                'netrtg': without_netrtg,
                'poss': without_poss,
                'games': without_row['without_games']
            },
            'impact': {
                'ortg_diff': with_ortg - without_ortg,
                'drtg_diff': with_drtg - without_drtg,  # Lower is better
                'netrtg_diff': with_netrtg - without_netrtg
            },
            'confidence': self.get_confidence_tier(min(with_poss, without_poss))
        }
    
    def find_beneficiaries(self, absent_player: str, team: str, min_possessions: float = 350) -> List[Dict]:
        """
        Find players who benefit when a star is OUT (usage vacuum).
        
        Args:
            absent_player: Name of OUT player
            team: 3-letter team abbreviation
            min_possessions: Minimum possessions required (default: 350)
            
        Returns:
            List of dicts with beneficiary stats and confidence
        """
        cursor = self.conn.cursor()
        
        # Get all players who play on team WITHOUT the absent player
        # Extract from lineup_players string (format: "Player A - Player B - Player C - Player D - Player E")
        cursor.execute("""
            SELECT DISTINCT lineup_players
            FROM team_lineups
            WHERE team_abbreviation = ?
                AND lineup_players NOT LIKE ?
                AND possessions >= 10
        """, (team, f'%{absent_player}%'))
        
        # Parse lineup_players strings to extract individual player names
        candidates_set = set()
        for row in cursor.fetchall():
            lineup_str = row['lineup_players']
            if lineup_str:
                players = [p.strip() for p in lineup_str.split(' - ')]
                candidates_set.update(players)
        
        candidates = [p for p in candidates_set if p and p != absent_player]
        
        # For each candidate, check if they have enough sample WITH and WITHOUT absent player
        beneficiaries = []
        
        for candidate in candidates:
            # Lineups WITH candidate AND WITHOUT absent player
            cursor.execute("""
                SELECT 
                    AVG(off_rating) as ortg,
                    SUM(possessions) as poss
                FROM team_lineups
                WHERE team_abbreviation = ?
                    AND lineup_players LIKE ?
                    AND lineup_players NOT LIKE ?
                    AND possessions >= 10
            """, (team, f'%{candidate}%', f'%{absent_player}%'))
            
            without_star_row = cursor.fetchone()
            
            # Lineups WITH candidate AND WITH absent player
            cursor.execute("""
                SELECT 
                    AVG(off_rating) as ortg,
                    SUM(possessions) as poss
                FROM team_lineups
                WHERE team_abbreviation = ?
                    AND lineup_players LIKE ?
                    AND lineup_players LIKE ?
                    AND possessions >= 10
            """, (team, f'%{candidate}%', f'%{absent_player}%'))
            
            with_star_row = cursor.fetchone()
            
            # Check sample size
            without_poss = without_star_row['poss'] or 0
            with_poss = with_star_row['poss'] or 0
            
            if without_poss < min_possessions or with_poss < min_possessions:
                continue
            
            # Calculate usage boost
            without_ortg = without_star_row['ortg'] or 0
            with_ortg = with_star_row['ortg'] or 0
            ortg_boost = without_ortg - with_ortg
            
            beneficiaries.append({
                'player': candidate,
                'without_star': {
                    'ortg': without_ortg,
                    'poss': without_poss
                },
                'with_star': {
                    'ortg': with_ortg,
                    'poss': with_poss
                },
                'ortg_boost': ortg_boost,
                'confidence': self.get_confidence_tier(min(without_poss, with_poss))
            })
        
        # Sort by ORtg boost (descending)
        beneficiaries.sort(key=lambda x: x['ortg_boost'], reverse=True)
        
        return beneficiaries
    
    def get_team_best_lineups(self, team: str, limit: int = 10, min_possessions: float = 150) -> List[Dict]:
        """
        Get team's best lineups by NetRtg.
        
        Args:
            team: 3-letter team abbreviation
            limit: Number of lineups to return (default: 10)
            min_possessions: Minimum possessions required (default: 150)
            
        Returns:
            List of lineup dicts sorted by NetRtg
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                lineup_players,
                off_rating,
                def_rating,
                net_rating,
                possessions,
                minutes
            FROM team_lineups
            WHERE team_abbreviation = ?
                AND possessions >= ?
            ORDER BY net_rating DESC
            LIMIT ?
        """, (team, min_possessions, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_team_worst_lineups(self, team: str, limit: int = 10, min_possessions: float = 150) -> List[Dict]:
        """
        Get team's worst lineups by NetRtg.
        
        Args:
            team: 3-letter team abbreviation
            limit: Number of lineups to return (default: 10)
            min_possessions: Minimum possessions required (default: 150)
            
        Returns:
            List of lineup dicts sorted by NetRtg (ascending)
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                lineup_players,
                off_rating,
                def_rating,
                net_rating,
                possessions,
                minutes
            FROM team_lineups
            WHERE team_abbreviation = ?
                AND possessions >= ?
            ORDER BY net_rating ASC
            LIMIT ?
        """, (team, min_possessions, limit))
        
        return [dict(row) for row in cursor.fetchall()]


def main():
    """CLI entry point for testing and demonstration."""
    parser = argparse.ArgumentParser(
        description="WOWY (With Or Without You) lineup analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Player impact analysis
  python wowy_calculator.py --player "Nikola Jokić" --team DEN --report
  
  # Find beneficiaries when star is OUT
  python wowy_calculator.py --beneficiaries "Damian Lillard" --team MIL
  
  # Best lineups for team
  python wowy_calculator.py --best OKC
  
  # Worst lineups for team
  python wowy_calculator.py --worst LAL --limit 5
        """
    )
    
    parser.add_argument('--player', type=str,
                        help='Player name for impact analysis')
    parser.add_argument('--team', type=str,
                        help='3-letter team abbreviation')
    parser.add_argument('--beneficiaries', type=str,
                        help='Find beneficiaries when this player is OUT')
    parser.add_argument('--best', type=str,
                        help='Show best lineups for team')
    parser.add_argument('--worst', type=str,
                        help='Show worst lineups for team')
    parser.add_argument('--report', action='store_true',
                        help='Display full report with context')
    parser.add_argument('--limit', type=int, default=10,
                        help='Number of lineups to show (default: 10)')
    parser.add_argument('--min-poss', type=float, default=350,
                        help='Minimum possessions required (default: 350)')
    
    args = parser.parse_args()
    
    calc = WOWYCalculator()
    
    try:
        # Player impact analysis
        if args.player and args.team:
            result = calc.get_player_impact(args.player, args.team, args.min_poss)
            
            if result is None:
                print(f"\n❌ Insufficient data for {args.player} ({args.team})")
                print(f"   Requires {args.min_poss}+ possessions WITH and WITHOUT player")
                return
            
            print(f"\n{'='*70}")
            print(f"WOWY Analysis: {result['player']} ({result['team']})")
            print(f"{'='*70}")
            print(f"Confidence: {result['confidence'].upper()} ({result['with']['poss']:.0f}/{result['without']['poss']:.0f} poss)")
            print()
            print(f"WITH {result['player']}:")
            print(f"  ORtg: {result['with']['ortg']:.1f}  |  DRtg: {result['with']['drtg']:.1f}  |  NetRtg: {result['with']['netrtg']:.1f}")
            print(f"  Sample: {result['with']['poss']:.0f} poss across {result['with']['games']} games")
            print()
            print(f"WITHOUT {result['player']}:")
            print(f"  ORtg: {result['without']['ortg']:.1f}  |  DRtg: {result['without']['drtg']:.1f}  |  NetRtg: {result['without']['netrtg']:.1f}")
            print(f"  Sample: {result['without']['poss']:.0f} poss across {result['without']['games']} games")
            print()
            print(f"IMPACT (WITH - WITHOUT):")
            print(f"  ORtg: {result['impact']['ortg_diff']:+.1f}  |  DRtg: {result['impact']['drtg_diff']:+.1f}  |  NetRtg: {result['impact']['netrtg_diff']:+.1f}")
            print()
            
            if result['impact']['netrtg_diff'] > 5:
                print("💡 Interpretation: MAJOR positive impact (team +5+ NetRtg with player)")
            elif result['impact']['netrtg_diff'] > 2:
                print("💡 Interpretation: Solid positive impact (team +2-5 NetRtg with player)")
            elif result['impact']['netrtg_diff'] > -2:
                print("💡 Interpretation: Neutral impact (minimal difference)")
            else:
                print("💡 Interpretation: Negative impact (team better without player)")
            print()
        
        # Beneficiary analysis
        elif args.beneficiaries and args.team:
            beneficiaries = calc.find_beneficiaries(args.beneficiaries, args.team, args.min_poss)
            
            if not beneficiaries:
                print(f"\n❌ No beneficiaries found for {args.beneficiaries} ({args.team})")
                print(f"   Requires {args.min_poss}+ possessions WITH and WITHOUT absent player")
                return
            
            print(f"\n{'='*70}")
            print(f"Usage Vacuum Beneficiaries: {args.beneficiaries} OUT ({args.team})")
            print(f"{'='*70}")
            print()
            
            for i, ben in enumerate(beneficiaries[:5], 1):
                print(f"{i}. {ben['player']} ({ben['confidence'].upper()})")
                print(f"   ORtg boost: {ben['ortg_boost']:+.1f}")
                print(f"   WITHOUT star: {ben['without_star']['ortg']:.1f} ORtg ({ben['without_star']['poss']:.0f} poss)")
                print(f"   WITH star: {ben['with_star']['ortg']:.1f} ORtg ({ben['with_star']['poss']:.0f} poss)")
                print()
        
        # Best lineups
        elif args.best:
            lineups = calc.get_team_best_lineups(args.best, args.limit, args.min_poss)
            
            if not lineups:
                print(f"\n❌ No lineups found for {args.best}")
                return
            
            print(f"\n{'='*70}")
            print(f"Best Lineups: {args.best}")
            print(f"{'='*70}")
            print()
            
            for i, lineup in enumerate(lineups, 1):
                print(f"{i}. NetRtg: {lineup['net_rating']:+.1f}  (ORtg: {lineup['off_rating']:.1f}, DRtg: {lineup['def_rating']:.1f})")
                print(f"   {lineup['lineup_players']}")
                print(f"   Sample: {lineup['possessions']:.0f} poss, {lineup['minutes']:.1f} min")
                print()
        
        # Worst lineups
        elif args.worst:
            lineups = calc.get_team_worst_lineups(args.worst, args.limit, args.min_poss)
            
            if not lineups:
                print(f"\n❌ No lineups found for {args.worst}")
                return
            
            print(f"\n{'='*70}")
            print(f"Worst Lineups: {args.worst}")
            print(f"{'='*70}")
            print()
            
            for i, lineup in enumerate(lineups, 1):
                print(f"{i}. NetRtg: {lineup['net_rating']:+.1f}  (ORtg: {lineup['off_rating']:.1f}, DRtg: {lineup['def_rating']:.1f})")
                print(f"   {lineup['lineup_players']}")
                print(f"   Sample: {lineup['possessions']:.0f} poss, {lineup['minutes']:.1f} min")
                print()
        
        else:
            parser.print_help()
    
    finally:
        calc.close()


if __name__ == "__main__":
    main()
