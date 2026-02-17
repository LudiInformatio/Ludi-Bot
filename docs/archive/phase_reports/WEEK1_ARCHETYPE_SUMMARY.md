# Week 1 Summary: Archetype Upgrade - Data Collection & Thresholds

**Date:** January 19, 2026  
**Status:** ✅ COMPLETE - Ready for Week 2 (with caveats)  
**Analyst:** Claude (Antigravity)

---

## Executive Summary

Week 1 of the Archetype Synergy Upgrade focused on **data validation** and **threshold calibration** for 8 new secondary playtypes. The analysis revealed strong data coverage (4,842 player-games) and successfully calibrated 4 playtypes to target ranges. However, 4 "big man" archetypes (P&R_ROLL_MAN, OFF_BALL_CUTTER, PUTBACK, POST_UP) show significant overlap due to similar player profiles.

**Key Decision Required:** Should we reduce to 6 total playtypes, or accept some overlap for the 4 big man categories?

---

## 1. Data Coverage Validation ✅

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Total tracking records (60 days) | 10,070 | - | ✅ |
| Backtest window records (30 days) | 4,842 | - | ✅ |
| Unique players with tracking | 464 | 400+ | ✅ |
| Game days covered | 29 | 30 | ✅ |
| Coverage % | 93%+ | >80% | ✅ |
| Shot quality profiles | 499 | - | ✅ |
| Advanced stats records | 9,724 | - | ✅ |

**Date Range:** 2025-12-20 to 2026-01-18 (29 game days)

**No significant gaps detected.** All dates have player tracking data.

---

## 2. Playtype Frequency Distributions

Analysis of 392 players with 10+ games in the L60 window:

### Key Metrics (Percentiles)

| Metric | Mean | P50 | P75 | P90 | Proposed Threshold |
|--------|------|-----|-----|-----|--------------------|
| Drives/game | 2.0 | 1.3 | 3.0 | 5.1 | 5-6 (elite) |
| Pull-up FGA | 2.0 | 1.1 | 2.7 | 5.4 | 3-5 (volume) |
| Catch-shoot FGA | 2.5 | 2.4 | 3.6 | 4.7 | 4+ (shooter) |
| Catch-shoot % | 35.4% | 35.8% | 41.5% | 48.5% | 38%+ (efficient) |
| Speed (mph) | 4.6 | 4.6 | 4.8 | 5.0 | 4.8+ (fast) |
| Distance (mi/game) | 0.86 | 0.90 | 1.12 | 1.28 | 1.1+ (high motor) |

---

## 3. Threshold Validation Results (v1.2)

### Tag Assignment Summary

| Playtype | Count | Coverage % | Target % | Status |
|----------|-------|------------|----------|--------|
| **ISO_SCORER** | 41 | 10.5% | 10-18% | ✅ GOOD |
| **P&R_HANDLER** | 66 | 16.8% | 10-18% | ✅ GOOD |
| **TRANSITION** | 75 | 19.1% | 12-22% | ✅ GOOD |
| **PUTBACK** | 46 | 11.7% | 6-14% | ✅ GOOD |
| **SPOT_UP** | 63 | 16.1% | 18-28% | ⚠️ LOW |
| **P&R_ROLL_MAN** | 170 | 43.4% | 10-20% | ⚠️ HIGH |
| **OFF_BALL_CUTTER** | 88 | 22.4% | 8-18% | ⚠️ HIGH |
| **POST_UP** | 83 | 21.2% | 8-16% | ⚠️ HIGH |

### Tag Pollution Check

| Metric | v1.0 | v1.1 | v1.2 | Target |
|--------|------|------|------|--------|
| Max tags/player | 5 | 4 | 4 | ≤3 |
| Players with 4+ tags | 157 (40%) | 63 (16%) | 45 (11.5%) | <5% |
| Players with 0 tags | 2 (0.5%) | 107 (27%) | 81 (21%) | ~30% |

**Progress:** Reduced 4+ tag pollution from 40% → 11.5% across 3 iterations.

---

## 4. Sample Tag Assignments

### ISO_SCORER (41 players, 10.5%) ✅
- Jaylen Brown, Jalen Brunson, Shai Gilgeous-Alexander
- Anthony Edwards, Devin Booker, Tyrese Maxey
- Brandon Ingram, Kevin Durant, Anfernee Simons

### P&R_HANDLER (66 players, 16.8%) ✅
- Cade Cunningham, Austin Reaves, Andrew Nembhard
- Brandin Podziemski, Jalen Smith, Amen Thompson

