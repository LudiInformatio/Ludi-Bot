# Model Performance Analyzer Enhancement Summary

**Date:** February 15, 2026
**Version:** V2.0
**Script:** `scripts/analyze_model_performance.py`

---

## What Was Done

### 1. Script Migration
- ✅ Moved from `scripts/archive/` to `scripts/analyze_model_performance.py`
- ✅ Enhanced from 6 tables to 10+ comprehensive analyses

### 2. Core Fixes

#### VOID Bet Exclusion
- **Issue:** Original script included VOID bets (actual_result = -999 or -998)
- **Fix:** Added `WHERE actual_result >= 0` filter in SQL query
- **Impact:** Reduced dataset from 15,575 to 14,423 bets (1,152 VOIDs excluded)

#### Sample Size Filter
- **Issue:** No minimum bet threshold for segment reporting
- **Fix:** Added `MIN_SAMPLE_SIZE = 100` for stat categories, positions, archetypes, cross-cuts
- **Impact:** Removes noise from low-sample segments

#### Edge Bucket Expected Win%
- **Issue:** Used rough formula instead of actual model probabilities
- **Fix:** Now calculates `AVG(model_prob)` per bucket for true calibration
- **Impact:** Reveals 25%+ edge bucket is severely overconfident (-23.8% vs expected)

#### Console Output
- **Status:** Already existed, enhanced with new tables

### 3. New Analysis Tables

#### Table 7: Spread Buckets
Analyzes performance based on game competitiveness:
- Heavy Fav (<-7): 2,727 bets, 54.6% win rate, -35.4 units
- Mod Fav (-7 to -3): 2,303 bets, 56.5% win rate, **+172.3 units** ✅
- Toss-Up (-3 to +3): 4,258 bets, 53.3% win rate, -213.2 units
- Mod Dog (+3 to +7): 2,557 bets, 55.3% win rate, +76.2 units
- Heavy Dog (>+7): 2,578 bets, 55.5% win rate, -3.2 units

**Insight:** Moderate favorites are the sweet spot (+172.3 units).

#### Table 8: Total Buckets
Analyzes performance by pace/scoring environment:
- Low (<218): 14,416 bets, 54.8% win rate, -7.7 units
- Normal (218-228): 4 bets, 100% win rate (too small)
- Moderate (228-238): 3 bets, 33.3% win rate (too small)
- High (>238): 0 bets

**Insight:** Nearly all bets are in low-total games (<218). Bucket thresholds may need adjustment.

#### Table 9: Home vs Away
- Home: 7,516 bets, 55.3% win rate, **+90.1 units** ✅
- Away: 6,907 bets, 54.2% win rate, -93.5 units

**Insight:** Significant home/away split. Model performs better on home teams.

#### Table 10: Archetype × Stat Cross-Cuts
Top performers (100+ bet minimum):
- ELITE_SCORER × STEALS: 138 bets, **75.4% win rate, +98.5 units** 🔥
- TWO_WAY_WING × STEALS: 129 bets, 48.8% win rate, +28.0 units
- UNKNOWN × 3PM: 101 bets, 59.4% win rate, +22.1 units
- TWO_WAY_WING × AST: 130 bets, 62.3% win rate, +22.0 units

**Insight:** Elite scorers on steals UNDER is a DIAMOND pattern.

### 4. Dual-Pool Analysis

Added morning vs evening pipeline run classification:
- **Morning (<20:00 UTC):** 10,495 bets, 54.8% win rate, **+78.4 units** ✅
- **Evening (≥20:00 UTC):** 3,928 bets, 54.8% win rate, -81.7 units

**Paired Dates:** 14 dates with both morning + evening runs (Jan 12-14, Feb 2-12)

**Insight:** Morning pool is profitable, evening pool is negative. Line movement or information edge?

### 5. Brier Score Calibration

Added Brier score per edge bucket (measures probability calibration):
- 5-10%: Brier 0.2472 (GOOD)
- 10-15%: Brier 0.2471 (GOOD)
- 15-20%: Brier 0.2466 (EXCELLENT)
- 20-25%: Brier 0.2580 (OVERCONFIDENT)
- 25%+: Brier 0.3217 (SEVERELY OVERCONFIDENT)

**Insight:** Lower Brier = better calibration. Model is well-calibrated up to 20% edge, then breaks down.

---

## Critical Findings

### 🚨 Major Issues

