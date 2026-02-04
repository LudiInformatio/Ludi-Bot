# Ludi-Bot Roadmap

**Last Updated:** February 4, 2026 @ 11:30 AM EST
**Current Phase:** Phase 6 - Full Data Integration
**Active Work:** Phase 6.5 (Forward CLV Capture) - Ready to Start
**Completed:** Phase 5.5 Phases 0-2 + Database Sync Redesign + Feb 2 Calibration + Performance Analysis + CLV Backfill + **Phase 6.1 Depth Charts** + **Phase 6.2 BENEFICIARY Pipeline** + **Phase 6.3 WOWY Enhancement** + **Phase 6.4 System Refinements** + **Referee Backfill** + **Phase 6.5b COMPLETE** + **Phase 6.5c COMPLETE** + **Phase 6.5d COMPLETE** + **Phase 6.5e COMPLETE (Workflow Fixes)**

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
- [x] Add to `data_sync.yml` workflow (Daily 8 AM UTC / 3 AM EST) ✅
- [x] Create `tests/test_wowy_enhancement.py` with 5 unit tests ✅

**Phase 6.4: System Refinements & ROLE_CHANGE Detection** ✅ COMPLETE (Feb 2, 2026)
- [x] Module G Foul Data Fix - Fixed uppercase 'PF' key in Tank01 API response ✅
- [x] Full Season PF Backfill - Re-fetched entire season (Oct 21 - Feb 1) with correct PF extraction ✅
- [x] WOWY Season Progress Calibration - Replaced with calendar-based approach (59.1% accuracy) ✅
- [x] ROLE_CHANGE handler in Module E - Dynamic ±8 min adjustments for starter elevation/demotion ✅
- [x] Created `tests/test_role_change_handler.py` with 3 unit tests ✅
- [x] Created `docs/PHASE_6_4_COMPLETION_REPORT.md` ✅
- [x] Referee Backfill Execution - 60-day backfill via nba_api (452 games, 100% success) ✅
- [x] Referee Learning Re-run - 171 games processed, 65 referee profiles updated ✅

**PF Data Coverage:** 21,328 / 26,936 game logs (79.2%) for full 2025-26 season
**Referee Coverage:** 515 / 1,769 games (29.1%) - up from 3.6%
**Test Results:** 3/3 unit tests passing
**Time Investment:** 2.5 hours (vs 3.5 hours estimated - 29% efficiency gain)

**Phase 6.5: Forward CLV Capture**
- [ ] Create `scripts/capture_closing_lines.py` (runs 5 min before tipoff)
- [ ] Store closing odds in `bet_recommendations.closing_odds_*` columns
- [ ] Calculate and store real CLV (not just closing line value)
- [ ] Add CLV metrics to daily Telegram summary

**Phase 6.5b: Daily Data Sync Fixes (NEW - Feb 3, 2026)** 🔄 IN PROGRESS
**Goal:** Fix data_sync.yml workflow issues and add safeguards for future backfills
**Priority:** HIGH (critical infrastructure, affects all data pipelines)

**Context:**
- Tank01 API was over-consumed during one-off backfill (2,097 vs 1,000 limit)
- Normal daily usage is low (~20-50 requests), but no safeguards exist
- Health monitor was broken (now fixed), revealing deeper sync issues
- Module H writes JSON → SQLite (unnecessary complexity)

**Step 1: Health Monitor Schema Fix** ✅ COMPLETE (Feb 3, 10:00 AM)
- [x] Created `SCHEMA_AUDIT_REPORT.md` documenting all mismatches
- [x] Fixed `monitor_system_health.py` SQL queries
- [x] Verified script runs without errors

**Step 2: Diagnostic - Identify Missing Dates** ✅ COMPLETE (Feb 3, 11:30 AM)
- [x] Created `scripts/audit_sync_gaps.py` (210 lines)
- [x] Queries `ludi.db` for distinct game_date values in `player_game_logs`
- [x] Compares against NBA schedule (Oct 22, 2025 to yesterday)
- [x] Outputs missing dates to `cache/pending_sync_dates.json`
- [x] Generated `SYNC_GAP_AUDIT_REPORT.md`
- **Result:** 13 dates need backfill (3 missing + 10 partial syncs)

