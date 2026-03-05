# Status History Archive

This file contains the chronological status updates from the Ludi-Bot project. For current tasks and priorities, see `ROADMAP.md` in the project root.

---

## Current Status (as of March 4, 2026)

- **Phase**: Phase 6.5d Player ID Remediation and Firewall Implementation
- **Goal**: Remediate systemic ID contamination and enforce canonical NBA ID integrity.
- **Achievement**: 100% of Tank01 composite IDs in `player_game_logs` and 7 other tables resolved and remediated. Mandatory 4-tier database firewall implemented in `database.py`.

---

## Player ID Remediation & Firewall (March 4, 2026) - COMPLETE

**Strategic Achievement:** Prevented long-term database pollution from Tank01 composite IDs by implementing a multi-tier firewall and remediating all existing dirty data.

### Remediation Results
- **Tables Cleaned (8 total):** `player_game_logs`, `player_game_advanced`, `player_game_tracking`, `player_game_opponent`, `player_game_hustle`, `player_clutch_stats`, `beneficiary_minutes`, `player_season_averages_bdl`.
- **Row Count:** ~45,000 rows remediated from Tank01 composite IDs to canonical NBA IDs.
- **Ratio:** Clean ID ratio in `player_game_logs` improved from ~70% to **96.83%**. Residual dirty IDs are unresolvable new players (staged for manual review).

### Database Firewall (4-Tier)
Implemented `LudiHistorian.resolve_player_id_for_insert(id, name)` in `database.py`:
1. **Exact Match:** Pass-through for valid canonical IDs.
2. **Alias Lookup:** Checks `aliases` and `tank01_aliases` JSON columns.
3. **Name Resolution:** Resolves via `PlayerIDResolver` + auto-registers the input ID as an alias for future-proofing.
4. **Fallback:** Logs warning and returns original ID (stages for manual review).

### Integration Points
Firewall wired into all critical ingestion and processing scripts:
- `sync_browser_backfill.py` (Ghost Protocol)
- `sync_bdl_season_averages.py`
- `build_rotation_profiles.py`
- `module_h_historian.py`
- `module_b.py` (LudiEngine cache loading)

---

## Phase History Summary (Jan–Feb 2026)

Content from Jan 2026 phases archived to `docs/archive/phase_reports/PHASES_1_4_AND_INFRA_SUMMARY.md`.

| Phase | Date | Key Achievement |
|-------|------|-----------------|
| Week 1: Foundation | Jan 7, 2026 | All 9 modules production-ready (73,232 LOC), Tank01 + Odds API integrated |
| Week 2: Data Sync + Tags | Jan 8, 2026 | 12k+ logs backfilled, 4-category tag classification system |
| Week 4: Module G | Jan 15, 2026 | Referee intelligence — 78 refs, 4 impact types, star bias engine |
| Phase 1: Synergy | Jan 21, 2026 | NBA Synergy playtypes → Module E (PPP modifier, Def Diff%, Drives assist) |
| Phase 3: Matchups | Jan 21, 2026 | ISO/P&R/SpotUp vs defense scheme matrix (14+ modifiers) |
| Phase 4: B2B Fatigue | Jan 21, 2026 | Research-backed fatigue modifiers, 60-day backtest +0.56 pts mean error |
| Twin Engine Upgrade | Jan 19, 2026 | Ghost Protocol (NBA.com) + PBP Stats shot quality — dual-engine Super Signal |
| Infrastructure v2 | Jan 19, 2026 | Docker containment, WAL mode, Keymaster Protocol, supply chain defense |

---

## Phase 8 AI-Enhanced Pipeline — Sprint Archive (Feb 20–24, 2026)

### Production Pipeline / WOWY / Settlement Fix ✅ COMPLETE (Feb 21, 2026)

Pipeline had been failing 5 consecutive days (Feb 17-21). WOWY sync timing out every run. Duplicate settlement notifications.

**P0 — Daily Production Pipeline (5-day outage):**

- `daily_simulation_pipeline.yml`: Added `continue-on-error: true` to "Verify data freshness" and "Run System Health Monitor" steps. Diagnostic steps no longer kill a pipeline that successfully generated bets.
- `monitor_system_health.py`: Tightened critical alert filter — only `'Table is empty'` or `'Database connection failed'` are critical. Odds API quota exhaustion no longer triggers `exit(1)`.

**P1 — WOWY Sync Timeouts:**

