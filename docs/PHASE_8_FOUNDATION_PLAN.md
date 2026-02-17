# Phase 8 Foundation: Injury + Rotation Intelligence Systems

**Status:** 📋 PLANNED (awaiting Phase 7.9.5 completion)
**Priority:** CRITICAL (blocking Phase 8.1+ AI integration)
**Related:** See `ROADMAP.md` Phase 8.0

---

## Executive Summary

This document outlines the implementation plan for Phase 8.0 Foundation: two data intelligence systems that create rich context for AI-enhanced pipeline work (Phase 8.1+):

1. **Injury Intelligence** — Persistent tracking of injury status, return dates, severity, descriptions
2. **Rotation Intelligence** — Minute-by-minute rotation patterns, coach tendencies, situational minutes modeling

Both systems address critical gaps:
- **Injury:** 19 players with no game logs → defaulting to GENERALIST (31.4%, target <25%)
- **Rotation:** Naive minutes projection (simple averages) → missing situational adjustments (blowouts, B2B, lineups)

---

## Part A: Injury Intelligence System

### Problem Statement

**Current State:**
- Injuries are in-memory only (`yak_cache.json`, 15-min TTL)
- No persistence, no history, no audit trail
- Long-term injured players (30+ days) silently disappear from pipeline
- BDL `return_date` and `description` (rich metadata) are fetched but discarded
- No distinction between injury vs data gap

**Impact:**
- Can't tell if Damian Lillard has no logs because he's injured or sync failure
- No way to track "how long has player X been out?"
- Can't forecast "welcome back" value plays for returning stars
- Process restart loses all injury state

### Solution: Persistent Injury Tracking

#### Database Schema

**New table: `player_injuries`**
```sql
CREATE TABLE player_injuries (
    player_name TEXT NOT NULL,
    team_abbreviation TEXT,
    status TEXT NOT NULL,  -- OUT, DOUBTFUL, QUESTIONABLE, PROBABLE, ACTIVE
    injury_type TEXT,      -- "Ankle sprain", "Knee soreness", etc.
    return_date TEXT,      -- YYYY-MM-DD or NULL
    days_out INTEGER,      -- Calculated from onset_date to return_date
    onset_date TEXT,       -- When injury first reported
    description TEXT,      -- Full BDL narrative paragraph (50-200 words)
    source TEXT,           -- 'BDL', 'Tank01', 'RotoWire'
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,      -- When player returned to ACTIVE
    PRIMARY KEY (player_name, onset_date)
);

CREATE INDEX idx_injuries_current ON player_injuries(player_name, resolved_at);
CREATE INDEX idx_injuries_status ON player_injuries(status, return_date);
```

**Enhance `players` table:**
```sql
ALTER TABLE players ADD COLUMN current_injury_status TEXT DEFAULT 'ACTIVE';
ALTER TABLE players ADD COLUMN days_out_current INTEGER DEFAULT 0;
ALTER TABLE players ADD COLUMN injury_return_date TEXT;
```

#### Module D Enhancement

**File:** `module_d.py` (lines 139-154)

**Current:** Only extracts injury status
**After:** Extract all BDL metadata

```python
# AFTER: Extract all fields
for entry in data['body']:
    p = entry.get('player', {})
    injury_record = {
        'player_name': f"{p.get('first_name')} {p.get('last_name')}",
        'team_abbreviation': self._resolve_team(p.get('team', {})),
        'status': self._normalize_status(entry.get('status')),
        'injury_type': self._extract_injury_type(entry.get('description', '')),
        'return_date': entry.get('return_date'),
        'description': entry.get('description', ''),
        'onset_date': self._infer_onset_date(existing_record, entry),
        'source': 'BDL'
    }
    self._persist_injury(injury_record)
```

**New helper methods needed:**
- `_extract_injury_type(description)` — Parse "ankle sprain" from description
- `_infer_onset_date(existing, new)` — Use DB history to set onset if new injury
- `_persist_injury(record)` — Write to `player_injuries` table
- `_calculate_days_out(onset, return_date)` — Compute duration

#### Pipeline Integration

**File:** `main.py` (lines 80-96)

**Problem:** `get_active_roster()` kills long-term injured players

**Current filter:**
```python
WHERE pgl.game_date >= date('now', '-30 days')
HAVING COUNT(pgl.player_id) >= 3  -- Eliminates Lillard, Tatum, etc.
```

