# Ludi-Bot Roadmap

**Last Updated:** Thursday, March 5, 2026 — 10:42 AM EST
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** Sprint 2 (`revalidate_recs.py`, `midday_refresh.py`) — Dynamic Rec Lifecycle + Perplexity upgrade (`is_valid` column, 2PM+4:30PM midday refresh, `perplexity_client.py` upgrades) + employee onboarding docs
**Completed:** CLV hardening (`module_b.py`, `db_backup.yml`, `morning_brief.py`) — game_date logger fix, closing lines wired nightly, stat_category case fix, bench filter, Feb 27–Mar 1 backfill ✅ + Curation v2 (`curate_plays.py`, `game_dossier.py`) — full-slate grading, 3-layer decision tree, shared dossier cache, BERT Pattern 2 prompt, evening guard ✅ + Pipeline Reliability (`database.py`, `sync_browser_backfill.py`) — DB lock cascade fix, Ghost Protocol Lastname/Firstname firewall, extract_id_from_href restored, dead script ref removed ✅

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
- `docs/projects/AI_EMPLOYEE_WORKFORCE.md` — AI Employee Workforce PRD (6 employees, OpenClaw runtime, ~$4.60/mo)

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
- [ ] **Sprint 2: Dynamic Rec Lifecycle + Perplexity upgrade** — `is_valid` column, `revalidate_recs.py`, `midday_refresh.py` (2 PM + 4:30 PM EST), `perplexity_client.py` upgrades. Full spec in `plans/pure-baking-river.md` PART 2B + 2C.
- [ ] **Alt note surface** — wire `Alt:` note from `bet_recommendations.note` into `morning_brief.py` cards + `bots/ask_ludi_db.py` edges intent (Sprint 4 follow-up).
- [ ] **Research follow-ups** — injury timestamp in cards (`player_injuries.snapshot_time`), `pct_money+diff` in Phase 8.22 social_signals, Ask Ludi `edges` intent 11-row scorecard, Ask Ludi `injuries` sub-intent WOWY delta.
- [ ] **Telegram native formatting upgrade** (`morning_brief.py`) — 4 zero-API text changes: (1) `>` blockquote on Key Advantage, (2) monospace projection table for bet cards, (3) L10 team context line under game header, (4) shot type progress bar per player. All data already in DB. Full spec + source screenshots: `docs/FUTURE_DATA_SOURCES.md` §5.3.
- [ ] **Game notes team totals fix** (`morning_brief.py` ~L758) — `{home_team_total}` / `{away_team_total}` always 'N/A'. Load from `cache/daily_games_{date}.json` instead of `bet_recommendations`. Data exists, just not wired.

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

**Phase 1.5: 2024-25 Historical Backfill** ← IN PROGRESS (backfill running nightly)
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

### AI Employee Workforce (March 2026 — OpenClaw Sprint)
**PRD:** `docs/projects/AI_EMPLOYEE_WORKFORCE.md` — 7 AI employees on OpenClaw runtime (~$4.60/mo)
**Team:** Solomon (PM), Silas (System Monitor), Vera (Pipeline QA), Iris (Social Scout), Henrik (Code Auditor), Maren (Content Strategist), **Lena (Data Analyst / Model Calibration)**

**Setup complete (Mar 1–2):** Telegram Bot 2 + Discord server + 6 soul files + webhooks + Gemini SOUL/ONBOARDING ✅

