#!/bin/bash

# Configuration
BACKUP_DIR="backups/database"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_FILE="ludi.db"
BACKUP_FILE="$BACKUP_DIR/ludi_$TIMESTAMP.db"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Perform safe hot backup using SQLite native command
# This prevents copying a locked/corrupt file during writes
echo "📦 Starting backup of $DB_FILE..."
sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"

if [ $? -eq 0 ]; then
    echo "✅ Backup successful: $BACKUP_FILE"
    
    # Rotation: Keep only the last 7 days of backups
    echo "🧹 Cleaning up old backups (retention: 7 days)..."
    find "$BACKUP_DIR" -name "ludi_*.db" -type f -mtime +7 -delete
else
    echo "❌ Backup FAILED!"
    exit 1
fi
