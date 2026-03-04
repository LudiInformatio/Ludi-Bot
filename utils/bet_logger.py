# LUDI INFORMATIO | BET LOGGER UTILITY
# ----------------------------------------
# Week 2, Days 1-2: Structured Logging Framework
# Purpose: Track all bet recommendations for backtesting and ROI analysis
# Storage: Dual format (JSON + SQLite) for flexibility

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class BetLogger:
    """
    Logs bet recommendations to both JSON (human-readable) and SQLite (queryable).

    Follows the singleton pattern to maintain a single connection pool and prevent
    duplicate logging across modules.

    Usage:
        from utils.bet_logger import get_bet_logger
        logger = get_bet_logger()
        bet_id = logger.log_recommendation(rec_data)
    """

    def __init__(self, db_path='ludi.db', logs_dir='logs/bets'):
        """
        Initialize bet logger with database and JSON log directory.

        Args:
            db_path: Path to SQLite database (default: 'ludi.db')
            logs_dir: Directory for daily JSON logs (default: 'logs/bets')
        """
        self.db_path = db_path
        self.logs_dir = logs_dir
        self._persistent_conn = None  # For in-memory databases

        # Create logs directory if it doesn't exist
        os.makedirs(logs_dir, exist_ok=True)

        # For in-memory databases, keep a persistent connection
        if db_path == ':memory:':
            self._persistent_conn = sqlite3.connect(db_path)

        # Initialize database schema
        self._initialize_schema()

        print(f"✅ BetLogger initialized (DB: {db_path}, Logs: {logs_dir})")

    def _get_conn(self) -> sqlite3.Connection:
        """Create a new database connection (or return persistent connection for :memory:)."""
        if self._persistent_conn:
            return self._persistent_conn
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _initialize_schema(self):
        """Create bet tracking tables if they don't exist."""
        conn = self._get_conn()
        c = conn.cursor()

        # Table 1: bet_recommendations
        c.execute('''
            CREATE TABLE IF NOT EXISTS bet_recommendations (
                -- Primary key
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Timing
                run_date TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Game context
                game_id TEXT NOT NULL,
                game_date TEXT NOT NULL,
                matchup TEXT,
                home_team TEXT,
                away_team TEXT,
                spread REAL,
                total REAL,

                -- Player identification
                player_id TEXT,
                player_name TEXT NOT NULL,
                team TEXT NOT NULL,
                opponent TEXT,

                -- Player context
                archetype TEXT,
                status TEXT,
                scenario TEXT,

                -- Bet details
                stat_category TEXT NOT NULL,
                bet_side TEXT NOT NULL,
                line REAL NOT NULL,
                odds_over INTEGER,
                odds_under INTEGER,

                -- Model analysis
                projection REAL NOT NULL,
                fair_prob REAL,
                model_prob REAL,
                true_edge REAL,
                ev REAL,

                -- Recommendation
                units REAL,
                confidence_tier TEXT,
                note TEXT,
                tags TEXT,

                -- Game factors
                referee_impact REAL,
                blowout_modifier REAL,

                -- Phase C1: Hit rate confirmation score (0.40*L5_hr + 0.35*L10_hr + 0.25*model_prob)
                confirmation_score REAL,
                
                -- Phase 8: Sharp consensus / CLV
                sharp_odds_over_at_bet INTEGER,
                sharp_odds_under_at_bet INTEGER,
                sharp_book_at_bet TEXT,
                sharp_consensus REAL,

                -- Outcome tracking (NULL until settled)
                outcome TEXT,
                actual_result REAL,
                profit_loss REAL,
                clv REAL,

                -- CLV Capture (Phase 7.4)
                closing_odds_over INTEGER,
                closing_odds_under INTEGER,
                clv_cents REAL,
                closing_time TEXT,
                line_movement REAL,

                settled_at TIMESTAMP,

                -- Phase 8.24: Edge type label (Projection/Matchup/Injury-Vacuum/Hot-Streak)
                edge_type TEXT DEFAULT 'Projection',

                -- Phase 8.26: SGP correlation risk flag (NULL = no risk detected)
                sgp_correlation_risk TEXT DEFAULT NULL,

                -- Time-context mode at pipeline run time (Ludi-Lite pattern)
                -- EARLY_LOOK (<noon) / AFTERNOON (noon-5 PM) / PRE_GAME (5-7 PM) / LOCK_TIME (>7 PM)
                time_context TEXT DEFAULT 'EARLY_LOOK',

                -- Metadata
                run_type TEXT DEFAULT 'production',
                bookmaker TEXT DEFAULT 'consensus',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Indexes for fast queries
        c.execute('CREATE INDEX IF NOT EXISTS idx_bet_recs_run_date ON bet_recommendations(run_date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_bet_recs_game_date ON bet_recommendations(game_date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_bet_recs_player ON bet_recommendations(player_name)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_bet_recs_game ON bet_recommendations(game_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_bet_recs_outcome ON bet_recommendations(outcome)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_bet_recs_stat ON bet_recommendations(stat_category)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_bet_recs_tier ON bet_recommendations(confidence_tier)')

        # Table 2: bet_daily_summaries
        c.execute('''
            CREATE TABLE IF NOT EXISTS bet_daily_summaries (
                -- Primary key
                run_date TEXT PRIMARY KEY,

                -- Volume
                total_bets INTEGER DEFAULT 0,
                total_units REAL DEFAULT 0.0,

                -- Results (NULL until bets settle)
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                pushes INTEGER DEFAULT 0,
                pending INTEGER DEFAULT 0,

                -- Performance
                win_rate REAL,
                roi REAL,
                profit_loss REAL,

                -- Edge validation
                avg_edge REAL,
                avg_ev REAL,
                avg_clv REAL,

                -- API cost tracking
                api_cost REAL,
                api_credits_used INTEGER,

                -- Metadata
                games_analyzed INTEGER,
                players_simulated INTEGER,
                runtime_seconds REAL,

                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        if not self._persistent_conn:
            conn.close()

    def log_recommendation(self, rec_data: Dict) -> int:
        """
        Log a single bet recommendation to both JSON and SQLite.

        Args:
            rec_data: Dictionary with recommendation fields (see schema for required fields)

        Returns:
            bet_id: Primary key of inserted record

        Required fields:
            - run_date: Date of pipeline run (YYYY-MM-DD)
            - game_id: Unique game identifier
            - game_date: Date of game
            - player_name: Player name
            - team: Player's team
            - stat_category: Stat being bet (PTS, REB, AST, etc.)
            - bet_side: 'OVER' or 'UNDER'
            - line: Sportsbook line value
            - projection: Model's projection
        """
        # Validate required fields
        required_fields = ['run_date', 'game_id', 'game_date', 'player_name',
                          'team', 'stat_category', 'bet_side', 'line', 'projection']
        missing = [f for f in required_fields if f not in rec_data or rec_data[f] is None]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        try:
            # 1. Insert to database
            bet_id = self._insert_to_database(rec_data)

            # 2. Append to JSON log
            self._append_to_json(rec_data, bet_id)

            return bet_id

        except Exception as e:
            print(f"⚠️  BetLogger error: {e}")
            # If database fails, try JSON only
            try:
                self._append_to_json(rec_data, bet_id=None)
            except Exception as e:
                print(f"[TAG] Context: {e}")
                pass
            raise

    def _insert_to_database(self, rec_data: Dict) -> int:
        """Insert recommendation to SQLite database."""
        conn = self._get_conn()
        c = conn.cursor()

        # Build INSERT statement with all fields
        fields = [
            'run_date', 'game_id', 'game_date', 'matchup', 'home_team', 'away_team',
            'spread', 'total', 'player_id', 'player_name', 'team', 'opponent',
            'archetype', 'status', 'scenario', 'stat_category', 'bet_side', 'line',
            'odds_over', 'odds_under', 'projection', 'fair_prob', 'model_prob',
            'true_edge', 'ev', 'units', 'confidence_tier', 'confirmation_score', 
            'sharp_odds_over_at_bet', 'sharp_odds_under_at_bet', 'sharp_book_at_bet', 'sharp_consensus',
            'note', 'tags',
            'referee_impact', 'blowout_modifier', 'run_type', 'bookmaker', 'time_context'
        ]

        # Get values (use None for missing optional fields)
        values = tuple(rec_data.get(f) for f in fields)
        placeholders = ','.join(['?' for _ in fields])

        query = f'''
            INSERT OR IGNORE INTO bet_recommendations ({','.join(fields)})
            VALUES ({placeholders})
        '''

        c.execute(query, values)
        bet_id = c.lastrowid

        conn.commit()
        if not self._persistent_conn:
            conn.close()

        return bet_id

    def _append_to_json(self, rec_data: Dict, bet_id: Optional[int] = None):
        """Append recommendation to daily JSON log file."""
        # Determine filename based on run_date
        run_date = rec_data.get('run_date', datetime.now().strftime('%Y-%m-%d'))
        json_file = os.path.join(self.logs_dir, f"{run_date}.json")

        # Add bet_id to rec_data
        if bet_id:
            rec_data['bet_id'] = bet_id

        # Load existing logs or create new array
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = []

        # Append new recommendation
        logs.append(rec_data)

        # Write back with pretty formatting
        with open(json_file, 'w') as f:
            json.dump(logs, f, indent=2, default=str)

    def log_batch_recommendations(self, recs: List[Dict]) -> List[int]:
        """
        Batch insert multiple recommendations (optimized for daily briefing).

        Args:
            recs: List of recommendation dictionaries

        Returns:
            List of bet_ids
        """
        if not recs:
            return []

        bet_ids = []
        conn = self._get_conn()
        c = conn.cursor()

        try:
            # Build field list
            fields = [
                'run_date', 'game_id', 'game_date', 'matchup', 'home_team', 'away_team',
                'spread', 'total', 'player_id', 'player_name', 'team', 'opponent',
                'archetype', 'status', 'scenario', 'stat_category', 'bet_side', 'line',
                'odds_over', 'odds_under', 'projection', 'fair_prob', 'model_prob',
                'true_edge', 'ev', 'units', 'confidence_tier', 'note', 'tags',
                'referee_impact', 'blowout_modifier', 'run_type', 'bookmaker',
                'sharp_odds_over_at_bet', 'sharp_odds_under_at_bet', 'sharp_book_at_bet', 'sharp_consensus'
            ]

            placeholders = ','.join(['?' for _ in fields])
            query = f'''
                INSERT OR IGNORE INTO bet_recommendations ({','.join(fields)})
                VALUES ({placeholders})
            '''

            # Execute batch insert
            for rec_data in recs:
                values = tuple(rec_data.get(f) for f in fields)
                c.execute(query, values)
                bet_ids.append(c.lastrowid)

            conn.commit()

            # Update JSON logs
            for rec_data, bet_id in zip(recs, bet_ids):
                self._append_to_json(rec_data, bet_id)

            return bet_ids

        except Exception as e:
            conn.rollback()
            print(f"⚠️  Batch insert failed: {e}")
            raise
        finally:
            conn.close()

    def update_outcome(self, bet_id: int, outcome: str, actual_result: float,
                      profit_loss: Optional[float] = None, clv: Optional[float] = None):
        """
        Update bet with actual outcome after game completion.

        Args:
            bet_id: Primary key of bet
            outcome: 'WIN', 'LOSS', or 'PUSH'
            actual_result: Actual stat achieved (e.g., 23.0 PTS)
            profit_loss: Profit/loss in units (optional, can be calculated)
            clv: Closing Line Value (optional, calculated by comparing final line)
        """
        if outcome not in ['WIN', 'LOSS', 'PUSH', 'VOID']:
            raise ValueError(f"Invalid outcome: {outcome}. Must be WIN, LOSS, PUSH, or VOID")

        conn = self._get_conn()
        c = conn.cursor()

        c.execute('''
            UPDATE bet_recommendations
            SET outcome = ?,
                actual_result = ?,
                profit_loss = ?,
                clv = ?,
                settled_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (outcome, actual_result, profit_loss, clv, bet_id))

        conn.commit()
        if not self._persistent_conn:
            conn.close()

    def get_pending_bets(self, game_date: Optional[str] = None) -> List[Dict]:
        """
        Query bets awaiting outcome settlement.

        Args:
            game_date: Filter by specific game date (optional)

        Returns:
            List of bet dictionaries with pending outcomes
        """
        conn = self._get_conn()
        conn.row_factory = sqlite3.Row  # Return rows as dicts
        c = conn.cursor()

        if game_date:
            query = '''
                SELECT * FROM bet_recommendations
                WHERE outcome IS NULL AND game_date = ?
                ORDER BY game_date, player_name
            '''
            c.execute(query, (game_date,))
        else:
            query = '''
                SELECT * FROM bet_recommendations
                WHERE outcome IS NULL
                ORDER BY game_date, player_name
            '''
            c.execute(query)

        results = [dict(row) for row in c.fetchall()]
        if not self._persistent_conn:
            conn.close()

        return results

    def calculate_daily_summary(self, run_date: str, summary_data: Optional[Dict] = None):
        """
        Calculate and store daily summary statistics.

        Args:
            run_date: Date to summarize (YYYY-MM-DD)
            summary_data: Optional pre-calculated summary dict (for performance)
        """
        conn = self._get_conn()
        c = conn.cursor()

        # If summary_data not provided, calculate from database
        if summary_data is None:
            c.execute('''
                SELECT
                    COUNT(*) as total_bets,
                    SUM(units) as total_units,
                    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN outcome = 'PUSH' THEN 1 ELSE 0 END) as pushes,
                    SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) as pending,
                    AVG(true_edge) as avg_edge,
                    AVG(ev) as avg_ev,
                    AVG(clv) as avg_clv,
                    SUM(profit_loss) as profit_loss
                FROM bet_recommendations
                WHERE run_date = ?
            ''', (run_date,))

            row = c.fetchone()
            summary_data = {
                'run_date': run_date,
                'total_bets': row[0] or 0,
                'total_units': row[1] or 0.0,
                'wins': row[2] or 0,
                'losses': row[3] or 0,
                'pushes': row[4] or 0,
                'pending': row[5] or 0,
                'avg_edge': row[6],
                'avg_ev': row[7],
                'avg_clv': row[8],
                'profit_loss': row[9]
            }

            # Calculate win_rate and roi
            settled = summary_data['wins'] + summary_data['losses']
            summary_data['win_rate'] = summary_data['wins'] / settled if settled > 0 else None
            summary_data['roi'] = (
                summary_data['profit_loss'] / summary_data['total_units']
                if summary_data['total_units'] > 0 and summary_data['profit_loss'] is not None
                else None
            )

        # UPSERT into bet_daily_summaries
        c.execute('''
            INSERT INTO bet_daily_summaries
            (run_date, total_bets, total_units, wins, losses, pushes, pending,
             win_rate, roi, profit_loss, avg_edge, avg_ev, avg_clv,
             api_cost, api_credits_used, games_analyzed, players_simulated, runtime_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_date) DO UPDATE SET
                total_bets=excluded.total_bets,
                total_units=excluded.total_units,
                wins=excluded.wins,
                losses=excluded.losses,
                pushes=excluded.pushes,
                pending=excluded.pending,
                win_rate=excluded.win_rate,
                roi=excluded.roi,
                profit_loss=excluded.profit_loss,
                avg_edge=excluded.avg_edge,
                avg_ev=excluded.avg_ev,
                avg_clv=excluded.avg_clv,
                api_cost=excluded.api_cost,
                api_credits_used=excluded.api_credits_used,
                games_analyzed=excluded.games_analyzed,
                players_simulated=excluded.players_simulated,
                runtime_seconds=excluded.runtime_seconds,
                updated_at=CURRENT_TIMESTAMP
        ''', (
            summary_data.get('run_date'),
            summary_data.get('total_bets', 0),
            summary_data.get('total_units', 0.0),
            summary_data.get('wins', 0),
            summary_data.get('losses', 0),
            summary_data.get('pushes', 0),
            summary_data.get('pending', 0),
            summary_data.get('win_rate'),
            summary_data.get('roi'),
            summary_data.get('profit_loss'),
            summary_data.get('avg_edge'),
            summary_data.get('avg_ev'),
            summary_data.get('avg_clv'),
            summary_data.get('api_cost'),
            summary_data.get('api_credits_used'),
            summary_data.get('games_analyzed'),
            summary_data.get('players_simulated'),
            summary_data.get('runtime_seconds')
        ))

        conn.commit()
        if not self._persistent_conn:
            conn.close()

    def get_performance_report(self, start_date: str, end_date: str) -> Dict:
        """
        Generate performance report for date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary with aggregated performance metrics
        """
        conn = self._get_conn()
        c = conn.cursor()

        c.execute('''
            SELECT
                SUM(total_bets) as total_bets,
                SUM(total_units) as total_units,
                SUM(wins) as wins,
                SUM(losses) as losses,
                SUM(pushes) as pushes,
                AVG(win_rate) as avg_win_rate,
                AVG(roi) as avg_roi,
                SUM(profit_loss) as total_profit_loss,
                AVG(avg_edge) as avg_edge,
                AVG(avg_clv) as avg_clv,
                SUM(api_cost) as total_api_cost
            FROM bet_daily_summaries
            WHERE run_date BETWEEN ? AND ?
        ''', (start_date, end_date))

        row = c.fetchone()
        if not self._persistent_conn:
            conn.close()

        return {
            'start_date': start_date,
            'end_date': end_date,
            'total_bets': row[0] or 0,
            'total_units': row[1] or 0.0,
            'wins': row[2] or 0,
            'losses': row[3] or 0,
            'pushes': row[4] or 0,
            'avg_win_rate': row[5],
            'avg_roi': row[6],
            'total_profit_loss': row[7] or 0.0,
            'avg_edge': row[8],
            'avg_clv': row[9],
            'total_api_cost': row[10] or 0.0
        }


# ============================================================
# SINGLETON PATTERN
# ============================================================

_logger_instance = None

def get_bet_logger(db_path='ludi.db', logs_dir='logs/bets') -> BetLogger:
    """
    Get singleton BetLogger instance.

    Args:
        db_path: Path to SQLite database (default: 'ludi.db')
        logs_dir: Directory for JSON logs (default: 'logs/bets')

    Returns:
        BetLogger instance

    Usage:
        from utils.bet_logger import get_bet_logger
        logger = get_bet_logger()
        bet_id = logger.log_recommendation(rec_data)
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = BetLogger(db_path=db_path, logs_dir=logs_dir)
    return _logger_instance


# ============================================================
# UNIT TESTS
# ============================================================

if __name__ == "__main__":
    print("="*60)
    print("BET LOGGER UNIT TESTS")
    print("="*60)

    # Test 1: Initialize logger (in-memory database)
    print("\nTest 1: Initialize logger")
    logger = BetLogger(db_path=':memory:', logs_dir='test_logs')
    print("✅ Logger initialized")

    # Test 2: Log single recommendation
    print("\nTest 2: Log single recommendation")
    rec = {
        'run_date': '2026-01-07',
        'game_id': 'TEST_GAME',
        'game_date': '2026-01-07',
        'matchup': 'TEST @ TEST',
        'player_name': 'Test Player',
        'team': 'TEST',
        'stat_category': 'PTS',
        'bet_side': 'OVER',
        'line': 20.5,
        'projection': 22.3,
        'true_edge': 8.5,
        'ev': 12.0,
        'units': 1.0,
        'confidence_tier': 'DIAMOND'
    }
    bet_id = logger.log_recommendation(rec)
    print(f"✅ Logged bet #{bet_id}")

    # Test 3: Query pending bets
    print("\nTest 3: Query pending bets")
    pending = logger.get_pending_bets()
    print(f"✅ Found {len(pending)} pending bets")
    assert len(pending) == 1, "Expected 1 pending bet"

    # Test 4: Update outcome
    print("\nTest 4: Update outcome")
    logger.update_outcome(bet_id, 'WIN', 23.0, profit_loss=1.91)
    pending = logger.get_pending_bets()
    print(f"✅ Outcome updated, {len(pending)} pending bets remaining")
    assert len(pending) == 0, "Expected 0 pending bets after update"

    # Test 5: Calculate daily summary
    print("\nTest 5: Calculate daily summary")
    logger.calculate_daily_summary('2026-01-07')
    print("✅ Daily summary calculated")

    # Test 6: Performance report
    print("\nTest 6: Performance report")
    report = logger.get_performance_report('2026-01-01', '2026-01-10')
    print(f"✅ Report generated: {report['total_bets']} bets, ROI: {report['avg_roi']}")

    print("\n" + "="*60)
    print("ALL TESTS PASSED ✅")
    print("="*60)
