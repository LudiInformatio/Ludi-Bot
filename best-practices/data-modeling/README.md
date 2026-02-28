# Data Modeling Best Practices

**Status:** ✅ Complete (updated 2026-02-24)

This guide covers SQLite schema design, data integrity, and ETL patterns for the Ludi-Bot analytics database. Every pattern is derived from a real incident or confirmed working design in the production `ludi.db`.

---

## Quick Reference

| Pattern | Rule |
|---------|------|
| `CREATE TABLE IF NOT EXISTS` | All table creation — never DROP+recreate in production |
| Dedup BEFORE UNIQUE index | `DELETE WHERE rowid NOT IN (SELECT MIN...)` then `CREATE UNIQUE INDEX` |
| `synced_at TEXT NOT NULL` column | Every sync table — enables freshness detection |
| Schedule metadata ≠ results tables | `nba_calendar` for when games happen; `games` for what happened |
| `players.team` vs `player_game_logs.team_abbreviation` | Snapshot vs historical truth — never mix |
| Self-healing daily rebuild | Some tables are cheaper to rebuild daily than track incrementally |
| `IF NOT EXISTS` on ALTER TABLE | Safe migration — check with `PRAGMA table_info(table_name)` |
| `player_trends` table | See `scripts/build_player_trends.py` — 12 stat types, L7/L10/L15/season averages |

---

## Pattern 1 — Deduplication Before UNIQUE Index Creation

**Critical order:** You must deduplicate BEFORE creating the UNIQUE index, not after. The index creation fails if duplicates exist.

```sql
-- ❌ Wrong order: index creation fails if any (game_id, player_id) dupes exist
CREATE UNIQUE INDEX idx_player_game_logs_unique ON player_game_logs(game_id, player_id);
DELETE FROM player_game_logs WHERE rowid NOT IN (SELECT MIN(rowid) FROM player_game_logs GROUP BY game_id, player_id);

-- ✅ Correct order: deduplicate first, then create index
DELETE FROM player_game_logs
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM player_game_logs
    GROUP BY game_id, player_id
);
-- Now safe to create unique index
CREATE UNIQUE INDEX IF NOT EXISTS idx_player_game_logs_unique
ON player_game_logs(game_id, player_id);
```

**General deduplication template:**
```sql
-- Remove duplicate rows, keeping the first (lowest rowid) occurrence
DELETE FROM <table_name>
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM <table_name>
    GROUP BY <unique_columns_that_should_not_duplicate>
);
```

**Used in:** `data_sync.yml` "Ensure database indexes and data integrity" step.

---

## Pattern 2 — `CREATE TABLE IF NOT EXISTS` for Safe Migrations

**Rule:** All table creation in `database.py` must use `IF NOT EXISTS`. Never DROP a table to recreate it — this destroys production data.

```sql
-- ✅ Safe — won't fail if table already exists
CREATE TABLE IF NOT EXISTS rotation_profiles (
    player_id TEXT NOT NULL,
    team_abbreviation TEXT NOT NULL,
    avg_minutes REAL,
    synced_at TEXT NOT NULL,
    UNIQUE(player_id, team_abbreviation, season)
);

-- ❌ Never in production
DROP TABLE IF EXISTS rotation_profiles;
CREATE TABLE rotation_profiles (...);  -- deletes all data
```

**Adding columns to existing tables:**
```python
# Migration-safe column addition in database.py
def migrate_add_column(conn, table, column, column_type, default=None):
    """Add column if it doesn't exist — safe to run repeatedly."""
    existing = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}{default_clause}")
        print(f"✅ Added column {column} to {table}")
    else:
        print(f"   Column {column} already exists in {table} — skipping")
```

---

## Pattern 3 — Canonical ID Mapping

**Problem:** External APIs use different player ID formats. Tank01 changed from 7-digit NBA IDs to 11-digit composite IDs in Jan 2026. Without a mapping layer, you get 271+ duplicate player records.

