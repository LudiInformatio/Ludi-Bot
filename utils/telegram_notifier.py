"""
LUDI INFORMATIO | TELEGRAM NOTIFIER
====================================
Utility for sending messages via Telegram Bot API

Created: January 7, 2026
Purpose: Enable Telegram notifications for daily briefings, alerts, and updates
"""

import requests
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID


def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """
    Send message via Telegram bot

    Args:
        text: Message content (supports Markdown or HTML)
        parse_mode: "Markdown" or "HTML" (default: "Markdown")

    Returns:
        True if sent successfully, False otherwise

    Example:
        >>> send_message("*Bold text* and _italic text_")
        ✅ Telegram message sent successfully
        True

        >>> send_message("<b>HTML bold</b>", parse_mode="HTML")
        ✅ Telegram message sent successfully
        True
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials not configured in .env file")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    
    # Only include parse_mode if explicitly set (Telegram rejects null values)
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()

        if response.json().get("ok"):
            print(f"✅ Telegram message sent successfully")
            return True
        else:
            error_msg = response.json().get("description", "Unknown error")
            print(f"❌ Telegram API error: {error_msg}")
            return False

    except requests.exceptions.Timeout:
        print(f"❌ Telegram API timeout after 10 seconds")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error: {e}")
        return False

def send_photo(photo_path: str, caption: str = None, parse_mode: str = None) -> bool:
    """
    Send a photo via Telegram bot.
    
    Args:
        photo_path: Absolute path to the image file
        caption: Optional text caption
        parse_mode: formatting mode (Markdown/HTML/None)
        
    Returns:
        True if sent successfully
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials not configured")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    
    try:
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': TELEGRAM_CHAT_ID}
            if caption:
                data['caption'] = caption
                if parse_mode:
                    data['parse_mode'] = parse_mode
            
            response = requests.post(url, files=files, data=data, timeout=20)
            response.raise_for_status()
            
            if response.json().get("ok"):
                print("✅ Telegram photo sent successfully")
                return True
            else:
                print(f"❌ Telegram API error: {response.json().get('description')}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to send Telegram photo: {e}")
        return False


def send_document(document_path: str, caption: str = None, parse_mode: str = None) -> bool:
    """
    Send a document/file via Telegram bot.
    
    Args:
        document_path: Absolute path to the file
        caption: Optional text caption
        parse_mode: formatting mode (Markdown/HTML/None)
        
    Returns:
        True if sent successfully
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Telegram credentials not configured")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    
    try:
        with open(document_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': TELEGRAM_CHAT_ID}
            if caption:
                data['caption'] = caption
                if parse_mode:
                    data['parse_mode'] = parse_mode
            
            response = requests.post(url, files=files, data=data, timeout=30)
            response.raise_for_status()
            
            if response.json().get("ok"):
                print("✅ Telegram document sent successfully")
                return True
            else:
                print(f"❌ Telegram API error: {response.json().get('description')}")
                return False
                
    except Exception as e:
        print(f"❌ Failed to send Telegram document: {e}")
        return False


def send_alert(title: str, message: str) -> bool:
    """
    Send formatted alert message

    Args:
        title: Alert title (will be bolded)
        message: Alert body text

    Returns:
        True if sent successfully, False otherwise

    Example:
        >>> send_alert("API Quota Warning", "80% of The-Odds-API quota used")
    """
    formatted_text = f"⚠️ *{title}*\n\n{message}"
    return send_message(formatted_text)


def send_daily_briefing(briefing_text: str) -> bool:
    """
    Send daily betting briefing

    Args:
        briefing_text: Formatted briefing content

    Returns:
        True if sent successfully, False otherwise

    Note:
        If briefing is >4096 characters, it will be split into multiple messages
    """
    MAX_LENGTH = 4096

    if len(briefing_text) <= MAX_LENGTH:
        return send_message(briefing_text)

    # Split into chunks if too long
    chunks = []
    lines = briefing_text.split('\n')
    current_chunk = ""

    for line in lines:
        if len(current_chunk) + len(line) + 1 <= MAX_LENGTH:
            current_chunk += line + '\n'
        else:
            chunks.append(current_chunk)
            current_chunk = line + '\n'

    if current_chunk:
        chunks.append(current_chunk)

    # Send all chunks
    print(f"📱 Sending {len(chunks)} message parts...")
    success = True
    for i, chunk in enumerate(chunks, 1):
        print(f"   Part {i}/{len(chunks)}...")
        if not send_message(chunk):
            success = False

    return success


if __name__ == "__main__":
    # Test the utility
    print("🧪 Testing Telegram notifier...\n")

    # Test 1: Simple message
    print("Test 1: Simple message")
    send_message("✅ Test message from Ludi Informatio")

    # Test 2: Markdown formatting
    print("\nTest 2: Markdown formatting")
    send_message("*Bold text*, _italic text_, and `code text`")

    # Test 3: Alert
    print("\nTest 3: Alert message")
    send_alert("Test Alert", "This is a test alert from the Ludi Bot")

    print("\n✅ All tests complete!")
