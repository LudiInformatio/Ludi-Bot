# Ludi-Bot Roadmap

**Last Updated:** February 19, 2026
**Current Phase:** Phase 8 — AI-Enhanced Pipeline
**Active Work:** Phase 8.10 — League Rankings (next up)
**Completed:** Phases 5–7 ✅ + Phase 8.0-A/B/C/D ✅ + Phase 8.5/8.2/8.3/8.6/8.7 ✅ + Phase 8.4 ✅ + Phase 8.9 ✅ + Phase 8.12 ✅ + Phase 8.14 ✅ + Slate Date Fix ✅

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
**Status:** 🟡 ACTIVE — Phase 8.0 complete (Feb 19), starting Phase 8.5
**Phase 8 Foundation Plan:** `docs/PHASE_8_FOUNDATION_PLAN.md` (Injury Intelligence + Phase 8 Pre-Work)
**Design Doc:** `.claude/plans/curried-growing-toucan.md` (revised Feb 17 — Ludi-Lite review + SMA audit)
**Estimated Daily Cost:** ~$0.40/day (~$12/month) — game notes scoped to top 4 games (was $0.73)

**Ground Rules:**
- Claude handles reasoning/analysis ONLY — never factual NBA data (enforced by CLAUDE.md Critical Data Rules)
- All NBA facts come from `ludi.db` or live APIs (fetched, not recalled)
- Raw math stays deterministic (Poisson sims, devigging, Kelly sizing)
- All Claude outputs must be auditable/reproducible
- Graceful degradation: if Claude API fails, fall back to existing rule-based logic

**Sub-Phases (recommended implementation order):**

| # | Sub-Phase | Priority | Description | Daily Cost |
|---|-----------|----------|-------------|------------|
| **Pre** ✅ | **Shared Claude Infrastructure** | **DONE** | **`utils/claude_client.py` (OAuth-first auth, Haiku/Sonnet), `utils/claude_prompts.py` (ROSTER_RULES + templates), config.py update** | **$0** |
| 8.0-A ✅ | Injury Schema + Sync | DONE | `player_injuries` table (intraday-safe), 4 `players` columns, `scripts/sync_injuries.py` standalone script. BDL primary, Tank01 fallback. All 4 canonical gaps resolved. | $0 |
| 8.0-B ✅ | Three-Tier Active Roster | DONE | `main.py` roster fix: Tier 1 (active), Tier 2 (recently returned "WELCOME_BACK"), Tier 3 (long-term out logged). Graceful fallback if table empty. | $0 |
| 8.0-C ✅ | Smart Vacuum Enhancement | DONE | `module_x_scenario.py` — DB-driven `days_out` lookup, `_classify_vacuum_smart()` (absorbed/active/partial scale), `_get_l10_stats()` from `player_game_logs`. | $0 |
| 8.0-D ✅ | Workflow Wiring | DONE | `sync_injuries.py` wired into `data_sync.yml` (5AM), `daily_briefing.yml` (11AM), `capture_closing_lines.yml` (5:30PM) | $0 |
| 8.5 ✅ | Play Curation Engine | DONE | Haiku sanity gate + Sonnet Top 5 curation. Board-wide, game-agnostic. MarkdownV2 escaping fixed. Max-2-per-game enforced in code. | ~$0.08 |
| 8.2 ✅ | Game Notes Generator | DONE | S.A.V.A.G.E. cards. Smart selection: top 4 games by tier-weight score. Notes persisted to `game_notes_log`. | ~$0.10-0.14 |
| 8.3 ✅ | Player Spotlight Cards | DONE | 2-3 sentence narratives for DIAMOND/BLUE CHIP only (~5/day). L10 + injury context injected. | ~$0.15 |
| 8.6 ✅ | CLV + Retrospective | DONE | CLV extended to all 11 markets. `settle_bets.py` clv fixed. `weekly_retrospective.py` win+loss analysis (~$0.054/week, Tuesdays). | ~$0.01 |
| 8.7 ✅ | Perplexity Integration | DONE | Sonar replaces DuckDuckGo in Module D. 4 injection points: injury nuance, game scoring bonus, game notes {schedule_notes}, Haiku soft-scratch gap. Module G referee fallback bonus. | ~$0.10 |
| 8.4 ✅ | Archetype Classifier Fix | DONE | `scripts/classify_archetypes.py` — weekly Claude Haiku batch (players + team schemes). Two-gate Synergy validation. Wired into `weekly_validation.yml`. | ~$0.03/wk |
| 8.9 ✅ | Rotation/Minutes Projection | DONE | `rotation_profiles` (396), `beneficiary_minutes` (789), `player_stagger_stats` (2,282 pairs), `player_stint_profiles` (163). `_get_projected_minutes()` in Module C, Tier 0 in Module X. | $0 |
| 8.14 ✅ | Scoring Environment Intelligence | DONE | Dynamic 14d OVER hit rate tracker. 4 data-proven OVER filters (TWO_WAY_WING, PTS 25+, SAC/IND/CLE, REB home). Opponent NULL bug fixed. Claude gets env label + team situational context in game notes + curation. | $0 |
| 8.8 | Game Score Formula v2 | LOW | Add line movement delta + handle% to `_score_game()` in `morning_brief.py`. Backtest vs CLV after Mar 2026 data accumulates. | $0 |
| 8.10 | League Rankings Module | LOW | Weekly SQL ranking tables for player/team types via Telegram | $0 |
| 8.11 | Ludi Power Ratings | LOW | Blended ortg+drtg+pace power ratings for game scoring + Ludi Lens | $0 |
| 8.13 | Ask Ludi — Interactive Telegram Bot | MEDIUM | Two-way Telegram bot: user sends message → bot parses intent → pulls from ludi.db + Claude → responds. Commands: `gamenote HOU CHA`, `profile DEN 14d`, `props Luka PTS`, `slate`, `rotation Tatum`. Nickname/alias handling (e.g. "Joker" → Jokic, "KD" → Durant). New: `scripts/run_telegram_bot.py` daemon + `utils/telegram_bot_handler.py`. Haiku for intent classification, Sonnet for analysis. Bridges gap until Ludi Lens web app. | ~$0.05/day |

