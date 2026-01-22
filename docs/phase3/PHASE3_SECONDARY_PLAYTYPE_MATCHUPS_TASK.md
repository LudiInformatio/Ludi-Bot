# Phase 3: Expanded Matchup Matrix (Secondary Playtype Matchups)

**Date:** January 21, 2026  
**Task Owner:** [Agent to be assigned]  
**Priority:** HIGH  
**Estimated Time:** 90-120 minutes  
**Prerequisites:** Phase 1 ✅, Phase 2 ✅

---

## Mission

Implement **Phase 3 of the Archetype & Team Type Upgrade Plan**:
1. **Secondary Playtype vs Defense Matchups** - 8 new playtype adjustments
2. **Team Offense vs Team Defense combos** - Additional team-level context
3. **Backtest Validation** - Verify modifiers with 60-day data

---

## Background Context

### What's Already Implemented

| Feature | Phase | Status |
|---------|-------|--------|
| Volume Floor & PPP Cap | Phase 1 | ✅ |
| Debug Logging | Phase 1 | ✅ |
| Shot Quality Logic (FT%, C&S) | Phase 1 | ✅ |
| Team Offensive Types | Phase 2 | ✅ |
| Team Defensive Types (0% mismatch) | Phase 2 | ✅ |
| Offense vs Defense Matchups | Phase 2 | ✅ |

### What's Missing (Phase 3)

- **Secondary playtype matchups** (ISO_SCORER vs BLITZ, etc.)
- **Full playtype classification** using Synergy data
- **Backtest to validate modifiers**

---

## Part 1: Secondary Playtype Classification

### 1A. Verify Playtype Threshold Logic

The playtype classification system was built in Phase 1. Verify it's working by running:

```bash
python3 scripts/test_playtype_thresholds_hybrid.py
```

**Expected:** 8 playtypes assigned, each with 25-35% coverage.

If the test script doesn't exist or fails, create `_assign_secondary_playtypes()` in `module_e.py`:

```python
def _assign_secondary_playtypes(self, player_data: dict) -> list:
    """Assign up to 2 secondary playtypes based on tracking data."""
    playtypes = []
    position = player_data.get('position', 'UNK')
    
    # Get tracking stats
    drives = player_data.get('drives', 0)
    ast = player_data.get('ast', 0)
    catch_shoot_3pa = player_data.get('catch_shoot_3pa', 0)
    pull_up_3pa = player_data.get('pull_up_3pa', 0)
    oreb = player_data.get('oreb', 0)
    usg = player_data.get('usg_pct', 0.20)
    
    # ISO_SCORER: drives > 8 AND pull_up > 5 AND usg > 0.28
    if drives > 8 and pull_up_3pa > 5 and usg > 0.28:
        playtypes.append('ISO_SCORER')
    
    # P&R_HANDLER: drives > 5 AND ast > 6 AND pull_up > catch_shoot
    if drives > 5 and ast > 6 and pull_up_3pa > catch_shoot_3pa:
        playtypes.append('P&R_HANDLER')
    
    # SPOT_UP: catch_shoot_3pa > 4 AND 3p% > 0.36
    if catch_shoot_3pa > 4 and player_data.get('fg3_pct', 0) > 0.36:
        playtypes.append('SPOT_UP')
    
    # TRANSITION: fast_break_pts > 3 OR drives > 10
    if player_data.get('fast_break_pts', 0) > 3 or drives > 10:
        playtypes.append('TRANSITION')
    
    # P&R_ROLL_MAN: (position C/F-C) AND rim_fg% > 60%
    if position in ['C', 'F-C'] and player_data.get('rim_fg_pct', 0) > 0.60:
        playtypes.append('P&R_ROLL_MAN')
    
    # OFF_BALL_CUTTER: (position F/G-F) AND drives < 4 AND pts_paint > 4
    if position in ['F', 'G-F'] and drives < 4 and player_data.get('pts_paint', 0) > 4:
        playtypes.append('OFF_BALL_CUTTER')
    
    # PUTBACK: oreb > 2.5
    if oreb > 2.5:
        playtypes.append('PUTBACK')
    
    # POST_UP: (position C/F-C) AND post_ups > 4
    if position in ['C', 'F-C'] and player_data.get('post_ups', 0) > 4:
        playtypes.append('POST_UP')
    
    # Limit to top 2 playtypes (highest confidence)
    return playtypes[:2]
```

