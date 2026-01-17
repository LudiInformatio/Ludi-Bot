# Ludi Lens v2.0: REVISED 8-Week Strategic Plan (Post-Assessment)

**Document Version:** 2.0 - Updated After Comprehensive Project Assessment
**Revision Date:** January 4, 2026
**Previous Plan:** 6 weeks (Foundation → Engine → Dashboard → Automation)
**New Plan:** 8 weeks (Foundation → Engine → **VALIDATION** → Calibration → Dashboard → Automation)

**GitHub Repository:** https://github.com/LudiInformatio/Ludi-Bot.git

---

## REVISION SUMMARY: What Changed and Why

### Critical Discovery from Assessment

The original 6-week plan had a **critical blind spot**: it jumped from building projections (Week 4) directly to dashboard (Week 5) without ever validating if the model was accurate.

**Industry Standard:** 15-20 weeks from concept to production-ready system
- Weeks 1-4: Design & Prototype ✅ *Original plan included this*
- **Weeks 5-10: Validation & Calibration** ❌ **MISSING from original plan**
- Weeks 11-16: UI & Automation ✅ *Original plan included this*

### What We're Adding (New Phases 4-5)

**NEW Phase 4 (Week 5):** Validation Framework
- Build backtesting infrastructure
- Paper trade 50+ games with real data
- Measure accuracy (RMSE, hit rate, CLV)
- **Gate:** Must complete before proceeding to Phase 5

**NEW Phase 5 (Week 6):** Calibration & Optimization
- Diagnose accuracy issues if any
- Adjust weights, multipliers, formulas based on data
- Re-test and iterate
- **Gate:** Must achieve "Strong Success" metrics before proceeding to dashboard

**Rationale:** Building a beautiful dashboard for an unvalidated model is premature optimization. We need to know the model works BEFORE investing in UI/UX.

---

## 1. The "Real Talk" Product Audit (Unchanged)

**Verdict:** **STRONG BUY** (with validation requirement added)

The market gap, value proposition, and innovation check remain the same. The addition of validation doesn't change the strategic vision - it strengthens execution.

**Updated Warning:**
- **Complexity Creep:** Still the #1 risk
- **Novice Trap:** Building features without proving core math works
- **Solution:** **Validation BEFORE polish**

---

## 2. Math & Model Feasibility Review (Unchanged)

**Status:** **Green Light** (with empirical validation required)

The mathematical foundation is sound:
- ✅ Poisson Simulations
- ✅ Usage Vacuum Theory
- ✅ Weighted Heuristics (defer ML to later)

**New Requirement:** Prove these algorithms work through backtesting before claiming "pro-level accuracy."

---

## 3. The Toolkit (Unchanged)

**Core Tech Stack:**
- Python + pandas + numpy
- SQLite (single file database)
- Streamlit (web dashboard)
- GitHub + Render/Streamlit Cloud (deployment)

**New Addition:**
- **Backtesting Framework:** Custom Python script to validate historical accuracy

---

## 4. THE REVISED 8-WEEK GAME PLAN

### Phase 1: The Foundation (Source of Truth) — Weeks 1-2 (ENHANCED)

**Goal:** Build robust database, integrate modules, run full pipeline end-to-end

#### Week 1: Security & Infrastructure
1. **CRITICAL SECURITY FIX (Day 1):** ✅ COMPLETE
   - Create .env file
   - Update .gitignore
   - Refactor config.py

2. **Migrate Historical Data (Days 2-3):** ✅ COMPLETE
   - Move 368K-line `ludi_history_db.json` to SQLite
   - Create `player_game_logs` table with proper indexing
   - **Status:** 10,840 records migrated to 2.8MB DB

3. **Repository Setup (Day 4):** ✅ COMPLETE
   - Create private GitHub repo `ludi_lens_v2`
   - Commit all code with protected `.env`
   - Add README with setup instructions

#### Week 2: Module Integration
4. **Connect Modules A-G (Days 5-7):**
   - Test each module independently first
   - Verify API connections (The-Odds-API, Tank01, Google)
   - Run `python main.py` and debug import errors

