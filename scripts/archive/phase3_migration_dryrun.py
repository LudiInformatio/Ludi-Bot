#!/usr/bin/env python3
"""
Run a dry-run of `migration_enable.sql` against a DB by computing counts
of rows that would be inserted/updated, without making changes.

Outputs:
 - count of players that would be marked inactive
 - count of missing log inserts that would be created from `players_archived`
"""
import sqlite3
import sys
from pathlib import Path


def main(db='ludi.db.test'):
    p = Path(db)
    if not p.exists():
        print('DB not found:', db); return 2
    conn = sqlite3.connect(db)
    cur = conn.cursor()

    # Check players_archived
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players_archived'")
    if not cur.fetchone():
        print('players_archived not present — cannot compute dry-run'); return 3

    # Count missing log entries
    cur.execute('SELECT COUNT(*) FROM players_archived pa LEFT JOIN player_canonical_ids_inactive_log l ON CAST(l.id AS TEXT)=CAST(pa.player_id AS TEXT) WHERE l.id IS NULL')
    missing_log = cur.fetchone()[0]

    # Count active players that would be marked inactive
    cur.execute('SELECT COUNT(*) FROM players WHERE is_active=1 AND CAST(player_id AS TEXT) IN (SELECT id FROM player_canonical_ids_inactive_log)')
    to_mark = cur.fetchone()[0]

    print('dry-run counts: missing_log_inserts=', missing_log, 'players_to_mark_inactive=', to_mark)
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
