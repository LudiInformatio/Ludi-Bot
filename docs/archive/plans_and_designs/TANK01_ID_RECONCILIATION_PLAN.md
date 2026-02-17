# Tank01 Player ID Reconciliation - Final Strategy

**Date:** January 20, 2026 @ 02:40 AM EST  
**Severity:** HIGH - Blocking Week 2 implementation  
**Status:** Analysis Complete → Ready for Implementation

---

## Executive Summary

**Root Cause Confirmed:** Tank01 API changed player IDs around Jan 1-2, 2026, creating **271+ duplicate player records** in the `players` table.

**Critical Finding:** You have **THREE simultaneous issues**:
1. ❌ **Duplicate Players:** Giannis exists 3 times with different IDs (203507, 28118035349, giannis_antetokounmpo_mil)
2. ❌ **Accent Mismatches:** "Luka Dončić" (with accent) vs "Luka Doncic" (without) are separate records
3. ✅ **Tracking Data is GOOD:** `player_game_tracking` table uses correct NBA IDs consistently

**Recommended Solution:** **Hybrid Canonical ID System** (combines ID + Name normalization)

---

## Current State Analysis

### Players Table (983 records, but many duplicates)

| Player | ID Format | ID Value | Source | Status |
|--------|-----------|----------|--------|--------|
| Giannis | NBA ID | `203507` | NBA API | ✅ KEEP |
| Giannis | New Tank01 | `28118035349` | Tank01 (Jan 2026) | ❌ DELETE |
| Giannis | String Slug | `giannis_antetokounmpo_mil` | Legacy | ❌ DELETE |
| Luka | NBA ID | `1629029` | NBA API | ✅ KEEP |
| Luka (no accent) | New Tank01 | `28398804489` | Tank01 (Jan 2026) | ❌ DELETE |
| Jokić | NBA ID | `203999` | NBA API | ✅ KEEP |
| Jokic (no accent) | New Tank01 | `28908111729` | Tank01 (Jan 2026) | ❌ DELETE |

**ID Length Distribution:**
- Min: 4 chars (NBA IDs like `2544` for LeBron)
- Max: 25 chars (String slugs like `giannis_antetokounmpo_mil`)
- **New Tank01 IDs:** 11 digits (e.g., `28118035349`)

### Tracking Tables (GOOD - No duplicates)

`player_game_tracking` uses **`nba_player_id`** column with correct NBA IDs:
- Luka: `1629029` ✅
- Giannis: `203507` ✅ (not the new 28118035349)
- Data from Jan 1-5, 2026 is intact

**This means your Ghost Protocol scraper is extracting NBA IDs correctly from stats.nba.com!**

---

## The Accent Problem

**Issue:** Tank01 API returns names **without accents** (ASCII), but NBA API returns names **with accents** (UTF-8).

### Examples of Mismatches:
| Tank01 (No Accent) | NBA API (With Accent) | Result |
|--------------------|----------------------|--------|
| Luka Doncic | Luka Dončić | 2 separate records |
| Nikola Jokic | Nikola Jokić | 2 separate records |
| Nikola Vucevic | Nikola Vučević | Potential mismatch |
| Bogdan Bogdanovic | Bogdan Bogdanović | Potential mismatch |

**Why this matters:** When Module E queries `player_game_tracking` by name, it might use "Luka Doncic" (from Tank01) but the tracking table has "Luka Dončić" (from NBA scraper), causing a **0 results** error.

---

