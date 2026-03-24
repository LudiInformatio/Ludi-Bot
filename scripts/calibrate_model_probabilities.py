#!/usr/bin/env python3
"""
Probability Calibration Script — Sprint 3 Workstream 3
========================================================
Calibrates the edge-to-probability mapping using isotonic regression
(Pool Adjacent Violators algorithm — no sklearn required).

The existing linear mapping `0.5 + (edge/100 * 0.5)` is miscalibrated:
Brier Score = 0.2968 vs naive = 0.2491 (model worse than coin flip on volume stats).

This script:
1. Loads settled bet_recommendations with true_edge and outcome
2. Bins bets by edge percentile
3. Applies PAV algorithm to enforce monotone non-decreasing win rates
4. Writes calibration curve + correction table to cache/probability_calibration.json

Usage:
    python scripts/calibrate_model_probabilities.py [--verbose] [--min-date YYYY-MM-DD]
"""

import argparse
import json
import math
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache')
OUTPUT_PATH = os.path.join(CACHE_DIR, 'probability_calibration.json')

MIN_BIN_SIZE = 50  # Merge bins below this threshold


def load_calibration_data(conn, min_date: str) -> list:
    """
    Query settled bet_recommendations with curation grades.
    Returns rows with true_edge, outcome, stat_category, curation_grade, game_date.
    """
    query = """
        SELECT
            true_edge,
            outcome,
            stat_category,
            curation_grade,
            game_date
        FROM bet_recommendations
        WHERE outcome IN ('WIN', 'LOSS')
          AND curation_grade IS NOT NULL
          AND true_edge IS NOT NULL
          AND game_date >= ?
        ORDER BY true_edge ASC
    """
    rows = conn.execute(query, [min_date]).fetchall()
    return [
        {
            'true_edge': float(row[0]),
            'outcome': row[1],
            'won': 1 if row[1] == 'WIN' else 0,
            'stat_category': row[2],
            'curation_grade': row[3],
            'game_date': row[4],
        }
        for row in rows
    ]


def brier_score(bets: list, prob_fn) -> float:
    """Compute Brier score: mean((predicted_prob - outcome)^2)"""
    if not bets:
        return 0.0
    errors = [(prob_fn(b['true_edge']) - b['won']) ** 2 for b in bets]
    return round(sum(errors) / len(errors), 4)


def linear_prob(edge: float) -> float:
    """Existing linear heuristic (baseline to beat)."""
    return 0.5 + (edge / 100.0 * 0.5)


