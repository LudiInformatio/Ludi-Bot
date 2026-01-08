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
1. **CRITICAL SECURITY FIX (Day 1):**
   ```bash
   # Create .env file
   touch .env
   echo "ODDS_API_KEY=3c4cff00b16889e49fc6320ffb0690a8" >> .env
   echo "TANK01_KEY=b4ec1031f4msh80f4fc4cd874de4p17e5b7jsn8eeafd9da310" >> .env
   echo "GOOGLE_SEARCH_KEY=AIzaSyAly9xlQ6of5WLmHDyzGORokvcbc7cg-nA" >> .env
   echo "GOOGLE_SEARCH_CX=435db9cf0319e43db" >> .env
   echo "TELEGRAM_TOKEN=8190581794:AAEUVV88PupubJYcudiyRCuWCpgPVLlZ-ag" >> .env
   echo "TELEGRAM_CHAT_ID=8190581794" >> .env

   # Update .gitignore
   echo ".env" >> .gitignore
   echo "*.pyc" >> .gitignore
   echo "__pycache__/" >> .gitignore

   # Refactor config.py to load from .env
   # Install: pip install python-dotenv
   ```

2. **Migrate Historical Data (Days 2-3):**
   - Move 368K-line `ludi_history_db.json` to SQLite
   - Create `player_game_logs` table with proper indexing
   - Script: `migrate_json_to_sqlite.py` (optimize this)
   - **Validation:** Query should return results in <1 second

3. **Repository Setup (Day 4):**
   - Create private GitHub repo `ludi_lens_v2`
   - Commit all code with protected `.env`
   - Add README with setup instructions

#### Week 1 Continued: Module Integration (Days 5-7)
4. **Test Individual Modules (Days 5-6):**
   - Test Module A (Gatekeeper): Fetch odds from The-Odds-API
   - Test Module C (Oracle): Run Poisson simulations
   - Test Module D (Yak): Check injury intelligence & 15-min cache
   - Test Module E (Calibrator): Apply matchup adjustments
   - Test Module F (Alchemist/Reporter): Generate daily briefing
   - Test Module G (Zebras): Referee impact calculations
   - Test Module H (Historian): Database read/write operations
   - Test Module X (Scenario Builder): Injury scenario toggles

5. **Critical Verification Checks (Day 7):**
   - **Blowout Tax**: Verify Module F downgrades props in blowout scenarios
   - **Scenario Control**: Verify Module X UI allows manual "Player OUT" toggles
   - **Usage Redistribution**: Confirm usage vacuum math when star player excluded
   - Run `python main.py` end-to-end and debug integration issues
   - Generate first `daily_briefing.txt`

**Week 1, Days 5-7 Success Criteria:**
- ✅ All 9 modules import and run without crashing
- ✅ API calls return valid data (check rate limits)
- ✅ Simulations generate player projections
- ✅ Blowout Tax logic verified in Module F
- ✅ Scenario Control toggles function correctly
- ✅ Daily briefing file contains readable recommendations

---

#### Week 2: Integration & Logging (Days 8-14)
6. **First End-to-End Pipeline Test (Days 8-9):**
   - Run full pipeline on single game slate
   - Verify data flows: Gatekeeper → Oracle → Yak → Calibrator → Reporter
   - Debug any module communication issues

7. **Add Logging Framework (Day 10):**
   ```python
   import logging
   logging.basicConfig(
       level=logging.INFO,
       format='[%(asctime)s] %(levelname)s: %(message)s',
       filename='ludi_pipeline.log'
   )
   ```

8. **Add Play Classification Tags (Days 11-12):** *NEW*
   - Implement "BLUE CHIP" tag: Edge >10% AND WinProb >60%
   - Implement "CORE ASSET" tag: Edge >4% AND WinProb >55%
   - Implement "THE STEAL" tag: Edge >5% AND Line Diff >1.5 pts
   - Update Module F output to include classification tags

