#!/usr/bin/env python3
"""
Phase 8.10: Weekly League Rankings
===================================
Generates 5 ranking tables from ludi.db and sends to Telegram.
Wired into weekly_validation.yml.

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


def get_pr_ball_handler_rankings(conn):
    query = """
        SELECT 
            psp.player_name,
            psp.team_abbr,
            psp.ppp,
            psp.freq_pct,
            psp.percentile
        FROM player_synergy_playtypes psp
        WHERE psp.playtype = 'PR_BALL_HANDLER'
            AND psp.freq_pct >= 15.0
        ORDER BY psp.ppp DESC
        LIMIT 15
    """
    return conn.execute(query).fetchall()


def get_spot_up_rankings(conn):
    query = """
        SELECT 
            psp.player_name,
            psp.team_abbr,
            psp.ppp,
            psp.freq_pct,
            psp.percentile
        FROM player_synergy_playtypes psp
        WHERE psp.playtype = 'SPOT_UP'
            AND psp.freq_pct >= 20.0
        ORDER BY psp.ppp DESC
        LIMIT 15
    """
    return conn.execute(query).fetchall()


def get_iso_rankings(conn):
    query = """
        SELECT 
            psp.player_name,
            psp.team_abbr,
            psp.ppp,
            psp.freq_pct,
            psp.percentile
        FROM player_synergy_playtypes psp
        WHERE psp.playtype = 'ISO'
            AND psp.freq_pct >= 10.0
        ORDER BY psp.ppp DESC
        LIMIT 15
    """
    return conn.execute(query).fetchall()


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


def get_pace_rankings(conn):
    query = """
        SELECT 
            team_abbr,
            overall_pace,
            overall_ortg
        FROM team_leverage_profiles
        ORDER BY overall_pace DESC
    """
    return conn.execute(query).fetchall()


def format_rankings_table(rows, cols):
    if not rows:
        return "No data available"
    
    lines = []
    header = f"{'#':<3} {'Player':<20} {'Team':<5} {cols[0]:<6} {cols[1]:<6} {cols[2]:<6}"
    lines.append(header)
    lines.append("-" * len(header))
    
    for i, row in enumerate(rows, 1):
        if len(row) >= 5:
            ppp = row[2] if row[2] is not None else 0.0
            freq = row[3] if row[3] is not None else 0.0
            pctl = row[4] if row[4] is not None else 0
            lines.append(f"{i:<3} {row[0][:18]:<20} {row[1]:<5} {ppp:>6.2f} {freq:>5.1f}% {pctl:>5}")
        else:
            lines.append(f"{i:<3} {row[0]:<20} {row[1]:<5} {row[2]:<6.2f}")
    
    return "\n".join(lines)


def format_scheme_table(rows):
    if not rows:
        return "No data available"
    
    lines = []
    for row in rows:
        scheme = row[0]
        count = row[1]
        teams = row[2]
        lines.append(f"• {scheme}: {count} teams ({teams[:50]}{'...' if len(teams) > 50 else ''})")
    
    return "\n".join(lines)


def format_pace_table(rows):
    if not rows:
        return "No data available"
    
    lines = []
    top5 = rows[:5]
    bottom5 = rows[-5:]
    
    lines.append("🏃 FASTEST (Top 5):")
    for row in top5:
        pace = row[1] if row[1] is not None else 0.0
        ortg = row[2] if row[2] is not None else 0.0
        lines.append(f"  {row[0]}: {pace:.1f} pace (ORTG: {ortg:.1f})")
    
    lines.append("")
    lines.append("🐢 SLOWEST (Bottom 5):")
    for row in bottom5:
        pace = row[1] if row[1] is not None else 0.0
        ortg = row[2] if row[2] is not None else 0.0
        lines.append(f"  {row[0]}: {pace:.1f} pace (ORTG: {ortg:.1f})")
    
    return "\n".join(lines)


def generate_rankings_message():
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    
    message = f"📊 LUDI LEAGUE RANKINGS — {today}\n\n"
    
    message += "1️⃣ P&R BALL HANDLERS (PPP) — freq ≥15%\n"
    pr_rows = get_pr_ball_handler_rankings(conn)
    message += "```\n"
    message += format_rankings_table(pr_rows, ["PPP", "Freq", "Pctl"])
    message += "\n```\n\n"
    
    message += "2️⃣ SPOT-UP SHOOTERS (PPP) — freq ≥20%\n"
    spot_rows = get_spot_up_rankings(conn)
    message += "```\n"
    message += format_rankings_table(spot_rows, ["PPP", "Freq", "Pctl"])
    message += "\n```\n\n"
    
    message += "3️⃣ ISO SCORERS (PPP) — freq ≥10%\n"
    iso_rows = get_iso_rankings(conn)
    message += "```\n"
    message += format_rankings_table(iso_rows, ["PPP", "Freq", "Pctl"])
    message += "\n```\n\n"
    
    message += "4️⃣ DEFENSIVE SCHEMES\n"
    scheme_rows = get_defensive_schemes(conn)
    message += "```\n"
    message += format_scheme_table(scheme_rows)
    message += "\n```\n\n"
    
    message += "5️⃣ PACE LEADERS\n"
    pace_rows = get_pace_rankings(conn)
    message += "```\n"
    message += format_pace_table(pace_rows)
    message += "\n```"
    
    conn.close()
    return message


def main():
    print("🏀 Generating weekly league rankings...")
    
    try:
        message = generate_rankings_message()
        print(f"Rankings generated ({len(message)} chars)")
        
        success = send_message(message)
        
        if success:
            print("✅ Rankings sent to Telegram")
        else:
            print("❌ Failed to send rankings")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error generating rankings: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
