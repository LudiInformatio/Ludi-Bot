import sqlite3
import re
import os

DB_PATH = 'ludi.db'

def fix_empty_teams():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Find games with empty or NULL team names
    print("🔍 Scanning for games with missing team names...")
    c.execute('''
        SELECT game_id, date, rowid 
        FROM games 
        WHERE (home_team IS NULL OR home_team = '' OR away_team IS NULL OR away_team = '')
    ''')
    
    broken_games = c.fetchall()
    count = len(broken_games)
    
    if count == 0:
        print("✅ No broken game records found.")
        conn.close()
        return

    print(f"⚠️  Found {count} games with missing team info.")
    print("   Attempting to parse from game_id (Format: YYYYMMDD_AWAY@HOME)...")

    fixed_count = 0
    errors = 0

    for game_id, game_date, rowid in broken_games:
        # Expected format: 20260112_LAL@SAC
        # Regex to extract: _(AAA)@(HHH)
        try:
            # Split by underscore to separate date from matchup
            parts = game_id.split('_')
            if len(parts) < 2:
                print(f"   ❌ Skipping malformed ID: {game_id}")
                errors += 1
                continue
            
            matchup_str = parts[1] # "LAL@SAC"
            
            if '@' not in matchup_str:
                print(f"   ❌ No '@' in matchup string: {game_id}")
                errors += 1
                continue
                
            away_team, home_team = matchup_str.split('@')
            
            # Update the record
            c.execute('''
                UPDATE games 
                SET home_team = ?, away_team = ?
                WHERE rowid = ?
            ''', (home_team, away_team, rowid))
            
            fixed_count += 1
            
        except Exception as e:
            print(f"   ❌ Error processing {game_id}: {e}")
            errors += 1

    conn.commit()
    conn.close()
    
    print("-" * 40)
    print(f"✅ REPAIR COMPLETE")
    print(f"   Fixed: {fixed_count}")
    print(f"   Errors: {errors}")
    print(f"   Remaining: {count - fixed_count}")

if __name__ == "__main__":
    fix_empty_teams()
