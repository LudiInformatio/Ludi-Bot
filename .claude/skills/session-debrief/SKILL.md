---
name: session-debrief
description: >
  Use this skill at the END of a session to wrap up work cleanly before signing off.
  Trigger phrases include: "wrap up", "end session", "session debrief", "signing off",
  "wrap it up", "end of day", "taking a break", "commit and close", or simply
  "/session-debrief". This skill updates docs, commits changes, and sends the PM bot
  break message. It is the end-of-session counterpart to /session-brief.
allowedTools:
  - Bash
  - Read
  - Edit
  - Write
  - Glob
  - Grep
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
7.5. Test & verify — agent work or long sessions (conditional — see below)
8. Commit all changes
9. Send PM bot break message (always last)

---

## Execution Steps

Perform ALL steps in order before writing any output.

### Step 1 — Get real date/time (always first)

**Use the Bash tool** to run: `date '+%A, %B %-d, %Y — %-I:%M %p %Z'` and capture the output.

Use this timestamp everywhere. Do NOT use memory or training data for the date.

---

### Step 2 — Understand session scope (parallel reads)

**Use the Bash tool** to run all three simultaneously (parallel tool calls):
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

**⚠️ PM Bot Grounding Check (mandatory — run every debrief):**

After writing `**Active Work:**`, read it back and verify it passes the BERT formula from
`best-practices/ai/PM_BOT_NOTES_GUIDE.md`:

```
Formula: [Module/Feature] ([file or class]) — [what specifically] → [next milestone]
Good:    Sprint 2 (`scripts/revalidate_recs.py`, `midday_refresh.py`) — is_valid lifecycle + Perplexity upgrade
Bad:     Sprint ongoing + Phase 8 work + backfill running
```

**Fail conditions (rewrite immediately if any apply):**
- No backtick file or class name in the first segment → Gemini has no grounding signal
- First segment starts with "Continue", "Ongoing", or "Working on" → too vague
- First segment is a phase number only (`Phase 8.23`) without a file or feature name
- Line is unchanged from the previous session despite different work happening today

The PM bot uses `in_progress[0]` (first ` + ` segment) for break messages. A vague
first segment = generic NBA trivia in THE VIBE/THE INTEL. This check is non-negotiable.

---

### Step 4 — Update active docs (scope-gated)

Only update if something is actually wrong or outdated — no additions for their own sake.
Use the Step 2 findings to determine what to check:

| What changed this session | Check this doc |
|---------------------------|----------------|
| Module files (`module_*.py`) | `docs/ARCHITECTURE.md` module reference table |
| Workflow files (`.github/workflows/*.yml`) | `CLAUDE.md` automation schedule table |
| Database schema (`database.py`) | `docs/ARCHITECTURE.md` schema section + **run schema gap check below** |
| New API behavior confirmed | `CLAUDE.md` API Configuration table |
| New scripts added | `CLAUDE.md` Quick Commands or `docs/TOOLS_GUIDE.md` |
| Any session with shipped features or phase completions | `README.md` — update Status date, Active/Planned Next section, add to Phase 8 completions table if warranted |
| Code fixes or workarounds shipped | `docs/TECH_DEBT.md` — move resolved items to Archive with commit hash; add new debt discovered |

**Schema gap check (run every session, not just when database.py changed):**
```bash
db_tables=$(grep -c 'CREATE TABLE IF NOT EXISTS\|CREATE TABLE [^I]' database.py 2>/dev/null || echo 0)
arch_tables=$(grep -c '^\| \`' docs/ARCHITECTURE.md 2>/dev/null || echo 0)
echo "DB:$db_tables ARCH:$arch_tables GAP:$((db_tables - arch_tables))"
```
- GAP ≤ 5 → acceptable drift, skip
- GAP 6–15 → add to **Next Session Priorities** in the debrief output
- GAP > 15 → add to Next Session Priorities AND flag in ROADMAP `**Active Work:**` if not already there

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

