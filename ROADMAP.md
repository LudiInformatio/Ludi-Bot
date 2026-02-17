# Ludi-Bot Roadmap

**Last Updated:** February 16, 2026 (5:15 PM EST)
**Current Phase:** Phase 7 - All-Star Break Sprint
**Active Work:** Phase 7.9.5 Module Overhauls — C ✅, E ✅, F 🔄 (agent executing), Archetype Overhaul 🔄 (agent executing)
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
**Status:** ✅ Sub-phases 7.1-7.8 COMPLETE | Phase 7.9 Backtest Audit IN PROGRESS
**Remaining (blocked until Feb 19 — first game day back):**
- [ ] Run full pipeline dry run with all new data sources active
- [ ] Validate all workflows via manual trigger on live game day

**Phase 7.9: Backtest Audit & Analysis** 🔄 IN PROGRESS (Feb 15-16, 2026)
**Dataset:** 15,575 settled bets (Jan 7 - Feb 12), 14,423 after VOID exclusion
**Data:** 21 game dates, 14 with morning+evening pipeline runs (pseudo-CLV pairs)
**Lost data:** ~5,593 bets across 15 game days (runner DB wiped by `clean: true` bug, fixed Feb 2)
**Reports:** 16 analysis reports generated in `reports/` (see `reports/MASTER_TREND_REPORT_2026-02-15.md`)

*Phase 1: Script Audits*
- [x] Audit `generate_validation_report.py` — per-stat RMSE, Brier score, edge/tier checks
- [x] Audit `scripts/analyze_model_performance.py` — 10-table analyzer, dual-pool, cross-cuts
- [x] Audit `backtest_archetypes.py` + Full Classification System Audit (5 parts)
  - Team Defensive: 93% NEUTRAL → 23% NEUTRAL, PERIMETER reactivated (16 dead branches fixed)
  - Team Offensive: 100% BALANCED → 47% BALANCED, name mismatch fixed, all 4 boosts verified
  - Player Archetypes: NULL 52→21, TWO_WAY_WING 59→3, 300 players reclassified, 96% valid
  - Backtest: 6/7 stats passing (STL 0.96 > 0.8 target — flagged)
- [ ] Audit `backtest_regression.py` — FG% regression-to-mean (low priority)
- [x] Audit `scripts/backtest_fatigue_21day.py` — V5.2 modifiers applied, markdown output added
- [x] Audit `scripts/backtest_playtype_trends_14day.py` — performance metrics added

*Phase 1b: 14-Day Trend Analysis (bonus)*
- [x] Fatigue trends (21-day window, 2,484 player-games)
- [x] Defensive scheme performance by scheme (6 schemes)
- [x] Player drift analysis (902 players)
- [x] Archetype vs Synergy validation (258/482 players with data)
- [x] Edge calibration analysis (5 buckets)
- [x] Stat category OVER/UNDER trends
- [x] Master trend report consolidating all findings

*Phase 2: Run Analysis*
- [x] Full pipeline scorecard — 55% WR, -3.34u P&L, Brier 0.2787
- [x] Per-stat deep dive — OVER leaks -649u, UNDER profits +645u
- [x] Direction analysis — OVER 46.1% WR, UNDER 59.0% WR (12.9% gap)
- [x] Edge calibration — 5-10% = 57.9% (only calibrated), 25%+ = 50.3% (broken)
- [x] Game context — moderate favorites (-7 to -3) = +172u sweet spot
- [x] Cross-cut analysis — archetype alignment +2.4% WR when Synergy-matched

