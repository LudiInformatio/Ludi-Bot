# Tank01 Data Expansion Project

**Status:** Planning Complete — Implementation Pending
**Last Updated:** February 20, 2026
**Roadmap Reference:** See ROADMAP.md Phase 8 sub-phases
**Account Tier:** PRO ($10/mo) — 1,000 req/day
**Current Daily Usage:** ~18 requests (~2% of quota)
**Projected Usage After Expansion:** ~70-80 requests (~7-8% of quota)

---

## Implementation Status — Feb 20, 2026

| Phase | Task | Status | Notes |
|-------|------|--------|-------|
| 0 | `utils/tank01_client.py` — central client, 12 public methods | ✅ DONE | Smoke tested: 72 injuries, lazy singleton |
| 1 | `module_h_historian.py` — `fantasyPoints=true` + `fantasy_pts` INSERT | ✅ DONE | `fantasy_pts` column was pre-existing in schema |
| 2 | `module_c.py` — STL/BLK weights 2→3 | ✅ DONE | Line 482 |
| 3 | `config.py` — `SIM_COUNT` 5000→10000 | ✅ DONE | Line 129 |
| 4 | `scripts/populate_todays_games.py` — 3-source fallback chain | ✅ DONE | Odds API→Tank01→BDL. Tank01 fallback fired live Feb 20 (Odds API quota exhausted) |
| 5 | `scripts/validate_pipeline_output.py` — output assertion gate | ✅ DONE | 5 checks. Detected 93.4% DIAMOND ratio (real drift) |
| 6 | `module_h_historian.py` — games table UPSERT bridge | ✅ DONE | `teamStats.home/away.pts` → `games.home_score/away_score` |
| 7 | `module_a.py` — Tank01 props validator + fallback framework | ✅ DONE | `_load_tank01_props()`, `_validate_line_with_tank01()` added. Full 3rd-fallback deferred pending Tank01↔BDL player ID cross-walk |
| 8 | `scripts/sync_team_current_info.py` + `morning_brief.py` | ✅ DONE | Uses `getNBATeams` (not `getNBACurrentInfo` — that returns metadata only). Streak notes in morning brief |
| 9 | `scripts/sync_tank01_projections.py` + `database.py` | ✅ DONE | `tank01_projections` table. `body` is flat dict (no `playerProjections` nesting) |
| 10 | `scripts/sync_player_news.py` + `module_d.py` | ✅ DONE (partial) | `player_news_cache` table. `getNBATopNews` returned 0 items — endpoint under investigation |
| 11 | `docs/projects/TANK01_DATA_EXPANSION.md` | ✅ THIS FILE | — |
| 12 | `ROADMAP.md` update | ✅ DONE | — |

### Open Items
- **Phase 7 full 3rd-fallback**: Needs Tank01 playerID → player_name cross-walk in `module_a.py` context. Recommend adding to `player_canonical_ids` table. *(deferred — medium priority)*

### Resolved Items (Feb 20, 2026)
- **`getNBATopNews` endpoint** ✅: Earlier "0 items" was a timing artifact (endpoint queried before daily news populated). Confirmed working: 50 items returned on second test. `player_news_cache` table created via `database.py` run. Endpoint is `/getNBANews?recentNews=true` (mapped as `get_top_news()` in Tank01Client).
- **DIAMOND ratio drift** ✅: Root cause — model consistently produces 30-44% average edges on Odds API days (not BDL fallback). No corrupt odds (insane_edges check = 0). Fixed in two steps:
  1. `module_f.py` — Added minimum edge floors: DIAMOND requires ≥10% edge, BLUE CHIP requires ≥7% edge. Prevents composite bonus (archetype + gold combo) from double-bumping low-edge bets to DIAMOND.
  2. `validate_pipeline_output.py` — Changed DIAMOND ratio from hard FAIL to WARN (threshold raised 80%→90%). `insane_edges > 100%` remains the real quality gate.

