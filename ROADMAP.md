# Ludi-Bot Roadmap

**Last Updated:** January 29, 2026 @ 3:55 PM EST
**Current Phase:** Phase 5 - Production Deployment & Automation

This is the single source of truth for project tasks and priorities.

---

## Legend

- `[ ]` = Todo
- `[-]` = In Progress
- `[x]` = Completed

---

## High Priority

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
**Status:** Phase 0 Complete ✅ | Phase 1 Complete ✅
**Started:** January 29, 2026
**Completed:** January 29, 2026

**Phase 0: URGENT FIX - ✅ COMPLETE**
- [x] Fix STAT_MAPPING in main.py (add STL, BLK, DREB) - Commits: 27f2392, b3cb571
- [x] Production test verified STL/BLK projections work (Alex Sarr: 2.0 BLK, Kyshawn George: 1.4 STL)
- [x] Committed and deployed fix

**Phase 1: 16-Archetype System (Week 1-2) - ✅ COMPLETE**
- [x] Implement unified archetype classification in module_e.py
- [x] Merge synergy playtypes as modifiers (not separate tags)
- [x] Add new archetypes:
  - TIER 1 ENGINES: HELIOCENTRIC_MAESTRO, ISO_ASSASSIN, SLASHING_CREATOR, JUMBO_FACILITATOR
  - TIER 2 SCORERS: SNIPER_ELITE, TWO_LEVEL_SCORER, ATHLETIC_FINISHER
  - TIER 3 BIG MEN: WARRIOR_BIG, VULTURE_BIG, STRETCH_BIG, POST_ANCHOR, ROLL_MAN
  - TIER 4 ROLE PLAYERS: SCREEN_NAVIGATOR, ISLAND_DEFENDER, CUTTER_SPECIALIST, FACILITATOR
- [x] Update matchup matrix for all 16 archetypes
- [x] Update populate_archetypes.py with new classification logic
- [x] Re-run archetype population to reduce GENERALIST % (now 25.4%, was 73.8%)
- [x] Database cleanup: Removed old archetype entries (TWO_WAY_WING, RIM_RUNNER, HELIOCENTRIC)

**Phase 2: Enhanced Defensive Tracking (Week 2)**
- [ ] Add opponent context (TOV rate, FGA, 3PA%) to player packets in main.py
- [ ] Implement contextual defensive stat modifiers in Module E
- [ ] Test STL boost vs high-turnover teams (>15% TO rate)
- [ ] Test BLK boost vs paint-heavy teams (>65% 2PA rate)

**Phase 3: SportVu Integration (Optional - Week 3-4)**
- [ ] Create scripts/sync_sportvu_tracking.py for rebounding data
- [ ] Integrate contested/uncontested rebound % for WARRIOR vs VULTURE
- [ ] Add defensive matchup tracking (FG% vs screens, ISO, etc.)

**Success Criteria:**
- [x] STL/BLK projections show realistic values (not 0.0) ✅
- [x] 16 archetypes implemented with <30% GENERALIST fallback (25.4%) ✅
- [x] Bet recommendations include new archetype tags ✅
- [x] No regression in core stat accuracy ✅
- [x] Database contains only 17 archetype types (16 new + GENERALIST) ✅

---

## Medium Priority

### Ludi Lens Dashboard (Week 6)
- [ ] Streamlit dashboard scaffold (`app.py`)
- [ ] "War Room" visual design implementation
- [ ] Real-time prop display integration
- [ ] Historical performance charts

### CLV Tracking Enhancement
- [ ] `scripts/capture_closing_lines.py` (5 min before tipoff)
- [ ] `utils/clv_calculator.py` implementation
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
- [ ] Depth Chart Authority modeling
- [ ] Shooting Luck Deviation signals

---

## Recently Completed

