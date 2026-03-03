
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def migrate():
    """
    Removes the denormalized `team` column from the `player_canonical_ids` table.

    This is a critical schema change to enforce normalization. The `players` table
    is the canonical source for a player's *current* team. Storing it in
    `player_canonical_ids` creates data duplication and risk of inconsistency.
    """
    db_path = getattr(config, 'DB_PATH', 'ludi.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Applying migration: 001_remove_team_from_player_canonical_ids")
    print("  - Dropping column `team` from `player_canonical_ids` table...")

    try:
        # Check if column exists before trying to drop
        cursor.execute("PRAGMA table_info(player_canonical_ids)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'team' in columns:
            try:
                cursor.execute("DROP INDEX IF EXISTS idx_canonical_team")
                print("  - Success: Dropped index 'idx_canonical_team'.")
            except sqlite3.OperationalError as e:
                print(f"  - Warning: Could not drop index 'idx_canonical_team'. It may not exist. Error: {e}")

            # In recent SQLite versions, DROP COLUMN is supported.
            # For older versions, this would require a table rebuild.
            cursor.execute("ALTER TABLE player_canonical_ids DROP COLUMN team")
            print("  - Success: `team` column dropped.")
            conn.commit()
        else:
            print("  - Info: `team` column already removed. Skipping.")

    except sqlite3.OperationalError as e:
        print(f"  - Error: Could not drop column. SQLite version may be too old. Error: {e}")
        print("  - Manual migration may be required: rename table, create new without column, copy data.")
    finally:
        conn.close()
        print("Migration script finished.")

if __name__ == "__main__":
    migrate()
