# Ludi Informatio v2.0

**NBA Player Props Analytics Platform**

A production-grade betting analytics engine that generates player prop recommendations using Monte Carlo simulations, injury intelligence, and edge calculation with devigging.

[![Daily Data Sync](https://github.com/LudiInformatio/Ludi-Bot/actions/workflows/data_sync.yml/badge.svg)](https://github.com/LudiInformatio/Ludi-Bot/actions/workflows/data_sync.yml)
[![Daily Production Pipeline](https://github.com/LudiInformatio/Ludi-Bot/actions/workflows/daily_simulation_pipeline.yml/badge.svg)](https://github.com/LudiInformatio/Ludi-Bot/actions/workflows/daily_simulation_pipeline.yml)

---

## Overview

| Component | Description |
|-----------|-------------|
| **Product** | Ludi Lens v2.0 (The Front Office War Room) |
| **Engine** | S.A.V.A.G.E. Protocol (Hybrid Poisson/Normal Sim \| 25K Runs \| Usage Vacuum) |
| **Stack** | Python 3.11 + SQLite + GitHub Actions |
| **Status** | Production (Phase 6 - Full Data Integration) |

### Key Features

- **Monte Carlo Simulations** - 25,000 iterations per player with Poisson/Normal hybrid distributions
- **Usage Vacuum Theory** - Automatic usage redistribution when star players are OUT
- **16-Archetype Matchup System** - Player style vs defensive scheme analysis
- **Line Shopping** - NC Legal book integration with CLV tracking
- **Real-time Injury Intelligence** - 15-minute refresh via Tank01 + RotoWire RSS
- **Referee Impact Modeling** - Pace, whistle tendency, and star bias factors

---

## Architecture

```
Module Pipeline:
A: Gatekeeper ─→ B: Engine ─→ C: Oracle ─→ D: Yak ─→ E: Calibrator ─→ F: Alchemist
     │                                                                      │
     └── G: Zebras (Referees)                                              │
     └── H: Historian (Historical Data)                                    │
     └── X: Scenario Builder (Usage Vacuum)         [Daily Recommendations] ◄─┘
```

| Module | Purpose |
|--------|---------|
| **A: Gatekeeper** | Odds ingestion from The-Odds-API |
| **B: Engine** | Historical analysis (L5, L10, season trends) |
| **C: Oracle** | Monte Carlo simulation engine (25K iterations) |
| **D: Yak** | Injury intelligence (Tank01 + RotoWire + DuckDuckGo) |
| **E: Calibrator** | Matchup adjustments (archetype vs defense) |
| **F: Alchemist** | Edge calculation, devigging, bet sizing |
| **G: Zebras** | Referee impact modeling |
| **H: Historian** | Historical data sync (Tank01 API) |
| **X: Scenario** | "What-if" injury scenarios |

---

## Quick Start

### Prerequisites

- Python 3.11+
- API Keys: The-Odds-API (paid), Tank01 (paid)
- Optional: Telegram bot for notifications

### Installation

```bash
# Clone repository
git clone https://github.com/LudiInformatio/Ludi-Bot.git
cd Ludi-Bot

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.template .env
# Edit .env with your API keys

# Initialize database
python database.py
```

### Running the Pipeline

```bash
# Activate environment
source .venv/bin/activate

# Run full pipeline
python main.py

# Run integration test
python test_pipeline.py
```

---

## Database

The database (`ludi.db`) is managed locally with automated backups. **Not tracked in git.**

```bash
# Create backup
bash scripts/backup_database.sh

# Restore from backup
bash scripts/restore_database.sh archives/data/ludi.db.backup_<timestamp>.gz

# List backups
ls -lht archives/data/ludi.db.backup_*.gz | head -10
```

---

## Automated Workflows

| Workflow | Schedule (EST) | Purpose |
|----------|---------------|---------|
| Daily Data Sync | 3:00 AM | Fetch game logs, update player stats |
| Daily Referee Sync | 4:30 AM | Scrape referee assignments |
| Morning Briefing | 6:00 AM | Generate visual betting cards |
| Production Pipeline | 11:00 AM | Run simulations, output recommendations |
| Evening Slate Lock | 6:00 PM | Final pre-game updates |
| Nightly Debrief | 10:30 PM | Settlement + PM Bot summary |
| Claude QA Check | 6:00 AM | Automated failure detection |

---

## Project Status

**Current Phase:** Phase 6 - Full Data Integration

**Recent Completions:**
- Phase 6.5e: Workflow infrastructure fixes
- Phase 6.5d: Canonical ID system audit (99.84% data quality)
- Phase 6.5c: PBP Stats API fixes (19.4x performance improvement)
- Phase 6.5b: Direct SQLite writes, JSON cleanup

**Performance (Jan 7-29, 2026):**
- Total Bets: 9,605 logged, 6,344 settled
- Win Rate: 55.7%
- Profit: +292 units
- CLV: Positive across all edge buckets

See [ROADMAP.md](ROADMAP.md) for detailed progress tracking.

---

## Documentation

| Document | Description |
|----------|-------------|
| [ROADMAP.md](ROADMAP.md) | Current tasks and priorities |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design and module reference |
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | Betting edge calculations |
| [docs/PRODUCTION_HANDBOOK.md](docs/PRODUCTION_HANDBOOK.md) | Deployment and operations guide |
| [CLAUDE.md](CLAUDE.md) | AI assistant instructions |

---

## API Integrations

| API | Tier | Purpose |
|-----|------|---------|
| The-Odds-API | Paid (20K/mo) | Game lines, player props |
| Tank01 | Paid (1K/day) | Rosters, injuries, box scores |
| PBP Stats | Free | Shot quality, WOWY data |
| NBA.com | Scraped | Referee assignments, tracking data |

---

## Tech Stack

- **Language:** Python 3.11
- **Database:** SQLite with WAL mode
- **Automation:** GitHub Actions (self-hosted runner)
- **Notifications:** Telegram Bot API
- **Browser Automation:** Playwright (Ghost Protocol scraping)

---

## License

Private repository - All rights reserved.

---

## Contact

For questions or issues, open a GitHub issue or contact the repository owner.
