# Ludi Bot - Week 3 Startup Prompt: Validation Phase

## Project Overview
**Project**: Ludi Informatio v2.0 - NBA Analytics Platform for betting recommendations
**Repository**: https://github.com/LudiInformatio/Ludi-Bot.git
**Working Directory**: /home/mnprice86/ludi_bot
**Owner Role**: Product visionary with business acumen (novice coder)
**Your Role**: PM / Consultant / Personal Assistant / Tutor

---

## Project Genesis & Vision

**What is Ludi Informatio?**
An NBA player props betting recommendation system that uses Monte Carlo simulations, injury intelligence, and edge calculation to identify profitable betting opportunities. The system is designed to:

1. **Ingest live odds** from The-Odds-API (20K requests/month paid tier)
2. **Fetch real-time injuries** from Tank01 API (1K requests/day paid tier)
3. **Run projections** using Poisson simulations (25,000 iterations per player)
4. **Apply matchup adjustments** based on player archetypes vs defensive schemes
5. **Calculate TRUE edge** by devigging bookmaker odds (removing vig)
6. **Generate recommendations** with tiered unit sizing (0.25u to 1.5u)

**Product Names**:
- **Ludi Lens**: Dashboard Interface (Week 5-6)
- **S.A.V.A.G.E. Protocol**: Scenario Analysis & Value Assessment Game Engine

---

## 8-Week Development Plan

| Week | Phase | Status |
|------|-------|--------|
| 1 | Module Implementation (A-H, X) | ✅ COMPLETE |
| 2 | Logging, Classification, Automation | ✅ COMPLETE (Day 6) |
| 3 | Validation & Backtesting | 🎯 CURRENT |
| 4-5 | Calibration & Tuning | Pending |
| 6-7 | Dashboard Development | Pending |
| 8 | Production Deployment | Pending |

---

## What's Been Built (73,232 lines of code)

### Module Architecture
```
Tank01 API → Module A (Gatekeeper) → Module D (Yak/Injuries)
                     ↓
              Module B (Engine/Historical)
                     ↓
              Module C (Oracle/Simulations)
                     ↓
              Module E (Calibrator/Matchups)
                     ↓
              Module F (Alchemist/Edge Calc) → Daily Briefing
                     ↓
              utils/bet_logger.py → ludi.db (SQLite)
```

### Module Details
| Module | File | Purpose |
|--------|------|---------|
| A | `module_a.py` | Gatekeeper - Fetches odds from The-Odds-API |
| B | `module_b.py` | Engine - Historical analysis, hot streaks |
| C | `module_c.py` | Oracle - Monte Carlo Poisson simulations |
| D | `module_d.py` | Yak - Injury intelligence (15-min cache) |
| E | `module_e.py` | Calibrator - Archetype matching, defense schemes |
| F | `module_f.py` | Alchemist - Edge calculation, devigging, reporting |
| G | `module_g.py` | Zebras - Referee pace impact |
| H | `module_h_historian.py` | Historian - Database sync from Tank01 |
| X | `module_x_scenario.py` | Scenario Builder - "What-if" injury toggles |

### Key Innovations
1. **Devigging** - Removes bookmaker vig to calculate TRUE edge (not raw edge)
2. **Usage Vacuum Theory** - Redistributes volume when star players are OUT
3. **Blowout Tax** - Reduces volume projections when spread > 7 points
4. **8-Archetype System** - BALL_HOG, SLASHER, STRETCH_BIG, RIM_RUNNER, SNIPER, TWO_WAY_WING, FACILITATOR, GENERALIST
5. **Matchup Modifiers** - Archetype bonuses vs different defensive schemes

---

## Week 2 Day 6 Accomplishments (Just Completed)

### ✅ Data Sync
- Database updated: 10,840 → 12,108 game logs (+1,268 records)
- Most recent game: January 8, 2026
- Fixed Module H to include `GAME_ID` in Tank01 records
- Fixed migration script for None matchup handling

### ✅ GitHub Actions Automation
- New workflow: `.github/workflows/data_sync.yml`
- Schedule: Daily at 3am EST (8am UTC)
- Auto-fetches Tank01 → migrates → commits → pushes
- GitHub secrets configured: `TANK01_KEY`, `ODDS_API_KEY`
- Test run: **SUCCESS** ✓

### ✅ Archetype Population
- Script: `populate_archetypes.py`
- Classified 774 players using Module E's 8-archetype system
- Distribution: GENERALIST (79%), BALL_HOG (7%), TWO_WAY_WING (5%), RIM_RUNNER (3%), SNIPER (3%), STRETCH_BIG (2%), SLASHER (2%)