**Step 3: Tank01 API Rate Limiting** ✅ COMPLETE (Feb 3, 12:00 PM)
- [x] Added configurable daily request budget to Module H (default: 200 requests)
- [x] Checks remaining quota BEFORE each API call
- [x] Stops gracefully if budget exhausted, saves state
- [x] CLI override: `--budget` argument
- **Result:** Budget enforcement tested and working

**Step 4: Resume State for Multi-Day Backfills** ✅ COMPLETE (Feb 3, 1:00 PM)
- [x] Created `cache/historian_sync_state.json` for resume tracking
- [x] Module H checks `pending_sync_dates.json` OR resume state
- [x] Processes dates oldest-to-newest
- [x] Saves progress after each successful date
- [x] Telegram alerts on pause/completion
- [x] Self-cleaning (deletes state/audit files on completion)
- [x] 6/6 unit tests passing (`tests/test_historian_resume.py`)
- **Result:** Full resume capability with graceful error handling

**Phase 6.5c: PBP Stats API Fixes** ✅ COMPLETE (Feb 3, 2026)
- [x] Added job-level timeout (60 min) to `data_sync.yml` ✅
- [x] Added step-level timeouts (5-30 min per step) ✅
- [x] Increased API timeout from 60s → 120s in `pbp_stats_client.py` ✅
- [x] Fixed retry logic: Added 429 handling, `total=3, backoff_factor=2` ✅
- [x] Implemented local response caching in `cache/pbp_stats/` ✅
- [x] Added leverage filtering to WOWY queries ✅
- **Results:** 19.4x performance improvement (7.46s → 0.385s cached)
- **QA Reports:** `PHASE_1_QA_REPORT.md`, `PHASE_2_QA_REPORT.md`

**Future PBP Stats Optimizations:** See `docs/FUTURE_DATA_SOURCES.md` Section 4 for:
- Resume capability for WOWY sync
- Unused data integration (shot quality, speed, TS%)
- Pipeline redundancy removal
- Missing endpoint additions (assist combos, four factors, possessions)

---

**Phase 6.5c: Workflow Infrastructure Fixes** ✅ COMPLETE (Feb 3, 4:00 PM)
**Goal:** Fix data_sync.yml workflow failures (5 consecutive days broken)
**Issues Fixed:**
1. `referee_daily_stats` missing UNIQUE constraint → ON CONFLICT errors in `learn_daily_trends.py`
2. WOWY sync using unresolved Tank01 composite IDs → 40% API failure rate

**Fixes Applied:**
- [x] Added unique index `idx_referee_daily_unique` on `(referee_id, sync_date)` to `database.py` ✅
- [x] Ran migration SQL on `ludi.db` to add index ✅
- [x] Updated `sync_pbp_wowy.py` to join with `player_canonical_ids` for ID resolution ✅
- [x] Created `scripts/validate_schema.py` for pre-flight schema checks ✅
- [x] Added schema validation step to `data_sync.yml` workflow ✅
- [x] Added `continue-on-error: true` to non-critical steps (WOWY, Star Bias) ✅
- [x] Added try/except wrapper in `learn_daily_trends.py` for per-game error handling ✅

**Verification:**
- ON CONFLICT upsert: ✅ Working
- Schema validation: ✅ All checks pass
- WOWY ID resolution: ✅ 100% success rate (was 60%)

**Step 5: Direct SQLite Writes (Architecture Cleanup)** ✅ COMPLETE (Feb 3, 2026 @ 2:30 PM)
- [x] Modify `module_h_historian.py` to write directly to `ludi.db` ✅
- [x] Use `ON CONFLICT DO UPDATE` pattern ✅
- [x] Reference `sync_pbp_wowy.py` for implementation pattern ✅
- [x] Update `data_sync.yml` to remove JSON migration step ✅

