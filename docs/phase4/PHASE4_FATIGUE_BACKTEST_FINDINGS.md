# Phase 4: B2B Fatigue - 21-Day Backtest Findings

**Date:** January 21, 2026
**Analysis Window:** Dec 31, 2025 - Jan 21, 2026 (21 days)
**Sample Size:** 2,646 player-games (10+ minutes)
**Status:** ⚠️ **MODIFIERS NEED TUNING**

---

## Executive Summary

The 21-day backtest **confirms** the anomalous finding from the Dec 20-Jan 16 backtest: **B2B players are OUTPERFORMING** predictions across all scenarios.

**Key Finding:** B2B players averaged **+1.40 pts** above prediction vs **+0.25 pts** for normal rest players, a **+1.15 pt differential** suggesting current fatigue penalties are **TOO AGGRESSIVE** for the 2025-26 season.

---

## Results by Scenario

### 1. Road B2B Guards
| Metric | Value | Assessment |
|--------|-------|------------|
| **Sample Size** | 16 games | Small sample ⚠️ |
| **Current Modifier** | -9.76% (-6% Road B2B, -4% Guard Tax) | |
| **Mean Error** | +1.78 pts | **UNDER-PROJECTION** |
| **Over-Projection %** | 62.5% | Players beat projection 62.5% of time |
| **RMSE** | 8.15 pts | High variance (small sample) |

**Recommendation:** Reduce penalty from **-9.76% to ~-2.6%**
**Rationale:** Players are consistently outperforming, suggesting either:
- Modern NBA rest protocols are effective
- Guards are more resilient than research suggests
- 2025-26 pace/style mitigates fatigue

---

### 2. Home B2B Guards
| Metric | Value | Assessment |
|--------|-------|------------|
| **Sample Size** | 125 games | **Reliable sample** ✅ |
| **Current Modifier** | -6.88% (-3% Home B2B, -4% Guard Tax) | |
| **Mean Error** | +2.26 pts | **UNDER-PROJECTION** |
| **Over-Projection %** | 58.4% | Consistently beat projection |
| **RMSE** | 7.25 pts | Moderate variance |

**Recommendation:** Reduce penalty from **-6.88% to ~-2.0%**
**Rationale:** 125-game sample is statistically significant. +2.26 pts error is substantial for a 25 PPG player (~9% error).

---

### 3. Road B2B Non-Guards (Bigs)
| Metric | Value | Assessment |
|--------|-------|------------|
| **Sample Size** | 21 games | Small sample ⚠️ |
| **Current Modifier** | -6.0% (Road B2B only, no Guard Tax) | |
| **Mean Error** | +3.40 pts | **LARGEST UNDER-PROJECTION** |
| **Over-Projection %** | 71.4% | Overwhelmingly beat projection |
| **RMSE** | 6.69 pts | |

**Recommendation:** Reduce penalty from **-6.0% to 0%** (eliminate Road B2B tax for bigs)
**Rationale:** +3.40 pts error is massive. Big men appear UNAFFECTED by road B2B fatigue in modern NBA.

---

### 4. Home B2B Non-Guards (Bigs)
| Metric | Value | Assessment |
|--------|-------|------------|
| **Sample Size** | 295 games | **Very Reliable** ✅ |
| **Current Modifier** | -3.0% (Home B2B) | |
| **Mean Error** | +0.87 pts | **BEST B2B CALIBRATION** |
| **Over-Projection %** | 52.2% | Nearly balanced |
| **RMSE** | 5.93 pts | Low variance |

**Recommendation:** Reduce penalty from **-3.0% to -1.5%**
**Rationale:** Error is within acceptable range but still positive. Minor adjustment to align with data.

---

### 5. Rested Home (3+ Days Rest)
| Metric | Value | Assessment |
|--------|-------|------------|
| **Sample Size** | 353 games | **Very Reliable** ✅ |
| **Current Modifier** | +3.0% boost | |
| **Mean Error** | **-0.28 pts** | **🎯 EXCELLENT CALIBRATION** |
| **Over-Projection %** | 45.3% | Slightly conservative |
| **RMSE** | 5.79 pts | Low variance |

**Recommendation:** **KEEP AS-IS** (+3.0% boost)
**Rationale:** -0.28 pts error is nearly perfect. This modifier is working exactly as intended.

---

### 6. Schedule Density (4-in-5 Nights)
| Metric | Value | Assessment |
|--------|-------|------------|
| **Sample Size** | 563 games | **Very Reliable** ✅ |
| **Current Modifier** | -2.0% density tax | |
| **Mean Error** | +0.63 pts | **SLIGHTLY UNDER-PROJECTION** |
| **Over-Projection %** | 51.7% | Balanced |
| **RMSE** | 5.89 pts | Low variance |

**Recommendation:** Reduce penalty from **-2.0% to -1.0%**
**Rationale:** Players are slightly outperforming. Halving the penalty aligns with observed data.

---

### 7. Normal Rest (Control Group)
| Metric | Value | Assessment |
|--------|-------|------------|
| **Sample Size** | 1,273 games | **Baseline** |
| **Current Modifier** | None (0%) | |
| **Mean Error** | +0.25 pts | **BASELINE PROJECTION** |
| **Over-Projection %** | 50.1% | Perfect balance |
| **RMSE** | 6.10 pts | Standard variance |

**Status:** Control group shows near-perfect calibration (+0.25 pts).

---

## Overall Assessment

### B2B vs Normal Rest Comparison

