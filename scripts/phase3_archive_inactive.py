#!/usr/bin/env python3
"""
Script: phase3_archive_inactive.py
- Connects to a SQLite DB (default: ludi.db.test)
- Replaces `players_archived` with rows from `players WHERE is_active=0`
- Prints counts: inactive_players, archived_rows, log_rows
- Prints up to 5 sample `id, player_name` from `players_archived` and up to 5 sample `row_json` from the log

Idempotent and robust: handles missing tables gracefully and exits non-zero on fatal DB errors.
"""

import argparse
import json
import sqlite3
import sys
from typing import List


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def table_count(conn: sqlite3.Connection, table: str) -> int | None:
    try:
        cur = conn.execute(f"SELECT COUNT(*) AS c FROM {table}")
        return int(cur.fetchone()[0])
    except sqlite3.OperationalError:
        return None


def fetch_samples(conn: sqlite3.Connection, query: str, limit: int = 5) -> List[sqlite3.Row]:
    cur = conn.execute(query)
    return cur.fetchmany(limit)


def create_players_archived(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    try:
        cur.execute("DROP TABLE IF EXISTS players_archived")
        cur.execute(
            "CREATE TABLE players_archived AS SELECT * FROM players WHERE is_active=0"
        )
        conn.commit()
    except sqlite3.OperationalError:
        conn.rollback()
        raise


def safe_print_samples_players(rows: List[sqlite3.Row]) -> None:
    if not rows:
        print("(no sample rows found in players_archived)")
        return
    for r in rows:
        rid = r["id"] if "id" in r.keys() else None
        name = r["player_name"] if "player_name" in r.keys() else None
        print(f"- id: {rid!s}, player_name: {name!s}")


def safe_print_samples_log(rows: List[sqlite3.Row]) -> None:
    if not rows:
        print("(no sample rows found in player_canonical_ids_inactive_log)")
        return
    for r in rows:
        val = r[0]
        try:
            parsed = json.loads(val)
            print(json.dumps(parsed, ensure_ascii=False))
        except Exception:
            print(val)


def main():
    parser = argparse.ArgumentParser(description="Archive inactive players into players_archived table")
    parser.add_argument("--db", "-d", default="ludi.db.test", help="Path to SQLite DB (default: ludi.db.test)")
    args = parser.parse_args()

    try:
        conn = connect(args.db)
    except Exception as e:
        print(f"ERROR: could not open database '{args.db}': {e}")
        sys.exit(2)

    try:
        create_players_archived(conn)
    except sqlite3.OperationalError as e:
        print(f"FATAL: database operation failed while creating players_archived: {e}")
        print("Ensure the `players` table exists and has an `is_active` column.")
        conn.close()
        sys.exit(3)

    inactive_count = table_count(conn, "(SELECT 1 FROM players WHERE is_active=0)")
    if inactive_count is None:
        try:
            cur = conn.execute("SELECT COUNT(*) FROM players WHERE is_active=0")
            inactive_count = int(cur.fetchone()[0])
        except sqlite3.OperationalError:
            inactive_count = None

    archived_count = table_count(conn, "players_archived")
    log_count = table_count(conn, "player_canonical_ids_inactive_log")

    print("Counts:")
    print(f"- inactive_players (players WHERE is_active=0): {inactive_count if inactive_count is not None else 'N/A'}")
    print(f"- archived_rows (players_archived): {archived_count if archived_count is not None else 'N/A'}")
    print(f"- log_rows (player_canonical_ids_inactive_log): {log_count if log_count is not None else 'N/A'}")

    print("\nSample players_archived (up to 5 rows):")
    try:
        sample_players = fetch_samples(conn, "SELECT id, player_name FROM players_archived LIMIT 5")
        safe_print_samples_players(sample_players)
    except sqlite3.OperationalError:
        print("(players_archived exists but could not select id/player_name - columns may differ)")
        try:
            sample_any = fetch_samples(conn, "SELECT * FROM players_archived LIMIT 5")
            for r in sample_any:
                print(dict(r))
        except Exception:
            print("(failed to fetch generic samples from players_archived)")

    print("\nSample player_canonical_ids_inactive_log.row_json (up to 5 rows):")
    if log_count is None:
        print("(table player_canonical_ids_inactive_log does not exist)")
    else:
        try:
            sample_log = fetch_samples(conn, "SELECT row_json FROM player_canonical_ids_inactive_log LIMIT 5")
            safe_print_samples_log(sample_log)
        except sqlite3.OperationalError:
            print("(player_canonical_ids_inactive_log exists but `row_json` column not found)")

    conn.close()


if __name__ == '__main__':
    main()
