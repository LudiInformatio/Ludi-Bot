#!/usr/bin/env python3
"""
Audit archived rows vs inactive log and produce `phase3_mismatches.csv`.

Outputs:
 - prints counts
 - writes CSV with columns: id, archived_json, log_json
"""
import sqlite3
import json
import csv
import sys
from pathlib import Path


def main(db='ludi.db.test'):
    p = Path(db)
    if not p.exists():
        print('DB not found:', db); return 2
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Ensure players_archived and log exist
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players_archived'")
    if not cur.fetchone():
        print('players_archived not found'); return 3
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_canonical_ids_inactive_log'")
    if not cur.fetchone():
        print('player_canonical_ids_inactive_log not found'); return 4

    # Determine id column in players_archived
    cur.execute("PRAGMA table_info(players_archived)")
    cols = [r[1] for r in cur.fetchall()]
    id_col = 'player_id' if 'player_id' in cols else ('id' if 'id' in cols else None)
    if not id_col:
        print('no id column in players_archived'); return 5

    # Build mapping
    archived = {}
    for r in conn.execute(f"SELECT * FROM players_archived"):
        archived[str(r[id_col])] = dict(r)

    logged = {}
    for r in conn.execute("SELECT id, row_json FROM player_canonical_ids_inactive_log"):
        logged[str(r['id'])] = r['row_json']

    archived_ids = set(archived.keys())
    logged_ids = set(logged.keys())

    only_archived = sorted(archived_ids - logged_ids)
    only_logged = sorted(logged_ids - archived_ids)
    both = sorted(archived_ids & logged_ids)

    mismatches = []
    for i in both:
        arch = archived[i]
        logj = logged[i]
        try:
            log_row = json.loads(logj)
        except Exception:
            log_row = None
        if log_row != arch:
            mismatches.append((i, json.dumps(arch, ensure_ascii=False), logj))

    out = Path('phase3_mismatches.csv')
    with out.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['id','archived_json','log_json'])
        for row in mismatches:
            w.writerow(row)

    print('counts: archived_total=', len(archived_ids), 'logged_total=', len(logged_ids))
    print('only_archived=', len(only_archived), 'only_logged=', len(only_logged), 'mismatches=', len(mismatches))
    if mismatches:
        print('Wrote', out)

    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
