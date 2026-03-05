# Ludi Lens v2.0 — The Edge, Magnified

**NBA Player Props Analytics | AI-Driven | Always On**

A production-grade autonomous analytics engine that generates player prop recommendations using Monte Carlo simulations, injury intelligence, and edge calculation with devigging.

[![Daily Data Sync](https://github.com/LudiInformatio/Ludi-Bot/actions/workflows/data_sync.yml/badge.svg)](https://github.com/LudiInformatio/Ludi-Bot/actions/workflows/data_sync.yml)
[![Daily Production Pipeline](https://github.com/LudiInformatio/Ludi-Bot/actions/workflows/daily_simulation_pipeline.yml/badge.svg)](https://github.com/LudiInformatio/Ludi-Bot/actions/workflows/daily_simulation_pipeline.yml)

---

## Overview

| Component | Description |
|-----------|-------------|
| **Product** | Ludi Lens v2.0 — The Edge, Magnified |
| **Engine** | S.A.V.A.G.E. Protocol (Hybrid Poisson/Normal Sim \| 10K Runs \| Usage Vacuum) |
| **Stack** | Python 3.14 + SQLite + GitHub Actions |
| **Status** | Production — Phase 8 AI-Enhanced Pipeline (March 2026) |

### Key Features

- **Monte Carlo Simulations** — 10,000 iterations per player with Poisson/Normal hybrid distributions
- **Usage Vacuum Theory** — Automatic usage redistribution when star players are OUT
- **Hybrid Archetype System** — 15 offensive archetypes (`players.archetype`) + deterministic defensive tags (`players.defensive_tag`); weekly Haiku batch + Synergy validation gate
- **Rotation Intelligence** — 396 player rotation profiles + 789 beneficiary pairs (e.g. Embiid OUT → Drummond +18 min)
- **Trend Engine** — Pre-computed L7/L10/L15 trends + live hit rate/streak for 4,500+ player-stat rows; stagger context
- **Scoring Environment** — Dynamic 14-day OVER hit rate tracker; auto-adjusts projections + 4 data-proven OVER filters
- **Matchup Analysis** — Archetype-vs-scheme context (`get_matchup_analysis`) injected into every Spotlight card
- **AI-Enhanced Pipeline** — Claude (Haiku/Sonnet) for play curation, S.A.V.A.G.E. game notes, and player spotlights
- **Perplexity Integration** — Real-time news context injected into injury analysis, game notes, and curation
- **Line Shopping** — NC Legal book integration with CLV tracking across 11 markets
- **Real-time Injury Intelligence** — ESPN (15–30 min lag) + Tank01 + BDL + RotoWire/RealGM RSS; accent-safe canonical name resolution; source-scoped resolve; status severity hierarchy (OUT > DOUBTFUL > GTD)
- **Referee Impact Modeling** — Pace, whistle tendency, and star bias factors
- **Advanced Stats Pipeline** — BDL V2 advanced/hustle/tracking stats + SportsDataIO enrichment (`started`, fantasy pts, doubles)
- **Dual Notification Routing** — Telegram for betting product; Slack (`vibestarters`) for ops alerts and diagnostics

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
| **B: Engine** | Trend/streak consolidation (`LudiEngine`) — pre-loads player_trends + game values at init; enriches player dicts with L5/L10/L15 averages, hit rates vs lines, streak scores |
| **C: Oracle** | Monte Carlo simulation engine (10K iterations) + rotation projection |
| **D: Yak** | Injury intelligence (Tank01 + BDL + RotoWire/RealGM RSS + Perplexity Sonar + ESPN suspension scan) |
| **E: Calibrator** | Matchup adjustments (archetype vs scheme) + scoring environment dampener |
| **F: Alchemist** | Edge calculation, devigging, OVER filters, bet sizing, tier classification |
| **G: Zebras** | Referee impact (pace, fouls, star bias) |
| **H: Historian** | Historical data backfill via Tank01 API (Ghost Protocol) |
| **X: Scenario** | Usage vacuum + injury what-if scenario builder |

---

## AI Employee Workforce

As of March 2026, the Ludi system is staffed by a 7-person AI team running on a hybrid architecture (Claude Agent Teams + Gemini CLI writer + OpenClaw always-on daemons). Each employee has a dedicated soul file in `employees/` that defines their role, communication style, and operating constraints.

| Employee | Role | Runtime | Soul File |
|----------|------|---------|-----------|
| **Solomon** | PM Agent — sprint status, next actions, team health | Claude Agent Teams (lead) | `employees/solomon/` |
| **Silas** | System Monitor — daily health checks, quota alerts, drift detection | OpenClaw (launchd daemon) | `employees/silas/` |
| **Vera** | Pipeline QA — bet logic validation, settlement verification, edge sanity | Claude Agent Teams (teammate) | `employees/vera/` |
| **Iris** | Social Scout — public sentiment, competitive intel, audience demand signals | OpenClaw (launchd daemon) | `employees/iris/` |
| **Henrik** | Code Auditor — independent code review (uses Gemini CLI for genuine writer/auditor split) | Claude Agent Teams (teammate) | `employees/henrik/` |
| **Maren** | Content Strategist — Telegram card copy, weekly report narrative, brand voice | Claude Agent Teams (teammate) | `employees/maren/` |
| **Lena** | Data Analyst / Model Calibration — CLV analysis, win rate audits, edge recalibration | Claude Agent Teams (teammate) | `employees/lena/` *(onboarding pending)* |

**Architecture:** Claude calls `gemini -p "..." --yolo -m gemini-2.5-pro` as a Bash subprocess for writing tasks. Henrik (Claude) reviews Gemini's output. Different model + different company = genuine independent audit. Silas and Iris run as persistent macOS launchd daemons via OpenClaw.

**PRD:** `docs/projects/AI_EMPLOYEE_WORKFORCE.md` — full spec (~$4.60/mo total runtime cost)

---

## Quick Start

### Prerequisites

- Python 3.14+
- API Keys: The-Odds-API (paid), Tank01 (paid), BallDontLie (paid)
- Optional: Telegram bot, Perplexity API, Anthropic API key, Slack Incoming Webhook

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

python main.py                              # Full pipeline
python main.py --games CLE                  # Integration test (single team)
```

---

## Database

`ludi.db` (~30 MB, 38+ tables) is managed locally — **not tracked in git**.

```bash
bash scripts/backup_database.sh                                    # Create backup
bash scripts/restore_database.sh archives/data/ludi.db.backup_*.gz # Restore
ls -lht archives/data/ludi.db.backup_*.gz | head -10               # List backups
```

**Key tables:** `player_game_logs`, `players`, `games`, `bet_recommendations`, `rotation_profiles`, `beneficiary_minutes`, `player_injuries`, `player_trends`, `player_synergy_playtypes`, `team_leverage_profiles`, `referee_profiles`, `player_foul_splits`, `team_dvp_by_archetype`, `player_canonical_ids`, `canonical_teams`, `canonical_games`

---

## Automated Workflows

| Workflow | Schedule (EST) | Purpose |
|----------|---------------|---------|
| DB Backup | 1:00 AM | Database backup (7-day rotation) + CLV closing line capture for yesterday's games |
| Daily Data Sync | 3:00 AM | Game logs, injuries, rotation profiles, scoring environment, enrichment |
| PBP Stats WOWY Sync | 5:00 AM Mon/Wed/Fri | PBP Stats WOWY + four-factor + team leverage profiles |
| Daily Reports | 6:00 AM | Work notes + bet summary |
| WOWY Sync | 7:00 AM | Daily WOWY sync |
| Weekly Referee Sync | Mondays 9:00 AM | Weekly referee intelligence — OddsShark + Covers data via Playwright |
| Daily Referee Sync | 9:30 AM | Scrape referee assignments |
| Lineup Sync | 9:45 AM | Pre-game starting lineups via Tank01 depth charts |
| Production Pipeline | 10:00 AM | Full simulation + play curation → Telegram; pipeline stats → Slack |
| Morning Briefing | 11:00 AM | AI game notes + player spotlights → Telegram |
| Injury Refresh | Every 2hr (11 AM–5 PM) + Every 20min (6–10:40 PM) | Intraday injury refresh (24 runs/game day) |
| Evening Slate Lock | 6:35 PM + 8:25 PM (west coast) | Pre-game Telegram cards; second run covers 9 PM+ tips only |
| Nightly Debrief | 8:30 PM | Bet settlement + daily P&L |
| Ghost Protocol Sync | Sundays (7-day sweep) + Thursdays (gap-fill) | NBA.com tracking data — drives, C&S, pull-ups, clutch stats via Playwright |
| Weekly Validation | Tuesdays | Backtest + archetype classifier + league rankings + ops digest → Slack |
| Claude QA Check | 6 AM + 5:30 PM + 8 PM | Workflow failure review + schema validation + pre-evening quota check |
| Claude Code Review | On PR open/push | Automatic code review on every pull request |
| Claude Ops Hub | On failure/cancel | Auto-diagnosis → Slack; GitHub issue creation |

---

## Project Status

**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Last Updated:** Thursday, March 5, 2026

**Phase 8 Completions:**

| Sub-Phase | Description |
|-----------|-------------|
| 8.0 A/B/C/D | Injury schema, three-tier active roster, smart vacuum, workflow wiring |
| 8.2 | S.A.V.A.G.E. game notes — top 4 games by tier-weight score; B2B fatigue + leverage context |
| 8.3 | Player spotlight cards — archetype-vs-scheme `analysis_block`, L7/L10/L15 trends, hit rate, streaks |
| 8.4 | Archetype classifier — weekly Haiku batch, 15 offensive archetypes + deterministic defensive_tag |
| 8.5 | Play Curation Engine — Haiku sanity gate + Sonnet Top 5 |
| 8.6 | CLV expanded to 11 markets + weekly retrospective |
| 8.7 | Perplexity Sonar integration (replaces DuckDuckGo in Module D) |
| 8.9 | Rotation profiles (396 players) + beneficiary minutes (789 pairs) + stagger/stint data |
| 8.10 | League Rankings — weekly PPP/scheme/pace rankings via Telegram (Tuesdays) |
| 8.12 | Roster Intelligence — trade detection, stale profile cleanup, NEW_TO_TEAM dampener |
| 8.14 | Scoring Environment Intelligence — dynamic OVER bias correction + 4 data-proven OVER filters |
| 8.15 | Trend Engine — `player_trends` (4,500+ rows), hybrid pre-computed + live hit rates, enriched briefings |
| 8.16 | Suspension Intelligence — ESPN 30-team scan; 5 active suspensions found on first run |
| 8.17 | Foul Intelligence — `player_foul_splits` (459 players); Module C `_load_foul_splits_data()` pre-load at init; LEAGUE_AVG_FOULS fixed 21.5→12.5; daily sync in `data_sync.yml` |
| 8.18 | Game Lines Integration — `team_totals` Odds API market, Module E 3-tier scoring modifier |
| 8.19 | Prompt Engineering Upgrade — few-shot examples, Haiku NSP news gate, pre-truncation |
| 8.20 | Stat Confidence & Edge Calibration — per-stat multipliers, RMSE sizing, Wilson 95% WR grades |
| 8.21 | ESPN Integration — `utils/espn_client.py` + Tier 3 game lines fallback + injury source + `espn_id` crosswalk |
| 8.23 | Claude/Perplexity Feedback Loop — `claude_analysis_log` Layer 1 LIVE; 14-day scan ~Mar 10 |
| 8.24 | Edge Type Labeling — deterministic Projection/Matchup/Injury-Vacuum/Hot-Streak label on every bet card |
| 8.25 | Key Advantage Callout — DVP archetype matchup angle prepended to morning brief Telegram cards |
| 8.26 | Correlated Props Flagging — SGP risk (HIGH/MODERATE/LOW) detected + flagged in curation output |
| 8.27 | Pre-Game Lineup Sync — Tank01 depth charts → `players.is_starter`; 9:45 AM + 6:35 PM workflows |
| 8.28 | Game Intelligence Cache — Claude game notes cached; validates before evening re-runs; $0 cost |
| 8.13 | Ask Ludi Telegram Bot — `bots/ask_ludi.py` + db + handlers; Haiku intent → Sonnet narrative; 7 intents live; data freshness layer + ghost injury guard |
| Infra | Infrastructure Sprints (Feb–Mar 2026) — module audit (8-signal confidence tier, STRUCTURAL_LOSERS filter); BDL V2 + SportsDataIO enrichment (100K+ rows); canonical ID system (99.79% clean, 638 entries); CLV hardening (closing lines nightly, stat_category fix); full codebase audit (20/20 workflows hardened, 100% coverage); AI Employee Workforce setup; Pipeline Reliability (Ghost Protocol 136→2 warnings, DB lock fix, curate max_tokens 8192→32000) |

**Active / Planned Next:**
- Sprint 2: Dynamic Rec Lifecycle — `revalidate_recs.py` + `midday_refresh.py` (2 PM/4:30 PM) + `is_valid` column + Perplexity upgrade; employee onboarding docs (~Mar 10)
- Phase 8.22: Social Intelligence System — architecture complete; `social_signals` table + Prop Pulse Score (0–100) into `curate_plays.py`
- Phase 8.23: CLV + Claude Feedback Loop — Wilson calibration at ~Mar 10 (14-day window); `_get_system_wr_context()` injection

**Performance (Jan 7 – Mar 4, 2026, post-dedup):**
- Settled Bets: 8,655 | Win Rate: 53.6% (excl. push/void) | Net Units: -147.54u | ROI: -1.9%
- UNDER bets: 56.4% WR (+84.88u) | OVER bets: 48.5% WR (-232.42u)
- BLK UNDER: 69.6% WR (790 bets) — strongest signal | 3PM UNDER: 60.5% WR (+55.92u)
- BLUE CHIP / STEAL / CORE tiers all net positive; DIAMOND tier (51% WR) under recalibration
- CLV: Positive across all edge buckets (83.9% coverage, avg +4.43c)
- All paper bet tracking — model under live calibration, OVER structural losers filter pending

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
| [docs/TOOLS_GUIDE.md](docs/TOOLS_GUIDE.md) | Task automation scripts and helpers |
| [docs/STATUS_HISTORY.md](docs/STATUS_HISTORY.md) | Archived project status updates (Phases 1-4) |
| [docs/research/competitive/BETIQ_TEAMRANKINGS_RESEARCH.md](docs/research/competitive/BETIQ_TEAMRANKINGS_RESEARCH.md) | BetIQ/TeamRankings competitive analysis — ATS/O-U patterns, feature gap analysis, implementation roadmap |
| [best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md](best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md) | BERT-derived prompt engineering patterns — 8 structural improvements for Claude prompts, implementation priority |
| [best-practices/ai/PM_BOT_NOTES_GUIDE.md](best-practices/ai/PM_BOT_NOTES_GUIDE.md) | How to write ROADMAP header lines so PM bot generates specific Gemini messages (BERT grounding pattern) |

---

## API Integrations

| API | Tier | Purpose |
|-----|------|---------|
| The-Odds-API | Paid (20K credit/mo) | Game lines, player props (primary) |
| Ball Don't Lie | Paid ($39.99/mo) | Fallback odds, injuries, game logs |
| Tank01 | Paid (1K credits/day) | Rosters, injuries, box scores |
| PBP Stats | Free | Shot quality, WOWY data |
| Perplexity Sonar | Paid | News context for injuries + game notes |
| SportsDataIO | Free (100 calls/day) | Fantasy stats enrichment (`started`, fantasy pts, doubles) |
| ESPN Public API | Free (no auth) | Suspension intelligence (30-team scan); future game injuries + Tier 3 lines |
| NBA.com | Scraped | Referee assignments, on-court tracking data (Ghost Protocol) |

---

## Tech Stack

- **Language:** Python 3.14
- **Database:** SQLite with WAL mode (~30 MB, 38+ tables)
- **Automation:** GitHub Actions (self-hosted macOS runner)
- **AI:** Claude Haiku / Sonnet (Anthropic) via OAuth
- **Notifications:** Telegram (betting product) + Slack (ops alerts, `vibestarters` workspace)
- **Browser Automation:** Playwright (Ghost Protocol scraping)

---

<!-- PERMANENT SECTION — DO NOT REMOVE OR MOVE. Update content periodically, never delete. -->
## Project Vision

**Started:** Summer 2025 — A solo NBA props model seeded from competitive research and a single thesis: *Poisson distributions can find exploitable value in player prop markets.*

**Core thesis (validated):** Props are exploitable via scenario-conditional simulation. When stars sit, usage redistributes. Referee tendencies leave measurable signal. The math is real — but edge requires rigorous infrastructure to find and trust.

**Where it is now (March 2026):** Phase 8 AI-Enhanced Pipeline — a 9-module production platform with 10,000-iteration Monte Carlo sims, 10+ redundant data sources, 40+ database tables, 9,200+ settled bets, and a 7-person AI employee team (Solomon, Silas, Vera, Iris, Henrik, Maren, Lena) managing pipeline health and content strategy.

**Where it's headed:** Ludi Lens web dashboard (Streamlit, post-Phase 8), WNBA/NFL expansion (2026-27 season), and deeper CLV recalibration as the model crosses 30,000+ settled bets.

*Last updated: March 2026*

---

## License

Private repository — All rights reserved.
