# Ludi-Bot Roadmap

**Last Updated:** February 25, 2026 — 2:10 PM EST
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** Phase 8.13 Ask Ludi (implementation ready) + Social Intelligence System (architecture complete, ready to build)
**Completed:** Phases 5–7 ✅ + Phase 8.0-A/B/C/D ✅ + Phase 8.2/8.3/8.4/8.5/8.6/8.7/8.9/8.10/8.12/8.14/8.15/8.16/8.18/8.19 ✅ + Slack/Notification Split ✅ + Model Calibration Fixes ✅ + Feb 20 Post-ASB Audit ✅ + Tank01 Data Expansion ✅ + Injury Intelligence Hardening ✅ + Claude Auth Fix ✅ + Ask Ludi Architecture Research ✅ + Morning Brief Pipeline Hardening ✅ + BetIQ/TeamRankings Research ✅ + BERT/NLP Prompt Architecture Research ✅ + Phase 8.20 Stat Confidence & Edge Calibration ✅ + Production Pipeline/WOWY/Settlement Fix ✅ + Phase 8.18 Game Lines Integration ✅ + Phase 8.19 Prompt Engineering Upgrade ✅ + **Full Project Audit (Sprints 0-10) ✅** + Post-Audit Bug Fixes & Documentation Integration ✅ + **Evening Lock Bug Fixes & Injury Intelligence Tightening ✅** + **Phase 8.16 Suspension Intelligence (ESPN) ✅** + **BDL V2 Full Integration + SportsDataIO Enrichment ✅** + **Hybrid Off/Def Role Tagging ✅** + **Scheme Cache d14 Fix + Quality Tiers ✅** + **Morning Brief Slate Trends Header ✅** + **Data Sync Pipeline Fix + PBP Stats Split + Module H BDL Fallback ✅** + **Injury Pipeline Hardening + ESPN Injury Source + Referee Timing Fix ✅** + **RSS Feed Parsing Hardening ✅** + **Canonical Table Hardening + ESPN Integration Foundation ✅** + **Claude Name Resolution Pipeline ✅** + **Settlement Pipeline Hardening + Report Upgrade ✅** + **Classification Gate 2 Hardening + BERT Pattern 9 Negative Few-Shot ✅** + **UNK Position Cleanup + Archetype Naming Audit ✅**

This is the single source of truth for project tasks and priorities.

**Active Project Docs:**
- **Prompt Engineering Reference:** `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md` — 8 BERT-derived patterns mapped to Claude prompts + priority implementation order
- **Tank01 Data Expansion:** `docs/projects/TANK01_DATA_EXPANSION.md` — 17-endpoint audit, O/U vs alt line parsing guide, model calibration findings, implementation phases
- **Best-Practices API Guide:** `best-practices/api/API_BEST_PRACTICES.md` — BDL + Tank01 complete endpoint reference, lessons learned
- **2024-25 Historical Backfill:** `docs/projects/HISTORICAL_BACKFILL_2024_25.md` — full plan to import prior season game logs (~18k rows), enrichment pipeline, 6-night automated backfill via Module H audit file mode
- **Social Intelligence System:** `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md` — full research sprint (Feb 24): market landscape audit, multi-agent architecture (Scout/Analyst/Research/Market/Synthesis/PM), competitor reverse engineering (LunarCrush/Outlier/Rithmm/Action Network), Prop Pulse Score data model, Smart Signal trigger, BERT-derived Haiku classification, Discord/Reddit strategy

---

## Legend

- `[ ]` = Todo
- `[-]` = In Progress
- `[x]` = Completed

---

## High Priority

### Current Sprint

- [-] Phase 8.13 — Ask Ludi Telegram Bot (`bots/ask_ludi.py`) — architecture complete, 3-file implementation ready
- [x] Canonical Table Hardening + ESPN Integration Foundation (Feb 24) — `canonical_teams` table, `normalize_bdl_abbr()` centralized, `build_espn_crosswalk.py`, `espn_id` column wired
- [x] Claude Name Resolution Pipeline (Feb 24) — `resolve_canonical_name()` in Haiku gate, spotlights, matchup analysis, archetype classifier; fixes accent mismatch silent failures
- [x] RSS Feed Parsing Hardening (Feb 23-24) — RotoWire + RealGM verb list expanded, canonical validation gate, `getattr` safety

---

### Phase 8: AI-Enhanced Pipeline (Claude Integration)