**Proposed fix — Three-tier roster:**
```python
# Tier 1: Active players (recent logs)
active_roster = db.query("""
    SELECT ... FROM player_game_logs
    WHERE game_date >= date('now', '-30 days')
    HAVING COUNT >= 3
""")

# Tier 2: Recently returned players (check injuries table)
recently_returned = db.query("""
    SELECT DISTINCT p.name, p.team, p.position, p.archetype
    FROM players p
    JOIN player_injuries i ON p.name = i.player_name
    WHERE i.status = 'ACTIVE'
      AND i.resolved_at >= date('now', '-7 days')  -- Returned in last 7 days
      AND p.name NOT IN (SELECT player_name FROM active_roster)
""")

# Tier 3: Long-term injured (track but skip simulation)
long_term_out = db.query("""
    SELECT player_name, status, days_out, return_date
    FROM player_injuries
    WHERE status IN ('OUT', 'DOUBTFUL')
      AND (days_out > 14 OR return_date > date('now', '+14 days'))
""")

final_roster = active_roster + recently_returned
# Log long_term_out players to explain why they have no recommendations
```

#### Daily Sync Script

**Create:** `scripts/sync_injuries.py`

**Purpose:** Run as part of `data_sync.yml` (5 AM EST) to populate injury table daily

**Logic:**
```python
def sync_injuries():
    # 1. Fetch from BDL (primary)
    bdl_injuries = bdl_client.get_active_injuries()

    # 2. Fetch from Tank01 (fallback)
    tank01_injuries = fetch_tank01_injuries()

    # 3. Merge (BDL takes priority)
    merged = merge_injury_sources(bdl_injuries, tank01_injuries)

    # 4. For each injury:
    for inj in merged:
        existing = db.query("SELECT * FROM player_injuries WHERE player_name = ? AND resolved_at IS NULL", inj['player_name'])

        if existing and inj['status'] == 'ACTIVE':
            # Player returned — mark as resolved
            db.execute("UPDATE player_injuries SET resolved_at = CURRENT_TIMESTAMP WHERE ...")
        elif not existing and inj['status'] != 'ACTIVE':
            # New injury — insert
            db.execute("INSERT INTO player_injuries (...) VALUES (...)")
        else:
            # Existing injury — update (e.g., status changed or return_date updated)
            db.execute("UPDATE player_injuries SET status = ?, return_date = ?, ... WHERE ...")

    # 5. Update players.current_injury_status
    db.execute("""
        UPDATE players SET
            current_injury_status = (SELECT status FROM player_injuries WHERE player_name = players.name AND resolved_at IS NULL),
            days_out_current = (SELECT days_out FROM player_injuries WHERE player_name = players.name AND resolved_at IS NULL),
            injury_return_date = (SELECT return_date FROM player_injuries WHERE player_name = players.name AND resolved_at IS NULL)
    """)
```

**Add to `.github/workflows/data_sync.yml`:**
```yaml
- name: Sync Injuries
  run: |
    source .venv/bin/activate
    python scripts/sync_injuries.py
```

#### Verification

**Query: Long-term injured players**
```sql
SELECT player_name, status, days_out, return_date, injury_type
FROM player_injuries
WHERE status IN ('OUT', 'DOUBTFUL')
  AND resolved_at IS NULL
ORDER BY days_out DESC;
```

**Query: Recent returns**
```sql
SELECT player_name, status, onset_date, resolved_at, days_out
FROM player_injuries
WHERE resolved_at >= date('now', '-7 days')
ORDER BY resolved_at DESC;
```

**Add to daily briefing Telegram:**
```
🏥 INJURY INTEL
━━━━━━━━━━━━━━━
Long-term OUT: Damian Lillard (DAL) - 42 days, return Feb 25
Recently returned: Jayson Tatum (BOS) - returned Feb 16 after 12 days
```

---

## Part B: Rotation Intelligence System

### Problem Statement

**Current State:**
- Minutes projection = `AVG(minutes)` from recent games (naive scalar)
- No rotation pattern modeling (when players check in/out, stint lengths)
- No situational adjustments (blowouts, close games, B2B rest management)
- No lineup-based minutes (some players get more run in specific combinations)
- No coach tendency modeling (rigid rotations vs dynamic adjustments)

**Impact:**
- Minutes are foundation for ALL volume stats (FGA, FTA, REB, AST)
- If minutes are wrong, everything downstream is wrong
- Missing huge edges: garbage time boost for bench, close game extension for starters, B2B rest

**Research:**
- StraightBettin.com and PopcornMachine.net track minute-by-minute rotation timelines
- Per-stint performance (points, +/-, fouls per rotation stint)
- Lineup analytics (which 5-man units are most effective)
- Data is publicly available via NBA play-by-play feeds

### Solution: Rotation Pattern Tracking

#### Database Schema

