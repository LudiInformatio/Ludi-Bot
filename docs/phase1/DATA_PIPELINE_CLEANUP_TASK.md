# Data Pipeline Cleanup Task

**Date:** January 21, 2026  
**Task Owner:** [Agent to be assigned]  
**Priority:** HIGH (Pre-Phase 2)  
**Estimated Time:** 45 minutes  

---

## Mission

Complete **two cleanup tasks** before Phase 2:
1. **Add PlayerIDResolver integration** to key sync scripts
2. **Backfill missing Synergy data** for 48 regular scorers

---

## Task 1: PlayerIDResolver Integration (30 min)

### Background

The `PlayerIDResolver` normalizes player names to handle:
- Special characters (e.g., `Dončić` → canonical format)
- Name variations (`LeBron James` vs `James, LeBron`)
- ID conflicts from different data sources

**Currently Used By:**
- ✅ `module_e.py`
- ✅ `database.py`
- ✅ `settle_bets.py`

**NOT Used By (Target Scripts):**
- ❌ `scripts/sync_synergy_playtypes.py`
- ❌ `scripts/sync_tracking_parallel.py`
- ❌ `scripts/sync_wowy_data.py`

---

### Implementation Steps

#### Step 1: Create Helper Function

Add to `/Users/flyprice/Desktop/Ludi Informatio/Projects/Ludi-Bot/utils/player_id_resolver.py`:

```python
def normalize_player_name(name: str, db_path: str = 'ludi.db') -> str:
    """
    Quick utility to normalize a player name using PlayerIDResolver.
    Use this in sync scripts for consistent name formatting.
    
    Args:
        name: Raw player name from API/scraper
        db_path: Path to database
        
    Returns:
        Canonical player name
    """
    resolver = get_resolver()
    # Try to find canonical name
    result = resolver.resolve(name)
    if result and result.get('canonical_name'):
        return result['canonical_name']
    return name  # Fallback to original if no match
```

#### Step 2: Update sync_synergy_playtypes.py

**Location:** Line ~150 (where player_name is inserted)

**Add import at top:**
```python
from utils.player_id_resolver import normalize_player_name
```

**Modify insertion logic:**
```python
# Before inserting, normalize the name
player_name = normalize_player_name(raw_player_name)
```

#### Step 3: Update sync_tracking_parallel.py

**Location:** Line ~200 (where player_name is stored)

**Add import and normalization:**
```python
from utils.player_id_resolver import normalize_player_name

# When processing player data
player_name = normalize_player_name(data.get('PLAYER_NAME', ''))
```

#### Step 4: Update sync_wowy_data.py

**Location:** Line ~180 (lineup player parsing)

**Add import and normalization:**
```python
from utils.player_id_resolver import normalize_player_name

# When parsing lineup_players string
players = [normalize_player_name(p.strip()) for p in lineup_str.split(' - ')]
```

---

### Verification Commands

```bash
# Test import works
python3 -c "from utils.player_id_resolver import normalize_player_name; print(normalize_player_name('Luka Doncic'))"

# Run sync script (dry run)
python3 scripts/sync_synergy_playtypes.py --dry-run
```

---

## Task 2: Backfill Missing Synergy Data (15 min)

### Background

48 regular scorers (10+ PPG last 30 days) are missing Synergy playtype data.

### Implementation Steps

#### Step 1: Get Missing Players List

```bash
sqlite3 ludi.db "
SELECT DISTINCT pgl.player_name, AVG(pgl.pts) as avg_pts
FROM player_game_logs pgl
WHERE pgl.game_date >= date('now', '-30 days')
AND pgl.pts >= 10
AND pgl.player_name NOT IN (
    SELECT DISTINCT player_name FROM player_synergy_playtypes
)
GROUP BY pgl.player_name
ORDER BY avg_pts DESC
LIMIT 50;
" > missing_synergy_players.txt
```

#### Step 2: Run Targeted Synergy Sync

```bash
# Run the Synergy sync script to capture all players
python3 scripts/sync_synergy_playtypes.py --full-refresh

# Or run targeted sync for specific players
python3 scripts/sync_synergy_playtypes.py --players-file missing_synergy_players.txt
```

#### Step 3: Verify Backfill

```bash
# Count after backfill
sqlite3 ludi.db "SELECT COUNT(DISTINCT player_name) FROM player_synergy_playtypes;"

# Should be 376 + ~48 = 420+ players
```

---

## Success Criteria

### Task 1: PlayerIDResolver Integration
- [ ] `normalize_player_name()` helper function added to player_id_resolver.py
- [ ] sync_synergy_playtypes.py uses normalization
- [ ] sync_tracking_parallel.py uses normalization
- [ ] sync_wowy_data.py uses normalization
- [ ] All scripts run without errors

### Task 2: Synergy Backfill
- [ ] Missing players list generated
- [ ] Synergy sync completed
- [ ] Player count increased from 376 to 400+
- [ ] Key players verified (check 3 previously missing stars)

---

## Reference Files

| File | Purpose |
|------|---------|
| `utils/player_id_resolver.py` | Add normalize helper |
| `scripts/sync_synergy_playtypes.py` | Primary sync script |
| `scripts/sync_tracking_parallel.py` | Tracking data sync |
| `scripts/sync_wowy_data.py` | WOWY lineup sync |

---

## Deliverables

1. **Modified player_id_resolver.py** with new helper function
2. **Updated sync scripts** (3 files)
3. **Verification output** showing:
   - Scripts run successfully
   - Synergy player count increased
4. **Summary statement** confirming success criteria met

---

## Key Constraints

1. **Non-breaking:** Existing functionality must not break
2. **Fallback safe:** If normalization fails, use original name
3. **No data loss:** Only ADD normalization, don't delete data

---

**Good luck! Report back with verification results.**
