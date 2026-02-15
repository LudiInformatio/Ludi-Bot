#!/usr/bin/env python3
"""
Sync assist combo data from PBP Stats API into ludi.db.
Fetches all passer→scorer assist combinations for the season.

Usage:
    python scripts/sync_assist_combos.py
"""
import sqlite3
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.pbp_stats_client import get_assist_combo_summary


DB_PATH = "ludi.db"
SEASON = "2025-26"


def create_table(conn):
    """Create assist_combos table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assist_combos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passer_name TEXT NOT NULL,
            scorer_name TEXT NOT NULL,
            assist_count INTEGER NOT NULL,
            season TEXT NOT NULL DEFAULT '2025-26',
            synced_at TEXT NOT NULL,
            UNIQUE(passer_name, scorer_name, season)
        )
    """)
    conn.commit()


def sync():
    print(f"[Assist Combos] Fetching assist combo data for {SEASON}...")

    data = get_assist_combo_summary(season=SEASON)
    if not data:
        print("[Assist Combos] ERROR: No data returned from API")
        return

    results = data.get('results', [])
    if not results:
        print("[Assist Combos] ERROR: No results in API response")
        return

    print(f"[Assist Combos] Received {len(results)} assist combos from API")

    conn = sqlite3.connect(DB_PATH)
    create_table(conn)

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inserted = 0
    passers = set()

    for combo in results:
        passer = combo.get('assist_player', '')
        scorer = combo.get('scorer_player', '')
        total = combo.get('total', 0)

        if not passer or not scorer or total <= 0:
            continue

        conn.execute("""
            INSERT OR REPLACE INTO assist_combos
                (passer_name, scorer_name, assist_count, season, synced_at)
            VALUES (?, ?, ?, ?, ?)
        """, (passer, scorer, total, SEASON, synced_at))

        inserted += 1
        passers.add(passer)

    conn.commit()
    conn.close()

    print(f"[Assist Combos] Synced {inserted} assist combos for {len(passers)} unique passers")


if __name__ == "__main__":
    sync()
