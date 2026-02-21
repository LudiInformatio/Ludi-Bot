# Ludi-Bot Roadmap

**Last Updated:** February 21, 2026 4:33 PM EST
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** Phase 8.13 Ask Ludi (implementation ready)
**Completed:** Phases 5–7 ✅ + Phase 8.0-A/B/C/D ✅ + Phase 8.2/8.3/8.4/8.5/8.6/8.7/8.9/8.10/8.12/8.14/8.15/8.18/8.19 ✅ + Slack/Notification Split ✅ + Model Calibration Fixes ✅ + Feb 20 Post-ASB Audit ✅ + Tank01 Data Expansion ✅ + Injury Intelligence Hardening ✅ + Claude Auth Fix ✅ + Ask Ludi Architecture Research ✅ + Morning Brief Pipeline Hardening ✅ + BetIQ/TeamRankings Research ✅ + BERT/NLP Prompt Architecture Research ✅ + Phase 8.20 Stat Confidence & Edge Calibration ✅ + Production Pipeline/WOWY/Settlement Fix ✅ + Phase 8.18 Game Lines Integration ✅ + Phase 8.19 Prompt Engineering Upgrade ✅ + **Full Project Audit (Sprints 0-10) ✅** + Post-Audit Bug Fixes & Documentation Integration ✅

This is the single source of truth for project tasks and priorities.

**Active Project Docs:**
- **Prompt Engineering Reference:** `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md` — 8 BERT-derived patterns mapped to Claude prompts + priority implementation order
- **Tank01 Data Expansion:** `docs/projects/TANK01_DATA_EXPANSION.md` — 17-endpoint audit, O/U vs alt line parsing guide, model calibration findings, implementation phases
- **Best-Practices API Guide:** `best-practices/api/API_BEST_PRACTICES.md` — BDL + Tank01 complete endpoint reference, lessons learned

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
**Status:** 🟡 ACTIVE — Core pipeline complete, remaining sub-phases are LOW/MEDIUM priority
**Estimated Daily Cost:** ~$0.40/day (~$12/month)

**Ground Rules:**
- Claude handles reasoning/analysis ONLY — never factual NBA data (enforced by CLAUDE.md Critical Data Rules)
- All NBA facts come from `ludi.db` or live APIs (fetched, not recalled)
- Raw math stays deterministic (Poisson sims, devigging, Kelly sizing)
- Graceful degradation: if Claude API fails, fall back to existing rule-based logic

**Sub-Phases:**

