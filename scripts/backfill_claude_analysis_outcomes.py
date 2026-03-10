"""
scripts/backfill_claude_analysis_outcomes.py
Phase 8.23-E: Backfill actual_outcome in claude_analysis_log from bet_recommendations.

Two passes:
  Pass 1 — Per-bet rows (call_type='curation_per_bet', bet_id IS NOT NULL):
            UPDATE via direct bet_id JOIN.
  Pass 2 — Batch rows (call_type='curation', bet_id IS NULL):
            UPDATE via player_name + game_date JOIN.
            Only sets actual_outcome if exactly 1 settled bet matches the key.

Usage:
  python scripts/backfill_claude_analysis_outcomes.py
  python scripts/backfill_claude_analysis_outcomes.py --dry-run
"""

import sqlite3
import sys
import os

DRY_RUN = "--dry-run" in sys.argv

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ludi.db")

def main():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout=30000")
    conn.row_factory = sqlite3.Row

    try:
        # Pass 1: Per-bet rows — direct bet_id JOIN
        pass1_result = conn.execute("""
            UPDATE claude_analysis_log
            SET actual_outcome = (
                SELECT br.outcome
                FROM bet_recommendations br
                WHERE br.id = claude_analysis_log.bet_id
                  AND br.outcome IN ('WIN', 'LOSS')
            )
            WHERE call_type = 'curation_per_bet'
              AND bet_id IS NOT NULL
              AND actual_outcome IS NULL
        """)
        pass1_count = pass1_result.rowcount
        print(f"Pass 1 (per-bet): {pass1_count} rows updated")

        # Pass 2: Batch rows — player_name + game_date JOIN (1:1 only)
        batch_rows = conn.execute("""
            SELECT id, player_name, game_date
            FROM claude_analysis_log
            WHERE call_type = 'curation'
              AND actual_outcome IS NULL
              AND player_name IS NOT NULL
              AND game_date IS NOT NULL
        """).fetchall()

        pass2_updated = 0
        pass2_skipped_ambiguous = 0
        pass2_skipped_unsettled = 0

        for row in batch_rows:
            log_id = row['id']
            player_name = row['player_name']
            game_date = row['game_date']

            matches = conn.execute("""
                SELECT outcome
                FROM bet_recommendations
                WHERE player_name = ?
                  AND game_date = ?
                  AND outcome IN ('WIN', 'LOSS')
            """, (player_name, game_date)).fetchall()

            if len(matches) == 1:
                conn.execute("""
                    UPDATE claude_analysis_log
                    SET actual_outcome = ?
                    WHERE id = ?
                """, (matches[0]['outcome'], log_id))
                pass2_updated += 1
            elif len(matches) > 1:
                pass2_skipped_ambiguous += 1
            else:
                pass2_skipped_unsettled += 1

        print(f"Pass 2 (batch): {pass2_updated} updated, {pass2_skipped_ambiguous} skipped (ambiguous), {pass2_skipped_unsettled} skipped (unsettled/no match)")

        if DRY_RUN:
            print("DRY RUN — rolling back all changes")
            conn.rollback()
        else:
            conn.commit()
            print("Committed.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
