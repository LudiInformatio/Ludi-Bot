# Coding Best Practices

**Status:** ✅ Complete (updated 2026-03-04)

This guide covers Python and bash coding patterns for the Ludi-Bot codebase. Every pattern is backed by a real incident or confirmed working pattern from the production system.

---

## Quick Reference

| Pattern | Rule |
|---------|------|
| `_` for discarded return values | Signals intentional discard; prevents `ValueError: too many values` |
| `${VAR:-default}` bash defaults | After any command that might return empty output |
| Never bare `except: pass` | Always log before `continue` — even one line |
| Lazy imports for optional dependencies | `import anthropic` inside function, not module level |
| Grep callers before changing return signature | Prevent silent crashes at call sites |
| `|| true` vs `|| echo "default"` | `|| echo` only fires on non-zero exit, not empty output |
| `INSERT OR IGNORE` + UNIQUE INDEX for pipeline loggers | Any table a pipeline writes to repeatedly needs a dedup guard — plain `INSERT` causes 2–10× row inflation |

---

## Pattern 1 — Discarding Tuple Return Values with `_`

**Problem:** Functions that return multiple values (tuples) are common in this codebase. When a function's return count grows, callers that unpack the old count silently crash.

```python
# module_f.py — returns 3 values after Phase 8.2/8.3 update
def generate_report(self, props):
    # ...
    return briefing_text, image_path, all_props  # 3-tuple

# ❌ Old caller — crashes with ValueError: too many values to unpack (expected 2)
briefing, image_path = self.reporter.generate_report(processed_slate)

# ✅ Use _ to explicitly discard values you don't need
briefing, image_path, _ = self.reporter.generate_report(processed_slate)
```

**Why `_` matters:**
- Signals to readers: "I know there's a 3rd value — I'm intentionally not using it"
- Prevents confusion about whether the caller missed something
- Python convention for "throw this away"

**Before changing any function's return count:**
```bash
# Find all callers and update them BEFORE committing
grep -rn "generate_report\|your_function_name" --include="*.py" .
```

**Real incident:** `main.py:639` crashed with `ValueError: too many values to unpack` for 4 consecutive days (Feb 16–19) because `module_f.generate_report()` was updated to return 3 values in commit `bd9cb38` but `main.py` was never updated.

---

## Pattern 2 — Bash Default Variable Substitution

**Problem:** Shell commands like `grep`, `sed`, `awk`, and `head` can return **empty output** with a non-zero exit code OR empty output with exit code 0 (success). The `|| echo "default"` pattern only handles the non-zero case.

```bash
# ❌ grep exits 0 with empty string when pattern not found
B2B_DIFF=$(grep "B2B Differential" logfile.log | grep -o "[+-]*[0-9]*\.[0-9]*" | head -1 || echo "0.0")
#          grep exits 0 → "|| echo" doesn't fire → B2B_DIFF = ""

python -c "float('$B2B_DIFF')"  # → ValueError: could not convert string to float: ''

# ✅ Use bash parameter expansion for the empty-output case
B2B_DIFF=$(grep "B2B Differential" logfile.log | grep -o "[+-]*[0-9]*\.[0-9]*" | head -1 || true)
B2B_DIFF="${B2B_DIFF:-0.0}"  # If empty, use "0.0"

python -c "float('$B2B_DIFF')"  # → 0.0 ✅
```

**When to use each:**

| Technique | Use when |
|-----------|----------|
| `cmd \|\| echo "default"` | Command might fail (non-zero exit) and you want a fallback |
| `${VAR:-default}` | Variable might be empty (command succeeded but returned no output) |
| Both together | Command might fail OR succeed with empty output |

```bash
# Safest combination
VAR=$(some_command || true)   # "|| true" makes exit code always 0
VAR="${VAR:-default_value}"   # then handle empty string case
```

**Real incident:** `weekly_validation.yml` "Check for Modifier Drift" step crashed with `ValueError: could not convert string to float: ''` when the backtest log had no "B2B Differential" line. Fixed Feb 19 (commit `9f50c6a`).

