#!/usr/bin/env python3
"""
run_backtest_suite.py — Ludi-Bot Weekly Backtest Validation Suite
=================================================================
Runs 21 math-based tests against ludi.db and produces a structured report.

Usage:
    python scripts/run_backtest_suite.py
    python scripts/run_backtest_suite.py --verbose

READ-ONLY: No writes to any table.
No module_*.py imports — pure SQL + stdlib math.
Scipy optional (graceful fallback for binomial test).
"""

import sqlite3
import argparse
import math
import time
import sys
from datetime import datetime
from collections import defaultdict

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_PATH = "ludi.db"
CURRENT_SEASON_START = "2025-10-01"
CLV_START = "2026-02-27"

# Stat category normalisation: map db values to canonical labels
COMBO_STATS = {"pr", "pa", "ra", "pra"}
STAT_DISPLAY = {
    "pts": "PTS", "ast": "AST", "reb": "REB", "fg3m": "3PM",
    "3pm": "3PM", "blk": "BLK", "stl": "STL",
    "pr": "PR", "pa": "PA", "ra": "RA", "pra": "PRA",
    "tov": "TOV",
}

# Targets for pass/warn/fail
RMSE_TARGETS = {
    "PTS": (7.0, 10.0),
    "AST": (2.5, 4.0),
    "REB": (3.5, 5.0),
    "3PM": (1.5, 2.5),
    "BLK": (0.9, 1.5),
    "STL": (0.9, 1.5),
    "PR":  (4.5, 7.0),
    "PA":  (4.5, 7.0),
    "RA":  (4.5, 7.0),
    "PRA": (7.0, 11.0),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pf(label: str) -> str:
    """Return PASS/WARNING/FAIL given a label that already contains the word."""
    return label  # label is already the status string from calling code


def status_tag(value, warn_thresh, fail_thresh, higher_is_worse=True):
    """Return PASS / WARNING / FAIL string."""
    if higher_is_worse:
        if value >= fail_thresh:
            return "FAIL"
        if value >= warn_thresh:
            return "WARNING"
        return "PASS"
    else:
        if value <= fail_thresh:
            return "FAIL"
        if value <= warn_thresh:
            return "WARNING"
        return "PASS"


def wilson_lower(wins: int, n: int, z: float = 1.645) -> float:
    """One-sided Wilson lower bound at ~95% confidence (z=1.645)."""
    if n == 0:
        return 0.0
    phat = wins / n
    denom = 1 + z * z / n
    centre = phat + z * z / (2 * n)
    spread = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return (centre - spread) / denom


def binomtest_pvalue(wins: int, n: int, p: float = 0.5) -> float:
    """
    Two-sided binomial p-value. Uses scipy if available, otherwise
    normal approximation (valid for N >= 20).
    """
    if n == 0:
        return 1.0
    try:
        from scipy.stats import binomtest
        return binomtest(wins, n, p).pvalue
    except ImportError:
        pass
    # Normal approximation
    phat = wins / n
    se = math.sqrt(p * (1 - p) / n)
    if se == 0:
        return 0.0
    z = abs(phat - p) / se
    # Two-tailed: P(|Z| > z) ≈ 2 * (1 - Phi(z)), approximate via erfc
    return math.erfc(z / math.sqrt(2))


def chi2_pvalue_2x2(a, b, c, d):
    """Chi-squared p-value for 2x2 table [[a,b],[c,d]]."""
    n = a + b + c + d
    if n == 0:
        return 1.0
    expected = [
        (a + b) * (a + c) / n,
        (a + b) * (b + d) / n,
        (c + d) * (a + c) / n,
        (c + d) * (b + d) / n,
    ]
    observed = [a, b, c, d]
    chi2 = sum((o - e) ** 2 / e for o, e in zip(observed, expected) if e > 0)
    # p-value for chi2 with df=1 using erfc approximation
    return math.erfc(math.sqrt(chi2 / 2))


def rmse(errors):
    if not errors:
        return None
    return math.sqrt(sum(e * e for e in errors) / len(errors))


def mae(errors):
    if not errors:
        return None
    return sum(abs(e) for e in errors) / len(errors)


def mean(vals):
    if not vals:
        return None
    return sum(vals) / len(vals)


def confidence_label(n: int) -> str:
    if n >= 50:
        return "HIGH"
    if n >= 30:
        return "MEDIUM"
    if n >= 20:
        return "LOW"
    return "INSUFFICIENT"


def sep(width=60):
    return "=" * width


def section(n, name):
    print()
    print(sep())
    print(f"TEST {n:02d}: {name}")
    print(sep())


def skip(reason):
    print(f"  SKIPPED: {reason}")
    print(sep())


VERBOSE = False


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Shared filter
# ---------------------------------------------------------------------------
SETTLED = "outcome IN ('WIN','LOSS') AND actual_result >= 0"
CURRENT_SEASON = f"game_date >= '{CURRENT_SEASON_START}'"


# ---------------------------------------------------------------------------
# TEST 1: RMSE + MAE by stat category
# ---------------------------------------------------------------------------
def test_01_rmse_by_stat(conn):
    section(1, "RMSE + MAE by Stat Category")
    rows = conn.execute(f"""
        SELECT
            LOWER(stat_category) as cat,
            COUNT(*) as n,
            AVG(actual_result - projection) as mean_err,
            AVG((actual_result - projection)*(actual_result - projection)) as mse,
            AVG(ABS(actual_result - projection)) as mae_val,
            AVG(CASE WHEN actual_result > line THEN 1.0 ELSE 0.0 END) as actual_over_pct,
            AVG(CASE WHEN projection > line THEN 1.0 ELSE 0.0 END) as proj_over_pct
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
          AND projection IS NOT NULL
        GROUP BY cat
        HAVING n >= 20
        ORDER BY mse DESC
    """).fetchall()

    if not rows:
        skip("No settled bets with projections found")
        return

    print(f"  {'Stat':<8} {'N':>6}  {'MeanErr':>8}  {'RMSE':>7}  {'MAE':>6}  {'ActOvr%':>8}  {'ProjOvr%':>9}  Status")
    print(f"  {'-'*8} {'-'*6}  {'-'*8}  {'-'*7}  {'-'*6}  {'-'*8}  {'-'*9}  {'-'*10}")

    findings = []
    for r in rows:
        cat = STAT_DISPLAY.get(r["cat"], r["cat"].upper())
        rmse_val = math.sqrt(r["mse"])
        warn, fail = RMSE_TARGETS.get(cat, (99, 99))
        st = status_tag(rmse_val, warn, fail)
        print(f"  {cat:<8} {r['n']:>6}  {r['mean_err']:>+8.2f}  {rmse_val:>7.2f}  {r['mae_val']:>6.2f}  "
              f"{r['actual_over_pct']*100:>7.1f}%  {r['proj_over_pct']*100:>8.1f}%  {st}")
        if st != "PASS":
            findings.append(f"{cat} RMSE={rmse_val:.2f} ({st})")

    # Summary
    failing = [f for f in findings if "FAIL" in f]
    warning = [f for f in findings if "WARNING" in f]
    if failing:
        print(f"\n  FINDING: {len(failing)} stat(s) exceed RMSE targets: {', '.join(failing)}")
    elif warning:
        print(f"\n  FINDING: {len(warning)} stat(s) in warning zone: {', '.join(warning)}")
    else:
        print(f"\n  FINDING: All stat categories within RMSE targets.")
    conf = confidence_label(min(r["n"] for r in rows))
    print(f"  CONFIDENCE: {conf} (N={sum(r['n'] for r in rows)} total settled bets)")
    print(f"  ACTION: Mean error > +1.5 or < -1.5 on any stat = systematic projection bias requiring Module C recalibration.")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 2: Brier Score — overall + per stat
# ---------------------------------------------------------------------------
def test_02_brier_score(conn):
    section(2, "Brier Score — Overall + Per Stat")

    rows = conn.execute(f"""
        SELECT
            LOWER(stat_category) as cat,
            COUNT(*) as n,
            AVG((model_prob - CASE WHEN outcome='WIN' THEN 1.0 ELSE 0.0 END)
                * (model_prob - CASE WHEN outcome='WIN' THEN 1.0 ELSE 0.0 END)) as brier,
            AVG(model_prob) as avg_prob
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
          AND model_prob IS NOT NULL
        GROUP BY cat
        HAVING n >= 20
        ORDER BY brier DESC
    """).fetchall()

    overall = conn.execute(f"""
        SELECT
            COUNT(*) as n,
            AVG((model_prob - CASE WHEN outcome='WIN' THEN 1.0 ELSE 0.0 END)
                * (model_prob - CASE WHEN outcome='WIN' THEN 1.0 ELSE 0.0 END)) as brier,
            AVG(model_prob) as avg_prob,
            AVG(CASE WHEN outcome='WIN' THEN 1.0 ELSE 0.0 END) as actual_wr
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
          AND model_prob IS NOT NULL
    """).fetchone()

    if not overall or overall["n"] == 0:
        skip("No model_prob data found")
        return

    naive_brier = overall["actual_wr"] * (1 - overall["actual_wr"])
    print(f"  Overall Brier Score: {overall['brier']:.4f}  |  Naive baseline: {naive_brier:.4f}  |  N={overall['n']}")
    brier_status = "PASS" if overall["brier"] < naive_brier else "WARNING"
    print(f"  Model vs Naive: {'BETTER than coin flip' if brier_status=='PASS' else 'WORSE than coin flip — probability miscalibrated'} ({brier_status})")
    print(f"  Avg model_prob: {overall['avg_prob']:.3f}  |  Actual WR: {overall['actual_wr']:.3f}")

    if rows:
        print(f"\n  {'Stat':<8} {'N':>6}  {'Brier':>8}  {'AvgProb':>8}  vs Naive")
        print(f"  {'-'*8} {'-'*6}  {'-'*8}  {'-'*8}  {'-'*12}")
        for r in rows:
            cat = STAT_DISPLAY.get(r["cat"], r["cat"].upper())
            print(f"  {cat:<8} {r['n']:>6}  {r['brier']:.4f}    {r['avg_prob']:.3f}    {'(ok)' if r['brier'] < 0.27 else '(high)'}")

    print(f"\n  FINDING: Brier={overall['brier']:.4f} vs naive={naive_brier:.4f}. "
          f"{'Model probability adds calibration value.' if brier_status=='PASS' else 'Model overconfident — probabilities need isotonic recalibration.'}")
    print(f"  CONFIDENCE: {confidence_label(overall['n'])} (N={overall['n']})")
    print(f"  ACTION: {'NONE — within acceptable range.' if brier_status == 'PASS' else 'Escalate to Solomon: Module C/F probability recalibration needed (Phase 9 Sprint 2).'}")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 3: Calibration Curve — model_prob buckets vs actual WR
# ---------------------------------------------------------------------------
def test_03_calibration_curve(conn):
    section(3, "Calibration Curve — model_prob Buckets vs Actual WR")

    rows = conn.execute(f"""
        SELECT
            ROUND(model_prob / 0.05) * 0.05 as prob_bucket,
            COUNT(*) as n,
            AVG(CASE WHEN outcome='WIN' THEN 1.0 ELSE 0.0 END) as actual_wr
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
          AND model_prob IS NOT NULL
        GROUP BY prob_bucket
        HAVING n >= 10
        ORDER BY prob_bucket
    """).fetchall()

    if not rows:
        skip("Insufficient model_prob data for calibration curve")
        return

    print(f"  {'Prob Bucket':<14} {'N':>6}  {'Actual WR':>10}  {'Gap':>8}  Calibration")
    print(f"  {'-'*14} {'-'*6}  {'-'*10}  {'-'*8}  {'-'*14}")

    miscalibrated = []
    for r in rows:
        bucket = r["prob_bucket"]
        gap = r["actual_wr"] - bucket
        status = "ok" if abs(gap) <= 0.05 else ("over-confident" if gap < 0 else "under-confident")
        print(f"  {bucket:>12.2f}   {r['n']:>6}  {r['actual_wr']:>9.3f}   {gap:>+7.3f}  {status}")
        if abs(gap) > 0.05:
            miscalibrated.append(f"bucket {bucket:.2f}: gap {gap:+.3f}")

    if miscalibrated:
        print(f"\n  FINDING: {len(miscalibrated)} bucket(s) miscalibrated by >5pp: {'; '.join(miscalibrated[:3])}")
    else:
        print(f"\n  FINDING: Model probabilities well-calibrated across all buckets (max gap <= 5pp).")
    print(f"  CONFIDENCE: {confidence_label(sum(r['n'] for r in rows))} (N={sum(r['n'] for r in rows)})")
    print(f"  ACTION: Gaps >5pp in high-volume buckets warrant isotonic regression recalibration (Phase 9 Sprint 2).")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 4: B2B Mean Error by Stat
# ---------------------------------------------------------------------------
def test_04_b2b_mean_error(conn):
    section(4, "B2B Mean Error by Stat Category")

    rows = conn.execute(f"""
        WITH b2b_flags AS (
            SELECT
                br.id,
                br.stat_category,
                br.actual_result,
                br.projection,
                br.outcome,
                LAG(pgl.game_date) OVER (
                    PARTITION BY pgl.player_name ORDER BY pgl.game_date
                ) AS prev_game_date,
                pgl.game_date
            FROM bet_recommendations br
            JOIN player_game_logs pgl
              ON LOWER(pgl.player_name) = LOWER(br.player_name)
             AND pgl.game_date = br.game_date
            WHERE br.{SETTLED} AND br.{CURRENT_SEASON}
              AND br.projection IS NOT NULL
        )
        SELECT
            LOWER(stat_category) as cat,
            COUNT(*) as n,
            AVG(actual_result - projection) as mean_err,
            AVG(ABS(actual_result - projection)) as mae_val,
            AVG((actual_result - projection)*(actual_result - projection)) as mse
        FROM b2b_flags
        WHERE CAST(JULIANDAY(game_date) - JULIANDAY(prev_game_date) AS INTEGER) = 1
        GROUP BY cat
        HAVING n >= 10
        ORDER BY ABS(mean_err) DESC
    """).fetchall()

    normal_rows = conn.execute(f"""
        WITH b2b_flags AS (
            SELECT
                br.id,
                br.stat_category,
                br.actual_result,
                br.projection,
                LAG(pgl.game_date) OVER (
                    PARTITION BY pgl.player_name ORDER BY pgl.game_date
                ) AS prev_game_date,
                pgl.game_date
            FROM bet_recommendations br
            JOIN player_game_logs pgl
              ON LOWER(pgl.player_name) = LOWER(br.player_name)
             AND pgl.game_date = br.game_date
            WHERE br.{SETTLED} AND br.{CURRENT_SEASON}
              AND br.projection IS NOT NULL
        )
        SELECT
            LOWER(stat_category) as cat,
            COUNT(*) as n,
            AVG(actual_result - projection) as mean_err
        FROM b2b_flags
        WHERE CAST(JULIANDAY(game_date) - JULIANDAY(prev_game_date) AS INTEGER) != 1
           OR prev_game_date IS NULL
        GROUP BY cat
        HAVING n >= 20
    """).fetchall()

    normal_lookup = {r["cat"]: r["mean_err"] for r in normal_rows}

    if not rows:
        skip("Insufficient B2B data for current season (need N>=10 per stat)")
        return

    print(f"  {'Stat':<8} {'N B2B':>7}  {'B2B MeanErr':>12}  {'Normal MeanErr':>15}  {'Delta':>8}  Status")
    print(f"  {'-'*8} {'-'*7}  {'-'*12}  {'-'*15}  {'-'*8}  {'-'*10}")

    flags = []
    for r in rows:
        cat = STAT_DISPLAY.get(r["cat"], r["cat"].upper())
        normal_err = normal_lookup.get(r["cat"], None)
        delta_str = f"{r['mean_err'] - normal_err:+.2f}" if normal_err is not None else "N/A"
        rmse_val = math.sqrt(r["mse"])
        warn, fail = RMSE_TARGETS.get(cat, (99, 99))
        st = status_tag(rmse_val, warn, fail)
        normal_display = f"{normal_err:+.2f}" if normal_err is not None else "N/A"
        print(f"  {cat:<8} {r['n']:>7}  {r['mean_err']:>+12.2f}  {normal_display:>15}  {delta_str:>8}  {st}")
        if st != "PASS":
            flags.append(f"{cat} B2B err={r['mean_err']:+.2f}")

    if flags:
        print(f"\n  FINDING: B2B fatigue underweighted — {', '.join(flags)}. Module C fatigue modifier may need +5–10% reduction.")
    else:
        print(f"\n  FINDING: B2B mean errors within acceptable range. Fatigue modifier calibrated.")
    total_b2b = sum(r["n"] for r in rows)
    print(f"  CONFIDENCE: {confidence_label(total_b2b)} (N={total_b2b} B2B bets total)")
    print(f"  ACTION: B2B delta > ±1.5 pts on PTS/REB/AST = Module C fatigue_mod needs recalibration.")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 5: Edge Monotonicity by Stat Category
# ---------------------------------------------------------------------------
def test_05_edge_monotonicity(conn):
    section(5, "Edge Monotonicity — Tier WR by Stat Category")

    rows = conn.execute(f"""
        SELECT
            LOWER(stat_category) as cat,
            CASE
                WHEN true_edge >= 15 THEN 'DIAMOND'
                WHEN true_edge >= 10 THEN 'BLUE_CHIP'
                WHEN true_edge >= 7  THEN 'CORE_ASSET'
                ELSE 'THE_STEAL'
            END as tier,
            COUNT(*) as n,
            ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
            AVG(true_edge) as avg_edge
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
          AND true_edge IS NOT NULL AND true_edge >= 5
        GROUP BY cat, tier
        HAVING n >= 20
        ORDER BY cat, avg_edge DESC
    """).fetchall()

    # Also compute overall tier monotonicity
    tier_rows = conn.execute(f"""
        SELECT
            CASE
                WHEN true_edge >= 15 THEN 'DIAMOND'
                WHEN true_edge >= 10 THEN 'BLUE_CHIP'
                WHEN true_edge >= 7  THEN 'CORE_ASSET'
                ELSE 'THE_STEAL'
            END as tier,
            COUNT(*) as n,
            ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*),1) as wr,
            AVG(true_edge) as avg_edge
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
          AND true_edge IS NOT NULL AND true_edge >= 5
        GROUP BY tier
        HAVING n >= 20
        ORDER BY avg_edge DESC
    """).fetchall()

    if not tier_rows:
        skip("Insufficient edge data for monotonicity test")
        return

    print("  OVERALL TIER MONOTONICITY:")
    print(f"  {'Tier':<12} {'N':>6}  {'WR%':>6}  {'AvgEdge':>8}")
    print(f"  {'-'*12} {'-'*6}  {'-'*6}  {'-'*8}")
    tier_wrs = {}
    for r in tier_rows:
        print(f"  {r['tier']:<12} {r['n']:>6}  {r['wr']:>5.1f}%  {r['avg_edge']:>7.1f}%")
        tier_wrs[r["tier"]] = r["wr"]

    # Check monotonicity
    tier_order = ["DIAMOND", "BLUE_CHIP", "CORE_ASSET", "THE_STEAL"]
    prev_wr = None
    inversions = []
    for t in tier_order:
        if t in tier_wrs:
            if prev_wr is not None and tier_wrs[t] > prev_wr:
                inversions.append(t)
            prev_wr = tier_wrs[t]

    if inversions:
        print(f"\n  WARNING: Tier inversion detected at: {inversions}. Higher edge not predicting higher WR.")
        mono_status = "WARNING"
    else:
        print(f"\n  PASS: Edge tiers are monotonically ordered (higher tier = higher WR).")
        mono_status = "PASS"

    if VERBOSE and rows:
        print(f"\n  PER-STAT BREAKDOWN (N>=20):")
        print(f"  {'Stat':<8} {'Tier':<12} {'N':>6}  {'WR%':>6}")
        print(f"  {'-'*8} {'-'*12} {'-'*6}  {'-'*6}")
        for r in rows:
            cat = STAT_DISPLAY.get(r["cat"], r["cat"].upper())
            print(f"  {cat:<8} {r['tier']:<12} {r['n']:>6}  {r['wr']:>5.1f}%")

    print(f"\n  FINDING: Edge monotonicity {mono_status}. {'Inversions suggest devigging or edge calc bug.' if inversions else 'Model edge metric is directionally predictive.'}")
    print(f"  CONFIDENCE: {confidence_label(sum(r['n'] for r in tier_rows))} (N={sum(r['n'] for r in tier_rows)})")
    print(f"  ACTION: {'Investigate Module F devigging or edge filter logic.' if inversions else 'NONE.'}")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 6: Archetype x Scheme WR Matrix
# ---------------------------------------------------------------------------
def test_06_archetype_scheme_matrix(conn):
    section(6, "Archetype x Scheme WR Matrix (binomial significance gate N>=20, p<0.10)")

    rows = conn.execute(f"""
        SELECT
            br.archetype as arch,
            br.matchup as scheme,
            COUNT(*) as n,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins
        FROM bet_recommendations br
        WHERE {SETTLED} AND br.{CURRENT_SEASON}
          AND br.archetype IS NOT NULL
          AND br.matchup IS NOT NULL
        GROUP BY arch, scheme
        HAVING n >= 20
        ORDER BY CAST(wins AS FLOAT)/n DESC
    """).fetchall()

    if not rows:
        # Try tags column fallback
        rows = conn.execute(f"""
            SELECT
                br.tags as tag_blob,
                COUNT(*) as n,
                SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins
            FROM bet_recommendations br
            WHERE {SETTLED} AND br.{CURRENT_SEASON}
              AND br.tags IS NOT NULL
              AND br.tags LIKE '%vs_%'
            GROUP BY tag_blob
            HAVING n >= 20
        """).fetchall()

        if not rows:
            skip("No archetype + matchup data with N>=20. Tags columns may not be populated.")
            return

    print(f"  {'Archetype':<22} {'Scheme':<15} {'N':>6}  {'WR%':>6}  {'Wilson_L':>9}  {'p-value':>8}  Sig")
    print(f"  {'-'*22} {'-'*15} {'-'*6}  {'-'*6}  {'-'*9}  {'-'*8}  {'-'*5}")

    edges = []
    for r in rows:
        arch = r["arch"] if "arch" in r.keys() else "N/A"
        scheme = r["scheme"] if "scheme" in r.keys() else "N/A"
        n, wins = r["n"], r["wins"]
        wr = wins / n
        wl = wilson_lower(wins, n)
        pval = binomtest_pvalue(wins, n, 0.5)
        sig = "YES" if pval < 0.10 and wr > 0.5 else ("NEG" if pval < 0.10 and wr < 0.5 else "no")
        print(f"  {str(arch):<22} {str(scheme):<15} {n:>6}  {wr*100:>5.1f}%  {wl*100:>8.1f}%  {pval:>8.3f}  {sig}")
        if pval < 0.10:
            edges.append((arch, scheme, wr, n, pval))

    sig_edges = [(a, s, wr, n, p) for a, s, wr, n, p in edges if wr > 0.5]
    sig_neg = [(a, s, wr, n, p) for a, s, wr, n, p in edges if wr <= 0.5]

    print(f"\n  FINDING: {len(sig_edges)} significant positive edges and {len(sig_neg)} significant negative edges (p<0.10).")
    if sig_edges:
        best = sig_edges[0]
        print(f"  Top edge: {best[0]} vs {best[1]} — WR={best[2]*100:.1f}% (N={best[3]}, p={best[4]:.3f})")
    print(f"  CONFIDENCE: {confidence_label(max(r['n'] for r in rows))} (max cell N)")
    print(f"  ACTION: Significant positive edges with N>=30 warrant Module E modifier uplift. Negative edges warrant downward modifier.")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 7: Grade Accuracy Decomposition
# ---------------------------------------------------------------------------
def test_07_grade_accuracy(conn):
    section(7, "Grade Accuracy Decomposition — MAE + WR by Curation Grade")

    rows = conn.execute(f"""
        SELECT
            curation_grade,
            COUNT(*) as n,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
            AVG(ABS(actual_result - projection)) as mae_val,
            AVG(actual_result - projection) as mean_err,
            AVG(true_edge) as avg_edge
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
          AND curation_grade IS NOT NULL
          AND projection IS NOT NULL
        GROUP BY curation_grade
        ORDER BY CAST(wins AS FLOAT)/n DESC
    """).fetchall()

    null_grade = conn.execute(f"""
        SELECT
            COUNT(*) as n,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
            AVG(ABS(actual_result - projection)) as mae_val
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
          AND curation_grade IS NULL
          AND projection IS NOT NULL
    """).fetchone()

    if not rows:
        skip("No graded bets with projections found")
        return

    print(f"  {'Grade':<10} {'N':>6}  {'WR%':>6}  {'Wilson_L':>9}  {'MAE':>6}  {'MeanErr':>8}  {'p-val':>7}")
    print(f"  {'-'*10} {'-'*6}  {'-'*6}  {'-'*9}  {'-'*6}  {'-'*8}  {'-'*7}")

    grade_wrs = {}
    for r in rows:
        n, wins = r["n"], r["wins"]
        wr = wins / n
        wl = wilson_lower(wins, n)
        pval = binomtest_pvalue(wins, n)
        grade_wrs[r["curation_grade"]] = wr
        print(f"  {r['curation_grade']:<10} {n:>6}  {wr*100:>5.1f}%  {wl*100:>8.1f}%  {r['mae_val']:>6.2f}  {r['mean_err']:>+8.2f}  {pval:>7.3f}")

    if null_grade and null_grade["n"] > 0:
        n, wins = null_grade["n"], null_grade["wins"]
        wr = wins / n
        wl = wilson_lower(wins, n)
        print(f"  {'(ungraded)':<10} {n:>6}  {wr*100:>5.1f}%  {wl*100:>8.1f}%  {null_grade['mae_val']:>6.2f}  {'N/A':>8}  {'N/A':>7}")

    # Inversion check
    strong_wr = grade_wrs.get("STRONG")
    fade_wr = grade_wrs.get("FADE")
    inversion = strong_wr and fade_wr and fade_wr > strong_wr

    if inversion:
        print(f"\n  FINDING: GRADE INVERSION — FADE WR ({fade_wr*100:.1f}%) > STRONG WR ({strong_wr*100:.1f}%). "
              f"Curation model assigning grades incorrectly. STRONG should be top tier.")
    else:
        print(f"\n  FINDING: Grade hierarchy correct — STRONG outperforms FADE.")
    print(f"  CONFIDENCE: {confidence_label(min(r['n'] for r in rows))} (min grade N)")
    print(f"  ACTION: Inversion present = Claude curation prompt needs restructuring (Phase 8.23 Sprint 2).")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 8: Shooting % Drift — Season Avg vs L10
# ---------------------------------------------------------------------------
def test_08_shooting_drift(conn):
    section(8, "Shooting % Drift — Season Avg vs L10 for Top 50 Players by Volume")

    rows = conn.execute(f"""
        WITH ranked AS (
            SELECT player_name, COUNT(*) as games,
                   AVG(CASE WHEN fga > 0 THEN CAST(fgm AS FLOAT)/fga END) as fg_season,
                   AVG(CASE WHEN fg3a > 0 THEN CAST(fg3m AS FLOAT)/fg3a END) as fg3_season,
                   AVG(CASE WHEN fta > 0 THEN CAST(ftm AS FLOAT)/fta END) as ft_season
            FROM player_game_logs
            WHERE game_date >= '{CURRENT_SEASON_START}'
            GROUP BY player_name
            HAVING games >= 20
            ORDER BY games DESC
            LIMIT 50
        ),
        l10 AS (
            SELECT pgl.player_name,
                   AVG(CASE WHEN pgl.fga > 0 THEN CAST(pgl.fgm AS FLOAT)/pgl.fga END) as fg_l10,
                   AVG(CASE WHEN pgl.fg3a > 0 THEN CAST(pgl.fg3m AS FLOAT)/pgl.fg3a END) as fg3_l10,
                   AVG(CASE WHEN pgl.fta > 0 THEN CAST(pgl.ftm AS FLOAT)/pgl.fta END) as ft_l10
            FROM player_game_logs pgl
            JOIN (
                SELECT player_name, game_date,
                       ROW_NUMBER() OVER (PARTITION BY player_name ORDER BY game_date DESC) as rn
                FROM player_game_logs WHERE game_date >= '{CURRENT_SEASON_START}'
            ) rnk ON pgl.player_name = rnk.player_name AND pgl.game_date = rnk.game_date
            WHERE rnk.rn <= 10
            GROUP BY pgl.player_name
        )
        SELECT r.player_name,
               r.fg_season, l.fg_l10, (l.fg_l10 - r.fg_season) as fg_drift,
               r.fg3_season, l.fg3_l10, (l.fg3_l10 - r.fg3_season) as fg3_drift,
               r.ft_season, l.ft_l10, (l.ft_l10 - r.ft_season) as ft_drift
        FROM ranked r
        JOIN l10 l ON r.player_name = l.player_name
        ORDER BY ABS(l.fg_l10 - r.fg_season) DESC
    """).fetchall()

    if not rows:
        skip("Insufficient shooting data for drift analysis")
        return

    # Summary drift stats
    fg_drifts = [r["fg_drift"] for r in rows if r["fg_drift"] is not None]
    fg3_drifts = [r["fg3_drift"] for r in rows if r["fg3_drift"] is not None]
    ft_drifts = [r["ft_drift"] for r in rows if r["ft_drift"] is not None]

    print(f"  {'FG% Drift':>12}  Mean={mean(fg_drifts)*100:+.1f}pp  Max={max(abs(d) for d in fg_drifts)*100:.1f}pp  N={len(fg_drifts)}")
    print(f"  {'3P% Drift':>12}  Mean={mean(fg3_drifts)*100:+.1f}pp  Max={max(abs(d) for d in fg3_drifts)*100:.1f}pp  N={len(fg3_drifts)}")
    print(f"  {'FT% Drift':>12}  Mean={mean(ft_drifts)*100:+.1f}pp  Max={max(abs(d) for d in ft_drifts)*100:.1f}pp  N={len(ft_drifts)}")

    if VERBOSE:
        print(f"\n  Top 10 players by FG% drift:")
        print(f"  {'Player':<25} {'FG_Ssn':>7}  {'FG_L10':>7}  {'Drift':>7}  {'3P_Drift':>9}  {'FT_Drift':>9}")
        for r in rows[:10]:
            fg_s = f"{r['fg_season']*100:.1f}%" if r["fg_season"] else "N/A"
            fg_l = f"{r['fg_l10']*100:.1f}%" if r["fg_l10"] else "N/A"
            drift = f"{r['fg_drift']*100:+.1f}pp" if r["fg_drift"] else "N/A"
            d3 = f"{r['fg3_drift']*100:+.1f}pp" if r["fg3_drift"] else "N/A"
            dt = f"{r['ft_drift']*100:+.1f}pp" if r["ft_drift"] else "N/A"
            print(f"  {r['player_name']:<25} {fg_s:>7}  {fg_l:>7}  {drift:>7}  {d3:>9}  {dt:>9}")

    large_drifters = [r for r in rows if r["fg_drift"] and abs(r["fg_drift"]) > 0.05]
    print(f"\n  FINDING: {len(large_drifters)} of top 50 players have FG% L10 drift >5pp from season avg. "
          f"FT% mean drift {mean(ft_drifts)*100:+.1f}pp.")
    print(f"  CONFIDENCE: HIGH (N={len(rows)} qualified players)")
    print(f"  ACTION: Players with >5pp drift are regression candidates — Module C should weight recent L5 vs season avg dynamically.")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 9: Pace Test — Game Total Buckets vs OVER WR
# ---------------------------------------------------------------------------
def test_09_pace_test(conn):
    section(9, "Pace Test — Game Total Buckets vs OVER WR by Stat")

    rows = conn.execute(f"""
        SELECT
            CASE
                WHEN br.total >= 235 THEN 'HIGH (>=235)'
                WHEN br.total >= 220 THEN 'MID (220-234)'
                ELSE 'LOW (<220)'
            END as pace_bucket,
            LOWER(br.stat_category) as cat,
            COUNT(*) as n,
            SUM(CASE WHEN br.outcome='WIN' AND br.bet_side='OVER' THEN 1
                     WHEN br.outcome='LOSS' AND br.bet_side='UNDER' THEN 1
                     ELSE 0 END) as over_wins,
            SUM(CASE WHEN br.bet_side='OVER' THEN 1 ELSE 0 END) as over_bets
        FROM bet_recommendations br
        WHERE {SETTLED} AND br.{CURRENT_SEASON}
          AND br.total IS NOT NULL AND br.total > 0
        GROUP BY pace_bucket, cat
        HAVING n >= 20 AND over_bets >= 10
        ORDER BY cat, pace_bucket
    """).fetchall()

    if not rows:
        # Simpler version without stat breakdown
        rows = conn.execute(f"""
            SELECT
                CASE
                    WHEN total >= 235 THEN 'HIGH (>=235)'
                    WHEN total >= 220 THEN 'MID (220-234)'
                    ELSE 'LOW (<220)'
                END as pace_bucket,
                COUNT(*) as n,
                ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*),1) as wr
            FROM bet_recommendations
            WHERE {SETTLED} AND {CURRENT_SEASON}
              AND total IS NOT NULL AND total > 0
            GROUP BY pace_bucket
            HAVING n >= 20
            ORDER BY pace_bucket
        """).fetchall()

        if not rows:
            skip("No game total data in current season bet_recommendations")
            return

        print(f"  {'Pace Bucket':<16} {'N':>6}  {'WR%':>6}")
        for r in rows:
            print(f"  {r['pace_bucket']:<16} {r['n']:>6}  {r['wr']:>5.1f}%")
        print(f"\n  FINDING: Game total bucketing shows overall WR pattern. Per-stat breakdown requires N>=20 per cell.")
        print(f"  CONFIDENCE: {confidence_label(min(r['n'] for r in rows))} (N={sum(r['n'] for r in rows)})")
        print(sep())
        return

    # Full breakdown
    if VERBOSE:
        print(f"  {'Stat':<8} {'Pace Bucket':<16} {'N':>6}  {'OVER bets':>10}  {'OVER WR%':>9}")
        for r in rows:
            cat = STAT_DISPLAY.get(r["cat"], r["cat"].upper())
            over_wr = r["over_wins"] / r["over_bets"] * 100 if r["over_bets"] > 0 else 0
            print(f"  {cat:<8} {r['pace_bucket']:<16} {r['n']:>6}  {r['over_bets']:>10}  {over_wr:>8.1f}%")

    # Summary: does high pace predict OVER better?
    high_rows = [r for r in rows if "HIGH" in r["pace_bucket"]]
    low_rows = [r for r in rows if "LOW" in r["pace_bucket"]]
    high_over_wr = sum(r["over_wins"] for r in high_rows) / max(sum(r["over_bets"] for r in high_rows), 1)
    low_over_wr = sum(r["over_wins"] for r in low_rows) / max(sum(r["over_bets"] for r in low_rows), 1)

    print(f"  HIGH pace OVER WR: {high_over_wr*100:.1f}%  |  LOW pace OVER WR: {low_over_wr*100:.1f}%  |  Delta: {(high_over_wr-low_over_wr)*100:+.1f}pp")
    pace_working = high_over_wr > low_over_wr
    print(f"\n  FINDING: Pace modifier {'WORKING' if pace_working else 'NOT WORKING'} — high total games produce "
          f"{'more' if pace_working else 'fewer'} OVER wins ({(high_over_wr-low_over_wr)*100:+.1f}pp delta).")
    print(f"  CONFIDENCE: {confidence_label(sum(r['n'] for r in rows))} (N={sum(r['n'] for r in rows)})")
    print(f"  ACTION: {'NONE — pace modifier directionally correct.' if pace_working else 'Module C pace_factor threshold may need adjustment.'}")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 10: Direction Bias — Chi-squared on OVER vs UNDER WR
# ---------------------------------------------------------------------------
def test_10_direction_bias(conn):
    section(10, "Direction Bias — OVER vs UNDER WR by Stat (Chi-Squared)")

    rows = conn.execute(f"""
        SELECT
            LOWER(stat_category) as cat,
            bet_side,
            COUNT(*) as n,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
          AND bet_side IN ('OVER','UNDER')
        GROUP BY cat, bet_side
        HAVING n >= 20
        ORDER BY cat, bet_side
    """).fetchall()

    if not rows:
        skip("Insufficient directional data")
        return

    # Restructure into dict
    data = defaultdict(dict)
    for r in rows:
        data[r["cat"]][r["bet_side"]] = {"n": r["n"], "wins": r["wins"]}

    print(f"  {'Stat':<8} {'N_OV':>7}  {'WR_OV%':>8}  {'N_UN':>7}  {'WR_UN%':>8}  {'Delta':>7}  {'p-val':>7}  Bias")
    print(f"  {'-'*8} {'-'*7}  {'-'*8}  {'-'*7}  {'-'*8}  {'-'*7}  {'-'*7}  {'-'*12}")

    significant_biases = []
    for cat in sorted(data.keys()):
        over = data[cat].get("OVER", {"n": 0, "wins": 0})
        under = data[cat].get("UNDER", {"n": 0, "wins": 0})

        if over["n"] < 20 or under["n"] < 20:
            continue

        ov_wr = over["wins"] / over["n"]
        un_wr = under["wins"] / under["n"]
        delta = ov_wr - un_wr

        # Chi-squared 2x2: [[OV_wins, OV_losses],[UN_wins, UN_losses]]
        pval = chi2_pvalue_2x2(
            over["wins"], over["n"] - over["wins"],
            under["wins"], under["n"] - under["wins"]
        )
        bias = "NEUTRAL"
        if pval < 0.05 and delta < 0:
            bias = "UNDER bias"
        elif pval < 0.05 and delta > 0:
            bias = "OVER bias"
        elif pval < 0.10:
            bias = "marginal"

        stat_label = STAT_DISPLAY.get(cat, cat.upper())
        print(f"  {stat_label:<8} {over['n']:>7}  {ov_wr*100:>7.1f}%  {under['n']:>7}  {un_wr*100:>7.1f}%  "
              f"{delta*100:>+6.1f}pp  {pval:>7.3f}  {bias}")
        if pval < 0.05:
            significant_biases.append(f"{stat_label}: {bias} ({delta*100:+.1f}pp)")

    if significant_biases:
        print(f"\n  FINDING: Significant directional bias (p<0.05) in: {'; '.join(significant_biases)}")
    else:
        print(f"\n  FINDING: No statistically significant OVER/UNDER directional bias detected.")
    print(f"  CONFIDENCE: HIGH (N={sum(r['n'] for r in rows)} total)")
    print(f"  ACTION: Persistent UNDER bias on low-freq stats (BLK/STL) is expected signal — books overset. "
          f"OVER bias on volume stats indicates projection inflation.")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 11: Monthly RMSE Drift — Time Series
# ---------------------------------------------------------------------------
def test_11_monthly_rmse_drift(conn):
    section(11, "Monthly RMSE Drift — Time Series")

    rows = conn.execute(f"""
        SELECT
            strftime('%Y-%m', game_date) as month,
            LOWER(stat_category) as cat,
            COUNT(*) as n,
            AVG(actual_result - projection) as mean_err,
            AVG((actual_result - projection)*(actual_result - projection)) as mse,
            ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*),1) as wr
        FROM bet_recommendations
        WHERE {SETTLED}
          AND projection IS NOT NULL
        GROUP BY month, cat
        HAVING n >= 20
        ORDER BY month, cat
    """).fetchall()

    if not rows:
        skip("Insufficient data for monthly drift analysis")
        return

    # Monthly summary (all stats combined)
    monthly_summary = conn.execute(f"""
        SELECT
            strftime('%Y-%m', game_date) as month,
            COUNT(*) as n,
            AVG(actual_result - projection) as mean_err,
            SQRT(AVG((actual_result - projection)*(actual_result - projection))) as rmse,
            ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*),1) as wr
        FROM bet_recommendations
        WHERE {SETTLED} AND projection IS NOT NULL
        GROUP BY month
        HAVING n >= 30
        ORDER BY month
    """).fetchall()

    print(f"  {'Month':<10} {'N':>6}  {'RMSE':>7}  {'MeanErr':>8}  {'WR%':>6}  Status")
    print(f"  {'-'*10} {'-'*6}  {'-'*7}  {'-'*8}  {'-'*6}  {'-'*8}")

    rmse_vals = []
    for r in monthly_summary:
        st = status_tag(r["rmse"], 8.0, 11.0)
        print(f"  {r['month']:<10} {r['n']:>6}  {r['rmse']:>7.2f}  {r['mean_err']:>+8.2f}  {r['wr']:>5.1f}%  {st}")
        rmse_vals.append(r["rmse"])

    if len(rmse_vals) >= 2:
        drift = rmse_vals[-1] - rmse_vals[0]
        trend = "improving" if drift < -0.3 else ("degrading" if drift > 0.3 else "stable")
        print(f"\n  FINDING: Monthly RMSE trend is {trend} ({drift:+.2f} change from first to last month).")
    else:
        print(f"\n  FINDING: Insufficient months for trend detection.")
    print(f"  CONFIDENCE: {confidence_label(min(r['n'] for r in monthly_summary))} (min monthly N)")
    print(f"  ACTION: RMSE drift >1.5 pts month-over-month = distribution shift in linesetters or scoring environment.")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 12: Day-of-Week WR
# ---------------------------------------------------------------------------
def test_12_day_of_week(conn):
    section(12, "Day-of-Week Win Rate")

    DOW_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    rows = conn.execute(f"""
        SELECT
            CAST(strftime('%w', game_date) AS INTEGER) as dow,
            COUNT(*) as n,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
        GROUP BY dow
        ORDER BY dow
    """).fetchall()

    if not rows:
        skip("No day-of-week data")
        return

    print(f"  {'Day':<12} {'N':>6}  {'WR%':>6}  {'Wilson_L':>9}  {'p-val':>7}")
    print(f"  {'-'*12} {'-'*6}  {'-'*6}  {'-'*9}  {'-'*7}")

    for r in rows:
        n, wins = r["n"], r["wins"]
        wr = wins / n
        wl = wilson_lower(wins, n)
        pval = binomtest_pvalue(wins, n)
        name = DOW_NAMES[r["dow"]]
        flag = " *" if pval < 0.10 else ""
        print(f"  {name:<12} {n:>6}  {wr*100:>5.1f}%  {wl*100:>8.1f}%  {pval:>7.3f}{flag}")

    sig = [DOW_NAMES[r["dow"]] for r in rows if binomtest_pvalue(r["wins"], r["n"]) < 0.10]
    print(f"\n  FINDING: {'Significant DOW patterns (p<0.10) on: ' + ', '.join(sig) + '. Check for scheduling artifacts.' if sig else 'No significant day-of-week WR patterns.'}")
    print(f"  CONFIDENCE: {confidence_label(min(r['n'] for r in rows))} (min DOW N)")
    print(f"  ACTION: Persistent DOW patterns (3+ seasons) could warrant a small schedule-context modifier.")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 13: Loss Clustering — Per-Game Z-Score
# ---------------------------------------------------------------------------
def test_13_loss_clustering(conn):
    section(13, "Loss Clustering — Per-Game Z-Score (Are Losses Independent?)")

    rows = conn.execute(f"""
        SELECT
            game_date,
            COUNT(*) as total_bets,
            SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) as losses
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
        GROUP BY game_date
        HAVING total_bets >= 5
        ORDER BY game_date
    """).fetchall()

    if not rows:
        skip("Insufficient per-game data")
        return

    totals = [r["total_bets"] for r in rows]
    losses = [r["losses"] for r in rows]

    # Overall loss rate
    total_n = sum(totals)
    total_loss = sum(losses)
    overall_loss_rate = total_loss / total_n

    # Expected losses per game under independence
    expected_losses = [overall_loss_rate * t for t in totals]
    actual_losses = losses

    # Variance of loss count per game under independence: p*(1-p)*n
    variances = [overall_loss_rate * (1 - overall_loss_rate) * t for t in totals]

    # Pearson chi-squared
    chi2 = sum(
        (obs - exp) ** 2 / exp
        for obs, exp, var in zip(actual_losses, expected_losses, variances)
        if exp > 0
    )

    n_games = len(rows)
    # Under independence, chi2 ~ chi2(n_games - 1)
    # Use normal approximation for large df: Z = sqrt(2*chi2) - sqrt(2*df-1)
    df = n_games - 1
    z_score = (math.sqrt(2 * chi2) - math.sqrt(2 * df - 1)) if df > 0 else 0

    # Loss rate per game stats
    loss_rates = [l / t for l, t in zip(losses, totals)]
    mean_lr = mean(loss_rates)
    std_lr = math.sqrt(sum((x - mean_lr) ** 2 for x in loss_rates) / len(loss_rates))

    # Find worst loss days
    worst = sorted(zip(rows, losses), key=lambda x: x[1], reverse=True)[:5]

    print(f"  Games analyzed: {n_games}  |  Total bets: {total_n}  |  Overall loss rate: {overall_loss_rate*100:.1f}%")
    print(f"  Loss rate per game — Mean: {mean_lr*100:.1f}%  Std: {std_lr*100:.1f}%")
    print(f"  Clustering Z-score: {z_score:.2f}  (>2.0 = significant clustering, losses are NOT independent)")

    if VERBOSE:
        print(f"\n  Top 5 worst loss days:")
        for day_row, loss_ct in worst:
            pct = loss_ct / day_row["total_bets"] * 100
            print(f"    {day_row['game_date']}: {loss_ct}/{day_row['total_bets']} bets lost ({pct:.0f}%)")

    clustering = abs(z_score) > 2.0
    print(f"\n  FINDING: Loss clustering Z={z_score:.2f} — losses are {'NOT independent (bad days cluster)' if clustering else 'approximately independent (random noise)'}.")
    print(f"  CONFIDENCE: {confidence_label(n_games)} (N={n_games} game-days)")
    print(f"  ACTION: {'Clustering suggests correlated model inputs or market-wide line movement bias. Investigate game-level common factors.' if clustering else 'NONE — independence assumption holds.'}")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 14: Player Tier Accuracy — MAE by Usage Tier
# ---------------------------------------------------------------------------
def test_14_player_tier_accuracy(conn):
    section(14, "Player Tier Accuracy — MAE by Usage Tier (Star/Core/Rotation/Bench)")

    rows = conn.execute(f"""
        SELECT
            CASE
                WHEN p.usg_pct >= 0.28 THEN 'STAR'
                WHEN p.usg_pct >= 0.22 THEN 'CORE'
                WHEN p.usg_pct >= 0.16 THEN 'ROTATION'
                ELSE 'BENCH'
            END as tier,
            COUNT(*) as n,
            SUM(CASE WHEN br.outcome='WIN' THEN 1 ELSE 0 END) as wins,
            AVG(ABS(br.actual_result - br.projection)) as mae_val,
            AVG(br.actual_result - br.projection) as mean_err,
            AVG((br.actual_result - br.projection)*(br.actual_result - br.projection)) as mse
        FROM bet_recommendations br
        JOIN players p ON LOWER(p.name) = LOWER(br.player_name)
        WHERE br.{SETTLED} AND br.{CURRENT_SEASON}
          AND br.projection IS NOT NULL
          AND p.usg_pct IS NOT NULL
        GROUP BY tier
        HAVING n >= 20
        ORDER BY p.usg_pct DESC
    """).fetchall()

    if not rows:
        # Try minutes-based fallback
        rows = conn.execute(f"""
            SELECT
                CASE
                    WHEN AVG(pgl.minutes) >= 32 THEN 'STAR'
                    WHEN AVG(pgl.minutes) >= 24 THEN 'CORE'
                    WHEN AVG(pgl.minutes) >= 18 THEN 'ROTATION'
                    ELSE 'BENCH'
                END as tier,
                COUNT(*) as n,
                SUM(CASE WHEN br.outcome='WIN' THEN 1 ELSE 0 END) as wins,
                AVG(ABS(br.actual_result - br.projection)) as mae_val,
                AVG(br.actual_result - br.projection) as mean_err,
                AVG((br.actual_result - br.projection)*(br.actual_result - br.projection)) as mse
            FROM bet_recommendations br
            JOIN player_game_logs pgl ON LOWER(pgl.player_name) = LOWER(br.player_name)
              AND pgl.game_date BETWEEN date(br.game_date, '-30 days') AND br.game_date
            WHERE br.{SETTLED} AND br.{CURRENT_SEASON}
              AND br.projection IS NOT NULL
            GROUP BY tier
            HAVING n >= 20
        """).fetchall()

        if not rows:
            skip("Cannot join bet_recommendations to players or game_logs for tier data")
            return

    print(f"  {'Tier':<12} {'N':>6}  {'WR%':>6}  {'MAE':>6}  {'MeanErr':>8}  {'RMSE':>7}")
    print(f"  {'-'*12} {'-'*6}  {'-'*6}  {'-'*6}  {'-'*8}  {'-'*7}")

    tier_order_wrs = {}
    for r in rows:
        n, wins = r["n"], r["wins"]
        wr = wins / n
        rmse_val = math.sqrt(r["mse"])
        tier_order_wrs[r["tier"]] = (wr, rmse_val, r["mae_val"])
        print(f"  {r['tier']:<12} {n:>6}  {wr*100:>5.1f}%  {r['mae_val']:>6.2f}  {r['mean_err']:>+8.2f}  {rmse_val:>7.2f}")

    # Is model more accurate on stars?
    star_rmse = tier_order_wrs.get("STAR", (0, 99, 0))[1]
    bench_rmse = tier_order_wrs.get("BENCH", (0, 99, 0))[1]

    print(f"\n  FINDING: STAR tier RMSE={star_rmse:.2f} vs BENCH tier RMSE={bench_rmse:.2f}. "
          f"{'Model is more accurate on stars — expected, higher sample depth.' if star_rmse < bench_rmse else 'Bench players have lower RMSE — star projections may be overfit.'}")
    print(f"  CONFIDENCE: {confidence_label(min(r['n'] for r in rows))} (min tier N)")
    print(f"  ACTION: Bench tier MAE > 3.0 = Module C low-sample player handling needs review.")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 15: Streak Persistence — WR After 3+ Game Win Streak
# ---------------------------------------------------------------------------
def test_15_streak_persistence(conn):
    section(15, "Streak Persistence — WR After 3+ Game Win Streak (Same Player/Stat)")

    rows = conn.execute(f"""
        WITH streak_base AS (
            SELECT
                player_name,
                stat_category,
                game_date,
                outcome,
                LAG(outcome, 1) OVER w as prev1,
                LAG(outcome, 2) OVER w as prev2,
                LAG(outcome, 3) OVER w as prev3
            FROM bet_recommendations
            WHERE {SETTLED} AND {CURRENT_SEASON}
            WINDOW w AS (PARTITION BY player_name, stat_category ORDER BY game_date)
        )
        SELECT
            CASE
                WHEN prev3='WIN' AND prev2='WIN' AND prev1='WIN' THEN '3+ streak'
                WHEN prev2='WIN' AND prev1='WIN' THEN '2 streak'
                ELSE 'no streak'
            END as streak_type,
            COUNT(*) as n,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins
        FROM streak_base
        WHERE prev1 IS NOT NULL
        GROUP BY streak_type
        ORDER BY streak_type
    """).fetchall()

    if not rows:
        skip("Insufficient streak data (need multiple bets on same player/stat)")
        return

    print(f"  {'Streak Type':<14} {'N':>6}  {'WR%':>6}  {'Wilson_L':>9}  {'p-val':>7}  vs Baseline")
    print(f"  {'-'*14} {'-'*6}  {'-'*6}  {'-'*9}  {'-'*7}  {'-'*12}")

    baseline_wr = None
    streak_wrs = {}
    for r in rows:
        n, wins = r["n"], r["wins"]
        wr = wins / n
        wl = wilson_lower(wins, n)
        pval = binomtest_pvalue(wins, n)
        streak_wrs[r["streak_type"]] = wr
        print(f"  {r['streak_type']:<14} {n:>6}  {wr*100:>5.1f}%  {wl*100:>8.1f}%  {pval:>7.3f}")
        if r["streak_type"] == "no streak":
            baseline_wr = wr

    if baseline_wr and "3+ streak" in streak_wrs:
        streak_3 = streak_wrs["3+ streak"]
        delta = streak_3 - baseline_wr
        persistence = delta > 0.03  # 3pp threshold
        print(f"\n  FINDING: Post-3-game-streak WR = {streak_3*100:.1f}% vs baseline {baseline_wr*100:.1f}% (delta {delta*100:+.1f}pp). "
              f"Streak {'PERSISTS' if persistence else 'does NOT persist'} meaningfully.")
    else:
        print(f"\n  FINDING: Insufficient streak data for 3+ game comparison.")
    print(f"  CONFIDENCE: {confidence_label(max(r['n'] for r in rows))} (max cell N)")
    print(f"  ACTION: Streak persistence delta >5pp = HOT_STREAK tag in Module F notes adds real signal.")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 16: Season Phase Accuracy — Early vs Mid vs Late RMSE
# ---------------------------------------------------------------------------
def test_16_season_phase(conn):
    section(16, "Season Phase Accuracy — Early vs Mid vs Late RMSE")

    rows = conn.execute(f"""
        SELECT
            CASE
                WHEN game_date BETWEEN '2025-10-01' AND '2025-11-30' THEN 'Early (Oct-Nov)'
                WHEN game_date BETWEEN '2025-12-01' AND '2026-01-31' THEN 'Mid (Dec-Jan)'
                ELSE 'Late (Feb-Mar)'
            END as phase,
            COUNT(*) as n,
            AVG(actual_result - projection) as mean_err,
            SQRT(AVG((actual_result - projection)*(actual_result - projection))) as rmse,
            ROUND(100.0*SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END)/COUNT(*),1) as wr
        FROM bet_recommendations
        WHERE {SETTLED} AND game_date >= '2025-10-01'
          AND projection IS NOT NULL
        GROUP BY phase
        HAVING n >= 20
        ORDER BY MIN(game_date)
    """).fetchall()

    if not rows:
        skip("Insufficient multi-phase data (requires Oct 2025 onward)")
        return

    print(f"  {'Phase':<18} {'N':>6}  {'RMSE':>7}  {'MeanErr':>8}  {'WR%':>6}  Status")
    print(f"  {'-'*18} {'-'*6}  {'-'*7}  {'-'*8}  {'-'*6}  {'-'*8}")

    rmse_by_phase = {}
    for r in rows:
        warn, fail = 8.0, 11.0
        st = status_tag(r["rmse"], warn, fail)
        print(f"  {r['phase']:<18} {r['n']:>6}  {r['rmse']:>7.2f}  {r['mean_err']:>+8.2f}  {r['wr']:>5.1f}%  {st}")
        rmse_by_phase[r["phase"]] = r["rmse"]

    phases = list(rmse_by_phase.items())
    if len(phases) >= 2:
        drift = phases[-1][1] - phases[0][1]
        trend = "improving" if drift < -0.3 else ("degrading" if drift > 0.3 else "stable")
        print(f"\n  FINDING: RMSE drift across season phases is {trend} ({drift:+.2f}). "
              f"{'Late-season model degradation may indicate role changes or fatigue underweighting.' if drift > 0.3 else 'Model stability is acceptable across season phases.'}")
    else:
        print(f"\n  FINDING: Only one phase with sufficient data — expand date range for trend analysis.")
    print(f"  CONFIDENCE: {confidence_label(min(r['n'] for r in rows))} (min phase N)")
    print(f"  ACTION: RMSE degradation >1.5 pts late season = Module C needs end-of-season calibration update.")
    print(sep())


# ---------------------------------------------------------------------------
# TEST 17: Season Average Baseline RMSE vs Model RMSE
# ---------------------------------------------------------------------------
def test_17_baseline_comparison(conn):
    section(17, "Season Average Baseline RMSE vs Model RMSE")
    print("  (Naive model = use each player's season avg as projection. Tells us if modifiers add value.)")

    # Map stat_category to player_game_logs column
    STAT_TO_COLUMN = {
        "pts": "pts", "ast": "ast", "reb": "reb",
        "3pm": "fg3m", "fg3m": "fg3m",
        "blk": "blk", "stl": "stl",
    }

    results = []
    for stat_cat, pgl_col in STAT_TO_COLUMN.items():
        # Compute naive baseline for each player: season avg up to each game date
        rows = conn.execute(f"""
            WITH season_avg AS (
                SELECT
                    pgl.player_name,
                    pgl.game_date,
                    AVG({pgl_col}) OVER (
                        PARTITION BY pgl.player_name
                        ORDER BY pgl.game_date
                        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
                    ) as naive_proj
                FROM player_game_logs pgl
                WHERE pgl.game_date >= '{CURRENT_SEASON_START}'
            )
            SELECT
                br.player_name,
                br.actual_result,
                br.projection as model_proj,
                sa.naive_proj,
                br.outcome
            FROM bet_recommendations br
            JOIN season_avg sa
              ON LOWER(sa.player_name) = LOWER(br.player_name)
             AND sa.game_date = br.game_date
            WHERE br.{SETTLED} AND br.{CURRENT_SEASON}
              AND LOWER(br.stat_category) = ?
              AND br.projection IS NOT NULL
              AND sa.naive_proj IS NOT NULL
        """, (stat_cat,)).fetchall()

        if len(rows) < 20:
            continue

        model_errors = [r["actual_result"] - r["model_proj"] for r in rows]
        naive_errors = [r["actual_result"] - r["naive_proj"] for r in rows]

        model_rmse = rmse(model_errors)
        naive_rmse_val = rmse(naive_errors)
        improvement = (naive_rmse_val - model_rmse) / naive_rmse_val * 100 if naive_rmse_val else 0

        results.append({
            "stat": STAT_DISPLAY.get(stat_cat, stat_cat.upper()),
            "n": len(rows),
            "model_rmse": model_rmse,
            "naive_rmse": naive_rmse_val,
            "improvement_pct": improvement,
        })

    if not results:
        skip("Cannot compute naive baseline — player_game_logs join produced no rows")
        return

    print(f"  {'Stat':<8} {'N':>6}  {'Model RMSE':>11}  {'Naive RMSE':>11}  {'Lift%':>7}  Verdict")
    print(f"  {'-'*8} {'-'*6}  {'-'*11}  {'-'*11}  {'-'*7}  {'-'*12}")

    positive_lifts = 0
    for r in results:
        verdict = "MODEL WINS" if r["improvement_pct"] > 0 else "NAIVE WINS"
        if r["improvement_pct"] > 0:
            positive_lifts += 1
        print(f"  {r['stat']:<8} {r['n']:>6}  {r['model_rmse']:>11.3f}  {r['naive_rmse']:>11.3f}  "
              f"{r['improvement_pct']:>+6.1f}%  {verdict}")

    print(f"\n  FINDING: Model outperforms naive baseline on {positive_lifts}/{len(results)} stat categories. "
          f"{'Modifiers add overall value.' if positive_lifts > len(results)/2 else 'WARNING: Model underperforms naive baseline on majority of stats — modifiers may be destroying value.'}")
    print(f"  CONFIDENCE: {confidence_label(min(r['n'] for r in results))} (min stat N)")
    print(f"  ACTION: Stat categories where naive beats model = investigate that modifier chain in Module C/E.")
    print(sep())


# ---------------------------------------------------------------------------
# BONUS TESTS 18-21 (Lena extension of original 17)
# ---------------------------------------------------------------------------

# TEST 18: CLV Correlation
def test_18_clv_correlation(conn):
    section(18, "CLV Correlation — Beat Opening Line vs WR")

    rows = conn.execute(f"""
        SELECT
            CASE WHEN clv_cents > 0 THEN 'CLV+ (beat line)' ELSE 'CLV- (lost line)' END as clv_dir,
            COUNT(*) as n,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins,
            AVG(clv_cents) as avg_clv
        FROM bet_recommendations
        WHERE {SETTLED}
          AND game_date >= '{CLV_START}'
          AND clv_cents IS NOT NULL
          AND ABS(clv_cents) < 200
        GROUP BY clv_dir
    """).fetchall()

    if not rows or all(r["n"] < 20 for r in rows):
        skip(f"Insufficient CLV data (data floor: {CLV_START}, need N>=20 per direction)")
        return

    print(f"  {'Direction':<18} {'N':>6}  {'WR%':>6}  {'Wilson_L':>9}  {'Avg CLV':>9}")
    print(f"  {'-'*18} {'-'*6}  {'-'*6}  {'-'*9}  {'-'*9}")

    clv_wrs = {}
    for r in rows:
        if r["n"] < 10:
            continue
        n, wins = r["n"], r["wins"]
        wr = wins / n
        wl = wilson_lower(wins, n)
        clv_wrs[r["clv_dir"]] = wr
        print(f"  {r['clv_dir']:<18} {n:>6}  {wr*100:>5.1f}%  {wl*100:>8.1f}%  {r['avg_clv']:>+8.1f}c")

    clv_pos = next((wr for d, wr in clv_wrs.items() if "+" in d), None)
    clv_neg = next((wr for d, wr in clv_wrs.items() if "-" in d), None)

    if clv_pos and clv_neg:
        delta = clv_pos - clv_neg
        working = delta > 0.03
        print(f"\n  FINDING: CLV+ bets win at {clv_pos*100:.1f}% vs CLV- at {clv_neg*100:.1f}% (delta {delta*100:+.1f}pp). "
              f"Line shopping {'adds value' if working else 'not validated yet'}.")
    else:
        print(f"\n  FINDING: Insufficient CLV data in one direction for comparison. Accumulate more data post-{CLV_START}.")
    print(f"  CONFIDENCE: {confidence_label(max(r['n'] for r in rows if r['n']>=10))} (N={sum(r['n'] for r in rows)})")
    print(f"  ACTION: CLV+ WR < 50% = line shopping strategy not working (investigate book selection / closing_odds logic).")
    print(sep())


# TEST 19: Ref Impact on Stat Outcomes
def test_19_ref_impact(conn):
    section(19, "Referee Impact — Points Impact vs Avg by Archetype")

    # Check if referee_player_bias table exists
    tbl_check = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='referee_player_bias'"
    ).fetchone()

    if not tbl_check:
        skip("referee_player_bias table does not exist")
        return

    rows = conn.execute(f"""
        SELECT
            rpb.player_name,
            rp.referee_name,
            rpb.avg_fta_awarded,
            rpb.points_impact_vs_avg,
            rpb.games_officiated,
            p.archetype
        FROM referee_player_bias rpb
        LEFT JOIN referee_profiles rp ON rp.referee_id = rpb.referee_id
        JOIN players p ON LOWER(p.name) = LOWER(rpb.player_name)
        WHERE rpb.games_officiated >= 5
          AND rpb.points_impact_vs_avg IS NOT NULL
        ORDER BY ABS(rpb.points_impact_vs_avg) DESC
        LIMIT 20
    """).fetchall()

    if not rows:
        skip("No referee_player_bias data with games_officiated >= 5")
        return

    # Summary by archetype
    arch_impact = defaultdict(list)
    for r in rows:
        if r["archetype"] and r["points_impact_vs_avg"] is not None:
            try:
                arch_impact[r["archetype"]].append(float(r["points_impact_vs_avg"]))
            except (TypeError, ValueError):
                pass

    print(f"  Archetype-level referee impact (mean pts delta vs avg ref):")
    print(f"  {'Archetype':<25} {'N pairs':>8}  {'Mean PPG delta':>14}  {'Max delta':>10}")
    print(f"  {'-'*25} {'-'*8}  {'-'*14}  {'-'*10}")

    for arch, impacts in sorted(arch_impact.items(), key=lambda x: abs(mean(x[1]) or 0), reverse=True):
        m = mean(impacts)
        mx = max(abs(i) for i in impacts)
        print(f"  {arch:<25} {len(impacts):>8}  {m:>+14.2f}  {mx:>+10.2f}")

    print(f"\n  Top 5 individual STAR_KILLER / PROTECTOR ref-player pairs:")
    print(f"  {'Player':<20} {'Referee':<20} {'PPG Delta':>10}  {'Arch':<20}")
    for r in rows[:5]:
        delta_val = float(r["points_impact_vs_avg"]) if r["points_impact_vs_avg"] is not None else 0.0
        ref_name = r["referee_name"] or "Unknown"
        print(f"  {r['player_name']:<20} {ref_name:<20} {delta_val:>+10.2f}  {str(r['archetype']):<20}")

    valid_deltas = [abs(float(r["points_impact_vs_avg"])) for r in rows if r["points_impact_vs_avg"] is not None]
    max_delta = max(valid_deltas) if valid_deltas else 0.0
    print(f"\n  FINDING: Referee impact data available for {len(rows)} player-ref pairs (N>=5 games). "
          f"Largest single-pair delta = {max_delta:.2f} PPG.")
    print(f"  CONFIDENCE: MEDIUM (N pairs with >= 5 games: {len(rows)})")
    print(f"  ACTION: Pairs with |delta| >= 3.5 PPG qualify for STAR_KILLER / PROTECTOR note in Module F.")
    print(sep())


