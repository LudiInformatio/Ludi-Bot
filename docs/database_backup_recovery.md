# Database Backup and Recovery Guide

## Overview

The `db_backup.yml` workflow creates daily backups of the `ludi.db` SQLite database at 08:40 UTC (03:40 EST / 04:40 EDT). It can also be triggered manually via workflow_dispatch.

## Workflow Behavior

### Healthy Database
When the database passes integrity checks:
1. ✓ WAL checkpoint is performed
2. ✓ `PRAGMA quick_check` returns "ok"
3. ✓ Backup is created with standard naming: `ludi.db.backup_YYYYMMDD_HHMMSS.sqlite`
4. ✓ Backup is compressed and uploaded as artifact with standard name
5. ✓ Workflow succeeds

### Corrupted Database
When the database has corruption issues:
1. ⚠ WAL checkpoint is performed
2. ⚠ `PRAGMA quick_check` returns corruption details
3. ⚠ Backup is still created with `.corrupted` suffix: `ludi.db.backup_YYYYMMDD_HHMMSS.corrupted.sqlite`
4. ⚠ Backup is compressed and uploaded with `-CORRUPTED` label in artifact name
5. ⚠ Workflow displays warning message with recovery guidance
6. ✓ Workflow succeeds (does not fail)

## Database Recovery Process

### When Corruption is Detected

If the workflow reports database corruption:

1. **Check Recent Backups**
   ```bash
   ls -lh backups/database/
   ```

2. **Restore from Most Recent Clean Backup**
   ```bash
   # Backup the corrupted database for analysis
   cp ludi.db ludi.db.corrupted
   
   # Restore from backup
   cp backups/database/ludi.db.backup_YYYYMMDD_HHMMSS.sqlite ludi.db
   ```

3. **Verify Restored Database**
   ```bash
   python3 -c "
   import sqlite3
   con = sqlite3.connect('ludi.db')
   result = con.execute('PRAGMA quick_check;').fetchone()[0]
   print(f'Integrity: {result}')
   con.close()
   "
   ```

4. **Commit and Push**
   ```bash
   git add ludi.db
   git commit -m "chore: restore database from backup"
   git push
   ```

### GitHub Actions Artifacts

Backups are retained as GitHub Actions artifacts for 30 days. To download:

1. Go to: https://github.com/LudiInformatio/Ludi-Bot/actions/workflows/db_backup.yml
2. Click on a successful run
3. Download the artifact from the "Artifacts" section
4. Extract the `.tar.gz` file to get the `.sqlite` backup

## Testing the Workflow

Use the test script to validate workflow logic:

```bash
python3 test_db_backup_workflow.py
```

This tests:
- Database integrity checking
- WAL checkpoint
- Backup creation
- Backup verification
- Corruption handling

## Incident Response: 2026-01-18

**Issue**: Workflow failing with exit code 1 due to database corruption  
**Root Cause**: Multiple invalid page references in ludi.db (pages 5373-6190)  
**Resolution**: 
1. Database restored from `backups/database/ludi.db.backup_20260115_135412.sqlite`
2. Workflow updated to handle corruption gracefully (no longer fails on corruption)
3. Corrupted backups now marked and uploaded with warnings

**Changes Made**:
- Split integrity check into separate step with `continue-on-error: true`
- Added WAL checkpoint before integrity check
- Backup creation continues even if corruption detected
- Corrupted backups labeled with `.corrupted` suffix and `-CORRUPTED` artifact name
- Added warning step with recovery guidance

## Monitoring

The workflow will:
- ✅ Always succeed (unless database file is completely missing)
- ⚠ Display warnings if corruption is detected
- 📦 Upload backups regardless of corruption status
- 🏷️ Mark corrupted backups clearly in artifact names

## Prevention

To minimize corruption risk:
1. Ensure proper database closure in all modules
2. Use WAL mode (already enabled): `PRAGMA journal_mode=WAL;`
3. Avoid killing processes while database writes are in progress
4. Monitor GitHub Actions for corruption warnings
5. Investigate root cause when corruption is detected (not just restore)

## Related Files

- `.github/workflows/db_backup.yml` - Backup workflow
- `test_db_backup_workflow.py` - Validation test script
- `backups/database/` - Local backup storage
- `ludi.db` - Primary database file
- `ludi.db-wal` - Write-Ahead Log file (temporary)
- `ludi.db-shm` - Shared memory file (temporary)
