# Ludi-Bot Roadmap

**Last Updated:** February 19, 2026
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** Phase 8 Pre-Work → Step 0 (Shared Claude Infrastructure)
**Completed:** Phases 5–7 ✅ (see `docs/archive/phase_reports/` for details)

This is the single source of truth for project tasks and priorities.

---

## Legend

- `[ ]` = Todo
- `[-]` = In Progress
- `[x]` = Completed

---

## High Priority

### Phase 8: AI-Enhanced Pipeline (Claude Integration)

**Goal:** Add Claude as an analytical reasoning layer on top of the deterministic pipeline
**Principle:** LLMs orchestrate and reason — never calculate. Math stays deterministic.
**Status:** 🟡 ACTIVE — Phase 7.9 complete, starting Phase 8.0
**Phase 8 Foundation Plan:** `docs/PHASE_8_FOUNDATION_PLAN.md` (Injury Intelligence + Phase 8 Pre-Work)
**Design Doc:** `.claude/plans/curried-growing-toucan.md` (revised Feb 17 — Ludi-Lite review + SMA audit)
**Estimated Daily Cost:** ~$0.73/day (~$22/month) — token-optimized with Haiku gates

**Ground Rules:**
- Claude handles reasoning/analysis ONLY — never factual NBA data (enforced by CLAUDE.md Critical Data Rules)
- All NBA facts come from `ludi.db` or live APIs (fetched, not recalled)
- Raw math stays deterministic (Poisson sims, devigging, Kelly sizing)
- All Claude outputs must be auditable/reproducible
- Graceful degradation: if Claude API fails, fall back to existing rule-based logic

**Sub-Phases (recommended implementation order):**

| # | Sub-Phase | Priority | Description | Daily Cost |
|---|-----------|----------|-------------|------------|
| **Pre** | **Shared Claude Infrastructure** | **BLOCKING** | **`utils/claude_client.py` (OAuth-first auth, Haiku/Sonnet), `utils/claude_prompts.py` (ROSTER_RULES + templates), config.py update** | **$0** |
| 8.0-A | Injury Schema + Sync | CRITICAL | `player_injuries` table (intraday-safe), 4 `players` columns, `scripts/sync_injuries.py` standalone script. BDL primary, Tank01 fallback. Fix 55-player canonical ID gap. | $0 |
| 8.0-B | Three-Tier Active Roster | CRITICAL | `main.py` roster fix: Tier 1 (active), Tier 2 (recently returned), Tier 3 (long-term out logged). Module D untouched. | $0 |
| 8.0-C | Smart Vacuum Enhancement | HIGH | `module_x_scenario.py` — full S.A.V.A.G.E. vacuum using `player_game_logs` L10, `player_wowy_stats`, archetype+scheme matrix | $0 |
| 8.0-D | Workflow Wiring | HIGH | Wire `sync_injuries.py` into `data_sync.yml` (5AM), `daily_briefing.yml` (11AM), `capture_closing_lines.yml` (5:30PM) | $0 |
| 8.5 | Play Curation Engine | HIGH | Haiku sanity gate (~$0.02) + Sonnet Top 5 curation (~$0.06). Claude reasons about selection — never recalculates edge. | ~$0.08 |
| 8.2 | Game Notes Generator | HIGH | Structured S.A.V.A.G.E. cards (tables + bullets) replacing wall-of-text. Morning brief + evening lock. | ~$0.35 |
| 8.3 | Player Spotlight Cards | HIGH | 2-3 sentence narratives for DIAMOND/BLUE CHIP only (~5/day) | ~$0.15 |
| 8.9 | **Rotation/Minutes Projection** | **MEDIUM** | **Track coach rotation patterns from PBP data (PlayByPlayV3), situational minutes modeling** | **TBD** |
| 8.7 | Perplexity MCP | MEDIUM | Real-time search replacing DuckDuckGo | ~$0.10 |
| 8.4 | Archetype Classifier Fix | MEDIUM | Weekly batch classification via Claude | ~$0.07 |
| 8.6 | MCP Server Integration | LOW | BDL + Odds API MCP for Ops Hub | $0 |

