# New Best Practices from Feb 2026 Audit + Bug Fixes

**Source:** 10-sprint comprehensive audit (Feb 21, 2026) + Title Mode/Defensive Playtype bug fixes
**Status:** Proposal — ready to integrate into `best-practices/`

This document contains 10 new patterns discovered during the audit and post-audit bug fixes. These are production-validated patterns that prevented or fixed real incidents.

---

## Coding Patterns (Add to `best-practices/coding/README.md`)

### Pattern 7 — Module-Level Constants for Configuration

**Problem:** Categorical logic (stat types, team schemes, archetype lists) scattered across functions makes it hard to maintain and extend.

**Solution:** Define configuration lists at module level as constants.

```python
# ✅ Module-level constants at top of file
OFFENSIVE_STATS = ['PTS', 'AST', '3PM', 'TOV', 'FGA', 'FTA', 'OREB']
DEFENSIVE_STATS = ['STL', 'BLK', 'DREB']
TOTAL_REB_STAT = ['REB']
MINUTES_STAT = ['MIN']

def get_matchup_analysis(player_name, opponent_abbr, cursor, stat_category='PTS'):
    """Routes to appropriate data source based on stat category."""
    stat_upper = stat_category.upper()

    if stat_upper in OFFENSIVE_STATS:
        return _get_offensive_matchup(player_name, opponent_abbr, cursor)
    elif stat_upper in DEFENSIVE_STATS:
        return _get_defensive_matchup(player_name, opponent_abbr, cursor)
    # ...
```

**Why module-level?**
- Single source of truth — change in one place
- Easy to extend (add new stat type, add to list)
- Self-documenting (reader sees all categories at top of file)
- Testable (can write tests that verify coverage of all stat types)

**When to use:**
- Categorization logic that might need to be extended
- Configuration that multiple functions share
- Enums/constants that define system behavior

**Real example:** `utils/trend_engine.py` lines 392-395 (defensive playtype bug fix)

---

### Pattern 8 — Helper Function Extraction for Complex Logic

**Problem:** Functions with multiple conditional branches doing completely different things are hard to test, debug, and understand.

**Solution:** Extract each branch into a focused helper function with a clear name.

```python
# ❌ Before: 150-line function with 4 different code paths
def get_matchup_analysis(player_name, opponent_abbr, cursor, stat_category='PTS'):
    try:
        if stat_category in OFFENSIVE_STATS:
            # 40 lines of Synergy playtype logic
            playtypes = cursor.execute("""...""").fetchall()
            # ... complex formatting ...
            return playtype_str
        elif stat_category in DEFENSIVE_STATS:
            # 35 lines of player_defense logic
            defense = cursor.execute("""...""").fetchall()
            # ... complex formatting ...
            return defense_str
        # ... 2 more branches
    except Exception:
        return ""

# ✅ After: Main function routes, helpers do the work
def get_matchup_analysis(player_name, opponent_abbr, cursor, stat_category='PTS'):
    """Routes to appropriate helper based on stat category."""
    try:
        if stat_category in OFFENSIVE_STATS:
            return _get_offensive_matchup(player_name, opponent_abbr, cursor, scheme)
        elif stat_category in DEFENSIVE_STATS:
            return _get_defensive_matchup(player_name, opponent_abbr, cursor, scheme)
        elif stat_category in TOTAL_REB_STAT:
            return _get_rebound_matchup(player_name, opponent_abbr, cursor, scheme)
        elif stat_category in MINUTES_STAT:
            return _get_minutes_matchup(player_name, cursor)
        return ""
    except Exception:
        return ""

def _get_offensive_matchup(player_name, opponent_abbr, cursor, scheme):
    """Handle offensive stat categories (PTS, AST, 3PM, TOV, FGA, FTA, OREB)."""
    playtypes = cursor.execute("""
        SELECT playtype, ppp, freq_pct, percentile
        FROM player_synergy_playtypes
        WHERE player_name = ? AND ppp IS NOT NULL
        ORDER BY freq_pct DESC LIMIT 2
    """, (player_name,)).fetchall()

    if not playtypes:
        return ""

    # ... formatting logic ...
    return f"{playtype_str} vs {scheme} defense"

def _get_defensive_matchup(player_name, opponent_abbr, cursor, scheme):
    """Handle defensive stat categories (STL, BLK, DREB)."""
    # ... focused defensive logic ...
```

