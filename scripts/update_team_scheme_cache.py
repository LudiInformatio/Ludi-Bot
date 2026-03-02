#!/usr/bin/env python3
"""
Update team_scheme_cache with 30g/15g/7g offensive/defensive schemes.
Uses game-count windows (not calendar days) for robustness against schedule gaps.
"""

import argparse
import sqlite3
import os
import sys
import math
from datetime import datetime
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.team_offensive_classifier import TeamOffensiveClassifier
from utils.team_defensive_classifier import TeamDefensiveClassifier
from utils.mappings import normalize_bdl_abbr  # F4: normalize BDL team abbreviations from player_game_advanced

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
    off_quality_14d TEXT,
    def_quality_14d TEXT,
    def_rating_14d REAL,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_abbr, scheme_type)
)
"""


def compute_team_def_quality_14d(db_path: str, d14_start: str, window_end: str) -> dict:
    """
    Compute relative defensive quality tiers using player_game_advanced.def_rating.
    Date-range version (kept for backward compatibility).

    Returns dict: {team_abbr: (tier, avg_dr_numeric)}
    """
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            """
            SELECT team_abbrev, AVG(def_rating) as avg_dr, COUNT(*) as n
            FROM player_game_advanced
            WHERE game_date >= ? AND game_date <= ?
              AND def_rating IS NOT NULL
            GROUP BY team_abbrev
            HAVING COUNT(*) >= 10
            ORDER BY avg_dr
            """,
            (d14_start, window_end),
        ).fetchall()
        conn.close()
    except Exception:
        return {}

    return _compute_def_quality_from_rows(rows)


def compute_team_off_quality_14d(db_path: str, d14_start: str, window_end: str) -> dict:
    """
    Compute relative offensive quality tiers using player_game_advanced.off_rating.
    Date-range version (kept for backward compatibility).

    Returns dict: {team_abbr: 'STRONG' | 'AVERAGE' | 'WEAK'}
    """
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            """
            SELECT team_abbrev, AVG(off_rating) as avg_or, COUNT(*) as n
            FROM player_game_advanced
            WHERE game_date >= ? AND game_date <= ?
              AND off_rating IS NOT NULL
            GROUP BY team_abbrev
            HAVING COUNT(*) >= 10
            ORDER BY avg_or DESC
            """,
            (d14_start, window_end),
        ).fetchall()
        conn.close()
    except Exception:
        return {}

    return _compute_off_quality_from_rows(rows)


def compute_team_def_quality_by_games(db_path: str, last_n_games: int, window_end: str) -> dict:
    """
    Compute relative defensive quality tiers using game-count window.

    Uses CTE with ROW_NUMBER to select last N games per team from player_game_advanced.
    Robust against schedule gaps (All-Star break, off-days).

    Returns dict: {team_abbr: (tier, avg_dr_numeric)}
    """
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            """
            WITH team_games AS (
                SELECT team_abbrev, game_date,
                       ROW_NUMBER() OVER (
                           PARTITION BY team_abbrev ORDER BY game_date DESC
                       ) as game_num
                FROM (
                    SELECT DISTINCT team_abbrev, game_date
                    FROM player_game_advanced
                    WHERE game_date <= ? AND def_rating IS NOT NULL
                )
            )
            SELECT a.team_abbrev, AVG(a.def_rating) as avg_dr, COUNT(*) as n
            FROM player_game_advanced a
            JOIN team_games tg
              ON a.team_abbrev = tg.team_abbrev AND a.game_date = tg.game_date
            WHERE tg.game_num <= ?
              AND a.def_rating IS NOT NULL
            GROUP BY a.team_abbrev
            HAVING COUNT(*) >= 10
            ORDER BY avg_dr
            """,
            (window_end, last_n_games),
        ).fetchall()
        conn.close()
    except Exception:
        return {}

    return _compute_def_quality_from_rows(rows)


def compute_team_off_quality_by_games(db_path: str, last_n_games: int, window_end: str) -> dict:
    """
    Compute relative offensive quality tiers using game-count window.

    Uses CTE with ROW_NUMBER to select last N games per team from player_game_advanced.

    Returns dict: {team_abbr: 'STRONG' | 'AVERAGE' | 'WEAK'}
    """
    try:
        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            """
            WITH team_games AS (
                SELECT team_abbrev, game_date,
                       ROW_NUMBER() OVER (
                           PARTITION BY team_abbrev ORDER BY game_date DESC
                       ) as game_num
                FROM (
                    SELECT DISTINCT team_abbrev, game_date
                    FROM player_game_advanced
                    WHERE game_date <= ? AND off_rating IS NOT NULL
                )
            )
            SELECT a.team_abbrev, AVG(a.off_rating) as avg_or, COUNT(*) as n
            FROM player_game_advanced a
            JOIN team_games tg
              ON a.team_abbrev = tg.team_abbrev AND a.game_date = tg.game_date
            WHERE tg.game_num <= ?
              AND a.off_rating IS NOT NULL
            GROUP BY a.team_abbrev
            HAVING COUNT(*) >= 10
            ORDER BY avg_or DESC
            """,
            (window_end, last_n_games),
        ).fetchall()
        conn.close()
    except Exception:
        return {}

    return _compute_off_quality_from_rows(rows)


def _compute_def_quality_from_rows(rows) -> dict:
    """Shared logic: convert def_rating rows into STRONG/AVERAGE/WEAK tiers."""
    if len(rows) < 15:
        return {}

    vals = [r[1] for r in rows]
    league_avg = sum(vals) / len(vals)
    std = math.sqrt(sum((v - league_avg) ** 2 for v in vals) / len(vals))

    result = {}
    for team_abbrev, avg_dr, _ in rows:
        if avg_dr < league_avg - std:
            tier = "STRONG"
        elif avg_dr > league_avg + std:
            tier = "WEAK"
        else:
            tier = "AVERAGE"
        result[normalize_bdl_abbr(team_abbrev)] = (tier, round(avg_dr, 2))

    return result


def _compute_off_quality_from_rows(rows) -> dict:
    """Shared logic: convert off_rating rows into STRONG/AVERAGE/WEAK tiers."""
    if len(rows) < 15:
        return {}

    vals = [r[1] for r in rows]
    league_avg = sum(vals) / len(vals)
    std = math.sqrt(sum((v - league_avg) ** 2 for v in vals) / len(vals))

    result = {}
    for team_abbrev, avg_or, _ in rows:
        canonical = normalize_bdl_abbr(team_abbrev)
        if avg_or > league_avg + std:
            result[canonical] = "STRONG"
        elif avg_or < league_avg - std:
            result[canonical] = "WEAK"
        else:
            result[canonical] = "AVERAGE"

    return result


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

    # Game-count windows — robust against schedule gaps (All-Star break, off-days).
    # Replaces calendar-day windows (60d/21d/7d) which produce noisy/empty results
    # when teams have irregular schedules. Every team gets exactly N games (or fewer
    # if early season), ensuring equal-sized samples for classification.
    GAMES_BASELINE = 30   # ~2 months of play
    GAMES_MEDIUM   = 15   # ~3-4 weeks
    GAMES_RECENT   = 7    # ~2 weeks (recent form)

    off_classifier = TeamOffensiveClassifier(db_path=args.db_path)
    def_classifier = TeamDefensiveClassifier(db_path=args.db_path)

    # BDL-based quality tiers (STRONG / AVERAGE / WEAK) — recent window shows current form.
    off_quality_14d = compute_team_off_quality_by_games(args.db_path, GAMES_RECENT, window_end)
    if args.verbose and off_quality_14d:
        print(f"[OFF QUALITY {GAMES_RECENT}g] computed for {len(off_quality_14d)} teams "
              f"(STRONG={sum(1 for v in off_quality_14d.values() if v=='STRONG')}, "
              f"WEAK={sum(1 for v in off_quality_14d.values() if v=='WEAK')})")

    def_quality_14d = compute_team_def_quality_by_games(args.db_path, GAMES_RECENT, window_end)
    if args.verbose and def_quality_14d:
        print(f"[DEF QUALITY {GAMES_RECENT}g] computed for {len(def_quality_14d)} teams "
              f"(STRONG={sum(1 for t, _ in def_quality_14d.values() if t=='STRONG')}, "
              f"WEAK={sum(1 for t, _ in def_quality_14d.values() if t=='WEAK')})")

    # Offense: [30g, 15g, 7g] game-count windows
    off_season = off_classifier.classify_all_teams_by_games(last_n_games=GAMES_BASELINE, end_date=window_end, min_games=15)
    off_21     = off_classifier.classify_all_teams_by_games(last_n_games=GAMES_MEDIUM,   end_date=window_end, min_games=8)
    off_14     = off_classifier.classify_all_teams_by_games(last_n_games=GAMES_RECENT,   end_date=window_end, min_games=3)

    # Defense: [30g, 15g, 7g] game-count windows
    def_season_raw, def_season_stats = def_classifier.batch_classify_all_teams_by_games(
        last_n_games=GAMES_BASELINE, end_date=window_end, min_games=8, return_stats=True
    )
    def_21_raw, def_21_stats = def_classifier.batch_classify_all_teams_by_games(
        last_n_games=GAMES_MEDIUM, end_date=window_end, min_games=4, return_stats=True
    )
    def_14_raw, def_14_stats = def_classifier.batch_classify_all_teams_by_games(
        last_n_games=GAMES_RECENT, end_date=window_end, min_games=2, return_stats=True
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

        # ── BDL fallback: replace INSUFFICIENT d14_def with quality-based label ──────
        # When Ghost Protocol tracking has no 14d rows, use BDL player_game_advanced
        # def_rating (daily, 35k+ rows) to classify defensive quality via z-score tiers.
        # WEAK (≥1 std dev above league avg) → NEUTRAL (scheme not executing)
        # STRONG / AVERAGE → inherit season_style (scheme is intact / status quo)
        # D3: def_quality_14d now returns (tier, avg_dr) tuple
        _def_qual_tuple = def_quality_14d.get(team, (None, None))
        team_def_quality = _def_qual_tuple[0]   # 'STRONG' | 'AVERAGE' | 'WEAK' | None
        team_def_rating_numeric = _def_qual_tuple[1]  # raw float for def_rating_14d column

        if d14_def == "INSUFFICIENT" and team_def_quality is not None:
            base = s_def if s_def not in ("INSUFFICIENT", None) else "NEUTRAL"
            d14_def = "NEUTRAL" if team_def_quality == "WEAK" else base

        a_def = pick_active(s_def if s_def != "INSUFFICIENT" else "NEUTRAL", d21_def, d14_def)

        if args.verbose:
            quality_label = f" [{team_def_quality}]" if team_def_quality else ""
            print(f"[DEF] {team} season={s_def} 21d={d21_def} 14d={d14_def}{quality_label} active={a_def}")

        team_off_quality = off_quality_14d.get(team)

        if not args.dry_run:
            # Upsert offense (includes off_quality_14d for morning brief context)
            cur.execute(
                """
                INSERT INTO team_scheme_cache
                    (team_abbr, scheme_type, season_style, d21_style, d14_style,
                     active_style, window_end, off_quality_14d)
                VALUES
                    (?, 'OFFENSE', ?, ?, ?, ?, ?, ?)
                ON CONFLICT(team_abbr, scheme_type) DO UPDATE SET
                    season_style=excluded.season_style,
                    d21_style=excluded.d21_style,
                    d14_style=excluded.d14_style,
                    active_style=excluded.active_style,
                    window_end=excluded.window_end,
                    off_quality_14d=excluded.off_quality_14d,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (team, s_off, d21_off, d14_off, a_off, window_end, team_off_quality)
            )

            # Upsert defense (includes def_quality_14d label + def_rating_14d numeric — D3)
            cur.execute(
                """
                INSERT INTO team_scheme_cache
                    (team_abbr, scheme_type, season_style, d21_style, d14_style,
                     active_style, window_end, def_quality_14d, def_rating_14d)
                VALUES
                    (?, 'DEFENSE', ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(team_abbr, scheme_type) DO UPDATE SET
                    season_style=excluded.season_style,
                    d21_style=excluded.d21_style,
                    d14_style=excluded.d14_style,
                    active_style=excluded.active_style,
                    window_end=excluded.window_end,
                    def_quality_14d=excluded.def_quality_14d,
                    def_rating_14d=excluded.def_rating_14d,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (team, s_def, d21_def, d14_def, a_def, window_end, team_def_quality, team_def_rating_numeric)
            )

    if not args.dry_run:
        conn.commit()
        conn.close()

    print(f"Updated team_scheme_cache (window_end={window_end})")


if __name__ == "__main__":
    main()
