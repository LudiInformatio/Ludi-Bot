#!/usr/bin/env python3
"""
One-time data repair: Recalculate avg_pace_impact and style in referee_profiles.

Root cause: avg_pace_impact was seeded with a /~42 divisor (total game fouls) instead of
/12.5 (per-referee share). This 3.36x error caused all pace impacts to be clamped to the
0.90 safety floor in get_game_impact(), killing the referee signal entirely.

Safe to re-run (idempotent).
"""

import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import DB_PATH

LEAGUE_AVG_FOULS = 12.5  # Per referee: ~37.5 total game fouls / 3 crew members


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Show before state for top offenders
    print("=== BEFORE ===")
    rows = conn.execute(
        "SELECT referee_name, avg_fouls_per_game, avg_pace_impact, style "
        "FROM referee_profiles WHERE avg_fouls_per_game > 0 "
        "ORDER BY avg_fouls_per_game DESC LIMIT 10"
    ).fetchall()
    for r in rows:
        print(f"  {r['referee_name']:25s}  fouls={r['avg_fouls_per_game']:.2f}  "
              f"pace={r['avg_pace_impact']:.3f}  style={r['style']}")

    # Apply the fix
    updated = conn.execute("""
        UPDATE referee_profiles
        SET avg_pace_impact = ROUND(avg_fouls_per_game / ?, 3),
            style = CASE
                WHEN avg_fouls_per_game >= 14.0 THEN 'STRICT'
                WHEN avg_fouls_per_game <= 11.0 THEN 'LENIENT'
                ELSE 'NEUTRAL'
            END
        WHERE avg_fouls_per_game > 0
    """, (LEAGUE_AVG_FOULS,)).rowcount
    conn.commit()

    # Show after state
    print(f"\n=== AFTER ({updated} rows updated) ===")
    rows = conn.execute(
        "SELECT referee_name, avg_fouls_per_game, avg_pace_impact, style "
        "FROM referee_profiles WHERE avg_fouls_per_game > 0 "
        "ORDER BY avg_fouls_per_game DESC LIMIT 10"
    ).fetchall()
    for r in rows:
        print(f"  {r['referee_name']:25s}  fouls={r['avg_fouls_per_game']:.2f}  "
              f"pace={r['avg_pace_impact']:.3f}  style={r['style']}")

    conn.close()
    print(f"\nDone. Verify: Tony Brothers should be ~1.387 STRICT.")


if __name__ == "__main__":
    main()
