# Ludi-Bot Roadmap

**Last Updated:** February 14, 2026
**Current Phase:** Phase 7 - All-Star Break Sprint
**Active Work:** Sprint 3 (Four-Factor WOWY + Leverage) + Post-Trade Deadline Roster Cleanup
**Completed:** Phases 5.5, 6.0-6.5f (see docs/archive/ for details)

This is the single source of truth for project tasks and priorities.

---

## Legend

- `[ ]` = Todo
- `[-]` = In Progress
- `[x]` = Completed

---

## High Priority

### Phase 7: All-Star Break Sprint (Feb 14-19, 2026)

**Goal:** Clean foundation, fix math, add API redundancy, prep for frontend
**Status:** 🔄 IN PROGRESS

**Phase 7.1: Git + Roadmap Cleanup** ✅ COMPLETE
- [x] Fix .gitignore, delete dead files, organize scripts
- [x] Archive completed roadmap details
- [x] Commit untracked reports

**Phase 7.2: Math Calibration V5.2** ✅ COMPLETE
- [x] Tiered stdev widening (60% at 20%+ edges, 40% at 15-20%)
- [x] Marginal edge filter (skip 20-22% edge bets)
- [x] Archetype edge bonuses/penalties (TWO_WAY_WING +3%, STRETCH_BIG -3%)
- [x] Starter status fix (use depth_charts instead of minutes heuristic)
- [x] Backtest validation (target: 20%+ edge WR >58%)

**Phase 7.3: Ball Don't Lie Integration** ✅ COMPLETE
- [x] Create `utils/bdl_client.py` (GOAT tier, 600 req/min, cached)
- [x] Module A fallback (odds + props)
- [x] Module D fallback (injuries)
- [x] API audit document (`docs/API_USAGE_AUDIT.md`)

**Phase 7.4: Backend Completion** ✅ COMPLETE (Feb 14, 2026)
- [x] Forward CLV capture (`scripts/capture_closing_lines.py`)
- [x] Integrate unused PBP Stats data (leverage/clutch tagging, WOWY activation)
- [x] Close Phase 5 gaps (log cleanup, IS_PRODUCTION flag)
- [ ] Validate all workflows on Feb 19 (first game day back)

**Phase 7.5: Ludi Lens Scaffold (stretch)**
- [ ] Streamlit app scaffold (`app.py`)
- [ ] War Room theme (Dark Navy + Gold + Emerald)

**Phase 7.6: Post-Trade Deadline Roster Verification** ⚠️ PRIORITY
- [ ] Clean `players` table (1005 active → ~450-510, remove duplicates/stale entries)
- [ ] Re-sync depth charts (last synced Feb 2, pre-deadline)
- [ ] Re-sync WOWY data (last synced Feb 3, pre-deadline)
- [ ] Update `player_canonical_ids` for traded players (new team mappings)
- [ ] Verify traded players' stats split correctly (pre-trade vs post-trade team)
- [ ] Flag players traded but not yet debuted for new team (DNP/injured)
- [ ] Fix "XXX" team assignment (1 player with invalid team)
- [ ] Fix IND inflated roster (40 active players, should be ~15-17)
- [ ] Re-run assist_combos sync post-deadline (team chemistry changed)
- [ ] Validate all downstream tables reflect correct team assignments

---

### Phase 6: Full Data Integration ✅ COMPLETE (Feb 2-4, 2026)

**Goal:** Integrate ALL unused data sources and fix broken data flows
**Result:** +292u profit, 55.7% win rate confirmed. Positive CLV across ALL edge buckets.

**Phase 6.1-6.4** ✅ COMPLETE — Depth charts, BENEFICIARY pipeline, WOWY enhancement, ROLE_CHANGE handler, referee backfill (515 games).
**Phase 6.5** — Forward CLV capture remaining items moved to Phase 7.4.

**Phase 6.5b: Daily Data Sync Fixes** ✅ COMPLETE (Feb 3, 2026)
Implemented Tank01 rate limiting (200 req/day budget), resume state for multi-day backfills,
direct SQLite writes (eliminated JSON staging), and canonical ID resolution (99.75% clean).
See `docs/archive/PHASE_6_5_DETAILS.md` for step-by-step details.

**Phase 6.5c: PBP Stats API Fixes** ✅ COMPLETE (Feb 3, 2026)
Added timeouts, retry logic with 429 handling, local response caching (19.4x speedup).
See `docs/archive/PHASE_6_5_DETAILS.md` for details.

**Phase 6.5c-ii: Workflow Infrastructure Fixes** ✅ COMPLETE (Feb 3, 2026)
Fixed referee UNIQUE constraint, WOWY ID resolution (100% success rate), schema validation.
See `docs/archive/PHASE_6_5_DETAILS.md` for details.

**Phase 6.5d: Canonical ID System Audit** ✅ COMPLETE (Feb 3, 2026)
99.84% clean IDs, 520 canonical players, CI validation automated.
See `docs/archive/PHASE_6_5_DETAILS.md` for details.

**Phase 6.5e: Workflow Infrastructure Fixes** ✅ COMPLETE (Feb 4, 2026)
Fixed 5 failing workflows, added Claude QA cron job, database initialization safeguards.
See `docs/archive/PHASE_6_5_DETAILS.md` for details.

**Phase 6.5f: Missing Index Fix** ✅ COMPLETE (Feb 4, 2026)
Added `idx_player_game_logs_unique`, standardized deduplication across 5 workflows.
See `docs/archive/PHASE_6_5_DETAILS.md` for details.

