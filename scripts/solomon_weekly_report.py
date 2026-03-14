#!/usr/bin/env python3
"""
Solomon's Weekly Report — Deterministic Model Health + Shipping Log
====================================================================
Queries settled bets from the last 7 days, computes per-grade calibration
metrics (Wilson CI lower bound), reads git log + ROADMAP.md next actions,
and sends a structured report to Discord #weekly-roundtable and Slack
#ludi-bot-notes.

NO LLM calls. $0 cost. All metrics are deterministic.

Usage:
    python scripts/solomon_weekly_report.py           # send to Discord + Slack
    python scripts/solomon_weekly_report.py --dry-run  # print to stdout only
    python scripts/solomon_weekly_report.py --verbose  # extra output

Created: 2026-03-14 | Phase 8
"""

import argparse
import math
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# ─── Path Setup ───────────────────────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

DB_PATH = os.path.join(_PROJECT_ROOT, 'ludi.db')
REPORTS_DIR = os.path.join(_PROJECT_ROOT, 'reports')
ROADMAP_PATH = os.path.join(_PROJECT_ROOT, 'ROADMAP.md')

GRADE_ORDER = ['STRONG', 'LEAN', 'FADE']


# ─── Wilson Score Interval (95% CI lower bound) ───────────────────────────────
def wilson_lower(wins: int, n: int, z: float = 1.96) -> float:
    """
    Compute the lower bound of the Wilson score 95% confidence interval.
    Returns 0.0 if n == 0.
    """
    if n == 0:
        return 0.0
    p = wins / n
    z2 = z * z
    numerator = p + z2 / (2 * n) - z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    denominator = 1 + z2 / n
    return max(0.0, numerator / denominator)


# ─── DB Query ─────────────────────────────────────────────────────────────────
def fetch_settled_bets(conn: sqlite3.Connection, week_start: str, week_end: str) -> list[dict]:
    """Query settled bets with a curation_grade from the last 7 days."""
    cursor = conn.execute("""
        SELECT player_name, stat_category, bet_side, true_edge, outcome, curation_grade
        FROM bet_recommendations
        WHERE game_date >= ?
          AND game_date <= ?
          AND outcome IN ('WIN', 'LOSS')
          AND curation_grade IS NOT NULL
        ORDER BY game_date DESC
    """, (week_start, week_end))
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


# ─── Grade Metrics ────────────────────────────────────────────────────────────
def compute_grade_metrics(bets: list[dict]) -> list[dict]:
    """
    Group bets by curation_grade, compute wins/n/raw_wr/wilson_lower.
    Returns list of dicts in GRADE_ORDER.
    """
    grade_groups: dict[str, list] = {}
    for bet in bets:
        grade = bet.get('curation_grade') or 'UNKNOWN'
        grade_groups.setdefault(grade, []).append(bet)

    results = []
    for grade in GRADE_ORDER:
        gbets = grade_groups.get(grade, [])
        n = len(gbets)
        wins = sum(1 for b in gbets if b['outcome'] == 'WIN')
        raw_wr = wins / n if n > 0 else 0.0
        wl = wilson_lower(wins, n)
        # Grade inversion: FADE winning > STRONG signals the hierarchy is backwards
        inverted = grade == 'FADE' and n > 0 and raw_wr > 0.55
        results.append({
            'grade': grade,
            'n': n,
            'wins': wins,
            'raw_wr': raw_wr,
            'wilson_lower': wl,
            'inverted': inverted,
        })
    return results


# ─── Grade Table ──────────────────────────────────────────────────────────────
def build_grade_table(grade_results: list[dict]) -> tuple[str, bool]:
    """
    Build a Markdown table from per-grade metrics.
    Returns (table_string, any_inverted).
    """
    header = "| Grade  | W  | N  | WR%  | Lower CI | Flag |"
    sep    = "|--------|----|----|------|----------|------|"
    rows = [header, sep]
    any_inverted = False

    for g in grade_results:
        if g['n'] == 0:
            rows.append(f"| {g['grade']:<6} | —  | —  | —    | —        |      |")
        else:
            flag = "!" if g['inverted'] else ""
            if g['inverted']:
                any_inverted = True
            rows.append(
                f"| {g['grade']:<6} | {g['wins']:<2} | {g['n']:<2} "
                f"| {g['raw_wr']*100:.1f} "
                f"| {g['wilson_lower']*100:.1f}%    | {flag:<4} |"
            )
    return "\n".join(rows), any_inverted


