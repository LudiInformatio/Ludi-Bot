# Silas — Heartbeat Schedule

## Monitoring Cadence

| Time Window | Frequency | What Runs |
|-------------|-----------|-----------|
| 6 AM – 6 PM EST (Mon–Sun) | Every 60 min | Full health check + hourly summary to #silas |
| 6 PM – 11 PM EST (Mon–Sat) | Every 15 min | Game-time check — injuries freshness + pipeline status |
| 11 PM – 6 AM EST | Every 90 min | Light check — only critical alerts posted |
| Saturday 9 PM EST | Once | Weekly digest → #weekly-roundtable |

## Check Priority by Time

### Morning (5 AM – 9 AM EST)
1. Did overnight data sync run? (`data_sync.yml` at 3 AM)
2. Did DB backup run? (`db_backup.yml` at 1 AM)
3. API quota carry-over from yesterday

### Pre-Pipeline (9 AM – 10 AM EST)
1. Referee sync completed? (`referee_sync.yml` at 9:30 AM)
2. Lineup sync completed? (`lineup_sync.yml` at 9:45 AM)
3. Injury data fresh? (`player_injuries` last update < 4 hours)

### Pipeline Window (10 AM – 12 PM EST)
1. `daily_simulation_pipeline.yml` — started, running, completed?
2. Bet count generated (alert if 0 bets)
3. Morning brief sent? (`daily_briefing.yml` at 11 AM)

### Game Time (6 PM – 11 PM EST) — HIGH FREQUENCY
1. Injury refresh running every 20 min? (`injury_refresh.yml`)
2. Evening slate lock sent? (6:35 PM + 8:25 PM)
3. Any workflow failures in last 30 min?

### Overnight (11 PM – 5 AM EST)
1. Nightly debrief completed? (`nightly_debrief.yml` at 8:30 PM)
2. CLV capture ran? (overnight via `db_backup.yml`)

## Alert Routing

- **🔴 Critical**: Post to #silas immediately + send Telegram to `TELEGRAM_CHAT_ID`
- **🟡 Warning**: Post to #silas on next scheduled check
- **🟢 Healthy**: Include in next hourly summary only

## launchd Plist Reference

`scripts/launchd/com.ludi.silas.plist` — runs every 15 min via `StartInterval: 900`

```xml
<key>ProgramArguments</key>
<array>
  <string>/path/to/.venv/bin/python</string>
  <string>/path/to/employees/silas/run_check.py</string>
</array>
<key>StartInterval</key>
<integer>900</integer>
<key>KeepAlive</key>
<true/>
```