**Shared Infrastructure (Pre-Work — COMPLETE ✅ Feb 19):**
- [x] Create `utils/claude_client.py` — OAuth-first auth (CLAUDE_CODE_OAUTH_TOKEN → ~/.claude/config.json → ANTHROPIC_API_KEY), Haiku/Sonnet model selection, token tracking, graceful degradation ✅
- [x] Create `utils/claude_prompts.py` — ROSTER_RULES anti-hallucination block, GAME_NOTES_TEMPLATE, SPOTLIGHT_TEMPLATE ✅
- [x] Add `CLAUDE_AUTH_TOKEN` to config.py via `_get_claude_auth_token()` helper ✅
- [x] Add `CLAUDE_CODE_OAUTH_TOKEN=your-token-here` to `.env.template` ✅
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
- [x] **Pre-Work (Step 0):** `utils/claude_client.py` + `utils/claude_prompts.py` + config.py update ✅ (Feb 19)
- [x] **8.0-A (Step 1):** `player_injuries` table + 4 `players` columns + `scripts/sync_injuries.py` (BDL primary, Tank01 fallback). 51/55 canonical IDs resolved. NULL team_abbreviation bug fixed (commit 8e53fcf). ✅ (Feb 19)
- [x] **8.0-B (Step 3):** Three-tier roster in `main.py`. Tier 1/2/3 logic live. Graceful fallback if `player_injuries` empty. ✅ (Feb 19)
- [x] **8.0-C (Step 4):** Smart vacuum in `module_x_scenario.py` — `_classify_vacuum_smart()` (DB-driven days_out, absorbed/active/partial scale), `_get_l10_stats()` from `player_game_logs`. ✅ (Feb 19)
- [x] **8.0-D (Step 5):** `sync_injuries.py` wired into `data_sync.yml` (5AM), `daily_briefing.yml` (11AM), `capture_closing_lines.yml` (5:30PM) with correct IS_GAME_DAY_REPORT flags. ✅ (Feb 19)
- [x] **8.5 (Step 6):** `scripts/curate_plays.py` — Stage 1 Haiku sanity gate (injury contradictions, impossible lines) + Stage 2 Sonnet Top 5 (correlation-aware, diversified). Claude NEVER recalculates edge. ✅ (Feb 19)
- [x] **8.2 (Step 7):** Structured S.A.V.A.G.E. game cards in `morning_brief.py`. Context table + Injury Impact + Scheme Edge + Key Edges. Notes persisted to `game_notes_log` table. Smart game selection: top 4 games by tier-weight score (DIAMOND=4.0, BLUE CHIP=2.5, CORE ASSET=1.0, THE STEAL=0.5, BENEFICIARY bonus=1.0). Token cost: ~$0.10-0.14/day vs $0.35 for all games. ✅ (Feb 17)
  - **Future:** Backtest game score formula vs CLV/win rate after 4-6 weeks of data (Mar 2026). Validate tier-weight formula produces better-performing game selections than random. Query: `game_notes_log JOIN bet_recommendations ON game_id` — compare avg CLV for selected vs skipped games.