5. **First End-to-End Test (Days 8-9):**
   - Run full pipeline on single game
   - Verify data flows: Gatekeeper → Oracle → Yak → Calibrator → Reporter
   - Generate first `daily_briefing.txt`

6. **Add Logging Framework (Day 10):**
   - Implement `logging.basicConfig`

**Week 2 Success Criteria:**
- ✅ main.py runs without crashing
- ✅ Generates projections for all players in slate
- ✅ daily_briefing.txt contains readable recommendations
- ✅ Log file shows no critical errors

---

### Phase 2: The Logic (The Engine) — Weeks 3-4 (REFINED)

**Goal:** Optimize performance, add error handling, generate consistent daily briefings

#### Week 3: Performance Optimization
1. **Simulation Tuning (Days 11-13):**
   - Current: 25,000 iterations per player
   - Test: 10,000 vs 25,000 - does accuracy improve?
   - Goal: Reduce runtime from ~5 min to <2 min per slate

2. **Database Indexing (Day 14):**
   - Add indexes on player_id, game_date
   - Test query performance (L5, L10 averages)

3. **Caching Strategy (Days 15-16):**
   - Cache referee data (refresh daily, not every run)
   - Cache team archetypes (static for season)
   - Cache injury status (15-minute TTL)

#### Week 4: Robustness & Error Handling
4. **Add Try/Except Blocks (Days 17-18):**
   - Wrap API calls with retry logic (max 3 attempts)
   - Graceful degradation if one module fails
   - Email/log critical errors

5. **Edge Case Testing (Day 19):**
   - Empty slate (no games scheduled)
   - API timeout scenarios
   - Player with no historical data

6. **Historical Run (Days 20-21):**
   - Run pipeline on 10 past dates
   - Store projections in database
   - Prepare data for Phase 4 validation

**Week 4 Success Criteria:**
- ✅ Pipeline runs on 10 consecutive dates without manual intervention
- ✅ Runtime <2 minutes per slate
- ✅ Projections stored in database for all dates
- ✅ Ready for historical comparison

---

### **NEW PHASE 4: Validation Framework — Week 5 (CRITICAL)**

**Goal:** Prove the model has predictive power through rigorous backtesting

#### Week 5: Build Backtesting Infrastructure

**Day 22: Schema Design**
Create `backtesting_results` table for projections vs actuals.

**Days 23-24: Backtesting Script**
Create `backtest_model.py` to calculate errors and hit rates.

**Days 25-26: Run Backtest & Analyze**
1. Execute on 50 past games (10 dates × 5 games avg)
2. Generate report with visualizations
3. **Review Results:**
   - Is RMSE < 10% for each stat?
   - Is hit rate > 52.4% overall?
   - Are high-edge bets performing better?

**Week 5 Success Criteria (GO/NO-GO DECISION):**

**Minimum Viable Accuracy:**
- ✅ RMSE < 15% for PTS/AST/REB (acceptable for personal use)
- ✅ Hit rate > 50% overall (better than random)
- ✅ Hit rate improves with edge threshold (validates edge calculation)

**Strong Success (Proceed to Phase 6 with confidence):**
- ✅ RMSE < 10% for PTS/AST/REB
- ✅ Hit rate > 52% overall
- ✅ Hit rate > 55% on 10%+ edge bets

**Failure (STOP, diagnose, refactor):**
- ❌ RMSE > 15%
- ❌ Hit rate < 50%
- ❌ No correlation between edge and hit rate

**If validation fails, do NOT proceed to Phase 6. Return to Phase 2 and fix the model.**

---

### **NEW PHASE 5: Calibration & Optimization — Week 6 (CONDITIONAL)**

**Goal:** Refine model based on backtest results, iterate until accuracy targets met

**This phase only runs if Week 5 shows weaknesses. If validation is strong, skip to Phase 6.**

#### Week 6: Diagnose & Fix Accuracy Issues