9. **Add Archetype Schema Foundation (Days 13-14):** *NEW*
   - Create `player_archetypes` table in database.py
   - Create `team_archetypes` table in database.py
   - Run one-time scout script to classify all 30 teams
   - Add offense_style/defense_style to team lookup

**Week 2 Success Criteria:**
- ✅ main.py runs without crashing on full slate
- ✅ Generates projections for all players in slate
- ✅ daily_briefing.txt contains BLUE CHIP/CORE ASSET tags
- ✅ Team archetypes populated (Pace & Space, Bully Ball, etc.)
- ✅ Log file shows no critical errors

---

### Phase 2: The S.A.V.A.G.E. Engine — Weeks 3-4 (ENHANCED)

**Goal:** Upgrade to production-grade Poisson simulations, implement archetype system, add tracking data

**Engine Name:** S.A.V.A.G.E. = **S**cenario **A**nalysis & **V**alue **A**ssessment **G**ame **E**ngine

#### Week 3: Simulation & Archetype Enhancement
1. **Upgrade to 2,500 Poisson Simulations (Days 15-16):**
   - Replace weighted averages with `numpy.random.poisson`
   - Target: 2% margin of error (optimal speed/accuracy balance)
   - Implement "fat tail" distribution for star player explosions
   - Add Coefficient of Variation (CV) calculation per player

2. **Player Archetype Classification (Days 17-18):** *NEW*
   - Fetch Synergy Play Type data from nba_api
   - Classify rebounding: "Warrior" vs "Vulture"
   - Classify defense: "Island", "Screen Navigator", "Drop Anchor"
   - Classify playmaking: "PnR Maestro", "Connector", "Transition Artist"
   - Populate `player_archetypes` table

3. **Implement "One Ball Rule" (Day 19):** *NEW*
   - Add negative correlation logic to simulations
   - If Giannis gets 15 rebounds in a sim run, Brook Lopez probability decreases
   - Enable accurate "PIVOT PLAY" correlation detection

4. **Referee Weekly Sync Enhancement (Day 20):** *NEW*
   - Basketball-Reference: Weekly personality profiles
   - NBAstuffer: Daily "Last 5 Games" recency data
   - Covers: Cross-reference O/U profitability trends
   - Add "Data Conflict" flag when sources disagree

#### Week 4: Robustness & Historical Run
5. **Add Try/Except Blocks (Days 21-22):**
   - Wrap API calls with retry logic (max 3 attempts)
   - Graceful degradation if one module fails
   - Email/log critical errors

6. **Add Tracking Data Integration (Days 23-24):** *NEW*
   - Fetch `PlayerDashPtPass` for Potential Assists
   - Fetch `PlayerDashPtReb` for Contested/Uncontested %
   - Run overnight batch job (not live) to avoid lag
   - Add `potential_assists`, `contested_reb_pct` columns

7. **Edge Case Testing (Day 25):**
   - Empty slate (no games scheduled)
   - API timeout scenarios
   - Player with no historical data
   - Back-to-back game fatigue tax

8. **Historical Run (Days 26-28):**
   - Run pipeline on 10 past dates
   - Store projections with BLUE CHIP/STEAL tags
   - Prepare data for Phase 4 validation
   - Document runtime performance

**Week 4 Success Criteria:**
- ✅ 2,500 Poisson simulations running per player
- ✅ Player archetypes populated for active roster
- ✅ "One Ball Rule" correlation working in sims
- ✅ Potential Assists/Rebounds data integrated
- ✅ Pipeline runs on 10 consecutive dates without manual intervention
- ✅ Runtime <2 minutes per slate
- ✅ Ready for historical comparison

---

### **NEW PHASE 4: Validation Framework — Week 5 (CRITICAL)**

**Goal:** Prove the model has predictive power through rigorous backtesting

#### Week 5: Build Backtesting Infrastructure

