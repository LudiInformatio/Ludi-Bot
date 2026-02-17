# Phase 7.9.5 Cleanup + Phase 8 Prep Agent

## Role
You are a **Technical Documentation & API Integration Specialist** completing Phase 7.9.5 cleanup and preparing Phase 8 foundation work.

## Tasks Overview

### Part 1: Phase 7.9.5 Cleanup (5 tasks)
1. Document archetype vs defensive_tag distinction
2. Update ROADMAP.md to show Archetype System complete
3. Wire team_scheme_cache to daily workflows
4. Remove HACKERS dead code from module_e.py
5. Update memory/MEMORY.md with archetype lessons

### Part 2: nba_api Updates (3 tasks)
6. Add league_id parameter to all nba_api endpoint calls
7. Pin nba_api version in requirements.txt
8. Add PlayByPlayV3 support for Phase 8

### Part 3: Documentation Updates (2 tasks)
9. Update ROADMAP.md Phase 8.0 with nba_api requirements
10. Update PHASE_8_FOUNDATION_PLAN.md with nba_api implementation details

---

## Reference Documents

**Phase 7.9.5 Plan:** `/Users/flyprice/.claude/plans/immutable-floating-gosling.md`
**Phase 8 Plan:** `docs/PHASE_8_FOUNDATION_PLAN.md`
**Current Status:** All tasks tracked in task list (use `TaskList` to view)

---

## Part 1: Phase 7.9.5 Cleanup

### Task 1: Document archetype vs defensive_tag

**File:** `docs/ARCHITECTURE.md`

**Location:** Find "### Key Tables" section in Database Schema

**Add after the tables list:**

```markdown
#### Player Classification Columns

| Column | Purpose | Values |
|--------|---------|--------|
| `archetype` | Primary role classification | GENERALIST, RIM_GUARDIAN, PERIMETER_HAWK, SNIPER_ELITE, etc. (19 types) |
| `defensive_tag` | Secondary overlay for poor defenders ONLY | WEAK_LINK or NULL |

**Important**: Defensive archetypes (RIM_GUARDIAN, PERIMETER_HAWK, SWITCHABLE_ANCHOR, HUSTLE_DISRUPTOR)
are stored in the `archetype` column, NOT `defensive_tag`. The `defensive_tag` column is reserved
exclusively for the WEAK_LINK designation (poor defenders who allow >1.5% worse FG% on >8% frequency).

**GENERALIST Measurement**: The <25% target applies to **active players** (21-day window), not all 503
players in database. Inactive players (injured, waived) default to GENERALIST but don't generate bets.
```

### Task 2: Update ROADMAP.md

**File:** `ROADMAP.md`

**Changes needed:**

1. **Line ~101** - Update Archetype System status:
```markdown
| Archetype System | ✅ COMPLETE | `1e100c7` | 5 defensive archetypes, Synergy hybrid, GENERALIST 20.7% (active), team scheme cache |
```

2. **Line ~90** - Add to Critical Findings table:
```markdown
| GENERALIST <25% target | 20.7% of active players (21-day window) | ✅ Achieved (was 31.4% all players) |
```

3. **After line ~101** - Add note:
```markdown
**Note on GENERALIST Measurement**: The 25% target applies to **active players** (21-day window),
not all 503 DB players. Inactive players (injured/waived) default to GENERALIST but don't generate
betting recommendations. Active: 95/458 = 20.7% ✅
```

### Task 3: Wire team_scheme_cache to Workflows

**File:** `.github/workflows/data_sync.yml`

**Location:** After existing sync steps (around line 150-160)

**Add:**
```yaml
      - name: Update Team Scheme Cache
        timeout-minutes: 5
        run: |
          python3 scripts/update_team_scheme_cache.py --db-path ludi.db --verbose
        env:
          PYTHONPATH: ${{ github.workspace }}
```

### Task 4: Remove HACKERS Dead Code

**File:** `module_e.py`