*Phase 3: Fix Critical Issues (Module Overhauls)*
- [x] Fix Module C OVER projection bias (46.1% WR on OVERs) ✅ commit `93635dc` — V4.0 overhaul: per-player shooting %, Poisson fix, opponent defense, fatigue tax, drives context
- [x] Fix Module E vs_FUNNEL matchup logic (-105u at 49.6% WR) ✅ commit `d00afd0` — 9-step overhaul: duplicate B2B removed, ±25% global cap, FUNNEL dedup, classifier retuned
- [-] Investigate & fix Module F edge/tier logic (inverted edge calibration) 🔄 Agent executing — 9 bugs (2 P0, 3 P1, 4 P2) + combo props (PRA/PA/PR/RA) via BDL
- [-] Player Archetype System Overhaul 🔄 Agent executing — 6 phases: new defensive archetypes (5 types replacing 2 broken), Synergy-powered secondary playtypes (hybrid 70/30), GENERALIST reduction (<25%), defensive Synergy scraping, tag_classifier sync, Module F re-enable. Plan: `docs/ARCHETYPE_OVERHAUL_PLAN.md`

*Phase 4: Forward Plan*
- [ ] Gap analysis & forward recommendations report
- [ ] Feb 19 full pipeline dry run with all module fixes active

**Critical Findings:**
| Finding | Impact | Status |
|---------|--------|--------|
| 25%+ edge = 50% WR (expected 74%) | Edge calc broken above 20% | 🔄 Module F fix in progress (edge dampening + 9 bugs) |
| OVER 46.1% WR / UNDER 59.0% WR | Systematic over-projection | ✅ Module C V4.0 fix (commit `93635dc`) |
| vs_FUNNEL -105u at 49.6% WR | TRANSITION +15% too aggressive | ✅ Module E fix — FUNNEL dedup (commit `d00afd0`) |
| Home B2B Guards +3.05 pts error | Guard Tax too conservative | ✅ Module E fix — duplicate B2B removed (commit `d00afd0`) |
| Spread sign strips abs() | Blowout tax on wrong team every game | 🔄 Module F Step 1 (P0 bug) |
| 3 stat keys unnormalized | STL/BLK/TOV: no sim hit rates | 🔄 Module F Step 3 (P1 bug) |
| Referee notes never generated | ref_data vs ref_impact key mismatch | 🔄 Module F Step 2 (P0 bug) |
| Defensive activation 7% → 77% | Classification fixes applied | ✅ Fixed |
| Offensive activation 0% → 53% | Name mismatch + classifier fixed | ✅ Fixed |
| Valid archetypes 56% → 96% | 300 players reclassified | ✅ Fixed |
| vs_NEUTRAL +74u, 58.9% WR | Base projections strong | ✅ Working |
| Archetype alignment +2.4% WR | Classification quality matters | ✅ Validated |
| Rested Home -0.35 pts error | Nearly perfect calibration | ✅ Working |

**Phase 7.9.5: Module Overhauls** 🔄 IN PROGRESS (Feb 16, 2026)
**Goal:** Fix all critical issues identified in Phase 7.9 backtest audit across 3 core modules + classifiers
**Plans:** `docs/module_f_overhaul.md` (Module F), `docs/module_f_agent.md` (agent prompt)

| Module | Status | Commit | Key Fixes |
|--------|--------|--------|-----------|
| C: Oracle | ✅ DONE | `93635dc` | Per-player FG%, Poisson fix, opponent defense, fatigue tax, drives context, data contract |
| E: Calibrator | ✅ DONE | `d00afd0` | Duplicate B2B removed, ±25% global cap, FUNNEL dedup, classifier retuned, opponent profiles wired |
| F: Alchemist | 🔄 Agent executing | — | 9 bugs (spread sign, ref key, stat normalization, gold combos, display dict) + combo props (PRA/PA/PR/RA) via BDL |
| Archetype System | 🔄 Agent executing | — | 5 new defensive archetypes, Synergy hybrid scoring, GENERALIST <25%, defensive Synergy scraping |

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
- [x] Validate all workflows on Feb 19 (first game day back) → moved to Phase 7 top-level remaining

**Phase 7.5: Ludi Lens Scaffold (stretch)**
- [ ] Streamlit app scaffold (`app.py`)
- [ ] War Room theme (Dark Navy + Gold + Emerald)

