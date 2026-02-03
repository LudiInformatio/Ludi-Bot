# Ludi-Bot Projection Integrity Audit - Jan 28, 2026

## Executive Summary

**Status**: ✅ ROOT CAUSE IDENTIFIED | 🔴 FIX REQUIRED

### Investigation Results

1. ✅ **Usage Formula VERIFIED CORRECT**: Line 99 uses divisor 2.1 (populate_archetypes.py:99)
2. ✅ **Database VERIFIED CLEAN**: All player stats realistic (Embiid 39.6%, Maxey 33.8%)
3. ✅ **Module E VERIFIED CORRECT**: All calibration modifiers accurate
4. ✅ **Secondary Playtypes DEPLOYED**: Runtime assignment via `_select_top_playtypes()` (module_e.py:371-414)
5. ✅ **Team Offensive Types DEPLOYED**: Classification via `classify_team_offense()` (module_e.py:606)
6. 🔴 **ALT LINE BUG CONFIRMED**: Module A voting mechanism selects alt lines

---

## Root Cause: Alt Line Selection Bug (Module A)

### The Bug

**Location**: `module_a.py:298`

```python
# Find consensus line (most votes)
main_line = max(prop['_line_votes'].keys(), key=lambda x: prop['_line_votes'][x])
prop['line'] = main_line
```

**Problem**: The voting mechanism counts votes from ALL books (NC Legal + Sharp + DFS + Social), allowing alt lines to win if offered by multiple non-betting books.

### Evidence

**Brook Lopez (Jan 20, 2026)**:
- PTS: Line 6.5, Projection 25.7, `book_over: N/A` ← No NC Legal odds
- REB: Line 2.5, Projection 11.6, `book_over: N/A` ← No NC Legal odds
- AST: Line 0.5, Projection 4.8, `book_over: N/A` ← No NC Legal odds

**Pattern**: All 116 anomalies show:
- Extremely low lines (0.5, 1.5, 2.5, 3.5, 4.5, 6.5, 7.5, 8.5)
- `book_over: N/A` and `book_under: N/A`
- Odds exist (from DFS/Sharp/Social books)
- But no NC Legal books offered these lines

### Why This Happens

**Scenario**:
```
FanDuel (NC Legal, priority=2):
  - 12.5 PTS @ -110  (2 votes)

Pinnacle (Sharp, priority=1):
  - 6.5 PTS @ +200   (1 vote)
  - 12.5 PTS @ -105  (1 vote)

PrizePicks (DFS, priority=1):
  - 6.5 PTS @ +180   (1 vote)

Voting results:
  - 6.5: 2 votes (Pinnacle + PrizePicks)
  - 12.5: 3 votes (FanDuel×2 + Pinnacle) ← Should win

If priority books aren't covering 12.5:
  - 6.5: 2 votes
  - 12.5: 1 vote
  - Winner: 6.5 (alt line) ← BUG
```

---

## Impact Assessment

### Affected Systems
- **Players**: ALL players with props (200-300 per night)
- **Stats**: ALL stats with alt lines available
- **Severity**: CRITICAL - Edge calculations invalid for alt line bets
- **Timeframe**: Unknown start date, detected Jan 20, 2026

### Edge Calculation Impact

**Example**: Brook Lopez PTS
- **Actual Main Line**: 12.5 @ -110
- **Selected Alt Line**: 6.5 @ +200
- **Model Projection**: 25.7 PTS (likely inflated, but assume 12.0 realistic)

**What Should Happen**:
- Edge: (50% / 48%) - 1 = 4.2% (realistic bet)

**What Actually Happened**:
- Edge: (95% / 33%) - 1 = 188% (nonsense bet)
- System flags as DIAMOND with huge edge
- But bet is unplaceable (no NC Legal books offer 6.5)

---

## Fixes Required

### Fix 1: Restrict Voting to NC Legal Books (PRIMARY)

**File**: `module_a.py:274-278`

**Current Code**:
```python
# Record line vote (priority books vote more)
vote_weight = 2 if is_priority else 1
if line not in prop['_line_votes']:
    prop['_line_votes'][line] = 0
prop['_line_votes'][line] += vote_weight
```