**Day 22: Schema Design**
Create `backtesting_results` table:
```sql
CREATE TABLE backtesting_results (
    id INTEGER PRIMARY KEY,
    test_date DATE,
    player_name TEXT,
    stat_category TEXT,  -- PTS, AST, REB, etc.

    -- Our Model
    projection_value REAL,
    projection_floor REAL,
    projection_ceiling REAL,

    -- Market
    line_value REAL,
    line_odds TEXT,  -- e.g., "-110"

    -- Actual
    actual_value REAL,

    -- Results
    edge_pct REAL,  -- (projection - line) / line
    hit BOOLEAN,  -- Did it go over the line?
    ev_pct REAL,  -- Expected value
    recommended BOOLEAN,  -- Did we recommend this bet?

    -- Metadata
    run_timestamp TIMESTAMP
);
```

**Days 23-24: Backtesting Script**
Create `backtest_model.py`:
```python
def backtest_historical_dates(start_date, end_date):
    """
    1. Load projections from database (Weeks 3-4 historical run)
    2. Load actual results from ludi_history_db.json
    3. Calculate errors and hit rates
    4. Store in backtesting_results table
    """
    results = []

    for date in date_range(start_date, end_date):
        projections = load_projections(date)
        actuals = load_actual_results(date)
        lines = load_market_lines(date)  # Historical odds if available

        for proj in projections:
            actual = find_matching_actual(actuals, proj.player, proj.stat)

            result = {
                'test_date': date,
                'player_name': proj.player,
                'stat_category': proj.stat,
                'projection_value': proj.value,
                'actual_value': actual.value,
                'error': abs(proj.value - actual.value),
                'pct_error': abs(proj.value - actual.value) / actual.value,
                'hit': (proj.value > proj.line) == (actual.value > proj.line)
            }
            results.append(result)

    return results

def calculate_metrics(results):
    """Calculate aggregate performance metrics"""
    metrics = {
        'rmse_pts': np.sqrt(np.mean([r['error']**2 for r in results if r['stat'] == 'PTS'])),
        'rmse_ast': np.sqrt(np.mean([r['error']**2 for r in results if r['stat'] == 'AST'])),
        'rmse_reb': np.sqrt(np.mean([r['error']**2 for r in results if r['stat'] == 'REB'])),
        'hit_rate': np.mean([r['hit'] for r in results]),
        'hit_rate_5pct_edge': np.mean([r['hit'] for r in results if r['edge_pct'] >= 5]),
        'hit_rate_10pct_edge': np.mean([r['hit'] for r in results if r['edge_pct'] >= 10]),
    }
    return metrics
```

**Days 33-34: Run Backtest & Analyze**
1. Execute on 50 past games (10 dates × 5 games avg)
2. Generate report with visualizations:
   - Error distribution by stat category
   - Hit rate by edge threshold
   - Calibration plot (projected prob vs actual outcomes)

3. **Review Results:**
   - Is RMSE < 10% for each stat?
   - Is hit rate > 52.4% overall?
   - Are high-edge bets performing better?

**Days 35: Add CLV Tracking Foundation** *NEW*
4. **Implement Closing Line Value (CLV) Tracking:**
   - Add `opening_line`, `closing_line` columns to backtesting_results
   - Calculate: `clv_pct = (closing_line - opening_line) / opening_line * 100`
   - CLV > 0 means you "beat the market" (even if bet loses)
   - Track CLV % as primary performance metric (not just W/L)

**Week 5 Success Criteria (GO/NO-GO DECISION):**

**Minimum Viable Accuracy:**
- ✅ RMSE < 15% for PTS/AST/REB (acceptable for personal use)
- ✅ Hit rate > 50% overall (better than random)
- ✅ Hit rate improves with edge threshold (validates edge calculation)
- ✅ CLV tracking schema implemented