# ─── Git Log ──────────────────────────────────────────────────────────────────
def get_git_log() -> str:
    """Return one-line git log for the last 7 days."""
    try:
        result = subprocess.run(
            ['git', '-C', _PROJECT_ROOT, 'log', '--oneline', '--since=7 days ago'],
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout.strip()
        return output if output else '(no commits this week)'
    except Exception as e:
        print(f"[ERROR] git log failed: {e}")
        return '(git log unavailable)'


# ─── ROADMAP Next Actions ─────────────────────────────────────────────────────
def get_next_actions() -> str:
    """
    Read ROADMAP.md and extract the **Next Actions:** block (lines starting with '- [ ]').
    Returns a formatted string of pending items.
    """
    try:
        with open(ROADMAP_PATH, 'r') as f:
            lines = f.readlines()

        in_next_actions = False
        items = []
        for line in lines:
            stripped = line.strip()
            if '**Next Actions:**' in stripped:
                in_next_actions = True
                continue
            if in_next_actions:
                # Stop at the next heading or blank line followed by a heading
                if stripped.startswith('##') or stripped.startswith('---'):
                    break
                if stripped.startswith('- [ ]'):
                    # Strip the '- [ ] ' prefix for a clean display
                    items.append(stripped[6:])
        if items:
            return '\n'.join(f'- [ ] {item}' for item in items[:5])  # cap at 5
        return '(no pending items found in ROADMAP.md)'
    except Exception as e:
        print(f"[ERROR] ROADMAP.md read failed: {e}")
        return '(ROADMAP.md unavailable)'


# ─── Report Builder ───────────────────────────────────────────────────────────
def build_report(
    week_start: str,
    week_end: str,
    bets: list[dict],
    grade_results: list[dict],
    git_log: str,
    next_actions: str,
) -> str:
    """Assemble the full weekly report in Solomon's voice."""
    today = datetime.now().strftime('%Y-%m-%d')
    grade_table, any_inverted = build_grade_table(grade_results)

    total_n = sum(g['n'] for g in grade_results)
    total_wins = sum(g['wins'] for g in grade_results)
    overall_wr = (total_wins / total_n * 100) if total_n > 0 else 0.0

    if total_n == 0:
        model_health_note = "No settled bets this week — calibration pool empty."
    else:
        model_health_note = f"Overall: {total_wins}W / {total_n} settled ({overall_wr:.1f}% WR)"

    inversion_flag = ""
    if any_inverted:
        inversion_flag = "\n**! GRADE INVERSION DETECTED: FADE WR > 55%. Review Maren prompt grading.**"

    report = f"""## Solomon's Weekly Report — Week of {week_start}

### THE WINS
```
{git_log}
```

### MODEL HEALTH
{model_health_note}
{grade_table}{inversion_flag}

> ! = FADE WR > 55% (grade hierarchy may be inverted)

### CODE HEALTH
(Henrik digest — populate manually from session notes or `/session-debrief`)

### NEXT WEEK
{next_actions}

---
*Generated: {today} | ludi.db settled bets {week_start} → {week_end} | $0 cost*"""

    return report


# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Solomon's Weekly Report — deterministic model health")
    parser.add_argument('--week-start', type=str, default=None,
                        help='Start date (YYYY-MM-DD). Defaults to 7 days ago.')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print report to stdout; do NOT send to Discord or Slack.')
    parser.add_argument('--verbose', action='store_true',
                        help='Extra output during run.')
    args = parser.parse_args()

    # ── Date range ────────────────────────────────────────────────────────────
    if args.week_start:
        week_start = args.week_start
    else:
        week_start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    week_end = datetime.now().strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')

    print("=" * 60)
    print("SOLOMON WEEKLY REPORT")
    print(f"Period: {week_start} -> {week_end}")
    print("=" * 60)

    if args.dry_run:
        print("DRY RUN -- Discord/Slack will NOT be sent\n")

    # ── DB connect ────────────────────────────────────────────────────────────
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=30000")

    # ── Fetch settled bets ────────────────────────────────────────────────────
    try:
        bets = fetch_settled_bets(conn, week_start, week_end)
    except Exception as e:
        print(f"[ERROR] Failed to query bet_recommendations: {e}")
        conn.close()
        sys.exit(1)
    finally:
        conn.close()

    if args.verbose:
        print(f"Settled bets found: {len(bets)}")

    if not bets:
        print("No settled bets this week. Generating empty-pool report.")

    # ── Compute grade metrics ─────────────────────────────────────────────────
    grade_results = compute_grade_metrics(bets)

    # ── Git log ───────────────────────────────────────────────────────────────
    git_log = get_git_log()
    if args.verbose:
        print(f"Git log lines: {len(git_log.splitlines())}")

    # ── ROADMAP next actions ──────────────────────────────────────────────────
    next_actions = get_next_actions()

    # ── Build report ──────────────────────────────────────────────────────────
    report = build_report(week_start, week_end, bets, grade_results, git_log, next_actions)

    if args.dry_run or args.verbose:
        print("\n" + "=" * 60)
        print(report)
        print("=" * 60 + "\n")

    if args.dry_run:
        print("Dry run complete. Report NOT sent.")
        sys.exit(0)

    # ── Send ──────────────────────────────────────────────────────────────────
    send_ok = True

    try:
        from utils.discord_notifier import send_to_weekly
        discord_ok = send_to_weekly(report)
        if not discord_ok:
            print("[ERROR] Discord send failed (send_to_weekly returned False)")
            send_ok = False
        else:
            print("[OK] Discord #weekly-roundtable sent")
    except Exception as e:
        print(f"[ERROR] Discord send raised exception: {e}")
        send_ok = False

    try:
        from utils.slack_notifier import send_slack_message
        slack_ok = send_slack_message(report)
        if not slack_ok:
            print("[ERROR] Slack send failed (send_slack_message returned False)")
            send_ok = False
        else:
            print("[OK] Slack #ludi-bot-notes sent")
    except Exception as e:
        print(f"[ERROR] Slack send raised exception: {e}")
        send_ok = False

    # ── Save to reports/ ──────────────────────────────────────────────────────
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        report_path = os.path.join(REPORTS_DIR, f"weekly_summary_{today}.md")
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"[OK] Report saved to {report_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save report file: {e}")
        # File save failure is non-fatal; only send failures trigger exit(1)

    if not send_ok:
        sys.exit(1)


if __name__ == '__main__':
    main()
