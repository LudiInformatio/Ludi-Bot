# Ludi-Bot Roadmap

**Last Updated:** February 2, 2026 @ 8:30 PM EST
**Current Phase:** Phase 6 - Full Data Integration
**Active Work:** Phase 6.3 - WOWY Data Enhancement
**Completed:** Phase 5.5 Phases 0-2 + Database Sync Redesign + Feb 2 Calibration + Performance Analysis + CLV Backfill + **Phase 6.1 Depth Charts** + **Phase 6.2 BENEFICIARY Pipeline**

This is the single source of truth for project tasks and priorities.

---

## Legend

- `[ ]` = Todo
- `[-]` = In Progress
- `[x]` = Completed

---

## High Priority

### Phase 6: Full Data Integration (NEW - Feb 2, 2026)

**Goal:** Integrate ALL unused data sources and fix broken data flows before further calibration
**Priority:** CRITICAL (must complete before any more validation work)
**Rationale:** Analysis revealed significant missed opportunities - we have valuable data that isn't being used

**Problem Statement:**
The Feb 2 performance analysis revealed that despite having profitable results (+292u, 55.7% win rate), we are NOT using:
- ~~Tank01 depth charts (starters vs backups) - NOT synced~~ ✅ FIXED in Phase 6.1
- ~~BENEFICIARY scenario tagging - 99.9% of bets logged as "Active" with zero "WITHOUT" scenarios~~ ✅ FIXED in Phase 6.2 (pipeline ready, awaiting star OUT trigger)
- WOWY data for usage vacuum calculations - Tables exist but unused
- player_touches, player_drives tables - Synced but not integrated
- ROLE_CHANGE detection from RotoWire RSS - Configured but no downstream usage
- Forward CLV capture - Historical backfill done, but no ongoing capture

**Phase 6.1: Tank01 Depth Charts Integration** ✅ COMPLETE (Feb 2, 2026)
- [x] Create `scripts/sync_depth_charts.py` using Tank01 `/getNBADepthCharts` endpoint ✅
- [x] Store in new `depth_charts` table (team, position, player_name, depth_order) ✅
- [x] Add `is_starter` column to `players` table (PG1/SG1/SF1/PF1/C1 = starter) ✅
- [x] Integrate starter status into Module E matchup calculations ✅
- [x] Created `tests/test_depth_charts.py` with 7 unit tests ✅

**Phase 6.2: BENEFICIARY Scenario Pipeline Fix** ✅ COMPLETE (Feb 2, 2026)
- [x] Audit Module D → Module F data flow for scenario tagging ✅
- [x] Fix: When star is OUT, tag teammates with `BENEFICIARY` scenario ✅
- [x] Integrate WOWY data (`team_lineups` table) to calculate actual usage boost ✅ (heuristic fallback active)
- [x] Log `scenario` field in `bet_recommendations` table ✅
- [x] Created `tests/test_beneficiary_pipeline.py` with 6 unit tests ✅

**Phase 6.3: WOWY Data Enhancement** ✅ COMPLETE (Feb 2, 2026)
- [x] Create `lineup_season_totals` SQL view (aggregate per-game lineup data) ✅
- [x] Adaptive WOWY confidence thresholds (BASE: 500/350/150, scales with season progress) ✅
- [x] Create `scripts/sync_pbp_wowy.py` using PBP Stats API `stat_type='team'` endpoint ✅
- [x] Integrate PBP Stats WOWY data into `player_season_wowy` table ✅
- [ ] Add to `data_sync.yml` workflow (Daily 3 AM EST) - Optional, can run manually
- [x] Create `tests/test_wowy_enhancement.py` with 5 unit tests ✅

**Phase 6.4: ROLE_CHANGE Detection**
- [ ] Module D already parses RotoWire for "will start", "moved to bench" keywords
- [ ] Create downstream handler to adjust projections when ROLE_CHANGE detected
- [ ] Add minutes projection adjustment for starter elevation (+8 min) / demotion (-8 min)

**Phase 6.5: Forward CLV Capture**
- [ ] Create `scripts/capture_closing_lines.py` (runs 5 min before tipoff)
- [ ] Store closing odds in `bet_recommendations.closing_odds_*` columns
- [ ] Calculate and store real CLV (not just closing line value)
- [ ] Add CLV metrics to daily Telegram summary