**Search and remove these 6 occurrences:**
- Line 1040: Remove `if def_style == "HACKERS":` block
- Line 1110: Remove `elif def_style == "HACKERS":` block
- Line 1124: Remove `elif def_style == "HACKERS":` block
- Line 1725: Change `if opponent_defense in ["FUNNEL", "HACKERS"]:` to `if opponent_defense == "FUNNEL":`
- Line 2188: Remove `elif def_style == 'HACKERS':` block
- Line 2193: Remove HACKERS logging line

**Test:** `python -c "from module_e import LudiCalibrator; print('✅ OK')"`

### Task 5: Update Memory.md

**File:** `/Users/flyprice/.claude/projects/-Users-flyprice-Desktop-Ludi-Informatio-Projects-Ludi-Bot/memory/MEMORY.md`

**Add to "## Key Patterns & Lessons":**

```markdown
### Archetype Classification System (Feb 17, 2026)
- `archetype` column: Primary role (19 types including defensive archetypes)
- `defensive_tag` column: ONLY stores WEAK_LINK (diff_pct > 1.5 AND freq_pct > 8.0)
- Defensive archetypes (RIM_GUARDIAN, PERIMETER_HAWK, etc.) live in `archetype`, NOT `defensive_tag`
- GENERALIST target (<25%) applies to ACTIVE players (21-day window), not all DB players
- Team scheme cache: season/21d/14d consensus with smart fallback (active_style column)
- HACKERS scheme removed (dead code, no upstream mapping)
```

---

## Part 2: nba_api Updates

### Task 6: Add league_id Parameter

**File:** `utils/nba_api_client.py`

**Changes:** Add `league_id="00"` to all endpoint calls

**Line ~306** - playerdashboardbyshootingsplits:
```python
response = playerdashboardbyshootingsplits.PlayerDashboardByShootingSplits(
    player_id=player_id,
    season=season,
    league_id="00",  # ✅ ADD THIS
    per_mode_detailed=per_mode,
    date_from_nullable=date_from or "",
    date_to_nullable=date_to or "",
    last_n_games=last_n_games,
    headers=self.headers,
    timeout=30
)
```

**Find and update ALL these endpoints:**
- playerdashboardbyshootingsplits.PlayerDashboardByShootingSplits
- playerdashptshots.PlayerDashPtShots
- playerdashptshotdefend.PlayerDashPtShotDefend
- playervsplayer.PlayerVsPlayer
- playerdashptreb.PlayerDashPtReb
- playerdashptpass.PlayerDashPtPass
- commonplayerinfo.CommonPlayerInfo (if used)

**Test:**
```python
from utils.nba_api_client import get_nba_client
client = get_nba_client()
splits = client.get_player_shooting_splits(player_id=203507, season="2025-26")
assert splits is not None and len(splits) > 0
```

### Task 7: Pin nba_api Version

**File:** `requirements.txt`

**Line 14** - Change:
```diff
- nba_api>=1.4.1
+ nba_api==1.11.3
```

### Task 8: Add PlayByPlayV3 Support

**File:** `utils/nba_api_client.py`

**Add import at top (around line 34):**
```python
from nba_api.stats.endpoints import (
    playerdashboardbyshootingsplits,
    playerdashptshots,
    playerdashptshotdefend,
    playervsplayer,
    playerdashptreb,
    playerdashptpass,
    commonplayerinfo,
    boxscorematchupsv3,
    leaguegamefinder,
    playbyplayv3  # ✅ ADD THIS
)
```

**Add new method (around line 400):**
```python
    def get_play_by_play(self, game_id: str, season: str = "2025-26") -> Optional[Dict]:
        """
        Get play-by-play data including substitution events.

        Used for rotation tracking (Phase 8.0 Rotation Intelligence).

        Args:
            game_id: NBA game ID (e.g., "0022300001")
            season: Season string (e.g., "2025-26")

        Returns:
            Dict with PBP data or None if fetch fails

        Example:
            pbp = client.get_play_by_play("0022300001")
            subs = [e for e in pbp['PlayByPlay'] if e['EVENTMSGTYPE'] == 8]
        """
        cache_key = f"playbyplay_{game_id}.json"
        cache_path = self._get_cache_path(cache_key)

        # Check cache (24-hour TTL)
        if self._is_cache_valid(cache_path, ttl_hours=24):
            print(f"   [NBA-API] Using cached PBP for {game_id}")
            return self._read_cache(cache_path)

        # Rate limit and fetch
        self._rate_limit()
        print(f"   [NBA-API] Fetching PBP for game {game_id}...")

        try:
            response = playbyplayv3.PlayByPlayV3(
                game_id=game_id,
                league_id="00"
            )

            result = response.get_dict()

            # Cache the result
            self._write_cache(cache_path, result)
            self.monitor.log_request('nba_api', 'playbyplay', {})

            return result

        except Exception as e:
            print(f"   [NBA-API] Error fetching PBP: {e}")
            return None
```

