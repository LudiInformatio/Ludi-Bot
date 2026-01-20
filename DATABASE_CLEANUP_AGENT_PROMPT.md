# Database Cleanup Agent - Tank01 ID Reconciliation

**Date:** January 20, 2026 @ 03:00 AM EST  
**Priority:** HIGH - Blocking Week 2 Archetype Implementation  

**Proof of Concept:** ✅ VALIDATED (8/8 tests passed)
**Status:** Phases 1-4 COMPLETE ✅

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

### Phase 4: Update Module E (COMPLETE ✅)

**Status:** Verified on Jan 20, 2026. Module E now correctly uses `PlayerIDResolver`.

---

### Phase 5: Database Guardrail (The "Smooth Rollout")

**Objective:** Implement "Heal on Ingestion" logic in `database.py` to prevent future database pollution from external modules (Historian, Yak).

#### Step 5.1: Modify `database.py`
**File:** `database.py`

1. Import `PlayerIDResolver`.
2. Locate `upsert_player_info` (or equivalent write method).
3. Add guardrail logic at the top of the method:

```python
# 🛡️ GUARDRAIL: Resolve ID before writing
try:
    # Attempt to resolve to canonical NBA ID
    canonical_id = self.resolver.resolve_to_canonical_id(player_data['id'])
    # Overwrite the dirty ID with the clean ID
    player_data['id'] = canonical_id
except ValueError:
    # If resolution fails, keep original ID (better to have dirty data than no data)
    pass 
```

#### Step 5.2: Verification
1. Run `module_h_historian.py` or a simulation script with a Tank01 ID.
2. Verify that `players` table receives an NBA ID, not the Tank01 ID.


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
