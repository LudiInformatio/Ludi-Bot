#!/usr/bin/env python3
"""
Modifier Ablation Baseline — Sprint 3
======================================
Computes counterfactual RMSE for each modifier by analytically reversing stored
modifier values from player_projections rows (settled bets only).

LIMITATION: blowout_mod and scheme_mod are stored as 1.0 in player_projections
(projection_logger.py). Those two modifiers will show ~0% delta until the logger
is updated to capture actual Module E/F values.
Affected flags: blowout, scheme. Active flags: pace, fatigue, ref, empirical.

Usage:
    python scripts/run_modifier_ablation.py [--output-dir results/modifier_ablation/] [--min-date 2025-10-01] [--stat pts]
"""

import argparse
import json
import math
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ludi.db')

# Maps stat_category string → player_game_logs column name
# Composite stats (PRA/PR/PA/RA) are handled as expressions at query time
STAT_CAT_TO_COL = {
    'pts':  'pts',
    'reb':  'reb',
    'ast':  'ast',
    'stl':  'stl',
    'blk':  'blk',
    '3pm':  'fg3m',
    'fg3m': 'fg3m',
    'fta':  'fta',
    'oreb': 'oreb',
    'dreb': 'dreb',
    'tov':  'tov',
    'pf':   'pf',
    'min':  'minutes',
    'pra':  None,   # composite: pts+reb+ast
    'pr':   None,   # composite: pts+reb
    'pa':   None,   # composite: pts+ast
    'ra':   None,   # composite: reb+ast
}

MODIFIER_COLUMNS = {
    'pace':      'pace_mod',
    'fatigue':   'fatigue_mod',
    'ref':       'ref_mod',
    'blowout':   'blowout_mod',   # NOTE: stored as 1.0 placeholder — delta will be ~0
    'scheme':    'scheme_mod',    # NOTE: stored as 1.0 placeholder — delta will be ~0
    'empirical': 'empirical_mod',
}

def _settle_actual_results(conn, rows: list) -> list:
    """
    In-memory JOIN: attaches actual_result to each projection row by
    looking up player_game_logs on (player_id, game_date) or (player_name, game_date)
    when player_id is NULL. Returns rows with actual_result populated; unmatched dropped.
    Read-only — no DB writes.
    """
    if not rows:
        return []

    # Detect whether player_id is populated — fall back to player_name if not
    use_name_key = all(not r.get('player_id') for r in rows)

    if use_name_key:
        # player_id not populated in player_projections — join by (player_name, game_date)
        name_dates = list({(r['player_name'], r['game_date']) for r in rows if r.get('player_name')})
        if not name_dates:
            return []
        conditions = ' OR '.join('(player_name=? AND game_date=?)' for _ in name_dates)
        flat_params = [val for pair in name_dates for val in pair]
        gl_rows = conn.execute(f"""
            SELECT player_name, game_date, pts, reb, ast, stl, blk, fg3m, fta, oreb, dreb, tov, pf, minutes
            FROM player_game_logs
            WHERE {conditions}
        """, flat_params).fetchall()
        gl_lookup = {}
        for gl in gl_rows:
            gl_lookup[(str(gl[0]), str(gl[1]))] = {
                'pts': gl[2], 'reb': gl[3], 'ast': gl[4], 'stl': gl[5],
                'blk': gl[6], 'fg3m': gl[7], 'fta': gl[8], 'oreb': gl[9],
                'dreb': gl[10], 'tov': gl[11], 'pf': gl[12], 'minutes': gl[13],
            }
    else:
        # Primary path: join by (player_id, game_date)
        player_dates = list({(r['player_id'], r['game_date']) for r in rows})
        placeholders = ','.join('(?,?)' for _ in player_dates)
        flat_params = [val for pair in player_dates for val in pair]
        try:
            gl_rows = conn.execute(f"""
                SELECT player_id, game_date, pts, reb, ast, stl, blk, fg3m, fta, oreb, dreb, tov, pf, minutes
                FROM player_game_logs
                WHERE (player_id, game_date) IN ({placeholders})
            """, flat_params).fetchall()
        except sqlite3.OperationalError:
            conditions = ' OR '.join('(player_id=? AND game_date=?)' for _ in player_dates)
            gl_rows = conn.execute(f"""
                SELECT player_id, game_date, pts, reb, ast, stl, blk, fg3m, fta, oreb, dreb, tov, pf, minutes
                FROM player_game_logs
                WHERE {conditions}
            """, flat_params).fetchall()
        gl_lookup = {}
        for gl in gl_rows:
            gl_lookup[(str(gl[0]), str(gl[1]))] = {
                'pts': gl[2], 'reb': gl[3], 'ast': gl[4], 'stl': gl[5],
                'blk': gl[6], 'fg3m': gl[7], 'fta': gl[8], 'oreb': gl[9],
                'dreb': gl[10], 'tov': gl[11], 'pf': gl[12], 'minutes': gl[13],
            }

    settled = []
    for row in rows:
        if use_name_key:
            key = (str(row.get('player_name', '')), str(row['game_date']))
        else:
            key = (str(row['player_id']), str(row['game_date']))
        gl = gl_lookup.get(key)
        if not gl:
            continue  # No game log found — skip row

        stat_cat = (row.get('stat_category') or '').lower()
        col = STAT_CAT_TO_COL.get(stat_cat)

        if col is not None:
            actual = gl.get(col)
        elif stat_cat == 'pra':
            actual = (gl.get('pts') or 0) + (gl.get('reb') or 0) + (gl.get('ast') or 0)
        elif stat_cat == 'pr':
            actual = (gl.get('pts') or 0) + (gl.get('reb') or 0)
        elif stat_cat == 'pa':
            actual = (gl.get('pts') or 0) + (gl.get('ast') or 0)
        elif stat_cat == 'ra':
            actual = (gl.get('reb') or 0) + (gl.get('ast') or 0)
        else:
            continue  # Unknown stat_category — skip

        if actual is None:
            continue

        settled.append({**row, 'actual_result': float(actual)})

    return settled


