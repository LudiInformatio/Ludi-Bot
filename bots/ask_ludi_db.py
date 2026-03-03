import sqlite3
import time as _time
from collections import defaultdict
from datetime import datetime
from typing import Any

from config import DB_PATH
from utils.player_id_resolver import resolve_canonical_name
from utils.time_utils import (
    get_est_today, get_est_yesterday,
    get_smart_target_date, get_est_tomorrow,
)


def get_db_connection() -> sqlite3.Connection:
    """Create a read-only connection to the ludi.db database."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


# ---------------------------------------------------------------------------
# Ghost injury defense — reusable SQL fragment
# Players who logged 10+ minutes in the last 3 game days are clearly not OUT.
# This is a bot-level firewall against stale Tank01/BDL injury data.
# Root fix (dedup + resolve logic) deferred to module audit sprint.
# ---------------------------------------------------------------------------
_GHOST_INJURY_GUARD = """
  AND NOT EXISTS (
      SELECT 1 FROM player_game_logs pgl
      JOIN player_canonical_ids pci2 ON LOWER(pci2.full_name) = LOWER(pi.player_name)
      WHERE pgl.player_id = pci2.canonical_id
        AND pgl.game_date >= date('now', '-3 days')
        AND pgl.minutes > 10
  )
"""


# ---------------------------------------------------------------------------
# In-memory slate context cache — 15-minute TTL (matches injury refresh cadence)
# ---------------------------------------------------------------------------
_slate_cache: dict[str, tuple[float, str]] = {}
_SLATE_CACHE_TTL = 900  # 15 minutes


def get_injuries() -> list[dict[str, Any]]:
    """Fetch current active injuries (OUT, DOUBTFUL, GTD).

    Includes ghost injury defense: filters players who have played
    10+ minutes in the last 3 days (Tank01 stale data protection).
    Uses GROUP BY to deduplicate multiple rows for the same player.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT pi.player_name, pi.status, pi.days_out,
                   CASE WHEN pi.source = 'ESPN' THEN pi.injury_type
                        ELSE pi.status END as display_type,
                   pi.team_abbreviation, MAX(pi.snapshot_time) as snapshot_time
            FROM player_injuries pi
            WHERE pi.resolved_at IS NULL
              AND pi.status IN ('OUT', 'DOUBTFUL', 'GTD')
              AND pi.snapshot_time >= datetime('now', '-14 days')
              {_GHOST_INJURY_GUARD}
            GROUP BY pi.player_name, pi.team_abbreviation
            ORDER BY
                CASE pi.status
                    WHEN 'OUT' THEN 1
                    WHEN 'DOUBTFUL' THEN 2
                    WHEN 'GTD' THEN 3
                END,
                pi.player_name
            LIMIT 30
        """)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_freshness_meta() -> dict[str, Any]:
    """Query the latest update timestamps for each data type.

    Returns dict with freshness info for injuries, edges, standings, and games.
    Used by formatters to show "data as of X PM EST" footers.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        meta: dict[str, Any] = {}

        # Injuries: most recent snapshot_time across all active records
        row = cursor.execute(
            "SELECT MAX(snapshot_time) FROM player_injuries WHERE resolved_at IS NULL"
        ).fetchone()
        meta['injuries'] = row[0] if row else None

        # Edges: most recent timestamp for today's pipeline run
        row = cursor.execute(
            "SELECT MAX(timestamp) FROM bet_recommendations WHERE run_date = ?",
            (get_est_today(),)
        ).fetchone()
        meta['edges'] = row[0] if row else None

        # Standings: most recent update
        row = cursor.execute(
            "SELECT MAX(updated_at) FROM team_standings_bdl"
        ).fetchone()
        meta['standings'] = row[0] if row else None

        # Games: count + target date for smart date display
        target = get_smart_target_date()
        row = cursor.execute(
            "SELECT COUNT(*) FROM games WHERE DATE(date) = ?", (target,)
        ).fetchone()
        meta['games_count'] = row[0] if row else 0
        meta['target_date'] = target

        return meta
    finally:
        conn.close()


def get_expected_game_count(date: str) -> int:
    """Check nba_calendar for expected game count (date-level only, no matchups).

    Falls back to 0 if nba_calendar table is unavailable.
    nba_calendar has date-level metadata only — use games table for matchup details.
    """
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT game_count FROM nba_calendar WHERE date = ?", (date,)
        ).fetchone()
        return row[0] if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


