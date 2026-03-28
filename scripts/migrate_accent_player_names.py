"""
scripts/migrate_accent_player_names.py
=======================================
One-time migration: backfill non-accented player names in bet_recommendations
and player_projections to their canonical accented forms.

Affected players (written before commit 24ff2ad):
  - Nikola Jokic        -> Nikola Jokic (accent: Jokić)
  - Luka Doncic         -> Luka Doncic (accent: Dončić)
  - Moussa Diabate      -> Moussa Diabate (accent: Diabaté)
  - Dennis Schroder     -> Dennis Schroder (accent: Schröder)
  - Kristaps Porzingis  -> Kristaps Porzingis (accent: Porziņģis)
  - Carlton Carrington  -> Bub Carrington (name variant — same player)
  - Alexandre Sarr      -> Alex Sarr (name variant — same player)

Usage:
  python scripts/migrate_accent_player_names.py           # dry-run (safe, no writes)
  python scripts/migrate_accent_player_names.py --execute # commit changes to DB

The script is idempotent: running it twice after --execute is a no-op because
the wrong names no longer exist in the tables after the first run.
"""

import argparse
import os
import sqlite3
import sys

# ── Path Setup ────────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

DB_PATH = os.path.join(_PROJECT_ROOT, "ludi.db")

# ── Mapping: wrong_name -> canonical_name ─────────────────────────────────────
# Includes both accent-stripped forms and known API name variants.
# Keys are the names as they appear in the DB today (pre-migration).
# Values are the canonical full_name stored in players.name / player_canonical_ids.
NAME_MAP = {
    "Nikola Jokic": "Nikola Joki\u0107",        # Jokić
    "Luka Doncic": "Luka Don\u010di\u0107",      # Dončić
    "Moussa Diabate": "Moussa Diabat\u00e9",        # Diabaté
    "Dennis Schroder": "Dennis Schr\u00f6der",    # Schröder
    "Kristaps Porzingis": "Kristaps Porzi\u0146\u0123is",  # Porziņģis
    "Carlton Carrington": "Bub Carrington",       # name variant
    "Alexandre Sarr": "Alex Sarr",                # name variant
}

# Tables and their player_name column to update
TARGETS = [
    ("bet_recommendations", "player_name"),
    ("player_projections",  "player_name"),
]


def run_migration(conn: sqlite3.Connection, execute: bool) -> None:
    """
    For each (wrong_name, canonical_name) pair, UPDATE each target table.
    Prints before/after counts per player-table pair.
    All writes happen inside one transaction; any failure triggers full rollback.
    """
    cursor = conn.cursor()

    print(f"\n{'='*60}")
    print(f"Accent Migration {'[DRY RUN]' if not execute else '[EXECUTE]'}")
    print(f"{'='*60}\n")

    total_updated = 0

    for wrong_name, canonical_name in NAME_MAP.items():
        for table, col in TARGETS:
            # Count rows before update
            cursor.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} = ?",
                (wrong_name,),
            )
            before = cursor.fetchone()[0]

            if before == 0:
                print(
                    f"  {table}.{col}: '{wrong_name}' — 0 rows (already clean or not present)"
                )
                continue

            print(
                f"  {table}.{col}: '{wrong_name}' -> '{canonical_name}' — {before} row(s) to update"
            )

            if execute:
                cursor.execute(
                    f"UPDATE {table} SET {col} = ? WHERE {col} = ?",
                    (canonical_name, wrong_name),
                )
                # Verify after
                cursor.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {col} = ?",
                    (wrong_name,),
                )
                after = cursor.fetchone()[0]
                if after != 0:
                    raise RuntimeError(
                        f"UPDATE failed for '{wrong_name}' in {table}: "
                        f"{after} rows still have wrong name"
                    )
                total_updated += before

    if execute:
        conn.commit()
        print(f"\n[OK] Transaction committed. {total_updated} total rows updated.")
    else:
        print(f"\n[DRY RUN] No changes written. Re-run with --execute to apply.")

    print()


def verify_clean(conn: sqlite3.Connection) -> None:
    """Post-run verification: assert zero rows remain with wrong names."""
    cursor = conn.cursor()
    print("Verification — checking for remaining wrong names:\n")
    found_any = False
    for wrong_name in NAME_MAP:
        for table, col in TARGETS:
            cursor.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} = ?",
                (wrong_name,),
            )
            count = cursor.fetchone()[0]
            status = "OK (0 rows)" if count == 0 else f"FAIL ({count} rows still present)"
            marker = "" if count == 0 else " <-- STILL DIRTY"
            print(f"  {table}.{col} '{wrong_name}': {status}{marker}")
            if count > 0:
                found_any = True
    if found_any:
        print("\n[WARN] Some wrong names remain — migration may not have completed.")
    else:
        print("\n[OK] All target tables are clean.")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-time accent backfill for bet_recommendations + player_projections"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually write changes to the DB. Dry-run by default.",
    )
    parser.add_argument(
        "--db",
        default=DB_PATH,
        help=f"Path to ludi.db (default: {DB_PATH})",
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"[ERROR] Database not found: {args.db}")
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA journal_mode=WAL")

    try:
        run_migration(conn, execute=args.execute)
        if args.execute:
            verify_clean(conn)
    except Exception as exc:
        conn.rollback()
        print(f"\n[ERROR] Migration failed — full rollback applied.\nReason: {exc}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
