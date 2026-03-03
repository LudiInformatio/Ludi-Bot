# Ludi-Bot Architecture

This document describes the system architecture, module pipeline, and database schema for the Ludi-Bot NBA analytics platform.

---

## System Overview

**Ludi Informatio v2.0** is an NBA analytics platform that generates betting recommendations for player props using Monte Carlo simulations, injury intelligence, and edge calculation with devigging.

- **Product Name**: Ludi Lens v2.0 — The Edge, Magnified
- **Descriptor**: NBA Player Props Analytics | AI-Driven | Always On
- **Engine**: S.A.V.A.G.E. Protocol (Hybrid Poisson/Normal Sim | 10k Runs | Usage Vacuum)
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
|  MODULE B: Engine (Trend/Streak Consolidation)              |
|  - Pre-loads player_trends + recent game values at init     |
|  - Enriches player dicts with L5/L10/L15 averages         |
|  - Calculates streak_score for HOT_STREAK tags             |
|  - Computes hit_rates_by_market for Module F confidence    |
|  - Persists opening prop lines to prop_line_snapshots       |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  MODULE C: Oracle (Monte Carlo Simulation)                  |
|  - 10,000 Poisson iterations per player                     |
|  - Simulates FGA, FG3A, FTA (volume)                        |
|  - Applies shooting %s, pace, fatigue, referee impact       |
|  - Outputs: Projected stats with confidence intervals       |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  MODULE D: Yak (Injury Intelligence)                        |
|  - 120-min day / 20-min game-time refresh cycle             |
|  - Primary: Tank01 API, Secondary: BallDontLie              |
|  - Corroboration: RotoWire RSS + RealGM RSS (dual-source)   |
|  - Nuance: Perplexity search + Claude AI blurb parsing      |
|  - Suspensions: ESPN sync (scripts/sync_suspensions_espn.py)|
|  - Classifies: OUT/DOUBTFUL/Q/PROBABLE/MINUTES_LIMIT/SUSP  |
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
| B: Engine | `module_b.py` | `LudiEngine` | None (pre-loads trends/game values, enriches player dicts) |
| C: Oracle | `module_c.py` | `LudiOracle` | None (pure math) |
| D: Yak | `module_d.py` | `LudiYak` | Tank01 + BDL fallback + RotoWire RSS + RealGM RSS + Perplexity nuance |
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
| `referee_profiles` | 85 | 81 NBA officials + 4 retired. `avg_fouls_per_game` (OddsShark per-ref: (home+away)/3), `rolling_21d_fouls` (internal L10), `games_worked`, `ou_percentage`, `home_ats_bias`, `badge_number`, `style` (STRICT/NEUTRAL/LENIENT). Sources: Covers.com (O/U, total), OddsShark (ATS, Home/Away Fouls), NBA Staff PDF (badge#). Weekly: `sync_external_intelligence.py`. (Mar 2) |
| `referee_player_bias` | 1,810+ | Per-player bias vs each referee: `avg_pf_called`, `avg_fta_awarded`, `points_impact_vs_avg`, `games_officiated`. Written daily by `scripts/analyze_star_bias.py`. Queried by `LudiRefEngine.get_player_crew_bias()` → consumed in `module_f.py` note field (STAR_KILLER / PROTECTOR labels, ≥3.5 PPG delta, ≥5 games threshold). Backfill pending: `scripts/backfill_referee_bias.py` (Feb 28) |
| `team_betting_trends` | 30 | H/A records, scoring avgs, ATS splits — computed from canonical_games + player_game_logs + bet_recommendations. Synced by `scripts/sync_team_betting_trends.py`. (Feb 28) |
| `player_synergy_playtypes` | 1,326 | Synergy playtype data |
| `player_shot_quality` | 499 | PBP Stats shot quality data |
| `team_lineups` | 10,669 | WOWY lineup data |
| `player_canonical_ids` | 559+ | ID crosswalk: `canonical_id`, `normalized_name`, `full_name`, `sportsdata_id`, `dk_player_id`, `fd_player_id`, `espn_id` (Feb 24); `team` column removed (Mar 3) — team always via LEFT JOIN `players`. CREATE TABLE in `database.py` |
| `canonical_teams` | 30 | Team ID crosswalk: `standard_abbr` (PK), `full_name`, `bdl_abbr`, `tank01_abbr`, `espn_id`; single source of truth for all BDL/Tank01/ESPN team ID mappings (Feb 24) |
| `canonical_games` | 902 | Game identity crosswalk: `canonical_game_id` PK (`{date}_{home}_{away}`), `nba_official_id` (002... format), `referee_crew`, `pace`. Deduplicates the 3-format games table (NBA official / shortened / date-team). `sync_canonical_games(conn)` importable from `database.py`. Use for Pattern-B JOINs (date+team pair) to prevent 3× row inflation. Added Feb 28. |
| `player_news_staging` | Dynamic | RSS-discovered players not yet in `player_canonical_ids` (rookies, two-ways, call-ups). `UNIQUE(player_name, source)`. Auto-promotes after 3+ appearances. Added Feb 25. |
| `player_type_profiles` | 382 | Unified classification layer: archetype + defensive_tag + top-3 Synergy playtypes + freqs + PPPs + `archetype_in_top3` flag + `position_synergy_match`. `PRIMARY KEY (player_name, season)`. Feeds BERT negative few-shot injection. Added Feb 25. |
| `player_foul_splits` | 459 | Rolling 21-day foul stats per player: `foul_rate`, `min_dampener` (0.70–1.0 scale), `data_confidence` (HIGH ≥ 10g / MEDIUM ≥ 5g). Synced daily via `scripts/sync_player_foul_splits.py`. Module C pre-loads at init via `_load_foul_splits_data()` — zero per-simulation DB connections. Added Feb 25 (Phase 8.17). |
| `prop_line_snapshots` | Dynamic | Written by `module_b.snapshot_opening_lines()` daily; updated by `scripts/capture_closing_lines.py` (closing columns). **Primary consumer (Mar 2026):** `scripts/send_settlement_summary.py` — `_line_movement_summary()` function appends opening vs closing line deltas to nightly Telegram message for bets where line moved ≥0.5 or odds moved ≥10 pts. **Future consumers:** Ask Ludi `edges` intent ("what was the opening line for X?"); `scripts/analyze_line_movement.py` (weekly steam move detection, post-Phase 8). |

#### Player Classification Columns — Hybrid Off/Def System (Feb 22 2026)

Every player gets **two independent role tags**:

| Column | Purpose | Values |
|--------|---------|--------|
| `archetype` | **Offensive role** — drives usage vacuum logic | 15 offensive archetypes (no defensive labels) |
| `defensive_tag` | **Defensive role** — independent of offensive role | PERIMETER_HAWK, RIM_GUARDIAN, SWITCHABLE_ANCHOR, HUSTLE_DISRUPTOR, WEAK_LINK, or NULL |

**Offensive archetypes (15):** HELIOCENTRIC_MAESTRO, SLASHING_CREATOR, ISO_ASSASSIN, JUMBO_FACILITATOR, SNIPER_ELITE, TWO_LEVEL_SCORER, WARRIOR_BIG, STRETCH_BIG, ROLL_MAN, HUB_BIG, ENERGY_BIG, CUTTER_SPECIALIST, CONNECTOR, FACILITATOR, GENERALIST

**Defensive tags (assigned deterministically — no Claude):**
- `PERIMETER_HAWK`: STL ≥ 0.9/g + SPOT_UP present in synergy
- `RIM_GUARDIAN`: at_rim_freq ≥ 50% + BLK ≥ 1.0/g
- `SWITCHABLE_ANCHOR`: STL+BLK ≥ 1.2/g (versatile, not pure rim or perimeter)
- `HUSTLE_DISRUPTOR`: STL+BLK ≥ 1.0/g + 3+ synergy playtypes
- `WEAK_LINK`: poor defender (existing threshold)
- `NULL`: average/unknown defender

**Why two columns:** A two-way wing like Jalen Williams is both a **scoring creator** (archetype=HELIOCENTRIC_MAESTRO/TWO_LEVEL_SCORER) AND a **perimeter defender** (defensive_tag=PERIMETER_HAWK). With one column, classifying him as PERIMETER_HAWK would cause Module X to skip his usage vacuum entirely — wrong, since his 25+ PPG absolutely creates an offensive void when he's out. The hybrid system ensures every player generates correct usage vacuum analysis via `archetype`, while defensive identity is visible separately in `defensive_tag`.

**GENERALIST Measurement**: The <25% target applies to **active players** (21-day window, ≥3 games), not all players in database. Injured/inactive players default to GENERALIST but don't generate bets.

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
| ESPN Public API | FREE | No auth | Suspension intelligence (`sync_suspensions_espn.py`), game injuries with beneficiary context (`longComment`), DraftKings game lines as Tier 3 fallback |

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
