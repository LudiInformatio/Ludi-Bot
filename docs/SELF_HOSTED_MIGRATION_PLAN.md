# Self-Hosted Migration Plan

## 🎯 Objective
Migrate critical data ingestion workflows to a **Self-Hosted Runner (macOS/Local)** to bypass Cloud IP blocking (WAF) and enable full browser automation.

## 🔍 Audit & Impact Analysis

### 1. Affected Scripts (Requires Migration)
These scripts currently fail or are restricted in GitHub Cloud runners:
- **`scripts/sync_wowy_hybrid.py`**: NBA.com `LeagueDashLineups` endpoint is blocked.
- **`scripts/sync_tracking_parallel.py`**: Uses NBA.com API; risks WAF blocks.
- **`scripts/sync_browser_backfill.py`**: Requires Playwright (Headful preferred for stealth).
- **`scripts/sync_daily_referees.py`**: NBA.com referee stats.
- **`scripts/sync_external_intelligence.py`**: Scrapes OddsShark/Covers (Headful preferred).

### 2. Affected Workflows (To Update)
We will modify the following workflows to use `runs-on: self-hosted`:
- [ ] `.github/workflows/data_sync.yml` (Backbone sync)
- [ ] `.github/workflows/weekly_referee_sync.yml` (WOWY + Referees)
- [ ] `.github/workflows/tracking_sync.yml` (Daily Tracking)
- [ ] `.github/workflows/ghost_protocol_sync.yml` (Browser Backfills)

## 🛠️ Implementation Guide

### Phase 1: Local Runner Setup (User Action)
1. **Download & Configure:** Follow GitHub instructions to set up the runner on your Mac (M-series preferred).
2. **Environment Prep:** Run the helper script `scripts/setup_runner.sh` to install Python, Playwright, and dependencies.
3. **Run Service:** Execute `./run.sh` (or install as service).

### Phase 2: Workflow Migration (Bot Action)
Once the runner is online, I will update the workflows:
```yaml
# OLD
runs-on: ubuntu-latest

# NEW
runs-on: self-hosted
env:
  # Ensure we use the local python environment
  PYTHONPATH: ${{ github.workspace }}
```

### Phase 3: Verification
1. **Trigger Manual Run:** Run `weekly_referee_sync` manually.
2. **Observe:** Watch the local terminal for execution logs.
3. **Verify Data:** Check `ludi.db` for new records.

## 📋 Pre-Flight Checklist
- [ ] Local Repo is clean & synced [✅ Done]
- [ ] `setup_runner.sh` created [Pending]
- [ ] Secrets (API Keys) are available to self-hosted runner (GitHub handles this automatically)

## 🔄 Reverting (Fallback)
If the local machine goes offline, we can revert workflows to `ubuntu-latest` and accept that WOWY/NBA data will skip/fail, but the build will pass (thanks to Graceful Skip).
