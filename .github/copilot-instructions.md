# Ludi Informatio v2.0 - AI Coding Agent Instructions

## Project Overview

**Ludi Lens v2.0** is an NBA analytics platform for player prop betting using Monte Carlo simulations (5K iterations), injury intelligence, and edge calculation with devigging. The system runs a modular pipeline (Modules A-H + X) orchestrated by `main.py`, backed by SQLite (`ludi.db`), and automated via GitHub Actions + Telegram notifications.

**Engine**: S.A.V.A.G.E. Protocol (Hybrid Poisson/Normal Simulation with Usage Vacuum theory)  
**Current Phase**: Week 3 (Validation) → Week 6 (Dashboard Build)  
**Repository**: https://github.com/LudiInformatio/Ludi-Bot.git

---

## Architecture: Modular Sequential Pipeline

The system follows a **sequential data flow** where each module depends on the previous:

```
A (Gatekeeper) → D (Yak) → C (Oracle) → E (Calibrator) → F (Alchemist/Reporter)
     ↓ (referee data)      ↓ (injuries)   ↓ (sims)      ↓ (matchups)    ↓ (edges)
     G (Zebras)        X (Scenario)    H (Historian - database sync)
```

### Module Naming Convention (CRITICAL)

**Always use EXACT class names when importing modules** - old names will cause `ImportError`:

| Module | File | Class Name | Purpose |
|--------|------|------------|---------|
| A: Gatekeeper | `module_a.py` | `Gatekeeper` | Fetches odds/props from The-Odds-API (PAID) |
| B: Engine | `module_b.py` | `print_sharp_box_score()` | Display function for stats/trends |
| C: Oracle | `module_c.py` | `LudiOracle` | Monte Carlo simulator (5k runs, hybrid Poisson/Normal) |
| D: Yak | `module_d.py` | `LudiYak` | Injury intelligence (Tank01 + DuckDuckGo, 15min refresh) |
| E: Calibrator | `module_e.py` | `LudiCalibrator` | Archetype matchup modifiers, blowout tax |
| F: Alchemist | `module_f.py` | `LudiReporter` | Edge calculation with devigging, generates briefings |
| G: Zebras | `module_g.py` | `LudiRefEngine` | Referee impact scraping (NBA.com) |
| H: Historian | `module_h_historian.py` | `LudiHistorian` | Database sync (Tank01 historical data) |
| X: Scenario | `module_x_scenario.py` | `ScenarioBuilder` | Usage Vacuum "what-if" scenarios |

**Example imports**:
```python
from module_a import Gatekeeper              # ✅ Correct
from module_c import LudiOracle              # ✅ Correct
from module_e import LudiCalibrator          # ✅ Correct

# WRONG (old names - DO NOT USE):
from module_a import LudiGatekeeper          # ❌ ImportError
from module_c import LudiSimulator           # ❌ ImportError
```

---

## Core Concepts & Critical Logic

### 1. **Devigging (Module F v4.4+)**
**Purpose**: Removes bookmaker vig (overround) to calculate TRUE edge vs fair probability.

**Why it matters**: Without devigging, edge is understated by 3-5%. A 2.8% raw edge might be 7.6% true edge.

**Implementation**: Uses `utils/devig.py` with multiplicative method:
```python
from utils.devig import devig_multiplicative
fair_over, fair_under = devig_multiplicative(-110, -110)
true_edge = (model_prob - fair_over) / fair_over * 100
```

### 2. **Usage Vacuum Theory (Modules C + X)**
**Concept**: When a star player (>18% usage) is OUT, their shots (FGA), free throws (FTA), and turnovers (TOV) redistribute to teammates.

**Implementation**:
- Module X creates "WITHOUT [Player]" scenarios
- Module C redistributes usage percentage across remaining rotation
- Module F labels beneficiaries with `BENEFICIARY` tag in output

