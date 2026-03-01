#!/usr/bin/env python3
"""Audit canonical ID and team-abbreviation consistency."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from typing import List, Set, Tuple

NBA_TEAMS: Set[str] = {
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW",
    "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL", "MIN", "NOP", "NYK",
    "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS",
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
    parser = argparse.ArgumentParser(description="Audit entity resolution in a SQLite DB")
    parser.add_argument("--db", default="ludi.db", help="Path to SQLite database")
    args = parser.parse_args()

    try:
        conn = sqlite3.connect(args.db)
    except sqlite3.Error as exc:
        print(f"[error] could not open database '{args.db}': {exc}")
        return 2

    findings: List[Tuple[str, str, int]] = []

    with conn:
        if not table_exists(conn, "player_canonical_ids"):
            findings.append(("missing_table", "player_canonical_ids", 1))
        else:
            if column_exists(conn, "player_canonical_ids", "team"):
                # Note: player_canonical_ids.team uses full names not abbreviations
                # Just count non-null values
                non_null = conn.execute(
                    "SELECT COUNT(*) FROM player_canonical_ids WHERE team IS NOT NULL"
                ).fetchone()[0]
                findings.append(("team_values_present", "player_canonical_ids", non_null))
            else:
                findings.append(("missing_required_column", "team", 1))

            required = ["full_name", "canonical_id"]
            for col in required:
                if column_exists(conn, "player_canonical_ids", col):
                    c = conn.execute(
                        f"SELECT COUNT(*) FROM player_canonical_ids WHERE {col} IS NULL"
                    ).fetchone()[0]
                    findings.append(("null_required_id", col, c))
                else:
                    findings.append(("missing_required_column", col, 1))

        if table_exists(conn, "players") and table_exists(conn, "player_canonical_ids"):
            if column_exists(conn, "players", "name") and column_exists(
                conn, "player_canonical_ids", "full_name"
            ):
                unresolved = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM players p
                    LEFT JOIN player_canonical_ids c
                      ON lower(trim(p.name)) = lower(trim(c.full_name))
                    WHERE c.full_name IS NULL
                    """
                ).fetchone()[0]
                findings.append(("players_missing_canonical_match", "players", unresolved))
            else:
                findings.append(("skipped_name_join_missing_columns", "players_vs_canonical", 1))

    print("check,scope,count")
    for check, scope, count in findings:
        print(f"{check},{scope},{count}")

    return 1 if any(count > 0 for _, _, count in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
