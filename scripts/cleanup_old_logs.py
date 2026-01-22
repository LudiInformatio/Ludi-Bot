#!/usr/bin/env python3
"""
Log Cleanup Script

Automatically cleans up old logs and artifacts to maintain disk space.
Designed to run as part of production workflows.

Retention Policies:
- Production logs: 30 days
- Backtest logs: 90 days  
- Health reports: 30 days
- Visual assets: 7 days
- Database backups: 30 days

Usage:
    python scripts/cleanup_old_logs.py [--dry-run] [--verbose]
"""

import os
import argparse
import glob
from datetime import datetime, timedelta
from pathlib import Path


class LogCleanup:
    def __init__(self, dry_run=False, verbose=False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.deleted_files = []
        self.deleted_size = 0
        
        # Cleanup policies (days)
        self.policies = {
            'logs/production/*.log': 30,
            'logs/production/*.log.gz': 30,
            'logs/backtest/*.log': 90,
            'logs/backtest/*.log.gz': 90,
            'logs/health/*.json': 30,
            'logs/validation/*.txt': 30,
            'assets/generated/*.png': 7,
            'backups/database/*.db': 30,
            'backups/database/*.db.gz': 30,
            'docs/weekly_validation_*.md': 90,
            'api_usage_log.json': 60,  # Single file, check modification time
        }
        
    def file_is_older_than_days(self, filepath: Path, days: int) -> bool:
        """Check if file is older than specified days"""
        try:
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            cutoff = datetime.now() - timedelta(days=days)
            return mtime < cutoff
        except OSError:
            # If we can't stat the file, consider it old
            return True
    
    def get_file_size(self, filepath: Path) -> int:
        """Get file size in bytes"""
        try:
            return filepath.stat().st_size
        except OSError:
            return 0
    
    def clean_pattern(self, pattern: str, days: int) -> dict:
        """Clean files matching a pattern with specific retention days"""
        
        # Convert relative pattern to absolute path
        full_pattern = self.project_root / pattern
        files = list(self.project_root.glob(pattern))
        
        deleted_count = 0
        deleted_size = 0
        skipped_count = 0
        
        for filepath in files:
            if filepath.is_file():
                if self.file_is_older_than_days(filepath, days):
                    size = self.get_file_size(filepath)
                    
                    if self.dry_run:
                        self.deleted_files.append(str(filepath))
                        self.deleted_size += size
                        deleted_count += 1
                        if self.verbose:
                            age_days = (datetime.now() - datetime.fromtimestamp(filepath.stat().st_mtime)).days
                            print(f"  Would delete: {filepath.name} (age: {age_days}d, size: {self.format_size(size)})")
                    else:
                        try:
                            filepath.unlink()
                            self.deleted_files.append(str(filepath))
                            self.deleted_size += size
                            deleted_count += 1
                            if self.verbose:
                                age_days = (datetime.now() - datetime.fromtimestamp(filepath.stat().st_mtime)).days
                                print(f"  Deleted: {filepath.name} (age: {age_days}d, size: {self.format_size(size)})")
                        except OSError as e:
                            if self.verbose:
                                print(f"  Error deleting {filepath.name}: {e}")
                            skipped_count += 1
                else:
                    skipped_count += 1
                    if self.verbose:
                        age_days = (datetime.now() - datetime.fromtimestamp(filepath.stat().st_mtime)).days
                        print(f"  Keeping: {filepath.name} (age: {age_days}d)")
        
        return {
            'deleted_count': deleted_count,
            'deleted_size': deleted_size,
            'skipped_count': skipped_count
        }
    
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"
    
    def clean_empty_directories(self):
        """Remove empty directories in logs/ and backups/"""
        
        empty_dirs = []
        
        for base_dir in ['logs', 'backups']:
            base_path = self.project_root / base_dir
            if not base_path.exists():
                continue
                
            # Find all directories under base_dir
            for dirpath in base_path.rglob('*'):
                if dirpath.is_dir():
                    try:
                        # Check if directory is empty (excluding .gitkeep)
                        contents = [f for f in dirpath.iterdir() if f.name != '.gitkeep']
                        if not contents:
                            empty_dirs.append(dirpath)
                    except OSError:
                        continue
        
        # Remove empty directories (reverse order to handle nested dirs first)
        for dirpath in sorted(empty_dirs, reverse=True):
            if self.dry_run:
                if self.verbose:
                    print(f"  Would remove empty directory: {dirpath.relative_to(self.project_root)}")
            else:
                try:
                    dirpath.rmdir()
                    if self.verbose:
                        print(f"  Removed empty directory: {dirpath.relative_to(self.project_root)}")
                except OSError:
                    # Directory might have been created by another process
                    pass
    
    def run_cleanup(self):
        """Execute the cleanup process"""
        
        print("🧹 LOG CLEANUP")
        print("==============")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE DELETION'}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("")
        
        total_deleted_files = 0
        total_deleted_size = 0
        total_skipped_files = 0
        
        # Process each pattern
        for pattern, days in self.policies.items():
            print(f"🔍 Processing: {pattern} (retain {days} days)")
            
            # Check if pattern exists
            if not list(self.project_root.glob(pattern)):
                print(f"  ⚠️  No files found matching pattern")
                print("")
                continue
            
            result = self.clean_pattern(pattern, days)
            total_deleted_files += result['deleted_count']
            total_deleted_size += result['deleted_size']
            total_skipped_files += result['skipped_count']
            
            if result['deleted_count'] > 0 or self.verbose:
                print(f"  Deleted: {result['deleted_count']} files ({self.format_size(result['deleted_size'])})")
                print(f"  Kept: {result['skipped_count']} files")
            print("")
        
        # Clean empty directories
        print("🗂️  Cleaning empty directories...")
        self.clean_empty_directories()
        print("")
        
        # Summary
        print("📊 CLEANUP SUMMARY")
        print("==================")
        print(f"Total files deleted: {total_deleted_files}")
        print(f"Total space freed: {self.format_size(total_deleted_size)}")
        print(f"Total files kept: {total_skipped_files}")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.dry_run:
            print("")
            print("⚠️  DRY RUN MODE - No files were actually deleted")
            print("Run without --dry-run to perform actual cleanup")
        
        return {
            'deleted_files': total_deleted_files,
            'deleted_size': total_deleted_size,
            'skipped_files': total_skipped_files,
            'dry_run': self.dry_run
        }


def main():
    parser = argparse.ArgumentParser(description='Clean up old logs and artifacts')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--verbose', action='store_true', 
                       help='Verbose output showing each file processed')
    
    args = parser.parse_args()
    
    # Check if we're in the right directory
    if not Path('ludi.db').exists():
        print("❌ Error: ludi.db not found. Run from project root directory.")
        return 1
    
    # Run cleanup
    cleanup = LogCleanup(dry_run=args.dry_run, verbose=args.verbose)
    result = cleanup.run_cleanup()
    
    return 0


if __name__ == "__main__":
    exit(main())