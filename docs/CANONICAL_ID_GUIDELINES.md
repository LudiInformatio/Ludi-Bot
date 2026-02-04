# Canonical ID Guidelines

**Created:** February 3, 2026
**Phase:** 6.5d - Canonical ID System Audit
**Purpose:** Standards for player ID handling in Ludi-Bot

---

## Overview

The Canonical ID System prevents Tank01 API ID pollution by resolving composite IDs to canonical NBA Player IDs. All player identification should flow through the `PlayerIDResolver` utility.

### Why This Matters

Tank01 API sometimes returns composite IDs (10+ digits like `28398804489`) instead of canonical NBA IDs (4-7 digits like `1629029`). Without resolution:
- Database joins fail silently
- Player stats don't aggregate correctly
- Downstream modules receive inconsistent data

---

## Architecture

### Data Flow

```
Tank01 API Response
       ↓
Module H (Historian)
       ↓
PlayerIDResolver._resolve_player_id()
       ↓
Canonical ID written to player_game_logs
       ↓
main.py reads clean data
       ↓
Modules C, E, F process in-memory
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `PlayerIDResolver` | `utils/player_id_resolver.py` | Centralized resolution logic |
| `player_canonical_ids` | `ludi.db` | Mapping table (507+ players) |
| `_resolve_player_id()` | `module_h_historian.py:76` | Integration hook |

---

## Using PlayerIDResolver

### When to Use

**ALWAYS** use `PlayerIDResolver` when:
1. Writing player IDs to the database
2. Looking up player information by ID
3. Handling data from external APIs (Tank01, The-Odds-API)

### Code Examples

```python
from utils.player_id_resolver import PlayerIDResolver

# Initialize (singleton pattern available)
resolver = PlayerIDResolver(db_path="ludi.db")

# Resolve any input to canonical ID
canonical_id = resolver.resolve_to_canonical_id("Luka Dončić")    # Name with accent
canonical_id = resolver.resolve_to_canonical_id("luka doncic")    # Normalized name
canonical_id = resolver.resolve_to_canonical_id("28398804489")    # Tank01 composite ID
canonical_id = resolver.resolve_to_canonical_id("1629029")        # Already canonical

# Get full player info
player = resolver.get_player_info("Giannis Antetokounmpo")
# Returns: {'canonical_id': '203507', 'full_name': 'Giannis Antetokounmpo', ...}
```

### Integration Pattern (Module H Style)

```python
def _resolve_player_id(self, tank01_id: str, player_name: str) -> str:
    """Resolve Tank01 ID to canonical format before DB write."""
    if not tank01_id:
        return '0'

    try:
        # Try ID-based resolution first
        return self.resolver.resolve_to_canonical_id(str(tank01_id))
    except ValueError:
        try:
            # Fall back to name-based resolution
            return self.resolver.resolve_to_canonical_id(player_name)
        except ValueError:
            # Log warning for new players
            print(f"⚠️ No canonical ID for: {player_name} ({tank01_id})")
            return str(tank01_id)  # Return original if no match
```

---

## Adding New Players

### When a New Player Appears

If `PlayerIDResolver` can't resolve a player:
1. Check if they're a G-League/two-way player (may not have NBA ID)
2. Search NBA.com for their official Player ID
3. Add to `player_canonical_ids` table

### Adding Canonical IDs

```python
# Option 1: Direct SQL
INSERT INTO player_canonical_ids
(canonical_id, full_name, normalized_name, team, position, is_active, tank01_aliases)
VALUES ('1630639', 'A.J. Lawson', 'aj lawson', 'MIN', 'G', 1, '[]');

# Option 2: Use script
python scripts/add_missing_tank01_aliases.py
```

### Adding Tank01 Aliases

When Tank01 returns a new composite ID for an existing player:

```python
from utils.player_id_resolver import PlayerIDResolver

resolver = PlayerIDResolver()
resolver.add_alias('1630639', '94724422047')  # Add Tank01 ID as alias
resolver.clear_cache()  # Clear cache after bulk updates
```

---

## ID Format Reference

### Canonical NBA IDs
- **Format:** 4-7 digit numbers
- **Examples:** `203507`, `1629029`, `201566`
- **Source:** stats.nba.com

### Tank01 Composite IDs
- **Format:** 10-12 digit numbers
- **Examples:** `28398804489`, `941742772339`
- **Pattern:** Often start with `28`, `94`, `287`

### G-League Players
- Some players only have Tank01 IDs (no official NBA ID)
- Their Tank01 ID becomes their canonical ID in our system
- These are tracked in `player_canonical_ids` with their Tank01 ID as primary

---

## Database Schema

### player_canonical_ids Table

```sql
CREATE TABLE player_canonical_ids (
    canonical_id TEXT PRIMARY KEY,       -- NBA ID or Tank01 ID
    full_name TEXT NOT NULL,             -- "Luka Dončić" (with accents)
    normalized_name TEXT NOT NULL UNIQUE, -- "luka doncic" (ASCII)
    team TEXT,                           -- "DAL"
    position TEXT,                       -- "G", "F", "C"
    is_active INTEGER DEFAULT 1,
    tank01_aliases TEXT,                 -- JSON array: ["28398804489"]
    nba_api_id TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Resolution Priority

1. **Direct match** on `canonical_id`
2. **Normalized name match** on `normalized_name`
3. **Alias search** in `tank01_aliases` JSON arrays

---

## Validation & Monitoring

### Health Check Query

```sql
-- Count dirty IDs in player_game_logs
SELECT
    COUNT(*) as total,
    SUM(CASE WHEN LENGTH(player_id) > 8 THEN 1 ELSE 0 END) as dirty,
    SUM(CASE WHEN LENGTH(player_id) <= 8 THEN 1 ELSE 0 END) as clean
FROM player_game_logs;
```

### Target Metrics
- **Clean ID ratio:** > 99.5%
- **Unresolvable IDs:** < 50 records (G-League players)
- **All dirty IDs in canonical_ids:** 100%

### Automated Validation (CI)

Run validation script in `data_sync.yml`:
```yaml
- name: Validate Canonical IDs
  run: python scripts/validate_canonical_ids.py --warn-threshold 50
```

---

## Troubleshooting

### "Player not found" Error

1. Check if player exists in `player_canonical_ids`
2. Try resolving by name instead of ID
3. Check for accent differences (Dončić vs Doncic)
4. Add player if truly new

### Cache Issues

```python
resolver = PlayerIDResolver()
resolver.clear_cache()  # Clear after DB updates
```

### New Tank01 ID Format

If Tank01 changes their ID format:
1. Log examples of new format
2. Update alias registration scripts
3. Run migration for existing data

---

## Best Practices

### DO:
- Use `PlayerIDResolver` for all player ID operations
- Log warnings for unresolvable IDs (helps identify new players)
- Clear cache after bulk database updates
- Add aliases when discovering new Tank01 composite IDs

### DON'T:
- Write raw Tank01 IDs directly to database
- Skip resolution for "known" players (IDs can change)
- Assume short IDs are always canonical (validate)
- Store player names as primary identifiers (use canonical_id)

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-02-03 | Initial creation (Phase 6.5d) | Claude Sonnet 4.5 |
| 2026-02-03 | Added 13 G-League players to canonical_ids | Claude Opus 4.5 |
| 2026-02-03 | Added 3 NBA player aliases (AJ Lawson, etc.) | Claude Opus 4.5 |
