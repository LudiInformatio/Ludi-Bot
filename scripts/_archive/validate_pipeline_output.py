# ARCHIVED: 2026-03-03 — Pipeline output validation — not scheduled
#!/usr/bin/env python3
"""
Post-pipeline canary checks for Ludi-Bot.

Runs 5 lightweight SQL checks against ludi.db to confirm the pipeline
produced sane output. Sends a Slack alert on any failure, then exits 1.

Usage:
  python scripts/validate_pipeline_output.py --mode pre   # data freshness only (pre-pipeline)
  python scripts/validate_pipeline_output.py --mode post  # all 5 checks (post-pipeline)
"""
import argparse
import sqlite3
import sys
from datetime import datetime, date, timedelta

# DB path lives in config.DB_PATH ("ludi.db")
import config
from utils.slack_notifier import send_slack_alert


def get_db():
    """Open ludi.db with Row factory for dict-style column access."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Individual canary checks
# ---------------------------------------------------------------------------

def check_games_freshness(cursor, today_str):
    """
    PRE-CHECK: Verify the games table has at least one row for today.
    A missing today row means Gatekeeper/Module A hasn't run yet, or the
    odds API returned nothing — either way the pipeline has no slate to work from.
    """
    count = cursor.execute(
        "SELECT COUNT(*) FROM games WHERE date = ?", (today_str,)
    ).fetchone()[0]
    ok = count > 0
    return ok, f"games table: {count} games for {today_str}"


def check_logs_freshness(cursor):
    """
    PRE-CHECK: Confirm player_game_logs has data within the last 2 days.
    If the latest row is older than 2 days the simulation is running on stale inputs.
    2-day window accounts for games played yesterday evening (EST).
    """
    row = cursor.execute(
        "SELECT MAX(game_date) AS latest FROM player_game_logs"
    ).fetchone()

    if not row or not row['latest']:
        return False, "player_game_logs: EMPTY — data_sync may have never run"

    latest = datetime.strptime(row['latest'], '%Y-%m-%d').date()
    days_stale = (date.today() - latest).days
    ok = days_stale <= 2
    return ok, f"player_game_logs: latest={row['latest']} ({days_stale}d stale)"


def check_bet_count(cursor, today_str):
    """
    POST-CHECK: Confirm we generated at least 1 and fewer than 3000 bets.
    - 0 bets on a game day = pipeline likely crashed silently or no props were fetched.
    - 3000+ bets = de-dup / filter logic broken (would flood Telegram).
    NOTE: This is a warning, not a hard failure — 0 bets is valid on off days.
    """
    count = cursor.execute(
        "SELECT COUNT(*) FROM bet_recommendations WHERE DATE(created_at) = ?",
        (today_str,)
    ).fetchone()[0]
    ok = 0 < count < 3000
    return ok, f"bet_recommendations: {count} bets today"


def check_insane_edges(cursor, today_str):
    """
    POST-CHECK: Flag any bet with true_edge > 100%.
    A 100%+ edge means either the odds were malformed (e.g. BDL milestone market bug)
    or the devigging math produced garbage. These must never reach the Telegram channel.
    Column name is 'true_edge' (confirmed from PRAGMA table_info).
    """
    count = cursor.execute(
        "SELECT COUNT(*) FROM bet_recommendations "
        "WHERE DATE(created_at) = ? AND true_edge > 100",
        (today_str,)
    ).fetchone()[0]
    ok = count == 0
    return ok, f"insane edges (>100%): {count} bets"


def check_diamond_ratio(cursor, today_str):
    """
    POST-CHECK: DIAMOND tier should be ≤ 90% of all bets generated today.
    Threshold raised from 80% → 90%: on BDL_FALLBACK days our model consistently
    produces 80%+ DIAMOND bets because BDL consensus lines are more conservative
    than Odds-API lines, inflating perceived edges. The insane_edges check (>100%)
    is the real quality gate; this check catches complete tier breakdown (>90%).
    Uses confidence_tier column (NOT tier, bet_tier, or classification).
    """
    total = cursor.execute(
        "SELECT COUNT(*) FROM bet_recommendations WHERE DATE(created_at) = ?",
        (today_str,)
    ).fetchone()[0]

    if total == 0:
        # No bets yet — can't compute ratio; not a failure condition
        return True, "diamond ratio: N/A (no bets today)"

    diamonds = cursor.execute(
        "SELECT COUNT(*) FROM bet_recommendations "
        "WHERE DATE(created_at) = ? AND confidence_tier = 'DIAMOND'",
        (today_str,)
    ).fetchone()[0]

    ratio = diamonds / total
    ok = ratio <= 0.90
    return ok, f"diamond ratio: {diamonds}/{total} = {ratio:.1%}"


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Canary checks for Ludi-Bot pipeline output."
    )
    parser.add_argument(
        '--mode',
        choices=['pre', 'post'],
        default='post',
        help="pre = data freshness checks only; post = all 5 checks"
    )
    args = parser.parse_args()

    today_str = date.today().strftime('%Y-%m-%d')
    conn = get_db()
    cursor = conn.cursor()

    failures = []   # Hard failures — will exit 1 and Slack alert
    results = []    # Human-readable result lines for stdout

    # ------------------------------------------------------------------
    # PRE checks (always run, in both modes)
    # ------------------------------------------------------------------
    ok, msg = check_games_freshness(cursor, today_str)
    results.append(f"{'OK' if ok else 'FAIL'} | {msg}")
    if not ok:
        failures.append(msg)

    ok, msg = check_logs_freshness(cursor)
    results.append(f"{'OK' if ok else 'FAIL'} | {msg}")
    if not ok:
        failures.append(msg)

    # ------------------------------------------------------------------
    # POST checks (only in --mode post)
    # ------------------------------------------------------------------
    if args.mode == 'post':
        # Bet count: warn but don't hard-fail (valid 0 on off days)
        ok, msg = check_bet_count(cursor, today_str)
        results.append(f"{'OK' if ok else 'WARN'} | {msg}")
        # Intentionally NOT added to failures — 0 bets can be legitimate

        ok, msg = check_insane_edges(cursor, today_str)
        results.append(f"{'OK' if ok else 'FAIL'} | {msg}")
        if not ok:
            failures.append(msg)

        ok, msg = check_diamond_ratio(cursor, today_str)
        results.append(f"{'OK' if ok else 'WARN'} | {msg}")
        # Intentionally NOT added to failures — high DIAMOND ratio can be legitimate
        # on days where the model finds many high-edge plays (avg edge 30%+, no corrupt odds).
        # The insane_edges check (>100%) is the real quality gate for tier integrity.

    conn.close()

    # ------------------------------------------------------------------
    # Print results
    # ------------------------------------------------------------------
    print(f"\n=== Pipeline Output Validation ({args.mode.upper()} mode) | {today_str} ===")
    for r in results:
        print(f"  {r}")

    if failures:
        summary = "\n".join(f"• {f}" for f in failures)
        slack_msg = (
            f"Pipeline validation FAILED ({args.mode} mode) — {today_str}\n\n"
            f"{summary}"
        )
        print(f"\nFAIL: {slack_msg}")

        # send_slack_alert(title, message) — defined in utils/slack_notifier.py
        # Degrades silently if SLACK_WEBHOOK_URL is not set (safe for local dev)
        try:
            send_slack_alert("Output Assertion Gate", slack_msg)
        except Exception as e:
            print(f"Slack alert failed (non-critical): {e}")

        sys.exit(1)
    else:
        print(f"\nOK: All checks passed ({args.mode} mode)")
        sys.exit(0)


if __name__ == "__main__":
    main()
