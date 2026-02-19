# Testing Best Practices

**Status:** ✅ Complete (updated 2026-02-19)

This guide covers validation patterns, smoke tests, and CI audit techniques for Ludi-Bot. Patterns focus on keeping tests fast and quota-safe while catching real production issues.

---

## Quick Reference

| Test Type | Command | When to Run |
|-----------|---------|-------------|
| Module smoke test | `python -c "from module_e import LudiCalibrator; print('OK')"` | After any change to module imports |
| Schema validation | `python scripts/validate_schema.py --verbose` | After any `database.py` change |
| Canonical ID check | `python scripts/validate_canonical_ids.py -v` | After player roster updates |
| Param existence test | `inspect.signature(Cls.__init__)` | After updating `requirements.txt` |
| CI health check | `gh run list --limit 10 --json name,conclusion` | After any workflow change |
| Workflow gate test | Trigger workflow on no-game date | After adding/changing check-slate gates |
| Backtest validation | `python scripts/backtest_fatigue_21day.py` | After model changes |

---

## Pattern 1 — Module Smoke Tests

Run after any change to module imports, class names, or constructor signatures.

```bash
# Test all core modules import without error
python3 -c "from module_a import Gatekeeper; print('✅ Module A OK')"
python3 -c "from module_b import print_sharp_box_score; print('✅ Module B OK')"
python3 -c "from module_c import LudiOracle; print('✅ Module C OK')"
python3 -c "from module_d import LudiYak; print('✅ Module D OK')"
python3 -c "from module_e import LudiCalibrator; print('✅ Module E OK')"
python3 -c "from module_f import LudiReporter; print('✅ Module F OK')"
python3 -c "from module_g import LudiRefEngine; print('✅ Module G OK')"
python3 -c "from module_h_historian import LudiHistorian; print('✅ Module H OK')"
python3 -c "from module_x_scenario import ScenarioBuilder; print('✅ Module X OK')"

# Test key scripts
python3 -c "import scripts.sync_stagger_stats; print('✅ Stagger stats OK')"
python3 -c "import scripts.sync_stint_profiles; print('✅ Stint profiles OK')"
python3 -c "import scripts.check_slate; print('✅ check_slate OK')"
```

---

## Pattern 2 — Database Integrity Test

Always run before and after any migration or schema change.

```bash
# Full schema validation — checks all required tables exist
python3 scripts/validate_schema.py --verbose

# Check canonical ID coverage
python3 scripts/validate_canonical_ids.py --warn-threshold 100 -v

# Quick SQLite integrity check
python3 -c "
import sqlite3
conn = sqlite3.connect('ludi.db')
result = conn.execute('PRAGMA integrity_check;').fetchone()[0]
print(f'DB integrity: {result}')  # Should print 'ok'
conn.close()
"

# Table freshness spot-check
python3 -c "
import sqlite3
conn = sqlite3.connect('ludi.db')
c = conn.cursor()
tables = ['player_game_logs', 'rotation_profiles', 'nba_calendar', 'team_lineups']
for t in tables:
    try:
        c.execute(f'SELECT COUNT(*), MAX(synced_at) FROM {t}')
        count, last = c.fetchone()
        print(f'{t}: {count} rows, last synced {last}')
    except Exception as e:
        print(f'{t}: ERROR — {e}')
conn.close()
"
```

---

## Pattern 3 — Library Parameter Existence Test

Run this **after any `requirements.txt` update** that touches nba_api or other libraries with keyword-arg constructors.

```bash
# Verify parameter names haven't changed after a library update
python3 -c "
from nba_api.stats.endpoints import leaguedashlineups
import inspect

sig = inspect.signature(leaguedashlineups.LeagueDashLineups.__init__)
params = list(sig.parameters.keys())

# Check parameters we rely on
required_params = ['league_id_nullable', 'season', 'date_from_nullable', 'date_to_nullable']
for p in required_params:
    status = '✅' if p in params else '❌ MISSING'
    print(f'{status} {p}')

# Check old name isn't reappearing
old_params = ['league_id']  # was renamed to league_id_nullable
for p in old_params:
    if p in params:
        print(f'⚠️ Old param re-appeared: {p} — check sync_wowy_hybrid.py')
"
```

**General template for any class:**
```python
from some_library import SomeClass
import inspect

sig = inspect.signature(SomeClass.__init__)
print(list(sig.parameters.keys()))
# Compare against your usage in the codebase
```

**Real incident:** `sync_wowy_hybrid.py` used `league_id="00"` which worked in an older nba_api version but was renamed to `league_id_nullable`. The script failed silently for weeks until discovered during the Feb 19 audit.

---

## Pattern 4 — Function Return Signature Test

Before committing any change to a function's return tuple, verify all callers are updated.

```bash
# Find all places that unpack generate_report()'s return value
grep -rn "generate_report\|= self\.reporter\." --include="*.py" .

# Check specifically for 2-value unpacking (old signature)
grep -rn ", image_path = .*generate_report\|briefing, image = " --include="*.py" .

# Programmatic check: how many values does the function return?
python3 -c "
from module_f import LudiReporter
import inspect
src = inspect.getsource(LudiReporter.generate_report)
# Count return statements and their tuple sizes
print(src)
"
```

**Real incident:** `module_f.generate_report()` was updated to return 3 values in commit `bd9cb38` but `main.py` still unpacked 2. Pipeline failed for 4 days. `grep` before commit would have caught it.

