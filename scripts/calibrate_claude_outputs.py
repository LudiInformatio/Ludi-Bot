"""
LUDI INFORMATIO | PHASE 8.23: CLAUDE CURATION CALIBRATION
==========================================================
Measures whether the curation system's bet selections produce positive expected value.

Queries curated settled bets from bet_recommendations, computes Wilson score intervals,
Brier Score, and per-group win rates to assess model calibration.

Usage:
  python scripts/calibrate_claude_outputs.py           # uses ludi.db in project root
  python scripts/calibrate_claude_outputs.py --verbose # extra detail

Output:
  - Formatted table to stdout
  - cache/claude_calibration.json with full results

Created: 2026-03-09 | Phase 8.23
"""

import json
import math
import os
import sqlite3
import sys
from datetime import datetime

# ─── Path Setup ───────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

DB_PATH = os.path.join(_PROJECT_ROOT, 'ludi.db')
CACHE_DIR = os.path.join(_PROJECT_ROOT, 'cache')

# ─── Wilson Score Interval (95% CI lower bound) ───────────────────────────────
def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    """
    Compute the lower bound of the Wilson score 95% confidence interval.
    Formula: (p + z²/2n - z*sqrt(p*(1-p)/n + z²/(4n²))) / (1 + z²/n)
    Returns 0.0 if n == 0.
    """
    if n == 0:
        return 0.0
    p = wins / n
    z2 = z * z
    numerator = p + z2 / (2 * n) - z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    denominator = 1 + z2 / n
    return max(0.0, numerator / denominator)


# ─── Brier Score ──────────────────────────────────────────────────────────────
def compute_brier_score(bets: list[dict]) -> float:
    """
    Brier Score = mean((predicted_prob - actual_outcome)^2)
    predicted_prob: linear map from true_edge to probability
      0% edge → 0.50, 25% edge → 0.625 (clamped to [0.50, 0.75])
    actual_outcome: 1 if WIN, 0 if LOSS
    Lower is better. Naive 50/50 predictor scores ~0.25.
    """
    if not bets:
        return 0.0
    total = 0.0
    for bet in bets:
        edge = bet.get('true_edge') or 0.0
        # Linear mapping: predicted_prob = 0.5 + (edge/100 * 0.5)
        predicted_prob = 0.5 + (edge / 100.0 * 0.5)
        # Clamp to [0.50, 0.75] to avoid distortion from outlier edges
        predicted_prob = max(0.50, min(0.75, predicted_prob))
        actual = 1.0 if bet['outcome'] == 'WIN' else 0.0
        total += (predicted_prob - actual) ** 2
    return total / len(bets)


# ─── Group Status ─────────────────────────────────────────────────────────────
def group_status(n: int, wl: float) -> str:
    """Determine calibration status for a group based on N and Wilson lower bound."""
    if n < 10:
        return "NEEDS_MORE_DATA"
    if wl >= 0.52:
        return "CALIBRATED"
    if wl >= 0.45:
        return "NEEDS_MORE_DATA"
    return "MISCALIBRATED"


def overall_status(n: int, wl: float) -> str:
    """Determine overall calibration status."""
    if n < 50:
        return "NEEDS_MORE_DATA"
    if wl >= 0.52:
        return "CALIBRATED"
    if wl >= 0.45:
        return "NEEDS_MORE_DATA"
    return "MISCALIBRATED"


