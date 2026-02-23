# Ops Hub — Known Fixes Log

> Auto-maintained by `claude-ops-hub.yml`. Claude reads this before every diagnosis run.
> Known patterns here allow instant fixes without re-investigation.

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