- `sync_wowy_hybrid.py`: Removed `@retry_with_backoff` decorator (double retry: 3 decorator × 3 outer loop = 9 attempts × 180s). Reduced `REQUEST_TIMEOUT` 180→60s. Fixed Ghost Protocol threshold: `api_failures >= 2` → `>= 1` (was unreachable for `--days 1`).
- `wowy_sync.yml`: Increased workflow timeout 30→45 min (Ghost Protocol needs 10-15 min after API fails).
- **Data source investigation:** BDL has no WOWY capability. PBP Stats is viable future Tier 3 (7 endpoints already in `pbp_stats_client.py`, not wired to `team_lineups`). popcornmachine.net not useful.

**P2 — Settlement Notifications:**

- `settle_bets.py`: Removed per-date Telegram sends (5 AM). 6 AM aggregate summary (`send_settlement_summary.py`) is the single notification now.

---

### Feb 20 Post-All-Star Break Audit ✅ COMPLETE (Feb 20, 2026)

First game day back exposed 9 critical/high issues. Full recovery + hardening completed before 6 PM pipeline.

**Bugs Fixed:**
- Module H `ON CONFLICT` mismatch → 8 days of silent game log insert failures (all game logs now syncing)
- `anthropic` missing from `requirements.txt` → all Phase 8 AI features were silently disabled in CI since launch
- Health monitor false failures → exited 1 on stale data, pipeline marked failed daily despite generating 213+ bets
- BDL milestone market type → corrupt odds (-2, -4, -9) produced 50× payout multiplier (+269u phantom P&L)
- `generate_report()` 3-tuple callers → 4 files, 6 callers fixed
- `player_game_logs` settle → 1,947 PUSH bets settled to 998W/863L/81V after backfill
- Referee sync → NBA.com consent popup blocked Playwright; skips date toggle for today's slate

**Hardening Added:**
- BDL vendor quality filter (DK/FD/Caesars/BetRivers/BetMGM only) + modal line ≥2 vendor requirement
- `scripts/backfill_games_bdl.py` — reusable when Odds API is down
- P&L sanity gate in settlement summary (±50u triggers Slack alert)
- `team_lineups.created_at` backfilled (17,368 rows had NULL)
- 4 missing packages added to `requirements.txt` (anthropic, PyYAML, schedule, tabulate)
- BDL API best-practices docs — comprehensive endpoint reference + audit lessons

---

### Ask Ludi Architecture Research ✅ COMPLETE (Feb 20, 2026)

Researched Telegram + Claude integration patterns across 5 sources (Medium articles, GitHub repos, docs). Full notes in `docs/FUTURE_DATA_SOURCES.md` §6 and `memory/MEMORY.md`.

**Implementation Plan (3 files, ready to build):**
- `bots/ask_ludi.py` — Entry point, long-polling loop, `/start` + free-text handler
- `bots/ask_ludi_db.py` — Read-only SQLite queries, 8 intent handlers (injuries/edges/trends/standings/schedule/recap/free/fallback)
- `bots/ask_ludi_handlers.py` — Intent → Haiku classification (JSON output) → DB fetch → Sonnet narrative → reply
- `scripts/launchd/com.ludi.askludi.plist` — macOS launchd keepalive (runs on self-hosted Mac runner)

**Key Design Decisions:**
- `python-telegram-bot` v21+ (async, long polling — no webhook/public IP needed)
- Haiku for intent ($0.0001/call, <200ms) → Sonnet for analysis (max_tokens=600)
- `sqlite3.connect("file:ludi.db?mode=ro", uri=True)` — read-only, WAL-safe, can't corrupt pipeline
- `CLAUDE_CODE_OAUTH_TOKEN` correctly used in `claude-code-action@v1` only (not SDK calls)

---

### Injury Intelligence Hardening ✅ COMPLETE (Feb 20, 2026)

Second sprint of Feb 20 — closed remaining injury pipeline gaps and built intraday refresh infrastructure.

