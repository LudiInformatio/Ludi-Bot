# Deployment Best Practices

**Status:** ✅ Complete (updated 2026-02-19)

This guide covers GitHub Actions workflow patterns for the Ludi-Bot production pipeline. Every pattern below is derived from a real incident — not theory.

---

## Quick Reference

| Pattern | File(s) | One-Line Rule |
|---------|---------|---------------|
| `clean: false` on checkout | All workflows | Never let `checkout@v4` delete `ludi.db` |
| `--autostash` on rebase | `data_sync.yml` | DB files leave the working tree dirty; autostash handles it |
| `github_token` explicit param | `claude-ops-hub.yml`, `claude-qa-check.yml` | `claude-code-action@v1` ignores `issues: write` permission alone |
| Secrets `env:` block per step | `weekly_validation.yml` | GitHub Secrets don't inject automatically — add `env:` to each step that needs them |
| `continue-on-error: true` scope | Multiple | Only for TRULY non-critical steps — it hides quota exhaustion and stale data |
| Concurrency group | All sync workflows | Prevents parallel SQLite writes from two runs |
| Workflow gate (check-slate) | All game-day workflows | Cheap pre-job check prevents burning API credits on no-op runs |
| `timeout-minutes` at two levels | All workflows | Job-level (max total) + step-level (per heavy step) |
| `workflow_run` failure monitor | `claude-ops-hub.yml` | Reactive auto-diagnosis fires on workflow failure, not on schedule |
| `|| echo` on notifications | All `failure()` steps | Telegram down shouldn't cause a second workflow failure |

---

## Patterns

### 1. Database Persistence — `clean: false`

**Problem:** `actions/checkout@v4` defaults to `clean: true`, which deletes all untracked files including `ludi.db`. This wiped 5,593 bets across 15 game days before the bug was caught.

```yaml
# ❌ Default behavior — DELETES ludi.db on every run
- name: Checkout repository
  uses: actions/checkout@v4

# ✅ Preserve database between runs
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    clean: false  # Preserve ludi.db between runs
```

**Why it matters:** SQLite is not tracked in git (to prevent merge conflicts). Without `clean: false`, the database is silently wiped and all bet data is permanently lost.

**Real incident:** `clean: true` (default) in `checkout@v4` wiped the runner DB on every run from Jan 8–Feb 1, 2026. Fix deployed commit `340f131`.

---

### 2. Git Rebase with Dirty Working Tree — `--autostash`

**Problem:** Sync scripts modify `ludi.db`, `cache/` files, and logs. When `git pull --rebase` runs with these unstaged changes, git refuses to proceed:
```
error: cannot pull with rebase: You have unstaged changes.
error: Please commit or stash them.
```

```bash
# ❌ Fails when working tree is dirty (ludi.db, cache/ modified)
git pull --rebase origin main

# ✅ Stashes dirty files before rebase, restores after
git pull --rebase --autostash origin main
```

**Full working pattern from `data_sync.yml`:**
```yaml
- name: Commit and push if changes
  run: |
    git config user.name "Ludi Bot"
    git config user.email "noreply@ludibot.com"
    git add logs/
    if git diff --staged --quiet; then
      echo "No changes to commit"
    else
      git commit -m "chore: data sync $(date +'%Y-%m-%d %H:%M')"
      git pull --rebase --autostash origin main  # ← --autostash required
      git push
    fi
```

**Real incident:** `data_sync.yml` failed every run for multiple days. The exit code 128 and "unstaged changes" error was buried under `continue-on-error: true` on other steps. Fixed Feb 19 (commit `2f93242`).

---

### 3. Claude Code Action — Explicit `github_token`

**Problem:** The `anthropics/claude-code-action@v1` action does NOT inherit the job's `permissions: issues: write`. The `gh` CLI inside the action gets no auth token unless you pass it explicitly.

Log symptom: `"github_token": ""` (empty string in action config).

```yaml
# ❌ Claude correctly diagnoses failures but CANNOT create issues
- name: Claude Ops Diagnosis
  uses: anthropics/claude-code-action@v1
  with:
    claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    # github_token not passed → gh CLI unauthenticated → all issue creation fails silently

# ✅ Explicitly pass github_token
- name: Claude Ops Diagnosis
  uses: anthropics/claude-code-action@v1
  with:
    claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    github_token: ${{ secrets.GITHUB_TOKEN }}   # ← required, not optional
    additional_permissions: |
      actions: read
```

**Why it matters:** Without this, Claude Ops Hub runs successfully (exit 0) but never actually creates issues or PRs — you lose the entire value of the automated diagnosis system.

**Real incident:** Claude Ops Hub was correctly diagnosing failures in logs but all `gh issue create` calls returned exit 128 silently. Fixed Feb 19 (commit `6aa8c0f`).

