# Agent Infrastructure Patterns

**Last Updated:** March 6, 2026
**Purpose:** Patterns for the hybrid AI employee architecture — Skills 2.0 subagents for interactive work + external stack (launchd, Discord, Telegram, GH Actions) for scheduled/always-on work.

---

## Architecture Decision: Hybrid (Skills 2.0 + External Stack)

**Mar 6, 2026:** After evaluating OpenClaw, Gemini CLI, and Claude Code Skills 2.0 subagents, we chose a **hybrid architecture**:

| Layer | Runtime | Cost | Use Case |
|-------|---------|------|----------|
| **Interactive** | Skills 2.0 subagents (`.claude/agents/*.md`) | $0 (subscription) | Code review, health checks, data analysis, sprint status |
| **Scheduled** | launchd plists + Python scripts | $0 | Cron-triggered collection (Iris), periodic health (Silas) |
| **Always-on** | Telegram bots (`bots/*.py`) | ~$2.40/mo | Solomon PM chat, Ask Ludi chatbot |
| **CI/CD** | GH Actions (`.github/workflows/*.yml`) | ~$2.20/mo | Code review on PR, ops hub failure diagnosis |
| **Async logs** | Discord webhooks | $0 | Employee output channels, weekly roundtable |

**Why not OpenClaw alone?** Skills 2.0 subagents are free (uses Claude Code subscription), have native tool integration, persistent memory across sessions, and auto-delegation by description. OpenClaw would add a separate runtime with no memory persistence.

**Why not subagents alone?** Subagents only run during active Claude Code sessions. Always-on bots (Telegram) and scheduled tasks (launchd, GH Actions) need processes that persist when Claude Code is closed.

---

## Skills 2.0 Subagent Patterns

### Agent File Anatomy

Every subagent lives at `.claude/agents/{name}.md` — YAML frontmatter + system prompt body.

```markdown
---
name: henrik
description: >
  Code Quality Architect — 11 YOE. Use after code changes to audit for
  Ludi-specific gotchas: silent pipeline failures, data contamination,
  accent mismatches, busy_timeout gaps, canonical ID firewall violations.
model: sonnet
tools: Read, Grep, Glob, Bash
skills:
  - ludi-audit
memory: project
isolation: worktree
maxTurns: 30
---

# Henrik — Code Quality Architect

[System prompt body — identity, responsibilities, constraints, output format]
```

### Key Frontmatter Fields

