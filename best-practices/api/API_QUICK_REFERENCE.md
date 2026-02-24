# API Best Practices — Quick Reference

**One-page cheatsheet for the comprehensive guide**
**See:** `docs/API_BEST_PRACTICES.md` for full details

---

## The Golden Rules

1. **Never fail silently** — Always log errors before `continue`
2. **Always have a fallback** — Primary → Secondary → Cache → Fail loudly
3. **Track your quota** — Monitor at 80%, alert at 95%
4. **Cache aggressively** — TTL-based, deterministic keys
5. **Retry intelligently** — Exponential backoff, max 3 attempts
6. **Fail loudly** — Errors should wake you up, not hide for weeks

---

## Critical Anti-Patterns

| ❌ Anti-Pattern | ✅ Correct Pattern |
|----------------|-------------------|
| `except: continue` | `except as e: print(f"Error: {e}"); continue` |
| `ODDS_API_KEY = "abc123"` | `ODDS_API_KEY = os.getenv('ODDS_API_KEY')` |
| No rate limiting | `time.sleep(0.1)` between requests |
| No cache expiration | TTL check before reading cache |
| Single API source | Primary + Fallback + Cache |
| Ignore HTTP status | `response.raise_for_status()` |
| Burn quota on tests | Mock responses or cached test data |

---

## Authentication Template

```python
# config.py
import os
from dotenv import load_dotenv

# Conditional loading (CI/CD uses injected secrets)
if not os.getenv('IS_SELF_HOSTED'):
    load_dotenv()

API_KEY = os.getenv('API_KEY')

def validate_config():
    if not API_KEY:
        raise ValueError("Missing API_KEY in .env")
```

---

## Rate Limiting Template

```python
class APIClient:
    def __init__(self):
        self.last_request_time = 0
        self.min_interval = 0.1  # 10 req/sec

    def _wait_for_rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()
```

---

## Caching Template

```python
import hashlib, json, os
from datetime import datetime, timedelta

def _get_cache_path(endpoint: str, params: dict) -> str:
    key = endpoint + json.dumps(params, sort_keys=True)
    digest = hashlib.md5(key.encode()).hexdigest()[:12]
    return f"cache/{endpoint}_{digest}.json"

def _read_cache(path: str, ttl_hours: float = 24) -> dict:
    if not os.path.exists(path):
        return None
    age = (time.time() - os.path.getmtime(path)) / 3600
    if age > ttl_hours:
        return None
    with open(path) as f:
        return json.load(f)

def _write_cache(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f)
```

---

## Retry Template

```python
def retry_with_backoff(max_attempts=3, backoff=2.0):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except requests.HTTPError as e:
                    if e.response.status_code == 429:
                        wait = backoff * (2 ** attempt)
                        time.sleep(wait)
                    else:
                        raise
            raise Exception(f"Failed after {max_attempts} attempts")
        return wrapper
    return decorator
```

---

## Error Handling Template

```python
def _get(self, url: str, params: dict) -> dict:
    try:
        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            print("❌ AUTH ERROR: Check API key")
        elif e.response.status_code == 429:
            print("⚠️ RATE LIMIT: Slow down")
        elif e.response.status_code >= 500:
            print("⚠️ SERVER ERROR: Retry later")
        return {}
    except requests.RequestException as e:
        print(f"❌ CONNECTION ERROR: {e}")
        return {}
```

---

## Fallback Template

```python
def get_data_with_fallback():
    # Try primary
    try:
        return primary_api.fetch()
    except Exception as e:
        print(f"⚠️ Primary failed: {e}")

    # Try secondary
    try:
        return secondary_api.fetch()
    except Exception as e:
        print(f"⚠️ Secondary failed: {e}")

    # Use stale cache
    cached = read_stale_cache()
    if cached:
        print("⚠️ Using stale cache")
        return cached

    # Fail loudly
    raise Exception("All sources failed")
```

---

## Monitoring Template