def load_settled_projections(conn, min_date: str, stat_cat: str = None) -> list:
    """Load settled player projections joined to bet_recommendations outcomes."""
    # Check what columns exist in player_projections
    cursor = conn.execute("PRAGMA table_info(player_projections)")
    cols = {row[1] for row in cursor.fetchall()}

    stat_filter = ""
    params = [min_date]
    if stat_cat:
        stat_filter = "AND pp.stat_category = ?"
        params.append(stat_cat)

    # Check if player_projections has the needed columns
    required_cols = ['final_projection', 'base_projection', 'actual_result', 'stat_category', 'game_date', 'player_id']
    missing = [c for c in required_cols if c not in cols]
    if missing:
        print(f"  Warning: player_projections missing columns: {missing}. Running with available data.")
        # If actual_result is missing entirely, settle via in-memory JOIN to player_game_logs
        if 'actual_result' not in cols:
            print("  ℹ️  actual_result not in schema — settling via player_game_logs JOIN")

    # Build per-modifier COALESCE selects based on what exists
    mod_select_parts = []
    for m in MODIFIER_COLUMNS:
        col = MODIFIER_COLUMNS[m]
        if col in cols:
            mod_select_parts.append(f"COALESCE(pp.{col}, 1.0) AS {m}_mod")
        else:
            mod_select_parts.append(f"1.0 AS {m}_mod")

    # When actual_result column is missing, select NULL as placeholder and omit the IS NOT NULL filter
    actual_result_select = "pp.actual_result" if 'actual_result' in cols else "NULL AS actual_result"
    actual_result_filter = "AND pp.actual_result IS NOT NULL" if 'actual_result' in cols else ""

    query = f"""
        SELECT
            pp.player_id,
            pp.player_name,
            pp.game_date,
            pp.stat_category,
            pp.final_projection,
            pp.base_projection,
            {actual_result_select},
            {', '.join(mod_select_parts)}
        FROM player_projections pp
        WHERE pp.game_date >= ?
          {actual_result_filter}
          AND pp.final_projection IS NOT NULL
          AND pp.base_projection IS NOT NULL
          AND pp.base_projection > 0
          {stat_filter}
        ORDER BY pp.game_date DESC
    """

    try:
        rows = conn.execute(query, params).fetchall()
        mod_keys = list(MODIFIER_COLUMNS.keys())
        result = []
        for row in rows:
            entry = {
                'player_id': row[0],
                'player_name': row[1],
                'game_date': row[2],
                'stat_category': row[3],
                'final_projection': float(row[4]),
                'base_projection': float(row[5]),
                'actual_result': float(row[6]) if row[6] is not None else None,
            }
            for i, m in enumerate(mod_keys):
                entry[f'{m}_mod'] = float(row[7 + i]) if row[7 + i] is not None else 1.0
            result.append(entry)

        # If actual_result not in schema, settle via in-memory JOIN to player_game_logs
        if result and result[0].get('actual_result') is None:
            result = _settle_actual_results(conn, result)

        return result
    except sqlite3.OperationalError as e:
        print(f"  Warning: Query error: {e}. Trying simplified query.")
        # Fallback: basic query without modifier columns
        actual_result_col = "actual_result" if 'actual_result' in cols else "NULL AS actual_result"
        actual_result_filter_fb = "AND actual_result IS NOT NULL" if 'actual_result' in cols else ""
        fallback_query = f"""
            SELECT player_id, player_name, game_date, stat_category, final_projection, base_projection, {actual_result_col}
            FROM player_projections
            WHERE game_date >= ?
              {actual_result_filter_fb}
              AND final_projection IS NOT NULL
              AND base_projection IS NOT NULL
              AND base_projection > 0
        """
        fallback_params = [min_date]
        if stat_cat:
            fallback_query += " AND stat_category = ?"
            fallback_params.append(stat_cat)
        rows = conn.execute(fallback_query, fallback_params).fetchall()
        result = [{
            'player_id': row[0], 'player_name': row[1], 'game_date': row[2], 'stat_category': row[3],
            'final_projection': float(row[4]), 'base_projection': float(row[5]),
            'actual_result': float(row[6]) if row[6] is not None else None,
            'pace_mod': 1.0, 'fatigue_mod': 1.0, 'ref_mod': 1.0,
            'blowout_mod': 1.0, 'scheme_mod': 1.0, 'empirical_mod': 1.0,
        } for row in rows]

        # If actual_result not in schema, settle via in-memory JOIN to player_game_logs
        if result and result[0].get('actual_result') is None:
            result = _settle_actual_results(conn, result)

        return result