| Field | Values | Purpose |
|-------|--------|---------|
| `model` | `haiku`, `sonnet`, `opus` | Which Claude model powers this agent |
| `tools` | `Read, Grep, Glob, Bash, ...` | Restrict which tools the agent can use |
| `memory` | `project` | Persistent memory across sessions — agent learns over time |
| `permissionMode` | `plan` | Enforces read-only at the tool level (no file edits) |
| `isolation` | `worktree` | Agent works on isolated git worktree copy (can't break working tree) |
| `maxTurns` | integer | Prevents runaway agents from consuming context |
| `skills` | list of skill names | Skills this agent can invoke |

### Auto-Delegation

Claude Code automatically routes user requests to the best-matching subagent by description. No explicit routing code needed:

- "review module_f.py for issues" -> matches Henrik's description -> delegates to Henrik
- "check system health" -> matches Silas's description -> delegates to Silas
- "what does the data say about BLK UNDER?" -> matches Lena's description -> delegates to Lena

### Shell Injection (Zero Token Cost)

Skills can inject live shell output into prompts using backtick-bang syntax:

```markdown
## Current System State

!`sqlite3 ludi.db "SELECT COUNT(*) FROM player_game_logs"`
!`gh run list --limit 5`
!`date '+%A, %B %-d, %Y'`
```

The shell commands run before the agent sees the prompt — real data at zero token cost.

### `$ARGUMENTS` for User Input

Skills accept user arguments via `$ARGUMENTS`:

```markdown
## Your Task

Analyze the following topic from the user:
$ARGUMENTS
```

Invoked as: `/lena-analyze BLK UNDER win rate by defensive tag`

### `context: fork` for Background Execution

Skills with `context: fork` run in a background subprocess — the main conversation continues while the skill executes:

```yaml
---
name: silas-check
context: fork
agent: silas
user-invocable: true
---
```

---

## Subagent vs External — Decision Table

| Need | Use Subagent | Use External |
|------|-------------|-------------|
| Interactive code review | Henrik (`.claude/agents/`) | — |
| Scheduled health check | — | launchd + `run_check.py` |
| Always-on Telegram bot | — | `bots/solomon_bot.py` |
| On-demand data query | Lena (`.claude/agents/`) | — |
| CI/CD event response | — | GH Actions (`claude-ops-hub.yml`) |
| Cron-triggered collection | — | launchd + Iris `run_collection.py` |
| Session-scoped audit | Henrik/Vera subagent | — |
| Sprint status check | Solomon subagent | — |
| Repo cleanup report | Kai subagent | — |

**Rule of thumb:** If it needs to run while Claude Code is closed -> external. If it runs during a session -> subagent.

---

## External Stack Patterns (launchd, Discord, Telegram)

The patterns below remain valid for the external layer of the hybrid architecture.

### Initial Setup Lessons (Mar 1, 2026)

Lessons learned during the first Discord + Telegram Bot 2 setup — avoid these mistakes next time.

#### Discord

**1. Bot creation requires human CAPTCHA** — Discord's developer portal shows an hCaptcha when creating a new application via automated browser. Cannot be bypassed with Playwright. User must create the app manually in their own browser. Channels and webhooks CAN be automated (no CAPTCHA).

**2. Webhook vs bot token scope:**
- **Webhook URL**: Post-only to one channel. Returns HTTP **204** (No Content) on success — not 200. Safer for always-on agents (Silas/Iris). Anyone with the URL can post to that one channel only.
- **Bot token**: Full server access. Returns HTTP **200** on success. Required for reading messages, reacting, DMs. Never use in launchd scripts (rotate if exposed).

**3. Channel IDs are stable snowflakes** — Pre-fill all `DISCORD_CHANNEL_*` IDs in `.env.template` when the server is created. They never change.

**4. `@everyone` Create Invite OFF** — First thing to do on a private ops server. Server Settings > Roles > @everyone > Permissions > Create Invite = off.

#### Telegram

**5. `TELEGRAM_CHAT_ID` is the RECIPIENT's ID, not the bot's ID** — Common mistake: pasting the first 10 digits of the bot token (the bot's own ID) as the chat ID. The chat ID is the person/group you want to receive messages. For a personal bot, this is your personal Telegram user ID (found via `@userinfobot`).

**6. Bot can't message you until you've messaged it first** — Send `/start` to the new bot before testing `sendMessage`. This creates the chat and makes the `chat_id` valid.

#### Testing Checklist (run after any bot/webhook setup)

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

### Gemini CLI Slash Commands

Gemini CLI supports slash commands via `.gemini/commands/*.toml`. This mirrors Claude Code's `.claude/commands/*.md` system but uses TOML format.

#### TOML Command Format

```toml
description = "Short description shown in /help"
prompt = """
Activate the {skill-name} skill.

Specific instructions for this command's phase or focus.

{{args}}
"""
```

- `{{args}}` — injects whatever the user types after the command
- One file = one command. File name = command name (colons are valid: `architect:audit.toml` -> `/architect:audit`)

#### Sub-Command Pattern

For multi-phase workflows, split one full skill into focused sub-commands:

```
architect.toml          ->  /architect          (full skill, all phases)
architect:audit.toml    ->  /architect:audit    (audit only -> stop, review)
architect:design.toml   ->  /architect:design   (design only -> stop, review)
architect:implement.toml -> /architect:implement (implement only)
```

This prevents the model from over-running before findings are reviewed.

#### Claude / Gemini Parity

Skills live in both places. Keep them in sync:

| Claude Code | Gemini CLI |
|-------------|------------|
| `.claude/skills/{name}/SKILL.md` | `.gemini/skills/{name}/SKILL.md` |
| `.claude/commands/{name}.md` | `.gemini/commands/{name}.toml` |
| `$ARGUMENTS` placeholder | `{{args}}` placeholder |

**Current shared skills:** `session-brief`, `session-debrief`, `sports-data-model-architect`, `ludi-audit`, `backtest`, `daily`

---

### Agent Runtime Pattern (macOS launchd)

Always-on and scheduled agents use Python scripts triggered by launchd:

```
employees/
├── silas/
│   ├── SOUL.md         — Identity (reference — content moves to .claude/agents/silas.md)
│   ├── HEARTBEAT.md    — Schedule, cadence, priority rules
│   └── run_check.py    — Execution script (launchd-triggered)
└── iris/
    ├── SOUL.md
    ├── HEARTBEAT.md
    └── run_collection.py
```

#### launchd Plist Template

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

#### Install/Uninstall Commands

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

### Discord Posting Pattern

Always-on agents post to Discord via webhook (no bot library needed):

```python
import requests
import os

WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_SILAS')

def post_to_discord(message: str, level: str = 'info'):
    """Post a message to the agent's Discord channel."""
    payload = {
        'content': f"[{level.upper()}] {message}",
        'username': 'Silas'
    }
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
    return resp.status_code == 204
```

---

### Gemini CLI Writer Pattern

For routine script writing (writer subprocess, not always-on):

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
# Routine task -> Gemini
output = run_gemini_writer("Write a Python script that reads ludi.db and...")

# Then Henrik reviews the diff before merge
# Core pipeline (Modules A-F) -> Claude only (never Gemini)
```

---

### Agent Output Schema

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

- **SOUL.md** content moves INTO the `.claude/agents/*.md` file (single source of truth). `employees/*/SOUL.md` becomes a reference link only.
- **HEARTBEAT.md** defines schedule and cadence — read by launchd plist (external layer only)
- **Subagents** handle interactive work during Claude Code sessions ($0)
- **External scripts** handle scheduled/always-on work (launchd, GH Actions, Telegram bots)
- **Webhooks** are the simplest Discord posting mechanism — no OAuth, no bot library
- **Gemini CLI** is the writer subprocess for routine code generation
