#!/usr/bin/env python3
"""
Send workflow summary to Slack ops channel.
Used by GitHub Actions to report pipeline results.
"""
import argparse
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

from utils.slack_notifier import send_slack_message


def main():
    parser = argparse.ArgumentParser(description='Send workflow summary to Telegram')
    parser.add_argument('--games', type=int, default=0, help='Number of games processed')
    parser.add_argument('--bets', type=int, default=0, help='Number of bets generated')
    parser.add_argument('--errors', type=int, default=0, help='Number of errors')
    parser.add_argument('--workflow', type=str, default='Production Pipeline', help='Workflow name')
    
    args = parser.parse_args()
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    time_str = datetime.now().strftime('%H:%M:%S')
    
    # Build simple summary message
    msg = f"PIPELINE SUMMARY {date_str}\n"
    msg += f"Games: {args.games}\n"
    msg += f"Bets: {args.bets}\n"
    msg += f"Errors: {args.errors}\n"
    msg += f"Time: {time_str}"
    
    try:
        send_slack_message(msg)
        print(f"✅ Summary sent to Slack: {args.games} games, {args.bets} bets, {args.errors} errors")
    except Exception as e:
        print(f"⚠️ Could not send summary: {e}")
        # Don't fail the workflow for notification issues
        return 0
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
