#!/usr/bin/env python3
"""
LUDI INFORMATIO | SETTLEMENT SUMMARY
====================================
Send last night's bet settlement P&L to Telegram.
Runs at 3 AM EST as part of data_sync workflow.
"""
import sys
import os
import sqlite3
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.telegram_notifier import send_solomon_message
from utils.time_utils import get_est_yesterday


def _calc_stats(row):
    """Shared helper: unpack a query row into a stats dict."""
    total, wins, losses, pushes, net_units, units_risked = row
    decided = wins + losses
    win_rate = (wins / decided * 100) if decided > 0 else 0
    # True ROI = net profit / total units risked (not per-bet average)
    roi = (net_units / units_risked * 100) if units_risked and units_risked > 0 else 0
    return {
        'total': total,
        'wins': wins,
        'losses': losses,
        'pushes': pushes or 0,
        'net_units': net_units or 0,
        'units_risked': round(units_risked or 0, 2),
        'win_rate': win_rate,
        'roi': roi,
    }


def get_settlement_summary():
    """Query yesterday's settled bets and season-to-date totals."""
    conn = sqlite3.connect('ludi.db')
    c = conn.cursor()

    yesterday = get_est_yesterday()

    # Shared SELECT columns for both daily and overall queries.
    # units_risked excludes PUSH and 0-unit bets — correct ROI denominator.
    _cols = '''
        COUNT(*) as total,
        SUM(CASE WHEN outcome = 'WIN'  THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN outcome = 'PUSH' THEN 1 ELSE 0 END) as pushes,
        SUM(COALESCE(profit_loss, 0))  as net_units,
        SUM(CASE WHEN outcome IN ('WIN','LOSS') AND units > 0 THEN units ELSE 0 END) as units_risked
    '''

    # --- Daily: games played yesterday (game_date, not settled_at).
    # Using game_date is the correct semantic: "how did yesterday's slate perform?"
    # settled_at gets overwritten on re-settlement, making it unreliable as a day marker.
    c.execute(f'SELECT {_cols} FROM bet_recommendations WHERE game_date = ? AND outcome IS NOT NULL', (yesterday,))
    daily_row = c.fetchone()

    # --- L10D: last 10 game dates with settled bets (rolling window, not calendar days) ---
    c.execute('''
        SELECT DISTINCT game_date FROM bet_recommendations
        WHERE outcome IN ('WIN','LOSS','PUSH') AND units > 0
        ORDER BY game_date DESC LIMIT 10
    ''')
    l10_dates = [r[0] for r in c.fetchall()]
    if l10_dates:
        placeholders = ','.join('?' * len(l10_dates))
        c.execute(f'SELECT {_cols} FROM bet_recommendations WHERE game_date IN ({placeholders}) AND outcome IN (\'WIN\',\'LOSS\',\'PUSH\') AND units > 0', l10_dates)
        l10_row = c.fetchone()
    else:
        l10_row = None

    # --- Overall: all settled bets with real outcomes (units > 0 guards legacy 0-unit rows) ---
    c.execute(f'SELECT {_cols} FROM bet_recommendations WHERE outcome IN (\'WIN\',\'LOSS\',\'PUSH\') AND units > 0')
    overall_row = c.fetchone()

    conn.close()

    if not daily_row or daily_row[0] == 0:
        return None

    daily = _calc_stats(daily_row)

    # All bets voided (DNP/no game) — nothing meaningful to report
    if daily['wins'] + daily['losses'] == 0:
        print(f"ℹ️  All {daily['total']} bets from yesterday were voided — skipping Telegram")
        return None

    if abs(daily['net_units']) > 50:
        anomaly_msg = f"⚠️ P&L ANOMALY: {daily['net_units']:.1f}u exceeds ±50u threshold — verify before trusting"
        print(anomaly_msg)
        from utils.slack_notifier import send_slack_alert
        send_slack_alert("P&L Anomaly Detected", anomaly_msg)

    l10 = _calc_stats(l10_row) if l10_row and l10_row[0] else None
    overall = _calc_stats(overall_row) if overall_row and overall_row[0] else None

    return {
        'date': yesterday,
        'daily': daily,
        'l10': l10,
        'overall': overall,
    }