**New table: `player_rotation_patterns`**
```sql
CREATE TABLE player_rotation_patterns (
    player_name TEXT NOT NULL,
    team_abbreviation TEXT,
    game_id TEXT,
    game_date TEXT,
    stint_number INTEGER,          -- 1st, 2nd, 3rd rotation stint
    check_in_time TEXT,            -- Game clock when checked in (e.g., "11:45 Q1")
    check_out_time TEXT,           -- Game clock when checked out
    stint_duration_minutes REAL,   -- Actual minutes played in stint
    stint_points INTEGER,          -- Points scored in this stint
    stint_plus_minus INTEGER,      -- +/- for this stint
    stint_fouls INTEGER,           -- Fouls in this stint
    lineup_id TEXT,                -- 5-player lineup hash for this stint
    PRIMARY KEY (game_id, player_name, stint_number)
);

CREATE INDEX idx_rotation_player_recent ON player_rotation_patterns(player_name, game_date DESC);
CREATE INDEX idx_rotation_lineup ON player_rotation_patterns(lineup_id, stint_plus_minus);
```

**New table: `coach_rotation_tendencies`**
```sql
CREATE TABLE coach_rotation_tendencies (
    team_abbreviation TEXT NOT NULL,
    season TEXT NOT NULL,
    avg_starter_first_rest TEXT,      -- When starters typically check out (e.g., "6:00 Q1")
    avg_stint_length_minutes REAL,    -- Average stint duration
    rotation_depth INTEGER,            -- How many players get meaningful minutes
    blowout_threshold INTEGER,         -- Spread at which coach pulls starters
    close_game_extension_minutes REAL, -- Extra minutes for starters in close games
    b2b_rest_reduction_pct REAL,      -- % reduction in starter minutes on B2B
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (team_abbreviation, season)
);
```

#### PBP Parsing Script

**Create:** `scripts/sync_rotation_patterns.py`

**Purpose:** Parse NBA play-by-play data to extract check-in/check-out times

**Data Sources (Research-Backed):**

Based on research from:
- `nba_api` (Python wrapper for NBA.com official stats)
- `lbiedma/nba-stats-analysis` (example implementations)
- SportAnalytics.com free data sources

**Recommended Approach:**
1. **`nba_api` PlayByPlayV3 endpoint** (Primary) ✅ **IMPLEMENTED in utils/nba_api_client.py**
   - Official NBA.com wrapper (v1.11.3)
   - Free, comprehensive PBP data
   - Includes substitution events with timestamps
   - **CRITICAL:** Must include `league_id="00"` parameter (2023-24+ requirement)
   - Example: `playbyplayv3.PlayByPlayV3(game_id='0022100001', league_id="00")`
   - **Available method:** `client.get_play_by_play(game_id)`

2. **BallDontLie PBP endpoint** (Fallback)
   - GOAT tier subscription ($39.99/mo)
   - May have cleaner PBP format

3. **Estimate from existing `player_game_logs`** (Last resort)
   - Use total minutes to infer approximate stints
   - Less accurate but always available

**Best Practices (from research):**
- **Rate limiting:** Retry logic with 30s sleep between attempts (up to 5 retries)
- **Batch processing:** Don't fetch all games at once, process incrementally
- **Caching:** Store raw PBP responses locally to avoid re-fetching
- **Pandas DataFrames:** Use for data manipulation and aggregation

**Logic (with best practices):**
```python
from utils.nba_api_client import get_nba_client

def parse_rotation_data(game_id):
    # 1. Fetch play-by-play data using our client wrapper
    client = get_nba_client()
    pbp_response = client.get_play_by_play(game_id)

    if not pbp_response:
        print(f"Failed to fetch PBP for {game_id}")
        return None

    # 2. Extract play-by-play events
    pbp_data = pbp_response.get('PlayByPlay', [])

    # 3. Identify substitution events (EVENTMSGTYPE == 8)
    subs = [e for e in pbp_data if e.get('EVENTMSGTYPE') == 8]

    # 4. Build stint timeline for each player
    # ... (rest of implementation)
        player_in = sub['PLAYER1_NAME']
        player_out = sub['PLAYER2_NAME']
        game_clock = sub['PCTIMESTRING']

        # Track check-in time
        if player_in not in player_stints:
            player_stints[player_in] = []
        player_stints[player_in].append({'check_in': game_clock})

        # Track check-out time
        if player_out in player_stints and player_stints[player_out]:
            player_stints[player_out][-1]['check_out'] = game_clock

    # 4. Calculate stint-level stats (points, +/-, fouls)
    for player, stints in player_stints.items():
        for i, stint in enumerate(stints):
            stint['stint_number'] = i + 1
            stint['stats'] = calculate_stint_stats(player, stint['check_in'], stint['check_out'], pbp_data)

    # 5. Persist to database
    save_rotation_patterns(player_stints, game_id)
```

