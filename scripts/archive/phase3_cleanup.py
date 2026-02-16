"""
Phase 3: Duplicate discovery and reversible migration SQL generator

Usage:
  python3 scripts/phase3_cleanup.py --db ludi.db.test

Outputs (written to repo root):
  - duplicates.csv     (dry-run list of player_name groups with >1 ID)
  - keepers.csv        (chosen keeper per group based on completeness rule)
  - migration.sql      (DDL for log table + commented UPDATE/INSERT statements)

This script is intentionally conservative: it does discovery and generates SQL
that is commented out. It will only write UPDATE statements if `--apply` is
passed (not recommended without manual review).

Author: GitHub Copilot (acting as project PM/lead dev)
"""
import argparse
import sqlite3
import csv
import json
import os
from collections import defaultdict

TABLES_TO_SCAN = [
    'player_canonical_ids',
    'players',
    'player_game_tracking',
    'player_game_logs',
]

OUT_DUP = 'duplicates.csv'
OUT_KEEP = 'keepers.csv'
OUT_SQL = 'migration.sql'

def get_tables(conn):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return set(r[0] for r in cur.fetchall())

def get_columns(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]

def pick_name_col(cols):
    # prefer explicit player_name-like columns
    c = [x for x in cols if 'player' in x.lower() and 'name' in x.lower()]
    if c:
        return c[0]
    c = [x for x in cols if x.lower() in ('name','player_name','PLAYER_NAME')]
    if c:
        return c[0]
    # fallback any column with 'name'
    c = [x for x in cols if 'name' in x.lower()]
    return c[0] if c else None

def pick_id_cols(cols):
    # return list of plausible id cols ordered by preference
    candidates = []
    for x in cols:
        l = x.lower()
        if 'nba' in l and 'id' in l:
            candidates.insert(0,x)
        elif 'canonical' in l and 'id' in l:
            candidates.insert(0,x)
        elif 'slug' in l or 'player_id' in l or l== 'id' or l.endswith('_id'):
            candidates.append(x)
    return candidates

def row_nonnull_count(row):
    return sum(1 for v in row if v is not None)