**Goal:** Add Claude as an analytical reasoning layer on top of the deterministic pipeline
**Principle:** LLMs orchestrate and reason — never calculate. Math stays deterministic.
**Status:** 🟡 ACTIVE — Core pipeline complete, remaining sub-phases are LOW/MEDIUM priority
**Estimated Daily Cost:** ~$0.40/day (~$12/month)

**Ground Rules:**
- Claude handles reasoning/analysis ONLY — never factual NBA data (enforced by CLAUDE.md Critical Data Rules)
- All NBA facts come from `ludi.db` or live APIs (fetched, not recalled)
- Raw math stays deterministic (Poisson sims, devigging, Kelly sizing)
- Graceful degradation: if Claude API fails, fall back to existing rule-based logic

**Completed sub-phases (Pre, 8.0-A/B/C/D, 8.2–8.7, 8.9–8.10, 8.12, 8.14–8.16, 8.18–8.20, Infra):** All DONE. Full details: `docs/STATUS_HISTORY.md`

**Active & Remaining Sub-Phases:**

| # | Sub-Phase | Status | Description | Cost |
|---|-----------|--------|-------------|------|
| 8.8 | Game Score Formula v2 | LOW | Add line movement delta + handle% to `_score_game()`. **Blocked: needs Mar 2026 data to backtest. Phase 8.18 creates the slot for this to plug in.** | $0 |
| 8.11 | Ludi Power Ratings | LOW | Blended ortg+drtg+pace power ratings for game scoring + Ludi Lens | $0 |
| 8.13 | Ask Ludi — Telegram Bot | MEDIUM | Natural language → ludi.db + Claude → response in Telegram thread. Architecture research complete (Feb 20): python-telegram-bot v21+ long polling, Haiku intent ($0.0001/call) → Sonnet analysis, read-only SQLite (`?mode=ro`), launchd keepalive, 3-file implementation (`bots/ask_ludi.py`, `ask_ludi_db.py`, `ask_ludi_handlers.py`). See `docs/FUTURE_DATA_SOURCES.md` §6. | ~$0.05/day |
| 8.17 | Foul Intelligence | MEDIUM | Extend `sync_stint_profiles.py` to parse foul events from PlayByPlayV3 (same API, same loop, no extra cost). New `player_foul_splits` table (period, clock, foul_number, ref_name). Unlocks: early foul trouble → Module C minutes dampener, ref-player bias rebuild, weekly Claude context. | $0 |
| 8.22 | Social Intelligence System | MEDIUM | Multi-agent pipeline that feeds social sentiment + market signals into curation as a Prop Pulse Score. **Architecture complete** — see `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md` for full spec. Phase 1: `social_signals` + `odds_snapshots` + `prop_intelligence` DB tables, Reddit Scout (PRAW), Action Network scraper, Market Intelligence Agent (odds snapshots 4x/day via existing Odds API). Phase 2: Haiku Analyst Team (4-field JSON, BERT-derived prompt), Synthesis Team (Prop Pulse Score 0-100, Smart Signal ⚡ trigger). Phase 3: PM Agent routing, inject Prop Pulse Score into `curate_plays.py`. Competitors reverse-engineered: LunarCrush (Galaxy Score formula), Outlier.bet (traffic light hit rate), Rithmm (Smart Signals + Power Trends), Action Network (bet% vs money% divergence, RLM). Discord lurker account strategy documented. | ~$0.02/day Haiku |
| 8.23 | Claude/Perplexity Analysis Feedback Loop | MEDIUM | 3-layer OpenClaw memory applied to core pipeline. **Layer 1:** `claude_analysis_log` — Gardener hot-path write per call (Haiku gate, Sonnet curation, spotlight, game notes, Perplexity claim). **Layer 2:** `scripts/calibrate_claude_outputs.py` — weekly Wilson accuracy per call type → `cache/claude_calibration.json`. **Layer 3:** inject calibration into `_get_system_wr_context()` (already wired for stat confidence). Completes Pattern 7 (`haiku_sonnet_disagreements`). **Timing:** 14-day first scan (~Mar 10) — early pattern detection, validate collection is working. 90-day window lands in offseason (late May 2026) → fine-tune Haiku FLAG criteria + Perplexity `hours_to_game` filter before 2026-27 season. Full spec: `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md` (same `bert_training_signals` pattern applied to Claude/Perplexity). | $0 |
| 8.21 | ESPN Full Integration | MEDIUM | **Foundation:** `utils/espn_client.py` (scoreboard, game summary, team injuries — follows `bdl_client.py` pattern). **Nightly longComment pull:** `data_sync.yml` step calls ESPN `/summary?event=` per tonight's games → writes `longComment` (beneficiary narrative, e.g. "Barlow figures to enter the starting lineup") to `player_injuries` (`ALTER TABLE player_injuries ADD COLUMN espn_long_comment TEXT`). Morning brief reads from DB — no real-time call needed. Replaces some Perplexity calls (~$0.05/day saved). **ESPN athlete ID crosswalk:** `scripts/build_espn_crosswalk.py` — fuzzy-match ESPN `displayName` → `players.full_name`, store `espn_id` in `player_canonical_ids` (`ALTER TABLE player_canonical_ids ADD COLUMN espn_id TEXT`). Weekly rebuild via `weekly_validation.yml`. **Tier 3 game lines:** `module_a.py` tertiary fallback when Odds API + BDL both fail — ESPN pickcenter returns DraftKings spread/O/U with juice (open+close+live). No player props in ESPN. **Future:** live box scores for Ask Ludi bot. ESPN team ID map and all endpoint patterns are documented in `best-practices/api/API_BEST_PRACTICES.md`. | $0 |

