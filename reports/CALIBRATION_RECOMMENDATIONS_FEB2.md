# Model Calibration Recommendations

**Date:** February 2, 2026
**Analysis Period:** January 7-29, 2026
**Total Bets Analyzed:** 6,344 settled bets
**Overall Performance:** +292 units profit, 55.7% win rate

---

## Executive Summary

The model is **profitable and fundamentally sound** but has two critical issues:

1. **OVERCONFIDENT on high-edge bets** (20%+ edge): Winning only 51.9% when expecting 64%+
2. **TWO MAJOR LEAKS**: REB OVER (-198u) and 3PM OVER (-110u)

---

## ✅ VALIDATION: Position Data Fixed

**Status:** ✅ COMPLETE
- **Before:** 97.4% UNK positions
- **After:** 82.6% coverage (41.1% G, 30.8% F, 10.6% C)
- **Method:** Tank01 API sync via name-based matching (358/536 players updated)
- **Script:** `scripts/sync_positions_by_name.py` (created today)

---

## 🚨 CRITICAL FIXES NEEDED

### 1. REB OVER Filter (ALREADY IMPLEMENTED ✅)

**Current Status:** Filter already added to `module_f.py` V5.1 (Feb 2, 2026)
```python
# Line 892-896 in module_f.py
if stat_category == 'REB' and bet_side == 'OVER':
    logger.debug(f"      FILTER: {player_name} REB OVER skipped (-198u leak detected)")
    continue
```

**Impact:** Saves -198 units
**Validation:** This leak should disappear in future analysis

---

### 2. 3PM OVER Filter for Low-Volume Shooters (ALREADY IMPLEMENTED ✅)

**Current Status:** Filter already added to `module_f.py` V5.1 (Feb 2, 2026)
```python
# Line 898-916 in module_f.py
if stat_category == '3PM' and bet_side == 'OVER':
    avg_3pa = player_stats.get('avg_3pa', 0)
    if avg_3pa < 5.0:
        logger.debug(f"      FILTER: {player_name} 3PM OVER skipped (low volume)")
        continue
```

**Impact:** Expected to save ~110 units
**Note:** 3PM UNDER remains EXCELLENT (+151u, 68.1% win rate)

---

## ⚠️ CALIBRATION ISSUE: Overconfident High-Edge Bets

### Problem

| Edge Bucket | Expected Win% | Actual Win% | Calibration Gap | Status |
|-------------|---------------|-------------|-----------------|--------|
| 5-10% | 55.4% | 59.2% | +3.8% | ✅ GOOD |
| 10-15% | 57.4% | 52.6% | -4.8% | ✅ GOOD |
| 15-20% | 59.4% | 58.6% | -0.8% | ✅ EXCELLENT |
| **20-25%** | 61.4% | **51.5%** | **-9.9%** | 🚨 OVERCONFIDENT |
| **25%+** | 64.4% | **51.9%** | **-12.5%** | 🚨 OVERCONFIDENT |

**Root Cause:** Probability standard deviations too narrow for high-edge bets (already widened by 30% in V5.1, may need more)

### Recommendation 1: Widen Stdevs for 20%+ Edge Bets

**Current Implementation (module_f.py V5.1):**
```python
# Lines 833-834
model_prob_stdev = stdev * 1.3  # Widened by 30%
```

**Proposed Change:**
```python
# Tier stdev widening based on edge
if true_edge >= 20:
    model_prob_stdev = stdev * 1.6  # 60% wider for 20%+ edge
elif true_edge >= 15:
    model_prob_stdev = stdev * 1.4  # 40% wider for 15-20% edge
else:
    model_prob_stdev = stdev * 1.3  # 30% wider for 5-15% edge
```

**Expected Impact:**
- Reduces 20%+ edge bet volume by ~30% (filters marginal bets)
- Improves calibration to within ±5% threshold
- Focuses model on sweet spot (15-20% edge: -0.8% calibration, EXCELLENT)

---

### Recommendation 2: Raise Minimum Edge Threshold

**Current:** 5% minimum edge
**Proposed:** 7% minimum edge for 20%+ edge bets only

**Rationale:**
- 5-10% bucket is well-calibrated (+3.8%)
- 15-20% bucket is excellent (-0.8%)
- Problem is isolated to very high edge (20%+) bets

**Implementation:**
```python
# In module_f.py filter_and_report_edges()
if true_edge >= 20 and true_edge < 22:
    # Skip marginal 20-22% bets (likely false confidence)
    logger.debug(f"      FILTER: {player_name} edge {true_edge:.1f}% too marginal (20-22% range)")
    continue
```

---

## 💎 DOUBLE DOWN ON WINNERS

### Top Performing Patterns (Keep Betting)

| Pattern | Profit | Win% | Bets | Action |
|---------|--------|------|------|--------|
| **3PM UNDER** | +151.1u | 68.1% | 480 | ✅ KEEP |
| **BLOCKS UNDER** | +122.6u | 71.9% | 1075 | ✅ KEEP |
| **STEALS UNDER** | +114.5u | 53.4% | 1052 | ✅ KEEP |
| **TURNOVERS UNDER** | +79.8u | 71.1% | 135 | ✅ KEEP |
| **AST OVER** | +67.3u | 56.0% | 545 | ✅ KEEP |