def build_bins(bets: list, n_bins: int = 10) -> list:
    """
    Bin bets by true_edge percentile. Merge bins below MIN_BIN_SIZE.
    Returns list of bin dicts: {edge_low, edge_high, observed_wr, n}.
    """
    if not bets:
        return []

    sorted_bets = sorted(bets, key=lambda b: b['true_edge'])
    bin_size = len(sorted_bets) // n_bins

    if bin_size < MIN_BIN_SIZE:
        # Reduce bin count to maintain minimum size
        n_bins = max(2, len(sorted_bets) // MIN_BIN_SIZE)
        bin_size = len(sorted_bets) // n_bins

    bins = []
    for i in range(n_bins):
        start = i * bin_size
        end = (i + 1) * bin_size if i < n_bins - 1 else len(sorted_bets)
        bin_bets = sorted_bets[start:end]

        if not bin_bets:
            continue

        wins = sum(b['won'] for b in bin_bets)
        observed_wr = wins / len(bin_bets)

        bins.append({
            'bin_id': i,
            'edge_low': bin_bets[0]['true_edge'],
            'edge_high': bin_bets[-1]['true_edge'],
            'n': len(bin_bets),
            'wins': wins,
            'observed_wr': round(observed_wr, 4),
        })

    return bins


def apply_pav(bins: list) -> list:
    """
    Pool Adjacent Violators (PAV) algorithm — enforces monotone non-decreasing
    win rates across bins without sklearn.

    If bin[i].observed_wr < bin[i-1].observed_wr, merge them and use weighted average.
    Repeat until fully monotone.
    """
    if not bins:
        return []

    # Work on a copy with weighted pools
    pools = [{'bins': [b], 'wr': b['observed_wr'], 'n': b['n'], 'wins': b['wins']} for b in bins]

    changed = True
    while changed:
        changed = False
        i = 0
        new_pools = []
        while i < len(pools):
            if i + 1 < len(pools) and pools[i]['wr'] > pools[i + 1]['wr']:
                # Violation: merge pools i and i+1
                merged_bins = pools[i]['bins'] + pools[i + 1]['bins']
                merged_n = pools[i]['n'] + pools[i + 1]['n']
                merged_wins = pools[i]['wins'] + pools[i + 1]['wins']
                merged_wr = merged_wins / merged_n
                new_pools.append({'bins': merged_bins, 'wr': merged_wr, 'n': merged_n, 'wins': merged_wins})
                i += 2
                changed = True
            else:
                new_pools.append(pools[i])
                i += 1
        pools = new_pools

    # Flatten back to bins with calibrated_prob = pool's pooled WR
    result = []
    for pool in pools:
        for b in pool['bins']:
            result.append({
                **b,
                'calibrated_prob': round(pool['wr'], 4),
            })

    # Sort by bin_id to restore original order
    result.sort(key=lambda b: b['bin_id'])
    return result


def build_correction_table(calibrated_bins: list) -> list:
    """Build lookup table mapping edge ranges to calibrated probabilities."""
    table = []
    for b in calibrated_bins:
        edge_mid = (b['edge_low'] + b['edge_high']) / 2
        raw_prob = linear_prob(edge_mid)
        calibrated = b['calibrated_prob']
        correction = round(calibrated / raw_prob, 4) if raw_prob > 0 else 1.0

        table.append({
            'edge_low': round(b['edge_low'], 2),
            'edge_high': round(b['edge_high'], 2),
            'n': b['n'],
            'raw_prob_mid': round(raw_prob, 4),
            'calibrated_prob': calibrated,
            'correction': correction,
        })
    return table


def run(verbose: bool = False, min_date: str = '2026-02-26') -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 5000")

    try:
        bets = load_calibration_data(conn, min_date)
        print(f"  Loaded {len(bets)} settled graded bets (min_date={min_date})")

        if len(bets) < 100:
            print(f"  Warning: Only {len(bets)} bets — calibration requires N>=100 for meaningful curves.")
            print("    Writing stub calibration file with fallback-to-linear flag.")
            stub = {
                'generated_at': datetime.now().isoformat(),
                'n_bets': len(bets),
                'insufficient_data': True,
                'note': f'Need N>=100 settled graded bets; found {len(bets)}',
            }
            with open(OUTPUT_PATH, 'w') as f:
                json.dump(stub, f, indent=2)
            return

        # Compute Brier score BEFORE calibration (linear heuristic)
        brier_before = brier_score(bets, linear_prob)
        naive_always_half = brier_score(bets, lambda e: 0.5)
        print(f"  Brier score (linear heuristic): {brier_before}")
        print(f"  Brier score (naive 0.5):        {naive_always_half}")

        # Build bins and apply PAV
        raw_bins = build_bins(bets, n_bins=10)
        calibrated_bins = apply_pav(raw_bins)

        if verbose:
            print("\n  Calibration curve (after PAV):")
            print(f"  {'Edge Range':>20} | {'N':>6} | {'Raw Prob':>10} | {'Cal. Prob':>10} | {'WR':>8}")
            print("  " + "-" * 65)
            for b in calibrated_bins:
                edge_mid = (b['edge_low'] + b['edge_high']) / 2
                print(f"  {b['edge_low']:>8.1f} – {b['edge_high']:>7.1f} | {b['n']:>6} | {linear_prob(edge_mid):>10.4f} | {b['calibrated_prob']:>10.4f} | {b['observed_wr']:>8.4f}")

        # Build correction table
        correction_table = build_correction_table(calibrated_bins)

        # Compute Brier score AFTER calibration
        def calibrated_prob_fn(edge):
            for entry in correction_table:
                if entry['edge_low'] <= edge < entry['edge_high']:
                    return entry['calibrated_prob']
            return linear_prob(edge)

        brier_after = brier_score(bets, calibrated_prob_fn)
        print(f"  Brier score (calibrated):       {brier_after}")
        improvement = round((brier_before - brier_after) / brier_before * 100, 1) if brier_before else 0
        verdict = 'improvement' if improvement > 0 else 'regression'
        print(f"  Improvement: {improvement}% ({verdict})")

        # Write output
        output = {
            'generated_at': datetime.now().isoformat(),
            'n_bets': len(bets),
            'min_date': min_date,
            'brier_before': brier_before,
            'brier_after': brier_after,
            'brier_naive_half': naive_always_half,
            'improvement_pct': improvement,
            'n_bins': len(calibrated_bins),
            'calibration_curve': [
                {
                    'bin_id': b['bin_id'],
                    'edge_low': round(b['edge_low'], 2),
                    'edge_high': round(b['edge_high'], 2),
                    'n': b['n'],
                    'observed_wr': b['observed_wr'],
                    'calibrated_prob': b['calibrated_prob'],
                }
                for b in calibrated_bins
            ],
            'correction_table': correction_table,
        }

        with open(OUTPUT_PATH, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"  Written to: {OUTPUT_PATH}")
        print(f"  Summary: {len(calibrated_bins)} calibration bins | N={len(bets)} bets")

    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Probability Calibration — Sprint 3')
    parser.add_argument('--verbose', action='store_true', help='Show calibration curve table')
    parser.add_argument('--min-date', default='2026-02-26', help='Min game_date for settled bets')
    args = parser.parse_args()

    run(verbose=args.verbose, min_date=args.min_date)


if __name__ == '__main__':
    main()
