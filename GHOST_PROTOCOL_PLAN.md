# Ghost Protocol: Comprehensive Tracking & Advanced Stats Backfill Plan

## Objective
Implement a robust, browser-based ("Ghost Protocol") strategy to backfill all critical player tracking, advanced statistics, and matchup data for the 2025-26 NBA season. This approach bypasses API blocking by mimicking human browsing behavior to scrape data directly from `nba.com/stats` dynamic tables.

## 1. Data Targets & Prioritization

We will scrape data by iterating through days (backwards or forwards) to build a complete historical dataset.

### Tier 1: Core Tracking (The "Physics" of the Engine)
These datasets directly feed Module C (Simulation) and Module F (Edge Calculation).
*   **Drives**: `nba.com/stats/players/drives`
    *   *Columns*: Drives, FGM, FGA, FG%, PTS, PASS%, AST%, TOV%, PF%.
*   **Catch & Shoot**: `nba.com/stats/players/catch-shoot`
    *   *Columns*: C&S FGM, C&S FGA, C&S 3PM, C&S 3PA, eFG%.
*   **Pull-Up Shooting**: `nba.com/stats/players/pullup`
    *   *Columns*: Pull-Up FGM, Pull-Up FGA, Pull-Up 3PM, Pull-Up 3PA, eFG%.
*   **Speed & Distance**: `nba.com/stats/players/speed-distance`
    *   *Columns*: Dist Miles, Avg Speed (Off/Def). (Useful for fatigue/load management).

### Tier 2: Matchup & Defense (The "Context")
These datasets feed Module E (Calibrator - Matchups).
*   **Defensive Impact**: `nba.com/stats/players/defensive-impact`
    *   *Columns*: Defended FG%, FG% Differential.
*   **Matchups (Head-to-Head)**: `nba.com/stats/players/matchups`
    *   *Note*: This is complex; usually yields large datasets. We may need to filter by "Notable Matchups" or just scrape key defensive assignments.
    *   *Strategy*: Prioritize scraping "Player vs Player" matchup data for upcoming games (just-in-time) rather than full historical backfill, OR scrape daily "Box Score Matchups".

### Tier 3: Advanced & Usage (The "Engine" Inputs)
*   **Advanced Stats**: `nba.com/stats/players/advanced`
    *   *Columns*: OFF RTG, DEF RTG, NET RTG, AST%, TOV%, USG%, PACE, PIE.
*   **Usage**: `nba.com/stats/players/usage`
    *   *Columns*: USG%, %FGA, %TOV, %AST. (Redundant with Advanced but sometimes offers split granularity).
*   **Clutch Traditional**: `nba.com/stats/players/clutch-traditional`
    *   *Columns*: GP, W/L, MIN, PTS, FGM, FGA, 3PM, 3PA in clutch time.

## 2. Technical Architecture

### script: `sync_browser_backfill.py` (Enhanced)
The existing script will be expanded to handle a `manifest` of data sources.

```python
DATA_MANIFEST = {
    "tracking_drives": {
        "url": "https://www.nba.com/stats/players/drives",
        "table_selector": "table.Crom_table__p1iZz",
        "target_table": "player_game_tracking" # updates columns: drives_fga, drives_fgm, etc.
    },
    "tracking_catch_shoot": {
        "url": "https://www.nba.com/stats/players/catch-shoot",
        "table_selector": "table.Crom_table__p1iZz",
        "target_table": "player_game_tracking" # updates columns: catch_shoot_fga, etc.
    },
    "tracking_pull_up": {
        "url": "https://www.nba.com/stats/players/pullup",
        "table_selector": "table.Crom_table__p1iZz",
        "target_table": "player_game_tracking"
    },
    "advanced_basic": {
        "url": "https://www.nba.com/stats/players/advanced",
        "table_selector": "table.Crom_table__p1iZz",
        "target_table": "player_game_advanced" # NEW TABLE
    },
    "clutch_traditional": {
        "url": "https://www.nba.com/stats/players/clutch-traditional",
        "table_selector": "table.Crom_table__p1iZz",
        "target_table": "player_clutch_stats"
    }
}
```

### Database Schema Expansion (`ludi.db`)

We need to formalize 2 new tables in `database.py`:

**1. `player_game_advanced`**
Link key: `player_id` + `game_date`
*   `off_rating` (REAL)
*   `def_rating` (REAL)
*   `net_rating` (REAL)
*   `ast_pct` (REAL)
*   `ast_to` (REAL)
*   `ast_ratio` (REAL)
*   `oreb_pct` (REAL)
*   `dreb_pct` (REAL)
*   `reb_pct` (REAL)
*   `tov_pct` (REAL)
*   `efg_pct` (REAL)
*   `ts_pct` (REAL)
*   `usg_pct` (REAL)
*   `pace` (REAL)
*   `pie` (REAL)

**2. `player_game_tracking` (Update)**
Ensure it has columns for:
*   `pull_up_fgm`, `pull_up_fga`, `pull_up_fg3m`, `pull_up_fg3a`, `pull_up_efg_pct`
*   `dist_miles_off`, `dist_miles_def`, `avg_speed_off`, `avg_speed_def`

## 3. Execution Strategy

### Phase 1: The "Skeleton" (Days 1-2)
*   **Goal**: Ensure `player_game_tracking` is 100% full for *Drives, Catch & Shoot, and Pull-Ups*.
*   **Action**: Run `sync_browser_backfill.py` targeting ONLY these 3 pages per day.
*   **Range**: Nov 14, 2025 -> Present.

### Phase 2: The "Engine" (Day 3)
*   **Goal**: Fill `player_game_advanced` and `player_clutch_stats`.
*   **Action**: Add `advanced` and `clutch-traditional` to the scrape loop.
*   **Range**: Nov 14, 2025 -> Present.

### Phase 3: The "Deep Dive" (Day 4+)
*   **Goal**: Matchups and Defensive Impact.
*   **Action**: Custom script for Matchups (likely needs specific filters like "Defended FG%" < 5ft, > 15ft, etc.).

## 4. Operational Guardrails

1.  **Politeness**: Random sleep 2.0s - 4.5s between page loads.
2.  **Pagination**: Always force "All" (-1) on dropdowns to get full daily datasets in one HTTP request per stat category.
3.  **Human Emulation**: Random mouse wiggles (optional, if detection increases) and User-Agent rotation.
4.  **Error Handling**: If a specific table fails (e.g., CSS selector change), log error -> skip to next category -> continue. Do not crash the whole day's loop.

## 5. Next Steps

1.  **Update Database**: Add `player_game_advanced` table and new columns to `player_game_tracking`.
2.  **Update Script**: Refactor `sync_browser_backfill.py` to support the `DATA_MANIFEST` structure and new categories.
3.  **Launch**: Execute Phase 1 Backfill.
