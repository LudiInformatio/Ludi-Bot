#!/usr/bin/env python3
"""
Phase 8.10: Weekly League Rankings
===================================
Generates player + team ranking tables from ludi.db and sends to Telegram.
Wired into weekly_validation.yml.

Player sections: Top 10 + Bottom 5 (worst) for each playtype.
Team section: Pace leaders/laggards + Offensive ratings.

Usage:
    python scripts/generate_rankings.py
"""

import sqlite3
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.telegram_notifier import send_message

DB_PATH = "ludi.db"


def get_connection():
    return sqlite3.connect(DB_PATH, timeout=30)


def _get_playtype_rankings(conn, playtype, freq_min, limit=10, order='DESC'):
    """Generic playtype rankings — top or bottom by PPP."""
    query = f"""
        SELECT
            psp.player_name,
            psp.team_abbr,
            psp.ppp,
            psp.freq_pct,
            psp.percentile
        FROM player_synergy_playtypes psp
        WHERE psp.playtype = ?
            AND psp.freq_pct >= ?
            AND psp.player_name IN (
                SELECT player_name
                FROM player_game_logs
                WHERE game_date >= date('now', '-30 days')
                GROUP BY player_name
                HAVING COUNT(*) >= 10
            )
        ORDER BY psp.ppp {order}
        LIMIT ?
    """
    return conn.execute(query, (playtype, freq_min, limit)).fetchall()


def get_defensive_schemes(conn):
    query = """
        SELECT
            active_style,
            COUNT(*) as team_count,
            GROUP_CONCAT(team_abbr, ', ') as teams
        FROM team_scheme_cache
        WHERE scheme_type = 'DEFENSE'
        GROUP BY active_style
        ORDER BY team_count DESC
    """
    return conn.execute(query).fetchall()


def get_offensive_schemes(conn):
    query = """
        SELECT
            active_style,
            COUNT(*) as team_count,
            GROUP_CONCAT(team_abbr, ', ') as teams
        FROM team_scheme_cache
        WHERE scheme_type = 'OFFENSE'
        GROUP BY active_style
        ORDER BY team_count DESC
    """
    return conn.execute(query).fetchall()


def get_pace_and_ortg_rankings(conn):
    """Returns all teams ordered by pace (DESC). Also returns ortg-sorted rows."""
    pace_rows = conn.execute(
        "SELECT team_abbr, overall_pace, overall_ortg, overall_efg_pct "
        "FROM team_leverage_profiles "
        "WHERE overall_pace IS NOT NULL "
        "ORDER BY overall_pace DESC"
    ).fetchall()
    ortg_rows = conn.execute(
        "SELECT team_abbr, overall_ortg, overall_pace "
        "FROM team_leverage_profiles "
        "WHERE overall_ortg IS NOT NULL "
        "ORDER BY overall_ortg DESC"
    ).fetchall()
    return pace_rows, ortg_rows


def format_playtype_section(title, top_rows, bottom_rows):
    """Format a single playtype block: top 10 + bottom 5."""
    cols = ["PPP", "Freq", "Pctl"]
    lines = []

    def fmt_rows(rows, label, start_rank=1, reverse_rank=False):
        lines.append(f"{label}")
        header = f"{'#':<3} {'Player':<18} {'Tm':<4} {cols[0]:<5} {cols[1]:<6} {cols[2]}"
        lines.append(header)
        total = len(rows)
        for i, row in enumerate(rows, start_rank):
            rank = (total - i + start_rank) if reverse_rank else i
            ppp = row[2] if row[2] is not None else 0.0
            freq = row[3] if row[3] is not None else 0.0
            pctl = int(row[4]) if row[4] is not None else 0
            lines.append(
                f"{i:<3} {row[0][:16]:<18} {row[1]:<4} {ppp:>4.2f} {freq:>4.1f}% {pctl:>3}"
            )
        return lines

    lines.append(title)
    if top_rows:
        fmt_rows(top_rows, "🔝 Best:")
    else:
        lines.append("  (no data)")
    lines.append("")
    if bottom_rows:
        fmt_rows(bottom_rows, "🔻 Worst:")
    else:
        lines.append("  (no data)")

    return "\n".join(lines)


def format_scheme_table(rows, label=""):
    if not rows:
        return "No data"
    lines = [label] if label else []
    for row in rows:
        scheme = row[0] or "UNKNOWN"
        count = row[1]
        teams = row[2] if row[2] else ""
        lines.append(f"• {scheme}: {count} ({teams[:55]}{'…' if len(teams) > 55 else ''})")
    return "\n".join(lines)


