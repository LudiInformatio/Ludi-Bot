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

        # 5. Roster History Table (Audit Trail for Trades/Signings/Waivers)
        c.execute('''
            CREATE TABLE IF NOT EXISTS roster_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team TEXT NOT NULL,
                season_id TEXT NOT NULL,
                status TEXT DEFAULT 'ACTIVE',
                change_type TEXT,
                change_date TEXT NOT NULL,
                previous_team TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add indexes for roster_history
        c.execute('CREATE INDEX IF NOT EXISTS idx_roster_history_player ON roster_history(player_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_roster_history_date ON roster_history(change_date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_roster_history_season ON roster_history(season_id)')

        # 6. Player Shot Quality Table (NBA API Tracking - Phase 1.3)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_shot_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT,
                season TEXT DEFAULT '2025-26',
                -- Shot areas
                restricted_area_fga REAL,
                restricted_area_fg_pct REAL,
                paint_fga REAL,
                paint_fg_pct REAL,
                mid_range_fga REAL,
                mid_range_fg_pct REAL,
                corner_3_fga REAL,
                corner_3_fg_pct REAL,
                above_break_3_fga REAL,
                above_break_3_fg_pct REAL,
                -- Shot difficulty (defender distance)
                very_tight_fga REAL,
                very_tight_fg_pct REAL,
                tight_fga REAL,
                tight_fg_pct REAL,
                open_fga REAL,
                open_fg_pct REAL,
                wide_open_fga REAL,
                wide_open_fg_pct REAL,
                contested_shot_pct REAL,
                -- Metadata
                fetch_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, season)
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_shot_quality_player ON player_shot_quality(player_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_shot_quality_season ON player_shot_quality(season)')

        # 7a. Shot Quality Table (PBP Stats - Derived Metrics)
        c.execute('''
            CREATE TABLE IF NOT EXISTS shot_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                player_name TEXT,
                shot_quality_avg REAL,
                shot_distance_avg REAL,
                shots_taken INTEGER,
                shots_made INTEGER,
                leverage_score REAL,
                wowy_on_off REAL,
                source TEXT DEFAULT 'pbp_stats',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, player_id)
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_pbp_shot_quality_game ON shot_quality(game_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_pbp_shot_quality_player ON shot_quality(player_id)')

        # 7. Player Workload Table (NBA API Tracking - Phase 1.3)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_workload (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT,
                season TEXT DEFAULT '2025-26',
                -- Games
                games_played INTEGER,
                -- Rebounding workload
                total_reb REAL,
                oreb REAL,
                dreb REAL,
                contested_reb REAL,
                uncontested_reb REAL,
                contested_reb_pct REAL,
                -- Passing workload
                total_passes REAL,
                total_assists REAL,
                -- Metadata
                fetch_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, season)
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_workload_player ON player_workload(player_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_workload_season ON player_workload(season)')

        # 8. Defender Matchups Table (NBA API Tracking - Phase 1.3)
        c.execute('''
            CREATE TABLE IF NOT EXISTS defender_matchups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT,
                defender_id TEXT NOT NULL,
                defender_name TEXT,
                season TEXT DEFAULT '2025-26',
                -- Matchup stats
                matchup_minutes REAL,
                games_vs_defender INTEGER,
                fga INTEGER,
                fgm INTEGER,
                fg_pct REAL,
                -- Metadata
                games_sampled INTEGER,
                fetch_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, defender_id, season)
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_matchups_player ON defender_matchups(player_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_matchups_defender ON defender_matchups(defender_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_matchups_season ON defender_matchups(season)')

        # Add new columns to players table (for existing databases)
        # Using ALTER TABLE with IF NOT EXISTS pattern (SQLite 3.35.0+)
        try:
            c.execute('ALTER TABLE players ADD COLUMN season_id TEXT DEFAULT "22025"')
        except:
            pass  # Column already exists

        try:
            c.execute('ALTER TABLE players ADD COLUMN is_active BOOLEAN DEFAULT 1')
        except:
            pass  # Column already exists

        try:
            c.execute('ALTER TABLE players ADD COLUMN roster_updated_at TIMESTAMP')
        except:
            pass  # Column already exists

        # Add composite index for season-aware roster queries
        c.execute('CREATE INDEX IF NOT EXISTS idx_players_season_team ON players(season_id, team, is_active)')

        # 9. Referee Profiles Table (Module G v2.0 - Jan 15, 2026)
        c.execute('''
            CREATE TABLE IF NOT EXISTS referee_profiles (
                referee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                referee_name TEXT UNIQUE NOT NULL,
                seasons_active INTEGER DEFAULT 1,
                -- Weekly baseline stats (from Basketball-Reference)
                avg_fouls_per_game REAL DEFAULT 0.0,
                avg_pace_impact REAL DEFAULT 1.0,
                avg_technical_rate REAL DEFAULT 0.0,
                -- Classification
                style TEXT DEFAULT 'NEUTRAL',  -- LENIENT, NEUTRAL, STRICT
                -- Betting Intelligence (Phase 5 - Jan 15, 2026)
                ou_record TEXT,             -- e.g. "19-9"
                ou_percentage REAL,         -- e.g. 0.679 (68% Over)
                avg_total REAL,             -- Avg game total points
                home_ats_record TEXT,       -- e.g. "18-6"
                home_ats_bias REAL,         -- e.g. 0.75 (75% Home Cover)
                -- Metadata
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_source TEXT DEFAULT 'basketball-reference'
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_referee_name ON referee_profiles(referee_name)')

        # 10. Referee Daily Stats Table (Module G v2.0 - Jan 15, 2026)
        c.execute('''
            CREATE TABLE IF NOT EXISTS referee_daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referee_id INTEGER,
                -- Last 5 games (from NBAStuffer)
                last5_fouls_avg REAL DEFAULT 0.0,
                last5_pace_impact REAL DEFAULT 1.0,
                last5_over_under_record TEXT,
                -- Recency flags
                is_hot_whistle BOOLEAN DEFAULT 0,
                is_fast_paced BOOLEAN DEFAULT 0,
                -- Metadata
                sync_date DATE DEFAULT CURRENT_DATE,
                data_source TEXT DEFAULT 'nbastuffer',
                FOREIGN KEY (referee_id) REFERENCES referee_profiles(referee_id)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_referee_daily_date ON referee_daily_stats(sync_date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_referee_daily_ref ON referee_daily_stats(referee_id)')

        # 11. Referee Player Bias Table (Module G Phase 4 - Jan 15, 2026)
        c.execute('''
            CREATE TABLE IF NOT EXISTS referee_player_bias (
                referee_id INTEGER,
                player_id TEXT,
                player_name TEXT,
                games_officiated INTEGER DEFAULT 0,
                avg_pf_called REAL DEFAULT 0.0,
                avg_fta_awarded REAL DEFAULT 0.0,
                points_impact_vs_avg REAL DEFAULT 0.0,
                last_updated DATE,
                PRIMARY KEY (referee_id, player_id),
                FOREIGN KEY (referee_id) REFERENCES referee_profiles(referee_id)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_ref_bias_player ON referee_player_bias(player_id)')

        conn.commit()
        conn.close()
        # print("✅ Ludi Memory (Database) initialized successfully.")

    def update_player_census(self, player_data):
        """
        Upserts (Update or Insert) player data.
        LEGACY METHOD - Use update_player_census_v2() for new code with season tracking.
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

    def update_player_census_v2(self, player_data, season_id='22025'):
        """
        Enhanced version with season tracking and roster update timestamps.

        Args:
            player_data: Dict with id, name, team, pos, status, ppg, usg
            season_id: Season identifier (default: '22025' for 2025-26)

        Returns:
            bool: True if team changed (trade detected), False otherwise
        """
        conn = self._get_conn()
        c = conn.cursor()

        # Check if player exists and team changed (trade detection)
        c.execute('SELECT team FROM players WHERE player_id = ?', (player_data['id'],))
        existing = c.fetchone()
        team_changed = existing and existing[0] != player_data['team']

        c.execute('''
            INSERT INTO players (
                player_id, name, team, position, status,
                base_ppg, usg_pct, season_id, is_active, roster_updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(player_id) DO UPDATE SET
                team=excluded.team,
                position=excluded.position,
                status=excluded.status,
                base_ppg=excluded.base_ppg,
                usg_pct=excluded.usg_pct,
                season_id=excluded.season_id,
                is_active=excluded.is_active,
                roster_updated_at=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
        ''', (
            player_data['id'],
            player_data['name'],
            player_data['team'],
            player_data.get('pos', 'UNK'),
            player_data.get('status', 'ACTIVE'),
            player_data.get('ppg', 0),
            player_data.get('usg', 0),
            season_id
        ))

        conn.commit()
        conn.close()

        return team_changed

    def log_roster_change(self, player_id, player_name, old_team, new_team, change_type, notes=''):
        """
        Log roster change to history table for audit trail.

        Args:
            player_id: Player identifier
            player_name: Player full name
            old_team: Previous team abbreviation (or None for signings)
            new_team: New team abbreviation (or None for waivers)
            change_type: 'TRADE', 'SIGNING', 'WAIVED', 'TWO_WAY'
            notes: Optional notes about the transaction
        """
        conn = self._get_conn()
        c = conn.cursor()

        c.execute('''
            INSERT INTO roster_history (
                player_id, player_name, team, season_id,
                change_type, change_date, previous_team, notes
            ) VALUES (?, ?, ?, ?, ?, DATE('now'), ?, ?)
        ''', (
            player_id,
            player_name,
            new_team or 'FREE_AGENT',
            '22025',
            change_type,
            old_team,
            notes
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
