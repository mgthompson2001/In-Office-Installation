#!/usr/bin/env python3
"""
Centralized Data Cleanup Utility - Passive data recycling system for ALL bots
Automatically removes unnecessary data to manage storage limits across the entire installation.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import gzip
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_LOGGER = logging.getLogger("data_cleanup")

# Import system configuration and data transfer
try:
    from .system_config import is_employee_computer, is_central_computer, get_central_data_path, get_computer_id, get_config_path
    from .data_transfer import DataTransferManager
except ImportError:
    # Fallback for direct imports
    try:
        from system_config import is_employee_computer, is_central_computer, get_central_data_path, get_computer_id, get_config_path
        from data_transfer import DataTransferManager
    except ImportError:
        # If modules don't exist yet, define stub functions
        def is_employee_computer(installation_dir): return False
        def is_central_computer(installation_dir): return True
        def get_central_data_path(installation_dir): return None
        def get_computer_id(installation_dir): return "unknown"
        DataTransferManager = None


class DataCleanupManager:
    """Manages passive cleanup of collected data to prevent storage bloat across all bots."""
    
    # Retention policies (days)
    DATABASE_RETENTION_DAYS = 30  # Keep browser activity data for 30 days
    BACKUP_RETENTION_DAYS = 7  # Keep backup files for 7 days
    LOG_RETENTION_DAYS = 14  # Keep log files for 14 days
    TEST_FILE_RETENTION_DAYS = 1  # Keep test files for 1 day
    TRAINING_DATA_KEEP_DATASETS = 3  # Keep only last N training datasets (compressed)
    TRAINING_DATA_ARCHIVE_DAYS = 30  # Archive training data older than N days
    
    def __init__(self, installation_dir: Path):
        self.installation_dir = Path(installation_dir)
        self.cleanup_stats = {
            'database_records_deleted': 0,
            'backup_files_deleted': 0,
            'test_files_deleted': 0,
            'log_files_deleted': 0,
            'training_files_compressed': 0,
            'training_files_archived': 0,
            'training_files_deleted': 0,
            'total_space_freed_mb': 0.0
        }
    
    def cleanup_all(self) -> dict:
        """Run all cleanup operations and return statistics.
        
        IMPORTANT: This runs AI learning FIRST to extract training data before recycling.
        Flow: Data Collection → AI Learning → Data Recycling
        
        For employee computers: Transfers data to central location instead of training.
        For central computer: Normal training and cleanup flow.
        """
        _LOGGER.info("Starting passive data cleanup across all bots...")
        self.cleanup_stats = {
            'database_records_deleted': 0,
            'backup_files_deleted': 0,
            'test_files_deleted': 0,
            'log_files_deleted': 0,
            'training_files_compressed': 0,
            'training_files_archived': 0,
            'training_files_deleted': 0,
            'total_space_freed_mb': 0.0,
            'ai_learning_processed': 0,
            'files_transferred': 0,
            'bytes_transferred': 0
        }
        
        # Check if this is an employee computer (data collection only)
        if is_employee_computer(self.installation_dir):
            _LOGGER.info("Employee computer detected - transferring data to central location...")
            return self._run_employee_mode()
        
        # CENTRAL COMPUTER MODE - Normal training and cleanup flow
        _LOGGER.info("Central computer mode - running training and cleanup...")
        
        # STEP 0: COLLECT DATA FROM EMPLOYEE COMPUTERS (if central computer)
        # Check if we have a central data path configured (for collecting from employees)
        try:
            from .system_config import load_config
            config = load_config(self.installation_dir)
            # If central computer has a central_data_path set, collect from it
            central_collection_path = config.get("central_data_path")
            if central_collection_path and Path(central_collection_path).exists():
                self._collect_employee_data(Path(central_collection_path))
        except Exception as e:
            _LOGGER.debug(f"Employee data collection check failed (non-critical): {e}")
        
        # STEP 1: AI LEARNING - Extract and process data for training BEFORE recycling
        try:
            self._run_ai_learning()
        except Exception as e:
            _LOGGER.warning(f"AI learning step failed (non-critical): {e}")
        
        # STEP 1.5: OPENAI FINE-TUNING - DISABLED (to avoid API charges)
        # Uncomment below to enable OpenAI fine-tuning:
        # try:
        #     self._run_openai_fine_tuning()
        # except Exception as e:
        #     _LOGGER.warning(f"OpenAI fine-tuning step failed (non-critical): {e}")
        
        # STEP 1.6: LOCAL TRAINING (Ollama) - Free, local training
        try:
            self._run_local_training()
        except Exception as e:
            _LOGGER.warning(f"Local training step failed (non-critical): {e}")
        
        # STEP 2: DATA RECYCLING - Clean up old data after AI has learned from it
        # Cleanup browser activity databases
        self._cleanup_browser_databases()
        
        # Cleanup backup files
        self._cleanup_backup_files()
        
        # Cleanup test files
        self._cleanup_test_files()
        
        # Cleanup old log files
        self._cleanup_log_files()
        
        # Cleanup and compress training data files
        self._cleanup_training_data()
        
        _LOGGER.info(f"Cleanup complete. Space freed: {self.cleanup_stats['total_space_freed_mb']:.2f} MB")
        return self.cleanup_stats
    
    def _run_employee_mode(self) -> dict:
        """Run employee computer mode: Transfer data to central location, minimal cleanup."""
        try:
            # Get central data path
            central_path = get_central_data_path(self.installation_dir)
            if not central_path:
                _LOGGER.warning("Employee mode enabled but central_data_path not configured. Skipping transfer.")
                return self.cleanup_stats
            
            central_path = Path(central_path)
            if not central_path.exists():
                _LOGGER.warning(f"Central data path does not exist: {central_path}. Creating it...")
                try:
                    central_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    _LOGGER.error(f"Cannot create central data path: {e}")
                    return self.cleanup_stats
            
            # Get computer ID
            computer_id = get_computer_id(self.installation_dir)
            
            # Check if it's time to transfer
            if DataTransferManager:
                transfer_manager = DataTransferManager(self.installation_dir)
                
                # Load config to get transfer interval
                from .system_config import load_config
                config = load_config(self.installation_dir)
                interval_hours = config.get("transfer_interval_hours", 24)
                
                # Check last transfer time
                last_transfer_file = self.installation_dir / "AI" / "monitoring" / "last_transfer.json"
                if transfer_manager.should_transfer(last_transfer_file, interval_hours):
                    _LOGGER.info(f"Transferring data to central location: {central_path}")
                    
                    # Transfer data
                    transfer_stats = transfer_manager.transfer_data_to_central(central_path, computer_id)
                    
                    # Update stats
                    self.cleanup_stats['files_transferred'] = transfer_stats.get('files_transferred', 0)
                    self.cleanup_stats['bytes_transferred'] = transfer_stats.get('bytes_transferred', 0)
                    
                    # Record transfer time
                    transfer_manager.record_transfer(last_transfer_file)
                    
                    _LOGGER.info(f"Transfer complete: {transfer_stats['files_transferred']} files, "
                               f"{transfer_stats['bytes_transferred'] / (1024*1024):.2f} MB")
                else:
                    _LOGGER.debug("Transfer interval not reached, skipping transfer")
            
            # Minimal cleanup on employee computers (only very old files)
            # Don't delete training data - it needs to be transferred first
            # Only clean up old logs and test files
            self._cleanup_log_files()
            self._cleanup_test_files()
            
            # Clean up browser databases (but keep recent ones for transfer)
            # Use longer retention for employee computers
            self._cleanup_browser_databases(retention_days=60)  # Keep 60 days instead of 30
            
            return self.cleanup_stats
            
        except Exception as e:
            _LOGGER.warning(f"Error in employee mode: {e}")
            return self.cleanup_stats
    
    def _run_ai_learning(self) -> None:
        """Run AI learning to extract training data from collected data."""
        try:
            # Import AI learning processor
            import sys
            from pathlib import Path
            
            # Find AI learning module
            ai_dir = self.installation_dir / "AI"
            learning_path = ai_dir / "learning" / "data_processor.py"
            
            if learning_path.exists():
                # Add AI directory to path
                if str(ai_dir) not in sys.path:
                    sys.path.insert(0, str(ai_dir))
                
                from learning.data_processor import process_data_for_ai
                
                # Process all data for AI training
                _LOGGER.info("Running AI learning: Extracting training data from collected bot data...")
                stats = process_data_for_ai(self.installation_dir)
                
                # Track what was processed
                self.cleanup_stats['ai_learning_processed'] = (
                    stats.get('browser_activity_records', 0) +
                    stats.get('bot_logs_processed', 0) +
                    stats.get('coordinate_data_extracted', 0) +
                    stats.get('screenshot_data_extracted', 0)
                )
                
                _LOGGER.info(f"AI learning complete: Processed {self.cleanup_stats['ai_learning_processed']} records for training")
            else:
                _LOGGER.debug("AI learning module not found, skipping learning step")
                
        except Exception as e:
            _LOGGER.warning(f"Error during AI learning step: {e}")
    
    def _run_openai_fine_tuning(self) -> None:
        """Run OpenAI fine-tuning if configured and enough data is available."""
        try:
            # Import OpenAI fine-tuning manager
            import sys
            ai_dir = self.installation_dir / "AI"
            training_path = ai_dir / "training" / "openai_fine_tuning.py"
            
            if not training_path.exists():
                _LOGGER.debug("OpenAI fine-tuning module not found, skipping")
                return
            
            # Add AI directory to path
            if str(ai_dir) not in sys.path:
                sys.path.insert(0, str(ai_dir))
            
            from training.openai_fine_tuning import get_fine_tuning_manager
            
            # Get fine-tuning manager
            manager = get_fine_tuning_manager(self.installation_dir)
            
            if not manager.is_configured():
                _LOGGER.debug("OpenAI fine-tuning not configured (no API key)")
                return
            
            # Check if we have enough training data
            training_data = manager.prepare_training_data()
            if not training_data:
                _LOGGER.debug("Insufficient training data for OpenAI fine-tuning")
                return
            
            # Run fine-tuning pipeline (only if we have enough data and haven't run recently)
            # Check last fine-tuning time to avoid running too frequently
            metadata_file = manager.models_dir / "fine_tuning_metadata.json"
            last_run = None
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        jobs = metadata.get("jobs", [])
                        if jobs:
                            # Get most recent job
                            last_job = max(jobs, key=lambda j: j.get("created_at", ""))
                            last_run = datetime.fromisoformat(last_job.get("created_at", ""))
                except Exception:
                    pass
            
            # Only run fine-tuning if last run was more than 7 days ago
            if last_run:
                days_since_last = (datetime.now() - last_run).days
                if days_since_last < 7:
                    _LOGGER.debug(f"Fine-tuning ran {days_since_last} days ago, skipping (runs weekly)")
                    return
            
            _LOGGER.info("Running OpenAI fine-tuning pipeline...")
            job_id = manager.run_fine_tuning_pipeline(
                model="gpt-3.5-turbo",
                suffix="integrity-bots"
            )
            
            if job_id:
                _LOGGER.info(f"OpenAI fine-tuning job created: {job_id}")
            else:
                _LOGGER.warning("OpenAI fine-tuning job creation failed")
                
        except Exception as e:
            _LOGGER.warning(f"Error during OpenAI fine-tuning step: {e}")
    
    def _run_local_training(self) -> None:
        """Run local AI training using Ollama (free, no API charges)."""
        try:
            import sys
            ai_dir = self.installation_dir / "AI"
            training_path = ai_dir / "training" / "local_ai_trainer.py"
            
            if not training_path.exists():
                _LOGGER.debug("Local training module not found, skipping")
                return
            
            # Add AI directory to path
            if str(ai_dir) not in sys.path:
                sys.path.insert(0, str(ai_dir))
            
            # Try to ensure Ollama is running
            try:
                ensure_ollama_path = self.installation_dir / "ENSURE_OLLAMA_RUNNING.py"
                if ensure_ollama_path.exists():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("ensure_ollama", ensure_ollama_path)
                    ensure_ollama = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(ensure_ollama)
                    ensure_ollama.ensure_ollama_running()
            except Exception as e:
                _LOGGER.debug(f"Could not auto-start Ollama: {e}")
            
            from training.local_ai_trainer import LocalAITrainer
            
            # Get local trainer
            trainer = LocalAITrainer(self.installation_dir, model_type="ollama")
            
            if not trainer.model:
                _LOGGER.debug("Ollama not running - local training skipped (will try again next time)")
                return
            
            # Check if we have enough data
            try:
                # Check training data availability
                training_data_dir = ai_dir / "training_data"
                training_files = list(training_data_dir.glob("*.json")) if training_data_dir.exists() else []
                
                if len(training_files) < 2:
                    _LOGGER.debug("Insufficient training data for local training")
                    return
                
                # Run training (this creates prompt templates, doesn't actually fine-tune)
                _LOGGER.info("Running local AI training with Ollama...")
                trainer.train_on_collected_data()
                _LOGGER.info("Local training completed successfully")
                
            except Exception as e:
                _LOGGER.warning(f"Error during local training: {e}")
                
        except Exception as e:
            _LOGGER.warning(f"Error during local training step: {e}")
    
    def _collect_employee_data(self, central_data_path: Path) -> None:
        """Collect data from employee computers and move to central training data."""
        try:
            from .central_data_collector import CentralDataCollector
            collector = CentralDataCollector(self.installation_dir, central_data_path)
            stats = collector.collect_employee_data()
            
            if stats["files_collected"] > 0:
                _LOGGER.info(f"Collected {stats['files_collected']} files from {stats['computers_processed']} employee computers")
                self.cleanup_stats['files_transferred'] = stats.get('files_collected', 0)
                self.cleanup_stats['bytes_transferred'] = stats.get('bytes_collected', 0)
        except ImportError:
            _LOGGER.debug("Central data collector module not available")
        except Exception as e:
            _LOGGER.warning(f"Error collecting employee data: {e}")
    
    def _cleanup_browser_databases(self, retention_days: Optional[int] = None) -> None:
        """Remove old records from browser activity databases across all bots."""
        try:
            # Use provided retention or default
            retention = retention_days if retention_days is not None else self.DATABASE_RETENTION_DAYS
            
            # Find all _secure_data directories
            secure_dirs = list(self.installation_dir.rglob("_secure_data"))
            
            for secure_dir in secure_dirs:
                db_path = secure_dir / "browser_activity.db"
                if not db_path.exists():
                    continue
                
                cutoff_date = datetime.now() - timedelta(days=retention)
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
        """Remove old backup files across all bots.
        
        CRITICAL SAFETY: Only removes files matching backup patterns (*.backup-*).
        NEVER touches actual bot files (.py, .bat, or regular .json files).
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.BACKUP_RETENTION_DAYS)
            
            # Find all backup files (ONLY files with .backup- in the name)
            backup_patterns = ["*.backup-*.json", "*.backup-*.db", "*.backup-*.log"]
            
            for pattern in backup_patterns:
                for backup_file in self.installation_dir.rglob(pattern):
                    # CRITICAL: Only process files that actually have ".backup-" in the name
                    if '.backup-' not in backup_file.name:
                        continue
                    
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
        """Remove old test files across all bots.
        
        CRITICAL SAFETY: NEVER touches any actual bot files.
        Only removes test files (test_*.py, temp_*.py, *_test.py) that are:
        - Older than retention period
        - NOT in _bots directories (bot files are protected)
        - NOT in protected directories
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.TEST_FILE_RETENTION_DAYS)
            
            # Find test files
            test_patterns = ["test_*.py", "temp_*.py", "*_test.py"]
            
            for pattern in test_patterns:
                for test_file in self.installation_dir.rglob(pattern):
                    # CRITICAL: NEVER touch files in _bots directories (bot files are protected)
                    if '_bots' in str(test_file):
                        continue
                    
                    # Skip if in quarantine or important directories
                    if any(skip in str(test_file) for skip in ['quarantine', '__pycache__', '.git', 'Cursor versions']):
                        continue
                    
                    # ADDITIONAL SAFETY: Never delete files with "bot" in the name
                    if 'bot' in test_file.name.lower() and '_bot.py' in test_file.name.lower():
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
        """Remove old log files across all bots (keep recent ones).
        
        CRITICAL SAFETY: Only removes .log files, NEVER touches .py or .bat files.
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=self.LOG_RETENTION_DAYS)
            
            # Find log files
            log_patterns = ["*.log", "*.log.*"]
            
            for pattern in log_patterns:
                for log_file in self.installation_dir.rglob(pattern):
                    # CRITICAL: Only process actual .log files, never .py or .bat
                    if log_file.suffix not in ['.log']:
                        continue
                    
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
    
    def _cleanup_training_data(self) -> None:
        """Clean up, compress, and archive training data files.
        
        Strategy:
        1. Keep only the last N datasets uncompressed (for active use)
        2. Compress older datasets that are still recent
        3. Archive datasets older than archive threshold
        4. Delete very old archived datasets if needed
        """
        try:
            ai_dir = self.installation_dir / "AI"
            training_data_dir = ai_dir / "training_data"
            archive_dir = ai_dir / "training_data" / "_archived"
            
            if not training_data_dir.exists():
                return
            
            # Create archive directory if it doesn't exist
            archive_dir.mkdir(exist_ok=True, mode=0o700)
            
            # Find all training dataset files
            training_files = []
            for pattern in ["training_dataset_*.json", "bot_logs_*.json", "browser_activity_*.json", 
                          "coordinates_*.json", "screenshots_*.json"]:
                for file in training_data_dir.glob(pattern):
                    if file.name.startswith("_"):  # Skip archive directory
                        continue
                    if file.suffix == ".gz":  # Skip already compressed files
                        continue
                    training_files.append(file)
            
            if not training_files:
                return
            
            # Sort by modification time (newest first)
            training_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # Keep last N datasets uncompressed
            keep_uncompressed = training_files[:self.TRAINING_DATA_KEEP_DATASETS]
            to_process = training_files[self.TRAINING_DATA_KEEP_DATASETS:]
            
            cutoff_date = datetime.now() - timedelta(days=self.TRAINING_DATA_ARCHIVE_DAYS)
            
            for file in to_process:
                try:
                    file_mtime = datetime.fromtimestamp(file.stat().st_mtime)
                    file_size_mb = file.stat().st_size / (1024 * 1024)
                    
                    # Check if already compressed
                    compressed_file = file.with_suffix(file.suffix + ".gz")
                    
                    if file_mtime < cutoff_date:
                        # Archive old files
                        archive_path = archive_dir / file.name
                        if not archive_path.exists():
                            shutil.move(str(file), str(archive_path))
                            self.cleanup_stats['training_files_archived'] += 1
                            self.cleanup_stats['total_space_freed_mb'] += file_size_mb * 0.1  # Estimate archive space savings
                            _LOGGER.info(f"Archived training file: {file.name}")
                    elif not compressed_file.exists():
                        # Compress files that are older than keep threshold but not old enough to archive
                        with open(file, 'rb') as f_in:
                            with gzip.open(compressed_file, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        # Calculate compression ratio
                        original_size = file.stat().st_size
                        compressed_size = compressed_file.stat().st_size
                        space_saved = (original_size - compressed_size) / (1024 * 1024)
                        
                        # Delete original file
                        file.unlink()
                        
                        self.cleanup_stats['training_files_compressed'] += 1
                        self.cleanup_stats['total_space_freed_mb'] += space_saved
                        _LOGGER.info(f"Compressed training file: {file.name} (saved {space_saved:.2f} MB)")
                    
                except Exception as e:
                    _LOGGER.warning(f"Error processing training file {file}: {e}")
            
            # Clean up old compressed files in archive (keep last 10)
            archived_files = sorted(archive_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if len(archived_files) > 10:
                for old_file in archived_files[10:]:
                    try:
                        file_size = old_file.stat().st_size / (1024 * 1024)
                        old_file.unlink()
                        self.cleanup_stats['training_files_deleted'] += 1
                        self.cleanup_stats['total_space_freed_mb'] += file_size
                        _LOGGER.info(f"Deleted old archived training file: {old_file.name}")
                    except Exception as e:
                        _LOGGER.warning(f"Error deleting archived file {old_file}: {e}")
                        
        except Exception as e:
            _LOGGER.warning(f"Error during training data cleanup: {e}")


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
        else:
            # Fallback: assume we're in installation root
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
    
    This runs the complete cycle: Data Collection → AI Learning → Data Recycling
    
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
            # Log results if significant activity occurred
            if stats.get('ai_learning_processed', 0) > 0 or stats['total_space_freed_mb'] > 0.1:
                log_msg = (f"🔄 Data cycle: AI learned from {stats.get('ai_learning_processed', 0)} records, "
                          f"freed {stats['total_space_freed_mb']:.2f} MB "
                          f"({stats['database_records_deleted']} DB records, "
                          f"{stats['backup_files_deleted']} backups, "
                          f"{stats['test_files_deleted']} test files, "
                          f"{stats['log_files_deleted']} logs, "
                          f"{stats.get('training_files_compressed', 0)} training files compressed, "
                          f"{stats.get('training_files_archived', 0)} archived)")
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

