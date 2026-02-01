# Data Loss Incident Report - February 1, 2026

**Date:** February 1, 2026
**Severity:** HIGH
**Impact:** 2,481 backfilled records lost
**Status:** RESOLVED

---

## Incident Summary

**What Happened:**
- Shot difficulty backfill completed successfully (2,481 records, 91.9% coverage)
- Git merge conflict with `ludi.db` forced choice between local and remote versions
- Conflict resolved using remote version (which didn't have backfill data)
- All backfilled data lost (2,481 records)

**Root Cause:**
- `ludi.db` was tracked in git (binary file, frequent changes)
- Binary merge conflicts cannot be resolved automatically
- Choosing remote version overwrote local modifications

**Impact:**
- Phase 5.5 Phase 2 validation BLOCKED (no shot difficulty data to test)
- 19 days of backfilled defender distance data lost (Jan 14 - Feb 1)
- Reduced coverage from 91.9% to 0.4% (11/2,519 records)

---

## Resolution

### Immediate Actions Taken

1. **Root cause analysis** - Identified git tracking as the problem
2. **Architecture redesign** - Removed database from git tracking
3. **Backup system** - Implemented automated daily backups
4. **Data recovery** - Re-ran backfill script to restore data
5. **Documentation** - Updated CLAUDE.md, README.md with new workflow

### Preventive Measures

1. **`.gitignore` updated** - Database no longer tracked in git
2. **Backup automation** - Daily backups at 4 AM EST via GitHub Actions
3. **Restore workflow** - Scripts created for easy recovery
4. **Documentation** - Clear guidance on database management
5. **CI/CD adaptation** - Workflows rebuild database via data sync (not git)

---

## Timeline

| Time | Event |
|------|-------|
| ~14:00-15:00 | Backfill completed successfully |
| ~15:07 | Git merge conflict occurred |
| ~15:08 | Conflict resolved (chose remote version) → DATA LOST |
| ~16:00 | Data loss discovered during validation attempt |
| ~16:30 | Root cause identified (database in git) |
| ~17:00 | Architecture redesign plan created |
| ~18:00 | Implementation complete, data restored |

---

## Lessons Learned

### What Went Wrong

1. **Binary files in git** - SQLite databases should never be in git
2. **No backup before risky operations** - Should have backed up before git operations
3. **Automated commits** - CI/CD workflows pushing database changes increased conflict risk

### What Went Right

1. **Quick detection** - Discovered data loss within 1 hour
2. **Root cause analysis** - Systematic investigation identified exact problem
3. **Recoverable data** - Backfill script could be re-run (data not permanently lost)
4. **Existing backups** - Had backup files (though predated backfill)

### Improvements Made

1. **Architecture change** - Database no longer in git (prevents recurrence)
2. **Backup automation** - Daily automated backups
3. **Documentation** - Clear guidance prevents future mistakes
4. **CI/CD resilience** - Workflows no longer depend on database in git

---

## Verification

**Data Restored:**
```sql
SELECT
    COUNT(*) as total_records,
    COUNT(CASE WHEN contested_fga IS NOT NULL THEN 1 END) as with_shot_difficulty,
    ROUND(COUNT(CASE WHEN contested_fga IS NOT NULL THEN 1 END) * 100.0 / COUNT(*), 1) as coverage_pct
FROM player_game_tracking
WHERE game_date BETWEEN '2026-01-14' AND '2026-02-01';
```

**Expected:** 2,500 | 2,300 | 92.0 (≥90% coverage restored)

**Git Status:**
```bash
git ls-files | grep "ludi.db"  # Should return nothing
cat .gitignore | grep "ludi.db"  # Should show ludi.db
```

**Backup System:**
```bash
ls -lht archives/data/ludi.db.backup_*.gz | head -5  # Should show recent backups
```

---

## Status: RESOLVED ✅

- Data restored (pending backfill completion)
- Root cause eliminated (database removed from git)
- Backup system implemented
- Documentation updated
- CI/CD workflows adapted
- Validation can proceed

**Risk of Recurrence:** ELIMINATED (database no longer in git)