**Step 5.5: Canonical ID Resolution** ✅ COMPLETE (Feb 3, 2026 @ 3:30 PM)
**BONUS PHASE:** Critical data quality fix discovered during Step 5 verification
- [x] Added `_resolve_player_id()` method to Module H ✅
- [x] Created `scripts/migrate_dirty_player_ids.py` for data migration ✅
- [x] Reduced dirty IDs from 520 to 17 (96.7% reduction) ✅
- [x] Added 6 rotation players to `player_canonical_ids` table ✅
- [x] Created `tests/test_canonical_id_resolution.py` with unit tests ✅
- **Result:** 99.75% clean canonical IDs (26,942/27,009 records)

**Step 6: Database Consolidation (JSON Cleanup)** ✅ COMPLETE (Feb 3, 2026 @ 5:00 PM)
- [x] Remove `ludi_history_db.json` from git tracking ✅
- [x] Verify all JSON data exists in `player_game_logs` table (27,009 records) ✅
- [x] Delete local `ludi_history_db.json` file after verification ✅
- [x] Module H JSON references removed (completed in Step 5) ✅
- [x] Final backup created: `archives/data/ludi_history_db.json.final_backup` ✅
- **Architecture:** Eliminated 7.7MB JSON staging buffer + 2-step migration pipeline ✅

**Success Criteria:**
- [x] Module H respects daily budget, never exceeds quota ✅ (Step 3)
- [x] Incomplete syncs resume gracefully across workflow runs ✅ (Step 4)
- [x] JSON migration step removed from workflow ✅ (Step 5)
- [x] `ludi_history_db.json` removed from git and deleted locally ✅ (Step 6)
- [x] No missing dates in database (audit passes) ✅ (Phase 6.5d)
- [x] Health monitor shows tables updated within 24h ✅ (Phase 6.5e - workflows fixed)
- [x] Claude QA cron job active for automated failure detection ✅ (Phase 6.5e)

**Phase 6.5d: Canonical ID System Audit** ✅ COMPLETE (Feb 3, 2026 @ 8:00 PM)
**Goal:** Audit all modules for PlayerIDResolver compliance, fix remaining dirty IDs, add CI validation
**Priority:** HIGH (data quality infrastructure)

**Completed Steps:**
- [x] Step 1: Module compliance audit (9 modules reviewed) ✅
- [x] Step 2: Added Tank01 aliases for 4 NBA players (AJ Lawson, etc.) ✅
- [x] Step 3: Added 13 G-League players to `player_canonical_ids` ✅
- [x] Step 4: Created `docs/CANONICAL_ID_GUIDELINES.md` (enforcement documentation) ✅
- [x] Step 5: Created `scripts/validate_canonical_ids.py` (CI validation) ✅
- [x] Step 6: Added validation step to `data_sync.yml` workflow ✅

**Results:**
- Data Quality: 99.84% clean IDs (was 99.75%)
- Unresolvable IDs: 0 (was 17)
- Canonical Players: 520 (was 507)
- CI Validation: Automated

**Documentation:** `docs/PHASE_6_5D_COMPLETION_REPORT.md`

**Phase 6.5e: Workflow Infrastructure Fixes** ✅ COMPLETE (Feb 4, 2026 @ 11:30 AM)
**Goal:** Fix overnight GitHub Actions failures and add future-proofing
**Priority:** HIGH (5 workflows failing)

**Root Causes Identified:**
1. `sync_wowy_backfill.py` importing non-existent functions from `browser_utils.py`
2. Runner database missing `idx_referee_daily_unique` index (created before index was added)
3. `bet_logger.py` null division error when `profit_loss` is NULL
4. `weekly_validation.yml` filename mismatch and missing log file fallback

**Phase 1 Fixes Applied (10:35 AM):**
- [x] Fix 1: Updated `sync_wowy_backfill.py` imports + inlined Playwright setup ✅
- [x] Fix 2: Added index migration step to `data_sync.yml` ✅
- [x] Fix 3: Added null-safe ROI calculation in `bet_logger.py` ✅
- [x] Fix 4: Fixed filename + added fallback in `weekly_validation.yml` ✅

**Future-Proofing Added (10:45 AM):**
- [x] Added database index check to `wowy_sync.yml` ✅
- [x] Added database index check to `weekly_referee_sync.yml` ✅
- [x] Created `claude-qa-check.yml` - Daily Claude QA cron job (6 AM EST) ✅