### Key Discoveries
- `getNBACurrentInfo` returns season metadata only (not per-team standings). Standings come from `getNBATeams`.
- `tank01_projections` response: `body` is flat playerID-keyed dict (spec said `playerProjections` nested key — incorrect).
- `games.home_score`, `games.away_score`, `player_game_logs.fantasy_pts` all pre-existed in schema.
- Tank01 uses `NO`/`GS`/`NY`/`PHO`/`SA` short codes (same as BDL) — normalized via `SHORT_ABBREV_MAP`.

---

## Overview

Tank01 provides 17 NBA API endpoints. We currently use 6. This document covers the expansion plan for the remaining 11, prioritized by value and implementation effort.

**The most important discovery:** Tank01's player props (`getNBABettingOdds?playerProps=true`) return **consensus line values only** — no over/under odds, no sportsbook breakdown. This makes Tank01 a **line quality oracle** that improves Odds-API and BDL prop filtering, rather than a direct odds replacement.

---

## Complete Endpoint Inventory

| # | Endpoint Name | API Function | Used? | Priority | Cost/day |
|---|--------------|-------------|-------|----------|----------|
| 1 | Get NBA Betting Odds | `getNBABettingOdds` | **NO** | **HIGH** | ~10-15 |
| 2 | Get Game Box Score (Live) | `getNBABoxScore` | ✅ YES | Core | ~12-15 |
| 3 | Get Teams | `getNBATeams` | ✅ YES | Core | ~1/week |
| 4 | Get NBA Games for Single Player | `getNBAGamesForPlayer` | **NO** | LOW | ~0-5 |
| 5 | Get Daily Scoreboard (Live) | `getNBAScoreboard` | **NO** | LOW | ~1 |
| 6 | Get General Game Information | `getNBAGameInfo` | **NO** | LOW | ~1 |
| 7 | Get Daily Schedule | `getNBASchedule` | **NO** | MEDIUM | ~1 |
| 8 | Get Team Roster | `getNBATeamRoster` | ✅ YES | Core | ~30/week |
| 9 | Get Injury List History | `getNBAInjuryListHistory` | **NO** | MEDIUM | ~50/week |
| 10 | Get Player Information | `getNBAPlayerInfo` | **NO** | LOW | ~0 |
| 11 | Get Player List | `getNBAPlayerList` | **NO** | LOW | ~0 |
| 12 | Get Team Schedule | `getNBATeamSchedule` | **NO** | LOW | ~0 |
| 13 | **Get Current Info** | `getNBACurrentInfo` | **NO** | **HIGH** | ~30 |
| 14 | DFS Salaries | `getNBADFSSalaries` | **NO** | LOW | ~0 |
| 15 | Get ADP | `getNBAAdp` | **NO** | LOW | ~0 |
| 16 | Get NBA Depth Charts | `getNBADepthCharts` | ✅ YES | Core | ~1 |
| 17 | Top News and Headlines | `getNBATopNews` | **NO** | MEDIUM | ~1-3 |
| 18 | **Get Fantasy Point Projections** | `getNBAProjections` | **NO** | **HIGH** | ~5-15 |

---

## Critical: Props Format + O/U Parsing Strategy

### Tank01 Player Props Response Structure

```json
{
  "gameID": "20251024_ATL@ORL",
  "awayTeam": "ATL",
  "homeTeam": "ORL",
  "playerProps": [
    {
      "playerID": "947149815539",
      "propBets": {
        "pts": "24.5",
        "reb": "7.5",
        "ast": "3.5",
        "blk": "0.5",
        "stl": "0.5",
        "threes": "1.5",
        "turnovers": "3.5",
        "ptsast": "28.5",
        "ptsreb": "32.5",
        "rebast": "11.5",
        "stlblk": "1.5",
        "ptsrebast": "36.5"
      }
    }
  ]
}
```

**Key facts:**
- Line values ONLY — no over/under odds, no sportsbook names
- ONE value per stat = consensus/aggregated main line (no alt lines)
- Player IDs are Tank01 composite format — requires `_resolve_player_id()` before DB storage
- 12 stat types: pts, reb, ast, blk, stl, threes, turnovers + combos (ptsast, ptsreb, rebast, stlblk, ptsrebast)
- Parameters: `gameDate` (YYYYMMDD), `gameID`, `playerProps=true`, `itemFormat=list`