**Benefits:**
- Each helper is testable in isolation
- Single Responsibility Principle (SRP)
- Easier to debug (stack trace points to specific helper)
- Easier to extend (add new helper for new stat type)

**Naming convention for helpers:**
- Prefix with `_` to signal "internal helper, not part of public API"
- Use verb + noun pattern: `_get_offensive_matchup`, `_calculate_edge`, `_format_bet_card`

**Real example:** `utils/trend_engine.py` lines 443-539 (defensive playtype bug fix)

---

### Pattern 9 — Default Parameters for Backward Compatibility

**Problem:** Adding a new required parameter to an existing function breaks all existing callers.

**Solution:** Use default parameter values that preserve old behavior.

```python
# ❌ Breaking change — all callers must be updated immediately
def get_matchup_analysis(player_name, opponent_abbr, cursor, stat_category):
    # Now requires stat_category — breaks all old callers

# ✅ Non-breaking change — old callers still work
def get_matchup_analysis(player_name, opponent_abbr, cursor, stat_category='PTS'):
    # Default to 'PTS' (most common) — old callers get offensive data as before
```

**When to use default parameters:**
- Adding new functionality to existing function
- Allowing incremental migration (update callers over time)
- Most common use case should be the default

**Default value guidelines:**
| Default | When to use |
|---------|------------|
| `None` | When absence of value has special meaning (e.g., "use current date") |
| Most common value | When one value is used 80%+ of the time (e.g., `stat_category='PTS'`) |
| Empty container | When function aggregates results (e.g., `tags=[]`) |
| Sensible fallback | When there's a "safe" default (e.g., `title="LUDI GAME BRIEF"`) |

**Real examples:**
- `trend_engine.py:398` — `stat_category='PTS'` (defensive playtype bug fix)
- `module_f.py:961` — `title="LUDI GAME BRIEF"` (title mode bug fix)

**Migration path:**
1. Add parameter with default value (non-breaking)
2. Update callers incrementally to pass explicit value
3. (Optional) After all callers updated, remove default to make it required

---

### Pattern 10 — Comprehensive Docstrings with Examples

**Problem:** Functions with conditional behavior are hard to understand without reading the implementation.

**Solution:** Include example outputs for each major code path in the docstring.

```python
# ❌ Minimal docstring — reader must trace code to understand outputs
def get_matchup_analysis(player_name, opponent_abbr, cursor, stat_category='PTS'):
    """Get matchup analysis for player."""
    # ... 100 lines of conditional logic

# ✅ Comprehensive docstring — reader sees all outputs at a glance
def get_matchup_analysis(player_name, opponent_abbr, cursor, stat_category='PTS'):
    """
    Build a structured archetype-vs-scheme matchup block for Spotlight cards.
    Returns a 1-2 line string, or empty string if data unavailable.

    Example outputs:
    - PTS OVER: "P&R Handler (1.18 PPP, 22%) | ISO (0.95 PPP, 18%) vs BLITZ defense"
    - BLK OVER: "Defends 18% of possessions | Allows 42.3% FG (-4.1% vs avg) vs P&R_HEAVY offense"
    - REB OVER: "Putbacks (1.12 PPP, 8%) | Defends 21% (DREB context)"
    - MIN OVER: "Starter: 34.2 avg | B2B: 31.5 | Blowout: 28.3 | Close: 36.1"

    Args:
        player_name: Player's full name (e.g., "LeBron James")
        opponent_abbr: Opponent's 3-letter team abbreviation (e.g., "GSW")
        cursor: SQLite cursor for database queries
        stat_category: Stat type (e.g., "PTS", "BLK", "REB", "MIN")

    Returns:
        Formatted matchup string, or empty string if no data available
    """
    # ... implementation
```

**What makes a docstring "comprehensive":**
- Clear one-line summary
- Example outputs for each major code path
- Explicit parameter types and formats
- Return value type and edge cases
- Notes about data sources or assumptions