**Phase 2 Enhancements (11:30 AM - Commit 76afa8b):**
- [x] Database initialization safeguard in `data_sync.yml` (checks integrity, reinits if corrupt) ✅
- [x] Health monitor `continue-on-error: true` in `daily_simulation_pipeline.yml` (pipeline shows success) ✅
- [x] Index verification step added to `referee_sync.yml` (consistency across workflows) ✅

**Results:**
- All 4 failed workflows now pass validation
- Database initialization safeguard prevents corrupt DB failures
- Production Pipeline shows SUCCESS (health alerts via Telegram)
- Database indexes verified across all key workflows
- Automated Claude QA for failure detection

**Commits:** `a0053a4` (Phase 1), `17fbf81` + `7c21a2a` (Future-proofing), `76afa8b` (Phase 2)
**Documentation:** `WORKFLOW_FIX_REPORT.md`

---

**Phase 6.6: API Audit & Optimization**
- [ ] Document all Tank01 endpoints in use vs available
- [ ] Document all The-Odds-API endpoints in use vs available
- [ ] Evaluate Ball Don't Lie API integration (free tier, 60 req/min)
- [ ] Create `docs/API_USAGE_AUDIT.md` with findings

---

### Database Architecture Strategy (Future-Proofing)

**Current State:** Single SQLite database (`ludi.db`) - 30 MB, 38 tables
**Target:** Clean architecture ready for multi-season and web app

**Phase 1: Consolidation (Phase 6.5b Step 5-6)**
- [ ] Remove JSON staging buffer (direct SQLite writes)
- [ ] All data flows directly to SQLite
- [ ] Single source of truth for all game data

**Phase 2: Multi-Season Support (Before 2026-27 Season)**
- [ ] Add season archive workflow: `archives/data/ludi_YYYY_YY.db`
- [ ] Create `scripts/archive_season.py` for end-of-season backup
- [ ] Document season rollover procedure in `docs/SEASON_ROLLOVER.md`

**Phase 3: Web App Migration (When Ludi Lens Launches)**
- [ ] Evaluate PostgreSQL vs SQLite for production web app
- [ ] If PostgreSQL: Use `pgloader` for migration
- [ ] Keep SQLite archives for historical seasons (read-only)
- [ ] Design API layer between frontend and database

---

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
- [x] Create `scripts/monitor_system_health.py` (data integrity + model drift alerts) ✅ FIXED (Feb 3, 2026)
- [x] Run referee backfill via `scripts/backfill_referee_assignments.py` (60-day, 452 games) ✅
  - Note: Script needs update to use `BoxScoreSummaryV3` (V2 deprecated after April 2025)
- [ ] Create `.github/workflows/weekly_validation.yml` (Tuesdays 4 AM EST)
- [ ] Implement automated weekly backtests with drift alerts
- [ ] Create `scripts/cleanup_old_logs.py` (30-day retention)
- [ ] Add `IS_PRODUCTION` flag handling in `config.py`
- [ ] Verify all workflows via manual trigger
- [ ] Update `docs/PRODUCTION_HANDBOOK.md`

**Health Monitor Fix (Feb 3, 2026):** ✅ COMPLETE
- [x] Diagnosed schema mismatches (8 columns across 7 tables)
- [x] Fixed `check_data_integrity()` - Added table-specific timestamp column mapping
- [x] Fixed `check_model_drift()` - Corrected column names (projection, line, true_edge)
- [x] Fixed `check_api_health()` - Updated parser to handle actual log format
- [x] All SQL errors resolved, script now runs successfully
- [x] Created `SCHEMA_AUDIT_REPORT.md` and `HEALTH_MONITOR_FIX_REPORT.md`
- **Test Results:** Exit code 0, all 6 data integrity checks passing
- **Time Investment:** 55 minutes (diagnosis + fixes + testing + documentation)

**Success Criteria:**
- [ ] `daily_simulation_pipeline.yml` operational and sending Telegram cards
- [x] `scripts/monitor_system_health.py` implemented and reporting status ✅
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