---

## Pattern 3 — Never Bare `except: pass` or `except Exception: continue`

**The single most important coding rule in this project.** Silent exceptions have caused data to go stale for 21+ days undetected.

```python
# ❌ Silent failure — NEVER do this
for row in rows:
    try:
        process_row(row)
    except Exception:
        continue  # Error is completely invisible

# ✅ Minimum: always log before continuing
for row in rows:
    try:
        process_row(row)
    except Exception as e:
        print(f"[ERROR] Row {row.get('id', '?')} failed: {e}")
        continue

# ✅ Better: track error count and print summary
success_count = 0
error_count = 0
first_error = None

for row in rows:
    try:
        process_row(row)
        success_count += 1
    except Exception as e:
        error_count += 1
        if first_error is None:
            first_error = str(e)
        print(f"[ERROR] Row {row.get('id', '?')} failed: {e}")

print(f"✅ Synced {success_count} rows | {'⚠️' if error_count else '✅'} {error_count} errors")
if first_error:
    print(f"   First error: {first_error}")
```

**What counts as "bare":**
- `except Exception: continue`
- `except Exception: pass`
- `except: continue`
- `except Exception as e: pass  # ignored`

**What's acceptable:**
- `except Exception as e: print(f"Error: {e}"); continue`
- `except Exception: return None  # documented fallback`
- `except ImportError: ...  # optional dependency not installed`

**Real incident:** `sync_wowy_hybrid.py` used `except Exception: continue` inside its main loop. The `league_id` parameter rename caused every API call to fail. Because the exception was swallowed, no error was ever printed. `team_lineups` was silently stale for multiple weeks.

---

## Pattern 4 — Lazy Imports for Optional Dependencies

**Problem:** If `import anthropic` is at the module level and the package isn't installed or the API key isn't configured, the import fails when the module is first loaded — even for users who never call the Claude-related function.

```python
# ❌ Module-level import — fails at import time if anthropic not configured
import anthropic

class LudiReporter:
    def generate_spotlight(self, player):
        client = anthropic.Anthropic()
        # ...

# ✅ Lazy import — only fails if the function is actually called
class LudiReporter:
    def generate_spotlight(self, player):
        import anthropic  # imported here, inside the function
        client = anthropic.Anthropic()
        # ...
```

**When to use lazy imports:**
- External packages that may not be installed in all environments
- API clients that require credentials at init time
- Heavy packages (ML libraries) where import time matters

**When NOT to use lazy imports:**
- Standard library modules (`datetime`, `os`, `json`)
- Core project utilities that are always needed
- Required dependencies where an ImportError early is actually desirable

**Reference:** `best-practices/api/LLM_INTEGRATION.md` — Claude client pattern uses lazy import throughout.

---

## Pattern 5 — Module Return Contract

When you change the number of values a function returns, you are changing its **contract** with all callers. Treat this like a breaking change.

**Checklist before changing a return signature:**

```bash
# 1. Find all call sites
grep -rn "def your_function_name" --include="*.py" .  # confirm location
grep -rn "your_function_name(" --include="*.py" .     # find all calls
grep -rn "= .*your_function_name\|, .*your_function_name" --include="*.py" .  # find unpack patterns

# 2. Update ALL callers in the same commit
# 3. In Python, prefer returning a named tuple or dict for multi-value returns — it's more resilient to extension
```

**Preferred: named tuple for complex return values**
```python
from collections import namedtuple

ReportResult = namedtuple('ReportResult', ['briefing', 'image_path', 'all_props'])

def generate_report(self, props):
    return ReportResult(briefing=..., image_path=..., all_props=...)

# Caller — resilient to new fields being added
result = self.reporter.generate_report(processed_slate)
briefing = result.briefing
image_path = result.image_path
# result.all_props available if needed, ignored if not
```

---

## Pattern 6 — Fail Loudly in Production, Degrade Gracefully for Enhancements

Two different error handling philosophies depending on what the code does:

