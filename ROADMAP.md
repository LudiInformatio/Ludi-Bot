# Ludi-Bot Roadmap

**Last Updated:** Sunday, March 8, 2026 — 6:48 PM EDT
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** T-002 Slack P1 (`curate_plays.py`, `module_d.py`, `module_g.py`) — Slack alert on critical failure wiring + Module X Sprint B (`team_dvp_by_archetype`) — DVP Condition 5, awaiting Sprint A production validation
**Completed:** `CLAUDE.md` slimmed 323→227 lines — Henrik audit + junior dev 9-edit spec, redundancy removed, `COMMON_MISTAKES.md` cross-ref added ✅ + `docs/ARCHITECTURE.md` + `docs/PRODUCTION_HANDBOOK.md` updated — 2 missing module rows, canonical_games count, 21-row automation schedule ✅ + Phase 9 docs (`LLM_PARADIGMS_AND_CALIBRATION.md`, `MODEL_CALIBRATION_PATTERNS.md`, Patterns 10-16) shipped in `3cab28c` ✅

This is the single source of truth for project tasks and priorities.

> **Agent Template Contract** — When updating this file, preserve the header format exactly:
> - `**Active Work:**` — short phrase(s) separated by ` + `. First item = current sprint focus.
> - `**Completed:**` — last 3 completions as separate ` + ` segments (PM bot reads `parts[-3:]`).
> - `### Current Sprint` → `**Next Actions:**` block — use `- [ ]` bullets for PM bot pending tasks.
> - Never put actionable next-steps ONLY in the Phase 8 table; the table is for status tracking only.

**Active Project Docs (on-disk, gitignored — private intel):**
- `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md` — BERT-derived prompt patterns (Patterns 1-9) + advanced paradigms (Patterns 10-16)
- `docs/projects/LLM_PARADIGMS_AND_CALIBRATION.md` — Phase 9 implementation plan (5 sprints)
- `docs/research/LLM_CANONICAL_RESEARCH_TABLE.md` — Academic LLM research reference table
- `docs/projects/HISTORICAL_BACKFILL_2024_25.md` — 2024-25 backfill plan (~18k rows, 6-night automated)
- `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md` — Social Intel + Prop Pulse Score full spec
- `docs/FUTURE_DATA_SOURCES.md` — Ask Ludi architecture (§6) + competitive patterns (§5.2-B) + PBP Stats endpoints (§4.4)
- `best-practices/api/API_BEST_PRACTICES.md` — BDL + Tank01 + ESPN endpoint reference
- `docs/projects/AI_EMPLOYEE_WORKFORCE.md` — AI Employee Workforce PRD (8 employees, Skills 2.0 hybrid, ~$4.60/mo)

**Tracked ops docs:**
- `docs/operations/COMMUNICATION_PROTOCOL.md` — channel routing, decision authority, escalation paths
- `docs/decisions/DECISION_LOG.md` — seed ADRs: Skills 2.0, canonical_games, bet_recs dedup, CLV props, DST cron
- `best-practices/agents/AGENT_OUTPUT_PATTERNS.md` — silent failure root cause, maxTurns config, resume vs re-run

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
- [x] **T-001a: Comm Protocol docs** — `docs/operations/COMMUNICATION_PROTOCOL.md` + `docs/decisions/DECISION_LOG.md` + `docs/decisions/ADR_TEMPLATE.md` ✅
- [ ] **T-002: Slack P1 wiring** — `curate_plays.py` / `module_d.py` / `module_g.py` Slack alert on critical failure. Junior dev writes → Henrik audits. After T-001a.

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

### AI Employee Workforce (March 2026 — Skills 2.0 Hybrid)
**PRD:** `docs/projects/AI_EMPLOYEE_WORKFORCE.md` (on-disk, gitignored) | **Implementation plan:** `.claude/plans/crystalline-petting-reef.md`
**Team (8):** Solomon (PM), Silas (SRE), Vera (QA), Iris (Social Scout), Henrik (Code Auditor), Maren (Strategist), Lena (Data Analyst), **Kai (Repo Custodian, junior under Silas)**
**Architecture:** Claude Code Skills 2.0 subagents (`.claude/agents/*.md`) for interactive work + external stack (Telegram bots, GH Actions, launchd) for scheduled/always-on. $0 incremental for subagents (uses subscription).

