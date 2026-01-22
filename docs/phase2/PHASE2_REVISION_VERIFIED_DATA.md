# Phase 2 Revision: Update Team Classifications with Verified 2025-26 Data

**Date:** January 21, 2026  
**Revision Needed:** Update OFFENSIVE_STYLES dict with verified current season data  
**Estimated Time:** 30 minutes  

---

## Context

You just completed Phase 2 implementation of team offensive types. **Excellent work on the code structure!** ✅

However, the task document used **preliminary 2024-25 season data**. We now have **verified 2025-26 data** showing **major team changes**:

1. **Memphis:** Slowest league pace (95.4) - NOT fastest
2. **Phoenix:** Now PACE_PUSH (post-KD/Beal)  
3. **Dallas:** Now NEUTRAL (post-Luka, struggling)
4. **Boston:** Slow pace BUT elite offense (dual nature)

---

## Part 1: Review Your Implementation (5 min)

### What You Built (All Good! ✅)

| File | Feature | Status |
|------|---------|--------|
| `module_e.py` | `OFFENSIVE_STYLES` dict | ✅ Implementation correct |
| `module_e.py` | `classify_team_offense()` method | ✅ Logic sound |
| `module_e.py` | `_apply_offensive_style_boost()` | ✅ Matchups working |
| `scripts/test_team_offensive_types.py` | Test script | ✅ Structure good |

**Code Quality:** Production-ready, follows all patterns ✅

---

## Part 2: Update Classifications (15 min)

### Current vs Verified Data

**CHANGES NEEDED:**

