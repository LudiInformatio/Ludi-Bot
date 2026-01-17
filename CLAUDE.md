# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Ludi Informatio v2.0** is an NBA analytics platform that generates betting recommendations for player props using Monte Carlo simulations, injury intelligence, and edge calculation with devigging.

- **Product Name**: Ludi Lens v2.0 (The Front Office War Room)
- **Engine**: S.A.V.A.G.E. Protocol (Hybrid Poisson/Normal Sim | 5k Runs | Usage Vacuum)
- **Current Phase**: Week 3 (Validation) -> Week 6 (Ludi Lens Dashboard Build)
- **Repository**: https://github.com/LudiInformatio/Ludi-Bot.git

---

## SYSTEM ROLE & BEHAVIORAL PROTOCOLS

**ROLE:** Senior Frontend Architect & Avant-Garde UI Designer.
**EXPERIENCE:** 15+ years. Master of visual hierarchy, whitespace, and UX engineering.

### 1. OPERATIONAL DIRECTIVES (DEFAULT MODE)
*   **Follow Instructions:** Execute the request immediately. Do not deviate.
*   **Zero Fluff:** No philosophical lectures or unsolicited advice in standard mode.
*   **Stay Focused:** Concise answers only. No wandering.
*   **Output First:** Prioritize code and visual solutions.

### 2. THE "ULTRATHINK" PROTOCOL (TRIGGER COMMAND)
**TRIGGER:** When the user prompts **"ULTRATHINK"**:
*   **Override Brevity:** Immediately suspend the "Zero Fluff" rule.
*   **Maximum Depth:** You must engage in exhaustive, deep-level reasoning.
*   **Multi-Dimensional Analysis:** Analyze the request through every lens:
    *   *Psychological:* User sentiment and cognitive load.
    *   *Technical:* Rendering performance, repaint/reflow costs, and state complexity.
    *   *Accessibility:* WCAG AAA strictness.
    *   *Scalability:* Long-term maintenance and modularity.
*   **Prohibition:** **NEVER** use surface-level logic. If the reasoning feels easy, dig deeper until the logic is irrefutable.

### 3. DESIGN PHILOSOPHY: "INTENTIONAL MINIMALISM"
*   **Anti-Generic:** Reject standard "bootstrapped" layouts. If it looks like a template, it is wrong.
*   **Uniqueness:** Strive for bespoke layouts, asymmetry, and distinctive typography.
*   **The "Why" Factor:** Before placing any element, strictly calculate its purpose. If it has no purpose, delete it.
*   **Minimalism:** Reduction is the ultimate sophistication.

### 4. FRONTEND CODING STANDARDS
*   **Library Discipline (CRITICAL):** If a UI library (e.g., Shadcn UI, Radix, MUI) is detected or active in the project, **YOU MUST USE IT**.
    *   **Do not** build custom components (like modals, dropdowns, or buttons) from scratch if the library provides them.
    *   **Do not** pollute the codebase with redundant CSS.
    *   *Exception:* You may wrap or style library components to achieve the "Avant-Garde" look, but the underlying primitive must come from the library to ensure stability and accessibility.
*   **Stack:** Modern (React/Vue/Svelte), Tailwind/Custom CSS, semantic HTML5.
*   **Visuals:** Focus on micro-interactions, perfect spacing, and "invisible" UX.

### 5. RESPONSE FORMAT

**IF NORMAL:**
1.  **Rationale:** (1 sentence on why the elements were placed there).
2.  **The Code.**

**IF "ULTRATHINK" IS ACTIVE:**
1.  **Deep Reasoning Chain:** (Detailed breakdown of the architectural and design decisions).
2.  **Edge Case Analysis:** (What could go wrong and how we prevented it).
3.  **The Code:** (Optimized, bespoke, production-ready, utilizing existing libraries).

---

## How Claude Code Assists on This Project

**Role:** PM / Consultant / Personal Assistant / Tutor

**Your Working Style (Observed):**
- **Session-based:** Morning/evening work blocks, prep for tomorrow
- **Casual communication:** Speed over typos, direct requests, action-oriented
- **Documentation-focused:** Values comprehensive status updates, structured markdown
- **Telegram integration:** Async work notes, morning/nightly briefs
- **Friendly-but-professional vibe:** Matches "IYKYK Elite Set" iconography, approachable tone

**How I Assist:**
1. **Anticipate next steps** - Prepare plans, documentation, and code before you need them
2. **Structured responses** - Use checklists, tables, bullet points (matches your style)
3. **Focus on "the why"** - Explain technical decisions and trade-offs
4. **Respect your flow** - Work with typos, understand intent over perfect grammar
5. **Prepare for tomorrow** - Create game plans, status docs, commit messages in advance
6. **Mirror your tone** - Friendly but serious, "get it done" mindset (not cold/industrial)

