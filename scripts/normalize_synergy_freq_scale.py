#!/usr/bin/env python3
"""
Normalize player_synergy_playtypes.freq_pct to canonical 0-100 scale.

Heuristic:
- For rows with 0 < freq_pct < 1.0, treat as proportions and multiply by 100.
"""

import argparse
import sqlite3


DB_PATH = "ludi.db"
SEASON = "2025-26"


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000;")
    return conn


def _count_candidates(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM player_synergy_playtypes
        WHERE season = ?
          AND freq_pct > 0
          AND freq_pct < 1.0
        """,
        (SEASON,),
    )
    return int(cur.fetchone()[0])


def _preview_by_playtype(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT playtype, COUNT(*) AS c, MIN(freq_pct), MAX(freq_pct)
        FROM player_synergy_playtypes
        WHERE season = ?
          AND freq_pct > 0
          AND freq_pct < 1.0
        GROUP BY playtype
        ORDER BY c DESC
        """,
        (SEASON,),
    )
    return cur.fetchall()


def _apply(conn):
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE player_synergy_playtypes
        SET freq_pct = ROUND(freq_pct * 100.0, 4)
        WHERE season = ?
          AND freq_pct > 0
          AND freq_pct < 1.0
        """,
        (SEASON,),
    )
    conn.commit()
    return cur.rowcount


def main():
    parser = argparse.ArgumentParser(description="Normalize synergy freq_pct scale")
    parser.add_argument("--apply", action="store_true", help="Apply UPDATE (default is dry-run)")
    args = parser.parse_args()

    conn = _connect()
    candidates = _count_candidates(conn)
    print(f"Rows needing normalization (0<freq_pct<1): {candidates}")
    for playtype, c, min_v, max_v in _preview_by_playtype(conn):
        print(f"- {playtype}: {c} rows (min={min_v:.4f}, max={max_v:.4f})")

    if args.apply and candidates > 0:
        updated = _apply(conn)
        print(f"Updated rows: {updated}")
    elif args.apply:
        print("No rows updated.")
    else:
        print("Dry-run only. Re-run with --apply to update.")

    conn.close()


if __name__ == "__main__":
    main()
