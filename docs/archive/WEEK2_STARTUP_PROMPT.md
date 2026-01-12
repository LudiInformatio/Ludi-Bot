# Week 2 Startup Prompt - Ludi Informatio v2.0

**Created:** January 7, 2026, 7:00 PM ET
**For:** New Terminal Window/Session
**Phase:** Week 2, Days 1-2 (Logging Framework)

---

## 📋 COPY THIS PROMPT TO NEW TERMINAL

```
I'm continuing work on the Ludi Informatio v2.0 NBA analytics platform. Week 1 is complete ✅ - all 9 modules validated with test_pipeline.py passing.

## Current Status (Jan 7, 2026, 7:00 PM ET)

**Week 1 Complete:**
- All 9 modules (A-H + X) production-ready: 73,688 lines
- test_pipeline.py: ✅ PASSED (3 games, 19 players, $0.1125 cost, 25% under budget)
- Diamond plays generated: 5 recommendations
- Database: 10,840 player game logs, 505 players
- API: The-Odds-API (PAID 20K/mo), Tank01 (PAID 1K/day)
- GitHub: Updated with Week 1 completion commit

## Week 2 Goal: Logging Framework (Days 1-2)

I need to create a structured logging system for bet tracking and backtesting.

### Deliverables

**1. utils/bet_logger.py - BetLogger class**
- Log every recommendation with full context
- Write to both JSON (logs/bets/YYYY-MM-DD.json) and SQLite (bet_tracking.db)
- Schema: timestamp, game_id, player, team, market, line, odds, projection, edge, EV, units, tags, result fields

**2. bet_tracking.db - SQLite database**
Tables:
- `bets`: id, timestamp, game_date, player_name, team, market, bet_direction, line, odds, projection, true_edge, ev, units, result, actual_stat, profit_loss, clv
- `daily_summaries`: date, total_bets, total_units, wins, losses, pushes, win_rate, roi, clv_average

**3. Module F Integration**
- Modify module_f.py (LudiReporter) to call bet_logger.log_recommendation()
- Include full recommendation context in logs
- Auto-increment bet IDs

**4. backfill_test_results.py**
- Parse daily_briefing.txt from Week 1
- Convert to structured log format
- Insert into bet_tracking.db
- Tag as "test_run"

### Success Criteria
- [ ] utils/bet_logger.py created with BetLogger class
- [ ] bet_tracking.db created with schema
- [ ] Module F integrated with logger
- [ ] JSON logs written to logs/bets/
- [ ] SQLite database populated
- [ ] Query interface working
- [ ] <5% performance overhead

## Context Files

**Read these first:**
1. /home/mnprice86/ludi_bot/CLAUDE.md - Project overview & current status
2. /home/mnprice86/ludi_bot/UPDATED_STATUS_AND_NEXT_STEPS.md - Week 2 plan
3. /home/mnprice86/ludi_bot/WEEK1_DAY7_COMPLETION_REPORT.md - Week 1 results
4. /home/mnprice86/ludi_bot/daily_briefing.txt - Sample output to backfill
5. /home/mnprice86/ludi_bot/module_f.py - Reporter to integrate with

**Key Directories:**
- Project root: /home/mnprice86/ludi_bot
- Modules: module_a.py through module_h_historian.py
- Tests: test_pipeline.py, test_3_games.py
- Database: ludi.db (10,840 game logs), bet_tracking.db (to create)
- Utils: utils/ directory (create bet_logger.py here)

## Implementation Approach

**Step 1: Create BetLogger Class**
- Class structure with __init__, log_recommendation(), query methods
- JSON serialization for timestamps, player names, tags
- SQLite connection management
- Thread-safe logging (use locks if needed)

**Step 2: Design Database Schema**
- CREATE TABLE statements for bets and daily_summaries
- Indexes on game_date, player_name, market for fast queries
- Foreign key relationships if needed
- Validation constraints (CHECK for result values)

**Step 3: Integrate with Module F**
- Import bet_logger in module_f.py
- Call logger.log_recommendation() in generate_report()
- Extract all required fields from processed_slate
- Handle errors gracefully (log but don't crash pipeline)

**Step 4: Backfill Test Data**
- Parse daily_briefing.txt line by line
- Extract player, team, market, line, projection, units
- Create log entries with timestamp from test date
- Mark all as result='PENDING' (actual results unknown)

**Step 5: Test Queries**
- SELECT * FROM bets WHERE game_date = '2026-01-07'
- SELECT * FROM bets WHERE market = 'points' AND true_edge > 0.10
- SELECT AVG(units) FROM bets GROUP BY confidence_tier
- Verify JSON logs are parsable

## Example JSON Log Entry (from Week 1 test)

```json
{
  "timestamp": "2026-01-07T19:00:00Z",
  "game_id": "CHI_DET_20260107",
  "player": "Duncan Robinson",
  "team": "DET",
  "opponent": "CHI",
  "market": "points",
  "bet_direction": "over",
  "line": 17.5,
  "odds_over": -110,
  "odds_under": -110,
  "fair_prob_over": 0.512,
  "model_prob": 0.687,
  "projection": 10.52,
  "true_edge": 0.342,
  "ev": 0.4325,
  "units": 1.5,
  "confidence_tier": "DIAMOND",
  "tags": ["CORRELATED_SGP"],
  "referee_impact": 1.003,
  "spread": -7.5,
  "total": 221.5,
  "result": null,
  "actual_stat": null,
  "won": null,
  "clv": null
}
```

## Sample Daily Briefing to Backfill

From /home/mnprice86/ludi_bot/daily_briefing.txt:
- Duncan Robinson (DET) | OVER 17.5 PTS (Proj: 10.52, EV: +43.25%, 1.5u)
- Duncan Robinson (DET) | OVER 4.5 3PM (Proj: 2.58, EV: +43.25%, 1.5u)
- Ausar Thompson (DET) | OVER 3.5 AST (Proj: 1.79, EV: +43.25%, 1.5u)
- Matas Buzelis (CHI) | OVER 1.5 3PM (Proj: 2.78, EV: +43.25%, 1.5u)
- Tyrese Maxey (PHI) | OVER 8.5 AST (Proj: 6.15, EV: +43.25%, 1.5u)

## Commands

**Activate environment:**
```bash
cd /home/mnprice86/ludi_bot
source venv/bin/activate
```

**Create utils directory (if doesn't exist):**
```bash
mkdir -p utils logs/bets
```

**Test logger:**
```python
from utils.bet_logger import BetLogger
logger = BetLogger()
# ... test logging
```

**Query database:**
```bash
sqlite3 bet_tracking.db "SELECT * FROM bets LIMIT 5;"
```

## Expected Output

After completion:
- utils/bet_logger.py (~150-200 lines)
- bet_tracking.db (initialized with schema)
- logs/bets/2026-01-07.json (5 entries from test)
- backfill_test_results.py (~100 lines)
- Updated module_f.py (with logger integration)

## Performance Requirements

- Logging overhead: <5% of pipeline runtime (<3 seconds)
- JSON write: <100ms per recommendation
- SQLite write: <50ms per recommendation
- No blocking on file I/O (use buffering if needed)

## Error Handling

- If log file can't be written → print warning, continue
- If database can't be written → print error, save to JSON only
- If logger fails completely → don't crash pipeline, log to stderr

## Validation

After implementation, run:
1. test_pipeline.py (should still pass, now with logging)
2. Check logs/bets/2026-01-07.json exists
3. Query bet_tracking.db for 5 entries
4. Verify all fields populated correctly
5. Confirm no performance regression

## Next Steps After Completion

Week 2, Days 3-4: Play Classification Tags
- Create utils/tag_classifier.py
- Add archetype, scenario, matchup tags
- Integrate with Module F
- Update database schema

Ready to start! Please help me implement the logging framework.
```

