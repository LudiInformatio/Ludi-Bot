import json
import sqlite3
import os
from datetime import datetime
from database import LudiHistorian

# --- CONFIGURATION ---
LEGACY_DB_PATH = "ludi_history_db.json"
YAK_CACHE_PATH = "yak_cache.json"

def migrate_data():
    """
    Reads legacy JSON files and inserts them into the new SQLite DB.
    """
    print("🚀 Starting Migration Protocol...")
    
    # 1. Initialize the New Historian
    historian = LudiHistorian()
    conn = historian._get_conn()
    c = conn.cursor()
    
    # 2. Check for Legacy File
    if not os.path.exists(LEGACY_DB_PATH):
        print(f"❌ Error: Legacy file '{LEGACY_DB_PATH}' not found!")
        return

    print(f"📂 Found legacy database: {LEGACY_DB_PATH}")
    
    try:
        with open(LEGACY_DB_PATH, 'r') as f:
            legacy_data = json.load(f)
    except json.JSONDecodeError:
        print("❌ Error: Could not parse JSON file. It might be corrupted.")
        return

    # 3. Migrate Players (The Census)
    # The JSON is a LIST of Game Logs. We need to aggregate them to find unique players
    # and calculate their "Baseline" stats from this history.
    
    unique_players = {}
    print(f"🔄 Processing {len(legacy_data)} game logs...")
    
    for row in legacy_data:
        p_id = str(row.get('PLAYER_ID'))
        name = row.get('PLAYER_NAME', 'Unknown')
        team = row.get('TEAM_ABBREVIATION', 'FA')
        pts = row.get('PTS', 0)
        
        # Initialize if new
        if p_id not in unique_players:
            unique_players[p_id] = {
                'name': name,
                'team': team,
                'total_pts': 0,
                'games_played': 0,
                'pos': 'UNK' # Position isn't in game logs usually, will default to UNK
            }
        
        # Accumulate stats
        unique_players[p_id]['total_pts'] += pts
        unique_players[p_id]['games_played'] += 1
        # Update team (in case they were traded, keep most recent)
        unique_players[p_id]['team'] = team 

    print(f"📝 Found {len(unique_players)} unique players. Inserting into DB...")
    
    players_migrated = 0
    for p_id, p_data in unique_players.items():
        # Calculate Average PPG from history
        avg_ppg = p_data['total_pts'] / max(1, p_data['games_played'])
        
        # Insert into SQLite
        try:
            c.execute('''
                INSERT INTO players (player_id, name, team, position, status, base_ppg, usg_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(player_id) DO UPDATE SET
                    base_ppg=excluded.base_ppg,
                    team=excluded.team,
                    updated_at=CURRENT_TIMESTAMP
            ''', (
                p_id, 
                p_data['name'], 
                p_data['team'], 
                p_data['pos'], 
                'ACTIVE', 
                round(avg_ppg, 1), 
                0.20 # Default Usage (Game logs don't have usage rate, setting generic default)
            ))
            players_migrated += 1
        except Exception as e:
            print(f"⚠️ Failed to migrate {p_data['name']}: {e}")

    conn.commit()

    print("-" * 30)
    print(f"✅ PHASE 1 COMPLETE: Players Table")
    print(f"📊 Historical Game Logs Processed: {len(legacy_data)}")
    print(f"👥 Unique Players Created: {players_migrated}")
    print("-" * 30)

    # 4. Migrate Game Logs (Full Historical Detail)
    print("\n📊 Phase 2: Migrating Game Logs...")
    game_logs_migrated = migrate_game_logs(conn, legacy_data)
    print(f"✅ Game logs migrated: {game_logs_migrated} records")

    # 5. Migrate Games Table
    print("\n🏀 Phase 3: Migrating Games Table...")
    games_migrated = migrate_games(conn, legacy_data)
    print(f"✅ Games migrated: {games_migrated} unique games")

    # 6. Validation
    print("\n🔍 Phase 4: Validation...")
    validation_passed = validate_migration(conn)

    conn.close()

    if validation_passed:
        print("\n" + "=" * 50)
        print(f"✅ MIGRATION COMPLETE!")
        print(f"💾 Database Location: {os.path.abspath('ludi.db')}")
        print("=" * 50)
    else:
        print("\n⚠️ MIGRATION COMPLETED WITH WARNINGS - Review results above")


