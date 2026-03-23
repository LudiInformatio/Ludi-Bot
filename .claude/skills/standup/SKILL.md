---
name: standup
description: >
  Monday morning team round-table — all employees report status.
  Solomon aggregates infrastructure, code, data, and QA signals into a single
  structured standup. Trigger phrases: "standup", "morning standup",
  "team standup", "Monday standup", "round table", "/standup".
agent: solomon
user-invocable: true
allowedTools:
  - Bash
  - Read
  - Glob
  - Grep
---

# Team Standup

All employees report status; Solomon synthesizes into one structured brief.

## What This Does

Gathers live signals from 4 sources simultaneously, then attributes findings to
the responsible employee by domain:
1. `ROADMAP.md` header — phase, active work, completed items
2. `git log` — what shipped in the last 7 days
3. `memory/MEMORY.md` — decisions, drift flags, lessons
4. `gh run list` — recent workflow health (Silas domain)

---

## Execution Steps

### Step 1 — Get current date/time

**Use the Bash tool** to run `date '+%A, %B %-d, %Y — %-I:%M %p %Z'` and capture the output. Use this in the standup header. If the day is Monday, label it "Monday Standup"; otherwise label it "Standup".

### Step 2 — Parallel Reads (run simultaneously)

1. **Read `ROADMAP.md` lines 1-6** — capture Current Phase, Active Work, Completed.
2. **Bash:** `git log --oneline --since="7 days ago"` — commits shipped this week.
3. **Bash:** `git status --short` — any uncommitted changes.
4. **Read `memory/MEMORY.md`** — first 3 `###` sections (if file exists; skip silently if missing).

### Step 3 — Check GitHub Actions health

**Bash:** `gh run list --limit 5 --json name,status,conclusion,createdAt`

Parse the JSON: count passed vs failed. Note any failed workflow names for Silas report.

### Step 4 — Synthesize team reports

Attribute findings to employees by domain:

- **Silas (Infra):** Derive from Step 3 GH Actions data — last 5 runs, pass/fail ratio, any failures by name.
- **Henrik (Code):** Scan git log from Step 2 for "Henrik APPROVED", "audit", "review", or PR-related commits. Summarize recent audit activity.
- **Lena (Data):** Scan ROADMAP Active Work + Completed + memory for calibration, model, drift, or data references.
- **Vera (QA):** Scan ROADMAP Next Actions + memory for backtest, validation, or QA references.

### Step 5 — Output the standup

Format exactly as shown below.

---

## Output Format

```
## [Monday Standup | Standup] — [date from Step 1]

### Phase Focus
[Current phase + active work from ROADMAP header lines 4-5]

### Team Reports
**Silas (Infra):** [1-2 lines from GH Actions — last 5 runs, any failures]
**Henrik (Code):** [1-2 lines — recent audits, open review items from git log]
**Lena (Data):** [1-2 lines — model metrics, drift flags from ROADMAP/memory]
**Vera (QA):** [1-2 lines — backtest status, warnings from ROADMAP/memory]

### Shipped Last Week
- [Max 5 bullets from git log + ROADMAP Completed line]

### Blockers
[Items flagged BLOCKED in ROADMAP Next Actions — or "None"]

### This Week's Priorities
1. [Top 3 unchecked `- [ ]` items from ROADMAP Next Actions, with backtick file/class names]

### Status: [ON_TRACK | AT_RISK | BLOCKED]
```

---

## Output Rules

- **No preamble.** Start directly with `## Monday Standup` or `## Standup`.
- **No commentary** about what you're reading or why. Just the standup.
- Status enum is mandatory: `ON_TRACK` if no blockers, `AT_RISK` if any warnings or failed workflows, `BLOCKED` if critical failures or all priorities stalled.
- Employee reports are 1-2 lines max each — signal only, no filler.
- Shipped Last Week: max 5 bullets. Prefer ROADMAP Completed items over raw commit hashes.
- This Week's Priorities: always include backtick file/class names where applicable.
- Keep the whole standup under 35 lines total.

---

## Post-Check Actions

- **ON_TRACK**: No follow-up needed — standup is informational.
- **AT_RISK**: Flag the specific risk in Blockers section so owner can triage.
- **BLOCKED**: Escalate — list the blocking item and which employee owns the fix.
