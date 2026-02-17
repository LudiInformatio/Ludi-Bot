# Ludi-Bot Architecture

This document describes the system architecture, module pipeline, and database schema for the Ludi-Bot NBA analytics platform.

---

## System Overview

**Ludi Informatio v2.0** is an NBA analytics platform that generates betting recommendations for player props using Monte Carlo simulations, injury intelligence, and edge calculation with devigging.

- **Product Name**: Ludi Lens v2.0 (The Front Office War Room)
- **Engine**: S.A.V.A.G.E. Protocol (Hybrid Poisson/Normal Sim | 5k Runs | Usage Vacuum)
- **Tech Stack**: Python + Streamlit + SQLite + GitHub Actions

---

## Modular Pipeline Design

The system uses a **sequential pipeline** where data flows through 9 specialized modules:

```
+-------------------------------------------------------------+
|  MODULE A: Gatekeeper (Odds Ingestion)                      |
|  - Fetches game lines, player props from The-Odds-API       |
|  - Integrates Module G (referee assignments)                |
|  - Outputs: Game slate, prop lines, referee factors         |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  MODULE B: Engine (Historical Analysis)                     |
|  - Loads player game logs from ludi.db                      |
|  - Calculates season avg, L5, L10 trends                    |
|  - Identifies "hot streaks" for reporting                   |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  MODULE C: Oracle (Monte Carlo Simulation)                  |
|  - 25,000 Poisson iterations per player                     |
|  - Simulates FGA, FG3A, FTA (volume)                        |
|  - Applies shooting %s, pace, fatigue, referee impact       |
|  - Outputs: Projected stats with confidence intervals       |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  MODULE D: Yak (Injury Intelligence)                        |
|  - 15-minute refresh cycle (aligns with NBA rules)          |
|  - Primary: Tank01 API, Secondary: BallDontLie              |
|  - Nuance detection via DuckDuckGo search                   |
|  - Classifies: OUT/DOUBTFUL/Q/PROBABLE/MINUTES_LIMIT        |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  MODULE E: Calibrator (Matchup Adjustments)                 |
|  - Assigns player archetype (SLASHER, STRETCH_BIG, etc)     |
|  - Applies matchup modifiers vs defense schemes             |
|  - Blowout tax (spread > 12.5 reduces volume)               |
|  - Pace modifiers (totals > 238 or < 218)                   |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  MODULE F: Alchemist (Edge Calculation & Reporting)         |
|  - Devigs bookmaker odds (removes vig)                      |
|  - Calculates TRUE edge vs fair probability                 |
|  - Filters: edge >= 5% threshold                            |
|  - EV & unit sizing (0.25u to 1.5u)                         |
|  - Classifies: DIAMOND/BLUE CHIP/CORE ASSET/THE STEAL       |
|  - Generates daily_briefing.txt                             |
+-------------------------------------------------------------+

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

---

## Module Class Names Reference

**Use these EXACT class names when importing modules:**

| Module | File | Correct Class Name | API Integration |
|--------|------|-------------------|-----------------|
| A: Gatekeeper | `module_a.py` | `Gatekeeper` | The-Odds-API (PAID) |
| B: Engine | `module_b.py` | `print_sharp_box_score` (function) | None (display layer) |
| C: Oracle | `module_c.py` | `LudiOracle` | None (pure math) |
| D: Yak | `module_d.py` | `LudiYak` | Tank01 + RotoWire (RSS) + DuckDuckGo |
| E: Calibrator | `module_e.py` | `LudiCalibrator` | None (matchup logic) |
| F: Alchemist | `module_f.py` | `LudiReporter` | Devigging (local) |
| G: Zebras | `module_g.py` | `LudiRefEngine` | NBA.com (scraping) |
| H: Historian | `module_h_historian.py` | `LudiHistorian` | Tank01 (PAID) |
| X: Scenario | `module_x_scenario.py` | `ScenarioBuilder` | None (usage vacuum) |

**Import Examples:**
```python
from module_a import Gatekeeper              # Correct
from module_c import LudiOracle              # Correct
from module_e import LudiCalibrator          # Correct