**Strong Success (Proceed to Phase 6 with confidence):**
- ✅ RMSE < 10% for PTS/AST/REB
- ✅ Hit rate > 52% overall
- ✅ Hit rate > 55% on 10%+ edge bets
- ✅ CLV positive on >50% of bets

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
1. **Which stats are most inaccurate?**
   - If PTS projections are off: Check FGA volume simulation
   - If AST projections are off: Check usage vacuum distribution
   - If REB projections are off: Check archetype vs defense matchups

2. **Are modifiers correct?**
   - Pace factor (referee impact): Compare projected pace vs actual pace
   - Fatigue tax (B2B): Compare B2B games vs normal rest
   - Defense multipliers: Compare vs opponent vs league avg

3. **Is win probability mapping accurate?**
   - Current formula: `win_prob = 0.50 + (edge / 140)`
   - **Calibrate empirically:**
     ```python
     # Group backtests by edge bucket
     buckets = {
         '0-5%': [results where edge 0-5%],
         '5-10%': [results where edge 5-10%],
         '10-15%': [results where edge 10-15%],
     }

     # Calculate actual hit rate per bucket
     for bucket, results in buckets.items():
         actual_hit_rate = np.mean([r['hit'] for r in results])
         print(f"{bucket} edge → {actual_hit_rate*100:.1f}% actual hit rate")

     # Fit new curve to data
     from scipy.optimize import curve_fit
     def win_prob_function(edge, a, b):
         return 0.50 + (edge / a) ** b

     params, _ = curve_fit(win_prob_function, edges, actual_hit_rates)
     ```

**Days 29-30: Adjust & Retest**
4. **Implement Fixes:**
   - Update modifier weights in `config.py` or `module_e.py`
   - Re-run simulations on same 50 historical games
   - Compare new RMSE vs old RMSE

5. **Iterate:**
   - If RMSE improves: Great, proceed
   - If RMSE worsens: Revert changes, try different approach
   - Goal: Get to "Strong Success" criteria

**Days 31-32: Final Validation Run**
6. Run backtest on **new 25 games** (holdout set, not used in calibration)
7. Verify improvements hold on fresh data
8. Document final model parameters

**Week 6 Success Criteria:**
- ✅ RMSE < 10% on both training set (50 games) and test set (25 games)
- ✅ Hit rate > 52% on test set
- ✅ Model coefficients are justified by data, not arbitrary

**If still failing after Week 6, consider:**
- Simplifying the model (fewer modifiers, focus on volume projection)
- Consulting NBA analytics literature for better formulas
- Extending validation period (more games needed)

---

### Phase 6: The Lens (The Dashboard) — Week 7 (MOVED FROM WEEK 5)

**Goal:** Build Streamlit web app to visualize validated projections

**Prerequisite:** Weeks 5-6 validation must be complete and successful. Do not build dashboard for unvalidated model.

#### Week 7: Streamlit Dashboard

**Days 33-35: Core Dashboard**
1. **Create `streamlit_app.py`:**
   ```python
   import streamlit as st
   import pandas as pd
   from datetime import date

   st.set_page_config(page_title="Ludi Lens v2.0", layout="wide")

   # Sidebar
   st.sidebar.title("⚙️ Controls")
   selected_date = st.sidebar.date_input("Game Date", value=date.today())

   # Main Page - The Briefing
   st.title("📊 Ludi Informatio - Executive Briefing")

   # Load today's projections
   projections = load_daily_briefing(selected_date)

   # Display Diamond Plays (top 5 highest EV)
   st.subheader("💎 Diamond Plays (1.2u+)")
   for play in projections['diamond']:
       with st.expander(f"{play.player} - {play.stat} {play.projection}"):
           col1, col2, col3 = st.columns(3)
           col1.metric("Projection", f"{play.projection:.1f}")
           col2.metric("Line", f"{play.line:.1f}")
           col3.metric("Edge", f"{play.edge_pct:.1f}%", delta=play.edge_pct)

           st.write(f"**EV:** {play.ev_pct:.1f}% | **Units:** {play.units:.2f}")
           st.write(f"**Context:** {play.note}")

   # Validation Metrics (show user model accuracy)
   st.sidebar.subheader("📈 Model Performance")
   st.sidebar.metric("Overall Hit Rate", "54.2%", delta="2.2%")
   st.sidebar.metric("RMSE (PTS)", "8.3%")
   st.sidebar.metric("CLV+", "62%", delta="12%")
   ```