---

### Completed Sprints

### Canonical Table Hardening + Claude Name Resolution Pipeline ✅ COMPLETE (Feb 24, 2026)
`canonical_teams` (30 rows) + `player_canonical_ids` restored in `database.py` · `normalize_bdl_abbr()` centralized in `utils/mappings.py` · `resolve_canonical_name()` wired into 4 Claude injection points. Full details: `docs/STATUS_HISTORY.md`

### Injury Pipeline Hardening + ESPN Injury Source + Referee Timing Fix ✅ COMPLETE (Feb 23, 2026)
11 files: accent-aware name resolution in `sync_injuries.py` · ESPN as faster injury source (15–30 min lag vs 2–6 hr) · UNION clause catches blank `team_abbreviation` · `daily_briefing.yml` moved 9 AM → 11 AM (refs race condition fixed). Full details: `docs/STATUS_HISTORY.md`

### Data Sync Pipeline Fix + PBP Stats Split + Module H BDL Fallback ✅ COMPLETE (Feb 23, 2026)
PBP Stats moved to own workflow `pbp_stats_sync.yml` cutting 57% API calls · Ops Hub now triggers on `cancelled` · Module H BDL fallback prevents silent 0-row ingestion. Full details: `docs/STATUS_HISTORY.md`

### BDL V2 Full Integration + SportsDataIO Enrichment ✅ COMPLETE (Feb 22, 2026)
4 sprints: SportsDataIO enrichment (13,706 rows) · BDL advanced/hustle/tracking (82,785 rows) · plus_minus 58.9%→99.2% · season averages replaces Ghost Protocol synergy scraping. Full details: `docs/STATUS_HISTORY.md`

### Evening Lock Bug Fixes & Injury Intelligence Tightening ✅ COMPLETE (Feb 21, 2026)
`UnboundLocalError` in `module_e.py` was root cause of silent zero-output outage · 9 fixes across 7 files · `time_context_note` injected into Claude prompts. Full details: `docs/STATUS_HISTORY.md`

### ESPN Research, Suspension Intelligence & Pipeline Hardening ✅ COMPLETE (Feb 21, 2026)
ESPN public API verified live · `sync_suspensions_espn.py` found 5 active suspensions (Paul George 32d, Gobert same-day) on first run · $0 cost. Full details: `docs/STATUS_HISTORY.md`

### Production Pipeline / WOWY / Settlement Fix ✅ COMPLETE (Feb 21, 2026)
`continue-on-error` on diagnostic steps fixed 5-day pipeline outage · WOWY retry loop removed (9× attempts → 1×) · settlement deduped to single 6 AM summary. Full details: `docs/STATUS_HISTORY.md`

### Injury Intelligence Hardening ✅ COMPLETE (Feb 20, 2026)
RealGM RSS dual-source corroboration (0.95 confidence when both agree) · `injury_refresh.yml` (4 daytime + 15 evening runs) · `--force` flag for evening lock. Full details: `docs/STATUS_HISTORY.md`

### Morning Brief Pipeline Hardening + BetIQ Research ✅ COMPLETE (Feb 20, 2026)
Native Telegram text (removed `send_photo`) · all-game processing (removed hardcoded watchlist) · `skip_resolve` bug fixed · 6 ATS/O-U patterns from BetIQ competitive analysis. Full details: `docs/STATUS_HISTORY.md`

