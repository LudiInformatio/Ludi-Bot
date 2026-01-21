# Phase 1: Shot Quality Enhancements Task

**Date:** January 21, 2026  
**Task Owner:** [Agent to be assigned]  
**Priority:** HIGH (P3)  
**Estimated Time:** 25-30 minutes  

---

## Mission

Implement two **ShotQualityBets-inspired enhancements** to Module E calibration:
1. **FT% → Shooting Touch** - Use free throw % to predict 3PM ability
2. **Shot Creation Split** - Adjust 3PM based on catch-and-shoot vs pull-up ratio

---

## Research Background

### From ShotQualityBets Methodology

> "Free throw ability indicates shooting touch, which improves jump shot predictions."

> "Catch-and-shoot threes are made ~4% more often than off-the-dribble threes."

**Key Insight:** FT% is more stable than 3PT% (less sample variance). Elite FT shooters rarely regress as jump shooters.

---

## Technical Implementation

### File to Modify

**Primary File:** `module_e.py`  
**Location:** `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/module_e.py`  
**Target Area:** `calibrate_player()` method, after the existing shot quality section (~line 815)

---

### Enhancement 1: FT% → Shooting Touch Indicator

**Insert after line ~848 (after existing shot quality logic, before nuance checks):**

```python
# === NEW: FT% SHOOTING TOUCH INDICATOR ===
# Research: Free throw ability indicates shooting touch (ShotQualityBets)
# Elite FT shooters (>85%) rarely regress as jump shooters

ft_pct = calibrated.get('base_ft_pct', 0)

if ft_pct > 0.85:
    # Elite FT shooter = elite shooting touch → boost 3PM
    self._boost_stat(calibrated, 'proj_3pm', 1.05)
    calibrated['notes'] += " | Elite Touch"
    self._log_adjustment(player_name, 'FT_TOUCH', 1.05, 
        f"Elite FT: {ft_pct:.1%}")
elif ft_pct < 0.65 and ft_pct > 0:
    # Poor FT% = poor touch → regress 3PT expectations
    self._boost_stat(calibrated, 'proj_3pm', 0.95)
    calibrated['notes'] += " | Poor Touch"
    self._log_adjustment(player_name, 'FT_TOUCH', 0.95, 
        f"Poor FT: {ft_pct:.1%}")
# === END FT% SHOOTING TOUCH ===
```

**Thresholds:**
- **>85% FT** → +5% 3PM boost (elite touch)
- **<65% FT** → -5% 3PM penalty (poor touch)
- **65-85% FT** → No adjustment (average range)

---

### Enhancement 2: Shot Creation Split (Catch-and-Shoot vs Pull-Up)

**Insert after FT% logic:**

```python
# === NEW: SHOT CREATION SPLIT ===
# Research: Off-dribble 3s made ~4% less often than catch-and-shoot (ShotQualityBets)
# Use tracking data to adjust expectations based on shot creation type

if tracking_data:
    cs_fga = tracking_data.get('avg_cs_fga', 0)
    pu_fga = tracking_data.get('avg_pu_fga', 0)
    
    if cs_fga > 0 and pu_fga > 0:
        total_3s = cs_fga + pu_fga
        shot_creation_ratio = pu_fga / total_3s
        
        if shot_creation_ratio > 0.65:
            # Pull-up dominant = off-dribble shooter (harder shots)
            self._boost_stat(calibrated, 'proj_3pm', 0.97)
            calibrated['notes'] += " | Off-Dribble 3s"
            self._log_adjustment(player_name, 'SHOT_CREATION', 0.97, 
                f"Pull-up: {shot_creation_ratio:.0%} of 3s")
        elif shot_creation_ratio < 0.25:
            # Catch-and-shoot dominant = easier shots
            self._boost_stat(calibrated, 'proj_3pm', 1.03)
            calibrated['notes'] += " | Spot-Up 3s"
            self._log_adjustment(player_name, 'SHOT_CREATION', 1.03, 
                f"Catch-shoot: {1-shot_creation_ratio:.0%} of 3s")
# === END SHOT CREATION SPLIT ===
```