- [x] **8.3 (Step 8):** Player spotlight cards in `morning_brief.py`. DIAMOND + BLUE CHIP only. Helper methods `_get_db_conn()` + `_get_l10_for_spotlight()` added. ✅ (Feb 19)
- [x] **8.6 (Step 9):** CLV capture extended to all 11 markets (PTS/REB/AST/3PM/STL/BLK/TOV/PRA/PR/PA/RA). `settle_bets.py` clv field now uses clv_cents. `game_notes_log` table persists Claude game cards. `scripts/weekly_retrospective.py` — win+loss pattern analysis over game-notes bets only (~$0.054/week, Tuesdays). ✅ (Feb 17)
- [x] **8.7 (Step 10):** Perplexity Sonar integration. `utils/perplexity_client.py` (file-based cache, graceful fallback). 4 injection points: `module_d` injury nuance, `morning_brief._score_game()` narrative bonus, GAME_NOTES_TEMPLATE `{schedule_notes}`, `curate_plays` soft-scratch check. Module G referee Perplexity fallback (bonus). Commit: `a4ca3b3`. ✅ (Feb 18)
- [x] **8.4:** `scripts/classify_archetypes.py` — weekly Claude Haiku classification. Part A: player archetypes (19 types, two-gate Synergy validation). Part B: team scheme conflict resolution. Wired into `weekly_validation.yml`. ✅ (Feb 18)
- [x] **8.9-A:** Core rotation system live ✅ (Feb 18) — `rotation_profiles` (396 players), `beneficiary_minutes` (789 pairs, e.g. Embiid OUT → Drummond +18.3 min). `_get_projected_minutes()` in `module_c.py`, Tier 0 in `module_x_scenario.py`. `USE_MINUTES_PROJECTION` feature flag in `config.py`. Rotation trends: Jaxson Hayes +16.8 min, Bronny -7.2 min.
- [x] **8.9-B:** `player_stagger_stats` (2,282 pairs, game-log SQL — PBP Stats endpoint doesn't exist) + `player_stint_profiles` (163 profiles, 80 games, PlayByPlayV3 subs). Wired into `weekly_validation.yml`. ✅ (Feb 18)
- [x] **8.12:** Roster Intelligence — trade/waiver awareness. Tier 1.5 freshly-traded roster (5 players detected: Coby White/CHA, Zubac/IND, Kuminga/ATL, Cole Anthony/PHX, Minott/BKN). 26 stale profiles + 102 stale bene rows removed. `games_on_current_team` column + NEW_TO_TEAM 0.95 dampener (15 players). `_classify_vacuum_smart()` team filter. ✅ (Feb 18)
- [x] **8.14:** Scoring Environment Intelligence. `scripts/sync_scoring_environment.py` — nightly 14d OVER hit rate tracker → `cache/scoring_environment.json`. Dynamic env label (UNDER_FAVORED/NEUTRAL/OVER_FAVORED). Module E 3% dampener when OVER < 48%. 4 OVER filters in Module F: TWO_WAY_WING skip (35.7%), PTS 25+ dampen (30.5%), SAC/IND/CLE skip (26-34%), REB home dampen (31.1%). Fixed `opponent` NULL bug (module_f.py lines 319/364/413). Claude context: `{env_note}` + `{situational_context}` in GAME_NOTES_TEMPLATE; env note in Haiku + Sonnet curation. Both workflows wired. Current env: NEUTRAL (48.6%, n=932). commit: `33e3039`. ✅ (Feb 19)
- [ ] 8.8: Game Score Formula v2 — add line movement delta + handle% to `_score_game()`. Blocked until Mar 2026 data accumulates for backtest validation.

**Slate Date Filter (Feb 18, 2026 — commit a4ca3b3):**
- `module_a.py`: 9 PM EST cutoff — before 9 PM: today only, after 9 PM: today + tomorrow (early research)
- `main.py`: `game_date` now uses actual `start_time` instead of hardcoded `get_est_today()` — fixes data corruption in `bet_recommendations`
- `morning_brief.py` + `claude_prompts.py`: `{game_label}` in GAME_NOTES_TEMPLATE → "TONIGHT · Feb 19" / "TOMORROW · Feb 20"
- `utils/bdl_client.py`: default `date=today` guard added to `get_odds()`
- Full API audit: all other slate-fetching scripts already had correct date filters ✅

**Data Architecture Notes:**
- Injury intraday: `player_injuries` stores multiple snapshots/day — only insert when status changes. `is_game_day_report=1` for snapshots <8h before tipoff. **LIVE ✅**
- Smart vacuum: DB-driven `days_out` lookup. Scale: absorbed >14d→0.0, active ≤3d→1.0, partial 4-14d→interpolated. **LIVE ✅**
- BDL injury endpoint quirk: returns `player.team_id` (int) only — no team object. Team abbreviation resolved from `players` table by name match. **Fixed (8e53fcf) ✅**
- GENERALIST target: **Already achieved at 20.0%** ✅ (was incorrectly noted as 31.4% blocking)
- SMA audit (Feb 17): Temporal ✅ Clean | Feature Coverage ✅ Clean | Entity Resolution ✅ Clean — all 4 gaps resolved (Nic Claxton → Nicolas Claxton, EJ Harkless → Elijah Harkless, Dom Barlow → Dominick Barlow, Nikola Djurisic added to canonical)

**Competitive Research:** See `docs/FUTURE_DATA_SOURCES.md` §5 for UI/UX patterns from 6 betting analytics sites (PropsMadness, LandYourBets, BucketsToBucks, Outlier.bet, Props.cash, StraightBettin)

---

### Phase 7: All-Star Break Sprint ✅ COMPLETE (Feb 17, 2026)

**Status:** All sub-phases 7.1–7.9.5 complete. Full details: `docs/archive/phase_reports/PHASE_7_COMPLETION_SUMMARY.md`

**Remaining (unblocked Feb 19 — first game day back):**
- [x] Run full pipeline dry run with all new data sources active ✅ (Feb 19)
- [x] Validate all workflows via manual trigger on live game day ✅ (Feb 19)

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

### Phase 8.10 — League Rankings Module (Future)
**Data ready now in ludi.db**
- Weekly SQL ranking tables: top P&R ball-handlers by PPP, top FUNNEL defenses by drive FG% allowed, etc.
- Source: player_synergy_playtypes, team_scheme_cache, player_game_tracking
- Output: Telegram table Tuesdays alongside validation report
- Cost: $0 (pure SQL, no API calls)

### Phase 8.11 — Ludi Power Ratings (Future)
**Builds on team_four_factors + team_leverage_profiles**
- Blended rating: ortg + drtg + pace adjustment + 14d recent form
- Advanced: opponent quality (SOS), margin-of-victory curves
- Feeds: morning_brief._score_game() + future Ludi Lens dashboard
- Cost: $0 (deterministic math)

---

## Archive

- **docs/archive/phase_reports/** — Phase completion reports (Phases 1–7)
  - `PHASE_7_COMPLETION_SUMMARY.md` — Phase 7 full details (module overhauls, critical findings, backtest)
  - `PHASE_6_COMPLETION_SUMMARY.md` — Phase 6 full details (CLV buckets, sub-phase steps)
  - `PHASE_5_5_COMPLETION_LOG.md` — Phase 5.5 completion
- **docs/STATUS_HISTORY.md** — Phases 1–4 history
- **reports/** — Calibration analysis, performance breakdowns
- **docs/archive/** — All other completion reports, organized by sub-phase
