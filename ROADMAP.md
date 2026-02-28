# Ludi-Bot Roadmap

**Last Updated:** Saturday, February 28, 2026 — 3:54 PM EST
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** Sprint 4.5 (`module_a.py` attempt props markets + `fix_referee_profiles_pace.py` + `backfill_referee_bias.py`) + Sprint 4 (`_all_books` alt lines) — Odds-API reset ~7 PM EST tonight + Sprint 2 (`revalidate_recs.py`) — `is_valid` lifecycle + Phase 8.23 Layer 1 (~Mar 10)
**Completed:** Module F Alchemist Audit (avg_ev fix, B3 DB fallback removed, 7 bugs total) ✅ + canonical_games table (database.py + 5-module Pattern-B JOIN fix) ✅ + Module G star bias (`module_g.py`, `main.py`, `module_f.py`) — `get_player_crew_bias()` + crew_bias bet card notes ✅

> **Ops Note (Feb 27 AM):** Internet outage overnight caused ~14 GH Actions runs to queue. 12 stale runs cancelled. Nightly Debrief ran successfully. Queue clear.

> **Ops Note (Feb 28):** Odds-API quota resets midnight UTC March 1 (~7 PM EST tonight). Alt line Sprint 4 testing window opens then. Key test: confirm that `_all_books` dict in `fetch_comprehensive_props()` Phase 1 captures ±1.5/±3.0 alt lines from DK/FD responses — no extra API call needed. Use `--limit-games 1` test run first to inspect raw `_all_books` structure before any writes. Do NOT enable alt line writes to DB until structure is verified. Odds-API resets monthly at midnight UTC on the 1st.

This is the single source of truth for project tasks and priorities.

> **Agent Template Contract** — When updating this file, preserve the header format exactly:
> - `**Active Work:**` — short phrase(s) separated by ` + `. First item = current sprint focus.
> - `**Completed:**` — last 3 completions as separate ` + ` segments (PM bot reads `parts[-3:]`).
> - `### Current Sprint` → `**Next Actions:**` block — use `- [ ]` bullets for PM bot pending tasks.
> - Never put actionable next-steps ONLY in the Phase 8 table; the table is for status tracking only.

**Active Project Docs:**
- `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md` — BERT-derived prompt patterns
- `docs/projects/HISTORICAL_BACKFILL_2024_25.md` — 2024-25 backfill plan (~18k rows, 6-night automated)
- `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md` — Social Intel + Prop Pulse Score full spec
- `docs/FUTURE_DATA_SOURCES.md` — Ask Ludi architecture (§6) + competitive patterns (§5.2-B) + PBP Stats endpoints (§4.4)
- `best-practices/api/API_BEST_PRACTICES.md` — BDL + Tank01 + ESPN endpoint reference

---

## Legend

- `[ ]` = Todo
- `[-]` = In Progress
- `[x]` = Completed

---

## High Priority

### Current Sprint

- [-] Phase 8.13 — Ask Ludi Telegram Bot (`bots/ask_ludi.py`) — v1 live, data freshness layer shipped (ghost guard, slate context, freshness footers, ESPN fallback)
- [-] Phase 8.23 — Claude/Perplexity Feedback Loop — Layer 1 collecting (14-day scan window ~Mar 10)

**Next Actions:**
- [x] Phase 8.13: Build `bots/ask_ludi.py` — entry point, long-polling loop, `/start` + free-text handler
- [x] Phase 8.13: Build `bots/ask_ludi_db.py` — 8 intent handlers (injuries/edges/trends/schedule/recap)
- [x] Phase 8.13: Build `bots/ask_ludi_handlers.py` — Haiku intent → DB → Sonnet narrative → reply
- [x] Phase 8.13: Wire `scripts/launchd/com.ludi.askludi.plist` — macOS keepalive for self-hosted runner
- [x] Phase 8.13: Data freshness layer — full-day slate access + next-day after 9 PM EST for early research
- [x] Module-by-module audit sprint — Modules A through F complete ✅ (Feb 28)
  - **Module F audit complete (Feb 28):** `avg_ev` field fixed (`p['ev']` not `p['edge']`), Injury-Return emoji added, 4 defensive tags removed from `positive_archetypes`, B3 DB fallback replaced with clean wiring comment, old SGP correlation block removed, `_STAT_COL_MAP` short-form aliases added (`pts/reb/ast/stl/blk/tov/3pm/fg3m`), `_bdl_fallback_active` initialized in `__init__`.
  - **Module B enhancement (Feb 28):** `vs_scheme_cache` added — pre-loads last-5 game values per player/stat vs each defense scheme (live `team_scheme_cache.active_style`). L20/L15/L10/L5 windows + L5-vs-scheme all surfaced in CR1 note block. `time_context` column (EARLY_LOOK/AFTERNOON/PRE_GAME/LOCK_TIME) added to `bet_recommendations`.
