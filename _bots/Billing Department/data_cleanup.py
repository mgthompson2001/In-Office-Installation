#!/usr/bin/env python3
"""
Centralized Data Cleanup Utility - Passive data recycling system for ALL bots
Automatically removes unnecessary data to manage storage limits across the entire installation.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_LOGGER = logging.getLogger("data_cleanup")


class DataCleanupManager:
    """Manages passive cleanup of collected data to prevent storage bloat across all bots."""
    
    # Retention policies (days)
    DATABASE_RETENTION_DAYS = 30  # Keep browser activity data for 30 days
    BACKUP_RETENTION_DAYS = 7  # Keep backup files for 7 days
    LOG_RETENTION_DAYS = 14  # Keep log files for 14 days
    TEST_FILE_RETENTION_DAYS = 1  # Keep test files for 1 day
    
    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.cleanup_stats = {
            'database_records_deleted': 0,
            'backup_files_deleted': 0,
            'test_files_deleted': 0,
            'log_files_deleted': 0,
            'total_space_freed_mb': 0.0
        }
    
    def cleanup_all(self) -> dict:
        """Run all cleanup operations and return statistics."""
        _LOGGER.info("Starting passive data cleanup across all bots...")
        self.cleanup_stats = {
            'database_records_deleted': 0,
            'backup_files_deleted': 0,
            'test_files_deleted': 0,
            'log_files_deleted': 0,
            'total_space_freed_mb': 0.0
        }
        
        # Cleanup browser activity databases
        self._cleanup_browser_databases()
        
        # Cleanup backup files
        self._cleanup_backup_files()
        
        # Cleanup test files
        self._cleanup_test_files()
        
        # Cleanup old log files
        self._cleanup_log_files()
        
        _LOGGER.info(f"Cleanup complete. Space freed: {self.cleanup_stats['total_space_freed_mb']:.2f} MB")
        return self.cleanup_stats
    
    def _cleanup_browser_databases(self) -> None:
        """Remove old records from browser activity databases across all bots."""
        try:
            # Find all _secure_data directories
            secure_dirs = list(self.installation_dir.rglob("_secure_data"))
            
            for secure_dir in secure_dirs:
                db_path = secure_dir / "browser_activity.db"
                if not db_path.exists():
                    continue
                
                cutoff_date = datetime.now() - timedelta(days=self.DATABASE_RETENTION_DAYS)
                cutoff_str = cutoff_date.isoformat()
                
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Delete old page navigations
                    cursor.execute(
                        "DELETE FROM page_navigations WHERE timestamp < ?",
                        (cutoff_str,)
                    )
                    nav_deleted = cursor.rowcount
                    
                    # Delete old element interactions
                    cursor.execute(
                        "DELETE FROM element_interactions WHERE timestamp < ?",
                        (cutoff_str,)
                    )
                    elem_deleted = cursor.rowcount
                    
                    conn.commit()
                    
                    # Vacuum database to reclaim space
                    cursor.execute("VACUUM")
                    conn.commit()
                    conn.close()
                    
                    total_deleted = nav_deleted + elem_deleted
                    if total_deleted > 0:
                        self.cleanup_stats['database_records_deleted'] += total_deleted
                        _LOGGER.info(f"Cleaned {total_deleted} old records from {db_path}")
                        
                        # Calculate space freed (approximate)
                        file_size_before = db_path.stat().st_size
                        # Re-check after vacuum
                        file_size_after = db_path.stat().st_size
                        space_freed = (file_size_before - file_size_after) / (1024 * 1024)
                        self.cleanup_stats['total_space_freed_mb'] += space_freed
                        
                except Exception as e:
                    _LOGGER.warning(f"Error cleaning database {db_path}: {e}")
                    
        except Exception as e:
            _LOGGER.warning(f"Error during database cleanup: {e}")
    
    def _cleanup_backup_files(self) -> None:
        """Remove old backup files across all bots."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.BACKUP_RETENTION_DAYS)
            
            # Find all backup files
            backup_patterns = ["*.backup-*.json", "*.backup-*.db", "*.backup-*.log"]
            
            for pattern in backup_patterns:
                for backup_file in self.installation_dir.rglob(pattern):
                    try:
                        # Get file modification time
                        file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                        
                        if file_mtime < cutoff_date:
                            file_size = backup_file.stat().st_size / (1024 * 1024)  # MB
                            backup_file.unlink()
                            self.cleanup_stats['backup_files_deleted'] += 1
                            self.cleanup_stats['total_space_freed_mb'] += file_size
                            _LOGGER.info(f"Deleted old backup: {backup_file}")
                    except Exception as e:
                        _LOGGER.warning(f"Error deleting backup {backup_file}: {e}")
                        
        except Exception as e:
            _LOGGER.warning(f"Error during backup cleanup: {e}")
    
    def _cleanup_test_files(self) -> None:
        """Remove old test files across all bots."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.TEST_FILE_RETENTION_DAYS)
            
            # Find test files
            test_patterns = ["test_*.py", "temp_*.py", "*_test.py"]
            
            for pattern in test_patterns:
                for test_file in self.installation_dir.rglob(pattern):
                    # Skip if in quarantine or important directories
                    if any(skip in str(test_file) for skip in ['quarantine', '__pycache__', '.git', 'Cursor versions']):
                        continue
                    
                    try:
                        # Get file modification time
                        file_mtime = datetime.fromtimestamp(test_file.stat().st_mtime)
                        
                        if file_mtime < cutoff_date:
                            file_size = test_file.stat().st_size / (1024 * 1024)  # MB
                            test_file.unlink()
                            self.cleanup_stats['test_files_deleted'] += 1
                            self.cleanup_stats['total_space_freed_mb'] += file_size
                            _LOGGER.info(f"Deleted old test file: {test_file}")
                    except Exception as e:
                        _LOGGER.warning(f"Error deleting test file {test_file}: {e}")
                        
        except Exception as e:
            _LOGGER.warning(f"Error during test file cleanup: {e}")
    
    def _cleanup_log_files(self) -> None:
        """Remove old log files across all bots (keep recent ones)."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.LOG_RETENTION_DAYS)
            
            # Find log files
            log_patterns = ["*.log", "*.log.*"]
            
            for pattern in log_patterns:
                for log_file in self.installation_dir.rglob(pattern):
                    # Skip if in important directories or "Past Logs" folders
                    if any(skip in str(log_file) for skip in ['__pycache__', '.git', 'Past Logs', 'Example Log', 'Cursor versions']):
                        continue
                    
                    try:
                        # Get file modification time
                        file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                        
                        if file_mtime < cutoff_date:
                            file_size = log_file.stat().st_size / (1024 * 1024)  # MB
                            log_file.unlink()
                            self.cleanup_stats['log_files_deleted'] += 1
                            self.cleanup_stats['total_space_freed_mb'] += file_size
                            _LOGGER.info(f"Deleted old log file: {log_file}")
                    except Exception as e:
                        _LOGGER.warning(f"Error deleting log file {log_file}: {e}")
                        
        except Exception as e:
            _LOGGER.warning(f"Error during log file cleanup: {e}")