- [ ] **Employee onboarding docs** — `employees/{name}/ONBOARDING.md` for all 8 employees (6 Agent Teams + Gemini + Lena). Gemini `SOUL.md` + `ONBOARDING.md` done ✅. Remaining 7 (incl. Lena): project context + domain ownership + first task + red lines. **Lena requires live DB queries for examples** (see plan). Build before first Agent Teams session. **Lena-specific:** consolidated glossary cheat sheet — archetypes (15 offensive + 5 defensive tags), team schemes (4 types + interaction rules), matchup matrix (why STRETCH_BIG vs PAINT_PACK is favorable), scenario tags (USAGE_VACUUM, BENEFICIARY, HOT_STREAK), synergy playtypes. Sources: `module_e.py`, `docs/ARCHITECTURE.md`, `utils/tag_classifier.py`, `team_scheme_cache`. Also inject into Claude curation system prompt (Pattern 6 domain pre-training).
- [ ] Monday kickoff: Agent Teams live test (Solomon → Henrik first audit)
- [ ] Build `employees/silas/run_check.py` + launchd plist — Silas goes live
- [ ] Build `employees/iris/run_collection.py` + launchd plist — Iris goes live
- [ ] **`bots/solomon_bot.py`** — two-way Telegram chat with Solomon (sprint status, next actions, team health). Pattern: `bots/ask_ludi.py`. Week 1 build.
- [ ] **Discord two-way** — command handlers in employee channels so you can message Silas/Iris/Henrik in Discord and they respond/act (e.g. `/run-check` in #silas, `/audit file.py` in #henrik). Requires Discord bot polling loop.
- [ ] **Lena: Season Pattern Mining** — proprietary trend analysis across full 2025-26 dataset. Mine `player_game_logs` (10.8K), `canonical_games` (902), `referee_player_bias` (12.5K), `player_game_tracking`, `player_game_advanced`, `team_lineups` (10.6K), `player_synergy_playtypes`, `player_shot_quality`, `prop_line_snapshots`. Focus areas: ref stat-category tendencies (beyond fouls), archetype B2B resilience, hot/cold streak persistence, WOWY beneficiary accuracy, shot quality regression candidates, line movement → outcome correlation, scheme × archetype win rates. Output: actionable findings that can feed back into curation dossier + Module E modifiers. Plan details after Lena onboarding.

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

### Prop Card & Odds Widget (Post-Phase 8 — Frontend Sprint)
**Research:** `docs/research/PROP_CARD_WIDGET_RESEARCH.md` — full design + data source map
**Data:** All in `ludi.db` — zero new APIs needed
- [ ] **Phase 1 — PIL PNG for Telegram**: `utils/card_engine.py` → `generate_player_prop_card(bet_dict, conn)` → 800×500px dark card. Wire into `morning_brief.py` (DIAMOND/BLUE CHIP) + `bots/ask_ludi_handlers.py` (edges intent). 1-session build.
- [ ] **Phase 2 — Streamlit HTML component**: `app/components/prop_card.py` — right panel of two-column layout (Odds Widget iframe left, prop cards right).
- [ ] **Phase 3 — Prop Pulse Score** (optional): `_prop_pulse_score()` → 0–100 composite: Edge% 40% + L10 hit rate 25% + DVP rank 20% + alt line EV delta 15%.
- [ ] **Odds Widget**: Free Starter plan active (500 req/month). `ODDS_WIDGET_KEY` in `.env` — add to `.env.template`. Explore widget implementation at builder URL. **Telegram only**: iframe not supported — widget for Streamlit game lines sidebar only.

### CLV Tracking Enhancement
- [ ] CLV reporting in PM Bot daily summary
- [ ] 30-day rolling CLV metrics

### Historical Odds Backfill (March 2026)
~5,593 bets lost Jan 8–Feb 1 due to `clean: true` bug. Recoverable via The-Odds-API `/v4/historical/`.
- [ ] Backfill historical odds (~10 credits/query, ~150 credits total for 15 dates)
- [ ] Re-run pipeline for 15 missing dates and settle bets
- **Ready to run** — primary key has ~17K credits. `ODDS_API_KEY_BACKFILL` reserved for April season-archive run only. Use `scripts/backfill_historical_odds.py --date YYYY-MM-DD --verbose`.

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
- [ ] **Schema validation script**: `scripts/validate_schema.py` — assert all expected columns exist at pipeline start. Dead references removed from 3 workflows (Mar 4). Archived at `scripts/_archive/validate_schema.py` — restore and wire when implementing.
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