**Days 27-28: Root Cause Analysis**
- Which stats are most inaccurate?
- Are modifiers correct? (Pace, Fatigue, Defense)
- Is win probability mapping accurate?

**Days 29-30: Adjust & Retest**
- Update modifier weights in `config.py` or `module_e.py`
- Re-run simulations on same 50 historical games
- Compare new RMSE vs old RMSE

**Days 31-32: Final Validation Run**
- Run backtest on **new 25 games** (holdout set)
- Verify improvements hold on fresh data

**Week 6 Success Criteria:**
- ✅ RMSE < 10% on both training set (50 games) and test set (25 games)
- ✅ Hit rate > 52% on test set
- ✅ Model coefficients are justified by data, not arbitrary

---

### Phase 6: The Lens (The Dashboard) — Week 7 (MOVED FROM WEEK 5)

**Goal:** Build Streamlit web app to visualize validated projections

**Prerequisite:** Weeks 5-6 validation must be complete and successful. Do not build dashboard for unvalidated model.

#### Week 7: Streamlit Dashboard

**Days 33-35: Core Dashboard**
- Create `streamlit_app.py`
- Display "The Briefing" card view
- Display Diamond Plays (top 5 highest EV)
- Validate Metrics (show user model accuracy)

**Days 36-37: "Ask Ludi" Chat Interface (Optional)**
- Integrate Gemini API for Q&A (Natural Language to SQL)

**Days 38-39: Testing & Polish**
- Test on mobile (Streamlit is responsive)
- Add dark mode toggle (config.toml)
- Deploy to Streamlit Community Cloud

**Week 7 Success Criteria:**
- ✅ Dashboard loads projections from database
- ✅ User can see validation metrics (hit rate, RMSE)
- ✅ Deployed to public URL (streamlit.app/ludi_lens)

---

### Phase 7: Automation & Hosting — Week 8 (MOVED FROM WEEK 6)

**Goal:** Pipeline runs automatically every morning, no manual intervention

#### Week 8: GitHub Actions + Production Deployment

**Days 40-42: GitHub Actions Workflow**
- Create `.github/workflows/daily_pipeline.yml`
- Add GitHub Secrets (API keys)

**Days 43-44: Telegram Notifications (Optional)**
- Create `telegram_bot.py`
- Send morning briefing

**Days 45-46: Monitoring & Alerts**
- Error notifications
- UptimeRobot setup

**Days 47-48: Documentation & Handoff**
- Update README.md
- Create USER_GUIDE.md

**Week 8 Success Criteria:**
- ✅ Pipeline runs automatically at 9:00 AM daily
- ✅ Briefing posted to Telegram (if configured)
- ✅ Dashboard auto-refreshes with new data
- ✅ Documentation complete for handoff

---

## 5. Scaling Options & Reality Check (UPDATED)

### Option A: The "Personal Edge" (Weeks 1-8 Goal)

**Status:** **PRIMARY FOCUS** - All 8 weeks are dedicated to this

**Scope:**
- ✅ Runs locally or on free cloud tier
- ✅ Basic Player Props with Injury adjustments
- ✅ **VALIDATED accuracy through backtesting**
- ✅ Streamlit dashboard for visualization
- ✅ GitHub Actions automation

**Cost:** ~$0 (Free API tiers + Free hosting)

### Option B: The "Pro Tool" (Month 6+ Goal)

**Status:** **DEFERRED** until Option A proves profitable

**Recommendation:** Do NOT expand scope until you've proven the core model works in real-world usage.

---

## 11. Next Steps (How to Use This Plan)

### Today (Day 1):
1. Review this revised plan
2. Fix API key security (create .env file) ✅ DONE
3. Commit to 8-week timeline

### Week 1:
1. Follow checklist (GitHub repo, JSON → SQLite, module integration)
2. Get main.py running end-to-end
3. Generate first daily_briefing.txt

### Weeks 2-4:
1. Optimize performance
2. Run pipeline on historical dates
3. Prepare for validation

### Week 5 (Critical):
1. Build backtesting framework
2. Measure accuracy
3. **DECISION POINT:** Pass/Fail validation

***
