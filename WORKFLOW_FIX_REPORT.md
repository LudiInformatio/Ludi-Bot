# Workflow Fix Report

**Date:** February 4, 2026
**Status:** COMPLETE

## Summary

Fixed 4 GitHub Actions workflow failures that occurred overnight. All fixes have been implemented, tested, and verified.

---

## Fixes Applied

### Fix 1: sync_wowy_backfill.py Import Error (HIGH)

**Problem:** Lines 30-34 imported non-existent functions from `utils/browser_utils.py`:
- `get_playwright_browser` - DOES NOT EXIST
- `smart_wait_for_selector` - DOES NOT EXIST
- `handle_pagination_dropdown` - DOES NOT EXIST

**Solution:**
1. Changed imports to use existing functions: `simulate_human_interaction`, `close_popups`, `wait_for_selector_safe`
2. Added inline `handle_pagination()` function based on `sync_browser_backfill.py` pattern
3. Replaced `get_playwright_browser()` call with inline Playwright browser setup including stealth configuration

**Files Modified:**
- `scripts/sync_wowy_backfill.py` (lines 30, 142-171, 331-370)

**Logic:** The script was referencing functions that were never added to `browser_utils.py`. The working script `sync_browser_backfill.py` already had the correct pattern - inlining browser setup and pagination handling rather than relying on centralized utilities.

---

### Fix 2: data_sync.yml Index Migration (HIGH)

**Problem:** Runner's database was created before the `idx_referee_daily_unique` index was added to `database.py`, causing schema validation to fail.

**Solution:** Added a new step "Ensure database indexes exist" that runs BEFORE schema validation. This step creates the index if it doesn't exist using `CREATE UNIQUE INDEX IF NOT EXISTS`.

**Files Modified:**
- `.github/workflows/data_sync.yml` (added step after line 36)

**Logic:** The index was added to `database.py` but the self-hosted runner's existing `ludi.db` predates that change. Adding a migration step ensures the index exists regardless of when the database was created.

---

### Fix 3: bet_logger.py Null Division (MEDIUM)

**Problem:** Line 455-456 performed division without checking if `profit_loss` was NULL, causing `TypeError: unsupported operand type(s) for /: 'NoneType' and 'float'`

**Solution:** Added null check to the ROI calculation:
```python
summary_data['roi'] = (
    summary_data['profit_loss'] / summary_data['total_units']
    if summary_data['total_units'] > 0 and summary_data['profit_loss'] is not None
    else None
)
```

**Files Modified:**
- `utils/bet_logger.py` (lines 455-459)

**Logic:** When bets are pending (not yet settled), `profit_loss` is NULL in the database. The original code only checked if `total_units > 0` but not if `profit_loss` was actually a number.

---

### Fix 4: weekly_validation.yml Log Check (LOW)

**Problem:** Two issues:
1. Filename mismatch: Line 97 checked for `playtype_trends_14day_...` but line 99 tried to read `playtype_trends_...` (missing `14day_`)
2. No fallback when log file doesn't exist

**Solution:**
1. Fixed the filename in the `tail` command to match the existence check
2. Added an `else` clause with a "not available" message

**Files Modified:**
- `.github/workflows/weekly_validation.yml` (lines 97-103)

**Logic:** The backtest script writes to `playtype_trends_14day_YYYYMMDD.log` but the report generation was looking for a different filename pattern. This caused the `tail` command to fail even when the backtest had run successfully.

---

## Testing Results

| Test | Result |
|------|--------|
| Python syntax validation | ✅ Passed |
| Schema validation | ✅ Passed (all tables/indexes verified) |
| Bet settlement (null division) | ✅ No TypeError |
| sync_wowy_backfill.py imports | ✅ Passed |
| YAML syntax validation | ✅ Both files valid |

---

## Issues Encountered

None. All fixes were straightforward based on the diagnostic information provided.

---

## Files Modified Summary

| File | Lines Changed | Type of Change |
|------|---------------|----------------|
| `scripts/sync_wowy_backfill.py` | 30, 142-171, 331-370 | Import fix + browser setup |
| `.github/workflows/data_sync.yml` | 37-47 (new step) | Index migration |
| `utils/bet_logger.py` | 455-459 | Null check |
| `.github/workflows/weekly_validation.yml` | 97-103 | Filename fix + else clause |

---

## Commit Ready

All changes are ready to be committed with message:
```
fix(workflows): resolve multiple GitHub Actions failures

- Fix sync_wowy_backfill.py import error (use existing browser_utils functions)
- Add database index migration step to data_sync.yml
- Fix null-safe division in bet_logger.py calculate_daily_summary()
- Add log file existence check in weekly_validation.yml

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```
