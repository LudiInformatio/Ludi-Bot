"""
Discord Notifier — Employee Channels
Routes employee-specific messages to individual Discord channels via webhooks.

Telegram = betting product (game notes, bet cards, spotlights, P&L)
Slack    = ops/work notes (pipeline failures, health alerts, diagnostics)
Discord  = employee channels (Henrik, Silas, Vera, Solomon, Maren, Iris, weekly roundtable)

Uses Incoming Webhooks — no OAuth, no bot token. Just a URL per channel in .env.
Graceful degradation: if URL not set, logs warning and returns False without crashing.

Discord-specific constraints:
  - 204 No Content on success (not 200); raise_for_status() still works
  - Never call response.json() on a 204 — it will raise
  - 2000 char message limit (vs Telegram's 4096)
  - Payload key is 'content', not 'text'
"""
import os

import requests

# Dual-source credential loading: config.py first, os.getenv() as fallback.
# config.py skips load_dotenv() when IS_SELF_HOSTED=true, relying on injected
# env vars. Workflow steps without an explicit `env:` block get empty strings
# from the imported constant; os.getenv() catches the process-level var directly.
try:
    from config import (
        DISCORD_WEBHOOK_SILAS,
        DISCORD_WEBHOOK_IRIS,
        DISCORD_WEBHOOK_VERA,
        DISCORD_WEBHOOK_SOLOMON,
        DISCORD_WEBHOOK_HENRIK,
        DISCORD_WEBHOOK_MAREN,
        DISCORD_WEBHOOK_WEEKLY,
        DISCORD_WEBHOOK_INCIDENTS,
    )
except (ImportError, ModuleNotFoundError):
    DISCORD_WEBHOOK_SILAS = os.getenv('DISCORD_WEBHOOK_SILAS', '')
    DISCORD_WEBHOOK_IRIS = os.getenv('DISCORD_WEBHOOK_IRIS', '')
    DISCORD_WEBHOOK_VERA = os.getenv('DISCORD_WEBHOOK_VERA', '')
    DISCORD_WEBHOOK_SOLOMON = os.getenv('DISCORD_WEBHOOK_SOLOMON', '')
    DISCORD_WEBHOOK_HENRIK = os.getenv('DISCORD_WEBHOOK_HENRIK', '')
    DISCORD_WEBHOOK_MAREN = os.getenv('DISCORD_WEBHOOK_MAREN', '')
    DISCORD_WEBHOOK_WEEKLY = os.getenv('DISCORD_WEBHOOK_WEEKLY', '')
    DISCORD_WEBHOOK_INCIDENTS = os.getenv('DISCORD_WEBHOOK_INCIDENTS', '')

# Employee name → module-level constant mapping.
# Used by send_to_employee() to resolve a name to its webhook URL.
_EMPLOYEE_WEBHOOK_MAP = {
    'silas':   'DISCORD_WEBHOOK_SILAS',
    'iris':    'DISCORD_WEBHOOK_IRIS',
    'vera':    'DISCORD_WEBHOOK_VERA',
    'solomon': 'DISCORD_WEBHOOK_SOLOMON',
    'henrik':  'DISCORD_WEBHOOK_HENRIK',
    'maren':   'DISCORD_WEBHOOK_MAREN',
}

# Discord hard limit. Messages exceeding this must be chunked.
_DISCORD_MAX_LENGTH = 2000


def _get_employee_webhook(employee: str) -> str:
    """Resolve an employee name to a webhook URL, checking both the imported
    constant and the live environment variable (handles GH Actions injection)."""
    env_var = _EMPLOYEE_WEBHOOK_MAP.get(employee.lower())
    if not env_var:
        return ''
    # Check module-level constant first; fall back to os.getenv() for injected vars.
    return globals().get(env_var) or os.getenv(env_var, '')


def send_discord_message(message: str, webhook_url: str) -> bool:
    """Send a plain text message to a Discord channel via webhook.

    Chunks messages that exceed Discord's 2000-char limit. Discord webhooks
    return 204 No Content on success — never call response.json() here.

    Args:
        message:     Message content. Supports Discord Markdown (**bold**, *italic*).
        webhook_url: Full Discord webhook URL for the target channel.

    Returns:
        True if all chunks sent successfully, False on any error.
    """
    if not webhook_url:
        print("WARNING discord_notifier: webhook_url is empty — skipping send")
        return False

    # Chunk into <=2000-char segments, splitting on newlines where possible
    # to avoid cutting mid-word or mid-line.
    if len(message) <= _DISCORD_MAX_LENGTH:
        chunks = [message]
    else:
        chunks = []
        lines = message.split('\n')
        current_chunk = ""
        for line in lines:
            # +1 for the newline we'll re-add between lines
            if len(current_chunk) + len(line) + 1 <= _DISCORD_MAX_LENGTH:
                current_chunk += line + '\n'
            else:
                if current_chunk:
                    chunks.append(current_chunk.rstrip('\n'))
                # Handle a single line that itself exceeds the limit
                while len(line) > _DISCORD_MAX_LENGTH:
                    chunks.append(line[:_DISCORD_MAX_LENGTH])
                    line = line[_DISCORD_MAX_LENGTH:]
                current_chunk = line + '\n'
        if current_chunk.strip():
            chunks.append(current_chunk.rstrip('\n'))

    success = True
    for chunk in chunks:
        try:
            r = requests.post(
                webhook_url,
                json={"content": chunk},
                timeout=10
            )
            r.raise_for_status()
            # Discord returns 204 No Content on success. Do NOT call r.json() here.
            if r.status_code not in (200, 204):
                print(f"WARNING discord_notifier: unexpected status {r.status_code}")
                success = False
        except Exception as e:
            print(f"WARNING discord_notifier: send failed — {e}")
            success = False

    return success


def send_to_employee(employee: str, message: str) -> bool:
    """Post a message to a named employee's Discord channel.

    Args:
        employee: One of: silas, iris, vera, solomon, henrik, maren (case-insensitive).
        message:  Message content.

    Returns:
        True on success, False if webhook not configured or send fails.
    """
    webhook_url = _get_employee_webhook(employee)
    if not webhook_url:
        print(f"WARNING discord_notifier: no webhook configured for employee '{employee}' — skipping")
        return False
    return send_discord_message(message, webhook_url)


def send_to_weekly(message: str) -> bool:
    """Post a message to the #weekly-roundtable Discord channel.

    Args:
        message: Message content (e.g., Henrik session digests).

    Returns:
        True on success, False if webhook not configured or send fails.
    """
    webhook_url = DISCORD_WEBHOOK_WEEKLY or os.getenv('DISCORD_WEBHOOK_WEEKLY', '')
    if not webhook_url:
        print("WARNING discord_notifier: DISCORD_WEBHOOK_WEEKLY not configured — skipping")
        return False
    return send_discord_message(message, webhook_url)


def send_to_incidents(message: str) -> bool:
    """Post a message to the #incidents Discord channel.

    Args:
        message: Message content (e.g., pipeline failure alerts, P0 findings).

    Returns:
        True on success, False if webhook not configured or send fails.
    """
    webhook_url = DISCORD_WEBHOOK_INCIDENTS or os.getenv('DISCORD_WEBHOOK_INCIDENTS', '')
    if not webhook_url:
        print("WARNING discord_notifier: DISCORD_WEBHOOK_INCIDENTS not configured — skipping")
        return False
    return send_discord_message(message, webhook_url)