# WRONG (old names - DO NOT USE):
from module_a import LudiGatekeeper          # ImportError
from module_c import LudiSimulator           # ImportError
from module_e import LudiEvaluator           # ImportError
```

---

## Database Schema (ludi.db)

### Key Tables

| Table | Records | Description |
|-------|---------|-------------|
| `player_game_logs` | 10,840+ | Historical performance data with all stats |
| `players` | 505 | Current roster with archetypes and usage |
| `games` | 496+ | Game results with pace and referee crews |
| `odds` | Dynamic | Live market data from bookmakers |
| `simulations` | Archive | Model output archive for backtesting |
| `bet_recommendations` | Dynamic | Logged bets with tags |
| `referee_profiles` | 78 | Referee baseline stats |
| `player_synergy_playtypes` | 1,326 | Synergy playtype data |
| `player_shot_quality` | 499 | PBP Stats shot quality data |
| `team_lineups` | 10,669 | WOWY lineup data |

#### Player Classification Columns

| Column | Purpose | Values |
|--------|---------|--------|
| `archetype` | Primary role classification | GENERALIST, RIM_GUARDIAN, PERIMETER_HAWK, SNIPER_ELITE, etc. (19 types) |
| `defensive_tag` | Secondary overlay for poor defenders ONLY | WEAK_LINK or NULL |

**Important**: Defensive archetypes (RIM_GUARDIAN, PERIMETER_HAWK, SWITCHABLE_ANCHOR, HUSTLE_DISRUPTOR)
are stored in the `archetype` column, NOT `defensive_tag`. The `defensive_tag` column is reserved
exclusively for the WEAK_LINK designation (poor defenders who allow >1.5% worse FG% on >8% frequency).

**GENERALIST Measurement**: The <25% target applies to **active players** (21-day window), not all 503
players in database. Inactive players (injured, waived) default to GENERALIST but don't generate bets.

### Indexes for Performance
- `idx_player_game_logs_player_date` (composite index for fast player queries)
- `idx_player_game_logs_game_date` (for date-range queries)

---

## Critical Innovations

### 1. Usage Vacuum Theory (Module C + Module X)
**Concept**: When a star player is OUT, their usage (FGA, FTA, TOV) is redistributed to teammates.

**Implementation**:
- Module X creates "WITHOUT [Player]" scenarios
- Module C redistributes usage percentage across remaining rotation
- Module F labels beneficiaries in briefing output

### 2. Blowout Tax (Module F)
**Problem**: Starters sit early in blowouts, killing volume props.

**Solution**: Sliding scale reduction based on spread
```python
if spread > 7.0:
    blowout_mult = 1.0 - ((spread - 7.0) * 0.015)
    # Example: 12-point spread = 0.925 multiplier (-7.5% volume)
```

### 3. 15-Minute Injury Sync (Module D)
**Why 15 minutes**: NBA requires teams to report injuries 15 minutes before tipoff.

**Implementation**:
- Caches injury data for 15 minutes (`yak_cache.json`)
- RotoWire RSS Integration (v4.0): Dynamic refresh 10-20 minutes
- Tank01 Official Layer: Hard status check
- DuckDuckGo Layer: Fallback for deep text analysis

### 4. Archetype Matchup Matrix (Module E)
**Concept**: Player style vs defensive scheme creates exploitable edges.

**Example Matchups**:
- STRETCH_BIG vs PAINT_PACK defense -> +15% 3PM/3PA
- SLASHER vs HACKERS defense -> +20% FTA
- RIM_RUNNER vs PERIMETER defense -> +30% OREB

**Team Defense Schemes (2025-26)**:
- PAINT_PACK: OKC, BOS, DET, MIN, SAS, ORL
- BLITZ: HOU, TOR, MIA, PHX
- PERIMETER: GSW, DAL, NYK
- FUNNEL: WAS, ATL, CHI, UTA, SAC
- HACKERS: IND, CHA, POR

### 5. Tag Classification System
**What it does**: Assigns searchable tags to betting recommendations for filtering, analysis, and pattern recognition.

**Tag Categories:**
1. **ARCHETYPE TAGS** (1 per player): STRETCH_BIG, SLASHER, SNIPER, RIM_RUNNER, HELIOCENTRIC, GENERALIST
2. **SCENARIO TAGS** (0-4 per player): BENEFICIARY, USAGE_VACUUM, MINUTES_LIMIT, HOT_STREAK
3. **MATCHUP TAGS** (1 per game): vs_PAINT_PACK, vs_BLITZ, vs_PERIMETER, vs_FUNNEL, vs_HACKERS, vs_NEUTRAL
4. **MARKET TAGS** (0-n per bet): CORRELATED_SGP, CONTRARIAN, STEAM_MOVE, CLOSING_VALUE

---

## Infrastructure (Self-Hosted)

### Runner Architecture
- **Platform**: Local macOS (Intel x64)
- **Workflows**: Configured with `runs-on: self-hosted`
- **Environment**: `IS_SELF_HOSTED: 'true'` to unlock blocked scripts

### Docker Containment
- **Image**: `ludi-core:latest` (python:3.11-slim base)
- **Capabilities**: Playwright (Chromium/FFMPEG), SQLite3, Git
- **Security**: Isolated execution; secrets injected at runtime

### Database Security
- **Mode**: WAL (Write-Ahead Logging)
- **Backups**: SQLite Hot Backup API with 7-day rotation

---

## API Integrations

| API | Tier | Limit | Purpose |
|-----|------|-------|---------|
| The-Odds-API | PAID | 20K/month | Game lines, player props |
| Tank01 (RapidAPI) | PAID | 1K/day | Rosters, injuries, box scores |
| PBP Stats | FREE | N/A | Shot quality, WOWY data |
| NBA.com | Scraped | N/A | Referee assignments, tracking |

---

## File Structure

```
Ludi-Bot/
├── main.py                    # Pipeline orchestrator
├── module_a.py - module_h.py  # Core modules
├── module_x_scenario.py       # Scenario builder
├── config.py                  # Configuration & API keys
├── database.py                # SQLite operations
├── ludi.db                    # Main database
├── utils/
│   ├── bet_logger.py          # Bet logging
│   ├── blowout_tax.py         # Smart blowout calculations
│   ├── devig.py               # Odds devigging
│   ├── tag_classifier.py      # Play classification
│   ├── telegram_notifier.py   # Telegram integration
│   ├── wowy_calculator.py     # WOWY analysis
│   └── ...
├── scripts/
│   ├── sync_*.py              # Data sync scripts
│   └── ...
├── .github/workflows/         # GitHub Actions
└── docs/                      # Documentation
```
