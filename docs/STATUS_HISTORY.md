# Status History Archive

This file contains the chronological status updates from the Ludi-Bot project. For current tasks and priorities, see `ROADMAP.md` in the project root.

---

## Current Status (as of Jan 21, 2026)

- **Phase**: Phase 4 Complete - B2B Fatigue & Schedule Integration
- **Next Phase**: Phase 5 - Production Deployment & Automation
- **Validation**: 60-day backtest (7,214 games, +0.56 pts mean error)

---

## V2.0 Final Integrity Checks (Jan 21, 2026)

- Roster Accuracy (2025-26): All scripts and database records verified for Klay Thompson (DAL), Clint Capela (HOU), and Tyus Jones (ORL).
- Global Debug Control: Added `DEBUG_LOG` flag to `config.py` for centralized calibration logging.
- Backtest Stability: 60-day window confirmed +/-0.6 pts mean error (Phase A conservative strategy).

---

## Week 3 Completion (Jan 21, 2026)

- Code Cleanup: BALL_HOG -> HELIOCENTRIC (4 files + Database updated)
- Backtest Validated: Dec 20-Jan 16 (28 days, 4,749 player-games)
- RMSE (PTS): 6.68 (Baseline established)
- B2B Fatigue Finding: B2B players *outperformed* rested players (+2.7% PTS) in this window. The implemented B2B Tax (-3%/-6%) resulted in under-projection (-3.36 mean error).
- Recommendation: Monitor B2B Tax closely; consider reducing modifiers if trend continues.
- Team Classifiers:
  - Offensive: 83% NEUTRAL (Due to missing `pace` data in `games` table).
  - Defensive: 47% SWITCH_HEAVY, 53% NEUTRAL (Valid distribution based on tracking data).
- Status: PRODUCTION READY (with monitoring)

---

## Phase 1: Synergy Playtype Integration (Jan 21, 2026) - COMPLETE

**Strategic Achievement:** Integrated NBA Synergy efficiency metrics into Module E calibration pipeline for granular matchup adjustments.

### Backtest Validation (Nov 20, 2025 - Jan 20, 2026)
- Test Window: 11,412 player-games (60 Days)
- Assist Hit Rate: +0.2% improvement (Consistent signal)
- Points RMSE: Neutral (+0.001)
- Stability: 100% (2,000 sims/game processed without error)

### Implementation Summary
- 3 New Calibration Functions (Module E lines 834-1008):
  1. PPP Efficiency Modifier: Uses weighted Points Per Possession across player's primary playtypes (league avg 1.05 PPP)
  2. Defensive Diff% Adjustment: Applies opponent rim protection penalty for rim-based scorers (e.g., Wembanyama -10.3% diff)
  3. Drives Assist Profile: Boosts assists for high-pass-rate playmakers (40%+ pass rate = +10% assists)

- Database Tables Created (5 new):
  - `player_synergy_playtypes`: 1,326 records (376 unique players, 5 playtypes synced)
  - `player_defense`: 509 players (Daeqwon Plowden -46.3% diff leads)
  - `player_drives`: 512 players (Kevin Porter Jr. 52.5% pass rate leads)
  - `player_touches`: Ready for future integration
  - `player_speed`: Ready for future integration

- Ghost Protocol Scraper: `scripts/sync_synergy_playtypes.py` (bypasses NBA.com WAF with visible browser mode)
- Validation Suite: 4/4 tests passed (10 players per function + integration test)

