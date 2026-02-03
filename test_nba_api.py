#!/usr/bin/env python3
"""
Quick test script for NBA API V3 referee extraction.
Verifies boxscoresummaryv3 endpoint works correctly.
"""

from nba_api.stats.endpoints import boxscoresummaryv3

def test_v3_officials():
    """Test V3 API officials extraction."""
    # Use recent game ID (adjust as needed for current season)
    test_game_id = "0022500010"

    print(f"Testing BoxScoreSummaryV3 with game_id: {test_game_id}")

    try:
        box = boxscoresummaryv3.BoxScoreSummaryV3(game_id=test_game_id)
        data = box.get_dict()

        officials = data.get('boxScoreSummary', {}).get('officials', [])

        if not officials:
            print("❌ No officials data found")
            return False

        print(f"✅ Found {len(officials)} officials:")
        for official in officials:
            name = official.get('name', 'Unknown')
            jersey = official.get('jerseyNum', 'N/A')
            assignment = official.get('assignment', 'N/A')
            print(f"   - {name} (#{jersey}, {assignment})")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_v3_officials()
    exit(0 if success else 1)