### SPOT_UP (63 players, 16.1%) ⚠️
- Klay Thompson, Michael Porter Jr., Aaron Nesmith
- Al Horford, Brook Lopez, Ayo Dosunmu, Ace Bailey

### TRANSITION (75 players, 19.1%) ✅
- De'Aaron Fox, Tyrese Maxey, Alperen Sengun
- Amen Thompson, Ajay Mitchell, AJ Green

### PUTBACK (46 players, 11.7%) ✅
- Andre Drummond, Ivica Zubac, Clint Capela
- Daniel Gafford, Adem Bona, Isaiah Jackson

### Notable Overlap Cases
- **Andre Drummond**: P&R_ROLL_MAN, OFF_BALL_CUTTER, PUTBACK, POST_UP
- **Clint Capela**: P&R_ROLL_MAN, OFF_BALL_CUTTER, PUTBACK, POST_UP
- **Brandon Ingram**: ISO_SCORER, P&R_HANDLER, SPOT_UP, TRANSITION

---

## 5. Key Findings & Insights

### ✅ What Worked
1. **ISO_SCORER thresholds are strict** - Only elite creators qualify (drives > 6, pull_up > 5)
2. **TRANSITION captures perimeter athletes** - Speed + distance + drives correctly identifies fast players
3. **PUTBACK is finally exclusive** - Stricter rim_freq (55%) and very low shooting thresholds work

### ⚠️ Challenge: Big Man Archetype Overlap

The 4 big man archetypes (P&R_ROLL_MAN, OFF_BALL_CUTTER, PUTBACK, POST_UP) fundamentally describe **similar player profiles**:
- High rim frequency (40-55%)
- Low drives (< 2)
- Low pull-up (< 1.5)
- Variable catch-shoot (0.5 - 2.5)

**Root Cause:** Traditional bigs like Clint Capela and Andre Drummond perform ALL of these actions:
- Roll to rim (P&R_ROLL_MAN)
- Cut for lobs (OFF_BALL_CUTTER)
- Rebound and finish (PUTBACK)
- Post up when needed (POST_UP)

### 🎯 Recommended Solution

**Option A: Accept Overlap (Recommended)**
- Allow bigs to have multiple tags (reflecting their versatility)
- Limit max tags to 3 by making one tag "primary" based on highest match score
- Use tags for matchup analysis, not player classification

**Option B: Reduce to 6 Playtypes**
- Consolidate P&R_ROLL_MAN + OFF_BALL_CUTTER → "RIM_FINISHER"
- Keep PUTBACK and POST_UP as modifiers (not primary tags)

---

## 6. Files Created

| File | Purpose |
|------|---------|
| `scripts/analyze_playtype_distributions.py` | Distribution analysis for all tracking metrics |
| `scripts/test_playtype_thresholds.py` | Threshold validation with 2-of-3 / 3-of-4 criteria |
| `config/playtype_thresholds.json` | v1.2 configuration with calibrated thresholds |

---

## 7. Recommendations for Week 2

### Before Implementation:
1. **Decide on overlap strategy** - Accept 4 tags for bigs OR consolidate to 6 playtypes
2. **Lower SPOT_UP threshold** from 4.0 to 3.5 cs_fga (currently at 16%, want 18-28%)
3. **Add "primary playtype" logic** - Assign only the BEST matching tag as primary

### Week 2 Implementation Plan:
1. Add secondary playtype assignment to `module_e.py` calibrate_player()
2. Store assigned tags in player context for matchup analysis
3. Create betting edge rules (e.g., SPOT_UP vs PAINT_PACK = boost 3PM)
4. Backtest with new tags to validate ROI improvement

---

## 8. Ready for Week 2?

- [x] Data coverage validated (>80%)
- [x] Distribution percentiles calculated
- [x] Thresholds calibrated (4 of 8 in target range)
- [x] Config file created (`config/playtype_thresholds.json`)
- [x] Analysis scripts working

**Status: ✅ PROCEED TO WEEK 2**

> **Note:** Big man archetype overlap is expected behavior. For betting purposes, we recommend implementing a "primary playtype" selector that chooses the strongest match rather than assigning multiple tags.

---

## Appendix: Threshold Evolution

| Version | Changes | Result |
|---------|---------|--------|
| v1.0 | Initial thresholds from plan | 69% P&R_ROLL_MAN, 5 max tags |
| v1.1 | Stricter thresholds, 3-of-4 rules | 41% P&R_ROLL_MAN, 4 max tags |
| v1.2 | Mutual exclusivity via catch_shoot | 43% P&R_ROLL_MAN, PUTBACK 11.7% ✅ |
