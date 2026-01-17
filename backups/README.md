# Database Backups

## Naming Convention
`ludi.db.backup_YYYYMMDD_HHMMSS`

## Retention Policy
- Keep last 7 daily backups
- Keep last 4 weekly backups (Sunday)
- Keep last 12 monthly backups (1st of month)

## Latest Backups
- **Jan 15, 2026 (13:54):** 14.8MB (before Module G Phase 5)
- **Jan 4, 2026 (20:18):** 86KB (early version)

## Notes
Database backups are created automatically by the system. The backup script is located at `scripts/backup_local_data.sh`.
