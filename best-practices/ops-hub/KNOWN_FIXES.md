# Ops Hub — Known Fixes Log

> Auto-maintained by `claude-ops-hub.yml`. Claude reads this before every diagnosis run.
> Known patterns here allow instant fixes without re-investigation.

---

## 2026-03-04 — claude-code-action: AJV crash = misleading error for auth/billing failures

**Symptom:** All `claude-code-action` runs fail: `is_error: true, total_cost_usd: 0, num_turns: 1, duration_ms: ~300-700ms`. Logs show AJV minified JS dump (`depsCount`, `dependencies` keyword code). No API calls made.

**Real root cause (confirmed via `show_full_output: true`):** The AJV dump is the SDK's error-wrapping code, NOT an AJV bug. The actual error was hidden behind `show_full_output: false` (default). Full output revealed: `"error": "authentication_failed", "text": "Invalid API key · Fix external API key"`. The `ANTHROPIC_API_KEY` GitHub Secret had an invalid/wrong value.

**Two separate issues that looked identical:**
1. `@v1` floating tag broke (SDK 0.2.66/0.2.68 bump, March 4 01:17 UTC) → fix: SHA pin
2. Auth token was `anthropic_api_key` pointing to invalid secret → fix: revert to `claude_code_oauth_token`

**Full fix:**
```yaml
# 1. Pin to last known good SHA (March 2, 2026 — before breaking SDK bumps)
uses: anthropics/claude-code-action@73367208d0bc0c529b8b3fb223cbd4a8f63586e4

# 2. Use OAuth token (1-year expiry, tied to Claude Pro/Max — no API credits needed)
claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```
Apply to: `claude-qa-check.yml`, `claude-ops-hub.yml`, `claude-code-review.yml`, `claude.yml`.

**OAuth token refresh:** Get from `claude auth login` or Chrome cookies at claude.ai (`sk-ant-sid01-...`). Update `CLAUDE_CODE_OAUTH_TOKEN` GitHub Secret. Token valid ~1 year. Update `CLAUDE_TOKEN_EXPIRES_AT` variable when refreshed.

**Diagnosing future crashes:** Add `show_full_output: true` to any failing `claude-code-action` step — the real error message will appear above the AJV dump. Remove after diagnosis.

**Unpin SHA when:** Anthropic releases a stable versioned tag (`v1.1` or similar). Monitor: https://github.com/anthropics/claude-code-action/releases

---

## 2026-03-03 — sync_lineup_starters: 'list' object has no attribute 'get' (Tank01 Format Change)

**Symptom:** `lineup_sync.yml` reports `continue-on-error` warning. Logs show `'list' object has no attribute 'get'` for all 20 teams. Zero starters synced.

**Root cause:** Tank01 silently changed `/getNBADepthCharts` response format (2026-03) from `{"ATL": {...}, ...}` (dict keyed by team) to `[{"teamAbv": "ATL", ...}, ...]` (list of 30 objects). `sync_lineup_starters.py` calls `depth_data.get(team_abbr)` — fails on list. Secondary: Tank01 uses BDL-style abbreviations (NY, GS, NO, PHO, SA) not standard (NYK, GSW, NOP, PHX, SAS).

**Fix:** `utils/tank01_client.py` `get_depth_charts()` — detect list, convert to dict with `normalize_bdl_abbr()` on keys. All callers receive dict transparently.

---

## 2026-03-03 — curate_plays: Active Player False-Flagged as OUT (Stale ESPN Record)

**Symptom:** Morning brief shows player as OUT in Claude analysis but still generates a bet rec. Player was active all day (e.g. Devin Booker, PHX). Race condition: ESPN sync wrote OUT at 6:58 PM March 2; `resolved_at` set at 12:27 PM March 3 (after 11 AM brief).

**Root cause 1:** `_fetch_player_injury()` in `curate_plays.py` lacked staleness guard (`snapshot_time >= datetime('now', '-14 days')`) and days_out filter (`days_out IS NULL OR days_out < 75`). `morning_brief.py` had both; `curate_plays.py` did not.

**Root cause 2:** `_haiku_sanity_check()` hard-returned FLAG on deterministic check without consulting Perplexity. Perplexity was only called when `injury is None` — so 1-day-old ESPN OUT records bypassed real-time verification entirely.

**Fix:** (1) Added both staleness filters to `_fetch_player_injury()`. (2) In `_haiku_sanity_check()`, deterministic FLAG with `days_out ≤ 3` now fetches Perplexity first — if news found, escalates to Haiku with real-time context; if no news, hard-flags. days_out > 3 still hard-flags (no regression on clear long-term cases).

---

## 2026-03-02 — Morning Briefing: start_time String AttributeError (Cache Deserialization)

**Symptom:** `daily_briefing.yml` crashes with `AttributeError: 'str' object has no attribute 'tzinfo'` at `morning_brief.py` line 512. Ops Hub issue #27.

**Root cause:** `save_games_cache()` serializes `datetime` → JSON string. `load_games_cache()` reads it back as string. Line 512 assumed `start_time` was always a `datetime` object (`_start.tzinfo`). First scheduled run to hit cache path since the odds cache feature shipped (Mar 1).

**Fix:** `morning_brief.py` L508-516 — `isinstance(str)` check + `datetime.fromisoformat()` parse before accessing `.tzinfo`. Handles both live (datetime) and cache (string) paths.

