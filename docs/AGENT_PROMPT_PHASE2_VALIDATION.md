# Agent Prompt: Phase 5.5 Phase 2 Backtest Validation

**Agent Role:** Validation Specialist
**Task ID:** Phase 5.5 Phase 2 - Backtest Validation
**Priority:** HIGH
**Estimated Duration:** 30-45 minutes
**Created:** February 1, 2026

---

## 🎯 Mission Overview

You are tasked with validating the **Phase 5.5 Phase 2** defensive tracking enhancements to the Ludi-Bot NBA analytics platform. Your goal is to measure whether the newly implemented shot difficulty modifiers and opponent context adjustments are improving betting recommendation accuracy.

**What was implemented:**
- Shot difficulty modifiers using defender distance data (contested, tight, open, wide-open FGA)
- Opponent context modifiers for defensive stats (STL boost vs high-TOV teams, BLK boost vs paint-heavy teams)
- Data coverage: 91.9% of player-games have shot difficulty data (Jan 14-31, 2026)

**Your task:**
Run a 14-day backtest to measure hit rate improvements on PTS, STL, and BLK props compared to baseline projections without these modifiers.

---

## 📚 Project Context

### System Architecture
- **Tech Stack:** Python 3.11 + SQLite + Streamlit
- **Database:** `ludi.db` (24 MB, ~12,000 player-games)
- **Pipeline:** 9 modules (A-H + X) process data sequentially
- **Key Module:** Module E (Calibrator) - applies all adjustment modifiers

### Phase 5.5 Timeline
- **Phase 0:** STL/BLK/DREB added to STAT_MAPPING (Jan 29) ✅
- **Phase 1:** 16-archetype system implemented (Jan 29) ✅
- **Phase 2:** Shot difficulty + opponent context modifiers (Feb 1) ✅
- **Phase 2 Validation:** YOUR TASK (Feb 1) ⏳

### Key Files
| File | Purpose |
|------|---------|
| `module_e.py` | Calibrator - contains shot difficulty & opponent context logic |
| `ludi.db` | SQLite database with player_game_tracking table (shot difficulty data) |
| `player_game_logs` table | Historical game results for backtest comparison |
| `player_game_tracking` table | Defender distance data (contested, tight, open, wide_open FGA) |
| `ROADMAP.md` | Project status and priorities |
| `docs/PHASE_5_5_VERIFICATION_REPORT.md` | Phase 0 & 1 verification report |

---

## 🔬 Validation Tests to Perform

### Test 1: Data Coverage Verification
**Objective:** Confirm sufficient data exists for reliable backtest

**Steps:**
1. Query `player_game_tracking` table for Jan 18-31, 2026 (14 days)
2. Count total records vs records with shot difficulty data (contested_fga IS NOT NULL)
3. Calculate coverage percentage
4. Identify any gaps or anomalies

**Success Criteria:**
- ✅ Coverage ≥80% overall
- ✅ At least 10 days with ≥90% coverage
- ✅ No critical data integrity issues (contested_fga < tight_fga)

**SQL Queries:**
```sql
-- Overall coverage
SELECT
  COUNT(*) as total_records,
  SUM(CASE WHEN contested_fga IS NOT NULL THEN 1 ELSE 0 END) as with_data,
  ROUND(100.0 * SUM(CASE WHEN contested_fga IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as coverage_pct
FROM player_game_tracking
WHERE game_date >= '2026-01-18' AND game_date <= '2026-01-31';

-- Daily coverage breakdown
SELECT
  game_date,
  COUNT(*) as total,
  SUM(CASE WHEN contested_fga IS NOT NULL THEN 1 ELSE 0 END) as with_data,
  ROUND(100.0 * SUM(CASE WHEN contested_fga IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1) as coverage_pct
FROM player_game_tracking
WHERE game_date >= '2026-01-18' AND game_date <= '2026-01-31'
GROUP BY game_date
ORDER BY game_date;

-- Data integrity check (contested should be >= tight)
SELECT COUNT(*) as integrity_violations
FROM player_game_tracking
WHERE game_date >= '2026-01-18'
  AND contested_fga IS NOT NULL
  AND tight_fga IS NOT NULL
  AND contested_fga < tight_fga;
```

---

### Test 2: Shot Difficulty Impact on PTS Props
**Objective:** Measure if wide-open ratio modifier improves PTS projection accuracy

**Hypothesis:** Players with high wide-open shot ratios should benefit from +3% FG% and +5% 3PM modifiers, leading to more accurate PTS projections.

**Steps:**
1. Identify players with wide-open ratio >50% (high quality shots)
2. Compare actual PTS vs projected PTS for these players
3. Calculate RMSE (Root Mean Square Error) and mean error
4. Compare to baseline (projections without shot difficulty modifier)