### 3. **Blowout Tax (Module E)**
**Problem**: Starters sit early in blowouts, killing volume props.

**Solution**: Sliding scale based on spread:
```python
if spread > 7.0:
    blowout_mult = 1.0 - ((spread - 7.0) * 0.015)
    # Example: 12-point spread = 0.925 multiplier (-7.5% volume)
```

### 4. **15-Minute Injury Sync (Module D)**
**Why 15 minutes**: NBA requires teams to report injuries 15 minutes before tipoff.

**Implementation**:
- Caches injury data for 15 minutes (`yak_cache.json`)
- Refreshes at 14:59 mark before games
- Nuance detection via DuckDuckGo for "late scratch", "minutes limit" keywords

### 5. **Archetype Matchup Matrix (Module E)**
**Concept**: Player style vs defensive scheme creates edges.

**Example exploits**:
- `STRETCH_BIG` vs `PAINT_PACK` → +15% 3PM/3PA (paint defenders leave shooters open)
- `SLASHER` vs `HACKERS` → +20% FTA (aggressive rim protection = more fouls)
- `RIM_RUNNER` vs `PERIMETER` → +30% OREB (small ball concedes size)

**Defensive schemes (2025-26)**:
- `PAINT_PACK`: OKC, BOS, DET, MIN, SAS, ORL
- `BLITZ`: HOU, TOR, MIA, PHX
- `PERIMETER`: GSW, DAL, NYK
- `FUNNEL`: WAS, ATL, CHI, UTA, SAC
- `HACKERS`: IND, CHA, POR

### 6. **Tag Classification System (Week 2)**
**Purpose**: Searchable tags for filtering, analysis, pattern recognition.

**4 Tag Categories**:
1. **ARCHETYPE** (1 per player): `STRETCH_BIG`, `SLASHER`, `SNIPER`, `RIM_RUNNER`, `BALL_HOG`, `GENERALIST`
2. **SCENARIO** (0-4 per player): `BENEFICIARY`, `USAGE_VACUUM`, `MINUTES_LIMIT`, `HOT_STREAK`
3. **MATCHUP** (1 per game): `vs_PAINT_PACK`, `vs_BLITZ`, `vs_PERIMETER`, `vs_FUNNEL`, `vs_HACKERS`, `vs_NEUTRAL`
4. **MARKET** (0-n per bet): `CORRELATED_SGP` (2+ high-unit bets ≥1.2u in same game)

**Implementation**: `utils/tag_classifier.py` (singleton pattern)  
**Storage**: JSON array in SQLite `bet_recommendations.tags` column

---

## Database Schema (ludi.db)

**Key Tables**:
- `player_game_logs` (10,840+ records): Historical box scores with ALL stats (PTS, REB, AST, FGA, FG3A, FTA, etc.)
- `players` (505 records): Current roster with archetypes, usage, team
- `games` (496 records): Results with pace, referee_crew, scores
- `bet_recommendations`: Model output with tags, edge, EV, unit sizing
- `bet_daily_summaries`: P&L tracking (win rate, ROI, units)

**Performance Indexes**:
- `idx_player_game_logs_player_date` (composite for fast player queries)
- `idx_player_game_logs_game_date` (date-range filtering)

**Database Access Pattern**:
```python
import sqlite3
conn = sqlite3.connect("ludi.db")
cursor = conn.cursor()
cursor.execute("SELECT AVG(pts), AVG(minutes) FROM player_game_logs WHERE player_id = ? AND game_date >= date('now', '-30 days')", (player_id,))
```

---

## Development Workflows

### Environment Setup
```bash
# Activate virtual environment (ALWAYS required)
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure API keys (create .env from template)
cp .env.template .env
# Edit .env: ODDS_API_KEY, TANK01_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID required
```

