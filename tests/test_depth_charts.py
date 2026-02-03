#!/usr/bin/env python3
"""
Unit tests for Phase 6.1: Depth Charts Integration

Tests:
1. API fetch returns 30 teams
2. Each team has 5 positions
3. Starters are marked as depth_order=1
4. Database upsert is idempotent
5. Player starter status updated
6. Canonical ID resolution works (placeholder)
7. Dry-run mode doesn't write to database

Run:
    python -m pytest tests/test_depth_charts.py -v

Author: Phase 6.1 Implementation
Date: February 2, 2026
"""

import pytest
import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.sync_depth_charts import DepthChartSync
from module_e import LudiCalibrator

# Use test database
TEST_DB = "test_ludi.db"


@pytest.fixture(scope="module")
def sync_instance():
    """Create DepthChartSync instance with test database"""
    return DepthChartSync(db_path=TEST_DB, verbose=False)


@pytest.fixture(scope="module")
def setup_test_db():
    """Setup test database with schema"""
    # Initialize test database
    conn = sqlite3.connect(TEST_DB, timeout=30)
    cursor = conn.cursor()

    # Create depth_charts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS depth_charts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_abbr TEXT NOT NULL,
            team_id TEXT,
            position TEXT NOT NULL,
            player_name TEXT NOT NULL,
            player_id TEXT,
            depth_order INTEGER NOT NULL,
            synced_at TEXT NOT NULL,
            UNIQUE(team_abbr, position, depth_order)
        )
    ''')

    # Create players table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            player_id TEXT PRIMARY KEY,
            name TEXT,
            team TEXT,
            position TEXT,
            is_starter INTEGER DEFAULT 0
        )
    ''')

    conn.commit()
    conn.close()

    yield

    # Cleanup test database after all tests
    Path(TEST_DB).unlink(missing_ok=True)


def test_fetch_depth_charts_returns_30_teams(sync_instance):
    """Test 1: Verify API returns all 30 NBA teams"""
    result = sync_instance.fetch_depth_charts()

    assert result["success"] is True, "API call should succeed"
    assert result["teams"] == 30, f"Expected 30 teams, got {result['teams']}"
    assert len(result["data"]) == 30, "Data should contain 30 team objects"
    assert len(result["errors"]) == 0, f"Should have no errors, got {result['errors']}"


def test_depth_chart_has_5_positions(sync_instance):
    """Test 2: Each team should have PG, SG, SF, PF, C"""
    result = sync_instance.fetch_depth_charts()

    assert result["success"] is True
    assert len(result["data"]) > 0, "Should have team data"

    # Check first team
    first_team = result["data"][0]
    assert "depthChart" in first_team, "Team should have depthChart"

    depth_chart = first_team["depthChart"]
    positions = set(depth_chart.keys())

    # Should have all 5 positions
    expected_positions = {"PG", "SG", "SF", "PF", "C"}
    assert expected_positions.issubset(positions), \
        f"Expected positions {expected_positions}, got {positions}"


def test_starter_is_depth_order_1(sync_instance, setup_test_db):
    """Test 3: Verify depth_order=1 players are marked as starters"""
    # Fetch and sync depth charts
    depth_data = sync_instance.fetch_depth_charts()
    assert depth_data["success"] is True

    result = sync_instance.sync_to_database(depth_data, dry_run=False)

    assert result["teams_synced"] == 30, "Should sync all 30 teams"
    assert result["starters_identified"] == 150, "Should identify 150 starters (30 teams × 5 positions)"

    # Verify in database
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM depth_charts WHERE depth_order = 1')
    starter_count = cursor.fetchone()[0]

    conn.close()

    assert starter_count == 150, f"Expected 150 starters in DB, got {starter_count}"


def test_database_upsert_idempotent(sync_instance, setup_test_db):
    """Test 4: Running sync twice shouldn't create duplicates"""
    depth_data = sync_instance.fetch_depth_charts()
    assert depth_data["success"] is True

    # First sync
    result1 = sync_instance.sync_to_database(depth_data, dry_run=False)
    players_first = result1["players_updated"]

    # Second sync (should clear and re-insert, not duplicate)
    result2 = sync_instance.sync_to_database(depth_data, dry_run=False)
    players_second = result2["players_updated"]

    # Verify no duplicates
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM depth_charts')
    total_players = cursor.fetchone()[0]

    # Check for UNIQUE constraint violations
    cursor.execute('''
        SELECT team_abbr, position, depth_order, COUNT(*) as cnt
        FROM depth_charts
        GROUP BY team_abbr, position, depth_order
        HAVING cnt > 1
    ''')
    duplicates = cursor.fetchall()

    conn.close()

    assert len(duplicates) == 0, f"Found {len(duplicates)} duplicate entries"
    assert players_second == players_first, "Second sync should insert same number of players"


def test_player_starter_status_updated(sync_instance, setup_test_db):
    """Test 5: Verify players.is_starter column is correctly populated"""
    # Sync depth charts first
    depth_data = sync_instance.fetch_depth_charts()
    sync_instance.sync_to_database(depth_data, dry_run=False)

    # Insert some test players
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    test_players = [
        ("test_id_1", "Stephen Curry", "GS", "PG"),  # Starter
        ("test_id_2", "LeBron James", "LAL", "PF"),  # Starter
        ("test_id_3", "Gabe Vincent", "LAL", "PG"),  # Backup
    ]

    for player in test_players:
        cursor.execute('''
            INSERT OR REPLACE INTO players (player_id, name, team, position, is_starter)
            VALUES (?, ?, ?, ?, 0)
        ''', player)

    conn.commit()
    conn.close()

    # Update starter status
    updated_count = sync_instance.update_player_starter_status()

    # Verify
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    cursor.execute('SELECT name, is_starter FROM players WHERE name IN (?, ?, ?)',
                   ("Stephen Curry", "LeBron James", "Gabe Vincent"))
    results = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    assert results.get("Stephen Curry") == 1, "Stephen Curry should be starter"
    assert results.get("LeBron James") == 1, "LeBron James should be starter"
    assert results.get("Gabe Vincent") == 0, "Gabe Vincent should not be starter"


def test_dry_run_mode(sync_instance, setup_test_db):
    """Test 7: Verify dry-run doesn't write to database"""
    # Clear database
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM depth_charts')
    conn.commit()

    # Count before dry-run
    cursor.execute('SELECT COUNT(*) FROM depth_charts')
    count_before = cursor.fetchone()[0]
    conn.close()

    # Dry-run sync
    depth_data = sync_instance.fetch_depth_charts()
    result = sync_instance.sync_to_database(depth_data, dry_run=True)

    # Count after dry-run
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM depth_charts')
    count_after = cursor.fetchone()[0]
    conn.close()

    assert count_before == count_after == 0, "Dry-run should not write to database"
    assert result["teams_synced"] == 30, "Dry-run should still process all teams"


def test_module_e_integration():
    """Test 6: Module E depth chart methods work"""
    # Use production database for this test (it has data from sync)
    calib = LudiCalibrator(db_path='ludi.db')

    # Test get_starter_status
    curry_status = calib.get_starter_status("Stephen Curry")
    assert curry_status is not None, "Should find Stephen Curry"
    assert curry_status["is_starter"] is True, "Curry should be a starter"
    assert curry_status["position"] in ["PG", "SG"], "Curry should be guard"

    # Test get_backup_at_position
    lal_pg2 = calib.get_backup_at_position("LAL", "PG", depth=2)
    assert lal_pg2 is not None, "LAL should have PG2"
    assert lal_pg2["depth_order"] == 2, "Should be depth order 2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