**Success Criteria:**
- ✅ RMSE reduction ≥1.0 pts for high wide-open ratio players
- ✅ Mean error closer to 0 (less systematic bias)
- ✅ Hit rate improvement ≥+2% on PTS props overall

**Implementation Notes:**
- **Shot difficulty modifier location:** `module_e.py` lines 1155-1192
- **Logic:** Wide-open ratio = wide_open_fga / (tight_fga + open_fga + wide_open_fga)
- **Modifier:** If ratio >50% → proj_fg_pct *= 1.03, proj_3pm *= 1.05
- **Modifier:** If ratio <20% → proj_fg_pct *= 0.97, proj_3pm *= 0.95

**Pseudocode:**
```python
# For each player-game in backtest period:
# 1. Calculate wide-open ratio from tracking data
# 2. Apply modifier to base projection
# 3. Compare modified projection vs actual result
# 4. Calculate error metrics
```

---

### Test 3: Opponent Context Impact on STL Props
**Objective:** Measure if STL boost vs high-turnover teams improves accuracy

**Hypothesis:** Players facing opponents with TOV rate >15% should benefit from +10% STL modifier.

**Steps:**
1. Identify games where opponent had TOV rate >15%
2. Compare actual STL vs projected STL for defenders in those games
3. Calculate hit rate on STL props (Over/Under)
4. Compare to baseline (no opponent context)

**Success Criteria:**
- ✅ Hit rate improvement ≥+3% on STL props vs high-TOV teams
- ✅ Mean error closer to 0
- ✅ No regression on STL props vs normal-TOV teams

**Implementation Notes:**
- **Modifier location:** `module_e.py` lines 1193-1221
- **Logic:** If opponent TOV rate >15% → proj_stl *= 1.10
- **Data source:** Opponent stats passed in player packet from main.py

**Test Query:**
```sql
-- Find high-TOV opponent games
SELECT
  pgl.player_name,
  pgl.game_date,
  pgl.stl as actual_stl,
  -- Calculate if opponent had high TOV rate (requires joining team stats)
  -- This will need custom logic to determine opponent TOV rate
FROM player_game_logs pgl
WHERE pgl.game_date >= '2026-01-18' AND pgl.game_date <= '2026-01-31'
  AND pgl.stl IS NOT NULL;
```

---

### Test 4: Opponent Context Impact on BLK Props
**Objective:** Measure if BLK boost vs paint-heavy teams improves accuracy

**Hypothesis:** Players facing opponents with 2PA rate >65% should benefit from +10% BLK modifier.

**Steps:**
1. Identify games where opponent had 2PA rate >65% (paint-heavy offense)
2. Compare actual BLK vs projected BLK for defenders in those games
3. Calculate hit rate on BLK props
4. Compare to baseline

**Success Criteria:**
- ✅ Hit rate improvement ≥+3% on BLK props vs paint-heavy teams
- ✅ Mean error closer to 0
- ✅ No regression on BLK props vs perimeter-heavy teams

**Implementation Notes:**
- **Modifier location:** `module_e.py` lines 1193-1221
- **Logic:** If opponent 2PA rate >65% → proj_blk *= 1.10
- **Data source:** Opponent stats passed in player packet from main.py

---

### Test 5: Integration Test - Full Pipeline
**Objective:** Verify modifiers don't break existing pipeline or cause regressions

**Steps:**
1. Run full pipeline simulation for 1 recent game day (e.g., Jan 31)
2. Check that all modules execute without errors
3. Verify betting recommendations are generated
4. Confirm no regression in AST, REB, 3PM accuracy (non-modified stats)

**Success Criteria:**
- ✅ Pipeline completes without errors
- ✅ All 9 modules execute successfully
- ✅ Betting recommendations generated with shot difficulty tags in notes
- ✅ No accuracy regression on AST, REB (control stats)

**Test Command:**
```bash
# From project root
source .venv/bin/activate
python main.py --date 2026-01-31 --verbose
```

---

## 📊 Report Generation Requirements

### Report Structure
Create a comprehensive markdown report at:
`docs/PHASE_5_5_PHASE_2_VALIDATION_REPORT.md`

### Required Sections

#### 1. Executive Summary
- Overall validation status (PASS/FAIL)
- Key metrics summary table
- Recommendation (proceed to Phase 5 or iterate)

#### 2. Test Results
For each test (1-5), include:
- Test name and objective
- Success criteria recap
- Actual results (with data tables)
- Pass/Fail status
- Evidence (SQL query outputs, charts if applicable)

#### 3. Hit Rate Analysis
Comparison table:

