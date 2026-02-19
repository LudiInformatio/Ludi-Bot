"""
LUDI INFORMATIO | TREND ENGINE
==============================
Phase 8.15 — Hybrid trend utility for game notes + spotlights.

Architecture:
  Pre-computed data (from player_trends table, refreshed at 5 AM):
    l7_avg, l10_avg, l15_avg, season_avg, trend_delta, trend_label, streak_vs_avg

  Live-computed data (when sportsbook line is provided):
    hit_rate_l10, streak_vs_line

  Minutes trend (from player_trends stat='MIN'):
    l7_min, l15_min, min_delta, min_label

Usage:
  from utils.trend_engine import get_player_trends, get_beneficiary_context, get_stagger_context

  # Pre-computed only (fast — single table read)
  trend = get_player_trends('LeBron James', 'PTS', 'LAL')

  # Hybrid: pre-computed + live hit rate/streak (needs line)
  trend = get_player_trends('LeBron James', 'PTS', 'LAL', line=25.5)

  # Beneficiary context for Claude prompt injection
  block = get_beneficiary_context('PHI', 'BOS')

  # Stagger context for spotlight enrichment
  note = get_stagger_context('Tyrese Maxey', 'PHI', ['Joel Embiid'])
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')

# Stat column mapping — matches player_game_logs schema exactly
STAT_COL = {
    'PTS': 'pts', 'REB': 'reb', 'AST': 'ast', '3PM': 'fg3m',
    'BLK': 'blk', 'STL': 'stl', 'TOV': 'tov',
}

# Combo stat SQL expressions
COMBO_EXPR = {
    'PRA': '(pts + reb + ast)',
    'PA': '(pts + ast)',
    'PR': '(pts + reb)',
    'RA': '(reb + ast)',
}


def _get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _resolve_player_id(conn, player_name: str, team_abbr: str) -> str:
    """Resolve player name to canonical player_id.

    Handles accented names (Jokić vs Jokic) by querying the players table
    which stores the authoritative name. Falls back to player_game_logs
    if not found in players.
    """
    # Try players table first (current roster — has accented names)
    row = conn.execute(
        "SELECT player_id FROM players WHERE name = ? AND team = ?",
        (player_name, team_abbr)
    ).fetchone()
    if row:
        return str(row['player_id'])

    # Try without team filter (player might have been traded)
    row = conn.execute(
        "SELECT player_id FROM players WHERE name = ? LIMIT 1",
        (player_name,)
    ).fetchone()
    if row:
        return str(row['player_id'])

    # Try player_game_logs (handles both accented and non-accented names)
    row = conn.execute(
        "SELECT DISTINCT player_id FROM player_game_logs WHERE player_name = ? AND team_abbreviation = ? LIMIT 1",
        (player_name, team_abbr)
    ).fetchone()
    if row:
        return str(row['player_id'])

    return None


def _get_stat_expr(stat: str) -> str:
    """Return SQL expression for a stat type."""
    if stat == 'MIN':
        return 'minutes'
    if stat in COMBO_EXPR:
        return COMBO_EXPR[stat]
    if stat in STAT_COL:
        return STAT_COL[stat]
    return None


def get_player_trends(player_name: str, stat: str, team_abbr: str,
                      line: float = None, player_id: str = None) -> dict:
    """Hybrid trend lookup: pre-computed averages + live line-based data.

    Args:
        player_name: Player's display name (handles accented names)
        stat: Stat type — PTS, REB, AST, 3PM, BLK, STL, TOV, PRA, PA, PR, RA, MIN
        team_abbr: Team abbreviation (e.g. 'LAL')
        line: Optional sportsbook line — triggers live hit rate + streak computation
        player_id: Optional canonical player_id — skips name resolution if provided

    Returns dict with keys:
        Pre-computed (from player_trends table):
          l7_avg, l10_avg, l15_avg, season_avg, trend_delta, trend_label, streak_vs_avg, games_found

        Live-computed (when line is provided):
          hit_rate_l10 (float 0-100), streak_vs_line (int, positive=over, negative=under)

        Minutes (from player_trends stat='MIN'):
          l7_min, l15_min, min_delta, min_label

        Returns {} if player/stat not found.
    """
    conn = _get_conn()
    try:
        # Step 0: Resolve player_id if not provided
        pid = player_id or _resolve_player_id(conn, player_name, team_abbr)
        if not pid:
            return {}

        result = {}

        # Step 1: Read pre-computed trend from player_trends table
        row = conn.execute("""
            SELECT l7_avg, l10_avg, l15_avg, season_avg, trend_delta, trend_label,
                   streak_vs_avg, games_found
            FROM player_trends
            WHERE player_id = ? AND stat = ? AND team_abbreviation = ?
        """, (pid, stat, team_abbr)).fetchone()

        if not row:
            return {}

        result.update({
            'l7_avg': row['l7_avg'],
            'l10_avg': row['l10_avg'],
            'l15_avg': row['l15_avg'],
            'season_avg': row['season_avg'],
            'trend_delta': row['trend_delta'],
            'trend_label': row['trend_label'],
            'streak_vs_avg': row['streak_vs_avg'],
            'games_found': row['games_found'],
        })

        # Step 2: Read minutes trend (always included unless stat IS minutes)
        if stat != 'MIN':
            min_row = conn.execute("""
                SELECT l7_avg, l15_avg, trend_delta, trend_label
                FROM player_trends
                WHERE player_id = ? AND stat = 'MIN' AND team_abbreviation = ?
            """, (pid, team_abbr)).fetchone()

            if min_row:
                result['l7_min'] = min_row['l7_avg']
                result['l15_min'] = min_row['l15_avg']
                result['min_delta'] = min_row['trend_delta']
                result['min_label'] = min_row['trend_label']

        # Step 3: If line provided, compute live hit rate + streak
        if line is not None:
            expr = _get_stat_expr(stat)
            if expr:
                live_rows = conn.execute(f"""
                    SELECT {expr} as val
                    FROM player_game_logs
                    WHERE player_id = ? AND team_abbreviation = ? AND minutes > 0
                    ORDER BY game_date DESC LIMIT 10
                """, (pid, team_abbr)).fetchall()

                values = [r['val'] for r in live_rows if r['val'] is not None]
                if values:
                    # Hit rate: % of L10 games that went OVER the line
                    hits = sum(1 for v in values if v > line)
                    result['hit_rate_l10'] = round(hits / len(values) * 100, 1)

                    # Streak vs line: consecutive games over(+) or under(-) line
                    streak = 0
                    first_over = values[0] > line
                    for v in values:
                        if first_over and v > line:
                            streak += 1
                        elif not first_over and v <= line:
                            streak -= 1
                        else:
                            break
                    result['streak_vs_line'] = streak

        return result

    except Exception as e:
        print(f"[trend_engine] get_player_trends error: {e}")
        return {}
    finally:
        conn.close()


def get_beneficiary_context(home_team: str, away_team: str) -> str:
    """Build beneficiary impact block for Claude prompt injection.

    Queries player_injuries for OUT players, then beneficiary_minutes
    for who absorbs their minutes.

    Returns formatted string like:
      BENEFICIARY IMPACT:
      * Joel Embiid OUT (PHI, 14d knee) -> Andre Drummond +18.3 min, Paul George +4.1 min
      * ...

    Returns empty string if no OUT players or no beneficiary data.
    """
    conn = _get_conn()
    try:
        # Find OUT players on both teams (no players table join — avoids dirty ID issues)
        out_players = conn.execute("""
            SELECT player_name, team_abbreviation, days_out, injury_type
            FROM player_injuries
            WHERE team_abbreviation IN (?, ?)
              AND resolved_at IS NULL
              AND status = 'OUT'
            ORDER BY days_out DESC
        """, (home_team, away_team)).fetchall()

        if not out_players:
            return ""

        lines = ["BENEFICIARY IMPACT:"]

        for op in out_players:
            team = op['team_abbreviation']

            # Get top beneficiaries (name-based join — sidesteps Tank01 dirty ID problem)
            bens = conn.execute("""
                SELECT beneficiary_player_name, minutes_delta, games_without
                FROM beneficiary_minutes
                WHERE out_player_name = ? AND team_abbreviation = ?
                  AND minutes_delta > 2.0
                ORDER BY minutes_delta DESC LIMIT 3
            """, (op['player_name'], team)).fetchall()

            injury_desc = op['injury_type'] or 'injury'
            days = op['days_out'] or 0

            if bens:
                ben_parts = [f"{b['beneficiary_player_name']} +{b['minutes_delta']:.1f} min" for b in bens]
                lines.append(
                    f"- {op['player_name']} OUT ({team}, {days}d {injury_desc}) -> {', '.join(ben_parts)}"
                )
            else:
                lines.append(
                    f"- {op['player_name']} OUT ({team}, {days}d {injury_desc}) -> No beneficiary data"
                )

        return "\n".join(lines) if len(lines) > 1 else ""

    except Exception as e:
        print(f"[trend_engine] get_beneficiary_context error: {e}")
        return ""
    finally:
        conn.close()


def get_stagger_context(player_name: str, team_abbr: str,
                        out_players: list, player_id: str = None) -> str:
    """Build stagger context for spotlight enrichment.

    When a teammate is OUT, shows how the target player's stats change.

    Args:
        player_name: Target player
        team_abbr: Team abbreviation
        out_players: List of OUT teammate names
        player_id: Optional canonical player_id

    Returns one-line string like:
      "Without Embiid: +7.7 PTS, -1.9 AST (28g sample)"
    Or empty string if no stagger data.
    """
    if not out_players:
        return ""

    conn = _get_conn()
    try:
        pid = player_id or _resolve_player_id(conn, player_name, team_abbr)
        if not pid:
            return ""

        # Query stagger stats where partner is one of the OUT players
        placeholders = ','.join(['?'] * len(out_players))
        rows = conn.execute(f"""
            SELECT partner_player_name, pts_delta, ast_delta, reb_delta, games_sample
            FROM player_stagger_stats
            WHERE player_id = ? AND team_abbreviation = ?
              AND partner_player_name IN ({placeholders})
              AND games_sample >= 3
            ORDER BY abs(pts_delta) DESC
        """, [pid, team_abbr] + out_players).fetchall()

        if not rows:
            return ""

        # Use the highest-impact partner relationship
        r = rows[0]
        parts = []
        if abs(r['pts_delta']) >= 1.0:
            sign = "+" if r['pts_delta'] > 0 else ""
            parts.append(f"{sign}{r['pts_delta']:.1f} PTS")
        if abs(r['ast_delta']) >= 0.5:
            sign = "+" if r['ast_delta'] > 0 else ""
            parts.append(f"{sign}{r['ast_delta']:.1f} AST")
        if abs(r['reb_delta']) >= 0.5:
            sign = "+" if r['reb_delta'] > 0 else ""
            parts.append(f"{sign}{r['reb_delta']:.1f} REB")

        if not parts:
            return ""

        return f"Without {r['partner_player_name']}: {', '.join(parts)} ({r['games_sample']}g sample)"

    except Exception as e:
        print(f"[trend_engine] get_stagger_context error: {e}")
        return ""
    finally:
        conn.close()


def format_trend_line(trend_data: dict) -> str:
    """Format trend data as a compact display line for spotlights.

    Returns string like: "UP +3.2 (L7: 28.4 vs L15: 25.2) | 7/10 hit rate | 3g over streak"
    """
    if not trend_data:
        return ""

    parts = []

    # Trend direction
    label = trend_data.get('trend_label', 'STABLE')
    l7 = trend_data.get('l7_avg', 0)
    l15 = trend_data.get('l15_avg', 0)
    parts.append(f"{label} (L7: {l7:.1f} vs L15: {l15:.1f})")

    # Hit rate (if available — needs line)
    hr = trend_data.get('hit_rate_l10')
    if hr is not None:
        parts.append(f"{hr:.0f}% L10 hit rate")

    # Streak vs line (if available)
    streak = trend_data.get('streak_vs_line')
    if streak is not None and streak != 0:
        direction = "over" if streak > 0 else "under"
        parts.append(f"{abs(streak)}g {direction} streak")

    return " | ".join(parts)


def format_minutes_line(trend_data: dict) -> str:
    """Format minutes trend as a compact display line.

    Returns string like: "MINS UP +3.2 (28.4 -> 31.6)" or "Stable at 32.1 min"
    """
    if not trend_data:
        return ""

    label = trend_data.get('min_label', 'STABLE')
    l7 = trend_data.get('l7_min')
    l15 = trend_data.get('l15_min')
    delta = trend_data.get('min_delta')

    if l7 is None or l15 is None:
        return ""

    if label == 'STABLE':
        return f"Stable at {l7:.1f} min"
    elif 'UP' in label:
        return f"MINS UP +{abs(delta):.1f} ({l15:.1f} -> {l7:.1f})"
    else:
        return f"MINS DOWN {delta:.1f} ({l15:.1f} -> {l7:.1f})"