- [x] `canonical_games` table (Feb 28) — `database.py` + `sync_canonical_games(conn)` importable function. 1926 raw games → 902 deduplicated rows. `module_b.py` DISTINCT CTE replaced. `module_g.py` + `populate_todays_games.py` wired to call sync after INSERTs. `sync_matchup_intelligence.py` (4 JOINs) + `team_defensive_classifier.py` (1 JOIN) fixed to prevent 3× row multiplication in DVP/scheme calculations.
  - **Remaining audit modules:** G (Zebras), H (Historian), X (Scenario Builder) — lower priority, schedule in March.
  - **Cross-module notes (carry forward):**
    - **Module D**: Harden AI blurb parse failure (`Expecting value: line 1 column 1`) — Haiku returning empty/non-JSON. Needs graceful fallback + logging. Dedup fix pending.
    - **backtest_model.py**: `ConceptValidator` is mock-only. Activate `LudiOracle(season='2024-25')` after backfill completes (~Mar 3).
    - **main.py**: `USG_PCT` key confirmed fixed at line 462. Verify in main.py audit sprint.
- [ ] **Sprint 4.5: Attempt props** — add `player_field_goals_attempted,player_free_throws_attempted,player_threes_attempted` to `module_a.py` markets string (~line 598); add `field_goals_attempted→fga`, `free_throws_attempted→fta`, `threes_attempted→fg3a` to `mk` dict in `main.py:build_reporter_input()`; add `'FG3A': 'proj_fg3a'` to STAT_MAPPING + `'fg3a': 'fg3a'` to `module_f._STAT_COL_MAP`. Test after Odds-API reset ~7 PM EST. **Full notes:** `memory/historical_odds_backfill_plan.md` (Sprint 4.5 section).
- [ ] **Run `fix_referee_profiles_pace.py`** — one-time DB repair: recalculates `avg_pace_impact` (fouls/12.5) + `style` thresholds in `referee_profiles` (Tony Brothers 0.413 → 1.387, NEUTRAL → STRICT). Safe to run anytime.
- [ ] **Run `backfill_referee_bias.py`** — populate historical `referee_player_bias` from 363 game dates (currently all `games_officiated=1` — backfill enables real PROTECTOR/STAR_KILLER signal).
- [ ] **Sprint 2: Dynamic Rec Lifecycle + Perplexity upgrade** — `is_valid` column, `revalidate_recs.py`, `midday_refresh.py` (2 PM + 4:30 PM EST), `perplexity_client.py` upgrades (per-player context, 5-min late news TTL). Full spec in `plans/pure-baking-river.md` PART 2B + 2C.
- [ ] **Sprint 4: Alt line testing + implementation** — Odds-API resets midnight UTC March 1 (~7 PM EST Feb 28).
  - **Test first (dry run):** `python main.py --limit-games 1 --verbose` → inspect raw `_all_books` dict to confirm ±1.5/±3.0 alt lines are captured per player/stat. Print `game['_all_books_debug']` or add temp logging. Do NOT write to DB until structure verified.
  - **Caching strategy:** Alt lines are slate-level data — cache alongside main props per `fetch_comprehensive_props()` call. No separate cache needed; they expire with the game slate.
  - **Credit-safe testing:** Odds-API charges per event request, not per market parsed. `_all_books` is populated from the SAME request as main props — zero extra credits for extracting alt lines from it.
  - **Implement:** Phase 2B in `module_a.py` (extract ±1.5/±3.0 → `game['alt_props']`) + Module F sweep (compare EV → inject note). Full spec in `plans/pure-baking-river.md` Sprint 4.
  - **Cross-module communication path:** Module A (`alt_props` on game dict) → `main.py:build_reporter_input()` passes `game` dict through → Module F reads `game.get('alt_props', {})` per bet → injects alt note into `bet_recommendations.note` column → Telegram card shows `"Alt: OVER 26.0 @ -138 available"`.
  - **Workflows that need updating after Sprint 4:** `morning_brief.py` (show alt note on bet card), `bots/ask_ludi_db.py` (alt note visible in edges intent), `settle_bets.py` (no change — alt note is metadata only).
