# Debugging Best Practices

**Status:** ✅ Complete (updated 2026-02-19)

This guide covers debugging workflows, CI diagnosis, and silent failure detection for the Ludi-Bot production pipeline. Patterns are derived from real incidents discovered through the Feb 19 workflow audit.

---

## Quick Reference

| Pattern | When to Use |
|---------|-------------|
| `gh run list` + `gh run view --log-failed` | First step when a workflow shows red |
| Audit "green" workflows for silent failures | After any library update or return signature change |
| `inspect.signature` for library params | Before writing code that calls a 3rd-party class with keyword args |
| `${VAR:-default}` bash default | Any bash variable derived from `grep` or `sed` that might be empty |
| Check callers after changing return count | Before committing any function that returns a tuple |
| Never bare `except: continue` | All Python scripts — log the error even if you continue |

---

## CI Workflow Diagnosis Playbook

Use this sequence when a workflow fails or shows unexpected behavior.

### Step 1 — Get the failing run ID

```bash
# List recent runs with outcomes
gh run list --limit 25 --json name,conclusion,databaseId,startedAt \
  --jq '.[] | "\(.databaseId) \(.conclusion) \(.name) \(.startedAt)"'

# Filter to only failures
gh run list --limit 25 --json name,conclusion,databaseId \
  --jq '[.[] | select(.conclusion == "failure")] | .[] | "\(.databaseId) \(.name)"'
```

### Step 2 — Read the failure log

```bash
# Get logs for failed steps only (much less noise than full log)
gh run view <RUN_ID> --log-failed

# Or get full log piped through grep for specific errors
gh run view <RUN_ID> --log 2>&1 | grep -E "##\[error\]|Error:|ValueError:|exit code"
```

### Step 3 — Check for "silent green" steps

A workflow can show ✅ SUCCESS while individual steps inside it have failed — if those steps have `continue-on-error: true`.

```bash
# Show true outcome of every step, including continue-on-error ones
gh run view <RUN_ID> --json jobs \
  --jq '.jobs[] | {job: .name, conclusion: .conclusion, steps: [.steps[] | {step: .name, outcome: .conclusion}]}'
```

Look for steps where `.conclusion == "failure"` even though the job shows success.

### Step 4 — Check what data went stale

If a sync step was silently failing, query the affected table's `synced_at` or latest `game_date`:

```sql
-- When was team_lineups last updated?
SELECT MAX(updated_at), COUNT(*) FROM team_lineups;

-- When were rotation profiles last rebuilt?
SELECT MAX(synced_at), COUNT(*) FROM rotation_profiles;

-- Is nba_calendar fresh?
SELECT date, has_games, season_phase, synced_at
FROM nba_calendar
WHERE date >= date('now', '-3 days')
ORDER BY date;
```

---

## Pattern 1 — Library Parameter Inspection

**Problem:** Python library updates silently rename constructor parameters. Code that worked yesterday raises `TypeError: unexpected keyword argument 'league_id'` with zero other symptoms.

**How to detect before writing code:**

```python
# Inspect actual parameter names before using them
from nba_api.stats.endpoints import leaguedashlineups
import inspect

sig = inspect.signature(leaguedashlineups.LeagueDashLineups.__init__)
print(list(sig.parameters.keys()))
# Output: ['self', 'season', 'league_id_nullable', 'season_type_all_star', ...]
#                                ↑ not 'league_id' — it was renamed
```

**How to check after a `requirements.txt` update:**

```bash
# If you updated nba_api, verify all keyword args still exist
source .venv/bin/activate
python3 -c "
from nba_api.stats.endpoints import leaguedashlineups
import inspect
sig = inspect.signature(leaguedashlineups.LeagueDashLineups.__init__)
params = list(sig.parameters.keys())
# Check the specific param you use
print('league_id_nullable' in params)  # Should be True
print('league_id' in params)           # Should be False after the rename
"
```

**Real incident:** `sync_wowy_hybrid.py` used `league_id="00"` which worked in an older nba_api version. After a library update, `LeagueDashLineups` renamed it to `league_id_nullable`. The script failed silently on every run for weeks because the WOWY sync step had `continue-on-error: true`. `team_lineups` table went stale. Fixed Feb 19 (commit `9f50c6a`).

---

## Pattern 2 — Function Return Tuple Mismatch

**Problem:** When a function's return tuple grows (e.g. returns 3 values instead of 2), all callers that unpack it silently crash at runtime with `ValueError: too many values to unpack (expected 2)`.

**The fix:** Use `_` to discard unused return values explicitly.

```python
# ❌ Breaks silently when generate_report() adds a 3rd return value
briefing, image_path = self.reporter.generate_report(processed_slate)

# ✅ Explicit discard — signals "I know there's a 3rd value, I don't need it"
briefing, image_path, _ = self.reporter.generate_report(processed_slate)
```

**How to find all callers before committing a return signature change:**

```bash
# Find every place that unpacks the return value
grep -rn "= self\.reporter\.generate_report\|= reporter\.generate_report\|generate_report(" \
  --include="*.py" .

# Or for any function
grep -rn "= self\.reporter\." --include="*.py" .
```

**Real incident:** Phase 8.2/8.3 (commit `bd9cb38`, Feb 17) changed `module_f.generate_report()` to return `(briefing, image_path, all_props)`. `main.py:639` still unpacked only 2 values. The pipeline crashed on every run from Feb 17–19. Fixed Feb 19 (commit `0104878`).

---

## Pattern 3 — Bash Empty Variable → Python Float Crash

**Problem:** `grep -o` returns an **empty string** (not a non-zero exit code) when the pattern doesn't match. If you pipe that empty string to Python's `float()`, you get `ValueError: could not convert string to float: ''`.

