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
| **Stack** | Python 3.14 + SQLite + GitHub Actions |
| **Status** | Production — Phase 8 AI-Enhanced Pipeline (Feb 2026) |

### Key Features

- **Monte Carlo Simulations** — 25,000 iterations per player with Poisson/Normal hybrid distributions
- **Usage Vacuum Theory** — Automatic usage redistribution when star players are OUT
- **19-Archetype Matchup System** — Player style vs defensive scheme analysis (incl. 5 defensive archetypes)
- **Rotation Intelligence** — 396 player rotation profiles + 789 beneficiary pairs (e.g. Embiid OUT → Drummond +18 min)
- **Scoring Environment** — Dynamic 14-day OVER hit rate tracker; auto-adjusts projections when market favors unders
- **AI-Enhanced Pipeline** — Claude (Haiku/Sonnet) for play curation, S.A.V.A.G.E. game notes, and player spotlights
- **Perplexity Integration** — Real-time news context injected into injury analysis, game notes, and curation
- **Line Shopping** — NC Legal book integration with CLV tracking across 11 markets
- **Real-time Injury Intelligence** — 15-minute refresh via BDL + Tank01, DB-driven smart vacuum
- **Referee Impact Modeling** — Pace, whistle tendency, and star bias factors

---

## Architecture

```
Module Pipeline:
A: Gatekeeper ─→ B: Engine ─→ C: Oracle ─→ D: Yak ─→ E: Calibrator ─→ F: Alchemist
     │                                                                        │
     ├── G: Zebras (Referees)                                                 │
     ├── H: Historian (Historical Backfill)                          [Daily Bets + Claude Cards]
     └── X: Scenario Builder (Usage Vacuum + Injury What-If)
```

| Module | Purpose |
|--------|---------|
| **A: Gatekeeper** | Odds ingestion (The-Odds-API primary, BDL fallback) |
| **B: Engine** | Historical analysis (L5, L10, season trends, hot streaks) |
| **C: Oracle** | Monte Carlo simulation engine (25K iterations) + rotation projection |
| **D: Yak** | Injury intelligence (BDL + Tank01 + Perplexity Sonar) |
| **E: Calibrator** | Matchup adjustments (archetype vs scheme) + scoring environment dampener |
| **F: Alchemist** | Edge calculation, devigging, OVER filters, bet sizing, tier classification |
| **G: Zebras** | Referee impact (pace, fouls, star bias) |
| **H: Historian** | Historical data backfill via Tank01 API (Ghost Protocol) |
| **X: Scenario** | Usage vacuum + injury what-if scenario builder |

---

## Quick Start

### Prerequisites

- Python 3.14+
- API Keys: The-Odds-API (paid), Tank01 (paid), BallDontLie (paid)
- Optional: Telegram bot, Perplexity API, Anthropic API key

### Installation

```bash
git clone https://github.com/LudiInformatio/Ludi-Bot.git
cd Ludi-Bot

python3.14 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.template .env
# Edit .env with your API keys

python database.py   # Initialize schema
```

### Running the Pipeline

```bash
source .venv/bin/activate

python main.py              # Full pipeline
python test_pipeline.py     # Integration test
```

---

## Database

`ludi.db` (~30 MB, 38+ tables) is managed locally — **not tracked in git**.

```bash
bash scripts/backup_database.sh                                    # Create backup
bash scripts/restore_database.sh archives/data/ludi.db.backup_*.gz # Restore
ls -lht archives/data/ludi.db.backup_*.gz | head -10               # List backups
```

**Key tables:** `player_game_logs`, `players`, `games`, `bet_recommendations`, `rotation_profiles`, `beneficiary_minutes`, `player_injuries`, `player_synergy_playtypes`, `referee_profiles`

---

## Automated Workflows