**When to write comprehensive docstrings:**
- Functions with multiple return formats (conditional behavior)
- Public API functions called from multiple modules
- Complex logic that isn't self-evident from the code
- Functions used by AI/Claude (helps with code generation)

**Real example:** `utils/trend_engine.py:398-408` (defensive playtype bug fix)

---

## Data Modeling Patterns (Add to `best-practices/data-modeling/README.md`)

### Pattern 9 — Schema Constraint Validation

**Problem:** Code assumptions about database constraints don't match actual schema, causing silent failures.

**Real incident:** Module H used `ON CONFLICT(game_id, player_id)` but the actual unique constraint was `(player_id, game_date)`. All inserts silently failed for 8 days.

**Solution:** Validate constraints before writing upsert logic.

```bash
# Check actual constraints on a table
sqlite3 ludi.db "PRAGMA table_info(player_game_logs);"
sqlite3 ludi.db "PRAGMA index_list(player_game_logs);"
sqlite3 ludi.db "PRAGMA index_info(idx_player_game_logs_unique);"

# Output shows ACTUAL constraint is (player_id, game_date), not (game_id, player_id)
```

**Fix pattern:**
```python
# ❌ Wrong: Code assumes (game_id, player_id) constraint
conn.execute("""
    INSERT INTO player_game_logs (game_id, player_id, game_date, pts, reb, ast)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(game_id, player_id) DO UPDATE SET pts = excluded.pts
""", row)
# Silently fails — constraint doesn't exist, inserts duplicate rows

# ✅ Right: Code matches actual schema constraint
conn.execute("""
    INSERT INTO player_game_logs (game_id, player_id, game_date, pts, reb, ast)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(player_id, game_date) DO UPDATE SET pts = excluded.pts
""", row)
```

**Validation checklist before writing upsert logic:**
1. Read schema: `PRAGMA table_info(table_name)`
2. List indexes: `PRAGMA index_list(table_name)`
3. Check constraint columns: `PRAGMA index_info(index_name)`
4. Verify `ON CONFLICT` clause matches actual constraint

**Add to migration scripts:**
```python
def validate_constraint_exists(conn, table, columns):
    """Verify that expected constraint actually exists in DB."""
    indexes = conn.execute(f"PRAGMA index_list({table})").fetchall()
    for idx in indexes:
        idx_name = idx[1]
        idx_cols = conn.execute(f"PRAGMA index_info({idx_name})").fetchall()
        col_names = [row[2] for row in idx_cols]
        if col_names == columns:
            return True
    raise ValueError(f"Expected constraint on {columns} not found in {table}")

# Usage
validate_constraint_exists(conn, 'player_game_logs', ['player_id', 'game_date'])
```

**Reference:** Sprint 1 audit findings, `module_h_historian.py` lines 67+174 fix

---

### Pattern 10 — Context-Aware Data Routing

**Problem:** Different use cases need different data sources, but using a single function for all cases leads to wrong data being returned.

**Real incident:** Defensive stats (BLK, STL) were getting offensive playtype data (P&R Handler PPP) because `get_matchup_analysis()` always queried `player_synergy_playtypes` table.

**Solution:** Route to appropriate data source based on context.

```python
# ❌ Before: One data source for all stats
def get_matchup_analysis(player_name, opponent_abbr, cursor):
    # Always queries offensive data
    playtypes = cursor.execute("""
        SELECT playtype, ppp, freq_pct FROM player_synergy_playtypes
        WHERE player_name = ?
    """, (player_name,)).fetchall()
    return f"P&R Handler ({ppp} PPP) vs {scheme}"  # Wrong for BLK/STL!

# ✅ After: Context-aware routing
def get_matchup_analysis(player_name, opponent_abbr, cursor, stat_category='PTS'):
    if stat_category in OFFENSIVE_STATS:  # PTS, AST, 3PM
        return _get_offensive_matchup(player_name, cursor)  # Uses player_synergy_playtypes
    elif stat_category in DEFENSIVE_STATS:  # STL, BLK, DREB
        return _get_defensive_matchup(player_name, cursor)  # Uses player_defense
    elif stat_category in TOTAL_REB_STAT:  # REB
        return _get_rebound_matchup(player_name, cursor)   # Uses BOTH tables
    # ...
```

