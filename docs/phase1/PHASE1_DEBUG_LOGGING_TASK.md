# Phase 1: Debug Logging Implementation Task

**Date:** January 21, 2026  
**Task Owner:** [Agent to be assigned]  
**Priority:** HIGH (P2)  
**Estimated Time:** 20-30 minutes  

---

## Mission

Implement **optional debug logging** for Module E calibration functions to create an audit trail for tracking when adjustments trigger, what modifiers are applied, and why players are filtered or boosted.

---

## Background Context

### Why Logging is Needed

**Current Problem:** Calibration functions fail silently — when a player doesn't get an adjustment, we don't know WHY:
- Did they fail the volume floor?
- Did they not have Synergy data?
- Did they not have a rim-based playtype for defensive adjustment?

**Solution:** Add opt-in debug logging that writes adjustment details to a log file.

**From Phase 1 Completion Report:**
> "No logging for silent failures - Impact: Moderate (hard to debug why adjustments don't trigger)"

---

## Technical Implementation

### File to Modify

**Primary File:** `module_e.py`  
**Location:** `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/module_e.py`

---

### Change 1: Update `__init__` Method (line 13)

**Current Code (lines 13-25):**
```python
class LudiCalibrator:
    def __init__(self):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE E (CALIBRATOR V7.0) ONLINE")
        print(f"   >>> SECONDARY PLAYTYPE SYSTEM ACTIVE")
        print(f"{'='*40}")
        
        self.id_resolver = PlayerIDResolver()
        
        self.ADJUSTMENT_RULES = {
            "MINUTES_LIMIT": 0.75,   
            "PROMOTION": 1.50,       
            "OUT": 0.0              
        }
```

**New Code:**
```python
class LudiCalibrator:
    def __init__(self, db_path='ludi.db', debug_log=False):
        print(f"\n{'='*40}")
        print(f"LUDI INFORMATIO: MODULE E (CALIBRATOR V7.0) ONLINE")
        print(f"   >>> SECONDARY PLAYTYPE SYSTEM ACTIVE")
        if debug_log:
            print(f"   >>> DEBUG LOGGING ENABLED")
        print(f"{'='*40}")
        
        self.db_path = db_path
        self.debug_log = debug_log
        
        # Initialize debug logger if enabled
        if debug_log:
            import logging
            import os
            os.makedirs('logs', exist_ok=True)
            logging.basicConfig(
                filename='logs/calibration_debug.log',
                level=logging.DEBUG,
                format='%(asctime)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            self.logger = logging.getLogger('module_e')
            self.logger.debug("=== Module E Debug Logging Initialized ===")
        
        self.id_resolver = PlayerIDResolver()
        
        self.ADJUSTMENT_RULES = {
            "MINUTES_LIMIT": 0.75,   
            "PROMOTION": 1.50,       
            "OUT": 0.0              
        }
```

---

### Change 2: Add Helper Method `_log_adjustment()` (after line ~90)

**Insert new method after existing helper methods:**

```python
def _log_adjustment(self, player_name: str, function: str, 
                    modifier: float, reason: str) -> None:
    """
    Log calibration adjustment if debug mode enabled.
    
    Args:
        player_name: Player being calibrated
        function: Name of the calibration function
        modifier: Adjustment factor applied (e.g., 1.07 for +7%)
        reason: Human-readable explanation
    """
    if self.debug_log and hasattr(self, 'logger'):
        self.logger.debug(
            f"ADJUST | {player_name} | {function} | "
            f"Modifier: {modifier:.3f} | {reason}"
        )

def _log_skip(self, player_name: str, function: str, reason: str) -> None:
    """
    Log when a calibration adjustment is skipped.
    
    Args:
        player_name: Player being calibrated
        function: Name of the calibration function
        reason: Why adjustment was skipped
    """
    if self.debug_log and hasattr(self, 'logger'):
        self.logger.debug(
            f"SKIP | {player_name} | {function} | {reason}"
        )
```

---

### Change 3: Add Logging to `_apply_synergy_ppp_efficiency()` (lines 856-940)

**Add logging calls at key decision points:**

