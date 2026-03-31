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
| I: Aggregator | `module_i_aggregator.py` | `LudiAggregator` (placeholder) | None |
| DB Firewall | `database.py` | `LudiHistorian.resolve_player_id_for_insert` | None |

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
| `bet_recommendations` | Dynamic | Created in utils/bet_logger.py (not database.py init_db). Logged bets with tags. `curation_grade` (STRONG/LEAN/FADE) added Mar 4 — Curation v2 full-slate AI grading. `is_curated=1` + `curated_rank` set for STRONG bets only. Shared game dossier via `cache/game_dossier_{date}.json` (written by `curate_plays.py`, read by `morning_brief.py`). |
| `referee_profiles` | 85 | 81 NBA officials + 4 retired. `avg_fouls_per_game` (OddsShark per-ref: (home+away)/3), `rolling_21d_fouls` (internal L10), `games_worked`, `ou_percentage`, `home_ats_bias`, `badge_number`, `style` (STRICT/NEUTRAL/LENIENT). Sources: Covers.com (O/U, total), OddsShark (ATS, Home/Away Fouls), NBA Staff PDF (badge#). Weekly: `sync_external_intelligence.py`. (Mar 2) |
| `referee_player_bias` | 1,810+ | Per-player bias vs each referee: `avg_pf_called`, `avg_fta_awarded`, `points_impact_vs_avg`, `games_officiated`. Written daily by `scripts/analyze_star_bias.py`. Queried by `LudiRefEngine.get_player_crew_bias()` → consumed in `module_f.py` note field (STAR_KILLER / PROTECTOR labels, ≥3.5 PPG delta, ≥5 games threshold). Backfill pending: `scripts/backfill_referee_bias.py` (Feb 28) |
| `team_betting_trends` | 30 | H/A records, scoring avgs, ATS splits — computed from canonical_games + player_game_logs + bet_recommendations. Synced by `scripts/sync_team_betting_trends.py`. (Feb 28) |
| `player_synergy_playtypes` | 1,326 | Created in migrations/create_synergy_tables.sql (not database.py init_db). Synergy playtype data |
| `player_shot_quality` | 499 | PBP Stats shot quality data |
| `team_lineups` | 10,669 | Created in scripts/sync_wowy_backfill.py (not database.py init_db). WOWY lineup data |
| `player_canonical_ids` | 638+ | ID crosswalk: `canonical_id`, `normalized_name`, `full_name`, `sportsdata_id`, `dk_player_id`, `fd_player_id`, `espn_id` (Feb 24); `team` column removed (Mar 3) — team always via LEFT JOIN `players`. CREATE TABLE in `database.py`. Full remediation Mar 4: 0 dirty canonical IDs, 99.79% downstream clean. |
| `canonical_teams` | 30 | Team ID crosswalk: `standard_abbr` (PK), `full_name`, `bdl_abbr`, `tank01_abbr`, `espn_id`; single source of truth for all BDL/Tank01/ESPN team ID mappings (Feb 24) |
| `canonical_games` | 955+ | Game identity crosswalk: `canonical_game_id` PK (`{date}_{home}_{away}`), `nba_official_id` (002... format), `referee_crew`, `pace`. Deduplicates the 3-format games table (NBA official / shortened / date-team). `sync_canonical_games(conn)` importable from `database.py`. Use for Pattern-B JOINs (date+team pair) to prevent 3× row inflation. Added Feb 28. |
| `player_news_staging` | Dynamic | RSS-discovered players not yet in `player_canonical_ids` (rookies, two-ways, call-ups). `UNIQUE(player_name, source)`. Auto-promotes after 3+ appearances. Added Feb 25. |
| `player_type_profiles` | 382 | Unified classification layer: archetype + defensive_tag + top-3 Synergy playtypes + freqs + PPPs + `archetype_in_top3` flag + `position_synergy_match`. `PRIMARY KEY (player_name, season)`. Feeds BERT negative few-shot injection. Added Feb 25. |
| `player_foul_splits` | 459 | Rolling 21-day foul stats per player: `foul_rate`, `min_dampener` (0.70–1.0 scale), `data_confidence` (HIGH ≥ 10g / MEDIUM ≥ 5g). Synced daily via `scripts/sync_player_foul_splits.py`. Module C pre-loads at init via `_load_foul_splits_data()` — zero per-simulation DB connections. Added Feb 25 (Phase 8.17). |
| `player_empirical_modifiers` | Dynamic | Per-player data-driven modifiers replacing hardcoded multipliers. Columns: starter/bench stat mods (7 stats × 2 roles), per-stat stdev, WOWY lineup delta, depth slot. `UNIQUE(player_name, season)`. Computed nightly by `scripts/compute_empirical_modifiers.py` (2:30 AM). Module C pre-loads at init via `_load_empirical_modifiers()` — zero per-simulation DB connections. Module F uses empirical stdev via `_get_stat_stdev()`. N-gates: N≥10/role, N≥30 stdev, N≥10 WOWY with/without. Added Mar 21 (Empirical Modifiers Sprint 1). |
| `prop_line_snapshots` | Dynamic | Written by `module_b.snapshot_opening_lines()` daily; updated by `scripts/capture_closing_lines.py` (closing columns). **T5d (Mar 30):** 5 Pinnacle columns added — `pinnacle_line_over`, `pinnacle_line_under`, `pinnacle_odds_over`, `pinnacle_odds_under`, `pinnacle_captured_at`. Written by `scripts/capture_pinnacle_lines.py` (6:30 PM EDT via `capture_pinnacle_lines.yml`). `module_f.py` loads Pinnacle data into `self._pinnacle_cache` at init; STEAM_MOVE tag fires when `abs(pinnacle_line - opening_line) >= STEAM_THRESHOLD[stat]`. Note: `closing_line_over`/`closing_line_under` are 100% NULL (CLV capture broken by issue #37 Mar 1–21 regions mismatch) — these are NOT the same as Pinnacle PM columns. `player_name` stores non-accented names (ASCII). |
| `claude_analysis_log` | 6,402+ | Per-bet Claude curation log for feedback loop + Brier calibration. Written by `scripts/curate_plays.py` + `utils/claude_logger.py`. Key columns: `player_name`, `stat_category`, `bet_side`, `curation_grade` (STRONG/LEAN/FADE), `model_prob`, `true_edge`, `prompt_version`, `signal_available_at TEXT` (when the signal was available — anti-look-ahead gate), `acted_on_at TEXT` (when curation ran). `signal_available_at`/`acted_on_at` added Mar 31 (`8907581`) — unblocks Brier calibration anti-look-ahead fix. Note: `player_projections.player_id` is always NULL — JOIN key = `(player_name, game_date)`. See TD-023. |
| `ask_ludi_interactions` | Dynamic | Ask Ludi query/response log for local model training. Written by `bots/ask_ludi_handlers.py` `handle_message()` — one row per user message. Columns: `query_text`, `intent`, `response_text` (truncated to 2000 chars), `response_time_ms`, `session_id` (Telegram user_id as string). Primary training corpus for intent classification fine-tuning. Added Mar 29. |
| `pm_bot_messages` | Dynamic | PM bot briefing archive for local model training. Written by `utils/pm_bot.py` `generate_briefing()` + `send_break_message()`. Columns: `mode` (morning/session/nightly/break), `briefing_text`, `telegram_sent` (0/1). Added Mar 29. |
| `ludi_ops_log` | Dynamic | Company operations event log for local model training. Written via `utils/ops_logger.log_ops_event()`. Captures routing decisions, code review outcomes, ADRs, owner interactions. Columns: `event_type` (ROUTING/CODE_REVIEW/OWNER_INTERACTION/ADR/PROMPT_CHANGE), `actor`, `target_employee`, `task_type`, `input_summary`, `output_summary`, `outcome` (nullable), `blocker_reason`, `session_id`, `prompt_version`, `token_cost_usd`, `model`, `tags` (JSON string). Added Mar 29. |
| `roster_history` | Dynamic | Player team-change audit log: change_type, change_date, previous_team, status per season. |
| `shot_quality` | Dynamic | PBP Stats-derived per-game shot quality metrics: shot_quality_avg, leverage_score, wowy_on_off. |
| `player_workload` | Dynamic | Season rebounding + passing workload: contested_reb_pct, total_passes (NBA Tracking Phase 1.3). |
| `defender_matchups` | Dynamic | Per-player vs per-defender matchup stats: matchup_minutes, fg_pct vs specific defender (NBA Tracking Phase 1.3). |
| `player_game_tracking` | Dynamic | Per-game tracking: drives, catch-and-shoot, pull-up shooting, speed/distance (Module H Ghost Protocol, NBA.com). |
| `player_game_advanced` | Dynamic | Per-game advanced box score: off_rating, def_rating, net_rating, usg_pct, ts_pct, pace, PIE (Module H). |
| `player_clutch_stats` | Dynamic | Per-game clutch stats (±5 pts, last 5 min): clutch_pts, clutch_fga, clutch_fg_pct (NBA API). |
| `player_game_opponent` | Dynamic | Per-game opponent defensive stats: opp_pts, opp_reb, opp_ast allowed vs the player's team (Phase 3). |
| `player_game_hustle` | Dynamic | Per-game hustle stats: screen_assists, deflections, loose_balls_recovered, charges_drawn (Phase 4). |
| `player_wowy_stats` | Dynamic | Per-game WOWY on/off splits: on/off_court_off_rtg, on_off_diff, possessions (PBP Stats). |
| `referee_game_assignments` | Dynamic | Daily referee crew assignments: game_date, home_team, crew, source. PRIMARY KEY (game_date, home_team). |
| `referee_daily_stats` | Dynamic | Rolling 5-game referee stats: last5_fouls_avg, is_hot_whistle, is_fast_paced (NBAStuffer). |
| `depth_charts` | Dynamic | Official Tank01 depth charts: team_abbr, position, player_name, depth_order (1=starter). Updated daily (Phase 6.1). |
| `player_season_wowy` | Dynamic | Full-season on/off splits from PBP Stats: on/off_ortg, on/off_drtg, on_off_diff, Four Factors (Phase 6.3). |
| `team_leverage_profiles` | Dynamic | Team game-state efficiency: vh/h/l/overall ortg + efg_pct + pace per leverage tier (PBP Stats Sprint 3). |
| `player_leverage_usage` | Dynamic | Player crunch-time usage: clutch_usage_rate, vh_shot_attempts vs total_shot_attempts (PBP Stats Sprint 3). |
| `player_defensive_synergy` | Dynamic | Per-player defensive synergy playtypes: poss_per_game, ppp_allowed, fg_pct_allowed per playtype (Phase 7.9). |
| `team_scheme_cache` | Dynamic | Cached defensive scheme per team: season_style, 21d, 14d, active_style. PRIMARY KEY (team_abbr, scheme_type). Query WHERE scheme_type='DEFENSE'. |
| `player_injuries` | Dynamic | Live injury snapshots: status, injury_type, onset_date, snapshot_time, is_game_day_report, resolved_at (Phase 8.0). |
| `canonical_injury_statuses` | Dynamic | Reference table: status_code PK, severity_score, sim_multiplier, usage_vacuum_trigger, confidence_decay_hours (Phase 8). |
| `injury_language_map` | Dynamic | Source-phrase-to-canonical-status mapping: source_phrase, source, canonical_status, parse_type, confidence (Phase 8). |
| `game_notes_log` | Dynamic | Claude-generated S.A.V.A.G.E. game notes archive: game_id, run_date, notes_text. UNIQUE(game_id, run_date) (Phase 8.6). |
| `rotation_profiles` | Dynamic | Per-player situational minutes: avg_min_as_starter/bench/blowout/b2b/close_game, depth_order, window_days=21 (Phase 8.9). |
| `beneficiary_minutes` | Dynamic | Injury beneficiary analysis: out_player → beneficiary player minutes_delta across games_without (Phase 8.9). |
| `player_stagger_stats` | Dynamic | Two-man pairing on/off splits: pts/ast/reb/usg with/without partner_player, per season (Phase 8.9-B). |
| `player_stint_profiles` | Dynamic | Intra-game stint patterns: avg_first_stint_min, pct_games_q4_starter, avg_min_q4_when_close (Phase 8.9). |
| `nba_calendar` | Dynamic | Schedule metadata for every date including off-days: has_games, game_count, season_phase. Separate from `games` table (Phase 8). |
| `player_trends` | Dynamic | Pre-computed L7/L10/L15 + season_avg per stat per player: trend_label, streak_vs_avg. Stats: PTS/REB/AST/3PM/BLK/STL/TOV/PRA/PA/PR/RA/MIN (Phase 8.15). |
| `tank01_projections` | Dynamic | Tank01 fantasy projections: pts/reb/ast/stl/blk/tov/fantasy_pts. READ-ONLY benchmark — never fed into SAVAGE model. |
| `team_current_info` | Dynamic | Team standings + win/loss streaks: wins, losses, win_streak, conference_rank. Synced daily from getNBACurrentInfo. |
| `player_news_cache` | Dynamic | Daily player/team news from Tank01 getNBATopNews: headline, content, published_at. Dedup on (headline, published_at). |
| `player_injury_history` | Dynamic | Historical injury records: injury_date, return_date, injury_type, games_missed. *(source API dead — Tank01 getNBAInjuryListHistory confirmed 404 — table kept for future BDL/Perplexity data.)* |
| `player_season_averages_bdl` | Dynamic | BDL V2 season averages: stats_json, ppp, efg_pct, drives, avg_speed, deflections, box_outs, screen_assists (Sprint B). |
| `team_standings_bdl` | Dynamic | BDL V2 standings: wins, losses, win_pct, conference/division rank, home/away splits, ortg, drtg, pace (Sprint D). |
| `player_wowy_observed` | Dynamic | Starter-filtered WOWY: observed pts/reb/ast/min for beneficiary canonical_id when star_canonical_id is out. Trade-aware (Phase 2B). |
| `player_canonical_ids_staging` | Dynamic | Auto-ingest staging for unrecognized player IDs: source, source_player_id, seen_count. Auto-promotes after 3+ appearances. |
| `player_projections` | Dynamic | Full projection breakdown per simulated player: base_projection, modifier values (pace/fatigue/ref/blowout/scheme/empirical), percentiles (p10–p90), is_bet. NOTE: player_id is always NULL — JOIN key = (player_name, game_date). See TD-023. |

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
- SLASHER vs BLITZ defense -> +12% FTA
- RIM_RUNNER vs PERIMETER defense -> +30% OREB

**Team Defense Schemes (2025-26)** — Updated Mar 4 (Sprint 2):
- **PAINT_PACK**: BOS, CHI, CLE, DEN, IND, LAC, MEM, MIA, MIN, NYK, PHI, SAS
- **BLITZ**: ATL
- **PERIMETER**: BKN, CHA, GSW, ORL, PHX, SAC, TOR, WAS
- **NEUTRAL**: DAL, DET, HOU, LAL, MIL, NOP, OKC, POR, UTA

### 5. Tag Classification System
**What it does**: Assigns searchable tags to betting recommendations for filtering, analysis, and pattern recognition.

**Tag Categories:**
1. **ARCHETYPE TAGS** (1 per player): STRETCH_BIG, SLASHER, SNIPER, RIM_RUNNER, HELIOCENTRIC, GENERALIST
2. **SCENARIO TAGS** (0-4 per player): BENEFICIARY, USAGE_VACUUM, MINUTES_LIMIT, HOT_STREAK
3. **MATCHUP TAGS** (1 per game): vs_PAINT_PACK, vs_BLITZ, vs_PERIMETER, vs_NEUTRAL
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