2. **Add Visualization (Altair Charts):**
   - Bell curve showing projection distribution
   - Historical accuracy chart (last 50 tracked bets)
   - Edge vs hit rate scatter plot

**Days 36-37: "Ask Ludi" Chat Interface (Optional)**
3. Integrate Gemini API for Q&A
4. Allow user to ask: "Why is Giannis projected 32 pts?"
5. Return SHAP-like explanation: "Pace: +3 pts, Matchup: +2 pts, Usage: +1 pt"

**Days 38-39: Testing & Polish**
6. Test on mobile (Streamlit is responsive)
7. Add dark mode toggle (config.toml)
8. Deploy to Streamlit Community Cloud

**Week 7 Success Criteria:**
- ✅ Dashboard loads projections from database
- ✅ User can see validation metrics (hit rate, RMSE)
- ✅ Deployed to public URL (streamlit.app/ludi_lens)

---

### Phase 7: Automation & Hosting — Week 8 (MOVED FROM WEEK 6)

**Goal:** Pipeline runs automatically every morning, no manual intervention

#### Week 8: GitHub Actions + Production Deployment

**Days 40-42: GitHub Actions Workflow**
1. **Create `.github/workflows/daily_pipeline.yml`:**
   ```yaml
   name: Ludi Daily Pipeline

   on:
     schedule:
       - cron: '0 9 * * *'  # 9:00 AM ET daily
     workflow_dispatch:  # Allow manual trigger

   jobs:
     run-pipeline:
       runs-on: ubuntu-latest

       steps:
       - name: Checkout code
         uses: actions/checkout@v3

       - name: Set up Python
         uses: actions/setup-python@v4
         with:
           python-version: '3.11'

       - name: Install dependencies
         run: |
           pip install -r requirements.txt

       - name: Run main pipeline
         env:
           ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }}
           TANK01_KEY: ${{ secrets.TANK01_KEY }}
         run: |
           python main.py

       - name: Commit results
         run: |
           git config user.name "Ludi Bot"
           git config user.email "ludi@example.com"
           git add daily_briefing.txt
           git commit -m "Daily briefing: $(date)"
           git push
   ```

2. **Add GitHub Secrets:**
   - Go to repo Settings → Secrets → Actions
   - Add all API keys from .env file

**Days 43-44: Telegram Notifications (Optional)**
3. **Create `telegram_bot.py`:**
   ```python
   import telegram

   bot = telegram.Bot(token=os.getenv('TELEGRAM_TOKEN'))

   def send_morning_briefing():
       briefing = open('daily_briefing.txt').read()
       bot.send_message(
           chat_id=os.getenv('TELEGRAM_CHAT_ID'),
           text=f"🏀 *Ludi Morning Briefing*\n\n{briefing}",
           parse_mode='Markdown'
       )
   ```

4. Add to GitHub Actions workflow (runs after main.py)

**Days 45-46: Monitoring & Alerts**
5. **Add error notifications:**
   - If pipeline fails, send Telegram alert
   - If hit rate drops below 50%, send warning

6. **Set up UptimeRobot:**
   - Ping Streamlit dashboard every 10 min
   - Prevents free tier from sleeping

**Days 47-48: Documentation & Handoff**
7. **Update README.md:**
   - Setup instructions
   - Architecture diagram
   - Validation results summary
   - Known limitations

8. **Create USER_GUIDE.md:**
   - How to read the briefing
   - What units mean (0.25u - 1.5u)
   - Bankroll management rules
   - Paper trading instructions

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