| # | Sub-Phase | Status | Description | Cost |
|---|-----------|--------|-------------|------|
| Pre ✅ | Shared Claude Infrastructure | DONE | `utils/claude_client.py`, `utils/claude_prompts.py`, config.py update | $0 |
| 8.0-A ✅ | Injury Schema + Sync | DONE | `player_injuries` table, `scripts/sync_injuries.py` (BDL primary, Tank01 fallback) | $0 |
| 8.0-B ✅ | Three-Tier Active Roster | DONE | Tier 1 (active), Tier 2 (WELCOME_BACK), Tier 3 (long-term out) in `main.py` | $0 |
| 8.0-C ✅ | Smart Vacuum Enhancement | DONE | `module_x_scenario.py` — DB-driven `days_out`, absorbed/active/partial scale | $0 |
| 8.0-D ✅ | Workflow Wiring | DONE | `sync_injuries.py` wired into `data_sync.yml`, `daily_briefing.yml`, `capture_closing_lines.yml` | $0 |
| 8.2 ✅ | Game Notes Generator | DONE | S.A.V.A.G.E. cards, top 4 games by tier-weight score, notes persisted to `game_notes_log` | ~$0.12/day |
| 8.3 ✅ | Player Spotlight Cards | DONE | 2-3 sentence narratives for DIAMOND/BLUE CHIP only, L10 + injury context | ~$0.15/day |
| 8.4 ✅ | Archetype Classifier | DONE | `scripts/classify_archetypes.py` — weekly Haiku batch, 19 types, two-gate Synergy validation | ~$0.03/wk |
| 8.5 ✅ | Play Curation Engine | DONE | Haiku sanity gate + Sonnet Top 5, max-2-per-game enforced | ~$0.08/day |
| 8.6 ✅ | CLV + Retrospective | DONE | CLV extended to all 11 markets, `weekly_retrospective.py` (Tuesdays) | ~$0.01/day |
| 8.7 ✅ | Perplexity Integration | DONE | Sonar replaces DuckDuckGo. 4 injection points: injury nuance, game scoring, game notes, curation | ~$0.10/day |
| 8.9 ✅ | Rotation/Minutes Projection | DONE | `rotation_profiles` (396), `beneficiary_minutes` (789), stagger stats (2,282 pairs), stint profiles (163) | $0 |
| 8.12 ✅ | Roster Intelligence | DONE | Tier 1.5 freshly-traded detection, stale profile cleanup, NEW_TO_TEAM 0.95 dampener | $0 |
| 8.14 ✅ | Scoring Environment Intelligence | DONE | Dynamic 14d OVER hit rate tracker, 4 data-proven OVER filters, opponent NULL bug fixed, Claude env context | $0 |
| 8.15 ✅ | Trend Engine + Enriched Briefings | DONE | `player_trends` table (4,500+ rows), `trend_engine.py` (hybrid pre-computed + live), `format_bet_card()` reusable method, enriched game notes (beneficiary/pace/combined Perplexity), enriched spotlights (L7/L10/L15 trends, minutes, hit rate, streaks, stagger context, combo props) | $0 |
| 8.10 ✅ | League Rankings Module | DONE | `scripts/generate_rankings.py` — weekly PPP (P&R/ISO/Spot-Up) + scheme distribution + pace leaders via Telegram. Min 10 games/30d gate. Wired into `weekly_validation.yml` | $0 |
| Infra ✅ | Slack/Notification Split | DONE | `utils/slack_notifier.py` — ops alerts (failures, health, QA, pipeline stats, PM bot work notes) route to Slack (`vibestarters` #C0AGBQXRXB3). Telegram stays clean for betting product only. 20 files updated. | $0 |
| Infra ✅ | Model Calibration Fixes | DONE | `module_f.py`: BLK OVER hard skip (33.6% WR → filtered), dead Filter 6 removed. `morning_brief.py`: B2B fatigue flag wired, data-driven team notes, leverage profile context. Spotlight `analysis_block` populated via `get_matchup_analysis()`. | $0 |
| Tank01 ✅ | Tank01 Data Expansion + Phase 3 Hardening | DONE | Central client (12 methods), STL/BLK weights fix, SIM_COUNT 10k, games fallback chain (Odds API→Tank01→BDL), output assertion gate (5 checks), Module H games bridge + fantasy_pts, Tank01 props validator in Module A, 4 new sync scripts (team info/projections/news/injury history), 4 new DB tables, morning brief streak notes. See `docs/projects/TANK01_DATA_EXPANSION.md` | $0 |
| Infra ✅ | Injury Intelligence Hardening | DONE | RealGM RSS dual-source corroboration in `_nuance_check()` (confidence 0.95 when RotoWire + RealGM agree). AI blurb prompt hardened: `INJURY_BLURB_SYSTEM` + `INJURY_BLURB_PARSE_PROMPT` (5 few-shot examples, `tonight_available`, `blurb_is_stale`, `temperature=0.0`). Intraday refresh: `injury_refresh.yml` (4 daytime + 15 evening 20-min runs, staleness guard prevents API waste). Evening lock: `--force` pre-sync captures late scratches before 6 PM cards. `module_d.get_refresh_interval()` aligned: 120 min day / 20 min game-time. | $0 |
| Infra ✅ | Claude Auth Fix | DONE | `utils/claude_client.py` priority reordered: ANTHROPIC_API_KEY (Priority 1) → `~/.claude/config.json` OAuth skipped in CI via `GITHUB_ACTIONS` check (Priority 2, local only) → `CLAUDE_CODE_OAUTH_TOKEN` last resort (Priority 3). `ANTHROPIC_API_KEY` added to GitHub repo secrets. Root cause: expired CLAUDE_CODE_OAUTH_TOKEN (set Feb 3) was winning Priority 1 in CI — fixed. | $0 |
| Infra ✅ | Morning Brief Pipeline Hardening | DONE | Removed `send_photo` + image card pipeline → native chunked Telegram text. Removed January hardcoded team watchlist → `target_teams=None` (all games processed). Spotlight 400 Bad Request fixed: 4000-char truncation + Markdown fallback. `sync_injuries.py` `skip_resolve` bug fixed: Step 4 RSS call was resolving all BDL/Tank01 injuries (0 active in DB). All games now scored by tier-weight algorithm, not filtered by hardcoded list. | $0 |
| Research ✅ | BetIQ / TeamRankings Competitive Analysis | DONE | 3-session sprint (Feb 20). Findings: 6 cross-game patterns (B2B covers at 78-82% ATS, 2-3 day rest ATS trap, home UNDER 30-40%, heavy favorites fail ATS, underdog covers, H1/H2 team identity). Feature gap analysis: Tier 1 all buildable from existing ludi.db. Full doc: `docs/research/BETIQ_TEAMRANKINGS_RESEARCH.md`. | $0 |
| Research ✅ | BERT/NLP Prompt Architecture Research | DONE | Feb 20 late PM. Studied google-research/bert codebase + Procedia CS 2024 BERT sentiment paper. Derived 8 patterns directly applicable to our Claude prompt architecture. Key findings: zero-shot GAME_NOTES/SPOTLIGHT templates are the root cause of format drift + 400 errors; few-shot examples are highest-ROI fix. Domain WR stats should be injected into Sonnet curation. Haiku NSP gate replaces keyword matching in `_score_game()`. Full reference: `best-practices/ai/PROMPT_ENGINEERING_PATTERNS.md`. | $0 |
| 8.20 ✅ | Stat Confidence & Edge Calibration | DONE | Feb 20 9:46 PM EST. Problem: model reports 35-40% edge on PTS/REB/AST but those bets win at 48-52%. Root cause: edge calc is systematically overconfident for high-variance stats. Fix: 3 layers — (1) `_apply_stat_calibration()` in Module F V5.3: per-stat edge multipliers (PTS OVER 0.78x, BLOCKS UNDER 1.25x boost — structural book inefficiency). (2) `_rmse_sizing_modifier()`: RMSE-based unit penalty (PTS/PRA 0.85x, BLOCKS/STEALS 1.0x). (3) `_get_system_wr_context()` in `curate_plays.py`: Wilson 95% lower bound grades injected into Sonnet system prompt as live domain knowledge. (4) `scripts/build_stat_confidence.py`: nightly cache builder → `cache/stat_confidence.json`. Full methodology: `best-practices/data/STAT_CONFIDENCE_FRAMEWORK.md`. Data: BLOCKS UNDER A+ iron-clad (68.7% Wilson floor, n=2187). 7 F-grade avoids confirmed. | $0 |
| 8.18 ✅ | Game Lines Integration | DONE | Fixed `total=0` data flow bug with try/except validation in `main.py:379-380`. Added `team_totals` Odds API market (zero extra API calls). Implemented Module E 3-tier team scoring modifier (Tier 1: real team totals from Odds API, Tier 2: derived implied = (total ± spread)/2, Tier 3: blanket fallback). Fixed Odds API spread/totals parsing by team name (not index). Added Home Total/Away Total rows to GAME_NOTES_TEMPLATE. Added USE_TEAM_TOTALS_MODIFIER feature flag. 6 files modified: config.py, main.py, module_a.py, module_e.py, claude_prompts.py, morning_brief.py. **Parallel sprint with 8.19, clean integration.** | $0 |
| 8.19 ✅ | Prompt Engineering Upgrade | DONE | Applied 6 of 8 BERT-derived patterns (2 already done). (1) Few-shot examples: GAME_NOTES_EXAMPLE + SPOTLIGHT_EXAMPLE prepended to Claude system prompts (zero-shot → 1-shot fixes format drift). (2) Label space first: SANITY_GATE_SYSTEM defines valid JSON output in curate_plays.py. (3) text_a/text_b separation: === section dividers === in GAME_NOTES_TEMPLATE. (4) Pre-truncate: _safe_inject() helper with max_chars dict (5 template variables). (5) Haiku NSP news gate: replaces keyword matching in _score_game() with -2.0 to +2.0 relevance score. (6) Parse failure logging: structured [HAIKU PARSE FAIL] / [SONNET PARSE FAIL] messages. Pattern 2 (domain WR injection) completed in 8.20. Pattern 8 (feedback loop) future work. 3 files modified: scripts/curate_plays.py, utils/claude_prompts.py, morning_brief.py. **Parallel sprint with 8.18, clean integration.** | ~$0.001/day |
| 8.8 | Game Score Formula v2 | LOW | Add line movement delta + handle% to `_score_game()`. **Blocked: needs Mar 2026 data to backtest. Phase 8.18 creates the slot for this to plug in.** | $0 |
| 8.11 | Ludi Power Ratings | LOW | Blended ortg+drtg+pace power ratings for game scoring + Ludi Lens | $0 |
| 8.13 | Ask Ludi — Telegram Bot | MEDIUM | Natural language → ludi.db + Claude → response in Telegram thread. Architecture research complete (Feb 20): python-telegram-bot v21+ long polling, Haiku intent ($0.0001/call) → Sonnet analysis, read-only SQLite (`?mode=ro`), launchd keepalive, 3-file implementation (`bots/ask_ludi.py`, `ask_ludi_db.py`, `ask_ludi_handlers.py`). See `docs/FUTURE_DATA_SOURCES.md` §6. | ~$0.05/day |
| 8.16 | Suspension Intelligence | MEDIUM | `sync_suspensions.py` (Perplexity → Claude Haiku → auto-insert into `player_injuries` as SUSPENDED). Module D + Module X pick up automatically. Three injection points: morning sync, game context query, Module D `get_injuries()`. | ~$0.02/day |
| 8.17 | Foul Intelligence | MEDIUM | Extend `sync_stint_profiles.py` to parse foul events from PlayByPlayV3 (same API, same loop, no extra cost). New `player_foul_splits` table (period, clock, foul_number, ref_name). Unlocks: early foul trouble → Module C minutes dampener, ref-player bias rebuild, weekly Claude context. | $0 |

---

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

**Remaining (next sprint):** Games table fallback chain (3A), output assertion gate (3B), Module H→games bridge (3C), Perplexity/Claude prompt enrichment (2H)

---

### Ask Ludi Architecture Research ✅ COMPLETE (Feb 20, 2026 PM)

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

### Injury Intelligence Hardening ✅ COMPLETE (Feb 20, 2026 PM)

Second sprint of Feb 20 — closed remaining injury pipeline gaps and built intraday refresh infrastructure.

**New Capabilities:**
- **RealGM RSS** added as 2nd corroboration source alongside RotoWire. `_nuance_check()` compares both; when they agree → confidence bumped to 0.95 (`[2-source confirmed]`)
- **AI blurb prompt** hardened: centralized `INJURY_BLURB_SYSTEM` + `INJURY_BLURB_PARSE_PROMPT` with 5 few-shot examples, `tonight_available` field (true/false/uncertain), `blurb_is_stale` flag, `temperature=0.0` for deterministic classification
- **`injury_refresh.yml`**: new GitHub Actions workflow — 4 daytime runs (every 2 hr, 11 AM–5 PM EST) + 15 evening runs (every 20 min, 6–10:40 PM EST). Staleness guard in `sync_injuries.py` exits early if DB is already fresh — protects Tank01/BDL quota
- **Evening slate lock**: `--force` injury sync step before `morning_brief --mode evening` captures 4–6 PM late scratches in DB before 6 PM cards generate
- **`--force` flag** on `sync_injuries.py` for on-demand overrides (web app, bot, evening lock)
- **Downstream ready**: Telegram bot (8.13) and Ludi Lens web app query `player_injuries` directly — always ≤20 min stale during game time

---

### Morning Brief Pipeline Hardening + BetIQ Research ✅ COMPLETE (Feb 20, 2026 — Late PM)

Third sprint of Feb 20 — hardened the morning/evening brief pipeline and completed competitive analysis.

**Pipeline Fixes (both morning + evening modes):**
- **Native Telegram text:** Removed `send_photo` + image card pipeline from `morning_brief.py`. Both morning and evening modes now send chunked native text (4000-char splits). No more PIL/PNG dependencies in briefing flow.
- **All-game processing:** Removed January hardcoded watchlist (`['PHX','MIA','CHI',...]`). Set `target_teams=None` — all games on the slate are now processed and scored by the tier-weight algorithm. Tonight's IND@WAS was previously invisible.
- **Spotlight Markdown fallback:** Claude spotlight outputs truncated to 4000 chars and retried as plain text on 400 Bad Request. Fixes Kyle Anderson-style failures.
- **Injury `skip_resolve` bug:** `sync_to_database()` called twice in `sync_injuries.py main()`. Step 4 RSS call (7 players) was resolving all 34+ BDL/Tank01 injuries because they weren't in the RSS batch. Fixed with `skip_resolve=True` parameter — RSS call now only adds, never sweeps.
- **`.gitignore` hardening:** Added `archives/data/`, `logs/health/`, `*.png` to gitignore.

**Competitive Research:**
- BetIQ/TeamRankings 3-session sprint — 6 cross-game ATS/O-U patterns confirmed across CLE@CHA, DAL@MIN, IND@WAS. 20+ power rating dimensions mapped. Tier 1 features all buildable from existing `ludi.db` (no new APIs). Doc: `docs/research/BETIQ_TEAMRANKINGS_RESEARCH.md`

**Game Lines Integration Planned (Phase 8.18):**
- Confirmed: Odds API supports `team_totals` market (zero extra API calls — same request). BDL and Tank01 do NOT have team totals. Architecture: real team totals (Odds API) → derived implied totals (BDL fallback) → blanket modifier. Full plan ready for implementation.

---

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
- [ ] Schedule `sync_pbp_wowy.py` weekly in `data_sync.yml` (season-level on/off splits, currently manual-only)
- [ ] Multi-book arbitrage detection
- [ ] Steam move detection (rapid line movement alerts)

### GH Actions / Claude Ops Improvements (identified Feb 20, 2026)
- [ ] **`claude-ops-hub.yml` upgrade**: Use `anthropics/claude-code-action@v1` with `CLAUDE_CODE_OAUTH_TOKEN` — proper tool, reads workflow logs, posts Slack diagnosis. Currently uses ad-hoc Sonnet call.
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
- **docs/STATUS_HISTORY.md** — Phases 1–4 history
- **reports/** — Calibration analysis, performance breakdowns
- **docs/ARCHITECTURE.md** — System design, module reference, DB schema
- **docs/METHODOLOGY.md** — Edge calc, devigging, CLV tracking
- **best-practices/** — API patterns, sportsbook tiers, lessons learned
