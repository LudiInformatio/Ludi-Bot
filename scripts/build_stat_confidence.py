"""
LUDI INFORMATIO | PHASE 8.20: STAT CONFIDENCE BUILDER
======================================================
Nightly script — runs after bet settlement (5 AM, after nightly_debrief.yml).

Computes per-stat-side confidence metrics from settled bets and writes
cache/stat_confidence.json. Module F and curate_plays.py read this file
to apply calibration-aware edge adjustments and sizing.

Metrics computed:
  - win_rate: raw %
  - wilson_lb: Wilson 95% lower bound (conservative, sample-size adjusted)
  - sample_n: number of settled bets
  - grade: A+/B/C/D/F (based on wilson_lb + sample_n)
  - rmse: projection vs line (from module_f _STAT_RMSE constants — DB-computed if available)
  - trend: IMPROVING/DEGRADING/STABLE/SMALL_N (early vs late season comparison)
  - calibration_gap: actual WR - predicted WR (how wrong our edge is)

Usage:
  python scripts/build_stat_confidence.py
  python scripts/build_stat_confidence.py --verbose
  python scripts/build_stat_confidence.py --min-n 30   # lower threshold for debugging

Created: February 20, 2026 | Phase 8.20
"""

import argparse
import json
import math
import os
import sqlite3
import sys
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

DB_PATH = os.path.join(_PROJECT_ROOT, 'ludi.db')
CACHE_PATH = os.path.join(_PROJECT_ROOT, 'cache', 'stat_confidence.json')


def _wilson_lower_bound(wins: int, n: int, z: float = 1.96) -> float:
    """Wilson score 95% confidence interval lower bound.

    More reliable than normal approximation for small samples (n < 100).
    Returns conservative estimate of true win rate — shrinks toward 0.5 for small n.
    """
    if n == 0:
        return 0.5
    p = wins / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return max(0.0, center - margin)


def _grade(wilson_lb: float, n: int) -> str:
    """Signal quality grade based on Wilson lower bound + sample size."""
    if wilson_lb >= 0.60 and n >= 500:    return "A+"   # iron-clad
    if wilson_lb >= 0.55 and n >= 150:    return "B"    # solid
    if wilson_lb >= 0.50 and n >= 75:     return "C"    # moderate
    if wilson_lb >= 0.50:                 return "C"    # moderate, small sample
    if wilson_lb >= 0.42:                 return "D"    # uncertain
    return "F"                                           # structural avoid


def _trend(early_wr, late_wr, early_n, late_n, min_n: int = 30) -> str:
    """Compare early vs late season WR to detect degradation or improvement."""
    if early_n < min_n or late_n < min_n:
        return "SMALL_N"
    if early_wr is None or late_wr is None:
        return "SMALL_N"
    delta = late_wr - early_wr
    if delta >= 4.0:   return "IMPROVING"
    if delta <= -4.0:  return "DEGRADING"
    return "STABLE"


