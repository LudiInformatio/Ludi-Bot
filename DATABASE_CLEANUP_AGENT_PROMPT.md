# Database Cleanup Agent - Tank01 ID Reconciliation

**Date:** January 20, 2026 @ 03:00 AM EST  
**Priority:** HIGH - Blocking Week 2 Archetype Implementation  
**Proof of Concept:** ✅ VALIDATED (8/8 tests passed)

---

## Your Mission

Clean up duplicate player records caused by Tank01 API ID change (Jan 1-2, 2026) and implement the canonical ID resolution system. The proof of concept test confirmed the strategy works perfectly.

**Timeline:** 4-6 hours  
**Impact:** Fixes 1,460 duplicate records, unblocks Module E integration

---

## Context (What Happened)

### The Problem
Around Jan 1-2, 2026, Tank01 changed their player ID format:
- **Before:** Used NBA IDs (`203507` for Giannis)
- **After:** New composite IDs (`28118035349` for Giannis)
- **Result:** 271+ players now have duplicate records in your database

### Proof of Concept Results ✅
We tested with 8 players (Luka, Jokić, Giannis, LeBron, Curry) and confirmed:
- ✅ Accent normalization works ("Dončić" and "Doncic" → same ID)
- ✅ NBA IDs are consistently found
- ✅ Tracking data exists for canonical IDs
- ✅ ~1,460 duplicate records need cleanup

**Test Output:** See `scripts/test_id_resolution_poc.py` (already run successfully)

---

## Implementation Checklist

### Phase 1: Create Canonical ID System (1.5 hours)

#### Step 1.1: Create Database Table
```bash
sqlite3 ludi.db
```

```sql
CREATE TABLE player_canonical_ids (
    canonical_id TEXT PRIMARY KEY,        -- NBA ID (203507)
    full_name TEXT NOT NULL,              -- "Luka Dončić" (UTF-8)
    normalized_name TEXT NOT NULL UNIQUE, -- "luka doncic" (ASCII)
    team TEXT,
    position TEXT,
    is_active INTEGER DEFAULT 1,
    -- Alias tracking
    tank01_aliases TEXT,  -- JSON: ["28398804489", "luka_doncic_dal"]
    nba_api_id TEXT,      -- Usually same as canonical_id
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_canonical_normalized_name ON player_canonical_ids(normalized_name);
CREATE INDEX idx_canonical_team ON player_canonical_ids(team);

-- Exit sqlite3
.quit
```

#### Step 1.2: Create ID Resolver Utility
**File:** `utils/player_id_resolver.py`

**Full implementation is in `docs/TANK01_ID_RECONCILIATION_PLAN.md` (lines 134-298)**

Copy the complete `PlayerIDResolver` class from that file. Key methods:
- `normalize_name(name)` - Removes accents, handles Jr./Sr.
- `resolve_to_canonical_id(input)` - Returns NBA ID for any input
- `get_player_info(input)` - Returns full player dict
- `add_alias(canonical_id, new_alias)` - Adds Tank01 aliases

**Quick validation:**
```bash
python3 -c "from utils.player_id_resolver import PlayerIDResolver; r = PlayerIDResolver(); print('Resolver loaded successfully')"
```

---

### Phase 2: Populate Canonical Table (1 hour)

#### Step 2.1: Create Population Script
**File:** `scripts/populate_canonical_ids.py`

**Full implementation is in `docs/TANK01_ID_RECONCILIATION_PLAN.md` (lines 306-386)**

This script:
1. Finds all players with NBA IDs (4-7 digits, no letters)
2. Inserts them into `player_canonical_ids` as canonical records
3. Finds all Tank01/Legacy IDs and adds them as aliases

#### Step 2.2: Run Population
```bash
python3 scripts/populate_canonical_ids.py
```

**Expected Output:**
```
Found 500+ players with NBA IDs
✅ Luka Dončić (1629029)
✅ Nikola Jokić (203999)
✅ Giannis Antetokounmpo (203507)
...

FINDING TANK01 ALIASES
✅ Alias added: Luka Doncic → 28398804489 (canonical: 1629029)
✅ Alias added: Nikola Jokic → 28908111729 (canonical: 203999)
...

✅ Canonical ID table populated!
```

