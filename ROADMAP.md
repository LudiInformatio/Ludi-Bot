# Ludi-Bot Roadmap

**Last Updated:** February 19, 2026
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** Phase 8.0 Injury Intelligence System
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
**Phase 8.0 Foundation Plan:** `docs/PHASE_8_FOUNDATION_PLAN.md` (Injury + Rotation Intelligence)
**Design Doc:** `.claude/plans/crystalline-swimming-horizon.md`
**Estimated Daily Cost:** ~$1.17/day (~$35/month)

**Ground Rules:**
- Claude handles reasoning/analysis ONLY — never factual NBA data (enforced by CLAUDE.md Critical Data Rules)
- All NBA facts come from `ludi.db` or live APIs (fetched, not recalled)
- Raw math stays deterministic (Poisson sims, devigging, Kelly sizing)
- All Claude outputs must be auditable/reproducible
- Graceful degradation: if Claude API fails, fall back to existing rule-based logic

**Sub-Phases (recommended implementation order):**

| # | Sub-Phase | Priority | Description | Daily Cost |
|---|-----------|----------|-------------|------------|
| 8.0 | **Injury Intelligence System** | **CRITICAL** | **Persistent injury tracking (status, return dates, descriptions), long-term injury handling, recently-returned player pipeline. REQUIRES: nba_api==1.11.3 with league_id parameter** | **$0** |
| 8.1 | Injury Intelligence Upgrade | HIGH | BDL → primary, Claude for ambiguous text | ~$0.20 |
| 8.5 | Play Curation Engine | HIGH | Sanity gate (Haiku) + Top 5 curation (Sonnet) | ~$0.20 |
| 8.2 | Game Notes Generator | HIGH | Analytical Telegram briefings | ~$0.35 |
| 8.3 | Player Spotlight Cards | HIGH | Per-bet narratives for DIAMOND/BLUE CHIP | ~$0.25 |
| 8.9 | **Rotation/Minutes Projection** | **MEDIUM** | **Track coach rotation patterns from PBP data (nba_api PlayByPlayV3), situational minutes modeling, stint-level analysis** | **TBD** |
| 8.7 | Perplexity MCP | MEDIUM | Real-time search replacing DuckDuckGo | ~$0.10 |
| 8.4 | Archetype Classifier Fix | MEDIUM | Weekly batch classification via Claude | ~$0.07 |
| 8.6 | MCP Server Integration | LOW | BDL + Odds API MCP for Ops Hub | $0 |

**Shared Infrastructure:**
- [ ] Create `utils/claude_client.py` — shared Anthropic SDK wrapper
- [ ] Add `ANTHROPIC_API_KEY` to config.py and `.env.template`
- [x] Verify `nba_api==1.11.3` installed with league_id parameter support ✅
- [x] Add PlayByPlayV3 endpoint support to `utils/nba_api_client.py` ✅

**Key Tasks:**
- [ ] 8.0: **Injury Intelligence System (Pre-Phase 8 Foundation)**
  - Create `player_injuries` table (status, return_date, injury_type, description, onset_date, days_out)
  - Enhance Module D to persist BDL injury metadata (not just cache)
  - Fix `get_active_roster()` to handle long-term injuries (30+ days) and recently returned players
  - Create `scripts/sync_injuries.py` for daily injury refresh
  - Add injury intel to daily Telegram briefing
- [ ] 8.1: Promote BDL injuries to primary, add Claude reasoning for ambiguous statuses
- [ ] 8.5: Sanity gate + holistic "Top 5 Plays" curation with reasoning
- [ ] 8.2: Per-game analytical cards with Key Advantages, Injury Beneficiaries, WOWY deltas
- [ ] 8.3: 2-3 sentence narratives with playtype breakdown, DVP ranking, hit rates
- [ ] 8.9: **Rotation/Minutes Projection Enhancement**
  - Parse play-by-play data to extract actual rotation patterns (check-in/check-out times)
  - Build coach tendency models (stint lengths, rest patterns, rotation depth)
  - Model situational minutes (blowout tax, close game boost, B2B rest management)
  - Create `scripts/analyze_rotation_patterns.py` to track historical patterns
  - Integrate rotation intelligence into Module C minutes projection
- [ ] 8.7: Perplexity MCP replacing Module D's DuckDuckGo `_nuance_check()`
- [ ] 8.4: `scripts/classify_archetypes.py` weekly batch, re-enable Module F modifiers
- [ ] 8.6: Configure BDL MCP server, add to Claude Ops Hub

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