**Deliverables at Week 8:**
- Proven model with >52% hit rate
- Daily automated briefings
- Web dashboard
- Comprehensive documentation

**Verdict:** This is now a complete, production-ready personal tool.

---

### Option B: The "Pro Tool" (Month 6+ Goal)

**Status:** **DEFERRED** until Option A proves profitable

**New Features to Add Later (Not in 8 weeks):**
- Module R (Ledger): Bankroll tracking, CLV monitoring
- Module S (Scout): Beat writer monitoring with 30-min polling
- Module T (Telegram): Two-way bot with remote commands
- ML Layer: XGBoost/SHAP for feature importance
- Multi-sport expansion: WNBA, NFL props

**Cost:** ~$50-100/mo (Paid APIs + Dedicated hosting)

**Timeline:** Only pursue after 3 months of profitable betting with Option A

**Recommendation:** Do NOT expand scope until you've proven the core model works in real-world usage.

---

## 6. Success Metrics (REFINED)

### Week 5 Validation Targets

**Minimum Viable (Proceed to Week 6):**
- ✅ RMSE < 15% for PTS/AST/REB
- ✅ Hit rate > 50% overall
- ✅ Edge correlation exists

**Strong Success (Proceed to Week 7):**
- ✅ RMSE < 10% for PTS/AST/REB
- ✅ Hit rate > 52% overall
- ✅ Hit rate > 55% on 10%+ edge bets

**Exceptional (Build with confidence):**
- ✅ RMSE < 8%
- ✅ Hit rate > 54%
- ✅ Positive CLV on 70%+ of bets

### Week 8 Production Readiness

**Technical:**
- ✅ Pipeline runs daily without manual intervention
- ✅ Dashboard loads in <3 seconds
- ✅ No critical errors in logs for 7 consecutive days

**Accuracy:**
- ✅ Paper trading shows consistent performance (Week 9+ real-world test)
- ✅ Model doesn't degrade over time (monitor for drift)

**Documentation:**
- ✅ README, USER_GUIDE, API_DOCS complete
- ✅ Bankroll management rules documented
- ✅ Known limitations disclosed

---

## 7. Risk Management (UPDATED)

### Technical Risks

| Risk | Mitigation in Revised Plan |
|------|---------------------------|
| **Unvalidated Model** | ✅ Weeks 5-6 dedicated to validation |
| **API Rate Limits** | Caching strategy (Week 3) |
| **Security Breach** | .env migration (Week 1 Day 1) |
| **Performance Issues** | 368K JSON → SQLite (Week 1) |

### Execution Risks

| Risk | Mitigation in Revised Plan |
|------|---------------------------|
| **Scope Creep** | Strict 8-week timeline, defer Option B |
| **Validation Fails** | Week 6 calibration phase, can extend if needed |
| **Burnout** | 2 extra weeks reduces pressure |

### Financial Risks

| Risk | Mitigation in Revised Plan |
|------|---------------------------|
| **Betting Unvalidated Model** | HARD GATE: No real money until Week 5 passes |
| **False Confidence** | Require 200 paper bets after Week 8 before real money |

---

## 8. Implementation Checklist (8-Week Gantt Chart)

