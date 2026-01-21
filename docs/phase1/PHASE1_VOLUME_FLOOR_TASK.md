# Phase 1: Volume Floor Implementation Task

**Date:** January 21, 2026  
**Task Owner:** [Agent to be assigned]  
**Priority:** HIGH  
**Estimated Time:** 30-45 minutes  

---

## Mission

Implement a **volume floor** for the Synergy PPP (Points Per Possession) efficiency modifier in Module E to prevent over-projection of low-volume, high-efficiency role players.

---

## Background Context

### The Problem: "Efficiency Paradox"

**Discovered in:** 60-day backtest (Nov 20 - Jan 20, 11,412 player-games)

**Finding:** The PPP efficiency boost showed **neutral to slightly negative impact** on points hit rate (-0.2%).

**Root Cause:** High-PPP players fall into two categories:
1. **High-volume stars** (Curry, Durant) → Efficiency is sustainable ✅
2. **Low-volume role players** (Luke Kornet 1.698 PPP, 4.2 FGA) → Efficiency inflated by limited attempts ❌

**Current behavior:** The system boosts **both equally**, causing over-projection for role players.

**Solution:** Add volume floor — only apply PPP boost if player meets minimum scoring volume.

---

## Research Summary

### Academic/Pro Standards for Volume Thresholds

From research on stat stabilization and NBA leaderboard requirements:

| Metric | Stabilization Point | Source |
|--------|---------------------|--------|
| **3PT%** | 242-750 attempts | Kuder-Richardson reliability studies |
| **NBA Leaderboards** | 300 FGM | NBA.com official rules |
| **General Shooting** | ~200 attempts | Statistical regression analysis |

### Proposed Thresholds

**Volume Floor:** Player must meet **10 FGA/game OR 12 PPG** minimum

**Rationale:**
- **10 FGA/game** ≈ 500 attempts over 50 games → Approaches NBA's 300 FGM threshold
- **12 PPG** ≈ Starter-level scoring output (filters out bench/garbage-time players)
- **Either condition met** = eligible for efficiency boost

---

## Technical Implementation

### File to Modify

**Primary File:** `module_e.py`  
**Function:** `_apply_synergy_ppp_efficiency()` (lines 856-910)  
**Location:** `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/module_e.py`

### Current Code (lines 869-887)

```python
def _apply_synergy_ppp_efficiency(self, calibrated: dict, opponent_abbr: str) -> None:
    """
    Apply Synergy PPP (Points Per Possession) efficiency modifier.
    """
    player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))

    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get player's primary playtypes (freq >= 5%)
        cursor.execute("""
            SELECT playtype, freq_pct, ppp
            FROM player_synergy_playtypes
            WHERE player_name = ? AND season = '2025-26' AND freq_pct >= 5.0
            ORDER BY freq_pct DESC
            LIMIT 4
        """, (player_name,))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return  # No data, no adjustment

        # Calculate weighted PPP
        total_freq = sum(r[1] for r in rows)
        weighted_ppp = sum(r[1] * r[2] for r in rows) / total_freq

        # Compare to league average (1.05 PPP = average NBA efficiency)
        LEAGUE_AVG_PPP = 1.05
        efficiency_ratio = weighted_ppp / LEAGUE_AVG_PPP

        # Cap at ±15% adjustment (avoid over-calibration)
        modifier = max(0.85, min(1.15, efficiency_ratio))

        # Apply to points projection
        self._boost_stat(calibrated, 'proj_pts', modifier)

        # ... rest of function
```

### Required Changes

**Insert BEFORE the Synergy playtype query (after line 872):**

```python
# === NEW: VOLUME FLOOR CHECK ===
# Step 1: Query player's scoring volume (last 60 days)
volume_query = """
    SELECT AVG(pts) as avg_pts, AVG(fga) as avg_fga
    FROM player_game_stats
    WHERE player_name = ? 
    AND game_date >= date('now', '-60 days')
    HAVING COUNT(*) >= 5
"""
cursor.execute(volume_query, (player_name,))
volume_row = cursor.fetchone()

# Step 2: Apply volume floor
MIN_FGA = 10.0
MIN_PTS = 12.0

if not volume_row or (volume_row[0] < MIN_PTS and volume_row[1] < MIN_FGA):
    # Player doesn't meet volume threshold - skip PPP boost
    conn.close()
    return
# === END VOLUME FLOOR CHECK ===

# Continue with existing Synergy playtype query...
```

**Additional Change:** Reduce PPP cap from ±15% to ±12%

```python
# OLD:
modifier = max(0.85, min(1.15, efficiency_ratio))

# NEW:
modifier = max(0.88, min(1.12, efficiency_ratio))
```

---

## Database Reference

### Table: `player_game_stats`

**Schema:**
```sql
CREATE TABLE player_game_stats (
    player_name TEXT,
    game_date TEXT,
    pts REAL,
    fga REAL,
    -- ... other stats
);
```