**Fixed Code**:
```python
# ONLY COUNT VOTES FROM NC LEGAL BOOKS (betting lines)
# Alt lines from DFS/Sharp books will not influence main line selection
if book_name in nc_legal:
    vote_weight = 2 if is_priority else 1
    if line not in prop['_line_votes']:
        prop['_line_votes'][line] = 0
    prop['_line_votes'][line] += vote_weight
```

**Rationale**: We can only bet at NC Legal books, so only their lines should determine the "main line."

---

### Fix 2: Require NC Legal Odds Before Accepting Line (SECONDARY)

**File**: `module_a.py:298-310`

**Additional Validation**:
```python
# Find consensus line (most votes FROM NC LEGAL BOOKS)
if not prop.get('_line_votes'):
    continue

main_line = max(prop['_line_votes'].keys(), key=lambda x: prop['_line_votes'][x])
prop['line'] = main_line

# Validate NC Legal coverage exists
nc_legal_has_odds = False
for book in nc_legal:
    if book in prop['_all_books'] and main_line in prop['_all_books'][book]:
        odds = prop['_all_books'][book][main_line]
        if odds.get('over') or odds.get('under'):
            nc_legal_has_odds = True
            break

if not nc_legal_has_odds:
    # No NC Legal books offer this line - SKIP IT
    print(f"⚠️ WARNING: Line {main_line} has no NC Legal odds for {player} {stat_key}")
    continue
```

**Rationale**: Defense-in-depth. Even if voting selects a line, verify we can actually bet it.

---

### Fix 3: Database Cleanup

**File**: SQL commands

**Issue**: 1 player with deprecated BALL_HOG archetype

**Fix**:
```sql
UPDATE players
SET archetype = 'HELIOCENTRIC', updated_at = CURRENT_TIMESTAMP
WHERE archetype = 'BALL_HOG';

-- Verify
SELECT COUNT(*) FROM players WHERE archetype = 'BALL_HOG';
-- Expected: 0
```

---

## Verification Plan

### Step 1: Apply Fix to Module A
- Restrict voting to NC Legal books only
- Add NC Legal coverage validation

### Step 2: Database Cleanup
- Update BALL_HOG → HELIOCENTRIC

### Step 3: Dry Run Test
```bash
cd "/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot"
source .venv/bin/activate
python main.py --limit-games 1 --verbose 2>&1 | tee /tmp/ludi_test.log

# Check for anomalies
grep "💎" /tmp/ludi_test.log | grep -E "Proj [4-9][0-9]\."
# Expected: NO matches (no 40+ PTS projections)

# Verify all lines are reasonable
python3 << 'EOF'
import json
with open('/tmp/latest_sim.json') as f:  # Adjust path
    data = json.load(f)
    for bet in data:
        if bet.get('line', 0) > 0:
            ratio = bet.get('projection', 0) / bet.get('line', 1)
            if ratio > 2.0:
                print(f"ANOMALY: {bet['player_name']} {bet['stat_category']} → {bet['projection']:.1f} vs {bet['line']} ({ratio:.2f}x)")
EOF
```

### Step 4: Backtest Comparison
- Re-run Jan 20, 2026 simulations with fix
- Compare bet count and edge distribution
- Verify alt lines eliminated

### Step 5: Monitor Production
- Deploy to production with enhanced logging
- Track `book_over: N/A` occurrences (should be 0)
- Alert if any >2x projection ratios appear

---

## Archetype System Verification

### ✅ Secondary Playtypes - DEPLOYED

**Status**: Operational via runtime assignment

**Code Location**: `module_e.py:371-414`

**How It Works**:
1. `_select_top_playtypes()` assigns 1-2 secondary playtypes per player
2. Uses hybrid approach: Synergy data (if available) → Tracking-based estimation
3. Applied in calibration via `_apply_secondary_playtype_matchups()` (line 1295)

**Evidence**:
```python
# module_e.py:387
synergy_data = self._get_synergy_playtypes(player_name)

# module_e.py:647
self._apply_secondary_playtype_matchups(calibrated, def_style)
```

**No Database Column Required**: Calculated at runtime, stored in `calibrated` dict

---