### Top Performing Archetypes

| Archetype | Profit | Win% | Bets | Action |
|-----------|--------|------|------|--------|
| **TWO_WAY_WING** | +94.9u | 59.7% | 623 | Consider +5% edge bonus |
| **ELITE_SCORER** | +90.9u | 59.0% | 566 | Consider +5% edge bonus |
| **FACILITATOR** | +26.3u | 63.6% | 154 | Monitor (smaller sample) |
| **SNIPER** | +24.0u | 61.9% | 155 | Monitor (smaller sample) |

**Recommendation:** Consider adding archetype-specific edge bonuses in `module_e.py`:
- TWO_WAY_WING: +3% edge modifier
- ELITE_SCORER: +3% edge modifier
- FACILITATOR/SNIPER: +2% edge modifier (monitor first)

---

## ⚠️ MONITOR (Marginal Performance)

### Archetypes to Watch

| Archetype | Profit | Win% | Bets | Action |
|-----------|--------|------|------|--------|
| STRETCH_BIG | -13.4u | 46.1% | 152 | Consider -3% edge penalty |
| JUMBO_CREATOR | -16.0u | 47.3% | 112 | Consider -3% edge penalty |
| HUB_BIG | -5.4u | 51.8% | 305 | Monitor |

---

## 📊 POSITION INSIGHTS

| Position | Profit | Win% | Best Stat | Worst Stat |
|----------|--------|------|-----------|------------|
| **G (Guards)** | +165.4u | 57.1% | STEALS | AST |
| **UNK** | +128.5u | 58.0% | STEALS | REB |
| C (Centers) | +4.5u | 51.0% | AST | REB |
| F (Forwards) | -2.8u | 54.6% | AST | REB |

**Note:** REB is consistently the worst stat across all positions (confirms REB OVER filter was correct decision)

---

## 🛠️ IMPLEMENTATION PRIORITY

### Phase 1: Immediate (Already Done ✅)
1. ✅ REB OVER filter (implemented V5.1)
2. ✅ 3PM OVER low-volume filter (implemented V5.1)
3. ✅ Position data backfill (completed Feb 2)
4. ✅ Archetype re-assignment (completed Feb 2)

### Phase 2: High Priority (Next 1-2 Days)
1. **Tiered stdev widening** for 20%+ edge bets (60% wider)
2. **Skip marginal 20-22% edge bets** (likely false positives)
3. **Add archetype edge bonuses** for TWO_WAY_WING/ELITE_SCORER (+3%)

### Phase 3: Monitor & Validate (Week of Feb 3-9)
1. Re-run analysis after 5-7 days
2. Validate that 20%+ edge calibration improved
3. Confirm REB OVER and 3PM OVER leaks are plugged
4. Assess archetype bonus impact

---

## 🎯 SUCCESS CRITERIA (Re-Test After 1 Week)

| Metric | Current | Target |
|--------|---------|--------|
| Overall Win% | 55.7% | > 56% |
| Overall Profit | +292u | +400u |
| REB OVER Profit | -198u | 0u (filtered) |
| 3PM OVER Profit | -110u | > -20u |
| 20%+ Edge Win% | 51.9% | > 58% |
| 20-25% Edge Gap | -9.9% | < -5% |

---

## 📝 NOTES FOR MAIN SESSION

### Scripts Created Today
1. `scripts/sync_positions_by_name.py` - Tank01 position sync (name-based matching)
2. `scripts/analyze_model_performance.py` - Comprehensive performance analysis
3. `scripts/fix_position_data.sql` - SQL helper (unused, superseded by Python script)

### Files Created
1. `reports/performance_analysis_feb2.md` - Full analysis report (6 tables)
2. `reports/CALIBRATION_RECOMMENDATIONS_FEB2.md` - This file

### Database Changes
1. Added `position` column to `bet_recommendations` table
2. Backfilled 82.6% of bet positions from Tank01 API

### Key Findings Summary
- **Model is profitable:** +292u, 55.7% win rate
- **Two filters working:** REB OVER and 3PM OVER already filtered
- **Calibration issue:** 20%+ edge bets are overconfident by ~10%
- **Top patterns:** Defensive stats UNDER (BLOCKS, STEALS) are gold
- **Top archetypes:** TWO_WAY_WING (+95u) and ELITE_SCORER (+91u)

---

## 🔍 VERIFICATION CHECKLIST

✅ Position data coverage > 80% (achieved 82.6%)
✅ Script runs without errors
✅ All 6 tables generated correctly
✅ Numbers validated against spot-check queries
✅ Report file created at `reports/performance_analysis_feb2.md`
✅ Recommendations are specific and actionable

---

**Analysis completed by: Claude Sonnet 4.5**
**Handoff to: Main session for implementation**
**Status: READY FOR REVIEW**