def main(db_path, apply_changes=False):
    if not os.path.exists(db_path):
        print('ERROR: DB not found:', db_path)
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    tables_present = get_tables(conn)

    collected = defaultdict(lambda: defaultdict(set))
    sources = defaultdict(set)

    for t in TABLES_TO_SCAN:
        if t not in tables_present:
            continue
        cols = get_columns(conn, t)
        name_col = pick_name_col(cols)
        id_cols = pick_id_cols(cols)
        if not name_col or not id_cols:
            continue
        id_col = id_cols[0]
        cur = conn.execute(f"SELECT DISTINCT {name_col} AS name, {id_col} AS id FROM {t} WHERE {name_col} IS NOT NULL AND {id_col} IS NOT NULL")
        for r in cur.fetchall():
            name = r['name']
            idv = str(r['id'])
            collected[name]['ids'].add(idv)
            collected[name]['sources'].add(f"{t}:{id_col}")

    # filter duplicates
    duplicates = {name: {'ids': list(v['ids']), 'sources': list(v['sources'])} for name, v in collected.items() if len(v['ids'])>1}

    # write duplicates.csv
    with open(OUT_DUP, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['player_name','id_count','ids','sources'])
        for name, info in sorted(duplicates.items()):
            w.writerow([name, len(info['ids']), ';'.join(info['ids']), ';'.join(info['sources'])])

    # For each duplicate group, choose keeper by completeness using `players` table where possible
    keepers = []
    for name, info in sorted(duplicates.items()):
        ids = info['ids']
        best = None
        best_score = -1
        best_row = None
        # try to find rows in players table
        if 'players' in tables_present:
            cols = get_columns(conn, 'players')
            # find id-like columns in players
            player_id_cols = pick_id_cols(cols)
            name_col_player = pick_name_col(cols)
            # we'll attempt to match any id value against any id-like column
            for idv in ids:
                # build OR conditions
                conds = []
                params = []
                for c in player_id_cols:
                    conds.append(f"CAST({c} AS TEXT)=?")
                    params.append(idv)
                if name_col_player:
                    q = f"SELECT * FROM players WHERE ({' OR '.join(conds)}) AND ({name_col_player}=?) LIMIT 1"
                    cur = conn.execute(q, params + [name])
                else:
                    q = f"SELECT * FROM players WHERE ({' OR '.join(conds)}) LIMIT 1"
                    cur = conn.execute(q, params)
                row = cur.fetchone()
                if row:
                    score = sum(1 for v in row if v is not None)
                    if score > best_score:
                        best = idv
                        best_score = score
                        best_row = dict(row)
        # fallback rules
        if best is None:
            # prefer id that looks numeric (likely NBA ID)
            numeric_ids = [i for i in ids if i.isdigit()]
            if numeric_ids:
                best = numeric_ids[0]
            else:
                best = ids[0]
        keepers.append({'player_name':name, 'keeper_id':best, 'ids':ids, 'best_score':best_score, 'sample_row': best_row})

    with open(OUT_KEEP, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['player_name','keeper_id','ids','best_score'])
        for k in keepers:
            w.writerow([k['player_name'], k['keeper_id'], ';'.join(k['ids']), k['best_score']])

    # Prepare migration SQL (dry-run): create log table and generate UPDATEs for non-keepers
    with open(OUT_SQL, 'w', encoding='utf-8') as f:
        f.write('-- Migration SQL for marking duplicate canonical/player records inactive\\n')
        f.write('-- Review `keepers.csv` before executing. This file intentionally comments out UPDATEs.\\n')
        f.write('BEGIN TRANSACTION;\\n')
        # log table DDL
        f.write('CREATE TABLE IF NOT EXISTS player_canonical_ids_inactive_log (\\\\n')
        f.write('  id TEXT PRIMARY KEY,\\\\n')
        f.write('  table_name TEXT,\\\\n')
        f.write('  row_json TEXT,\\\\n')
        f.write('  changed_at TEXT DEFAULT (datetime("now")),\\\\n')
        f.write('  changed_by TEXT\\\\n')
        f.write(');\\n')
        # statements per duplicate group
        for k in keepers:
            name = k['player_name']
            keeper = k['keeper_id']
            for idv in k['ids']:
                if idv == keeper:
                    continue
                # decide target table: prefer player_canonical_ids if present
                if 'player_canonical_ids' in tables_present:
                    target = 'player_canonical_ids'
                    id_col_candidates = pick_id_cols(get_columns(conn, target))
                    id_col = id_col_candidates[0] if id_col_candidates else 'id'
                    f.write(f"-- group: {name} will keep {keeper}; marking {idv} inactive in {target}\\n")
                    f.write(f"-- INSERT INTO player_canonical_ids_inactive_log (id, table_name, row_json, changed_by) SELECT {id_col}::TEXT, '{target}', json(CAST(rowid AS TEXT) || ' replacement'), 'phase3-script' FROM {target} WHERE CAST({id_col} AS TEXT)='{idv}';\\n")
                    f.write(f"-- UPDATE {target} SET is_active = 0 WHERE CAST({id_col} AS TEXT)='{idv}';\\n")
                elif 'players' in tables_present:
                    target = 'players'
                    id_col_candidates = pick_id_cols(get_columns(conn, target))
                    id_col = id_col_candidates[0] if id_col_candidates else 'player_id'
                    f.write(f"-- group: {name} will keep {keeper}; marking {idv} inactive in {target}\\n")
                    # build json_object column pairs safely
                    cols = get_columns(conn, target)
                    col_pairs = ", ".join([f"'{c}', {c}" for c in cols])
                    f.write(f"-- INSERT INTO player_canonical_ids_inactive_log (id, table_name, row_json, changed_by) SELECT CAST({id_col} AS TEXT), '{target}', json_object({col_pairs}), 'phase3-script' FROM {target} WHERE CAST({id_col} AS TEXT)='{idv}';\\n")
                    f.write(f"-- UPDATE {target} SET is_active = 0 WHERE CAST({id_col} AS TEXT)='{idv}';\\n")
                else:
                    f.write(f"-- No suitable target table found to mark {idv} inactive for {name}. Manual action required.\n")
        f.write('COMMIT;\n')

    print('Done. Outputs: ', OUT_DUP, OUT_KEEP, OUT_SQL)
    conn.close()
    return 0

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--db', default='ludi.db', help='Path to sqlite DB (default: ludi.db)')
    p.add_argument('--apply', action='store_true', help='Apply generated UPDATEs (not recommended without review)')
    args = p.parse_args()
    exit(main(args.db, args.apply))