| Code type | Error strategy | Example |
|-----------|---------------|---------|
| Core pipeline (simulations, bets) | Fail loudly — let the error surface | `module_c.py`, `module_f.py` |
| Enhancement / enrichment (Claude, Perplexity) | Degrade gracefully — fall back to deterministic | `curate_plays.py`, `morning_brief.py` |
| Sync scripts called with `continue-on-error: true` | Log + continue — but ALWAYS print the error | `sync_wowy_hybrid.py`, `sync_bdl_tracking.py` |

```python
# ✅ Graceful degradation for Claude-enhanced features
def generate_spotlight(self, player, stats):
    try:
        import anthropic
        # ... Claude call
        return claude_narrative
    except Exception as e:
        print(f"[WARNING] Claude spotlight failed, using fallback: {e}")
        return f"{player['name']} averaging {stats['pts']:.1f} PPG over last 10 games."  # deterministic fallback

# ✅ Fail loudly for core math
def calculate_edge(self, model_prob, fair_prob):
    if fair_prob <= 0:
        raise ValueError(f"Invalid fair_prob: {fair_prob}")  # this should never happen
    return (model_prob - fair_prob) / fair_prob * 100
```

---

## Pattern 7 — Module-Level Constants for Configuration

**Problem:** Stat categorizations scattered across functions create maintenance burden. Adding a stat type requires editing multiple conditionals.

**Example:**
```python
# ❌ Before: magic values in every function
def get_matchup_analysis(stat_category):
    if stat_category in ['PTS', 'AST', '3PM', 'TOV']:
        return _offensive_matchup()
    elif stat_category in ['STL', 'BLK', 'DREB']:
        return _defensive_matchup()

def apply_modifier(stat_category):
    if stat_category in ['PTS', 'AST', '3PM', 'TOV']:  # Duplicate list
        return offensive_modifier()

# ✅ After: single source of truth at module level
OFFENSIVE_STATS = ['PTS', 'AST', '3PM', 'TOV', 'FGA', 'FTA', 'OREB']
DEFENSIVE_STATS = ['STL', 'BLK', 'DREB']

def get_matchup_analysis(stat_category):
    if stat_category in OFFENSIVE_STATS:
        return _offensive_matchup()
    elif stat_category in DEFENSIVE_STATS:
        return _defensive_matchup()
```

**Real incident:** Bug 2 (defensive playtype filtering) — stat routing logic needed in 2+ functions. Module-level constants solved it (Sprint 10 post-audit).

---

## Pattern 8 — Normalize String Values at Load Time, Not Lookup Time

**Problem:** DB columns written by external APIs often use different casing or format than the code expects. If you normalize at lookup time, you have to remember it everywhere. Normalize once at load — at the `_load_*()` method — and the rest of the codebase sees a clean value.

```python
# ❌ DB stores 'HOME'/'AWAY', lookup expects 'home'/'away' — silently returns None everywhere
ha_stats = ha_data.get(scenario_context['home_or_away'])  # 'home' → never matches 'HOME'

# ✅ Normalize at load time — one place, fixes every downstream call
for row in rows:
    ha = row['home_or_away'].lower() if row['home_or_away'] else row['home_or_away']
    result[pid][ha] = {...}  # stored as 'home'/'away' — matches all lookups
```

**Rule:** Before writing any dict keyed by a DB string column, verify the exact stored values first:
```python
conn.execute("SELECT DISTINCT col FROM table WHERE col IS NOT NULL LIMIT 5").fetchall()
```

**When this applies:** Any `_load_*()` method that groups by a DB column used as a dict key: `home_or_away`, `style`, `active_style`, `position`, `archetype`, `source`.

**Real incident:** `module_x_scenario._load_ha_splits()` keyed on `'HOME'`/`'AWAY'` (raw from DB). Condition 1 H/A modifier returned `None` for every player. Caught by smoke test — all mods were exactly `1.0`.