```python
class APIMonitor:
    def log_request(self, api_name: str, headers: dict):
        remaining = headers.get('x-requests-remaining')
        print(f"📊 {api_name}: {remaining} credits remaining")

        if int(remaining) < 0.2 * QUOTA_LIMIT:
            send_telegram_alert(f"⚠️ {api_name} at 80% quota")
```

---

## Team Code Normalization

```python
TEAM_NORMALIZER = {
    'GS': 'GSW',   # BDL → Standard
    'NO': 'NOP',
    'NY': 'NYK',
    'PHO': 'PHX',
    'SA': 'SAS',
}

def normalize_team(code: str) -> str:
    return TEAM_NORMALIZER.get(code, code)
```

---

## Cache TTL Guidelines

| Data Type | TTL | Reasoning |
|-----------|-----|-----------|
| Injury reports | 15 min | NBA rule: 15 min before tipoff |
| Live odds | 30 min | Rapid line movement |
| Season averages | 24 hours | Changes daily at most |
| Historical stats | 30 days | Immutable once finalized |
| Player rosters | 1 hour | Trade deadline flux |

---

## HTTP Status Code Actions

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Return data |
| 401 | Unauthorized | Check API key, DON'T RETRY |
| 403 | Forbidden | Check permissions, DON'T RETRY |
| 429 | Rate limit | Sleep 2x longer, RETRY |
| 500+ | Server error | Exponential backoff, RETRY |
| Timeout | Network issue | Retry with longer timeout |

---

## Ludi-Bot Real Failures & Fixes

### Silent Failure (21-day bug)
```python
# ❌ Bug hid for 21 days
except Exception:
    continue

# ✅ Fix
except Exception as e:
    print(f"Row error: {e}")
    continue
```

### Quota Exhaustion (5-day outage)
```python
# ❌ No monitoring
response = requests.get(url)

# ✅ Fix
response = requests.get(url)
monitor.log_request('odds_api', response.headers)
monitor.check_quota_threshold('odds_api')
```

### ID Format Change (Pipeline failure)
```python
# ❌ Assumed stable IDs
player_id = api_response['id']  # Changed from "1629029" to "28398804489"

# ✅ Fix: Canonical ID mapping
canonical_id = resolve_to_nba_id(api_response['id'], api_response['name'])
```

### BDL Milestone Market → Phantom P&L (Feb 2026)
```python
# ❌ Reading over_odds from milestone market → gets -2, -4, -9
# 100/abs(-2) = 50x payout. Reported +269u when actual = -41u.
over_odds = market.get('over_odds')  # None or garbage on milestone market

# ✅ Fix: Always check market type first
if market.get('type') != 'over_under': continue
if abs(over_odds) < 100 or abs(under_odds) < 100: continue
```

### UPSERT Conflict Target Mismatch (8 days data loss, Feb 2026)
```python
# ❌ Wrong conflict target — inserts silently fail for 8 days
ON CONFLICT(game_id, player_id) ...  # actual unique key is (player_id, game_date)

# ✅ Fix: verify with PRAGMA index_info(idx_name) before writing ON CONFLICT
ON CONFLICT(player_id, game_date) DO UPDATE SET pts = excluded.pts
```

### Single API Population Path → Table Frozen When API Down (Feb 2026)
- `games` table had ONE path: Odds API. When quota hit, table froze for 8 days.
- Fix: Add BDL/Tank01 fallback. Any critical table needs ≥ 2 independent population paths.

### CLV Quota Graceful Exit (Feb 2026) — New Pattern
```python
# ❌ exit(1) on expected monthly quota exhaustion → false Ops Hub alerts
if total_updated == 0 and len(pending_bets) > 0:
    sys.exit(1)  # Fires even when quota=0 is a known monthly state

# ✅ Distinguish expected noise from real failures at the exit point
if total_updated == 0 and len(pending_bets) > 0:
    if _read_cached_quota() == "0":
        print("Odds API quota exhausted (expected monthly event) — exiting cleanly.")
        sys.exit(0)  # Known state — not an ops-hub alert
    sys.exit(1)  # Genuine failure — alert
```
**Rule:** Apply `exit(0)` checks for every known, expected state before `exit(1)`. Monthly quota exhaustion = expected noise. Real data fetch failures = genuine failure.