#### Coach Tendency Analyzer

**Create:** `scripts/analyze_rotation_tendencies.py`

**Purpose:** Aggregate rotation patterns to identify coach tendencies

**Logic:**
```python
def analyze_coach_tendencies(team, season):
    # 1. Get all rotation patterns for team
    patterns = db.query("""
        SELECT * FROM player_rotation_patterns
        WHERE team_abbreviation = ? AND game_date >= ?
    """, team, season_start_date)

    # 2. Calculate averages
    avg_first_rest = median([p['check_out_time'] for p in patterns if p['stint_number'] == 1])
    avg_stint_length = mean([p['stint_duration_minutes'] for p in patterns])
    rotation_depth = len(set([p['player_name'] for p in patterns if p['stint_duration_minutes'] > 10]))

    # 3. Blowout analysis
    blowout_games = get_blowout_games(team, season)
    blowout_threshold = median([g['spread'] for g in blowout_games if starter_minutes_reduced(g)])

    # 4. Save tendencies
    db.upsert_coach_tendencies(team, season, {
        'avg_starter_first_rest': avg_first_rest,
        'avg_stint_length': avg_stint_length,
        'rotation_depth': rotation_depth,
        'blowout_threshold': blowout_threshold
    })
```

#### Module C Integration

**File:** `module_c.py` (line ~220)

**Current:** Naive minutes
```python
"MIN": round(player.get('MIN', 0), 1)
```

**After:** Situational minutes projection
```python
def _project_situational_minutes(player, scenario):
    """
    Project minutes based on game situation, coach tendencies, and rotation patterns.
    """
    # Base minutes from recent games
    base_minutes = player.get('MIN', 0)

    # Get coach tendencies
    team = player['TEAM_ABBREVIATION']
    tendencies = get_coach_tendencies(team)

    # Situational adjustments
    adjusted_minutes = base_minutes

    # 1. Blowout tax
    if abs(scenario['spread']) > tendencies['blowout_threshold']:
        if player['is_starter']:
            adjusted_minutes *= 0.85  # Starters sit early
        else:
            adjusted_minutes *= 1.15  # Bench gets garbage time

    # 2. Close game boost
    if abs(scenario['spread']) < 3.0 and player['is_starter']:
        adjusted_minutes *= 1.08  # Starters play more in close games

    # 3. B2B rest management
    if scenario.get('b2b') and player['is_starter']:
        reduction = tendencies['b2b_rest_reduction_pct']
        adjusted_minutes *= (1 - reduction)

    # 4. Injury-driven rotation chaos
    if scenario.get('injured_players'):
        # Check if this player is beneficiary of injury
        beneficiary_minutes = calculate_beneficiary_boost(player, scenario['injured_players'])
        adjusted_minutes += beneficiary_minutes

    return round(adjusted_minutes, 1)

"MIN": _project_situational_minutes(player, scenario)
```

#### Daily Sync Script

**Create:** `scripts/sync_daily_rotations.py`

**Purpose:** Run after each game day to populate rotation patterns

**Add to `.github/workflows/data_sync.yml`:**
```yaml
- name: Sync Rotation Patterns
  run: |
    source .venv/bin/activate
    python scripts/sync_rotation_patterns.py --yesterday
    python scripts/analyze_rotation_tendencies.py --all-teams
```

#### Verification

**Query: Rotation patterns**
```sql
-- Top players by stint efficiency
SELECT player_name, AVG(stint_plus_minus) as avg_stint_pm, COUNT(*) as stints
FROM player_rotation_patterns
WHERE game_date >= date('now', '-30 days')
GROUP BY player_name
ORDER BY avg_stint_pm DESC
LIMIT 20;
```

**Query: Coach tendencies**
```sql
SELECT team_abbreviation, avg_stint_length, rotation_depth, blowout_threshold
FROM coach_rotation_tendencies
WHERE season = '2025-26';
```

---

## Critical Files

| File | Changes | Part |
|------|---------|------|
| `database.py` | Add `player_injuries`, `player_rotation_patterns`, `coach_rotation_tendencies` tables | Both |
| `module_d.py` | Extract BDL injury metadata, persist to DB | A |
| `module_c.py` | Replace naive MIN with `_project_situational_minutes()` | B |
| `main.py` | Fix `get_active_roster()` for long-term injuries + recently returned | A |
| `scripts/sync_injuries.py` | NEW — daily injury sync | A |
| `scripts/sync_rotation_patterns.py` | NEW — parse PBP for rotation data | B |
| `scripts/analyze_rotation_tendencies.py` | NEW — aggregate coach patterns | B |
| `.github/workflows/data_sync.yml` | Add injury + rotation sync steps | Both |
| `requirements.txt` | `nba_api==1.11.3` already installed, add `league_id="00"` to all endpoints | B |

