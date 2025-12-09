#!/usr/bin/env python3
"""Check passive cleanup status and calculate potential storage savings"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add AI to path
installation_root = Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation")
ai_dir = installation_root / "AI"
sys.path.insert(0, str(ai_dir))

from monitoring.data_cleanup import DataCleanupManager

print("=" * 70)
print("PASSIVE DATA RECYCLING STATUS CHECK")
print("=" * 70)

# Check what files exist that would be cleaned
print("\nANALYZING FILES FOR CLEANUP...\n")

# Backup files
backup_files = list(installation_root.rglob("*.backup-*.json"))
backup_files.extend(list(installation_root.rglob("*.backup-*.db")))
backup_files.extend(list(installation_root.rglob("*.backup-*.log")))

cutoff_backup = datetime.now() - timedelta(days=7)
old_backups = [f for f in backup_files if datetime.fromtimestamp(f.stat().st_mtime) < cutoff_backup]
backup_size = sum(f.stat().st_size for f in old_backups) / (1024 * 1024)

print(f"Backup Files:")
print(f"   Total found: {len(backup_files)}")
print(f"   Old (>7 days): {len(old_backups)}")
print(f"   Space to free: {backup_size:.2f} MB")

# Test files
test_files = list(installation_root.rglob("test_*.py"))
test_files.extend(list(installation_root.rglob("temp_*.py")))
test_files = [f for f in test_files if 'quarantine' not in str(f) and '__pycache__' not in str(f) and 'Cursor versions' not in str(f)]

cutoff_test = datetime.now() - timedelta(days=1)
old_tests = [f for f in test_files if datetime.fromtimestamp(f.stat().st_mtime) < cutoff_test]
test_size = sum(f.stat().st_size for f in old_tests) / (1024 * 1024)

print(f"\nTest Files:")
print(f"   Total found: {len(test_files)}")
print(f"   Old (>1 day): {len(old_tests)}")
print(f"   Space to free: {test_size:.2f} MB")

# Log files
log_files = list(installation_root.rglob("*.log"))
log_files = [f for f in log_files if 'Past Logs' not in str(f) and 'Example Log' not in str(f) and 'Cursor versions' not in str(f) and '__pycache__' not in str(f)]

cutoff_log = datetime.now() - timedelta(days=14)
old_logs = [f for f in log_files if datetime.fromtimestamp(f.stat().st_mtime) < cutoff_log]
log_size = sum(f.stat().st_size for f in old_logs) / (1024 * 1024)

print(f"\nLog Files:")
print(f"   Total found: {len(log_files)}")
print(f"   Old (>14 days): {len(old_logs)}")
print(f"   Space to free: {log_size:.2f} MB")

# Browser activity databases
secure_dirs = list(installation_root.rglob("_secure_data"))
db_files = [d / "browser_activity.db" for d in secure_dirs if (d / "browser_activity.db").exists()]
print(f"\nBrowser Activity Databases:")
print(f"   Databases found: {len(db_files)}")
for db in db_files:
    size_mb = db.stat().st_size / (1024 * 1024)
    print(f"   - {db.parent.parent.name}: {size_mb:.2f} MB")

total_potential = backup_size + test_size + log_size

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total potential space to free: {total_potential:.2f} MB")
print(f"  - Backup files: {backup_size:.2f} MB")
print(f"  - Test files: {test_size:.2f} MB")
print(f"  - Log files: {log_size:.2f} MB")

print("\n" + "=" * 70)
print("RUNNING CLEANUP NOW...")
print("=" * 70)

# Run actual cleanup
manager = DataCleanupManager(installation_root)
stats = manager.cleanup_all()

print("\n" + "=" * 70)
print("CLEANUP RESULTS")
print("=" * 70)
print(f"Database records deleted: {stats['database_records_deleted']}")
print(f"Backup files deleted: {stats['backup_files_deleted']}")
print(f"Test files deleted: {stats['test_files_deleted']}")
print(f"Log files deleted: {stats['log_files_deleted']}")
print(f"AI learning processed: {stats.get('ai_learning_processed', 0)} records")
print(f"\nTOTAL SPACE FREED: {stats['total_space_freed_mb']:.2f} MB")
print("=" * 70)

