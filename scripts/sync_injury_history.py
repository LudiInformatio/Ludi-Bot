#!/usr/bin/env python3
"""
Sync Tank01 historical injury records → player_injury_history table.

Tank01 endpoint: getNBAInjuryListHistory
NOTE: Suspensions do NOT appear here — use Phase 8.16 sync_suspensions.py instead.

Response structure (observed):
  body = [
    {
      "playerID": "28398804489",
      "playerName": "LeBron James",
      "injDate": "2026-01-15",        # injury start date
      "returnDate": "2026-01-20",     # actual return (may be empty if still out)
      "description": "Left ankle sprain",
      "designation": "OUT",
      "teamAbv": "LAL",
      "gamesMissed": "3"
    },
    ...
  ]

Run: weekly (Tuesday), inside weekly_validation.yml
"""
import sys
import sqlite3
from datetime import date

sys.path.insert(0, '.')
import config
from utils.tank01_client import get_client as get_tank01_client


def sync_injury_history(days: int = 30) -> int:
    client = get_tank01_client()

    history = client.get_injury_history(days=days)
    if not history:
        print(f"[sync_injury_history] No history returned for last {days} days")
        return 0

    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()
    count = 0

    for record in history:
        if not isinstance(record, dict):
            continue
        try:
            # Tank01 field names: playerID/injDate/returnDate/description/designation/gamesMissed
            player_id    = record.get('playerID', record.get('player_id', '')) or ''
            injury_date  = record.get('injDate', record.get('injuryDate', record.get('date', ''))) or ''
            return_date  = record.get('returnDate', record.get('return_date', '')) or ''
            # "description" = verbose injury text; "designation" = OUT/DOUBTFUL/Q/etc.
            injury_type  = record.get('description', record.get('injuryType', record.get('injury', ''))) or ''
            status       = record.get('designation', record.get('status', '')) or ''
            games_missed = int(record.get('gamesMissed', record.get('games_missed', 0)) or 0)

            if not player_id or not injury_date:
                continue  # skip incomplete records

            cursor.execute("""
                INSERT INTO player_injury_history
                    (player_id, injury_date, return_date, injury_type, status, games_missed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (player_id, injury_date, return_date, injury_type, status, games_missed))
            count += 1
        except Exception as e:
            print(f"[sync_injury_history] Error on record: {e}")

    conn.commit()
    conn.close()
    print(f"[sync_injury_history] Inserted {count} records (last {days} days)")
    return count


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sync Tank01 injury history")
    parser.add_argument("--days", type=int, default=30, help="Days of history to fetch")
    args = parser.parse_args()
    sync_injury_history(days=args.days)
