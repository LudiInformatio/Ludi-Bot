---
name: daily
description: >
  Run daily pipeline health check before the 10 AM simulation.
  Verifies data integrity, API quotas, and system readiness.
  Trigger phrases: "health check", "daily check", "run /daily", "/daily".
agent: silas
user-invocable: true
context: fork
---

# Daily Pipeline Health Check

Verifies Ludi-Bot is ready for the daily simulation run.

## What This Does

Runs the system health monitor to check:
1. Data integrity — tables updated in last 24h
2. API quotas — not exhausted
3. Module outputs — pipeline ran successfully
4. Model drift — projections vs market lines

---

## Execution Steps

### Step 1 — Run Health Monitor

```bash
source .venv/bin/activate
python scripts/monitor_system_health.py
```

### Step 2 — Check GitHub Actions

```bash
gh run list --limit 5
```

### Step 3 — Check Database Freshness

```bash
sqlite3 ludi.db "SELECT COUNT(*) FROM player_game_logs"
sqlite3 ludi.db "SELECT MAX(game_date) FROM games"
```

---

## Output Format

```
## Daily Health Check — [date] [time] EST

### Data Integrity
- Player game logs: [COUNT] records
- Last game date: [DATE]
- Tables updated: ✅/⚠️/❌

### API Status
- The-Odds-API: [X]% used
- Tank01: [X]% used

### Pipeline Status
- Last run: [TIME] - [SUCCESS/FAILED]
- Module outputs: ✅/⚠️

### Alerts
- [List any warnings/critical issues]

### Status
CLEAR TO RUN | BLOCKED ([reason])
```

---

## Success Criteria

| Check | Healthy | Warning | Critical |
|-------|---------|---------|----------|
| DB records | 10,000+ | 8,000-10,000 | <8,000 |
| Tables 24h | All fresh | Some stale | Empty |
| API quota | <80% | 80-95% | >95% |
| Alerts | None | Warnings | Critical |

---

## Post-Check Actions

- **CLEAR TO RUN**: Report to Solomon "✅ /daily: All systems healthy"
- **BLOCKED**: Report "🔴 /daily: BLOCKED — [reason]" with specific issues
