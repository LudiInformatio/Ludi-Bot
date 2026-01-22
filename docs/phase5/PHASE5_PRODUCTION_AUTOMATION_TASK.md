# Phase 5: Production Deployment & Automation Task

**Date:** January 21, 2026  
**Task Owner:** [Agent to be assigned]  
**Priority:** HIGH  
**Estimated Time:** 60-90 minutes  
**Prerequisites:** Phase 4 ✅

---

## Mission

Transition the upgraded Ludi-Bot pipeline from "stable development" to **"automated production."** This involves setting up cron-based workflows, establishing an automated monitoring/alerting suite, and ensuring the weekly data-syncing infrastructure is robust.

---

## Background

We have successfully upgraded Module E (Synergy Playtypes, Team Styles, B2B Fatigue). The logic is validated (60-day results: +0.56 pts mean error). Now we need to ensure this logic runs every morning without manual intervention and alerts us if performance drifts.

---

## Technical Implementation

### 1. Automation Setup (GitHub Actions)

We need to ensure the daily synchronization and simulation pipeline is fully integrated.

**Current Workflows:**
- `data_sync.yml`: Runs 5 AM EST.
- `referee_sync.yml`: Runs 9:30 AM EST.
- `weekly_referee_sync.yml`: Runs Mondays 5 AM EST.

**Task:** Create or Update `daily_simulation_pipeline.yml` to:
1.  **Trigger:** Daily at 11 AM EST (after Ref assignments are confirmed).
2.  **Execute:** `main.py` with full Module A-X pipeline.
3.  **Output:** Send final Telegram "Diamond Cards" to the production channel.
4.  **Logging:** Archive daily logs to `logs/production/`.

### 2. Monitoring & Alerting Suite

**Create `scripts/monitor_system_health.py`** to run post-simulation:
- **Data Integrity:** Check if `ludi.db` tables (Synergy, Tracking) updated in the last 24h.
- **Model Drift:** Alert if today's mean projection variance from market lines exceeds ±3.0 pts (system-wide).
- **Failure Alerts:** Hook into `utils/pm_bot.py` to send a "🚨 SYSTEM ALERT" to Telegram if any module (A-X) returns 0 records.

### 3. Automated Weekly Backtests

**Create `.github/workflows/weekly_validation.yml`**:
- **Schedule:** **Tuesdays at 4:00 AM EST** (`0 9 * * 2` UTC).
- **Reasoning:** Captures the full previous week (including Sunday night) while avoiding the busy Monday weekly syncs and daily 3-6 AM EST processing windows.
- **Command:** Run `scripts/backtest_fatigue_21day.py` and `scripts/backtest_playtype_trends_14day.py`.
- **Action:** If B2B differential > |1.5 pts|, mark a "⚠️ MODIFIER DRIFT" alert in the weekly report.

---

## 🛠️ Mandatory Verification (DO NOT SKIP)

The next agent **must** verify all work using the following protocol:
1. **Manual Trigger:** Manually trigger the new GitHub Actions workflows and verify they complete successfully.
2. **Log Audit:** Verify all logs are correctly routed to `logs/production/` and contain expected structured data.
3. **Alert Validation:** Trigger a manual alert using `scripts/monitor_system_health.py` and confirm receipt in the Telegram production channel.
4. **Consistency Check:** Run a final 60-day backtest to ensure the "production-ready" code still matches our Phase 4 validated baseline (+0.56 pts mean error).

### 4. Code Hardening & Cleanliness

- **Production Flags:** Ensure `config.py` correctly handles `DEBUG_LOG` and `IS_PRODUCTION` flags.
- **Cleanup:** Implement a `scripts/cleanup_old_logs.py` to delete logs/artifacts older than 30 days.

---

## Testing Plan

1.  **Dry Run:** Execute the full pipeline manually via `scripts/run_production_dry_run.sh`.
2.  **Alert Test:** Intentionally break a config key and verify the Telegram alert fires.
3.  **Action Test:** Verify the GitHub Action triggers on a manual `workflow_dispatch`.

---

## Success Criteria

- [ ] `daily_simulation_pipeline.yml` operational and sending Telegram cards.
- [ ] `scripts/monitor_system_health.py` implemented and reporting status.
- [ ] Weekly validation automated with drift alerts.
- [ ] Production logging directory established and protected.
- [ ] Documentation updated in `docs/PRODUCTION_HANDBOOK.md`.

---

**Estimated Time:** 60-90 minutes