### Technical Details
- Integration Point: Module E line 677-681 (Layer 6.5 - between secondary playtypes and PBP shot quality)
- Error Handling: All functions wrapped in try/except with silent failures (won't break pipeline if data unavailable)
- Multiplicative Adjustments: Uses `_boost_stat()` pattern for backward compatibility
- Adjustment Caps: PPP +/-15%, Defensive Diff +/-12%, Drives +/-10% (prevents over-calibration)

---

## Phase 3: Secondary Playtype Matchups (Jan 21, 2026) - COMPLETE

**Strategic Achievement:** Implemented granular player-vs-defense matchups based on Synergy playtype data (ISO, P&R, Spot-Up).

### Validation Results
- Test Bench: 8 specific matchups verified (e.g., ISO tax vs Blitz, Spot-Up boost vs Pack).
- Sensitivity Analysis: 20-game sample window verified 13+ unique matchup triggers.
- 14-Day Trends: Defensive landscape confirmed stable (variance < 1.5% for all schemes).

### Key Matchup Matrix
- ISO_SCORER vs BLITZ: -8% PTS / +12% TOV (Pressure forces mistakes)
- SPOT_UP vs PAINT_PACK: +12% 3PM (Open looks from help-side sagging)
- P&R_ROLL_MAN vs PAINT_PACK: +15% PTS (Lob threat vs drop coverage)

---

## Phase 4: B2B Fatigue & Schedule Integration (Jan 21, 2026) - COMPLETE

**Strategic Achievement:** Integrated research-backed fatigue modifiers tuned for modern (2025-26) player resilience.

### Backtest Validation (Nov 22, 2025 - Jan 21, 2026)
- Test Window: 7,214 player-games (60 Days)
- Mean Error: +0.56 pts (Within +/-1.0 pt tolerance)
- Rested Home Edge Calibration: +0.30 pts error (Near perfect signal)
- Stability: 5/5 unit tests passed across all fatigue scenarios.

### Implementation Summary
- Tuned Modifiers (Phase A 50% Strategy):
  - Road B2B: -4.8% (Tuned from research -9.7%)
  - Home B2B: -1.5% (Tuned from research -3.0%)
  - Guard Tax: -2.0% (Tuned from research -4.0%)
  - Density Tax (4-in-5): -1.0% (Tuned from research -2.0%)
- Guard Resilience: Data confirmed modern guards outperform historical fatigue expectations by +1.45 pts.

---

## Week 1 Archetype Upgrade Summary (Jan 19, 2026)

- Data validation complete (93% tracking coverage, 4,842 player-games)
- 8 secondary playtypes calibrated: ISO_SCORER, P&R_HANDLER, P&R_ROLL_MAN, SPOT_UP, OFF_BALL_CUTTER, TRANSITION, PUTBACK, POST_UP
- Hybrid approach implemented: Position-based filtering + priority scoring
- Tag pollution eliminated (max 2 tags per player, down from 4)
- Production-ready validator: `scripts/test_playtype_thresholds_hybrid.py`
- Results documented in: `docs/WEEK1_HYBRID_FINAL_REPORT.md`

**Architecture:** Secondary playtypes enhance existing primary archetypes (HELIOCENTRIC, HUB_BIG, ELITE_SCORER, etc.) for granular matchup analysis.

---

## Jan 19, 2026: Archetype Synergy Upgrade Plan

**Strategic Objective:** Upgrade Module E (Calibrator) with NBA Synergy-aligned playtype classifications using 60-day backfilled tracking data.

### Key Upgrades Planned
1. Secondary Playtypes (8 types) - ISO_SCORER, P&R_HANDLER, P&R_ROLL_MAN, SPOT_UP, OFF_BALL_CUTTER, TRANSITION, PUTBACK, POST_UP
2. Team Offensive Types (6 types) - Automated weekly classification mirroring defensive types
3. Matchup Matrix Expansion - 14+ new research-backed modifiers
4. B2B Fatigue Integration - Guards -6% on road back-to-backs (Garcia et al. 2020)
5. Blowout Tax Validation - Backtest current smart blowout tax accuracy

### Implementation Strategy
**Strict Thresholds:** Players must meet 2 of 3 criteria for each secondary playtype (prevents tag pollution)

**Data Sources:**
- `player_game_tracking` - drives, catch_shoot, pull_up, speed, distance
- `player_game_advanced` - off_rating, def_rating, ts_pct
- `player_shot_quality` - rim_freq, corner_3_freq, shot quality
- `team_lineups` - WOWY data for usage vacuum validation
- Tank01 API - Season team stats for offensive classification

---

## Jan 19, 2026: The "Twin Engine" Upgrade

We have established two distinct data engines to power the "Super Signal" (Actual vs Expected).

### Engine A: The "Visible Ghost" (Legacy/Stable)
**Purpose:** Scrapes proprietary NBA.com data (Lineups, Defense, Speed) that has no public API.
- Upgraded Script: `scripts/sync_wowy_hybrid.py`
- The Fix: Now intelligently falls back to Visible Browser Mode when running on Self-Hosted runners (`IS_SELF_HOSTED=true`). This bypasses the NBA's WAF which blocks Headless browsers.
- Stealth Tech: `scripts/sync_browser_backfill.py` uses stealth injections and mouse randomization to mimic human behavior.

### Engine B: PBP Stats (New/Clean)
**Purpose:** Fetches "Shot Quality" and "Expected eFG%" via API.
- New Script: `scripts/sync_pbp_shot_quality.py`
- New Client: `utils/pbp_stats_client.py` (upgraded with browser headers).
- New Data: `player_shot_quality` table in `ludi.db`.
- Status: ACTIVE. 499 players synced for 2025-26.

### The "Super Signal" Methodology
We blend these two engines to find the Ludi Regression Index:
- Physical Layer (NBA API): Volume & Opportunity (Drives, Touches).
- Quality Layer (PBP Stats): Efficiency Context (Shot Quality, Expected eFG%).
- The Signal: If `Shot Quality` > `Actual Results` = DIAMOND PLAY (Buy Low).

---

## Jan 20, 2026: The "Tank01 ID" Integrity Update

**Strategic Objective:** Prevent database pollution from Tank01 API's sudden ID format change (Composite IDs vs Legacy NBA IDs).

### The "Database Guardrail" Defense
Instead of rewriting 8+ modules, we implemented a firewall at the database layer.

1. Canonical ID System: `player_canonical_ids` table maps 505 active players to their immutable NBA IDs.
2. Auto-Healing Ingestion: `database.py` now silently intercepts and resolves dirty Tank01 IDs (e.g., `28398804489`) into clean NBA IDs (`1629029`) before they ever touch the `players` table.
3. Result: Modules H (Historian), D (Yak), and F (Alchemist) are automatically protected without code changes.

Status: COMPLETE & VERIFIED (All tests passed)

---

## Week 6: Referee Sync Orchestration Fix (Jan 20, 2026) - COMPLETE

**Problem Identified:** Daily Referee Sync (`scripts/sync_daily_referees.py`) consistently reported "0 games found" because the `games` table wasn't populated with current day's data before referee scraping began.

**Root Cause:** The workflow at 9:30 AM ET depended on games table being pre-populated, but no automation existed to ensure this.

**Solution Implemented: Smart Auto-Population System**

### Phase 1: Module G Enhancement
Modified `module_g.py` - Added auto-population methods to `LudiRefEngine` class

### Phase 2: Integration Points Updated
Enhanced `scripts/sync_daily_referees.py` - Added same auto-population logic to `DailyRefereeSync` class
- Auto-population trigger: Runs before any referee operations
- API integration: Uses existing config.ODDS_API_KEY
- Team mapping: Reuses TEAM_MAP from populate_todays_games.py
- Database upserts: `ON CONFLICT(game_id) DO UPDATE` for idempotency

### Benefits Achieved
- Zero new workflows needed - Enhanced existing orchestration
- Self-healing - Auto-populates whenever games are missing
- Backward compatible - All existing Module G integrations inherit the fix
- Production ready - <2 seconds execution time, comprehensive error handling
- Database integrity - Uses proper upserts and transaction handling

---

## Jan 18, 2026: Major System Upgrade (WOWY + Smart Tax)

### Database Revival (Morning Session)
**Problem:** `team_lineups` table had empty `possessions` column after 60-day backfill
**Solution:** Calculated possessions from pace x minutes / 48 formula

**Verification Results:**
| Metric | Value | Status |
|--------|-------|--------|
| Total Lineup Records | 10,669 | OK |
| Records with Possessions | 9,314 | 87.3% |
| Teams Covered | 30/30 | 100% |
| Date Range | Nov 19 - Jan 17 | 60 days |
| Duplicate Check | 0 | Clean |
| Game Days | 45 | OK |
| High-Quality Lineups (150+ poss) | 27 | OK |

### WOWY Calculator Integration (NEW - Phase 6)
**Strategic Achievement:** Built proprietary WOWY (With Or Without You) lineup analysis system

**New Utility Created: `utils/wowy_calculator.py` (450 lines)**
- Confidence Tiers: HIGH (500+ poss), MEDIUM (350+ poss), LOW (150+ poss), INSUFFICIENT (<150)
- Key Methods:
  - `get_player_impact()` - WITH vs WITHOUT efficiency comparison
  - `find_beneficiaries()` - Usage vacuum analysis for OUT players
  - `get_team_best_lineups()` - Top lineups by NetRtg
  - `get_team_worst_lineups()` - Worst lineups by NetRtg
- Confidence Weighting: HIGH=1.0, MEDIUM=0.7, LOW=0.4, INSUFFICIENT=0.0

### Smart Blowout Tax (V4.7) - Replaced Double Taxation
**Problem:** Old system taxed twice (Module E -6% flat + Module F sliding scale)
**Solution:** Consolidated to context-aware per-player calculation in Module F only

**New Utility Created: `utils/blowout_tax.py` (200 lines)**
- Tax Logic:
  - Favorites (Starters): Tax starts at 10pt spread (-10% at 15pt, -20% at 20pt, -30% at 25pt)
  - Favorites (Bench): BOOST in blowouts (+5% at 15pt, +10% at 20pt - garbage time)
  - Underdogs: Neutral (no tax - keep fighting)
- Floor/Cap: 70% minimum (30% max tax), 120% maximum (20% max boost)

---

## Week 5: Ghost Protocol (Historical Backfill Engine) - COMPLETE

**Status:** Phases 1 & 2 Verified (Jan 16, 2026)
**Priority:** HIGH
**Final Yield:** ~14,700 records (Physics: 9.4k | Brain: 5.3k)

---

## Week 4: Module G (Referee Intelligence) Upgrade - COMPLETE

**Date:** January 15, 2026

### Executive Summary
- Refs in Database: 78 (Full Roster) with accurate 2025-26 Season Stats
- Coverage: 100% (Up from 17.6%)
- Impact Types: Pace + Whistle (FTA) + Ejection Risk + Star Bias
- Data Sources: Basketball-Reference (Seeded) + NBAStuffer (Daily Trend) + Box Scores (Star Bias)

### Phase 1: Data Pipeline Expansion - COMPLETE
New Table: `referee_profiles` - Stores baseline stats: `avg_fouls_per_game`, `avg_pace_impact`, `whistle_impact` (calculated from fouls).
New Table: `referee_daily_stats` - Stores rolling trends and "hot whistle" flags.

### Phase 2: Hybrid Learning System - COMPLETE
Script: `scripts/learn_daily_trends.py` - Incremental updating of referee profiles based on nightly results.

### Phase 3: Reporting Suite - COMPLETE
Deliverables:
1. Daily Whistle Watch (`utils/referee_briefing.py`)
2. Weekly Leaderboard (`scripts/generate_weekly_zebra_report.py`)
3. Visual Integration (`utils/render_full_report.py` - Added Referee Footer)

### Phase 4: Advanced Bias Engine - Verified
Challenge: `nba_api` restricted access to historical games.
Solution: Built `scripts/seed_referees.py` using browser-extracted JSON from Basketball-Reference (Active Roster).
Forward Learning: Created `scripts/analyze_star_bias.py` to track "Star Killer" trends daily.
Automation: Created `scripts/ludi_cron_master.sh` to run the 3-step pipeline.

### Phase 5: Day Forward Capture System - COMPLETE (Jan 17, 2026)
Strategic Pivot: Abandoned historical backfill (data unavailable), built proprietary dataset organically

New Scripts:
1. `scripts/sync_daily_referees.py` (319 lines)
2. `scripts/sync_external_intelligence.py` (Playwright)
3. `scripts/generate_weekly_zebra_report.py` (318 lines)

---

## Week 3: Visual Upgrade & Pipeline Integration - COMPLETE

### Jan 15 Afternoon Session (4:00 PM)
- Module G Audit Complete: Confirmed critical gaps in referee data (13/74 refs) and logic (Pace impact only).
- Fixed: `morning_brief.py` visual generation (macOS font paths + int casting).
- Fixed: `launch_parallel_sync.sh` virtual environment path (`.venv`).
- Verified: All systems operational.

---

## Week 2: Data Sync, Automation, Tags - COMPLETE

### Database Sync
- Records: 12k+ logs backfilled.
- Table: `games` confirmed to have `referee_crew` for analysis.

### Tag System
- Archetypes: SLASHER, STRETCH_BIG, etc.
- Scenarios: BENEFICIARY, USAGE_VACUUM.
- Matchups: vs_PAINT_PACK, vs_BLITZ.

### Days 1-2: Logging Framework - Complete
- `utils/bet_logger.py` (650 lines) - BetLogger class with dual storage
- SQLite tables: `bet_recommendations`, `bet_daily_summaries` in ludi.db
- JSON logs: `logs/bets/YYYY-MM-DD.json` format
- Status: Operational & Backfilled.

### Days 3-4: Tag Classification System - Complete (Jan 8, 2026)
- Core Utility: `utils/tag_classifier.py` (492 lines) - Searchable play classification
- 4 Tag Categories: Archetype (6), Scenario (4), Matchup (5+), Market (extensible)
- Module F Integration: v4.6 with tag assignment in bet logging pipeline
- Storage Format: JSON arrays in SQLite

---

## Week 1: Foundation - COMPLETE

### Module Implementation Status
- All 9 modules (A-H + X) production-ready: 73,232 lines of code
- API integrations: The-Odds-API (PAID 20K/mo), Tank01 (PAID 1K/day)
- Utilities: Devigging, monitoring, retry logic all complete
- Database: 10,840 game logs, 505 players, 496 games migrated
- NEW: `test_pipeline.py` - Full end-to-end integration test (456 lines)
- NEW: Telegram notification system - Real-time alerts & daily briefings

### Integration Test Results (Jan 7, 7:00 PM ET)
- test_pipeline.py: PASSED ALL CRITERIA
- Games processed: 3 (CHI-DET, WAS-PHI, TOR-CHA)
- Players simulated: 19 (dynamic roster discovery via database)
- Diamond plays generated: 5 recommendations
- API cost: $0.1125 (75 credits, 25% under budget)
- Current usage: 19,729/20,000 credits remaining (98.6%)

### Cost Performance
| Metric | Value | Status |
|--------|-------|--------|
| Per Game (Test) | $0.0375 | 62% under target |
| Daily (3 games avg) | $0.1125 | Well within budget |
| Monthly (30 days) | $3.38 | 89% headroom |
| Paid Tier Budget | $30.00/month | Active |

---

## Infrastructure & Security (Self-Hosted)

*Architecture upgraded Jan 19, 2026 for bare-metal security.*

### 1. The Containment Layer (Docker)
- Strategy: All automated workflows run inside the `ludi-core` Docker container.
- Image: `ludi-core:latest` (Local build, based on `python:3.11-slim`).
- Capabilities: Pre-installed Playwright (Chromium/FFMPEG), SQLite3, Git.
- Persistence: Workflows bind-mount the project root to `/app`.
- Reasoning: Isolates execution from the host macOS system. If a script goes rogue, it destroys a disposable container, not the host.

### 2. The Keymaster Protocol (Secrets)
- Strategy: Zero-trust secret handling in production.
- Implementation: `config.py` detects `IS_SELF_HOSTED` env var.
- Behavior:
  - Local Dev: Loads `.env` file (legacy behavior).
  - Docker/CI: IGNORES `.env` file. Secrets must be injected by the runner.
- Benefit: Prevents secret leakage via volume mounts or log artifacts.

### 3. Supply Chain Defense
- Tool: `pip-audit`.
- Integration: Runs during `docker build`.
- Policy: The build FAILS if any `requirements.txt` package has known vulnerabilities.

### 4. Database Fortification
- Mode: WAL (Write-Ahead Logging) enabled (`PRAGMA journal_mode=WAL`).
- Backups: `backup_local_data.sh` upgraded to use SQLite Hot Backup API (`.backup`).
- Retention: Automated 7-day rotation of backup files.

---

## Telegram Schedule (Final)

| Time (EST) | Type | Content |
|------------|------|---------|
| 5:00 AM | Work Notes | Bet Settlement + System Status |
| 6:00 AM | Bet Summary | Profit/Loss Table (Telegram) |
| 10:00 AM | Game Notes | Visual cards (post-ref assignments) |
| 6:00 PM | Game Notes | Evening lock visual |
| 8:00 PM | Work Notes | PM Bot nightly debrief |

---

## Phase 8 AI-Enhanced Pipeline — Sprint Archive (Feb 20–24, 2026)

### Production Pipeline / WOWY / Settlement Fix ✅ COMPLETE (Feb 21, 2026)

Pipeline had been failing 5 consecutive days (Feb 17-21). WOWY sync timing out every run. Duplicate settlement notifications.

**P0 — Daily Production Pipeline (5-day outage):**

- `daily_simulation_pipeline.yml`: Added `continue-on-error: true` to "Verify data freshness" and "Run System Health Monitor" steps. Diagnostic steps no longer kill a pipeline that successfully generated bets.
- `monitor_system_health.py`: Tightened critical alert filter — only `'Table is empty'` or `'Database connection failed'` are critical. Odds API quota exhaustion no longer triggers `exit(1)`.

**P1 — WOWY Sync Timeouts:**

- `sync_wowy_hybrid.py`: Removed `@retry_with_backoff` decorator (double retry: 3 decorator × 3 outer loop = 9 attempts × 180s). Reduced `REQUEST_TIMEOUT` 180→60s. Fixed Ghost Protocol threshold: `api_failures >= 2` → `>= 1` (was unreachable for `--days 1`).
- `wowy_sync.yml`: Increased workflow timeout 30→45 min (Ghost Protocol needs 10-15 min after API fails).
- **Data source investigation:** BDL has no WOWY capability. PBP Stats is viable future Tier 3 (7 endpoints already in `pbp_stats_client.py`, not wired to `team_lineups`). popcornmachine.net not useful.

**P2 — Settlement Notifications:**

- `settle_bets.py`: Removed per-date Telegram sends (5 AM). 6 AM aggregate summary (`send_settlement_summary.py`) is the single notification now.

---

### Feb 20 Post-All-Star Break Audit ✅ COMPLETE (Feb 20, 2026)

First game day back exposed 9 critical/high issues. Full recovery + hardening completed before 6 PM pipeline.

**Bugs Fixed:**
- Module H `ON CONFLICT` mismatch → 8 days of silent game log insert failures (all game logs now syncing)
- `anthropic` missing from `requirements.txt` → all Phase 8 AI features were silently disabled in CI since launch
- Health monitor false failures → exited 1 on stale data, pipeline marked failed daily despite generating 213+ bets
- BDL milestone market type → corrupt odds (-2, -4, -9) produced 50× payout multiplier (+269u phantom P&L)
- `generate_report()` 3-tuple callers → 4 files, 6 callers fixed
- `player_game_logs` settle → 1,947 PUSH bets settled to 998W/863L/81V after backfill
- Referee sync → NBA.com consent popup blocked Playwright; skips date toggle for today's slate

**Hardening Added:**
- BDL vendor quality filter (DK/FD/Caesars/BetRivers/BetMGM only) + modal line ≥2 vendor requirement
- `scripts/backfill_games_bdl.py` — reusable when Odds API is down
- P&L sanity gate in settlement summary (±50u triggers Slack alert)
- `team_lineups.created_at` backfilled (17,368 rows had NULL)
- 4 missing packages added to `requirements.txt` (anthropic, PyYAML, schedule, tabulate)
- BDL API best-practices docs — comprehensive endpoint reference + audit lessons

---

### Ask Ludi Architecture Research ✅ COMPLETE (Feb 20, 2026)

Researched Telegram + Claude integration patterns across 5 sources (Medium articles, GitHub repos, docs). Full notes in `docs/FUTURE_DATA_SOURCES.md` §6 and `memory/MEMORY.md`.

**Implementation Plan (3 files, ready to build):**
- `bots/ask_ludi.py` — Entry point, long-polling loop, `/start` + free-text handler
- `bots/ask_ludi_db.py` — Read-only SQLite queries, 8 intent handlers (injuries/edges/trends/standings/schedule/recap/free/fallback)
- `bots/ask_ludi_handlers.py` — Intent → Haiku classification (JSON output) → DB fetch → Sonnet narrative → reply
- `scripts/launchd/com.ludi.askludi.plist` — macOS launchd keepalive (runs on self-hosted Mac runner)

**Key Design Decisions:**
- `python-telegram-bot` v21+ (async, long polling — no webhook/public IP needed)
- Haiku for intent ($0.0001/call, <200ms) → Sonnet for analysis (max_tokens=600)
- `sqlite3.connect("file:ludi.db?mode=ro", uri=True)` — read-only, WAL-safe, can't corrupt pipeline
- `CLAUDE_CODE_OAUTH_TOKEN` correctly used in `claude-code-action@v1` only (not SDK calls)

---

### Injury Intelligence Hardening ✅ COMPLETE (Feb 20, 2026)

Second sprint of Feb 20 — closed remaining injury pipeline gaps and built intraday refresh infrastructure.

**New Capabilities:**
- **RealGM RSS** added as 2nd corroboration source alongside RotoWire. `_nuance_check()` compares both; when they agree → confidence bumped to 0.95 (`[2-source confirmed]`)
- **AI blurb prompt** hardened: centralized `INJURY_BLURB_SYSTEM` + `INJURY_BLURB_PARSE_PROMPT` with 5 few-shot examples, `tonight_available` field (true/false/uncertain), `blurb_is_stale` flag, `temperature=0.0` for deterministic classification
- **`injury_refresh.yml`**: new GitHub Actions workflow — 4 daytime runs (every 2 hr, 11 AM–5 PM EST) + 15 evening runs (every 20 min, 6–10:40 PM EST). Staleness guard in `sync_injuries.py` exits early if DB is already fresh — protects Tank01/BDL quota
- **Evening slate lock**: `--force` injury sync step before `morning_brief --mode evening` captures 4–6 PM late scratches in DB before 6 PM cards generate
- **`--force` flag** on `sync_injuries.py` for on-demand overrides (web app, bot, evening lock)
- **Downstream ready**: Telegram bot (8.13) and Ludi Lens web app query `player_injuries` directly — always ≤20 min stale during game time

---

### Morning Brief Pipeline Hardening + BetIQ Research ✅ COMPLETE (Feb 20, 2026)

Third sprint of Feb 20 — hardened the morning/evening brief pipeline and completed competitive analysis.

**Pipeline Fixes (both morning + evening modes):**
- **Native Telegram text:** Removed `send_photo` + image card pipeline from `morning_brief.py`. Both morning and evening modes now send chunked native text (4000-char splits). No more PIL/PNG dependencies in briefing flow.
- **All-game processing:** Removed January hardcoded watchlist (`['PHX','MIA','CHI',...]`). Set `target_teams=None` — all games on the slate are now processed and scored by the tier-weight algorithm. Tonight's IND@WAS was previously invisible.
- **Spotlight Markdown fallback:** Claude spotlight outputs truncated to 4000 chars and retried as plain text on 400 Bad Request. Fixes Kyle Anderson-style failures.
- **Injury `skip_resolve` bug:** `sync_to_database()` called twice in `sync_injuries.py main()`. Step 4 RSS call (7 players) was resolving all 34+ BDL/Tank01 injuries because they weren't in the RSS batch. Fixed with `skip_resolve=True` parameter — RSS call now only adds, never sweeps.
- **`.gitignore` hardening:** Added `archives/data/`, `logs/health/`, `*.png` to gitignore.

**Competitive Research:**
- BetIQ/TeamRankings 3-session sprint — 6 cross-game ATS/O-U patterns confirmed across CLE@CHA, DAL@MIN, IND@WAS. 20+ power rating dimensions mapped. Tier 1 features all buildable from existing `ludi.db` (no new APIs). Doc: `docs/research/BETIQ_TEAMRANKINGS_RESEARCH.md`

---

### ESPN Research, Suspension Intelligence & Pipeline Hardening ✅ COMPLETE (Feb 21, 2026)

**ESPN API Research (3-session sprint):**
- Confirmed ESPN has no official NBA injury API — PDF-only (timestamped, no predictable URL). No direct endpoint.
- ESPN public API (`site.api.espn.com`, `sports.core.api.espn.com`) verified live: injuries per game (shortComment/longComment/returnDate), DraftKings game lines (spread/O/U/ML open+close+live), scoreboard, news. **No player props** in any ESPN endpoint.
- DraftKings pickcenter: game-level only (spread, O/U, moneyline with juice). No H1/H2 or Q1/Q4.
- ESPN `longComment` names beneficiaries — potential future replacement for some Perplexity calls (free).
- Full ESPN client plan documented at `~/.claude/plans/`. Integration (Phase 8.21) covers: ESPN client, espn_id crosswalk, game injuries enrichment, Tier 3 game lines fallback, longComment corpus for prompt training.

**Phase 8.16 — Suspension Intelligence via ESPN (implemented same session):**
- `scripts/sync_suspensions_espn.py`: 30-team scan, ESPN `INJURY_STATUS_SUSPENSION` type, returnDate, auto-resolve on expiry
- First run found 5 active suspensions previously invisible to pipeline: Paul George (PHI, 32d, anti-drug), Isaiah Stewart (DET, 10d), Miles Bridges + Moussa Diabate (CHA, 3d), Rudy Gobert (MIN, 3d — same-day flagrant foul #6 catch)
- Wired into `data_sync.yml` after injury sync step. $0 cost.

---

### BDL V2 Full Integration + SportsDataIO Enrichment ✅ COMPLETE (Feb 22, 2026)

**Goal:** Eliminate Ghost Protocol advanced scraping dependency, fill critical `player_game_logs` gaps (started, fantasy pts, home/away, doubles), and replace NBA.com synergy scraping with BDL playtype API. All on existing GOAT tier ($39.99/mo, no new cost).

**4 sprints shipped (commits 5d8576b + 6ccf4b6):**

- **Sprint A — SportsDataIO enrichment** (`sync_sportsdata_enrichment.py`): Populates `started`, `fantasy_pts_dk`, `fantasy_pts_fd`, `home_or_away`, `double_doubles`, `triple_doubles` in `player_game_logs`. 3-day rolling default (3 API calls/day, 100/day budget). Backfill: 13,706 rows across 90 prior-season dates.
- **Sprint B — BDL V2 advanced stats** (`sync_bdl_advanced_stats.py`): Daily advanced ratings (off/def/net rating, pace, PIE, usage, true shooting) + hustle (deflections, box outs, screen assists, charges drawn) + tracking (speed, distance, touches, passes). **Replaces Ghost Protocol advanced scraping.** Backfill: 82,785 advanced + 16,716 hustle + 12,804 tracking rows across 115 dates.
- **Sprint C — BDL plus_minus fill** (`sync_bdl_plus_minus.py`): Tier 2 fill — COALESCE, never overwrites Tank01/SportsDataIO. Coverage: 58.9% → **99.2%** (18,260/18,405 rows).
- **Sprint D — BDL season averages** (`sync_bdl_season_averages.py`): Weekly sync of all 18 category/subtype combos (general/tracking/hustle/shotdashboard/playtype) to `player_season_averages_bdl`. **Replaces Ghost Protocol synergy (NBA.com) scraping.** 7,958 rows, 100% canonical_id coverage. Standings to `team_standings_bdl`.

**Ghost Protocol demotion:** `--skip-advanced` flag added; synergy NBA.com step removed from `ghost_protocol_sync.yml`. Ghost Protocol now handles only: drives/C&S/pull-up per game, closest defender, clutch stats.

**Canonical ID hardening:** `_resolve_canonical_ids()` baked into season averages sync. 5 missing players added to `player_canonical_ids` (Cameron Payne/1626166, Trevor Keels/1631211, Alondes Williams/1631214, Patrick Baldwin Jr./1631116, Dillon Jones/1641794) — verified via `nba_api.stats.static.players`.

**Note:** `SPORTSDATA_API_KEY` must be added as a GitHub Actions secret for the enrichment step to run in CI.

---

### Evening Lock Bug Fixes & Injury Intelligence Tightening ✅ COMPLETE (Feb 21, 2026)

**Root cause:** Phase 8.18 introduced `UnboundLocalError` in `module_e.py` (odds/total/spread used before assignment in section 3.6). With `USE_TEAM_TOTALS_MODIFIER=True`, every game silently failed, producing zero Telegram output. Pipeline showed "success" (exit 0) so no alerts fired.

**9 fixes across 7 files:**
- `module_e.py`: Move odds/total/spread extraction before section 3.6 (root cause of silent outage)
- `morning_brief.py`: `sys.exit(1)` when no bets processed → workflow now fails loudly + triggers Claude Ops Hub
- `morning_brief.py`: Game notes markdown fallback (Markdown→plain text on 400, matching spotlight pattern)
- `morning_brief.py`: `snapshot_time >= datetime('now', '-14 days')` staleness guard on all 3 `player_injuries` queries — eliminates ghost records from mid-season DB init appearing as currently OUT
- `main.py`: Tier 2 NOT EXISTS guard — player with resolved injury + new same-day OUT was classified as WELCOME_BACK instead of OUT (Embiid pattern). Beneficiary vacuum now fires correctly.
- `morning_brief.py`: Skip games tipped >45 min ago (ORL@PHX 5pm processed at 6pm evening lock)
- `utils/perplexity_client.py`: Empty response logs HTTP status code; `_get_recency_filter()` switches "hour"/"day"/"week" based on hours_to_game (Ludi-Lite pattern — tighter search pre-tip, cheaper on morning runs)
- `utils/time_utils.py`: `get_time_context()` + `format_time_context_note()` — EARLY_LOOK/AFTERNOON/PRE_GAME/LOCK_TIME modes based on EST hour. Foundation for bot + web app confidence display.
- `utils/claude_prompts.py`: `{time_context_note}` row in GAME_NOTES_TEMPLATE — Claude calibrates certainty to data confidence at call time
- `CLAUDE.md`: 2025-26 season reminder added to Critical Data Rules — prevents AI roster drift

**Industry research:** NBA official injury report now publishes every 15 min (2025-26 rule). Our RotoWire + RealGM dual-source corroboration already matches industry standard. Perplexity hours_to_game filter borrowed from Ludi-Lite for cost-efficient dynamic recency.

---

### Data Sync Pipeline Fix + PBP Stats Split + Module H BDL Fallback ✅ COMPLETE (Feb 23, 2026)

Daily Data Sync was cancelled after 60 minutes — 3 PBP Stats scripts consumed 55 of the 60-min job budget, causing 22 downstream steps to be skipped entirely. Ops Hub didn't fire because it only triggered on `failure`, not `cancelled`.

**Fix 1 — PBP Stats Split (`pbp_stats_sync.yml`):**
- Moved `sync_pbp_wowy.py`, `sync_four_factor_wowy.py`, `sync_team_leverage_profiles.py` to own workflow (Mon/Wed/Fri 5 AM EST, 90-min budget). Season-aggregate data doesn't need daily refresh. Cuts PBP Stats API calls 57% (7,140/week → 3,060/week).

**Fix 2 — Ops Hub `cancelled` trigger:**
- `claude-ops-hub.yml` now fires on both `failure` AND `cancelled` conclusions. Also monitors the new `PBP Stats WOWY Sync` workflow.

**Fix 3 — Python-level hardening:**
- Wall-clock guards (`MAX_RUNTIME_SECONDS`) in all 3 PBP Stats scripts — exit gracefully with checkpoint before step timeout kills the process.
- `utils/pbp_stats_client.py`: HTTP timeouts lowered (120s→60s primary, 180s→90s fallback). User-Agent updated to Chrome/131.

**Fix 4 — Module H BDL fallback:**
- `module_h_historian.py`: When Tank01 returns 0 games for a date, automatically falls back to BDL `get_box_scores()`. Uses canonical ID resolution and COALESCE pattern. Prevents silent 0-row ingestion (Feb 22 bug: 11 games/382 players existed but Module H ingested nothing).

**9 files changed:** `pbp_stats_sync.yml` (new), `data_sync.yml`, `claude-ops-hub.yml`, 3 PBP Stats scripts, `pbp_stats_client.py`, `module_h_historian.py`, `sync_bdl_plus_minus.py`.

---

### Injury Pipeline Hardening + ESPN Injury Source + Referee Timing Fix ✅ COMPLETE (Feb 23, 2026)

Tonight's evening lock revealed 3 systemic problems: (1) Jaren Jackson Jr. (UTA, injured) shown as healthy — no entry in `player_injuries`, BDL/Tank01 not yet reporting; (2) Nurkic (UTA, OUT) injury in DB from RSS but `team_abbreviation` blank → query excluded him silently; (3) referee sync runs at 9:30 AM but morning brief at 9:00 AM — race condition every day.

**Root cause confirmed via live DB queries and workflow logs — no assumptions.**

**Fix 1 — `player_canonical_ids` as name resolution source:**
- `sync_injuries.py`: Added `_normalize_for_canonical()` (Unicode NFD accent strip + suffix removal: Jr./Sr./III) and `_get_canonical_lookup_from_db()` (normalized_name → full_name + team).
- Team resolution in `sync_to_database()` now routes through `player_canonical_ids.normalized_name` instead of `players.name` with `.lower()` only.
- Canonical `full_name` now stored in `player_injuries.player_name` (e.g. `Jusuf Nurkić` not `Jusuf Nurkic`) — ensures consistent downstream name matching.

**Fix 2 — Dedup guard in `sync_injuries.py`:**
- INSERT now skips if identical `(player_name, status, DATE(snapshot_time))` already exists today. Eliminates Naji Marshall 7-duplicate-row pattern.

**Fix 3 — Resolve scope scoped to non-ESPN sources:**
- BDL/Tank01 resolve step now filters `AND source NOT IN ('ESPN', 'espn_suspension')` — prevents BDL from wiping ESPN-sourced injuries when BDL API hasn't caught up yet. ESPN resolves its own.

**Fix 4 — ESPN as faster injury source (`scripts/sync_injuries_espn.py` — partial Phase 8.21):**
- New script following `sync_suspensions_espn.py` pattern. 30-team scan via `sports.core.api.espn.com` (free, no auth, 15-30 min lag vs BDL/Tank01 2-6 hr lag).
- Maps ESPN `displayName` → `player_canonical_ids.normalized_name` for canonical name + team resolution.
- Skips suspensions (type_id=17) — those belong to `sync_suspensions_espn.py`.
- Source-scoped resolve: only resolves its own `source='ESPN'` entries.
- Wired into: `daily_briefing.yml` (before morning briefing), `evening_slate_lock.yml` (before force injury sync), `injury_refresh.yml` (first step every 20-min cycle).

**Fix 5 — Morning brief injury query hardened:**
- UNION clause added: catches injuries where `team_abbreviation` is blank via `player_canonical_ids` join (the Nurkic bug).
- `AND (days_out IS NULL OR days_out < 75)` filter: Steven Adams (220d) and season-ending outs no longer consume Claude's 600-char injury context budget.
- Status conflict dedup: when ESPN and BDL/Tank01 report different status for same player, highest-severity wins (OUT > DOUBTFUL > GTD). Prevents Claude seeing same player listed twice.
- `if not player_name: continue` guard in spotlight to prevent None names flowing through.

**Fix 6 — Referee timing + popup:**
- `daily_briefing.yml` moved from 9:00 AM → 11:00 AM EST. Morning brief now runs after referee_sync (9:30 AM) and simulation pipeline (10:00 AM). Refs always in DB when brief generates.
- `module_g.build_ref_database()`: DB-first check added. If `games.referee_crew` populated for today → load from DB, skip Playwright. Eliminates 3× redundant browser scrapes per briefing.
- `utils/browser_utils.py` + `browser_utils_async.py`: Consent button selectors (`has-text("Accept/Agree/I Accept")`) added before OneTrust block. `setup_page()` helper added for JS dialog auto-dismiss.
- `scripts/sync_daily_referees.py`: Removed redundant consent block (now handled by `close_popups()`).

**Phase 8.21 status update:** ESPN injury pipeline (this sprint) complete. Remaining Phase 8.21 items deferred: ESPN client utility, athlete ID crosswalk, game lines Tier 3 fallback, longComment corpus.

**11 files changed:** `sync_injuries.py`, `sync_injuries_espn.py` (new), `morning_brief.py`, `module_g.py`, `utils/browser_utils.py`, `utils/browser_utils_async.py`, `scripts/sync_daily_referees.py`, `daily_briefing.yml`, `evening_slate_lock.yml`, `injury_refresh.yml`, `ROADMAP.md`.

---

### Canonical Table Hardening + ESPN Integration Foundation ✅ COMPLETE (Feb 24, 2026)

- `player_canonical_ids` CREATE TABLE restored to `database.py` (was orphaned — comment acknowledged it but code didn't create it). Migration guard added for `espn_id` column via `ALTER TABLE ... ADD COLUMN` in try/except.
- `canonical_teams` table (30 rows) added: `standard_abbr` (PK), `full_name`, `bdl_abbr`, `tank01_abbr`, `espn_id`. Single source of truth for all BDL/Tank01/ESPN team ID mappings.
- `normalize_bdl_abbr()` centralized in `utils/mappings.py` — replaces 6 copy-pasted dicts. Both directions idempotent: `normalize_bdl_abbr('GS')='GSW'`, `normalize_bdl_abbr('GSW')='GSW'`.
- `scripts/build_espn_crosswalk.py` added: scans ESPN `athletes` endpoint per team, normalizes `displayName` → `player_canonical_ids.normalized_name`, writes `espn_id`. Wired into `weekly_validation.yml`.
- ESPN team IDs loaded from DB: `sync_suspensions_espn.py` + `sync_injuries_espn.py` call `_load_espn_team_ids(conn)` → `canonical_teams`; hardcoded fallback kept for safety.

### Claude Name Resolution Pipeline ✅ COMPLETE (Feb 24, 2026)

- `resolve_canonical_name(conn, name)` added to `utils/player_id_resolver.py`. NFKD normalize → look up `player_canonical_ids.normalized_name` → return `full_name`. Graceful fallback (returns original on any error).
- Wired into 4 Claude injection points: `curate_plays._fetch_player_injury()` (Haiku sanity gate was returning "No injury on record" for OUT accented players), `morning_brief.py` (hit rate query + spotlight name), `trend_engine.get_matchup_analysis()` (covers all 5 matchup helpers), `classify_archetypes.py` (dual-form lookup for Jokić/Nurkić/Dončić).
- `classify_archetypes.py`: `_strip_accents()` helper added. `get_player_synergy()` + `get_player_season_advanced()` try exact match first, then accent-stripped fallback. Prevents silent GENERALIST downgrades.
- `trend_engine._resolve_player_id()` tier 4 added: canonical fallback after the 3 existing tiers.
