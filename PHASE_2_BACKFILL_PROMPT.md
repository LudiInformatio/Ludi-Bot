# GHOST PROTOCOL: PHASE 2 EXECUTION PROMPT
**Target:** Brain Backfill (Advanced Stats & Clutch Metrics)
**Date Range:** Nov 14, 2025 → Jan 16, 2026
**Priority:** HIGH
**Est. Runtime:** ~30-40 minutes

---

## MISSION BRIEFING

**Objective:** Backfill the "Brain" data that determines efficiency and clutch performance. This data supplements the "Physics" data (completed in Phase 1).

**Data Targets:**
1. **Advanced Stats** → Efficiency metrics (OFFRTG, DEFRTG, USG%, TS%, PACE).
2. **Clutch Stats** → Performance in last 5 min, score within 5 pts (PTS, FGM, FGA, FTM).

**Database Impact:**
- Target Tables: `player_game_advanced`, `player_clutch_stats`
- Expected Yield:
  - Advanced: ~190 records/day (Full Roster)
  - Clutch: ~40-80 records/day (Only players in close games)

---

## EXECUTION COMMAND

```bash
cd ~/Desktop/Ludi\ Informatio/Projects/Ludi-Bot
./.venv/bin/python scripts/sync_browser_backfill.py \
  --start-date 2025-11-14 \
  --end-date 2026-01-16
```

---

## WHAT TO MONITOR

### Success Indicators
✅ Console Output:
   ```
   [2026-01-15] Processing...
      Scanning Advanced Stats table...
      [DEBUG] Headers: ['PLAYER', 'TEAM', 'AGE', 'GP', 'W', 'L', 'MIN', 'OFFRTG', ...]
      [DEBUG] Found 201 rows for Advanced Stats
   ✓ Advanced Stats: 201 records
      Scanning Clutch Traditional table...
      [DEBUG] Headers: ['PLAYER', 'TEAM', 'GP', 'W', 'L', 'MIN', 'PTS', ...]
      [DEBUG] Found 79 rows for Clutch Traditional
   ✓ Clutch Traditional: 79 records
   ```

### Warning Signs
⚠️ `✓ Clutch Traditional: 0 records` → **Normal** for blowout days (no "clutch" minutes played).
⚠️ `✓ Advanced Stats: 0 records` → **Abnormal**. Check debug logs.

---

## VERIFICATION PROTOCOL

**Step 1: Check Record Counts**
```bash
sqlite3 ludi.db "
SELECT '--- ADVANCED STATS ---';
SELECT COUNT(*) FROM player_game_advanced;

SELECT '--- CLUTCH STATS ---';
SELECT COUNT(*) FROM player_clutch_stats;
"
```

**Step 2: Check Data Quality (sample row)**
```bash
sqlite3 ludi.db "
SELECT '--- SAMPLE ADVANCED ---';
SELECT player_name, off_rating, def_rating, usg_pct 
FROM player_game_advanced 
ORDER BY game_date DESC LIMIT 3;

SELECT '--- SAMPLE CLUTCH ---';
SELECT player_name, clutch_pts, clutch_fgm, clutch_fga 
FROM player_clutch_stats 
ORDER BY game_date DESC LIMIT 3;
"
```

---

## CONTINGENCY PLANS

### If Script Freezes
- The script has random delays (2-4s). If it hangs for >30s, check terminal for error messages.
- Ctrl+C to stop, then restart from the last successful date.

---

## APPROVAL TO LAUNCH

**Pre-Flight Checklist:**
- [x] `sync_browser_backfill.py` manifest updated (Advanced + Clutch enabled).
- [x] Redundant/Broken code removed from script.
- [x] Database schemas verified.

**GO/NO-GO:** Ready for execution.
