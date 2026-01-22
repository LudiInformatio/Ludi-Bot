# Phase 2: Team Offensive Types & Matchup Matrix Expansion

**Date:** January 21, 2026  
**Task Owner:** [Agent to be assigned]  
**Priority:** HIGH  
**Estimated Time:** 60-90 minutes  
**Prerequisite:** Phase 1 Complete ✅

---

## Mission

Implement **Phase 2 of the Archetype & Team Type Upgrade Plan**:
1. **Team Offensive Types** - Automated classification for all 30 teams
2. **Matchup Matrix Expansion** - Add offense-vs-defense modifiers

---

## Background Context

### Why This Matters

**Phase 1 Delivered:**
- Volume floor for PPP efficiency (prevents role player over-projection)
- Debug logging for audit trail
- FT% shooting touch indicator
- Shot creation split (C&S vs pull-up)
- Data pipeline cleanup (100% coverage)

**Phase 2 Adds:**
- **Team Offensive Types:** Match team offensive style (MOTION, ISO-HEAVY, etc.) with player archetypes
- **Enhanced Matchup Matrix:** Add offense type × defense type modifiers

**From ARCHETYPE_SYNERGY_UPGRADE_PLAN.md:**
> "Team Offensive Types - Automated weekly classification system (mirrors defense)"

---

## Part 1: Team Offensive Types (6 Classifications)

### 1A. Team Type Definitions

| Type | Criteria | Examples (2025-26 Data) |
|------|----------|----------|
| **MOTION** | High assist rate, low ISO rate | GSW (ORtg 116.9), BOS (ORtg 122.1), DEN |
| **ISO_HEAVY** | High ISO possessions, low pass% | Note: DAL transitioning post-Luka, PHX now PACE_PUSH |
| **PACE_PUSH** | Pace > 100, high transition | UTA (101.8), CHI (101.5), WAS (101.1), PHX (uptempo) |
| **HALF_COURT** | Pace < 97, methodical | MEM (95.4), LAC (95.8), BOS (95.7), BKN (96.6), PHI (96.6) |
| **POST_CENTRIC** | High paint touches, post-up freq | (Verify with Synergy data) |
| **NEUTRAL** | Doesn't strongly fit above | Default fallback |