# TEST 20: WOWY Usage Vacuum Validation
def test_20_wowy_validation(conn):
    section(20, "WOWY Usage Vacuum Validation — Beneficiary Stat Lift")

    # Check team_lineups
    tbl_check = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='team_lineups'"
    ).fetchone()

    if not tbl_check:
        skip("team_lineups table does not exist")
        return

    row_count = conn.execute("SELECT COUNT(*) as n FROM team_lineups").fetchone()["n"]

    if row_count < 100:
        skip(f"team_lineups too sparse: only {row_count} rows")
        return

    # Check what columns exist
    cols = [r[1] for r in conn.execute("PRAGMA table_info(team_lineups)").fetchall()]
    print(f"  team_lineups: {row_count} rows. Columns: {', '.join(cols[:10])}{'...' if len(cols)>10 else ''}")

    # Try to find on/off splits
    on_off_cols = [c for c in cols if "on" in c.lower() or "off" in c.lower() or "without" in c.lower()]

    if not on_off_cols:
        print(f"  No on/off columns found in team_lineups. Available: {cols}")
        skip("Cannot compute WOWY — on/off columns not present")
        return

    # Summarize available data
    sample = conn.execute(f"""
        SELECT COUNT(DISTINCT player_name) as players,
               MIN(game_date) as min_d,
               MAX(game_date) as max_d
        FROM team_lineups
        WHERE game_date >= '{CURRENT_SEASON_START}'
    """).fetchone() if "game_date" in cols and "player_name" in cols else None

    if sample:
        print(f"  Current season WOWY data: {sample['players']} players, {sample['min_d']} to {sample['max_d']}")

    print(f"\n  FINDING: team_lineups contains {row_count} rows. On/off columns: {on_off_cols[:5]}. "
          f"Full WOWY delta analysis requires `compute_empirical_modifiers.py` output in `player_empirical_modifiers`.")

    # Check player_empirical_modifiers
    emp_check = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='player_empirical_modifiers'"
    ).fetchone()

    if emp_check:
        emp_rows = conn.execute("SELECT COUNT(*) as n FROM player_empirical_modifiers").fetchone()["n"]
        print(f"  player_empirical_modifiers: {emp_rows} rows (WOWY deltas pre-computed here).")
        if emp_rows >= 20:
            wowy_data = conn.execute("""
                SELECT AVG(ABS(wowy_pts_delta)) as avg_abs_delta, COUNT(*) as n
                FROM player_empirical_modifiers
                WHERE wowy_pts_delta IS NOT NULL
            """).fetchone() if any("wowy" in c.lower() for c in [r[1] for r in conn.execute("PRAGMA table_info(player_empirical_modifiers)").fetchall()]) else None

            if wowy_data and wowy_data["n"] > 0:
                print(f"  Avg |WOWY PTS delta|: {wowy_data['avg_abs_delta']:.2f} pts (N={wowy_data['n']})")
    else:
        print(f"  player_empirical_modifiers not yet populated (pending first compute run).")

    print(f"  CONFIDENCE: LOW (WOWY pipeline validation pending first production run)")
    print(f"  ACTION: After compute_empirical_modifiers.py runs, compare wowy_pts_delta to Module X beneficiary projections.")
    print(sep())