---

## Pattern 5 — Workflow Gate Smoke Test

After adding or modifying a `check-slate` gate in any workflow, verify it works both ways.

```bash
# Test: "no games" case → gate should block the main job
# Method: check_slate.py on a known off-day (All-Star break, summer date)
python3 scripts/check_slate.py --date 2026-02-16  # All-Star break
echo "Exit code: $?"  # Should be 2 (no games)

# Test: "games exist" case → gate should allow through
python3 scripts/check_slate.py --date 2026-02-19  # Game day
echo "Exit code: $?"  # Should be 0 (games exist)

# Test: "fail-open" behavior → exception should exit 0, not block pipeline
python3 -c "
import scripts.check_slate as cs
# Temporarily point to non-existent DB
import sys
# Simulate exception → should exit 0 (fail-open), not 2 or 1
"
```

**Manual workflow test:**
1. Go to GitHub → Actions → Daily Production Pipeline
2. Click "Run workflow" → run manually
3. On a no-game day: verify `check-slate` job completes, main `run-production-pipeline` job shows "skipped"
4. On a game day: verify both jobs run

---

## Pattern 6 — API Integration Test (Quota-Safe)

Test API clients using cached responses — don't burn quota on tests.

```python
# Uses cache/nba_api/ directory — reads cached responses if available
# Only makes a live API call if cache is stale or missing
from utils.nba_api_client import NBAAPIClient

client = NBAAPIClient()
# This will use cache/nba_api/ if the file exists
result = client.get_player_splits(player_id=203507, season="2025-26")
assert result is not None, "Player splits returned None"
print(f"✅ NBA API integration OK: {len(result)} split categories")
```

**BDL test (uses file cache):**
```python
from utils.bdl_client import BDLClient
client = BDLClient()
# BDL client caches to cache/bdl/ — quota-safe
players = client.get_players(search="LeBron")
assert len(players) > 0
print(f"✅ BDL API OK: found {len(players)} results for 'LeBron'")
```

**When to use real API vs cache:**
| Test type | Use |
|-----------|-----|
| Unit test / daily local dev | Always use cache — don't burn quota |
| Integration test (verify live data) | Once per week max, not in CI |
| CI/CD workflow | Cache only — real API calls in CI waste quota |

---

## Pattern 7 — CI Health Audit

After any workflow change, verify the CI system is healthy before declaring success.

```bash
# Check recent run outcomes for all workflows
gh run list --limit 20 --json name,conclusion,startedAt \
  --jq '.[] | "\(.conclusion) \(.name) \(.startedAt)"' | sort

# Filter to only failures
gh run list --limit 20 --json name,conclusion,databaseId \
  --jq '[.[] | select(.conclusion == "failure")] | .[] | "\(.databaseId) \(.name)"'

# Check a specific workflow's last 5 runs
gh run list --workflow=data_sync.yml --limit 5 --json conclusion,startedAt \
  --jq '.[] | "\(.conclusion) \(.startedAt)"'
```

**Expected output after a healthy deployment:**
```
success Daily Data Sync
success Daily Production Pipeline
success Daily Referee Sync
skipped Daily Production Pipeline  ← (on a no-game day — this is correct)
```

**Red flags:**
- `failure` for any core workflow more than 2 days in a row
- `success` for a workflow that should have generated data, but the table is stale
- Long gap in workflow runs (runner offline or misconfigured cron)

---

## Pattern 8 — Backtest Validation

Run after any model change (Module C, E, or F) to verify the change doesn't introduce regression.

```bash
# 21-day B2B fatigue backtest
python3 scripts/backtest_fatigue_21day.py --verbose

# 14-day playtype trends backtest
python3 scripts/backtest_playtype_trends_14day.py --verbose
```

**Thresholds for pass/fail:**

| Metric | Pass | Warning | Fail |
|--------|------|---------|------|
| B2B differential | ≤ ±1.5 pts | ±1.5–3.0 pts | > ±3.0 pts |
| Mean projection error (PTS) | ≤ ±1.0 pts | ±1.0–3.0 pts | > ±3.0 pts |
| Hit rate | > 52% | 50–52% | < 50% |

**From the Feb 17, 2026 run:**
```
B2B Differential: +3.07 pts  → ⚠️ WARNING (above ±3.0 threshold)
```
This triggers a drift alert in `weekly_validation.yml` and a Telegram notification. It does NOT automatically revert the model — human review required.

---

## Anti-Patterns

| Anti-Pattern | Risk | Fix |
|-------------|------|-----|
| Testing with live API calls in CI | Burns quota; slows tests | Always use cached responses in CI |
| Not running smoke tests after module rename | Import fails silently in production | Run `python -c "from module import Class"` after every refactor |
| Trusting green CI status without checking step outcomes | Silent failures with `continue-on-error: true` | `gh run view --json jobs --jq` for true step outcomes |
| Not checking parameter names after library update | `TypeError: unexpected keyword argument` in production | `inspect.signature()` after every `requirements.txt` update |
| Running full pipeline as a "test" | Wastes API quota and time | Use `check_slate.py`, `validate_schema.py`, and module smoke tests instead |

---

## Future Skill

**`/test-gen`** — Automated test generation
- Analyzes code and generates smoke tests for all modules
- Creates parameter existence checks based on `requirements.txt` dependencies
- Runs CI audit and formats results
- Generates: test readiness report + recommended edge cases