def format_pace_ortg_table(pace_rows, ortg_rows):
    lines = []
    top5_pace = pace_rows[:5]
    bot5_pace = pace_rows[-5:]
    top5_ortg = ortg_rows[:5]
    bot5_ortg = ortg_rows[-5:]

    lines.append("🏃 PACE — Fastest:")
    for r in top5_pace:
        pace = r[1] if r[1] is not None else 0.0
        ortg = r[2] if r[2] is not None else 0.0
        lines.append(f"  {r[0]}: {pace:.1f} pace | ORTG {ortg:.1f}")

    lines.append("🐢 PACE — Slowest:")
    for r in bot5_pace:
        pace = r[1] if r[1] is not None else 0.0
        ortg = r[2] if r[2] is not None else 0.0
        lines.append(f"  {r[0]}: {pace:.1f} pace | ORTG {ortg:.1f}")

    lines.append("")
    lines.append("⚡ ORTG — Best offenses:")
    for r in top5_ortg:
        ortg = r[1] if r[1] is not None else 0.0
        pace = r[2] if r[2] is not None else 0.0
        lines.append(f"  {r[0]}: {ortg:.1f} ORTG ({pace:.0f} pace)")

    lines.append("🧱 ORTG — Worst offenses:")
    for r in bot5_ortg:
        ortg = r[1] if r[1] is not None else 0.0
        pace = r[2] if r[2] is not None else 0.0
        lines.append(f"  {r[0]}: {ortg:.1f} ORTG ({pace:.0f} pace)")

    return "\n".join(lines)


def generate_player_rankings_message(conn, today):
    """Player rankings: 5 playtypes × (top 10 + bottom 5)."""
    sections = [
        ("P&R BALL HANDLERS", "PR_BALL_HANDLER", 15.0),
        ("SPOT-UP SHOOTERS",  "SPOT_UP",         20.0),
        ("ISO SCORERS",       "ISO",              10.0),
        ("P&R ROLL MEN",      "PR_ROLL_MAN",      10.0),
        ("TRANSITION",        "TRANSITION",        10.0),
    ]

    msg = f"🏀 PLAYER RANKINGS (PPP) — {today}\n"
    msg += "Top 10 best + Bottom 5 worst (freq threshold per type)\n\n"

    for label, playtype, freq_min in sections:
        top = _get_playtype_rankings(conn, playtype, freq_min, limit=10, order='DESC')
        bot = _get_playtype_rankings(conn, playtype, freq_min, limit=5,  order='ASC')
        section = format_playtype_section(f"▸ {label} (freq ≥{freq_min:.0f}%)", top, bot)
        msg += "```\n" + section + "\n```\n\n"

    return msg


def generate_team_rankings_message(conn, today):
    """Team rankings: pace + ortg + offensive + defensive schemes."""
    pace_rows, ortg_rows = get_pace_and_ortg_rankings(conn)
    def_rows = get_defensive_schemes(conn)
    off_rows = get_offensive_schemes(conn)

    msg = f"📊 TEAM RANKINGS — {today}\n\n"

    msg += "1️⃣ PACE & ORTG\n```\n"
    msg += format_pace_ortg_table(pace_rows, ortg_rows)
    msg += "\n```\n\n"

    msg += "2️⃣ DEFENSIVE SCHEMES\n```\n"
    msg += format_scheme_table(def_rows)
    msg += "\n```\n\n"

    msg += "3️⃣ OFFENSIVE SCHEMES\n```\n"
    msg += format_scheme_table(off_rows)
    msg += "\n```"

    return msg


def main():
    print("🏀 Generating weekly league rankings...")

    try:
        conn = get_connection()
        today = datetime.now().strftime("%Y-%m-%d")

        # Send two separate messages (player + team) to stay under Telegram 4096 char limit
        player_msg = generate_player_rankings_message(conn, today)
        team_msg = generate_team_rankings_message(conn, today)
        conn.close()

        print(f"Player rankings: {len(player_msg)} chars | Team rankings: {len(team_msg)} chars")

        ok1 = send_message(player_msg)
        ok2 = send_message(team_msg)

        if ok1 and ok2:
            print("✅ Rankings sent to Telegram (2 messages)")
        else:
            print(f"❌ Send failures — player: {ok1}, team: {ok2}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ Error generating rankings: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