### Live Game Filtering for Odds API (Feb 2026)
```python
# ❌ Odds API matched games by team name only — live games served in-game odds
matched_events = [ev for ev in events_data if teams_match(ev)]

# ✅ Filter by commence_time — reject live games and future-date games
def _game_is_on_slate(ev, game_date):
    ct = ev.get('commence_time', '')
    if not ct: return True
    game_utc = datetime.fromisoformat(ct.replace('Z', '+00:00'))
    game_est_date = game_utc.astimezone(EST).strftime('%Y-%m-%d')
    if game_est_date != game_date: return False       # wrong date
    if game_utc < datetime.now(timezone.utc) - timedelta(minutes=15): return False  # live
    return True

matched_events = [ev for ev in events_data if teams_match(ev) and _game_is_on_slate(ev, game_date)]
```

---

## Pre-Integration Checklist

- [ ] Test API in browser/Postman first
- [ ] Understand quota limits and pricing
- [ ] Add API key to `.env` (gitignored)
- [ ] Implement rate limiting
- [ ] Add caching with TTL
- [ ] Add retry logic
- [ ] Add fallback source
- [ ] Add monitoring/alerts
- [ ] Write integration test
- [ ] Document in API_USAGE_AUDIT.md

---

---

## BDL Quick Reference (GOAT Tier, Feb 2026)

| What | Endpoint | Key Params |
|------|----------|------------|
| Games | `GET /v1/games` | `dates[]`, `team_ids[]`, `start_date`/`end_date` |
| Box scores (live) | `GET /v1/box_scores/live` | none |
| Box scores (historical) | `GET /v1/box_scores` | `date` (required) |
| Player game stats | `GET /v1/stats` | `dates[]`, `player_ids[]`, `game_ids[]` |
| Advanced stats (V2) | `GET /nba/v2/stats/advanced` | `dates[]`, `player_ids[]`, `period` (0-4) |
| Season averages (general) | `GET /v1/season_averages/general?type=base` | `season`, `season_type`, `player_ids[]` |
| **Season averages (playtype)** | `GET /v1/season_averages/playtype?type=isolation` | — replaces Synergy scraping |
| **Season averages (tracking)** | `GET /v1/season_averages/tracking?type=drives` | — replaces Ghost Protocol |
| Team season averages | `GET /nba/v1/team_season_averages/general?type=opponent` | Defensive stats |
| Game odds | `GET /v2/odds` | `dates[]` or `game_ids[]` (one required) |
| **Player props** | `GET /v2/odds/player_props` | `game_id` (required), `vendors[]`, `prop_type` |
| Player injuries | `GET /v1/player_injuries` | `player_ids[]`, `team_ids[]` |
| Leaders | `GET /v1/leaders` | `stat_type`, `season` |
| Plays (PBP) | `GET /v1/plays` | `game_id` (required) |

**Props must-do:**
1. `if market.get('type') != 'over_under': continue` — skip milestone markets
2. `if abs(over_odds) < 100: continue` — skip corrupt/truncated odds
3. Add `vendors[]=['draftkings','fanduel','caesars']` to filter low-quality books

**Pagination:** `meta.next_cursor` → pass as `?cursor=VALUE`. Always `per_page=100`.

**⚡ Strategic opportunities:**
- `/v1/season_averages/playtype` = Synergy data via clean API (replace NBA.com scraping)
- `/nba/v2/stats/advanced` = tracking + hustle + defensive matchup per game (replace Ghost Protocol)

---

## Remember

> "The best API integration is one that fails loudly, degrades gracefully, and logs everything."

**Full guide:** `best-practices/api/API_BEST_PRACTICES.md`