### O/U and Alt Line Parsing — All Three Sources

| Source | Lines | Over/Under Odds | Alt Lines Present? | Our Strategy |
|--------|-------|-----------------|-------------------|--------------|
| **Odds-API** (primary) | Per-book | ✅ Full odds | YES — mixed with main | Best price on main line. Tank01 consensus validates which line is "main" |
| **BDL** (1st fallback) | Per-vendor | ✅ `over_odds`/`under_odds` | YES — mixed in | Modal filter ≥2 vendors + milestone market guard + Tank01 cross-check |
| **Tank01** (2nd fallback/validator) | Single consensus | ❌ None | NO — single consensus | Cross-check other sources. As standalone: assume -110/-110 |

### Tank01 as Line Quality Oracle

```python
def _validate_line_with_tank01(stat_key, book_line, tank01_line, tolerance=0.5):
    """
    Returns True if book_line matches Tank01 consensus (is the main line).

    Use cases:
    1. Odds-API: filter alt lines from multi-book response
    2. BDL: recover single-vendor lines when Tank01 confirms the line
    3. Standalone: Tank01 line + -110/-110 assumed = 50%/50% fair probability
    """
    if tank01_line is None:
        return True  # No Tank01 data — don't filter
    return abs(float(book_line) - float(tank01_line)) <= tolerance
```

**Three ways Tank01 improves other sources:**

1. **Odds-API + Tank01**: Multiple books return different lines. Tank01 consensus identifies the main line. Any book line >0.5 pts from consensus = alt line → skip.

2. **BDL + Tank01**: Our ≥2-vendor rule skips single-vendor lines. If that single-vendor line matches Tank01's consensus → accept it. Extends game coverage from ~3/10 to potentially 6-7/10 games on BDL fallback days.

3. **Tank01 standalone**: When both Odds-API and BDL have zero coverage → Tank01 line + assumed -110/-110 → edge = (model_prob - 0.5) / 0.5. Pure model edge, no devigging needed.

---

## New Endpoint Integration Details

### Priority 1: `fantasyPoints=true` — Free Data (Zero New Calls)

**What changes:** `module_h_historian.py` line 597
```python
# Current:
params_box = {"gameID": game_id, "fantasyPoints": "false"}
# Fix:
params_box = {"gameID": game_id, "fantasyPoints": "true"}
```
Plus extend the INSERT to populate `fantasy_pts` column (already in schema, always NULL).

**Impact:** Every box score call now returns official fantasy point totals per player. Enables actual vs projected fantasy points comparison.

---

### Priority 2: `getNBABettingOdds?playerProps=true` — Line Validator + 3rd Fallback

**Endpoint:** `GET https://tank01-fantasy-stats.p.rapidapi.com/getNBABettingOdds`
**Parameters:**
- `gameDate`: YYYYMMDD
- `playerProps`: "true"
- `itemFormat`: "list"

**Integration point:** `module_a.py`
- **New function:** `_fetch_tank01_prop_lines(game_date)` — returns dict: `{player_id: {stat: line_value}}`
- **Used in three places:**
  1. After fetching Odds-API props: validate each line against Tank01 consensus
  2. After BDL modal filter: if single-vendor line passes Tank01 check, accept it
  3. If no BDL coverage for a game: use Tank01 lines with -110/-110 assumed

**Field mapping:**
```
Tank01 propBets key → our stat_category
pts        → PTS
reb        → REB
ast        → AST
blk        → BLK
stl        → STL
threes     → 3PM
turnovers  → TOV
ptsast     → PA
ptsreb     → PR
rebast     → RA
stlblk     → (STL+BLK combo)
ptsrebast  → PRA
```

**Feature flag:** `config.USE_TANK01_LINE_VALIDATION = True` (default True)

---

### Priority 3: `getNBACurrentInfo` — Live Team Context