**⚠️ 2025-26 Season Updates:**
- **Memphis** leads SLOWEST pace (95.4) - NOT fastest (changed from 2024-25)
- **Utah, Chicago, Washington** are FASTEST (101+)
- **Phoenix** shifted to PACE_PUSH (post-KD/Beal, Booker-led uptempo)
- **Dallas** no longer ISO_HEAVY (post-Luka departure, struggling offense)
- **Boston** has SLOW pace (95.7) but ELITE offense (122.1 ORtg #2 league)

### 1B. Implementation

**Target File:** `module_e.py`

**Add after `DEFENSIVE_STYLES` dict (around line 46):**

```python
# 2025-26 TEAM OFFENSIVE STYLES
# Updated bi-weekly via classify_team_offense()
# Based on verified pace/ORtg data (Jan 2026)
self.OFFENSIVE_STYLES = {
    # MOTION - High ball movement, assist-heavy
    "GSW": "MOTION", "BOS": "MOTION", "DEN": "MOTION", 
    "ATL": "MOTION", "IND": "MOTION", "OKC": "MOTION",
    
    # ISO_HEAVY - Star-driven isolation (reduced from prior season)
    "MIA": "ISO_HEAVY", "HOU": "ISO_HEAVY", "CLE": "ISO_HEAVY",
    # Note: DAL removed (post-Luka), PHX moved to PACE_PUSH
    
    # PACE_PUSH - Fast break focused (>100 pace)
    "UTA": "PACE_PUSH", "CHI": "PACE_PUSH", "WAS": "PACE_PUSH",
    "PHX": "PACE_PUSH", "SAC": "PACE_PUSH", "NYK": "PACE_PUSH",
    
    # HALF_COURT - Methodical, low pace (<97)
    "MEM": "HALF_COURT", "LAC": "HALF_COURT", "BKN": "HALF_COURT",
    "PHI": "HALF_COURT", "ORL": "HALF_COURT", "TOR": "HALF_COURT",
    "MIN": "HALF_COURT",
    
    # Default: NEUTRAL
    "LAL": "NEUTRAL", "MIL": "NEUTRAL", "DAL": "NEUTRAL",
    "CHA": "NEUTRAL", "DET": "NEUTRAL", "POR": "NEUTRAL", 
    "SAS": "NEUTRAL", "NOP": "NEUTRAL"
}
```

### 1C. Add Dynamic Classifier Method

**Add new method to LudiCalibrator class:**

```python
def classify_team_offense(self, team_abbr: str) -> str:
    """
    Dynamically classify team offensive style based on tracking data.
    Falls back to static dict if insufficient data.
    
    Returns: MOTION, ISO_HEAVY, PACE_PUSH, HALF_COURT, or NEUTRAL
    """
    try:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Query team stats from last 30 days
        cursor.execute("""
            SELECT 
                AVG(team_pace) as pace,
                AVG(team_ast) as assists,
                AVG(team_pts_paint) as paint_pts
            FROM games
            WHERE (home_team = ? OR away_team = ?)
            AND date >= date('now', '-30 days')
        """, (team_abbr, team_abbr))
        
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            pace = row[0] or 100
            assists = row[1] or 25
            
            # Classification logic
            if pace > 103:
                return "PACE_PUSH"
            elif pace < 97:
                return "HALF_COURT"
            elif assists > 27:
                return "MOTION"
            # Fallback to static
            return self.OFFENSIVE_STYLES.get(team_abbr, "NEUTRAL")
        
        return self.OFFENSIVE_STYLES.get(team_abbr, "NEUTRAL")
        
    except Exception as e:
        return self.OFFENSIVE_STYLES.get(team_abbr, "NEUTRAL")
```

---

## Part 2: Matchup Matrix Expansion

### 2A. New Offensive Style Modifiers

**Add new matchup logic in calibrate_player() or create new method:**

```python
def _apply_offensive_style_boost(self, calibrated: dict, team_offense: str, 
                                  opponent_defense: str) -> None:
    """
    Apply modifiers based on team offensive style vs opponent defense.
    
    Research basis:
    - MOTION offense beats BLITZ defense (ball movement beats pressure)
    - ISO_HEAVY struggles vs PAINT_PACK (limited driving lanes)
    - PACE_PUSH exploits slow teams in transition
    """
    player_name = calibrated.get('name', calibrated.get('PLAYER_NAME', ''))
    sec_playtypes = calibrated.get('secondary_playtypes', [])
    
    # MOTION offense bonuses
    if team_offense == "MOTION":
        if opponent_defense == "BLITZ":
            # Ball movement beats aggressive traps
            if 'SPOT_UP' in sec_playtypes or 'OFF_BALL_CUTTER' in sec_playtypes:
                self._boost_stat(calibrated, 'proj_pts', 1.05)
                self._boost_stat(calibrated, 'proj_ast', 1.05)
                calibrated['notes'] += " | Motion vs Blitz"
                self._log_adjustment(player_name, 'OFF_STYLE', 1.05, 
                    "MOTION vs BLITZ: ball movement advantage")
    
    # ISO_HEAVY penalties
    elif team_offense == "ISO_HEAVY":
        if opponent_defense == "PAINT_PACK":
            # Limited driving lanes
            if 'ISO_SCORER' in sec_playtypes or 'P&R_HANDLER' in sec_playtypes:
                self._boost_stat(calibrated, 'proj_pts', 0.96)
                calibrated['notes'] += " | ISO vs Paint Pack"
                self._log_adjustment(player_name, 'OFF_STYLE', 0.96, 
                    "ISO_HEAVY vs PAINT_PACK: clogged lanes")
    
    # PACE_PUSH bonuses
    elif team_offense == "PACE_PUSH":
        if opponent_defense in ["FUNNEL", "HACKERS"]:
            # Transition exploits slow recovery
            if 'TRANSITION' in sec_playtypes:
                self._boost_stat(calibrated, 'proj_pts', 1.06)
                calibrated['notes'] += " | Pace Push"
                self._log_adjustment(player_name, 'OFF_STYLE', 1.06, 
                    "PACE_PUSH vs weak transition defense")
    
    # HALF_COURT specific
    elif team_offense == "HALF_COURT":
        if opponent_defense == "PERIMETER":
            # Methodical offense finds gaps
            if 'P&R_ROLL_MAN' in sec_playtypes or 'POST_UP' in sec_playtypes:
                self._boost_stat(calibrated, 'proj_pts', 1.04)
                calibrated['notes'] += " | Half-Court Advantage"
                self._log_adjustment(player_name, 'OFF_STYLE', 1.04, 
                    "HALF_COURT exploits perimeter D")
```

### 2B. Integration Point

**In `calibrate_player()` method, after defensive adjustments (~line 680):**

```python
# Get team offensive style
player_team = calibrated.get('team', p.get('TEAM_ABBREVIATION', ''))
team_offense = self.classify_team_offense(player_team)

# Get opponent defensive style  
opponent_defense = self.DEFENSIVE_STYLES.get(opponent_abbr, 'NEUTRAL')

# Apply offensive style matchup
self._apply_offensive_style_boost(calibrated, team_offense, opponent_defense)
```

---

## Part 3: Testing & Validation

### Test Script

**Create `scripts/test_team_offensive_types.py`:**

```python
#!/usr/bin/env python3
"""Test team offensive type classification and matchups."""
import sys
sys.path.insert(0, '.')

from module_e import LudiCalibrator

def test_offensive_types():
    print("=" * 60)
    print("Testing Team Offensive Types")
    print("=" * 60)
    
    calib = LudiCalibrator(debug_log=True)
    
    # Test static classifications
    tests = [
        ('GSW', 'MOTION'),
        ('DAL', 'ISO_HEAVY'),
        ('SAC', 'PACE_PUSH'),
        ('MIN', 'HALF_COURT'),
        ('LAL', 'NEUTRAL'),
    ]
    
    for team, expected in tests:
        result = calib.classify_team_offense(team)
        status = "✅" if result == expected else "❌"
        print(f"{status} {team}: {result} (expected: {expected})")
    
    # Test matchup adjustments
    print("\n--- Matchup Tests ---")
    
    # MOTION vs BLITZ (should boost)
    test_player = {
        'name': 'Klay Thompson',
        'team': 'GSW',
        'proj_pts': 20.0,
        'secondary_playtypes': ['SPOT_UP'],
        'notes': ''
    }
    calib._apply_offensive_style_boost(test_player, 'MOTION', 'BLITZ')
    print(f"MOTION vs BLITZ: pts = {test_player['proj_pts']:.1f} (expected: 21.0)")
    
    print("\n✅ Check logs/calibration_debug.log for OFF_STYLE entries")

if __name__ == "__main__":
    test_offensive_types()
```

**Run:**
```bash
python3 scripts/test_team_offensive_types.py
```

---

## Success Criteria

### Part 1: Team Offensive Types
- [x] `OFFENSIVE_STYLES` dict added to `__init__` (30 teams)
- [x] `classify_team_offense()` method implemented
- [x] Falls back to static dict if data unavailable

### Part 2: Matchup Matrix
- [x] `_apply_offensive_style_boost()` method added
- [x] Integrated into `calibrate_player()` flow
- [x] Debug logging for OFF_STYLE adjustments

### Part 3: Testing
- [x] Test script created and passing
- [x] Log entries appear for matchup adjustments
- [x] No regression in existing tests

---

## Reference Files

| File | Purpose |
|------|---------|
| `module_e.py` | Target file for implementation |
| `ARCHETYPE_SYNERGY_UPGRADE_PLAN.md` | Original plan document |
| `docs/phase1/` | Phase 1 reference task docs |
| `utils/blowout_tax.py` | Reference for existing calibration patterns |

---

## Key Constraints

1. **Follow existing patterns** - Use `_boost_stat()` helper, match code style
2. **Debug logging** - Use `_log_adjustment()` for all new adjustments
3. **Silent failures** - Wrap in try/except, don't break pipeline
4. **Backward compatible** - All existing functionality must work

---

## Deliverables

Upon completion, provide:

1. **Modified `module_e.py`** with:
   - `OFFENSIVE_STYLES` dict
   - `classify_team_offense()` method
   - `_apply_offensive_style_boost()` method
   - Integration in `calibrate_player()`

2. **Test script** `scripts/test_team_offensive_types.py`

3. **Log output** showing OFF_STYLE adjustments

4. **Confirmation** that all success criteria met

---

**Estimated Time:** 60-90 minutes  
**Good luck!**
