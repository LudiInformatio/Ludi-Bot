# Canonical Name Resolution — Best Practices

**Created:** February 24, 2026
**Applies to:** All code that passes player names to DB queries or Claude prompts

---

## The Problem

NBA player names exist in two incompatible forms across our data sources:

| Source | Format | Example |
|--------|--------|---------|
| Odds API | ASCII (no accents) | `Nikola Jokic` |
| ESPN displayName | Usually with accents | `Nikola Jokić` |
| BDL API | Mixed | `Nikola Jokić` or `Nikola Jokic` |
| `players.name` | With accents (canonical) | `Nikola Jokić` |
| `player_injuries.player_name` | With accents (after Feb 24 fix) | `Nikola Jokić` |
| `player_synergy_playtypes` | Without accents (strip-joined) | `Nikola Jokic` |

**Consequence:** A player name from the Odds API flowing into a DB query against `players.name` returns 0 rows — completely silent failure. This caused Claude prompts to receive "No injury on record" for players who were OUT.

---

## The Solution: Two Transforms for Two Directions

### Direction 1: Incoming name → canonical `full_name`
**Use when:** You have a raw name from an external API (Odds API, BDL, Tank01) and need to match it against our DB.

```python
from utils.player_id_resolver import resolve_canonical_name

# Usage
canonical = resolve_canonical_name(conn, "Nikola Jokic")
# Returns: "Nikola Jokić"

# Falls back gracefully — returns original name on any error
canonical = resolve_canonical_name(conn, "Unknown Player")
# Returns: "Unknown Player"
```

**How it works:**
1. NFKD-normalize the input (strips accents): `"Jokić"` → `"Jokic"`
2. Lowercase, strip suffixes (Jr./Sr./III)
3. Query `player_canonical_ids.normalized_name` for the match
4. Return the corresponding `full_name` (the accented version)

### Direction 2: Canonical name → accent-stripped for synergy tables
**Use when:** You have a canonical name and need to match against `player_synergy_playtypes` or similar tables that store stripped names.

```python
import unicodedata

def _strip_accents(name: str) -> str:
    nfd = unicodedata.normalize('NFD', name)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')

# Usage: try exact first, fallback to stripped
result = db.query("SELECT * FROM player_synergy_playtypes WHERE player_name = ?", [name])
if not result:
    result = db.query("SELECT * FROM player_synergy_playtypes WHERE player_name = ?", [_strip_accents(name)])
```

---

## Where to Apply

### Always call `resolve_canonical_name()` when:
- A name comes from the **Odds API** before any DB query
- A name comes from **BDL** before writing to `player_injuries`
- Passing player names into **Claude prompts** (injury context, spotlight analysis)
- Querying hit rates, trends, or trends by player name

### Do NOT call it when:
- You already have a value from `players.name` or `player_canonical_ids.full_name` — it's already canonical
- Writing to `player_canonical_ids.normalized_name` — that column stores the stripped form intentionally

### Current injection points (as of Feb 24, 2026):
| File | Location | Purpose |
|------|----------|---------|
| `scripts/curate_plays.py` | `_fetch_player_injury()` | Haiku sanity gate injury lookup |
| `morning_brief.py` | Hit rate query + spotlight | Morning/evening brief player cards |
| `scripts/trend_engine.py` | `get_matchup_analysis()` | All 5 matchup analysis helpers |
| `scripts/classify_archetypes.py` | `get_player_synergy()` + `get_player_season_advanced()` | Archetype classification batch |

---

## The `player_canonical_ids` Table

This is the single source of truth for name normalization.

```sql
CREATE TABLE player_canonical_ids (
    canonical_id    TEXT PRIMARY KEY,   -- NBA official player ID
    normalized_name TEXT,               -- accent-stripped lowercase (lookup key)
    full_name       TEXT,               -- accented canonical name (return value)
    team            TEXT,
    sportsdata_id   TEXT,
    dk_player_id    TEXT,
    fd_player_id    TEXT,
    espn_id         TEXT                -- added Feb 24, 2026
);
```

**`normalized_name` convention:** lowercase, accents stripped via NFD decomposition, suffixes removed (Jr./Sr./III). Example: `"Jusuf Nurkić Jr."` → `"jusuf nurkic"`.

**IMPORTANT:** Do NOT use `normalized_name` as a display name — it's a lookup key only. Always use `full_name` for display.

---

## The `canonical_teams` Table

Single source of truth for team abbreviation mapping across all APIs.

```sql
SELECT * FROM canonical_teams WHERE standard_abbr = 'GSW';
-- standard_abbr='GSW', bdl_abbr='GS', tank01_abbr='GSW', espn_id=...
```

### Normalize BDL abbreviations

```python
from utils.mappings import normalize_bdl_abbr

normalize_bdl_abbr('GS')   # → 'GSW'
normalize_bdl_abbr('GSW')  # → 'GSW'  (idempotent)
normalize_bdl_abbr('NO')   # → 'NOP'
normalize_bdl_abbr('NY')   # → 'NYK'
normalize_bdl_abbr('PHO')  # → 'PHX'
normalize_bdl_abbr('SA')   # → 'SAS'
```

**Rule:** Call `normalize_bdl_abbr()` on any abbreviation that came from BDL before comparing to `players.team` or any other internal table.

---

## The `sync_injuries.py` Name Resolution Pattern

The injury sync pipeline demonstrates the correct pattern for resolving names from multiple sources:

```python
def _normalize_for_canonical(name: str) -> str:
    """Strips accents + removes suffixes for canonical_ids lookup."""
    import unicodedata
    # NFD decompose → drop combining characters
    nfd = unicodedata.normalize('NFD', name)
    stripped = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    # Remove common suffixes
    for suffix in [' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii']:
        if stripped.lower().endswith(suffix):
            stripped = stripped[:len(stripped)-len(suffix)]
    return stripped.strip().lower()

def _get_canonical_lookup_from_db(conn) -> dict:
    """Returns {normalized_name: (full_name, team)} for all players."""
    cursor = conn.execute(
        "SELECT normalized_name, full_name, team FROM player_canonical_ids"
    )
    return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
```

---

## Common Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Claude receives "No injury on record" for OUT player | Accent mismatch in injury query | Call `resolve_canonical_name()` before query |
| Player gets GENERALIST archetype despite having synergy data | `get_player_synergy()` exact match failed | Use `_strip_accents()` fallback in synergy lookup |
| `team_abbreviation = ''` in `player_injuries` | BDL/RSS returned non-accented name, `players.name` lookup failed | Use canonical lookup in `sync_to_database()` |
| Trend engine returns no data for player | `_resolve_player_id()` failed all 3 tiers | Tier 4 canonical fallback in `trend_engine.py` |
| 7 duplicate rows for same player in `player_injuries` | Missing dedup guard | `INSERT ... WHERE NOT EXISTS (same player/status/date)` |

---

## Ludi-Lite Comparison

Ludi-Lite uses `normalize_for_crosswalk()` which is more aggressive: strips apostrophes and hyphens (`"De'Aaron"` → `"deaaron"`). Our `normalized_name` preserves apostrophes/hyphens (e.g. `"de'aaron fox"`). This difference means ~5-10 edge-case players won't match across systems. Low priority to reconcile.
