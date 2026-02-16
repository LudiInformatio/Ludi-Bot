# Part 1 Summary: Existing Backtest Scripts Analysis

**Generated:** 2026-02-15
**Status:** ✅ COMPLETE

---

## Overview

Part 1 involved fixing and running two existing backtest scripts:
1. `backtest_fatigue_21day.py` - Updated to V5.2 fatigue modifiers
2. `backtest_playtype_trends_14day.py` - Enhanced with performance metrics

Both scripts now include markdown report generation capabilities.

---

## Part 1A: Fatigue Backtest Results

**Script:** `scripts/backtest_fatigue_21day.py`
**Report:** `reports/fatigue_trends_2026-02-15.md`
**Test Window:** Last 21 days (Jan 25 - Feb 15, 2026)
**Sample Size:** 2,484 player-games

### Changes Applied

Updated to V5.2 modifier values:
- Road B2B: 0.94 → **0.952** (-4.8%, was -6%)
- Home B2B: 0.97 → **0.985** (-1.5%, was -3%)
- Guard Tax: 0.96 → **0.98** (-2%, was -4%)
- Density (4-in-5): 0.99 (-1%, unchanged)

### Key Findings

| Scenario | N | Mean Error | RMSE | Status |
|----------|---|------------|------|--------|
| **Home B2B Guards** | 138 | **+3.05 pts** | 7.64 | ⚠️ UNDER-PROJECTION |
| Home B2B Non-Guards | 340 | +1.52 pts | 6.28 | Slight under-proj |
| **Rested Home (3+ days)** | 432 | **-0.35 pts** | 5.91 | ✅ WELL-CALIBRATED |
| Density (4-in-5) | 480 | +0.80 pts | 6.33 | Acceptable |
| Normal Rest | 1,094 | +0.69 pts | 6.28 | Acceptable |

### Critical Issue: Home B2B Guards

**Problem:** Home B2B Guards are outperforming projections by +3.05 pts (65.2% over-projection rate)

**Current Modifier:** -3.5% total (-1.5% B2B Home + -2% Guard Tax)

**Recommendation:**
- Current V5.2 modifiers may be TOO CONSERVATIVE for home B2B guards
- Consider increasing penalty OR investigating if modern guards handle home B2Bs better than expected
- Further investigation needed with larger sample (138 games may be insufficient)

### Overall Assessment

✅ **B2B vs Normal Rest difference: 1.3 pts (reasonable)**
- B2B Players (All): +1.96 pts mean error (n=478)
- Normal Rest: +0.69 pts mean error (n=1,094)

**Interpretation:** The 1.3 pt difference suggests V5.2 fatigue penalties are slightly under-aggressive, but within acceptable range (<2.0 pts threshold).

---

## Part 1B: Playtype Trends Results

**Script:** `scripts/backtest_playtype_trends_14day.py`
**Report:** `reports/playtype_trends_2026-02-15.md`
**Analysis Period:** Last 14 days (Feb 1-15, 2026)
**Sample Size:** 180 recent team-games vs 236 baseline games

### Defensive Style Frequency Trends

No significant shifts detected (all changes <5%):

| Defense Style | Recent % | Baseline % | Trend |
|---------------|----------|------------|-------|
| NEUTRAL | 37.2% | 34.7% | +2.5% (stable) |
| FUNNEL | 20.0% | 21.2% | -1.2% (stable) |
| PAINT_PACK | 17.2% | 16.1% | +1.1% (stable) |
| BLITZ | 12.8% | 14.8% | -2.1% (stable) |
| HACKERS | 10.0% | 10.2% | -0.2% (stable) |
| PERIMETER | 2.8% | 3.0% | -0.2% (stable) |

**Conclusion:** No recent shifts in defensive scheme deployment. The matchup matrix remains stable.

### Performance Metrics by Defensive Scheme

**NEW Enhancement:** Script now joins with `bet_recommendations` table to calculate:
- Hit rate per defensive scheme
- ROI (profit/loss) per scheme
- Net profit in units

| Defensive Scheme | Bets | Win Rate | ROI | Net Profit | Status |
|------------------|------|----------|-----|------------|--------|
| **vs_NEUTRAL** | 1,882 | 58.9% | **+3.9%** | **+74.31u** | ✅ BEST |
| vs_HACKERS | 454 | 60.1% | +3.0% | +13.43u | ✅ Profitable |
| vs_PERIMETER | 414 | 56.6% | +1.1% | +4.74u | ➡️ Marginal |
| vs_BLITZ | 1,014 | 55.8% | -1.3% | -13.08u | ➡️ Marginal loss |
| vs_PAINT_PACK | 1,028 | 51.7% | -4.7% | -48.59u | ⚠️ Losing |
| **vs_FUNNEL** | 1,178 | 49.6% | **-8.9%** | **-105.13u** | 🚨 WORST |

### Critical Finding: vs_FUNNEL Bets Are Bleeding Units

**Problem:** Bets against FUNNEL defenses are the worst performers:
- 1,178 bets placed (2nd highest volume)
- Only 49.6% win rate (below 52% target)
- -8.9% ROI (worst of all schemes)
- **-105.13 units lost** (largest loss)

**Current Matchup Modifiers:**
- ISO_SCORER vs FUNNEL: No penalty
- TRANSITION vs FUNNEL: +15% boost (may be over-aggressive)

**Recommendation:**
- Audit Module E matchup matrix for FUNNEL defense
- Consider reducing or removing TRANSITION boost vs FUNNEL
- Investigate if FUNNEL defenses are misclassified or matchup modifiers are incorrect

### Best Performer: vs_NEUTRAL

**Insight:** Bets against NEUTRAL defenses are the most profitable:
- 1,882 bets (largest volume)
- 58.9% win rate (strong)
- +3.9% ROI
- **+74.31 units profit**

**Interpretation:** The model performs best when defensive scheme modifiers are NOT applied. This suggests:
1. NEUTRAL classification is accurate
2. Base projections (Module C) are strong
3. Defensive scheme modifiers may be introducing noise rather than signal

---

## Part 1 Deliverables

✅ **Scripts Updated:**
- `scripts/backtest_fatigue_21day.py` - V5.2 modifiers + markdown reporting
- `scripts/backtest_playtype_trends_14day.py` - Enhanced with performance metrics + markdown reporting

✅ **Reports Generated:**
- `reports/fatigue_trends_2026-02-15.md`
- `reports/playtype_trends_2026-02-15.md`

✅ **Key Findings:**
1. **Home B2B Guards** under-projecting by +3.05 pts (needs investigation)
2. **vs_FUNNEL bets** losing -105.13u over 14 days (critical issue)
3. **vs_NEUTRAL bets** are most profitable (+74.31u, 58.9% WR)
4. **Rested Home boost** is well-calibrated (-0.35 pts mean error)

---

## Next Steps (Part 2-4)

**Part 2:** Create `analyze_14day_trends.py` - Statistical analysis of recent bet performance
**Part 3:** Create `validate_archetypes_vs_synergy.py` - Cross-validate archetype assignments vs Synergy data
**Part 4:** Generate master trend report combining all findings

---

*Generated by Claude Code - Phase 7.9 Backtest Audit (Part 1 Complete)*