### System Stability & Browser Automation Revamp - 2026/01/29
- [x] Resolved CI/CD race conditions (added `git pull --rebase`) in 5 core workflows
- [x] Created `utils/browser_utils.py` and `utils/browser_utils_async.py` for centralized suppression & stealth
- [x] Added OddsShark modal suppression & safe selector waits
- [x] Refactored all 6 scrapers (Sync, Backfill, Referees, Intel, WOWY, Synergy) to use unified logic
- [x] Improved reliability against OneTrust modals, newsletters, and WAF detection across all environments
- [x] Standardized on `domcontentloaded` wait strategy to prevent hanging on external tracking pixels

### WOWY Sync Repair - 2026/01/29
- [x] Fixed `scripts/sync_wowy_data.py` import ordering bug (ModuleNotFoundError)
- [x] Implemented Game ID Auto-Healing for custom Tank01 IDs
- [x] Backfilled 8 days of missing data (Jan 20-27) - 1,116 records restored

### Module G Browser Timeout Fix - 2026/01/29
- [x] Switched scraper to `headless=False` (Visible Browser) for reliability
- [x] Added Date Dropdown interaction logic to force layout update
- [x] Relaxed navigation timeout to 60s
- [x] Verified with manual dry-run (8 games scraped)

### Basketball-Reference Scraper Fix - 2026/01/29
- [x] Migrated `scrape_referee_roster.py` to Playwright (Bypass 403 Forbidden)
- [x] Implemented MultiIndex column flattening for new table layout
- [x] Verified live scraping of 72 referees (replacing fallback)

### Alt Line Bug Fix & Archetype Verification - 2026/01/29
- [x] Fixed alt line selection bug in Module A (voting mechanism)
- [x] Added NC Legal coverage validation (defense-in-depth)
- [x] Verified secondary playtypes system deployed and active
- [x] Verified team offensive types system deployed and active
- [x] Fixed BALL_HOG archetype (1 player updated to HELIOCENTRIC)
- [x] Production tested: Max ratio reduced from 9.6x to 1.64x
- [x] Created comprehensive documentation (AUDIT_FINDINGS_JAN28.md, TEST_RESULTS_JAN29.md)

### Referee Intelligence Repair - 2026/01/28
- [x] Diagnosed empty table issue (CSR/JavaScript requirement)
- [x] Implemented "Date Toggle" workaround (Yesterday -> Today) to force data load
- [x] Added "Fallback Validation" (Critical Alert if 0 refs found)
- [x] Upgraded scraper to Playwright for reliable rendering
- [x] Identified Historical Backfill opportunity via date picker

### Phase 4: B2B Fatigue & Schedule Integration - 2026/01/21
- [x] Integrated research-backed fatigue modifiers
- [x] Tuned modifiers for 2025-26 player resilience
- [x] 60-day backtest validated (+0.56 pts mean error)
- [x] Guard resilience confirmed (+1.45 pts vs historical)

### Phase 3: Secondary Playtype Matchups - 2026/01/21
- [x] Implemented player-vs-defense matchups (ISO, P&R, Spot-Up)
- [x] 8 specific matchups verified
- [x] 14-day defensive trends validated

### Phase 1: Synergy Playtype Integration - 2026/01/21
- [x] Integrated NBA Synergy efficiency metrics
- [x] 3 new calibration functions in Module E
- [x] 5 new database tables created
- [x] Ghost Protocol scraper operational

### Referee Sync Orchestration Fix - 2026/01/20
- [x] Auto-population system for games table
- [x] Module G enhancement complete

### Tank01 ID Integrity Update - 2026/01/20
- [x] Canonical ID system implemented
- [x] Auto-healing ingestion in database.py

### WOWY Calculator Integration - 2026/01/18
- [x] `utils/wowy_calculator.py` (450 lines)
- [x] Smart blowout tax (V4.7)

### Module G Referee Intelligence - 2026/01/17
- [x] 78 referees in database (100% coverage)
- [x] Day forward capture system
- [x] Weekly zebra reports automated

### Ghost Protocol Backfill - 2026/01/16
- [x] ~14,700 records (Physics: 9.4k | Brain: 5.3k)

---

## Archive

For detailed historical status updates, see `docs/STATUS_HISTORY.md`.