**Endpoint:** `GET https://tank01-fantasy-stats.p.rapidapi.com/getNBACurrentInfo?date=YYYYMMDD`
**ONE call = standings + streak + roster + schedule for ALL 30 teams**

**New script:** `scripts/sync_team_current_info.py`
**New table:**
```sql
CREATE TABLE IF NOT EXISTS team_current_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_abv TEXT UNIQUE,
    wins INTEGER,
    losses INTEGER,
    win_streak INTEGER,      -- positive = win streak, negative = loss streak
    conference_rank INTEGER,
    last_game_result TEXT,
    next_game_date TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Integration:** Replaces hardcoded `_TEAM_SITUATION_NOTES` dict in `morning_brief.py` with live data:
```python
# Instead of: {"CHA": "CHA hot", "LAL": "LAL dog", ...}
# Query: SELECT team_abv, win_streak, wins, losses FROM team_current_info WHERE team_abv = ?
```

**Workflow:** `daily_briefing.yml` — add step before "Run Morning Briefing"

---

### Priority 4: `getNBAProjections` — Model Blind-Test

**Endpoint:** `GET https://tank01-fantasy-stats.p.rapidapi.com/getNBAProjections`
**Parameters (custom scoring weights):**
```
numOfDays=7, pts=1, reb=1.25, ast=1.5, stl=3, blk=3, TOV=-1, mins=0
```
*(Matches FanDuel scoring = our internal FANTASY_PTS formula after MC-1 fix)*

**ONE call = projected fantasy points for all ~345 active players**

**New table:**
```sql
CREATE TABLE IF NOT EXISTS tank01_projections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    player_name TEXT,
    game_date TEXT,
    projected_fantasy_pts REAL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, game_date)
);
```

**Use case — blind-test comparison:**
```python
# Convert our raw stat projections to same fantasy point scale
our_fantasy_pts = (pts * 1.0 + reb * 1.25 + ast * 1.5 +
                   stl * 3.0 + blk * 3.0 - tov * 1.0)
# Flag if gap > 20% — potential model drift signal
gap_pct = abs(our_fantasy_pts - tank01_pts) / tank01_pts
if gap_pct > 0.20:
    alert("Model drift detected for player X")
```

**Rule:** Tank01 projections are a **read-only benchmark**. Never fed INTO the model as input.

**Workflow:** `data_sync.yml` — add after "Build Player Trends"

---

### Priority 5: `getNBATopNews` — Player News Cache

**Endpoint:** `GET https://tank01-fantasy-stats.p.rapidapi.com/getNBATopNews`
**Fetch ONCE per day** (bulk, all news) → cache to `player_news_cache` table.

**New table:**
```sql
CREATE TABLE IF NOT EXISTS player_news_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT,
    team_abv TEXT,
    headline TEXT,
    content TEXT,
    published_at TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Integration:** `module_d.py` — `targeted_search()` queries cache before DuckDuckGo/Perplexity:
```python
# Query cache first (fast, no API cost)
cached_news = self._query_news_cache(player_name)
if cached_news:
    return cached_news