- [ ] Research follow-up: Alt line edge sweep in `module_f.py` — sweep ±1.5/±3.0 alt lines per player, surface best-value alt line in bet card (confirmed by OddsJam + Outlier + Action Network — `COMPETITIVE_RESEARCH_2026.md` Tier 1)
- [ ] Research follow-up: Surface `player_injuries.snapshot_time` in `morning_brief.py` Telegram cards — "OUT (updated 5:18 PM)" format (confirmed by Outlier + StraightBettin)
- [ ] Research follow-up: Add `pct_money` + `diff` (money%-bets%) fields to Phase 8.22 `social_signals` — sharper than `pct_bets` alone (Action Network DIFF column + Outlier confirmed both signals)
- [ ] Research follow-up: Add `edges` intent to `bots/ask_ludi_db.py` — "Check [Player] [Line]" returns 11-row PropsMadness-style scorecard (L15 avg/hit, H2H, DVP rank, expected minutes, similar players) from existing tables — zero new data
- [ ] Research follow-up: Add `injuries` sub-intent "who benefits if X is out?" → `wowy_calculator.find_beneficiaries()` → delta table (name + PTS delta) in Ask Ludi reply (StraightBettin WOWY pattern)

---

### Phase 8: AI-Enhanced Pipeline (Remaining Sub-Phases)

**Principle:** LLMs orchestrate and reason — never calculate. Math stays deterministic.
**Completed:** 8.0-A/B/C/D + 8.2–8.17 + 8.21 + 8.24–8.28 ✅ — Full details: `docs/STATUS_HISTORY.md`

| # | Sub-Phase | Status | Description | Cost |
|---|-----------|--------|-------------|------|
| 8.8 | Game Score Formula v2 | LOW | Add line movement delta + handle% to `_score_game()`. **Blocked: needs Mar 2026 data.** | $0 |
| 8.11 | Ludi Power Ratings | LOW | Blended ortg+drtg+pace power ratings for game scoring + Ludi Lens. | $0 |
| 8.13 | Ask Ludi — Telegram Bot | TESTING | v1 live — `/start`, `/help`, 7 intents. Data freshness layer shipped: ghost injury guard, `build_slate_context()` cache, freshness footers, BERT prompt upgrade, ESPN fallback Source 4. | ~$0.02/day |
| 8.22 | Social Intelligence System | MEDIUM | Social sentiment + market signals → Prop Pulse Score injected into `curate_plays.py`. Architecture complete. See `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md`. | ~$0.02/day |
| 8.23 | Claude/Perplexity Feedback Loop | MEDIUM | Layer 1 LIVE — `claude_analysis_log` collecting. Wilson calibration at 14-day mark (~Mar 10). Inject into `_get_system_wr_context()`. | $0 |

---

### Database Architecture Strategy

**Current State:** Single SQLite database (`ludi.db`) — ~30 MB, 40+ tables

**Phase 1: Consolidation** ✅ COMPLETE — Single source of truth, direct SQLite writes, no JSON staging

**Phase 1.5: 2024-25 Historical Backfill** ← IN PROGRESS (~Mar 3 completion)
- [-] Module H auto-backfill running — 174 dates, ~6 nights at 200 Tank01 req/day
- [ ] BDL advanced stats + SportsDataIO enrichment fill new rows automatically
- **Full plan:** `docs/projects/HISTORICAL_BACKFILL_2024_25.md`

**Phase 2: Multi-Season Support (Before 2026-27 Season)**
- [ ] Add season archive workflow: `archives/data/ludi_YYYY_YY.db`
- [ ] Create `scripts/archive_season.py`
- [ ] Document season rollover in `docs/SEASON_ROLLOVER.md`

**Phase 3: Web App Migration (When Ludi Lens Launches)**
- [ ] Evaluate PostgreSQL vs SQLite for production
- [ ] Design API layer between frontend and database

---

## Medium Priority

### Ludi Lens Dashboard (Post-Phase 8 — Web App Sprint)
**Blocked until:** Phase 8 complete + dedicated web app sprint
**Design identity:** Dark Navy #0F172A, Gold #FBBF24, Emerald #10B981 | "The Edge, Magnified" theme
- [ ] Streamlit app scaffold (`app.py`)
- [ ] "The Edge, Magnified" visual design implementation
- [ ] Real-time prop display integration
- [ ] Historical performance charts

### Infographic & Data Visualization System (Post-Phase 8 — Frontend Sprint)
**Blocked until:** Phase 8 backend cleanup complete
**Full plan:** `docs/projects/INFOGRAPHIC_VISUALIZATION_SYSTEM.md`
**PaperBanana pattern adopted:** LLM writes matplotlib code → `exec()` in subprocess → base64 JPEG (see research Feb 25)
- [ ] Phase V1: `utils/chart_engine.py` (Plotly + Kaleido) + 6 MVP charts:
  - Hit Streak Tracker (Player Cards)
  - Archetype Leaderboard Top 10 / Bottom 10 (Game Notes + Weekly Update)
  - Matchup Edge Heatmap compact/full (Game Notes + Weekly Update)
  - Hot / Cool Players — L7 delta vs season avg (Weekly Update + Morning Brief)
  - Stat Confidence Grade Matrix (Morning Brief)
  - Daily P&L Waterfall (Nightly Debrief)
