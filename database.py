import sqlite3
import json
from datetime import datetime
import os

DB_PATH = "ludi.db"

class LudiHistorian:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._initialize_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _initialize_db(self):
        """
        Creates the database tables if they don't exist.
        Novice-Friendly: Just run the app, and the DB builds itself.
        """
        conn = self._get_conn()
        c = conn.cursor()

        # 1. Players Table (The Census)
        c.execute('''
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                name TEXT,
                team TEXT,
                position TEXT,
                status TEXT DEFAULT 'ACTIVE',
                base_ppg REAL,
                usg_pct REAL,
                archetype TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Games Table (The Slate)
        c.execute('''
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                date TEXT,
                home_team TEXT,
                away_team TEXT,
                home_score INTEGER,
                away_score INTEGER,
                pace REAL,
                referee_crew TEXT
            )
        ''')
        
        # 3. Player Game Logs (Historical Performance)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_game_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id TEXT,
                player_id INTEGER NOT NULL,
                player_name TEXT,
                team_id INTEGER,
                team_abbreviation TEXT,
                team_name TEXT,
                game_id TEXT NOT NULL,
                game_date TEXT NOT NULL,
                matchup TEXT,
                win_loss TEXT,
                minutes INTEGER,
                fgm INTEGER, fga INTEGER, fg_pct REAL,
                fg3m INTEGER, fg3a INTEGER, fg3_pct REAL,
                ftm INTEGER, fta INTEGER, ft_pct REAL,
                oreb INTEGER, dreb INTEGER, reb INTEGER,
                ast INTEGER, stl INTEGER, blk INTEGER,
                tov INTEGER, pf INTEGER, pts INTEGER,
                plus_minus INTEGER,
                fantasy_pts REAL,
                video_available INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add indexes for performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_player_game_logs_player_id ON player_game_logs(player_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_player_game_logs_game_id ON player_game_logs(game_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_player_game_logs_game_date ON player_game_logs(game_date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_player_game_logs_player_date ON player_game_logs(player_id, game_date)')

        # 4. Odds Table (The Market)
        c.execute('''
            CREATE TABLE IF NOT EXISTS odds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                bookmaker TEXT,
                home_spread REAL,
                total REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 4. Sims Table (The Brain's Work)
        c.execute('''
            CREATE TABLE IF NOT EXISTS simulations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT,
                player_name TEXT,
                stat_category TEXT,
                projection_mean REAL,
                projection_floor REAL,
                projection_ceiling REAL,
                prob_over_line REAL,
                is_diamond_play BOOLEAN DEFAULT 0
            )
        ''')

        conn.commit()
        conn.close()
        # print("✅ Ludi Memory (Database) initialized successfully.")

    def update_player_census(self, player_data):
        """
        Upserts (Update or Insert) player data.
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO players (player_id, name, team, position, status, base_ppg, usg_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                status=excluded.status,
                base_ppg=excluded.base_ppg,
                usg_pct=excluded.usg_pct,
                updated_at=CURRENT_TIMESTAMP
        ''', (
            player_data['id'], 
            player_data['name'], 
            player_data['team'], 
            player_data['pos'],
            player_data.get('status', 'ACTIVE'),
            player_data.get('ppg', 0),
            player_data.get('usg', 0)
        ))
        
        conn.commit()
        conn.close()

if __name__ == "__main__":
    # Test the DB Creation
    historian = LudiHistorian()
    print("✅ Database initialized at", os.path.abspath(DB_PATH))
    
    # Add a Dummy Player
    historian.update_player_census({
        'id': 'giannis_antetokounmpo_mil',
        'name': 'Giannis Antetokounmpo',
        'team': 'MIL',
        'pos': 'F',
        'status': 'ACTIVE',
        'ppg': 30.4,
        'usg': 0.33
    })
    print("✅ Test Player (Giannis) inserted.")