# Fall through to Perplexity...
```

**Workflow:** `data_sync.yml` — add before "Sync Injuries"

---

### Priority 6: `getNBAInjuryListHistory` — Historical Injury Records

**Weekly batch** (Tuesdays, `weekly_validation.yml`). Returns historical injury records per player.

**Important:** NBA suspensions do NOT appear in Tank01/BDL injury feeds. Suspensions use a separate NBA disciplinary channel. Phase 8.16 (Perplexity detection) remains required for suspension intelligence.

**New table:**
```sql
CREATE TABLE IF NOT EXISTS player_injury_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id TEXT,
    player_name TEXT,
    injury_date TEXT,
    return_date TEXT,
    injury_type TEXT,
    status TEXT,
    games_missed INTEGER,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(player_id, injury_date, injury_type)
);
```

**Use cases:**
- WELCOME_BACK detection (see how long player was actually out, not just designation)
- Chronic injury patterns (player misses games with knee injury every 30 days?)
- Validate Module D injury duration estimates

---

### Priority 7: `getNBAGamesForPlayer` — Targeted Lookup

Budget optimizer. Same data as box score but per-player instead of per-game.

**Use when:** Backfilling 1-5 specific players rather than re-fetching all box scores for all games.

**No new workflow step needed** — used in `module_h_historian.py` for targeted patch operations only.

---

## Architectural Foundation: `utils/tank01_client.py`

**This is Phase 0 — build before anything else.** All Tank01 calls currently scattered across 8+ files as inline `requests` calls.

```python
class Tank01Client:
    HOST = "tank01-fantasy-stats.p.rapidapi.com"
    BASE_URL = f"https://{HOST}"

    def __init__(self):
        self.api_key = config.TANK01_KEY
        self.session = requests.Session()
        self.session.headers.update({
            "x-rapidapi-host": self.HOST,
            "x-rapidapi-key": self.api_key
        })

    # Existing endpoints (migrate from inline calls):
    def get_injury_list(self) -> List[Dict]: ...
    def get_games_for_date(self, game_date: str) -> List[Dict]: ...
    def get_box_score(self, game_id: str, fantasy_points: bool = True) -> Dict: ...
    def get_teams(self) -> List[Dict]: ...
    def get_team_roster(self, team_abv: str) -> Dict: ...
    def get_depth_charts(self) -> Dict: ...

    # New endpoints:
    def get_betting_odds(self, game_date: str = None, game_id: str = None,
                         player_props: bool = False) -> Dict: ...
    def get_projections(self, num_days: int = 7, **scoring_weights) -> Dict: ...
    def get_current_info(self, date: str) -> Dict: ...
    def get_injury_history(self, player_id: str = None, days: int = 30) -> List[Dict]: ...
    def get_top_news(self, team_abv: str = None) -> List[Dict]: ...
    def get_games_for_player(self, player_id: str, season: str = "2024-25") -> List[Dict]: ...
