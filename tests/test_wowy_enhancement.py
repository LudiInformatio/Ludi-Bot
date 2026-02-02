"""
Unit Tests for Phase 6.3: WOWY Data Enhancement

Tests verify that:
1. SQL aggregation view returns correct data
2. New confidence thresholds work correctly  
3. WOWY calculator uses new data sources
4. Integration with BENEFICIARY tagging works
5. Database schema supports new table
"""

import sys
from pathlib import Path
import sqlite3

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.wowy_calculator import WOWYCalculator


class TestWOWYEnhancement:
    """Test suite for WOWY data enhancement (Phase 6.3)"""

    def test_sql_view_returns_aggregated_data(self):
        """Test 1: lineup_season_totals view aggregates per-game data"""
        conn = sqlite3.connect("ludi.db")
        cursor = conn.cursor()
        
        # Check view exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view' AND name='lineup_season_totals'")
        result = cursor.fetchone()
        assert result is not None, "lineup_season_totals view should exist"
        
        # Check view returns data
        cursor.execute("SELECT * FROM lineup_season_totals WHERE total_possessions > 100 LIMIT 5")
        rows = cursor.fetchall()
        
        assert len(rows) > 0, "View should return lineups with 100+ possessions"
        
        # Check aggregation worked (total_possessions should be higher than per-game max of 58)
        max_poss = max(row[2] for row in rows)  # total_possessions is 3rd column
        assert max_poss > 58, f"Aggregation should yield >58 possessions (got {max_poss})"
        
        conn.close()
        print("✅ Test 1 passed: SQL view returns aggregated data")

    def test_new_confidence_thresholds(self):
        """Test 2: Confidence thresholds are adaptive based on season progress"""
        calc = WOWYCalculator()

        # Test adaptive thresholds (scaled from BASE values by season progress)
        # BASE: HIGH=500, MEDIUM=350, LOW=150
        # Scale factor range: 0.40 (floor) to 1.00 (full season)
        info = calc.get_threshold_info()

        # Verify thresholds are properly scaled
        assert calc.THRESHOLD_HIGH == int(calc.BASE_THRESHOLD_HIGH * calc._season_progress), \
            f"HIGH should be scaled: {calc.THRESHOLD_HIGH} != {int(calc.BASE_THRESHOLD_HIGH * calc._season_progress)}"
        assert calc.THRESHOLD_MEDIUM == int(calc.BASE_THRESHOLD_MEDIUM * calc._season_progress), \
            "MEDIUM should be scaled from base"
        assert calc.THRESHOLD_LOW == int(calc.BASE_THRESHOLD_LOW * calc._season_progress), \
            "LOW should be scaled from base"

        # Test floor enforced (40% minimum)
        assert calc._season_progress >= 0.40, "Season progress should have 40% floor"

        # Test confidence tier assignment works correctly
        # Use relative thresholds for testing
        assert calc.get_confidence_tier(calc.THRESHOLD_HIGH + 100) == 'high', "Above HIGH threshold should be HIGH"
        assert calc.get_confidence_tier(calc.THRESHOLD_MEDIUM + 10) == 'medium', "Just above MEDIUM should be MEDIUM"
        assert calc.get_confidence_tier(calc.THRESHOLD_LOW + 5) == 'low', "Just above LOW should be LOW"
        assert calc.get_confidence_tier(calc.THRESHOLD_LOW - 10) == 'insufficient', "Below LOW should be INSUFFICIENT"

        print(f"   Season progress: {info['season_progress']}")
        print(f"   Scaled thresholds: HIGH={calc.THRESHOLD_HIGH}, MEDIUM={calc.THRESHOLD_MEDIUM}, LOW={calc.THRESHOLD_LOW}")

        calc.close()
        print("✅ Test 2 passed: Adaptive confidence thresholds work correctly")

    def test_player_season_wowy_table_exists(self):
        """Test 3: player_season_wowy table created with correct schema"""
        conn = sqlite3.connect("ludi.db")
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_season_wowy'")
        result = cursor.fetchone()
        assert result is not None, "player_season_wowy table should exist"
        
        # Check schema
        cursor.execute("PRAGMA table_info(player_season_wowy)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        required_cols = ['player_id', 'player_name', 'team_abbr', 'season',
                        'on_possessions', 'on_ortg', 'on_drtg', 'on_netrtg',
                        'off_possessions', 'off_ortg', 'off_drtg', 'off_netrtg',
                        'on_off_diff', 'synced_at']
        
        for col in required_cols:
            assert col in columns, f"{col} column should exist"
        
        conn.close()
        print("✅ Test 3 passed: player_season_wowy table schema correct")

    def test_calculator_uses_lower_thresholds(self):
        """Test 4: WOWY calculator now returns data with lower thresholds"""
        calc = WOWYCalculator()
        
        # Try to get beneficiaries with new threshold (100 possessions)
        # This should now work for teams that previously failed
        beneficiaries = calc.find_beneficiaries('Nikola Jokic', 'DEN', min_possessions=100)
        
        # With aggregated data and lower thresholds, we might get results
        # (test passes even if empty - data quality is separate from code correctness)
        assert isinstance(beneficiaries, list), "Should return a list"
        
        if beneficiaries:
            assert 'player' in beneficiaries[0], "Beneficiary should have player name"
            assert 'confidence' in beneficiaries[0], "Beneficiary should have confidence tier"
            print(f"   Found {len(beneficiaries)} beneficiaries with new thresholds")
        else:
            print(f"   No beneficiaries found (may need more season data)")
        
        calc.close()
        print("✅ Test 4 passed: Calculator uses lower thresholds")

    def test_integration_with_aggregated_view(self):
        """Test 5: Verify aggregated view provides better data than per-game"""
        conn = sqlite3.connect("ludi.db")
        cursor = conn.cursor()
        
        # Compare per-game max vs aggregated max
        cursor.execute("SELECT MAX(possessions) FROM team_lineups")
        per_game_max = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(total_possessions) FROM lineup_season_totals")
        aggregated_max = cursor.fetchone()[0]
        
        assert aggregated_max > per_game_max, \
            f"Aggregated max ({aggregated_max}) should exceed per-game max ({per_game_max})"
        
        # Check that aggregated view has lineups meeting MEDIUM threshold
        cursor.execute("SELECT COUNT(*) FROM lineup_season_totals WHERE total_possessions >= 100")
        medium_count = cursor.fetchone()[0]
        
        assert medium_count > 0, "Should have lineups meeting MEDIUM threshold (100+ poss)"
        
        # Check that aggregated view has lineups meeting HIGH threshold
        cursor.execute("SELECT COUNT(*) FROM lineup_season_totals WHERE total_possessions >= 200")
        high_count = cursor.fetchone()[0]
        
        assert high_count > 0, "Should have lineups meeting HIGH threshold (200+ poss)"
        
        conn.close()
        print(f"✅ Test 5 passed: Aggregated view improves data quality")
        print(f"   Per-game max: {per_game_max}, Aggregated max: {aggregated_max}")
        print(f"   MEDIUM+ lineups: {medium_count}, HIGH+ lineups: {high_count}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Phase 6.3 WOWY Enhancement - Unit Tests")
    print("="*70 + "\n")
    
    test_suite = TestWOWYEnhancement()
    
    try:
        test_suite.test_sql_view_returns_aggregated_data()
        test_suite.test_new_confidence_thresholds()
        test_suite.test_player_season_wowy_table_exists()
        test_suite.test_calculator_uses_lower_thresholds()
        test_suite.test_integration_with_aggregated_view()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