```
Week 1: Foundation (Days 1-7)
[x] Day 1:    Security fix (.env migration) ✅
[x] Day 2-3:  Migrate JSON to SQLite ✅
[x] Day 4:    Create GitHub repo ✅
[ ] Day 5-6:  Test individual modules (A-H, X)
[ ] Day 7:    Critical verification (Blowout Tax, Scenario Control)

Week 2: Integration & Classification (Days 8-14)
[ ] Day 8-9:   First end-to-end pipeline run
[ ] Day 10:    Add logging framework
[ ] Day 11-12: Add play classification tags (BLUE CHIP, STEAL) *NEW*
[ ] Day 13-14: Add archetype schema foundation *NEW*

**MILESTONE: Team archetypes populated, classification tags working**

Week 3: S.A.V.A.G.E. Engine Upgrade (Days 15-20)
[ ] Day 15-16: Upgrade to 2,500 Poisson simulations *NEW*
[ ] Day 17-18: Player archetype classification *NEW*
[ ] Day 19:    Implement "One Ball Rule" correlation *NEW*
[ ] Day 20:    Referee weekly sync enhancement *NEW*

Week 4: Tracking Data & Historical Run (Days 21-28)
[ ] Day 21-22: Add try/except blocks, error handling
[ ] Day 23-24: Tracking data integration (Potential Assists) *NEW*
[ ] Day 25:    Edge case testing (empty slate, timeouts, B2B)
[ ] Day 26-28: Historical run on 10 past dates

**GATE 1: Week 4 Complete → Proceed to Validation**

Week 5: Validation ⚠️ CRITICAL (Days 29-35)
[ ] Day 29:    Design backtesting schema
[ ] Day 30-31: Write backtest_model.py
[ ] Day 32-33: Run on 50 historical games
[ ] Day 34:    Analyze results (RMSE, hit rate)
[ ] Day 35:    Add CLV tracking foundation *NEW*

**GATE 2: Week 5 Validation → GO/NO-GO Decision**
- If PASS (>52% hit rate): Proceed to Week 6 or Week 7
- If FAIL (<50% hit rate): Extend Week 6 for deep refactoring

Week 6: Calibration & Alerts (Days 36-42)
[ ] Day 36-37: Root cause analysis (if needed)
[ ] Day 38-39: Adjust modifiers and retest
[ ] Day 40:    Add "Reverse Line Movement" alert *NEW*
[ ] Day 41-42: Validate on holdout set

**GATE 3: Week 6 Calibrated → Proceed to Dashboard**

Week 7: Dashboard (Days 43-49)
[ ] Day 43-45: Build Streamlit app ("The Front Office")
[ ] Day 46-47: Add visualizations (Market Pulse, The Radar)
[ ] Day 48-49: Deploy to Streamlit Cloud

Week 8: Automation & Documentation (Days 50-56)
[ ] Day 50-51: GitHub Actions workflow
[ ] Day 52-53: Telegram bot (optional)
[ ] Day 54-55: Documentation (README, USER_GUIDE, terminology.md) *NEW*
[ ] Day 56:    Launch! 🚀

**POST-LAUNCH: 200 paper bets before real money**
```

---

## 9. NEW: S.A.V.A.G.E. Engine Reference

**Full Name:** Scenario Analysis & Value Assessment Game Engine

### Core Components
| Component | Module | Description |
|-----------|--------|-------------|
| **Scenario** | Module X | Dynamic roster/injury scenarios |
| **Analysis** | Module E | Matchup and archetype evaluation |
| **Value** | Module F | Edge detection and EV calculation |
| **Assessment** | Module C | Confidence grading (Oracle) |
| **Game** | Module A | Sport-specific data (Gatekeeper) |
| **Engine** | Core | 2,500 Poisson simulations |

### Play Classification Tags
| Tag | Criteria | Action |
|-----|----------|--------|
| **BLUE CHIP** | Edge >10%, WinProb >60% | High allocation |
| **CORE ASSET** | Edge >4%, WinProb >55% | Standard allocation |
| **THE STEAL** | Edge >5%, Line Diff >1.5 | Value opportunity |
| **STRUCTURED** | Correlation value detected | SGP consideration |
| **PIVOT PLAY** | Negative correlation | Trade-off bet |

### Archetype Quick Reference
**Team Offense:** Pace & Space, Bully Ball, Heliocentric
**Team Defense:** Funnel (Drop), Swarm (Blitz), Switch Everything
**Player Rebounding:** Warrior (Contested), Vulture (Uncontested)
**Player Defense:** Island, Screen Navigator, Drop Anchor
**Player Playmaking:** PnR Maestro, Connector, Transition Artist

---

## 9. The "Real Talk" Commitment (Developer Contract)