def compute_counterfactual(row: dict, disabled_mod: str) -> float:
    """
    Return what the projection would have been without the disabled modifier.
    final_projection ≈ base_projection × pace_mod × fatigue_mod × ref_mod × blowout_mod × scheme_mod × empirical_mod
    counterfactual = final_projection / mod_value (reverting that modifier to 1.0)
    """
    col_key = disabled_mod + '_mod'
    mod_value = row.get(col_key, 1.0)
    if not mod_value or mod_value == 0:
        return row['final_projection']
    return row['final_projection'] / mod_value


def rmse(errors: list) -> float:
    if not errors:
        return 0.0
    return math.sqrt(sum(e ** 2 for e in errors) / len(errors))


def naive_projection(row: dict) -> float:
    """Naive = base_projection (season average, no modifiers)."""
    return row['base_projection']


def compute_stat_rmse(rows: list, projection_fn) -> dict:
    """Compute RMSE per stat_category and overall for a given projection function."""
    by_stat = {}
    all_errors = []
    for row in rows:
        pred = projection_fn(row)
        err = pred - row['actual_result']
        all_errors.append(err)
        stat = row['stat_category']
        by_stat.setdefault(stat, [])
        by_stat[stat].append(err)

    result = {
        stat: {'n': len(errs), 'rmse': round(rmse(errs), 4)}
        for stat, errs in by_stat.items()
    }
    result['_overall'] = {'n': len(all_errors), 'rmse': round(rmse(all_errors), 4)}
    return result


