# Phase 3 Production Runbook — Canonical ID Cleanup

Purpose: safely mark duplicate/non-canonical player rows inactive, archive them, and preserve audit logs.

Prereqs:
- Confirm DB backup exists: `ludi.db.backup_YYYYMMDD_HHMMSS`
- Work on maintenance window; notify stakeholders

Steps (operator):

1) Backup production DB
```
cp ludi.db ludi.db.backup_$(date +%Y%m%d_%H%M%S)
```

2) Dry-run the migration against production copy (recommended)
```
python3 scripts/phase3_migration_dryrun.py --db ludi.db
```
Check output `missing_log_inserts` and `players_to_mark_inactive`.

3) Apply `migration_enable.sql` (idempotent)
```
sqlite3 ludi.db < migration_enable.sql
```

4) Post-apply verification
```
sqlite3 ludi.db "SELECT COUNT(*) FROM players WHERE is_active=1;"
sqlite3 ludi.db "SELECT COUNT(*) FROM players WHERE is_active=0;"
sqlite3 ludi.db "SELECT COUNT(*) FROM player_canonical_ids_inactive_log;"
```
Expected: active ~500, inactive ~1460, log ~inactive count.

5) Optional: create `players_archived` from inactive rows (if you prefer physical archive)
```
sqlite3 ludi.db "DROP TABLE IF EXISTS players_archived; CREATE TABLE players_archived AS SELECT * FROM players WHERE is_active=0;"
```

6) Rollback options
- Restore backup: `cp ludi.db.backup_YYYYMMDD_HHMMSS ludi.db`
- Or re-activate specific rows using `player_canonical_ids_inactive_log` to update `players`.

Monitoring & smoke tests
- Run `python3 scripts/phase3_post_migration_smoke.py`
- Run targeted pytest: `pytest -q test_pipeline.py test_integration.py`

Notes
- `migration_enable.sql` assumes `player_canonical_ids_inactive_log` or `players_archived` present; dry-run shows zero for already-applied test DB.
