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

from utils.telegram_notifier import send_message
from utils.time_utils import get_est_yesterday


def get_settlement_summary():
    """Query yesterday's settled bets from database."""
    conn = sqlite3.connect('ludi.db')
    c = conn.cursor()

    # Get yesterday's date (EST)
    yesterday = get_est_yesterday()

    # Query settled bets from yesterday
    # Column names: outcome (WIN/LOSS/PUSH), profit_loss (units won/lost)
    c.execute('''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
            SUM(CASE WHEN outcome = 'PUSH' THEN 1 ELSE 0 END) as pushes,
            SUM(COALESCE(profit_loss, 0)) as net_units
        FROM bet_recommendations
        WHERE DATE(settled_at) = ? AND outcome IS NOT NULL
    ''', (yesterday,))

    row = c.fetchone()
    conn.close()

    if not row or row[0] == 0:
        return None

    total, wins, losses, pushes, net_units = row

    if abs(net_units) > 50:
        anomaly_msg = f"⚠️ P&L ANOMALY: {net_units:.1f}u exceeds ±50u threshold — verify before trusting"
        print(anomaly_msg)
        from utils.slack_notifier import send_slack_alert
        send_slack_alert("P&L Anomaly Detected", anomaly_msg)

    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    roi = (net_units / total * 100) if total > 0 else 0

    return {
        'date': yesterday,
        'total': total,
        'wins': wins,
        'losses': losses,
        'pushes': pushes or 0,
        'win_rate': win_rate,
        'net_units': net_units or 0,
        'roi': roi
    }


def main():
    """Generate and send settlement summary."""
    print("=" * 50)
    print("LUDI SETTLEMENT SUMMARY")
    print("=" * 50)

    summary = get_settlement_summary()

    if not summary:
        print("No settled bets from yesterday - skipping Telegram")
        return

    # Determine emoji based on P&L
    if summary['net_units'] >= 0:
        emoji = "🟢"
        vibe = "Let's build on it."
    else:
        emoji = "🔴"
        vibe = "Recalibrating."

    # Format message
    msg = f"""📊 **SETTLEMENT REPORT | {summary['date']}**
────────────────────────
{emoji} **{summary['wins']}-{summary['losses']}** ({summary['win_rate']:.1f}%)
💰 **{summary['net_units']:+.2f}u** ({summary['roi']:+.1f}% ROI)
────────────────────────
_{vibe} Bets graded: {summary['total']}_"""

    # Send to Telegram
    success = send_message(msg)

    if success:
        print(f"✅ Settlement summary sent: {summary['wins']}-{summary['losses']} ({summary['net_units']:+.2f}u)")
    else:
        print("❌ Failed to send settlement summary")


if __name__ == "__main__":
    main()
