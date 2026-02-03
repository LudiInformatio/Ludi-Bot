"""
Test Suite for Phase 6.4: ROLE_CHANGE Detection Handler

Validates Module E's handling of starter elevation and bench demotion
based on RotoWire RSS keyword detection.

Created: Feb 2, 2026
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from module_e import LudiCalibrator


class TestRoleChangeHandler(unittest.TestCase):
    """Test ROLE_CHANGE status handling in Module E"""

    def setUp(self):
        """Initialize calibrator for each test"""
        self.calibrator = LudiCalibrator()

    def test_starter_elevation_boosts_volume(self):
        """
        Test Case 1: Player elevated to starter (depth_order=1)
        Expected: +28% boost to volume stats (8 min / 28 base min)
        """
        # Mock player packet (backup player with 28 min average)
        player_packet = {
            'PLAYER_NAME': 'Test Player',
            'TEAM_ABBREVIATION': 'TOR',
            'MIN': 28,
            'base_pts': 12.0,
            'base_ast': 3.0,
            'base_reb': 5.0,
            'base_fga': 10.0,
            'base_fg3a': 3.0,
            'base_fta': 2.0,
            'base_stl': 1.0,
            'base_blk': 0.5,
            'base_tov': 2.0
        }

        # Mock yak_report with ROLE_CHANGE status
        yak_report = {
            'status': 'ROLE_CHANGE'
        }

        # Mock get_starter_status to return starter=True, depth_order=1
        original_method = self.calibrator.get_starter_status
        def mock_starter_status(player_name, team_abbr):
            return {
                'is_starter': True,
                'depth_order': 1,
                'position': 'PG'
            }
        self.calibrator.get_starter_status = mock_starter_status

        # Run calibration
        result = self.calibrator.calibrate_player(player_packet, yak_report, use_synergy=False)

        # Expected boost: +8 min / 28 base = +28.6% (approximately 1.286 multiplier)
        expected_multiplier = 1 + (8 / 28)

        # Verify FGA boosted correctly
        self.assertAlmostEqual(
            result['proj_fga'],
            10.0 * expected_multiplier,
            places=1,
            msg=f"FGA should be boosted by ~28.6% (expected {10.0 * expected_multiplier:.2f}, got {result['proj_fga']:.2f})"
        )

        # Verify notes updated
        self.assertIn("Elevated to Starter", result['notes'])

        # Restore original method
        self.calibrator.get_starter_status = original_method

    def test_bench_demotion_reduces_volume(self):
        """
        Test Case 2: Player demoted to bench (depth_order>=2)
        Expected: -28% reduction to volume stats (8 min / 28 base min)
        """
        # Mock player packet (starter with 28 min average)
        player_packet = {
            'PLAYER_NAME': 'Test Starter',
            'TEAM_ABBREVIATION': 'BOS',
            'MIN': 28,
            'base_pts': 18.0,
            'base_ast': 5.0,
            'base_reb': 7.0,
            'base_fga': 14.0,
            'base_fg3a': 5.0,
            'base_fta': 4.0,
            'base_stl': 1.5,
            'base_blk': 0.8,
            'base_tov': 3.0
        }

        # Mock yak_report with ROLE_CHANGE status
        yak_report = {
            'status': 'ROLE_CHANGE'
        }

        # Mock get_starter_status to return is_starter=False, depth_order=2
        original_method = self.calibrator.get_starter_status
        def mock_bench_status(player_name, team_abbr):
            return {
                'is_starter': False,
                'depth_order': 2,
                'position': 'SG'
            }
        self.calibrator.get_starter_status = mock_bench_status

        # Run calibration
        result = self.calibrator.calibrate_player(player_packet, yak_report, use_synergy=False)

        # Expected reduction: -8 min / 28 base = -28.6% (approximately 0.714 multiplier)
        expected_multiplier = 1 - (8 / 28)

        # Verify FGA reduced correctly
        self.assertAlmostEqual(
            result['proj_fga'],
            14.0 * expected_multiplier,
            places=1,
            msg=f"FGA should be reduced by ~28.6% (expected {14.0 * expected_multiplier:.2f}, got {result['proj_fga']:.2f})"
        )

        # Verify notes updated
        self.assertIn("Moved to Bench", result['notes'])

        # Restore original method
        self.calibrator.get_starter_status = original_method

    def test_no_adjustment_if_starter_status_unavailable(self):
        """
        Test Case 3: ROLE_CHANGE status but no depth chart data
        Expected: Graceful fallback (no adjustment, no crash)
        """
        # Mock player packet
        player_packet = {
            'PLAYER_NAME': 'Unknown Player',
            'TEAM_ABBREVIATION': 'UNK',
            'MIN': 28,
            'base_pts': 15.0,
            'base_fga': 12.0
        }

        # Mock yak_report with ROLE_CHANGE status
        yak_report = {
            'status': 'ROLE_CHANGE'
        }

        # Mock get_starter_status to return None (no data available)
        original_method = self.calibrator.get_starter_status
        def mock_no_status(player_name, team_abbr):
            return None
        self.calibrator.get_starter_status = mock_no_status

        # Run calibration - should NOT crash
        try:
            result = self.calibrator.calibrate_player(player_packet, yak_report, use_synergy=False)

            # Verify FGA unchanged (no adjustment applied)
            self.assertAlmostEqual(
                result['proj_fga'],
                12.0,
                places=1,
                msg="FGA should remain unchanged when starter status unavailable"
            )

            # Verify no role change note added
            self.assertNotIn("Elevated to Starter", result['notes'])
            self.assertNotIn("Moved to Bench", result['notes'])

            test_passed = True
        except Exception as e:
            test_passed = False
            self.fail(f"Calibration crashed when starter status unavailable: {e}")

        # Restore original method
        self.calibrator.get_starter_status = original_method

        self.assertTrue(test_passed, "Should handle missing starter status gracefully")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("PHASE 6.4: ROLE_CHANGE HANDLER TEST SUITE")
    print("="*60 + "\n")

    # Run tests with verbose output
    unittest.main(verbosity=2)