**Context-aware data mapping:**
| Stat Category | Data Source | Metrics |
|--------------|-------------|---------|
| Offensive (PTS/AST/3PM) | `player_synergy_playtypes` | PPP (Points Per Possession) |
| Defensive (STL/BLK/DREB) | `player_defense` | freq_pct, dfg_pct, diff_pct |
| Total Rebounds (REB) | Both tables | Putbacks (offensive) + DREB context (defensive) |
| Minutes (MIN) | `rotation_profiles` | Role, avg_minutes by context (B2B/close/blowout) |

**When to use context-aware routing:**
- Same logical operation (e.g., "get matchup analysis") but different data sources depending on input
- Different business logic for different categories (e.g., offensive vs defensive stats)
- Different output formats needed based on context

**Implementation pattern:**
1. Define category constants at module level
2. Main function routes based on category
3. Helper functions handle specific contexts
4. Each helper queries appropriate data source

**Reference:** Defensive playtype bug fix, `utils/trend_engine.py` lines 392-539

---

### Pattern 11 — Defensive Queries with Graceful Degradation

**Problem:** Missing data in enrichment tables (Synergy, defense, rotation profiles) shouldn't crash the pipeline.

**Solution:** Enrichment queries return empty string when data unavailable, allowing pipeline to continue.

```python
# ✅ Helper function with graceful degradation
def _get_offensive_matchup(player_name, opponent_abbr, cursor, scheme):
    """Handle offensive stat categories (PTS, AST, 3PM, TOV, FGA, FTA, OREB)."""
    playtypes = cursor.execute("""
        SELECT playtype, ppp, freq_pct, percentile
        FROM player_synergy_playtypes
        WHERE player_name = ? AND ppp IS NOT NULL
        ORDER BY freq_pct DESC LIMIT 2
    """, (player_name,)).fetchall()

    # Graceful degradation: no data = empty string, not crash
    if not playtypes:
        return ""  # Spotlight card just won't have matchup analysis

    # ... format and return data ...
    return f"{playtype_str} vs {scheme} defense"
```

**When to use graceful degradation:**
| Data Type | Strategy | Why |
|-----------|---------|-----|
| Core pipeline data (game logs, odds) | Fail loudly | Missing data = broken bets, must fix |
| Enrichment data (Synergy, trends, Claude) | Degrade gracefully | Nice-to-have, pipeline works without it |
| Sync script failures | Log error + continue | Other data still needs to sync |

**Graceful degradation checklist:**
1. Query might return zero rows (player not in table)
2. Check `if not rows:` before processing
3. Return safe default (empty string, None, fallback value)
4. Log when degradation occurs (for monitoring)
5. Document in docstring that function can return empty/None

**Example use cases:**
- `get_matchup_analysis()` — returns `""` if no Synergy data
- `get_beneficiary_context()` — returns `""` if player not in beneficiary_minutes
- `get_stagger_context()` — returns `""` if no stagger data
- Claude spotlight generation — returns deterministic fallback if API fails

**Reference:** All helper functions in `utils/trend_engine.py` defensive playtype bug fix

---

## Debugging Patterns (Add to `best-practices/debugging/README.md`)

### Pattern 7 — Parameter Propagation Debugging

**Problem:** Parameter exists in some parts of call chain but doesn't reach final destination, causing hardcoded values to be used instead.

**Real incident:** Title mode bug — `report_title` correctly set in `morning_brief.py`, passed to `generate_report()`, but never passed to `create_daily_briefing()`, so hardcoded "LUDI ELITE BRIEFING" was always used.

**Debugging workflow:**

