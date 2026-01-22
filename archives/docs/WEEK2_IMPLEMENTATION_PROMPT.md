# Week 2: Archetype Implementation - Code Integration

**Date:** January 20, 2026 @ 01:45 AM EST  
**Phase:** Code Implementation (Module E Integration)  
**Context:** Week 1 Complete - Hybrid approach validated, ready for production

---

## Your Mission

Integrate the **validated hybrid archetype system** into Module E (Calibrator). Week 1 successfully eliminated tag pollution using position filtering + priority scoring. Now you need to implement this system in the production betting pipeline.

**Goal:** Replace the current simple archetype system with the sophisticated secondary playtype system that will improve betting edge calculations.

---

## What Week 1 Accomplished ✅

### Problem Solved
- **Tag Pollution Eliminated:** Reduced from 4+ tags per big man to maximum 2 tags per player
- **Position Logic:** Guards create, wings cut/shoot, bigs finish at rim
- **Data Validation:** 93% tracking data coverage, thresholds calibrated on 60 days of data

### Files Created (Your References)
- `config/playtype_thresholds.json` (v1.2) - **Final validated thresholds**
- `scripts/test_playtype_thresholds_hybrid.py` - **Reference implementation** 
- `scripts/sync_player_positions.py` - Position data sync utility
- `docs/WEEK1_HYBRID_FINAL_REPORT.md` - Complete results analysis

### Key Results
- **Coverage:** 5 of 8 playtypes in target ranges (10-25%)
- **Max tags:** 2 per player (down from 4)
- **Position filtering:** Guards blocked from rim roles, bigs blocked from creation
- **Priority scoring:** Top 2 matches only, prevents dilution

---

## Week 2 Implementation Tasks

### Task 1: Update Module E Schema
**Goal:** Add secondary playtype support to Module E's player data structure.

**Current State (module_e.py lines 20-40):**
```python
# Current primary archetypes only
ARCHETYPE_PROFILES = {
    'STRETCH_BIG': {...},
    'SLASHER': {...},
    'SNIPER': {...},
    # ... 8 more
}
```

**Required Changes:**
1. **Add secondary playtype constants** from `config/playtype_thresholds.json`
2. **Update `_assign_archetype()` method** to include secondary playtypes
3. **Store both primary + secondary** in player packet

**File Locations:**
- `module_e.py` lines 20-90 (archetype definitions)
- `module_e.py` lines 150-220 (assignment logic)

---

### Task 2: Implement Position-Based Filtering
**Goal:** Prevent Guards from getting rim-based tags, prevent Bigs from getting creation tags.

**Reference Implementation** (from `test_playtype_thresholds_hybrid.py` lines 45-85):
```python
POSITION_ELIGIBILITY = {
    'G': ['ISO_SCORER', 'P&R_HANDLER', 'SPOT_UP', 'TRANSITION'],
    'G-F': ['ISO_SCORER', 'P&R_HANDLER', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION'],
    'F': ['ISO_SCORER', 'P&R_HANDLER', 'P&R_ROLL_MAN', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION'],
    'F-C': ['P&R_ROLL_MAN', 'SPOT_UP', 'OFF_BALL_CUTTER', 'TRANSITION', 'PUTBACK', 'POST_UP'],
    'C': ['P&R_ROLL_MAN', 'OFF_BALL_CUTTER', 'PUTBACK', 'POST_UP', 'SPOT_UP', 'TRANSITION']
}

def get_eligible_playtypes(position: str) -> List[str]:
    """Get list of playtypes this position can qualify for."""
    return POSITION_ELIGIBILITY.get(position, [])
```

**Integration Point:**
- Add to `module_e.py` as new method: `_get_eligible_playtypes()`
- Call from `calibrate_player()` before running playtype checks

---

### Task 3: Implement Priority Scoring System
**Goal:** Select only the top 1-2 playtype matches per player using data-driven scores.

**Reference Logic** (from `test_playtype_thresholds_hybrid.py` lines 180-250):
```python
def calculate_match_score(player_data: dict, playtype: str) -> float:
    """Calculate how well player matches this playtype (0.0 to 1.0+)."""
    thresholds = THRESHOLDS[playtype]
    criteria_met = 0
    total_criteria = len(thresholds)
    
    # Count criteria met (example for ISO_SCORER)
    if playtype == 'ISO_SCORER':
        if player_data.get('drives', 0) > thresholds['drives_per_game']:
            criteria_met += 1
        if player_data.get('pull_up_fga', 0) > thresholds['pull_up_fga_per_game']:
            criteria_met += 1
        if player_data.get('pull_up_fga', 0) > player_data.get('catch_shoot_fga', 0) * 1.5:
            criteria_met += 1
    
    base_score = criteria_met / total_criteria
    
    # Apply position bonus
    bonus = get_position_bonus(playtype, player_data['position'])
    
    return base_score + bonus

def select_top_playtypes(player_data: dict) -> tuple:
    """Return (primary_playtype, secondary_playtype) or (primary, None)."""
    eligible = get_eligible_playtypes(player_data['position'])
    scores = {pt: calculate_match_score(player_data, pt) for pt in eligible}
    
    # Filter by thresholds
    qualified = {pt: score for pt, score in scores.items() 
                if score >= PRIMARY_THRESHOLD}  # 0.66
    
    if not qualified:
        return None, None
    
    # Sort by score, take top 2
    sorted_matches = sorted(qualified.items(), key=lambda x: x[1], reverse=True)
    
    primary = sorted_matches[0][0]
    secondary = sorted_matches[1][0] if len(sorted_matches) > 1 and sorted_matches[1][1] >= SECONDARY_THRESHOLD else None
    
    return primary, secondary
```