**Also fixed:** `scripts/news_agent.py` L86 — `games.game_date` → `games.date` (column doesn't exist; correct column is `date`).

---

## 2026-03-02 — Pipeline NameError: sharp_consensus Not Defined

**Symptom:** `daily_simulation_pipeline.yml` crashes with `NameError: name 'sharp_consensus' is not defined` at `module_f.py` line 762.

**Root cause:** Agent cleanup Fix C3 (Mar 1) deleted dead assignment `sharp_consensus = confirmation_score` but left 2 dict references at lines 709 and 762 that used the variable.

**Fix:** `module_f.py` — compute `sharp_consensus` in `generate_report()` using `self._sharp_consensus()` with direction-specific sharp/actual odds.

---

## 2026-03-02 — PBP Stats 3-Script Silent Failure (Fail-Loud Added)

**Symptom:** `pbp_stats_sync.yml` exits 0 (green check) but all 3 scripts write 0 rows to DB. Same zombie sqlite3 lock as WOWY sync.

**Fix:** Added `sys.exit(1)` when `total_success == 0 && total_attempted > 0` to: `sync_pbp_wowy.py`, `sync_four_factor_wowy.py`, `sync_team_leverage_profiles.py`.

---

## 2026-03-02 — WOWY Sync Silent Failure: 345 Rows Scraped, 0 Written

**Symptom:** `wowy_sync.yml` exits 0 (green check) but 0 lineup records actually persisted. Logs show 345 rows scraped by Ghost Protocol over 31 minutes, then every INSERT fails with `database is locked`.

**Root cause:** Zombie `main.py --games LAL` process (PID 29623) held 134 open file descriptors on `ludi.db`. Default SQLite timeout = 5s, insufficient when another process holds WAL lock indefinitely. Per-row errors were caught and continued, so the script finished with exit code 0 despite writing nothing.

**Fix (2 files):**
1. `scripts/sync_wowy_backfill.py` + `scripts/sync_wowy_hybrid.py`: Added `PRAGMA busy_timeout = 30000` (retry for 30s on lock). Added fail-loud pattern: track `row_errors`, log first 3, `sys.exit(1)` if 100% of rows fail.
2. Kill zombie process: `kill <PID>`, verify with `lsof ludi.db`.

**Prevention:** Always check `lsof ludi.db` before investigating silent workflow failures. If FD count > 10, a zombie process is likely.

---

## 2026-03-02 — learn_daily_trends.py NameError: ROLLING_WINDOW_DAYS

**Symptom:** Step 24 of data_sync fails with `NameError: name 'ROLLING_WINDOW_DAYS' is not defined`. Caught by try/except, reported as "non-critical" warning — rolling stats never update.

**Root cause:** Game-count refactor (Feb 28) renamed constant from `ROLLING_WINDOW_DAYS` to `ROLLING_WINDOW_GAMES` and kwarg from `rolling_days=` to `rolling_games_n=`, but missed the call site at lines 507-509.

**Fix:** `scripts/learn_daily_trends.py` L507-509: Change `ROLLING_WINDOW_DAYS` → `ROLLING_WINDOW_GAMES` and `rolling_days=` → `rolling_games_n=`.

---

## 2026-03-02 — Team Scheme Cache Calendar-Day Windows Break During Schedule Gaps

**Symptom:** Team classifications show INSUFFICIENT during All-Star break or schedule gaps because `timedelta(days=7)` window may contain 0-2 games for some teams while others have 4+.

**Root cause:** `update_team_scheme_cache.py` used `timedelta(days=59/20/6)` for 3-window voting. Calendar-day windows produce unequal sample sizes across teams.

**Fix:** Replaced with game-count windows (30g/15g/7g). Added `classify_all_teams_by_games()` to offensive classifier and `batch_classify_all_teams_by_games()` to defensive classifier. Both use `ROW_NUMBER() OVER (PARTITION BY team ORDER BY game_date DESC)` CTE for equal-sized samples.

---

## 2026-03-01 — Runner Stale Code: GH Actions Using Old module_a.py

**Symptom:** Workflow fails with 422 on `markets=h2h,spreads,totals,team_totals` bulk endpoint even though local code removed team_totals. Runner's `capture_closing_lines.yml` also shows `TANK01_KEY not set` even though the secret exists.

**Root cause:** GH Actions runner checks out `origin/main`. If local commits are never pushed (especially after a divergence), the runner runs stale code indefinitely. Overnight `chore: data sync` commits from the runner push to `origin/main` without the developer's local commits, creating a divergence that blocks `git push`.

**Fix sequence:**
```bash
git fetch origin
git diff main...origin/main --stat     # Confirm only log files differ
git merge origin/main --no-edit        # Safe — logs only, no conflicts
git push origin main                   # Runner now gets correct code
```

**Prevention:** Always run `git push origin main` at end of every session, immediately after the debrief commit. This is now required in Step 8 of the `session-debrief` skill.

**Secondary fix (CLV workflow):** `capture_closing_lines.yml` was missing `TANK01_KEY` + `TANK01_TIER` in the `Capture closing lines` step env block. Tank01 Tier 3 fallback silently failed auth on every CLV run. Fixed 2026-03-01 in commit `96fc556`.

---

## 2026-02-28 — Module G Zebras Audit: Referee Profile Data Quality Fixes

- **H1 (avg_pace_impact stale)**: `referee_profiles.avg_pace_impact` was seeded with `/~42` divisor; correct formula is `/12.5` (fouls per game / league avg). Tony Brothers: DB=0.413, correct=1.387. `get_game_impact()` safety cap `[0.90, 1.10]` was hiding the error silently. Fix: `scripts/fix_referee_profiles_pace.py` — one-time repair SQL. Defensive fallback added to `_get_referee_profile()`: recomputes from fouls if `pace_impact < 0.5`.
- **H2 (style thresholds wrong)**: STRICT threshold was `>= 16.0` (matches only 1 ref: Sean Wright 17.88). Corrected to `>= 14.0 STRICT / <= 12.0 LENIENT`. Tony Brothers (17.34), Scott Twardoski (17.07), Dedric Taylor (17.04) all now STRICT.
- **M1 (dead code)**: `DailyRefereeSync._populate_todays_games()` existed (lines 80-148) but was never called from `run()`. Removed. `module_g._populate_todays_games()` handles game insertion correctly (with `sync_canonical_games`).
- **M3 (learn_daily_trends failure kills data_sync)**: `learn_daily_trends.py` step in `data_sync.yml` was missing `continue-on-error: true` — failure killed all 50+ downstream steps. Fixed. `analyze_star_bias.py` step also added with `continue-on-error: true`.
- **Rolling window undersampling**: Calendar-day 21-day cutoff returned 1-2 games per ref during All-Star break. Fix: changed to last-N-games (ROLLING_WINDOW_GAMES=10) — game-count is scheduling-agnostic. See data-modeling Pattern 10.
- **New OddsShark signals wired**: `ou_percentage`, `avg_total`, `home_ats_bias`, `ou_record`, `home_ats_record` fields now returned from `_get_referee_profile()` with COALESCE defaults (0.5 for pcts, 0 for totals). `get_game_impact()` returns `ref_ou_avg` + `ref_home_ats_avg` across crew.
- **Team trends**: `team_betting_trends` table (30 rows) + `get_team_trends(team_abbr)` in `module_g.py`. `sync_team_betting_trends.py` derives H/A W-L, scoring averages, ATS splits from `canonical_games` + `player_game_logs`. Score derivation: SUM(pts) per game_date+team WITHOUT `home_or_away` filter (BDL rows have NULL). See data-modeling Pattern 11.

---

## 2026-02-28 — canonical_games Table: Pattern-B JOIN Triple-Row Inflation

- **Symptom**: `sync_matchup_intelligence.py` DVP calculations produced inflated sample sizes (3× actual); `team_defensive_classifier.py` scheme classification was silently counting each game 3 times. `module_b.py vs_scheme_cache` also required an ugly DISTINCT workaround.
- **Root Cause**: The `games` table stores each game in **3 different `game_id` formats** from three different ingestion sources:
  1. `002XXXXXXXX` — NBA official format (Module H, Tank01)
  2. `22500XXX` — Shortened format (BDL backfill)
  3. `20251021_HOU@OKC` — Date-team format (populate_todays_games.py, Module G)
  Pattern-B JOINs (`JOIN games g ON g.date = x AND (g.home_team = y OR g.away_team = y)`) matched all 3 rows per game → 3× row multiplication.
- **Fix Applied**: Added `canonical_games` table (Feb 28, 2026):
  - `PRIMARY KEY canonical_game_id = '{date}_{home}_{away}'` — one row per game, always.
  - `sync_canonical_games(conn)` importable from `database.py` — call after any `INSERT INTO games`.
  - 1,926 raw rows → 902 canonical rows. Called automatically in `_initialize_db()`.
  - Wired into: `module_b.py` (vs_scheme_cache), `populate_todays_games.py`, `module_g.py`, `scripts/sync_matchup_intelligence.py` (4 JOINs), `utils/team_defensive_classifier.py` (1 JOIN).
- **Pattern**: `JOIN canonical_games g ON g.date = x AND (g.home_team = y OR g.away_team = y)` — safe, one row per game by design. COALESCE upsert preserves non-null data across all 3 source formats.
- **Commit**: chore(session) end-of-session doc sync 2026-02-28

---

## 2026-02-28 — Module F Audit: 7 Bugs Fixed (LudiReporter)

- **A1 (avg_ev)**: `bet_daily_summaries.avg_ev` stored `p['edge']` not `p['ev']` — mislabeled data since V5.0. Fix: `sum(p['ev'] for p in all_props)`.
- **B1 (emoji map)**: `_classify_edge_type()` returns `'Injury-Return'` but emoji map had no entry → fell through to 📊 default. Fix: Added `'Injury-Return': '🩹'`.
- **B2 (defensive archetypes)**: `positive_archetypes` contained `RIM_GUARDIAN`, `PERIMETER_HAWK`, `SWITCHABLE_ANCHOR`, `HUSTLE_DISRUPTOR` (all defensive tags). Caused tier bonus to fire for defensive roles. Fix: Removed all 4 defensive tags from set.
- **C1 (old SGP block)**: 3-line SGP correlation block fired when single player had PTS OVER + AST OVER, mislabeling as `[🔥 CORRELATED SGP]`. Superseded by Phase 8.26 `curate_plays.py`. Fix: Removed entirely.
- **C2 (_STAT_COL_MAP aliases)**: Map had `'points' → 'pts'` but NOT `'pts' → 'pts'`. Module A sends short-form keys — DB hit-rate fallback returned 0.5/0.5 neutral for every bet. Fix: Added 8 short-form aliases.
- **C3 (_bdl_fallback_active)**: Read via `getattr` at line 1171 but never initialized in `__init__`. Fix: `self._bdl_fallback_active = False`.
- **CR1 (multi-window hit rates)**: Bet card showed single hit rate. Fix: L5/L10/L15 windows now surface in note field when available from Module B.

---

## 2026-02-28 — Module B Enhancement: vs_scheme_cache + L20 Windows + time_context

- **vs_scheme_cache**: Pre-loads last-5 game values per player/stat vs each defense scheme (live `team_scheme_cache.active_style`). L5/L10/L15/L20 windows + L5-vs-scheme all surfaced in CR1 note block.
- **time_context**: `EARLY_LOOK/AFTERNOON/PRE_GAME/LOCK_TIME` column added to `bet_recommendations`.
- **Note**: Both features added in same session as Module F audit. Verified against HOU/MIA test with JSJ OUT scenario.

---

## 2026-02-27 — Module D Audit Sprint (LudiYak)

### D1/G2: Haiku Empty-Response Guard (Correctness)

- **Symptom**: `json.loads("")` ValueError — James Harden "Expecting value: line 1 column 1" errors in logs.
- **Root Cause**: Haiku returns empty string when `description` field is empty or <10 chars. `json.loads("")` raises JSONDecodeError. Also `json.loads(None)` raises TypeError.
- **Fix Applied**: `module_d.py _ai_parse_blurb()` (lines ~907-950):
  - Added pre-call guard: `if not description or len(description.strip()) < 10: return {}`
  - Added None/empty guard after API call: `if not result_text or not result_text.strip(): return {}`
  - Added markdown code-fence strip: `if text.startswith('...'): text = '\n'.join(lines_list[1:-1])`
- **Prevention**: Always guard before `json.loads()` with `if not result_text or not result_text.strip()`.

---

### B1: RSS DB Connection Batching (Performance)

- **Symptom**: Up to 150 DB connections per RSS refresh cycle (per-item open/close).
- **Root Cause**: `_upsert_news_staging()` opens sqlite3.connect() per RSS item inside loops.
- **Fix Applied**: `module_d.py _upsert_news_staging()` — added optional `conn` parameter. Callers can pass pre-opened connection. Backward compatible: if conn=None, opens/closes internally.
- **Prevention**: When function is called in loop, pass shared connection.

---

### G1: Ghost Injury Auto-Resolve (Data Quality)

- **Symptom**: Players shown as OUT/DOUBTFUL who have active game logs (Naji Marshall, Tyler Herro with 130+ duplicate rows).
- **Root Cause**: Tank01 keeps returning stale injured players. Resolve step only fires when player disappears from API list. Also dedup used 3-column key `(player_name, status, DATE)` allowing duplicates when injury_type changes.
- **Fix Applied**: `scripts/sync_injuries.py`:
  - Added `_auto_resolve_active_players()` function — UPDATE player_injuries SET resolved_at=now() WHERE player logged 10+ min in last 3 game_days
  - Changed dedup from `(player_name, status, DATE)` to `(player_name, DATE)` only
  - Added call to `_auto_resolve_active_players()` at end of main()
- **Note**: Fix runs when sync_injuries.py executes (next scheduled run). Existing ghost rows will be cleaned up.

---

### G3: INJURY_RETURN Edge Type (Bet Analytics)

- **Symptom**: Ramp-up players (returning from 7+ day absence) generate UNDER edges labeled "EDGE: Projection" — identical to normal projection bets, hiding ramp-up signal from post-hoc analysis.
- **Root Cause**: Module C G3 ramp-up dampening existed but no edge type classification for it.
- **Fix Applied**:
  - `module_c.py run_simulation_batch()` — added `player['_games_since_return'] = games_back` when ramp-up fires (line ~427), added `GAMES_SINCE_RETURN` to sim_profile
  - `main.py build_reporter_input()` — added pass-through: `'games_since_return': sim.get('GAMES_SINCE_RETURN')` (line ~467)
  - `module_f.py _classify_edge_type()` — added new branch after Injury-Vacuum: `if games_since_return and int(games_since_return) <= 4: return 'Injury-Return'`
- **Prevention**: When adding stat dampeners, always propagate signal metadata to edge classification.

---

### G4: Injury Timestamp Surfacing (Competitive Parity)

- **Symptom**: Telegram cards show bare "OUT" with no freshness context. Competitors (Outlier, StraightBettin) surface timestamps.
- **Root Cause**: `player_injuries.snapshot_time` exists in DB but not surfaced in output.
- **Fix Applied**: `morning_brief.py`:
  - Added `snapshot_time` to SELECT queries (lines ~689, ~697)
  - Added `_format_injury_stamp()` helper function — formats as "OUT (updated 5:18 PM)" if <6h, "OUT (reported 5:18 PM)" if <36h, "OUT (as of Feb 25)" otherwise
  - Updated injury line formatting to use helper (line ~725)

---

## 2026-02-27 — Silent No-Op in module_a.py `fetch_team_archetypes()` (Agent Dict Key Bug)

- **Symptom**: `archetypes['home_pace']`, `archetypes['home_def_rtg']`, `archetypes['home_ortg']` always 0 — team pace/DRtg data never populated despite successful DB queries.
- **Root Cause**: Agent used wrong dict key names when accessing the `games[game_id]` dict. Wrote `game.get('home_team', '')` but the key is `'home'`. Wrote `game.get('team_info', {})` but the key is `'archetypes'`. The whole method ran without error but populated nothing.
- **Fix Applied**: `module_a.py fetch_team_archetypes()` — `'home_team'`→`'home'`, `'away_team'`→`'away'`, `'team_info'`→`'archetypes'`. All downstream references updated (`team_info['home_pace']`→`archetypes['home_pace']` etc).
- **Prevention**: Before writing any method that reads from `self.games[game_id]`, check the game dict contract at `module_a.py` init sections (lines ~176, ~388, ~486) to confirm key names. The data contract docstring in the `Gatekeeper` class also documents the exact keys.
- **Commit**: 771439e — fix(audit): Module A Tier F

---

## 2026-02-26 — Ghost Injuries (Players Shown as OUT Who Are Playing)

- **Symptom**: Ask Ludi bot shows players as OUT/DOUBTFUL who have active game logs (e.g., Naji Marshall 131+ duplicate rows, Tyler Herro 45 rows — both playing full minutes).
- **Root Cause**: Tank01 keeps returning stale injured players in every API response. The resolve step in `sync_injuries.py` (lines 660-694) only resolves players NOT present in `active_player_names` from current API response — so if Tank01 keeps sending them, they're never resolved. The dedup guard checks `(player_name, status, DATE(snapshot_time))` but misses same-player entries with different `injury_type` strings.
- **Bot-Level Fix (applied Feb 26)**: Added `_GHOST_INJURY_GUARD` SQL fragment to all injury queries in `bots/ask_ludi_db.py`:
  ```sql
  AND NOT EXISTS (
      SELECT 1 FROM player_game_logs pgl
      WHERE LOWER(pgl.player_name) = LOWER(pi.player_name)
        AND pgl.game_date >= date('now', '-3 days')
        AND pgl.minutes > 10
  )
  ```
  Also added `GROUP BY player_name, team_abbreviation` dedup guard.
- **Root Fix (deferred to module audit)**: Fix `sync_injuries.py` resolve logic to cross-reference `player_game_logs` — if a player logged 10+ min last 3 days → auto-resolve regardless of API response. Change dedup to `(player_name, DATE(snapshot_time))` only.

---

## 2026-02-26 — AI Training Data in Prompt Examples

- **Symptom**: `ASK_LUDI_NARRATIVE_SYSTEM` example used Trae Young, Anthony Davis, D'Angelo Russell as WAS players (OUT). Those players were traded to WAS but had not yet played a game — "OUT" meant nothing since they had no usage baseline.
- **Root Cause**: Using AI training data to recall current roster assignments in hardcoded prompt examples. AI knowledge cutoff predates current season trades.
- **Fix**: Query `ludi.db` directly before writing any prompt example. Use `SELECT name, team FROM players WHERE team = 'WAS'` to find real current roster + game logs to verify they've actually played.
- **Rule**: Every hardcoded player example in `utils/claude_prompts.py` must be verified against `ludi.db` OR use clearly generic placeholders like `[PLAYER_A]`, `[TEAM]`. Never use AI training memory for current-season roster facts.


---

## 2026-02-26 — Ask Ludi Bot: Python 3.14 asyncio.get_event_loop() RuntimeError

- **Script**: `bots/ask_ludi.py`
- **Symptom**: `RuntimeError: There is no current event loop in thread 'MainThread'` on startup. Bot crashes immediately.
- **Root Cause**: Python 3.14 removed implicit event loop creation in `asyncio.get_event_loop()` (deprecated since 3.10, warning since 3.12, error since 3.14). `python-telegram-bot` v21.x calls `get_event_loop()` internally in `run_polling()`.
- **Fix Applied**: Create event loop explicitly before `run_polling()`:
  ```python
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  app.run_polling()
  ```
- **Pattern**: Any library using `asyncio.get_event_loop()` will break on Python 3.14. Fix: create loop explicitly before calling the library. Or upgrade to library version that uses `asyncio.run()` pattern.
- **Commit**: Phase 8.13 session (Feb 26, 2026)

---

## 2026-02-24 — Settlement All-Void: Game Logs Not Ingested Before Settlement Ran

- **Symptom**: Settlement Telegram showed "no bets" / 0-0 record. DB showed 348 bets settled as PUSH with `actual_result = -998.0` (VOID-DNP code).
- **Root Cause**: `player_game_logs` for Feb 22 were not inserted until Feb 24 08:29 AM (due to Module H `c35fed5` bug). Settlement ran Feb 23 10:49 AM — found no game logs — voided all 348 bets as DNP. Same pattern hit Feb 23 bets (445 bets, same day).
- **Diagnosis Signal**: `actual_result = -998` for ALL bets on a given date + `player_game_logs` `created_at` timestamp AFTER `settled_at` timestamp = game logs arrived after settlement ran.
- **Recovery**: `python settle_bets.py --date YYYY-MM-DD` re-settles all bets for that `game_date` regardless of current outcome. Verify game log coverage first: `SELECT team_abbreviation, COUNT(*) FROM player_game_logs WHERE game_date = 'YYYY-MM-DD' GROUP BY team_abbreviation`.
- **Fix Applied**: `settle_bets.py` — date ceiling guard: normal runs now filter `game_date <= get_est_yesterday()`, preventing settlement of today's future slate. Also added Strategy 3 canonical name fallback (`resolve_canonical_name`) for accent mismatches.
- **Pattern**: When all bets on a date are `-998`, check game log `created_at` vs `settled_at`. If logs arrived after settlement → re-settle with `--date`. Not a model failure, a data timing failure.

---

---

## 2026-02-24 — Capture Closing Lines: Graceful Quota Exit + Live Game Filter

- **Workflow**: `capture_closing_lines.yml`
- **Symptom**: `exit code 1` at 10:32 PM EST. Logs: "Found 322 uncaptured bets → Odds API: quota exhausted (cached) → BDL: 3 scheduled games → Matched 1 game(s) → 0 updated, 96 skipped → WARNING: Had pending bets but captured 0 closing lines".
- **Root Cause**: Odds API monthly quota was exhausted (known Feb event, documented in ROADMAP.md). BDL fallback correctly filtered out `status=2/3` (in-progress/final) games — all earlier games had finished. Only 3 late upcoming games remained; only Utah@Houston matched; BDL had only 4 player props for that game, none matching our 96 bets (which were for earlier, now-completed games). Three `exit(1)` paths in `capture_closing_lines.py` did NOT check `odds_api_quota.json` before exiting — unlike `morning_brief.py` which already had this pattern. Also: Odds API event matching had no `commence_time` filter — could have served in-game live odds if quota was available.
- **Fix Applied**: Tier 2 —
  1. Three exit points (normalized_games empty, game_bet_map empty, 0 captures) now check `_read_cached_quota() == "0"` first → `sys.exit(0)` with informative message (matches `morning_brief.py` pattern)
  2. Added `_game_is_on_slate(ev, game_date)` helper: filters Odds API events by `commence_time` date == today EST AND game has not started >15 min ago (rejects live games and future-date games)
  3. BDL `fetch_bdl_games_today()` now logs how many in-progress/final games were filtered out (`"X in-progress/final game(s) skipped (status 2/3)"`)
- **Pattern**: "Distinguish expected noise from real failures at the exit point." Quota=0 → monthly known event → `exit(0)`. Genuine data failure → `exit(1)` → Ops Hub fires. Same pattern applies to any API with monthly quota exhaustion.
- **Commit**: 44c4297

---

## 2026-02-23 — Injury Pipeline: ESPN/BDL Source Conflict + Name Normalization

- **Symptom**: Players (Nurkić/Nurkic, Porziņģis/Porzingis) had injury records with `team_abbreviation = ''` — invisible to morning brief query `WHERE team_abbreviation IN (...)`. JJJ appeared healthy despite being injured (no record in DB).
- **Root Cause**: `sync_injuries.py` used `.lower()` only for team resolution → accented names never matched `players.name` → blank team. JJJ: BDL/Tank01 hadn't reported his injury; only ESPN had it.
- **Fix Applied**: Tier 2 —
  1. `_normalize_for_canonical()` in `sync_injuries.py` — NFD accent strip + suffix removal (Jr./Sr./III) matching `player_canonical_ids.normalized_name`
  2. `_get_canonical_lookup_from_db()` — preload canonical lookup once per sync run
  3. Stores canonical `full_name` (e.g. `Jusuf Nurkić`) in `player_injuries` for consistent downstream joins
  4. `morning_brief.py` UNION query catches blank `team_abbreviation` via canonical_ids join
  5. `scripts/sync_injuries_espn.py` (new) — ESPN 30-team scan, 15-30 min lag, source-scoped resolve
  6. ESPN protection in `sync_injuries.py` — BDL/Tank01 cannot downgrade an ESPN OUT to GTD/PROBABLE
  7. BDL resolve step scoped: `AND source NOT IN ('ESPN', 'espn_suspension')` — prevents BDL wiping ESPN entries
- **Commit**: 5e8f6ac

---

## 2026-02-23 — Module D: yak_cache Never Written + Perplexity Not Cached

- **Symptom**: `yak_cache.json` never existed. Perplexity was called on every `search_news()` invocation even for repeat queries in the same pipeline run.
- **Root Cause**: `_save_cache()` was called in `search_news()` but never defined — `AttributeError` silently caught by `except Exception`. Perplexity path returned without writing to `self.cache` at all.
- **Fix Applied**: Tier 1 — Added `_save_cache()` definition. Both Perplexity and DuckDuckGo results now written to `self.cache` + flushed to disk. 20-min TTL prevents repeat API calls within same pipeline run.
- **Commit**: 8b1366b

---

## 2026-02-23 — Evening Slate Lock: Graceful Quota Exit Check Failed

- **Workflow**: `evening_slate_lock.yml`
- **Symptom**: Pipeline failed with `exit code 1` and triggered Ops Hub alert. Logs showed `⚠️ The-Odds-API Failed: 422 Client Error...` followed by `⚠️ No data processed. Aborting.`.
- **Root Cause**: The Odds API quota exhaustion is a known monthly event. `morning_brief.py` is supposed to detect this in `cache/odds_api_quota.json` and exit gracefully (exit code 0). However, the cache read was failing (either due to relative path resolution or an integer vs. string type mismatch in the JSON `remaining` field). Because it was wrapped in a bare `except Exception: pass`, the error was silently swallowed, and the script fell through to the hard `sys.exit(1)`.
- **Fix Applied**: Tier 1 —
  1. Updated the cache file lookup to use an absolute path resolved from `__file__`.
  2. Checked for both integer `0` and string `"0"` in the JSON payload.
  3. Changed `except Exception:` to `except Exception as e: print(e)` so future cache-read failures are visible.
- **Commit**: 2d50f36

---

## 2026-02-23 — Daily Morning Briefing: Telegram 400 Bad Request (Silent Failure)

- **Workflow**: `daily_briefing.yml`
- **Symptom**: Pipeline finished with a green checkmark (exit code 0), but no Telegram notifications were received. Logs showed multiple `❌ HTTP error: 400 Client Error: Bad Request for url: .../sendMessage`.
- **Root Cause**: The 4000-character chunking logic in `morning_brief.py` blindly split Claude's output. If the split happened in the middle of a Markdown formatting tag (like `*bold*`), Telegram's MarkdownV2 parser rejected the entire chunk with a 400 error. The script caught the exception, printed a warning, and moved on without exiting, causing GitHub Actions to mark the step as successful and blinding Claude Ops Hub to the failure. AI outputs were also too long and frequently triggered chunking.
- **Fix Applied**: Tier 2 (multi-file) —
  1. Added a plain text fallback (`parse_mode=None`) if the Markdown send fails in `morning_brief.py` and `scripts/curate_plays.py`.
  2. Forced a hard failure (`sys.exit(1)`) if both sending attempts fail, ensuring Ops Hub detects future outages.
  3. Added a strict `CONCISE` rule to `ANALYSIS_PROTOCOL` in `utils/claude_prompts.py` to force Claude to keep responses under 1500 characters, heavily reducing the need for chunking.
- **Commit**: 6f71f4c

---

## 2026-02-23 — Daily Data Sync: PBP Stats Timeout Cascade (Job Cancelled)

- **Workflow**: `data_sync.yml`
- **Symptom**: Job cancelled after 60 minutes. 22 downstream steps (injuries, rotations, trends, scheme cache, commit) skipped entirely. Ops Hub did NOT fire (only triggered on `failure`, not `cancelled`).
- **Root Cause**: 3 PBP Stats scripts had step timeouts summing to 75 min (30+25+20) inside a 60-min job timeout budget. `sync_pbp_wowy.py` and `sync_four_factor_wowy.py` each hung until their individual timeouts, consuming 55 min. Job-level timeout killed everything before remaining steps could run.
- **Fix Applied**: Tier 2 (multi-file) —
  1. Split 3 PBP Stats scripts to own workflow `pbp_stats_sync.yml` (Mon/Wed/Fri 5 AM EST, 90-min budget)
  2. Removed those steps from `data_sync.yml` (remaining steps ~25 min, well within 60-min budget)
  3. Added `cancelled` trigger to `claude-ops-hub.yml` condition
  4. Added wall-clock guards (`MAX_RUNTIME_SECONDS`) in all 3 scripts
  5. Lowered HTTP timeouts in `pbp_stats_client.py` (120→60s, 180→90s)
  6. Added BDL fallback to Module H (related: Tank01 returned 0 games for Feb 22 despite 11 games)
- **Commit**: (this session)

---

## 2026-02-22 — Capture Closing Lines: BDL V2 Status Filter + Quota Pre-flight

- **Workflow**: `capture_closing_lines.yml`
- **Symptom**: "BDL: 0 scheduled games for YYYY-MM-DD" (logs show 0 games despite active slate)
- **Root Cause**: `fetch_bdl_games_today()` in `scripts/capture_closing_lines.py` filtered on
  string status names ("Scheduled", "Pre-Game") but BDL V2 API returns numeric codes:
  "1" = upcoming, "2" = in-progress, "3" = final. String filter always returned 0 matches.
- **Fix Applied**: Tier 1 — changed filter to `str(g.get('status', '1')) in ('2', '3')` to
  skip only in-progress/final games (keep "1" = upcoming). Also added `cache/odds_api_quota.json`
  pre-flight: checks cached quota before calling Odds API; skips entirely if `remaining == "0"`.
- **Commit**: e95c6a0

---

## 2026-02-22 — Slack Notifier: Python Callers Silent in CI

- **Workflow**: All Python-based Slack notification calls across all workflows
- **Symptom**: No Slack messages from Python scripts in CI; curl-based Slack calls work fine.
  `utils/slack_notifier.py` prints "SLACK_WEBHOOK_URL not configured" warning and returns False.
- **Root Cause**: `config.py` skips `load_dotenv()` when `IS_SELF_HOSTED=true`, relying on
  injected env vars. Workflow steps that don't have `env: SLACK_WEBHOOK_URL:` in their step
  definition get an empty string from the imported constant. `_get_webhook()` only checked the
  imported constant, not `os.getenv()` directly.
- **Fix Applied**: Tier 1 — added top-level `import os`; changed `_get_webhook()` to
  `return SLACK_WEBHOOK_URL or os.getenv('SLACK_WEBHOOK_URL', '')` in `utils/slack_notifier.py`
- **Commit**: (this session)

---

## 2026-02-22 — Claude Ops Hub: No Issues Created, No Auto-Fixes Committed

- **Workflow**: `claude-ops-hub.yml` (meta: ops-hub diagnosing its own prior failure)
- **Symptom**: Claude Ops Hub ran for 6m55s, correctly analyzed CLV failure, identified root
  cause, but created no issues and committed no fixes. No error logged.
- **Root Cause**: `claude-code-action@v1` disables Bash tools by default for security. Claude
  could read files and analyze logs but had no tool to execute `gh issue create` or `git commit`.
  Additionally, verification step used `--createdAfter "-10m"` which is not a valid `gh issue list`
  flag — caused verification to always return empty, triggering spurious fallback attempts.
- **Fix Applied**: Tier 1 — added `claude_args: '--allowedTools "Bash(gh:*),Bash(git:*)"'` to
  the `Claude Ops Diagnosis` step `with:` block. Removed invalid `--createdAfter` flag from the
  verification step.
- **Commit**: (this session)

---

## 2026-02-24 -- Capture Closing Lines: Odds API Quota Exhausted + BDL Post-Game Props Unavailable

- **Workflow**: `capture_closing_lines.yml`
- **Symptom**: 322 uncaptured bets, 0 CLV captures. All bets SKIPd with no match [bdl]. Script exits non-zero.
- **Root Cause**: Two compounding TRANSIENT factors -- (1) Odds API monthly quota exhausted (cache pre-flight working correctly, skipped to BDL). (2) Run at 10:32 PM EST after games concluded; BDL does not serve historical closing line data for completed games, only returned 4 players with props for UTA@HOU (none matching bet records for Sengun, A. Thompson, etc.).
- **Fix Applied**: No code change -- TRANSIENT. If this pattern repeats 3+ nights consecutively, escalate to TIER_3 to evaluate earlier CLV window or graceful exit on quota exhaustion.
- **Commit/PR/Issue**: Issue created (severity:transient)

---

## 2026-02-25 — ESPN Crosswalk 404: Season-Aware URL Required

- **Script**: `scripts/build_espn_crosswalk.py`
- **Symptom**: All 30 teams return 404. `espn_id` and position writes fail entirely.
- **Root Cause**: ESPN changed their API. The season-less path `/teams/{id}/athletes` no longer works.
  Correct URL: `/seasons/2026/teams/{id}/athletes?limit=100`
- **Fix Applied**: Updated `fetch_team_athletes()` to include `/seasons/2026/` in path.
- **Additional Finding**: ESPN athlete endpoint returns `position.leaf=false` (G/F/C parent nodes only).
  Fine-grained PG/SG/SF/PF unavailable from ESPN, BDL, or Tank01 — only from SportsDataIO `/Players`.

---

## 2026-02-26 — Module G: LEAGUE_AVG_FOULS Calibration Error (21.5 → 12.5)

- **Script**: `module_g.py`, `scripts/learn_daily_trends.py`, `scripts/sync_daily_referees.py`
- **Symptom**: `referee_profiles.whistle_impact` scores ~1.7x for most refs instead of ~1.1x (near-neutral). Almost no refs classified LENIENT. `player_foul_splits.pf_vs_strict`/`pf_vs_lenient` columns always NULL.
- **Root Cause**: `LEAGUE_AVG_FOULS = 21.5` (per-game total, both teams) used as per-ref baseline. Correct value is 12.5 per ref per game (18.74 team fouls × 2 teams ÷ 3 crew = 12.49). `whistle_impact = ref_avg / LEAGUE_AVG_FOULS` → 14.0 / 21.5 = 0.65 (looked lenient) vs 14.0 / 12.5 = 1.12 (correctly strict). Same error in `learn_daily_trends.py`: used 42.0 (full game total instead of 37.5), and 21.5 per-ref avg instead of 12.5.
- **Fix Applied**: `module_g.py` LEAGUE_AVG_FOULS 21.5 → 12.5. `learn_daily_trends.py` LEAGUE_AVG_FOULS 42.0 → 37.5, PER_REF_AVG_FOULS 21.5 → 12.5. Seed default in `sync_daily_referees.py` 21.5 → 12.5. DB migration WHERE avg_fouls_per_game > 18.0 → 0 rows needed reset (EMA had already converged to realistic values).
- **STRICT/LENIENT thresholds**: ≥14.0 / ≤11.0 fouls per ref per game. With 21.5 as the divisor, nearly every ref appeared LENIENT — inverted signal.
- **Commit**: Phase 8.17 session (Feb 26, 2026)

---

## 2026-02-27 — Module C Audit: Projection Upgrades (G1-G3)

- **Context**: Module C (`LudiOracle`) audit sprint. Calendar-day windows, thin-sample players, and returning injury players all produced undersampled projections.
- **G1 — Calendar-day → game-count window** (`main.py:get_active_roster()`):
  - **Problem**: `WHERE game_date >= date('now', '-30 days')` returns 1-4 games during All-Star breaks or injuries (77 players had ≤4 games in the 30d window pre-fix). Player averages become statistically noisy.
  - **Fix**: Replaced with game-count subquery — last 25 played games per player. `WHERE game_date IN (SELECT game_date FROM player_game_logs sub WHERE sub.player_id = pgl.player_id AND sub.minutes > 0 ORDER BY game_date DESC LIMIT 25)`. Also added `GAMES_PLAYED` column (COUNT of rows) to the SELECT and player dict output for G2 confidence weighting.
  - **Performance note**: Correlated subquery pattern with `player_game_logs` (10K+ rows) → acceptable at this scale. If table grows >100K rows, convert to CTE with `ROW_NUMBER()` (same pattern as module_c.py pre-load methods).
- **G2 — Season baseline blend for thin-sample players** (`module_c.py:run_simulation_batch()`):
  - **Problem**: Players with <15 recent games use a statistically unreliable average. SGA with 3 games showed PTS=28.0 vs true season avg 31.8 (3.8 delta).
  - **Fix**: Added `_load_season_baselines()` pre-load from `player_season_averages_bdl`. In `run_simulation_batch()`, if `GAMES_PLAYED < 15`: blend recent avg with season baseline using `w = min(games_recent / 15.0, 1.0)`. At 3 games → SGA PTS becomes 31.0 (w=0.20). At 15+ games → w=1.0, pure recent data.
  - **Data source**: `player_season_averages_bdl` table (`category='general'`, `stat_type='base'`, `season=2025`). Falls back gracefully if table empty.
- **G3 — Injury return ramp-up detection** (`module_c.py`):
  - **Problem**: Game 1 back from a 2-week absence treated identically to Game 50. Return-from-injury players show reduced volume for 2-4 games post-return.
  - **Fix**: Added `_load_return_status()` pre-load — detects 7+ day gaps in `player_game_logs` via `LAG() OVER (PARTITION BY player_id ORDER BY game_date ASC)`. Stores `games_since_return` per player. In `run_simulation_batch()`, applies ramp factors to ALL stats: `{1: 0.70, 2: 0.80, 3: 0.90, 4: 0.95}`. 416 players detected as recently returned on audit date.
- **Commits**: Module C audit sprint (Feb 27, 2026)

---

## 2026-02-27 — Module C Audit: Pre-load, Mutation, and Normalization Fixes (C1/C3/C4)

- **C1 — `rotation_profiles` per-player DB query** (`module_c.py:_get_projected_minutes()`):
  - **Symptom**: `_get_projected_minutes()` opened `sqlite3.connect()` for every player. 16 players × 5+ games = 80+ DB connections per pipeline run. Every other data source was pre-loaded at init; this one was missed.
  - **Fix**: Added `_load_rotation_data()` pre-load at init — loads all `rotation_profiles WHERE window_days = 21` keyed by `str(player_id)`. `_get_projected_minutes()` now does `row = self.rotation_data.get(player_id)` dict lookup. Zero DB connections during simulation.
  - **Rule**: Any data used inside `run_simulation_batch()` (which calls `_simulate_player()` 10K times) MUST be pre-loaded at init. Never open a DB connection inside a simulation loop.
- **C3 — Player dict mutation after simulation** (`module_c.py:run_simulation_batch()`):
  - **Symptom**: Lines mutated `player['FGA']`, `player['FG3A']`, `player['FTA']` with `min_scale` AFTER the simulation already completed. Distributions were already computed — mutation had zero effect but corrupted the caller's player dict silently.
  - **Fix**: Removed the 3 mutation lines. Added `sim_profile['MIN_SCALE'] = round(min_scale, 3)` to store it as simulation metadata instead.
  - **Verification**: `build_reporter_input()` in `main.py` reads from the `sim` dict only (`sim.get('PTS', 0)` etc). Confirmed at `main.py:447-454`. No downstream code reads `player['FGA']` after Module C returns.
- **C4 — Accent normalization for name-keyed lookups** (`module_c.py`):
  - **Symptom**: `rolling_ts_data` and `drives_data` dicts keyed by raw `player_name`. BDL-sourced rows store "Nikola Jokic" (no accent); canonical names use "Nikola Jokić". Lookups silently returned `None` → default 1.0 modifier for all accented-name players. Always use NFKD, never `str.replace()` chains — those miss ć/č/š/ž.
  - **Fix**: Added `_normalize_name()` static method (NFKD decompose + strip Mn categories). Dicts now keyed by normalized name at load time. Lookups normalize the input name before `.get()`. Follows the same pattern as `module_b.py:155-164`.
- **Commits**: Module C audit sprint (Feb 27, 2026)

---

## 2026-02-27 — BDL Team Abbreviation Contamination Cleaned (C16)

- **Symptom**: `get_active_roster('GSW', 8)` returned fewer players than expected. ~33-40% of game logs for GS/NO/NY/PHO/SA teams were stored under BDL abbreviations, invisible to standard queries.
- **Root Cause**: Module H BDL fallback (added Feb 23) wrote `team_abbr` directly from BDL API response without normalizing. The `normalize_bdl_abbr()` centralization in `utils/mappings.py` (Feb 24) was only applied to sync scripts written after that date — not to the BDL fallback path in `module_h_historian.py`.
- **Contamination scope**: 1,857 `player_game_logs` rows (GS:113, NO:109, NY:145, PHO:149, SA:153 pre-2025-26 + current season mix) + 253 `games` rows (home_team + away_team). Full SQL cleanup applied.
- **Fix Applied**:
  1. SQL: `UPDATE player_game_logs SET team_abbreviation = 'GSW' WHERE team_abbreviation = 'GS'` (+ NO→NOP, NY→NYK, PHO→PHX, SA→SAS). Same for `games.home_team` and `games.away_team`. All 10 updates executed, 0 rows remaining.
  2. `module_h_historian.py` BDL fallback: added `from utils.mappings import normalize_bdl_abbr` and `team_abbr = normalize_bdl_abbr(side.get('team', {}).get('abbreviation', 'UNK'))` at write time — prevents re-contamination on future BDL fallback runs.
- **Prevention**: All BDL API consumers MUST call `normalize_bdl_abbr()` before any write to `player_game_logs.team_abbreviation` or `games.home_team/away_team`. The function is idempotent: `normalize_bdl_abbr('GSW') = 'GSW'`. Check new BDL sync scripts against `utils/mappings.py` pattern.
- **Module C defense confirmed safe**: Module C's `_load_team_defense_data()` reads from `player_game_opponent.team_abbrev` — all standard abbreviations, no BDL contamination. Defense lookup keyed by scenario's `home_team` (Odds-API standard). No fix needed in Module C itself.
- **Commits**: Module C audit sprint (Feb 27, 2026)

---

## 2026-02-25 — UNK Position Coverage (155 players bypassing Gate 2)

- **Context**: `players.position='UNK'` for 155 active players — bypasses all Gate 2 position gates.
- **Root Cause**: Tank01 only returns G/F/C. `player_canonical_ids.position` existed but was 96% UNK.
  14 additional rows had team abbrevs (IND/LAC) as position — data corruption from missing `pos` field.
- **Fix Applied**:
  1. `sync_sportsdata_enrichment.py --sync-positions` — SportsDataIO `/Players` has PG/SG/SF/PF/C.
     Upgrade-only rank system (UNK=0 < G/F/C=1-2 < PG/SG/SF/PF=3). 391 upgraded in first run.
  2. `classify_archetypes.py` — COALESCE query: prefers `player_canonical_ids.position` → `players.position` → UNK.
  3. `build_espn_crosswalk.py` — corrupt team-abbrev cleanup runs on every execution.
  4. Wired `--sync-positions` into `data_sync.yml` (1 cached API call/day, no extra quota cost).
 - **Result**: Active 21d window: 155 UNK → 4 (97% reduction). Gate 2 coverage: 17% → 88%.

---

## 2026-02-27 — Module E Audit Sprint (DVP, Bulk Pre-loads, Backup Intelligence)

- **Context**: Module E (`module_e.py`) audit — performance optimization, data accuracy, backup intelligence
- **Root Cause**: Per-player DB queries, hardcoded matchup boosts, missing data sources
- **Fixes Applied**:
  1. **A1**: Synergy + tracking bulk pre-load at init — eliminates ~160 DB connections per slate
     - `_load_synergy_playtypes_bulk()`: pre-loads player_synergy_playtypes with canonical name resolution
     - `_load_tracking_stats_bulk()`: CTE-based last-15-games window (not days)
     - `_get_synergy_playtypes()` + `_get_tracking_stats()`: cache-first with DB fallback
  2. **B1**: DVP data-driven matchup modulation
     - `_load_dvp_by_archetype()`: pre-loads team_dvp_by_archetype (HIGH/MEDIUM only)
     - `_get_dvp_modulator()`: applies ±8% modulation based on real per-100-possession data
     - Blends hardcoded boosts with DVP data for improved accuracy
  3. **G1**: player_archetype_vs_defense matrix integration
     - `_load_archetype_vs_defense_matrix()`: pre-loads system bet performance by archetype×defense
     - DVP modulation dampened by 50% when system confidence is LOW (<30 bets)
  4. **G2**: player_type_profiles confidence flag
     - `_load_player_type_profiles()`: pre-loads archetype_in_top3 validation
     - `archetype_confidence` flag added to calibrated dict (HIGH/LOW)
     - Matchup boosts reduced 30% when archetype not validated by synergy data
  5. **I1**: Player-specific B2B splits
     - `_load_b2b_splits()`: CTE-based actual B2B vs rested delta from player_game_logs
     - Replaces blanket -4.8%/-1.5% modifiers with player's actual performance delta
     - Requires ≥3 B2B games, caps at ±15% to prevent outlier distortion
  6. **I2**: MINUTES_LIMIT scaling uses actual player dict value
     - Now reads `player_packet.get('minutes_limit')` instead of hardcoded 0.75
  7. **H1**: main.py get_active_roster limit 8→12 (catches rank 9-12 backups)
  8. **H2**: USG% key fix — `sim.get('USG_PCT', 0) / 100.0` (was reading wrong key)
  9. **H3**: WOWY-based backup projections in module_x_scenario.py
     - `_get_wowy_projections()`: uses actual per-36 stats from team_lineups
  10. **H4**: effective_starter flag cross-module flow
     - Added to module_x_scenario.py when elevated minutes ≥25
     - Passed through main.py build_reporter_input()
     - Module E calibrates as starter when flag is True
  11. **H5**: depth_charts tier-0 backup lookup in module_x_scenario.py
     - Position-specific backup lookup before beneficiary_minutes
  12. **C1**: Removed dead `import pandas as pd` (line 1)
  13. **C2**: Added named constants for magic numbers (GAME_TOTAL_HIGH/LOW_THRESHOLD, etc.)
  14. **D1**: Added debug logging to 3 silent exception handlers
- **Module Changes**: module_e.py (~320 lines), main.py (3 changes), module_x_scenario.py (3 additions)
- **Verification**: Integration test `.venv/bin/python main.py --games CLE`


---

## 2026-02-28 — Odds-API: `team_totals` Silently Killing Entire Game Slate (422)

- **Affected file**: `module_a.py` — `fetch_live_slate()`
- **Symptom**: `⚠️ The-Odds-API Failed: 422 Unprocessable Entity` — entire Gatekeeper falls back to BDL, which only had 3/5 games with lines. Two upcoming games invisible to pipeline every day.
- **Root Cause**: `team_totals` was in the bulk `/v4/sports/basketball_nba/odds` markets string (`h2h,spreads,totals,team_totals`). The bulk endpoint does NOT support `team_totals` — it returns 422 and drops ALL markets/games.
- **Fix**: Remove `team_totals` from bulk call. Add Phase 1.5 per-event enrichment loop: after game slate built, call `/v4/sports/{sport}/events/{event_id}/odds?markets=team_totals` per game (1 credit/game). Parse using `outcome['description']` (team name) + `outcome['name']` (Over/Under) — different from old bulk format that used `outcome['name']` for team.
- **Field mapping (per-event format)**:
  ```python
  # outcome['description'] = team name (e.g. "Toronto Raptors")
  # outcome['name'] = "Over" or "Under"
  # outcome['point'] = the line value
  # (old bulk parser was wrong — used outcome['name'] == home_team, never fired)
  ```
- **Credit cost**: 1 credit per game per day (~5 games = 5 credits). Previously 0 credits but 0 data.
- **Verification**: `TeamTotal:114.5` appears in Module E bet card notes confirming data flows correctly.

---

## 2026-02-28 — Python 3.11: Backslash Escapes in f-string Expressions

- **Affected file**: `module_a.py` — Tank01 3rd fallback logging line
- **Symptom**: `SyntaxError: unexpected character after line continuation character` at module import. `from module_a import Gatekeeper` fails immediately.
- **Root Cause**: Python 3.11 does not allow backslash escape sequences (`\"`) inside f-string `{}` expression braces. This was fixed in Python 3.12 but breaks on the project's current 3.11 runtime.
- **Fix**: Extract the string literal to a variable before the f-string, or lift complex expressions out entirely.
  ```python
  # BROKEN (Python 3.11):
  f'{len([p for p in d if all(v.get(\"key\") == \"val\" for v in d[p].values())])}'
  # FIXED:
  target_val = 'val'
  count = len([p for p in d if all(v.get('key') == target_val for v in d[p].values())])
  f'{count} items found'
  ```
- **Rule**: Never use `\"` inside f-string `{}` blocks in this codebase (Python 3.11).

---

## 2026-03-02 — Referee External Intelligence: Stale Seeded Data + 42 Duplicates

- **Affected file**: `scripts/sync_external_intelligence.py` (full rewrite v2)
- **Symptom**: `referee_profiles.avg_fouls_per_game` contained BBR-seeded values (e.g., Tony Brothers=17.34) on a different scale than internal rolling L10 data (~11.80). Result: ~66 refs incorrectly labeled STRICT. Also 42 duplicate rows with `(#N)` badge suffix alongside bare-name rows.
- **Root Cause**: Original scraper used hardcoded column indices (broke on site layout changes), no name normalization, no duplicate detection. OddsShark Home/Away Fouls were never scraped — only ATS data was captured.
- **Fix**: Full rewrite with 5 improvements:
  1. **Header-based column matching**: JavaScript `evaluate()` builds header index map from `<th>` — resilient to column reorder
  2. **Name normalization**: `_normalize_ref_name()` strips `(#N)` badge suffix, removes periods in initials ("J.B." → "JB"), lowercases
  3. **OddsShark Home/Away Fouls**: `(home_fouls + away_fouls) / 3` = per-ref scale matching internal rolling_21d_fouls
  4. **Style recalculation**: STRICT ≥13.5, LENIENT ≤11.0, NEUTRAL otherwise (per-ref scale, not BBR team-total scale)
  5. **Duplicate cleanup**: `_cleanup_duplicate_rows()` deletes `(#N)` suffixed rows where bare-name exists
- **Result**: 42 duplicates cleaned, NULL ou_percentage 48%→12%, NULL home_ats_bias 50%→8%, style distribution corrected (59 NEUTRAL + 26 STRICT vs mostly-STRICT before)
- **Pattern 11 compliance**: `setup_page()` after `context.new_page()`, `close_popups()` after `page.goto()`, `wait_until='domcontentloaded'`

---

## 2026-03-03 — utils/claude_logger.py: Missing busy_timeout on Phase 8.23 log writes

**Symptom:** Intermittent `database is locked` errors during concurrent pipeline runs. Claude analysis log entries silently dropped.

**Root cause:** `sqlite3.connect(_DB_PATH)` at L64 has no `PRAGMA busy_timeout=30000`. Phase 8.23 fires on every Claude call — multiple concurrent writers guaranteed.

**Fix:** Add `conn.execute("PRAGMA busy_timeout=30000")` after connect. Keep the `except Exception: pass` — intentional design to never let logging crash the pipeline.

---

## 2026-03-03 — utils/game_notes_cache.py: player_injuries query accent-unsafe

**Symptom:** Game notes cache validation returns wrong result for accented players (Jokić, Nurkić). Cache records exist but query finds 0 rows.

**Root cause:** L150 `WHERE LOWER(player_name) = LOWER(?)` — LOWER() doesn't strip Unicode diacritics. `player_injuries.player_name` stores canonical accented names after Feb 24 fix. Non-accented lookup misses.

**Fix:** NFD-normalize input before query: `unicodedata.normalize('NFKD', name)` + strip combining chars.

---

## 2026-03-03 — utils/telegram_notifier.py: No startup warning for missing Solomon credentials

**Symptom:** `daily_reports.yml` bet-summary shows green but zero Telegram ops alerts delivered. No error in logs.

**Root cause:** `TELEGRAM_TOKEN_SOLOMON` / `TELEGRAM_CHAT_ID_SOLOMON` absent from workflow env block. `send_solomon_message()` returns False silently — no module-level check at import time.

**Fix:** Add startup guard at module level: print warning if Solomon credentials are absent. Also verify workflow env block includes both secrets.