**Validation:**
```bash
sqlite3 ludi.db "SELECT COUNT(*) FROM player_canonical_ids;"
# Should show ~500 players

sqlite3 ludi.db "SELECT full_name, normalized_name, canonical_id FROM player_canonical_ids WHERE full_name LIKE '%Luka%';"
# Should show: Luka Dončić|luka doncic|1629029
```

---

### Phase 3: Clean Up Duplicate Records (30 minutes)

#### Step 3.1: Mark Duplicates as Inactive
```bash
sqlite3 ludi.db
```

```sql
-- Mark all Tank01 IDs (>10 chars) as inactive
UPDATE players
SET is_active = 0, updated_at = CURRENT_TIMESTAMP
WHERE LENGTH(player_id) > 10;

-- Mark all Legacy IDs (with underscore) as inactive
UPDATE players
SET is_active = 0, updated_at = CURRENT_TIMESTAMP
WHERE player_id LIKE '%_%';

-- Verify only NBA IDs remain active
SELECT COUNT(*) FROM players WHERE is_active = 1;
-- Should show ~500 players (one per player)

-- Verify cleanup
SELECT COUNT(*) FROM players WHERE is_active = 0;
-- Should show ~1460 duplicates marked inactive

.quit
```

#### Step 3.2: Archive Duplicates (Optional)
```bash
sqlite3 ludi.db
```

```sql
-- Create archive table for audit trail
CREATE TABLE players_archived AS 
SELECT * FROM players WHERE is_active = 0;

-- Verify archive
SELECT COUNT(*) FROM players_archived;
-- Should show ~1460 records

-- OPTIONAL: Delete archived records (keep commented out for now)
-- DELETE FROM players WHERE is_active = 0;

.quit
```

---

### Phase 4: Update Module E (1 hour)

#### Step 4.1: Update Calibrator to Use Resolver
**File:** `module_e.py`

**Current code (line 228):**
```python
def _get_tracking_stats(self, player_name, days=20):
    # ❌ OLD: Query by name (accent mismatch risk)
```

**New code:**
```python
from utils.player_id_resolver import PlayerIDResolver

class LudiCalibrator:
    def __init__(self):
        self.id_resolver = PlayerIDResolver()
        # ... rest of __init__
    
    def _get_tracking_stats(self, player_name_or_id, days=20):
        """
        Get tracking stats using canonical ID resolution.
        
        Args:
            player_name_or_id: Can be name (with/without accents) or any ID format
            days: Lookback window (default 20)
        
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
            
            import sqlite3
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

**Apply changes:**
```bash
# Find the method in module_e.py
grep -n "_get_tracking_stats" module_e.py

# Replace the method (lines will vary, find exact location first)
# Use your editor or the edit_files tool
```

---

### Phase 5: Testing (1 hour)

#### Test 1: Resolver Unit Tests
```bash
python3 -c "
from utils.player_id_resolver import PlayerIDResolver

resolver = PlayerIDResolver()

# Test accent handling
assert resolver.resolve_to_canonical_id('Luka Dončić') == '1629029'
assert resolver.resolve_to_canonical_id('Luka Doncic') == '1629029'
assert resolver.resolve_to_canonical_id('luka doncic') == '1629029'

# Test ID lookup
assert resolver.resolve_to_canonical_id('1629029') == '1629029'
assert resolver.resolve_to_canonical_id('28398804489') == '1629029'  # Tank01 alias

print('✅ All resolver tests passed!')
"
```

#### Test 2: Module E Integration
```bash
python3 -c "
from module_e import LudiCalibrator

calibrator = LudiCalibrator()

# Test with accent
stats1 = calibrator._get_tracking_stats('Luka Dončić', days=10)

# Test without accent
stats2 = calibrator._get_tracking_stats('Luka Doncic', days=10)

# Should return same data
assert stats1['drives'] == stats2['drives'], f\"Mismatch: {stats1['drives']} != {stats2['drives']}\"
assert stats1['catch_shoot_fga'] == stats2['catch_shoot_fga']