**Integration Point:**
- Add methods to `module_e.py`: `_calculate_playtype_score()`, `_select_top_playtypes()`
- Update `calibrate_player()` to call these methods
- Store results in player packet: `player_packet['secondary_playtypes'] = [primary, secondary]`

---

### Task 4: Add Tracking Data Integration
**Goal:** Feed tracking stats from database into playtype scoring system.

**Required Data Sources:**
```python
# From player_game_tracking table (last 20 games)
tracking_stats = {
    'drives': avg_drives_per_game,
    'catch_shoot_fga': avg_catch_shoot_fga,
    'catch_shoot_pct': catch_shoot_percentage,
    'pull_up_fga': avg_pull_up_fga,
    'speed': avg_speed_mph,
    'distance': avg_distance_miles
}

# From player_shot_quality table
shot_stats = {
    'rim_freq': rim_frequency,  # % of shots at rim
    'corner_3_freq': corner_3_frequency
}
```

**Implementation:**
1. **Add method** `_get_tracking_stats(player_id, days=20)` to query database
2. **Update `calibrate_player()`** to call this method
3. **Merge tracking data** into player stats for playtype scoring

**SQL Queries Needed:**
```sql
-- Get tracking averages (last 20 games)
SELECT 
    AVG(drives) as avg_drives,
    AVG(catch_shoot_fga) as avg_cs_fga,
    AVG(CAST(catch_shoot_fgm AS FLOAT) / NULLIF(catch_shoot_fga, 0)) as cs_pct,
    AVG(pull_up_fga) as avg_pu_fga,
    AVG(speed) as avg_speed,
    AVG(distance) as avg_distance
FROM player_game_tracking
WHERE player_name = ? AND game_date >= date('now', '-20 days')

-- Get shot quality (season)
SELECT rim_freq, corner_3_freq 
FROM player_shot_quality 
WHERE player_id = ? AND season = '2025-26'
```

---

### Task 5: Update Matchup Modifiers
**Goal:** Create new matchup multipliers based on secondary playtypes vs defensive schemes.

**Current System (lines 92-167 in module_e.py):**
```python
# Expand this table with secondary playtypes
MATCHUP_MODIFIERS = {
    # Existing primary archetype matchups...
    
    # NEW: Secondary playtype matchups
    ('SPOT_UP', 'PAINT_PACK'): 1.15,     # 3PM boost vs rim protection
    ('OFF_BALL_CUTTER', 'BLITZ'): 1.20,  # Rim FG% boost vs aggressive D
    ('ISO_SCORER', 'SWITCH'): 1.10,      # Points boost vs switching
    ('P&R_HANDLER', 'FUNNEL'): 1.12,     # Assists boost vs help D
    ('P&R_ROLL_MAN', 'PERIMETER'): 1.25, # Rim shots vs small ball
    ('TRANSITION', 'SLOW_PACE'): 1.15,    # Fast break vs slow teams
    ('PUTBACK', 'WEAK_REBOUNDING'): 1.30, # OREB vs poor rebounding teams
    ('POST_UP', 'SMALL_BALL'): 1.20      # Post scoring vs undersized D
}
```

**Integration:**
- **Add constants** to module_e.py
- **Update `apply_matchup_modifiers()`** to check secondary playtypes
- **Apply multipliers** to relevant stat categories (PTS, AST, REB, 3PM, etc.)

---

### Task 6: Update Bet Briefing Integration
**Goal:** Show secondary playtypes in betting reports for context.

**Current Format** (module_f.py):
```
🏷️ STRETCH_BIG | vs_PAINT_PACK
```

**New Format:**
```
🏷️ STRETCH_BIG + SPOT_UP | vs_PAINT_PACK
```

**Implementation:**
- **Update `utils/tag_classifier.py`** to include secondary playtypes
- **Modify briefing formatting** to show "PRIMARY + SECONDARY" when both exist
- **Keep existing logic** for market tags (CORRELATED_SGP, etc.)

---