```sql
-- Maps any external ID format to our canonical NBA ID
CREATE TABLE IF NOT EXISTS player_canonical_ids (
    input_id TEXT PRIMARY KEY,          -- the external ID (Tank01, BDL, etc.)
    canonical_id INTEGER NOT NULL,      -- our internal NBA ID (immutable)
    source TEXT NOT NULL,               -- 'tank01', 'bdl', 'manual'
    confidence REAL DEFAULT 1.0,        -- 1.0 = exact match, <1.0 = fuzzy
    player_name TEXT,                   -- for debugging
    created_at TEXT DEFAULT (datetime('now'))
);
```

**Auto-healing resolution in `database.py`:**
```python
def resolve_player_id(self, external_id: str) -> int:
    """Resolve any external ID format to canonical NBA ID."""
    # 1. Check canonical mapping first
    row = self.conn.execute(
        "SELECT canonical_id FROM player_canonical_ids WHERE input_id = ?",
        (str(external_id),)
    ).fetchone()
    if row:
        return row[0]

    # 2. If it looks like a Tank01 composite ID (11+ digits), extract embedded NBA ID
    if len(str(external_id)) > 10:
        # Tank01 format: {timestamp}{nba_id} — last 7 digits are NBA ID
        nba_id = int(str(external_id)[-7:])
        return nba_id

    # 3. Return as-is if it's already in NBA format (7 digits)
    return int(external_id)
```

---

## Pattern 4 — Composite Indexes for Query Performance

**Design for your most common query pattern:**

```sql
-- Most common query: get all stats for a player within a date range
-- ✅ Composite index puts player_id first — perfect for this pattern
CREATE INDEX IF NOT EXISTS idx_player_game_logs_player_date
ON player_game_logs(player_id, game_date);

-- For date-first queries (e.g., "all players on 2026-02-19")
CREATE INDEX IF NOT EXISTS idx_player_game_logs_game_date
ON player_game_logs(game_date);

-- For game_id lookup (Module H upserts)
CREATE UNIQUE INDEX IF NOT EXISTS idx_player_game_logs_unique
ON player_game_logs(game_id, player_id);
```

**Index naming convention:** `idx_{table}_{columns_joined_by_underscore}`

---

## Pattern 5 — Schedule Metadata vs Results Tables

**Design principle:** Tables that answer "did a game happen?" are fundamentally different from tables that answer "what happened in the game?". Keep them separate.

| `nba_calendar` (schedule metadata) | `games` (results + analytics) |
|------------------------------------|-------------------------------|
| Has a row for EVERY date | Only has rows for played/scheduled games |
| Includes off-days (has_games=0) | Never has rows for off-days |
| Used by workflow gates | Used by simulations and WOWY |
| Updated weekly from BDL schedule | Locked once game is Final |
| `has_games`, `game_count`, `season_phase` | Scores, lineups, referee crews, pace |

```sql
-- ✅ nba_calendar: pure schedule metadata
CREATE TABLE IF NOT EXISTS nba_calendar (
    date         TEXT PRIMARY KEY,      -- YYYY-MM-DD
    season       TEXT NOT NULL,         -- '2025-26'
    has_games    INTEGER NOT NULL DEFAULT 0,  -- 1 = game day, 0 = off day
    game_count   INTEGER DEFAULT 0,
    season_phase TEXT NOT NULL DEFAULT 'regular',  -- regular/playoffs/allstar_break/offseason
    notes        TEXT,
    synced_at    TEXT NOT NULL
);

-- ✅ games: analytics results (different purpose, different usage)
CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    home_team TEXT, away_team TEXT,
    home_score INTEGER, away_score INTEGER,
    referee_crew TEXT,
    ...
);
```