# ─── Main ─────────────────────────────────────────────────────────────────────
def run(verbose: bool = False) -> None:
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # ── Query all curated settled bets ────────────────────────────────────────
    cursor = conn.execute("""
        SELECT stat_category, bet_side, outcome, true_edge, game_date,
               curation_grade
        FROM bet_recommendations
        WHERE curation_grade IS NOT NULL
          AND game_date >= '2026-02-26'
          AND outcome IN ('WIN', 'LOSS')
        ORDER BY game_date
    """)
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("No settled curated bets found. Nothing to calibrate.")
        sys.exit(0)

    all_bets = [dict(r) for r in rows]
    total_n = len(all_bets)
    total_wins = sum(1 for b in all_bets if b['outcome'] == 'WIN')
    overall_wr = total_wins / total_n
    overall_wl = wilson_lower(total_wins, total_n)
    brier = compute_brier_score(all_bets)
    o_status = overall_status(total_n, overall_wl)

    # ── Per-group breakdown ───────────────────────────────────────────────────
    # Build groups: (stat_category, bet_side)
    groups: dict[tuple, list] = {}
    for bet in all_bets:
        key = (bet['stat_category'], bet['bet_side'])
        groups.setdefault(key, []).append(bet)

    group_results = []
    for (stat, side), gbets in sorted(groups.items()):
        n = len(gbets)
        wins = sum(1 for b in gbets if b['outcome'] == 'WIN')
        raw_wr = wins / n
        wl = wilson_lower(wins, n)
        avg_edge = sum(b.get('true_edge') or 0.0 for b in gbets) / n
        status = group_status(n, wl)
        group_results.append({
            'stat_category': stat,
            'bet_side': side,
            'n': n,
            'wins': wins,
            'raw_wr': raw_wr,
            'wilson_lower': wl,
            'avg_edge': avg_edge,
            'status': status,
        })

    # Filter to N >= 5 for display
    display_groups = [g for g in group_results if g['n'] >= 5]
    display_groups.sort(key=lambda g: g['n'], reverse=True)

    # ── Per-grade breakdown ───────────────────────────────────────────────────
    # Groups: STRONG / LEAN / FADE — grouped from the same all_bets list
    grade_groups: dict[str, list] = {}
    for bet in all_bets:
        grade = bet.get('curation_grade') or 'UNKNOWN'
        grade_groups.setdefault(grade, []).append(bet)

    grade_results = []
    GRADE_ORDER = ['STRONG', 'LEAN', 'FADE']
    for grade in GRADE_ORDER:
        gbets = grade_groups.get(grade, [])
        n = len(gbets)
        wins = sum(1 for b in gbets if b['outcome'] == 'WIN')
        raw_wr = wins / n if n > 0 else 0.0
        wl = wilson_lower(wins, n)
        avg_edge = sum(b.get('true_edge') or 0.0 for b in gbets) / n if n > 0 else 0.0
        brier_grade = compute_brier_score(gbets)
        status = group_status(n, wl)
        # Inversion flag: FADE winning > 55% means grade hierarchy is backwards
        inverted = grade == 'FADE' and n > 0 and raw_wr > 0.55
        grade_results.append({
            'grade': grade,
            'n': n,
            'wins': wins,
            'raw_wr': raw_wr,
            'wilson_lower': wl,
            'avg_edge': avg_edge,
            'brier_score': brier_grade,
            'status': status,
            'inverted': inverted,
        })

    # ── Stdout output ─────────────────────────────────────────────────────────
    date_range_start = min(b['game_date'] for b in all_bets)
    date_range_end = max(b['game_date'] for b in all_bets)

    print(f"\n{'='*65}")
    print(f"  Ludi Curation Calibration Report — {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{'='*65}")
    print(f"  Date range : {date_range_start} → {date_range_end}")
    print(f"  Total bets : {total_n}  |  Wins: {total_wins}  |  Raw WR: {overall_wr:.1%}")
    print(f"  Wilson 95% lower bound : {overall_wl:.1%}")
    print(f"  Brier Score : {brier:.4f}  (naive baseline ~0.2500)")
    print(f"  Overall status : {o_status}")
    if total_n < 50:
        print(f"  NOTE: N={total_n} is below the N=50 significance threshold.")
    print(f"{'='*65}\n")

    if display_groups:
        header = f"  {'stat':<10} {'side':<8} {'N':>4}  {'wins':>4}  {'raw WR':>7}  {'wilson lower':>13}  {'avg edge':>9}  status"
        sep = "  " + "-" * (len(header) - 2)
        print(header)
        print(sep)
        for g in display_groups:
            sig_flag = " *" if g['n'] >= 50 else ("  " if g['n'] >= 10 else "  ")
            print(
                f"  {g['stat_category']:<10} {g['bet_side']:<8} {g['n']:>4}  "
                f"{g['wins']:>4}  {g['raw_wr']:>6.1%}  {g['wilson_lower']:>12.1%}  "
                f"{g['avg_edge']:>8.2f}%  {g['status']}{sig_flag}"
            )
        print(f"\n  * = N >= 50 (statistically significant)")
        print(f"  Groups with N < 5 omitted.\n")
    else:
        print("  No groups with N >= 5 found.\n")

    # ── Per-grade section ─────────────────────────────────────────────────────
    print(f"  {'─'*63}")
    print(f"  Per-grade breakdown (STRONG / LEAN / FADE)")
    print(f"  {'─'*63}")
    grade_header = f"  {'grade':<10} {'N':>4}  {'wins':>4}  {'raw WR':>7}  {'wilson lower':>13}  {'avg edge':>9}  {'brier':>7}  status"
    grade_sep = "  " + "-" * (len(grade_header) - 2)
    print(grade_header)
    print(grade_sep)
    for g in grade_results:
        if g['n'] == 0:
            print(f"  {g['grade']:<10} {'—':>4}  {'—':>4}  {'—':>7}  {'—':>13}  {'—':>9}  {'—':>7}  NO DATA")
        else:
            inv_flag = " !" if g['inverted'] else "  "
            print(
                f"  {g['grade']:<10} {g['n']:>4}  "
                f"{g['wins']:>4}  {g['raw_wr']:>6.1%}  {g['wilson_lower']:>12.1%}  "
                f"{g['avg_edge']:>8.2f}%  {g['brier_score']:>6.4f}  {g['status']}{inv_flag}"
            )
    print(f"\n  ! = FADE WR > 55% (grade hierarchy may be inverted)")
    print(f"{'='*65}\n")

    # ── Write cache/claude_calibration.json ───────────────────────────────────
    os.makedirs(CACHE_DIR, exist_ok=True)
    output = {
        'generated_at': datetime.now().isoformat(),
        'date_range': {'from': date_range_start, 'to': date_range_end},
        'overall': {
            'n': total_n,
            'wins': total_wins,
            'raw_wr': round(overall_wr, 4),
            'wilson_lower': round(overall_wl, 4),
            'brier_score': round(brier, 4),
            'status': o_status,
        },
        'by_group': [
            {
                'stat_category': g['stat_category'],
                'bet_side': g['bet_side'],
                'n': g['n'],
                'wins': g['wins'],
                'raw_wr': round(g['raw_wr'], 4),
                'wilson_lower': round(g['wilson_lower'], 4),
                'avg_edge': round(g['avg_edge'], 2),
                'status': g['status'],
            }
            for g in group_results  # include all groups in JSON (N < 5 too, labeled)
        ],
        'by_grade': [
            {
                'grade': g['grade'],
                'n': g['n'],
                'wins': g['wins'],
                'raw_wr': round(g['raw_wr'], 4),
                'wilson_lower': round(g['wilson_lower'], 4),
                'avg_edge': round(g['avg_edge'], 2),
                'brier_score': round(g['brier_score'], 4),
                'status': g['status'],
            }
            for g in grade_results
        ],
        'notes': [
            "Per-grade breakdown groups by curation_grade (STRONG/LEAN/FADE) using the same Wilson CI logic as by_group.",
            "Groups with N < 5 shown in JSON but omitted from stdout table.",
            f"Wilson confidence interval uses z=1.96 (95% CI).",
            f"Brier predicted_prob = 0.5 + (true_edge/100 * 0.5), clamped to [0.50, 0.75].",
        ],
    }
    cache_path = os.path.join(CACHE_DIR, 'claude_calibration.json')
    with open(cache_path, 'w') as f:
        json.dump(output, f, indent=2)

    if verbose:
        print(f"  [JSON] Written to {cache_path}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Ludi Claude curation calibration report')
    parser.add_argument('--verbose', action='store_true', help='Extra output')
    args = parser.parse_args()
    run(verbose=args.verbose)
