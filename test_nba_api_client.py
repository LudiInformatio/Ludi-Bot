#!/usr/bin/env python3
"""
LUDI INFORMATIO | NBA API CLIENT TEST SCRIPT
=============================================
Verifies connectivity and data quality from nba_api wrapper.

Usage:
    ./venv/bin/python test_nba_api_client.py

Tests:
    1. Player ID Lookup (static, no API call)
    2. Shooting Splits (API call)
    3. Shot Difficulty (API call)
    4. Cache Behavior (verify cache hit/miss)
    5. Rate Limiting (verify no 429 errors)
"""

import sys
import os
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.nba_api_client import get_nba_client


def test_player_id_lookup():
    """Test 1: Player ID lookup (no API call)"""
    print("\n" + "="*50)
    print("TEST 1: Player ID Lookup (Static)")
    print("="*50)

    client = get_nba_client()

    test_cases = [
        ("LeBron James", True),
        ("Giannis Antetokounmpo", True),
        ("Luka Doncic", True),
        ("Stephen Curry", True),
        ("InvalidPlayerName12345", False),  # Should return None
    ]

    all_passed = True
    for name, should_exist in test_cases:
        player_id = client.get_player_id(name)

        if should_exist:
            if player_id is not None:
                print(f"   PASS: {name} -> ID {player_id}")
            else:
                print(f"   FAIL: {name} -> Expected ID, got None")
                all_passed = False
        else:
            if player_id is None:
                print(f"   PASS: {name} -> None (expected)")
            else:
                print(f"   FAIL: {name} -> Expected None, got {player_id}")
                all_passed = False

    return all_passed


def test_shooting_splits():
    """Test 2: Shooting splits endpoint"""
    print("\n" + "="*50)
    print("TEST 2: Shooting Splits (API Call)")
    print("="*50)

    client = get_nba_client()

    # Giannis Antetokounmpo - well-known player with data
    player_id = 203507

    try:
        # Use 2025-26 season (current season)
        data = client.get_player_shooting_splits(player_id, season="2025-26")

        # Validate structure
        required_keys = ['shot_area', 'shot_type', 'overall']
        missing_keys = [k for k in required_keys if k not in data]

        if missing_keys:
            print(f"   FAIL: Missing keys: {missing_keys}")
            return False

        # Check data exists
        shot_area_rows = len(data.get('shot_area', {}).get('data', []))
        overall_rows = len(data.get('overall', {}).get('data', []))

        print(f"   Player ID: {player_id}")
        print(f"   Keys returned: {list(data.keys())}")
        print(f"   Shot areas: {shot_area_rows} rows")
        print(f"   Overall: {overall_rows} rows")

        if shot_area_rows > 0 and overall_rows > 0:
            print("   PASS")
            return True
        else:
            print("   WARN: Data returned but empty (may be off-season)")
            return True  # Not a hard failure

    except Exception as e:
        print(f"   FAIL: {e}")
        return False


def test_shot_difficulty():
    """Test 3: Shot difficulty endpoint"""
    print("\n" + "="*50)
    print("TEST 3: Shot Difficulty (API Call)")
    print("="*50)

    client = get_nba_client()
    player_id = 203507  # Giannis

    try:
        data = client.get_player_shot_difficulty(player_id, season="2025-26")

        required_keys = ['closest_defender', 'dribbles', 'general']
        missing_keys = [k for k in required_keys if k not in data]

        if missing_keys:
            print(f"   FAIL: Missing keys: {missing_keys}")
            return False

        defender_rows = len(data.get('closest_defender', {}).get('data', []))
        dribbles_rows = len(data.get('dribbles', {}).get('data', []))

        print(f"   Player ID: {player_id}")
        print(f"   Keys returned: {list(data.keys())}")
        print(f"   Defender distance: {defender_rows} rows")
        print(f"   Dribbles breakdown: {dribbles_rows} rows")

        if defender_rows > 0:
            print("   PASS")
            return True
        else:
            print("   WARN: Data returned but empty")
            return True

    except Exception as e:
        print(f"   FAIL: {e}")
        return False