def run_ablation(conn, output_dir: str, min_date: str, stat_cat: str = None, verbose: bool = False) -> None:
    os.makedirs(output_dir, exist_ok=True)

    rows = load_settled_projections(conn, min_date, stat_cat)
    print(f"  Loaded {len(rows)} settled projection rows (min_date={min_date})")

    if not rows:
        print("  Warning: No settled rows found. player_projections may not have actual_result populated yet.")
        print("    This is expected if the table was just created — run after settlement cycle.")
        # Write empty baseline files
        empty = {
            'generated_at': datetime.now().isoformat(),
            'n': 0,
            'note': 'No settled rows yet — run after pipeline settlement cycle'
        }
        for fname in ['baseline_all_flags_true.json', 'baseline_naive.json']:
            with open(os.path.join(output_dir, fname), 'w') as f:
                json.dump(empty, f, indent=2)
        return

    # Baseline: model as-is (all flags active)
    baseline_stats = compute_stat_rmse(rows, lambda r: r['final_projection'])
    baseline_output = {
        'flag': 'baseline_all_flags_true',
        'generated_at': datetime.now().isoformat(),
        'n': len(rows),
        'stats': baseline_stats,
        'note': 'Model projection with all MODIFIER_FLAGS=True'
    }
    with open(os.path.join(output_dir, 'baseline_all_flags_true.json'), 'w') as f:
        json.dump(baseline_output, f, indent=2)
    print(f"  baseline_all_flags_true — overall RMSE: {baseline_stats.get('_overall', {}).get('rmse', 'N/A')}")

    # Naive baseline: season average only (no modifiers)
    naive_stats = compute_stat_rmse(rows, naive_projection)
    naive_output = {
        'flag': 'baseline_naive',
        'generated_at': datetime.now().isoformat(),
        'n': len(rows),
        'stats': naive_stats,
        'note': 'Naive projection = base_projection (season average, no modifiers)'
    }
    with open(os.path.join(output_dir, 'baseline_naive.json'), 'w') as f:
        json.dump(naive_output, f, indent=2)
    print(f"  baseline_naive — overall RMSE: {naive_stats.get('_overall', {}).get('rmse', 'N/A')}")

    # Per-modifier ablation
    for mod_name in MODIFIER_COLUMNS:
        counterfactual_stats = compute_stat_rmse(rows, lambda r, m=mod_name: compute_counterfactual(r, m))

        # Compute lift vs baseline per stat
        stats_with_lift = {}
        for stat, data in counterfactual_stats.items():
            baseline_rmse_val = baseline_stats.get(stat, {}).get('rmse', 0)
            counterfactual_rmse_val = data['rmse']
            lift_pct = round((counterfactual_rmse_val - baseline_rmse_val) / baseline_rmse_val * 100, 2) if baseline_rmse_val else 0
            stats_with_lift[stat] = {
                'n': data['n'],
                'rmse_on': baseline_rmse_val,
                'rmse_off': counterfactual_rmse_val,
                'lift_pct': lift_pct,  # positive = modifier helps (lower RMSE when disabled = was hurting), negative = modifier helps
                'verdict': 'HELPFUL' if lift_pct < -0.5 else ('HARMFUL' if lift_pct > 0.5 else 'NEUTRAL')
            }

        is_placeholder = mod_name in ('blowout', 'scheme')
        note = ('PLACEHOLDER: blowout_mod stored as 1.0 in player_projections — delta will be ~0 '
                'until projection_logger.py is updated to capture actual Module E values.') if is_placeholder else ''

        ablation_output = {
            'flag': f'ablation_flag_{mod_name}',
            'generated_at': datetime.now().isoformat(),
            'n': len(rows),
            'is_placeholder': is_placeholder,
            'note': note,
            'stats': stats_with_lift
        }
        fname = f'ablation_flag_{mod_name}.json'
        with open(os.path.join(output_dir, fname), 'w') as f:
            json.dump(ablation_output, f, indent=2)

        overall = stats_with_lift.get('_overall', {})
        placeholder_note = ' [PLACEHOLDER — expect ~0 delta]' if is_placeholder else ''
        print(f"  {fname} — lift: {overall.get('lift_pct', 'N/A')}% ({overall.get('verdict', '?')}){placeholder_note}")

        if verbose:
            for stat, data in stats_with_lift.items():
                if stat != '_overall':
                    print(f"     {stat}: RMSE on={data['rmse_on']} off={data['rmse_off']} lift={data['lift_pct']}% ({data['verdict']})")

    print(f"\n  Ablation results written to: {output_dir}")
    print(f"  Summary: baseline RMSE={baseline_stats.get('_overall', {}).get('rmse')}, naive RMSE={naive_stats.get('_overall', {}).get('rmse')}")


def main():
    parser = argparse.ArgumentParser(description='Modifier Ablation Baseline — Sprint 3')
    parser.add_argument('--output-dir', default='results/modifier_ablation/', help='Output directory for JSON results')
    parser.add_argument('--min-date', default='2025-10-01', help='Minimum game_date for settled projections')
    parser.add_argument('--stat', default=None, help='Filter to specific stat_category (e.g., pts)')
    parser.add_argument('--verbose', action='store_true', help='Show per-stat breakdown')
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        run_ablation(conn, args.output_dir, args.min_date, args.stat, args.verbose)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