def build_stat_confidence(conn: sqlite3.Connection, min_n: int = 50, verbose: bool = False) -> dict:
    """Compute confidence metrics for all stat/side combos with >= min_n settled bets."""

    # 1. Overall WR per stat/side
    rows = conn.execute("""
        SELECT stat_category, bet_side,
               COUNT(*) as n,
               SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
               ROUND(AVG(true_edge), 1) as avg_edge
        FROM bet_recommendations
        WHERE outcome IN ('WIN','LOSS')
        GROUP BY stat_category, bet_side
        HAVING COUNT(*) >= ?
        ORDER BY stat_category, bet_side
    """, (min_n,)).fetchall()

    # 2. Early vs late season for trend detection (split at Jan 15 midpoint)
    trend_rows = conn.execute("""
        SELECT stat_category, bet_side,
               SUM(CASE WHEN game_date <= '2026-01-15' THEN 1 ELSE 0 END) as early_n,
               ROUND(100.0 * SUM(CASE WHEN game_date <= '2026-01-15' AND outcome='WIN' THEN 1 ELSE 0 END) /
                     NULLIF(SUM(CASE WHEN game_date <= '2026-01-15' THEN 1 ELSE 0 END), 0), 1) as early_wr,
               SUM(CASE WHEN game_date > '2026-01-15' THEN 1 ELSE 0 END) as late_n,
               ROUND(100.0 * SUM(CASE WHEN game_date > '2026-01-15' AND outcome='WIN' THEN 1 ELSE 0 END) /
                     NULLIF(SUM(CASE WHEN game_date > '2026-01-15' THEN 1 ELSE 0 END), 0), 1) as late_wr
        FROM bet_recommendations
        WHERE outcome IN ('WIN','LOSS')
        GROUP BY stat_category, bet_side
    """).fetchall()
    trend_map = {(r[0], r[1]): (r[2], r[3], r[4], r[5]) for r in trend_rows}

    # 3. RMSE from projection vs line (best available — these are Module F constants as fallback)
    rmse_fallback = {
        'BLOCKS': 0.35, 'BLK': 0.35,
        'STEALS': 0.46, 'STL': 0.46,
        '3PM': 0.67,
        'AST': 1.24,
        'REB': 1.87,
        'PTS': 4.93,
        'PA': 4.80, 'PR': 4.96, 'PRA': 5.51,
        'TURNOVERS': 1.60, 'TOV': 1.60,  # estimated (no direct DB RMSE)
        'RA': 1.67,
    }
    try:
        rmse_rows = conn.execute("""
            SELECT stat_category,
                   ROUND(SQRT(AVG((projection - line)*(projection - line))), 3) as rmse
            FROM bet_recommendations
            WHERE projection IS NOT NULL AND line IS NOT NULL
              AND projection > 0 AND line > 0
              AND outcome IN ('WIN','LOSS','PUSH')
            GROUP BY stat_category
            HAVING COUNT(*) >= 30
        """).fetchall()
        rmse_map = {r[0]: r[1] for r in rmse_rows if r[1] is not None}
    except Exception:
        rmse_map = {}

    result = {}
    for stat, side, n, wins, avg_edge in rows:
        wr = round(100.0 * wins / n, 1) if n > 0 else 0
        wlb = _wilson_lower_bound(wins, n)
        grade = _grade(wlb, n)

        trend_data = trend_map.get((stat, side), (0, None, 0, None))
        early_n, early_wr, late_n, late_wr = trend_data
        trend_label = _trend(early_wr, late_wr, early_n, late_n)

        # Calibration gap: actual WR - what avg_edge predicts (50% + edge/2 is rough model)
        if avg_edge is not None and n > 0:
            predicted_wr = 50.0 + (avg_edge / 2.0)
            calibration_gap = round(wr - predicted_wr, 1)
        else:
            calibration_gap = None

        rmse = rmse_map.get(stat) or rmse_fallback.get(stat)

        key = f"{stat}_{side}"
        result[key] = {
            "stat_category": stat,
            "bet_side": side,
            "win_rate": wr,
            "wilson_lb": round(wlb * 100, 1),
            "wins": wins,
            "sample_n": n,
            "grade": grade,
            "rmse": rmse,
            "trend": trend_label,
            "avg_edge": avg_edge,
            "calibration_gap": calibration_gap,
            "computed_at": datetime.now().isoformat(),
        }

        if verbose:
            flag = " ← PRIORITIZE" if grade == "A+" else (" ← AVOID" if grade == "F" else "")
            print(f"  {stat:12} {side:5} | WR={wr:5.1f}% | W_LB={wlb*100:.1f}% | "
                  f"n={n:4} | {grade:3} | trend={trend_label:10} | cal_gap={calibration_gap}{flag}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Build stat confidence cache")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--min-n", type=int, default=50,
                        help="Minimum settled bets to include (default 50)")
    args = parser.parse_args()

    print(f"[stat_confidence] Building cache from {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    if args.verbose:
        print(f"\n{'STAT':12} {'SIDE':5} | {'WR%':7} | {'W_LB%':6} | {'n':4} | GRADE | TREND      | GAP")
        print("-" * 80)

    data = build_stat_confidence(conn, min_n=args.min_n, verbose=args.verbose)
    conn.close()

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"[stat_confidence] Wrote {len(data)} stat/side combos → {CACHE_PATH}")

    # Summary of A+ signals
    a_plus = [(k, v['win_rate'], v['wilson_lb'], v['sample_n'])
              for k, v in data.items() if v['grade'] == 'A+']
    avoids = [(k, v['win_rate'], v['wilson_lb'], v['sample_n'])
              for k, v in data.items() if v['grade'] == 'F']
    if a_plus:
        print(f"\nA+ IRON-CLAD signals ({len(a_plus)}):")
        for k, wr, wlb, n in sorted(a_plus, key=lambda x: -x[1]):
            print(f"  {k}: {wr:.1f}% WR (floor={wlb:.1f}%, n={n})")
    if avoids:
        print(f"\nF AVOID signals ({len(avoids)}):")
        for k, wr, wlb, n in sorted(avoids, key=lambda x: x[1]):
            print(f"  {k}: {wr:.1f}% WR (floor={wlb:.1f}%, n={n})")


if __name__ == "__main__":
    main()