---

### 4. Secrets on Self-Hosted Runners — Explicit `env:` Block

**Problem:** GitHub Secrets are NOT automatically available as environment variables in workflow steps, even on self-hosted runners. The runner's `.env` file does not contain secrets from GitHub Settings → Secrets.

Each step that needs a secret must explicitly declare it in an `env:` block.

```yaml
# ❌ Step runs but TELEGRAM_TOKEN is empty — Python notifier prints:
#    "❌ Telegram credentials not configured in .env file"
- name: Generate Weekly Validation Report
  run: |
    python -c "from utils.telegram_notifier import send_daily_briefing; send_daily_briefing('''$REPORT''')"

# ✅ Inject secrets via env: block
- name: Generate Weekly Validation Report
  env:
    TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
    TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
  run: |
    python -c "from utils.telegram_notifier import send_daily_briefing; send_daily_briefing('''$REPORT''')"
```

**Pattern:** Any step calling a Python function that reads env vars (Telegram, API keys) needs the corresponding `env:` block. Don't assume the runner has secrets available globally.

**Real incident:** `weekly_validation.yml` "Generate Weekly Validation Report" step silently skipped Telegram delivery every week. Fixed Feb 19 (commit `9f50c6a`).

---

### 5. `continue-on-error: true` — Use Sparingly and Deliberately

**Problem:** `continue-on-error: true` makes a workflow step's failure invisible. It's meant for non-critical supplementary steps, but if overused it hides quota exhaustion, stale data, and broken APIs.

```yaml
# ❌ Overuse: critical data sync step hidden under continue-on-error
- name: Sync BDL Clutch Usage  # feeds betting edge calculations
  continue-on-error: true      # failure is invisible, data goes stale for days
  run: |
    python3 scripts/sync_bdl_clutch_usage.py

# ✅ Justified use: genuinely supplementary step
- name: Analyze Star Bias
  continue-on-error: true  # Non-critical: supplementary data, not in pipeline critical path
  run: |
    python3 scripts/analyze_star_bias.py
```

**Rules for `continue-on-error: true`:**
1. Only use if the workflow is correct with or without this step's output
2. Add a comment explaining WHY it's non-critical
3. Never use on steps that write data other pipeline steps depend on
4. The presence of `continue-on-error: true` on a step is NOT a substitute for error logging inside the script

**Real incident:** `sync_wowy_hybrid.py` had a `league_id` parameter renamed in `nba_api`. The script failed on every run for weeks. Because the step had `continue-on-error: true`, the job showed green, `team_lineups` went stale, and the pipeline silently operated on outdated lineup data.

---

### 6. Concurrency Groups — Prevent Parallel SQLite Writes

**Problem:** Two workflow runs executing simultaneously can cause SQLite `database is locked` errors or corrupt write conflicts.

```yaml
# ✅ Required on any workflow that writes to ludi.db
concurrency:
  group: data-sync          # unique name per workflow
  cancel-in-progress: false  # NEVER cancel a running sync — data integrity risk
```