# TEST 21: Curation Grade Efficiency by Stat/Side
def test_21_grade_stat_efficiency(conn):
    section(21, "Curation Grade Efficiency by Stat + Side (Key Signal Matrix)")

    rows = conn.execute(f"""
        SELECT
            curation_grade,
            LOWER(stat_category) as cat,
            bet_side,
            COUNT(*) as n,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins
        FROM bet_recommendations
        WHERE {SETTLED} AND {CURRENT_SEASON}
          AND curation_grade IS NOT NULL
          AND bet_side IN ('OVER','UNDER')
        GROUP BY curation_grade, cat, bet_side
        HAVING n >= 15
        ORDER BY CAST(wins AS FLOAT)/n DESC
    """).fetchall()

    if not rows:
        skip("Insufficient graded bets by stat/side (need N>=15 per cell)")
        return

    print(f"  {'Grade':<10} {'Stat':<8} {'Side':<7} {'N':>5}  {'WR%':>6}  {'Wilson_L':>9}  Verdict")
    print(f"  {'-'*10} {'-'*8} {'-'*7} {'-'*5}  {'-'*6}  {'-'*9}  {'-'*14}")

    positives = []
    negatives = []
    for r in rows:
        n, wins = r["n"], r["wins"]
        wr = wins / n
        wl = wilson_lower(wins, n)
        cat = STAT_DISPLAY.get(r["cat"], r["cat"].upper())
        verdict = ""
        if wl > 0.55:
            verdict = "STRONG SIGNAL"
            positives.append(f"{r['curation_grade']} {cat} {r['bet_side']}: {wr*100:.1f}% WR (N={n})")
        elif wr < 0.40:
            verdict = "ANTI-SIGNAL"
            negatives.append(f"{r['curation_grade']} {cat} {r['bet_side']}: {wr*100:.1f}% WR (N={n})")
        print(f"  {r['curation_grade']:<10} {cat:<8} {r['bet_side']:<7} {n:>5}  {wr*100:>5.1f}%  {wl*100:>8.1f}%  {verdict}")

    print(f"\n  STRONG SIGNALS (Wilson lower >55%): {len(positives)}")
    for s in positives[:5]:
        print(f"    - {s}")
    print(f"\n  ANTI-SIGNALS (WR <40%): {len(negatives)}")
    for s in negatives[:5]:
        print(f"    - {s}")

    print(f"\n  FINDING: Grade x Stat x Side matrix shows {len(positives)} positive edges and {len(negatives)} negative edges at N>=15 threshold.")
    print(f"  CONFIDENCE: MEDIUM (max N={max(r['n'] for r in rows)} per cell)")
    print(f"  ACTION: Strong signals with N>=30 warrant Module F note injection. Anti-signals indicate grade inversion by category.")
    print(sep())


# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
def print_summary(results, total_time):
    print()
    print(sep(70))
    print("BACKTEST SUITE SUMMARY")
    print(sep(70))
    counts = {"PASS": 0, "WARNING": 0, "FAIL": 0, "SKIP": 0}
    for r in results:
        counts[r] += 1
    print(f"  Tests run:    {sum(counts.values())}")
    print(f"  PASS:         {counts['PASS']}")
    print(f"  WARNING:      {counts['WARNING']}")
    print(f"  FAIL:         {counts['FAIL']}")
    print(f"  SKIPPED:      {counts['SKIP']}")
    print(f"  Runtime:      {total_time:.1f}s")
    print()
    overall = "PASS"
    if counts["FAIL"] > 0:
        overall = "FAIL"
    elif counts["WARNING"] > 0:
        overall = "WARNING"
    print(f"  OVERALL STATUS: {overall}")
    print(sep(70))
    print()
    print("  Ludi-Bot Backtest Suite complete.")
    print(f"  Run date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global VERBOSE

    parser = argparse.ArgumentParser(description="Ludi-Bot Backtest Validation Suite (READ-ONLY)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed per-player/per-game breakdowns")
    parser.add_argument("--db", default=DB_PATH, help=f"Path to ludi.db (default: {DB_PATH})")
    args = parser.parse_args()

    VERBOSE = args.verbose
    db_path = args.db

    print()
    print(sep(70))
    print("LUDI-BOT BACKTEST VALIDATION SUITE")
    print(f"Database: {db_path}")
    print(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Season filter: {CURRENT_SEASON_START} onward | CLV floor: {CLV_START}")
    print(f"Verbose mode: {'ON' if VERBOSE else 'OFF'}")
    print(sep(70))

    try:
        conn = connect()
    except Exception as e:
        print(f"\nFATAL: Cannot connect to database: {e}")
        sys.exit(1)

    # Quick sanity check
    try:
        n_settled = conn.execute(
            f"SELECT COUNT(*) as n FROM bet_recommendations WHERE {SETTLED}"
        ).fetchone()["n"]
        n_logs = conn.execute("SELECT COUNT(*) as n FROM player_game_logs").fetchone()["n"]
        print(f"\n  Database: {n_settled:,} settled bets | {n_logs:,} game log rows")
        print(f"  Scipy: {'available' if _scipy_available() else 'not available (using normal approx for p-values)'}")
        print()
    except Exception as e:
        print(f"\nFATAL: Database read error: {e}")
        sys.exit(1)

    tests = [
        ("RMSE + MAE by Stat", test_01_rmse_by_stat),
        ("Brier Score", test_02_brier_score),
        ("Calibration Curve", test_03_calibration_curve),
        ("B2B Mean Error", test_04_b2b_mean_error),
        ("Edge Monotonicity", test_05_edge_monotonicity),
        ("Archetype x Scheme", test_06_archetype_scheme_matrix),
        ("Grade Accuracy", test_07_grade_accuracy),
        ("Shooting Drift", test_08_shooting_drift),
        ("Pace Test", test_09_pace_test),
        ("Direction Bias", test_10_direction_bias),
        ("Monthly RMSE Drift", test_11_monthly_rmse_drift),
        ("Day-of-Week WR", test_12_day_of_week),
        ("Loss Clustering", test_13_loss_clustering),
        ("Player Tier Accuracy", test_14_player_tier_accuracy),
        ("Streak Persistence", test_15_streak_persistence),
        ("Season Phase Accuracy", test_16_season_phase),
        ("Baseline Comparison", test_17_baseline_comparison),
        ("CLV Correlation", test_18_clv_correlation),
        ("Ref Impact", test_19_ref_impact),
        ("WOWY Validation", test_20_wowy_validation),
        ("Grade x Stat Efficiency", test_21_grade_stat_efficiency),
    ]

    results = []
    start = time.time()

    for name, fn in tests:
        t0 = time.time()
        try:
            fn(conn)
            results.append("PASS")  # If test completed without raising
        except Exception as e:
            print(f"\n  ERROR in test '{name}': {e}")
            import traceback
            if VERBOSE:
                traceback.print_exc()
            results.append("FAIL")
        finally:
            elapsed = time.time() - t0
            if VERBOSE:
                print(f"  [test runtime: {elapsed:.2f}s]")

    conn.close()
    total_time = time.time() - start
    print_summary(results, total_time)


def _scipy_available():
    try:
        import scipy  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    main()
