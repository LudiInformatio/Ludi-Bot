#!/bin/bash
# Daily database backup with 30-day retention

set -e

BACKUP_DIR="archives/data"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/ludi.db.backup_${TIMESTAMP}"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Create backup using SQLite hot backup API
if [ -f "ludi.db" ]; then
    echo "Creating database backup..."
    sqlite3 ludi.db ".backup ${BACKUP_FILE}"

    # Compress for space savings
    gzip "${BACKUP_FILE}"

    # Keep only last 30 days of backups
    find "${BACKUP_DIR}" -name "ludi.db.backup_*.gz" -mtime +30 -delete

    echo "✅ Database backup created: ${BACKUP_FILE}.gz"

    # Show backup size
    ls -lh "${BACKUP_FILE}.gz"
else
    echo "❌ Database file not found: ludi.db"
    exit 1
fi