**Shared Infrastructure (Pre-Work — BLOCKING all Phase 8 Claude calls):**
- [ ] Create `utils/claude_client.py` — OAuth-first auth (CLAUDE_CODE_OAUTH_TOKEN → ~/.claude/config.json → ANTHROPIC_API_KEY), Haiku/Sonnet model selection, token tracking, graceful degradation
- [ ] Create `utils/claude_prompts.py` — ROSTER_RULES anti-hallucination block, GAME_NOTES_TEMPLATE, SPOTLIGHT_TEMPLATE
- [ ] Add `CLAUDE_AUTH_TOKEN` to config.py via `_get_claude_auth_token()` helper
- [ ] Add `CLAUDE_CODE_OAUTH_TOKEN=your-token-here` to `.env.template`
- [x] Verify `nba_api==1.11.3` installed with league_id parameter support ✅
- [x] Add PlayByPlayV3 endpoint support to `utils/nba_api_client.py` ✅

**Token Optimization (5x Max Plan):**
| Task | Model | Est. tokens/call | Frequency |
|------|-------|-----------------|-----------|
| Sanity gate | Haiku (temp=0.1) | ~800 | Per bet (~300/day → ~$0.02) |
| Top 5 curation | Sonnet (temp=0.1) | ~2,000 | Once/day → ~$0.06 |
| Game notes | Sonnet (temp=0.2) | ~1,500/game | ~10 games/day → ~$0.35 |
| Player spotlights | Sonnet (temp=0.2) | ~1,000/bet | DIAMOND+BLUE only (~5/day → ~$0.15) |

**Key Tasks:**
- [ ] **Pre-Work (Step 0):** `utils/claude_client.py` + `utils/claude_prompts.py` + config.py update
  - OAuth-first: tries `CLAUDE_CODE_OAUTH_TOKEN` → `~/.claude/config.json` → `ANTHROPIC_API_KEY`
  - No actual Claude calls — just wrapper + prompts setup
- [ ] **8.0-A (Step 1):** `player_injuries` table (intraday-safe — `snapshot_time`, `is_game_day_report`, status-change detection), 4 new `players` columns, `scripts/sync_injuries.py` standalone (BDL primary, Tank01 roster fallback). Fix 55-player canonical ID gap. NOTE: NBA.com CDN injury endpoint CONFIRMED BROKEN (403/empty, Feb 2026) — do not use.
- [ ] **8.0-B (Step 3):** Three-tier roster in `main.py`. Module D stays untouched. Falls back to Tier 1 if `player_injuries` empty.
- [ ] **8.0-C (Step 4):** Smart vacuum in `module_x_scenario.py` — `player_game_logs` L10 (not API averages), `player_wowy_stats` on/off delta, archetype vs scheme modifier, exact `days_out` from DB (not keyword matching)
- [ ] **8.0-D (Step 5):** Wire `sync_injuries.py` into 3 workflows: `data_sync.yml` (5AM, `is_game_day_report=0`), `daily_briefing.yml` (11AM, `is_game_day_report=1`), `capture_closing_lines.yml` (5:30PM, `is_game_day_report=1`)
- [ ] **8.5 (Step 6):** `scripts/curate_plays.py` — Stage 1 Haiku sanity gate (injury contradictions, impossible lines) + Stage 2 Sonnet Top 5 (correlation-aware, diversified). Claude NEVER recalculates edge.
- [ ] **8.2 (Step 7):** Structured S.A.V.A.G.E. game cards in `morning_brief.py` + `evening_slate_lock.py`. Format: Context table + Injury Impact + Scheme Edge + Key Edges.
- [ ] **8.3 (Step 8):** Player spotlight cards in `utils/telegram_notifier.py`. DIAMOND + BLUE CHIP only.
- [ ] 8.9: **Rotation/Minutes Projection Enhancement** — Parse PBP (PlayByPlayV3), coach tendency models, situational minutes in Module C
- [ ] 8.7: Perplexity MCP replacing Module D's DuckDuckGo `_nuance_check()`
- [ ] 8.4: `scripts/classify_archetypes.py` weekly batch, re-enable Module F modifiers
- [ ] 8.6: Configure BDL MCP server, add to Claude Ops Hub

**Data Architecture Notes:**
- Injury intraday: `player_injuries` stores multiple snapshots/day — only insert when status changes. `is_game_day_report=1` for snapshots <8h before tipoff.
- Smart vacuum uses full S.A.V.A.G.E. DB (not simplified Ludi-Lite API approach): `player_game_logs` L10, `player_wowy_stats`, archetype+scheme matrix
- GENERALIST target: **Already achieved at 20.0%** ✅ (was incorrectly noted as 31.4% blocking)
- SMA audit (Feb 17): Temporal ✅ Clean | Feature Coverage ✅ Clean | Entity Resolution ⚠️ 55 canonical ID gap (fix in 8.0-A)

**Competitive Research:** See `docs/FUTURE_DATA_SOURCES.md` §5 for UI/UX patterns from 6 betting analytics sites (PropsMadness, LandYourBets, BucketsToBucks, Outlier.bet, Props.cash, StraightBettin)