### Running the System
```bash
# Main pipeline (orchestrates all modules)
python main.py

# Target specific teams (for testing)
python main.py --teams CLE SAC PHX

# Test full pipeline (validates end-to-end)
python test_pipeline.py

# Test single module
python -c "from module_a import Gatekeeper; gk = Gatekeeper(); gk.fetch_live_slate()"
```

### Database Operations
```bash
# Inspect database
python inspect_db.py

# Backup before migrations
cp ludi.db ludi.db.backup_$(date +%Y%m%d_%H%M%S)

# Migrate JSON to SQLite (one-time)
python migrate_json_to_sqlite.py

# Query directly
sqlite3 ludi.db "SELECT COUNT(*) FROM player_game_logs;"
```

### API Monitoring
```bash
# View real-time API usage
cat api_usage_log.json | python -m json.tool

# Paid Tier Limits (check .env):
# - ODDS_API_KEY: 20,000 requests/month
# - TANK01_KEY: 1,000 requests/day
```

---

## Automation (GitHub Actions)

**Daily Schedule (EST)**:
- **3:00 AM**: Data sync (`data_sync.yml`) - Module H fetches historical games, syncs to DB
- **4:00 AM**: Tracking sync (`tracking_sync.yml`) - NBA API player tracking backfill
- **5:00 AM**: Morning briefing (`daily_briefing.yml`) - PM Bot sends "The Vision" + Settlement P&L
- **6:00 AM**: Daily reports (`daily_reports.yml`) - Bet summary table
- **10:00 AM**: Visual morning brief (Top 5 plays with PNG cards)
- **6:00 PM**: Evening lock (`evening_slate_lock.yml`) - Visual game notes
- **8:00 PM**: Nightly debrief (`nightly_debrief.yml`) - PM Bot sends "The Wins"

**Manual Trigger**: All workflows support `workflow_dispatch` for testing.

**Environment Secrets Required**:
- `ODDS_API_KEY`, `TANK01_KEY`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
- Set in GitHub repo: Settings → Secrets → Actions

---

## Telegram Integration

**Bot**: @CashingChips_bot (Ludi_Bot)

**Usage in code**:
```python
from utils.telegram_notifier import send_message, send_alert, send_daily_briefing

# Send formatted message (supports Markdown)
send_message("*Bold text* and _italic text_")

# Send alert
send_alert("API Warning", "80% of quota consumed")

# Send daily briefing (auto-splits >4096 chars)
briefing = reporter.generate_report(processed_slate)
send_daily_briefing(briefing)
```

**PM Bot (Project Manager Assistant)**:
- **Morning**: "The Vision" (💎), "The Blueprint" (📐), "The Intel" (🥃)
- **Nightly**: "The Wins" (🍾), "The Pivot" (🥊), "The Vibe" (🧊)
- **Assets**: Vector headers in `assets/` (V10 minimalist design)

---

## Testing Conventions

**Test files naming**: `test_*.py` (e.g., `test_pipeline.py`, `test_integration.py`)

**Testing pattern**:
```python
def test_pipeline():
    """End-to-end test: Gatekeeper → Oracle → Reporter"""
    # 1. Setup
    gate = Gatekeeper()
    oracle = LudiOracle()
    
    # 2. Fetch data
    games = gate.fetch_live_slate()
    
    # 3. Run simulations
    results = oracle.run_simulation_batch(scenarios)
    
    # 4. Validate
    assert len(results) > 0
    assert all('PTS' in r for r in results)
```

**Backtest files**: `backtest_*.py` (e.g., `backtest_archetypes.py`, `backtest_regression.py`)  
**Output**: CSV files stored as `regression_backtest_*.csv`

---

## API Integrations & Tier Configuration

**Paid APIs (CRITICAL - check .env)**:
- **The-Odds-API**: Game lines, player props (20K requests/month)
- **Tank01 (RapidAPI)**: Historical stats, live rosters (1K requests/day)

**Retry Logic**: All API calls use `@retry_with_backoff(max_attempts=3, backoff=2.0)` decorator from `utils/api_helpers.py`