---

## Part 2: Secondary Playtype Matchup Logic

### 2A. Add `_apply_secondary_playtype_matchups()` Method

**Add to `module_e.py` after `_apply_offensive_style_boost()`:**

```python
def _apply_secondary_playtype_matchups(self, calibrated: dict, def_style: str) -> None:
    """
    Apply modifiers based on player's secondary playtypes vs opponent defense.
    
    Research basis:
    - ISO vs BLITZ: Pressure forces turnovers
    - SPOT_UP vs PAINT_PACK: Open shooters feast on helpers
    - P&R_ROLL_MAN vs DROP: Lobs and dunks available
    """
    player_name = calibrated.get('name', '')
    secondary_types = calibrated.get('secondary_playtypes', [])
    
    for playtype in secondary_types:
        # ISO_SCORER matchups
        if playtype == 'ISO_SCORER':
            if def_style == "BLITZ":
                self._boost_stat(calibrated, 'proj_pts', 0.92)
                self._boost_stat(calibrated, 'proj_tov', 1.12)
                calibrated['notes'] += " | ISO Tax vs Blitz"
                self._log_adjustment(player_name, 'PLAYTYPE', 0.92, 
                    "ISO_SCORER vs BLITZ: pressure forces mistakes")
            elif def_style == "PERIMETER":
                self._boost_stat(calibrated, 'proj_pts', 1.10)
                calibrated['notes'] += " | ISO Mismatch"
                self._log_adjustment(player_name, 'PLAYTYPE', 1.10, 
                    "ISO_SCORER vs PERIMETER: space to operate")
        
        # P&R_HANDLER matchups
        elif playtype == 'P&R_HANDLER':
            if def_style == "PAINT_PACK":
                self._boost_stat(calibrated, 'proj_ast', 1.08)
                calibrated['notes'] += " | P&R Drop Edge"
                self._log_adjustment(player_name, 'PLAYTYPE', 1.08, 
                    "P&R_HANDLER vs DROP: passing lanes open")
            elif def_style == "BLITZ":
                self._boost_stat(calibrated, 'proj_ast', 0.90)
                self._boost_stat(calibrated, 'proj_tov', 1.15)
                calibrated['notes'] += " | P&R Blitz Tax"
                self._log_adjustment(player_name, 'PLAYTYPE', 0.90, 
                    "P&R_HANDLER vs BLITZ: traps create errors")
        
        # SPOT_UP matchups (strongest research validation)
        elif playtype == 'SPOT_UP':
            if def_style == "PAINT_PACK":
                self._boost_stat(calibrated, 'proj_3pm', 1.12)
                calibrated['notes'] += " | Spot-Up vs Helpers"
                self._log_adjustment(player_name, 'PLAYTYPE', 1.12, 
                    "SPOT_UP vs PAINT_PACK: open 3s from help D")
            elif def_style == "PERIMETER":
                self._boost_stat(calibrated, 'proj_3pm', 0.95)
                self._log_adjustment(player_name, 'PLAYTYPE', 0.95, 
                    "SPOT_UP vs PERIMETER: contested shots")
        
        # TRANSITION matchups
        elif playtype == 'TRANSITION':
            if def_style == "FUNNEL":
                self._boost_stat(calibrated, 'proj_pts', 1.15)
                calibrated['notes'] += " | Transition Chaos"
                self._log_adjustment(player_name, 'PLAYTYPE', 1.15, 
                    "TRANSITION vs FUNNEL: fast break chaos")
            elif def_style == "PAINT_PACK":
                self._boost_stat(calibrated, 'proj_pts', 0.92)
                self._log_adjustment(player_name, 'PLAYTYPE', 0.92, 
                    "TRANSITION vs PAINT_PACK: set defense stops breaks")
        
        # P&R_ROLL_MAN matchups
        elif playtype == 'P&R_ROLL_MAN':
            if def_style == "PAINT_PACK":
                self._boost_stat(calibrated, 'proj_pts', 1.15)
                self._boost_stat(calibrated, 'proj_fg_pct', 1.10)
                calibrated['notes'] += " | Roll Man vs Drop"
                self._log_adjustment(player_name, 'PLAYTYPE', 1.15, 
                    "P&R_ROLL_MAN vs DROP: lobs and dunks")
            elif def_style == "BLITZ":
                self._boost_stat(calibrated, 'proj_pts', 0.88)
                self._log_adjustment(player_name, 'PLAYTYPE', 0.88, 
                    "P&R_ROLL_MAN vs BLITZ: no space at rim")
        
        # OFF_BALL_CUTTER matchups
        elif playtype == 'OFF_BALL_CUTTER':
            if def_style == "PERIMETER":
                self._boost_stat(calibrated, 'proj_pts', 1.12)
                calibrated['notes'] += " | Cutter vs Small Ball"
                self._log_adjustment(player_name, 'PLAYTYPE', 1.12, 
                    "OFF_BALL_CUTTER vs PERIMETER: backdoor cuts")
            elif def_style == "PAINT_PACK":
                self._boost_stat(calibrated, 'proj_fg_pct', 0.90)
                self._log_adjustment(player_name, 'PLAYTYPE', 0.90, 
                    "OFF_BALL_CUTTER vs PAINT_PACK: clogged lanes")
        
        # PUTBACK matchups
        elif playtype == 'PUTBACK':
            if def_style == "PERIMETER":
                self._boost_stat(calibrated, 'proj_oreb', 1.20)
                self._boost_stat(calibrated, 'proj_pts', 1.15)
                calibrated['notes'] += " | Putback vs Small Ball"
                self._log_adjustment(player_name, 'PLAYTYPE', 1.15, 
                    "PUTBACK vs PERIMETER: size advantage")
```

