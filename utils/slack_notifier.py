"""
Slack Notifier — Ops/Work Notes Channel
Routes operational alerts to Slack, keeping Telegram clean for betting product only.

Telegram = betting product (game notes, bet cards, spotlights, P&L)
Slack    = ops/work notes (pipeline failures, health alerts, diagnostics, QA, PM bot work notes)

Uses Incoming Webhook — no OAuth, no bot token. Just a URL in SLACK_WEBHOOK_URL.
Graceful degradation: if URL not set, prints warning but doesn't crash.
"""
import requests

try:
    from config import SLACK_WEBHOOK_URL
except (ImportError, ModuleNotFoundError):
    import os
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')


def _get_webhook() -> str:
    return SLACK_WEBHOOK_URL or ''


def send_slack_message(text: str) -> bool:
    """Send a plain text message to the Slack ops channel."""
    webhook = _get_webhook()
    if not webhook:
        print("⚠️ SLACK_WEBHOOK_URL not configured - skipping Slack notification")
        return False
    try:
        r = requests.post(
            webhook,
            json={"text": text},
            timeout=10
        )
        return r.status_code == 200
    except Exception as e:
        print(f"⚠️ Slack notification failed: {e}")
        return False


def send_slack_alert(title: str, message: str) -> bool:
    """Send a formatted warning alert to Slack."""
    return send_slack_message(f"⚠️ *{title}*\n\n{message}")
