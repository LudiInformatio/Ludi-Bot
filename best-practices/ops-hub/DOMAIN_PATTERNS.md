# Ops Hub — Domain Diagnosis Examples

Few-shot diagnosis chain examples per workflow domain. Claude reads these as structured
examples before applying the NSP classification gate. Same pattern as `GAME_NOTES_EXAMPLE`
in `utils/claude_prompts.py` — one worked example is worth 10 instructions.

---

## Settlement Domain — Example Chain

**Workflow**: Capture Closing Lines
**Logs**: "BDL: 0 scheduled games for 2026-02-22"

**Step 1 — NSP Classification**:
{"failure_type": "KNOWN_PATTERN", "matched_fix": "2026-02-22 — BDL V2 Status Filter", "confidence": "HIGH", "reasoning": "Symptom exactly matches prior fix — BDL V2 numeric status codes"}

**Step 2 — Tier**: TIER_1 (single-line filter change, zero logic impact)

**Step 3 — Action**:
1. Edit `scripts/capture_closing_lines.py` `fetch_bdl_games_today()` status filter
2. `git commit -m "fix(clv): BDL V2 status codes (1/2/3 not string names)"`
3. Append entry to `KNOWN_FIXES.md` + commit
4. Comment on open ops-hub issue + close it

---

## Settlement Domain — Example Chain 2

**Workflow**: Capture Closing Lines
**Logs**: "Odds API: quota exhausted (cached) — skipping to BDL fallback" then "ERROR: Could not fetch closing data"

**Step 1 — NSP Classification**:
{"failure_type": "TRANSIENT", "matched_fix": "2026-02-22 — Quota Pre-flight", "confidence": "HIGH", "reasoning": "Odds API monthly 20K quota exhausted; BDL should have served as fallback"}

**Step 2 — Tier**: TRANSIENT (monthly reset auto-resolves; if BDL also failing, escalate to TIER_3)

**Step 3 — Action**: Check if BDL fallback is actually working. If BDL returned 0 games, check BDL status filter (see prior fix). If BDL is down, TIER_3 issue only.

---

## Pipeline Domain — Example Chain

**Workflow**: Daily Production Pipeline
**Logs**: "UnboundLocalError: local variable 'odds' referenced before assignment" in `module_e.py`

**Step 1 — NSP Classification**:
{"failure_type": "NEW_FAILURE", "matched_fix": null, "confidence": "HIGH", "reasoning": "UnboundLocalError in module_e.py — variable used before initialization, likely new code path"}

**Step 2 — Tier**: TIER_2 if multi-line fix needed, TIER_1 if single variable initialization missing

**Step 3 — Action**:
1. Read `module_e.py` around the error line
2. Check if variable needs default initialization before the code block that uses it
3. If single-line fix (e.g., `odds = None`): TIER_1 commit
4. If structural (e.g., initialization block in wrong order): TIER_2 PR

---

## Data Sync Domain — Example Chain

**Workflow**: Daily Data Sync
**Logs**: "SLACK_WEBHOOK_URL not configured — skipping Slack notification"

**Step 1 — NSP Classification**:
{"failure_type": "KNOWN_PATTERN", "matched_fix": "2026-02-22 — Slack Notifier Silent in CI", "confidence": "HIGH", "reasoning": "Symptom matches prior fix; utils/slack_notifier.py already patched"}

**Step 2 — Tier**: TRANSIENT (already fixed in notifier — this log is informational, not a failure)

**Step 3 — Action**: None. If the workflow STEP itself failed (not just a Slack skip), investigate the actual failing step. The Slack warning log is expected behavior when step doesn't inject SLACK_WEBHOOK_URL env var.

---

## Database Domain — Example Chain

**Workflow**: Daily Database Backup
**Logs**: "ludi.db: No such file or directory"

**Step 1 — NSP Classification**:
{"failure_type": "NEW_FAILURE", "matched_fix": null, "confidence": "HIGH", "reasoning": "ludi.db missing — runner restart may have broken symlink or DB was not restored"}

**Step 2 — Tier**: TIER_3 (database loss is CRITICAL — do NOT auto-fix, requires human investigation)

**Step 3 — Action**:
1. Create issue with severity:critical
2. Body: check if runner symlink `/Users/flyprice/actions-runner/_work/Ludi-Bot/Ludi-Bot/ludi.db` is intact
3. Recovery: `bash scripts/restore_database.sh` from most recent backup in `archives/data/`

---

## Validation Domain — Example Chain

**Workflow**: Weekly Validation
**Logs**: "Schema drift detected: column 'foo' missing from player_game_logs"

**Step 1 — NSP Classification**:
{"failure_type": "NEW_FAILURE", "matched_fix": null, "confidence": "MEDIUM", "reasoning": "New column expected by validation script but not in DB — likely new feature added without migration"}

**Step 2 — Tier**: TIER_3 (schema changes touch database structure — always TIER_3)

**Step 3 — Action**:
1. Create issue with severity:warning
2. Body: identify which script added the column expectation vs when `database.py` was last updated
3. Fix path: run `python database.py` to apply migration, then re-validate

---

## When to Escalate TRANSIENT → TIER_3

If the same TRANSIENT failure repeats 3+ times in a week:
- Create a TIER_3 issue documenting the pattern
- Tag with `severity:warning` + add a note: "Recurring transient — needs root cause investigation"
