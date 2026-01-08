#!/usr/bin/env python
"""
LUDI INFORMATIO | WEEK 2 CHECKLIST TELEGRAM NOTIFIER
======================================================
Send Week 2 development checklist to Telegram

Created: January 7, 2026, 7:30 PM ET
Purpose: Notify user of Week 2 deliverables and success criteria
"""

from utils.telegram_notifier import send_message


# Week 2 checklist message (formatted with Telegram markdown)
message = """🎯 *WEEK 2 DEVELOPMENT PLAN*
_Ludi Informatio v2.0_

📅 *Timeline:* January 8-14, 2026
✅ *Week 1:* COMPLETE - Test pipeline passed!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 *DAYS 1-2: LOGGING FRAMEWORK*

*Deliverables:*
☐ `utils/bet_logger.py` - BetLogger class
☐ `bet_tracking.db` - SQLite database
☐ Module F integration
☐ JSON logs → `logs/bets/YYYY-MM-DD.json`
☐ Backfill script for test results

*Success Criteria:*
☐ Logs written to both JSON + SQLite
☐ Query interface working
☐ <5% performance overhead

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 *DAYS 3-4: PLAY CLASSIFICATION TAGS*

*Tag Categories:*
• Archetype: SLASHER, STRETCH_BIG, RIM_RUNNER
• Scenario: BENEFICIARY, USAGE_VACUUM
• Matchup: HACKERS, PAINT_PACK, PERIMETER
• Market: CORRELATED_SGP, SHARP_MOVE

*Deliverables:*
☐ `utils/tag_classifier.py`
☐ Module F integration
☐ Database schema update
☐ Tags in daily briefing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 *DAYS 5-7: CONFIDENCE INTERVALS*

*Approach:*
• 25th/50th/75th percentile from Monte Carlo
• Floor/ceiling projections
• Display: "Proj: 10.5 (8.2-12.8)"

*Deliverables:*
☐ Module C enhancement (percentiles)
☐ Updated briefing format
☐ Risk assessment logic
☐ Distribution data logged

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 *WEEK 2 SUCCESS GATE*

Must achieve before Week 3:
☐ Logging framework operational
☐ 10+ bets logged with full context
☐ Tag classification working
☐ Confidence intervals displayed
☐ No performance regression (<60s pipeline)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 *NEXT STEP:* Start with `utils/bet_logger.py`

📄 See: `/home/mnprice86/ludi_bot/WEEK2_STARTUP_PROMPT.md`

🚀 Ready to begin Week 2!
"""


def main():
    """Send Week 2 checklist to Telegram"""
    print("=" * 70)
    print("LUDI INFORMATIO - WEEK 2 CHECKLIST NOTIFIER")
    print("=" * 70)
    print()
    print("🤖 Bot: @CashingChips_bot (Ludi_Bot)")
    print()
    print("📱 Sending Week 2 checklist to Telegram...")
    print()

    if send_message(message):
        print()
        print("=" * 70)
        print("✅ WEEK 2 CHECKLIST DELIVERED!")
        print("=" * 70)
        print()
        print("Check your Telegram app for the full Week 2 plan.")
        print()
        print("Next steps:")
        print("  1. Review the checklist in Telegram")
        print("  2. Start with utils/bet_logger.py")
        print("  3. Follow WEEK2_STARTUP_PROMPT.md for details")
        print()
        return True
    else:
        print()
        print("=" * 70)
        print("❌ FAILED TO SEND MESSAGE")
        print("=" * 70)
        print()
        print("⚠️  IMPORTANT: If you see a 403 Forbidden error:")
        print()
        print("  You need to start a conversation with the bot first!")
        print()
        print("  Steps to fix:")
        print("    1. Open Telegram app")
        print("    2. Search for: @CashingChips_bot")
        print("    3. Click 'Start' or send: /start")
        print("    4. Run this script again")
        print()
        print("  Once you've started the conversation, the bot can send messages.")
        print()
        print("Other troubleshooting:")
        print("  • Check TELEGRAM_TOKEN in .env file")
        print("  • Check TELEGRAM_CHAT_ID in .env file")
        print("  • Get your chat ID: Send a message to the bot, then run:")
        print("    curl https://api.telegram.org/bot<TOKEN>/getUpdates")
        print()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
