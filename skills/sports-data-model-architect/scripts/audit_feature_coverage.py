#!/usr/bin/env python3
"""Audit table availability and null coverage for key feature columns."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from typing import Dict, List, Tuple

CHECK_SPEC: Dict[str, List[str]] = {
    "player_game_logs": ["player_id", "game_date", "team_abbreviation"],
    "players": ["player_id", "full_name", "team"],
    "player_canonical_ids": ["canonical_name", "team_abbreviation"],
}


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit feature coverage in a SQLite DB")
    parser.add_argument("--db", default="ludi.db", help="Path to SQLite database")
    args = parser.parse_args()

    try:
        conn = sqlite3.connect(args.db)
    except sqlite3.Error as exc:
        print(f"[error] could not open database '{args.db}': {exc}")
        return 2

    issues: List[Tuple[str, str, str, float]] = []

    with conn:
        for table, columns in CHECK_SPEC.items():
            if not table_exists(conn, table):
                issues.append((table, "table", "missing", 1.0))
                continue

            total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for col in columns:
                if not column_exists(conn, table, col):
                    issues.append((table, col, "missing", 1.0))
                    continue

                if total == 0:
                    issues.append((table, col, "empty_table", 1.0))
                    continue

                nulls = conn.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL"
                ).fetchone()[0]
                ratio = nulls / total
                if ratio > 0.05:
                    issues.append((table, col, "null_ratio_gt_5pct", ratio))

    print("table,column,issue,value")
    for table, col, issue, value in issues:
        print(f"{table},{col},{issue},{value:.4f}")

    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
