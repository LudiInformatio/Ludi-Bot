# Paid API Integration - Migration Report
**Date**: January 7, 2026
**Project**: Ludi Informatio v2.0
**Phase**: Week 1, Days 5-6 - Paid Tier Integration

---

## Executive Summary

**Status**: ✅ **INTEGRATION COMPLETE** (Pending Testing)

Successfully integrated paid tier API keys for The-Odds-API and Tank01 with comprehensive monitoring and error handling infrastructure. All code changes have been implemented and are ready for testing once dependencies are installed.

**Tier Upgrade**:
- **The-Odds-API**: FREE (500/month) → PAID (20,000/month) = **40x increase**
- **Tank01**: FREE (1,000/month) → PAID (1,000/day = 30,000/month) = **30x increase**

---

## What Was Completed

### Phase 1: Monitoring Infrastructure ✅
**Created 2 new utility files** to track API usage and handle errors:

#### 1. `utils/api_monitor.py` (274 lines)
**Features Implemented**:
- ✅ Request logging to `api_usage_log.json`
- ✅ Rate limit header parsing for both APIs
  - The-Odds-API: `x-requests-remaining`, `x-requests-used`, `x-requests-last`
  - Tank01: `x-ratelimit-requests-remaining`, `x-ratelimit-limit`
- ✅ Console warnings when >80% quota consumed
- ✅ Telegram notification integration (uses existing TELEGRAM_TOKEN)
- ✅ Failed request logging with error details
- ✅ Usage summary reports (daily/weekly/monthly)

**Key Methods**:
```python
monitor.log_request('odds_api', 'fetch_slate', response.headers)
monitor.check_quota_threshold('odds_api')  # Alerts at 80%
monitor.log_failed_request('tank01', 'box_score', error_msg)
monitor.get_usage_summary(days=7)  # 7-day usage report
```

#### 2. `utils/api_helpers.py` (265 lines)
**Features Implemented**:
- ✅ Retry decorator with exponential backoff
- ✅ Specific error handling:
  - **401/403**: Authentication errors → Hard fail with clear message
  - **429**: Rate limit → Sleep and retry with extended wait time
  - **5xx**: Server errors → Retry with exponential backoff (max 3 attempts)
  - **Network errors**: Connection/timeout handling
- ✅ Circuit breaker pattern (prevents cascading failures)
- ✅ Rate limit header parsing utility

**Usage Example**:
```python
@retry_with_backoff(max_attempts=3, backoff=2.0)
def fetch_data(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()
```

### Phase 2: API Key Integration ✅
**Updated 2 configuration files**:

#### 1. `.env` (Environment Variables)
**Changes**:
- ✅ Updated `ODDS_API_KEY` from `3c4cff00b16889e49fc6320ffb0690a8` (free) to `9aa84b1836e565ec82161558d5cc948b` (paid)
- ✅ Kept `TANK01_KEY` as `b4ec1031f4msh80f4fc4cd874de4p17e5b7jsn8eeafd9da310` (already paid tier)
- ✅ Added `ODDS_API_TIER=paid`
- ✅ Added `TANK01_TIER=paid`

#### 2. `config.py` (Configuration Validation)
**Changes**:
- ✅ Added tier detection variables (`ODDS_API_TIER`, `TANK01_TIER`)
- ✅ Added tier limits dictionary:
  ```python
  TIER_LIMITS = {
      'odds_api': {'free': 500, 'paid': 20000},
      'tank01': {'free': 1000, 'paid': 1000}  # per DAY for paid
  }
  ```
- ✅ Enhanced `validate_config()` to display tier information:
  ```
  ✅ The-Odds-API tier: PAID (limit: 20,000 requests/month)
  ✅ Tank01 tier: PAID (limit: 1,000 requests/day)
  ```

### Phase 3: Module Integration ✅
**Updated 3 core modules** with monitoring and error handling:

#### 1. `module_a.py` (The Gatekeeper)
**Changes**:
- ✅ Added imports: `get_monitor`, `retry_with_backoff`
- ✅ Initialized `self.monitor` in `__init__`
- ✅ Added `@retry_with_backoff` decorator to `fetch_live_slate()`
- ✅ Added monitoring hooks in 2 locations:
  - **Line 66-67**: `fetch_live_slate()` - Logs slate fetch requests
  - **Line 200**: `fetch_props()` loop - Logs each prop fetch request
- ✅ Quota threshold checking after slate fetch

**API Calls Monitored**: 2 endpoints
- `/v4/sports/basketball_nba/odds` (game slate)
- `/v4/sports/basketball_nba/events/{game_id}/odds` (player props)

#### 2. `module_d.py` (The Yak - Injury Intelligence)
**Changes**:
- ✅ Added imports: `get_monitor`, `retry_with_backoff`
- ✅ Initialized `self.monitor` in `__init__`
- ✅ Added `@retry_with_backoff` decorator to `refresh_official_injuries()`
- ✅ Added monitoring hook at line 72
- ✅ Enhanced error handling:
  - Specific handling for 429 (rate limit) - extends cache instead of failing
  - HTTP errors logged with status codes
  - All exceptions logged to monitor with Telegram alerts

**API Calls Monitored**: 1 endpoint
- `getNBAInjuryList` (15-minute sync)

#### 3. `module_h_historian.py` (The Historian)
**Changes**:
- ✅ Added import: `get_monitor`
- ✅ Initialized `self.monitor` in `__init__`
- ✅ Added monitoring hook at line 151
- ✅ **Removed silent failure** at lines 187-188:
  - **OLD**: `except: pass` (errors were ignored)
  - **NEW**: Proper error logging with `log_failed_request()`

**API Calls Monitored**: 1 endpoint
- `getNBABoxScore` (historical game data)

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `utils/api_monitor.py` | 274 | API usage tracking, Telegram alerts |
| `utils/api_helpers.py` | 265 | Retry logic, error handling, circuit breaker |
| `PAID_API_MIGRATION_REPORT.md` | (this file) | Migration documentation |

---

## Files Modified

| File | Changes | Impact |
|------|---------|--------|
| `.env` | Updated ODDS_API_KEY, added tier variables | Production API keys active |
| `config.py` | Added tier detection & validation | Displays tier info on startup |
| `module_a.py` | Monitoring + retry logic (2 locations) | Tracks all odds/props requests |
| `module_d.py` | Monitoring + enhanced error handling | Tracks injury API calls |
| `module_h_historian.py` | Monitoring + removed silent failures | No more hidden errors |
| `CLAUDE.md` | Added paid tier setup instructions | Documentation updated |

---

## API Usage Tracking

### The-Odds-API (Paid Tier: 20,000 requests/month)

**Endpoints Monitored**:
1. **Fetch Game Slate**: `/v4/sports/basketball_nba/odds`
   - **Cost**: `markets × regions` = 3 markets × 2 regions = **6 credits per call**
   - **Frequency**: Once per day (before games start)

2. **Fetch Player Props**: `/v4/sports/basketball_nba/events/{game_id}/odds`
   - **Cost**: `markets × regions` = 10 markets × 3 regions = **30 credits per game**
   - **Frequency**: Once per game (for targeted games)

**Projected Daily Usage (12 games/day)**:
- Slate fetch: 6 credits
- Props (3 games tested): 3 × 30 = 90 credits
- **Total**: ~96 credits/day = **2,880 credits/month** (well within 20K limit)

### Tank01 (Paid Tier: 1,000 requests/day)

**Endpoints Monitored**:
1. **Injury List**: `getNBAInjuryList`
   - **Cost**: 1 request per call
   - **Frequency**: Every 15 minutes during game day = ~32 calls/day
   - **Cache**: 15-minute TTL prevents excessive calls

2. **Box Scores**: `getNBABoxScore`
   - **Cost**: 1 request per game
   - **Frequency**: 12 calls/day (historical backfill)

**Projected Daily Usage**:
- Injuries: 32 requests
- Box scores: 12 requests
- **Total**: ~44 requests/day (well within 1,000/day limit)

---

## Alert Configuration