The `|| echo "0.0"` fallback **does not help** — it only fires on non-zero exit, not empty output.

```bash
# ❌ grep returns "" when "B2B Differential" line not found
B2B_DIFF=$(grep "B2B Differential" some_log.log | grep -o "[+-]*[0-9]*\.[0-9]*" | head -1 || echo "0.0")
# ^ "|| echo" doesn't fire — grep exits 0 with empty output

# Then in Python: float('') → ValueError

# ✅ Use bash default substitution for the empty-output case
B2B_DIFF=$(grep "B2B Differential" some_log.log | grep -o "[+-]*[0-9]*\.[0-9]*" | head -1 || true)
B2B_DIFF="${B2B_DIFF:-0.0}"  # default to 0.0 if grep returned empty
```

**General rule:** Any bash variable derived from `grep`, `sed`, `awk`, or any command that might produce empty output should be followed by `VAR="${VAR:-default}"` before it's passed to Python or bash arithmetic.

**Real incident:** `weekly_validation.yml` "Check for Modifier Drift" step produced `float('')` when the backtest log didn't contain a "B2B Differential" line on a no-game week. Fixed Feb 19 (commit `9f50c6a`).

---

## Pattern 4 — Silent Failure Detection

**The #1 debugging rule:** Never use bare `except: pass` or `except Exception: continue` without logging. Silent swallowed exceptions have caused multi-week data degradation.

```python
# ❌ Bug: 21 days of hidden failures — no visibility at all
for row in rows:
    try:
        process_wowy_row(row)
    except Exception:
        continue

# ✅ Fix: Log the error, then decide to continue
for row in rows:
    try:
        process_wowy_row(row)
    except Exception as e:
        print(f"[ERROR] Row {row.get('id')} failed: {e}")
        continue
```

**For scripts with `continue-on-error: true` in the workflow:**

The script itself MUST log failures. The workflow-level `continue-on-error` only prevents job failure — it doesn't give you any visibility into what went wrong. If the script swallows errors too, you're completely blind.

```python
# At the end of any sync script, print a summary
print(f"✅ Synced {success_count} rows | ⚠️ {error_count} errors")
if error_count > 0:
    print(f"   First error: {first_error}")
```

---

## Pattern 5 — Database Corruption Detection

Before any critical database operation (write, migration, sync), verify the database is healthy.

```python
import subprocess

def check_db_integrity(db_path='ludi.db') -> bool:
    """Returns True if DB is healthy, False if corrupted."""
    result = subprocess.run(
        ['sqlite3', db_path, 'PRAGMA integrity_check;'],
        capture_output=True, text=True
    )
    return result.stdout.strip() == 'ok'

# Usage in a sync script
if not check_db_integrity():
    print("⚠️ Database corrupted — aborting sync to prevent data loss")
    sys.exit(1)
```

**In GitHub Actions workflows:**
```yaml
- name: Initialize database if needed
  run: |
    if [ ! -f ludi.db ]; then
      python3 database.py
    else
      INTEGRITY=$(sqlite3 ludi.db "PRAGMA integrity_check;" 2>&1)
      if [ "$INTEGRITY" != "ok" ]; then
        echo "⚠️ Database corrupted, reinitializing..."
        mv ludi.db ludi.db.corrupted.$(date +%Y%m%d_%H%M%S)
        python3 database.py
      fi
    fi
```

---

## Pattern 6 — "Silent Green" Workflow Diagnosis

**Problem:** A GitHub Actions job shows ✅ SUCCESS but the data it was supposed to sync hasn't been updated in days. This happens when `continue-on-error: true` steps are the ones that fail.

**Diagnosis steps:**

```bash
# 1. Get job details with step-level outcomes
gh run view <RUN_ID> --json jobs \
  --jq '.jobs[] | "JOB: \(.name) = \(.conclusion)\n" + (.steps[] | "  STEP: \(.name) = \(.conclusion // "skipped")")'

# 2. Look for steps where conclusion == "failure" despite job == "success"

# 3. Check the log for that specific step
gh run view <RUN_ID> --log 2>&1 | grep -A 20 "##\[group\]Run.*step_name"

# 4. Verify the affected table's freshness
python3 -c "
import sqlite3
conn = sqlite3.connect('ludi.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*), MAX(game_date) FROM team_lineups')
print(cursor.fetchone())
"
```

**Red flags that suggest silent green:**
- Table has data but `MAX(synced_at)` or `MAX(game_date)` is multiple days old
- Workflow shows ✅ but `nba_calendar` freshness check in `validate_schema.py` fails
- Pipeline output looks reasonable but edge calculations are based on stale WOWY data

---

## Anti-Patterns

| Anti-Pattern | What You Miss | Correct Pattern |
|-------------|--------------|-----------------|
| `except Exception: continue` | Every error — forever | `except Exception as e: print(f"[ERROR] {e}"); continue` |
| `|| echo "default"` for empty grep | `grep` returns 0 with empty output | `${VAR:-default}` bash substitution |
| Assuming library params are stable | API renames break silently | `inspect.signature()` check before every library upgrade |
| Not checking callers after adding a return value | Caller raises `ValueError: too many values` | `grep -rn` callers before committing |
| Trusting green CI status on `continue-on-error` steps | Stale data for days/weeks | `gh run view --json jobs --jq` to check step-level outcomes |

---

## Future Skill

**`/debug-assist`** — Interactive debugging helper
- Guided troubleshooting workflow
- Runs `gh run list` + `gh run view` automatically
- Queries affected table freshness
- Suggests diagnostic steps based on symptoms
- Generates: diagnostic report + recommended fixes