### 2B. Integration Point

**In `calibrate_player()` method, after `_apply_offensive_style_boost()`:**

```python
# After team offense vs defense matchup:
self._apply_offensive_style_boost(calibrated, team_offense, opponent_defense)

# NEW: Secondary playtype matchups
self._apply_secondary_playtype_matchups(calibrated, opponent_defense)
```

---

## Part 3: Testing & Validation

### Test Script

**Create `scripts/test_secondary_playtype_matchups.py`:**

```python
#!/usr/bin/env python3
"""Test secondary playtype vs defense matchup logic."""
import sys
sys.path.insert(0, '.')

from module_e import LudiCalibrator

def test_playtype_matchups():
    print("=" * 60)
    print("Testing Secondary Playtype Matchups")
    print("=" * 60)
    
    calib = LudiCalibrator(debug_log=True)
    
    # Test 1: ISO_SCORER vs BLITZ (-8% pts, +12% tov)
    test1 = {
        'name': 'Shai Gilgeous-Alexander',
        'team': 'OKC',
        'proj_pts': 25.0,
        'proj_tov': 4.0,
        'secondary_playtypes': ['ISO_SCORER'],
        'notes': ''
    }
    calib._apply_secondary_playtype_matchups(test1, 'BLITZ')
    print(f"ISO vs BLITZ: pts {25.0:.1f}→{test1['proj_pts']:.1f} (-8% expected)")
    print(f"ISO vs BLITZ: tov {4.0:.1f}→{test1['proj_tov']:.1f} (+12% expected)")
    
    # Test 2: SPOT_UP vs PAINT_PACK (+12% 3pm)
    test2 = {
        'name': 'Klay Thompson',
        'team': 'DAL',
        'proj_3pm': 3.0,
        'secondary_playtypes': ['SPOT_UP'],
        'notes': ''
    }
    calib._apply_secondary_playtype_matchups(test2, 'PAINT_PACK')
    print(f"SPOT_UP vs PAINT_PACK: 3pm {3.0:.1f}→{test2['proj_3pm']:.1f} (+12% expected)")
    
    # Test 3: P&R_ROLL_MAN vs PAINT_PACK (+15% pts)
    test3 = {
        'name': 'Clint Capela',
        'team': 'HOU',
        'proj_pts': 10.0,
        'secondary_playtypes': ['P&R_ROLL_MAN'],
        'notes': ''
    }
    calib._apply_secondary_playtype_matchups(test3, 'PAINT_PACK')
    print(f"ROLL_MAN vs DROP: pts {10.0:.1f}→{test3['proj_pts']:.1f} (+15% expected)")
    
    # Test 4: TRANSITION vs FUNNEL (+15% pts)
    test4 = {
        'name': 'Anthony Edwards',
        'team': 'MIN',
        'proj_pts': 22.0,
        'secondary_playtypes': ['TRANSITION'],
        'notes': ''
    }
    calib._apply_secondary_playtype_matchups(test4, 'FUNNEL')
    print(f"TRANSITION vs FUNNEL: pts {22.0:.1f}→{test4['proj_pts']:.1f} (+15% expected)")
    
    print("\n✅ Check logs/calibration_debug.log for PLAYTYPE entries")

if __name__ == "__main__":
    test_playtype_matchups()
```

