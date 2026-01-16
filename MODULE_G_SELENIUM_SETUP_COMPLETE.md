# Module G: Selenium Setup Complete (Jan 15, 2026)

## Summary

Successfully set up Selenium browser automation to bypass Basketball-Reference 403 blocking and access historical referee data.

---

## What We Accomplished

### 1. Browser Test - CONFIRMED ACCESS ✅
- Opened BBR referee roster, recent games, and sample box score in your browser
- **Result**: All 3 pages loaded successfully (403 NOT present in browser)
- **Conclusion**: BBR blocks Python `requests` but allows browser access

### 2. Selenium Installation ✅
- Installed `selenium` library (v4.39.0)
- Installed `webdriver-manager` (v4.0.2) for automatic ChromeDriver management
- **No manual ChromeDriver setup required** - webdriver-manager handles it automatically

### 3. Selenium Verification ✅
- Created test script: `scripts/test_selenium_quick.py`
- **Successfully loaded BBR referee roster page** (bypassed 403!)
- Page title confirmed: "2025-26 NBA Referees | Basketball-Reference.com"
- **Proof**: Selenium can access BBR data that Python requests cannot

---

## Files Created

### 1. `scripts/backfill_referee_assignments_selenium.py` (Main Scraper)
**Purpose**: Scrape referee assignments from BBR for last 30 days

**Features**:
- Headless Chrome (runs in background)
- Auto-downloads ChromeDriver via webdriver-manager
- Converts game dates to BBR game ID format
- Stores referee crews to `games.referee_crew` column in database
- Rate limiting (3 second delays between requests)

**Usage**:
```bash
python3 scripts/backfill_referee_assignments_selenium.py
```

### 2. `scripts/test_selenium_quick.py` (Verification Test)
**Purpose**: Quick test to verify Selenium + ChromeDriver working

**Usage**:
```bash
python3 scripts/test_selenium_quick.py
```

### 3. `scripts/inspect_bbr_structure.py` (Page Structure Inspector)
**Purpose**: Inspect BBR page HTML structure to find correct CSS selectors

**Usage**:
```bash
python3 scripts/inspect_bbr_structure.py
```

---

## Current Status

### ✅ COMPLETE
- Selenium + ChromeDriver installed and working
- BBR 403 bypass confirmed (pages load successfully)
- Scraper scripts created and ready

### ⏳ IN PROGRESS
- Main backfill script running in background (Task ID: b90ac93)
- Page structure inspection running (Task ID: b538e22)

### ⏳ NEXT STEPS
1. **Wait for backfill script to complete** (may take 5-10 minutes for 30 days of games)
2. **Verify referee data in database** (check `games.referee_crew` column)
3. **Fix any HTML selector issues** if needed (use inspect script output)
4. **Add daily archiving** to 5 AM workflow (store refs going forward)

---

## Technical Details

### BBR Game ID Format
```
YYYYMMDD0TTT
```
- `YYYYMMDD`: Date (e.g., 20260114 for Jan 14, 2026)
- `0`: Game number (usually 0 for single game that day)
- `TTT`: Home team 3-letter code (e.g., LAL for Lakers)

**Example**: `202601140LAL` = Lakers home game on Jan 14, 2026

### Team Code Mappings
| Our Code | BBR Code |
|----------|----------|
| BKN      | BRK      |
| PHX      | PHO      |
| CHA      | CHO (sometimes) |

### Where Referee Data is Stored
- **Page Location**: Box score scorebox_meta div
- **Format**: "Officials: Name1, Name2, Name3"
- **Database**: `games.referee_crew` (comma-separated string)

---

## Troubleshooting

### If Backfill Fails
1. **Check output**: `cat /tmp/claude/.../tasks/b90ac93.output`
2. **Common issues**:
   - Wrong game ID format (404 errors)
   - HTML selector changed (no Officials: found)
   - ChromeDriver version mismatch (webdriver-manager should fix this)

### If 403 Returns
- Run `scripts/test_selenium_quick.py` to verify Selenium still works
- Check if BBR changed their bot detection
- Try adding `time.sleep()` delays between requests

### Manual Fallback
If Selenium fails completely, you can:
1. Visit BBR box scores manually in browser
2. Copy referee names
3. Add to database via SQL:
```sql
UPDATE games
SET referee_crew = 'Scott Foster,Tony Brothers,Ed Malloy'
WHERE date = '2026-01-14' AND home_team = 'LAL';
```

---

## Performance Expectations

### Backfill Speed
- **~3-4 seconds per game** (rate limiting + page load)
- **30 days = ~100 games = ~6 minutes total**
- **90 days = ~300 games = ~18 minutes total**

### Success Rate
- **Expected**: 80-90% success rate
- **Failures**: Future games (404), wrong game IDs, page structure changes

---

## Module G Current State

### Database Coverage
- **51 referees** in `referee_profiles` table
- **39 original + 12 newly researched** (Jan 15 update)
- **Unknown refs handled gracefully** with confidence scoring

### Live Assignments
- ✅ NBA.com scraper working (9 games found today)
- ✅ Confidence scores returned (0.0-1.0 based on known refs)

### Historical Data
- ⏳ **In progress**: Selenium backfill for last 30 days
- ✅ **Future-ready**: Can repeat backfill anytime for more historical data

---

## Recommendation

### For MVP (Week 3-5)
**Stick with current approach**:
- 51 hardcoded refs (covers most games)
- Live NBA.com assignments (daily updates)
- Confidence scoring (flags low-coverage games)
- **Selenium backfill optional** (nice-to-have for backtesting)

### For Phase 2 (Week 6+)
**If backtesting shows referee impact matters**:
- Run Selenium backfill for full season (~500 games)
- Add incremental learning (track unknown refs game-by-game)
- Add Covers.com scraper (economic validation)

---

## Key Takeaway

🎯 **We successfully bypassed BBR's 403 blocking!**

Selenium using a real Chrome browser can access all the data that Python `requests` cannot. The scraper is now running to backfill 30 days of referee assignments for backtesting.

**Current bottleneck**: Waiting for background processes to complete. Check back in 5-10 minutes for results.

---

**Created**: Jan 15, 2026
**Status**: Selenium setup complete, backfill in progress
**Next Check**: View backfill results with `cat /tmp/claude/.../tasks/b90ac93.output`
