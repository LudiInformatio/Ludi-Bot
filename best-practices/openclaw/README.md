# OpenClaw Patterns & Conventions

This document captures patterns for always-on agents (Silas, Iris) running via macOS launchd.

## Initial Setup Lessons (Mar 1, 2026)

Lessons learned during the first Discord + Telegram Bot 2 setup — avoid these mistakes next time.

### Discord

**1. Bot creation requires human CAPTCHA** — Discord's developer portal shows an hCaptcha when creating a new application via automated browser. Cannot be bypassed with Playwright. User must create the app manually in their own browser. Channels and webhooks CAN be automated (no CAPTCHA).

**2. Webhook vs bot token scope:**
- **Webhook URL**: Post-only to one channel. Returns HTTP **204** (No Content) on success — not 200. Safer for always-on agents (Silas/Iris). Anyone with the URL can post to that one channel only.
- **Bot token**: Full server access. Returns HTTP **200** on success. Required for reading messages, reacting, DMs. Never use in launchd scripts (rotate if exposed).

**3. Channel IDs are stable snowflakes** — Pre-fill all `DISCORD_CHANNEL_*` IDs in `.env.template` when the server is created. They never change. Avoids the "which channel was that?" lookup problem later.

**4. `@everyone` Create Invite OFF** — First thing to do on a private ops server. Prevents users from inviting strangers. Server Settings → Roles → @everyone → Permissions → Create Invite = ❌.

### Telegram

**5. `TELEGRAM_CHAT_ID` is the RECIPIENT's ID, not the bot's ID** — Common mistake: pasting the first 10 digits of the bot token (the bot's own ID) as the chat ID. The chat ID is the person/group you want to receive messages. For a personal bot, this is your personal Telegram user ID (found via `@userinfobot`). When in doubt: look at the existing working `TELEGRAM_CHAT_ID` in `.env` — Solomon's should match unless you want a separate channel.

**6. Bot can't message you until you've messaged it first** — Telegram bots can't initiate conversations with users who haven't started a chat. Send `/start` to the new bot before testing `sendMessage`. This creates the chat and makes the `chat_id` valid.

### Testing Checklist (run after any bot/webhook setup)

```python
# Test all 3 Discord webhooks
for name, url in webhooks.items():
    resp = requests.post(url, json={'content': f'test', 'username': name})
    assert resp.status_code == 204, f"#{name} failed: {resp.status_code}"

# Test Telegram bot
resp = requests.post(f'https://api.telegram.org/bot{token}/sendMessage',
    json={'chat_id': chat_id, 'text': 'test'})
assert resp.status_code == 200, f"Telegram failed: {resp.text}"
```

---

## Architecture Decision

**We use Gemini CLI (`gemini -p "..." -m gemini-2.5-pro --yolo`) as the writer model, not OpenClaw.**

OpenClaw is available as an option, but Gemini CLI was already installed, authenticated, and working on Mar 1 2026. The agent runtime pattern below uses Python scripts + launchd instead.

---

## Agent Runtime Pattern (macOS launchd)

Always-on agents follow this structure:

```
employees/
├── silas/
│   ├── SOUL.md         — Identity, responsibilities, output format
│   ├── HEARTBEAT.md    — Schedule, cadence, priority rules
│   └── run_check.py    — Actual execution script (to be built)
└── iris/
    ├── SOUL.md
    ├── HEARTBEAT.md
    └── run_collection.py
```

### launchd Plist Template

Place in `~/Library/LaunchAgents/`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.ludi.{agent_name}</string>

  <key>ProgramArguments</key>
  <array>
    <string>/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/.venv/bin/python</string>
    <string>/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/employees/{agent}/run_check.py</string>
  </array>

  <key>StartInterval</key>
  <integer>900</integer>  <!-- 900 = 15 min, 1800 = 30 min, 3600 = 1 hr -->

  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/logs/{agent}/stdout.log</string>

  <key>StandardErrorPath</key>
  <string>/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/logs/{agent}/stderr.log</string>

  <key>WorkingDirectory</key>
  <string>/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/.venv/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
```

### Install/Uninstall Commands

```bash
# Install (start agent)
launchctl load ~/Library/LaunchAgents/com.ludi.silas.plist

# Uninstall (stop agent)
launchctl unload ~/Library/LaunchAgents/com.ludi.silas.plist

# Check status
launchctl list | grep com.ludi

# Force run now (for testing)
launchctl start com.ludi.silas
```

---

## Discord Posting Pattern

Always-on agents post to Discord via webhook (no bot library needed for one-way posting):

```python
import requests
import os

WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_SILAS')  # Per-channel webhook URL

def post_to_discord(message: str, level: str = 'info'):
    """Post a message to the agent's Discord channel."""
    emoji = {'critical': '🔴', 'warning': '🟡', 'healthy': '🟢', 'info': '📊'}
    payload = {
        'content': f"{emoji.get(level, '📊')} {message}",
        'username': 'Silas'  # or 'Iris'
    }
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
    return resp.status_code == 204
```

### Create Webhook URL

In Discord:
1. Go to Ludi Lens server → #silas channel
2. Channel Settings → Integrations → Webhooks → New Webhook
3. Name it "Silas", copy URL → add to `.env` as `DISCORD_WEBHOOK_SILAS`

---

## Gemini CLI Writer Pattern

For routine script writing (not always-on agents — just the writer subprocess):

```python
import subprocess

def run_gemini_writer(prompt: str, model: str = 'gemini-2.5-pro') -> str:
    """Call Gemini CLI as writer subprocess."""
    result = subprocess.run(
        ['gemini', '-p', prompt, '-m', model, '--yolo', '-o', 'text'],
        capture_output=True,
        text=True,
        timeout=120
    )
    if result.returncode != 0:
        raise RuntimeError(f"Gemini CLI error: {result.stderr}")
    return result.stdout.strip()
```

**Solomon's routing decision:**
```python
# Routine task → Gemini
output = run_gemini_writer("Write a Python script that reads ludi.db and...")

# Then Henrik reviews the diff before merge
# Core pipeline (Modules A-F) → Claude only (never Gemini)
```

---

## Agent Output Schema

All always-on agents return structured output for downstream parsing:

```python
{
    "agent": "silas",
    "timestamp": "2026-03-01T14:00:00-05:00",
    "level": "healthy",  # critical | warning | healthy | info
    "summary": "All systems nominal",
    "checks": [
        {"name": "daily_simulation", "status": "ok", "detail": "ran 10:14 AM, 23 bets"},
        {"name": "odds_api_quota", "status": "warning", "detail": "74.2% used"}
    ],
    "discord_posted": True
}
```

---

## Key Notes

- **SOUL.md** defines identity and responsibilities — read by the agent at startup
- **HEARTBEAT.md** defines schedule and cadence — read by launchd plist
- **run_check.py / run_collection.py** are the actual execution scripts (Phase 2 build)
- **Webhooks** are the simplest posting mechanism — no OAuth, no bot library
- **Gemini CLI** is the writer subprocess — not OpenClaw, not OpenCode