**Phase 6.6: API Audit & Optimization** ✅ COMPLETE (Feb 14, 2026)
- [x] Document all Tank01 endpoints in use vs available
- [x] Document all The-Odds-API endpoints in use vs available
- [x] Integrate Ball Don't Lie API (GOAT tier $39.99/mo, 600 req/min)
- [x] Create `docs/API_USAGE_AUDIT.md` with findings

**CLV Finding (Important Context):**
Historical CLV backfill (Jan 7-29) showed positive CLV across ALL edge buckets:
| Edge Bucket | Real CLV (pts) | Win Rate |
|-------------|----------------|----------|
| 5-10% | +0.013 | 58.3% |
| 10-15% | +0.050 | 52.8% |
| 15-20% | +0.096 | 58.6% |
| 20-25% | +0.115 | 51.5% |
| 25%+ | +0.147 | 51.6% |

---

### Phase 5: Production Deployment & Automation ✅ ESSENTIALLY COMPLETE

**Status:** 7/8 items done. Final item (Feb 19 workflow validation) pending first game day back.

- [x] Create/Update `daily_simulation_pipeline.yml` (11 AM EST trigger) ✅
- [x] `scripts/monitor_system_health.py` ✅ FIXED (Feb 3)
- [x] Referee backfill (60-day, 452 games) ✅
- [x] Create `.github/workflows/weekly_validation.yml` (Tuesdays 4 AM EST) ✅
- [x] Implement automated weekly backtests with drift alerts ✅
- [x] Create `scripts/cleanup_old_logs.py` (30-day retention) ✅
- [x] Add `IS_PRODUCTION` flag handling in `config.py` ✅ (Phase 7.4)
- [ ] Verify all workflows via manual trigger

---

### Database Architecture Strategy

**Current State:** Single SQLite database (`ludi.db`) - 30 MB, 38 tables

**Phase 1: Consolidation** ✅ COMPLETE (Phase 6.5b Steps 5-6)
- [x] JSON staging buffer removed (direct SQLite writes)
- [x] All data flows directly to SQLite
- [x] Single source of truth for all game data

**Phase 2: Multi-Season Support (Before 2026-27 Season)**
- [ ] Add season archive workflow: `archives/data/ludi_YYYY_YY.db`
- [ ] Create `scripts/archive_season.py` for end-of-season backup
- [ ] Document season rollover procedure in `docs/SEASON_ROLLOVER.md`

**Phase 3: Web App Migration (When Ludi Lens Launches)**
- [ ] Evaluate PostgreSQL vs SQLite for production web app
- [ ] Design API layer between frontend and database

---

## Medium Priority

### Ludi Lens Dashboard
- [ ] Streamlit dashboard scaffold (`app.py`)
- [ ] "War Room" visual design implementation
- [ ] Real-time prop display integration
- [ ] Historical performance charts

### CLV Tracking Enhancement
- [x] Historical CLV backfill (Jan 7-29, 2026) - 63.5% of bets updated ✅
- [x] Forward CLV capture → **COMPLETE in Phase 7.4** ✅
- [ ] CLV reporting in PM Bot daily summary
- [ ] 30-day rolling CLV metrics

### Dormant Data Activation (synced daily but unused in pipeline)
- [x] Integrate `shot_quality_avg` into Module C FG% simulation adjustment (499 players synced) ✅
- [x] Use rolling TS%, eFG% from `player_game_advanced` in Module C (12,179 records synced) ✅
- [x] Activate `player_defense` in Module E for matchup-based defensive adjustments (509 players) ✅
- [x] Integrate `player_touches` into Module E usage refinement (505 players synced) ✅
- [x] Add drives/assists boost in Module C using `player_drives` data (currently archetype-only) ✅
- [x] Add speed/fatigue context in Module E using `player_speed` data (currently archetype-only) ✅

### Missing PBP Stats Endpoints
- [x] Implement `get_assist_combo_summary` — fixes BENEFICIARY (currently 99.9% NULL) ✅
- [x] Implement `get_four_factor_on_off` — better WOWY (4 dimensions vs 1) ✅ (Sprint 3)
- [x] Implement `get_possessions` — clutch detection, blowout tax validation ✅ (Sprint 3)

### Data Pipeline Improvements
- [ ] Consolidate WOWY scripts (`sync_wowy_hybrid.py` + `sync_pbp_wowy.py` — duplicate work)
- [ ] Multi-book arbitrage detection
- [ ] Steam move detection (rapid line movement alerts)

---

## Low Priority

### Future Enhancements
- [ ] DFS multiplier conversion (PrizePicks/Underdog)
- [ ] Strength of Schedule (SOS) adjustment
- [x] Depth Chart Authority modeling → **COMPLETE in Phase 6.1** ✅
- [ ] Shooting Luck Deviation signals
- [ ] Sync PlayerRebounding tracking data (contested vs uncontested %)

---

## Archive

- **docs/archive/PHASE_6_5_DETAILS.md** — Phase 6.5 step-by-step details
- **docs/archive/PHASE_5_5_COMPLETION_LOG.md** — Phase 5.5 completion
- **docs/STATUS_HISTORY.md** — Phases 1-4 history
- **reports/** — Calibration analysis, performance breakdowns
- **docs/archive/** — All other completion reports, organized by phase