---

## Implementation Order (Recommended)

**Part A first (Injury Intelligence):**
1. Database schema (injuries table) — `database.py`
2. Module D enhancement (persist BDL data) — `module_d.py`
3. Pipeline integration (roster fixes) — `main.py`
4. Sync script + workflow — `scripts/sync_injuries.py`, `data_sync.yml`

**Part B second (Rotation Intelligence):**
5. ~~Install `nba_api`~~ ✅ Already installed (v1.11.3) — verify league_id parameter added
6. Database schema (rotation tables) — `database.py`
7. PBP parsing script — `scripts/sync_rotation_patterns.py` using PlayByPlayV3 endpoint
8. Coach tendency analyzer — `scripts/analyze_rotation_tendencies.py`
9. Module C integration — `module_c.py`
10. Sync script + workflow — `data_sync.yml`

**Rationale:** Injury system is **CRITICAL** (blocking archetype cleanup). Rotation system is **HIGH PRIORITY** but not blocking. Build injury foundation first, then layer rotation intelligence on top.

---

## Acceptance Criteria

### Injury Intelligence
- [ ] `player_injuries` table exists with 10+ rows
- [ ] Damian Lillard shows as OUT with `days_out > 30` and `return_date` populated
- [ ] `players.current_injury_status` synced for all injured players
- [ ] `get_active_roster()` logs dropped players with injury reasons
- [ ] Jayson Tatum (recently returned) appears in Tier 2 roster even if <3 games in 30 days
- [ ] BDL `description` field stored in database (not discarded)
- [ ] Run dry run: Pipeline generates bets for recently returned players
- [ ] No NULLs in `player_injuries.status`
- [ ] GENERALIST count drops below 25% (currently 31.4%)
- [ ] Phase 8.1 ready (injury descriptions stored for Claude input)

### Rotation Intelligence
- [ ] `nba_api` package installed and tested
- [ ] `player_rotation_patterns` table populated with 100+ recent games
- [ ] Stint-level data captured (check-in/out times, stint +/-)
- [ ] Coach tendencies calculated for all 30 teams
- [ ] Situational minutes projection implemented in Module C
- [ ] Minutes projections more accurate (measure RMSE before/after on 30-day sample)
- [ ] Blowout scenarios correctly reduce starter minutes by ~15%
- [ ] Close game scenarios correctly boost starter minutes by ~8%
- [ ] B2B scenarios correctly reduce starter minutes by coach tendency %
- [ ] Phase 8.2 ready (rotation patterns available for Claude reasoning)

---

## Phase 8.1+ Integration (Future)

Once both systems are implemented, Claude (Phase 8.1+) will:

**From Injury Intelligence:**
- Reason about injury severity ("ankle sprain" vs "ACL tear")
- Identify minutes-limit signals in descriptions
- Flag beneficiaries when stars are out
- Generate "welcome back" value plays for returning players
- Detect recurring injury patterns (e.g., "3rd ankle injury this season")

**From Rotation Intelligence:**
- Adjust situational minutes predictions based on game context
- Identify lineup combinations that maximize player performance
- Flag games where rotation chaos is likely (multiple injuries, unusual matchups)
- Warn when coach tendencies shift (new rotation patterns emerging)

Both systems provide **deterministic data** that Claude will **reason about** — keeping math and AI layers cleanly separated.

---

## Dependencies

**Required:**
- BallDontLie API (GOAT tier, $39.99/mo) — injury data
- Tank01 API (PAID) — injury fallback
- `nba_api==1.11.3` Python package — PBP data (free, already installed) ✅
  - **CRITICAL:** All endpoints must include `league_id="00"` parameter
  - PlayByPlayV3 endpoint wrapper available in `utils/nba_api_client.py`

**Nice-to-Have:**
- RotoWire RSS feed — breaking injury news (already integrated)

---

## Success Metrics

**Injury Intelligence:**
- GENERALIST archetype < 25% (down from 31.4%)
- Long-term injured players explicitly tracked (not silently dropped)
- Injury onset-to-return timeline queryable

**Rotation Intelligence:**
- Minutes projection RMSE improves by ≥10%
- Blowout detection accuracy > 85%
- Coach tendency detection for all 30 teams

---

**For questions or updates, see:** `ROADMAP.md` Phase 8.0 or contact the development team.