**Phase 7.6: Post-Trade Deadline Roster Verification** ✅ COMPLETE (Feb 15, 2026)
- [x] Clean `players` table (1005 active → 503, removed 502 composite duplicates + stale entries)
- [x] Re-sync depth charts (722 entries, 150 starters, 30 teams)
- [x] Re-sync WOWY data (base: 357 records, four-factor: 292 players)
- [x] Update `player_canonical_ids` for traded players (60 team assignments updated)
- [x] Verify traded players' stats split correctly (pre-trade vs post-trade team)
- [x] Flag players traded but not yet debuted for new team (DNP/injured)
- [x] Fix "XXX" team assignment (1 placeholder deleted)
- [x] Fix IND inflated roster (40 → 17 active players)
- [-] Re-run assist_combos sync post-deadline → skipped (already refreshed Feb 14)
- [x] Validate all downstream tables reflect correct team assignments
- [x] Fix non-standard abbreviations (GS→GSW, NO→NOP, NY→NYK, PHO→PHX, SA→SAS)
- [x] RosterValidator applied 229 changes (134 trades, 32 signings, 63 waivers)
- [x] Resolved 16 diacritical name mismatches (Jokić→Jokic, Dončić→Doncic, etc.)
- [x] Module E smoke test passed

**Phase 7.7: Full Integration Audit + BDL Fallback** ✅ COMPLETE (Feb 15, 2026)
- [x] BDL game lines fallback (Module A + CLV capture)
- [x] GitHub Actions updated with BALLDONTLIE_KEY
- [x] Refresh stale PBP Stats data (11,189 records, 8 tables, BDL migration for 5 tables)
- [x] Module F V5.2: negative edge fix, edge dampening, composite tiers, tier-based sizing
- [x] Settle/void 436 unsettled bets (241 NO_GAME, 195 DNP)
- [x] End-to-end integration audit (WOWY import fix, BDL tracking wired, schedule collision fixed)
- [x] Verify sync script → table → module consumer paths

**Phase 7.8: Workflow Hardening + Claude Ops Hub** ✅ COMPLETE (Feb 15, 2026)
- [x] GitHub Actions audit: 7 fixes across 8 workflows
  - Disabled redundant tracking_sync (replaced by BDL in data_sync)
  - Fixed db_backup schedule collision (09:00→06:00 UTC)
  - Added Telegram failure alerts to 6 silent workflows
  - Removed stale Jan 9 test cron from nightly_debrief
  - Removed unused secrets from wowy_sync
  - Consolidated duplicate dedup+index blocks (data_sync owns this)
  - Reduced Ghost Protocol to Sunday only (BDL covers weekdays)
- [x] Claude Ops Hub: reactive failure diagnosis for 14 monitored workflows
  - 5 domain sub-agents (Data Sync, Pipeline, Database, Settlement, Validation)
  - Auto-creates GitHub issues with root cause + recommended fix
- [x] Silent failure elimination: 3 critical fixes + 2 freshness gates
  - CLV capture: removed continue-on-error (must fail loudly)
  - Health monitor: removed continue-on-error (drift detection critical)
  - QA check: fixed self-masking (broken gh CLI no longer reports "all clear")
  - Data freshness gate in data_sync (fails if games played but no logs synced)
  - Pre-simulation freshness check in pipeline (blocks stale-data runs)
- [x] Runner/local DB split-brain fix: symlinked runner ludi.db → local project
  - Imported 5,970 missing bets (Feb 2-12) from runner DB
  - Settled 716 unsettled bets (all VOID-DNP)
  - Single source of truth going forward (no more data divergence)

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
- [x] Verify all workflows via manual trigger → moved to Phase 7 top-level remaining

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