- [ ] Phase V2: Edge vs WR scatter, player trend sparklines, tier performance
- [ ] Phase V3: Full catalog + `scripts/generate_all_charts.py`
- [ ] Phase V4: Streamlit integration + PaperBanana AI-assisted ad-hoc chart generation

### CLV Tracking Enhancement
- [ ] CLV reporting in PM Bot daily summary
- [ ] 30-day rolling CLV metrics

### Historical Odds Backfill (March 2026)
~5,593 bets lost Jan 8–Feb 1 due to `clean: true` bug. Recoverable via The-Odds-API `/v4/historical/`.
- [ ] Backfill historical odds (~10 credits/query)
- [ ] Re-run pipeline for 15 missing dates and settle bets
- **Blocked until:** March 2026 (Feb Odds API quota exhausted)

### Data Pipeline Improvements
- [ ] **Trade-aware sim context**: When a traded player returns from injury, verify Module C/E use correct team for matchup modifiers and L5/L10 stats split by pre/post-trade. `players.team` is correct (roster sync), but `player_game_logs` history is all on old team — could skew projections.
- [ ] Consolidate WOWY scripts (`sync_wowy_hybrid.py` + `sync_pbp_wowy.py` — duplicate work)
- [ ] PBP Stats: wire `get_possessions` endpoint → clutch detection + blowout tax validation (Section 4.4 in `docs/FUTURE_DATA_SOURCES.md`)
- [ ] Ghost Protocol date-skip optimization: pre-check `team_lineups` before scraping each date (~30s saved)
- [ ] Multi-book arbitrage detection
- [ ] Steam move detection (rapid line movement alerts)

### GH Actions / Claude Ops Improvements
- [ ] **PR review action**: Add `anthropics/claude-code-action@v1` to PR events for automated code review on push to main
- [ ] **`pip-audit` step**: Add to `data_sync.yml` — fails build on known CVEs in `requirements.txt`
- [ ] **Weekly Claude cost report**: `scripts/claude_cost_report.py` — reads `claude_usage_log`, sends weekly $/1k-token summary
- [ ] **Token budget guard**: `max_tokens` cap in `claude_client.py` per task type (Haiku=200, Sonnet=800)
- [ ] **Ask Ludi bot management workflow**: `bot_management.yml` — start/stop/status commands via launchd
- [ ] **Schema validation script**: `scripts/validate_schema.py` — assert all expected columns exist at pipeline start
- [ ] **OAuth token refresh reminder**: Warn in `claude-ops-hub.yml` when `CLAUDE_CODE_OAUTH_TOKEN` is >25 days old

---

## Low Priority

### Future Enhancements
- [ ] DFS multiplier conversion (PrizePicks/Underdog)
- [ ] Strength of Schedule (SOS) adjustment
- [ ] Shooting Luck Deviation signals
- [ ] Sync PlayerRebounding tracking data (contested vs uncontested %)

### Live Betting Pipeline (post model-math verification)
**Blocked until:** Model hit rate + CLV verified over 90-day window (est. May 2026). ESPN RSS is planned corroboration source.

### Developer Workflow Improvements
- [ ] **Session start checklist**: `scripts/session_check.py` — quick health check (DB rows, API quota, last sync time) in <5s
- [ ] **`AGENTS.md`**: Create agent operating guide (primary rules for Codex-style agents)
- [ ] **GH workflow shortcuts**: `scripts/run_workflow.sh <name>` wrapper for `gh workflow run`
- [ ] **`/compact` habit**: Use before context fills — prevents losing work mid-session
- [ ] **End-of-session memory update**: Always update `memory/MEMORY.md` at session end

---

## Archive

- **docs/STATUS_HISTORY.md** — Phases 1–4 history + Phase 8 sprint archive (Feb 20–25, 2026)
- **docs/archive/phase_reports/** — Phase completion reports (Phases 1–7)
- **docs/audit/AUDIT_2026_02_21.md** — Full 10-sprint audit report (0 critical issues, production-ready)
- **reports/** — Calibration analysis, performance breakdowns
- **docs/ARCHITECTURE.md** — System design, module reference, DB schema
- **docs/METHODOLOGY.md** — Edge calc, devigging, CLV tracking
- **best-practices/** — API patterns, sportsbook tiers, lessons learned
