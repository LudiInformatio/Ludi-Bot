# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**Ludi Informatio v2.0** is an NBA analytics platform that generates betting recommendations for player props using Monte Carlo simulations, injury intelligence, and edge calculation with devigging.

- **Product Name**: Ludi Lens v2.0 (The Front Office War Room)
- **Engine**: S.A.V.A.G.E. Protocol (Hybrid Poisson/Normal Sim | 5k Runs | Usage Vacuum)
- **Tech Stack**: Python + Streamlit + SQLite + GitHub Actions
- **Repository**: https://github.com/LudiInformatio/Ludi-Bot.git

---

## Project Context

See @ROADMAP.md for current tasks and priorities.
See @docs/ARCHITECTURE.md for system design and module reference.
See @docs/METHODOLOGY.md for betting edge calculations.
See @docs/STATUS_HISTORY.md for historical updates.

---

## Critical Data Rules

**NEVER use AI training data for NBA roster/player/trade knowledge.** The AI's training data is outdated and WILL produce incorrect results (wrong teams, missed trades, phantom transactions).

Instead, ALWAYS use these sources for current-season truth:
1. **`ludi.db` database** — `players` table (current rosters), `player_game_logs` (game-by-game team assignments), `player_canonical_ids` (ID mappings)
2. **Live APIs** — Tank01 (`RosterValidator`), Ball Don't Lie (`BDLClient`), PBP Stats
3. **`player_game_logs.team_abbreviation`** — Tracks which team a player played for on each game date (historical proof of trades)

**Examples of what NOT to do:**
- Do NOT assume which players were traded based on AI memory
- Do NOT hardcode trade lists from general knowledge
- Do NOT guess player team assignments — query the database or API

**The correct process for roster/trade operations:**
1. Query our database first (`players`, `player_game_logs`)
2. If needed, fetch LIVE data from Tank01 or BDL APIs
3. Compare API data vs database to detect changes
4. Never fill gaps with AI assumptions

---

## Quick Commands

```bash
# Activate environment
source .venv/bin/activate

# Run main pipeline
.venv/bin/python main.py

# Run integration test
.venv/bin/python test_pipeline.py

# Initialize database
.venv/bin/python database.py

# Test individual modules
python -c "from module_a import Gatekeeper; gk = Gatekeeper(); print(gk.fetch_live_slate())"
python -c "from module_d import LudiYak; print(LudiYak().get_injuries())"

# Send Telegram test
python -c "from utils.telegram_notifier import send_message; send_message('Test')"
```

---

## Database Management

**IMPORTANT:** `ludi.db` is NOT tracked in git to prevent merge conflicts.

**Architecture:**
- **Local Development:** Database managed locally with backup/restore workflow
- **CI/CD Workflows:** Database rebuilt via data sync (not restored from git)
- **Backups:** Automated daily backups at 4 AM EST via GitHub Actions

### Backup & Restore

**Create manual backup:**
```bash
bash scripts/backup_database.sh
```

**Restore from backup:**
```bash
# List available backups
bash scripts/restore_database.sh

# Restore specific backup
bash scripts/restore_database.sh archives/data/ludi.db.backup_YYYYMMDD_HHMMSS.gz
```

**List recent backups:**
```bash
ls -lht archives/data/ludi.db.backup_*.gz | head -10
```

### Why Database is Not in Git

**Problem:** Binary database files create merge conflicts that cause data loss
**Solution:** Local database + automated backups + data sync workflows
**Result:** No more merge conflicts, data is safe, CI/CD still works

**If you need to share database state:** Use backup files, not git commits

---

## Module Reference

| Module | File | Class Name |
|--------|------|------------|
| A: Gatekeeper | `module_a.py` | `Gatekeeper` |
| B: Engine | `module_b.py` | `print_sharp_box_score` |
| C: Oracle | `module_c.py` | `LudiOracle` |
| D: Yak | `module_d.py` | `LudiYak` |
| E: Calibrator | `module_e.py` | `LudiCalibrator` |
| F: Alchemist | `module_f.py` | `LudiReporter` |
| G: Zebras | `module_g.py` | `LudiRefEngine` |
| H: Historian | `module_h_historian.py` | `LudiHistorian` |
| X: Scenario | `module_x_scenario.py` | `ScenarioBuilder` |

---

## Project Identity

- **Colors**: Dark Navy #0F172A, Gold #FBBF24, Emerald #10B981
- **Voice**: Professional, Tactical, "Asset Management" (No "locks" or gambling slang)
- **Iconography**: IYKYK Elite Set (diamond, blueprint, pour, toast, counter-punch, frosty)

---

## Current Focus

**Phase:** Phase 5 - Production Deployment & Automation
**Status:** Phase 4 validated (60-day backtest, +0.56 pts mean error)
**Priority:** Automated pipeline, monitoring suite, weekly backtests

See @ROADMAP.md for detailed task list.

---

## API Configuration

| API | Tier | Purpose |
|-----|------|---------|
| The-Odds-API | PAID (20K/mo) | Game lines, player props |
| Tank01 | PAID (1K/day) | Rosters, injuries, box scores |
| PBP Stats | FREE | Shot quality, WOWY data |

Environment variables in `.env`:
- `ODDS_API_KEY`, `TANK01_KEY` (required)
- `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` (notifications)
- `DEBUG_LOG`, `IS_PRODUCTION`, `IS_SELF_HOSTED` (flags)

---

## Development Workflow

1. ALWAYS activate virtual environment before running code
2. ALWAYS check `.env` file exists with required API keys
3. Test modules individually before running full pipeline
4. Backup database before running migration scripts
5. Paper trade any model changes before deploying to production

---

## Known Gotchas

- Referee assignments require web scraping (can fail if NBA.com changes HTML)
- DuckDuckGo search in Module D can be rate-limited - use sparingly
- Module I (Aggregator) is placeholder code - not yet implemented
- Always use correct class names (see Module Reference above)

---

## Custom Skills

This project has custom skills available:
- `/backtest` - Run validation suite and check model accuracy
- `/daily` - Daily pipeline health check

---

## Resources

- **Roadmap**: @ROADMAP.md (tasks & priorities)
- **Architecture**: @docs/ARCHITECTURE.md (pipeline, schema, modules)
- **Methodology**: @docs/METHODOLOGY.md (edge calc, line shopping, CLV)
- **Status History**: @docs/STATUS_HISTORY.md (archived updates)
- **Production Handbook**: @docs/PRODUCTION_HANDBOOK.md
