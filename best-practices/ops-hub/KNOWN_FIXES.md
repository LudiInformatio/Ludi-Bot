# Ops Hub — Known Fixes Log

> Auto-maintained by `claude-ops-hub.yml`. Claude reads this before every diagnosis run.
> Known patterns here allow instant fixes without re-investigation.

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
