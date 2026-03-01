# Daily Pipeline Check

Run this workflow to verify Ludi-Bot's daily operations are healthy.

## Why Daily Checks Matter
The betting pipeline runs automatically via GitHub Actions. This check ensures:
- Workflows completed successfully
- Database has fresh data
- API quotas aren't exhausted
- No silent failures occurred

## Check Steps

### 1. GitHub Actions Status
```bash
gh run list --limit 5
```
**What to look for**:
- All recent runs show ✓ (success)
- No ✗ (failures) in last 24 hours
- Daily pipeline ran at expected time (11 AM EST)

### 2. Database Integrity
```bash
sqlite3 ludi.db "SELECT COUNT(*) FROM player_game_logs"
```
**What to expect**:
- Count should be 10,000+ (you currently have ~10,840)
- Number should grow by ~100-300 after each game day

### 3. API Quota Check
Review `api_usage_log.json` for:
- The-Odds-API: Should be <80% of 20K monthly quota
- Tank01: Should be <80% of 1K daily quota

**Warning threshold**: 80% usage
**Critical threshold**: 95% usage

## Report Format

```
Daily Health Check [DATE]

GitHub Actions:
- Last run: [TIME] - [SUCCESS/FAILED]
- Failures in 24h: [COUNT]

Database:
- Player game logs: [COUNT] records
- Last update: [DATE]

API Quotas:
- Odds API: [X]% of monthly quota
- Tank01: [X]% of daily quota

Status: [HEALTHY/WARNING/CRITICAL]
```

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| Workflow failed | API timeout | Re-run manually |
| DB count unchanged | No games yesterday | Check NBA schedule |
| API quota high | Unusual activity | Review recent runs |
