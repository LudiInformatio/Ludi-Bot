import sqlite3
import json
import logging
from datetime import datetime
import os
from utils.player_id_resolver import PlayerIDResolver

# Setup logger for database operations
logger = logging.getLogger(__name__)

DB_PATH = "ludi.db"


def sync_canonical_games(conn):
    """
    Refresh canonical_games from the games table — single source of truth for game identity.

    The games table stores up to 3 row formats per game (NBA official, shortened, date-team).
    Any Pattern-B JOIN (date + team pair) returns 3× rows without this dedup layer.

    Call this after any INSERT INTO games to keep canonical_games current.
    Uses MAX() aggregation to pick the best available data from duplicate rows:
      - nba_official_id: prefers 0022500001 format (10-char, starts with '002')
      - referee_crew / pace / scores: first non-null/non-zero value wins
    Safe to call repeatedly — ON CONFLICT DO UPDATE uses COALESCE to protect existing data.

    Usage:
        from database import sync_canonical_games
        sync_canonical_games(conn)   # conn must be an open sqlite3.Connection
    """
    _sync_canonical_games(conn)


def _sync_canonical_games(conn):
    """Internal implementation — called by both sync_canonical_games() and create_tables()."""
    conn.execute("""
        INSERT INTO canonical_games
            (canonical_game_id, date, home_team, away_team, nba_official_id,
             home_score, away_score, pace, referee_crew, updated_at)
        SELECT
            date || '_' || home_team || '_' || away_team           AS canonical_game_id,
            date,
            home_team,
            away_team,
            -- Prefer the 10-char 002... format from NBA official/Tank01 sources
            MAX(CASE WHEN length(game_id) = 10 AND game_id GLOB '002*'
                     THEN game_id END)                             AS nba_official_id,
            MAX(CASE WHEN home_score > 0 THEN home_score END)      AS home_score,
            MAX(CASE WHEN away_score > 0 THEN away_score END)      AS away_score,
            MAX(CASE WHEN pace > 0 THEN pace END)                  AS pace,
            MAX(CASE WHEN referee_crew IS NOT NULL AND referee_crew != ''
                     THEN referee_crew END)                        AS referee_crew,
            datetime('now')                                        AS updated_at
        FROM games
        WHERE home_team IS NOT NULL AND home_team != ''
          AND away_team IS NOT NULL AND away_team != ''
          AND date IS NOT NULL AND date != '2025-10-20'
        GROUP BY date, home_team, away_team
        ON CONFLICT(canonical_game_id) DO UPDATE SET
            -- COALESCE: keep existing non-null value if new row doesn't have one
            nba_official_id = COALESCE(excluded.nba_official_id, canonical_games.nba_official_id),
            home_score      = COALESCE(excluded.home_score,       canonical_games.home_score),
            away_score      = COALESCE(excluded.away_score,       canonical_games.away_score),
            pace            = COALESCE(excluded.pace,             canonical_games.pace),
            referee_crew    = COALESCE(excluded.referee_crew,     canonical_games.referee_crew),
            updated_at      = datetime('now')
    """)
    conn.commit()


def seed_injury_taxonomy(conn):
    try:
        from utils.injury_taxonomy import INJURY_TAXONOMY, INJURY_LANGUAGE_MAP
    except ImportError:
        return

    c = conn.cursor()
    for code, data in INJURY_TAXONOMY.items():
        c.execute('''
            INSERT OR REPLACE INTO canonical_injury_statuses (
                status_code, category, display_name, severity_score, 
                sim_multiplier, usage_vacuum_trigger, confidence_decay_hours, 
                edge_type, actionable
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            code, data['category'], data['display_name'], data['severity_score'],
            float(data['sim_multiplier']), 1 if data['usage_vacuum_trigger'] else 0, 
            data['confidence_decay_hours'], data['edge_type'], 1 if data['actionable'] else 0
        ))

    for item in INJURY_LANGUAGE_MAP:
        c.execute('''
            INSERT OR REPLACE INTO injury_language_map (
                source_phrase, source, canonical_status, parse_type, confidence
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            item['source_phrase'], item['source'], item['canonical_status'],
            item['parse_type'], float(item['confidence'])
        ))
    conn.commit()