```python
def _apply_synergy_ppp_efficiency(self, calibrated: dict, opponent_abbr: str) -> None:
    player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))

    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Volume floor check
        volume_query = """..."""
        cursor.execute(volume_query, (player_name,))
        volume_row = cursor.fetchone()

        MIN_FGA = 10.0
        MIN_PTS = 12.0

        if not volume_row or (volume_row[0] < MIN_PTS and volume_row[1] < MIN_FGA):
            conn.close()
            # NEW: Log skip
            self._log_skip(player_name, 'PPP_EFFICIENCY', 
                f"Volume floor: {volume_row[0] if volume_row else 0:.1f} PPG, "
                f"{volume_row[1] if volume_row else 0:.1f} FGA")
            return

        # ... existing Synergy query ...
        
        if not rows:
            # NEW: Log skip  
            self._log_skip(player_name, 'PPP_EFFICIENCY', 'No Synergy playtype data')
            return

        # ... calculate modifier ...
        
        # Apply to points projection
        self._boost_stat(calibrated, 'proj_pts', modifier)
        
        # NEW: Log adjustment
        self._log_adjustment(player_name, 'PPP_EFFICIENCY', modifier,
            f"Weighted PPP: {weighted_ppp:.3f}")

    except Exception as e:
        # NEW: Log error
        if self.debug_log and hasattr(self, 'logger'):
            self.logger.debug(f"ERROR | {player_name} | PPP_EFFICIENCY | {str(e)}")
```

---

### Change 4: Add Logging to `_apply_defensive_diff_adjustment()` (lines 938-1003)

**Add logging calls:**

```python
def _apply_defensive_diff_adjustment(self, calibrated: dict, opponent_abbr: str) -> None:
    player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))
    sec_playtypes = calibrated.get('secondary_playtypes', [])

    RIM_BASED = ['P&R_ROLL_MAN', 'OFF_BALL_CUTTER', 'PUTBACK', 'POST_UP']
    has_rim_playtype = any(pt in RIM_BASED for pt in sec_playtypes)

    if not has_rim_playtype:
        # NEW: Log skip
        self._log_skip(player_name, 'DEFENSIVE_DIFF', 
            f"No rim playtype (has: {sec_playtypes})")
        return

    # ... existing query ...
    
    if not row:
        # NEW: Log skip
        self._log_skip(player_name, 'DEFENSIVE_DIFF', 
            f"No defensive data for {opponent_abbr}")
        return

    # ... calculate modifier ...
    
    # Apply modifier
    self._boost_stat(calibrated, 'proj_pts', modifier)
    
    # NEW: Log adjustment
    self._log_adjustment(player_name, 'DEFENSIVE_DIFF', modifier,
        f"vs {rim_protector_name}: {diff_pct:.1f}% diff")
```

---

### Change 5: Add Logging to `_apply_drives_assist_profile()` (lines 1005-1060)

**Add logging calls:**

```python
def _apply_drives_assist_profile(self, calibrated: dict) -> None:
    player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))

    # ... existing query ...
    
    if not row or row[0] < 5:
        # NEW: Log skip
        self._log_skip(player_name, 'DRIVES_AST', 
            f"Insufficient data ({row[0] if row else 0} games)")
        return

    games, drives, pass_pct = row

    if drives >= 8 and pass_pct >= 40:
        modifier = 1.10
        tag = "Elite Playmaker"
    elif drives >= 6 and pass_pct >= 35:
        modifier = 1.05
        tag = "High Pass Rate"
    elif pass_pct < 25:
        modifier = 0.95
        tag = "Score-First Driver"
    else:
        # NEW: Log neutral profile
        self._log_skip(player_name, 'DRIVES_AST', 
            f"Neutral profile ({drives:.1f} drives, {pass_pct:.1f}% pass)")
        return

    # Apply modifier
    self._boost_stat(calibrated, 'proj_ast', modifier)
    
    # NEW: Log adjustment
    self._log_adjustment(player_name, 'DRIVES_AST', modifier,
        f"{tag}: {drives:.1f} drives, {pass_pct:.1f}% pass")
```

---

## Testing & Verification

### Automated Test

Create test script `scripts/test_debug_logging.py`:

