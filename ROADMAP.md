# Ludi-Bot Roadmap

**Last Updated:** Friday, February 27, 2026 — 4:09 PM EST
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** Module Audit Sprint (A+B+C complete → Module D next) + Phase 8.23 Layer 1 collecting (~Mar 10) + 2024-25 Backfill running (~Mar 3)
**Completed:** Module A Audit (Tiers A-F) ✅ + Module B Engine Rewrite (Tiers A-D) ✅ + Module C Oracle Audit (Tiers A-F + G1-G4) ✅

> **Ops Note (Feb 27 AM):** Internet outage overnight caused ~14 GH Actions runs to queue. 12 stale runs cancelled (6 Injury Refresh, Evening Slate Lock, 2 Closing Lines, 3 QA). Nightly Debrief ran successfully (yesterday's bets settled). Data Sync + PBP Stats completed. Queue is clear for today's schedule.

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
- [-] Module-by-module audit sprint — A through H + X: Modules A+B+C complete. Module D (`module_d.py`, `LudiYak`) is next.
  - **Module C cross-module notes (for future audits):**
    - **Module D**: James Harden AI blurb parse failure (`Expecting value: line 1 column 1`) fires repeatedly in integration test — Haiku returning empty/non-JSON. Needs graceful fallback + logging in `module_d.py`. Dedup fix (MEMORY.md) still pending.
    - **Module F**: G3 ramp-up players (Mobley, Duren) generate UNDER edges with `EDGE: Projection` label — should add `INJURY_RETURN` edge type to `module_f.py:_classify_edge_type()` (Phase 8.24 pattern) so these are identifiable in bet logs.
    - **module_h_historian.py**: BDL fallback abbreviation normalization **fixed this sprint** — `normalize_bdl_abbr()` now applied at write time. Verify in future audits.
    - **backtest_model.py**: `ConceptValidator` is mock-only (hardcoded PTS=20 stats). For real historical backtesting of G2/G3 effects, needs to pass actual historical game-log data + `player_id` for ramp detection. Deferred until 2024-25 backfill completes (~Mar 3).
    - **morning_brief.py / send_single_game_notes.py**: Both route through `build_simulation_scenario()` → `get_active_roster()` — automatically receive `GAMES_PLAYED` and game-count window fixes. No changes needed. ✓
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
