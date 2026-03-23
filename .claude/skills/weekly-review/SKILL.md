---
name: weekly-review
description: >
  End-of-week retrospective — what shipped, model performance, team health.
  Solomon synthesizes commits, workflow data, model metrics, and ROADMAP state
  into a structured weekly review. Trigger phrases: "weekly review",
  "end of week", "week review", "retro", "retrospective", "Friday review",
  "/weekly-review".
agent: solomon
user-invocable: true
allowedTools:
  - Bash
  - Read
  - Glob
  - Grep
---

# Weekly Review

End-of-week retrospective covering shipped work, model performance, pipeline health, and team status.

## What This Does

Gathers a full week of signals from 5 sources, then synthesizes into a structured
retrospective with actionable next-week priorities:
1. `ROADMAP.md` — full sprint state, active work, completed items, next actions
2. `git log` — all commits from the past 7 days
3. `memory/MEMORY.md` — decisions, lessons, flags from the week
4. `gh run list` — 20 most recent workflow runs (week's pipeline health)
5. `ludi.db` — bet settlement and CLV metrics (optional; graceful fallback)

---

## Execution Steps

### Step 1 — Get current date/time

**Use the Bash tool** to run `date '+%A, %B %-d, %Y — %-I:%M %p %Z'` and capture the output. Calculate the Monday and Friday dates for the current week to use in the header.

### Step 2 — Parallel Reads (run simultaneously)

1. **Read `ROADMAP.md`** — full file. Focus on: Current Phase, Active Work, Completed line, Current Sprint section (Next Actions checklist), Phase 8 table status column.
2. **Bash:** `git log --oneline --since="7 days ago"` — full week's commits.
3. **Read `memory/MEMORY.md`** — all recent entries (if file exists; skip silently if missing).
4. **Bash:** `gh run list --limit 20 --json name,status,conclusion,createdAt` — week's workflow health.

### Step 3 — Check for reports

**Bash:** `ls -la reports/ 2>/dev/null` — look for any backtest or calibration reports generated this week.

### Step 4 — Model performance query (optional)

**Bash:** Run the following against `ludi.db`. If the database is not accessible or returns no rows, use fallback text "No settled bets this period".

```bash
sqlite3 ludi.db "SELECT COUNT(*) as total, SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) as wins, SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) as losses, ROUND(AVG(CASE WHEN clv_cents IS NOT NULL THEN clv_cents END), 1) as avg_clv FROM bet_recommendations WHERE game_date >= date('now', '-7 days') AND outcome IS NOT NULL;"
```

### Step 5 — Synthesize weekly review

Parse all gathered data and format exactly as shown below. For "What Worked" and "What Didn't", synthesize from git log patterns (e.g., fix commits = things that broke, feature commits = things that shipped cleanly) and ROADMAP changes. Do not speculate.

---

## Output Format

```
## Weekly Review — Week of [Monday date] to [Friday date]

### Sprint Summary
**Phase:** [from ROADMAP]
**Planned:** [what was in Active Work at week start — from ROADMAP header]
**Shipped:** [what moved to Completed — from ROADMAP Completed line]

### Commits This Week
1. [commit hash + message, max 10 entries from git log]

### Model Performance
- Bets settled: [N] (W-L: [X]-[Y])
- Hit rate: [X%] (target: >52%)
- Avg CLV: [+/- X cents]
[Or "No settled bets this period" if no data]

### Pipeline Health (Silas)
- Workflow runs: [N total], [X passed], [Y failed]
- [List any failed workflows by name — or "All workflows passed"]

### What Worked
- [2-3 bullets — process wins, clean deploys, good catches from git log]

### What Didn't
- [2-3 bullets — fix commits, blockers hit, tech debt from git log + ROADMAP]

### Team Health
| Employee | Status | Notes |
|----------|--------|-------|
| Silas | [ON_TRACK/AT_RISK] | [1 line from workflow data] |
| Henrik | [ON_TRACK/AT_RISK] | [1 line from git log audit activity] |
| Lena | [ON_TRACK/AT_RISK] | [1 line from calibration/data status] |
| Vera | [ON_TRACK/AT_RISK] | [1 line from backtest/QA status] |

### Next Week Priorities
1. [Top 3 unchecked `- [ ]` items from ROADMAP Next Actions]

### Decisions Needed
[Items requiring owner sign-off from ROADMAP — or "None"]

### Overall: [ON_TRACK | AT_RISK | BLOCKED]
```

---

## Output Rules

- **No preamble.** Start directly with `## Weekly Review`.
- **No commentary** about what you're reading or why. Just the review.
- Model Performance: if DB not accessible or query returns zero rows, say "No settled bets this period" — never error or leave blank.
- Team Health uses enum status only: `ON_TRACK` or `AT_RISK`. Never free-form text in the Status column.
- What Worked / What Didn't: ground every bullet in observable evidence (commit messages, ROADMAP state changes, workflow failures). Do not speculate or assume.
- Commits This Week: max 10 entries. If more than 10, show the 10 most significant (features/fixes over docs/formatting).
- Next Week Priorities: always include backtick file/class names where applicable.
- Decisions Needed: only list items from ROADMAP that explicitly require sign-off or choice — not general tasks.
- Keep the whole review under 50 lines total.
- Overall status enum: `ON_TRACK` if hit rate on target and no critical failures, `AT_RISK` if any metric below threshold or failed workflows, `BLOCKED` if critical path stalled.

---

## Post-Check Actions

- **ON_TRACK**: Archive as a good week. No follow-up needed.
- **AT_RISK**: Identify the specific risk and which employee owns triage in Decisions Needed.
- **BLOCKED**: Escalate — the blocking item and responsible employee must be named explicitly.
