---
name: session-brief
description: >
  Use this skill when the user wants to start a new session, resume work after a break,
  or get oriented quickly without providing manual context. Trigger phrases include:
  "catch me up", "where did we leave off", "what was I working on", "start of day",
  "session brief", "what's the current state", "what's active", "orient me",
  "morning check-in", "coming back from a break", or simply "/session-brief".
---

# Session Brief

Instantly orients you at the start of any session — no manual context-setting needed.

## What This Does

Reads 4 live sources simultaneously, then synthesizes them into a single structured brief:
1. `ROADMAP.md` — active work, recent completions, next priorities
2. `memory/MEMORY.md` — key decisions, bugs fixed, lessons learned
3. `git log` — last 7 commits (what actually shipped)
4. `git status` — any uncommitted local changes right now

---

## Execution Steps

When invoked, perform ALL of the following steps before writing any output:

### Step 1 — Get current date/time

**Use the Bash tool** to run `date '+%A, %B %-d, %Y — %-I:%M %p %Z'` and capture the output. Use this in the brief header — do NOT use today's date from memory or training data.

### Step 2 — Parallel Reads (run simultaneously)

1. **Read ROADMAP.md** — focus on:
   - Line 1–6 (Last Updated, Current Phase, Active Work, Completed)
   - The active sub-phase rows in the current phase table (STATUS = anything other than DONE)
   - The most recent completed sprint section (the last `✅ COMPLETE` block)

2. **Read memory/MEMORY.md** — focus on:
   - The **first 3** `###` section headers and their bullet points (newest entries are prepended at the top)
   - Any lines that mention bugs, fixes, or "next step"

3. **Use the Bash tool to run `git log --oneline -7`** — last 7 commit messages

4. **Use the Bash tool to run `git status --short`** — modified + untracked files

---

### Step 3 — Output the Session Brief

Format the output exactly as shown below. Keep each section tight — bullets only, no paragraphs.

```
## Session Brief — [output of date command, e.g. "Friday, February 20, 2026 — 9:27 PM EST"]

### Active Work
[Phase # — Name]: [one-line description of what's in progress]
[If multiple active items, list each on its own line]

### Last Shipped
[Most recent ✅ sprint name] — [2-3 key things that landed, comma-separated]

### Uncommitted Changes
[List modified/untracked files from git status, or "None — working tree clean"]

### Recent Commits (last 7)
[Paste git log output verbatim, one per line]

### Memory Highlights (recent)
[2-4 most recent bullet points from MEMORY.md that are likely relevant right now]

### Recommended Next Step
[One sentence synthesizing all of the above: "Based on the active work and recent commits, the most logical next step is..."]
```

---

## Output Rules

- **No preamble.** Start directly with `## Session Brief`.
- **No commentary** about what you're reading or why. Just the brief.
- **Recommended Next Step must be actionable** — name a specific file, phase, or task, not a vague suggestion.
- If ROADMAP.md shows multiple active phases, list the highest-priority one first (check the priority column: HIGH > MEDIUM > LOW).
- If git status is clean, say "None — working tree clean" in that section.
- Keep the whole brief under 40 lines total — this is a fast orientation tool, not a report.
