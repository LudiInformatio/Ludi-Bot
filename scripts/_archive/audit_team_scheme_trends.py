# ARCHIVED: 2026-03-03 — Replaced by update_team_scheme_cache.py in data_sync.yml
#!/usr/bin/env python3
"""
Audit team offensive/defensive scheme classifications over multiple windows.

Outputs a markdown report with season-long and recent 21/14-day windows ending at a target date.
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.team_offensive_classifier import TeamOffensiveClassifier, TEAM_ABBR_MAP
from utils.team_defensive_classifier import TeamDefensiveClassifier


DB_PATH = "ludi.db"
DEFAULT_REPORT_PATH = Path("reports/team_scheme_trends_20260217.md")

DEFENSE_DYNAMIC_TO_MODULE_E = {
    'DROP_COVERAGE': 'PAINT_PACK',
    'RIM_FORTRESS': 'PAINT_PACK',
    'SWITCH_HEAVY': 'PERIMETER',
    'PERIMETER_FUNNEL': 'FUNNEL',
    'ZONE_FLUID': 'BLITZ',
    'NEUTRAL': 'NEUTRAL'
}


def _resolve_window_end(db_path: str, end_date: str = None) -> datetime.date:
    if end_date:
        return datetime.strptime(end_date, "%Y-%m-%d").date()
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT MAX(date) FROM games")
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return datetime.strptime(row[0], "%Y-%m-%d").date()
    except Exception:
        pass
    return datetime.strptime("2026-02-12", "%Y-%m-%d").date()


def _fetch_offensive_stats(conn, start_date, end_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            team_abbreviation as team,
            COUNT(DISTINCT game_id) as games,
            SUM(pts) * 1.0 / COUNT(DISTINCT game_id) as ppg,
            SUM(ast) * 1.0 / COUNT(DISTINCT game_id) as apg,
            SUM(fg3a) * 1.0 / COUNT(DISTINCT game_id) as t3pa,
            SUM(fg3m) * 1.0 / COUNT(DISTINCT game_id) as t3pm,
            SUM(fga) * 1.0 / COUNT(DISTINCT game_id) as fga,
            SUM(stl) * 1.0 / COUNT(DISTINCT game_id) as spg,
            CASE WHEN SUM(fgm) > 0 THEN 1.0 * SUM(ast) / SUM(fgm) ELSE 0.6 END as ast_per_fgm
        FROM player_game_logs
        WHERE game_date >= ?
          AND game_date <= ?
          AND team_abbreviation IS NOT NULL
        GROUP BY team_abbreviation
        """
    , (start_date.isoformat(), end_date.isoformat()))

    stats = {}
    for row in cur.fetchall():
        team, games, ppg, apg, t3pa, t3pm, fga, spg, ast_per_fgm = row
        normalized = TEAM_ABBR_MAP.get(team, team)
        t3pa_rate = t3pa / fga if fga and fga > 0 else 0.35
        stats[normalized] = {
            "games": games,
            "ppg": ppg,
            "ast": apg,
            "3pa": t3pa,
            "3pm": t3pm,
            "fga": fga,
            "steals": spg,
            "ast_per_fgm": ast_per_fgm,
            "3pa_rate": t3pa_rate,
            "pace": 98 + (ppg - 110) * 0.15,
        }
    return stats


