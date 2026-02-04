# Database Schema Audit Report
**Date:** February 3, 2026
**Purpose:** Identify mismatches between health monitor queries and actual database schema

---

## Executive Summary

The system health monitor (`scripts/monitor_system_health.py`) is querying columns that don't exist in the actual database schema. This causes SQL errors and prevents health monitoring from functioning.

**Critical Issues Found:** 8 column mismatches across 7 tables

---

## Detailed Findings

### 1. Data Integrity Check (Lines 42-96)

The monitor queries `created_at` and `updated_at` on all tables, but most tables use different timestamp column names.

| Table | Column Queried | Exists? | Actual Column | Type |
|-------|---------------|---------|---------------|------|
| `player_synergy_playtypes` | `created_at` | ❌ NO | `synced_at` | TEXT |
| `player_synergy_playtypes` | `updated_at` | ❌ NO | `synced_at` | TEXT |
| `player_game_tracking` | `created_at` | ❌ NO | `synced_at` | TEXT |
| `player_game_tracking` | `updated_at` | ❌ NO | `synced_at` | TEXT |
| `player_shot_quality` | `created_at` | ❌ NO | `synced_at` | TIMESTAMP |
| `player_shot_quality` | `updated_at` | ❌ NO | `synced_at` | TIMESTAMP |
| `team_lineups` | `updated_at` | ❌ NO | `created_at` | TEXT |
| `referee_profiles` | `created_at` | ❌ NO | `last_updated` | TIMESTAMP |
| `referee_profiles` | `updated_at` | ❌ NO | `last_updated` | TIMESTAMP |
| `games` | `created_at` | ❌ NO | *(no timestamp)* | - |
| `games` | `updated_at` | ❌ NO | *(no timestamp)* | - |

### 2. Model Drift Check (Lines 116-125)

| Table | Column Queried | Exists? | Actual Column | Type |
|-------|---------------|---------|---------------|------|
| `bet_recommendations` | `proj_value` | ❌ NO | `projection` | REAL |
| `bet_recommendations` | `line_over` | ❌ NO | `line` | REAL |
| `bet_recommendations` | `created_at` | ✅ YES | `created_at` | TIMESTAMP |

---

## Impact Assessment

### High Severity
- **Data Integrity Check:** 6 out of 6 tables will fail with "no such column" errors
- **Model Drift Check:** Calculation completely broken due to wrong column names

### Medium Severity
- **Health Reports:** Cannot generate accurate freshness metrics
- **Production Alerts:** False alarms or missed alerts

---

## Recommended Fixes

### Fix Strategy
**Do NOT modify database schema** - Fix the queries to match actual schema

### Timestamp Column Mapping
```python
TIMESTAMP_COLUMNS = {
    'player_synergy_playtypes': 'synced_at',
    'player_game_tracking': 'synced_at',
    'player_shot_quality': 'synced_at',
    'team_lineups': 'created_at',
    'referee_profiles': 'last_updated',
    'games': 'date'  # Use game date as freshness check
}
```

### Column Name Corrections
- `proj_value` → `projection`
- `line_over` → `line`

---

## Files Requiring Changes

1. **scripts/monitor_system_health.py**
   - Lines 42-96: Refactor `check_data_integrity()` with table-specific timestamp columns
   - Lines 116-125: Fix `check_model_drift()` column names

---

## Verification Steps

After fixes:
1. Run: `python scripts/monitor_system_health.py`
2. Expected: No SQL errors
3. Verify: All 6 tables show health status
4. Verify: Model drift calculation works

---

## Additional Notes

**Why This Happened:**
- Database schema evolved over time
- Different sync scripts use different timestamp conventions (`synced_at`, `created_at`, `last_updated`)
- Health monitor was written with assumptions about standardized column names

**Prevention:**
- Add schema validation tests
- Document timestamp column conventions in `database.py`
- Consider adding a "last_activity" view for standardized freshness checks
