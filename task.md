- [x] Review and Verify Current Telegram Bot Status
- [x] Refine Telegram UI & Experience (New Request) <!-- id: 2 -->
    - [x] Create Implementation Plan & Evaluation
    - [x] Monitor Design: Morning Header (Restored V5 - Square)
    - [x] Generate Design: Nightly Header (Restored V3 - Square)
    - [x] Generate FINAL FUSION: Wide Clean Vector (Morning/Night)
    - [x] Generate Break Header: "Recharging" (Refined V2)
    - [x] Implement "Full Package Card" Text Layout (Notebook Aesthetic)
    - [x] Implement `send_break_message()` in `utils/pm_bot.py`
    - [x] Verify changes
    - [x] Discover GitHub Actions Workflows (daily/nightly)
    - [x] Update Workflows to use new `pm_bot.py` logic (Committed)
    - [x] Verify `main.py` calls `ProjectManagerBot` correctly
    - [x] **FIX: GitHub Actions API Keys & SDK Migration (Jan 11, 2026)**
        - [x] Add secrets to workflows (daily/nightly)
        - [x] Migrate to `google-genai` SDK
        - [x] Add missing dependencies (`unidecode`, `beautifulsoup4`, etc.)
    - [x] **Feature: Single Game Notes (Jan 11, 2026)**
        - [x] Create `send_single_game_notes.py` for targeted reporting
        - [x] Schedule GitHub Action (`game_notes_mil_den.yml`) for 10am EST
- [x] Evaluate ShotQuality Integration (New Request) <!-- id: 3 -->
    - [x] Create Analysis Report
    - [x] Determine Integration Points (Module E/F)
- [x] Implement Play Classification Tags (Week 2, Days 3-4) <!-- id: 0 -->
    - [x] Create `utils/tag_classifier.py`
    - [x] Integrate tags into `module_f.py` (Briefing generation)
    - [x] **Validation Phase B: Archetype Backtesting:**
  - [x] Implement `backtest_archetypes.py` (8 Archetypes x 5 Def Schemes)
  - [x] Define Defensive Schemes (Funnel, Paint Pack, etc.)
  - [x] Run Archetype Validation on Targeted Slate (Jan 9-10)

- [x] **BUG FIX: Line Capture Priority (Jan 9 - FIXED)**
  - [x] Module A was capturing Bovada alts instead of NC Legal
  - [x] Deployed priority logic for FanDuel/DraftKings

- [x] **Rescue Mission: Ludi Vision Restored (Jan 12, 2026)**
  - [x] Math Integrity Audit (EV Check)
  - [x] Architecture: Scenario Forks (GTD Play vs Sit)
  - [x] Yak Enhancement: Targeted Deep Search (Coach/Beat Writers)
  - [x] Archetype Overhaul: Scout-Approved Tiers (Heliocentric, Hub Big, Elite Scorer)
  - [x] Trend Watch & Secondary Archetypes Implemented
  - [x] Full Backtest Validation (RMSE 5.92)

- [x] **Phase 4: The Digital Scout (Jan 12, 2026)**
  - [x] Module G: Live Referee Scraping (official.nba.com)
  - [x] Module G: Crew Impact Calculation
  - [x] Pipeline Verification: `verify_slate_logic.py` created & passed
  - [x] Documentation: `MISSION_COMPLETE.md` & `TOOLS_GUIDE.md` generated

- [x] **P0: CRITICAL - Integrate Yak into Main Pipeline (Jan 12, 10:00 AM)**
  - [x] Add self.yak.get_player_status() call in main.py
  - [x] Update player status before building scenarios
  - [x] Skip players with status OUT/DOUBTFUL

- [x] **Module E Integration (Jan 12, 11:35 AM)**
  - [x] Wire calibrate_player() into main.py build_reporter_input
  - [x] Pass opponent context for matchup logic
  - [x] Pass yak_report for MINUTES_LIMIT handling
  - [x] Added base stats for archetype classification

- [x] **Verification Tests (Jan 12, 11:45 AM)**
  - [x] Created verify_calibration.py
  - [x] Test 1: Slasher vs Hackers - PASSED (+20% FTA)
  - [x] Test 2: Blowout Tax - PASSED (-6% all stats)
  - [x] Test 3: Minutes Limit - PASSED (-25% all stats)
  - [x] Test 4: Stretch Big vs Paint Pack - PASSED (+15% 3PM)

- [x] **Archetype Backtest (Jan 12, 12:00 PM)**
  - [x] Created backtest_archetypes.py
  - [x] Validated historical matchup patterns

- [x] **P0: Refactor send_single_game_notes.py (Jan 12, 12:25 PM)**
  - [x] Use LudiOrchestrator for full A→D→C→E→F pipeline
  - [x] Deleted verify_calibration.py (tests complete)
  - [x] Tested successfully with Telegram

- [x] **P1: Full Season Backtest Mode (Jan 12, 12:30 PM)**
  - [x] Added --full-season flag (120 days vs 60)
  - [x] Both modes tested and working

- [ ] **ENHANCEMENT: Multi-Bookmaker Tracking (Post-Validation)**
  - [ ] Refactor Module A to store Lines per Bookmaker
  - [ ] Update Module F to Report Best Line + Book
  - [ ] Enable "Line Shopping" Logic in Main Orchestrator
  - [ ] Create utils/line_shop.py for sharp vs NC comparison

- [ ] **Validation Phase C: Referee Impact & Final Report:**
  - [ ] Implement `backtest_refs.py` (Crew Analysis)
  - [ ] Generate WEEK 3 VALIDATION REPORT
- [ ] Implement Confidence Intervals (Week 2, Days 5-7) <!-- id: 1 -->
    - [ ] Update `module_c.py` for percentiles
    - [ ] Update `module_f.py` for risk display

- [-] Execute Backtesting Protocol (Week 3) <!-- id: 4 -->
    - [x] Run `backtest_model.py` on 50 historical games
    - [x] Validate Regression/SOS Logic
    - [x] Validate Rotation/Depth Chart Logic
    - [x] Validate Shooting Luck Logic

- [x] **Visual Reporting Upgrade (Jan 12, 8:40 PM)**
    - [x] Create `utils/render_full_report.py` - Python PNG generator
    - [x] Implement Moleskine Cream background (#FDFBF7)
    - [x] Add Navy Ludi Wreath logo (transparent bg)
    - [x] Add `generate_image_card()` to `module_f.py`
    - [x] Update `send_single_game_notes.py` for image delivery
    - [x] Create `utils/mock_morning_brief.py` for template testing
    - [x] Verified: UTA@CLE, LAL@SAC, BKN@DAL game notes sent
    - [x] Finalized: Morning Brief "Top 5 Quality" format

- [ ] **Morning Brief Automation (Jan 13)**
    - [ ] Update GitHub Actions workflow for visual cards
    - [ ] Integrate curated "Diamond + SGP" template

