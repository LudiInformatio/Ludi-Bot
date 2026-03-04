# ARCHIVED: 2026-03-03 — One-off exploratory audit
#!/usr/bin/env python3
"""Run temporal integrity checks for common sports analytics tables in SQLite."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from typing import List, Tuple


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def run_checks(conn: sqlite3.Connection) -> List[Tuple[str, str, int]]:
    checks: List[Tuple[str, str, int]] = []

    if table_exists(conn, "player_game_logs"):
        if column_exists(conn, "player_game_logs", "game_date"):
            c = conn.execute(
                "SELECT COUNT(*) FROM player_game_logs WHERE date(game_date) > date('now')"
            ).fetchone()[0]
            checks.append(("future_game_dates", "critical", c))

        needed = ["player_id", "game_date"]
        if all(column_exists(conn, "player_game_logs", col) for col in needed):
            c = conn.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT player_id, game_date, COUNT(*) cnt
                    FROM player_game_logs
                    GROUP BY player_id, game_date
                    HAVING COUNT(*) > 1
                )
                """
            ).fetchone()[0]
            checks.append(("duplicate_player_game_rows", "high", c))

        if column_exists(conn, "player_game_logs", "team_abbreviation"):
            c = conn.execute(
                """
                SELECT COUNT(*)
                FROM player_game_logs
                WHERE team_abbreviation IS NULL
                   OR trim(team_abbreviation) = ''
                   OR team_abbreviation = 'XXX'
                """
            ).fetchone()[0]
            checks.append(("invalid_team_abbreviation_rows", "high", c))
    else:
        checks.append(("missing_table_player_game_logs", "critical", 1))

    if table_exists(conn, "player_props_log"):
        if all(
            column_exists(conn, "player_props_log", col)
            for col in ("created_at", "game_date")
        ):
            c = conn.execute(
                """
                SELECT COUNT(*)
                FROM player_props_log
                WHERE datetime(created_at) > datetime(game_date || ' 23:59:59')
                """
            ).fetchone()[0]
            checks.append(("post_game_logged_props", "medium", c))

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit temporal integrity in a SQLite DB")
    parser.add_argument("--db", default="ludi.db", help="Path to SQLite database")
    args = parser.parse_args()

    try:
        conn = sqlite3.connect(args.db)
    except sqlite3.Error as exc:
        print(f"[error] could not open database '{args.db}': {exc}")
        return 2

    with conn:
        checks = run_checks(conn)

    print("check,severity,count")
    for name, severity, count in checks:
        print(f"{name},{severity},{count}")

    critical_total = sum(c for _, sev, c in checks if sev == "critical")
    return 1 if critical_total > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