1. **25%+ Edge Bucket Overconfidence**
   - Expected: 73.8% win rate
   - Actual: 50.0% win rate
   - Calibration: -23.8% (SEVERELY OVERCONFIDENT)
   - Sample: 6,095 bets (42% of all bets!)
   - **Action Required:** Investigate edge calculation formula. Likely edge dampening or archetype modifiers are broken.

2. **OVER Bet Leaks**
   - REB OVER: -276.2 units (39.7% win rate, 974 bets)
   - 3PM OVER: -242.5 units (42.3% win rate, 780 bets)
   - BLOCKS OVER: -77.7 units (38.1% win rate, 333 bets)
   - **Action Required:** Filter out OVER bets for these categories or recalibrate projections.

3. **Evening Pool Negative**
   - Evening runs: -81.7 units across 3,928 bets
   - Morning runs: +78.4 units across 10,495 bets
   - **Hypothesis:** Line movement to closing disadvantages evening bets OR stale injury info.

### ✅ Major Strengths

1. **UNDER Bet Dominance**
   - 3PM UNDER: +181.6 units (62.3% win rate, 1,354 bets)
   - STEALS UNDER: +121.8 units (54.8% win rate, 1,644 bets)
   - TURNOVERS UNDER: +104.8 units (72.2% win rate, 169 bets)
   - BLOCKS UNDER: +90.1 units (70.7% win rate, 2,187 bets)
   - REB UNDER: +84.7 units (55.5% win rate, 1,253 bets)

2. **Elite Scorer Steals Pattern**
   - 75.4% win rate (+98.5 units on 138 bets)
   - Highest performing archetype × stat combo

3. **Moderate Favorites Sweet Spot**
   - Spread -7 to -3: +172.3 units (56.5% win rate, 2,303 bets)

---

## Technical Improvements

### Code Quality
- Added comprehensive comments explaining non-obvious logic
- Maintained ModelPerformanceAnalyzer class structure
- Used descriptive variable names for novice coder readability

### Performance
- Single-pass data loading (no redundant queries)
- Efficient in-memory aggregations
- Handles 15k+ bets without performance issues

### Output
- **Console:** Formatted tables with proper alignment
- **Markdown:** Clean report file at `reports/performance_analysis_YYYY-MM-DD.md`
- Both include all 10+ tables

---

## Usage

### Console Output Only
```bash
cd "/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot"
source .venv/bin/activate
python scripts/analyze_model_performance.py
```

### Generate Markdown Report
```bash
python scripts/analyze_model_performance.py --output markdown
```

---

## Next Steps

### Immediate (Critical)

1. **Investigate 25%+ Edge Bucket**
   - Review edge calculation in Module F
   - Check if archetype modifiers are broken (user noted 3 broken classification systems)
   - Verify edge dampening formula (20%+ edges should be dampened)

2. **Filter Out OVER Bet Leaks**
   - Add filters in Module F:
     - REB OVER (39.7% WR)
     - 3PM OVER (42.3% WR)
     - BLOCKS OVER (38.1% WR)

3. **Investigate Evening Pool Negativity**
   - Compare line movement (opening vs closing odds)
   - Check if injury info is fresher in morning runs
   - Analyze paired dates (14 dates with both pools)

### Short-Term (Optimization)

4. **Total Bucket Recalibration**
   - Current thresholds (218/228/238) don't match data distribution
   - Consider percentile-based buckets instead

5. **Home/Away Context Integration**
   - Add home court advantage modifier in Module C or E
   - Investigate why home bets outperform (+90.1 vs -93.5)

6. **Archetype Classification Audit**
   - User noted 55% GENERALIST (should be lower)
   - GENERALIST has -159.8 units (poor performance)
   - Review classification logic in Module E

---

## Validation

### Test Results
- ✅ Script runs without errors
- ✅ Console output formatted correctly
- ✅ Markdown report generated
- ✅ All 10+ tables populated
- ✅ VOIDs excluded (14,423 bets vs 15,575 total)
- ✅ Sample size filters applied
- ✅ Brier scores calculated
- ✅ Dual-pool classification working

### Database
- **Path:** `ludi.db` in project root
- **Table:** `bet_recommendations` (42 columns)
- **Date Range:** 2026-01-07 to 2026-02-12 (37 days)
- **Total Bets:** 15,575 (14,423 settled + 1,152 VOIDs)

---

## Files Modified/Created

1. **Created:** `scripts/analyze_model_performance.py` (new location)
2. **Created:** `reports/performance_analysis_2026-02-15.md` (markdown output)
3. **Created:** `reports/ANALYZER_ENHANCEMENT_SUMMARY.md` (this file)
4. **Archived:** `scripts/archive/analyze_model_performance.py` (original)