**Sample Query to Verify Data:**
```sql
SELECT 
    player_name,
    AVG(pts) as avg_pts, 
    AVG(fga) as avg_fga,
    COUNT(*) as games
FROM player_game_stats
WHERE game_date >= date('now', '-60 days')
GROUP BY player_name
HAVING COUNT(*) >= 5
ORDER BY avg_pts DESC
LIMIT 10;
```

---

## Validation & Testing

### Test Suite to Run

**Primary Test Script:** `scripts/test_synergy_calibrations.py`

```bash
cd /Users/flyprice/Desktop/Ludi\ Informatio/Projects/Ludi-Bot
python3 scripts/test_synergy_calibrations.py
```

**Expected Result:** All 4 test suites passing (35 test cases)

### Manual Verification Tests

#### Test 1: Low-Volume Player (Should be FILTERED OUT)

**Player:** Luke Kornet  
**Stats:** 4.2 FGA/game, ~5.5 PPG (2025-26)  
**Expected:** NO PPP boost applied (filtered by volume floor)

**Test Command:**
```python
# In Python REPL:
from module_e import LudiCalibrator
calib = LudiCalibrator()

test_player = {
    'name': 'Luke Kornet',
    'base_pts': 5.5,
    'proj_pts': 25.0,
    'notes': ''
}

# Before: Would get +14% PPP boost (1.698 PPP)
# After: Should get NO adjustment (filtered by volume floor)
calib._apply_synergy_ppp_efficiency(test_player, 'BOS')
print(test_player['proj_pts'])  # Should still be 25.0 (no change)
print(test_player['notes'])      # Should NOT contain "Efficient" or PPP note
```

#### Test 2: High-Volume Star (Should STILL get boost)

**Player:** LeBron James  
**Stats:** 18+ FGA/game, 23+ PPG  
**Expected:** PPP boost STILL applies (passes volume floor)

**Test Command:**
```python
test_player = {
    'name': 'LeBron James',
    'base_pts': 23.0,
    'proj_pts': 25.0,
    'notes': ''
}

# Should still get PPP adjustment (passes volume floor)
calib._apply_synergy_ppp_efficiency(test_player, 'BOS')
print(test_player['proj_pts'])  # Should be modified (25.0 * modifier)
print(test_player['notes'])      # Should contain PPP adjustment note
```

#### Test 3: Mid-Volume Player (Boundary Test)

**Player:** Cam Thomas  
**Stats:** ~10 FGA/game, ~24 PPG  
**Expected:** PPP boost applies (meets volume floor via PPG)

---

## Success Criteria

✅ **Code Quality:**
- [ ] Volume floor logic added before Synergy query
- [ ] PPP cap reduced from ±15% to ±12%
- [ ] Error handling preserved (try/except with silent failure)
- [ ] Database connection properly closed

✅ **Testing:**
- [ ] `test_synergy_calibrations.py` passes (4/4 suites)
- [ ] Luke Kornet (low-volume) NO LONGER gets PPP boost
- [ ] LeBron James (high-volume) STILL gets PPP boost
- [ ] No regression on other calibration functions

✅ **Documentation:**
- [ ] Add inline comment explaining volume floor logic
- [ ] Update function docstring with volume floor note

---

## Reference Documents

| Document | Purpose | Location |
|----------|---------|----------|
| **PHASE1_COMPLETION_REPORT.md** | Phase 1 validation results, backtest findings | `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/` |
| **ARCHETYPE_SYNERGY_UPGRADE_PLAN.md** | Overall Phase 1 context and research | `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/` |
| **implementation_plan.md** | Detailed implementation plan with research | `/Users/flyprice/.gemini/antigravity/brain/e98c2994-a6ad-438c-914a-b9c231510d16/` |
| **module_e.py** | Target file for modifications | `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/` |
| **CLAUDE.md** | Project documentation (context only) | `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/` |

---

## Key Constraints

1. **Silent Failures:** Maintain existing try/except pattern — function should fail gracefully if volume data unavailable
2. **Backward Compatibility:** Function must work even if `player_game_stats` table is missing
3. **Minimal Invasiveness:** Only modify `_apply_synergy_ppp_efficiency()` — do not touch other calibration functions
4. **Database Connection:** Always close connection, even on early return

---

## Rollback Plan

If tests fail or unexpected behavior occurs:

1. **Revert Changes:** Use git to restore `module_e.py` to previous state
2. **Re-run Tests:** Confirm backtest results return to baseline
3. **Report Issues:** Document specific failure mode and player examples

---

## Deliverables

Upon completion, provide:

1. **Modified Code:** Updated `module_e.py` with volume floor implemented
2. **Test Results:** Output from `test_synergy_calibrations.py`
3. **Manual Verification:** Results from Luke Kornet and LeBron James tests
4. **Confirmation:** Statement that all success criteria met

---

## Questions?

If you encounter issues:
- **Missing `player_game_stats` table?** Check if table exists: `sqlite3 ludi.db ".tables"`
- **Player name mismatch?** Try canonical name resolution (PlayerIDResolver)
- **Need sample data?** Query existing data to verify date ranges and player names

**Good luck! The fix should take about 30-45 minutes including testing.**