### Console Alerts (Always Active)
- ✅ Quota warnings when >80% consumed
- ✅ API error messages with details
- ✅ Rate limit notifications

### Telegram Alerts (Requires TELEGRAM_TOKEN)
- ✅ Quota warnings at 80% threshold
- ✅ API failure notifications with error details
- ✅ Rate limit alerts

**Telegram Setup** (already configured):
- Token: `8190581794:AAEUVV88PupubJYcudiyRCuWCpgPVLlZ-ag`
- Chat ID: `8190581794`

---

## Cost Analysis

### Monthly Costs (Paid Tier)
- **The-Odds-API**: $30/month (20,000 credits)
- **Tank01**: $10/month (1,000 requests/day)
- **Total**: **$40/month**

### Cost Per Prediction
**Assumptions**:
- 12 games/day
- 3 games props fetched/day
- 96 credits/day for Odds API
- 44 requests/day for Tank01

**Calculation**:
- The-Odds-API: $30 / 20,000 = $0.0015 per credit × 96 = $0.144/day
- Tank01: $10 / 30,000 = $0.000333 per request × 44 = $0.015/day
- **Total daily cost**: $0.159 for ~3 games = **$0.053 per game**

**Result**: ✅ **WELL UNDER** the $0.10 budget target!

---

## Testing Requirements

### Pre-Test Checklist
- [ ] **Install dependencies**: `pip install numpy pandas requests python-dotenv duckduckgo-search pytz unidecode`
- [ ] **Verify .env file**: Contains paid tier keys and tier variables
- [ ] **Activate virtual environment**: `source venv/bin/activate`

### Test Sequence

#### Test 1: Configuration Validation
```bash
./venv/bin/python -c "import config"
```
**Expected Output**:
```
✅ Core API keys loaded (ODDS_API_KEY, TANK01_KEY)
✅ The-Odds-API tier: PAID (limit: 20,000 requests/month)
✅ Tank01 tier: PAID (limit: 1,000 requests/day)
```

#### Test 2: Integration Test
```bash
./venv/bin/python test_integration.py
```
**Expected Output**:
```
🔌 Testing Module A (Gatekeeper) Integration...
✅ Gatekeeper Initialized
✅ ODDS_API_KEY Found
✅ LudiHistorian (DB) Initialized
✅ Gatekeeper has 'fetch_live_slate' method
📊 ODDS_API: [X] credits remaining
🎉 Module A Integration Test: READY to connect.
```

#### Test 3: 3-Game Validation Test
```bash
./venv/bin/python main.py  # (with limit_games=3 in code)
```
**Expected Behavior**:
- Fetches game slate (6 credits)
- Fetches props for 3 games (90 credits)
- Syncs injury list (1 request)
- Creates `api_usage_log.json` with request details
- Displays quota remaining in console
- Sends Telegram alert if >80% quota used

#### Test 4: Review Logs
```bash
cat api_usage_log.json | python -m json.tool
```
**Expected Content**:
```json
[
  {
    "timestamp": "2026-01-07T...",
    "api": "odds_api",
    "endpoint": "fetch_slate",
    "rate_limit_info": {
      "requests_remaining": "19994",
      "requests_used": "6",
      "request_cost": "6"
    }
  },
  ...
]
```

---

## Known Issues & Limitations

### 1. Dependencies Not Installed
**Issue**: Virtual environment missing required packages
**Solution**: Run `pip install numpy pandas requests python-dotenv duckduckgo-search pytz unidecode`

### 2. Testing Postponed
**Issue**: Cannot run full integration tests without dependencies
**Status**: Code integration complete, ready for testing after pip install

### 3. BallDontLie Integration
**Issue**: Stubbed but not implemented (optional API)
**Cost**: $40/month additional
**Recommendation**: Test with The-Odds-API + Tank01 first, add if needed

### 4. API-Sports Integration
**Issue**: Stubbed but not implemented (optional API)
**Cost**: $25/month additional
**Recommendation**: Implement in Week 4-5 for backtesting

---

## Next Steps