| Stat | Baseline Hit Rate | With Modifiers | Improvement | Target | Status |
|------|-------------------|----------------|-------------|--------|--------|
| PTS (All) | X% | Y% | +Z% | ≥+2% | ✅/❌ |
| PTS (High Quality Shots) | X% | Y% | +Z% | ≥+3% | ✅/❌ |
| STL (High TOV Opp) | X% | Y% | +Z% | ≥+3% | ✅/❌ |
| BLK (Paint Heavy Opp) | X% | Y% | +Z% | ≥+3% | ✅/❌ |

#### 4. Error Metrics
| Stat | Baseline RMSE | With Modifiers | Improvement | Target |
|------|---------------|----------------|-------------|--------|
| PTS | X.XX | Y.YY | -Z.ZZ | ≥-1.0 |
| STL | X.XX | Y.YY | -Z.ZZ | ≥-0.2 |
| BLK | X.XX | Y.YY | -Z.ZZ | ≥-0.2 |

#### 5. Coverage Analysis
- Data availability summary
- Gaps or anomalies identified
- Impact on validation reliability

#### 6. Findings & Observations
- What worked well
- What needs tuning
- Unexpected patterns
- Edge cases discovered

#### 7. Recommendations
Based on results, recommend one of:
- ✅ **PROCEED:** Validation passed, move to Phase 5 automation
- ⚠️ **TUNE:** Validation passed but modifiers need adjustment (provide specific tuning suggestions)
- ❌ **REVISE:** Validation failed, implementation needs revision (provide specific issues)

#### 8. Appendix
- SQL queries used
- Sample data tables
- Charts/visualizations (if created)
- Full test logs

---

## 🔧 Technical Implementation Guide

### Environment Setup
```bash
cd /Users/flyprice/Desktop/Ludi\ Informatio/Projects/Ludi-Bot
source .venv/bin/activate
```

### Key Database Tables

**player_game_tracking** (shot difficulty data):
- `nba_player_id` - Player ID
- `game_date` - Game date
- `contested_fga` - Contested field goal attempts (0-4 feet)
- `tight_fga` - Tight defense (2-4 feet)
- `open_fga` - Open shots (4-6 feet)
- `wide_open_fga` - Wide open shots (6+ feet)

**player_game_logs** (actual results):
- `player_name` - Player name
- `game_date` - Game date
- `pts`, `stl`, `blk` - Actual stats
- `fga`, `fgm`, `fg3a`, `fg3m` - Shooting stats

### Baseline Projection Calculation
To compare "with modifiers" vs "without modifiers", you'll need to:

1. **Extract base projections** from Module C (Oracle) before Module E applies modifiers
2. **Apply modifiers manually** for test group
3. **Compare both to actual results**

**Option 1 - Simpler Approach:**
Run simulations with/without modifiers enabled and compare results.

**Option 2 - Manual Calculation:**
Query tracking data and manually apply the modifier formulas:
```python
# Shot difficulty modifier
wide_open_ratio = wide_open_fga / (tight_fga + open_fga + wide_open_fga)
if wide_open_ratio > 0.5:
    modified_fg_pct = base_fg_pct * 1.03
    modified_3pm = base_3pm * 1.05
elif wide_open_ratio < 0.2:
    modified_fg_pct = base_fg_pct * 0.97
    modified_3pm = base_3pm * 0.95

# Opponent context modifiers
if opponent_tov_rate > 0.15:
    modified_stl = base_stl * 1.10
if opponent_2pa_rate > 0.65:
    modified_blk = base_blk * 1.10
```

### Recommended Approach: Batch Backtest Script

Create a new script: `scripts/backtest_phase2_validation.py`

**Suggested structure:**
```python
#!/usr/bin/env python3
"""
Phase 5.5 Phase 2 Validation Backtest
Measures hit rate improvements from shot difficulty and opponent context modifiers.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from module_e import LudiCalibrator
from database import DB_PATH

def test_1_coverage_verification():
    """Test 1: Verify data coverage for backtest period."""
    # Implementation here
    pass

def test_2_shot_difficulty_pts():
    """Test 2: Shot difficulty impact on PTS props."""
    # Implementation here
    pass

def test_3_opponent_context_stl():
    """Test 3: Opponent context impact on STL props."""
    # Implementation here
    pass

def test_4_opponent_context_blk():
    """Test 4: Opponent context impact on BLK props."""
    # Implementation here
    pass

def test_5_integration_test():
    """Test 5: Full pipeline integration test."""
    # Implementation here
    pass

def generate_report(results):
    """Generate validation report markdown file."""
    # Implementation here
    pass

def main():
    print("\n" + "="*60)
    print("PHASE 5.5 PHASE 2 VALIDATION BACKTEST")
    print("Shot Difficulty & Opponent Context Modifiers")
    print("="*60 + "\n")

    results = {}

    # Run tests
    results['Test 1'] = test_1_coverage_verification()
    results['Test 2'] = test_2_shot_difficulty_pts()
    results['Test 3'] = test_3_opponent_context_stl()
    results['Test 4'] = test_4_opponent_context_blk()
    results['Test 5'] = test_5_integration_test()

    # Generate report
    generate_report(results)

    print("\n✅ Validation complete. Report saved to:")
    print("   docs/PHASE_5_5_PHASE_2_VALIDATION_REPORT.md")

if __name__ == '__main__':
    main()
```