def migrate_game_logs(conn, legacy_data):
    """
    Migrates all game log records to player_game_logs table.
    Uses batch inserts for performance (1000 records per batch).
    """
    c = conn.cursor()
    batch_size = 1000
    total_inserted = 0

    for i in range(0, len(legacy_data), batch_size):
        batch = legacy_data[i:i + batch_size]
        records = []

        for row in batch:
            # Handle NULL values for percentage fields
            fg_pct = row.get('FG_PCT') if row.get('FG_PCT') is not None else None
            fg3_pct = row.get('FG3_PCT') if row.get('FG3_PCT') is not None else None
            ft_pct = row.get('FT_PCT') if row.get('FT_PCT') is not None else None

            record = (
                row.get('SEASON_ID'),
                row.get('PLAYER_ID'),
                row.get('PLAYER_NAME'),
                row.get('TEAM_ID'),
                row.get('TEAM_ABBREVIATION'),
                row.get('TEAM_NAME'),
                row.get('GAME_ID'),
                row.get('GAME_DATE'),
                row.get('MATCHUP'),
                row.get('WL'),
                row.get('MIN'),
                row.get('FGM'), row.get('FGA'), fg_pct,
                row.get('FG3M'), row.get('FG3A'), fg3_pct,
                row.get('FTM'), row.get('FTA'), ft_pct,
                row.get('OREB'), row.get('DREB'), row.get('REB'),
                row.get('AST'), row.get('STL'), row.get('BLK'),
                row.get('TOV'), row.get('PF'), row.get('PTS'),
                row.get('PLUS_MINUS'),
                row.get('FANTASY_PTS'),
                row.get('VIDEO_AVAILABLE', 0)
            )
            records.append(record)

        # Batch insert
        c.executemany('''
            INSERT INTO player_game_logs (
                season_id, player_id, player_name, team_id, team_abbreviation, team_name,
                game_id, game_date, matchup, win_loss, minutes,
                fgm, fga, fg_pct, fg3m, fg3a, fg3_pct, ftm, fta, ft_pct,
                oreb, dreb, reb, ast, stl, blk, tov, pf, pts, plus_minus,
                fantasy_pts, video_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', records)

        total_inserted += len(records)
        conn.commit()  # Commit each batch

    return total_inserted


def migrate_games(conn, legacy_data):
    """
    Populates games table with unique games from game logs.
    Parses MATCHUP field to extract home/away teams.
    """
    c = conn.cursor()
    unique_games = {}

    for row in legacy_data:
        game_id = row.get('GAME_ID')
        if game_id and game_id not in unique_games:
            matchup = row.get('MATCHUP', '')
            game_date = row.get('GAME_DATE')

            # Parse matchup: "MIL vs. BKN" or "MIL @ BKN"
            # "@" means team is away, "vs." means team is home
            team_abbr = row.get('TEAM_ABBREVIATION', '')

            if ' @ ' in matchup:
                # Team is away
                away_team = team_abbr
                home_team = matchup.split(' @ ')[1] if ' @ ' in matchup else ''
            elif ' vs. ' in matchup:
                # Team is home
                home_team = team_abbr
                away_team = matchup.split(' vs. ')[1] if ' vs. ' in matchup else ''
            else:
                # Fallback
                home_team = ''
                away_team = ''

            unique_games[game_id] = {
                'date': game_date,
                'home_team': home_team,
                'away_team': away_team
            }

    # Insert unique games
    games_inserted = 0
    for game_id, game_data in unique_games.items():
        try:
            c.execute('''
                INSERT OR IGNORE INTO games (game_id, date, home_team, away_team)
                VALUES (?, ?, ?, ?)
            ''', (game_id, game_data['date'], game_data['home_team'], game_data['away_team']))
            games_inserted += 1
        except Exception as e:
            print(f"⚠️ Failed to insert game {game_id}: {e}")

    conn.commit()
    return games_inserted


def validate_migration(conn):
    """
    Comprehensive validation of migration results.
    """
    c = conn.cursor()
    all_passed = True

    # Check 1: Player game logs count
    c.execute('SELECT COUNT(*) FROM player_game_logs')
    game_logs_count = c.fetchone()[0]
    print(f"  ✓ player_game_logs: {game_logs_count} records")
    if game_logs_count == 0:
        print("    ⚠️ WARNING: No game logs migrated")
        all_passed = False

    # Check 2: Games count
    c.execute('SELECT COUNT(*) FROM games')
    games_count = c.fetchone()[0]
    print(f"  ✓ games: {games_count} records")
    if games_count == 0:
        print("    ⚠️ WARNING: No games migrated")
        all_passed = False

    # Check 3: Players count
    c.execute('SELECT COUNT(*) FROM players')
    players_count = c.fetchone()[0]
    print(f"  ✓ players: {players_count} records")

    # Check 4: Indexes created
    c.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_player_game_logs%'")
    indexes = c.fetchall()
    print(f"  ✓ indexes: {len(indexes)} created")
    if len(indexes) < 4:
        print("    ⚠️ WARNING: Expected 4 indexes, found", len(indexes))
        all_passed = False

    # Check 5: Sample query test
    c.execute('''
        SELECT player_name, pts, game_date
        FROM player_game_logs
        ORDER BY pts DESC
        LIMIT 1
    ''')
    top_scorer = c.fetchone()
    if top_scorer:
        print(f"  ✓ Sample query: Top game = {top_scorer[0]} ({top_scorer[1]} pts on {top_scorer[2]})")
    else:
        print("    ⚠️ WARNING: Sample query returned no results")
        all_passed = False

    if all_passed:
        print("\n  ✅ VALIDATION PASSED: All checks successful!")

    return all_passed

if __name__ == "__main__":
    # Create dummy JSON if it doesn't exist (for testing the script itself)
    if not os.path.exists(LEGACY_DB_PATH):
        print("⚠️  No legacy DB found used for testing. Creating a dummy one...")
        dummy_data = {
            "lebron_james_lal": {"name": "LeBron James", "team": "LAL", "pos": "SF", "ppg": 25.0, "usage_rate": 0.28},
            "stephen_curry_gsw": {"name": "Stephen Curry", "team": "GSW", "pos": "PG", "ppg": 26.4, "usage_rate": 0.30}
        }
        with open(LEGACY_DB_PATH, 'w') as f:
            json.dump(dummy_data, f)
            
    migrate_data()