```bash
# Step 1: Find where parameter is first set
grep -rn "report_title" morning_brief.py
# Output: Line 295-301 sets report_title based on self.mode

# Step 2: Trace forward through call chain
grep -rn "generate_report" morning_brief.py
# Output: Line 309 passes title=report_title

grep -rn "def generate_report" module_f.py
# Output: Line 558 has title parameter

grep -rn "create_daily_briefing" module_f.py
# Output: Line 560 calls it — but NO title parameter passed!

# Step 3: Check function signature
grep -A 3 "def create_daily_briefing" module_f.py
# Output: Line 961 has NO title parameter in signature

# Step 4: Check usage
grep -A 5 "def create_daily_briefing" module_f.py
# Output: Line 963 hardcodes "LUDI ELITE BRIEFING"
```

**Parameter propagation checklist:**
1. Where is parameter first set? (grep for variable name)
2. Is it passed to next function? (grep for function call)
3. Does that function accept it? (grep for `def function_name`)
4. Does that function pass it forward? (grep inside function body)
5. Does final destination use it? (grep for usage)

**Visual trace of title mode bug:**
```
morning_brief.py:295-301
  ↓ Sets report_title correctly based on self.mode
morning_brief.py:309
  ↓ Passes title=report_title to generate_report() ✓
module_f.py:558
  ↓ Receives title parameter ✓
module_f.py:560
  ✗ Calls create_daily_briefing(all_props) — MISSING title!
module_f.py:961
  ✗ def create_daily_briefing(self, props) — NO title parameter
module_f.py:963
  ✗ Hardcodes "LUDI ELITE BRIEFING" instead of using {title}
```

**Reference:** Title mode bug fix, `module_f.py` lines 560, 961, 963

---

### Pattern 8 — Schema Mismatch Debugging

**Problem:** Upsert queries silently fail (no error, but rows don't insert/update) due to wrong constraint in `ON CONFLICT` clause.

**Debugging workflow:**

```bash
# Step 1: Verify row count isn't increasing
sqlite3 ludi.db "SELECT COUNT(*) FROM player_game_logs;"
# Expected: ~18k rows (increases daily)
# Actual: 9,847 rows (hasn't changed in 8 days)

# Step 2: Check what constraints actually exist
sqlite3 ludi.db "PRAGMA table_info(player_game_logs);"
# Shows columns but not constraints

sqlite3 ludi.db "PRAGMA index_list(player_game_logs);"
# Output:
# seq | name | unique | origin | partial
# 0   | idx_player_game_logs_unique | 1 | c | 0

# Step 3: Check what columns the unique constraint covers
sqlite3 ludi.db "PRAGMA index_info(idx_player_game_logs_unique);"
# Output:
# seqno | cid | name
# 0     | 2   | player_id
# 1     | 3   | game_date
# ↑ ACTUAL constraint is (player_id, game_date)

# Step 4: Check what code assumes
grep -n "ON CONFLICT" module_h_historian.py
# Line 67: ON CONFLICT(game_id, player_id)
# ↑ WRONG — constraint doesn't exist!

# Step 5: Fix code to match schema
# Change ON CONFLICT(game_id, player_id) → ON CONFLICT(player_id, game_date)
```

**Symptoms of schema mismatch:**
- Table row count doesn't increase despite sync running
- No SQL errors in logs
- `INSERT OR REPLACE` inserts duplicate rows instead of updating
- `ON CONFLICT DO UPDATE` doesn't update

**Reference:** Sprint 1 audit findings, Module H bug fix

---

## Summary

| Category | New Patterns | Key Incidents Prevented |
|----------|-------------|------------------------|
| Coding | 4 (module constants, helper extraction, default params, docstrings) | Parameter propagation bugs, hard-to-maintain conditional logic |
| Data Modeling | 3 (schema validation, context routing, graceful degradation) | Silent upsert failures, wrong data for context, missing data crashes |
| Debugging | 2 (parameter trace, schema mismatch) | 8-day data staleness, hardcoded values bug |

**Total:** 10 production-validated patterns ready to integrate

**Next Steps:**
1. Review this proposal
2. Integrate patterns into respective `best-practices/` files
3. Update `best-practices/README.md` to reflect new pattern counts
4. Cross-reference from MEMORY.md where relevant

---

**Created:** February 21, 2026
**Source:** Comprehensive audit (Sprints 0-10) + Post-audit bug fixes
**Status:** Ready for integration