def build_slate_context(target_date: str | None = None) -> str:
    """Build a full-slate text block for narrative prompt injection.

    Includes: games, top 8 rotation players per team (avg_minutes from rotation_profiles),
    and active injuries with inline IN/OUT status. Ghost injury defense applied.

    Cached for 15 minutes — safe to call on every message without DB overhead.
    Uses smart target date (after 9 PM → tomorrow's slate for early research).
    """
    if target_date is None:
        target_date = get_smart_target_date()

    # Return cached result if still fresh
    cached = _slate_cache.get(target_date)
    if cached and (_time.time() - cached[0]) < _SLATE_CACHE_TTL:
        return cached[1]

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 1. Games on this date
        cursor.execute("""
            SELECT home_team, away_team FROM games WHERE DATE(date) = ?
        """, (target_date,))
        games = cursor.fetchall()

        if not games:
            context = f"No games loaded for {target_date} yet."
            _slate_cache[target_date] = (_time.time(), context)
            return context

        # Collect all teams on the slate
        teams = list({team for pair in games for team in pair})
        placeholders = ','.join('?' * len(teams))

        # 2. Rotation players (top 8 per team by avg_minutes, 21-day window)
        cursor.execute(f"""
            SELECT rp.player_name, rp.team_abbreviation,
                   ROUND(rp.avg_minutes, 1) as avg_min,
                   p.archetype, p.position
            FROM rotation_profiles rp
            LEFT JOIN players p ON rp.player_id = p.player_id
            WHERE rp.team_abbreviation IN ({placeholders})
              AND rp.window_days = 21
            ORDER BY rp.team_abbreviation, rp.avg_minutes DESC
        """, teams)
        rotation_rows = cursor.fetchall()

        # 3. Active injuries on slate teams (ghost injury defense + dedup + ESPN type pref)
        cursor.execute(f"""
            SELECT pi.player_name, pi.team_abbreviation, pi.status,
                   CASE WHEN pi.source = 'ESPN' THEN pi.injury_type
                        ELSE pi.status END as display_type
            FROM player_injuries pi
            WHERE pi.team_abbreviation IN ({placeholders})
              AND pi.resolved_at IS NULL
              AND pi.status IN ('OUT', 'DOUBTFUL', 'GTD')
              AND pi.snapshot_time >= datetime('now', '-14 days')
              {_GHOST_INJURY_GUARD}
            GROUP BY pi.player_name, pi.team_abbreviation
            ORDER BY MAX(pi.snapshot_time) DESC
        """, teams)
        injury_rows = cursor.fetchall()

        # Build injury lookup: (player_name, team) → (status, display_type)
        injury_map = {}
        for name, team, status, display_type in injury_rows:
            injury_map[(name, team)] = (status, display_type)

        # Format slate header
        lines = [f"TONIGHT'S SLATE ({target_date}) — {len(games)} games:"]
        for home, away in games:
            lines.append(f"  {away} @ {home}")

        # Group rotation by team (top 8), with inline injury status
        team_rosters: dict[str, list[str]] = defaultdict(list)
        for name, team, avg_min, arch, pos in rotation_rows:
            if len(team_rosters[team]) >= 8:
                continue
            arch_tag = f" [{arch}]" if arch and arch != 'GENERALIST' else ""
            inj = injury_map.get((name, team))
            if inj:
                status_tag, display_type = inj
                inj_detail = (
                    f" — {display_type}"
                    if display_type and display_type not in ('OUT', 'DOUBTFUL', 'GTD')
                    else ""
                )
                team_rosters[team].append(
                    f"{name} ({pos}, {avg_min}m{arch_tag}) [{status_tag}{inj_detail}]"
                )
            else:
                team_rosters[team].append(f"{name} ({pos}, {avg_min}m{arch_tag})")

        lines.append("\nKEY ROTATION PLAYERS (top 8 per team, injury status inline):")
        for team in sorted(team_rosters):
            lines.append(f"  {team}: {', '.join(team_rosters[team])}")

        context = "\n".join(lines)

        # Pre-truncate to stay within token budget (BERT Pattern 4)
        if len(context) > 2000:
            context = context[:2000] + "\n  ... [truncated for token budget]"

        _slate_cache[target_date] = (_time.time(), context)
        return context
    finally:
        conn.close()


def get_edges() -> list[dict[str, Any]]:
    """Fetch today's recommended bets with positive edge.

    Always uses today's date — the pipeline only runs once per day.
    """
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
    """Fetch game schedule for the smart target date (or specified date).

    After 9 PM EST, smart date = tomorrow to support early research.
    Returns empty list if games not yet populated — caller should check
    get_expected_game_count() for nba_calendar fallback message.
    """
    if date is None:
        date = get_smart_target_date()
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
    target_date = get_smart_target_date()

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

    if "schedule" in query_lower or "games today" in query_lower or "games tonight" in query_lower:
        schedule = get_schedule(target_date)
        if not schedule:
            expected = get_expected_game_count(target_date)
            if expected > 0:
                return f"{expected} games expected on {target_date} — matchups available after 3 AM sync."
            return f"No games found for {target_date}."
        lines = [f"{s['away_team']} @ {s['home_team']}" for s in schedule]
        return f"Games on {target_date}:\n" + "\n".join(lines)

    if "yesterday" in query_lower or "recap" in query_lower:
        recap = get_recap()
        if not recap:
            return "No game results found for yesterday."
        lines = [f"{r['away_team']} {r['away_score']} @ {r['home_team']} {r['home_score']}" for r in recap]
        return "Yesterday's results:\n" + "\n".join(lines)

    return "I can help with injuries, edges, trends, schedule, recap, or standings. What would you like to know?"