### Task 7: Create Integration Tests
**Goal:** Verify the new system works end-to-end without breaking existing functionality.

**Test Cases:**
1. **Guards get guard tags only:** Luka Doncic should get ISO_SCORER + P&R_HANDLER, NOT P&R_ROLL_MAN
2. **Centers get big man tags:** Clint Capela should get P&R_ROLL_MAN + PUTBACK, NOT ISO_SCORER
3. **Forwards get hybrid tags:** Jayson Tatum should get ISO_SCORER + SPOT_UP (versatile wing)
4. **Max 2 tags per player:** No player should have more than 2 secondary playtypes
5. **Existing pipeline works:** Main.py should run without errors, generate bets with new tags

**Test Script Template:**
```python
# scripts/test_module_e_integration.py
from module_e import LudiCalibrator

calibrator = LudiCalibrator()

# Test known players
test_players = [
    {'name': 'Luka Doncic', 'position': 'G', 'expected_tags': ['ISO_SCORER', 'P&R_HANDLER']},
    {'name': 'Clint Capela', 'position': 'C', 'expected_tags': ['P&R_ROLL_MAN', 'PUTBACK']},
    {'name': 'Jayson Tatum', 'position': 'F', 'expected_tags': ['ISO_SCORER', 'SPOT_UP']}
]

for player in test_players:
    packet = calibrator.calibrate_player(player)
    print(f"{player['name']}: {packet.get('secondary_playtypes', [])}")
```

---

## Implementation Checklist

- [ ] **Schema Update:** Add secondary playtype constants to module_e.py
- [ ] **Position Filtering:** Add `_get_eligible_playtypes()` method with position restrictions
- [ ] **Priority Scoring:** Add `_calculate_playtype_score()` and `_select_top_playtypes()` methods
- [ ] **Tracking Integration:** Add `_get_tracking_stats()` method with database queries
- [ ] **Matchup Expansion:** Add 8 new secondary playtype vs defense matchups
- [ ] **Briefing Update:** Update tag display format to show "PRIMARY + SECONDARY"
- [ ] **Integration Test:** Create test script to validate known player assignments
- [ ] **End-to-End Test:** Run main.py with new system, verify bets generate successfully

---

## Key Files to Modify

| File | Changes | Lines | Description |
|------|---------|-------|-------------|
| **`module_e.py`** | Major update | 20-90, 150-220 | Add secondary playtype system |
| **`utils/tag_classifier.py`** | Minor update | 34-40, 130-140 | Update tag formatting |
| **`config/playtype_thresholds.json`** | Reference only | N/A | Contains validated thresholds |
| **`scripts/test_module_e_integration.py`** | New file | N/A | Integration testing |

---

## Success Criteria

### Functional Requirements
- ✅ Position filtering prevents impossible assignments (Guards don't get PUTBACK)
- ✅ Priority scoring selects meaningful matches only (max 2 tags per player)
- ✅ Tracking data integration works (database queries successful)
- ✅ Matchup modifiers apply correctly (SPOT_UP vs PAINT_PACK = 1.15x 3PM)

### System Requirements
- ✅ Module E runs without errors
- ✅ Main.py pipeline generates bets successfully
- ✅ Briefing shows new tag format
- ✅ No performance regression (< 10% slower than current system)

---

## Reference Materials

### Week 1 Results (MANDATORY READING)
- **`docs/WEEK1_HYBRID_FINAL_REPORT.md`** - Complete validation results
- **`scripts/test_playtype_thresholds_hybrid.py`** - Reference implementation code
- **`config/playtype_thresholds.json`** - Final validated thresholds (v1.2)

### Current System Context
- **`ARCHETYPE_SYNERGY_UPGRADE_PLAN.md`** - Original 4-week plan
- **`CLAUDE.md` lines 97-142** - Project context for other agents
- **`module_e.py`** - Current calibrator implementation

---

## Questions?

If you encounter issues:
1. **Check Week 1 validation results** in `WEEK1_HYBRID_FINAL_REPORT.md`
2. **Use the reference implementation** in `test_playtype_thresholds_hybrid.py`
3. **Test incrementally** - don't implement everything at once
4. **Validate against known players** - Luka should be ISO_SCORER, Capela should be P&R_ROLL_MAN

**Remember:** Week 1 proved the approach works. Your job is to translate the validated logic into the production betting pipeline.

---

## Implementation Strategy

**Phase 1 (Day 1-2):** Core functionality
1. Add secondary playtype constants and position filtering
2. Implement priority scoring system
3. Basic integration test

**Phase 2 (Day 3-4):** Data integration  
1. Add tracking data queries
2. Update matchup modifiers
3. Update briefing format

**Phase 3 (Day 5):** Validation & Polish
1. End-to-end testing
2. Performance optimization
3. Documentation update

**The hybrid approach eliminated tag pollution and is ready for production. Execute with confidence!**