def get_cleanup_manager(installation_dir: Optional[Path] = None) -> DataCleanupManager:
    """Get or create a DataCleanupManager instance.
    
    Args:
        installation_dir: Path to installation root. If None, auto-detects from AI folder location.
    """
    if installation_dir is None:
        # Auto-detect: if we're in AI/monitoring/data_cleanup.py, go up 2 levels to installation root
        current_file = Path(__file__).resolve()
        if current_file.parent.name == "monitoring" and current_file.parent.parent.name == "AI":
            installation_dir = current_file.parent.parent.parent
        elif current_file.parent.name == "_bots":
            # Fallback: if in _bots directory, go up one level
            installation_dir = current_file.parent.parent
        else:
            # Last resort: assume we're in installation root
            installation_dir = current_file.parent.parent.parent
    return DataCleanupManager(Path(installation_dir))


def run_passive_cleanup(installation_dir: Optional[Path] = None) -> dict:
    """Run passive cleanup across all bots and return statistics.
    
    This is the main entry point that all bots should call.
    
    Args:
        installation_dir: Path to installation root. If None, auto-detects.
        
    Returns:
        Dictionary with cleanup statistics
    """
    manager = get_cleanup_manager(installation_dir)
    return manager.cleanup_all()


def init_passive_cleanup(installation_dir: Optional[Path] = None, logger=None) -> None:
    """Initialize passive cleanup in a background thread (non-blocking).
    
    This is the recommended way for bots to enable cleanup - it runs
    automatically in the background without blocking bot startup.
    
    Args:
        installation_dir: Path to installation root. If None, auto-detects.
        logger: Optional logger instance. If None, uses default logging.
    """
    import threading
    
    def cleanup_thread():
        try:
            stats = run_passive_cleanup(installation_dir)
            # Only log if significant cleanup occurred
            if stats['total_space_freed_mb'] > 0.1:
                log_msg = (f"🧹 Passive cleanup: Freed {stats['total_space_freed_mb']:.2f} MB "
                          f"({stats['database_records_deleted']} DB records, "
                          f"{stats['backup_files_deleted']} backups, "
                          f"{stats['test_files_deleted']} test files, "
                          f"{stats['log_files_deleted']} logs)")
                if logger:
                    logger.info(log_msg)
                else:
                    _LOGGER.info(log_msg)
        except Exception as e:
            # Silently fail - cleanup shouldn't break bot startup
            if logger:
                logger.debug(f"Passive cleanup failed (non-critical): {e}")
            else:
                _LOGGER.debug(f"Passive cleanup failed (non-critical): {e}")
    
    # Run in background thread
    cleanup_thread_obj = threading.Thread(target=cleanup_thread, daemon=True)
    cleanup_thread_obj.start()