---

## ✅ Success Criteria Summary

### Must-Pass Criteria (All Required)
- [ ] Test 1: Data coverage ≥80% overall
- [ ] Test 2: PTS hit rate improvement ≥+2% OR RMSE reduction ≥1.0 pts
- [ ] Test 3: STL hit rate improvement ≥+3% vs high-TOV teams
- [ ] Test 4: BLK hit rate improvement ≥+3% vs paint-heavy teams
- [ ] Test 5: Full pipeline runs without errors

### Good-to-Have (Bonus Points)
- [ ] PTS RMSE reduction ≥2.0 pts (exceptional improvement)
- [ ] STL/BLK hit rate improvement ≥+5% (strong signal)
- [ ] No regression on control stats (AST, REB, non-modified 3PM)
- [ ] Visualizations included in report (charts, graphs)

### Overall Validation Status
- **PASS:** 5/5 must-pass criteria met
- **CONDITIONAL PASS:** 4/5 met with minor tuning recommendations
- **FAIL:** <4/5 met, requires implementation revision

---

## 📝 Deliverables Checklist

Upon completion, you must deliver:

- [ ] **Validation Report** - `docs/PHASE_5_5_PHASE_2_VALIDATION_REPORT.md`
- [ ] **Backtest Script** - `scripts/backtest_phase2_validation.py` (if created)
- [ ] **Updated ROADMAP.md** - Mark Phase 2 Validation as complete with results summary
- [ ] **SQL Query Logs** - Evidence of data queries performed
- [ ] **Terminal Output** - Full test execution logs (if applicable)

Optional:
- [ ] **Charts/Visualizations** - Hit rate comparisons, error distribution plots
- [ ] **Tuning Recommendations** - If modifiers need adjustment (with specific values)
- [ ] **Edge Case Documentation** - Any anomalies or unexpected behavior discovered

---

## ⚠️ Important Notes

### What NOT to Do
- ❌ DO NOT modify Module E code during validation (this is a test-only phase)
- ❌ DO NOT run production pipeline without `--dry-run` flag
- ❌ DO NOT commit changes to database during testing
- ❌ DO NOT use live API calls (use cached database data only)

### What TO Do
- ✅ Use read-only database queries
- ✅ Document all assumptions made
- ✅ Report unexpected findings (even if tests pass)
- ✅ Include both positive and negative results in report
- ✅ Suggest tuning values if results are marginal

### Data Integrity Reminders
- Shot difficulty data availability: Jan 14-31, 2026 (17 days)
- Best coverage period: Jan 18-31 (14 days, excluding Jan 25)
- Jan 25 has only 33.1% coverage (exclude from critical tests)
- Opponent context data depends on team stats availability

### Time Management
- **Coverage verification:** ~5 minutes
- **PTS analysis:** ~10-15 minutes
- **STL/BLK analysis:** ~10-15 minutes (combined)
- **Integration test:** ~5 minutes
- **Report generation:** ~10 minutes
- **Total:** 30-45 minutes

---

## 🚀 Execution Checklist

Before starting:
- [ ] Read ROADMAP.md to understand project context
- [ ] Read docs/PHASE_5_5_VERIFICATION_REPORT.md for Phase 0 & 1 context
- [ ] Verify database exists and is accessible
- [ ] Check that venv is activated

During execution:
- [ ] Run tests in order (1-5)
- [ ] Document findings as you go
- [ ] Save SQL query outputs
- [ ] Note any anomalies or unexpected behavior

After completion:
- [ ] Generate comprehensive report
- [ ] Update ROADMAP.md with results
- [ ] Summarize key findings for user
- [ ] Provide clear recommendation (PROCEED/TUNE/REVISE)

---

## 📞 Questions or Issues?

If you encounter blockers:
1. Document the issue clearly
2. Check if it's a data availability problem (missing tracking data)
3. Try alternative analysis approaches if primary method fails
4. Report partial results if full validation cannot be completed
5. Provide recommendations based on available data

**Remember:** The goal is to determine if the modifiers are improving accuracy, not to prove they work perfectly. Honest assessment is more valuable than forced success.

---

**End of Agent Prompt**

Good luck! 🎯