**New Capabilities:**
- **RealGM RSS** added as 2nd corroboration source alongside RotoWire. `_nuance_check()` compares both; when they agree → confidence bumped to 0.95 (`[2-source confirmed]`)
- **AI blurb prompt** hardened: centralized `INJURY_BLURB_SYSTEM` + `INJURY_BLURB_PARSE_PROMPT` with 5 few-shot examples, `tonight_available` field (true/false/uncertain), `blurb_is_stale` flag, `temperature=0.0` for deterministic classification
- **`injury_refresh.yml`**: new GitHub Actions workflow — 4 daytime runs (every 2 hr, 11 AM–5 PM EST) + 15 evening runs (every 20 min, 6–10:40 PM EST). Staleness guard in `sync_injuries.py` exits early if DB is already fresh — protects Tank01/BDL quota
- **Evening slate lock**: `--force` injury sync step before `morning_brief --mode evening` captures 4–6 PM late scratches in DB before 6 PM cards generate
- **`--force` flag** on `sync_injuries.py` for on-demand overrides (web app, bot, evening lock)
- **Downstream ready**: Telegram bot (8.13) and Ludi Lens web app query `player_injuries` directly — always ≤20 min stale during game time

---

### Morning Brief Pipeline Hardening + BetIQ Research ✅ COMPLETE (Feb 20, 2026)

Third sprint of Feb 20 — hardened the morning/evening brief pipeline and completed competitive analysis.

**Pipeline Fixes (both morning + evening modes):**
- **Native Telegram text:** Removed `send_photo` + image card pipeline from `morning_brief.py`. Both morning and evening modes now send chunked native text (4000-char splits). No more PIL/PNG dependencies in briefing flow.
- **All-game processing:** Removed January hardcoded watchlist (`['PHX','MIA','CHI',...]`). Set `target_teams=None` — all games on the slate are now processed and scored by the tier-weight algorithm. Tonight's IND@WAS was previously invisible.
- **Spotlight Markdown fallback:** Claude spotlight outputs truncated to 4000 chars and retried as plain text on 400 Bad Request. Fixes Kyle Anderson-style failures.
- **Injury `skip_resolve` bug:** `sync_to_database()` called twice in `sync_injuries.py main()`. Step 4 RSS call (7 players) was resolving all 34+ BDL/Tank01 injuries because they weren't in the RSS batch. Fixed with `skip_resolve=True` parameter — RSS call now only adds, never sweeps.
- **`.gitignore` hardening:** Added `archives/data/`, `logs/health/`, `*.png` to gitignore.

**Competitive Research:**
- BetIQ/TeamRankings 3-session sprint — 6 cross-game ATS/O-U patterns confirmed across CLE@CHA, DAL@MIN, IND@WAS. 20+ power rating dimensions mapped. Tier 1 features all buildable from existing `ludi.db` (no new APIs). Doc: `docs/research/BETIQ_TEAMRANKINGS_RESEARCH.md`

---

### ESPN Research, Suspension Intelligence & Pipeline Hardening ✅ COMPLETE (Feb 21, 2026)

**ESPN API Research (3-session sprint):**
- Confirmed ESPN has no official NBA injury API — PDF-only (timestamped, no predictable URL). No direct endpoint.
- ESPN public API (`site.api.espn.com`, `sports.core.api.espn.com`) verified live: injuries per game (shortComment/longComment/returnDate), DraftKings game lines (spread/O/U/ML open+close+live), scoreboard, news. **No player props** in any ESPN endpoint.
- DraftKings pickcenter: game-level only (spread, O/U, moneyline with juice). No H1/H2 or Q1/Q4.
- ESPN `longComment` names beneficiaries — potential future replacement for some Perplexity calls (free).
- Full ESPN client plan documented at `~/.claude/plans/`. Integration (Phase 8.21) covers: ESPN client, espn_id crosswalk, game injuries enrichment, Tier 3 game lines fallback, longComment corpus for prompt training.