**I commit to the following:**

1. ✅ **Week 1 Day 1:** Fix API key security (non-negotiable)
2. ✅ **Week 5:** Build validation framework (no shortcuts)
3. ✅ **Week 5 Gate:** If validation fails, extend Week 6 instead of proceeding
4. ✅ **No Real Money:** Until 200 paper bets show >52% hit rate
5. ✅ **No Scope Creep:** Option B features are OFF LIMITS until Month 6

**If I break these commitments:**
- Risk building a polished system that doesn't work
- Risk financial loss from unvalidated bets
- Risk wasted time on features instead of accuracy

---

## 10. Comparison: Old Plan vs New Plan

| Aspect | Original 6-Week Plan | Revised 8-Week Plan |
|--------|---------------------|---------------------|
| **Timeline** | 6 weeks | 8 weeks (+33%) |
| **Validation** | ❌ None | ✅ Weeks 5-6 dedicated |
| **Risk** | HIGH (blind faith in math) | MEDIUM (data-driven) |
| **Outcome** | Unknown if model works | Proven accuracy before polish |
| **Confidence** | "It should work" | "It does work (tested)" |
| **Industry Standard** | 40% of standard timeline | 50% of standard timeline |

**Key Difference:** The new plan treats accuracy as a prerequisite for UI, not an afterthought.

---

## 11. Next Steps (How to Use This Plan)

### Today (Day 1):
1. Review this revised plan
2. Fix API key security (create .env file)
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

### Weeks 6-8 (Conditional):
1. If Week 5 passes: Calibrate lightly → Build dashboard → Automate
2. If Week 5 fails: Deep refactoring → Retest → Then proceed

---

## FINAL NOTE: Why 8 Weeks Instead of 6

The original 6-week plan was **ambitious but incomplete**. It built a race car without testing the engine.

**The 2 extra weeks are not "delay" - they're insurance.**

By Week 8, you'll have:
- ✅ A validated model (not just projections, but proven accuracy)
- ✅ Confidence to use the system for real decisions
- ✅ Data showing where the model excels and where it struggles
- ✅ A foundation to build Option B (if profitable)

**8 weeks of validated work beats 6 weeks of unproven work.**

---

**Document Version:** 2.2 - Added Devigging Implementation
**Compiled By:** Claude Opus 4.5 (Post-Historical Context Review)
**Original Date:** January 4, 2026
**Last Updated:** January 6, 2026
**Status:** APPROVED - Week 1 Days 1-4 Complete ✅ | Devigging Added ✅
**Current Phase:** Week 1, Days 5-7 (Module Integration Testing)
**Engine Name:** S.A.V.A.G.E. Protocol (Scenario Analysis & Value Assessment Game Engine)
**Reference Doc:** See `original vision/more_relevant_history.md` for full project history

---

## CHANGELOG: January 6, 2026

### V2.2 - Devigging Implementation Added

**New Files Created:**
- `utils/__init__.py` - Utils package initializer
- `utils/devig.py` - Fair odds calculation utilities

**Files Modified:**
- `module_f.py` (V4.3 → V4.4) - Integrated devigged edge calculation

**What Changed:**
1. Edge calculation now removes bookmaker vig (~2-5%) to reveal TRUE edge
2. Module F accepts new prop format with odds: `{"line": 24.5, "odds_over": -115, "odds_under": -105}`
3. Backwards compatible with legacy format (line only, assumes -110/-110)
4. Added `_estimate_over_probability()` method using stat-specific variance
5. Win probability now uses model probability directly (more accurate)

**Impact:**
- Edge values will be ~3-5% HIGHER than before (vig was hiding true edge)
- More accurate EV calculations
- Better alignment with CLV tracking in Week 5 validation

**Example:**
```
Before (with vig):  Model 55% vs Raw 53.5% = 2.8% edge
After (devigged):   Model 55% vs Fair 51.1% = 7.6% edge
```