```

---

## Model Calibration Findings

### Industry Methodology Comparison

**Our approach vs RotoGrinders/FiveThirtyEight/Academic Research:**

| Method | Industry Standard | Ludi-Bot | Status |
|--------|------------------|----------|--------|
| Hybrid Poisson/Normal sim | ✅ Industry standard | ✅ Implemented | Match |
| Usage vacuum (beneficiary) | Rare — most tools skip this | ✅ 789 pairs | **Superior** |
| CLV tracking | Sharp bettor standard | ✅ Phase 8.6 | Match |
| Devigging (multiplicative) | Industry correct | ✅ Implemented | Match |
| Archetype vs scheme matrix | DvP by position (generic) | ✅ 14+ scheme modifiers | **Superior** |
| Recency weighting | Exponential decay | ❌ Flat average | Gap |
| Bayesian regression to mean | Standard | ❌ Not implemented | Gap |
| Lookback window | 20+ games | 10-15 games (30 days) | Gap |

### Confirmed Bugs — Fix Now

**Bug 1: STL/BLK underweighted in FANTASY_PTS**
- Location: `module_c.py` line ~481
- Current: `+ stl * 2 + blk * 2`
- Fix: `+ stl * 3 + blk * 3`
- Evidence: DraftKings = 3, FanDuel = 3, Tank01 default = 3. All industry platforms agree.
- Impact: Defensive players (Davis, Adebayo, etc.) are underranked in internal FANTASY_PTS sort.

**Bug 2: SIM_COUNT too low**
- Location: `config.py`
- Current: `SIM_COUNT = 5000`
- Fix: `SIM_COUNT = 10000`
- Evidence: Academic research benchmarks use 10,000-50,000 for production. Our current 5,000 adds ~1.5% extra variance per projection.

### Methodology Gaps — Post-Phase 8 Calibration Sprint

These require backtest validation before deploying to production:

| Gap | Fix | Backtest Gate |
|-----|-----|---------------|
| Flat recency weighting | EMA: L10 (60%) + L11-L20 (30%) + L21-L30 (10%) | RMSE improvement ≥0.1 pts |
| Too-short lookback (10-15 games) | Extend window to 50 days (ensures 20+ games) | Compare L20 vs L10 accuracy |
| No regression to mean | 0.7x shrinkage when recent avg > 1.3x season | Must not reduce win rate on high-edge bets |
| Usage formula incomplete | Add `+AST + 3PA*0.1` terms to `_calculate_usage()` | Neutral or positive impact |

---

## Implementation Phases

### Phase 0 (Prerequisite — Do First)
- **Create `utils/tank01_client.py`** — central client with all methods
- All other phases depend on this

### Phases 1-3 (Parallel — No File Conflicts)
- Phase 1: `fantasyPoints=true` + extend INSERT in `module_h_historian.py`
- Phase 2: Fix STL/BLK weights in `module_c.py`
- Phase 3: Increase SIM_COUNT in `config.py`
- Phase 5: Create `scripts/validate_pipeline_output.py` (3B assertion gate)

### Phase 4 (After Phase 0)
- Games table fallback chain (3A): `scripts/populate_todays_games.py` + `data_sync.yml`

### Phases 6-10 (After Phase 0, Parallel)
- Phase 6: Module H → games bridge (3C): `module_h_historian.py`
- Phase 7: Tank01 props fallback + line validator: `module_a.py`
- Phase 8: Team current info sync: `scripts/sync_team_current_info.py` + `morning_brief.py`
- Phase 9: Fantasy projections sync: `scripts/sync_tank01_projections.py` + `database.py`
- Phase 10: News cache: `scripts/sync_player_news.py` + `module_d.py`

---

## New Files Required

| File | Purpose | Priority |
|------|---------|----------|
| `utils/tank01_client.py` | Central client — prerequisite for all | P0 |
| `scripts/validate_pipeline_output.py` | Canary checks — 3B | P0 |
| `scripts/sync_team_current_info.py` | Live team standings/streak | P1 |
| `scripts/sync_tank01_projections.py` | Model drift benchmark | P1 |
| `scripts/sync_player_news.py` | News cache for Module D | P1 |
| `scripts/sync_injury_history.py` | Historical injury records | P2 (weekly) |

---

## Quota Budget

| Category | Calls/Day | Running Total |
|----------|-----------|---------------|
| Current (6 endpoints, game day) | ~18 | 18 |
| + Betting odds with props | +12 | 30 |
| + Fantasy projections | +1 | 31 |
| + Current info (30 teams) | +30 | 61 |
| + Top news | +2 | 63 |
| + Misc (targeted lookups) | ~5 | ~68 |
| **Total after full expansion** | **~68/day** | **6.8% of 1,000** |

ULTRA tier ($25/mo = 15,000/day) not needed until we add live in-game polling.

---

## Workflow Changes

| Workflow | New Step | Position | Purpose |
|----------|----------|----------|---------|
| `data_sync.yml` | Sync Tank01 Projections | After "Build Player Trends" | Drift benchmark |
| `data_sync.yml` | Sync Player News Cache | Before "Sync Injuries" | Module D feed |
| `data_sync.yml` | Populate Games (fallback chain) | Early step, before Module H | 3A fallback |
| `daily_briefing.yml` | Sync Team Current Info | Before "Run Morning Briefing" | Live context |
| `daily_simulation_pipeline.yml` | Validate Pipeline Output | After "Run Pipeline" | 3B canary |
| `weekly_validation.yml` | Sync Injury History | After "Weekly Classification" | History records |

All new steps must use `continue-on-error: true` to prevent workflow failure if Tank01 is temporarily unavailable.

---

## References

- [Tank01 API on RapidAPI](https://rapidapi.com/tank01/api/tank01-fantasy-stats)
- [Tank01 Game Status Codes](https://www.tank01.com/Guides_Game_Status_Code_NBA.html)
- [Tank01 Odds Guide](https://www.tank01.com/Guides_Odds_NBA.html)
- [BDL Complete Endpoint Reference](../best-practices/api/API_BEST_PRACTICES.md#16-balldontlie-bdl-complete-endpoint-reference)
- [Industry Projection Methodology Sources](../best-practices/api/API_BEST_PRACTICES.md)
- ROADMAP.md — Phase 8 sub-phases table
