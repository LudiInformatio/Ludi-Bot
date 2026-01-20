#!/usr/bin/env python3
"""
Reconcile `players_archived` with `player_canonical_ids_inactive_log`.

Find archived player rows not present in the inactive log, insert missing
log entries (with the archived row JSON) and report counts.

Runs against `ludi.db.test` by default. Safe to run multiple times.
"""

import argparse
import sqlite3
import json
import sys
from typing import List


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_archived_ids(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute("PRAGMA table_info(players_archived)")
    cols = [r[1] for r in cur.fetchall()]
    id_col = 'player_id' if 'player_id' in cols else ('id' if 'id' in cols else None)
    if not id_col:
        raise RuntimeError('players_archived has no id/player_id column')
    cur = conn.execute(f"SELECT {id_col} FROM players_archived")
    return [str(r[0]) for r in cur.fetchall()]


def get_logged_ids(conn: sqlite3.Connection) -> set:
    try:
        cur = conn.execute("SELECT id FROM player_canonical_ids_inactive_log")
    except sqlite3.OperationalError:
        return set()
    return set(str(r[0]) for r in cur.fetchall())


def fetch_archived_row(conn: sqlite3.Connection, id_col: str, val: str) -> sqlite3.Row:
    cur = conn.execute(f"SELECT * FROM players_archived WHERE {id_col} = ? LIMIT 1", (val,))
    return cur.fetchone()


def insert_log_entry(conn: sqlite3.Connection, idv: str, table_name: str, row_json: str):
    conn.execute('INSERT INTO player_canonical_ids_inactive_log (id, table_name, row_json, changed_by) VALUES (?, ?, ?, ?)', (idv, table_name, row_json, 'reconcile-script'))


def main(db_path: str):
    try:
        conn = connect(db_path)
    except Exception as e:
        print('ERROR opening DB:', e)
        return 2

    # Check players_archived exists
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players_archived'")
    if not cur.fetchone():
        print('players_archived table not found in', db_path)
        conn.close()
        return 2

    # Determine id column
    cur = conn.execute("PRAGMA table_info(players_archived)")
    cols = [r[1] for r in cur.fetchall()]
    id_col = 'player_id' if 'player_id' in cols else ('id' if 'id' in cols else None)
    if not id_col:
        print('players_archived has no id column')
        conn.close()
        return 3

    archived_ids = get_archived_ids(conn)
    logged_ids = get_logged_ids(conn)

    missing = [i for i in archived_ids if i not in logged_ids]

    print('archived_count:', len(archived_ids))
    print('logged_count_before:', len(logged_ids))
    print('missing_count:', len(missing))

    inserted = 0
    if missing:
        try:
            conn.execute('BEGIN')
            for idv in missing:
                row = fetch_archived_row(conn, id_col, idv)
                if not row:
                    continue
                rowj = json.dumps(dict(row))
                # defensive: ensure no duplicate
                cur = conn.execute('SELECT 1 FROM player_canonical_ids_inactive_log WHERE id=? AND table_name=? LIMIT 1', (idv, 'players_archived'))
                if cur.fetchone():
                    continue
                insert_log_entry(conn, idv, 'players_archived', rowj)
                inserted += 1
            conn.execute('COMMIT')
        except Exception as e:
            conn.execute('ROLLBACK')
            print('ERROR during insert:', e)
            conn.close()
            return 4

    # Final counts
    final_logged = get_logged_ids(conn)
    print('inserted:', inserted)
    print('logged_count_after:', len(final_logged))

    # Print a few missing samples if any remained
    if len(missing) > 0 and inserted == 0:
        print('No inserts performed; maybe all missing were already logged with different table_name.')

    conn.close()
    return 0


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--db', default='ludi.db.test')
    args = p.parse_args()
    sys.exit(main(args.db))