class LudiHistorian:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._initialize_db()
        self._ensure_prop_line_snapshots()
        self.resolver = PlayerIDResolver(db_path=db_path)

    def resolve_player_id_for_insert(self, input_id, player_name=None):
        """
        Database Firewall (4-Tier) to enforce canonical NBA ID integrity.
        
        Args:
            input_id: Raw ID from API (might be dirty, e.g. "28118035349")
            player_name: Player name for name-based fallback (e.g. "Luka Dončić")
            
        Returns:
            Canonical NBA ID (e.g. "1629029")
            
        Rules (Firewall Tiers):
            1. Exact canonical match: If input_id starts with '1' or '2' and is <= 7 chars, pass through.
            2. Alias lookup: Check 'aliases' and 'tank01_aliases' JSON columns in player_canonical_ids.
            3. Name resolution: Use PlayerIDResolver.normalize_name + auto-register input_id as alias.
            4. Fallback: Return original input_id + logger.warning()
        """
        input_id = str(input_id).strip() if input_id else ""
        if not input_id and not player_name:
            return input_id # nothing to work with — bail
        
        # If input_id is empty but player_name exists, fall through to Tier 3 name resolution
            
        # Tier 1: Exact canonical match (pass through)
        # Dirty ID Rule: len(str(id)) > 7 OR not str(id).startswith(('1','2'))
        is_dirty = len(input_id) > 7 or not input_id.startswith(('1', '2'))
        
        if not is_dirty:
            # Check if it actually exists in canonical table to be sure
            conn = self._get_conn()
            row = conn.execute("SELECT 1 FROM player_canonical_ids WHERE canonical_id = ?", (input_id,)).fetchone()
            conn.close()
            if row:
                return input_id
                
        # Tier 2: Alias lookup (aliases or tank01_aliases)
        conn = self._get_conn()
        if input_id:
            row = conn.execute("""
                SELECT canonical_id FROM player_canonical_ids 
                WHERE (aliases LIKE ? OR tank01_aliases LIKE ?)
            """, (f'%"{input_id}"%', f'%"{input_id}"%')).fetchone()
            
            if row:
                canonical_id = row[0]
                conn.close()
                return canonical_id
            
        # Tier 3: Name-based resolution + best-effort alias registration
        if player_name:
            try:
                canonical_id = self.resolver.resolve_to_canonical_id(player_name)
            except (ValueError, Exception):
                canonical_id = None

            if canonical_id:
                # Best-effort alias registration — fail fast (1s), never block caller
                if is_dirty:
                    try:
                        alias_conn = sqlite3.connect(self.db_path, timeout=1)
                        alias_conn.execute("PRAGMA busy_timeout=1000")
                        row = alias_conn.execute(
                            "SELECT tank01_aliases FROM player_canonical_ids WHERE canonical_id = ?",
                            (canonical_id,)
                        ).fetchone()
                        if row:
                            aliases = json.loads(row[0]) if row[0] else []
                            if input_id not in aliases:
                                aliases.append(input_id)
                                alias_conn.execute(
                                    "UPDATE player_canonical_ids SET tank01_aliases = ?, updated_at = CURRENT_TIMESTAMP WHERE canonical_id = ?",
                                    (json.dumps(aliases), canonical_id)
                                )
                                alias_conn.commit()
                                logger.info(f"Auto-registered Tank01 alias: {input_id} -> {canonical_id} ({player_name})")
                        alias_conn.close()
                    except Exception:
                        pass  # Non-blocking — alias will be registered on next successful run
                conn.close()
                return canonical_id  # ALWAYS return canonical ID when Tier 3 succeeds

        # Tier 4: Fallback with warning
        if is_dirty:
            logger.warning(f"Database Firewall: ID '{input_id}' ({player_name}) is dirty and could not be resolved.")
        try:
            conn.close()
        except Exception:
            pass
        return input_id

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
                started INTEGER,
                fantasy_pts_dk REAL,
                fantasy_pts_fd REAL,
                home_or_away TEXT,
                double_doubles INTEGER,
                triple_doubles INTEGER,
                video_available INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # SportsDataIO Columns Migration
        for col_def in [
            "started INTEGER",
            "fantasy_pts_dk REAL",
            "fantasy_pts_fd REAL",
            "home_or_away TEXT",
            "double_doubles INTEGER",
            "triple_doubles INTEGER"
        ]:
            try:
                c.execute(f"ALTER TABLE player_game_logs ADD COLUMN {col_def}")
            except Exception:
                pass

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
            except Exception as e:
                print(f"[TAG] Context: {e}")
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
        except Exception as e:
            print(f"[TAG] Context: {e}")
            pass  # Column already exists

        try:
            c.execute('ALTER TABLE players ADD COLUMN is_active BOOLEAN DEFAULT 1')
        except Exception as e:
            print(f"[TAG] Context: {e}")
            pass  # Column already exists

        try:
            c.execute('ALTER TABLE players ADD COLUMN roster_updated_at TIMESTAMP')
        except Exception as e:
            print(f"[TAG] Context: {e}")
            pass  # Column already exists

        # Add composite index for season-aware roster queries
        c.execute('CREATE INDEX IF NOT EXISTS idx_players_season_team ON players(season_id, team, is_active)')

        # 9. Referee Profiles Table (Module G v2.0 - Jan 15, 2026)
        c.execute('''
            CREATE TABLE IF NOT EXISTS referee_profiles (
                referee_id INTEGER PRIMARY KEY AUTOINCREMENT,
                referee_name TEXT UNIQUE NOT NULL,
                badge_number INT,
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
        
        # Migration: Add badge_number column if not exists
        try:
            c.execute("ALTER TABLE referee_profiles ADD COLUMN badge_number INT")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ref_badge ON referee_profiles(badge_number)")
        except Exception:
            pass  # Column already exists

        # Migration: Rolling window + season tracking columns (Feb 2026)
        # rolling_21d_fouls  — avg fouls/ref over last 21 days (short-term trend)
        # rolling_21d_games  — number of games in the 21-day window (confidence signal)
        # games_worked       — total games tracked this season (season sample size)
        for col_def in [
            "ALTER TABLE referee_profiles ADD COLUMN rolling_21d_fouls REAL",
            "ALTER TABLE referee_profiles ADD COLUMN rolling_21d_games INTEGER DEFAULT 0",
            "ALTER TABLE referee_profiles ADD COLUMN games_worked INTEGER DEFAULT 0",
        ]:
            try:
                c.execute(col_def)
            except Exception:
                pass  # Column already exists

        # 9b. Referee Game Assignments Crosswalk (Mar 2026)
        # Keyed by (game_date, home_team) — decoupled from games.game_id format.
        # Survives BDL fallback, Odds API quota exhaustion, or any game_id change.
        # Written by build_ref_database() after every scrape (Playwright or Perplexity).
        # Read by build_ref_database() DB-first check instead of games.referee_crew.
        c.execute('''
            CREATE TABLE IF NOT EXISTS referee_game_assignments (
                game_date  TEXT NOT NULL,
                home_team  TEXT NOT NULL,
                crew       TEXT NOT NULL,
                source     TEXT DEFAULT 'nba_official',
                scraped_at TEXT DEFAULT (datetime('now')),
                PRIMARY KEY (game_date, home_team)
            )
        ''')

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
                fta_impact_vs_avg REAL DEFAULT NULL,  -- FTA delta vs player baseline (Phase 2 delta, Mar 2026)
                pf_impact_vs_avg REAL DEFAULT NULL,   -- PF delta vs player baseline (foul-trouble signal)
                last_updated DATE,
                PRIMARY KEY (referee_id, player_id),
                FOREIGN KEY (referee_id) REFERENCES referee_profiles(referee_id)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_ref_bias_player ON referee_player_bias(player_id)')
        # Migration: add delta columns to existing DBs (safe to re-run)
        for _col, _type in [('fta_impact_vs_avg', 'REAL'), ('pf_impact_vs_avg', 'REAL')]:
            try:
                c.execute(f'ALTER TABLE referee_player_bias ADD COLUMN {_col} {_type} DEFAULT NULL')
            except Exception:
                pass  # column already exists

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

        # player_injuries table (Phase 8.0 - Injury Intelligence)
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_injuries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                team_abbreviation TEXT,
                status TEXT NOT NULL,
                injury_type TEXT,
                return_date TEXT,
                days_out INTEGER,
                onset_date TEXT,
                description TEXT,
                source TEXT,
                snapshot_time TEXT DEFAULT CURRENT_TIMESTAMP,
                is_game_day_report BOOLEAN DEFAULT 0,
                resolved_at TEXT
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_injuries_player_latest ON player_injuries(player_name, snapshot_time DESC)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_injuries_game_day ON player_injuries(snapshot_time, is_game_day_report)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_injuries_active ON player_injuries(status, resolved_at)')

        # canonical_injury_statuses (Phase 8 Module D Overhaul)
        c.execute('''
            CREATE TABLE IF NOT EXISTS canonical_injury_statuses (
                status_code TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                display_name TEXT NOT NULL,
                severity_score INTEGER NOT NULL,
                sim_multiplier REAL NOT NULL,
                usage_vacuum_trigger BOOLEAN NOT NULL,
                confidence_decay_hours INTEGER NOT NULL,
                edge_type TEXT NOT NULL,
                actionable BOOLEAN NOT NULL
            )
        ''')

        # injury_language_map (Phase 8 Module D Overhaul)
        c.execute('''
            CREATE TABLE IF NOT EXISTS injury_language_map (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_phrase TEXT NOT NULL,
                source TEXT NOT NULL,
                canonical_status TEXT NOT NULL,
                parse_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                FOREIGN KEY(canonical_status) REFERENCES canonical_injury_statuses(status_code),
                UNIQUE(source, source_phrase)
            )
        ''')

        # Add injury columns to players table (Phase 8.0)
        try:
            c.execute('ALTER TABLE players ADD COLUMN current_injury_status TEXT DEFAULT \'ACTIVE\'')
        except Exception as e:
            print(f"[TAG] Context: {e}")
            pass

        try:
            c.execute('ALTER TABLE players ADD COLUMN injury_updated_at TEXT')
        except Exception as e:
            print(f"[TAG] Context: {e}")
            pass

        try:
            c.execute('ALTER TABLE players ADD COLUMN injury_return_date TEXT')
        except Exception as e:
            print(f"[TAG] Context: {e}")
            pass

        try:
            c.execute('ALTER TABLE players ADD COLUMN days_out_current INTEGER DEFAULT 0')
        except Exception as e:
            print(f"[TAG] Context: {e}")
            pass

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

        # game_notes_log: stores Claude-generated S.A.V.A.G.E. game notes (Phase 8.6)
        c.execute('''
            CREATE TABLE IF NOT EXISTS game_notes_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                run_date TEXT NOT NULL,
                notes_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(game_id, run_date)
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_game_notes_run_date
                ON game_notes_log(run_date, game_id)
        ''')

        # rotation_profiles: per-player situational minutes profile (Phase 8.9)
        c.execute('''
            CREATE TABLE IF NOT EXISTS rotation_profiles (
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_abbreviation TEXT NOT NULL,
                avg_minutes REAL,
                std_minutes REAL,
                min_minutes REAL,
                max_minutes REAL,
                games_started INTEGER,
                games_played INTEGER,
                start_rate REAL,
                avg_min_as_starter REAL,
                avg_min_off_bench REAL,
                avg_min_blowout_win REAL,
                avg_min_blowout_loss REAL,
                avg_min_close_game REAL,
                avg_min_b2b REAL,
                depth_order INTEGER,
                position TEXT,
                window_days INTEGER DEFAULT 21,
                games_on_current_team INTEGER DEFAULT NULL,
                computed_at TEXT NOT NULL,
                UNIQUE(player_id, team_abbreviation, window_days)
            )
        ''')
        # Migration guard for existing installs (Phase 8.12)
        try:
            c.execute('ALTER TABLE rotation_profiles ADD COLUMN games_on_current_team INTEGER DEFAULT NULL')
        except Exception as e:
            print(f"[TAG] Context: {e}")
            pass  # Column already exists
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_rotation_profiles_player
                ON rotation_profiles(player_id, window_days)
        ''')

        # player_foul_splits: rolling 21-day foul stats for Phase 8.17 Foul Intelligence
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_foul_splits (
                player_id INTEGER,
                player_name TEXT NOT NULL,
                season TEXT NOT NULL DEFAULT '2025-26',

                -- Rolling 21-day window stats (sourced from player_game_logs.pf)
                games_in_window INT DEFAULT 0,
                avg_pf_per_game REAL DEFAULT 0.0,
                pf_per_36_min REAL DEFAULT 0.0,
                games_4plus_fouls INT DEFAULT 0,
                pct_games_4plus_fouls REAL DEFAULT 0.0,  -- 0.0 to 1.0

                -- Archetype context
                archetype TEXT,

                -- Minutes impact (cross-referenced from player_game_logs.minutes + pf)
                avg_min_normal REAL,           -- avg MIN when pf < 4
                avg_min_foul_trouble REAL,     -- avg MIN when pf >= 4
                min_dampener REAL DEFAULT 1.0, -- recommended multiplier (0.70–1.0)

                -- Referee sensitivity (cross-referenced with games.referee_crew + referee_profiles.style)
                avg_pf_vs_strict REAL,         -- avg PF when ref style = 'STRICT'
                avg_pf_vs_lenient REAL,        -- avg PF when ref style = 'LENIENT'

                data_confidence TEXT DEFAULT 'LOW',  -- HIGH (>=15g) / MEDIUM (>=8g) / LOW
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (player_id, season)
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_foul_splits_name
            ON player_foul_splits(player_name)
        ''')

        # beneficiary_minutes: when player X is out, who gets extra minutes? (Phase 8.9)
        c.execute('''
            CREATE TABLE IF NOT EXISTS beneficiary_minutes (
                out_player_id TEXT NOT NULL,
                out_player_name TEXT NOT NULL,
                team_abbreviation TEXT NOT NULL,
                beneficiary_player_id TEXT NOT NULL,
                beneficiary_player_name TEXT NOT NULL,
                games_without INTEGER,
                avg_minutes_without REAL,
                avg_minutes_with REAL,
                minutes_delta REAL,
                sample_start TEXT,
                sample_end TEXT,
                computed_at TEXT NOT NULL,
                UNIQUE(out_player_id, beneficiary_player_id, team_abbreviation)
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_beneficiary_out_player
                ON beneficiary_minutes(out_player_id, team_abbreviation)
        ''')

        # Phase 8.9-B: Stagger stats — two-man pairing on/off splits
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_stagger_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_abbreviation TEXT NOT NULL,
                partner_player_id TEXT NOT NULL,
                partner_player_name TEXT NOT NULL,
                season TEXT DEFAULT '2025-26',
                min_with REAL,
                pts_with REAL,
                ast_with REAL,
                reb_with REAL,
                usg_with REAL,
                ortg_with REAL,
                min_without REAL,
                pts_without REAL,
                ast_without REAL,
                reb_without REAL,
                usg_without REAL,
                ortg_without REAL,
                pts_delta REAL,
                ast_delta REAL,
                reb_delta REAL,
                usg_delta REAL,
                games_sample INTEGER,
                synced_at TEXT NOT NULL,
                UNIQUE(player_id, partner_player_id, team_abbreviation, season)
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_stagger_player
                ON player_stagger_stats(player_id, team_abbreviation)
        ''')

        # Phase 8.9-B: Stint profiles — aggregated substitution patterns per player
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_stint_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                team_abbreviation TEXT NOT NULL,
                season TEXT DEFAULT '2025-26',
                avg_stints_per_game REAL,
                avg_first_stint_min REAL,
                avg_stint_length REAL,
                pct_games_q4_starter REAL,
                avg_min_q4 REAL,
                avg_min_q4_when_close REAL,
                avg_min_q4_blowout REAL,
                games_sample INTEGER,
                synced_at TEXT NOT NULL,
                UNIQUE(player_id, team_abbreviation, season)
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_stint_player
                ON player_stint_profiles(player_id, team_abbreviation)
        ''')

        # NBA Calendar Table (Phase 8 — Schedule Awareness)
        # Separate from `games` table (which is analytics/results).
        # This is schedule metadata only — has rows for EVERY date including off-days.
        c.execute('''
            CREATE TABLE IF NOT EXISTS nba_calendar (
                date         TEXT PRIMARY KEY,
                season       TEXT NOT NULL,
                has_games    INTEGER NOT NULL DEFAULT 0,
                game_count   INTEGER DEFAULT 0,
                season_phase TEXT NOT NULL DEFAULT 'regular',
                notes        TEXT,
                synced_at    TEXT NOT NULL
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_nba_calendar_phase
                ON nba_calendar(season_phase, date)
        ''')

        # Player Trends Table (Phase 8.15)
        # Pre-computed daily: L7/L10/L15 averages, season avg, trend labels, streak vs season avg.
        # Stat types: PTS, REB, AST, 3PM, BLK, STL, TOV, PRA, PA, PR, RA, MIN
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_trends (
                player_id          TEXT NOT NULL,
                player_name        TEXT NOT NULL,
                team_abbreviation  TEXT NOT NULL,
                stat               TEXT NOT NULL,
                l7_avg             REAL,
                l10_avg            REAL,
                l15_avg            REAL,
                season_avg         REAL,
                trend_delta        REAL,
                trend_label        TEXT,
                streak_vs_avg      INTEGER,
                games_found        INTEGER,
                computed_at        TEXT NOT NULL,
                UNIQUE(player_id, stat, team_abbreviation)
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_player_trends_lookup
                ON player_trends(player_name, team_abbreviation, stat)
        ''')

        # ---------------------------------------------------------------------------
        # Tank01 Enrichment Tables (Phase 8 expansion)
        # ---------------------------------------------------------------------------

        # Tank01 fantasy projections — READ-ONLY benchmark, never fed into SAVAGE model
        c.execute('''
            CREATE TABLE IF NOT EXISTS tank01_projections (
                player_id    TEXT NOT NULL,
                game_date    TEXT NOT NULL,
                pts          REAL,
                reb          REAL,
                ast          REAL,
                stl          REAL,
                blk          REAL,
                tov          REAL,
                fantasy_pts  REAL,
                fetched_at   TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_id, game_date)
            )
        ''')

        # Team standings + win/loss streaks — synced daily from getNBACurrentInfo
        c.execute('''
            CREATE TABLE IF NOT EXISTS team_current_info (
                team_abv          TEXT PRIMARY KEY,
                wins              INTEGER,
                losses            INTEGER,
                win_streak        INTEGER,
                loss_streak       INTEGER,
                conference_rank   INTEGER,
                next_game_date    TEXT,
                fetched_at        TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Daily player/team news cache — synced once/day from getNBATopNews
        # Deduplication handled by (headline, published_at) uniqueness at insert time
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_news_cache (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name  TEXT,
                team_abv     TEXT,
                headline     TEXT,
                content      TEXT,
                published_at TEXT,
                fetched_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_player_news_lookup
                ON player_news_cache(player_name, fetched_date)
        ''')

        # Historical injury records — Tank01 getNBAInjuryListHistory confirmed dead (404)
        # Table kept for potential future BDL/Perplexity-sourced historical data
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_injury_history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id    TEXT,
                player_name  TEXT,
                injury_date  TEXT,
                return_date  TEXT,
                injury_type  TEXT,
                status       TEXT,
                games_missed INTEGER,
                UNIQUE(player_id, injury_date, injury_type)
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_injury_history_player
                ON player_injury_history(player_id, injury_date)
        ''')


        # =====================================================================
        # MIGRATION: Box Score Enrichment + BDL V2 Advanced Stats (Sprint A/B/D)
        # Added: 2026-02-22
        # =====================================================================

        # -- Sprint A: player_game_logs new columns --
        sprint_a_cols = [
            ('player_game_logs', 'started TINYINT'),
            ('player_game_logs', 'fantasy_pts_dk REAL'),
            ('player_game_logs', 'fantasy_pts_fd REAL'),
            ('player_game_logs', 'home_or_away TEXT'),
            ('player_game_logs', 'double_doubles INT'),
            ('player_game_logs', 'triple_doubles INT'),
        ]
        for table, col_def in sprint_a_cols:
            col_name = col_def.split()[0]
            try:
                c.execute(f'ALTER TABLE {table} ADD COLUMN {col_def}')
                print(f'[MIGRATION] Added {col_name} to {table}')
            except Exception as e:
                print(f'[MIGRATION] {table}.{col_name}: {e}')
                pass  # Column already exists

        # -- Sprint B: player_game_advanced BDL V2 columns --
        sprint_b_advanced_cols = [
            'points_paint INT',
            'points_fast_break INT',
            'points_second_chance INT',
            'points_off_turnovers INT',
            'estimated_off_rating REAL',
            'estimated_def_rating REAL',
            'estimated_net_rating REAL',
            'pct_pts_paint REAL',
            'pct_pts_fast_break REAL',
            'pct_pts_free_throw REAL',
            'pct_pts_midrange_2pt REAL',
            'bdl_source TINYINT DEFAULT 0',
        ]
        for col_def in sprint_b_advanced_cols:
            col_name = col_def.split()[0]
            try:
                c.execute(f'ALTER TABLE player_game_advanced ADD COLUMN {col_def}')
                print(f'[MIGRATION] Added {col_name} to player_game_advanced')
            except Exception as e:
                print(f'[MIGRATION] player_game_advanced.{col_name}: {e}')
                pass  # Column already exists

        # -- Sprint B: player_game_tracking BDL V2 columns (speed/distance/touches/passes only) --
        sprint_b_tracking_cols = [
            'speed REAL',
            'distance REAL',
            'touches INT',
            'passes INT',
            'bdl_source TINYINT DEFAULT 0',
        ]
        for col_def in sprint_b_tracking_cols:
            col_name = col_def.split()[0]
            try:
                c.execute(f'ALTER TABLE player_game_tracking ADD COLUMN {col_def}')
                print(f'[MIGRATION] Added {col_name} to player_game_tracking')
            except Exception as e:
                print(f'[MIGRATION] player_game_tracking.{col_name}: {e}')
                pass  # Column already exists

        # -- Sprint B: player_game_hustle bdl_source flag --
        try:
            c.execute('ALTER TABLE player_game_hustle ADD COLUMN bdl_source TINYINT DEFAULT 0')
            print('[MIGRATION] Added bdl_source to player_game_hustle')
        except Exception as e:
            print(f'[MIGRATION] player_game_hustle.bdl_source: {e}')
            pass  # Column already exists

        # -- Sprint D: player_season_averages_bdl (BDL V2 season-level aggregates) --
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_season_averages_bdl (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                canonical_id  TEXT,
                player_id     INTEGER,
                player_name   TEXT,
                team_abbrev   TEXT,
                season        INT,
                category      TEXT,
                stat_type     TEXT,
                stats_json    TEXT,
                ppp           REAL,
                poss_pct      REAL,
                efg_pct       REAL,
                drives        INT,
                avg_speed     REAL,
                dist_miles    REAL,
                deflections   REAL,
                box_outs      REAL,
                screen_assists REAL,
                updated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, season, category, stat_type)
            )
        ''')

        # -- Sprint D: team_standings_bdl (BDL V2 standings) --
        c.execute('''
            CREATE TABLE IF NOT EXISTS team_standings_bdl (
                team_id        INTEGER PRIMARY KEY,
                team_name      TEXT,
                team_abbrev    TEXT,
                wins           INT,
                losses         INT,
                win_pct        REAL,
                conference     TEXT,
                conference_rank INT,
                division       TEXT,
                division_rank  INT,
                home_wins      INT,
                home_losses    INT,
                away_wins      INT,
                away_losses    INT,
                last_ten_wins  INT,
                streak         TEXT,
                season         INT,
                updated_at     TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # -- Module G: team_betting_trends (H/A records + scoring averages from internal data) --
        c.execute('''
            CREATE TABLE IF NOT EXISTS team_betting_trends (
                team             TEXT PRIMARY KEY,
                home_wins        INTEGER DEFAULT 0,
                home_losses      INTEGER DEFAULT 0,
                away_wins        INTEGER DEFAULT 0,
                away_losses      INTEGER DEFAULT 0,
                home_ats_wins    INTEGER DEFAULT 0,
                home_ats_losses  INTEGER DEFAULT 0,
                away_ats_wins    INTEGER DEFAULT 0,
                away_ats_losses  INTEGER DEFAULT 0,
                home_avg_score   REAL,
                home_avg_allowed REAL,
                away_avg_score   REAL,
                away_avg_allowed REAL,
                avg_game_total   REAL,
                games_tracked    INTEGER DEFAULT 0,
                ats_games_tracked INTEGER DEFAULT 0,
                last_updated     TIMESTAMP
            )
        ''')

        # -- Phase 2A: player_trends cross-season signal columns --
        for col in [
            ('prior_season_avg', 'REAL'),
            ('season_delta_pct', 'REAL'),
            ('trend_signal', 'TEXT'),
        ]:
            try:
                c.execute(f'ALTER TABLE player_trends ADD COLUMN {col[0]} {col[1]}')
                print(f'[MIGRATION] Added player_trends.{col[0]}')
            except Exception:
                pass  # Column already exists

        # -- Phase 2A: Backfill season_id in player_game_logs (idempotent) --
        try:
            # Fix any corrupt legacy values before backfilling NULLs
            c.execute("""
                UPDATE player_game_logs SET season_id = '2025-26'
                WHERE game_date >= '2025-10-01' AND (season_id IS NULL OR season_id NOT IN ('2024-25','2025-26'))
            """)
            c.execute("""
                UPDATE player_game_logs SET season_id = '2024-25'
                WHERE game_date < '2025-10-01' AND (season_id IS NULL OR season_id NOT IN ('2024-25','2025-26'))
            """)
        except Exception as e:
            print(f'[MIGRATION] season_id backfill: {e}')

        # -- Sprint 2: player_wowy_observed trade-awareness + role scoring columns --
        for col in [
            ('star_games_on_team', 'INT'),
            ('star_archetype',     'TEXT'),
            ('ben_archetype',      'TEXT'),
            ('role_match_score',   'REAL'),
            ('confidence_adjusted','TEXT'),
            ('star_position',      'TEXT'),   # Sprint 3: off/def + position axis
            ('ben_position',       'TEXT'),
        ]:
            try:
                c.execute(f'ALTER TABLE player_wowy_observed ADD COLUMN {col[0]} {col[1]}')
                print(f'[MIGRATION] Added player_wowy_observed.{col[0]}')
            except Exception:
                pass  # Column already exists

        # -- Phase 2B: Starter-filtered WOWY observed beneficiary performance --
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_wowy_observed (
                canonical_id        TEXT,
                star_canonical_id   TEXT,
                team_abbreviation   TEXT,
                obs_pts             REAL,
                obs_reb             REAL,
                obs_ast             REAL,
                obs_min             REAL,
                obs_fga             REAL,
                obs_usg_proxy       REAL,
                base_pts            REAL,
                base_min            REAL,
                pts_delta           REAL,
                min_delta           REAL,
                obs_games           INT,
                base_games          INT,
                confidence          TEXT,
                star_games_on_team  INT,
                star_archetype      TEXT,
                ben_archetype       TEXT,
                role_match_score    REAL,
                confidence_adjusted TEXT,
                star_position       TEXT,
                ben_position        TEXT,
                updated_at          TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(canonical_id, star_canonical_id)
            )
        ''')

        # -- Canonical ID mapping (restored Feb 2026 — was orphaned; creation script lost) --
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_canonical_ids (
                canonical_id     TEXT PRIMARY KEY,
                full_name        TEXT NOT NULL,
                normalized_name  TEXT NOT NULL UNIQUE,
                team             TEXT,
                position         TEXT,
                is_active        INTEGER DEFAULT 1,
                tank01_aliases   TEXT,
                nba_api_id       TEXT,
                sportsdata_id    TEXT,
                dk_player_id     TEXT,
                fd_player_id     TEXT,
                espn_id          TEXT,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        c.execute("CREATE INDEX IF NOT EXISTS idx_canonical_norm ON player_canonical_ids(normalized_name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_canonical_active ON player_canonical_ids(is_active)")
        # Migration guard: add espn_id to existing DBs that pre-date this column
        try:
            c.execute("ALTER TABLE player_canonical_ids ADD COLUMN espn_id TEXT")
        except Exception:
            pass  # Column already exists — safe to ignore
        # Migration guard: add tank01_player_id for Tank01 crosswalk (A6)
        try:
            c.execute("ALTER TABLE player_canonical_ids ADD COLUMN tank01_player_id TEXT")
        except Exception:
            pass  # Column already exists — safe to ignore

        # Migration guard: add aliases JSON column for generic ID/name mapping (A7)
        try:
            c.execute("ALTER TABLE player_canonical_ids ADD COLUMN aliases TEXT DEFAULT '[]'")
        except Exception:
            pass  # Column already exists — safe to ignore

        # Migration guard: add confirmation_score for hit rate modifier (C1)
        try:
            c.execute("ALTER TABLE bet_recommendations ADD COLUMN confirmation_score REAL")
        except Exception:
            pass  # Column already exists — safe to ignore

        # Migration guards: team_scheme_cache quality columns (D3)
        for col_def in [
            "off_quality_14d TEXT",
            "def_quality_14d TEXT",
            "def_rating_14d REAL",  # D3: numeric def rating (not just tier label)
        ]:
            try:
                c.execute(f"ALTER TABLE team_scheme_cache ADD COLUMN {col_def}")
            except Exception:
                pass  # Column already exists — safe to ignore

        # Migration guards: team_standings_bdl advanced stats columns (E1)
        for col_def in [
            "ortg REAL",   # offensive rating
            "drtg REAL",   # defensive rating
            "pace REAL",   # pace (possessions per game)
        ]:
            try:
                c.execute(f"ALTER TABLE team_standings_bdl ADD COLUMN {col_def}")
            except Exception:
                pass  # Column already exists — safe to ignore

        # -- Canonical ID staging table (auto-ingest missing IDs for review) --
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_canonical_ids_staging (
                source           TEXT NOT NULL,
                source_player_id TEXT NOT NULL,
                player_name      TEXT NOT NULL,
                normalized_name  TEXT,
                first_game_date  TEXT,
                last_game_date   TEXT,
                seen_count       INTEGER DEFAULT 1,
                first_seen_at    TEXT NOT NULL,
                last_seen_at     TEXT NOT NULL,
                PRIMARY KEY (source, source_player_id)
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_canonical_staging_last_seen
                ON player_canonical_ids_staging(last_seen_at)
        ''')

        # -- 30-team canonical crosswalk: standard_abbr ↔ BDL / Tank01 / ESPN IDs --
        # Foundation for Phase 8.21 ESPN full integration.
        # bdl_abbr = NULL means team abbr matches standard (e.g. ATL, BOS, CHI...).
        # Only 5 teams differ from BDL: GS, NO, NY, PHO, SA.
        c.execute('''
            CREATE TABLE IF NOT EXISTS canonical_teams (
                standard_abbr  TEXT PRIMARY KEY,   -- our internal standard: GSW, NOP, NYK, PHX, SAS
                full_name      TEXT NOT NULL,
                bdl_abbr       TEXT,               -- BDL short code; NULL if same as standard_abbr
                tank01_abbr    TEXT,               -- same as BDL for all 30 teams
                espn_id        INTEGER             -- ESPN numeric team ID (stable, 1-30)
            )
        ''')
        _team_seed = [
            ('ATL', 'Atlanta Hawks',          None,  None,  1),
            ('BOS', 'Boston Celtics',         None,  None,  2),
            ('NOP', 'New Orleans Pelicans',   'NO',  'NO',  3),
            ('CHI', 'Chicago Bulls',          None,  None,  4),
            ('CLE', 'Cleveland Cavaliers',    None,  None,  5),
            ('DAL', 'Dallas Mavericks',       None,  None,  6),
            ('DEN', 'Denver Nuggets',         None,  None,  7),
            ('DET', 'Detroit Pistons',        None,  None,  8),
            ('GSW', 'Golden State Warriors',  'GS',  'GS',  9),
            ('HOU', 'Houston Rockets',        None,  None,  10),
            ('IND', 'Indiana Pacers',         None,  None,  11),
            ('LAC', 'LA Clippers',            None,  None,  12),
            ('LAL', 'Los Angeles Lakers',     None,  None,  13),
            ('MIA', 'Miami Heat',             None,  None,  14),
            ('MIL', 'Milwaukee Bucks',        None,  None,  15),
            ('MIN', 'Minnesota Timberwolves', None,  None,  16),
            ('BKN', 'Brooklyn Nets',          None,  None,  17),
            ('NYK', 'New York Knicks',        'NY',  'NY',  18),
            ('ORL', 'Orlando Magic',          None,  None,  19),
            ('PHI', 'Philadelphia 76ers',     None,  None,  20),
            ('PHX', 'Phoenix Suns',           'PHO', 'PHO', 21),
            ('POR', 'Portland Trail Blazers', None,  None,  22),
            ('SAC', 'Sacramento Kings',       None,  None,  23),
            ('SAS', 'San Antonio Spurs',      'SA',  'SA',  24),
            ('OKC', 'Oklahoma City Thunder',  None,  None,  25),
            ('UTA', 'Utah Jazz',              None,  None,  26),
            ('WAS', 'Washington Wizards',     None,  None,  27),
            ('TOR', 'Toronto Raptors',        None,  None,  28),
            ('MEM', 'Memphis Grizzlies',      None,  None,  29),
            ('CHA', 'Charlotte Hornets',      None,  None,  30),
        ]
        c.executemany(
            "INSERT OR IGNORE INTO canonical_teams "
            "(standard_abbr, full_name, bdl_abbr, tank01_abbr, espn_id) VALUES (?,?,?,?,?)",
            _team_seed
        )

        # -- Canonical Games: single source of truth for game identity (Feb 28, 2026) --
        # The games table stores up to 3 row formats per game from different sources:
        #   0022500001    (NBA official format — from Module H / Tank01)
        #   22500001      (shortened format — from BDL backfill)
        #   20251021_HOU@OKC (date-team format — from populate_todays_games / Module G)
        #
        # Any JOIN on games using date + team pair (Pattern B) returns 3× rows.
        # canonical_games deduplicates to exactly ONE row per game, using standard_abbr
        # from canonical_teams for both home_team and away_team.
        #
        # PRIMARY KEY: {date}_{home_team}_{away_team} — e.g. "2025-10-21_OKC_HOU"
        # Refreshed by sync_canonical_games(conn) — callable from any game writer.
        # Pattern mirrors canonical_teams: seed once, upsert daily as data enriches.
        c.execute('''
            CREATE TABLE IF NOT EXISTS canonical_games (
                canonical_game_id  TEXT PRIMARY KEY,   -- {date}_{home}_{away} e.g. 2025-10-21_OKC_HOU
                date               TEXT NOT NULL,
                home_team          TEXT NOT NULL,      -- canonical_teams.standard_abbr
                away_team          TEXT NOT NULL,      -- canonical_teams.standard_abbr
                nba_official_id    TEXT,               -- 0022500001 format; NULL until Module H resolves
                home_score         INTEGER,
                away_score         INTEGER,
                pace               REAL,
                referee_crew       TEXT,
                created_at         TEXT DEFAULT (datetime('now')),
                updated_at         TEXT DEFAULT (datetime('now')),
                UNIQUE(date, home_team, away_team)
            )
        ''')
        c.execute("CREATE INDEX IF NOT EXISTS idx_cg_date   ON canonical_games(date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_cg_teams  ON canonical_games(home_team, away_team)")

        # -- Player news staging: discovered players from RSS feeds not in canonical_ids --
        # Enables tracking of rookies, two-ways, and call-ups found via news blurbs.
        # Auto-promotes to player_canonical_ids after 3+ consistent appearances.
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_news_staging (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name         TEXT NOT NULL,
                team_abbreviation   TEXT,
                source              TEXT NOT NULL,
                headline            TEXT,
                description        TEXT,
                status_extracted   TEXT,
                confidence         REAL,
                first_seen_at      TEXT NOT NULL,
                last_seen_at       TEXT NOT NULL,
                seen_count         INTEGER DEFAULT 1,
                is_reviewed        INTEGER DEFAULT 0,
                UNIQUE(player_name, source)
            )
        ''')
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_news_staging_player
                ON player_news_staging(player_name, last_seen_at)
        ''')

        # -- Player type profiles: unified per-player type layer (Feb 25, 2026) --
        # Consolidates archetype + defensive_tag + top-3 NBA Synergy playtypes
        # + position-synergy match validation into one queryable row per player.
        # Built by scripts/build_classification_profiles.py::build_player_type_profiles()
        # Refreshed weekly (weekly_validation.yml) after classify_archetypes runs.
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_type_profiles (
                player_name          TEXT NOT NULL,
                team                 TEXT,
                position             TEXT,
                -- Our classification system
                archetype            TEXT,        -- primary offensive identity (15 types)
                defensive_tag        TEXT,        -- defensive role (5 types)
                -- NBA Synergy types (raw names, top 3 by freq, ≥75 total possessions)
                synergy_type_1       TEXT,        -- e.g. POST_UP (highest freq)
                synergy_freq_1       REAL,        -- freq% e.g. 20.1
                synergy_ppp_1        REAL,        -- Points Per Possession
                synergy_type_2       TEXT,
                synergy_freq_2       REAL,
                synergy_ppp_2        REAL,
                synergy_type_3       TEXT,
                synergy_freq_3       REAL,
                synergy_ppp_3        REAL,
                -- Our internal translated names (ISO_SCORER, P&R_HANDLER, etc.)
                synergy_tag_1        TEXT,
                synergy_tag_2        TEXT,
                synergy_tag_3        TEXT,
                -- Position-playtype validation: 1=match, 0=mismatch
                -- e.g. Jokić (C) with PR_BALL_HANDLER #1 → position_synergy_match=0
                position_synergy_match INTEGER DEFAULT 1,
                -- Archetype-synergy alignment check
                archetype_primary_tag   TEXT,    -- what archetype_synergy_map expects
                archetype_in_top3       INTEGER, -- 1 if archetype's tag appears in top 3 synergy
                season               TEXT DEFAULT '2025-26',
                updated_at           TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (player_name, season)
            )
        ''')
        c.execute("CREATE INDEX IF NOT EXISTS idx_ptp_archetype ON player_type_profiles(archetype)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ptp_team ON player_type_profiles(team)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_ptp_def_tag ON player_type_profiles(defensive_tag)")

        # Sprint 1 — Empirical Modifiers
        # Computed nightly by scripts/compute_empirical_modifiers.py (1-3 AM window).
        # Module C reads at __init__; zero DB calls during simulation.
        c.execute('''
            CREATE TABLE IF NOT EXISTS player_empirical_modifiers (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name     TEXT NOT NULL,   -- normalized (accent-safe, lowercase)
                season          TEXT NOT NULL DEFAULT '2025-26',

                -- Item 1: Starter/bench role split (N >= 10 per role required)
                starter_pts_mod     REAL DEFAULT 1.0,
                starter_reb_mod     REAL DEFAULT 1.0,
                starter_ast_mod     REAL DEFAULT 1.0,
                starter_fta_mod     REAL DEFAULT 1.0,
                starter_stl_mod     REAL DEFAULT 1.0,
                starter_blk_mod     REAL DEFAULT 1.0,
                starter_fg3m_mod    REAL DEFAULT 1.0,
                starter_n           INTEGER DEFAULT 0,  -- games as starter
                bench_pts_mod       REAL DEFAULT 1.0,
                bench_reb_mod       REAL DEFAULT 1.0,
                bench_ast_mod       REAL DEFAULT 1.0,
                bench_fta_mod       REAL DEFAULT 1.0,
                bench_stl_mod       REAL DEFAULT 1.0,
                bench_blk_mod       REAL DEFAULT 1.0,
                bench_fg3m_mod      REAL DEFAULT 1.0,
                bench_n             INTEGER DEFAULT 0,  -- games as bench

                -- Item 3: Per-stat empirical stdev (N >= 30 total games)
                stdev_pts       REAL,   -- NULL if N < 30
                stdev_reb       REAL,
                stdev_ast       REAL,
                stdev_stl       REAL,
                stdev_blk       REAL,
                stdev_fg3m      REAL,
                stdev_fta       REAL,
                stdev_n         INTEGER DEFAULT 0,

                -- Item 4: WOWY lineup delta
                wowy_with_avg   REAL,   -- team net_rating when player is in lineup
                wowy_without_avg REAL,  -- team net_rating when player is out
                wowy_delta      REAL,   -- with - without (positive = player helps)
                wowy_with_n     INTEGER DEFAULT 0,
                wowy_without_n  INTEGER DEFAULT 0,

                -- Item 5: Depth chart slot (Tank01)
                depth_slot      INTEGER,  -- 1=starter, 2=backup, 3=third-string, NULL=unknown
                depth_synced_at TEXT,

                computed_at     TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_name, season)
            )
        ''')
        c.execute("CREATE INDEX IF NOT EXISTS idx_emp_mod_player ON player_empirical_modifiers(player_name)")

        # Phase 8.23 Layer 1 — Claude/Perplexity feedback loop data collection.
        # Every get_claude_analysis() call writes one row here.
        # Layer 2 (weekly): calibrate_claude_outputs.py computes Wilson accuracy per call_type.
        # Layer 3: calibration injected into _get_system_wr_context().
        # actual_outcome is NULL during Layer 1; settlement pipeline fills it retroactively.
        c.execute('''
            CREATE TABLE IF NOT EXISTS claude_analysis_log (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                call_type        TEXT,          -- 'sanity_gate','curation','game_notes','spotlight','scheme','archetype','weekly'
                model            TEXT,          -- 'claude-haiku-...' or 'claude-sonnet-...'
                input_tokens     INTEGER,
                output_tokens    INTEGER,
                game_date        TEXT,          -- nullable — context of which game date
                player_name      TEXT,          -- nullable — context of which player
                response_text    TEXT,          -- first 2000 chars of Claude response
                estimated_cost_usd REAL,        -- computed from tokens + pricing at log time
                actual_outcome   TEXT,          -- NULL during Layer 1; 'WIN'/'LOSS'/'PUSH' after settlement
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                stat_category    TEXT,
                bet_side         TEXT,
                curation_grade   TEXT,
                bet_id           INTEGER,
                true_edge        REAL,
                thinking_text    TEXT
            )
        ''')
        c.execute("CREATE INDEX IF NOT EXISTS idx_cal_call_type ON claude_analysis_log(call_type)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_cal_game_date ON claude_analysis_log(game_date)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_cal_model ON claude_analysis_log(model)")

        # News catalyst columns — written by scripts/news_agent.py, read by morning_brief.py
        for _col_def in [
            "ALTER TABLE claude_analysis_log ADD COLUMN analysis_date TEXT",
            "ALTER TABLE claude_analysis_log ADD COLUMN analysis_type TEXT",
            "ALTER TABLE claude_analysis_log ADD COLUMN has_catalyst INTEGER DEFAULT 0",
            "ALTER TABLE claude_analysis_log ADD COLUMN catalyst_type TEXT",
            "ALTER TABLE claude_analysis_log ADD COLUMN catalyst_signal TEXT",
            "ALTER TABLE claude_analysis_log ADD COLUMN catalyst_confidence REAL",
        ]:
            try:
                c.execute(_col_def)
            except Exception:
                pass  # Column already exists

        # Phase 8.23-F — Per-bet logging columns migration guard
        for _col_def in [
            "ALTER TABLE claude_analysis_log ADD COLUMN stat_category TEXT",
            "ALTER TABLE claude_analysis_log ADD COLUMN bet_side TEXT",
            "ALTER TABLE claude_analysis_log ADD COLUMN curation_grade TEXT",
            "ALTER TABLE claude_analysis_log ADD COLUMN bet_id INTEGER",
            "ALTER TABLE claude_analysis_log ADD COLUMN true_edge REAL",
            "ALTER TABLE claude_analysis_log ADD COLUMN thinking_text TEXT",
            "ALTER TABLE claude_analysis_log ADD COLUMN prompt_version TEXT",
        ]:
            try:
                c.execute(_col_def)
            except Exception:
                pass

        # Sprint 1 — lineup_id column for WOWY lineup identity
        try:
            c.execute("ALTER TABLE team_lineups ADD COLUMN lineup_id TEXT")
        except Exception:
            pass  # Column already exists

        # Phase 8.24 — Edge type label migration guard (bet_recommendations is an orphan table
        # owned by utils/bet_logger.py; guards here ensure live DBs pick up new columns too).
        try:
            c.execute("ALTER TABLE bet_recommendations ADD COLUMN edge_type TEXT DEFAULT 'Projection'")
        except Exception:
            pass  # Column already exists
        # Phase 8.26 — SGP correlation risk flag migration guard
        try:
            c.execute("ALTER TABLE bet_recommendations ADD COLUMN sgp_correlation_risk TEXT DEFAULT NULL")
        except Exception:
            pass  # Column already exists
        # Phase CLV — line_movement migration guard (how far the line moved from bet to close)
        try:
            c.execute("ALTER TABLE bet_recommendations ADD COLUMN line_movement REAL")
        except Exception:
            pass  # Column already exists

        # Module B/F — time_context: pipeline run mode (EARLY_LOOK/AFTERNOON/PRE_GAME/LOCK_TIME)
        # Enables downstream confidence framing in Ask Ludi, Ludi Lens, bet cards.
        try:
            c.execute("ALTER TABLE bet_recommendations ADD COLUMN time_context TEXT DEFAULT 'EARLY_LOOK'")
        except Exception:
            pass  # Column already exists
            
        # Part 2B: Sharp consensus schema additions

        for col in ['sharp_odds_over_at_bet INTEGER', 'sharp_odds_under_at_bet INTEGER', 'sharp_book_at_bet TEXT', 'sharp_consensus REAL']:
            try:
                c.execute(f"ALTER TABLE bet_recommendations ADD COLUMN {col}")
            except Exception:
                pass


        # Seed canonical_games from any games data already in the DB.
        # Uses the same sync_canonical_games() function available to all game writers.
        _sync_canonical_games(conn)
        
        # Seed injury taxonomy
        seed_injury_taxonomy(conn)

        conn.commit()
        conn.close()
        # print("✅ Ludi Memory (Database) initialized successfully.")

    # -------------------------------------------------------------------------
    # Module B (LudiEngine) - Line History Table
    # Added Feb 27, 2026 - Tracks opening/closing/actual lifecycle for all prop lines
    def _ensure_prop_line_snapshots(self):
        """Create prop_line_snapshots table if it doesn't exist."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS prop_line_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_date TEXT NOT NULL,
                player_name TEXT NOT NULL,
                player_id TEXT,
                stat_category TEXT NOT NULL,
                opening_line REAL NOT NULL,
                opening_odds_over INTEGER,
                opening_odds_under INTEGER,
                opening_bookmaker TEXT,
                vendor_count INTEGER DEFAULT 1,
                source_quality TEXT,
                closing_line REAL,
                closing_odds_over INTEGER,
                closing_odds_under INTEGER,
                closing_bookmaker TEXT,
                closing_captured_at TEXT,
                actual_value REAL,
                actual_hit_over INTEGER,
                minutes_played REAL,
                team TEXT,
                opponent TEXT,
                captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
                settled_at TEXT,
                UNIQUE(game_date, player_name, stat_category)
            )
        ''')
        
        # Create indexes if they don't exist
        try:
            c.execute('''
                CREATE INDEX IF NOT EXISTS idx_prop_snapshots_player_stat
                ON prop_line_snapshots(player_name, stat_category)
            ''')
        except Exception:
            pass
        
        try:
            c.execute('''
                CREATE INDEX IF NOT EXISTS idx_prop_snapshots_date
                ON prop_line_snapshots(game_date)
            ''')
        except Exception:
            pass
        
        conn.commit()
        conn.close()

    # -------------------------------------------------------------------------
    # ORPHAN TABLES (created by migrations or scripts — NOT in CREATE TABLE above)
    # Sprint 8 DB Schema Audit (Feb 2026): 37 tables in database.py + 16 orphans = 53+ documented.
    # Each orphan is owned by the script/migration that creates it.
    #
    # Source: migrations/create_synergy_tables.sql
    #   player_synergy_playtypes  — NBA Synergy playtype data (1,326 rows)
    #   player_drives             — Drive-based play data
    #   player_touches            — Touch/possession data
    #   player_speed              — Speed/distance tracking
    #   player_defense            — Opponent defensive matchup data
    #
    # Source: migrations/migration.sql + migrations/migration_enable.sql
    #   player_canonical_ids_inactive_log  — Audit log for Phase 3 ID dedup
    #
    # Source: scripts/build_classification_profiles.py (SQLite views)
    #   player_offensive_playtype_profile  — Aggregated view for archetype classification
    #   team_offensive_playtype_profile    — Team-level playtype view
    #   player_defense_proxy_profile       — Defensive proxy metrics view
    #
    # Source: scripts/sync_assist_combos.py
    #   assist_combos             — Player-to-player assist pair frequency (BENEFICIARY aid)
    #
    # Source: scripts/sync_pbp_totals.py
    #   player_season_quality     — Season-level PBP shot quality aggregates
    #
    # Source: scripts/sync_wowy_backfill.py
    #   team_lineups              — 5-man lineup on/off data (Ghost Protocol, 10,669 rows)
    #   player_on_off_stats       — Player-level on/off efficiency splits
    #
    # Source: utils/bet_logger.py
    #   bet_recommendations       — Primary bet log (15,575+ records, settlement target)
    #   bet_daily_summaries       — Daily P&L rollup (one row per date)
    #
    # Restored to init_db() above (Feb 2026):
    #   player_canonical_ids      — ID mapping table (559+ rows); CREATE TABLE restored Feb 24 2026
    #   canonical_teams           — 30-team BDL/Tank01/ESPN ID crosswalk; added Feb 24 2026
    #   canonical_games           — Deduplicated game identity table; added Feb 28 2026
    #                               sync_canonical_games(conn) keeps it current after any games INSERT
    #   claude_analysis_log       — Phase 8.23 Layer 1 feedback loop; added Feb 25 2026
    #
    # Source: Module B (LudiEngine) - Line History
    #   prop_line_snapshots      — Opening/closing/actual lifecycle for all prop lines; added Feb 27 2026
    #
    # Unresolved (referenced in production but CREATE TABLE source not found):
    #   players_archived          — Referenced in migration_enable.sql; presumed manual creation
    # -------------------------------------------------------------------------

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