---

## 🚀 QUICK START INSTRUCTIONS

1. **Open New Terminal**
2. **Copy entire block above** (between triple backticks)
3. **Paste into Claude Code**
4. **Claude will:**
   - Read context files
   - Create utils/bet_logger.py
   - Design bet_tracking.db schema
   - Integrate with Module F
   - Create backfill script
   - Test everything

---

## ⚙️ Alternative: Focused Task Prompt

If you want to work on specific components:

### Option A: Just Create BetLogger Class
```
Create utils/bet_logger.py with a BetLogger class that logs betting recommendations to both JSON (logs/bets/YYYY-MM-DD.json) and SQLite (bet_tracking.db).

See /home/mnprice86/ludi_bot/WEEK2_STARTUP_PROMPT.md for full spec and schema.

Log schema includes: timestamp, player, team, market, line, projection, edge, EV, units, tags, result fields.
```

### Option B: Just Create Database
```
Create bet_tracking.db with tables for bet tracking:
- bets table (id, timestamp, player, market, line, projection, edge, ev, units, result, etc.)
- daily_summaries table (date, total_bets, wins, losses, win_rate, roi, clv)

See /home/mnprice86/ludi_bot/WEEK2_STARTUP_PROMPT.md for complete schema.
```

### Option C: Just Integrate with Module F
```
Integrate bet logging into module_f.py (LudiReporter).

Import utils.bet_logger.BetLogger and call logger.log_recommendation() for each bet in generate_report().

See /home/mnprice86/ludi_bot/daily_briefing.txt for sample output format.
```

---

## 📊 Week 1 Achievements Reference

**For Context:**
- Integration test: test_pipeline.py (456 lines)
- Modules: 73,688 total lines
- Database: 10,840 player game logs
- API cost: $0.1125 per run (25% under budget)
- Diamond plays: 5 generated
- Runtime: ~45 seconds

**All files committed to GitHub:** https://github.com/LudiInformatio/Ludi-Bot.git

---

**Last Updated:** January 7, 2026, 7:00 PM ET
**Use In:** New terminal window/Claude session
**Phase:** Week 2, Days 1-2