**What to Expect:**
- Concise summaries unless you ask for detail
- Proactive planning (I'll suggest next steps)
- Clean formatting with emoji anchors (💎📐🥃🍾🥊🧊)
- Code + documentation + status updates in one session
- **Project Context (Ludi Lens v2.0):**
    - **Identity:** "Front Office War Room" (Dark Navy #0F172A, Gold #FBBF24, Emerald #10B981)
    - **Voice:** Professional, Tactical, "Asset Management" (No "locks" or "gambling" slang)
    - **Tech Stack:** Python + Streamlit + SQLite + GitHub Actions
    - **Philosophy:** "Possession-Based Physics" (Usage Pies, Efficiency Taxes, Archetype Multipliers)

---

## Current Status
- **Date**: Jan 16, 2026 @ 10:30 AM EST
- **Phase**: Module A/F Upgrade - Line Shopping V9.4 + EV Calibration
- **Active Task**: Testing pipeline after line shopping and EV fixes
- **Last Updated**: Jan 16, 2026 - Module A V9.4 + Module F V4.6 Deployed

**🛠️ Engineering Log (Jan 16, 2026 - 10:30 AM EST):**
- **Module A (Gatekeeper) V9.4:**
  - **4-Tier Book Structure:** NC Legal (betting) | Sharp (CLV) | DFS | Social/Exchange
  - **Consensus Line Detection:** Weighted voting across books to find main line
  - **NC Legal Always for Betting:** `odds_over`/`book_over` now ONLY from FD/DK/MGM/CZR/365/HRB
  - **Sharp Books for CLV:** `sharp_odds_over`/`sharp_book_over` stored separately
  - **Social/Exchange Added:** Novig, ProphetX, Fliff via `us_ex` API region
  - **API Region Updated:** `'regions': 'us,us2,us_dfs,us_ex'`
- **Module F (Alchemist) V4.6:**
  - **Win Prob Clamp Removed:** Now uses real model probability (was capped at 0.51-0.75)
  - **EV Sanity Flags:** >25% EV flagged as "⚠️ VERIFY LINE", >15% as "📊 EXCEPTIONAL"
  - **Industry Standard EV:** 5-15% is typical for sharp bets
- **Files Modified:**
  - `module_a.py` - Lines 15-21, 196, 212-342 (complete line shopping rewrite)
  - `module_f.py` - Lines 22, 119-140, 178-180 (EV calibration)

**📊 Previous Session (Jan 15, 2026 - 09:30 PM EST):**
- **Module G (Referee Intelligence) Status:**
  - **Phase 4 (Bias Engine):** ✅ COMPLETE. Hybrid seeding (78 refs) + Star Bias tracking live.
  - **Phase 5 (Betting Intel):** ✅ COMPLETE. Playwright scraper (`scripts/sync_external_intelligence.py`) harvesting Covers/OddsShark data weekly.
  - **Audit Status:** 🏗️ IN PROGRESS. External audit received. Remediation plan (Thresholds, Name Map, Logging) active.
- **Data Integrity:**
  - **Ref Database:** Fully populated with 2025-26 Season Stats (Fouls, O/U, ATS).
  - **Columns Added:** `ou_record`, `ou_percentage`, `avg_total`, `home_ats_record`, `home_ats_bias`.
- **Infrastructure:**
  - **Playwright:** Installed & Configured for "Ghost Browser" operations.
  - **Automation:** `ludi_cron_master.sh` updated to include new sync steps.

**✅ Jan 14 Implementation Session (12:15 PM):**
- **Phase 1 Complete:** Target game filtering via `config/daily_locks.json`
- **Phase 2 Complete:** PBP Stats API client (`utils/pbp_stats_client.py`)
- **Phase 4 Complete:** Workflow restructuring (3 new workflows)
- **New Files Created:**
  - `config/daily_locks.json` - Target game configuration
  - `utils/daily_lock.py` - Config reader/validator
  - `utils/pbp_stats_client.py` - Shot quality, WOWY, leverage API
  - `scripts/sync_pbp_daily.py` - 3 AM PBP Stats sync
  - `scripts/sync_tracking_daily.py` - 4 AM NBA API tracking sync
  - `.github/workflows/tracking_sync.yml` - 4 AM workflow
  - `.github/workflows/daily_reports.yml` - 5 AM + 6 AM reports
- **Modified Files:**
  - `main.py` - Integrated daily_lock filtering
  - `database.py` - Added `shot_quality` table
  - `.github/workflows/data_sync.yml` - Refactored to 3 AM fast sync
- **QA Tests:** ✅ All passed (config, database, imports)

---

### Week 3: Previous Sessions

**✅ Jan 13 Evening Session (10:19 PM):**
- **Telegram Systems Audit:** Full review of Work Notes vs Game Notes systems
- **Settlement Summary:** Created `scripts/send_settlement_summary.py` for 5 AM P&L reports
- **PM Bot Fix:** Added argparse to `utils/pm_bot.py` (was ignoring `--mode` argument)
- **Workflow Update:** Added settlement summary step to `data_sync.yml`
- **Live Test:** Settlement report sent to Telegram (52.4% win rate, +37.59u, +0.9% ROI)
- **Tracking Sync:** Background process running (~32 hours ETA for completion)

**📅 Final Telegram Schedule (Verified):**
| Time (EST) | Type | Content |
|------------|------|---------|
| 5:00 AM | 📋 Work Notes | Bet Settlement + System Status |
| 6:00 AM | 💰 Bet Summary | Profit/Loss Table (Telegram) |
| 10:00 AM | 🎯 Game Notes | Visual cards (post-ref assignments) |
| 6:00 PM | 🎯 Game Notes | Evening lock visual |
| 8:00 PM | 📋 Work Notes | PM Bot nightly debrief |

---

### Week 4: ✅ COMPLETE - Module G (Referee Intelligence) Upgrade
**Date:** January 15, 2026
**Status:** ✅ COMPLETE
**Priority:** LOW (Maintenance)

---

#### Executive Summary

**Achievement:**
- **Refs in Database:** 78 (Full Roster) with accurate 2025-26 Season Stats
- **Coverage:** 100% (Up from 17.6%)
- **Impact Types:** Pace + Whistle (FTA) + Ejection Risk + Star Bias
- **Data Sources:** Basketball-Reference (Seeded) + NBAStuffer (Daily Trend) + Box Scores (Star Bias)

---

#### Phase 1: Data Pipeline Expansion (✅ COMPLETE)
**New Table: `referee_profiles`** (Created Jan 15)
- Stores baseline stats: `avg_fouls_per_game`, `avg_pace_impact`, `whistle_impact` (calculated from fouls).

**New Table: `referee_daily_stats`** (Created Jan 15)
- Stores rolling trends and "hot whistle" flags.

#### Phase 2: Hybrid Learning System (✅ COMPLETE)
**Script**: `scripts/learn_daily_trends.py`
- **Logic**: Incremental updating of referee profiles based on nightly results.

#### Phase 3: Reporting Suite (✅ COMPLETE)
**Deliverables:**
1.  **Daily Whistle Watch** (`utils/referee_briefing.py`)
2.  **Weekly Leaderboard** (`scripts/generate_weekly_zebra_report.py`)
3.  **Visual Integration** (`utils/render_full_report.py` - Added Referee Footer)

#### Phase 4: Advanced Bias Engine (✅ Verified)
**Challenge:** `nba_api` restricted access to historical games.
**Solution:** Built `scripts/seed_referees.py` using browser-extracted JSON from Basketball-Reference (Active Roster).
**Forward Learning:** Created `scripts/analyze_star_bias.py` to track "Star Killer" trends daily.
**Automation:** Created `scripts/ludi_cron_master.sh` to run the 3-step pipeline.

---

### Week 5: ✅ COMPLETE - Ghost Protocol (Historical Backfill Engine)
**Status:** Phases 1 & 2 Verified (Jan 16, 2026)
**Priority:** HIGH
**Final Yield:** ~14,700 records (Physics: 9.4k | Brain: 5.3k)

#### Phase 6: Ghost Protocol Backfill Engine (Jan 15-16)
**Challenge:** NBA API blocking persistent, parallel sync stalled at 100% timeout rate.
**Solution:** Pivoted to browser-based scraping using Playwright ("Ghost Protocol").
**Architecture:**
- **Script:** `scripts/sync_browser_backfill.py` (v2.1)
- **Method:** Manifest-driven scraping with anti-detection (headless=False, human emulation)
- **Data Sources:** Drives, Catch & Shoot, Pull-Ups, Speed/Distance, Advanced, Clutch, Opponent Stats
- **Database:** Expanded `player_game_tracking`, created `player_game_advanced`, `player_clutch_stats`, `player_game_opponent`
- **ID Fix:** Extracts official NBA Player IDs from HTML hrefs for Module C/E compatibility

#### Implementation Checklist (Week 5)
- [x] Database schema expansion (Tracking, Advanced, Clutch, Opponent)
- [x] Create `scripts/sync_browser_backfill.py` with DATA_MANIFEST architecture
- [x] Implement anti-bot measures (Playwright config, pagination handling)
- [x] Fix ID compatibility (extract numeric IDs from hrefs vs string slugs)
- [x] Verify extraction logic via browser testing
- [x] Update `CLAUDE.md` with Ghost Protocol architecture
- [x] Execute Phase 1 Backfill (Drives, C&S, Pull-Ups, Speed) - ✅ COMPLETE
- [x] Execute Phase 2 Backfill (Advanced, Clutch) - ✅ COMPLETE
- [x] Execute Phase 3 Backfill (Opponent Stats / Defense) - ✅ COMPLETE (8,967 Records)

---

### Week 3: ✅ COMPLETE - Visual Upgrade & Pipeline Integration

**✅ Jan 15 Afternoon Session (4:00 PM):**
- **Module G Audit Complete:** Confirmed critical gaps in referee data (13/74 refs) and logic (Pace impact only).
- **Fixed:** `morning_brief.py` visual generation (macOS font paths + int casting).
- **Fixed:** `launch_parallel_sync.sh` virtual environment path (`.venv`).
- **Verified:** All systems operational.

---

### Week 2: ✅ COMPLETE - Visual Upgrade & Pipeline Integration


**✅ Jan 12 Evening Session (8:40 PM):**
- **Visual Reporting Upgrade:** Implemented Python-based PNG generator for game notes
- **Single Game Notes:** Now sends visual card + text via Telegram
- **Morning Brief Template:** Curated "Top 5" plays format verified (Diamond + SGP tiers)
- **Files Modified:**
  - `utils/render_full_report.py` - Visual card generator (Pillow + Pilmoji)
  - `module_f.py` - Added `generate_image_card()` method
  - `send_single_game_notes.py` - Image + text delivery
  - `utils/mock_morning_brief.py` - Morning Brief template

**✅ Design Specifications:**
- **Background:** Moleskine Cream (#FDFBF7)
- **Ink Color:** Deep Navy (#0F172A / 26,44,66)
- **Highlight:** Teal (#00A896)
- **Logo:** Ludi Wreath Seal (Navy, Transparent Background)
- **Font:** Arimo (Sans) + Tinos (Serif)

**✅ Jan 12 AM Completed Work:**
- **Cloud Fixes (9:55 AM):** Added `lxml`, `numpy` to requirements.txt, fixed workflow tier vars
- **Module D Integration (10:00 AM):** Wired `yak.get_player_status()` into main.py
- **Module E Integration (11:35 AM):** Wired `calib.calibrate_player()` into pipeline
- **Verification Tests (11:45 AM):** All 4 tests passing (Slasher, Blowout, MinLimit, StretchBig)

**✅ Pipeline Now Complete:**
```
A (Odds) → D (Injuries) → C (Simulation) → E (Calibration) → F (Report + Visual)
```

**✅ Module F (Alchemist V4.6) - Visual Upgrade:**
- Text Report: create_daily_briefing()
- Visual Card: generate_image_card() → PNG output
- Returns tuple: (text_report, image_path)

**✅ Phase 1: Foundation Repair (Jan 13, 09:45 AM):**
- **Data Integrity:** Fixed 92 game records with missing team names in `ludi.db`.
- **Ingestion Upgrade:** Patched `migrate_json_to_sqlite.py` to parse Tank01 game IDs (fallback logic).
- **Git Hygiene:** Removed untracked `gemini-cli` submodule.

**✅ Phase 2: Settlement & ROI (Jan 13, 10:15 AM):**
- **Settlement Engine:** Created `settle_bets.py` to grade pending bets against actual game logs.
- **Results:** Settled 4,000+ bets. Jan 12 Summary: 49.6% Win Rate, -2.3% ROI (High volume due to testing).
- **Workflow:** Integrated settlement into `data_sync.yml` (Runs 5 AM EST).

**✅ Phase 3: Automation (Jan 13, 10:30 AM):**
- **Visual Briefing:** Created `morning_brief.py` production engine.
- **Scheduling:** Full 4-Stage Daily Workflow:
    - 5:00 AM: Data Sync + Settlement P&L + PM Bot Morning Brief
    - 10:00 AM: Visual Morning Brief (Top 5 Quality)
    - 6:00 PM: Evening Lock (Visual)
    - 8:00 PM: PM Bot Nightly Brief
- **Visual Upgrade:** Validated 1200px visual card with "Top 3 Per Game" curation.
- **Telegram:** Visuals sent as image-only; Work briefs sent as text.

**✅ Live Fire Test (Jan 13):**
- **Target:** PHX, HOU, OKC games.
- **Result:** Successfully generated and delivered visual card for today's slate.

**🔄 Active Background Processes:**
- **Tracking Sync:** `scripts/sync_tracking_complete.py` is running (Backfilling NBA API data).
- **Regression Backtest:** Analysis results stored in `regression_backtest_*.csv`.

**⏳ Next Steps (Jan 14):**
- **P1:** Monitor Tracking Sync completion.
- **P2:** Phase C - Referee Impact Validation (backtest_refs.py).
- **P3:** Multi-Bookmaker Tracking Enhancement

### Week 2: ✅ COMPLETE - Data Sync, Automation, Tags

**✅ Database Sync:**
- Records: 12k+ logs backfilled.
- Table: `games` confirmed to have `referee_crew` for analysis.

**✅ Tag System:**
- Archetypes: SLASHER, STRETCH_BIG, etc.
- Scenarios: BENEFICIARY, USAGE_VACUUM.
- Matchups: vs_PAINT_PACK, vs_BLITZ.


**✅ Days 1-2: Logging Framework (Complete):**
- `utils/bet_logger.py` (650 lines) - BetLogger class with dual storage
- SQLite tables: `bet_recommendations`, `bet_daily_summaries` in ludi.db
- JSON logs: `logs/bets/YYYY-MM-DD.json` format
- **Status:** Operational & Backfilled.

**✅ Days 3-4: Tag Classification System (Complete - Jan 8, 2026):**
- **Core Utility:** `utils/tag_classifier.py` (492 lines) - Searchable play classification
- **4 Tag Categories:** Archetype (6), Scenario (4), Matchup (5+), Market (extensible)
- **Module F Integration:** v4.6 with tag assignment in bet logging pipeline
- **Storage Format:** JSON arrays in SQLite (`["STRETCH_BIG", "BENEFICIARY", "vs_PAINT_PACK"]`)
- **Archetype System:** STRETCH_BIG, SLASHER, SNIPER, RIM_RUNNER, BALL_HOG, GENERALIST
- **Scenario Tags:** BENEFICIARY, USAGE_VACUUM, MINUTES_LIMIT, HOT_STREAK
- **Matchup Tags:** vs_PAINT_PACK, vs_BLITZ, vs_PERIMETER, vs_FUNNEL, vs_HACKERS, vs_NEUTRAL
- **Market Tags:** CORRELATED_SGP (framework for CONTRARIAN, STEAM_MOVE, CLOSING_VALUE)

**✅ Vibe Starters Assistant (Upgraded - Jan 8, 2026):**
- **Persona:** "The Smart Creative" (Voice: "Let's cook", "The Blueprint")
- **Assets:** V10 Vector Headers (clean, minimalist design)
  - Morning: `header_morning_vector_v10_1767920729761.png`
  - Nightly: `header_nightly_vector_v10_1767920745059.png`
  - Break: `header_break_recharge_v2_1767921486336.png` (NEW - state preservation)
- **Iconography:** "IYKYK Elite Set" - 💎 (Vision), 📐 (Blueprint), 🥃 (Intel), 🍾 (Wins), 🥊 (Pivot), 🧊 (Vibe)
- **Context Optimization:** Reads `task.md` + `UPDATED_STATUS_AND_NEXT_STEPS.md` (focused, fast)
- **NEW Feature:** Break message trigger (`utils/trigger_break.py`) for work session pauses
- **Integration:**
    - `utils/pm_bot.py`: AI generation logic with V10 assets
    - `.github/workflows/daily_briefing.yml`: Automated Morning Brief (5am EST)
    - `.github/workflows/nightly_debrief.yml`: Automated Nightly Debrief (8pm EST)

**✅ System Audit: Referee Nomenclature (Complete - Jan 8, 2026):**
- **Document:** `REFEREE_NOMENCLATURE_AUDIT.md` (462 lines) - Comprehensive Module G analysis
- **Current Match Rate:** 16.7% (2/12 officials matched today)
- **Risk Assessment:** 🟡 MEDIUM (functional but suboptimal, substring matching is fragile)
- **Recommendations:** Phase 1 (exact matching + normalization), Phase 2 (unit tests), Phase 3 (expand coverage)

---

### Week 1: ✅ COMPLETE

**✅ Module Implementation Status:**
- All 9 modules (A-H + X) production-ready: **73,232 lines of code**
- API integrations: The-Odds-API (PAID 20K/mo), Tank01 (PAID 1K/day)
- Utilities: Devigging, monitoring, retry logic all complete
- Database: 10,840 game logs, 505 players, 496 games migrated
- **NEW:** `test_pipeline.py` - Full end-to-end integration test (456 lines)
- **NEW:** Telegram notification system - Real-time alerts & daily briefings

**✅ Integration Test Results (Jan 7, 7:00 PM ET):**
- **test_pipeline.py**: ✅ PASSED ALL CRITERIA
- Games processed: 3 (CHI-DET, WAS-PHI, TOR-CHA)
- Players simulated: 19 (dynamic roster discovery via database)
- Diamond plays generated: 5 recommendations
- API cost: **$0.1125** (75 credits, **25% under budget**)
- Current usage: 19,729/20,000 credits remaining (98.6%)

**✅ Fixed Issues:**
- Module A: Invalid market names corrected (player_field_goals_attempts → removed)
- test_pipeline.py: Type validation added for prop lines (N/A handling)
- Roster discovery: 100% automated, zero hardcoded player names

**📊 Cost Performance:**
| Metric | Value | Status |
|--------|-------|--------|
| Per Game (Test) | $0.0375 | ✅ 62% under target |
| Daily (3 games avg) | $0.1125 | ✅ Well within budget |
| Monthly (30 days) | $3.38 | ✅ 89% headroom |
| Paid Tier Budget | $30.00/month | ✅ Active |

### Module Class Names Reference (CRITICAL)

**Use these EXACT class names when importing modules:**

| Module | File | Correct Class Name | API Integration |
|--------|------|-------------------|-----------------|
| A: Gatekeeper | `module_a.py` | `Gatekeeper` | The-Odds-API (PAID) |
| B: Engine | `module_b.py` | `print_sharp_box_score` (function) | None (display layer) |
| C: Oracle | `module_c.py` | `LudiOracle` | None (pure math) |
| D: Yak | `module_d.py` | `LudiYak` | Tank01 + DuckDuckGo |
| E: Calibrator | `module_e.py` | `LudiCalibrator` | None (matchup logic) |
| F: Alchemist | `module_f.py` | `LudiReporter` | Devigging (local) |
| G: Zebras | `module_g.py` | `LudiRefEngine` | NBA.com (scraping) |
| H: Historian | `module_h_historian.py` | `LudiHistorian` | Tank01 (PAID) |
| X: Scenario | `module_x_scenario.py` | `ScenarioBuilder` | None (usage vacuum) |

**Import Examples:**
```python
from module_a import Gatekeeper              # ✅ Correct
from module_c import LudiOracle              # ✅ Correct
from module_e import LudiCalibrator          # ✅ Correct

# WRONG (old names - DO NOT USE):
from module_a import LudiGatekeeper          # ❌ ImportError
from module_c import LudiSimulator           # ❌ ImportError
from module_e import LudiEvaluator           # ❌ ImportError
```

---

## Development Commands

### Environment Setup
```bash
# 1. Create virtual environment (if needed)
python3.11 -m venv venv

# 2. Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or: .\venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install numpy pandas requests python-dotenv duckduckgo-search pytz unidecode

# 4. Configure environment variables
cp .env.template .env
# Then edit .env with your API keys (ODDS_API_KEY, TANK01_KEY required)
```

### Paid Tier Setup (NEW - January 7, 2026)
```bash
# The system is now configured for PAID tier APIs!
# Your .env file contains:
# - ODDS_API_KEY: 9aa84b1836e565ec82161558d5cc948b (PAID: 20K requests/month)
# - TANK01_KEY: b4ec1031f4msh80f4fc4cd874de4p17e5b7jsn8eeafd9da310 (PAID: 1K requests/day)
# - ODDS_API_TIER: paid
# - TANK01_TIER: paid

# To verify tier configuration:
./venv/bin/python -c "import config"
# Should output:
# ✅ Core API keys loaded (ODDS_API_KEY, TANK01_KEY)
# ✅ The-Odds-API tier: PAID (limit: 20,000 requests/month)
# ✅ Tank01 tier: PAID (limit: 1,000 requests/day)
```

### Running the System
```bash
# Run the main daily pipeline (orchestrates all modules)
./venv/bin/python main.py

# Test integration (verifies Module A connectivity)
./venv/bin/python test_integration.py

# Run prototype simulation engine (validates math)
./venv/bin/python prototype_engine.py

# Initialize/verify database
./venv/bin/python database.py

# Sync historical data to database
./venv/bin/python module_h_historian.py
```

### Monitoring API Usage (NEW - Paid Tier Integration)
```bash
# View real-time API usage logs
cat api_usage_log.json | python -m json.tool

# Get usage summary (requires implementing monitor_api_usage.py)
./venv/bin/python monitor_api_usage.py

# Check Telegram alerts
# Alerts are sent automatically when:
# - API quota >80% consumed
# - API errors occur
# - Rate limits hit
```

### Telegram Notifications (NEW - January 7, 2026)
```bash
# Send a test message
python -c "from utils.telegram_notifier import send_message; send_message('✅ Test from Ludi Bot')"

# Send an alert
python -c "from utils.telegram_notifier import send_alert; send_alert('Test Alert', 'This is a test')"

# Send daily briefing (auto-splits if >4096 chars)
python -c "from utils.telegram_notifier import send_daily_briefing; send_daily_briefing(briefing_text)"

# Get your Telegram chat ID (if needed)
./venv/bin/python get_telegram_chat_id.py
```

**Bot Configuration:**
- Bot: @CashingChips_bot (Ludi_Bot)
- Credentials: Set in `.env` file (`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`)
- To start: Search for @CashingChips_bot in Telegram, send `/start`

**Usage in Code:**
```python
from utils.telegram_notifier import send_message, send_alert, send_daily_briefing

# Send formatted message
send_message("*Bold text* and _italic text_")

# Send alert
send_alert("API Warning", "80% of quota consumed")

# Send daily briefing (from Module F)
briefing = reporter.generate_report(processed_slate)
send_daily_briefing(briefing)

# Send Vibe Starters AI Brief (Manual Test)
python utils/pm_bot.py
```

### Vibe Starters Assistant (PM Bot)
**Role:** Project Manager & Personal Assistant
- **Morning Routine:** Sends "The Vision", "The Blueprint", "The Intel" at 5am.
- **Nightly Routine:** Sends "The Wins", "The Pivot", "The Vibe" at 8pm.
- **Assets:** Clean, minimalist images stored in `.gemini/antigravity/brain/...` (configured in `pm_bot.py`)

### Design Identity & Visual Guidelines
**Core Logo:** The "Winking Notebook" (Character).
- **Visuals:** A friendly, animated notebook character with a winking face and "sparks" flying out the top.
- **Vibe:** Playful, "Get it done", Approchable, NOT cold/industrial.
- **Reference Image:** `/home/mnprice86/.gemini/antigravity/brain/cc7a00ac-2b90-4fa5-9eec-9978df401a91/uploaded_image_1767915156997.png`
- **Typography:** Rounded sans-serif, friendly but clean.
- **Colors:** Cream, Dark Slate, Gold Sparks.

### Brand Iconography (The "IYKYK" Elite Set)
*Use these "Insider/Sharp" anchors:*
- **Morning Vision:** 💎 (The Diamond / Sharp Vision)
- **The Blueprint:** 📐 (The Angle / The Playbook)
- **The Intel:** 🥃 (The Pour / Straight Up Truth)
- **The Wins:** 🍾 (The Toast / Bottles)
- **The Pivot:** 🥊 (The Counter-Punch / Adjustment)
- **The Vibe/Energy:** 🧊 (Stay Frosty / Composed) or 🛑 (Hard Stop)
- **Separators:** `──────────────` (Clean Line)
- **Metadata:** `📅 JAN 08 | 🟢 ONLINE` (Monospace)

### Testing Individual Modules
```bash
# Test Module A (Gatekeeper - fetches odds)
python -c "from module_a import Gatekeeper; gk = Gatekeeper(); print(gk.fetch_live_slate())"

# Test Module D (Yak - injury intelligence)
python -c "from module_d import LudiYak; yak = LudiYak(); print(yak.get_injuries())"

# Test Module F (Alchemist - edge calculation)
python module_f.py  # If it has a __main__ block

# Test devigging utility
python -c "from utils.devig import devig_multiplicative; print(devig_multiplicative(-110, -110))"
```

### Database Operations
```bash
# Inspect database contents
python inspect_db.py

# Backup database before migrations
cp ludi.db ludi.db.backup_$(date +%Y%m%d_%H%M%S)

# Migrate JSON to SQLite (one-time operation)
python migrate_json_to_sqlite.py

# Query database directly
sqlite3 ludi.db "SELECT COUNT(*) FROM player_game_logs;"
sqlite3 ludi.db "SELECT DISTINCT team_abbreviation FROM player_game_logs ORDER BY team_abbreviation;"
### Ludi Lens v2.0 Architecture (Target State - Week 6)
**The Mission:** Validate the Math (Week 3-5), then Build the War Room (Week 6).

**1. The Stack:**
*   **Frontend:** Streamlit (Hosted on Community Cloud or Local)
*   **Backend:** Python Modules A-H (The S.A.V.A.G.E. Engine)
*   **Database:** SQLite (`ludi.db`) - The Single Source of Truth
*   **Automation:** GitHub Actions (Morning Briefs) + Render/Telegram (Real-time Scout)

**2. Key Files (To Be Built):**
*   `app.py`: The War Room Dashboard (Streamlit)
*   `engine.py`: The Simulation Core (Poisson/Normal Hybrid)
*   `scout.py`: The "Pulse Protocol" (News/Injury Alerts)
*   `config.py`: Central Command (Theaters, Colors, Keys)

**3. The Syndicate Workflow:**
*   **05:00 AM (The Night Shift):** Historian syncs box scores. Scout checks NBAstuffer (Ref Stats). Ledger grades bets.
*   **09:05 AM (The Live Wire):** Scout Grabs Official Ref Assignments. Gatekeeper pulls Opening Lines.
*   **09:10 AM (The Physics):** Engine runs 5,000 Hybrid Sims using Usage Vacuums & Ref Modifiers.
*   **09:30 AM (The Briefing):** "Executive Briefing" delivered to Dashboard & Telegram.

**4. Data Sources (The "Intel Stack"):**
*   **Speed:** Underdog NBA Twitter (The Trigger)
*   **Context:** Beat Writer Lists (The "Why" / Narrative Tax)
*   **Physics:** NBAstuffer (Ref Bias, Usage Rates)
*   **Economics:** Covers/OddsShark (Betting Trends, Line Movement)
*   **Official:** NBA API (L2M Reports, Lineups)

## Architecture Overview

### Modular Pipeline Design

The system uses a **sequential pipeline** where data flows through 9 specialized modules:

```
┌─────────────────────────────────────────────────────────┐
│  MODULE A: Gatekeeper (Odds Ingestion)                  │
│  - Fetches game lines, player props from The-Odds-API   │
│  - Integrates Module G (referee assignments)            │
│  - Outputs: Game slate, prop lines, referee factors     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MODULE B: Engine (Historical Analysis)                 │
│  - Loads player game logs from ludi.db                  │
│  - Calculates season avg, L5, L10 trends                │
│  - Identifies "hot streaks" for reporting               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MODULE C: Oracle (Monte Carlo Simulation)              │
│  - 25,000 Poisson iterations per player                 │
│  - Simulates FGA, FG3A, FTA (volume)                    │
│  - Applies shooting %s, pace, fatigue, referee impact   │
│  - Outputs: Projected stats with confidence intervals   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MODULE D: Yak (Injury Intelligence)                    │
│  - 15-minute refresh cycle (aligns with NBA rules)      │
│  - Primary: Tank01 API, Secondary: BallDontLie          │
│  - Nuance detection via DuckDuckGo search               │
│  - Classifies: OUT/DOUBTFUL/Q/PROBABLE/MINUTES_LIMIT    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MODULE E: Calibrator (Matchup Adjustments)             │
│  - Assigns player archetype (SLASHER, STRETCH_BIG, etc) │
│  - Applies matchup modifiers vs defense schemes         │
│  - Blowout tax (spread > 12.5 reduces volume)           │
│  - Pace modifiers (totals > 238 or < 218)               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MODULE F: Alchemist (Edge Calculation & Reporting)     │
│  - Devigs bookmaker odds (removes vig)                  │
│  - Calculates TRUE edge vs fair probability             │
│  - Filters: edge ≥ 5% threshold                         │
│  - EV & unit sizing (0.25u to 1.5u)                     │
│  - Classifies: DIAMOND/BLUE CHIP/CORE ASSET/THE STEAL   │
│  - Generates daily_briefing.txt                         │
└─────────────────────────────────────────────────────────┘

Supporting Modules:
  MODULE G: Zebras (referee pace impact, scraped daily)
  MODULE H: Ghost Protocol (browser-based backfill engine, v2.1)
    - Playwright automation bypassing stats.nba.com WAF
    - Extracts Tracking (Drives, C&S, Pull-Ups, Speed), Advanced, Clutch stats
    - Hydrates: player_game_tracking, player_game_advanced, player_clutch_stats
    - ID-compatible: Extracts official NBA Player IDs from HTML
  MODULE X: Scenario Builder (injury "what-if" toggles)
  MODULE I: Aggregator (future unified data layer - placeholder)
```

### Database Schema (ludi.db)

**Key Tables:**
- `player_game_logs` (10,840 records): Historical performance data with all stats
- `players` (505 records): Current roster with archetypes and usage
- `games` (496 records): Game results with pace and referee crews
- `odds`: Live market data from bookmakers
- `simulations`: Model output archive for backtesting

**Indexes for Performance:**
- `idx_player_game_logs_player_date` (composite index for fast player queries)
- `idx_player_game_logs_game_date` (for date-range queries)

### Critical Innovations

#### 1. Devigging (Module F - v4.4 Update, Jan 6 2026)
**What it does**: Removes bookmaker vig (overround) to calculate TRUE edge instead of raw edge.

**Why it matters**: Without devigging, edge calculations are understated by 3-5%. A bet that looks like 2.8% edge might actually be 7.6% true edge.

**Implementation**: Uses `utils/devig.py` with multiplicative method
```python
from utils.devig import devig_multiplicative
fair_over, fair_under = devig_multiplicative(-110, -110)
true_edge = (model_prob - fair_over) / fair_over * 100
```

#### 2. Usage Vacuum Theory (Module C + Module X)
**Concept**: When a star player is OUT, their usage (FGA, FTA, TOV) is redistributed to teammates.

**Implementation**:
- Module X creates "WITHOUT [Player]" scenarios
- Module C redistributes usage percentage across remaining rotation
- Module F labels beneficiaries in briefing output

#### 3. Blowout Tax (Module F)
**Problem**: Starters sit early in blowouts, killing volume props.

**Solution**: Sliding scale reduction based on spread
```python
if spread > 7.0:
    blowout_mult = 1.0 - ((spread - 7.0) * 0.015)
    # Example: 12-point spread = 0.925 multiplier (-7.5% volume)
```

#### 4. 15-Minute Injury Sync (Module D)
**Why 15 minutes**: NBA requires teams to report injuries 15 minutes before tipoff.

**Implementation**:
- Caches injury data for 15 minutes (`yak_cache.json`)
- Refreshes at 14:59 mark before games
- Nuance detection scans news for "late scratch", "minutes limit" keywords

#### 5. Archetype Matchup Matrix (Module E)
**Concept**: Player style vs defensive scheme creates exploitable edges.

**Example Matchups**:
- STRETCH_BIG vs PAINT_PACK defense → +15% 3PM/3PA (paint defenders leave shooters open)
- SLASHER vs HACKERS defense → +20% FTA (aggressive rim protection = more fouls)
- RIM_RUNNER vs PERIMETER defense → +30% OREB (small ball concedes size advantage)

**Team Defense Schemes (2025-26)**:
- PAINT_PACK: OKC, BOS, DET, MIN, SAS, ORL
- BLITZ: HOU, TOR, MIA, PHX
- PERIMETER: GSW, DAL, NYK
- FUNNEL: WAS, ATL, CHI, UTA, SAC
- HACKERS: IND, CHA, POR

#### 6. Tag Classification System (Week 2 Days 3-4, Jan 8 2026)
**What it does**: Assigns searchable tags to betting recommendations for filtering, analysis, and pattern recognition.

**Why it matters**: Enables filtering bets by archetype (STRETCH_BIG), scenario (BENEFICIARY), matchup (vs_PAINT_PACK), or market context (CORRELATED_SGP). Essential for dashboard search, historical analysis, and ML training.

**Implementation**: `utils/tag_classifier.py` (492 lines) - Singleton pattern with 4 tag categories

**Tag Categories:**

1. **ARCHETYPE TAGS** (1 per player):
   - STRETCH_BIG, SLASHER, SNIPER, RIM_RUNNER, BALL_HOG, GENERALIST
   - Reuses Module E's `_assign_archetype()` logic (validated thresholds)

2. **SCENARIO TAGS** (0-4 per player):
   - BENEFICIARY: Usage vacuum beneficiary (Module X integration)
   - USAGE_VACUUM: High-usage player is OUT (>18% usage)
   - MINUTES_LIMIT: Injury management restriction (Module D status)
   - HOT_STREAK: L5 performance ≥ 20% above season average

3. **MATCHUP TAGS** (1 per game):
   - vs_PAINT_PACK, vs_BLITZ, vs_PERIMETER, vs_FUNNEL, vs_HACKERS, vs_NEUTRAL
   - Uses defensive scheme mapping (30 NBA teams)
   - Handles team aliases (PHO→PHX, NO→NOP, NY→NYK)

4. **MARKET TAGS** (0-n per bet):
   - CORRELATED_SGP: 2+ high-unit bets (≥1.2u) in same game
   - Framework extensible for CONTRARIAN, STEAM_MOVE, CLOSING_VALUE

**Storage Format**: JSON array in SQLite `bet_recommendations.tags` column
```python
tags = ["STRETCH_BIG", "BENEFICIARY", "vs_PAINT_PACK", "CORRELATED_SGP"]
stored_as = json.dumps(tags)  # ["STRETCH_BIG","BENEFICIARY","vs_PAINT_PACK","CORRELATED_SGP"]
```

**Module F Integration** (v4.6):
- Lines 6, 34-40: Import and initialize singleton
- Lines 134-168: Build context, assign tags, format for database
- Lines 332-342: Parse tags from database, display in briefing as `🏷️ TAG1 | TAG2 | TAG3`

**Usage Example:**
```python
from utils.tag_classifier import get_tag_classifier

classifier = get_tag_classifier()
tags = classifier.classify_play(
    player_packet={'base_pts': 18.9, 'base_reb': 6.5, 'base_3pm': 2.1, ...},
    game_context={'opponent': 'OKC', 'spread': 4.5, 'injury_status': 'ACTIVE'},
    scenario_field='WITHOUT Giannis (+2.4 FGA)',
    all_game_props=[...]  # For correlation detection
)
# Returns: ['STRETCH_BIG', 'BENEFICIARY', 'vs_PAINT_PACK']
```

## Key Concepts for Development

### Poisson Simulation Approach (Module C)
- **25,000 iterations** per player (optimal balance of speed vs accuracy)
- **Two-stage simulation**:
  1. Volume simulation (FGA, FG3A, FTA using Poisson distributions)
  2. Outcome simulation (apply shooting percentages)
- **Modifiers applied**: pace × referee_factor × fatigue_tax × defense_rating

### Edge Calculation Methodology (Module F)
```python
# 1. Devig bookmaker odds
fair_prob = devig_multiplicative(over_odds, under_odds)

# 2. Calculate true edge
true_edge = (model_prob - fair_prob) / fair_prob * 100

# 3. Filter by threshold
if true_edge >= 5.0:  # 5% minimum edge (sharp market standard)
    # 4. Calculate EV
    win_prob = clamp(model_prob, 0.51, 0.75)
    ev = ((win_prob * 1.91) - 1) * 100  # Assumes -110 juice

    # 5. Kelly sizing
    units = ev / 8  # Conservative fractional Kelly
    units = clamp(units, 0.25, 1.5)
```

### Validation Requirements (Week 5 Gate)
**Must-Achieve Metrics Before Dashboard Development**:
- RMSE < 10% for PTS/AST/REB projections
- Hit rate > 52% overall
- Hit rate > 55% on 10%+ edge bets
- Positive CLV (Closing Line Value) on >50% of bets

**If metrics fail**: Extend Week 6 for calibration, DO NOT proceed to dashboard.

## Configuration & Security

### Environment Variables (.env)
**Required for core functionality**:
- `ODDS_API_KEY`: The-Odds-API key (game lines, player props)
- `TANK01_KEY`: Tank01 RapidAPI key (rosters, injuries, box scores)

**Optional but recommended**:
- `BALLDONTLIE_KEY`: BallDontLie API key (props validation, backup data)
- `APISPORTS_KEY`: API-Sports key (historical backtesting data)
- `GEMINI_API_KEY`: Google Gemini AI key (Week 7 chatbot feature)

**Security**:
- `.env` file is in `.gitignore` - NEVER commit it
- Use `.env.template` as reference for required keys
- `config.py` validates required keys on import

### API Rate Limits & Caching
- **The-Odds-API**: Free tier = 500 requests/month, Paid = $30/mo for 20K
- **Tank01**: Free = 1K/month, Paid = $10/mo for 1K/day
- **Module D caching**: 15-minute cache prevents redundant injury API calls
- **Module G caching**: Referee assignments scraped once daily

## Common Development Patterns

### Adding a New Module
1. Create `module_x.py` with a class following naming convention (e.g., `LudiNewFeature`)
2. Import in `main.py` orchestrator
3. Initialize in `LudiOrchestrator.__init__()`
4. Call in `run_daily_cycle()` at appropriate pipeline stage
5. Update this CLAUDE.md with module description

### Modifying Edge Calculation
- **File**: `module_f.py` (LudiReporter or LudiAlchemist class)
- **Key methods**: `calculate_edge()`, `calculate_ev()`, `calculate_kelly()`
- **Testing**: Run `python module_f.py` if it has test code, or create unit test
- **Devigging**: Always use `utils/devig.py` functions, never raw odds

### Adding New Player Archetypes
- **File**: `module_e.py` (LudiCalibrator class)
- **Pattern**: Add to `ARCHETYPE_PROFILES` dictionary
- **Matchup modifiers**: Update `apply_matchup_modifiers()` method
- **Classification logic**: Update `assign_archetype()` based on player stats

### Updating Defensive Schemes
- **File**: `module_e.py`
- **Map**: `TEAM_DEFENSIVE_SCHEMES` dictionary (30 NBA teams)
- **Season updates**: Review schemes annually (pace changes, coaching changes)
- **Source**: NBA.com defensive stats, league pass observations

## Important Notes

### Current Project Status
- **Completed**: Security hardening, database migration (10,840 game logs), devigging implementation
- **In Progress**: Week 1 Days 5-7 integration testing (all modules A-H, X)
- **Next Phase**: Week 2 logging framework, play classification tags
- **Critical Gate**: Week 5 validation (DO NOT skip - model accuracy must be proven)

### Development Workflow
1. **ALWAYS** activate virtual environment before running code
2. **ALWAYS** check `.env` file exists with required API keys
3. **Test modules individually** before running full pipeline
4. **Backup database** before running migration scripts
5. **Paper trade** any model changes before deploying to production

### Known Issues & Gotchas
- `main.py` uses old class names (LudiGatekeeper vs Gatekeeper) - check imports
- Module I (Aggregator) is placeholder code - not yet implemented
- Referee assignments require web scraping (can fail if NBA.com changes HTML structure)
- DuckDuckGo search in Module D can be rate-limited - use sparingly
- Blowout tax logic is in Module F, not Module E (despite being a "calibration")

### Testing Strategy
- **Unit tests**: Test individual module methods in isolation
- **Integration tests**: Use `test_integration.py` to verify module connections
- **End-to-end tests**: Run `main.py` with `limit_games=1` to test full pipeline on single game
- **Validation tests**: Week 5 backtesting framework (50+ historical games)

---

## Line Shopping & EV Calculation Methodology (Added Jan 15, 2026)

### Overview: Two-Tier Line Shopping Strategy

**Core Principle:** Find the best odds available at NC Legal books (where user can actually bet), then validate model sharpness against sharp book closing lines.

**Why This Approach:**
- **Tier 1 (Betting):** NC Legal books (FanDuel, DK, BetMGM, Caesars, bet365, HRB) are the ONLY books accessible in North Carolina
- **Tier 2 (Validation):** Sharp books (Pinnacle, Bovada, BetOnline) used for CLV measurement to prove model finds real value

**Research Validation:** TopEndSports guide shows "Shopping lines on props can add 5-10% to your edge" - this system maximizes that edge by finding best NC Legal book for each market.

### Line Shopping Algorithm (Module A)

**Location:** `module_a.py` Lines 241-329

**Step 1: Establish Main Line**
```python
# NC Legal books set the main line (e.g., 27.5 for Tatum Points)
# Only ONE line per player/market to enable fair comparison
```

**Step 2: Filter Alt Lines**
```python
# Ignore alt lines (26.5, 28.5, etc.)
# Only compare same line across all books
# This ensures apples-to-apples edge calculations
```

**Step 3: Select Best NC Legal Odds**
```python
# Compare all NC Legal books at main line
# Choose HIGHEST decimal odds (best return for bettor)
# Example: FD -108 (1.926) beats DK -115 (1.870)
```

**Step 4: Track Sharp Books (CLV Validation)**
```python
# Log Pinnacle/Bovada closing line separately
# NOT for betting, but for post-bet CLV measurement
# Measure if you beat sharp market (most efficient pricing)
```

### 2025-26 NBA Season Examples (ACTIVE PLAYERS)

**Example 1: Jan 15, 2026 (9:26 PM EST) - Luka Doncic Points**
```
Player: Luka Doncic Points (ACTIVE - playing tonight)
Line: 28.5 (main line from FanDuel)

NC LEGAL BOOKS (Can Bet):
FanDuel:    28.5 @ -108  (1.926 decimal) ✅ BEST
DraftKings: 28.5 @ -115  (1.870 decimal)
BetMGM:     28.5 @ -110  (1.909 decimal)
Caesars:    28.5 @ -112  (1.893 decimal)

SHARP BOOKS (CLV Benchmark):
Pinnacle:   28.5 @ -105  (1.952 decimal) - Close line target: -120
Bovada:     28.5 @ -107  (1.935 decimal) - Close line target: -118

DECISION:
- Bet: FanDuel -108 (best NC Legal available)
- Line shopping edge: 18 cents vs DraftKings (-115)
- CLV Target: Beat Pinnacle's -120 closing line
- Result: If Pinnacle closes -120, user's -108 bet = +12 cents CLV (beat efficient market)
```

**Example 2: Jan 15, 2026 (9:26 PM EST) - Donovan Mitchell Assists**
```
Player: Donovan Mitchell Assists (ACTIVE - playing tonight)
Line: 7.5 (main line from DraftKings)

NC LEGAL BOOKS (Can Bet):
FanDuel:    7.5 @ -118  (1.847 decimal)
DraftKings: 7.5 @ -110  (1.909 decimal) ✅ BEST
BetMGM:     7.5 @ -115  (1.870 decimal)
bet365:     7.5 @ -112  (1.893 decimal)

SHARP BOOKS (CLV Benchmark):
Pinnacle:   7.5 @ -108  (1.926 decimal) - Close line target: -125
Bovada:     7.5 @ -109  (1.917 decimal) - Close line target: -124

DECISION:
- Bet: DraftKings -110 (best NC Legal)
- Line shopping edge: 8 cents vs FanDuel (-118)
- CLV Target: Beat Pinnacle's -125 closing line
- Result: If Pinnacle closes -125, DK's -110 beats closing by 15 cents (strong validation)
```

### EV Calculation & Devigging (Module F)

**Location:** `module_f.py` Lines 105-133 + `utils/devig.py`

**Critical Insight:** Without devigging, edge calculations understate true value by 3-5%

**Process:**
1. **Devig NC Legal odds:** Remove bookmaker vig to find fair probability
2. **Compare to model:** Module C generates probability from 5,000 Poisson simulations
3. **Calculate edge:** (model_prob - fair_prob) / fair_prob × 100
4. **Filter:** Only recommend bets with ≥5% edge (sharp market standard)
5. **Size units:** Use 12.5% fractional Kelly (conservative vs 25-50% recommended)

**Example (Active Player - 2025-26 Season):**
```
Doncic Over 28.5 @ FanDuel -108 (Jan 15, 2026)

Devigging:
- Raw implied (FD -108): 51.95%
- Devigged fair prob: 50.8% (removes 1.15% vig)

Model says: 62% (from 5,000 Poisson simulations)

Edge calculation:
- Raw edge: 62% - 51.95% = 10.05% (understated!)
- TRUE edge: (62% - 50.8%) / 50.8% = 22.0% (real value revealed)

Unit sizing:
- EV = 0.62 × 1.926 - 1 = 0.195 = 19.5%
- Units = 19.5% / 8 = 2.44u
- Capped at 1.5u (conservative Kelly - avoid ruin)

Conclusion:
- Devigging revealed 12% more edge than raw odds (22% vs 10%)
- This is why devigging is CRITICAL for accurate edge calculation
```

### CLV Tracking System (NEW - Added Jan 15, 2026)

**Definition:** Closing Line Value measures whether your NC Legal bet odds beat the final sharp closing line.

**Why CLV > Win Rate:**
- Win rate is noisy (luck variance, blowouts, etc.)
- CLV is signal (you consistently found value the market adjusts to)
- Professional bettors beat closing line 55-60% of the time
- CLV > 0 over 30+ days = model is SHARP

**Implementation:**

**Phase 1: Database Schema**
```sql
ALTER TABLE bet_recommendations ADD COLUMN closing_odds_over INTEGER;
ALTER TABLE bet_recommendations ADD COLUMN closing_odds_under INTEGER;
ALTER TABLE bet_recommendations ADD COLUMN clv_cents INTEGER;
ALTER TABLE bet_recommendations ADD COLUMN closing_time TEXT;
```

**Phase 2: Capture Closing Lines**
- New script: `scripts/capture_closing_lines.py`
- Runs 5 minutes before tipoff via GitHub Actions
- Fetches sharp book closing line from The-Odds-API
- Stores in database for CLV calculation

**Phase 3: CLV Calculation**
- New utility: `utils/clv_calculator.py`
- Formula: `(opening_decimal - closing_decimal) × 100` = CLV in cents
- Example: FD -108 (1.926) vs Pinnacle closing -120 (1.833) = +9.3 cents

**Phase 4: CLV Reporting**
- Updated: `utils/pm_bot.py` - daily CLV summary
- Optional: Streamlit dashboard section showing CLV trends
- Metric: Average CLV over last 30 days (target: +5 cents or higher)

**CLV Example (Active Player - 2025-26 Season):**
```
Bet: Doncic Over 28.5 @ FanDuel -108 (Jan 15, 2026, 2:00 PM)
Closing: Pinnacle Over 28.5 @ -120 (Jan 15, 2026, 7:55 PM - 5 min before tipoff)

CLV Analysis:
- Your FD odds: -108 = 1.926 decimal
- Pinnacle closing: -120 = 1.833 decimal
- CLV: +9.3 cents (you beat sharp market)

Interpretation:
- Market moved 12 cents against your position
- Proves you found value before sharp money recognized it
- This is the signal that your model is SHARP
```

### Best Practices (Research-Backed)

**Do:**
- ✅ Compare all NC Legal books at main line
- ✅ Use devigging for true edge (multiplicative method)
- ✅ Filter by ≥5% edge minimum
- ✅ Track sharp closing lines for CLV validation
- ✅ Size bets with conservative Kelly (12.5% fractional)
- ✅ Report daily CLV (not win rate)

**Don't:**
- ❌ Use consensus average odds (line shopping beats averaging)
- ❌ Bet on alt lines (25.5 vs 27.5 creates apples-to-oranges comparisons)
- ❌ Skip devigging (edge is understated by 3-5%)
- ❌ Bet sharp books (Bovada/Pinnacle not accessible in NC)
- ❌ Use aggressive Kelly sizing (1.5u max prevents ruin)
- ❌ Trust win rate alone (CLV is the signal)

### Current Implementation Status

**Existing (Working):**
- ✅ Line shopping algorithm (Module A) - finds best NC Legal book
- ✅ Devigging engine (utils/devig.py) - multiplicative method
- ✅ EV calculation (Module F) - true edge vs model probability
- ✅ 5% threshold filter - quality bet selection
- ✅ Kelly sizing (12.5% fractional) - unit management

**In Progress (Jan 15, 2026):**
- 🔄 CLV tracking system - capture closing lines, calculate CLV
- 🔄 CLV reporting - daily metrics in PM Bot
- 🔄 CLAUDE.md documentation - this section

**Future (Not Yet):**
- ⏳ DFS multiplier conversion (PrizePicks/Underdog) - LOW priority
- ⏳ Steam detection (rapid line movement alerts)
- ⏳ Multi-book arbitrage detection

---

## Resources

- **Implementation Plan**: See `/Users/flyprice/.claude/plans/tranquil-coalescing-patterson.md` (updated Jan 15, 2026)
- **Project History**: See `original vision/more_relevant_history.md` for context
- **Week Status**: See `UPDATED_STATUS_AND_NEXT_STEPS.md` for current progress
- **Completion Reports**: See `WEEK1_DAY2-4_COMPLETION_REPORT.md` for past milestones
- **Line Shopping Analysis**: See `docs/LINE_SHOPPING_GUIDE.md` (being created)
- **CLV Tracking Guide**: See `docs/CLV_TRACKING_GUIDE.md` (being created)

## Strategic Roadmap: The Road to "Pro" (Week 6+ Concepts)
*These concepts identify "Smart Money" regression spots and are slated for the Calibration Phase.*

### 1. Strength of Schedule (SOS) Adjustment
**Concept:** Adjust L10 averages based on opponent defensive rating.
- **Example:** Scored 12 pts vs #1 Defense → Rated as "Neutral" (not bad).
- **Implementation:** Weighted multiplier on historical logs before calculating baseline.

### 2. Depth Chart Authority (Rotation Chaos)
**Concept:** Explicitly model "Starter Returns" impact on bench usage.
- **Problem:** When Haliburton returns, McConnell's minutes drop, but his L5 logs are still inflated.
- **Solution:** Maintain team depth charts; trigger "Minutes Compression" when a starter enters active status.

### 3. Shooting Luck Deviation (The "Poor Man's ShotQuality")
**Concept:** Identify unsustainable efficiency variance.
- **Signal:** Large gap between Season FG% (48%) and L5 FG% (25%).
- **Action:** Bet on **Positive Regression** (Buy Low).

### Strategic Roadmap: PBP Stats Expansion
PBP Stats API capability verification complete (Jan 14). The following data layers are unlocked for future integration:
1.  **WOWY Impact (Scenario Builder):** Use `get_player_on_off_impact` to replace usage vacuum heuristics with real On/Off OffRtg splits.
2.  **Clutch/Leverage:** Use `get_team_leverage_summary` to identify "Clutch Killers" (high performance in High Leverage).
3.  **Lineup Analysis:** Use `get_game_stats(Type="Lineup")` to fade/target specific bench units.
4.  **Shot Distance:** Use shot location data to refine "Rim Runner" vs "Pop Big" archetypes.