| Metric | B2B Players (All) | Normal Rest | Differential |
|--------|-------------------|-------------|--------------|
| **Sample Size** | 457 games | 1,273 games | - |
| **Mean Error** | **+1.40 pts** | +0.25 pts | **+1.15 pts** |
| **Over-Projection %** | 56.2% | 50.1% | +6.1% |

**Interpretation:**
- B2B players are outperforming by **+1.15 pts** compared to normal rest
- This suggests current B2B penalties are **overstated** for the 2025-26 NBA season
- Difference is **statistically significant** (457 B2B games is robust sample)

---

## Recommendations

### Immediate Actions (High Confidence)

1. **✅ Keep Rested Home Boost (+3.0%)**
   - Performing excellently (-0.28 pts error)
   - 353-game sample confirms accuracy

2. **⚠️ Reduce Home B2B Non-Guard Penalty**
   - Current: -3.0% → **Recommended: -1.5%**
   - Largest sample (295 games), +0.87 pts error
   - High confidence adjustment

3. **⚠️ Reduce Home B2B Guard Penalty**
   - Current: -6.88% → **Recommended: -2.0%**
   - 125-game sample, +2.26 pts error
   - Guard-specific tax appears invalid

### Moderate Confidence Actions

4. **⚠️ Reduce Schedule Density Tax**
   - Current: -2.0% → **Recommended: -1.0%**
   - 563-game sample, +0.63 pts error
   - Minor adjustment needed

### Low Confidence Actions (Small Samples)

5. **⚠️ Road B2B Guards (n=16 games)**
   - Current: -9.76% → **Consider: -2.6%**
   - Small sample, monitor for more data

6. **⚠️ Road B2B Non-Guards (n=21 games)**
   - Current: -6.0% → **Consider: 0.0%**
   - Small sample, large error (+3.40 pts)
   - May need elimination of penalty

---

## Research Context: Why the Discrepancy?

The **García et al. (2020)** research showing -1.27 effect size in Q4 of B2B games is sound, but may not apply to 2025-26 NBA due to:

### Possible Explanations

1. **Modern Rest Protocols**
   - Teams now have sports science departments
   - Load management, cryotherapy, recovery tech
   - Better sleep/nutrition protocols

2. **Schedule Changes**
   - NBA reduced back-to-backs from 18.3/team (2014) to 13.3/team (2023)
   - Players are more accustomed to spacing

3. **Pace & Style Evolution**
   - 2025-26 pace may be faster but less physical
   - Less post-up grinding, more perimeter play
   - Reduced contact → less cumulative fatigue

4. **Sample Timing**
   - Dec 31-Jan 21 is mid-season (peak conditioning)
   - Research may have studied early-season or playoffs
   - Seasonal conditioning curve matters

5. **Survivorship Bias**
   - Players who can't handle B2Bs get load managed (DNP-REST)
   - Only healthy, resilient players play B2Bs
   - Our data only sees successful B2B performances

---

## Implementation Plan

### Phase A: Conservative Adjustment (Recommended)

Apply **50% reduction** to all B2B penalties (preserve research basis but align with data):

| Scenario | Current | Proposed | Change |
|----------|---------|----------|--------|
| Road B2B Guard | -9.76% | **-4.88%** | Cut in half |
| Road B2B Non-Guard | -6.0% | **-3.0%** | Cut in half |
| Home B2B Guard | -6.88% | **-3.44%** | Cut in half |
| Home B2B Non-Guard | -3.0% | **-1.5%** | Cut in half |
| Density 4-in-5 | -2.0% | **-1.0%** | Cut in half |
| Rested Home | +3.0% | **+3.0%** | Keep as-is |

**Rationale:** Conservative approach preserves research foundation while acknowledging modern NBA reality.

### Phase B: Data-Driven Adjustment (Aggressive)

Apply **full correction** based on observed errors:

| Scenario | Current | Error | Proposed |
|----------|---------|-------|----------|
| Road B2B Guard | -9.76% | +1.78 pts | **-2.6%** |
| Road B2B Non-Guard | -6.0% | +3.40 pts | **0.0%** |
| Home B2B Guard | -6.88% | +2.26 pts | **-2.0%** |
| Home B2B Non-Guard | -3.0% | +0.87 pts | **-1.5%** |
| Density 4-in-5 | -2.0% | +0.63 pts | **-1.0%** |
| Rested Home | +3.0% | -0.28 pts | **+3.0%** |

**Rationale:** Fully trust the data. Risk: May overfit to recent 21-day window.

---

## Monitoring Plan

### Short-Term (Next 14 Days)

- Run weekly backtests to validate adjustments
- Track B2B vs Normal Rest differential
- Alert if mean error exceeds ±1.5 pts for any scenario

### Long-Term (Season)

- Accumulate 60+ games per scenario for statistical power
- Re-calibrate at All-Star Break (Feb 16, 2026)
- Document seasonal trends (are early-season B2Bs worse?)

---

## Files Modified

1. **module_e.py** - `_apply_fatigue_adjustments()` method ready for tuning
2. **scripts/backtest_fatigue_21day.py** - Comprehensive backtest framework
3. **PHASE4_FATIGUE_BACKTEST_FINDINGS.md** - This report

---

## Next Steps

1. **Decide on adjustment strategy:** Conservative (Phase A) vs Aggressive (Phase B)
2. **Update module_e.py** with new modifiers
3. **Run validation backtest** to confirm improvements
4. **Deploy to production** with monitoring
5. **Schedule follow-up analysis** at All-Star Break

---

**Conclusion:** The research-backed fatigue penalties do NOT match 2025-26 NBA reality. Modern rest protocols, schedule improvements, and survivorship bias likely explain the discrepancy. **Recommendation: Implement Phase A (50% reduction) immediately, monitor, and iterate.**
