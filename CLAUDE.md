# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.
It is supplemental context only. `AGENTS.md` is the primary operating guide for Codex-style agent behavior.

## Instruction Precedence

When instructions conflict, use this order:
1. `AGENTS.md` (primary agent operating rules)
2. `ROADMAP.md` (current phase and priorities)
3. `CLAUDE.md` (supplemental project context)

## Project Overview

**Ludi Informatio v2.0** is an NBA analytics platform that generates betting recommendations for player props using Monte Carlo simulations, injury intelligence, and edge calculation with devigging.

- **Product Name**: Ludi Lens v2.0 (The Front Office War Room)
- **Engine**: S.A.V.A.G.E. Protocol (Hybrid Poisson/Normal Sim | Usage Vacuum)
- **Tech Stack**: Python + Streamlit + SQLite + GitHub Actions
- **Repository**: https://github.com/LudiInformatio/Ludi-Bot.git

---

## Project Context

See @ROADMAP.md for current tasks and priorities.
See @docs/ARCHITECTURE.md for system design and module reference.
See @docs/METHODOLOGY.md for betting edge calculations.
See @docs/STATUS_HISTORY.md for historical updates.
See @docs/TOOLS_GUIDE.md for task automation scripts and helpers.
See @best-practices/ for reusable patterns and lessons learned.

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

**Current NBA season is 2025-26.** Never use AI training data for current rosters, trades,
or injury status — it will be wrong. Players change teams, get injured, and return throughout
the season. The AI's knowledge cutoff predates this season's moves. Always verify against
`ludi.db` or a live API call before making any roster or injury assumption.

**This rule applies to mock scenarios and prompt examples too.** When writing or editing
example prompts, format templates, or test scenarios in `utils/claude_prompts.py` or
anywhere else — never hardcode a player's team from AI training memory. Either:
1. Query `ludi.db` first: `SELECT name, team FROM players WHERE name = '...';`
2. Use clearly generic placeholders: `[PLAYER]`, `[TEAM]`, `[BOS starter]`
3. Use `build_archetype_system_prompt(conn)` pattern — examples built from DB at runtime

**Multi-team trade paths must be accepted as-is from the database.** Players can have
offseason trades AND mid-season trades — `player_game_logs.team_abbreviation` is the
authoritative record. Example: Anfernee Simons (POR → BOS offseason, BOS → CHI mid-season
2025-26) — the database correctly shows BOS,CHI. Never question multi-team histories that
look "wrong" from training data memory. The API data is always right; training data is stale.

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
| I: Aggregator | `module_i_aggregator.py` | `LudiAggregator` (placeholder) |

---

## Project Identity

- **Colors**: Dark Navy #0F172A, Gold #FBBF24, Emerald #10B981
- **Voice**: Professional, Tactical, "Asset Management" (No "locks" or gambling slang)
- **Iconography**: IYKYK Elite Set (diamond, blueprint, pour, toast, counter-punch, frosty)

---

## API Configuration

| API | Tier | Purpose |
|-----|------|---------|
| The-Odds-API | PAID (20K/mo) | Game lines, player props |
| Tank01 | PAID (1K/day) | Rosters, injuries, box scores |
| Ball Don't Lie | GOAT ($39.99/mo) | Fallback odds, injuries, game logs |
| PBP Stats | FREE | Shot quality, WOWY data |

Environment variables in `.env` (see `.env.template` for full list):
- `ODDS_API_KEY`, `TANK01_KEY`, `BALLDONTLIE_KEY` (required)
- `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` (notifications)
- `GEMINI_API_KEY` (optional — Ask Ludi chatbot)
- `DEBUG_LOG`, `IS_PRODUCTION` (flags)

---

## Automation Schedule (GitHub Actions)

All workflows run on a self-hosted macOS runner. See `.github/workflows/` for details.

| Time (EST) | Workflow | Purpose |
|------------|----------|---------|
| 1:00 AM | `db_backup.yml` | Automated database backup |
| 3:00 AM | `data_sync.yml` | Sync game logs, WOWY, clutch, assists |
| 6:00 AM | `daily_reports.yml` | Work notes + bet summary |
| 7:00 AM | `wowy_sync.yml` | Daily WOWY sync |
| 9:00 AM | `daily_briefing.yml` | Morning Telegram cards |
| 9:30 AM | `referee_sync.yml` | Daily referee assignments |
| 10:00 AM | `daily_simulation_pipeline.yml` | Full pipeline run |
| 6:00 PM | `evening_slate_lock.yml` | Evening Telegram cards |
| 8:30 PM | `nightly_debrief.yml` | Settlement + daily P&L |
| 7:30-11:30 PM | `capture_closing_lines.yml` | CLV capture (5 runs/night) |
| Sundays | `ghost_protocol_sync.yml` | NBA.com tracking data (6hr sync) |
| Tuesdays | `weekly_validation.yml` | Backtest + drift detection |
| On failure | `claude-ops-hub.yml` | Auto-diagnosis of workflow failures |

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
- DuckDuckGo search in Module D can be rate-limited — use sparingly
- Module I (Aggregator) is placeholder code — not yet implemented
- Runner DB symlink: `actions-runner/.../ludi.db` → local project DB. Don't break the symlink.
- BDL team abbreviation mismatches: GS/NO/NY/PHO/SA vs our GSW/NOP/NYK/PHX/SAS — always normalize
- Always use correct class names (see Module Reference above)

---

## Custom Skills

This project has custom skills available:
- `/backtest` - Run validation suite and check model accuracy
- `/daily` - Daily pipeline health check
- `/sports-model` (alias: `/sma`) - Use `skills/sports-data-model-architect` for balanced audit-first data modeling + implementation support

---

## Resources

- **Roadmap**: @ROADMAP.md (tasks & priorities)
- **Architecture**: @docs/ARCHITECTURE.md (pipeline, schema, modules)
- **Methodology**: @docs/METHODOLOGY.md (edge calc, line shopping, CLV)
- **Status History**: @docs/STATUS_HISTORY.md (archived updates)
- **Production Handbook**: @docs/PRODUCTION_HANDBOOK.md
- **Best Practices**: `best-practices/` (API patterns, lessons learned, reusable templates)
  - **API Best Practices**: `best-practices/api/API_BEST_PRACTICES.md` (comprehensive guide)
  - **API Quick Reference**: `best-practices/api/API_QUICK_REFERENCE.md` (cheatsheet)
- **Tools Guide**: @docs/TOOLS_GUIDE.md (automation scripts, helpers)
- **Research**: `docs/research/` (competitive analysis, prompt engineering)
