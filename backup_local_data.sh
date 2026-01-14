#!/bin/bash
# Quick backup of local-only data (not in git)

BACKUP_DIR="backups/local_data_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Backing up local data to $BACKUP_DIR..."

# Database
cp ludi.db "$BACKUP_DIR/ludi.db"
echo "  ✓ ludi.db ($(du -h ludi.db | cut -f1))"

# CSVs
cp -r data/raw_nba_data "$BACKUP_DIR/"
echo "  ✓ data/raw_nba_data/"

# Progress logs
cp logs/tracking_sync_progress.json "$BACKUP_DIR/" 2>/dev/null || true
echo "  ✓ logs/tracking_sync_progress.json"

# Cache (optional - large)
# cp -r cache/ "$BACKUP_DIR/" 2>/dev/null || true

echo ""
echo "Backup complete: $BACKUP_DIR"
du -sh "$BACKUP_DIR"