| Workflow | Schedule (EST) | Purpose |
|----------|---------------|---------|
| Daily Data Sync | 5:00 AM | Game logs, WOWY, injuries, rotation profiles, scoring environment |
| Nightly Debrief | 5:00 AM | Bet settlement + daily P&L |
| DB Backup | 6:00 AM | Automated database backup (7-day rotation) |
| Morning Briefing | 9:00 AM | AI game notes + player spotlights → Telegram |
| Daily Referee Sync | 9:30 AM | Scrape referee assignments |
| Production Pipeline | 11:00 AM | Full simulation + play curation → Telegram |
| Closing Line Capture | 5:30 PM | CLV capture before tipoff |
| Evening Slate Lock | 6:00 PM | Final pre-game Telegram cards |
| Weekly Validation | Tuesdays | Backtest + drift detection + archetype classifier + retrospective |
| Claude Ops Hub | On failure | Auto-diagnosis of workflow failures |

---

## Project Status

**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Last Updated:** February 19, 2026

**Phase 8 Completions:**

| Sub-Phase | Description |
|-----------|-------------|
| 8.0 A/B/C/D | Injury schema, three-tier active roster, smart vacuum, workflow wiring |
| 8.2 | S.A.V.A.G.E. game notes — top 4 games by tier-weight score |
| 8.3 | Player spotlight cards (DIAMOND + BLUE CHIP only) |
| 8.4 | Archetype classifier — weekly Haiku batch, 19 types, Synergy validation |
| 8.5 | Play Curation Engine — Haiku sanity gate + Sonnet Top 5 |
| 8.6 | CLV expanded to 11 markets + weekly retrospective |
| 8.7 | Perplexity Sonar integration (replaces DuckDuckGo in Module D) |
| 8.9 | Rotation profiles (396 players) + beneficiary minutes (789 pairs) + stagger/stint data |
| 8.12 | Roster Intelligence — trade detection, stale profile cleanup, NEW_TO_TEAM dampener |
| 8.14 | Scoring Environment Intelligence — dynamic OVER bias correction + 4 data-proven OVER filters |

**Performance (Jan 7 – Feb 19, 2026):**
- Settled Bets: 14,423
- Win Rate: ~54.8% overall | UNDER bets: 55.0% | OVER bets: 42.1%
- UNDER hit rate stable across full season; OVER filters (8.14) targeting known weak categories
- CLV: Positive across all edge buckets

See [ROADMAP.md](ROADMAP.md) for detailed progress and upcoming work.

---

## Documentation

| Document | Description |
|----------|-------------|
| [ROADMAP.md](ROADMAP.md) | Current tasks and priorities |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, module reference, DB schema |
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | Edge calculation, devigging, CLV tracking |
| [docs/PRODUCTION_HANDBOOK.md](docs/PRODUCTION_HANDBOOK.md) | Deployment and operations guide |
| [best-practices/](best-practices/) | API patterns, sportsbook tiers, lessons learned |
| [CLAUDE.md](CLAUDE.md) | AI assistant project instructions |

---

## API Integrations

| API | Tier | Purpose |
|-----|------|---------|
| The-Odds-API | Paid (20K/mo) | Game lines, player props (primary) |
| Ball Don't Lie | Paid ($39.99/mo) | Fallback odds, injuries, game logs |
| Tank01 | Paid (1K/day) | Rosters, injuries, box scores |
| PBP Stats | Free | Shot quality, WOWY data |
| Perplexity Sonar | Paid | News context for injuries + game notes |
| NBA.com | Scraped | Referee assignments, tracking data |

---

## Tech Stack

- **Language:** Python 3.14
- **Database:** SQLite with WAL mode (~30 MB, 38+ tables)
- **Automation:** GitHub Actions (self-hosted macOS runner)
- **AI:** Claude Haiku / Sonnet (Anthropic) via OAuth
- **Notifications:** Telegram Bot API
- **Browser Automation:** Playwright (Ghost Protocol scraping)

---

## License

Private repository — All rights reserved.