def _fmt_section(stats):
    """Format one stats block: record, units, ROI on two lines."""
    emoji = "🟢" if stats['net_units'] >= 0 else "🔴"
    return (
        f"{emoji} {stats['wins']}-{stats['losses']} ({stats['win_rate']:.1f}%)\n"
        f"💰 {stats['net_units']:+.2f}u on {stats['units_risked']:.1f}u risked  |  ROI: {stats['roi']:+.1f}%"
    )


def _line_movement_summary(conn, game_date):
    """
    B3 consumer: Query prop_line_snapshots for line movement delta.
    
    Finds bets where |closing_line - opening_line| >= 0.5 OR 
    |closing_odds - opening_odds| >= 10.
    
    Returns formatted string block or empty string if no significant movement.
    """
    c = conn.cursor()
    c.execute('''
        SELECT 
            player_name,
            stat_category,
            opening_line,
            closing_line,
            opening_odds_over,
            closing_odds_over,
            team,
            opponent
        FROM prop_line_snapshots
        WHERE game_date = ?
          AND closing_line IS NOT NULL
          AND opening_line IS NOT NULL
          AND (
              ABS(closing_line - opening_line) >= 0.5
              OR ABS(COALESCE(closing_odds_over, 0) - COALESCE(opening_odds_over, 0)) >= 10
          )
        ORDER BY ABS(COALESCE(closing_line, 0) - opening_line) DESC
        LIMIT 10
    ''', (game_date,))
    
    rows = c.fetchall()
    if not rows:
        return ""
    
    lines = ["", "📈 **LINE MOVEMENT**", ""]
    for r in rows:
        player, stat, open_line, close_line, open_odds, close_odds, team, opp = r
        line_move = close_line - open_line
        odds_move = (close_odds or 0) - (open_odds or 0)
        arrow = "📈" if line_move > 0 else "📉"
        # Guard against NULL odds (opening_odds_over / closing_odds_over are nullable)
        o_fmt = f"{open_odds:+d}" if open_odds is not None else "—"
        c_fmt = f"{close_odds:+d}" if close_odds is not None else "—"
        lines.append(
            f"{arrow} {player} {stat}: {open_line:.1f} → {close_line:.1f} "
            f"({line_move:+.1f}) | {o_fmt} → {c_fmt} ({odds_move:+d})"
        )
    
    return "\n".join(lines)


def main():
    """Generate and send settlement summary."""
    print("=" * 50)
    print("LUDI SETTLEMENT SUMMARY")
    print("=" * 50)

    summary = get_settlement_summary()

    if not summary:
        print("No settled bets from yesterday - skipping Telegram")
        return

    d = summary['daily']
    l10 = summary['l10']
    ov = summary['overall']

    lines = [f"📊 **SETTLEMENT | {summary['date']}** `[BETA]`", ""]

    lines += ["📅 **YESTERDAY**", _fmt_section(d), ""]

    if l10:
        lines += ["📉 **LAST 10 DAYS**", _fmt_section(l10), ""]

    if ov:
        lines += ["🏦 **SINCE LAUNCH (Jan 7)**", _fmt_section(ov)]

    # B3: Line movement summary from prop_line_snapshots
    conn = sqlite3.connect('ludi.db')
    movement_block = _line_movement_summary(conn, summary['date'])
    conn.close()
    if movement_block:
        lines.append(movement_block)

    msg = "\n".join(lines)

    # Send via Solomon Bot 2 (PM/ops channel)
    success = send_solomon_message(msg)

    if success:
        print(f"✅ Sent: {d['wins']}-{d['losses']} ({d['net_units']:+.2f}u) | L10: {l10['net_units']:+.2f}u | Overall: {ov['net_units']:+.2f}u")
    else:
        print("❌ Failed to send settlement summary")


if __name__ == "__main__":
    main()
