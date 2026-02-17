# NBA API Best Practices Guide

**Created:** February 2, 2026 @ 9:45 PM EST  
**Purpose:** Standardize NBA API usage across all Ludi-Bot modules for maximum reliability  
**Applies to:** All scripts/modules using `nba_api` library or `stats.nba.com` endpoints

---

## Executive Summary

The NBA's stats.nba.com API is **notoriously unreliable** with frequent timeouts, rate limiting, and server errors. This guide documents battle-tested patterns for robust API interactions based on:

- ✅ Official `nba_api` library documentation
- ✅ Community best practices (GitHub issues, Slack discussions)
- ✅ Real-world testing (Phase 6.4 referee backfill: 1,640 games)

---

## Core Principles

1. **Always use timeout parameters** (default 30s is too short)
2. **Always implement retry logic** (NBA API has no built-in retries)
3. **Always respect rate limits** (0.6s between requests minimum)
4. **Never assume success** (validate responses, handle errors gracefully)
5. **Use static data when possible** (reduce unnecessary API calls)

---

## Required Implementation Pattern

### Minimum Standard (All NBA API Calls)

```python
from nba_api.stats.endpoints import boxscoresummaryv3
from utils.api_helpers import retry_with_backoff
import time

@retry_with_backoff(max_attempts=3, backoff=2.0, exceptions=(Exception,))
def fetch_game_data(nba_game_id: str):
    """
    Fetch game data from NBA API with resilience.
    
    Key parameters:
    - timeout=60: Double default timeout (30s too short for backfills)
    - retry_with_backoff: 3 attempts with exponential backoff (2s, 4s, 8s)
    """
    try:
        # CRITICAL: Always set timeout parameter explicitly
        box = boxscoresummaryv3.BoxScoreSummaryV3(
            game_id=nba_game_id,
            timeout=60  # vs default 30s
        )
        data = box.get_dict()
        
        # Validate response before returning
        if not data or 'boxScoreSummary' not in data:
            raise ValueError(f"Invalid API response for game {nba_game_id}")
        
        # IMPORTANT: Sleep between requests to respect rate limits
        time.sleep(0.6)
        
        return data
        
    except Exception as e:
        print(f"[ERROR] Failed to fetch game {nba_game_id}: {e}")
        raise  # Let retry decorator handle it
```

---

## API Configuration Reference

### Timeout Settings

| Endpoint Type | Recommended Timeout | Rationale |
|--------------|---------------------|-----------|
| Single Game Queries | 60s | BoxScore, PlayByPlay endpoints can be slow |
| Season/League Queries | 90s | Large datasets take longer to generate |
| Player Career Stats | 45s | Moderate dataset size |
| Static Data (Teams, Players) | 30s | Small responses, use default |

**Default timeout is 30s** - this is **too short** for production use during high-traffic periods.

### Rate Limiting