def _fetch_defensive_stats(conn, team, start_date, end_date):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            pg.game_date,
            SUM(pg.catch_shoot_3pa) as opp_catch_shoot_3pa,
            SUM(pg.catch_shoot_3pm) as opp_catch_shoot_3pm,
            SUM(pg.drives_fga) as opp_drives_fga,
            SUM(pg.drives_fgm) as opp_drives_fgm,
            AVG(pg.avg_speed_off) as opp_speed,
            AVG(pg.avg_defender_dist) as opp_avg_defender_dist
        FROM player_game_tracking pg
        JOIN games g ON pg.game_date = g.date
        WHERE (g.home_team = ? OR g.away_team = ?)
          AND pg.team_abbr != ?
          AND pg.game_date >= ?
          AND pg.game_date <= ?
        GROUP BY pg.game_date
        ORDER BY pg.game_date DESC
        """
    , (team, team, team, start_date.isoformat(), end_date.isoformat()))
    rows = cur.fetchall()
    if not rows:
        return {}

    total_games = len(rows)
    def safe_avg(idx):
        vals = [r[idx] for r in rows if r[idx] is not None]
        return sum(vals) / len(vals) if vals else 0.0

    avg_opp_cs_3pa = safe_avg(1)
    avg_opp_cs_3pm = safe_avg(2)
    avg_opp_drives_fga = safe_avg(3)
    avg_opp_drives_fgm = safe_avg(4)
    avg_opp_speed = safe_avg(5)
    avg_opp_def_dist = safe_avg(6)

    opp_drive_fg_pct = (avg_opp_drives_fgm / avg_opp_drives_fga) if avg_opp_drives_fga > 0 else 0.0
    opp_cs_3p_pct = (avg_opp_cs_3pm / avg_opp_cs_3pa) if avg_opp_cs_3pa > 0 else 0.0

    return {
        "opp_catch_shoot_3pa": avg_opp_cs_3pa,
        "opp_catch_shoot_3p_pct": opp_cs_3p_pct,
        "opp_drives_fga": avg_opp_drives_fga,
        "opp_drive_fg_pct": opp_drive_fg_pct,
        "opp_speed": avg_opp_speed,
        "opp_avg_defender_dist": avg_opp_def_dist,
        "sample_size": total_games,
    }


def main():
    parser = argparse.ArgumentParser(description="Audit team scheme trends")
    parser.add_argument("--db-path", default=DB_PATH)
    parser.add_argument("--season-start", default="2025-10-01")
    parser.add_argument("--window-end", default=None)
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    report_path = Path(args.report_path)
    end_date = _resolve_window_end(args.db_path, args.window_end)
    season_start = datetime.strptime(args.season_start, "%Y-%m-%d").date()

    windows = {
        f"Season ({season_start.isoformat()} to {end_date.isoformat()})": (season_start, end_date),
        f"Last 21 days (ending {end_date.isoformat()})": (end_date - timedelta(days=20), end_date),
        f"Last 14 days (ending {end_date.isoformat()})": (end_date - timedelta(days=13), end_date),
    }

    conn = sqlite3.connect(args.db_path)

    off_classifier = TeamOffensiveClassifier(db_path=args.db_path)
    def_classifier = TeamDefensiveClassifier(db_path=args.db_path)

    teams = [
        "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET",
        "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL",
        "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX", "POR",
        "SAC", "SAS", "TOR", "UTA", "WAS"
    ]

    window_results = {}
    for label, (start_date, end_date) in windows.items():
        off_stats = _fetch_offensive_stats(conn, start_date, end_date)
        off_types = {}
        off_games = {}
        for team in teams:
            stats = off_stats.get(team)
            if not stats or stats.get("games", 0) < 5:
                off_types[team] = "INSUFFICIENT"
                off_games[team] = stats.get("games", 0) if stats else 0
                continue
            off_types[team] = off_classifier._classify_team(team, stats)
            off_games[team] = stats.get("games", 0)

        def_stats = {}
        def_games = {}
        for team in teams:
            stats = _fetch_defensive_stats(conn, team, start_date, end_date)
            if stats and stats.get("sample_size", 0) >= 5:
                def_stats[team] = stats
                def_games[team] = stats.get("sample_size", 0)
            else:
                def_games[team] = stats.get("sample_size", 0) if stats else 0

        thresholds = def_classifier._compute_relative_thresholds(def_stats)
        def_types = {}
        for team in teams:
            stats = def_stats.get(team)
            if not stats:
                def_types[team] = "INSUFFICIENT"
            else:
                dyn = def_classifier._apply_relative_rules(stats, thresholds)
                def_types[team] = DEFENSE_DYNAMIC_TO_MODULE_E.get(dyn, dyn)

        window_results[label] = {
            "off_types": off_types,
            "off_games": off_games,
            "def_types": def_types,
            "def_games": def_games,
        }

    # Build report
    lines = []
    lines.append("# Team Scheme Trends — 2026-02-17\n")
    lines.append(f"End date: {end_date.isoformat()}")
    lines.append("")

    for label, data in window_results.items():
        off_counts = Counter(data["off_types"].values())
        def_counts = Counter(data["def_types"].values())
        lines.append(f"## {label}")
        lines.append("")
        lines.append("### Offensive Distribution")
        lines.append(", ".join([f"{k}: {v}" for k, v in sorted(off_counts.items())]))
        lines.append("")
        lines.append("### Defensive Distribution")
        lines.append(", ".join([f"{k}: {v}" for k, v in sorted(def_counts.items())]))
        lines.append("")

    # Per-team table
    lines.append("## Per-Team Scheme Changes")
    lines.append("")
    lines.append("| Team | Off Season | Off 21d | Off 14d | Def Season | Def 21d | Def 14d |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")

    labels = list(windows.keys())
    for team in teams:
        off_season = window_results[labels[0]]["off_types"][team]
        off_21 = window_results[labels[1]]["off_types"][team]
        off_14 = window_results[labels[2]]["off_types"][team]
        def_season = window_results[labels[0]]["def_types"][team]
        def_21 = window_results[labels[1]]["def_types"][team]
        def_14 = window_results[labels[2]]["def_types"][team]
        lines.append(f"| {team} | {off_season} | {off_21} | {off_14} | {def_season} | {def_21} | {def_14} |")

    # Notable changes
    lines.append("")
    lines.append("## Notable Changes (Season vs 14d)")
    lines.append("")
    lines.append("### Offense")
    off_changes = []
    for team in teams:
        off_season = window_results[labels[0]]["off_types"][team]
        off_14 = window_results[labels[2]]["off_types"][team]
        if off_season != off_14:
            off_changes.append((team, off_season, off_14))
    if off_changes:
        for team, a, b in off_changes:
            lines.append(f"- {team}: {a} → {b}")
    else:
        lines.append("None")

    lines.append("")
    lines.append("### Defense")
    def_changes = []
    for team in teams:
        def_season = window_results[labels[0]]["def_types"][team]
        def_14 = window_results[labels[2]]["def_types"][team]
        if def_season != def_14:
            def_changes.append((team, def_season, def_14))
    if def_changes:
        for team, a, b in def_changes:
            lines.append(f"- {team}: {a} → {b}")
    else:
        lines.append("None")

    lines.append("")
    lines.append("## BDL Endpoint Check")
    lines.append("- BDL provides team season averages and offensive playtype data, but no defensive playtype endpoint with allowed PPP/percentiles.")
    lines.append("- Defensive Synergy remains Ghost Protocol-only for now.")

    report_path.write_text("\n".join(lines) + "\n")
    print(f"Wrote {report_path}")
    conn.close()


if __name__ == "__main__":
    main()