---

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| `except: pass` | Hides every error forever | Always include `print(f"[ERROR] {e}")` |
| `|| echo "default"` for empty grep | Doesn't fire on empty output, only non-zero exit | Use `${VAR:-default}` |
| Module-level Claude/Anthropic import | Fails at import time if not configured | Lazy import inside function |
| Unpacking tuple without `_` for extras | Crashes when return count grows | Always use `_` for unused values |
| Not grepping callers before return change | Silent crashes at call sites | `grep -rn "function_name(" --include="*.py" .` first |
| Hardcoded `DB_PATH = "ludi.db"` (relative) | Fails when bot/web app runs from `bots/` or another directory | Use `os.path.join(os.path.dirname(os.path.abspath(__file__)), "ludi.db")` in `config.py` — anchors to file location, not CWD |

---

---

## Pattern — `INSERT OR IGNORE` + UNIQUE INDEX for Pipeline Loggers *(Added: 2026-03-04)*

**Problem:** Any table that a scheduled pipeline writes to repeatedly will silently accumulate duplicate rows if it uses plain `INSERT INTO`. Pipeline re-runs, manual triggers, GH Actions retries, and concurrency races all create duplicate entries. With no UNIQUE constraint, the DB never rejects them. This inflates P&L unit totals, bet counts, and any aggregate metric — while win rate % stays correct (duplicates settle identically).

**Real incident:** `bet_recommendations` accumulated 17,202 duplicate rows (65% of the table) over 7 weeks. Peak was 10.17× duplication on a single date. P&L totals were inflated 2–10× throughout.

**The fix has two layers — both required:**

**Layer 1 — UNIQUE INDEX (DB enforcement):**
```sql
-- SQLite does not support ADD CONSTRAINT after table creation.
-- Use a unique index instead — INSERT OR IGNORE will respect it.
CREATE UNIQUE INDEX IF NOT EXISTS idx_bet_recs_no_dupes
ON bet_recommendations(game_date, player_name, stat_category, bet_side);
```

**Layer 2 — INSERT OR IGNORE (application layer):**
```python
# ❌ Plain INSERT — silently adds duplicates on every pipeline re-run
query = f"INSERT INTO bet_recommendations ({fields}) VALUES ({placeholders})"

# ✅ INSERT OR IGNORE — first insertion wins; re-runs skip existing rows
query = f"INSERT OR IGNORE INTO bet_recommendations ({fields}) VALUES ({placeholders})"
```

**Dedup recovery query (if duplicates already exist):**
```sql
-- Step 1: Delete duplicates, keeping MIN(id) per unique combo
DELETE FROM table_name
WHERE id NOT IN (
    SELECT MIN(id) FROM table_name
    GROUP BY game_date, player_name, stat_category, bet_side
);

-- Step 2: Create the index AFTER dedup (will fail if dupes remain)
CREATE UNIQUE INDEX IF NOT EXISTS idx_name ON table_name(col1, col2, col3, col4);
```

**Diagnosis query — run on any pipeline output table to check for duplication:**
```sql
SELECT date_col, COUNT(*) as total,
       COUNT(DISTINCT key_col1 || '|' || key_col2) as unique_combos,
       ROUND(CAST(COUNT(*) AS REAL) / COUNT(DISTINCT key_col1 || '|' || key_col2), 2) as dupe_factor
FROM table_name
GROUP BY date_col
ORDER BY date_col DESC;
```
Any `dupe_factor > 1.0` = duplicates present. Target: 1.0 on all dates.

**`INSERT OR REPLACE` vs `INSERT OR IGNORE`:**
- `OR IGNORE` — first insertion wins; re-runs are no-ops. Best for immutable records (bets, log entries).
- `OR REPLACE` — latest insertion wins (deletes + re-inserts). Wipes `outcome`/`actual_result` if settlement data exists. **Do NOT use for settled records.**

**Other tables to audit in this codebase:** `claude_analysis_log`, `prop_line_snapshots`, `player_news_staging` — all written by pipelines that re-run daily.

---

## Future Skill

**`/code-review`** — Automated code quality check
- Validates against project coding standards
- Checks for common anti-patterns (bare `except`, missing `_`, module-level Claude imports)
- Runs `grep` to verify callers are updated when return signatures change
- Generates: compliance report + refactoring recommendations
