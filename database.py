import sqlite3
import json
from datetime import datetime
import os
from utils.player_id_resolver import PlayerIDResolver

DB_PATH = "ludi.db"

class LudiHistorian:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._initialize_db()
        self.resolver = PlayerIDResolver(db_path=db_path)

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        return conn

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

        # CRITICAL: Unique index for Module H upsert operations (ON CONFLICT requires this)
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_player_game_logs_unique ON player_game_logs(game_id, player_id)')

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

        # 14. Player Game Tracking (Unified Tracking Table)
        # Note: Merged legacy and new schemas.
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_game_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT,
                player_name TEXT,
                team_abbrev TEXT,
                game_date TEXT,
                matchup TEXT,
                w_l TEXT,
                min INTEGER,
                
                -- Drives
                drives_fga REAL,
                drives_fgm REAL,
                drives_fg_pct REAL,
                drives_pts REAL,
                drives_pass_pct REAL,
                
                -- Catch & Shoot
                catch_shoot_fga REAL,
                catch_shoot_fgm REAL,
                catch_shoot_fg_pct REAL,
                catch_shoot_3pa REAL,
                catch_shoot_3pm REAL,
                catch_shoot_3p_pct REAL,
                catch_shoot_efg_pct REAL,
                
                -- Pull-Up Shooting
                pull_up_fga REAL,
                pull_up_fgm REAL,
                pull_up_fg_pct REAL,
                pull_up_3pa REAL,
                pull_up_3pm REAL,
                pull_up_3p_pct REAL,
                pull_up_efg_pct REAL,

                -- Speed & Distance
                dist_miles_off REAL,
                dist_miles_def REAL,
                avg_speed_off REAL,
                avg_speed_def REAL,
                
                -- Shot Difficulty
                shot_dist_0_2_fga REAL,
                shot_dist_2_4_fga REAL,
                shot_dist_4_6_fga REAL,
                shot_dist_6_plus_fga REAL,
                
                nba_game_id TEXT,
                synced_at TIMESTAMP,
                
                UNIQUE(player_id, game_date)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_tracking_date ON player_game_tracking(game_date)')

        # MIGRATION: Add new columns to existing player_game_tracking table
        new_tracking_cols = [
            'pull_up_fga REAL', 'pull_up_fgm REAL', 'pull_up_fg_pct REAL',
            'pull_up_3pa REAL', 'pull_up_3pm REAL', 'pull_up_3p_pct REAL', 'pull_up_efg_pct REAL',
            'dist_miles_off REAL', 'dist_miles_def REAL', 'avg_speed_off REAL', 'avg_speed_def REAL',
            'catch_shoot_3pa REAL', 'catch_shoot_3pm REAL', 'catch_shoot_3p_pct REAL', 'catch_shoot_efg_pct REAL'
        ]
        for col_def in new_tracking_cols:
            col_name = col_def.split()[0]
            try:
                c.execute(f'ALTER TABLE player_game_tracking ADD COLUMN {col_def}')
            except:
                pass # Column exists

        # 16. Player Game Advanced (New)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_game_advanced (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT,
                player_name TEXT,
                team_abbrev TEXT,
                game_date TEXT,
                matchup TEXT,
                w_l TEXT,
                min INTEGER,
                off_rating REAL,
                def_rating REAL,
                net_rating REAL,
                ast_pct REAL,
                ast_to REAL,
                ast_ratio REAL,
                oreb_pct REAL,
                dreb_pct REAL,
                reb_pct REAL,
                tov_pct REAL,
                efg_pct REAL,
                ts_pct REAL,
                usg_pct REAL,
                pace REAL,
                pie REAL,
                nba_game_id TEXT,
                synced_at TIMESTAMP,
                UNIQUE(player_id, game_date)
            )
        ''')

        # 10. Player Clutch Stats (NBA API - Traditional Clutch)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_clutch_stats (
                nba_player_id TEXT NOT NULL,
                player_name TEXT,
                team_abbr TEXT,
                game_date TEXT NOT NULL,
                -- Clutch Totals
                clutch_min REAL,
                clutch_pts REAL,
                clutch_rebs REAL,
                clutch_asts REAL,
                clutch_stl REAL,
                clutch_blk REAL,
                -- Clutch Shooting
                clutch_fgm REAL,
                clutch_fga REAL,
                clutch_fg_pct REAL,
                clutch_3pm REAL,
                clutch_3pa REAL,
                clutch_3p_pct REAL,
                clutch_ftm REAL,
                clutch_fta REAL,
                clutch_ft_pct REAL,
                -- Metadata
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (nba_player_id, game_date)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_clutch_date ON player_clutch_stats(game_date)')

        # 17. Player Game Opponent (New - Phase 3)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_game_opponent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT,
                player_name TEXT,
                team_abbrev TEXT,
                game_date TEXT,
                opp_fgm REAL,
                opp_fga REAL,
                opp_fg_pct REAL,
                opp_3pm REAL,
                opp_3pa REAL,
                opp_3p_pct REAL,
                opp_ftm REAL,
                opp_fta REAL,
                opp_ft_pct REAL,
                opp_reb REAL,
                opp_ast REAL,
                opp_tov REAL,
                opp_stl REAL,
                opp_blk REAL,
                opp_pts REAL,
                nba_game_id TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, game_date)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_opponent_date ON player_game_opponent(game_date)')

        # 18. Player Game Hustle (New - Phase 4)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_game_hustle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT,
                player_name TEXT,
                team_abbrev TEXT,
                game_date TEXT,
                
                screen_assists REAL,
                screen_assists_pts REAL,
                deflections REAL,
                loose_balls_recovered REAL,
                charges_drawn REAL,
                contested_2pt_shots REAL,
                contested_3pt_shots REAL,
                contested_shots REAL,
                box_outs REAL,
                
                nba_game_id TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, game_date)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_hustle_date ON player_game_hustle(game_date)')

        # 19. Player WOWY Stats (With-Or-Without-You On/Off Splits)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_wowy_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT,
                player_name TEXT,
                team_abbrev TEXT,
                game_date TEXT,
                game_id TEXT,
                
                on_court_minutes REAL,
                off_court_minutes REAL,
                on_court_off_rtg REAL,
                off_court_off_rtg REAL,
                on_off_diff REAL,
                on_court_pts_per_100 REAL,
                off_court_pts_per_100 REAL,
                on_court_possessions INTEGER,
                off_court_possessions INTEGER,
                
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, game_date)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_wowy_player_date ON player_wowy_stats(player_id, game_date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_wowy_date ON player_wowy_stats(game_date)')

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
        # UNIQUE constraint for ON CONFLICT upsert support (Phase 6.5b - Feb 3, 2026)
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_referee_daily_unique ON referee_daily_stats(referee_id, sync_date)')

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

        # 12. Depth Charts Table (Phase 6.1 - Feb 2, 2026)
        # Stores official NBA depth charts from Tank01 API
        c.execute('''
            CREATE TABLE IF NOT EXISTS depth_charts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_abbr TEXT NOT NULL,           -- ATL, LAL, etc.
                team_id TEXT,                       -- NBA team ID
                position TEXT NOT NULL,             -- PG, SG, SF, PF, C
                player_name TEXT NOT NULL,          -- Full name (from Tank01)
                player_id TEXT,                     -- NBA player ID (canonical)
                depth_order INTEGER NOT NULL,       -- 1=starter, 2=backup, 3=deep bench
                synced_at TEXT NOT NULL,            -- ISO timestamp of sync
                UNIQUE(team_abbr, position, depth_order)
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_depth_charts_team ON depth_charts(team_abbr)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_depth_charts_player ON depth_charts(player_name)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_depth_charts_position ON depth_charts(team_abbr, position)')

        # Add is_starter column to players table if it doesn't exist
        # SQLite doesn't support IF NOT EXISTS for ALTER COLUMN, so we check manually
        try:
            c.execute('SELECT is_starter FROM players LIMIT 1')
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            c.execute('ALTER TABLE players ADD COLUMN is_starter INTEGER DEFAULT 0')

        # 13. Player Season WOWY Table (Phase 6.3 - Feb 2, 2026)
        # Stores full-season on/off splits from PBP Stats API
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_season_wowy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT,
                team_abbr TEXT,
                team_id TEXT,
                season TEXT DEFAULT '2025-26',
                -- ON-court stats (team with this player)
                on_possessions INTEGER,
                on_ortg REAL,
                on_drtg REAL,
                on_netrtg REAL,
                -- OFF-court stats (team without this player)
                off_possessions INTEGER,
                off_ortg REAL,
                off_drtg REAL,
                off_netrtg REAL,
                -- Impact metrics
                on_off_diff REAL,  -- on_netrtg - off_netrtg (star player impact)
                -- Metadata
                synced_at TEXT,
                UNIQUE(player_id, season)
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_season_wowy_player ON player_season_wowy(player_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_season_wowy_team ON player_season_wowy(team_abbr)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_season_wowy_season ON player_season_wowy(season)')

        # Sprint 3: Add Four Factor On/Off columns to player_season_wowy table
        # These columns store the Four Factors (eFG%, TOV%, OREB%, FT Rate) for on/off court
        try:
            c.execute('ALTER TABLE player_season_wowy ADD COLUMN on_efg_pct REAL')
            c.execute('ALTER TABLE player_season_wowy ADD COLUMN off_efg_pct REAL')
            c.execute('ALTER TABLE player_season_wowy ADD COLUMN on_tov_pct REAL')
            c.execute('ALTER TABLE player_season_wowy ADD COLUMN off_tov_pct REAL')
            c.execute('ALTER TABLE player_season_wowy ADD COLUMN on_oreb_pct REAL')
            c.execute('ALTER TABLE player_season_wowy ADD COLUMN off_oreb_pct REAL')
            c.execute('ALTER TABLE player_season_wowy ADD COLUMN on_ft_rate REAL')
            c.execute('ALTER TABLE player_season_wowy ADD COLUMN off_ft_rate REAL')
            c.execute('ALTER TABLE player_season_wowy ADD COLUMN on_pace REAL')
            c.execute('ALTER TABLE player_season_wowy ADD COLUMN off_pace REAL')
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                print(f"Warning: Four factor columns may already exist: {e}")

        # Sprint 3: Team Leverage Profiles table (game state intelligence)
        c.execute('''
            CREATE TABLE IF NOT EXISTS team_leverage_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_abbr TEXT NOT NULL,
                team_id TEXT NOT NULL,
                season TEXT DEFAULT '2025-26',
                vh_possessions INTEGER,
                vh_ortg REAL,
                vh_efg_pct REAL,
                vh_pace REAL,
                vh_oreb_pct REAL,
                vh_ft_rate REAL,
                h_possessions INTEGER,
                h_ortg REAL,
                h_efg_pct REAL,
                h_pace REAL,
                h_oreb_pct REAL,
                h_ft_rate REAL,
                l_possessions INTEGER,
                l_ortg REAL,
                l_efg_pct REAL,
                l_pace REAL,
                l_oreb_pct REAL,
                l_ft_rate REAL,
                overall_possessions INTEGER,
                overall_ortg REAL,
                overall_efg_pct REAL,
                overall_pace REAL,
                overall_oreb_pct REAL,
                overall_ft_rate REAL,
                garbage_time_boost REAL,
                clutch_factor REAL,
                pace_variance REAL,
                synced_at TEXT,
                UNIQUE(team_abbr, season)
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_leverage_team ON team_leverage_profiles(team_abbr)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_leverage_season ON team_leverage_profiles(season)')

        # Sprint 3: Player Leverage Usage table (crunch time identification)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_leverage_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                team_abbr TEXT NOT NULL,
                season TEXT DEFAULT '2025-26',
                vh_possessions INTEGER,
                vh_shot_attempts INTEGER,
                total_possessions INTEGER,
                total_shot_attempts INTEGER,
                clutch_usage_rate REAL,
                synced_at TEXT,
                UNIQUE(player_name, team_abbr, season)
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_player_leverage_player ON player_leverage_usage(player_name)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_player_leverage_team ON player_leverage_usage(team_abbr)')

        # Defensive Synergy (Phase 7.9 archetype overhaul)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_defensive_synergy (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                team_abbr TEXT,
                season TEXT DEFAULT '2025-26',
                playtype TEXT NOT NULL,
                games_played INTEGER,
                poss_per_game REAL,
                freq_pct REAL,
                ppp_allowed REAL,
                fg_pct_allowed REAL,
                percentile INTEGER,
                synced_at TEXT,
                UNIQUE(player_name, playtype, season)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_def_synergy_player ON player_defensive_synergy(player_name)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_def_synergy_team ON player_defensive_synergy(team_abbr)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_def_synergy_playtype ON player_defensive_synergy(playtype)')

        # Team scheme cache (season + 21d + 14d with active scheme)
        c.execute('''
            CREATE TABLE IF NOT EXISTS team_scheme_cache (
                team_abbr TEXT NOT NULL,
                scheme_type TEXT NOT NULL,
                season_style TEXT NOT NULL,
                d21_style TEXT NOT NULL,
                d14_style TEXT NOT NULL,
                active_style TEXT NOT NULL,
                window_end TEXT NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (team_abbr, scheme_type)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_team_scheme_type ON team_scheme_cache(scheme_type)')

        # Create lineup_season_totals view (aggregates per-game lineup data)
        # This view aggregates team_lineups from per-game to full-season totals
        c.execute('''
            CREATE VIEW IF NOT EXISTS lineup_season_totals AS
            SELECT
                team_abbreviation,
                lineup_players,
                SUM(possessions) as total_possessions,
                SUM(minutes) as total_minutes,
                AVG(off_rating) as avg_ortg,
                AVG(def_rating) as avg_drtg,
                AVG(net_rating) as avg_netrtg,
                COUNT(*) as games_played
            FROM team_lineups
            GROUP BY team_abbreviation, lineup_players
            HAVING SUM(possessions) >= 25
        ''')

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

        try:
            # 🛡️ GUARDRAIL: Resolve ID before writing (Heal on Ingestion)
            canonical_id = self.resolver.resolve_to_canonical_id(player_data['id'])
            player_data['id'] = canonical_id
        except ValueError:
            pass # Keep original if resolution fails

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

        try:
            # 🛡️ GUARDRAIL: Resolve ID before writing (Heal on Ingestion)
            # This protects against Tank01 sending "28398804489" -> converts to "1629029"
            canonical_id = self.resolver.resolve_to_canonical_id(player_data['id'])
            player_data['id'] = canonical_id
        except ValueError:
            pass # Keep original if resolution fails

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
