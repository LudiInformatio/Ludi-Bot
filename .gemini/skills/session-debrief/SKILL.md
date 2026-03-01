---
name: session-debrief
description: >
  Use this skill at the END of a session to wrap up work cleanly before signing off.
  Trigger phrases include: "wrap up", "end session", "session debrief", "signing off",
  "wrap it up", "end of day", "taking a break", "commit and close", or simply
  "/session-debrief". This skill updates docs, commits changes, and sends the PM bot
  break message. It is the end-of-session counterpart to /session-brief.
---

# Session Debrief

Wraps up any session cleanly — updates docs, captures learnings, commits all changes,
and sends the PM bot break message. The counterpart to `/session-brief`.

## What This Does

Nine ordered steps that must run in sequence. Do NOT skip steps or reorder them.

1. Get real date/time
2. Understand session scope from git
3. Update ROADMAP.md header
4. Update active docs (scope-gated — only what changed)
5. Review `best-practices/` for new patterns and bloat
6. Update `memory/MEMORY.md` (enforce 200-line limit)
7. Spot-check git status and `CLAUDE.md`
8. Commit all changes
9. Send PM bot break message (always last)

---

## Execution Steps

Perform ALL steps in order before writing any output.

### Step 1 — Get real date/time (always first)

Run: `date '+%A, %B %-d, %Y — %-I:%M %p %Z'`

Use this timestamp everywhere. Do NOT use memory or training data for the date.

---

### Step 2 — Understand session scope (parallel reads)

Run simultaneously:
- `git log --oneline -10` — what was committed this session
- `git status --short` — what is uncommitted right now
- `git diff --stat HEAD~5` — which files were touched across recent commits

This output scopes all downstream steps. Only update docs related to what actually changed.
If a doc area was not touched this session, do not update it.

---

### Step 3 — Update ROADMAP.md header

**Always update:**
- `**Last Updated:**` → current date/time from Step 1

**Update only if warranted by Step 2 findings:**
- `**Active Work:**` → if a new sub-phase started or active item shifted
- `**Completed:**` → append sub-phases or sprints closed this session

**Constraint:** Touch ONLY the 6-line header block and any directly affected rows in the
active sub-phase table. Do NOT rewrite prose sections — those evolve intentionally,
not auto-edited every session.

---

### Step 4 — Update active docs (scope-gated)

Only update if something is actually wrong or outdated — no additions for their own sake.
Use the Step 2 findings to determine what to check:

| What changed this session | Check this doc |
|---------------------------|----------------|
| Module files (`module_*.py`) | `docs/ARCHITECTURE.md` module reference table |
| Workflow files (`.github/workflows/*.yml`) | `CLAUDE.md` automation schedule table |
| Database schema (`database.py`) | `docs/ARCHITECTURE.md` schema section |
| New API behavior confirmed | `CLAUDE.md` API Configuration table |
| New scripts added | `CLAUDE.md` Quick Commands or `docs/TOOLS_GUIDE.md` |

If nothing in the relevant doc is wrong → skip this step entirely.

---

### Step 5 — Review `best-practices/`

Scope to areas touched during this session. For each area, ask:
**"Did today's work reveal a reusable pattern not already documented?"**

- If yes → add to the appropriate doc, or create a new sub-section if genuinely new territory
- If existing content is outdated by today's work → trim or update it
- **Anti-bloat rule:** If a pattern is already captured, do NOT re-document it with a slight
  variation. One clear example beats three redundant ones.
- Check `ops-hub/KNOWN_FIXES.md` — any fixes from today not yet appended? Log them now.
- If any category doc was changed → update the `Last Updated:` line in `best-practices/README.md`

---

### Step 6 — Update `memory/MEMORY.md`

Add new entries at the TOP (newest-first pattern). Only log:
- Bugs fixed with non-obvious root causes
- New architectural decisions made
- API behaviors discovered or confirmed
- Patterns validated across multiple interactions

**Hard limit: MEMORY.md must be ≤ 200 lines.**
The file is truncated at line 200 — anything beyond is invisible to future sessions.
If adding new entries would push past 200, consolidate or remove outdated entries first.
Check line count after edits: `wc -l memory/MEMORY.md`

---

### Step 7 — Check git status and CLAUDE.md

Run `git status` to see all modified and untracked files.

Spot-check `CLAUDE.md` for accuracy — especially:
- Automation schedule table (any new or changed workflow times?)
- Module Reference table (any renamed or new modules?)
- Known Gotchas section (any new gotchas discovered today?)

If today's changes made anything in `CLAUDE.md` stale → fix it now before committing.

---

### Step 8 — Commit all changes

Stage all updated files and commit:

```bash
git add [list of files changed in steps 3–7]
git commit -m "$(cat <<'EOF'
chore(session): end-of-session doc sync YYYY-MM-DD

- ROADMAP.md: Last Updated timestamp [+ any status changes]
- [each other file changed, one line per file]
- memory/MEMORY.md: N new entries added

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

Replace YYYY-MM-DD with today's date. If no doc changes were needed (clean session),
still commit with "no doc changes needed — working tree clean".

---

### Step 9 — Send PM bot break message (always last, always after commit)

```bash
source .venv/bin/activate
python main.py --mode pm_break
```

This sends the structured break card to Telegram and the Slack ops channel:
- **STATE PRESERVED** — current in-progress task from ROADMAP.md `[-]` items
- **QUICK WINS** — recent completions from ROADMAP.md `[x]` items
- **THE VIBE** — motivational closing line (Gemini-generated)

Step 9 is always last. The break message must reflect a clean committed state.
If the commit in Step 8 failed → do NOT send the PM break. Resolve the commit first.

---

## Output Format

After all 9 steps complete, output exactly this format. No preamble — start directly
with `## Session Debrief`. Keep the total under 30 lines.

```
## Session Debrief — [date/time from Step 1]

### Shipped This Session
- [one bullet per major thing completed and committed this session]

### Docs Updated
- [list each file touched during steps 3–7, or "None — all docs current"]

### Commit
[short hash] — [commit message first line]

### PM Bot Break
Sent ✅   (or ❌ [brief error note])

### Next Session Priorities
- [1–3 specific actionable items from ROADMAP active work — name file, phase, or task]
```

---

## Output Rules

- **No preamble.** Start directly with `## Session Debrief`.
- **No commentary** about what you did or why. Just the debrief.
- **Next Session Priorities must be actionable** — name a specific file, phase, or task.
  Not: "Continue Phase 8 work." Yes: "Implement Ask Ludi bot at `bots/ask_ludi.py`."
- If git was already clean before the debrief, say so under Docs Updated.
- If PM bot fails, note the error and suggest running `python main.py --mode pm_break` manually.
