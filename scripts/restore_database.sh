#!/bin/bash
# Restore database from backup

set -e

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore_database.sh <backup_file.gz>"
    echo ""
    echo "Available backups (most recent first):"
    ls -lht archives/data/ludi.db.backup_*.gz 2>/dev/null | head -10
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Extracting backup..."
gunzip -c "${BACKUP_FILE}" > ludi.db.restore_temp

echo "Verifying backup integrity..."
if sqlite3 ludi.db.restore_temp "PRAGMA integrity_check;" | grep -q "ok"; then
    echo "✅ Backup integrity verified"

    # Backup current database before overwriting
    if [ -f "ludi.db" ]; then
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        mv ludi.db "ludi.db.before_restore_${TIMESTAMP}"
        echo "📦 Current database backed up to: ludi.db.before_restore_${TIMESTAMP}"
    fi

    # Restore
    mv ludi.db.restore_temp ludi.db
    echo "✅ Database restored from ${BACKUP_FILE}"

    # Show database info
    echo ""
    echo "Database info:"
    ls -lh ludi.db
    sqlite3 ludi.db "SELECT COUNT(*) as tables FROM sqlite_master WHERE type='table';"
else
    echo "❌ Backup file is corrupted, restoration aborted"
    rm ludi.db.restore_temp
    exit 1
fi
