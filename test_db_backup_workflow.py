#!/usr/bin/env python3
"""
Test script to validate the db_backup workflow logic
"""

import os
import sqlite3
import sys
import tempfile
from datetime import datetime


def test_integrity_check(db_path):
    """Test the integrity check step"""
    print("=" * 60)
    print("Testing: Check DB integrity")
    print("=" * 60)
    
    if not os.path.exists(db_path):
        print(f"❌ Missing database: {db_path}")
        return False, "missing"
    
    con = sqlite3.connect(db_path)
    try:
        # First try to checkpoint WAL to ensure all changes are merged
        con.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        print("✓ WAL checkpoint completed")
        
        # Run integrity check
        result = con.execute("PRAGMA quick_check;").fetchone()[0]
        print(f"✓ PRAGMA quick_check: {result}")
        
        if result == "ok":
            status = "ok"
        else:
            status = "corrupted"
            print("⚠ Database corruption detected!")
        
        return True, status
    except Exception as e:
        print(f"❌ Error during integrity check: {e}")
        return False, "error"
    finally:
        con.close()


def test_backup_creation(db_path, backup_dir, status):
    """Test the backup creation step"""
    print("\n" + "=" * 60)
    print("Testing: Create backup")
    print("=" * 60)
    
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    
    # Add status suffix if corrupted
    suffix = ".corrupted" if status == "corrupted" else ""
    backup_path = os.path.join(backup_dir, f"ludi.db.backup_{ts}{suffix}.sqlite")
    
    con = sqlite3.connect(db_path)
    try:
        dest = sqlite3.connect(backup_path)
        try:
            con.backup(dest)
            print(f"✓ Backup created: {backup_path}")
            if status == "corrupted":
                print("⚠ WARNING: Backup created from corrupted database!")
        finally:
            dest.close()
    except Exception as e:
        print(f"❌ Error creating backup: {e}")
        return False, None
    finally:
        con.close()
    
    # Verify backup
    try:
        dest = sqlite3.connect(backup_path)
        backup_result = dest.execute("PRAGMA quick_check;").fetchone()[0]
        dest.close()
        print(f"✓ Backup integrity check: {backup_result}")
        
        # Get backup size
        backup_size = os.path.getsize(backup_path)
        print(f"✓ Backup size: {backup_size / 1024 / 1024:.2f} MB")
        
        return True, backup_path
    except Exception as e:
        print(f"❌ Error verifying backup: {e}")
        return False, None


def main():
    print("\n🧪 Testing DB Backup Workflow Logic")
    print("=" * 60)
    
    db_path = "ludi.db"
    backup_dir = tempfile.mkdtemp()
    
    # Step 1: Check database presence
    print(f"\nDatabase path: {db_path}")
    print(f"Temp backup dir: {backup_dir}")
    
    # Step 2: Check integrity
    success, status = test_integrity_check(db_path)
    if not success:
        print("\n❌ FAILED: Integrity check step")
        sys.exit(1)
    
    print(f"\n✓ Status: {status}")
    
    # Step 3: Create backup
    success, backup_path = test_backup_creation(db_path, backup_dir, status)
    if not success:
        print("\n❌ FAILED: Backup creation step")
        sys.exit(1)
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print(f"Database status: {status.upper()}")
    print(f"Backup created: {backup_path}")
    
    if status == "corrupted":
        print("\n⚠ WORKFLOW BEHAVIOR:")
        print("  - Backup created successfully despite corruption")
        print("  - Backup marked with '.corrupted' suffix")
        print("  - Artifact will be labeled with '-CORRUPTED'")
        print("  - Warning message will be displayed")
    else:
        print("\n✓ WORKFLOW BEHAVIOR:")
        print("  - Database is healthy")
        print("  - Backup created successfully")
        print("  - No warnings needed")
    
    print("\n🎉 Workflow is ready to run on GitHub Actions!")


if __name__ == "__main__":
    main()