**Monitoring**: `utils/api_monitor.py` logs usage to `api_usage_log.json`, sends Telegram alerts at 80% quota

---

## Design & Brand Identity

**Brand Voice**: Professional, tactical, "asset management" (NOT gambling slang)  
**Color Palette**:
- Dark Navy: `#0F172A`
- Gold: `#FBBF24`
- Emerald: `#10B981`
- Moleskine Cream: `#FDFBF7` (visual cards background)

**Logo**: Ludi Wreath Seal (Navy, transparent background)  
**Typography**: Arimo (Sans) + Tinos (Serif)

**Iconography (IYKYK Elite Set)**:
- 💎 Vision (Sharp Insight)
- 📐 Blueprint (The Playbook)
- 🥃 Intel (Straight Truth)
- 🍾 Wins (Celebration)
- 🥊 Pivot (Adjustments)
- 🧊 Vibe (Stay Composed)

**Visual Reporting**: PNG cards generated via `utils/render_full_report.py` (Pillow + Pilmoji)

---

## Code Style & Conventions

**Imports**:
```python
# Standard library first
import sys, os, time, logging
from datetime import datetime

# Third-party
import pandas as pd
import numpy as np
import requests

# Local modules
import config
from module_a import Gatekeeper
from utils.telegram_notifier import send_message
```

**Logging**:
```python
import logging
logging.basicConfig(level=logging.INFO, format="[LUDI-CORE] %(message)s")
logging.info("✅ Module initialized")
```

**Error Handling**: Always wrap API calls in try/except with logging:
```python
try:
    response = requests.get(url, params=params)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    logging.error(f"API Error: {e}")
    return None
```

**Data Structures**: Use dictionaries for player profiles, DataFrames for aggregation:
```python
player = {
    'PLAYER_NAME': 'Damian Lillard',
    'TEAM_ABBREVIATION': 'MIL',
    'PTS': 25.3, 'MIN': 35.2, 'base_usg': 0.28
}
```

---

## Common Gotchas

1. **Module imports**: Use exact class names (`Gatekeeper`, not `LudiGatekeeper`)
2. **API keys**: Always load from `.env`, never hardcode
3. **Database connections**: Always close connections (`conn.close()`)
4. **Timezone handling**: All times stored in EST (`pytz.timezone('US/Eastern')`)
5. **Team abbreviations**: Use 3-letter codes (PHX not PHO, CHA not CHO)
6. **Devigging**: Always devig odds before edge calculation (Module F requirement)
7. **Tag storage**: Use `json.dumps(tags)` before SQLite insertion

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `main.py` | Orchestrator (entry point) |
| `config.py` | API keys, feature flags, tier limits |
| `database.py` | Schema initialization |
| `requirements.txt` | Dependencies (numpy, pandas, requests, etc.) |
| `utils/devig.py` | Vig removal (multiplicative method) |
| `utils/tag_classifier.py` | Tag assignment singleton |
| `utils/pm_bot.py` | Project Manager AI briefings |
| `config/daily_locks.json` | Target game filtering config |
| `.github/workflows/data_sync.yml` | Automated daily sync |

---

## Documentation Hierarchy

**For architecture questions**: Read [CLAUDE.md](CLAUDE.md) (857 lines - comprehensive project history)  
**For implementation plan**: Read [implementation_plan_REVISED_8WEEK.md](implementation_plan_REVISED_8WEEK.md)  
**For referee audit**: Read [REFEREE_NOMENCLATURE_AUDIT.md](REFEREE_NOMENCLATURE_AUDIT.md)  
**For quick start**: Read [README.md](README.md) (basic commands)

---

**Last Updated**: January 15, 2026  
**Phase**: Week 3 (Validation) → Week 6 (Dashboard Build)  
**Status**: Production-ready, 73,232 lines of code across 9 modules