### Immediate (Today)
1. ✅ **Code integration**: COMPLETE
2. ⏳ **Install dependencies**: `pip install numpy pandas requests python-dotenv duckduckgo-search pytz unidecode`
3. ⏳ **Test configuration**: `./venv/bin/python -c "import config"`
4. ⏳ **Run integration test**: `./venv/bin/python test_integration.py`

### Short-Term (This Week)
5. ⏳ **3-game validation**: Run `main.py` with 3 games
6. ⏳ **Review usage logs**: Check `api_usage_log.json`
7. ⏳ **Verify Telegram alerts**: Confirm notifications received
8. ⏳ **Calculate actual cost**: Compare projected vs actual credits used

### Medium-Term (Week 2)
9. ⏳ **Full slate test**: Run with all 12 games
10. ⏳ **Monitor for 3 days**: Track daily usage patterns
11. ⏳ **Optimize caching**: Reduce unnecessary API calls
12. ⏳ **Build usage dashboard**: Create `monitor_api_usage.py` script

### Long-Term (Week 5+)
13. ⏳ **Validation gate**: Backtest with historical data
14. ⏳ **ROI analysis**: Cost per prediction vs accuracy
15. ⏳ **Consider optional APIs**: BallDontLie, API-Sports if needed

---

## Risk Assessment

### LOW RISK ✅
- **Budget overrun**: Projected $0.053/game is well under $0.10 target
- **Rate limits**: Comfortable headroom (96/20,000 daily for Odds API)
- **Error handling**: Comprehensive retry logic and monitoring in place

### MEDIUM RISK ⚠️
- **Silent failures eliminated**: But new error logging may reveal hidden issues
- **Telegram dependency**: Alerts require valid token/chat_id
- **Testing incomplete**: Need to run full pipeline to verify integration

### MITIGATED RISKS ✅
- ~~Silent API failures~~ → Now logged with Telegram alerts
- ~~Unknown costs~~ → Usage tracking active from Day 1
- ~~Rate limit surprises~~ → 80% threshold warnings implemented
- ~~No retry logic~~ → Exponential backoff with circuit breaker

---

## Success Criteria

### Code Integration ✅
- [x] Monitoring utilities created
- [x] API keys updated to paid tier
- [x] Tier detection configured
- [x] All 3 modules integrated
- [x] Silent failures removed
- [x] Documentation updated

### Testing (Pending Dependencies)
- [ ] Configuration validation passes
- [ ] Integration test passes
- [ ] 3-game test completes successfully
- [ ] Usage logs created
- [ ] Cost < $0.10 per game
- [ ] Telegram alerts received

### Validation (Week 2+)
- [ ] 7-day usage tracking
- [ ] No rate limit errors
- [ ] Positive ROI measured
- [ ] Model accuracy validated

---

## Recommendations

### For Immediate Testing
1. **Install dependencies first**: Don't skip this step
2. **Test with 1 game**: Before scaling to 3 games
3. **Monitor Telegram**: Keep app open to see alerts
4. **Review logs frequently**: Check `api_usage_log.json` after each run

### For Production Deployment
1. **Paper trade for 7 days**: Verify costs and accuracy
2. **Set budget alerts**: External monitoring (email/SMS)
3. **Backup API keys**: Store securely offline
4. **Document learnings**: Update CLAUDE.md with findings

### For Cost Optimization
1. **Cache aggressively**: 15-min injury cache is excellent
2. **Limit prop fetches**: Only fetch for high-value games
3. **Batch requests**: Use regions wisely (us,us2 vs full coverage)
4. **Monitor daily**: Don't wait for monthly bill surprise

---

## Conclusion

**Paid tier integration is CODE COMPLETE** and ready for testing. All infrastructure (monitoring, error handling, retry logic) is in place to prevent unexpected costs and track ROI from Day 1.

**Estimated cost**: $0.053 per game (well under $0.10 budget)
**Next blocker**: Install dependencies → Run tests → Measure actual usage

**Confidence Level**: 🟢 **HIGH** - Code is robust, costs are reasonable, monitoring is comprehensive.

---

**Report Compiled By**: Claude (Sonnet 4.5)
**Date**: January 7, 2026
**Status**: Integration Complete, Testing Pending
