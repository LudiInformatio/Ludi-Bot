# GHOST PROTOCOL: PHASE 1 EXECUTION PROMPT
**Target:** Physics Engine Backfill (Nov 14, 2025 → Jan 16, 2026)  
**Priority:** HIGH  
**Est. Runtime:** 3-4 hours (63 days × 4 stat categories × ~15s/page)

---

## MISSION BRIEFING

**Objective:** Backfill the "Physics" of player movement and shooting behavior to power Module C (Oracle) simulations.

**Data Targets:**
1. **Drives** → How often players attack the rim (FGA, PTS, PASS%)
2. **Catch & Shoot** → Spot-up shooting efficiency (FGA, FGM, 3PA, 3PM)
3. **Pull-Ups** → Off-dribble shooting (FGA, FGM, 3PA, 3PM, eFG%)
4. **Speed & Distance** → Player movement metrics (Miles Off/Def, Avg Speed)

**Database Impact:**
- Target Table: `player_game_tracking`
- Expected Records: ~190 players/day × 63 days = **~12,000 new rows**
- Storage: ~5MB additional data

---

## EXECUTION COMMAND

```bash
cd ~/Desktop/Ludi\ Informatio/Projects/Ludi-Bot
./.venv/bin/python scripts/sync_browser_backfill.py \
  --start-date 2025-11-14 \
  --end-date 2026-01-16
```

**Alternative (Test Single Day First):**
```bash
# Dry run: Test on Nov 14 only
./.venv/bin/python scripts/sync_browser_backfill.py \
  --start-date 2025-11-14 \
  --end-date 2025-11-14
```

---

## WHAT TO MONITOR

### Success Indicators
✅ Browser window opens (non-headless mode)  
✅ Each date shows: `[YYYY-MM-DD] Processing...`  
✅ Per-category output: `✓ Drives: 190 records`, `✓ Catch & Shoot: 190 records`, etc.  
✅ Random delays between pages (2-4 seconds)

### Warning Signs
⚠️ `❌ [Category] Error: Timeout` → NBA.com slow; script retries automatically  
⚠️ `✓ [Category]: 0 records` → No games that day OR table structure changed  
⚠️ Browser crashes → Rare; script should auto-restart

### Critical Failures (ABORT MISSION)
🚨 `Page.goto: ERR_HTTP2_PROTOCOL_ERROR` on 3+ consecutive pages → IP block detected  
🚨 Consistent 0-record days for ALL categories → CSS selectors broken

---

## VERIFICATION PROTOCOL

**Step 1: Spot Check Database**
```bash
sqlite3 ludi.db "SELECT COUNT(*) FROM player_game_tracking;"
# Expected: 5,522 (existing) + ~12,000 (new) = ~17,500 total

sqlite3 ludi.db "SELECT game_date, COUNT(*) FROM player_game_tracking GROUP BY game_date ORDER BY game_date DESC LIMIT 5;"
# Should show recent dates with ~190 players each
```

**Step 2: Validate Player ID Format**
```bash
sqlite3 ludi.db "SELECT nba_player_id, player_name FROM player_game_tracking WHERE game_date='2025-11-14' LIMIT 5;"
# IDs should be numeric (e.g., '1630639'), NOT slugs ('aj_lawson')
```

**Step 3: Check Data Completeness**
```bash
sqlite3 ludi.db "SELECT 
  COUNT(*) as total_rows,
  COUNT(drives_fga) as has_drives,
  COUNT(catch_shoot_fga) as has_catch_shoot,
  COUNT(pull_up_fga) as has_pullup,
  COUNT(dist_miles_off) as has_speed
FROM player_game_tracking 
WHERE game_date >= '2025-11-14';"
# All counts should be similar (10k-12k range)
```

---

## CONTINGENCY PLANS

### If IP Block Detected
1. **STOP SCRIPT** (Ctrl+C)
2. Wait 2-4 hours
3. Resume with `--start-date [LAST_SUCCESSFUL_DATE]`

### If 0 Records for Multiple Days
1. Check `nba.com/stats/players/drives` manually in browser
2. If site is up, inspect table headers → Update `DATA_MANIFEST` in script
3. Re-run failed date range

### If Browser Crashes
1. Script auto-continues from last processed date
2. Check logs for `[YYYY-MM-DD] Processing...` to find resume point
3. Re-run with `--start-date [NEXT_DATE]`

---

## POST-EXECUTION CHECKLIST

- [ ] Verify record count in `player_game_tracking` (~17,500 total)
- [ ] Spot-check 5 players' stats against NBA.com source
- [ ] Confirm Player IDs are numeric (not string slugs)
- [ ] Update `CLAUDE.md` Week 5 checklist: Mark "Execute Phase 1" as DONE
- [ ] Proceed to Phase 2 (Advanced Stats) or pause for validation

---

## APPROVAL TO LAUNCH

**Pre-Flight Checklist:**
- [x] Database schema updated (`player_game_tracking` has new columns)
- [x] ID extraction logic verified (extracts from hrefs)
- [x] Anti-bot measures enabled (headless=False, delays)
- [x] CLAUDE.md updated (source of truth confirmed)

**GO/NO-GO:** Awaiting user confirmation to execute.

**Command Ready:**
```bash
./.venv/bin/python scripts/sync_browser_backfill.py --start-date 2025-11-14 --end-date 2026-01-16
```