## Hybrid Solution: Canonical ID + Name Normalization

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  NEW TABLE: player_canonical_ids (Single Source of Truth)
│  - canonical_id (PRIMARY KEY) → NBA ID (203507)
│  - full_name → "Luka Dončić" (UTF-8, from NBA)
│  - normalized_name → "luka doncic" (ASCII, searchable)
│  - tank01_aliases → ["28398804489", "luka_doncic_dal"]
│  - active → TRUE/FALSE
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│  NEW UTILITY: utils/player_id_resolver.py
│  Methods:
│  - resolve_to_canonical_id(input_id_or_name) → NBA ID
│  - normalize_name(name) → ASCII lowercase, no accents
│  - get_player_by_name(name) → Player record
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│  ALL MODULES use ID Resolver for lookups
│  - Module E queries: resolver.resolve("Luka Doncic")
│  - Returns: 1629029 (canonical NBA ID)
│  - Queries tracking table with NBA ID ✅
└─────────────────────────────────────────────────────────┘
```

### Benefits of This Approach

✅ **Immune to Tank01 changes:** If Tank01 changes IDs again, just update aliases  
✅ **Handles accents:** Normalizes "Dončić" and "Doncic" to same ID  
✅ **Works across all APIs:** NBA, Tank01, PBP Stats all resolve to same ID  
✅ **Backwards compatible:** Existing code can call `resolve()` wrapper  
✅ **Performance:** Single index lookup on normalized_name  

---

## Implementation Plan (4-6 hours)

### Phase 1: Create Canonical ID System (1.5 hours)

**Step 1.1: Create new table**
```sql
CREATE TABLE player_canonical_ids (
    canonical_id TEXT PRIMARY KEY,  -- NBA ID (203507)
    full_name TEXT NOT NULL,        -- "Luka Dončić" (UTF-8)
    normalized_name TEXT NOT NULL UNIQUE,  -- "luka doncic" (ASCII)
    team TEXT,
    position TEXT,
    is_active INTEGER DEFAULT 1,
    -- Alias tracking
    tank01_aliases TEXT,  -- JSON: ["28398804489", "luka_doncic_dal"]
    nba_api_id TEXT,      -- 1629029 (might differ from canonical_id in rare cases)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_canonical_normalized_name ON player_canonical_ids(normalized_name);
CREATE INDEX idx_canonical_team ON player_canonical_ids(team);
```

**Step 1.2: Create ID resolver utility**
```python
# utils/player_id_resolver.py
import sqlite3
import unicodedata
import json

class PlayerIDResolver:
    """
    Single source of truth for player ID resolution.
    Handles Tank01 ID changes, accent normalization, and cross-API mapping.
    """
    
    def __init__(self, db_path='ludi.db'):
        self.db_path = db_path
        self._cache = {}  # In-memory cache for performance
    
    @staticmethod
    def normalize_name(name: str) -> str:
        """
        Normalize player name for matching across APIs.
        
        Handles:
        - Accents: Dončić → Doncic
        - Case: LUKA → luka
        - Suffixes: Jr., Sr., III, II removed
        - Whitespace: trimmed
        
        Examples:
            "Luka Dončić" → "luka doncic"
            "Nikola Jokić" → "nikola jokic"
            "Gary Payton II" → "gary payton"
        """
        if not name:
            return ''
        
        # Remove accents using Unicode normalization
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ASCII', 'ignore').decode('ASCII')
        
        # Lowercase and strip
        name = name.lower().strip()
        
        # Remove suffixes
        for suffix in [' jr.', ' jr', ' sr.', ' sr', ' iii', ' ii', ' iv', ' v']:
            name = name.replace(suffix, '')
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name
    
    def resolve_to_canonical_id(self, input_value: str) -> str:
        """
        Resolve any player identifier (ID, name, alias) to canonical NBA ID.
        
        Args:
            input_value: Can be:
                - NBA ID: "203507"
                - Tank01 ID: "28118035349"
                - Name with accent: "Luka Dončić"
                - Name without accent: "Luka Doncic"
        
        Returns:
            Canonical NBA ID (e.g., "203507")
        
        Raises:
            ValueError: If player not found
        """
        # Check cache first
        if input_value in self._cache:
            return self._cache[input_value]
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Try exact canonical ID match
        c.execute('SELECT canonical_id FROM player_canonical_ids WHERE canonical_id = ?', (input_value,))
        row = c.fetchone()
        if row:
            conn.close()
            self._cache[input_value] = row[0]
            return row[0]
        
        # Try normalized name match
        normalized = self.normalize_name(input_value)
        c.execute('SELECT canonical_id FROM player_canonical_ids WHERE normalized_name = ?', (normalized,))
        row = c.fetchone()
        if row:
            conn.close()
            self._cache[input_value] = row[0]
            return row[0]
        
        # Try Tank01 alias match
        c.execute('SELECT canonical_id, tank01_aliases FROM player_canonical_ids WHERE is_active = 1')
        rows = c.fetchall()
        for canonical_id, aliases_json in rows:
            if aliases_json:
                aliases = json.loads(aliases_json)
                if input_value in aliases:
                    conn.close()
                    self._cache[input_value] = canonical_id
                    return canonical_id
        
        conn.close()
        raise ValueError(f"Player not found: {input_value} (normalized: {normalized})")
    
    def get_player_info(self, input_value: str) -> dict:
        """
        Get full player info by any identifier.
        
        Returns:
            {
                'canonical_id': '203507',
                'full_name': 'Giannis Antetokounmpo',
                'normalized_name': 'giannis antetokounmpo',
                'team': 'MIL',
                'position': 'F'
            }
        """
        canonical_id = self.resolve_to_canonical_id(input_value)
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT canonical_id, full_name, normalized_name, team, position
            FROM player_canonical_ids
            WHERE canonical_id = ?
        ''', (canonical_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            raise ValueError(f"Canonical ID not found: {canonical_id}")
        
        return {
            'canonical_id': row[0],
            'full_name': row[1],
            'normalized_name': row[2],
            'team': row[3],
            'position': row[4]
        }
    
    def add_alias(self, canonical_id: str, new_alias: str):
        """Add a new Tank01 alias to existing player."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT tank01_aliases FROM player_canonical_ids WHERE canonical_id = ?', (canonical_id,))
        row = c.fetchone()
        
        if not row:
            conn.close()
            raise ValueError(f"Player not found: {canonical_id}")
        
        aliases = json.loads(row[0]) if row[0] else []
        if new_alias not in aliases:
            aliases.append(new_alias)
            c.execute('''
                UPDATE player_canonical_ids 
                SET tank01_aliases = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE canonical_id = ?
            ''', (json.dumps(aliases), canonical_id))
            conn.commit()
        
        conn.close()
```

---

### Phase 2: Populate Canonical Table (1 hour)

**Step 2.1: Create population script**
```python
# scripts/populate_canonical_ids.py
import sqlite3
import json
from utils.player_id_resolver import PlayerIDResolver

resolver = PlayerIDResolver()
conn = sqlite3.connect('ludi.db')
c = conn.cursor()

# Get all players with NBA-format IDs (4-7 digits, no letters)
c.execute('''
    SELECT DISTINCT player_id, name, team, position
    FROM players
    WHERE LENGTH(player_id) BETWEEN 4 AND 7
    AND player_id NOT LIKE '%_%'
    AND player_id NOT LIKE '%a%' AND player_id NOT LIKE '%z%'
    ORDER BY name
''')

nba_players = c.fetchall()

print(f"Found {len(nba_players)} players with NBA IDs")

# Insert into canonical table
for player_id, name, team, position in nba_players:
    normalized = resolver.normalize_name(name)
    
    try:
        c.execute('''
            INSERT INTO player_canonical_ids 
            (canonical_id, full_name, normalized_name, team, position, tank01_aliases, nba_api_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (player_id, name, normalized, team, position, json.dumps([]), player_id))
        print(f"✅ {name} ({player_id})")
    except sqlite3.IntegrityError:
        # Duplicate normalized name - player already exists
        print(f"⚠️  SKIP: {name} (duplicate)")

conn.commit()

# Now find Tank01 aliases
print("\n" + "=" * 80)
print("FINDING TANK01 ALIASES")
print("=" * 80)

c.execute('''
    SELECT player_id, name FROM players
    WHERE LENGTH(player_id) > 10
''')

tank01_ids = c.fetchall()

for tank01_id, name in tank01_ids:
    normalized = resolver.normalize_name(name)
    
    # Find matching canonical player
    c.execute('SELECT canonical_id FROM player_canonical_ids WHERE normalized_name = ?', (normalized,))
    row = c.fetchone()
    
    if row:
        canonical_id = row[0]
        
        # Add as alias
        c.execute('SELECT tank01_aliases FROM player_canonical_ids WHERE canonical_id = ?', (canonical_id,))
        aliases_json = c.fetchone()[0]
        aliases = json.loads(aliases_json) if aliases_json else []
        
        if tank01_id not in aliases:
            aliases.append(tank01_id)
            c.execute('''
                UPDATE player_canonical_ids 
                SET tank01_aliases = ? 
                WHERE canonical_id = ?
            ''', (json.dumps(aliases), canonical_id))
            print(f"✅ Alias added: {name} → {tank01_id} (canonical: {canonical_id})")

conn.commit()
conn.close()

print("\n✅ Canonical ID table populated!")
```

**Run:**
```bash
python scripts/populate_canonical_ids.py
```

---

### Phase 3: Update Module E to Use Resolver (1 hour)

**File:** `module_e.py`

**Current (line 228-296):**
```python
def _get_tracking_stats(self, player_name, days=20):
    # ❌ OLD: Query by name directly (accent mismatch risk)
    query = '''
        SELECT AVG(drives_fga), AVG(catch_shoot_fga), ...
        FROM player_game_tracking
        WHERE player_name = ? AND game_date >= date('now', '-20 days')
    '''
```

**New:**
```python
from utils.player_id_resolver import PlayerIDResolver

class LudiCalibrator:
    def __init__(self):
        self.id_resolver = PlayerIDResolver()
        # ... rest of init
    
    def _get_tracking_stats(self, player_name_or_id, days=20):
        """
        Get tracking stats using canonical ID resolution.
        
        Args:
            player_name_or_id: Can be name (with/without accents) or any ID format
            days: Lookback window
        
        Returns:
            Dict of tracking averages
        """
        try:
            # Resolve to canonical NBA ID
            canonical_id = self.id_resolver.resolve_to_canonical_id(player_name_or_id)
            
            # Query tracking table by NBA ID (not name!)
            query = '''
                SELECT 
                    AVG(drives_fga) as avg_drives,
                    AVG(catch_shoot_fga) as avg_cs_fga,
                    AVG(CAST(catch_shoot_fgm AS FLOAT) / NULLIF(catch_shoot_fga, 0)) as cs_pct,
                    AVG(pull_up_fga) as avg_pu_fga,
                    AVG(avg_speed_off) as avg_speed,
                    AVG(dist_miles_off) as avg_distance
                FROM player_game_tracking
                WHERE nba_player_id = ? AND game_date >= date('now', ? || ' days')
            '''
            
            conn = sqlite3.connect('ludi.db')
            c = conn.cursor()
            c.execute(query, (canonical_id, f'-{days}'))
            row = c.fetchone()
            conn.close()
            
            if not row or row[0] is None:
                # No tracking data - return zeros
                return {
                    'drives': 0.0,
                    'catch_shoot_fga': 0.0,
                    'catch_shoot_pct': 0.0,
                    'pull_up_fga': 0.0,
                    'speed': 0.0,
                    'distance': 0.0
                }
            
            return {
                'drives': row[0] or 0.0,
                'catch_shoot_fga': row[1] or 0.0,
                'catch_shoot_pct': row[2] or 0.0,
                'pull_up_fga': row[3] or 0.0,
                'speed': row[4] or 0.0,
                'distance': row[5] or 0.0
            }
        
        except ValueError as e:
            # Player not found
            print(f"⚠️  Player lookup failed: {e}")
            return {
                'drives': 0.0,
                'catch_shoot_fga': 0.0,
                'catch_shoot_pct': 0.0,
                'pull_up_fga': 0.0,
                'speed': 0.0,
                'distance': 0.0
            }
```

---

### Phase 4: Update Other Modules (1.5 hours)

**Files to update:**
1. **`database.py`** - update_player_census_v2()
2. **`utils/roster_validator.py`** - compare_rosters()
3. **`scripts/sync_player_positions.py`** - update_player_position()
4. **`main.py`** - player lookups

**Pattern for all modules:**
```python
from utils.player_id_resolver import PlayerIDResolver

resolver = PlayerIDResolver()

# When you receive a player name from Tank01:
tank01_name = player.get('longName', '')  # "Luka Doncic" (no accent)

# Resolve to canonical ID:
canonical_id = resolver.resolve_to_canonical_id(tank01_name)

# Use canonical ID for all database operations:
conn.execute('UPDATE players SET team = ? WHERE player_id = ?', (team, canonical_id))
```

---

### Phase 5: Clean Up Duplicate Records (30 minutes)

**Step 5.1: Mark duplicates as inactive**
```sql
-- Find all non-NBA IDs
UPDATE players
SET is_active = 0, updated_at = CURRENT_TIMESTAMP
WHERE LENGTH(player_id) > 10 OR player_id LIKE '%_%';

-- Verify only NBA IDs remain active
SELECT COUNT(*) FROM players WHERE is_active = 1;
-- Should be ~500 (one per player)
```

**Step 5.2: Archive duplicates** (optional, for audit trail)
```sql
CREATE TABLE players_archived AS 
SELECT * FROM players WHERE is_active = 0;

-- Later, you can delete them
-- DELETE FROM players WHERE is_active = 0;
```

---

## Testing Strategy

### Test 1: Name Resolution (All Variations)
```python
from utils.player_id_resolver import PlayerIDResolver

resolver = PlayerIDResolver()

# Test accent handling
assert resolver.resolve_to_canonical_id("Luka Dončić") == "1629029"
assert resolver.resolve_to_canonical_id("Luka Doncic") == "1629029"
assert resolver.resolve_to_canonical_id("luka doncic") == "1629029"

# Test ID lookup
assert resolver.resolve_to_canonical_id("1629029") == "1629029"
assert resolver.resolve_to_canonical_id("28398804489") == "1629029"  # Tank01 alias

print("✅ All name resolution tests passed!")
```

### Test 2: Tracking Data Lookup
```python
from module_e import LudiCalibrator

calibrator = LudiCalibrator()

# Test with accent
stats1 = calibrator._get_tracking_stats("Luka Dončić", days=10)

# Test without accent
stats2 = calibrator._get_tracking_stats("Luka Doncic", days=10)

# Should return same data
assert stats1['drives'] == stats2['drives']
assert stats1['catch_shoot_fga'] == stats2['catch_shoot_fga']

print("✅ Tracking lookup works with/without accents!")
```

### Test 3: End-to-End Pipeline
```bash
# Run main.py with test games
python main.py --limit-games 1

# Check for errors in logs
grep "Player lookup failed" logs/*.log

# Should see 0 errors
```

---

## Rollout Plan

### Day 1 (Monday): Foundation
- [ ] Create `player_canonical_ids` table
- [ ] Create `utils/player_id_resolver.py`
- [ ] Run `populate_canonical_ids.py`
- [ ] Verify 500+ canonical players populated

### Day 2 (Tuesday): Module E Integration
- [ ] Update Module E `_get_tracking_stats()`
- [ ] Test with known players (Luka, Giannis, LeBron)
- [ ] Fix any edge cases

### Day 3 (Wednesday): Pipeline Integration
- [ ] Update `database.py`, `roster_validator.py`
- [ ] Update `main.py` lookups
- [ ] Run end-to-end test

### Day 4 (Thursday): Cleanup & Ship
- [ ] Mark duplicate records inactive
- [ ] Update Week 2 implementation to use resolver
- [ ] Ship to production

---

## FAQ

### Q: Why not just use player names everywhere?
**A:** Performance. Integer ID lookups are 10x faster than string comparisons. Also, name matching is fragile (typos, nicknames, abbreviations).

### Q: What if Tank01 changes IDs again?
**A:** Just run `populate_canonical_ids.py` again. It will detect new aliases and add them automatically.

### Q: Will this break existing code?
**A:** No. The resolver has a `resolve_to_canonical_id()` method that accepts ANY input (old ID, new ID, name with/without accents) and returns the canonical NBA ID. Existing code just needs to call this wrapper function.

### Q: How do I handle new player signings?
**A:** When Tank01 returns a new player:
1. Resolver tries to match by normalized name
2. If not found, it's a true new player
3. Create new canonical record with Tank01 ID as alias
4. Future roster syncs will update the canonical record

---

## Success Metrics

- ✅ Zero "Player not found" errors in Module E
- ✅ All 271+ duplicate players deduplicated
- ✅ Accent variations (Dončić/Doncic) resolve to same ID
- ✅ Week 2 archetype system can query tracking data successfully
- ✅ Pipeline runs end-to-end without ID mismatch errors

---

## Next Steps

**Immediate:**
1. Review this plan with user
2. Get approval on hybrid approach
3. Start Day 1 implementation

**Post-Implementation:**
- Monitor for any new Tank01 ID changes
- Add unit tests for resolver
- Document in CLAUDE.md for future agents

**Let's discuss any concerns or adjustments before proceeding!**
