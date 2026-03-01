# Iris — Heartbeat Schedule

## Collection Cadence

| Time Window | Frequency | What Runs |
|-------------|-----------|-----------|
| 8 AM – 11 PM EST (Mon–Sun) | Every 30 min | Full signal collection (all 3 missions) |
| 11 PM – 8 AM EST | Paused | No collection overnight |
| Saturday 9 PM EST | Once | Weekly digest → #weekly-roundtable |

## Collection Priority by Time

### Morning (8 AM – 12 PM EST)
1. Overnight injury news (Twitter/Reddit)
2. Official injury report updates (BDL/Tank01 lag — cross-reference with ESPN)
3. Competitor product announcements or blog posts

### Pre-Lock (12 PM – 6 PM EST)
1. Lineup confirmations and scratches
2. Sharp money movements on major props
3. Action Network public % shifts
4. Reddit pre-game injury threads

### Game Time (6 PM – 11 PM EST) — MISSION 1 PRIORITY
1. In-game injury news (30-min cycle)
2. Live line movement confirmation
3. Twitter real-time player status
4. DNP/late scratch announcements

## Signal Escalation Rules

- **T1 signals during game time:** Post to #iris within 5 minutes of detection
- **T2 signals:** Post to #iris on next 30-min cycle
- **T3 signals:** Hold for Saturday digest only
- **Competitive intelligence:** Post to #iris same day, no urgency

## Saturday Digest Timing

Post at 9:00 PM EST, formatted for Solomon's Sunday 10 PM aggregation.
Digest covers: Mon 8 AM → Sat 9 PM (full week).

## launchd Plist Reference

`scripts/launchd/com.ludi.iris.plist` — runs every 30 min via `StartInterval: 1800`

```xml
<key>ProgramArguments</key>
<array>
  <string>/path/to/.venv/bin/python</string>
  <string>/path/to/employees/iris/run_collection.py</string>
</array>
<key>StartInterval</key>
<integer>1800</integer>
<key>KeepAlive</key>
<true/>
<key>RunAtLoad</key>
<false/>
```

## Rate Limiting

- Twitter search: max 10 queries per 30-min cycle (stay under free tier)
- Reddit API: 60 req/min (OAuth2 app — register at reddit.com/prefs/apps)
- Action Network: scrape only, no auth required
