-- =========================================================
-- Add Rotation Player Canonical IDs
-- Phase 6.5b Step 5.5 Cleanup
-- Date: February 3, 2026
-- =========================================================
--
-- This script adds canonical IDs for 6 rotation players
-- that were missing from the player_canonical_ids table
--
-- Tier 1: High Priority (3 players, 3,233 total minutes)
-- Tier 2: Medium Priority (3 players, 852 total minutes)
--
-- Total Impact: 4,085 minutes of game time
-- Expected dirty ID reduction: 23 → 17
--
-- =========================================================

-- TIER 1: HIGH PRIORITY ROTATION PLAYERS

-- Nicolas Claxton - Brooklyn Nets (STARTER)
-- Stats: 1,352 minutes across 46 games (29.4 MPG)
INSERT OR REPLACE INTO player_canonical_ids (
    canonical_id,
    full_name,
    normalized_name,
    team,
    position,
    is_active,
    tank01_aliases,
    nba_api_id,
    created_at,
    updated_at
) VALUES (
    '1629651',
    'Nicolas Claxton',
    'nicolas claxton',
    'BKN',
    'C',
    1,
    '["1629651", "28568879869"]',
    '1629651',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Ron Holland II - Detroit Pistons (ROTATION)
-- Stats: 950 minutes across 46 games (20.7 MPG)
INSERT OR REPLACE INTO player_canonical_ids (
    canonical_id,
    full_name,
    normalized_name,
    team,
    position,
    is_active,
    tank01_aliases,
    nba_api_id,
    created_at,
    updated_at
) VALUES (
    '1641705',
    'Ron Holland II',
    'ron holland',
    'DET',
    'F',
    1,
    '["1641705", "942541715989"]',
    '1641705',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Dominick Barlow - Philadelphia 76ers (ROTATION)
-- Stats: 931 minutes across 39 games (23.9 MPG)
INSERT OR REPLACE INTO player_canonical_ids (
    canonical_id,
    full_name,
    normalized_name,
    team,
    position,
    is_active,
    tank01_aliases,
    nba_api_id,
    created_at,
    updated_at
) VALUES (
    '1631112',
    'Dominick Barlow',
    'dominick barlow',
    'PHI',
    'F',
    1,
    '["1631112", "948647045669"]',
    '1631112',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- TIER 2: MEDIUM PRIORITY ROTATION PLAYERS

-- GG Jackson II - Memphis Grizzlies (ROTATION)
-- Stats: 481 minutes across 28 games (17.2 MPG)
INSERT OR REPLACE INTO player_canonical_ids (
    canonical_id,
    full_name,
    normalized_name,
    team,
    position,
    is_active,
    tank01_aliases,
    nba_api_id,
    created_at,
    updated_at
) VALUES (
    '1641712',
    'Gregory Jackson II',
    'gregory jackson',
    'MEM',
    'F',
    1,
    '["1641712", "949540391869", "gg jackson"]',
    '1641712',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Grant Williams - Charlotte Hornets (ROTATION)
-- Stats: 177 minutes across 10 games (17.7 MPG)
-- Note: Coming back from injury, minutes increasing
INSERT OR REPLACE INTO player_canonical_ids (
    canonical_id,
    full_name,
    normalized_name,
    team,
    position,
    is_active,
    tank01_aliases,
    nba_api_id,
    created_at,
    updated_at
) VALUES (
    '1629684',
    'Grant Williams',
    'grant williams',
    'CHA',
    'F',
    1,
    '["1629684", "28698616399"]',
    '1629684',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Nigel Hayes - Phoenix Suns (ROTATION)
-- Stats: 194 minutes across 27 games (7.2 MPG)
INSERT OR REPLACE INTO player_canonical_ids (
    canonical_id,
    full_name,
    normalized_name,
    team,
    position,
    is_active,
    tank01_aliases,
    nba_api_id,
    created_at,
    updated_at
) VALUES (
    '1628388',
    'Nigel Hayes-Davis',
    'nigel hayes',
    'PHO',
    'PF',
    1,
    '["1628388", "28218091429", "nigel hayes davis"]',
    '1628388',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- =========================================================
-- VERIFICATION QUERY
-- Run after executing this script to verify additions:
--
-- sqlite3 ludi.db "SELECT canonical_id, full_name, team, tank01_aliases
--                   FROM player_canonical_ids
--                   WHERE canonical_id IN ('1629651', '1641705', '1631112',
--                                           '1641712', '1629684', '1628388');"
--
-- Expected: 6 rows returned
-- =========================================================
