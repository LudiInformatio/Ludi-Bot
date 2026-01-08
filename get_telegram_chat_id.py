#!/usr/bin/env python
"""
LUDI INFORMATIO | TELEGRAM CHAT ID HELPER
==========================================
Get your Telegram chat ID after sending /start to the bot

Created: January 7, 2026
Purpose: Help users find their correct Telegram chat ID
"""

import requests
from config import TELEGRAM_TOKEN


def get_chat_id():
    """
    Retrieve chat ID from recent bot messages

    Instructions:
        1. Open Telegram and search for @CashingChips_bot
        2. Send the message: /start
        3. Run this script to get your chat ID
        4. Update TELEGRAM_CHAT_ID in .env file
    """
    print("=" * 70)
    print("LUDI INFORMATIO - TELEGRAM CHAT ID FINDER")
    print("=" * 70)
    print()
    print("🤖 Bot: @CashingChips_bot")
    print()

    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN not found in .env file")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"

    try:
        print("📱 Fetching recent messages...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):
            print(f"❌ Telegram API error: {data.get('description', 'Unknown error')}")
            return

        updates = data.get("result", [])

        if not updates:
            print()
            print("⚠️  No messages found!")
            print()
            print("You need to start a conversation with the bot first:")
            print()
            print("  1. Open Telegram app")
            print("  2. Search for: @CashingChips_bot")
            print("  3. Click 'Start' or send: /start")
            print("  4. Run this script again")
            print()
            return

        print(f"✅ Found {len(updates)} message(s)")
        print()

        # Get the most recent message
        latest = updates[-1]
        chat = latest.get("message", {}).get("chat", {})

        chat_id = chat.get("id")
        first_name = chat.get("first_name", "Unknown")
        username = chat.get("username", "N/A")

        print("=" * 70)
        print("YOUR TELEGRAM CHAT ID")
        print("=" * 70)
        print()
        print(f"  Chat ID: {chat_id}")
        print(f"  Name: {first_name}")
        print(f"  Username: @{username}")
        print()
        print("=" * 70)
        print()
        print("Next steps:")
        print()
        print(f"  1. Open .env file")
        print(f"  2. Update this line:")
        print(f"     TELEGRAM_CHAT_ID={chat_id}")
        print(f"  3. Save the file")
        print(f"  4. Run: python send_week2_checklist.py")
        print()
        print("=" * 70)

    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching updates: {e}")


if __name__ == "__main__":
    get_chat_id()