**Use the Bash tool** to run `git status` to see all modified and untracked files.

Spot-check `CLAUDE.md` for accuracy — especially:
- Automation schedule table (any new or changed workflow times?)
- Module Reference table (any renamed or new modules?)
- Known Gotchas section (any new gotchas discovered today?)

If today's changes made anything in `CLAUDE.md` stale → fix it now before committing.

---

### Step 7.5 — Test & verify (conditional — run before committing)

**Run this step if ANY of the following are true:**
- This session reviewed or continued another agent's work
- 5+ files were changed this session
- Any files were created, moved, or renamed by an agent

**Use the Bash tool** to run each applicable check:

1. **Files created by agent** → confirm they exist and have correct content:
   ```bash
   ls [path/to/expected/file]
   head -5 [path/to/new/file]   # verify no --- YAML front matter artifact at line 1
   ```

2. **Files moved by agent** → confirm source is gone, destination present:
   ```bash
   ls .github/workflows/          # moved file should NOT appear here
   ls .github/workflows/_archive/ # moved file SHOULD appear here
   ```

3. **Python files added or changed** → catch import errors before they reach main:
   ```bash
   source .venv/bin/activate && python -c "from [module] import [ClassName]"
   ```

4. **DB schema changes** → verify columns are as expected:
   ```bash
   sqlite3 ludi.db "PRAGMA table_info([table_name]);"
   ```

5. **`git diff --stat`** → review the full set of staged/unstaged changes one final time before commit.

**If any check fails** → fix the issue now, before proceeding to Step 8. Do NOT commit broken state.

---

### Step 8 — Commit all changes

**Use the Bash tool** to stage all updated files and commit. Execute these commands:

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

**CRITICAL: Always push immediately after committing.**
The GH Actions runner checks out `origin/main` — if you commit but don't push, the runner
runs stale code for every workflow until the next push. This is a silent failure mode.

**Use the Bash tool** to push:
```bash
git push origin main
```

If push is rejected with "branches diverged" (GH Actions data-sync commits ran overnight),
**use the Bash tool** to run:
```bash
git diff main...origin/main --stat   # Verify only log files differ
git merge origin/main --no-edit      # Safe merge — logs only, no conflicts
git push origin main
```

---

### Step 9 — Send PM bot break message (always last, always after commit)

**Pre-flight — use the Bash tool to read back `**Active Work:**` from the committed ROADMAP.md:**

```bash
grep "^\*\*Active Work:" ROADMAP.md
```

Check all three conditions before running pm_break:

| Check | Pass | Fail → Action |
|-------|------|---------------|
| First segment has a backtick file/class name | `` `module_f.py` ``, `` `LudiReporter` `` | Rewrite Active Work, recommit, then pm_break |
| First segment is NOT generic | Not "Continue...", "Ongoing...", "Working on..." | Same fix |
| `**Completed:**` has exactly 3 ` + ` segments | Three distinct items | Add/split items, recommit |

If any check fails → fix ROADMAP.md, re-run Step 8 (commit the fix), THEN run pm_session.
**Never run pm_session with a vague Active Work line — the result will be generic every time.**

**Use the Bash tool** to execute:
```bash
source .venv/bin/activate && python main.py --mode pm_session
```

This sends the session debrief card to Telegram and Slack (uses `header_break.png` — recharging graphic):
- **THE WINS** — last 3 completions from `**Completed:**` in ROADMAP.md
- **THE PIVOT** — `in_progress[0]` as today's sprint + `pending[0]` as tomorrow
- **THE VIBE** — Gemini closing line grounded in the sprint above

> `pm_break` (STATE PRESERVED format) is for mid-session pauses only — NOT end-of-session.
> `pm_session` is always the correct choice at end of session (uses recharging break graphic).
> `pm_debrief` is the automated nightly P&L workflow (uses nightly graphic) — do NOT use for session end.

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

### PM Bot Debrief
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