**Phase 6.6: API Audit & Optimization**
- [ ] Document all Tank01 endpoints in use vs available
- [ ] Document all The-Odds-API endpoints in use vs available
- [ ] Evaluate Ball Don't Lie API integration (free tier, 60 req/min)
- [ ] Create `docs/API_USAGE_AUDIT.md` with findings

**Success Criteria:**
- [x] Depth charts synced daily, starter status accurate for all 30 teams ✅ (Phase 6.1)
- [x] BENEFICIARY scenarios tagged when star OUT ✅ (Phase 6.2 - pipeline ready)
- [x] WOWY differential used with real confidence scoring ✅ (Phase 6.3 - adaptive thresholds + PBP Stats sync)
- [ ] CLV captured going forward (not just historical backfill)
- [ ] API audit document created with integration roadmap

**CLV Finding (Important Context):**
Historical CLV backfill (Jan 7-29) showed positive CLV across ALL edge buckets:
| Edge Bucket | Real CLV (pts) | Win Rate |
|-------------|----------------|----------|
| 5-10% | +0.013 | 58.3% |
| 10-15% | +0.050 | 52.8% |
| 15-20% | +0.096 | 58.6% |
| 20-25% | +0.115 | 51.5% |
| 25%+ | +0.147 | 51.6% |

This suggests the model IS finding real value (CLV positive), but variance is affecting win rate at high edges. Full data integration may improve both signal AND reduce variance.

---

### Phase 5: Production Deployment & Automation
**Target:** Transition from "stable development" to "automated production"

- [ ] Create/Update `daily_simulation_pipeline.yml` (11 AM EST trigger)
- [ ] Create `scripts/monitor_system_health.py` (data integrity + model drift alerts)
- [ ] Create `scripts/backfill_referees.py` (Historical 45-day backfill via date picker)
- [ ] Create `.github/workflows/weekly_validation.yml` (Tuesdays 4 AM EST)
- [ ] Implement automated weekly backtests with drift alerts
- [ ] Create `scripts/cleanup_old_logs.py` (30-day retention)
- [ ] Add `IS_PRODUCTION` flag handling in `config.py`
- [ ] Verify all workflows via manual trigger
- [ ] Update `docs/PRODUCTION_HANDBOOK.md`

**Success Criteria:**
- [ ] `daily_simulation_pipeline.yml` operational and sending Telegram cards
- [ ] `scripts/monitor_system_health.py` implemented and reporting status
- [ ] Weekly validation automated with drift alerts
- [ ] Production logging directory established

---

### Phase 5.5: Defensive Stat Fix & 16-Archetype Expansion

**Completed Phases:** ✅ Phase 0-2 COMPLETE (Jan 29 - Feb 1, 2026)
- Details: See docs/archive/PHASE_5_5_COMPLETION_LOG.md

**Phase 2 Validation:** ✅ READY FOR TESTING (Feb 2, 2026)
- **Status:** Implementation complete, data restored, ready for backtest validation
- **Data Coverage:** 91.9% (2,650/2,883 records) - Jan 14 to Feb 1, 2026
- **Blockers Resolved:** Ghost Protocol scraper fixed, backfill data restored (Feb 1)
- **Database Sync:** Redesigned architecture prevents future data loss (see DATABASE_SYNC_REDESIGN_HANDOFF.md)

**Infrastructure Fixes (Completed Feb 1, 2026):**
- [x] URGENT: Fixed Ghost Protocol scraper to restore defender distance data sync ✅
- [x] HIGH: Database removed from git tracking (prevents merge conflicts) ✅
- [x] MEDIUM: Backfilled missing data for Jan 14-Feb 1 (91.9% coverage achieved) ✅
- [x] MEDIUM: Automated backup system deployed (daily at 4 AM EST) ✅

**Next Step:**
- [ ] ACTIVE: Run Phase 2 validation backtest (assigned to separate agent)