### Ask Ludi Architecture Research ✅ COMPLETE (Feb 20, 2026)
3-file implementation plan ready (`bots/ask_ludi.py`, `ask_ludi_db.py`, `ask_ludi_handlers.py`) · python-telegram-bot v21+, Haiku intent → Sonnet analysis, read-only SQLite. Full details: `docs/STATUS_HISTORY.md`

### Feb 20 Post-All-Star Break Audit ✅ COMPLETE (Feb 20, 2026)
9 critical bugs fixed (Module H `ON CONFLICT`, missing `anthropic` in requirements.txt, BDL milestone odds corruption, +269u phantom P&L) · BDL vendor quality filter added · 4 packages added to requirements.txt. Full details: `docs/STATUS_HISTORY.md`

### Phase 7: All-Star Break Sprint ✅ COMPLETE (Feb 17–19, 2026)
Module C/E/F overhauls (V4.0/V4.0/V5.2) · OVER bias fixed · GENERALIST 20.7% · 5 defensive archetypes · 10,780 duplicate rows removed · nba_api 10 endpoints integrated. Pipeline validated on first game day back (Feb 19). Full details: `docs/archive/phase_reports/PHASE_7_COMPLETION_SUMMARY.md`

### Phase 6 ✅ COMPLETE (Feb 2–14, 2026)
+292u profit, 55.7% WR, positive CLV across all edge buckets. Full details: `docs/archive/phase_reports/PHASE_6_COMPLETION_SUMMARY.md`

### Phase 5 ✅ COMPLETE
Production automation fully live and validated. See `docs/archive/phase_reports/PHASE_5_5_COMPLETION_LOG.md`

---

### Database Architecture Strategy

**Current State:** Single SQLite database (`ludi.db`) — ~30 MB, 38+ tables

**Phase 1: Consolidation** ✅ COMPLETE — Single source of truth, direct SQLite writes, no JSON staging

**Phase 1.5: 2024-25 Historical Backfill** ← NEXT (plan ready)
- [ ] Create `cache/pending_sync_dates.json` with Oct 22, 2024 → Apr 13, 2025 date range
- [ ] Module H auto-backfill (~6 nights at 200 Tank01 req/day, fully automated)
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
**Design identity:** Dark Navy #0F172A, Gold #FBBF24, Emerald #10B981 | "War Room" theme
- [ ] Streamlit app scaffold (`app.py`)
- [ ] "War Room" visual design implementation
- [ ] Real-time prop display integration
- [ ] Historical performance charts

### Infographic & Data Visualization System (Post-Phase 8 — Frontend Sprint)
**Blocked until:** Phase 8 backend cleanup complete
**Full plan:** `docs/projects/INFOGRAPHIC_VISUALIZATION_SYSTEM.md`
**Inspired by:** PaperBanana (arXiv:2601.23265) — AI-assisted illustration framework, code releasing ~March 2026
- [ ] Phase V1: `utils/chart_engine.py` (Plotly + Kaleido) + 2 MVP charts (stat confidence matrix, daily P&L waterfall) wired into morning brief
- [ ] Phase V2: Edge vs WR scatter, player trend sparklines, tier performance → weekly validation + debrief
- [ ] Phase V3: Full 12-chart catalog + `scripts/generate_all_charts.py`
- [ ] Phase V4: Streamlit integration + PaperBanana AI-assisted chart generation for Ask Ludi

### CLV Tracking Enhancement
- [ ] CLV reporting in PM Bot daily summary
- [ ] 30-day rolling CLV metrics

### Historical Odds Backfill (March 2026)
~5,593 bets lost Jan 8–Feb 1 due to `clean: true` bug (fixed Feb 2). Recoverable via The-Odds-API `/v4/historical/`.
- [ ] Backfill historical odds (~10 credits/query)
- [ ] Re-run pipeline for 15 missing dates and settle bets
- **Blocked until:** March 2026 (Feb Odds API quota exhausted)

### Data Pipeline Improvements
- [ ] Consolidate WOWY scripts (`sync_wowy_hybrid.py` + `sync_pbp_wowy.py` — duplicate work)
- [ ] Ghost Protocol date-skip optimization: pre-check `team_lineups` before scraping each date (~30s saved per already-synced date in weekly backfills)
- [ ] Ghost Protocol on/off scraping: uncomment/implement on/off tab in `WOWY_MANIFEST` (currently lineups-only)
- [x] ~~Schedule `sync_pbp_wowy.py` weekly in `data_sync.yml`~~ → Moved to own workflow `pbp_stats_sync.yml` (Mon/Wed/Fri 5 AM EST) — Feb 23, 2026
- [ ] Multi-book arbitrage detection
- [ ] Steam move detection (rapid line movement alerts)

