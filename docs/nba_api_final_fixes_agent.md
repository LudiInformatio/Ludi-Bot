# nba_api Final Fixes - Missing league_id Parameters

## Role
You are an **API Integration Specialist** completing the final 2 nba_api updates that were missed in the initial pass.

## Context
The main `utils/nba_api_client.py` wrapper was updated with `league_id="00"` parameters, but **2 active scripts** make direct nba_api endpoint calls and were missed. These scripts run in production workflows and need the same fix.

**Why this matters:** Starting with the 2023-24 NBA season, the NBA.com API requires explicit `league_id` values. Without this parameter, these scripts will return **empty datasets** for current season data.

## Task
Add `league_id="00"` parameter to 2 direct nba_api endpoint calls.

---

## File 1: scripts/sync_wowy_hybrid.py

**Location:** Line 71

**Current Code:**
```python
lineups = leaguedashlineups.LeagueDashLineups(
    season='2025-26',
    season_type_all_star='Regular Season',
    measure_type_detailed_defense='Advanced',
    group_quantity=5,
    date_from_nullable=nba_date_str,
    date_to_nullable=nba_date_str,
    headers=HEADERS,
    timeout=REQUEST_TIMEOUT
)
```

**Updated Code:**
```python
lineups = leaguedashlineups.LeagueDashLineups(
    season='2025-26',
    season_type_all_star='Regular Season',
    measure_type_detailed_defense='Advanced',
    group_quantity=5,
    league_id="00",  # ✅ NBA league ID (required for 2023-24+)
    date_from_nullable=nba_date_str,
    date_to_nullable=nba_date_str,
    headers=HEADERS,
    timeout=REQUEST_TIMEOUT
)
```

**What this script does:** Syncs WOWY (With Or Without You) lineup data
**Used by:** `.github/workflows/data_sync.yml` (runs daily at 5 AM EST)
**Critical:** Yes - this is production data pipeline

---

## File 2: initialize_season.py

**Location:** Line 53

**Current Code:**
```python
logs = leaguegamelog.LeagueGameLog(
    season=target_season,
    player_or_team_abbreviation='P',
    headers=headers,
    timeout=120
).get_data_frames()[0]
```

**Updated Code:**
```python
logs = leaguegamelog.LeagueGameLog(
    season=target_season,
    player_or_team_abbreviation='P',
    league_id="00",  # ✅ NBA league ID (required for 2023-24+)
    headers=headers,
    timeout=120
).get_data_frames()[0]
```

**What this script does:** Initializes full season game logs at start of season
**Used by:** Manual execution (season setup)
**Critical:** Medium - used once per season but important for fresh installs

---

## Implementation Steps

### Step 1: Update sync_wowy_hybrid.py
1. Open `scripts/sync_wowy_hybrid.py`
2. Navigate to line 71 (inside `sync_via_api` function)
3. Add `league_id="00",` after `group_quantity=5,`
4. Ensure proper comma placement and indentation

### Step 2: Update initialize_season.py
1. Open `initialize_season.py`
2. Navigate to line 53 (inside `fetch_season_game_logs` function)
3. Add `league_id="00",` after `player_or_team_abbreviation='P',`
4. Ensure proper comma placement and indentation

### Step 3: Verify Changes
Run these commands to verify the fixes:

```bash
# 1. Verify both files have league_id parameter
grep -n 'league_id="00"' scripts/sync_wowy_hybrid.py
grep -n 'league_id="00"' initialize_season.py

# 2. Check syntax (should import without errors)
python -c "import sys; sys.path.insert(0, '.'); from scripts.sync_wowy_hybrid import sync_via_api; print('✅ sync_wowy_hybrid OK')"
python -c "import initialize_season; print('✅ initialize_season OK')"

# 3. Count total league_id occurrences across all files (should be 8+)
grep -r 'league_id="00"' --include="*.py" --exclude-dir=.venv --exclude-dir=archives | wc -l
```

---

## Verification Checklist

After implementation, confirm:

- [ ] `scripts/sync_wowy_hybrid.py` line 71 has `league_id="00"`
- [ ] `initialize_season.py` line 53 has `league_id="00"`
- [ ] Both files import without syntax errors
- [ ] Total `league_id="00"` count is 8+ across codebase (utils + scripts)
- [ ] No other active scripts use nba_api endpoints directly

---

## Success Report Format

```markdown
# nba_api Final Fixes - Completion Report

## Files Updated ✅
1. scripts/sync_wowy_hybrid.py (line 71) - Added league_id to LeagueDashLineups
2. initialize_season.py (line 53) - Added league_id to LeagueGameLog

## Verification Results ✅
- ✅ sync_wowy_hybrid.py has league_id parameter
- ✅ initialize_season.py has league_id parameter
- ✅ Both files import successfully (no syntax errors)
- ✅ Total league_id="00" occurrences: X (expected 8+)

## Impact
- WOWY sync will now return data for 2025-26 season (prevents empty datasets)
- Season initialization will work correctly for future seasons
- All nba_api endpoint calls now comply with 2023-24+ API requirements

## Next Steps
- Deploy to production (no breaking changes)
- Monitor data_sync.yml workflow on Feb 19 (first game day back)
- Verify WOWY data populates correctly after daily sync
```

---

## Error Handling

If you encounter issues:

**Import Error:** Check Python syntax (commas, indentation)
**AttributeError:** Verify nba_api version is 1.11.3 (`pip show nba_api`)
**Empty Dataset:** Confirm league_id is string "00" not integer 0

---

## Additional Context

**Why "00"?** NBA league ID codes:
- "00" = NBA
- "10" = WNBA
- "20" = G League

**Other endpoints that need league_id** (already fixed in utils/nba_api_client.py):
- PlayerDashboardByShootingSplits
- PlayerDashPtShots
- PlayerDashPtShotDefend
- PlayerVsPlayer
- PlayerDashPtReb
- PlayerDashPtPass
- PlayByPlayV3

**Reference:** https://github.com/swar/nba_api/issues (2023-24 season breaking change)

---

## Estimated Time
- Implementation: 2 minutes
- Verification: 1 minute
- **Total: 3 minutes**

---

**Priority:** HIGH (production workflows depend on these scripts)
**Complexity:** LOW (simple parameter addition)
**Risk:** MINIMAL (non-breaking change, only adds required parameter)