### Run Tests

```bash
python3 scripts/test_secondary_playtype_matchups.py
```

**Expected Output:**
```
ISO vs BLITZ: pts 25.0→23.0 (-8% expected)
ISO vs BLITZ: tov 4.0→4.5 (+12% expected)
SPOT_UP vs PAINT_PACK: 3pm 3.0→3.4 (+12% expected)
ROLL_MAN vs DROP: pts 10.0→11.5 (+15% expected)
TRANSITION vs FUNNEL: pts 22.0→25.3 (+15% expected)
```

---

## Part 4: Backtest (60-Day Validation)

### Create `scripts/backtest_playtype_matchups.py`

Compare predictions WITH vs WITHOUT playtype matchup logic.

**Metrics:**
- Hit rate change
- Average projection error
- Modifier frequency (how often each matchup fires)

---

## Success Criteria

- [x] `_assign_secondary_playtypes()` method added (or verified working)
- [x] `_apply_secondary_playtype_matchups()` method added
- [x] Integrated into `calibrate_player()` flow
- [x] Test script passing with expected modifiers
- [x] Debug log shows PLAYTYPE entries
- [x] No regression in Phase 1/2 tests

---

## Matchup Reference

| Playtype | vs Defense | Effect | Reasoning |
|----------|------------|--------|-----------|
| ISO_SCORER | BLITZ | -8% pts, +12% tov | Pressure forces mistakes |
| ISO_SCORER | PERIMETER | +10% pts | Space to operate |
| P&R_HANDLER | PAINT_PACK | +8% ast | Drop opens passing lanes |
| P&R_HANDLER | BLITZ | -10% ast, +15% tov | Traps create errors |
| SPOT_UP | PAINT_PACK | +12% 3pm | Open 3s from help D |
| SPOT_UP | PERIMETER | -5% 3pm | Contested shots |
| TRANSITION | FUNNEL | +15% pts | Fast break chaos |
| TRANSITION | PAINT_PACK | -8% pts | Set defense stops breaks |
| P&R_ROLL_MAN | PAINT_PACK | +15% pts, +10% fg% | Lobs and dunks |
| P&R_ROLL_MAN | BLITZ | -12% pts | No space at rim |
| OFF_BALL_CUTTER | PERIMETER | +12% pts | Backdoor cuts |
| OFF_BALL_CUTTER | PAINT_PACK | -10% fg% | Clogged lanes |
| PUTBACK | PERIMETER | +20% oreb, +15% pts | Size advantage |

---

## Reference Files

| File | Purpose |
|------|---------|
| `module_e.py` | Target for implementation |
| `ARCHETYPE_SYNERGY_UPGRADE_PLAN.md` | Original plan (lines 462-556) |
| `config/playtype_thresholds.json` | Threshold config |
| `scripts/test_team_offensive_types.py` | Pattern reference |

---

**Estimated Time:** 90-120 minutes  
**Deliverables:**
1. Updated `module_e.py` with playtype matchup logic
2. Test script `scripts/test_secondary_playtype_matchups.py`
3. Log output showing PLAYTYPE entries
4. Confirmation that all success criteria met

Good luck! 🚀