---

## Part 3: Documentation Updates

### Task 9: Update ROADMAP.md Phase 8

**File:** `ROADMAP.md`

**Find Phase 8 table (around line 230-250)**

**Update row 8.0:**
```markdown
| 8.0 | **Injury Intelligence System** | **CRITICAL** | **Persistent injury tracking (status, return dates, descriptions), long-term injury handling, recently-returned player pipeline. REQUIRES: nba_api==1.11.3 with league_id parameter** | **$0** |
```

**Add new row 8.9:**
```markdown
| 8.9 | **Rotation/Minutes Projection** | **MEDIUM** | **Track coach rotation patterns from PBP data (nba_api PlayByPlayV3), situational minutes modeling, stint-level analysis** | **TBD** |
```

**Update "Shared Infrastructure" section:**
```markdown
**Shared Infrastructure:**
- [ ] Create `utils/claude_client.py` — shared Anthropic SDK wrapper
- [ ] Add `ANTHROPIC_API_KEY` to config.py and `.env.template`
- [x] Verify `nba_api==1.11.3` installed with league_id parameter support ✅
- [x] Add PlayByPlayV3 endpoint support to `utils/nba_api_client.py` ✅
```

### Task 10: Update PHASE_8_FOUNDATION_PLAN.md

**File:** `docs/PHASE_8_FOUNDATION_PLAN.md`

**Line 504** - Update requirements.txt note:
```markdown
| `requirements.txt` | `nba_api==1.11.3` already installed, add `league_id="00"` to all endpoints | B |
```

**Line 517** - Update Part B implementation:
```markdown
**Part B second (Rotation Intelligence):**
5. ~~Install `nba_api`~~ ✅ Already installed (v1.11.3) — verify league_id parameter added
6. Database schema (rotation tables) — `database.py`
7. PBP parsing script — `scripts/sync_rotation_patterns.py` using PlayByPlayV3 endpoint
8. Coach tendency analyzer — `scripts/analyze_rotation_tendencies.py`
9. Module C integration — `module_c.py`
10. Sync script + workflow — `data_sync.yml`
```

**Line 300-305** - Update data source section:
```markdown
**Recommended Approach:**
1. **`nba_api` PlayByPlayV3 endpoint** (Primary) ✅ **IMPLEMENTED in utils/nba_api_client.py**
   - Official NBA.com wrapper (v1.11.3)
   - Free, comprehensive PBP data
   - Includes substitution events with timestamps
   - **CRITICAL:** Must include `league_id="00"` parameter (2023-24+ requirement)
   - Example: `playbyplayv3.PlayByPlayV3(game_id='0022100001', league_id="00")`
   - **Available method:** `client.get_play_by_play(game_id)`
```

**Line 322** - Update code example:
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
```

**Line 580** - Update dependencies:
```markdown
**Required:**
- BallDontLie API (GOAT tier, $39.99/mo) — injury data
- Tank01 API (PAID) — injury fallback
- `nba_api==1.11.3` Python package — PBP data (free, already installed) ✅
  - **CRITICAL:** All endpoints must include `league_id="00"` parameter
  - PlayByPlayV3 endpoint wrapper available in `utils/nba_api_client.py`
```

---

## Verification Checklist

Run ALL of these after implementation:

### Part 1: Phase 7.9.5
```bash
# 1. Verify ARCHITECTURE.md update
grep -A 5 "Player Classification Columns" docs/ARCHITECTURE.md