**Validation Tests (Ready to Execute):**
- [ ] Test 1: Data coverage verification (≥80% required)
- [ ] Test 2: Shot difficulty impact on PTS (≥+2% hit rate OR ≥1.0 RMSE reduction)
- [ ] Test 3: STL boost vs high-TOV teams (≥+3% hit rate improvement)
- [ ] Test 4: BLK boost vs paint-heavy teams (≥+3% hit rate improvement)
- [ ] Test 5: Integration test - no regressions on AST/REB

**Phase 3: SportVu Integration (Optional - Week 3-4)**
- [ ] Create scripts/sync_sportvu_tracking.py for rebounding data
- [ ] Integrate contested/uncontested rebound % for WARRIOR vs VULTURE
- [ ] Add defensive matchup tracking (FG% vs screens, ISO, etc.)

---

### Betting Model Calibration (Feb 2, 2026) ✅ COMPLETE

**Analysis Period:** Jan 7-29, 2026 (9,605 bets, 6,344 settled)
**Key Findings:** Model profitable (+292u, 55.7% win rate) but with calibration opportunities

**Data Cleanup (CRITICAL):** ✅ COMPLETE
- [x] Created `scripts/cleanup_player_duplicates.py`
- [x] Removed 420 Tank01 composite ID duplicates
- [x] Reduced player count from 957 to 536 active players
- [x] Verified no duplicate names remain

**Archetype Re-Assignment:** ✅ COMPLETE
- [x] Created `scripts/reassign_archetypes.py` (V2 - uses full season box scores)
- [x] Assigned 15 distinct archetypes (was mostly GENERALIST before)
- [x] GENERALIST rate: 31% (acceptable for low-minute bench players)
- [x] Top players now have meaningful archetypes (ISO_ASSASSIN, HELIOCENTRIC_MAESTRO, etc.)

**Team Offensive Classification:** ✅ COMPLETE
- [x] Updated `utils/team_offensive_classifier.py` with real DB data
- [x] All 30 teams classified into 6 offensive types
- [x] Types: THREE_POINT_CENTRIC, MOTION_OFFENSE, PACE_PUSH, PAINT_ATTACK, ISOLATION_HEAVY, BALANCED

**Module F Calibration (V5.1):** ✅ COMPLETE
- [x] Added REB OVER filter (skip until calibration - was -198u leak)
- [x] Added 3PM OVER filter for low-volume shooters (<5 3PA)
- [x] Reduced max unit sizing from 1.5u to 1.0u (conservative testing)
- [x] Widened probability stdevs by 30% (reduce overconfidence)

**Impact Summary:**
- REB OVER leak fixed: +198u saved
- 3PM OVER low-volume filter: +110u expected savings
- Conservative sizing: Reduced risk during validation
- Better archetype calibration: More accurate matchup adjustments

**Performance Analysis (Feb 2, 2026):** ✅ COMPLETE
- [x] Created `scripts/sync_positions_by_name.py` (Tank01 position sync)
- [x] Fixed position data: 82.6% coverage (was 2.6% before)
- [x] Created `scripts/analyze_model_performance.py`
- [x] Generated `reports/performance_analysis_feb2.md` (6 analysis tables)
- [x] Generated `reports/CALIBRATION_RECOMMENDATIONS_FEB2.md`

---

### Calibration Refinement (Option A) - ON HOLD

**Status:** ⏸️ PAUSED - Waiting for Phase 6 (Full Data Integration) to complete
**Reason:** CLV analysis revealed model IS finding value (positive CLV all buckets). Better to integrate unused data first, then re-evaluate calibration needs.

**Original Problem (may be resolved by Phase 6):**
- 20-25% edge bets: Expected 61.4% win rate, actual 51.5% (-9.9% gap)
- 25%+ edge bets: Expected 64.4% win rate, actual 51.9% (-12.5% gap)
- However: CLV is POSITIVE for these buckets (+0.115, +0.147 pts) suggesting variance, not overconfidence

**Tasks (resume after Phase 6):**
- [ ] Implement tiered stdev widening in `module_f.py`:
  - 20%+ edge: 60% wider (currently 30% flat)
  - 15-20% edge: 40% wider
  - 5-15% edge: 30% wider (current)
- [ ] Add filter for marginal 20-22% edge bets (likely false positives)
- [ ] Add archetype edge bonuses in `module_e.py`:
  - TWO_WAY_WING: +3% edge bonus (+95u profit, 59.7% win rate)
  - ELITE_SCORER: +3% edge bonus (+91u profit, 59.0% win rate)