**Thresholds:**
- **>65% pull-up** → -3% 3PM (harder shot selection)
- **<25% pull-up** → +3% 3PM (easier catch-and-shoot)
- **25-65%** → No adjustment (balanced)

---

## Data Requirements

### FT% Data

**Source:** Already available in `base_ft_pct` field from player base stats

**Verify with:**
```sql
SELECT player_name, ft_pct 
FROM player_season_stats 
WHERE season = '2025-26' 
ORDER BY ft_pct DESC 
LIMIT 10;
```

### Tracking Data (Shot Creation)

**Source:** Already fetched in `_get_tracking_stats()` method

**Fields used:**
- `avg_cs_fga` - Catch-and-shoot 3PA per game
- `avg_pu_fga` - Pull-up 3PA per game

---

## Testing & Verification

### Test Script

```python
#!/usr/bin/env python3
"""Test FT% and Shot Creation enhancements."""
import sys
sys.path.insert(0, '.')

from module_e import LudiCalibrator

def test_shot_quality_enhancements():
    print("=" * 60)
    print("Testing Shot Quality Enhancements")
    print("=" * 60)
    
    calib = LudiCalibrator(debug_log=True)
    
    # Test 1: Elite FT shooter
    test_elite = {
        'name': 'Stephen Curry',
        'base_ft_pct': 0.92,
        'proj_3pm': 5.0,
        'notes': ''
    }
    # Apply FT logic manually or via calibrate_player
    
    # Test 2: Poor FT shooter
    test_poor = {
        'name': 'Shaquille ONeal Test',
        'base_ft_pct': 0.52,
        'proj_3pm': 1.0,
        'notes': ''
    }
    
    # Test 3: Pull-up shooter
    # Check tracking data for pull-up dominant player
    
    print("Check logs/calibration_debug.log for FT_TOUCH and SHOT_CREATION entries")

if __name__ == "__main__":
    test_shot_quality_enhancements()
```

### Expected Log Entries

```
2026-01-21 15:50:00 | ADJUST | Stephen Curry | FT_TOUCH | Modifier: 1.050 | Elite FT: 92.0%
2026-01-21 15:50:00 | ADJUST | Duncan Robinson | SHOT_CREATION | Modifier: 1.030 | Catch-shoot: 85% of 3s
2026-01-21 15:50:00 | ADJUST | Luka Doncic | SHOT_CREATION | Modifier: 0.970 | Pull-up: 72% of 3s
```

---

## Success Criteria

✅ **Code Quality:**
- [ ] FT% logic added with correct thresholds (>85%, <65%)
- [ ] Shot creation logic added with correct thresholds (>65% pull-up, <25%)
- [ ] Debug logging integrated for both enhancements
- [ ] Notes appended for adjustments

✅ **Testing:**
- [ ] Elite FT shooter gets +5% 3PM boost
- [ ] Poor FT shooter gets -5% 3PM penalty
- [ ] Pull-up shooter gets -3% 3PM adjustment
- [ ] Spot-up shooter gets +3% 3PM boost
- [ ] Log entries appear for FT_TOUCH and SHOT_CREATION

---

## Reference Files

| File | Purpose | Location |
|------|---------|----------|
| **module_e.py** | Target file | `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/` |
| **implementation_plan.md** | Research summary | Artifacts dir |

---

## Key Constraints

1. **Order:** Insert after existing shot quality logic, before nuance checks
2. **Tracking Data:** Only apply shot creation if `tracking_data` exists
3. **FT% Zero Check:** Skip if `ft_pct == 0` (no data)
4. **Logging:** Use existing `_log_adjustment()` helper

---

## Deliverables

1. **Modified Code:** Updated `module_e.py` with both enhancements
2. **Test Results:** Log entries showing adjustments applied
3. **Sample Players:** 2-3 players affected by each enhancement
4. **Confirmation:** Statement that all success criteria met

---

**Estimated Time:** 25-30 minutes  
**Good luck!**