```python
#!/usr/bin/env python3
"""Test debug logging functionality in Module E."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from module_e import LudiCalibrator

def test_debug_logging():
    print("=" * 60)
    print("Testing Module E Debug Logging")
    print("=" * 60)
    
    # Clean old log file
    log_path = 'logs/calibration_debug.log'
    if os.path.exists(log_path):
        os.remove(log_path)
    
    # Initialize with debug logging enabled
    calib = LudiCalibrator(debug_log=True)
    
    # Test 1: High-volume player (should get PPP boost)
    test_player_1 = {
        'name': 'LeBron James',
        'base_pts': 23.0,
        'proj_pts': 25.0,
        'secondary_playtypes': [],
        'notes': ''
    }
    calib._apply_synergy_ppp_efficiency(test_player_1, 'BOS')
    
    # Test 2: Low-volume player (should be skipped)
    test_player_2 = {
        'name': 'Luke Kornet',
        'base_pts': 5.5,
        'proj_pts': 5.5,
        'secondary_playtypes': [],
        'notes': ''
    }
    calib._apply_synergy_ppp_efficiency(test_player_2, 'BOS')
    
    # Test 3: Rim scorer (should get defensive adjustment if data exists)
    test_player_3 = {
        'name': 'Clint Capela',
        'base_pts': 10.0,
        'proj_pts': 12.0,
        'secondary_playtypes': ['P&R_ROLL_MAN'],
        'notes': ''
    }
    calib._apply_defensive_diff_adjustment(test_player_3, 'SAS')
    
    # Verify log file exists and has content
    if os.path.exists(log_path):
        with open(log_path, 'r') as f:
            log_content = f.read()
        print("\n✅ Log file created successfully")
        print(f"   Path: {log_path}")
        print(f"   Size: {len(log_content)} bytes")
        print("\n--- LOG CONTENTS ---")
        print(log_content)
        print("--- END LOG ---")
        
        # Check for expected entries
        checks = [
            ('Module E Debug Logging Initialized', 'Initialization'),
            ('LeBron James', 'LeBron entry'),
            ('Luke Kornet', 'Kornet entry'),
        ]
        
        for check, name in checks:
            if check in log_content:
                print(f"✅ {name}: Found")
            else:
                print(f"❌ {name}: NOT FOUND")
        
        return True
    else:
        print("❌ Log file not created!")
        return False


if __name__ == "__main__":
    success = test_debug_logging()
    print("\n" + "=" * 60)
    print(f"TEST RESULT: {'✅ PASSED' if success else '❌ FAILED'}")
    print("=" * 60)
```

**Run test:**
```bash
cd /Users/flyprice/Desktop/Ludi\ Informatio/Projects/Ludi-Bot
python3 scripts/test_debug_logging.py
```

---

### Manual Verification

**1. Check log file exists:**
```bash
ls -la logs/calibration_debug.log
```

**2. View log contents:**
```bash
cat logs/calibration_debug.log
```

**Expected Log Format:**
```
2026-01-21 15:30:00 | === Module E Debug Logging Initialized ===
2026-01-21 15:30:01 | ADJUST | LeBron James | PPP_EFFICIENCY | Modifier: 1.070 | Weighted PPP: 1.124
2026-01-21 15:30:01 | SKIP | Luke Kornet | PPP_EFFICIENCY | Volume floor: 8.2 PPG, 4.9 FGA
2026-01-21 15:30:01 | SKIP | Clint Capela | DEFENSIVE_DIFF | No defensive data for SAS
```

**3. Verify backward compatibility (default OFF):**
```python
# Normal usage - no logging
calib = LudiCalibrator()  # debug_log defaults to False

# Debug usage - with logging
calib = LudiCalibrator(debug_log=True)
```

---

## Success Criteria

✅ **Code Quality:**
- [ ] `__init__` updated with `debug_log=False` parameter
- [ ] `logs/` directory created automatically if missing
- [ ] `_log_adjustment()` helper method added
- [ ] `_log_skip()` helper method added
- [ ] Logging added to all 3 Synergy functions

✅ **Testing:**
- [ ] Test script passes (log file created, entries present)
- [ ] LeBron adjustment logged with modifier value
- [ ] Luke Kornet skip logged with volume reason
- [ ] Backward compatibility: default behavior unchanged

✅ **Performance:**
- [ ] No logging overhead when `debug_log=False`
- [ ] Log file size reasonable (< 1MB per day typical usage)

✅ **Documentation:**
- [ ] Helper method docstrings added
- [ ] Init docstring updated

---

## Reference Files

| File | Purpose | Location |
|------|---------|----------|
| **module_e.py** | Target file for modifications | `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/` |
| **PHASE1_VOLUME_FLOOR_TASK.md** | Previous task (reference) | `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/` |
| **phase1_roadmap.md** | Project roadmap | `/Users/flyprice/.gemini/antigravity/brain/e98c2994-a6ad-438c-914a-b9c231510d16/` |

---

## Key Constraints

1. **Opt-in Only:** Debug logging MUST be disabled by default (`debug_log=False`)
2. **Backward Compatible:** Existing code using `LudiCalibrator()` must work unchanged
3. **Silent When Disabled:** No performance overhead if logging is off
4. **Auto-create Directory:** Create `logs/` dir if it doesn't exist
5. **Append Mode:** Log file should append, not overwrite

---

## Deliverables

Upon completion, provide:

1. **Modified Code:** Updated `module_e.py` with logging system
2. **Test Script:** `scripts/test_debug_logging.py`
3. **Test Results:** Output showing log file created and entries present
4. **Sample Log:** First 20 lines of `logs/calibration_debug.log`
5. **Confirmation:** Statement that all success criteria met

---

## Estimated Effort

| Step | Time |
|------|------|
| Update `__init__` method | 5 min |
| Add helper methods | 5 min |
| Add logging to 3 functions | 10 min |
| Create test script | 5 min |
| Run tests & verify | 5 min |
| **Total** | **~30 min** |

---

**Good luck! Report back with verification results.**
