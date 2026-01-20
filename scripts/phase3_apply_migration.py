"""
Apply reversible Phase 3 migration on a target SQLite DB.

Usage:
  python3 scripts/phase3_apply_migration.py --db ludi.db.test

This script:
 - Reads `keepers.csv` (must exist in repo root).
 - For each non-keeper id in a group, finds matching rows in
   `player_canonical_ids` or `players` and sets `is_active=0`.
 - Inserts the pre-change row JSON into `player_canonical_ids_inactive_log`.
 - Operates inside a transaction and prints a summary.

SAFE: run against `ludi.db.test` first. Changes are irreversible except by
restoring the DB backup or using the log table contents.
"""
import argparse
import sqlite3
import csv
import json
import os
from collections import defaultdict


def get_tables(conn):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return set(r[0] for r in cur.fetchall())


def get_columns(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]


def pick_id_cols(cols):
    candidates = []
    for x in cols:
        l = x.lower()
        if 'nba' in l and 'id' in l:
            candidates.insert(0, x)
        elif 'canonical' in l and 'id' in l:
            candidates.insert(0, x)
        elif 'slug' in l or 'player_id' in l or l == 'id' or l.endswith('_id'):
            candidates.append(x)
    return candidates


def row_to_dict(cur, row):
    return {k[0]: row[idx] for idx, k in enumerate(cur.description)}


def main(db_path, dry_run=False):
    if not os.path.exists('keepers.csv'):
        print('keepers.csv not found in repo root. Run discovery first.')
        return 2
    if not os.path.exists(db_path):
        print('DB not found:', db_path)
        return 2

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables = get_tables(conn)

    # Ensure log table exists
    cur.execute('''
    CREATE TABLE IF NOT EXISTS player_canonical_ids_inactive_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        id TEXT,
        table_name TEXT,
        row_json TEXT,
        changed_at TEXT DEFAULT (datetime('now')),
        changed_by TEXT
    )
    ''')
    conn.commit()

    # Load keepers
    keepers = []
    with open('keepers.csv', newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            ids = [i for i in (row.get('ids') or '').split(';') if i]
            keepers.append({'player_name': row.get('player_name'), 'keeper': row.get('keeper_id'), 'ids': ids})

    total_marked = 0
    details = []

    try:
        cur.execute('BEGIN')
        for g in keepers:
            keeper = g['keeper']
            for idv in g['ids']:
                if idv == keeper:
                    continue
                applied = False

                # Try player_canonical_ids
                if 'player_canonical_ids' in tables:
                    cols = get_columns(conn, 'player_canonical_ids')
                    id_cols = pick_id_cols(cols)
                    if id_cols:
                        id_col = id_cols[0]
                        cur.execute(f"SELECT * FROM player_canonical_ids WHERE CAST({id_col} AS TEXT)=?", (idv,))
                        row = cur.fetchone()
                        if row:
                            rowj = json.dumps(dict(row))
                            if not dry_run:
                                cur.execute('INSERT INTO player_canonical_ids_inactive_log (id, table_name, row_json, changed_by) VALUES (?, ?, ?, ?)', (idv, 'player_canonical_ids', rowj, 'phase3-script'))
                                cur.execute(f"UPDATE player_canonical_ids SET is_active = 0 WHERE CAST({id_col} AS TEXT)=?", (idv,))
                            total_marked += 1
                            details.append((g['player_name'], 'player_canonical_ids', idv))
                            applied = True

                # Try players table (may have multiple rows)
                if not applied and 'players' in tables:
                    cols = get_columns(conn, 'players')
                    id_cols = pick_id_cols(cols)
                    for c in id_cols:
                        cur.execute(f"SELECT * FROM players WHERE CAST({c} AS TEXT)=?", (idv,))
                        rows = cur.fetchall()
                        if rows:
                            for row in rows:
                                rowj = json.dumps(dict(row))
                                if not dry_run:
                                    cur.execute('INSERT INTO player_canonical_ids_inactive_log (id, table_name, row_json, changed_by) VALUES (?, ?, ?, ?)', (idv, 'players', rowj, 'phase3-script'))
                                    cur.execute(f"UPDATE players SET is_active = 0 WHERE CAST({c} AS TEXT)=?", (idv,))
                                total_marked += 1
                                details.append((g['player_name'], 'players', idv))
                            applied = True
                            break

                # If not applied, note it
                if not applied:
                    details.append((g['player_name'], 'NOT_FOUND', idv))

        if dry_run:
            cur.execute('ROLLBACK')
            print('Dry-run complete. No changes applied.')
        else:
            cur.execute('COMMIT')
            print('Migration applied on', db_path)

    except Exception as e:
        cur.execute('ROLLBACK')
        print('ERROR during migration:', e)
        return 3
    finally:
        conn.close()

    # Summary
    found_count = sum(1 for d in details if d[1] != 'NOT_FOUND')
    not_found = [d for d in details if d[1] == 'NOT_FOUND']
    print('Total ids processed:', sum(len(g['ids']) - (1 if g['keeper'] in g['ids'] else 0) for g in keepers))
    print('Total marked inactive:', total_marked)
    print('Records not found (sample up to 20):')
    for i, nf in enumerate(not_found[:20], 1):
        print(i, nf)

    return 0


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--db', default='ludi.db.test')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    exit(main(args.db, dry_run=args.dry_run))