- [ ] Add archetype edge penalties for underperformers:
  - STRETCH_BIG: -3% edge penalty (-13u, 46.1% win rate)
  - JUMBO_CREATOR: -3% edge penalty (-16u, 47.3% win rate)
- [ ] Run validation after changes (target: 20%+ edge win rate > 58%)

**Success Criteria:**
- [ ] 20%+ edge calibration gap reduced from -10% to < -5%
- [ ] No regression in 15-20% edge bucket (currently excellent at -0.8%)
- [ ] Overall win rate maintained > 55%

---

## Medium Priority

### Ludi Lens Dashboard (Week 6)
- [ ] Streamlit dashboard scaffold (`app.py`)
- [ ] "War Room" visual design implementation
- [ ] Real-time prop display integration
- [ ] Historical performance charts

### CLV Tracking Enhancement
- [x] Historical CLV backfill (Jan 7-29, 2026) - 63.5% of bets updated ✅
- [ ] `scripts/capture_closing_lines.py` (5 min before tipoff) → **Moved to Phase 6.5**
- [ ] `utils/clv_calculator.py` implementation → **Moved to Phase 6.5**
- [ ] CLV reporting in PM Bot daily summary
- [ ] 30-day rolling CLV metrics

### Data Pipeline Improvements
- [ ] Multi-book arbitrage detection
- [ ] Steam move detection (rapid line movement alerts)

---

## Low Priority

### Future Enhancements
- [ ] DFS multiplier conversion (PrizePicks/Underdog)
- [ ] Strength of Schedule (SOS) adjustment
- [x] Depth Chart Authority modeling → **COMPLETE in Phase 6.1** ✅
- [ ] Shooting Luck Deviation signals

---

## Archive

For detailed historical status updates and completion reports, see:
- **docs/STATUS_HISTORY.md** - Comprehensive historical record (Phases 1-4)
- **docs/archive/PHASE_5_5_COMPLETION_LOG.md** - Phase 5.5 completion details (Feb 1)
- **docs/archive/JAN_2026_SYSTEM_STABILITY_FIXES.md** - January fixes log (Jan 16-31)
- **docs/DATABASE_SYNC_REDESIGN_HANDOFF.md** - Database architecture redesign (Feb 1)
- **reports/CALIBRATION_RECOMMENDATIONS_FEB2.md** - Calibration analysis & recommendations (Feb 2)
- **reports/performance_analysis_feb2.md** - Full performance breakdown by stat/position/archetype (Feb 2)
- **Phase 6.1 Completion** - See "Phase 6.1 Completion Summary" section above (Feb 2)
- **docs/archive/** - Organized by phase/topic

### Phase 6.1 Completion Summary (Feb 2, 2026 @ 7:00 PM EST)

**Deliverables:**
| File | Action | Status |
|------|--------|--------|
| `scripts/sync_depth_charts.py` | Created | ✅ |
| `tests/test_depth_charts.py` | Created | ✅ |
| `database.py` | Modified - added `depth_charts` table | ✅ |
| `module_e.py` | Modified - added `get_starter_status()` | ✅ |

**Results:**
- All 30 teams synced to `depth_charts` table
- 150 starters identified (30 teams × 5 positions)
- `players.is_starter` column populated
- All 7 unit tests pass

**Next:** Phase 6.2 - BENEFICIARY Scenario Pipeline Fix

---

### Phase 6 Discovery Notes (Feb 2, 2026)
**Data Gaps Identified:**
- 99.9% of `bet_recommendations` have `scenario=NULL` (BENEFICIARY not being tagged)
- ~~Tank01 depth charts endpoint available but not implemented~~ ✅ FIXED
- `player_touches`, `player_drives`, `player_wowy_stats` tables exist but unused
- RotoWire ROLE_CHANGE parsing works but no downstream handling
- CLV column stores closing LINE value, not CLV difference (fixed via SQL calculation)

**CLV Backfill Results:**
- Script: `scripts/sync_historical_odds.py`
- Coverage: 63.5% of bets (Jan 7-29) updated with closing lines
- Finding: Positive CLV across ALL edge buckets (model finding real value)
