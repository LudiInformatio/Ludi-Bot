#!/usr/bin/env python3
"""
Update team_scheme_cache with season, 21d, and 14d offensive/defensive schemes.
"""

import argparse
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.team_offensive_classifier import TeamOffensiveClassifier
from utils.team_defensive_classifier import TeamDefensiveClassifier

TEAMS = [
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET",
    "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA", "MIL",
    "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX", "POR",
    "SAC", "SAS", "TOR", "UTA", "WAS"
]

DEFENSE_DYNAMIC_TO_MODULE_E = {
    'DROP_COVERAGE': 'PAINT_PACK',
    'RIM_FORTRESS': 'PAINT_PACK',
    'SWITCH_HEAVY': 'PERIMETER',
    'PERIMETER_FUNNEL': 'FUNNEL',
    'ZONE_FLUID': 'BLITZ',
    'NEUTRAL': 'NEUTRAL'
}

SCHEME_TABLE_SQL = """
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
"""


def resolve_window_end(db_path: str, end_date: str = None) -> str:
    if end_date:
        return end_date
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT MAX(date) FROM games")
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            return row[0]
    except Exception:
        pass
    return "2026-02-12"


def normalize_recent(value: str, season: str) -> str:
    if value in (None, "INSUFFICIENT"):
        return season
    return value

def normalize_offense(value: str, fallback: str) -> str:
    if value in (None, "INSUFFICIENT"):
        return fallback
    return value


def pick_active(season: str, d21: str, d14: str) -> str:
    d21_norm = normalize_recent(d21, season)
    d14_norm = normalize_recent(d14, season)

    if d21_norm == d14_norm and d21_norm != season:
        return d14_norm

    votes = Counter([season, d21_norm, d14_norm])
    top = votes.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return season
    return top[0][0]


def main():
    parser = argparse.ArgumentParser(description="Update team_scheme_cache")
    parser.add_argument("--db-path", default="ludi.db")
    parser.add_argument("--season-start", default="2025-10-01")
    parser.add_argument("--window-end", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    window_end = resolve_window_end(args.db_path, args.window_end)
    season_start = args.season_start

    end_dt = datetime.strptime(window_end, "%Y-%m-%d")
    d21_start = (end_dt - timedelta(days=20)).strftime("%Y-%m-%d")
    d14_start = (end_dt - timedelta(days=13)).strftime("%Y-%m-%d")

    off_classifier = TeamOffensiveClassifier(db_path=args.db_path)
    def_classifier = TeamDefensiveClassifier(db_path=args.db_path)

    off_season = off_classifier.classify_all_teams(start_date=season_start, end_date=window_end, min_games=30)
    off_21 = off_classifier.classify_all_teams(start_date=d21_start, end_date=window_end, min_games=5)
    off_14 = off_classifier.classify_all_teams(start_date=d14_start, end_date=window_end, min_games=5)

    def_season_raw, def_season_stats = def_classifier.batch_classify_all_teams(
        start_date=season_start, end_date=window_end, min_games=10, return_stats=True
    )
    def_21_raw, def_21_stats = def_classifier.batch_classify_all_teams(
        start_date=d21_start, end_date=window_end, min_games=5, return_stats=True
    )
    def_14_raw, def_14_stats = def_classifier.batch_classify_all_teams(
        start_date=d14_start, end_date=window_end, min_games=5, return_stats=True
    )

    if not args.dry_run:
        conn = sqlite3.connect(args.db_path)
        cur = conn.cursor()
        cur.execute(SCHEME_TABLE_SQL)

    for team in TEAMS:
        # Offense
        s_off = normalize_offense(off_season.get(team, "INSUFFICIENT"), "BALANCED")
        d21_off = normalize_offense(off_21.get(team, "INSUFFICIENT"), s_off)
        d14_off = normalize_offense(off_14.get(team, "INSUFFICIENT"), s_off)
        a_off = pick_active(s_off, d21_off, d14_off)

        if args.verbose:
            print(f"[OFF] {team} season={s_off} 21d={d21_off} 14d={d14_off} active={a_off}")

        # Defense
        s_def_raw = def_season_raw.get(team, "NEUTRAL")
        d21_def_raw = def_21_raw.get(team, "NEUTRAL")
        d14_def_raw = def_14_raw.get(team, "NEUTRAL")

        s_def = DEFENSE_DYNAMIC_TO_MODULE_E.get(s_def_raw, s_def_raw)
        d21_def = DEFENSE_DYNAMIC_TO_MODULE_E.get(d21_def_raw, d21_def_raw)
        d14_def = DEFENSE_DYNAMIC_TO_MODULE_E.get(d14_def_raw, d14_def_raw)

        if not def_season_stats.get(team):
            s_def = "INSUFFICIENT"
        if not def_21_stats.get(team):
            d21_def = "INSUFFICIENT"
        if not def_14_stats.get(team):
            d14_def = "INSUFFICIENT"

        a_def = pick_active(s_def if s_def != "INSUFFICIENT" else "NEUTRAL", d21_def, d14_def)

        if args.verbose:
            print(f"[DEF] {team} season={s_def} 21d={d21_def} 14d={d14_def} active={a_def}")

        if not args.dry_run:
            # Upsert offense
            cur.execute(
                """
                INSERT INTO team_scheme_cache
                    (team_abbr, scheme_type, season_style, d21_style, d14_style, active_style, window_end)
                VALUES
                    (?, 'OFFENSE', ?, ?, ?, ?, ?)
                ON CONFLICT(team_abbr, scheme_type) DO UPDATE SET
                    season_style=excluded.season_style,
                    d21_style=excluded.d21_style,
                    d14_style=excluded.d14_style,
                    active_style=excluded.active_style,
                    window_end=excluded.window_end,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (team, s_off, d21_off, d14_off, a_off, window_end)
            )

            # Upsert defense
            cur.execute(
                """
                INSERT INTO team_scheme_cache
                    (team_abbr, scheme_type, season_style, d21_style, d14_style, active_style, window_end)
                VALUES
                    (?, 'DEFENSE', ?, ?, ?, ?, ?)
                ON CONFLICT(team_abbr, scheme_type) DO UPDATE SET
                    season_style=excluded.season_style,
                    d21_style=excluded.d21_style,
                    d14_style=excluded.d14_style,
                    active_style=excluded.active_style,
                    window_end=excluded.window_end,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (team, s_def, d21_def, d14_def, a_def, window_end)
            )

    if not args.dry_run:
        conn.commit()
        conn.close()

    print(f"Updated team_scheme_cache (window_end={window_end})")


if __name__ == "__main__":
    main()