| Team | Your Classification | Verified 2025-26 | Reason |
|------|-------------------|-----------------|--------|
| **MEM** | HALF_COURT ✅ | HALF_COURT | Pace 95.4 (slowest) |
| **PHX** | ISO_HEAVY ❌ | **PACE_PUSH** | Post-KD/Beal, Booker uptempo |
| **DAL** | ISO_HEAVY ❌ | **NEUTRAL** | Post-Luka, no identity |
| **CHI** | NEUTRAL ❌ | **PACE_PUSH** | Pace 101.5 (#2 fastest) |
| **WAS** | NEUTRAL ❌ | **PACE_PUSH** | Pace 101.1 (#3 fastest) |
| **UTA** | NEUTRAL ❌ | **PACE_PUSH** | Pace 101.8 (#1 fastest) |
| **LAC** | NEUTRAL ❌ | **HALF_COURT** | Pace 95.8 (#2 slowest) |
| **BKN** | NEUTRAL ❌ | **HALF_COURT** | Pace 96.6 |
| **PHI** | NEUTRAL ❌ | **HALF_COURT** | Pace 96.6 |
| **OKC** | PACE_PUSH ✅ | **MOTION** (better fit) | 120.0 ORtg, ball movement |

### Updated `OFFENSIVE_STYLES` Dict

**Replace lines 60-82 in `module_e.py`:**

```python
# 2025-26 TEAM OFFENSIVE STYLES (VERIFIED JAN 21, 2026)
# Based on Basketball-Reference/StatMuse pace + ORtg data
self.OFFENSIVE_STYLES = {
    # MOTION - High ball movement, assist-heavy
    "GSW": "MOTION", "BOS": "MOTION", "DEN": "MOTION", 
    "ATL": "MOTION", "IND": "MOTION", "OKC": "MOTION",  # OKC moved from PACE_PUSH
    
    # ISO_HEAVY - Star-driven isolation (REDUCED from 5 to 3 teams)
    "MIA": "ISO_HEAVY", "HOU": "ISO_HEAVY", "CLE": "ISO_HEAVY",
    # Removed: DAL (post-Luka), PHX (now PACE_PUSH)
    
    # PACE_PUSH - Fast break focused (>100 pace)
    "UTA": "PACE_PUSH",   # 101.8 (#1 fastest)
    "CHI": "PACE_PUSH",   # 101.5 (#2 fastest)
    "WAS": "PACE_PUSH",   # 101.1 (#3 fastest)
    "PHX": "PACE_PUSH",   # Booker-led uptempo (changed from ISO_HEAVY)
    "SAC": "PACE_PUSH", "NYK": "PACE_PUSH",
    
    # HALF_COURT - Methodical, low pace (<97)
    "MEM": "HALF_COURT",  # 95.4 (slowest)
    "LAC": "HALF_COURT",  # 95.8 (#2 slowest)
    "BOS": "HALF_COURT",  # 95.7 (slow but elite 122.1 ORtg)
    "BKN": "HALF_COURT",  # 96.6
    "PHI": "HALF_COURT",  # 96.6
    "ORL": "HALF_COURT", "TOR": "HALF_COURT", "MIN": "HALF_COURT",
    
    # Default: NEUTRAL (only 8 teams now, was 13)
    "LAL": "NEUTRAL", "MIL": "NEUTRAL", "DAL": "NEUTRAL",  # DAL changed from ISO_HEAVY
    "CHA": "NEUTRAL", "DET": "NEUTRAL", "POR": "NEUTRAL", 
    "SAS": "NEUTRAL", "NOP": "NEUTRAL"
}
```

### Test Script Updates

**Update `scripts/test_team_offensive_types.py` test cases (lines 16-22):**

```python
# Test static classifications (UPDATED FOR 2025-26)
tests = [
    ('GSW', 'MOTION'),
    ('PHX', 'PACE_PUSH'),    # Changed from DAL
    ('UTA', 'PACE_PUSH'),    # Changed from SAC (verify fastest)
    ('MEM', 'HALF_COURT'),   # Changed from MIN (verify slowest)
    ('DAL', 'NEUTRAL'),      # Changed from LAL
    ('BOS', 'HALF_COURT'),   # New test: slow pace, elite offense
]
```

**Update test player examples (lines 44-52):**

```python
# ISO_HEAVY vs PAINT_PACK (UPDATE: use MIA not DAL)
test_player2 = {
    'name': 'Jimmy Butler',  # Changed from Luka
    'team': 'MIA',           # Changed from DAL
    'proj_pts': 23.0,
    'secondary_playtypes': ['ISO_SCORER'],
    'notes': ''
}
calib._apply_offensive_style_boost(test_player2, 'ISO_HEAVY', 'PAINT_PACK')
print(f"ISO_HEAVY vs PAINT_PACK: pts = {test_player2['proj_pts']:.1f} (expected: 22.1)")
```

---

## Part 3: Backtest Verification (20-30 min)

### 3A. 60-Day Backtest (Verify Classifications)

**Create `scripts/backtest_team_styles_60day.py`:**

```python
#!/usr/bin/env python3
"""
60-day backtest to verify team offensive style classifications.
Compares actual pace/ORtg to our OFFENSIVE_STYLES assignments.
"""
import sys
sys.path.insert(0, '.')
import sqlite3
from module_e import LudiCalibrator

def backtest_60_days():
    print("=" * 70)
    print("60-DAY TEAM STYLE VERIFICATION BACKTEST")
    print("=" * 70)
    
    conn = sqlite3.connect('ludi.db')
    cursor = conn.cursor()
    
    # Get actual team pace/ORtg over last 60 days
    cursor.execute("""
        SELECT 
            CASE 
                WHEN home_team = ? THEN home_team 
                ELSE away_team 
            END as team,
            AVG(CASE WHEN home_team = ? THEN home_score ELSE away_score END) as avg_pts,
            COUNT(*) as games
        FROM games
        WHERE date >= date('now', '-60 days')
        AND (home_team = ? OR away_team = ?)
        GROUP BY team
    """)
    
    # TODO: Calculate pace (need possessions data)
    # TODO: Compare to OFFENSIVE_STYLES assignments
    # TODO: Flag mismatches (e.g., PACE_PUSH team with <98 pace)
    
    conn.close()

if __name__ == "__main__":
    backtest_60_days()
```

**Run and analyze:**
```bash
python3 scripts/backtest_team_styles_60day.py
```

**Look for:**
- Teams with pace mismatch (e.g., PACE_PUSH but <100 pace)
- Teams with style change mid-window
- Outliers requiring NEUTRAL classification

### 3B. 14-Day Recent Trends

**Create `scripts/backtest_team_styles_14day.py`:**

```python
#!/usr/bin/env python3
"""
14-day recent trends backtest.
Identifies teams that changed style in last 2 weeks.
"""
import sys
sys.path.insert(0, '.')
import sqlite3

def analyze_recent_trends():
    print("=" * 70)
    print("14-DAY RECENT TRENDS ANALYSIS")
    print("=" * 70)
    
    conn = sqlite3.connect('ludi.db')
    cursor = conn.cursor()
    
    # Compare last 14 days vs prior 46 days (14-60)
    # Look for pace/ORtg changes >5%
    
    teams_to_watch = []
    
    # TODO: Query pace change
    # TODO: Query ORtg change
    # TODO: Flag teams with >5% change
    
    conn.close()
    
    if teams_to_watch:
        print("\n⚠️ TEAMS WITH RECENT STYLE CHANGES:")
        for team in teams_to_watch:
            print(f"  - {team}")
    else:
        print("\n✅ No significant style changes in last 14 days")

if __name__ == "__main__":
    analyze_recent_trends()
```

---

## Part 4: Integration Test

**Run updated test:**
```bash
python3 scripts/test_team_offensive_types.py
```

**Expected Results:**
```
✅ GSW: MOTION (expected: MOTION)
✅ PHX: PACE_PUSH (expected: PACE_PUSH)
✅ UTA: PACE_PUSH (expected: PACE_PUSH)
✅ MEM: HALF_COURT (expected: HALF_COURT)
✅ DAL: NEUTRAL (expected: NEUTRAL)
✅ BOS: HALF_COURT (expected: HALF_COURT)

--- Matchup Tests ---
MOTION vs BLITZ: pts = 21.0 (expected: 21.0)
ISO_HEAVY vs PAINT_PACK: pts = 22.1 (expected: 22.1)
PACE_PUSH vs FUNNEL: pts = 23.3 (expected: 23.3)
```

---

## Success Criteria (Updated)

- [x] `OFFENSIVE_STYLES` dict updated with verified 2025-26 data
- [x] PHX moved from ISO_HEAVY → PACE_PUSH
- [x] DAL moved from ISO_HEAVY → NEUTRAL
- [x] CHI, WAS, UTA moved to PACE_PUSH (fastest teams)
- [x] LAC, BKN, PHI moved to HALF_COURT (slow pace)
- [x] Test script passes with new assignments
- [x] 60-day backtest shows <10% mismatches
- [x] 14-day trends analysis completed

---

## Reference Files

| File | Purpose |
|------|---------|
| `docs/phase2/TEAM_OFFENSIVE_STYLE_RESEARCH_2025-26.md` | Full research summary with citations |
| `PHASE2_TEAM_OFFENSIVE_TYPES_TASK.md` | Updated task doc with verified data |
| `module_e.py` | Your implementation (lines 58-82 need update) |

---

## Deliverables

1. **Updated `module_e.py`** with corrected OFFENSIVE_STYLES
2. **Updated `test_team_offensive_types.py`** with new test cases
3. **60-day backtest results** (summary + any anomalies)
4. **14-day trends report** (teams with recent changes)
5. **Sign-off** that all tests pass

**Priority:** HIGH (data accuracy critical for production)  
**Estimated Time:** 30 minutes for updates + backtests

Good luck! 🚀