---

### Phase 7: All-Star Break Sprint ✅ COMPLETE (Feb 17, 2026)

**Status:** All sub-phases 7.1–7.9.5 complete. Full details: `docs/archive/phase_reports/PHASE_7_COMPLETION_SUMMARY.md`

**Remaining (unblocked Feb 19 — first game day back):**
- [ ] Run full pipeline dry run with all new data sources active
- [ ] Validate all workflows via manual trigger on live game day

**Key outcomes:** Module C/E/F overhauls (V4.0/V4.0/V5.2) · OVER bias fixed (46.1%→target) · GENERALIST 20.7% ✅ · 5 defensive archetypes · 10,780 duplicate rows removed · nba_api 10 endpoints integrated · API best practices guide created (69 KB)

---

### Phase 6 ✅ COMPLETE (Feb 2–14, 2026)
+292u profit, 55.7% WR, positive CLV across all edge buckets. Full details: `docs/archive/phase_reports/PHASE_6_COMPLETION_SUMMARY.md`

### Phase 5 ✅ ESSENTIALLY COMPLETE
Production automation live. Final validation pending Feb 19. See `docs/archive/phase_reports/PHASE_5_5_COMPLETION_LOG.md`

---

### Database Architecture Strategy

**Current State:** Single SQLite database (`ludi.db`) — 30 MB, 38 tables

**Phase 1: Consolidation** ✅ COMPLETE (Phase 6.5b)
- [x] JSON staging buffer removed (direct SQLite writes)
- [x] Single source of truth for all game data

**Phase 2: Multi-Season Support (Before 2026-27 Season)**
- [ ] Add season archive workflow: `archives/data/ludi_YYYY_YY.db`
- [ ] Create `scripts/archive_season.py` for end-of-season backup
- [ ] Document season rollover procedure in `docs/SEASON_ROLLOVER.md`

**Phase 3: Web App Migration (When Ludi Lens Launches)**
- [ ] Evaluate PostgreSQL vs SQLite for production web app
- [ ] Design API layer between frontend and database

---

## Medium Priority

### Ludi Lens Dashboard (Post-Phase 8 — Web App Sprint)
**Blocked until:** Phase 8 complete + dedicated web app sprint
**Design identity:** Dark Navy #0F172A, Gold #FBBF24, Emerald #10B981 | "War Room" theme
- [ ] Streamlit app scaffold (`app.py`)
- [ ] "War Room" visual design implementation
- [ ] Real-time prop display integration
- [ ] Historical performance charts

### CLV Tracking Enhancement
- [ ] CLV reporting in PM Bot daily summary
- [ ] 30-day rolling CLV metrics

### Historical Odds Backfill (March 2026)
**Context:** ~5,593 bets lost across 15 game days (Jan 8,10,16-28,30-31,Feb 1) due to `clean: true` bug. Fix deployed Feb 2. Recoverable via The-Odds-API `/v4/historical/` in March.
- [ ] Backfill historical odds via The-Odds-API `/v4/historical/` endpoint (~10 credits/query)
- [ ] Re-run pipeline for 15 missing dates to regenerate bets with historical odds
- [ ] Settle regenerated bets against existing game logs
- **Blocked until:** March 2026 (Feb Odds API quota exhausted)

### Data Pipeline Improvements
- [ ] Consolidate WOWY scripts (`sync_wowy_hybrid.py` + `sync_pbp_wowy.py` — duplicate work)
- [ ] Multi-book arbitrage detection
- [ ] Steam move detection (rapid line movement alerts)

---

## Low Priority

### Future Enhancements
- [ ] DFS multiplier conversion (PrizePicks/Underdog)
- [ ] Strength of Schedule (SOS) adjustment
- [ ] Shooting Luck Deviation signals
- [ ] Sync PlayerRebounding tracking data (contested vs uncontested %)

---

## Archive

- **docs/archive/phase_reports/** — Phase completion reports (Phases 1–7)
  - `PHASE_7_COMPLETION_SUMMARY.md` — Phase 7 full details (module overhauls, critical findings, backtest)
  - `PHASE_6_COMPLETION_SUMMARY.md` — Phase 6 full details (CLV buckets, sub-phase steps)
  - `PHASE_5_5_COMPLETION_LOG.md` — Phase 5.5 completion
- **docs/STATUS_HISTORY.md** — Phases 1–4 history
- **reports/** — Calibration analysis, performance breakdowns
- **docs/archive/** — All other completion reports, organized by sub-phase