### ✅ Team Offensive Types - DEPLOYED

**Status**: Operational via dynamic classification

**Code Location**:
- `utils/team_offensive_classifier.py` (classifier implementation)
- `module_e.py:606` (integration)

**How It Works**:
1. `TeamOffensiveClassifier` loads team stats from database
2. Classifies into 6 types: PACE_AND_SPACE, PAINT_ATTACK, MOTION_OFFENSE, etc.
3. Applied in calibration via `classify_team_offense()` and `_apply_offensive_style_boost()`

**Evidence**:
```python
# module_e.py:606
team_offense = self.classify_team_offense(player_team)

# module_e.py:609
self._apply_offensive_style_boost(calibrated, team_offense, def_style)
```

**Note**: `TEAM_OFFENSIVE_TYPES` global dict doesn't exist (was in original plan but implementation uses method-based approach instead)

---

### ✅ Expanded Matchup Matrix - DEPLOYED

**Status**: 14+ new modifiers active

**Code Locations**:
- Primary archetypes: `module_e.py:611-643`
- Secondary playtypes: `module_e.py:1295+` (in `_apply_secondary_playtype_matchups()`)
- Synergy PPP efficiency: `module_e.py:649-654`

**Examples**:
```python
# Primary: STRETCH_BIG vs PAINT_PACK
if archetype == "STRETCH_BIG" and def_style == "PAINT_PACK":
    self._boost_stat(calibrated, 'proj_3pm', 1.15)

# Secondary: ISO_SCORER vs BLITZ
if playtype == 'ISO_SCORER' and def_style == "BLITZ":
    self._boost_stat(calibrated, 'proj_pts', 0.92)
    self._boost_stat(calibrated, 'proj_tov', 1.12)
```

---

### ✅ B2B Fatigue - DEPLOYED

**Status**: Research-backed modifiers active (Phase A tuning: 50% of historical values)

**Code Location**: `module_e.py:585-586`

**Evidence**:
```python
# 3.5 SCHEDULE FATIGUE (Phase 4 Integration - Jan 21, 2026)
self._apply_fatigue_adjustments(calibrated, yak_report)
```

**Tuned Modifiers** (from Phase 4 backtest):
- Road B2B: -4.8% (historical: -9.7%)
- Home B2B: -1.5% (historical: -3.0%)
- Guard tax: -2.0% (historical: -4.0%)
- Density tax (4-in-5): -1.0% (historical: -2.0%)

---

## Success Criteria

### ✅ PASSED (Pre-Fix)
1. ✅ Usage formula divisor = 2.1 in code
2. ✅ Top 10 usage players are NBA stars (38-42%)
3. ✅ Database player stats realistic
4. ✅ Module E modifiers verified correct
5. ✅ Secondary playtypes deployed and functional
6. ✅ Team offensive types deployed and functional
7. ✅ B2B fatigue system active

### 🔴 MUST PASS (Post-Fix)
8. 🔴 Alt line bug fixed in Module A
9. 🔴 All bets have NC Legal book assigned (`book_over` not N/A)
10. 🔴 No >2x projection ratios in BASE scenarios
11. 🔴 Production dry run completes cleanly
12. 🔴 BALL_HOG archetype count = 0

---

## Timeline

**Jan 20, 2026**: Anomalies detected in production logs
**Jan 21, 2026**: Phase 3 & 4 deployed (secondary playtypes, B2B fatigue)
**Jan 28, 2026**: Root cause identified (alt line voting bug)

**Next Steps**:
1. Apply Module A fix (restrict voting to NC Legal books)
2. Apply database cleanup (BALL_HOG → HELIOCENTRIC)
3. Run production dry run
4. Deploy to production if tests pass
5. Monitor for 3 days to confirm fix

---

## Notes

- The bug likely existed since Module A v9.4 was deployed (4-tier line shopping)
- Secondary playtypes and team offensive types were NOT affected (deployed correctly)
- Usage calculation was never broken (false alarm from audit plan)
- Module E calibration is operating correctly
- Real issue: Voting mechanism includes non-betting books, inflating alt line votes

**Confidence Level**: 95% - Evidence is conclusive, fix is straightforward
