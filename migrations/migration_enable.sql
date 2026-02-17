-- migration_enable.sql
-- Phase 3 production migration SQL (idempotent)
-- WARNING: Back up your DB before running. Designed to be safe when run once.

PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;

-- Ensure inactive log exists
CREATE TABLE IF NOT EXISTS player_canonical_ids_inactive_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT,
    table_name TEXT,
    row_json TEXT,
    changed_at TEXT DEFAULT (datetime('now')),
    changed_by TEXT
);

-- Insert missing log entries for any players currently active but identified in players_archived
-- (This assumes `players_archived` exists in the DB and contains authoritative rows.)
INSERT INTO player_canonical_ids_inactive_log (id, table_name, row_json, changed_by)
SELECT pa.player_id, 'players_archived', json_object(), 'migration-enable'
FROM players_archived pa
LEFT JOIN player_canonical_ids_inactive_log l ON CAST(l.id AS TEXT)=CAST(pa.player_id AS TEXT)
WHERE l.id IS NULL;

-- Mark players inactive where their id is present in the inactive log
UPDATE players
SET is_active = 0, updated_at = CURRENT_TIMESTAMP
WHERE CAST(player_id AS TEXT) IN (SELECT id FROM player_canonical_ids_inactive_log)
  AND is_active = 1;

COMMIT;
PRAGMA foreign_keys=ON;

-- Verification queries (run after applying):
-- SELECT COUNT(*) FROM players WHERE is_active=1; -- should be ~500
-- SELECT COUNT(*) FROM players WHERE is_active=0; -- should be ~1460