**Cancel-in-progress should be `false` for:**
- Any workflow that writes to `ludi.db`
- Any workflow that sends Telegram messages (don't cancel mid-send)
- Any long-running data sync (partial sync is worse than no sync)

**Cancel-in-progress can be `true` for:**
- Static site deployments (re-deploy supersedes previous)
- Preview environments

---

### 7. Workflow Gate Pattern — Pre-Job Schedule Check

**Problem:** Game-day workflows (briefing, pipeline, CLV capture) consume expensive API credits unconditionally, even on no-game days (All-Star break, off-season).

**Solution:** A cheap `check-slate` job runs first and gates the expensive job.

```yaml
jobs:
  # Cheap pre-check: queries local SQLite (nba_calendar), 0 API credits
  check-slate:
    runs-on: self-hosted
    outputs:
      has_games: ${{ steps.check.outputs.has_games }}
    steps:
      - uses: actions/checkout@v4
        with: { clean: false }
      - name: Check today's NBA slate
        id: check
        run: |
          source .venv/bin/activate 2>/dev/null || true
          export PYTHONPATH=$PWD
          set +e
          python scripts/check_slate.py
          CODE=$?
          set -e
          if [ $CODE -eq 2 ]; then
            echo "has_games=false" >> $GITHUB_OUTPUT
          else
            echo "has_games=true" >> $GITHUB_OUTPUT  # fail-open: assume games on error
          fi

  # Expensive main job: only runs when games exist
  run-production-pipeline:
    needs: [check-slate]
    if: needs.check-slate.outputs.has_games == 'true'
    # ... rest of job
```

**Exit code convention for `check_slate.py`:**
- Exit `0` = games today → proceed
- Exit `2` = no games → skip gracefully (NOT an error)
- Exception → exit `0` (fail-open: assume games, let pipeline decide)

**Applied to:** `daily_simulation_pipeline.yml`, `daily_briefing.yml`, `evening_slate_lock.yml`, `capture_closing_lines.yml`, `referee_sync.yml`

---

### 8. Timeout at Two Levels

**Problem:** A single hanging API call (NBA.com WAF timeout, rate limit) can freeze an entire workflow for hours.

```yaml
# ✅ Two-level timeout: job ceiling + per-step caps
jobs:
  sync-data:
    timeout-minutes: 60  # Job-level ceiling: workflow dies after 60 min no matter what

    steps:
      - name: Sync PBP Stats WOWY Data
        timeout-minutes: 30  # Step-level cap: this specific step gets 30 min max
        continue-on-error: true  # (only if non-critical)
        run: |
          python3 scripts/sync_pbp_wowy.py --top 10 --verbose --resume

      - name: Sync BDL Clutch Usage
        timeout-minutes: 10  # Faster step gets smaller cap
        run: |
          python3 scripts/sync_bdl_clutch_usage.py
```

**Guideline for timeout values:**
| Step Type | Timeout |
|-----------|---------|
| Database operations | 5 min |
| Single API call | 5–10 min |
| Multi-page API sync | 15 min |
| WOWY/heavy sync | 30 min |
| Job-level ceiling | 60 min |

---

### 9. Reactive Failure Monitoring — `workflow_run`

**Problem:** Scheduled health-check workflows (polling) don't know WHICH workflow failed or WHY. They're also noisy on healthy days.

**Solution:** Use `workflow_run` with `conclusion == 'failure'` to trigger diagnosis only when a workflow actually fails.

```yaml
# Claude Ops Hub pattern — fires on workflow failure
on:
  workflow_run:
    workflows:
      - "Daily Data Sync"
      - "Daily Production Pipeline"
      # ... 12 more
    types:
      - completed

jobs:
  diagnose-failure:
    if: github.event.workflow_run.conclusion == 'failure'  # ONLY on failure
    runs-on: ubuntu-latest
    # ... Claude reads failure logs, creates issue, attempts fix
```

**Why `workflow_run` > scheduled polling:**
- Fires immediately on failure, not on the next scheduled poll
- Carries the failing workflow's run ID (`github.event.workflow_run.id`) → `gh run view --log-failed`
- No false positives on healthy days
- Can read the actual failure logs programmatically

---

### 10. Telegram Failure Notification with Fallback

**Problem:** If Telegram is down when a workflow fails, a bare `send_message()` call fails too — and depending on how the step is written, this can mask the original failure.

```yaml
# ❌ If Telegram is down, this step also fails — double failure
- name: Notify on failure
  if: failure()
  run: |
    python3 -c "from utils.telegram_notifier import send_message; send_message('❌ FAILED')"

# ✅ Telegram failure is non-fatal
- name: Notify on failure
  if: failure()
  env:
    TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
    TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
  run: |
    export PYTHONPATH=$PWD
    python3 -c "from utils.telegram_notifier import send_message; send_message('❌ WORKFLOW FAILED: ${{ github.workflow }}')" || echo "Telegram notification failed"
```

**The `|| echo "..."` pattern** prevents a Telegram outage from creating a second failure in the notification step and obscuring the original failure in the logs.

---

## Anti-Patterns

| Anti-Pattern | Consequence | Fix |
|-------------|-------------|-----|
| `clean: true` (default) on checkout | Deletes `ludi.db` every run — permanent data loss | `clean: false` on ALL checkouts that run on self-hosted |
| `git pull --rebase` without `--autostash` | Fails with "unstaged changes" when any file is modified by the sync | Always use `--autostash` |
| Missing `github_token` in claude-code-action | Issue creation silently fails, Claude's diagnosis is lost | Always pass `github_token: ${{ secrets.GITHUB_TOKEN }}` |
| `continue-on-error: true` on data-critical steps | Stale data silently degrades pipeline for days/weeks | Remove it, or log the failure explicitly inside the script |
| Secrets not in `env:` block | Python notifiers see empty TELEGRAM_TOKEN and silently skip | Every step that reads secrets needs its own `env:` block |
| No job-level `timeout-minutes` | One hanging NBA.com request freezes the runner for hours | Always set `timeout-minutes` at both job and step level |

---

## Future Skill

**`/deploy-check`** — Pre-deployment validation
- Runs all pre-deployment checks automatically
- Validates: no uncommitted changes, `ludi.db` exists and is healthy, all workflow YAMLs are syntactically valid
- Checks: secrets are accessible, timeout values exist, `clean: false` is set
- Generates: deployment readiness report + go/no-go recommendation
