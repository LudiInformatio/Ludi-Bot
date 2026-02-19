# Ludi-Bot Roadmap

**Last Updated:** February 19, 2026 5:45 PM EST
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** Phase 8.10 — League Rankings (next up)
**Completed:** Phases 5–7 ✅ + Phase 8.0-A/B/C/D ✅ + Phase 8.2/8.3/8.4/8.5/8.6/8.7/8.9/8.12/8.14/8.15 ✅ + Slate Date Fix ✅

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
| 8.8 | Game Score Formula v2 | LOW | Add line movement delta + handle% to `_score_game()`. **Blocked: needs Mar 2026 data to backtest** | $0 |
| 8.10 | League Rankings Module | LOW | Weekly SQL ranking tables (PPP by playtype, defense by scheme) via Telegram. Data ready in `ludi.db` | $0 |
| 8.11 | Ludi Power Ratings | LOW | Blended ortg+drtg+pace power ratings for game scoring + Ludi Lens | $0 |
| 8.13 | Ask Ludi — Telegram Bot | MEDIUM | Two-way Telegram bot: natural language → ludi.db + Claude → response. Haiku intent, Sonnet analysis | ~$0.05/day |

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
- **docs/STATUS_HISTORY.md** — Phases 1–4 history
- **reports/** — Calibration analysis, performance breakdowns
- **docs/ARCHITECTURE.md** — System design, module reference, DB schema
- **docs/METHODOLOGY.md** — Edge calc, devigging, CLV tracking
- **best-practices/** — API patterns, sportsbook tiers, lessons learned