### Historical Odds Backfill (March 2026)
**Context:** ~5,593 bets lost across 15 game days (Jan 8,10,16-28,30-31,Feb 1) due to `clean: true` bug wiping runner DB between workflow runs. Fix deployed Feb 2. Bets were confirmed generated via workflow logs but individual records are unrecoverable.
- [ ] Backfill historical odds via The-Odds-API `/v4/historical/` endpoint (~10 credits/query)
- [ ] Re-run pipeline for 15 missing dates to regenerate bets with historical odds
- [ ] Settle regenerated bets against existing game logs
- **Blocked until:** March 2026 (Feb Odds API quota exhausted by Ludi Lite project; 20K credits/month)

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

## Future Phases

### Phase 8: AI-Enhanced Pipeline (Claude Integration)

**Goal:** Add Claude as an analytical reasoning layer on top of the deterministic pipeline
**Principle:** LLMs orchestrate and reason — never calculate. Math stays deterministic.
**Status:** 📋 PLANNED — detailed design complete, pending Phase 7.9 completion
**Design Doc:** `.claude/plans/crystalline-swimming-horizon.md`
**Estimated Daily Cost:** ~$1.17/day (~$35/month)

**Ground Rules:**
- Claude handles reasoning/analysis ONLY — never factual NBA data (enforced by CLAUDE.md Critical Data Rules)
- All NBA facts come from `ludi.db` or live APIs (fetched, not recalled)
- Raw math stays deterministic (Poisson sims, devigging, Kelly sizing)
- All Claude outputs must be auditable/reproducible
- Graceful degradation: if Claude API fails, fall back to existing rule-based logic

**Sub-Phases (recommended implementation order):**

| # | Sub-Phase | Priority | Description | Daily Cost |
|---|-----------|----------|-------------|------------|
| 8.1 | Injury Intelligence Upgrade | HIGH | BDL → primary, Claude for ambiguous text | ~$0.20 |
| 8.5 | Play Curation Engine | HIGH | Sanity gate (Haiku) + Top 5 curation (Sonnet) | ~$0.20 |
| 8.2 | Game Notes Generator | HIGH | Analytical Telegram briefings | ~$0.35 |
| 8.3 | Player Spotlight Cards | HIGH | Per-bet narratives for DIAMOND/BLUE CHIP | ~$0.25 |
| 8.7 | Perplexity MCP | MEDIUM | Real-time search replacing DuckDuckGo | ~$0.10 |
| 8.4 | Archetype Classifier Fix | MEDIUM | Weekly batch classification via Claude | ~$0.07 |
| 8.6 | MCP Server Integration | LOW | BDL + Odds API MCP for Ops Hub | $0 |

**Shared Infrastructure:**
- [ ] Create `utils/claude_client.py` — shared Anthropic SDK wrapper
- [ ] Add `ANTHROPIC_API_KEY` to config.py and `.env.template`

**Key Tasks:**
- [ ] 8.1: Promote BDL injuries to primary, add Claude reasoning for ambiguous statuses
- [ ] 8.5: Sanity gate + holistic "Top 5 Plays" curation with reasoning
- [ ] 8.2: Per-game analytical cards with Key Advantages, Injury Beneficiaries, WOWY deltas
- [ ] 8.3: 2-3 sentence narratives with playtype breakdown, DVP ranking, hit rates
- [ ] 8.7: Perplexity MCP replacing Module D's DuckDuckGo `_nuance_check()`
- [ ] 8.4: `scripts/classify_archetypes.py` weekly batch, re-enable Module F modifiers
- [ ] 8.6: Configure BDL MCP server, add to Claude Ops Hub

**Competitive Research:** See `docs/FUTURE_DATA_SOURCES.md` §5 for UI/UX patterns from 6 betting analytics sites (PropsMadness, LandYourBets, BucketsToBucks, Outlier.bet, Props.cash, StraightBettin)

---

## Archive

- **docs/archive/PHASE_6_5_DETAILS.md** — Phase 6.5 step-by-step details
- **docs/archive/PHASE_5_5_COMPLETION_LOG.md** — Phase 5.5 completion
- **docs/STATUS_HISTORY.md** — Phases 1-4 history
- **reports/** — Calibration analysis, performance breakdowns
- **docs/archive/** — All other completion reports, organized by phase