**Never query `games` table to determine if games exist today.** Use `nba_calendar` for scheduling decisions. The `games` table may be missing rows for legitimate reasons (Module H hasn't synced yet, game in progress).

---

## Pattern 6 — `synced_at` Column + Freshness Validation

**Every table populated by a sync script should have a `synced_at` column.** This allows `validate_schema.py` to detect stale data before it silently degrades the pipeline.

```sql
-- ✅ Every sync table includes synced_at
CREATE TABLE IF NOT EXISTS rotation_profiles (
    player_id TEXT NOT NULL,
    team_abbreviation TEXT NOT NULL,
    -- ... stats columns ...
    synced_at TEXT NOT NULL,   -- ← ISO timestamp of last sync
    UNIQUE(player_id, team_abbreviation, season)
);
```

**Freshness check in `validate_schema.py`:**
```python
def check_table_freshness(conn, table_name, max_stale_days=8):
    row = conn.execute(f"SELECT MAX(synced_at) FROM {table_name}").fetchone()
    last_sync = row[0] if row and row[0] else None

    if last_sync is None:
        return f"⚠️ {table_name}: no rows (never synced)"

    from datetime import datetime
    days_stale = (datetime.now() - datetime.fromisoformat(last_sync)).days
    if days_stale > max_stale_days:
        return f"⚠️ {table_name}: stale ({days_stale}d since last sync)"

    return f"✅ {table_name}: fresh ({days_stale}d ago)"
```

**Tables with freshness checks in `validate_schema.py`:**
- `nba_calendar` — max 8 days stale
- `rotation_profiles` — max 2 days stale
- `player_synergy_playtypes` — max 7 days stale

---

## Pattern 7 — `players.team` vs `player_game_logs.team_abbreviation`

**The most important data modeling rule in this codebase.** These two fields serve completely different purposes.

| Field | Meaning | Use for |
|-------|---------|---------|
| `players.team` | Current snapshot — player's team RIGHT NOW | Roster lists, lineup checks, current team context |
| `player_game_logs.team_abbreviation` | Historical truth — which team they played for on that game date | Stats queries, WOWY analysis, trade detection |

```python
# ❌ Wrong: using players.team for historical queries
cursor.execute("""
    SELECT AVG(pts) FROM player_game_logs
    WHERE player_id = ?
    AND team_abbreviation = (SELECT team FROM players WHERE player_id = ?)
    AND game_date >= date('now', '-30 days')
""", (player_id, player_id))
# Breaks after a trade — the player's old-team logs get excluded

# ✅ Right: query by player_id only for historical stats
cursor.execute("""
    SELECT AVG(pts) FROM player_game_logs
    WHERE player_id = ?
    AND game_date >= date('now', '-30 days')
""", (player_id,))

# ✅ Right: use players.team only for current team context
cursor.execute("SELECT team FROM players WHERE player_id = ?", (player_id,))
current_team = cursor.fetchone()[0]
```

**Trade detection pattern:**
```python
# Detect recently traded players: on team per players.team, but game logs are on old team
def is_freshly_traded(player_id, current_team, conn):
    # Games on current team in last 30 days
    row = conn.execute("""
        SELECT COUNT(*) FROM player_game_logs
        WHERE player_id = ? AND team_abbreviation = ? AND game_date >= date('now', '-30 days')
    """, (player_id, current_team)).fetchone()
    games_on_new_team = row[0]

    # Has game logs from ANY team in last 30 days
    row = conn.execute("""
        SELECT COUNT(*) FROM player_game_logs
        WHERE player_id = ? AND game_date >= date('now', '-30 days')
    """, (player_id,)).fetchone()
    total_recent_games = row[0]

    return games_on_new_team == 0 and total_recent_games > 0
```

---

## Pattern 8 — Self-Healing Daily Rebuild

**Some tables are cheaper to fully rebuild daily** than to track incremental changes (inserts, updates, deletes). This is especially true when the source data itself changes shape daily (rotation patterns, beneficiary relationships).

```python
# build_rotation_profiles.py — zero API calls, pure SQL
# Runs daily at 5 AM, completely rebuilds rotation_profiles and beneficiary_minutes

def rebuild_rotation_profiles(conn, window_days=21, min_games=3):
    """
    Full daily rebuild:
    1. Delete stale profiles (player on wrong team)
    2. Delete rows for players with too few recent games
    3. Rebuild all active player profiles from player_game_logs
    """
    # Step 1: Remove stale profiles (player changed teams)
    conn.execute("""
        DELETE FROM rotation_profiles
        WHERE (player_id, team_abbreviation) NOT IN (
            SELECT player_id, team FROM players WHERE status = 'Active'
        )
    """)

    # Step 2: Full rebuild for all active players
    conn.execute("""
        INSERT OR REPLACE INTO rotation_profiles (player_id, team_abbreviation, avg_minutes, synced_at)
        SELECT
            pgl.player_id,
            p.team,
            AVG(pgl.minutes),
            datetime('now')
        FROM player_game_logs pgl
        JOIN players p ON pgl.player_id = p.player_id
        WHERE pgl.game_date >= date('now', '-? days')
        GROUP BY pgl.player_id, p.team
        HAVING COUNT(*) >= ?
    """, (window_days, min_games))
```

**When to use self-healing rebuild vs incremental:**
- ✅ Rebuild: Derived/aggregated data (rotation profiles, beneficiary_minutes, team_scheme_cache, player_trends)
- ✅ Rebuild: Tables where staleness = just recompute from source data (zero API cost) — see `scripts/build_player_trends.py`
- ❌ Rebuild: Tables that hold raw API responses (player_game_logs, games, odds) — incremental only
- ❌ Rebuild: Tables with expensive API calls to re-populate — too slow daily

---

## Pattern 9 — Schema Constraint Validation

**Problem:** `ON CONFLICT` clause must match the ACTUAL constraint name in CREATE TABLE, not assumed column names. Mismatches cause silent insert failures.

**Example:**
```sql
-- ❌ Wrong: conflict clause doesn't match actual constraint
CREATE TABLE player_game_logs (
    player_id TEXT NOT NULL,
    game_date TEXT NOT NULL,
    pts INTEGER,
    UNIQUE(player_id, game_date)  -- Actual constraint
);
-- Later: ON CONFLICT(game_id, player_id) silently fails

-- ✅ Right: verify constraint before writing upsert
PRAGMA table_info(player_game_logs);
-- Then: ON CONFLICT(player_id, game_date) DO UPDATE
```

**Real incident:** Module H `ON CONFLICT(game_id, player_id)` wrong → actual constraint `(player_id, game_date)` — all inserts silently failed 8 days (Sprint 8).

---

## Known Data Quality Issues

### Tank01 ID Format Change (Jan 2026)
**Problem:** Tank01 switched from 7-digit NBA IDs to 11-digit composite IDs (format: `{timestamp}{nba_id}`)
**Impact:** 271+ duplicate player records before fix
**Fix:** `player_canonical_ids` table + `database.py` auto-healing resolution
**Reference:** `database.py` `resolve_player_id()` method

### BDL Team Abbreviation Mismatch
**Problem:** BDL uses GS/NO/NY/PHO/SA vs our standard GSW/NOP/NYK/PHX/SAS
**Impact:** Team joins silently fail, affecting WOWY and injury lookups
**Fix:** `normalize_bdl_abbr(abbr)` from `utils/mappings.py` — centralized Feb 24, idempotent. DO NOT add local dicts in new scripts. ESPN team IDs live in `canonical_teams` table (30 rows), not hardcoded dicts.

### Accent Mismatches — Two-Direction Problem
**Problem:** Accent mismatches go in two directions with different fixes:
1. Odds API / bet_recommendations → DB: "Jokic" must match "Jokić" in `player_injuries` (canonical has accent)
2. `players.name` → synergy/season tables: "Jokić" must match "Jokic" in BDL-sourced tables (no accent)

**Impact:** Haiku sanity gate receives "No injury on record" for OUT accented players → bad bets pass. Archetype classifier silently downgrades accented players to GENERALIST.

**Fix (direction 1 — resolve TO canonical):** `resolve_canonical_name(conn, name)` from `utils/player_id_resolver.py` — NFKD strip → look up `player_canonical_ids.normalized_name` → return `full_name` with correct accents. Graceful fallback if not found. Use before any Claude prompt injection.

**Fix (direction 2 — resolve AWAY FROM canonical):** `_strip_accents(name)` — `unicodedata.normalize('NFKD', name)` + strip `Mn` category chars. Try exact match first, then stripped form. Used in `classify_archetypes.py` synergy/season lookups.

### `players.team` After Trade
**Problem:** `players.team` snapshots current team; historical logs show old-team stats
**Impact:** Per-team stat queries exclude pre-trade performance
**Fix:** Always query `player_game_logs` by `player_id` only for historical stats; use `players.team` only for current context
**Reference:** Phase 8.12 — Roster Intelligence

---

## Pattern 10 — Game-Count Rolling Windows (Not Calendar Days)

**Problem:** Date-based rolling windows (e.g., `WHERE game_date >= date('now', '-21 days')`) produce extreme undersampling during scheduling gaps. The NBA All-Star break (Feb 13-20) left a 7-day gap — a "21-day" window during this period returned only 1-2 games per referee.

**Rule:** For any stat computed over "recent games" (referee fouls, player averages, team trends), use a **game-count window** (last N games) instead of a calendar-day cutoff.

```python
# ❌ Wrong: calendar-day window breaks during All-Star break, bye weeks, etc.
ROLLING_WINDOW_DAYS = 21
cursor.execute("""
    SELECT SUM(total_fouls) / COUNT(*)
    FROM referee_daily_stats
    WHERE referee_name = ?
    AND DATE(game_date) >= date('now', '-? days')
""", (name, ROLLING_WINDOW_DAYS))

# ✅ Right: game-count window — scheduling-agnostic
ROLLING_WINDOW_GAMES = 10  # ~2.5 weeks of regular-season play
cursor.execute("""
    SELECT date, total_fouls FROM referee_daily_stats
    WHERE referee_name = ?
    ORDER BY date DESC
""", (name,))
rows = cursor.fetchall()
last_n_games = rows[:ROLLING_WINDOW_GAMES]  # take first N from DESC list
rolling_avg = sum(r['total_fouls'] for r in last_n_games) / len(last_n_games)
```

**Applied in:** `scripts/learn_daily_trends.py` `update_rolling_and_season_stats()` — changed from 21-day calendar cutoff to last-10-games per referee (Feb 28, 2026). Result: all active refs now show 10 games in window regardless of break schedule.

**Rule of thumb:** 10 regular-season NBA games ≈ 2.5 calendar weeks of play.

---

## Pattern 11 — Team Score Derivation from `player_game_logs`

**Context:** When computing team scores from box scores (for H/A records, ATS splits, etc.) there is no clean single-row-per-game table. The `games` table has 3 game_id formats (3× row inflation). `team_standings_bdl` has corrupted data. `home_or_away` column in `player_game_logs` is NULL for BDL-sourced rows.

**Correct pattern:** SUM pts per (game_date, team_abbreviation) WITHOUT filtering on `home_or_away`, anchored via `canonical_games` for home/away assignment.

```sql
-- ✅ Correct: derive team scores without home_or_away filter
SELECT cg.date, cg.home_team, cg.away_team,
       h.home_score, a.away_score,
       h.home_score - a.away_score AS margin
FROM canonical_games cg
JOIN (
    SELECT game_date, team_abbreviation, SUM(pts) AS home_score
    FROM player_game_logs WHERE pts IS NOT NULL
    GROUP BY game_date, team_abbreviation
) h ON cg.date = h.game_date AND cg.home_team = h.team_abbreviation
JOIN (
    SELECT game_date, team_abbreviation, SUM(pts) AS away_score
    FROM player_game_logs WHERE pts IS NOT NULL
    GROUP BY game_date, team_abbreviation
) a ON cg.date = a.game_date AND cg.away_team = a.team_abbreviation
WHERE h.home_score >= 60 AND a.away_score >= 60  -- sanity gate: filters DNP-only rows
```

**Gotchas:**
- `AND pts < 60` on individual rows removes players who scored 60+ (Wilt Chamberlain problem). Filter at team-total level instead.
- `home_or_away = 'HOME'` filter excludes NULL rows from BDL sync — causes incomplete team totals.
- Use `canonical_games` as anchor (not `games`) to avoid 3× row inflation from duplicate game_id formats.

**ATS convention:** `positive spread = home team getting points (underdog)`. Home covers if `(home_score - away_score) + spread > 0`. Applied in `scripts/sync_team_betting_trends.py`.

**Applied in:** `scripts/sync_team_betting_trends.py` — produces 893 complete game scores with verified accuracy (Feb 28, 2026).

---

## Future Skill

**`/schema-audit`** — Database design review
- Analyzes schema for optimization opportunities
- Checks: missing indexes, tables without `synced_at`, constraint violations
- Validates: `nba_calendar` freshness, `rotation_profiles` freshness, canonical ID coverage
- Generates: schema health report + migration recommendations
