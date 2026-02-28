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
| **Status** | Production — Phase 8 AI-Enhanced Pipeline (Feb 27, 2026 5:56 PM EST) |

### Key Features

- **Monte Carlo Simulations** — 10,000 iterations per player with Poisson/Normal hybrid distributions
- **Usage Vacuum Theory** — Automatic usage redistribution when star players are OUT
- **Hybrid Archetype System** — 15 offensive archetypes in `players.archetype`; deterministic `players.defensive_tag` (PERIMETER_HAWK/RIM_GUARDIAN/SWITCHABLE_ANCHOR/HUSTLE_DISRUPTOR/WEAK_LINK); weekly Haiku batch + Synergy validation gate
- **Rotation Intelligence** — 396 player rotation profiles + 789 beneficiary pairs (e.g. Embiid OUT → Drummond +18 min)
- **Trend Engine** — Pre-computed L7/L10/L15 trends + live hit rate/streak for 4,500+ player-stat rows; stagger context
- **Scoring Environment** — Dynamic 14-day OVER hit rate tracker; auto-adjusts projections + 4 data-proven OVER filters
- **Matchup Analysis** — Archetype-vs-scheme context (`get_matchup_analysis`) injected into every Spotlight card
- **League Rankings** — Weekly PPP rankings (P&R/ISO/Spot-Up), defensive scheme distribution, pace leaders via Telegram
- **AI-Enhanced Pipeline** — Claude (Haiku/Sonnet) for play curation, S.A.V.A.G.E. game notes, and player spotlights
- **Perplexity Integration** — Real-time news context injected into injury analysis, game notes, and curation
- **Line Shopping** — NC Legal book integration with CLV tracking across 11 markets
- **Real-time Injury Intelligence** — ESPN injuries (15-30min lag, primary fast source) + Tank01 + BDL + RotoWire/RealGM RSS; `player_canonical_ids.normalized_name` for accent-safe name resolution; source-scoped resolve (ESPN, BDL, suspension independently); status severity hierarchy (OUT > DOUBTFUL > GTD); 75-day filter excludes season-enders from Claude context
- **Referee Impact Modeling** — Pace, whistle tendency, and star bias factors
- **Dual Notification Routing** — Telegram for betting product; Slack (`vibestarters`) for ops alerts and diagnostics
- **Slate Trends Header** — `_build_slate_trends_header()` sends injury-filtered HOT/COOLING signals once per briefing before per-game notes
- **Advanced Stats Pipeline** — BDL V2 advanced/hustle/tracking stats + SportsDataIO enrichment (`started`, fantasy pts, doubles); Ghost Protocol reserved for on-court only
- **Foul Intelligence** — Rolling 21-day foul splits (`player_foul_splits`, 459 players); Module C pre-loads at init for zero-overhead per-simulation lookups; `min_dampener` dampens minutes for foul-trouble players

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

**Key tables:** `player_game_logs`, `players`, `games`, `bet_recommendations`, `rotation_profiles`, `beneficiary_minutes`, `player_injuries`, `player_trends`, `player_synergy_playtypes`, `team_leverage_profiles`, `referee_profiles`, `player_foul_splits`, `team_dvp_by_archetype`, `player_canonical_ids`, `canonical_teams`

---

## Automated Workflows

| Workflow | Schedule (EST) | Purpose |
|----------|---------------|---------|
| DB Backup | 1:00 AM | Automated database backup (7-day rotation) |
| Daily Data Sync | 3:00 AM | Game logs, injuries, rotation profiles, scoring environment, enrichment |
| PBP Stats WOWY Sync | 5:00 AM Mon/Wed/Fri | PBP Stats WOWY + four-factor + team leverage profiles |
| Daily Reports | 6:00 AM | Work notes + bet summary |
| WOWY Sync | 7:00 AM | Daily WOWY sync |
| Morning Briefing | 11:00 AM | AI game notes + player spotlights → Telegram (moved from 9 AM; refs+pipeline run first) |
| Daily Referee Sync | 9:30 AM | Scrape referee assignments |
| Production Pipeline | 10:00 AM | Full simulation + play curation → Telegram; pipeline stats → Slack |
| Evening Slate Lock | 6:00 PM | Final pre-game Telegram cards |
| Nightly Debrief | 8:30 PM | Bet settlement + daily P&L |
| Closing Line Capture | 7:30-11:30 PM | CLV capture (5 runs/night) |
| Weekly Validation | Tuesdays | Backtest + archetype classifier + league rankings + ops digest → Slack |
| Claude Ops Hub | On failure/cancel | Auto-diagnosis → Slack; GitHub issue creation |

---

## Project Status

**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Last Updated:** February 27, 2026 — 5:56 PM EST

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
| Infra | Module Audit Sprint (A+B+C+D+E) — Gatekeeper bug fixes (totals, BDL crash, timeouts), CLV overhaul (Tank01 Tier 3, always-capture, quota TTL), `LudiEngine` class (HOT_STREAK fix, hit rates, line history); `LudiOracle` 8 pre-load dicts + zero-DB sim loop; `LudiCalibrator` bulk pre-loads (DVP, B2B splits, archetype matrix); `LudiYak` news_agent, INJURY_RETURN edge type, ghost resolve fix; `USG_PCT` key fix in `main.py`; Module F (`LudiReporter`) next |
| Infra | Full Project Audit (Sprints 0-10) — 0 critical issues, 375+ dead files removed, 4 CVE patches |
| Infra | Injury Pipeline Hardening — ESPN fast source (15-30min lag); accent-safe canonical name resolution; source-scoped resolve; status severity hierarchy; 75-day staleness filter |
| Infra | BDL V2 + SportsDataIO Enrichment — 4 sync scripts; 100K+ rows (advanced/hustle/tracking/fantasy pts/started); Ghost Protocol `--skip-advanced` |
| Infra | Canonical Table Hardening — `player_canonical_ids` CREATE TABLE restored; `canonical_teams` (30 rows); `normalize_bdl_abbr()` centralized; `resolve_canonical_name()` wired into 4 injection points |
| Infra | Settlement Pipeline Hardening — date-ceiling guard; canonical name fallback; three-section report (daily/L10/launch); all-void guard |
| Infra | Hybrid Off/Def Tagging — `players.archetype` = 15 offensive only; `players.defensive_tag` deterministic |
| Infra | DVP Rankings — `team_dvp_by_archetype` (250 rows, 10 archetypes × 30 teams, per-100 normalized) |

**Active / Planned Next:**
- Module Audit Sprint — A+B+C+D+E complete; Module F (`LudiReporter`) next
- Phase 8.22: Social Intelligence System — architecture complete; Phase 1 = `social_signals` + `odds_snapshots` + Prop Pulse Score (0–100)
- Phase 8.23: Claude/Perplexity Feedback Loop — Layer 1 collecting; Wilson calibration at 14-day mark (~Mar 10)

**Performance (Jan 7 – Feb 25, 2026):**
- Settled Bets: 16,336+ | Win Rate: ~53.2% overall | ROI: -0.1% (model in BETA)
- BLOCKS UNDER: 70.7% WR — strongest signal in system
- UNDER bets: 55.0% | OVER bets: 42.1% (OVER filters actively suppressing weak categories)
- CLV: Positive across all edge buckets
- All paper bet tracking in beta

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
| The-Odds-API | Paid (20K/mo) | Game lines, player props (primary) |
| Ball Don't Lie | Paid ($39.99/mo) | Fallback odds, injuries, game logs |
| Tank01 | Paid (1K/day) | Rosters, injuries, box scores |
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

## License

Private repository — All rights reserved.