### GH Actions / Claude Ops Improvements (identified Feb 20, 2026)
- [x] **`claude-ops-hub.yml` upgrade**: Uses `anthropics/claude-code-action@v1` with `CLAUDE_CODE_OAUTH_TOKEN`. BERT-trained diagnosis via KNOWN_FIXES.md few-shot context. Triggers on both `failure` and `cancelled` conclusions. — Feb 22-23, 2026
- [ ] **PR review action**: Add `anthropics/claude-code-action@v1` to PR events for automated code review on push to main
- [ ] **`pip-audit` step**: Add to `data_sync.yml` or a separate security workflow — fails build on known CVEs in `requirements.txt`
- [ ] **Weekly Claude cost report**: `scripts/claude_cost_report.py` — reads `claude_usage_log` table, sends weekly $/1k-token summary to Slack
- [ ] **Token budget guard**: `max_tokens` cap in `claude_client.py` per task type (Haiku=200, Sonnet=800) + log when approaching daily budget
- [ ] **Ask Ludi bot management workflow**: `bot_management.yml` — start/stop/status commands for the long-polling bot process via launchd
- [ ] **Schema validation script**: `scripts/validate_schema.py` — assert all expected columns exist in key tables; run at pipeline start. Prevents silent failures like the `confidence_tier` vs `tier` bug.
- [ ] **OAuth token refresh reminder**: Add to `claude-ops-hub.yml` — warn in Slack when `CLAUDE_CODE_OAUTH_TOKEN` is >25 days old (expires ~30 days)

---

## Low Priority

### Future Enhancements
- [ ] DFS multiplier conversion (PrizePicks/Underdog)
- [ ] Strength of Schedule (SOS) adjustment
- [ ] Shooting Luck Deviation signals
- [ ] Sync PlayerRebounding tracking data (contested vs uncontested %)

### Live Betting Pipeline (post model-math verification)
**Blocked until:** model hit rate + CLV verified over 90-day window (est. May 2026)
**Architecture note:** ESPN RSS (`https://www.espn.com/espn/rss/nba/news`) is the fastest source
for mid-game player exits (15–30 min ahead of official injury APIs). Slot into:
- `module_d._nuance_check()` as 3rd corroboration source (same pattern as RotoWire + RealGM) → `[3-source confirmed]` confidence boost
- Ask Ludi Telegram bot: "Is Tatum still in the game?" queries ESPN RSS first, then `player_injuries` DB
- Ludi Lens web app: live player status banner for active games using ESPN RSS as feed
- Future live prop recommendations require real-time line feed + ESPN RSS as injury trigger

### Developer Workflow Improvements (identified Feb 20, 2026)
- [ ] **Session start checklist**: `scripts/session_check.py` — quick health check (DB rows, API quota, last sync time) in <5s. Run at start of each dev session.
- [ ] **`AGENTS.md`**: Create agent operating guide (primary rules for Codex-style agents) so CLAUDE.md can stay as supplemental context only
- [ ] **GH workflow shortcuts**: `scripts/run_workflow.sh <name>` wrapper for `gh workflow run` — avoids memorizing exact workflow names
- [ ] **`/compact` habit**: Use before context fills — prevents losing work mid-session
- [ ] **End-of-session memory update**: Always update `memory/MEMORY.md` at session end with key decisions/bugs fixed before compacting

---

### Full Project Audit (Feb 21, 2026) ✅ COMPLETE

**Scope:** 10-sprint audit (code correctness, file cleanup, redundancy, security, modules, workflows, dependencies)
**Status:** All sprints complete, 0 critical issues, codebase production-ready
**Report:** `docs/audit/AUDIT_2026_02_21.md`

---

## Archive

- **docs/archive/phase_reports/** — Phase completion reports (Phases 1–7)
- **docs/STATUS_HISTORY.md** — Phases 1–4 history + Phase 8 sprint archive (Feb 20–24, 2026)
- **reports/** — Calibration analysis, performance breakdowns
- **docs/ARCHITECTURE.md** — System design, module reference, DB schema
- **docs/METHODOLOGY.md** — Edge calc, devigging, CLV tracking
- **best-practices/** — API patterns, sportsbook tiers, lessons learned