**Setup complete (Mar 1–2):** Telegram Bot 2 + Discord server + 7 soul files + webhooks + Gemini SOUL/ONBOARDING ✅
**Research complete (Mar 6):** Skills 2.0 + subagents + agent teams evaluated. Hybrid architecture finalized. Plan in `.claude/plans/`.

- [x] **Phase 1 subagents** — Henrik, Silas, Lena shipped as `.claude/agents/*.md` ✅
- [x] **Phase 2 skills** — `/lena-analyze`, `/repo-hygiene` (Kai), `ludi-audit` + `daily` + `backtest` wired ✅
- [x] **Phase 3 subagents** — Vera, Solomon, Maren, Kai agents + `/iris-collect` skill (zero-LLM) ✅
- [x] **ONBOARDING.md** — All 8 employees have `employees/{name}/ONBOARDING.md` ✅
- [x] **Lena SOUL.md** — new soul file at `employees/lena/SOUL.md` + Kai SOUL.md at `employees/kai/SOUL.md` ✅
- [ ] **`bots/solomon_bot.py`** — two-way Telegram chat with Solomon. Pattern: `bots/ask_ludi.py`. Stays external (always-on).
- [ ] **Lena: Season Pattern Mining** — mine `player_game_logs`, `referee_player_bias`, `team_lineups`, `player_synergy_playtypes`, `prop_line_snapshots`. Focus: ref stat tendencies, archetype B2B resilience, streak persistence, scheme × archetype win rates. Output feeds curation dossier + Module E modifiers.

### Phase 9: Advanced LLM Paradigms & Model Calibration (Post-Phase 8)
**Full plan:** `docs/projects/LLM_PARADIGMS_AND_CALIBRATION.md`
**Research:** `docs/research/LLM_TRAINING_METHODOLOGIES_LANDSCAPE.md` | `docs/research/LLM_CANONICAL_RESEARCH_TABLE.md`
**Best practices:** `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md` (Patterns 10-16), `best-practices/data/MODEL_CALIBRATION_PATTERNS.md`, `best-practices/ai/EMPLOYEE_TRAINING_PARADIGMS.md`
**Principle:** LLMs orchestrate, never calculate. ML learns constants OFFLINE; math stays deterministic.
- [ ] Sprint 1: Measurement infrastructure (Brier Score, residual analysis, calibration curves)
- [ ] Sprint 2: Learned constants (isotonic calibration, per-stat variance, absorption rates)
- [ ] Sprint 3: Curation prompt engineering (randomize order, prefilling, Many-Shot ICL, CoT)
- [ ] Sprint 4: Knowledge distillation + Reflexion (feedback loops, Haiku calibration, lessons-learned)
- [ ] Sprint 5: Advanced patterns + structural hardening (debate, confidence scoring, handoff protocols)

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
- [ ] Phase V1: `utils/chart_engine.py` (Plotly + Kaleido) + 6 MVP charts — Hit Streak, Archetype Leaderboard, Matchup Edge Heatmap, Hot/Cool Players L7, Stat Confidence Grade, P&L Waterfall
- [ ] Phase V2–V4: Edge/WR scatter, sparklines, full catalog, Streamlit + PaperBanana AI charts — see `docs/projects/INFOGRAPHIC_VISUALIZATION_SYSTEM.md`

### Prop Card & Odds Widget (Post-Phase 8 — Frontend Sprint)
**Research:** `docs/research/PROP_CARD_WIDGET_RESEARCH.md` — full design + data source map
**Data:** All in `ludi.db` — zero new APIs needed
- [ ] **Phase 1 — PIL PNG for Telegram**: `utils/card_engine.py` → 800×500px dark card. Wire into `morning_brief.py` + `bots/ask_ludi_handlers.py`. 1-session build.
- [ ] **Phase 2–3 + Odds Widget**: Streamlit component (`app/components/prop_card.py`) + Prop Pulse Score (0–100 composite). `ODDS_WIDGET_KEY` in `.env` — Streamlit sidebar only (no Telegram iframe). See `docs/research/PROP_CARD_WIDGET_RESEARCH.md`.

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
