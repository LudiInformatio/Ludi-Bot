import sqlite3
from datetime import datetime, timedelta
from typing import Any

from config import DB_PATH
from utils.player_id_resolver import resolve_canonical_name
from utils.time_utils import get_est_today, get_est_yesterday


def get_db_connection() -> sqlite3.Connection:
    """Create a read-only connection to the ludi.db database."""
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def get_injuries() -> list[dict[str, Any]]:
    """Fetch current active injuries (OUT, DOUBTFUL, GTD)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT player_name, status, days_out, injury_type, team_abbreviation
            FROM player_injuries
            WHERE resolved_at IS NULL
              AND status IN ('OUT', 'DOUBTFUL', 'GTD')
              AND snapshot_time >= datetime('now', '-14 days')
            ORDER BY 
                CASE status
                    WHEN 'OUT' THEN 1
                    WHEN 'DOUBTFUL' THEN 2
                    WHEN 'GTD' THEN 3
                END,
                player_name
            LIMIT 30
        """)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_edges() -> list[dict[str, Any]]:
    """Fetch today's recommended bets with positive edge."""
    today = get_est_today()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT player_name, team, opponent, stat_category, bet_side, line,
                   true_edge, projection, confidence_tier, matchup
            FROM bet_recommendations
            WHERE run_date = ?
              AND outcome IS NULL
              AND true_edge > 0
            ORDER BY true_edge DESC
            LIMIT 20
        """, (today,))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_trends(player_name: str | None = None) -> list[dict[str, Any]]:
    """Fetch recent player performance trends. If player_name provided, filter to that player."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if player_name:
            canonical = resolve_canonical_name(conn, player_name)
            cursor.execute("""
                SELECT player_name, team_abbreviation, game_date, pts, reb, ast,
                       min, fg_pct, three_pt_pct, ft_pct
                FROM player_game_logs
                WHERE LOWER(player_name) = LOWER(?)
                ORDER BY game_date DESC
                LIMIT 20
            """, (canonical,))
        else:
            cursor.execute("""
                SELECT player_name, team_abbreviation, game_date, pts, reb, ast,
                       min, fg_pct, three_pt_pct, ft_pct
                FROM player_game_logs
                WHERE game_date >= datetime('now', '-14 days')
                ORDER BY game_date DESC
                LIMIT 50
            """)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_schedule(date: str | None = None) -> list[dict[str, Any]]:
    """Fetch today's or specified date's game schedule."""
    if date is None:
        date = get_est_today()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT game_id, home_team, away_team, date,
                   home_score, away_score
            FROM games
            WHERE DATE(date) = ?
            ORDER BY date
        """, (date,))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_recap(date: str | None = None) -> list[dict[str, Any]]:
    """Fetch yesterday's or specified date's game results."""
    if date is None:
        date = get_est_yesterday()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT game_id, home_team, away_team, date,
                   home_score, away_score
            FROM games
            WHERE DATE(date) = ?
              AND home_score IS NOT NULL
            ORDER BY date
        """, (date,))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_standings() -> list[dict[str, Any]]:
    """Fetch current NBA standings."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT team_abbrev, wins, losses, win_pct, home_wins, home_losses,
                   away_wins, away_losses, conference, division
            FROM team_standings_bdl
            ORDER BY win_pct DESC
        """)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def free_text_query(query: str) -> str:
    """Route free-text queries to the appropriate handler. Returns descriptive data."""
    query_lower = query.lower()

    if "bet" in query_lower or "edge" in query_lower:
        return f"Today's edges: {len(get_edges())} plays with positive EV found."

    if "injury" in query_lower or "out" in query_lower:
        injuries = get_injuries()
        if not injuries:
            return "No active injuries on record."
        lines = [f"{i['player_name']} ({i['team_abbreviation']}) - {i['status']}" for i in injuries[:10]]
        return "Current injuries:\n" + "\n".join(lines)

    if "standings" in query_lower or "record" in query_lower:
        standings = get_standings()
        top = standings[:5]
        lines = [f"{s['team_abbrev']}: {s['wins']}-{s['losses']}" for s in top]
        return "Top of the standings:\n" + "\n".join(lines)

    if "schedule" in query_lower or "games today" in query_lower:
        schedule = get_schedule()
        if not schedule:
            return "No games scheduled for today."
        lines = [f"{s['away_team']} @ {s['home_team']}" for s in schedule]
        return "Today's games:\n" + "\n".join(lines)

    if "yesterday" in query_lower or "recap" in query_lower:
        recap = get_recap()
        if not recap:
            return "No game results found for yesterday."
        lines = [f"{r['away_team']} {r['away_score']} @ {r['home_team']} {r['home_score']}" for r in recap]
        return "Yesterday's results:\n" + "\n".join(lines)

    return "I can help with injuries, edges, trends, schedule, recap, or standings. What would you like to know?"