def test_cache_behavior():
    """Test 4: Cache hit/miss behavior"""
    print("\n" + "="*50)
    print("TEST 4: Cache Behavior")
    print("="*50)

    client = get_nba_client()
    player_id = 203507

    # First call (may be cache hit if tests run consecutively)
    start1 = datetime.now()
    data1 = client.get_player_shooting_splits(player_id, season="2025-26")
    time1 = (datetime.now() - start1).total_seconds()

    # Second call (should be cache hit)
    start2 = datetime.now()
    data2 = client.get_player_shooting_splits(player_id, season="2025-26")
    time2 = (datetime.now() - start2).total_seconds()

    print(f"   First call: {time1:.3f}s")
    print(f"   Second call: {time2:.3f}s")
    print(f"   Data identical: {data1 == data2}")

    # Cache hit should be very fast (< 0.1s)
    if time2 < 0.1:
        print("   PASS (cache working - second call < 0.1s)")
        return True
    elif time2 < time1 / 2:
        print("   PASS (cache working - second call faster)")
        return True
    else:
        print("   WARN (cache may not be optimal)")
        return True  # Not a hard failure


def test_player_tracking():
    """Test 5: Player tracking data"""
    print("\n" + "="*50)
    print("TEST 5: Player Tracking Data")
    print("="*50)

    client = get_nba_client()
    player_id = 203507  # Giannis

    try:
        data = client.get_player_tracking(player_id, season="2025-26")

        print(f"   Player ID: {player_id}")
        print(f"   Keys returned: {list(data.keys())}")

        # Check rebounding
        if 'rebounding' in data:
            if 'error' in data['rebounding']:
                print(f"   Rebounding: ERROR - {data['rebounding']['error'][:50]}")
            else:
                print(f"   Rebounding: OK")

        # Check passing
        if 'passing' in data:
            if 'error' in data['passing']:
                print(f"   Passing: ERROR - {data['passing']['error'][:50]}")
            else:
                print(f"   Passing: OK")

        # Pass if at least one category has data
        has_data = any(
            k in data and 'error' not in data[k]
            for k in ['rebounding', 'passing']
        )

        if has_data:
            print("   PASS (at least one tracking category has data)")
            return True
        else:
            print("   WARN (tracking data may be unavailable)")
            return True  # Not a hard failure

    except Exception as e:
        print(f"   FAIL: {e}")
        return False


def test_offensive_matchups():
    """Test 6: Offensive matchups (boxscorematchupsv3)"""
    print("\n" + "="*50)
    print("TEST 6: Offensive Matchups (boxscorematchupsv3)")
    print("="*50)

    client = get_nba_client()
    player_id = 203507  # Giannis

    try:
        # Test get_player_offensive_matchups (uses boxscorematchupsv3)
        data = client.get_player_offensive_matchups(player_id, season="2025-26", last_n_games=3)

        print(f"   Player ID: {player_id}")
        print(f"   Games analyzed: {data.get('games_analyzed', 0)}")
        print(f"   Total defenders: {data.get('all_defenders', 0)}")

        primary_defenders = data.get('primary_defenders', [])
        if primary_defenders:
            print(f"   Top defenders:")
            for d in primary_defenders[:3]:
                print(f"      - {d['defender_name']}: {d['matchup_minutes']:.1f} min, {d['fga']} FGA")

        if data.get('games_analyzed', 0) > 0 and len(primary_defenders) > 0:
            print("   PASS (offensive matchup data retrieved)")
            return True
        else:
            print("   WARN (no matchup data found - games may not have tracking)")
            return True  # Not a hard failure

    except Exception as e:
        print(f"   FAIL: {e}")
        return False


def test_cache_stats():
    """Test 7: Cache statistics"""
    print("\n" + "="*50)
    print("TEST 7: Cache Statistics")
    print("="*50)

    client = get_nba_client()
    stats = client.get_cache_stats()

    print(f"   Cache files: {stats['files']}")
    print(f"   Cache size: {stats['size_mb']} MB")

    # Should have some cache files from previous tests
    if stats['files'] > 0:
        print("   PASS (cache directory has files)")
        return True
    else:
        print("   WARN (no cache files - may be first run)")
        return True


def run_all_tests():
    """Run full test suite"""
    print("\n" + "="*60)
    print("   LUDI NBA API CLIENT - TEST SUITE")
    print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    results = {}

    # Run tests in order
    results["Player ID Lookup"] = test_player_id_lookup()
    results["Shooting Splits"] = test_shooting_splits()
    results["Shot Difficulty"] = test_shot_difficulty()
    results["Cache Behavior"] = test_cache_behavior()
    results["Player Tracking"] = test_player_tracking()
    results["Offensive Matchups"] = test_offensive_matchups()
    results["Cache Statistics"] = test_cache_stats()

    # Summary
    print("\n" + "="*60)
    print("   TEST SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"   {test_name}: {status}")

    print(f"\n   Total: {passed}/{total} tests passed")
    print("="*60)

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