**Phase 8.16 — Suspension Intelligence via ESPN (implemented same session):**
- `scripts/sync_suspensions_espn.py`: 30-team scan, ESPN `INJURY_STATUS_SUSPENSION` type, returnDate, auto-resolve on expiry
- First run found 5 active suspensions previously invisible to pipeline: Paul George (PHI, 32d, anti-drug), Isaiah Stewart (DET, 10d), Miles Bridges + Moussa Diabate (CHA, 3d), Rudy Gobert (MIN, 3d — same-day flagrant foul #6 catch)
- Wired into `data_sync.yml` after injury sync step. $0 cost.

---

### BDL V2 Full Integration + SportsDataIO Enrichment ✅ COMPLETE (Feb 22, 2026)

**Goal:** Eliminate Ghost Protocol advanced scraping dependency, fill critical `player_game_logs` gaps (started, fantasy pts, home/away, doubles), and replace NBA.com synergy scraping with BDL playtype API. All on existing GOAT tier ($39.99/mo, no new cost).

**4 sprints shipped (commits 5d8576b + 6ccf4b6):**

- **Sprint A — SportsDataIO enrichment** (`sync_sportsdata_enrichment.py`): Populates `started`, `fantasy_pts_dk`, `fantasy_pts_fd`, `home_or_away`, `double_doubles`, `triple_doubles` in `player_game_logs`. 3-day rolling default (3 API calls/day, 100/day budget). Backfill: 13,706 rows across 90 prior-season dates.
- **Sprint B — BDL V2 advanced stats** (`sync_bdl_advanced_stats.py`): Daily advanced ratings (off/def/net rating, pace, PIE, usage, true shooting) + hustle (deflections, box outs, screen assists, charges drawn) + tracking (speed, distance, touches, passes). **Replaces Ghost Protocol advanced scraping.** Backfill: 82,785 advanced + 16,716 hustle + 12,804 tracking rows across 115 dates.
- **Sprint C — BDL plus_minus fill** (`sync_bdl_plus_minus.py`): Tier 2 fill — COALESCE, never overwrites Tank01/SportsDataIO. Coverage: 58.9% → **99.2%** (18,260/18,405 rows).
- **Sprint D — BDL season averages** (`sync_bdl_season_averages.py`): Weekly sync of all 18 category/subtype combos (general/tracking/hustle/shotdashboard/playtype) to `player_season_averages_bdl`. **Replaces Ghost Protocol synergy (NBA.com) scraping.** 7,958 rows, 100% canonical_id coverage. Standings to `team_standings_bdl`.

**Ghost Protocol demotion:** `--skip-advanced` flag added; synergy NBA.com step removed from `ghost_protocol_sync.yml`. Ghost Protocol now handles only: drives/C&S/pull-up per game, closest defender, clutch stats.

**Canonical ID hardening:** `_resolve_canonical_ids()` baked into season averages sync. 5 missing players added to `player_canonical_ids` (Cameron Payne/1626166, Trevor Keels/1631211, Alondes Williams/1631214, Patrick Baldwin Jr./1631116, Dillon Jones/1641794) — verified via `nba_api.stats.static.players`.

**Note:** `SPORTSDATA_API_KEY` must be added as a GitHub Actions secret for the enrichment step to run in CI.

---

### Evening Lock Bug Fixes & Injury Intelligence Tightening ✅ COMPLETE (Feb 21, 2026)

**Root cause:** Phase 8.18 introduced `UnboundLocalError` in `module_e.py` (odds/total/spread used before assignment in section 3.6). With `USE_TEAM_TOTALS_MODIFIER=True`, every game silently failed, producing zero Telegram output. Pipeline showed "success" (exit 0) so no alerts fired.

**9 fixes across 7 files:**
- `module_e.py`: Move odds/total/spread extraction before section 3.6 (root cause of silent outage)
- `morning_brief.py`: `sys.exit(1)` when no bets processed → workflow now fails loudly + triggers Claude Ops Hub
- `morning_brief.py`: Game notes markdown fallback (Markdown→plain text on 400, matching spotlight pattern)
- `morning_brief.py`: `snapshot_time >= datetime('now', '-14 days')` staleness guard on all 3 `player_injuries` queries — eliminates ghost records from mid-season DB init appearing as currently OUT
- `main.py`: Tier 2 NOT EXISTS guard — player with resolved injury + new same-day OUT was classified as WELCOME_BACK instead of OUT (Embiid pattern). Beneficiary vacuum now fires correctly.
- `morning_brief.py`: Skip games tipped >45 min ago (ORL@PHX 5pm processed at 6pm evening lock)
- `utils/perplexity_client.py`: Empty response logs HTTP status code; `_get_recency_filter()` switches "hour"/"day"/"week" based on hours_to_game (Ludi-Lite pattern — tighter search pre-tip, cheaper on morning runs)
- `utils/time_utils.py`: `get_time_context()` + `format_time_context_note()` — EARLY_LOOK/AFTERNOON/PRE_GAME/LOCK_TIME modes based on EST hour. Foundation for bot + web app confidence display.
- `utils/claude_prompts.py`: `{time_context_note}` row in GAME_NOTES_TEMPLATE — Claude calibrates certainty to data confidence at call time
- `CLAUDE.md`: 2025-26 season reminder added to Critical Data Rules — prevents AI roster drift

**Industry research:** NBA official injury report now publishes every 15 min (2025-26 rule). Our RotoWire + RealGM dual-source corroboration already matches industry standard. Perplexity hours_to_game filter borrowed from Ludi-Lite for cost-efficient dynamic recency.

---

### Data Sync Pipeline Fix + PBP Stats Split + Module H BDL Fallback ✅ COMPLETE (Feb 23, 2026)

Daily Data Sync was cancelled after 60 minutes — 3 PBP Stats scripts consumed 55 of the 60-min job budget, causing 22 downstream steps to be skipped entirely. Ops Hub didn't fire because it only triggered on `failure`, not `cancelled`.

**Fix 1 — PBP Stats Split (`pbp_stats_sync.yml`):**
- Moved `sync_pbp_wowy.py`, `sync_four_factor_wowy.py`, `sync_team_leverage_profiles.py` to own workflow (Mon/Wed/Fri 5 AM EST, 90-min budget). Season-aggregate data doesn't need daily refresh. Cuts PBP Stats API calls 57% (7,140/week → 3,060/week).

**Fix 2 — Ops Hub `cancelled` trigger:**
- `claude-ops-hub.yml` now fires on both `failure` AND `cancelled` conclusions. Also monitors the new `PBP Stats WOWY Sync` workflow.

**Fix 3 — Python-level hardening:**
- Wall-clock guards (`MAX_RUNTIME_SECONDS`) in all 3 PBP Stats scripts — exit gracefully with checkpoint before step timeout kills the process.
- `utils/pbp_stats_client.py`: HTTP timeouts lowered (120s→60s primary, 180s→90s fallback). User-Agent updated to Chrome/131.

**Fix 4 — Module H BDL fallback:**
- `module_h_historian.py`: When Tank01 returns 0 games for a date, automatically falls back to BDL `get_box_scores()`. Uses canonical ID resolution and COALESCE pattern. Prevents silent 0-row ingestion (Feb 22 bug: 11 games/382 players existed but Module H ingested nothing).

**9 files changed:** `pbp_stats_sync.yml` (new), `data_sync.yml`, `claude-ops-hub.yml`, 3 PBP Stats scripts, `pbp_stats_client.py`, `module_h_historian.py`, `sync_bdl_plus_minus.py`.

---

### Injury Pipeline Hardening + ESPN Injury Source + Referee Timing Fix ✅ COMPLETE (Feb 23, 2026)

Tonight's evening lock revealed 3 systemic problems: (1) Jaren Jackson Jr. (UTA, injured) shown as healthy — no entry in `player_injuries`, BDL/Tank01 not yet reporting; (2) Nurkic (UTA, OUT) injury in DB from RSS but `team_abbreviation` blank → query excluded him silently; (3) referee sync runs at 9:30 AM but morning brief at 9:00 AM — race condition every day.

**Root cause confirmed via live DB queries and workflow logs — no assumptions.**

**Fix 1 — `player_canonical_ids` as name resolution source:**
- `sync_injuries.py`: Added `_normalize_for_canonical()` (Unicode NFD accent strip + suffix removal: Jr./Sr./III) and `_get_canonical_lookup_from_db()` (normalized_name → full_name + team).
- Team resolution in `sync_to_database()` now routes through `player_canonical_ids.normalized_name` instead of `players.name` with `.lower()` only.
- Canonical `full_name` now stored in `player_injuries.player_name` (e.g. `Jusuf Nurkić` not `Jusuf Nurkic`) — ensures consistent downstream name matching.

**Fix 2 — Dedup guard in `sync_injuries.py`:**
- INSERT now skips if identical `(player_name, status, DATE(snapshot_time))` already exists today. Eliminates Naji Marshall 7-duplicate-row pattern.

**Fix 3 — Resolve scope scoped to non-ESPN sources:**
- BDL/Tank01 resolve step now filters `AND source NOT IN ('ESPN', 'espn_suspension')` — prevents BDL from wiping ESPN-sourced injuries when BDL API hasn't caught up yet. ESPN resolves its own.

**Fix 4 — ESPN as faster injury source (`scripts/sync_injuries_espn.py` — partial Phase 8.21):**
- New script following `sync_suspensions_espn.py` pattern. 30-team scan via `sports.core.api.espn.com` (free, no auth, 15-30 min lag vs BDL/Tank01 2-6 hr lag).
- Maps ESPN `displayName` → `player_canonical_ids.normalized_name` for canonical name + team resolution.
- Skips suspensions (type_id=17) — those belong to `sync_suspensions_espn.py`.
- Source-scoped resolve: only resolves its own `source='ESPN'` entries.
- Wired into: `daily_briefing.yml` (before morning briefing), `evening_slate_lock.yml` (before force injury sync), `injury_refresh.yml` (first step every 20-min cycle).

**Fix 5 — Morning brief injury query hardened:**
- UNION clause added: catches injuries where `team_abbreviation` is blank via `player_canonical_ids` join (the Nurkic bug).
- `AND (days_out IS NULL OR days_out < 75)` filter: Steven Adams (220d) and season-ending outs no longer consume Claude's 600-char injury context budget.
- Status conflict dedup: when ESPN and BDL/Tank01 report different status for same player, highest-severity wins (OUT > DOUBTFUL > GTD). Prevents Claude seeing same player listed twice.
- `if not player_name: continue` guard in spotlight to prevent None names flowing through.

**Fix 6 — Referee timing + popup:**
- `daily_briefing.yml` moved from 9:00 AM → 11:00 AM EST. Morning brief now runs after referee_sync (9:30 AM) and simulation pipeline (10:00 AM). Refs always in DB when brief generates.
- `module_g.build_ref_database()`: DB-first check added. If `games.referee_crew` populated for today → load from DB, skip Playwright. Eliminates 3× redundant browser scrapes per briefing.
- `utils/browser_utils.py` + `browser_utils_async.py`: Consent button selectors (`has-text("Accept/Agree/I Accept")`) added before OneTrust block. `setup_page()` helper added for JS dialog auto-dismiss.
- `scripts/sync_daily_referees.py`: Removed redundant consent block (now handled by `close_popups()`).

**Phase 8.21 status update:** ESPN injury pipeline (this sprint) complete. Remaining Phase 8.21 items deferred: ESPN client utility, athlete ID crosswalk, game lines Tier 3 fallback, longComment corpus.

**11 files changed:** `sync_injuries.py`, `sync_injuries_espn.py` (new), `morning_brief.py`, `module_g.py`, `utils/browser_utils.py`, `utils/browser_utils_async.py`, `scripts/sync_daily_referees.py`, `daily_briefing.yml`, `evening_slate_lock.yml`, `injury_refresh.yml`, `ROADMAP.md`.

---

### Canonical Table Hardening + ESPN Integration Foundation ✅ COMPLETE (Feb 24, 2026)

- `player_canonical_ids` CREATE TABLE restored to `database.py` (was orphaned — comment acknowledged it but code didn't create it). Migration guard added for `espn_id` column via `ALTER TABLE ... ADD COLUMN` in try/except.
- `canonical_teams` table (30 rows) added: `standard_abbr` (PK), `full_name`, `bdl_abbr`, `tank01_abbr`, `espn_id`. Single source of truth for all BDL/Tank01/ESPN team ID mappings.
- `normalize_bdl_abbr()` centralized in `utils/mappings.py` — replaces 6 copy-pasted dicts. Both directions idempotent: `normalize_bdl_abbr('GS')='GSW'`, `normalize_bdl_abbr('GSW')='GSW'`.
- `scripts/build_espn_crosswalk.py` added: scans ESPN `athletes` endpoint per team, normalizes `displayName` → `player_canonical_ids.normalized_name`, writes `espn_id`. Wired into `weekly_validation.yml`.
- ESPN team IDs loaded from DB: `sync_suspensions_espn.py` + `sync_injuries_espn.py` call `_load_espn_team_ids(conn)` → `canonical_teams`; hardcoded fallback kept for safety.

### Claude Name Resolution Pipeline ✅ COMPLETE (Feb 24, 2026)

- `resolve_canonical_name(conn, name)` added to `utils/player_id_resolver.py`. NFKD normalize → look up `player_canonical_ids.normalized_name` → return `full_name`. Graceful fallback (returns original on any error).
- Wired into 4 Claude injection points: `curate_plays._fetch_player_injury()` (Haiku sanity gate was returning "No injury on record" for OUT accented players), `morning_brief.py` (hit rate query + spotlight name), `trend_engine.get_matchup_analysis()` (covers all 5 matchup helpers), `classify_archetypes.py` (dual-form lookup for Jokić/Nurkić/Dončić).
- `classify_archetypes.py`: `_strip_accents()` helper added. `get_player_synergy()` + `get_player_season_advanced()` try exact match first, then accent-stripped fallback. Prevents silent GENERALIST downgrades.
- `trend_engine._resolve_player_id()` tier 4 added: canonical fallback after the 3 existing tiers.