print('✅ Module E tracking lookup works with/without accents!')
print(f\"Luka drives: {stats1['drives']:.2f}/game\")
"
```

#### Test 3: Database Integrity Check
```bash
sqlite3 ludi.db "
SELECT 
    (SELECT COUNT(*) FROM players WHERE is_active = 1) as active_players,
    (SELECT COUNT(*) FROM players WHERE is_active = 0) as inactive_duplicates,
    (SELECT COUNT(*) FROM player_canonical_ids) as canonical_records,
    (SELECT COUNT(*) FROM player_game_tracking WHERE nba_player_id IN (SELECT canonical_id FROM player_canonical_ids)) as tracking_records_linked;
"
```

**Expected output:**
```
active_players|inactive_duplicates|canonical_records|tracking_records_linked
500|1460|500|14000+
```

---

## Success Criteria

Check all boxes before marking complete:

- [ ] `player_canonical_ids` table created with indexes
- [ ] `utils/player_id_resolver.py` created and loads successfully
- [ ] `populate_canonical_ids.py` ran successfully (~500 players)
- [ ] Tank01 aliases added to canonical table
- [ ] ~1,460 duplicate records marked inactive in `players` table
- [ ] Module E updated to use resolver
- [ ] All 3 test suites pass (resolver, Module E, database integrity)
- [ ] Zero "Player lookup failed" errors when running Module E

---

## Common Issues & Solutions

### Issue 1: "Player not found" after cleanup
**Cause:** Old code is still querying by Tank01 ID  
**Fix:** Update ALL modules to use `resolver.resolve_to_canonical_id()` before querying

### Issue 2: Accent variations return different IDs
**Cause:** Normalization not applied correctly  
**Fix:** Always use `resolver.normalize_name()` before comparisons

### Issue 3: Tracking data shows 0 results
**Cause:** Querying `player_game_tracking` by name instead of `nba_player_id`  
**Fix:** Update query to use `WHERE nba_player_id = ?` (canonical ID)

---

## Files to Create/Modify

| File | Action | Location |
|------|--------|----------|
| `player_canonical_ids` table | CREATE | Database |
| `utils/player_id_resolver.py` | CREATE | New utility |
| `scripts/populate_canonical_ids.py` | CREATE | New script |
| `module_e.py` | MODIFY | Line ~228 (`_get_tracking_stats`) |
| `players_archived` table | CREATE (optional) | Database |

---

## Post-Cleanup Tasks (Optional)

After everything works:

1. **Update other modules** to use resolver:
   - `database.py` (line 604)
   - `utils/roster_validator.py` (line 215)
   - `scripts/sync_player_positions.py` (line 208)
   - `main.py` (line 70-98)

2. **Delete archived duplicates** (once confident):
   ```sql
   DELETE FROM players WHERE is_active = 0;
   ```

3. **Update CLAUDE.md** with new system:
   ```markdown
   ## Player ID Resolution System (Added Jan 20, 2026)
   - All modules use `PlayerIDResolver` for player lookups
   - Handles Tank01 API ID changes automatically
   - Accent normalization: Dončić/Doncic → same ID
   - Canonical IDs stored in `player_canonical_ids` table
   ```

---

## Reference Documents

- **Full Plan:** `docs/TANK01_ID_RECONCILIATION_PLAN.md` (658 lines)
- **Proof of Concept:** `scripts/test_id_resolution_poc.py` (already validated ✅)
- **Test Results:** 8/8 tests passed, accent handling confirmed working

---

## Questions/Blockers?

If you encounter issues:

1. **Check proof of concept results:** Run `python3 scripts/test_id_resolution_poc.py` again
2. **Verify table creation:** `sqlite3 ludi.db "PRAGMA table_info(player_canonical_ids);"`
3. **Check resolver loads:** `python3 -c "from utils.player_id_resolver import PlayerIDResolver"`
4. **Database backup:** Before cleanup, run `cp ludi.db ludi.db.backup_$(date +%Y%m%d)`

**Report back with:**
- Which phase you're on
- Any error messages
- Test results

---

**Ready to clean up the database! Start with Phase 1 (Create Canonical ID System).**
