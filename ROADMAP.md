# Ludi-Bot Roadmap

**Last Updated:** February 25, 2026 — 3:00 PM EST
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** Phase 8.13 Ask Ludi (implementation ready) + Phase 8.23 Layer 1 collection (start now — Mar 10 window) + 2024-25 Historical Backfill (kick off this session)
**Completed:** Phases 1–7 + Phase 8.0-A/B/C/D + sub-phases 8.2–8.20 ✅ (full history: `docs/STATUS_HISTORY.md`) + **Classification Gate 2 Hardening + BERT Pattern 9 ✅** + **UNK Position Cleanup + Archetype Naming Audit ✅**

This is the single source of truth for project tasks and priorities.

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

- [-] Phase 8.13 — Ask Ludi Telegram Bot (`bots/ask_ludi.py`) — architecture complete, 3-file implementation ready
- [-] Phase 8.23 — Claude/Perplexity Feedback Loop — Layer 1 `claude_analysis_log` collection (14-day scan window: ~Mar 10)

---

### Phase 8: AI-Enhanced Pipeline (Claude Integration)

**Goal:** Add Claude as an analytical reasoning layer on top of the deterministic pipeline
**Principle:** LLMs orchestrate and reason — never calculate. Math stays deterministic.
**Status:** 🟡 ACTIVE — Core pipeline complete, remaining sub-phases are LOW/MEDIUM priority
**Estimated Daily Cost:** ~$0.40/day (~$12/month)

**Completed sub-phases (Pre, 8.0-A/B/C/D, 8.2–8.7, 8.9–8.10, 8.12, 8.14–8.16, 8.18–8.20, Infra):** All DONE. Full details: `docs/STATUS_HISTORY.md`

**Active & Remaining Sub-Phases:**

| # | Sub-Phase | Status | Description | Cost |
|---|-----------|--------|-------------|------|
| 8.8 | Game Score Formula v2 | LOW | Add line movement delta + handle% to `_score_game()`. **Blocked: needs Mar 2026 data.** | $0 |
| 8.11 | Ludi Power Ratings | LOW | Blended ortg+drtg+pace power ratings for game scoring + Ludi Lens. | $0 |
| 8.13 | Ask Ludi — Telegram Bot | MEDIUM | Natural language → ludi.db + Claude → Telegram reply. Architecture complete: python-telegram-bot v21+, Haiku intent → Sonnet, read-only SQLite. See `docs/FUTURE_DATA_SOURCES.md` §6. | ~$0.05/day |
| 8.17 | Foul Intelligence | MEDIUM | Parse foul events from PlayByPlayV3 → `player_foul_splits` table → Module C minutes dampener + ref-player bias rebuild. $0 extra API cost. | $0 |
| 8.21 | ESPN Full Integration | MEDIUM | ESPN client + nightly `longComment` pull to `player_injuries` + Tier 3 game lines fallback in `module_a.py`. See `best-practices/api/API_BEST_PRACTICES.md`. | $0 |
| 8.22 | Social Intelligence System | MEDIUM | Social sentiment + market signals → Prop Pulse Score injected into `curate_plays.py`. Architecture complete. See `docs/projects/SOCIAL_INTELLIGENCE_SYSTEM.md`. | ~$0.02/day |
| 8.23 | Claude/Perplexity Feedback Loop | MEDIUM | 3-layer OpenClaw: `claude_analysis_log` collection → weekly Wilson calibration (`calibrate_claude_outputs.py`) → inject into `_get_system_wr_context()`. **Start Layer 1 NOW — 14-day scan ~Mar 10.** | $0 |
| 8.24 | Edge Type Labeling ⭐ | MEDIUM | Tag each bet: `Projection`/`Matchup`/`Injury-Vacuum`/`Hot-Streak`. 1 Haiku call in `module_f.py` bet card. Product differentiator vs competitors. See `docs/FUTURE_DATA_SOURCES.md` §5.2-B. | ~$0.01/day |
| 8.25 | Key Advantage Callout ⭐ | MEDIUM | Auto-surface #1 exploitable angle per game in `morning_brief._score_game()`. 1 Haiku call/game — e.g. "IND allows 38% rim FG% — ROLL_MAN OVER angle". See `docs/FUTURE_DATA_SOURCES.md` §5.2-B. | ~$0.01/day |
| 8.26 | Correlated Props Flagging ⭐ | MEDIUM | Scan Top 5 bets for same-game pairs → flag SGP correlation risk. Python logic + 1 Haiku confirm in `curate_plays.py`. See `docs/FUTURE_DATA_SOURCES.md` §5.2-B. | ~$0.005/day |

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
- [ ] DVP rankings sync — `defender_matchups` table exists but 0 rows. Create `scripts/sync_dvp_rankings.py` (PBP Stats `get_shot_query_summary` or Tank01 endpoint). Feeds phase 8.25 Key Advantage callout + player spotlight DVP rank badge.
- [ ] PBP Stats: wire `get_possessions` endpoint → clutch detection + blowout tax validation (Section 4.4 in `docs/FUTURE_DATA_SOURCES.md`)
- [ ] Ghost Protocol date-skip optimization: pre-check `team_lineups` before scraping each date (~30s saved per already-synced date in weekly backfills)
- [ ] Multi-book arbitrage detection
- [ ] Steam move detection (rapid line movement alerts)

### GH Actions / Claude Ops Improvements (identified Feb 20, 2026)
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
**Blocked until:** Model hit rate + CLV verified over 90-day window (est. May 2026). ESPN RSS is planned corroboration source (15–30 min faster than injury APIs).

### Developer Workflow Improvements (identified Feb 20, 2026)
- [ ] **Session start checklist**: `scripts/session_check.py` — quick health check (DB rows, API quota, last sync time) in <5s. Run at start of each dev session.
- [ ] **`AGENTS.md`**: Create agent operating guide (primary rules for Codex-style agents) so CLAUDE.md can stay as supplemental context only
- [ ] **GH workflow shortcuts**: `scripts/run_workflow.sh <name>` wrapper for `gh workflow run` — avoids memorizing exact workflow names
- [ ] **`/compact` habit**: Use before context fills — prevents losing work mid-session
- [ ] **End-of-session memory update**: Always update `memory/MEMORY.md` at session end with key decisions/bugs fixed before compacting

---

## Archive

- **docs/STATUS_HISTORY.md** — Phases 1–4 history + Phase 8 sprint archive (Feb 20–25, 2026)
- **docs/archive/phase_reports/** — Phase completion reports (Phases 1–7)
- **docs/audit/AUDIT_2026_02_21.md** — Full 10-sprint audit report (0 critical issues, production-ready)
- **reports/** — Calibration analysis, performance breakdowns
- **docs/ARCHITECTURE.md** — System design, module reference, DB schema
- **docs/METHODOLOGY.md** — Edge calc, devigging, CLV tracking
- **best-practices/** — API patterns, sportsbook tiers, lessons learned
