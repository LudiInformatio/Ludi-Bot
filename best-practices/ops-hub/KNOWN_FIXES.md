# Ops Hub — Known Fixes Log

> Auto-maintained by `claude-ops-hub.yml`. Claude reads this before every diagnosis run.
> Known patterns here allow instant fixes without re-investigation.

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
