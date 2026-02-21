# API Best Practices Guide for Sports Analytics

**Version:** 1.0
**Last Updated:** February 17, 2026
**Author:** Ludi-Bot Development Team
**Purpose:** Comprehensive guide for working with sports data APIs (NBA, WNBA, NFL, MLB)

---

## Table of Contents

1. [Authentication & Secrets Management](#1-authentication--secrets-management)
2. [Rate Limiting & Quota Management](#2-rate-limiting--quota-management)
3. [Caching Strategies](#3-caching-strategies)
4. [Error Handling & Retry Logic](#4-error-handling--retry-logic)
5. [Request & Response Patterns](#5-request--response-patterns)
6. [Version Management & Breaking Changes](#6-version-management--breaking-changes)
7. [Testing & Validation](#7-testing--validation)
8. [Monitoring & Alerting](#8-monitoring--alerting)
9. [Multi-API Architecture](#9-multi-api-architecture)
10. [Common Pitfalls & Anti-Patterns](#10-common-pitfalls--anti-patterns)
11. [Ludi-Bot Specific Patterns](#11-ludi-bot-specific-patterns)
12. [Sports API Considerations](#12-sports-api-considerations)
13. [Checklist for Adding New APIs](#13-checklist-for-adding-new-apis)
14. [Future-Proofing for WNBA/NFL/MLB](#14-future-proofing-for-wnbanflmlb)

---

## 1. Authentication & Secrets Management

### API Key Storage

**DO:**
- ✅ Store API keys in `.env` file (never commit to git)
- ✅ Load via `python-dotenv` or environment variables
- ✅ Validate keys exist at startup
- ✅ Support multi-environment configs (local, CI/CD, production)

**DON'T:**
- ❌ Hard-code API keys in source code
- ❌ Commit `.env` file to version control
- ❌ Expose keys in logs or error messages

### Implementation Pattern

```python
# config.py
import os
from dotenv import load_dotenv

# Load .env ONLY if not in self-hosted/CI environment
if not os.getenv('IS_SELF_HOSTED'):
    load_dotenv()
else:
    print("🔒 Running in Self-Hosted Mode: Using injected secrets")

# Load API keys
ODDS_API_KEY = os.getenv('ODDS_API_KEY')
TANK01_KEY = os.getenv('TANK01_KEY')
BALLDONTLIE_KEY = os.getenv('BALLDONTLIE_KEY')

# Validation function
def validate_config():
    required_keys = {
        'ODDS_API_KEY': ODDS_API_KEY,
        'TANK01_KEY': TANK01_KEY,
    }

    missing = [key for key, value in required_keys.items() if not value]

    if missing:
        raise ValueError(f"Missing REQUIRED API keys: {', '.join(missing)}")

    print("✅ Core API keys loaded")
```

> **Lessons from Ludi-Bot:**
> We learned the hard way that `load_dotenv()` in Python 3.14+ can fail with an `AssertionError` in some environments. Our solution: conditional loading based on `IS_SELF_HOSTED` flag, with manual parsing as fallback. Additionally, CI/CD workflows should NEVER load `.env` files — secrets must be injected via GitHub Actions secrets to prevent leakage.

### Header Management

```python
# Client initialization
class BDLClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("BALLDONTLIE_KEY")

        # Session with persistent headers
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": self.api_key or "",
            "Content-Type": "application/json",
        })
```

### Secret Rotation

When rotating API keys:
1. Add new key to `.env` as `{SERVICE}_KEY_NEW`
2. Update code to try new key first, fallback to old
3. Test thoroughly in staging
4. Remove old key after 24-48 hours

---

## 2. Rate Limiting & Quota Management

### Request Budgeting

**Principle:** Track quota usage BEFORE you hit the limit.

```python
# Example: Tank01 daily budget enforcement
class HistorianSync:
    DAILY_BUDGET = 200  # 20% of 1,000/day limit

    def __init__(self):
        self.request_count = 0
        self.budget_exceeded = False

    def _check_budget(self):
        if self.request_count >= self.DAILY_BUDGET:
            self.budget_exceeded = True
            raise Exception(f"Daily budget of {self.DAILY_BUDGET} requests exceeded")
        self.request_count += 1
```

### Intelligent Throttling

**Pattern:** Sleep delays between requests to respect rate limits.

```python
# BDL Client: 600 req/min = 10 req/sec
class BDLClient:
    def __init__(self):
        self.last_request_time = 0
        self.min_interval = 0.11  # slightly above 0.1s (safety margin)

    def _wait_for_rate_limit(self):
        """Enforce rate limits between calls."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
```

### Quota Monitoring

**Pattern:** Parse rate limit headers and alert at thresholds.

```python
# API Monitor implementation
class APIMonitor:
    def check_quota_threshold(self, api_name: str, threshold: float = 0.8):
        """Alert if API quota is approaching limit."""
        remaining = self._get_remaining_quota(api_name)
        total_limit = self._get_total_limit(api_name)

        used_pct = 1.0 - (remaining / total_limit)

        if used_pct >= threshold:
            msg = f"⚠️ WARNING: {api_name} quota at {used_pct*100:.1f}%"
            print(msg)
            self._send_telegram_alert(msg)
```

> **Lessons from Ludi-Bot:**
> We hit quota exhaustion on The-Odds-API during January, causing 5+ days of pipeline failures before we noticed. The fix: implement `api_monitor.py` that checks quota after EVERY request and sends Telegram alerts at 80% usage. Additionally, we added BDL as a fallback when primary APIs are exhausted.

### Fallback Strategies

**When quota exhausted:**
1. **Graceful degradation** — Switch to backup API
2. **Cached data** — Use stale data with warnings
3. **Fail loudly** — Alert user, don't silently fail

```python
# Module A fallback pattern
try:
    data = self._fetch_from_odds_api()
except QuotaExceeded:
    print("📡 The-Odds-API quota exhausted, falling back to BallDontLie...")
    self._using_bdl_fallback = True
    data = self._fetch_from_balldontlie()
```

### Request Prioritization

**Principle:** Not all requests are equal.

```python
# Priority tiers for Tank01 budget
PRIORITY_TIERS = {
    'injury_list': 1,        # Critical (affects lineup)
    'box_scores': 2,         # High (needed for settlement)
    'depth_charts': 3,       # Medium (daily refresh)
    'team_schedule': 4,      # Low (infrequent changes)
}
```

---

## 3. Caching Strategies

### When to Cache

| Data Type | TTL | Reasoning |
|-----------|-----|-----------|
| Injury reports | 15 min | NBA rule: 15 min before tipoff |
| Season averages | 24 hours | Changes daily at most |
| Game schedules | 12 hours | Rarely change mid-season |
| Live odds | 30 min | Rapid line movement |
| Historical stats | 30 days | Immutable once finalized |
| Player rosters | 1 hour | Trade deadline flux |

### File-Based Caching

**Pattern:** Deterministic cache keys with TTL validation.

```python
import hashlib
import json
import os
from datetime import datetime, timedelta

CACHE_DIR = "cache/bdl"
CACHE_TTL_HOURS = 24

def _get_cache_path(endpoint: str, params: dict = None) -> str:
    """Generate deterministic cache file path from endpoint + params."""
    key = endpoint
    if params:
        key += "_" + json.dumps(params, sort_keys=True)
    digest = hashlib.md5(key.encode()).hexdigest()[:12]
    safe_endpoint = endpoint.replace("/", "_").replace("?", "_")
    return os.path.join(CACHE_DIR, f"{safe_endpoint}_{digest}.json")

def _read_cache(cache_path: str) -> Optional[Dict]:
    """Read from cache if file exists and is not expired."""
    if not os.path.exists(cache_path):
        return None

    # Check TTL
    file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
    if datetime.now() - file_time > timedelta(hours=CACHE_TTL_HOURS):
        return None  # Expired

    try:
        with open(cache_path, 'r') as f:
            return json.load(f)
    except Exception:
        return None  # Corrupt cache

def _write_cache(cache_path: str, data: Dict) -> None:
    """Write data to cache file. Silent failure OK."""
    try:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass  # Cache is performance optimization, not critical
```

> **Lessons from Ludi-Bot:**
> PBP Stats API was painfully slow (120s timeouts common). Adding file-based caching with 24h TTL gave us a **19.4x speedup** on cached requests. The key insight: use MD5 hashing of sorted params to generate deterministic cache filenames, so the same query always hits the same cache file.

### Cache Invalidation Rules

**Golden rule:** Be explicit about when cache is stale.

```python
# Cache invalidation triggers
def invalidate_cache_if_needed(cache_path: str, event: str) -> None:
    """Delete cache if specific event occurs."""
    if event == 'trade_deadline':
        # All roster caches are stale
        if 'roster' in cache_path or 'depth' in cache_path:
            os.remove(cache_path)
    elif event == 'all_star_break':
        # Reset season averages (sample size shift)
        if 'season_averages' in cache_path:
            os.remove(cache_path)
```

### In-Memory Caching (functools.lru_cache)

**Use case:** Frequently called functions with static data.

```python
from functools import lru_cache

class BDLClient:
    @lru_cache(maxsize=1000)
    def get_player_by_id(self, player_id: int) -> Dict:
        """Fetch single player details by ID (cached in memory)."""
        data = self._get(f"{self.BASE_URL_V1}/players/{player_id}")
        return data.get("data", {}) if data else {}
```

**Warning:** Only use `lru_cache` for functions with **immutable** inputs (player IDs, team IDs). Don't cache functions that take mutable dicts or lists as arguments.

---

## 4. Error Handling & Retry Logic

### HTTP Status Code Handling

**Principle:** Different errors require different strategies.

```python
# Comprehensive error handling
def _get(self, url: str, params: Dict = None) -> Dict:
    try:
        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code

        if status_code == 401 or status_code == 403:
            # Authentication error - DON'T RETRY
            logger.error(f"AUTH ERROR ({status_code}): Check API Key")
            return {}
        elif status_code == 429:
            # Rate limit - RETRY with longer delay
            logger.error(f"RATE LIMIT (429): Slow down requests")
            return {}
        elif status_code >= 500:
            # Server error - RETRY with backoff
            logger.error(f"SERVER ERROR ({status_code}): Retrying...")
            return {}
        else:
            # Other HTTP errors
            logger.error(f"HTTP Error: {e}")
            return {}
    except requests.exceptions.RequestException as e:
        logger.error(f"Connection Error: {e}")
        return {}
```

### Retry Strategies

**Pattern:** Exponential backoff with max attempts.

```python
from functools import wraps
import time

def retry_with_backoff(max_attempts: int = 3, backoff: float = 2.0):
    """Decorator to retry function with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 1

            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)

                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if e.response else None

                    if status_code == 401 or status_code == 403:
                        # Don't retry auth errors
                        raise
                    elif status_code == 429:
                        # Rate limit - double the wait time
                        wait_time = backoff * (2 ** (attempt - 1)) * 2
                        print(f"⏳ RATE LIMIT: Waiting {wait_time:.1f}s...")
                        if attempt < max_attempts:
                            time.sleep(wait_time)
                            attempt += 1
                            continue
                        else:
                            raise
                    elif status_code and status_code >= 500:
                        # Server error - standard backoff
                        wait_time = backoff * (2 ** (attempt - 1))
                        print(f"⚠️ SERVER ERROR: Retrying in {wait_time:.1f}s...")
                        if attempt < max_attempts:
                            time.sleep(wait_time)
                            attempt += 1
                            continue
                        else:
                            raise
                    else:
                        raise

                except requests.exceptions.Timeout:
                    wait_time = backoff * (2 ** (attempt - 1))
                    print(f"⏱️ TIMEOUT: Retrying in {wait_time:.1f}s...")
                    if attempt < max_attempts:
                        time.sleep(wait_time)
                        attempt += 1
                        continue
                    else:
                        raise

        return wrapper
    return decorator
```

**Usage:**

```python
@retry_with_backoff(max_attempts=3, backoff=2.0)
def fetch_live_slate(self):
    url = f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds'
    response = self.session.get(url, params=params)
    response.raise_for_status()
    return response.json()
```

> **Lessons from Ludi-Bot:**
> PBP Stats API had frequent 429 errors and timeouts. Adding retry logic with exponential backoff (2s → 4s → 8s) and timeout escalation (120s → 180s) reduced failure rate from 15% to <1%. The key: double the wait time for rate limits (429), use standard backoff for server errors (5xx).

### Timeout Configuration

**Pattern:** Tiered timeouts based on endpoint complexity.

```python
# PBP Stats timeouts
def get_on_off(team_id: str, player_id: str, use_cache: bool = True) -> Optional[Dict]:
    """Get on/off data with timeout fallback."""

    # Try 120s first, escalate to 180s if timeout
    for timeout in [120, 180]:
        try:
            response = _session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            if timeout == 120:
                print(f"⏱️ Timeout at 120s, retrying with 180s...")
                continue
            else:
                print(f"⏱️ Final timeout at 180s")
                return None
```

### Fallback Data Sources

**Pattern:** Primary → Secondary → Cached → Default.

```python
def get_injuries(self) -> List[Dict]:
    """Fetch injury list with fallback chain."""

    # Try Tank01 (primary)
    try:
        return self._fetch_from_tank01()
    except Exception as e:
        print(f"⚠️ Tank01 failed: {e}")

    # Try BallDontLie (secondary)
    try:
        return self._fetch_from_balldontlie()
    except Exception as e:
        print(f"⚠️ BallDontLie failed: {e}")

    # Use cached data (stale OK)
    cached = self._read_stale_cache()
    if cached:
        print(f"⚠️ Using stale cache (age: {cached['age']})")
        return cached['data']

    # Default: empty list
    print(f"⚠️ All sources failed, returning empty injury list")
    return []
```

---

## 5. Request & Response Patterns

### Required vs Optional Parameters

**Pattern:** Validate required params BEFORE making request.

```python
def get_wowy_stats(team_id: str, player_ids: List[str],
                   season: str = "2025-26") -> Optional[Dict]:
    """Get WOWY stats with parameter validation."""

    # Validate REQUIRED parameters
    if not team_id:
        raise ValueError("team_id is required")
    if not player_ids or len(player_ids) == 0:
        raise ValueError("player_ids is required and must not be empty")

    # Optional parameters have defaults
    params = {
        "Season": season,
        "SeasonType": "Regular Season",  # default
        "TeamId": team_id,
        "0Exactly1OnFloor": ",".join(player_ids)
    }

    return self._get(url, params)
```

> **Lessons from Ludi-Bot:**
> We discovered that many NBA API endpoints silently require a `league_id` parameter (usually "00" for NBA) even though it's not documented as required. The symptom: 400 errors with unhelpful error messages. The fix: always include `league_id: "00"` in params for NBA endpoints, even if documentation says it's optional.

### Header Standardization

**Pattern:** Browser-like headers to avoid 403 Forbidden.

```python
# PBP Stats client headers
def _get_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': 'https://www.pbpstats.com/',
        'Origin': 'https://www.pbpstats.com'
    })
    return session
```

**Why?** Some APIs (especially stats.nba.com) block requests with generic Python user agents or missing Referer headers.

### Request Validation

**Pattern:** Validate inputs match API constraints.

```python
def get_games(self, date: str = None, season: int = None) -> Dict:
    """Fetch games with input validation."""

    # Validate date format
    if date:
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            raise ValueError(f"Invalid date format: {date}. Expected YYYY-MM-DD")

    # Validate season year
    if season:
        if season < 2000 or season > 2030:
            raise ValueError(f"Invalid season: {season}")

    params = {"per_page": 100}
    if date:
        params["dates[]"] = date
    if season:
        params["seasons[]"] = season

    return self._get(f"{self.BASE_URL_V1}/games", params)
```

### Response Parsing & Validation

**Pattern:** Defensive parsing with fallbacks.

```python
def parse_response(response: Dict) -> List[Dict]:
    """Parse API response with validation."""

    # Check for expected structure
    if not response:
        return []

    # Handle different response formats
    data = response.get('data')
    if data is None:
        # Some APIs use 'results' instead
        data = response.get('results', [])

    # Validate data type
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        return [data]  # Wrap single object in list
    else:
        print(f"⚠️ Unexpected response format: {type(data)}")
        return []
```

### Data Contract Enforcement

**Pattern:** Validate critical fields exist before processing.

```python
def validate_game_data(game: Dict) -> bool:
    """Validate game dict has required fields."""
    required_fields = ['id', 'home_team', 'away_team', 'commence_time']

    for field in required_fields:
        if field not in game:
            print(f"⚠️ Missing required field: {field}")
            return False

    # Validate field types
    if not isinstance(game['id'], str):
        print(f"⚠️ Invalid field type: id should be str")
        return False

    return True
```

---

## 6. Version Management & Breaking Changes

### Dependency Pinning

**Pattern:** Lock dependencies to prevent breaking changes.

```python
# requirements.txt
requests==2.31.0          # Explicit version
python-dotenv==1.0.0      # Pinned
pytz==2024.1              # Stable timezone lib

# NOT this:
# requests>=2.0            # Too loose
# python-dotenv            # Unpinned (dangerous)
```

**Why pin?** API client libraries can introduce breaking changes in minor versions. Pinning ensures reproducibility.

### Breaking Change Detection

**Pattern:** Validate response structure in tests.

```python
def test_api_response_structure():
    """Detect breaking changes in API response format."""
    client = BDLClient()
    games = client.get_games(date='2026-02-17')

    # Assert expected structure
    assert 'data' in games, "Missing 'data' key in response"
    assert isinstance(games['data'], list), "'data' should be a list"

    if len(games['data']) > 0:
        game = games['data'][0]
        required_fields = ['id', 'home_team', 'visitor_team', 'datetime']
        for field in required_fields:
            assert field in game, f"Missing required field: {field}"
```

### Migration Strategies

**When API introduces breaking changes:**

1. **Dual support period** — Support both old and new formats
2. **Feature flags** — Toggle new API version via config
3. **Gradual rollout** — Test new version in staging first
4. **Rollback plan** — Keep old code commented out for 30 days

```python
# Example: Supporting v1 and v2 endpoints
class BDLClient:
    BASE_URL_V1 = "https://api.balldontlie.io/nba/v1"
    BASE_URL_V2 = "https://api.balldontlie.io/nba/v2"

    def get_advanced_stats(self, player_ids: List[int]) -> List[Dict]:
        """Fetch advanced stats (v2 endpoint)."""
        # v2 is faster but newer
        return self._get_all_pages(f"{self.BASE_URL_V2}/stats/advanced", params)

    def get_stats(self, player_ids: List[int]) -> Dict:
        """Fetch basic stats (v1 endpoint, stable)."""
        # v1 is legacy but reliable
        return self._get(f"{self.BASE_URL_V1}/stats", params)
```

### Testing New API Versions

**Pattern:** Test new version against known-good dataset.

```python
def test_new_api_version():
    """Compare new API version output with cached v1 output."""

    # Load cached v1 response
    with open('test_data/v1_response.json') as f:
        v1_data = json.load(f)

    # Fetch from new v2 endpoint
    client = BDLClient()
    v2_data = client.get_advanced_stats_v2(player_ids=[1629029])

    # Compare critical fields
    assert v2_data['player_id'] == v1_data['player_id']
    assert abs(v2_data['pts'] - v1_data['pts']) < 0.1

    print("✅ v2 API matches v1 output")
```

---

## 7. Testing & Validation

### Mock API Responses

**Pattern:** Use recorded responses for unit tests.

```python
import pytest
from unittest.mock import Mock, patch

@patch('requests.Session.get')
def test_fetch_games_with_mock(mock_get):
    """Test game fetching with mocked API response."""

    # Mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'data': [
            {'id': 1, 'home_team': {'full_name': 'Boston Celtics'}}
        ]
    }
    mock_get.return_value = mock_response

    # Call function
    client = BDLClient()
    games = client.get_games(date='2026-02-17')

    # Assertions
    assert len(games['data']) == 1
    assert games['data'][0]['home_team']['full_name'] == 'Boston Celtics'
```

### Integration Test Patterns

**Pattern:** Test real API with small quota usage.

```python
def test_live_api_integration():
    """Test against live API (quota-aware)."""

    # Only run if API key is set
    if not os.getenv('BALLDONTLIE_KEY'):
        pytest.skip("BDL API key not set")

    client = BDLClient()

    # Test single player lookup (low quota cost)
    player = client.get_player_by_id(1629029)  # Luka Doncic

    assert player['first_name'] == 'Luka'
    assert player['last_name'] == 'Doncic'

    print("✅ Live API integration test passed")
```

### Quota-Aware Testing

**DON'T:**
```python
# Bad: Burns quota on every test run
def test_all_players():
    client = BDLClient()
    players = client.get_all_players()  # Paginated call (expensive)
    assert len(players) > 400
```

**DO:**
```python
# Good: Use cached data for tests
def test_all_players():
    cache_path = 'test_data/all_players.json'

    if os.path.exists(cache_path):
        # Use cached data
        with open(cache_path) as f:
            players = json.load(f)
    else:
        # Fetch live (only once)
        client = BDLClient()
        players = client.get_all_players()
        with open(cache_path, 'w') as f:
            json.dump(players, f)

    assert len(players) > 400
```

### Validation Scripts

**Pattern:** Scheduled health checks for API stability.

```python
#!/usr/bin/env python3
"""
API Health Check — Runs daily via GitHub Actions
Tests critical endpoints without burning quota
"""

def check_odds_api():
    """Test The-Odds-API health."""
    try:
        gatekeeper = Gatekeeper()
        games = gatekeeper.fetch_live_slate()
        assert len(games) > 0, "No games returned"
        return True
    except Exception as e:
        print(f"❌ Odds API failed: {e}")
        return False

def check_tank01():
    """Test Tank01 API health."""
    try:
        # Test injury endpoint (low cost)
        url = "https://tank01-fantasy-stats.p.rapidapi.com/getNBAInjuryList"
        response = requests.get(url, headers=headers)
        assert response.status_code == 200
        return True
    except Exception as e:
        print(f"❌ Tank01 failed: {e}")
        return False

if __name__ == "__main__":
    results = {
        'odds_api': check_odds_api(),
        'tank01': check_tank01(),
    }

    if not all(results.values()):
        sys.exit(1)  # Fail CI if any API is down
```

### Dry-Run Modes

**Pattern:** Test pipeline without making real API calls.

```python
# main.py
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                       help="Test mode: use cached data only")
    args = parser.parse_args()

    if args.dry_run:
        print("🧪 DRY RUN MODE: Using cached data")
        os.environ['USE_CACHE_ONLY'] = 'true'
```

---

## 8. Monitoring & Alerting

### Request Logging

**Pattern:** Log all API requests to structured JSON.

```python
class APIMonitor:
    def log_request(self, api_name: str, endpoint: str, response_headers: Dict):
        """Log an API request with rate limit information."""
        timestamp = datetime.now().isoformat()

        # Parse rate limit headers
        rate_info = self._parse_rate_limit_headers(response_headers, api_name)

        log_entry = {
            'timestamp': timestamp,
            'api': api_name,
            'endpoint': endpoint,
            'rate_limit_info': rate_info
        }

        # Persist to JSON
        self.logs.append(log_entry)
        self._save_logs()

        # Console output (don't expose API keys!)
        if 'requests_remaining' in rate_info:
            print(f"📊 {api_name}: {rate_info['requests_remaining']} credits remaining")
```

**CRITICAL:** Never log API keys, even in debug mode.

```python
# Bad
print(f"Making request to {url} with key {api_key}")

# Good
print(f"Making request to {url}")  # Key is in headers, not logged
```

### Success/Failure Metrics

**Pattern:** Track hit rates and error patterns.

```python
class APIMonitor:
    def get_success_rate(self, api_name: str, days: int = 7) -> float:
        """Calculate API success rate over time period."""
        recent_logs = self._get_recent_logs(api_name, days)

        total = len(recent_logs)
        failures = len([log for log in recent_logs if log.get('status') == 'FAILED'])

        success_rate = (total - failures) / total if total > 0 else 0
        return success_rate
```

### Quota Usage Tracking

**Pattern:** Real-time quota dashboard.

```python
def print_quota_dashboard():
    """Print current quota usage across all APIs."""
    monitor = get_monitor()

    print("\n" + "="*50)
    print("   API QUOTA DASHBOARD")
    print("="*50)

    # The-Odds-API
    odds_remaining = monitor.get_remaining('odds_api')
    odds_limit = 20000  # monthly
    odds_pct = (1 - odds_remaining/odds_limit) * 100
    print(f"The-Odds-API: {odds_remaining:,} / {odds_limit:,} ({odds_pct:.1f}% used)")

    # Tank01
    tank_remaining = monitor.get_remaining('tank01')
    tank_limit = 1000  # daily
    tank_pct = (1 - tank_remaining/tank_limit) * 100
    print(f"Tank01: {tank_remaining} / {tank_limit} ({tank_pct:.1f}% used)")

    print("="*50 + "\n")
```

### Performance Monitoring

**Pattern:** Track latency and detect slowdowns.

```python
import time

class APIMonitor:
    def time_request(self, api_name: str, func: Callable):
        """Measure request latency."""
        start = time.time()
        result = func()
        elapsed = time.time() - start

        self.log_latency(api_name, elapsed)

        # Alert if abnormally slow
        if elapsed > 10.0:
            print(f"⚠️ Slow request: {api_name} took {elapsed:.1f}s")

        return result
```

### Alert Thresholds

**Pattern:** Multi-tier alerting based on severity.

```python
ALERT_THRESHOLDS = {
    'quota_warning': 0.80,   # 80% usage
    'quota_critical': 0.95,  # 95% usage
    'error_rate_warning': 0.05,  # 5% failures
    'error_rate_critical': 0.15,  # 15% failures
}

def check_alerts():
    """Check all alert conditions and notify if needed."""
    monitor = get_monitor()

    # Quota alerts
    for api_name in ['odds_api', 'tank01']:
        usage_pct = monitor.get_usage_pct(api_name)

        if usage_pct >= ALERT_THRESHOLDS['quota_critical']:
            send_critical_alert(f"{api_name} quota at {usage_pct*100:.1f}%")
        elif usage_pct >= ALERT_THRESHOLDS['quota_warning']:
            send_warning_alert(f"{api_name} quota at {usage_pct*100:.1f}%")

    # Error rate alerts
    error_rate = monitor.get_error_rate(days=1)
    if error_rate >= ALERT_THRESHOLDS['error_rate_critical']:
        send_critical_alert(f"Error rate: {error_rate*100:.1f}%")
```

### P&L Sanity Gate

**Problem:** Corrupt odds data (from BDL fallback sources) can produce impossible payout multipliers that inflate P&L by 10-100x. Standard monitoring doesn't catch this.

```python
# In settlement summary script — validate before reporting
total_pnl = sum(bet.profit_loss for bet in settled_bets)

# Sanity gate: single-day P&L > ±50u is anomalous (flag immediately)
if abs(total_pnl) > 50:
    msg = f"⚠️ P&L ANOMALY: {total_pnl:.1f}u on {len(settled_bets)} bets — investigate before trusting"
    print(msg)
    from utils.slack_notifier import send_slack_alert
    send_slack_alert("P&L Anomaly Detected", msg)

# Also validate no single bet has > 10u profit (catches 50x multiplier bug)
outliers = [b for b in settled_bets if abs(b.profit_loss) > 10]
if outliers:
    send_slack_alert("Bet Outliers", f"{len(outliers)} bets with >10u P&L — check odds data")
```

> **Real example (Feb 19, 2026):** Reported +269u was actually -41u. Root cause: BDL milestone market types produced corrupt odds (-2, -4, -9). Settlement formula `100/abs(-2) = 50x` per win.

### Notification Routing: Telegram vs Slack

**Pattern (Ludi-Bot Feb 2026):** Separate ops alerts from betting product.

```python
# Ops/system alerts → Slack (webhook, channel C0AGBQXRXB3)
# Includes: quota warnings, P&L anomalies, API failures, workflow errors
from utils.slack_notifier import send_slack_alert
send_slack_alert("Quota Warning", f"{api_name} at {pct:.1f}% — {remaining} remaining")

# Betting product → Telegram (stays clean for bettors)
# Includes: Diamond plays, P&L summaries, game notes, spotlights
from utils.telegram_notifier import send_message
send_message("💎 DIAMOND: Player Props Brief")
```

**Why separate:** Mixing ops alerts (workflow failures, API errors) with betting output clutters the betting experience. Ops team monitors Slack; bettors see clean Telegram.

### Telegram Notifications

**Pattern:** Real-time alerts to mobile.

```python
def send_telegram_alert(message: str):
    """Send alert via Telegram bot."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': f"🤖 Ludi API Monitor\n\n{message}",
            'parse_mode': 'HTML'
        }
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"⚠️ Telegram alert failed: {e}")
```

> **Lessons from Ludi-Bot:**
> We implemented a full API monitoring system (`utils/api_monitor.py`) after discovering quota exhaustion issues. The system logs every request to `api_usage_log.json`, tracks quota in real-time, and sends Telegram alerts at 80% usage. This prevented 3+ outages in the first month alone.

---

## 9. Multi-API Architecture

### Primary/Fallback Pattern

**Architecture:** Layer APIs by reliability and cost.

```
Primary Layer:    The-Odds-API (paid, reliable)
Secondary Layer:  BallDontLie (paid, backup)
Tertiary Layer:   Cached data (stale but available)
```

**Implementation:**

```python
class Gatekeeper:
    def fetch_game_lines(self):
        """Fetch game lines with automatic fallback."""

        # Try primary
        try:
            return self._fetch_from_odds_api()
        except QuotaExceeded:
            print("📡 Quota exhausted, falling back to BallDontLie...")
            self._using_bdl_fallback = True
        except Exception as e:
            print(f"⚠️ The-Odds-API failed: {e}")

        # Try secondary
        try:
            return self._fetch_from_balldontlie()
        except Exception as e:
            print(f"⚠️ BallDontLie failed: {e}")

        # Fallback to cache
        cached = self._read_stale_cache('game_lines')
        if cached:
            print(f"⚠️ Using stale cache")
            return cached

        # No data available
        raise Exception("All data sources failed")
```

### Data Normalization

**Problem:** Different APIs use different team codes.

| API | Warriors | Pelicans | Knicks | Suns | Spurs |
|-----|----------|----------|--------|------|-------|
| Ludi Standard | GSW | NOP | NYK | PHX | SAS |
| BallDontLie | GS | NO | NY | PHO | SA |
| The-Odds-API | Golden State Warriors | New Orleans Pelicans | ... | ... | ... |

**Solution:** Normalization layer.

```python
class BDLClient:
    # Mapping: BDL → Standard
    TEAM_ABBREVIATION_MAP = {
        'GS': 'GSW',
        'NO': 'NOP',
        'NY': 'NYK',
        'PHO': 'PHX',
        'SA': 'SAS'
    }

    def _normalize_team_abbreviation(self, abbrev: str) -> str:
        """Normalize BDL team codes to standard NBA codes."""
        return self.TEAM_ABBREVIATION_MAP.get(abbrev, abbrev)

    def _normalize_team_data(self, data: Any) -> Any:
        """Recursively normalize team codes in API response."""
        if isinstance(data, dict):
            if 'abbreviation' in data:
                data['abbreviation'] = self._normalize_team_abbreviation(data['abbreviation'])
            # Recurse into nested dicts
            for key, value in data.items():
                data[key] = self._normalize_team_data(value)
        elif isinstance(data, list):
            return [self._normalize_team_data(item) for item in data]
        return data
```

### Canonical ID Systems

**Problem:** Each API uses different player IDs.

- Tank01: Composite IDs (e.g., `28398804489`)
- NBA.com: Official IDs (e.g., `1629029`)
- BallDontLie: BDL IDs (e.g., `37428`)

**Solution:** Canonical ID mapping table.

```sql
CREATE TABLE player_canonical_ids (
    id INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL,
    nba_id TEXT UNIQUE,           -- Official NBA ID
    tank01_id TEXT,               -- Tank01 composite ID
    bdl_id TEXT,                  -- BallDontLie ID
    UNIQUE(player_name)
);
```

**Mapping function:**

```python
def map_bdl_to_canonical(bdl_player: Dict) -> Optional[str]:
    """Map BDL player to our canonical NBA ID."""
    first = bdl_player.get("first_name", "")
    last = bdl_player.get("last_name", "")
    full_name = f"{first} {last}"

    conn = sqlite3.connect("ludi.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT nba_id FROM player_canonical_ids WHERE LOWER(player_name) = ?",
        (full_name.lower(),)
    )
    row = cursor.fetchone()
    conn.close()

    return str(row[0]) if row else None
```

> **Lessons from Ludi-Bot:**
> Tank01 changed their ID format from simple NBA IDs to composite IDs (player_id + team_id) without warning, breaking our entire pipeline. The fix: implement a canonical ID system (`player_canonical_ids` table) that maps all API-specific IDs to our internal NBA ID standard. Now when Tank01 changes formats again, we only update one mapping function instead of 8+ modules.

### API Selection Logic

**Pattern:** Choose API based on data freshness requirements.

```python
def get_player_stats(player_id: str, freshness: str = 'live') -> Dict:
    """Fetch player stats with appropriate API based on freshness need."""

    if freshness == 'live':
        # Live data: Use Tank01 (updated every 5 min)
        return tank01_client.get_box_score(player_id)
    elif freshness == 'daily':
        # Daily averages: Use BDL (faster, cached 24h)
        return bdl_client.get_season_averages(player_id)
    elif freshness == 'historical':
        # Historical: Use local database (no API cost)
        return db.get_player_game_logs(player_id)
```

### Cross-API Validation

**Pattern:** Sanity check data across multiple sources.

```python
def validate_game_schedule():
    """Verify game schedule matches across APIs."""

    # Fetch from 3 sources
    odds_games = odds_api.get_games(date='2026-02-17')
    bdl_games = bdl_client.get_games(date='2026-02-17')
    tank_games = tank01_client.get_games(date='2026-02-17')

    # Compare counts
    if len(odds_games) != len(bdl_games):
        print(f"⚠️ Game count mismatch: Odds={len(odds_games)}, BDL={len(bdl_games)}")

    # Cross-reference game IDs
    odds_ids = {g['id'] for g in odds_games}
    bdl_ids = {g['id'] for g in bdl_games}

    missing = odds_ids - bdl_ids
    if missing:
        print(f"⚠️ Games in Odds API but not BDL: {missing}")
```

---

## 10. Common Pitfalls & Anti-Patterns

### ❌ UPSERT Conflict Target Doesn't Match Unique Constraint

**Anti-Pattern:**
```python
# BAD: ON CONFLICT target doesn't match the actual unique index
cursor.execute("""
    INSERT INTO player_game_logs (player_id, game_date, pts)
    VALUES (?, ?, ?)
    ON CONFLICT(game_id, player_id) DO UPDATE SET pts = excluded.pts
""")
# If actual unique constraint is (player_id, game_date):
# → No conflict is ever detected
# → Inserts either silently succeed as duplicates OR fail with ConstraintError
# → Days/weeks of data missing with NO ERROR MESSAGE
```

**Correct Pattern:**
```python
# GOOD: Verify conflict target against actual unique constraint FIRST
# Check with: sqlite3 db.db ".indexes" then "PRAGMA index_info(idx_name);"
cursor.execute("""
    INSERT INTO player_game_logs (player_id, game_date, pts)
    VALUES (?, ?, ?)
    ON CONFLICT(player_id, game_date) DO UPDATE SET pts = excluded.pts
""")
```

> **Lessons from Ludi-Bot (Feb 19, 2026):** `module_h_historian.py` had `ON CONFLICT(game_id, player_id)` but the actual unique constraint is `(player_id, game_date)`. All game log inserts silently failed for 8 days — zero data from Feb 12–19. The script reported success with no errors. Fix: always run `PRAGMA index_info()` before writing ON CONFLICT clauses.

---

### ❌ Silent Failures

**Anti-Pattern:**
```python
# BAD: Error swallowed silently
try:
    data = fetch_wowy_data(player_id)
    process_data(data)
except Exception:
    continue  # Bug hidden for 21+ days!
```

**Correct Pattern:**
```python
# GOOD: Log error before continuing
try:
    data = fetch_wowy_data(player_id)
    process_data(data)
except Exception as e:
    print(f"⚠️ WOWY sync failed for {player_id}: {e}")
    continue  # Now we know WHY it failed
```

> **Lessons from Ludi-Bot:**
> A single `except Exception: continue` line in `sync_wowy_hybrid.py` hid a critical bug for **21+ days**. The symptom: WOWY table had 0 records, but the script reported "success" every day. The fix: Always log errors before `continue`, even if you don't want to fail the entire batch. Silent failures are the #1 cause of data quality issues in our project.

### ❌ Missing Required Parameters

**Anti-Pattern:**
```python
# BAD: Assumes optional parameter
response = api.get_games(season=2025)  # Missing league_id!
# Result: 400 Bad Request with unhelpful error
```

**Correct Pattern:**
```python
# GOOD: Include all required params (even if undocumented)
response = api.get_games(
    season=2025,
    league_id="00"  # Required for NBA endpoints
)
```

### ❌ Hard-Coded Values

**Anti-Pattern:**
```python
# BAD: Magic numbers scattered in code
def adjust_projection(pts):
    return pts * 0.965  # What does this mean?
```

**Correct Pattern:**
```python
# GOOD: Named constants with documentation
FATIGUE_B2B_TAX = 0.965  # Research: Garcia et al. 2020

def adjust_projection(pts):
    return pts * FATIGUE_B2B_TAX
```

### ❌ No Cache Invalidation Strategy

**Anti-Pattern:**
```python
# BAD: Cache never expires
if os.path.exists(cache_file):
    return json.load(open(cache_file))  # Could be months old!
```

**Correct Pattern:**
```python
# GOOD: TTL-based expiration
if os.path.exists(cache_file):
    age = time.time() - os.path.getmtime(cache_file)
    if age < CACHE_TTL_SECONDS:
        return json.load(open(cache_file))
    else:
        os.remove(cache_file)  # Expired, fetch fresh
```

### ❌ Ignoring HTTP Status Codes

**Anti-Pattern:**
```python
# BAD: Blind json parsing
response = requests.get(url)
return response.json()  # Could be 404, 500, etc.
```

**Correct Pattern:**
```python
# GOOD: Check status before parsing
response = requests.get(url)
response.raise_for_status()  # Raises HTTPError for 4xx/5xx
return response.json()
```

### ❌ Not Tracking Quota Usage

**Anti-Pattern:**
```python
# BAD: Burn through quota unknowingly
for player in all_players:  # 500+ API calls!
    stats = api.get_player_stats(player['id'])
```

**Correct Pattern:**
```python
# GOOD: Batch requests, track usage
# Use bulk endpoint if available
stats = api.get_bulk_player_stats(player_ids)

# Or at minimum, track usage
for i, player in enumerate(all_players):
    if i >= DAILY_BUDGET:
        print(f"⚠️ Daily budget reached ({DAILY_BUDGET} requests)")
        break
    stats = api.get_player_stats(player['id'])
```

### ❌ No Fallback When Primary Fails

**Anti-Pattern:**
```python
# BAD: Single point of failure
def get_injuries():
    return tank01_api.get_injury_list()  # What if Tank01 is down?
```

**Correct Pattern:**
```python
# GOOD: Fallback chain
def get_injuries():
    try:
        return tank01_api.get_injury_list()
    except Exception:
        return bdl_api.get_active_injuries()  # Backup source
```

### ❌ Exposing API Keys in Logs

**Anti-Pattern:**
```python
# BAD: Key in plain text
print(f"Calling {url}?api_key={API_KEY}")  # Leaked in logs!
```

**Correct Pattern:**
```python
# GOOD: Key in headers, not logged
headers = {"Authorization": f"Bearer {API_KEY}"}
print(f"Calling {url}")  # URL only, key hidden
```

### ❌ Not Testing with Real API Before Production

**Anti-Pattern:**
```python
# BAD: Deploy untested code to production
# "It should work based on the docs..."
```

**Correct Pattern:**
```python
# GOOD: Integration test with small dataset
def test_live_api():
    """Test actual API before deploying."""
    client = NewAPIClient()
    result = client.get_test_endpoint()
    assert result['status'] == 'ok'
    print("✅ API integration verified")
```

### ❌ Relying on Unverified CDN Endpoints

**Anti-Pattern:**
```python
# BAD: Assuming a CDN endpoint works because it's in the docs
url = "https://cdn.nba.com/static/json/staticData/injury-report_{date}.json"
response = requests.get(url)
injuries = response.json()  # 403 Forbidden — endpoint broken as of Feb 2026
```

**Correct Pattern:**
```python
# GOOD: Test the endpoint before shipping; always have a fallback
def get_nba_official_injuries():
    # NBA.com CDN endpoints CONFIRMED BROKEN as of Feb 2026 (403/empty).
    # Do not use cdn.nba.com or ak-static.cms.nba.com for injury data.
    # Use BDL primary → Tank01 fallback instead.
    return []
```

> **Lessons from Ludi-Bot:**
> Both `cdn.nba.com/static/json/staticData/injury-report_{date}.json` and `ak-static.cms.nba.com/referee/injury/...` return 403 or empty responses as of February 2026. This was discovered during Phase 8 planning — not at runtime — because we test endpoints before building on them. Always verify CDN endpoints are live before using them as a data source. CDN paths can go dark without notice.

---

## 11. Ludi-Bot Specific Patterns

### Client Wrapper Architecture

**Pattern:** Dedicated client class per API with common interface.

```
utils/
├── bdl_client.py           # BallDontLie (v1 + v2)
├── pbp_stats_client.py     # PBP Stats (free)
├── api_helpers.py          # Shared retry logic
└── api_monitor.py          # Global monitoring
```

**Common interface:**
```python
class APIClient:
    def __init__(self, api_key: str = None)
    def _get(self, url: str, params: Dict) -> Dict
    def _get_all_pages(self, url: str, params: Dict) -> List[Dict]
    def check_api_status(self) -> bool
```

### Caching Approach

**Pattern:** File-based cache with deterministic keys.

- **Cache directory:** `cache/{api_name}/`
- **Cache key:** MD5(endpoint + sorted_params)
- **TTL:** Configured per data type
- **Silent failures:** Cache writes never block requests

```python
# Example: BDL cache structure
cache/bdl/
├── player_injuries_a3f2c1.json      # TTL: 15 min
├── season_averages_general_b7e4.json  # TTL: 24 hours
└── odds_2026-02-17_c9d3.json         # TTL: 30 min
```

### Error Handling Standards

**Pattern:** 3-tier error handling.

```python
# Tier 1: Retry with backoff (transient errors)
@retry_with_backoff(max_attempts=3)
def fetch_data():
    pass

# Tier 2: Fallback to alternate source (source failure)
try:
    data = primary_api.fetch()
except Exception:
    data = secondary_api.fetch()

# Tier 3: Graceful degradation (all sources fail)
if not data:
    data = cached_data  # Stale but available
```

### Team Code Normalization

**Standard:** All internal code uses official NBA abbreviations.

```python
# Normalization map (any variant → standard)
TEAM_NORMALIZER = {
    'GS': 'GSW',           # BDL variant
    'Golden State': 'GSW', # Odds API variant
    'Warriors': 'GSW',     # Informal
    # ... (30 teams)
}
```

### Canonical ID Resolution

**Pattern:** Auto-resolve foreign IDs to our standard.

```python
# Database.py: ID resolution firewall
def upsert_player(player_data: Dict):
    """Upsert player with automatic ID resolution."""

    # Check if ID is non-standard (composite, BDL, etc.)
    if not is_valid_nba_id(player_data['id']):
        # Resolve to canonical
        canonical_id = resolve_canonical_id(player_data['name'])
        if canonical_id:
            player_data['id'] = canonical_id
        else:
            print(f"⚠️ Cannot resolve ID for {player_data['name']}")
            return  # Skip dirty data

    # Proceed with clean ID
    conn.execute("INSERT OR REPLACE INTO players ...", player_data)
```

---

## 12. Sports API Considerations

### Real-Time vs Historical Data

| Use Case | Latency Tolerance | Best Source |
|----------|------------------|-------------|
| Live odds | < 1 min | The-Odds-API (WebSocket if available) |
| Injury reports | 15 min | Tank01 / BDL (per NBA rule) |
| Box scores | 5-10 min post-game | Tank01 live endpoint |
| Season averages | 24 hours | BDL season_averages (cached) |
| Historical stats | N/A | Local database |

### Game Day vs Off-Season Patterns

**Game day (high traffic):**
- Minimize API calls (use cache aggressively)
- Batch requests when possible
- Pre-fetch data 2 hours before tipoff

**Off-season (low traffic):**
- Backfill historical data
- Refresh stale caches
- Run expensive analytics

### Player Identification Across APIs

**Challenge:** Same player, different IDs in each API.

**Solution:** Name-based matching with fuzzy tolerance.

```python
def fuzzy_match_player(name: str, candidates: List[Dict]) -> Optional[Dict]:
    """Match player name with tolerance for diacritics, Jr./Sr., etc."""

    # Normalize input
    normalized = normalize_name(name)  # Remove accents, lowercase, trim

    for candidate in candidates:
        candidate_name = normalize_name(f"{candidate['first']} {candidate['last']}")

        # Exact match
        if normalized == candidate_name:
            return candidate

        # Fuzzy match (Levenshtein distance)
        if levenshtein(normalized, candidate_name) <= 2:
            return candidate

    return None
```

> **Lessons from Ludi-Bot:**
> We had 16 player name mismatches due to diacritics: Jokić → Jokic, Dončić → Doncic, etc. RosterValidator resolved these by normalizing both API and DB names before comparison, reducing mismatch rate from 3.2% to 0.16%.

### Team Code Normalization

**Standard codes:** Use official NBA abbreviations (GSW, NOP, NYK, PHX, SAS).

**Mapping table:**

```python
TEAM_CODE_VARIANTS = {
    'Warriors': ['GS', 'GSW', 'Golden State', 'Golden State Warriors'],
    'Pelicans': ['NO', 'NOP', 'New Orleans', 'New Orleans Pelicans'],
    'Knicks': ['NY', 'NYK', 'New York', 'New York Knicks'],
    'Suns': ['PHO', 'PHX', 'Phoenix', 'Phoenix Suns'],
    'Spurs': ['SA', 'SAS', 'San Antonio', 'San Antonio Spurs'],
}
```

### Schedule Syncing

**Best practice:** Fetch schedule from multiple sources, cross-validate.

```python
def sync_schedule(date: str):
    """Sync game schedule with cross-API validation."""

    # Fetch from 3 sources
    espn_games = fetch_espn_schedule(date)
    bdl_games = bdl_client.get_games(date=date)
    tank_games = tank01_client.get_games(date=date)

    # Verify all agree
    if len(espn_games) != len(bdl_games) or len(bdl_games) != len(tank_games):
        print(f"⚠️ Schedule mismatch: ESPN={len(espn_games)}, BDL={len(bdl_games)}, Tank={len(tank_games)}")
    else:
        print(f"✅ Schedule verified: {len(bdl_games)} games")

    # Use BDL as source of truth (most reliable in our testing)
    return bdl_games
```

### Injury Data Handling

**NBA rule:** Teams must report injuries 15 minutes before tipoff.

> ⚠️ **NBA.com CDN CONFIRMED BROKEN (Feb 2026)**
> Both `cdn.nba.com/static/json/staticData/injury-report_{date}.json` and
> `ak-static.cms.nba.com/referee/injury/...` return 403 or empty responses.
> Do **not** use these endpoints. See anti-patterns section for details.

**Source hierarchy (updated Phase 8):**
1. **BDL primary** — `bdl_client.get_injuries()` (most reliable, structured response)
2. **Tank01 fallback** — roster-embedded injury fields via `get_team_roster()`
3. **`player_injuries` table** — local DB cache with intraday snapshots (Phase 8.0-A)

**Phase 8 intraday pattern (replaces file-based `yak_cache.json`):**

The new `player_injuries` table stores multiple snapshots per day, inserting only when status changes. This avoids unbounded row growth while preserving history.

```python
# scripts/sync_injuries.py — standalone, runs 3x daily
# is_game_day_report: 0 = overnight sync (5AM), 1 = game-day windows (11AM, 5:30PM)

def sync_injuries(is_game_day_report: int = 0):
    """Fetch injuries from BDL; only insert row when status changes."""
    injuries = bdl_client.get_injuries()  # BDL primary

    for player in injuries:
        last = db.query(
            "SELECT status FROM player_injuries WHERE player_id=? ORDER BY snapshot_time DESC LIMIT 1",
            [player['id']]
        )
        if not last or last[0]['status'] != player['status']:
            # Status changed — insert new snapshot
            db.execute(
                "INSERT INTO player_injuries (player_id, status, designation, "
                "description, snapshot_time, is_game_day_report) VALUES (?,?,?,?,?,?)",
                [player['id'], player['status'], player['designation'],
                 player['description'], datetime.utcnow().isoformat(), is_game_day_report]
            )
            # Also update fast-lookup columns on players table
            db.execute(
                "UPDATE players SET injury_status=?, injury_description=?, "
                "last_injury_update=? WHERE id=?",
                [player['status'], player['description'], datetime.utcnow().isoformat(), player['id']]
            )

# Three sync windows (wired via GitHub Actions):
# data_sync.yml      3:00 AM  — is_game_day_report=0  (overnight baseline)
# daily_briefing.yml 9:00 AM — is_game_day_report=1  (game-day report)
# capture_closing.yml 6:00 PM — is_game_day_report=1  (pre-tipoff final)
```

### Line/Odds Data Freshness

**Pattern:** Refresh frequency based on time until tipoff.

```python
def get_odds_refresh_interval(minutes_until_tipoff: int) -> int:
    """Dynamic refresh based on proximity to game start."""

    if minutes_until_tipoff > 120:
        return 60  # 1 hour before: refresh every 60 min
    elif minutes_until_tipoff > 60:
        return 30  # 1-2 hours before: every 30 min
    elif minutes_until_tipoff > 15:
        return 10  # 15-60 min before: every 10 min
    else:
        return 1   # Final 15 min: every 1 min (rapid line movement)
```

---

## 13. Checklist for Adding New APIs

Use this checklist when integrating a new sports data API:

### Pre-Integration
- [ ] Research API documentation thoroughly
- [ ] Understand pricing tier and quota limits
- [ ] Identify required vs optional parameters
- [ ] Check authentication method (API key, OAuth, etc.)
- [ ] Review rate limiting rules
- [ ] Test API in browser/Postman before coding

### Authentication
- [ ] Add API key to `.env.template` (without real value)
- [ ] Add API key to `.env` (gitignored)
- [ ] Update `config.py` with new key variable
- [ ] Add validation check in `validate_config()`
- [ ] Document tier/pricing in `docs/API_USAGE_AUDIT.md`

### Client Implementation
- [ ] Create dedicated client file (`utils/{api_name}_client.py`)
- [ ] Implement session with persistent headers
- [ ] Add rate limiting logic
- [ ] Add retry logic with exponential backoff
- [ ] Implement caching with appropriate TTL
- [ ] Add error handling for 401/403/429/5xx
- [ ] Validate response structure before returning
- [ ] Add team code normalization if needed
- [ ] Add player ID mapping if needed

### Testing
- [ ] Write unit tests with mocked responses
- [ ] Write integration test with live API (quota-aware)
- [ ] Test error handling (simulate 429, 500, timeout)
- [ ] Validate response parsing edge cases
- [ ] Test cache hit/miss scenarios
- [ ] Verify retry logic works correctly

### Monitoring
- [ ] Add API to `api_monitor.py`
- [ ] Log all requests with quota tracking
- [ ] Set quota alert thresholds (80% warning, 95% critical)
- [ ] Add API to health check script
- [ ] Test Telegram alerts work

### Integration
- [ ] Wire client into relevant modules
- [ ] Add fallback logic if replacing existing API
- [ ] Update data normalization layer
- [ ] Test end-to-end pipeline with new API
- [ ] Verify database writes work correctly

### Documentation
- [ ] Update `README.md` with new API
- [ ] Document in `docs/API_USAGE_AUDIT.md`
- [ ] Add usage examples to client docstrings
- [ ] Update `ARCHITECTURE.md` if significant change
- [ ] Document any gotchas in `MEMORY.md`

### Production
- [ ] Add API key to GitHub Actions secrets
- [ ] Update workflows to use new API
- [ ] Run production dry-run test
- [ ] Monitor for 24 hours before trusting
- [ ] Set calendar reminder to review quota usage in 30 days

---

## 14. Future-Proofing for WNBA/NFL/MLB

### Reusable Client Patterns

**Pattern:** Sport-agnostic base client.

```python
# utils/base_sports_client.py
class BaseSportsClient:
    """Base class for all sports API clients."""

    def __init__(self, api_key: str, sport: str):
        self.api_key = api_key
        self.sport = sport  # 'nba', 'wnba', 'nfl', 'mlb'
        self.session = requests.Session()

    def _get(self, url: str, params: Dict) -> Dict:
        """Standard GET with retry logic."""
        # Shared implementation
        pass

    def _normalize_team_code(self, code: str) -> str:
        """Sport-specific team code normalization."""
        mapping = TEAM_NORMALIZERS[self.sport]
        return mapping.get(code, code)

# Sport-specific implementations
class NBAClient(BaseSportsClient):
    def __init__(self, api_key: str):
        super().__init__(api_key, sport='nba')

class WNBAClient(BaseSportsClient):
    def __init__(self, api_key: str):
        super().__init__(api_key, sport='wnba')
```

### Sport-Agnostic Data Models

**Pattern:** Flexible schema supporting multiple sports.

```sql
-- Generic player table
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    sport TEXT NOT NULL,            -- 'nba', 'wnba', 'nfl', 'mlb'
    name TEXT NOT NULL,
    team TEXT,
    position TEXT,
    status TEXT,
    metadata JSON,                  -- Sport-specific data
    UNIQUE(sport, name)
);

-- Generic game logs (stat columns are JSON for flexibility)
CREATE TABLE game_logs (
    id INTEGER PRIMARY KEY,
    sport TEXT NOT NULL,
    player_id INTEGER,
    game_date TEXT,
    stats JSON,                     -- Flexible: points/yards/hits/goals
    FOREIGN KEY(player_id) REFERENCES players(id)
);
```

### Configurable Endpoints

**Pattern:** Sport-specific config files.

```python
# config/nba.py
API_ENDPOINTS = {
    'odds': 'https://api.the-odds-api.com/v4/sports/basketball_nba/odds',
    'schedule': 'https://api.balldontlie.io/nba/v1/games',
}

# config/wnba.py
API_ENDPOINTS = {
    'odds': 'https://api.the-odds-api.com/v4/sports/basketball_wnba/odds',
    'schedule': 'https://api.balldontlie.io/wnba/v1/games',
}

# Load based on sport
def load_config(sport: str):
    if sport == 'nba':
        from config import nba
        return nba
    elif sport == 'wnba':
        from config import wnba
        return wnba
```

### Flexible Schema Design

**Pattern:** JSON columns for sport-specific data.

```python
# NBA player
{
    "sport": "nba",
    "name": "Luka Doncic",
    "metadata": {
        "position": "PG",
        "archetype": "HELIOCENTRIC",
        "usage_pct": 34.5
    }
}

# NFL player
{
    "sport": "nfl",
    "name": "Patrick Mahomes",
    "metadata": {
        "position": "QB",
        "archetype": "GUNSLINGER",
        "completion_pct": 68.2
    }
}
```

### Cross-Sport Lessons

**NBA → WNBA:**
- Same data structure (PBP Stats supports both)
- Same injury rules (15-min reporting)
- Same simulation approach (Poisson for volume stats)

**NBA → NFL:**
- Different stats (yards vs points, tackles vs rebounds)
- Different injury timelines (weekly vs daily)
- Different simulation (binomial for pass/rush vs Poisson)

**NBA → MLB:**
- Fundamentally different stats (batting avg, ERA)
- No pace factor (9 innings fixed)
- Different simulation (beta distribution for batting)

---

## Appendix: Reference Files

### Key Ludi-Bot Files

| File | Purpose |
|------|---------|
| `config.py` | API key management and global settings |
| `utils/bdl_client.py` | BallDontLie API client (607 lines) |
| `utils/pbp_stats_client.py` | PBP Stats API client (796 lines) |
| `utils/api_helpers.py` | Retry logic, circuit breaker (308 lines) |
| `utils/api_monitor.py` | Quota tracking, alerts (292 lines) |
| `module_a.py` | Gatekeeper (odds ingestion with fallback) |
| `docs/API_USAGE_AUDIT.md` | Full API inventory and cost analysis |

### External Resources

- [The-Odds-API Docs](https://the-odds-api.com/liveapi/guides/v4/)
- [BallDontLie API Docs](https://docs.balldontlie.io/)
- [PBP Stats API Docs](https://pbpstats.readthedocs.io/)
- [Tank01 API on RapidAPI](https://rapidapi.com/tank01/api/tank01-fantasy-stats)
- [Requests Library Docs](https://requests.readthedocs.io/)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-17 | Initial comprehensive guide based on Ludi-Bot lessons |

---

**This guide is a living document.** Update when you discover new patterns, gotchas, or best practices. The best API integration is one that fails loudly, degrades gracefully, and logs everything.

---

## 15. GitHub Actions API Patterns (CI/CD Best Practices)

**Extracted from:** `.github/workflows/` (18 production workflows)

### Pattern 1: Secret Injection via Environment Variables

```yaml
# ✅ Correct: Secrets injected at runtime, never in code
- name: Capture closing lines
  env:
    ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }}
    BALLDONTLIE_KEY: ${{ secrets.BALLDONTLIE_KEY }}
    ODDS_API_TIER: paid
    IS_SELF_HOSTED: 'true'
  run: |
    python3 scripts/capture_closing_lines.py --verbose
```

**Why this works:**
- Secrets are injected per-step (not workflow-level)
- `IS_SELF_HOSTED` flag tells `config.py` to skip `.env` loading
- Multiple API keys provided (primary + fallback)

### Pattern 2: Database Integrity Checks Before API Sync

```yaml
- name: Initialize database if needed
  run: |
    if [ ! -f ludi.db ]; then
      echo "⚠️ Database not found, initializing..."
      python3 database.py
    else
      INTEGRITY=$(sqlite3 ludi.db "PRAGMA integrity_check;" 2>&1)
      if [ "$INTEGRITY" != "ok" ]; then
        echo "⚠️ Database corrupted, reinitializing..."
        mv ludi.db ludi.db.corrupted.$(date +%Y%m%d_%H%M%S)
        python3 database.py
      fi
    fi
```

**Prevents:** Running API syncs into a corrupted database (data loss)

### Pattern 3: Automatic Deduplication Before Indexes

```yaml
- name: Ensure database indexes and data integrity
  run: |
    python3 -c "
    import sqlite3
    conn = sqlite3.connect('ludi.db')
    c = conn.cursor()
    
    # CRITICAL: Deduplicate FIRST (enables unique index creation)
    c.execute('''
        DELETE FROM player_game_logs
        WHERE rowid NOT IN (
            SELECT MIN(rowid)
            FROM player_game_logs
            GROUP BY game_id, player_id
        )
    ''')
    deduped = c.rowcount
    print(f'✅ Deduped {deduped} records')
    
    # NOW create UNIQUE index (would fail if dupes existed)
    c.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_player_game_logs_unique 
               ON player_game_logs(game_id, player_id)')
    conn.commit()
    "
```

**Why this matters:** UNIQUE indexes fail if duplicates exist. Dedup first, then index.

### Pattern 4: Granular Timeout Management

```yaml
jobs:
  sync-data:
    timeout-minutes: 60  # Workflow-level timeout
    
    steps:
      - name: Run Module H (Fetch recent games)
        timeout-minutes: 10  # Step-level timeout
        run: python3 scripts/sync_game_logs.py
      
      - name: Sync WOWY data
        timeout-minutes: 15  # Different timeout per step
        run: python3 scripts/sync_wowy_hybrid.py
```

**Benefits:**
- Prevents infinite hangs (1-hour max for entire workflow)
- Fast-fail on specific steps (10-min WOWY timeout)
- Different timeouts based on expected API latency

### Pattern 5: Multiple Scheduled Times for API Coverage

```yaml
on:
  schedule:
    - cron: '30 23,0,1,2,3 * * *'  # 7:30 PM, 8 PM, 9 PM, 10 PM, 11 PM EST
```

**Used for:** Closing line capture (CLV tracking)

**Why multiple times:**
- Games start at different times (7:30 PM - 10:30 PM ET)
- Need closing line 5-10 minutes before each game
- Single cron would miss some games

### Pattern 6: Telegram Failure Notifications

```yaml
- name: Notify on failure
  if: failure()
  env:
    TELEGRAM_TOKEN: ${{ secrets.TELEGRAM_TOKEN }}
    TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
  run: |
    python3 -c "from utils.telegram_notifier import send_message; 
                send_message('❌ WORKFLOW FAILED: ${{ github.workflow }}')" || 
    echo "Telegram notification failed"
```

**Critical addition:** The `|| echo` fallback prevents workflow failure if Telegram is down.

### Pattern 7: Workflow Dispatch with Optional Parameters

```yaml
on:
  schedule:
    - cron: '30 23 * * *'  # Automatic daily
  workflow_dispatch:        # Manual trigger option
    inputs:
      game_date:
        description: 'Game date to process (YYYY-MM-DD)'
        required: false
        type: string
```

**Usage in script:**
```yaml
run: |
  if [ -n "${{ github.event.inputs.game_date }}" ]; then
    python3 scripts/capture_closing_lines.py --game-date "${{ github.event.inputs.game_date }}"
  else
    python3 scripts/capture_closing_lines.py
  fi
```

**Enables:** Manual backfills for specific dates without editing code.

### Pattern 8: Reactive Failure Monitoring (Claude Ops Hub)

```yaml
on:
  workflow_run:
    workflows:
      - "Daily Data Sync"
      - "Daily Production Pipeline"
      - "Capture Closing Lines"
      # ... 14 total workflows monitored
    types:
      - completed

jobs:
  diagnose-failure:
    if: github.event.workflow_run.conclusion == 'failure'
    steps:
      - name: Fetch failure logs
        run: |
          gh run view ${{ github.event.workflow_run.id }} --log-failed | tail -300
      
      - name: Claude Ops Diagnosis
        uses: anthropics/claude-code-action@v1
        with:
          prompt: |
            Analyze this workflow failure and create a GitHub issue with:
            - Root cause analysis
            - Recommended fix
            - Priority level
```

**Result:** Automated diagnosis + GitHub issue creation on any workflow failure.

### Pattern 9: Clean: False for Database Persistence

```yaml
- name: Checkout repository
  uses: actions/checkout@v4
  with:
    clean: false  # CRITICAL: Preserve ludi.db between runs
```

**Without this:** `git clean -ffdx` deletes `ludi.db` on every run (lost 5,593 bets this way).

### Pattern 10: Cache Pip Dependencies

```yaml
- name: Cache pip
  uses: actions/cache@v4
  with:
    path: ~/Library/Caches/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-
```

**Speedup:** 60s install → 10s on cache hit.

---

## GitHub Actions API Integration Checklist

When adding a new API-calling workflow:

- [ ] **Set workflow timeout** (60 min recommended max)
- [ ] **Set step timeouts** (10-15 min per API step)
- [ ] **Inject secrets via env vars** (never hardcode)
- [ ] **Use `clean: false`** if workflow needs DB persistence
- [ ] **Add Telegram failure notification**
- [ ] **Add workflow_dispatch** for manual triggers
- [ ] **Check database integrity** before syncing
- [ ] **Deduplicate before creating UNIQUE indexes**
- [ ] **Use conditional parameters** for backfill support
- [ ] **Add to Claude Ops Hub monitoring** (if critical)
- [ ] **Cache pip dependencies** for faster runs
- [ ] **Multiple cron times** if needed for coverage

---

## Real Workflow Failures Documented

### 1. CLV Capture Failed Silently (Jan 30+)
**Problem:** `continue-on-error: true` masked 401 errors from Odds API quota exhaustion  
**Impact:** No CLV data for 5+ days, no alert  
**Fix:** Removed `continue-on-error`, added BDL fallback, added Telegram alerts

### 2. Database Backup Schedule Collision (Feb 15)
**Problem:** `db_backup.yml` ran at 9 AM UTC (same as `data_sync.yml`)  
**Impact:** SQLite lock errors, backup failures  
**Fix:** Moved backup to 6 AM UTC (1-hour separation)

### 3. Git Race Conditions (Jan 29)
**Problem:** Multiple workflows pushing simultaneously → git conflicts  
**Impact:** 15% workflow failure rate for 2 weeks  
**Fix:** Added `git pull --rebase` before every push

### 4. Workflow Passing Invalid CLI Args (Jan 28)
**Problem:** Workflow used `--production-mode` flag that didn't exist in `main.py`
**Impact:** Pipeline crashed immediately on every run
**Fix:** Replaced CLI flags with environment variables (`IS_PRODUCTION`)

### 5. BDL Milestone Market Leak → Phantom +269u P&L (Feb 20, 2026)
**Problem:** BDL has two prop market structures: `over_under` (correct) and `milestone` (achievement bet with single `odds` field). Code reading `over_odds`/`under_odds` from milestone markets got None/garbage (-2, -4, -9). Settlement formula `100/abs(-2) = 50x` per win.
**Impact:** Reported +269u profit on a day that was actually -41u. 167 bets affected.
**Fix:** `if prop.get('market', {}).get('type') != 'over_under': continue` + `if abs(over_odds) < 100: continue`

### 6. UPSERT Conflict Target Mismatch → 8 Days Silent Data Loss (Feb 19, 2026)
**Problem:** `module_h_historian.py` had `ON CONFLICT(game_id, player_id)` but actual unique constraint is `(player_id, game_date)`. No conflict was ever triggered — inserts appeared to succeed but either created duplicates or silently did nothing.
**Impact:** ALL player game log inserts failed silently for 8 days. Zero new data from Feb 12–19.
**Fix:** `ON CONFLICT(player_id, game_date)`. Always verify with `PRAGMA index_info(idx_name)` before writing ON CONFLICT clauses.

### 7. Single Population Path → Table Freezes When Primary API Fails (Feb 19, 2026)
**Problem:** `games` table had exactly ONE population path — Odds API scripts (`populate_todays_games.py`, `module_g.py`, `sync_daily_referees.py`). When Odds API returned 401 (quota), the table froze at Feb 12.
**Impact:** No game results → 1,947 bets unsettled. Settlement, scoring environment, and briefings all dependent on `games` table.
**Fix:** Added BDL fallback to `populate_todays_games.py`. Added Module H → games UPSERT bridge. Two independent population paths now exist.

### 8. BDL Props Coverage Is Not Full-Slate (Feb 19, 2026)
**Problem:** BDL's `/v2/odds/player_props` endpoint only returns props for games where sportsbooks have published lines. On a 10-game slate with BDL as fallback, only 3 games had props.
**Impact:** Pipeline covered only 30% of games. 7 games silently skipped (no warning in output).
**Fix:** Added explicit log when a game has no props: `print(f"No props for {matchup} — BDL coverage gap")`. Expected behavior, not a code bug — but must be surfaced clearly.

---

## 16. BallDontLie (BDL) Complete Endpoint Reference

**Last Updated:** February 20, 2026 | **Account tier required:** GOAT ($39.99/mo) for most endpoints
**Base URLs:** `https://api.balldontlie.io/v1/` | `https://api.balldontlie.io/nba/v1/` | `https://api.balldontlie.io/nba/v2/`
**Pagination:** Cursor-based. `meta.next_cursor` in response → pass as `?cursor=VALUE`. Max 100 per page.

---

### Games & Scores

| Endpoint | URL | Key Params | Notes |
|----------|-----|------------|-------|
| All Games | `GET /v1/games` | `dates[]`, `seasons[]`, `team_ids[]`, `start_date`, `end_date`, `postseason` | Status: "Final", "1st Qtr", "7:00 pm ET" |
| Single Game | `GET /v1/games/{id}` | — | Same shape as above |
| Live Box Scores | `GET /v1/box_scores/live` | none | Real-time, all games today |
| Historical Box Scores | `GET /v1/box_scores` | `date` (required, YYYY-MM-DD) | Completed games only |

**Box score per-player fields:** `min`, `pts`, `reb`, `ast`, `stl`, `blk`, `fgm/fga`, `fg3m/fg3a`, `ftm/fta`, `oreb`, `dreb`, `turnover`, `pf`, `plus_minus`

**Game status values:**
- Pre-game: `"7:00 pm ET"` (time string)
- In-progress: `"1st Qtr"`, `"Halftime"`, `"4th Qtr"`, etc.
- Complete: `"Final"`

**Note:** Quarter scores (`home_q1`-`q4`), bonus status, and timeouts only available for 2023 season+.

---

### Player Stats

| Endpoint | URL | Key Params | Notes |
|----------|-----|------------|-------|
| Game Stats | `GET /v1/stats` | `dates[]`, `seasons[]`, `player_ids[]`, `game_ids[]` | Per-game box scores |
| Advanced Stats V1 | `GET /nba/v1/stats/advanced` | `dates[]`, `player_ids[]`, `seasons[]`, `game_ids[]` | PIE, pace, usage%, ortg/drtg, reb%, ast% |
| Advanced Stats V2 | `GET /nba/v2/stats/advanced` | Same + `period` (0=game, 1-4=qtrs) | **EVERYTHING**: tracking, hustle, defensive matchup, four factors, scoring splits |
| Season Averages | `GET /v1/season_averages/{category}` | `season`, `season_type`, `type`, `player_ids[]` | Categories below |
| Leaders | `GET /v1/leaders` | `stat_type`, `season` | League leaders by any stat |

**Advanced Stats V2 — what's available (per-game or per-quarter):**
- Core: `usage_percentage`, `offensive_rating`, `defensive_rating`, `net_rating`, `pace`, `pie`, `true_shooting_percentage`
- Tracking: `speed`, `distance`, `touches`, `passes`, `contested_fg_pct`, `uncontested_fg_pct`
- Hustle: `box_outs`, `deflections`, `charges_drawn`, `contested_shots`, `loose_balls_recovered`, `screen_assists`
- Defensive matchup: `matchup_fg_pct`, `matchup_minutes`, `switches_on`, `partial_possessions`
- Four Factors: `efg_pct`, `free_throw_attempt_rate`, `team_turnover_pct` (and opponent versions)
- Scoring splits: paint points, fast break points, second-chance points, assisted/unassisted splits

**⚡ Strategic note:** BDL V2 Advanced Stats has tracking + hustle + defensive matchup DATA PER GAME. This could REPLACE Ghost Protocol (browser scraping from NBA.com) for most use cases. Much cleaner pipeline.

**Season Averages categories (`/v1/season_averages/{category}`):**
| Category | Available Types | Use Case |
|----------|----------------|----------|
| general | base, advanced, usage, scoring, defense, misc | Standard projections |
| playtype | isolation, postup, transition, spotup, handoff, cut, offscreen, roll_man, putback | **Synergy alternative** — cleaner API vs browser scrape |
| tracking | drives, passing, rebounding, speeddistance, catchshoot, pullups | Speed, distance, touches |
| shooting | 5ft_range, by_zone | Shot zone frequency + efficiency |
| clutch | base, advanced, misc, scoring, usage | Clutch-time stats |
| hustle | (no type) | Box outs, deflections, screen assists |
| shotdashboard | overall, pullups, catch_and_shoot, less_than_10_ft | Shot profile |

**⚡ Strategic note:** `playtype` category via `/v1/season_averages/playtype?type=isolation` returns the same data as NBA Synergy (ISO PPP, frequency%) via a clean API. Currently we scrape this from NBA.com with browser automation. This BDL endpoint is a much cleaner replacement.

---

### Betting / Odds

| Endpoint | URL | Key Params | Notes |
|----------|-----|------------|-------|
| Game Odds | `GET /v2/odds` | `dates[]` or `game_ids[]` (one required) | Spread, moneyline, total per book |
| Player Props | `GET /v2/odds/player_props` | `game_id` (required), `player_id`, `prop_type`, `vendors[]` | See critical patterns below |

**Player Props — CRITICAL PATTERNS:**
```python
for prop in props_data:
    market = prop.get('market', {})

    # 1. ALWAYS check market type first
    if market.get('type') != 'over_under':
        continue  # Skip milestone markets (single odds field, no over/under)
                  # Milestone example: "Will player score 30+ points?"

    over_odds = market.get('over_odds')
    under_odds = market.get('under_odds')

    # 2. Validate American odds range (must be abs >= 100)
    if not over_odds or not under_odds:
        continue
    if abs(over_odds) < 100 or abs(under_odds) < 100:
        print(f"[BDL] Corrupt odds: {over_odds}/{under_odds} — skipping")
        continue

    # 3. Process valid over/under prop
    process_prop(prop, over_odds, under_odds)
```

**Supported prop types:** `points`, `rebounds`, `assists`, `blocks`, `steals`, `threes`, `points_rebounds_assists`, `points_rebounds`, `points_assists`, `rebounds_assists`, `double_double`, `triple_double`, and quarter splits.

**Vendor quality tiers (add `vendors[]` filter to API request):**
- **Tier 1 (recommended):** `draftkings`, `fanduel`, `caesars`, `betmgm`, `betrivers`
- **Tier 2 (lower quality):** `ballybet`, `betparx`, `betway`, `fanatics`, `rebet`
- Best practice: filter to Tier 1 only to reduce alt-line noise

**Coverage note:** BDL props covers only games where sportsbooks publish lines. On a typical 10-game slate, expect 3–7 games covered. Log a warning for games with no props — do not silently skip.

---

### Team Stats

| Endpoint | URL | Key Params | Notes |
|----------|-----|------------|-------|
| Team Season Averages | `GET /nba/v1/team_season_averages/{category}` | `season`, `season_type`, `type`, `team_ids[]` | Same categories as player; adds opponent + violations |
| Standings | `GET /v1/standings` | `season` | Win/loss, conference rank |

**Team Season Averages unique additions:**
- `general/opponent` — opponent defensive stats (useful for scheme detection)
- `general/violations` — intentional fouls, violations data
- Includes W/L record alongside traditional stats

---

### Roster / Player Data

| Endpoint | URL | Key Params | Notes |
|----------|-----|------------|-------|
| Player Injuries | `GET /v1/player_injuries` | `player_ids[]`, `team_ids[]` | Returns status, description, return_date |
| Active Players | `GET /v1/players/active` | `cursor`, `per_page` | Current-season roster |
| All Players | `GET /v1/players` | `search`, `player_ids[]` | Historical + current |
| Player Contracts | `GET /v1/contracts/players` | `player_id` | Cap hit, base salary, total cash |
| Team Contracts | `GET /v1/contracts/teams` | `team_id`, `season` | Full team salary breakdown |

**Player Injuries fields:** `status` (Out/Doubtful/Questionable/Probable), `description` (narrative with date), `return_date` (e.g., "Nov 17"). Tier: ALL-STAR+.

---

### Play-by-Play

| Endpoint | URL | Key Params | Notes |
|----------|-----|------------|-------|
| Plays | `GET /v1/plays` | `game_id` (required) | Court coords, period, clock, shot type, score |

**PBP fields:** `type`, `text`, `period`, `clock`, `coordinate_x/y`, `scoring_play`, `shooting_play`, `score_value`, `wallclock`. 2025 season+ only. No pagination.

---

### Pagination Pattern (applies to all paginated endpoints)

```python
def get_all_pages(client, url, params):
    """Iterate all BDL pages using cursor-based pagination."""
    results = []
    cursor = None

    while True:
        if cursor:
            params['cursor'] = cursor
        params['per_page'] = 100  # Always use max

        response = client._get(url, params)
        data = response.get('data', [])
        results.extend(data)

        next_cursor = response.get('meta', {}).get('next_cursor')
        if not next_cursor:
            break  # No more pages
        cursor = next_cursor

    return results
```

**Note:** Some endpoints (plays, live box scores, leaders) have no pagination — all data in single response.

---

### BDL Tier Requirements Summary

| Tier | Cost | Endpoints Available |
|------|------|-------------------|
| Free | $0 | Basic player/game/stats (limited) |
| ALL-STAR | $? | Player injuries, most stats |
| GOAT | $39.99/mo | ALL endpoints: odds, props, advanced stats, contracts, plays, lineups, season averages |

We are on GOAT tier — all endpoints available.

---

## Summary: GitHub Actions as API Orchestration Layer

GitHub Actions workflows are effectively **API orchestration** — they:
- ✅ Manage secrets (inject API keys per-step)
- ✅ Handle timeouts (workflow + step level)
- ✅ Coordinate multiple APIs (data_sync calls 5+ APIs)
- ✅ Monitor failures (Telegram + Claude Ops Hub)
- ✅ Enable manual triggers (workflow_dispatch)
- ✅ Preserve state (clean: false, database persistence)
- ✅ Deduplicate data (before creating UNIQUE indexes)

**Key Lesson:** Treat workflows as part of your API reliability stack, not just deployment automation.