### ✅ GitHub CLI Setup
- Installed `gh` CLI v2.83.2
- Authenticated as LudiInformatio
- Can now trigger workflows: `gh workflow run data_sync.yml`

---

## Database State

**File**: `ludi.db` (SQLite, ~3MB)

| Table | Records | Purpose |
|-------|---------|---------|
| player_game_logs | 12,108 | Historical box scores |
| players | 944 | Player roster with archetypes |
| games | 1,052 | Game metadata (home/away teams) |
| bet_recommendations | ~100+ | Logged bet recommendations |
| bet_daily_summaries | 10+ | Daily bet summaries |

**Data Range**: October 2025 → January 8, 2026

---

## API Configuration

**Paid Tier Keys** (in `.env`):
- `ODDS_API_KEY`: 9aa84b1836e565ec82161558d5cc948b (20K/month)
- `TANK01_KEY`: b4ec1031f4msh80f4fc4cd874de4p17e5b7jsn8eeafd9da310 (1K/day)
- `ODDS_API_TIER`: paid
- `TANK01_TIER`: paid

**Current Usage**: ~860 Tank01 credits remaining today (used ~140 for data sync)

---

## Week 3 Mission: Validation Phase

### Critical Gate (MUST ACHIEVE)
Before proceeding to dashboard development, the model MUST prove:

| Metric | Target | Purpose |
|--------|--------|---------|
| RMSE | < 10% | Projection accuracy for PTS/AST/REB |
| Overall Hit Rate | > 52% | Win rate on all recommendations |
| 10%+ Edge Hit Rate | > 55% | Win rate on high-confidence bets |
| CLV (Closing Line Value) | > 50% positive | Beating market movement |

**If metrics fail**: Do NOT proceed to dashboard. Extend Week 5 for calibration tuning.

---

## Recommended Week 3 Tasks

### Day 1-2: Backtest Framework Setup
1. Create `backtester.py` script
2. Select 50+ historical games from database
3. Implement replay logic: feed historical odds → run pipeline → compare to actual results
4. Define metrics calculation (RMSE, hit rate, CLV)

### Day 3-4: Run Backtests
1. Execute backtester on historical games
2. Log predictions vs actuals
3. Calculate aggregate metrics
4. Identify patterns in wins/losses

### Day 5-7: Analysis & Calibration
1. Analyze which archetypes over/underperform
2. Tune matchup modifiers if needed
3. Adjust edge thresholds if hit rate is off
4. Document findings for Week 4

---

## Key Files to Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Comprehensive project documentation |
| `implementation_plan_REVISED_8WEEK.md` | Full 8-week roadmap |
| `UPDATED_STATUS_AND_NEXT_STEPS.md` | Current status tracking |
| `test_pipeline.py` | Integration test (runs 3-game simulation) |
| `module_f.py` | Edge calculation & recommendation generation |
| `module_e.py` | Archetype classification & matchup logic |
| `utils/bet_logger.py` | Bet logging to SQLite |

---

## Communication Style

- **Format**: Use ★ Insight blocks for technical explanations
- **Tone**: Friendly-but-professional, "get it done" mindset
- **Icons**: 💎 (Vision), 📐 (Blueprint), 🥃 (Intel), 🍾 (Wins), 🥊 (Pivot), 🧊 (Vibe)
- **Updates**: Concise summaries, structured markdown, emoji anchors
- **Tutorials**: Explain technical decisions and trade-offs clearly

---

## Quick Start Commands

```bash
# Activate environment
cd /home/mnprice86/ludi_bot
source venv/bin/activate

# Check database status
./venv/bin/python -c "import sqlite3; conn = sqlite3.connect('ludi.db'); c = conn.cursor(); c.execute('SELECT MAX(game_date), COUNT(*) FROM player_game_logs'); print(c.fetchone())"

# Run integration test
./venv/bin/python test_pipeline.py

# Trigger data sync manually
gh workflow run data_sync.yml

# Check workflow status
gh run list --workflow=data_sync.yml --limit 3
```

---

## Your First Steps

1. **Read CLAUDE.md** - Full project context and conventions
2. **Check database freshness** - Should show Jan 8-9, 2026
3. **Review test_pipeline.py** - Understand current integration test structure
4. **Propose backtest framework design** - Create implementation plan for validation
5. **Ask clarifying questions** - Before starting Week 3 work

---

## Questions to Consider

1. How should we handle games where odds data is missing from our historical records?
2. Should the backtester simulate real-time conditions (injury updates, line movement)?
3. What's the minimum sample size needed for statistically significant validation?
4. Should we weight recent games more heavily than older games?
5. How do we handle players who changed teams mid-season?

---

Ready to begin Week 3: Validation Phase?
