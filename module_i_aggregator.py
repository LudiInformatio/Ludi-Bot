import config
import requests
# [FUTURE] This module will serve as the central hub for data fetching,
# routing requests to the appropriate API provider based on availability and cost.

class LudiAggregator:
    """
    Central Data Aggregator for Ludi Information.
    Routes requests to Primary, Secondary, or Fallback APIs.
    """
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE I (AGGREGATOR) ONLINE")
        print(f"   >>> UNIFIED DATA LAYER ACTIVE")
        print(f"{'='*40}")
        
        self.sources = {
            'odds': ['the_odds_api', 'balldontlie'],
            'injuries': ['tank01', 'balldontlie'],
            'stats': ['tank01', 'apisports'],
        }

    def get_player_props(self, game_id, sport='basketball_nba'):
        """
        Fetch props with fallback logic.
        1. Try The-Odds-API (Primary)
        2. Try BallDontLie (Backup)
        """
        # Placeholder for future logic
        pass

    def get_injury_report(self):
        """
        Fetch injury report.
        1. Try Tank01 (Primary - 15min refresh)
        2. Try BallDontLie (Backup)
        """
        # Placeholder for future logic
        pass

if __name__ == "__main__":
    aggregator = LudiAggregator()
    print("Aggregator Ready.")