# 2. Verify ROADMAP.md shows completion
grep "Archetype System.*COMPLETE" ROADMAP.md
grep "GENERALIST.*20.7%" ROADMAP.md

# 3. Verify workflow cache step
grep "Update Team Scheme Cache" .github/workflows/data_sync.yml

# 4. Verify HACKERS removed
git grep HACKERS module_e.py  # Should return 0 results

# 5. Verify Module E still works
python -c "from module_e import LudiCalibrator; print('✅ Module E OK')"

# 6. Verify memory update
grep "Archetype Classification System" /Users/flyprice/.claude/projects/-Users-flyprice-Desktop-Ludi-Informatio-Projects-Ludi-Bot/memory/MEMORY.md
```

### Part 2: nba_api
```bash
# 7. Verify league_id in all calls
grep -n 'league_id="00"' utils/nba_api_client.py | wc -l  # Should be 6+

# 8. Verify version pinned
grep 'nba_api==1.11.3' requirements.txt

# 9. Verify PlayByPlayV3 import
grep 'playbyplayv3' utils/nba_api_client.py

# 10. Test PlayByPlayV3 method
python -c "from utils.nba_api_client import get_nba_client; c = get_nba_client(); print('get_play_by_play' in dir(c))"
```

### Part 3: Documentation
```bash
# 11. Verify ROADMAP Phase 8 updates
grep "nba_api==1.11.3" ROADMAP.md
grep "PlayByPlayV3" ROADMAP.md

# 12. Verify PHASE_8 plan updates
grep "league_id" docs/PHASE_8_FOUNDATION_PLAN.md
grep "get_play_by_play" docs/PHASE_8_FOUNDATION_PLAN.md
```

---

## Success Report Format

```markdown
# Phase 7.9.5 Cleanup + Phase 8 Prep - Completion Report

## Part 1: Phase 7.9.5 Cleanup ✅
- [x] Documented archetype vs defensive_tag in ARCHITECTURE.md
- [x] Updated ROADMAP.md (Archetype System ✅ COMPLETE, GENERALIST 20.7%)
- [x] Wired team_scheme_cache to data_sync.yml
- [x] Removed 6 HACKERS references from module_e.py
- [x] Updated memory/MEMORY.md with archetype lessons

## Part 2: nba_api Updates ✅
- [x] Added league_id="00" to 6 endpoint calls in nba_api_client.py
- [x] Pinned nba_api==1.11.3 in requirements.txt
- [x] Added PlayByPlayV3 support (get_play_by_play method)

## Part 3: Documentation Updates ✅
- [x] Updated ROADMAP.md Phase 8.0 with nba_api requirements
- [x] Updated PHASE_8_FOUNDATION_PLAN.md with implementation details

## Verification Results
- ✅ All 12 verification checks passed
- ✅ Module E imports successfully
- ✅ nba_api client has PlayByPlayV3 support
- ✅ league_id parameter added to all endpoints
- ✅ Phase 8 documentation updated

## Files Modified
1. docs/ARCHITECTURE.md
2. ROADMAP.md
3. .github/workflows/data_sync.yml
4. module_e.py
5. memory/MEMORY.md
6. utils/nba_api_client.py
7. requirements.txt
8. docs/PHASE_8_FOUNDATION_PLAN.md

## Phase 7.9.5 Status
✅ **COMPLETE** - All archetype cleanup tasks finished, documentation updated

## Phase 8 Prep Status
✅ **READY** - nba_api configured with league_id, PlayByPlayV3 endpoint ready for rotation tracking
```

---

## Notes

- **Priority:** Complete Part 1 (Phase 7.9.5) first, then Part 2 (nba_api), then Part 3 (docs)
- **HACKERS removal:** Safe to remove - dead code with no upstream mapping
- **league_id parameter:** CRITICAL for 2023-24+ season data (prevents empty datasets)
- **PlayByPlayV3:** Foundation for Phase 8.0 Part B (Rotation Intelligence)
- **Testing:** Run verification checklist after each part