**Official Limit:** Unknown (NBA doesn't publish rate limits)  
**Community Consensus:** ~600ms between requests (1.67 req/sec max)  
**Ludi-Bot Standard:** 0.6s sleep between ALL NBA API calls

```python
# Configuration constant (use in all scripts)
API_SLEEP_SECONDS = 0.6  # Respect rate limits
time.sleep(API_SLEEP_SECONDS)
```

---

## Retry Logic Specification

### Using Ludi-Bot's `retry_with_backoff` Decorator

**Location:** `utils/api_helpers.py`

**Features:**
- ✅ Exponential backoff (2s → 4s → 8s)
- ✅ Specific handling for HTTP 429 (rate limit)
- ✅ Specific handling for HTTP 5xx (server errors)
- ✅ Timeout retry with increasing delays
- ✅ Connection error recovery

**Standard Configuration:**
```python
@retry_with_backoff(
    max_attempts=3,      # 3 total tries (1 original + 2 retries)
    backoff=2.0,         # Base delay multiplier
    exceptions=(Exception,)  # Catch all exceptions (NBA API varies)
)
```

**Retry Behavior:**
1. **Attempt 1:** Immediate execution
2. **Timeout/Error:** Wait 2s
3. **Attempt 2:** Retry
4. **Timeout/Error:** Wait 4s
5. **Attempt 3:** Final retry
6. **Timeout/Error:** Raise exception, log failure

---

## Common Pitfalls & Solutions

### ❌ WRONG: Using Default Timeout

```python
# DON'T DO THIS - will timeout frequently
box = boxscoresummaryv3.BoxScoreSummaryV3(game_id=game_id)
```

### ✅ CORRECT: Explicit Timeout

```python
# ALWAYS set timeout explicitly
box = boxscoresummaryv3.BoxScoreSummaryV3(game_id=game_id, timeout=60)
```

---

### ❌ WRONG: No Retry Logic

```python
# DON'T DO THIS - single timeout kills entire backfill
def fetch_data(game_id):
    box = boxscoresummaryv3.BoxScoreSummaryV3(game_id=game_id)
    return box.get_dict()
```

### ✅ CORRECT: Retry with Backoff

```python
# ALWAYS use retry decorator
@retry_with_backoff(max_attempts=3, backoff=2.0, exceptions=(Exception,))
def fetch_data(game_id):
    box = boxscoresummaryv3.BoxScoreSummaryV3(game_id=game_id, timeout=60)
    return box.get_dict()
```

---

### ❌ WRONG: No Rate Limiting

```python
# DON'T DO THIS - will trigger rate limits
for game_id in games:
    fetch_data(game_id)  # Rapid-fire requests
```

### ✅ CORRECT: Sleep Between Requests

```python
# ALWAYS sleep between requests
for game_id in games:
    fetch_data(game_id)
    time.sleep(0.6)  # Respect rate limits
```

---

## Response Validation

### Always Validate API Responses

```python
def validate_response(data: dict, expected_keys: list) -> bool:
    """
    Validate NBA API response has expected structure.
    
    Returns:
        True if valid, raises ValueError if invalid
    """
    if not data:
        raise ValueError("API returned empty response")
    
    for key in expected_keys:
        if key not in data:
            raise ValueError(f"Missing required key: {key}")
    
    return True

# Usage example
data = box.get_dict()
validate_response(data, ['boxScoreSummary', 'game'])
```

---

## Error Handling Guidelines

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process normally |
| 401/403 | Auth Error | Don't retry - check API key |
| 429 | Rate Limit | Retry with 2x backoff delay |
| 500-599 | Server Error | Retry with exponential backoff |
| Timeout | NBA API slow | Retry with longer timeout |

**The `retry_with_backoff` decorator handles all of these automatically.**

---

## Module Audit Checklist

Use this checklist to verify each module follows best practices:

- [ ] Imports `retry_with_backoff` from `utils.api_helpers`
- [ ] All NBA API calls wrapped with `@retry_with_backoff` decorator
- [ ] All endpoint constructors include `timeout=60` (or higher)
- [ ] All API call loops include `time.sleep(0.6)` between requests
- [ ] Response validation before processing data
- [ ] Error logging with context (game_id, player_id, etc.)
- [ ] No silent failures (no `except: pass` blocks)

---

## Scripts/Modules to Audit

### Priority 1 (Uses NBA API Directly)
- [x] `scripts/backfill_referee_assignments.py` - **UPDATED Phase 6.4**
- [ ] `scripts/sync_daily_referees.py` - Needs update
- [ ] `module_g.py` (LudiRefEngine) - Verify compliance

### Priority 2 (May Use NBA API Indirectly)
- [ ] `scripts/sync_tracking_*.py` - Check if using nba_api
- [ ] `scripts/sync_synergy_playtypes.py` - Uses Ghost Protocol, not NBA API
- [ ] `scripts/backfill_wowy*.py` - Check implementation

---

## Performance Benchmarks

### Phase 6.4 Referee Backfill Results

**Before Fixes (Default 30s timeout, no retry):**
- Games processed: 602/1,125 (53.5%)
- Timeout failures: ~523 games
- Success rate: 53.5%
- Time: 12 minutes (aborted due to consecutive failures)

**After Fixes (60s timeout + retry logic):**
- Games processed: 523/523 (100%)
- Timeout failures: 0 (all retries successful)
- Success rate: 100%
- Time: ~6 minutes
- **Coverage improvement: 68.1% → 100% of games with NBA IDs**

---

## Advanced: Circuit Breaker Pattern

For production systems making high-volume API calls, consider using the circuit breaker:

```python
from utils.api_helpers import safe_api_call, get_circuit_breaker

# Circuit breaker prevents cascading failures
def fetch_with_circuit_breaker(game_id):
    breaker = get_circuit_breaker('nba_api')
    
    def _fetch():
        box = boxscoresummaryv3.BoxScoreSummaryV3(game_id=game_id, timeout=60)
        return box.get_dict()
    
    return breaker.call(_fetch)
```

**Circuit Breaker States:**
- **CLOSED:** Normal operation
- **OPEN:** Too many failures (5+), reject calls immediately for 60s
- **HALF_OPEN:** Testing if endpoint recovered

---

## Static Data Optimization

Reduce API calls by using static datasets for common queries:

```python
from nba_api.stats.static import teams, players

# These DON'T make API calls - instant response
all_teams = teams.get_teams()
all_players = players.get_active_players()

# Use for lookups instead of querying API
lakers = [t for t in all_teams if t['abbreviation'] == 'LAL'][0]
lebron = [p for p in all_players if p['full_name'] == 'LeBron James'][0]
```

---

## Monitoring & Logging

### Log All API Interactions

```python
import logging

logger = logging.getLogger(__name__)

@retry_with_backoff(max_attempts=3, backoff=2.0, exceptions=(Exception,))
def fetch_data(game_id):
    logger.info(f"Fetching game data: {game_id}")
    
    try:
        box = boxscoresummaryv3.BoxScoreSummaryV3(game_id=game_id, timeout=60)
        data = box.get_dict()
        logger.info(f"✅ Success: {game_id}")
        return data
        
    except Exception as e:
        logger.error(f"❌ Failed: {game_id} - {e}")
        raise
```

---

## Known Issues & Workarounds

### Issue #1: AWS Lambda/EC2 Timeouts

**Problem:** NBA API times out more frequently on AWS infrastructure  
**Workaround:** Increase timeout to 90s, use retry logic  
**Reference:** [nba_api GitHub Issue #405](https://github.com/swar/nba_api/issues/405)

### Issue #2: Intermittent Server Errors

**Problem:** NBA API returns 500 errors sporadically  
**Workaround:** Retry with exponential backoff (already implemented)  
**Note:** Labeled as "third-party issue" - NBA's API, not the library

### Issue #3: Inconsistent Response Times

**Problem:** Same endpoint can take 2s or 30s+ unpredictably  
**Workaround:** Use 60s timeout for all production calls  
**Pattern:** Worse during live games and high-traffic periods

---

## Quick Reference Card

```python
# COPY THIS TEMPLATE FOR ALL NBA API CALLS

from nba_api.stats.endpoints import [YourEndpoint]
from utils.api_helpers import retry_with_backoff
import time

@retry_with_backoff(max_attempts=3, backoff=2.0, exceptions=(Exception,))
def your_function(identifier: str):
    """Your docstring here."""
    try:
        # 1. Set timeout explicitly (60s recommended)
        response = YourEndpoint(
            param=identifier,
            timeout=60
        )
        
        # 2. Get and validate data
        data = response.get_dict()
        if not data:
            raise ValueError("Empty response")
        
        # 3. Sleep to respect rate limits
        time.sleep(0.6)
        
        return data
        
    except Exception as e:
        print(f"[ERROR] {identifier}: {e}")
        raise  # Let retry decorator handle it
```

---

## References

1. **nba_api GitHub:** https://github.com/swar/nba_api
2. **HTTP Client Source:** https://github.com/swar/nba_api/blob/master/src/nba_api/library/http.py
3. **Timeout Issues:** https://github.com/swar/nba_api/issues?q=timeout
4. **Ludi-Bot API Helpers:** `utils/api_helpers.py`
5. **Phase 6.4 Implementation:** `scripts/backfill_referee_assignments.py`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-02 | Initial release (Phase 6.4 findings) |

---

**Questions or Issues?** Update this document as new patterns emerge.

**Last Updated:** February 2, 2026 @ 9:45 PM EST
