#!/usr/bin/env python3
"""
Data Centralization System - OneDrive-Based Data Aggregation
Centralizes data from all employee computers for AI training.
Works with OneDrive cloud sync to aggregate data from all locations.
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import shutil

# User registration
try:
    from user_registration import UserRegistration
    USER_REGISTRATION_AVAILABLE = True
except ImportError:
    USER_REGISTRATION_AVAILABLE = False
    UserRegistration = None


class DataCentralization:
    """
    Centralizes data from all employee computers.
    Works with OneDrive cloud sync to aggregate data from all locations.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize data centralization system"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        
        # Central data directory (in OneDrive - syncs across all computers)
        self.central_data_dir = self.installation_dir / "_centralized_data"
        self.central_data_dir.mkdir(exist_ok=True)
        
        # Aggregated database (in OneDrive - centralized)
        self.central_db = self.central_data_dir / "centralized_data.db"
        self._init_central_database()
        
        # Local data directories (per computer - will sync to OneDrive)
        self.local_data_dirs = [
            self.installation_dir / "_secure_data",
            self.installation_dir / "_ai_intelligence",
            self.installation_dir / "_admin_data"
        ]
        
        # Setup logging
        self.log_file = self.central_data_dir / "centralization.log"
        self._setup_logging()
    
    def _init_central_database(self):
        """Initialize centralized database"""
        conn = sqlite3.connect(self.central_db)
        cursor = conn.cursor()
        
        # Aggregated bot executions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aggregated_bot_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_hash TEXT NOT NULL,
                computer_id TEXT NOT NULL,
                bot_name TEXT NOT NULL,
                execution_time REAL,
                success INTEGER,
                execution_timestamp TEXT,
                aggregated_at TEXT
            )
        """)
        
        # Aggregated AI prompts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aggregated_ai_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_hash TEXT NOT NULL,
                computer_id TEXT NOT NULL,
                prompt_text TEXT,
                bot_selected TEXT,
                confidence_score REAL,
                prompt_timestamp TEXT,
                aggregated_at TEXT
            )
        """)
        
        # Aggregated workflow patterns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aggregated_workflow_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_hash TEXT NOT NULL,
                computer_id TEXT NOT NULL,
                bot_name TEXT NOT NULL,
                parameter_pattern TEXT,
                file_pattern TEXT,
                frequency INTEGER,
                pattern_timestamp TEXT,
                aggregated_at TEXT
            )
        """)
        
        # Aggregation metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aggregation_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aggregation_type TEXT NOT NULL,
                source_computers INTEGER,
                records_aggregated INTEGER,
                aggregation_timestamp TEXT,
                duration_seconds REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _setup_logging(self):
        """Setup logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def aggregate_all_data(self) -> Dict:
        """
        Aggregate data from all local databases.
        OneDrive sync ensures data from all computers is available.
        """
        self.logger.info("Starting data aggregation from all computers...")
        
        start_time = datetime.now()
        total_records = 0
        
        # Aggregate bot executions
        bot_executions = self._aggregate_bot_executions()
        total_records += bot_executions.get("aggregated", 0)
        
        # Aggregate AI prompts
        ai_prompts = self._aggregate_ai_prompts()
        total_records += ai_prompts.get("aggregated", 0)
        
        # Aggregate workflow patterns
        workflow_patterns = self._aggregate_workflow_patterns()
        total_records += workflow_patterns.get("aggregated", 0)
        
        # Record aggregation metadata
        duration = (datetime.now() - start_time).total_seconds()
        self._record_aggregation_metadata(
            "full_aggregation",
            total_records,
            duration
        )
        
        self.logger.info(f"Aggregation complete: {total_records} records aggregated")
        
        return {
            "bot_executions": bot_executions,
            "ai_prompts": ai_prompts,
            "workflow_patterns": workflow_patterns,
            "total_records": total_records,
            "aggregated_at": datetime.now().isoformat()
        }
    
    def _aggregate_bot_executions(self) -> Dict:
        """Aggregate bot execution data from all computers"""
        from secure_data_collector import SecureDataCollector
        
        collector = SecureDataCollector(self.installation_dir)
        history = collector.get_workflow_history(days=365)  # Get all data
        
        # Get user registration info
        user_reg = UserRegistration(self.installation_dir) if USER_REGISTRATION_AVAILABLE else None
        local_user = user_reg.get_local_user() if user_reg else None
        computer_id = local_user.get("computer_id") if local_user else "unknown"
        
        # Aggregate to central database
        conn = sqlite3.connect(self.central_db)
        cursor = conn.cursor()
        
        aggregated = 0
        for record in history:
            user_hash = record.get("user_hash") or record.get("user_name", "unknown")
            if user_hash == "unknown" and local_user:
                user_hash = local_user.get("user_hash", "unknown")
            
            # Check if already aggregated
            cursor.execute("""
                SELECT id FROM aggregated_bot_executions
                WHERE user_hash = ? AND bot_name = ? AND execution_timestamp = ?
            """, (
                user_hash,
                record.get("bot_name", ""),
                record.get("timestamp", "")
            ))
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO aggregated_bot_executions
                    (user_hash, computer_id, bot_name, execution_time, success, execution_timestamp, aggregated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_hash,
                    computer_id,
                    record.get("bot_name", ""),
                    record.get("execution_time", 0),
                    1 if record.get("success") else 0,
                    record.get("timestamp", datetime.now().isoformat()),
                    datetime.now().isoformat()
                ))
                aggregated += 1
        
        conn.commit()
        conn.close()
        
        return {"aggregated": aggregated, "total": len(history)}
    
    def _aggregate_ai_prompts(self) -> Dict:
        """Aggregate AI prompt data from all computers"""
        # Get AI prompts from local database
        local_db = self.installation_dir / "_secure_data" / "secure_collection.db"
        if not local_db.exists():
            return {"aggregated": 0, "total": 0}
        
        conn_local = sqlite3.connect(local_db)
        cursor_local = conn_local.cursor()
        
        try:
            cursor_local.execute("""
                SELECT timestamp, user_hash, prompt_text, response_data, bot_selected, confidence_score
                FROM ai_prompts
                ORDER BY timestamp DESC
            """)
            
            prompts = cursor_local.fetchall()
        except:
            prompts = []
        finally:
            conn_local.close()
        
        # Get user registration info
        user_reg = UserRegistration(self.installation_dir) if USER_REGISTRATION_AVAILABLE else None
        local_user = user_reg.get_local_user() if user_reg else None
        computer_id = local_user.get("computer_id") if local_user else "unknown"
        
        # Aggregate to central database
        conn_central = sqlite3.connect(self.central_db)
        cursor_central = conn_central.cursor()
        
        aggregated = 0
        for prompt in prompts:
            timestamp, user_hash, prompt_text, response_data, bot_selected, confidence = prompt
            
            # Parse response data
            try:
                response_dict = json.loads(response_data) if response_data else {}
            except:
                response_dict = {}
            
            # Check if already aggregated
            cursor_central.execute("""
                SELECT id FROM aggregated_ai_prompts
                WHERE user_hash = ? AND prompt_timestamp = ?
            """, (user_hash or "unknown", timestamp))
            
            if not cursor_central.fetchone():
                cursor_central.execute("""
                    INSERT INTO aggregated_ai_prompts
                    (user_hash, computer_id, prompt_text, bot_selected, confidence_score, prompt_timestamp, aggregated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_hash or "unknown",
                    computer_id,
                    prompt_text,
                    bot_selected,
                    confidence,
                    timestamp,
                    datetime.now().isoformat()
                ))
                aggregated += 1
        
        conn_central.commit()
        conn_central.close()
        
        return {"aggregated": aggregated, "total": len(prompts)}
    
    def _aggregate_workflow_patterns(self) -> Dict:
        """Aggregate workflow pattern data from all computers"""
        # Get workflow patterns from local database
        local_db = self.installation_dir / "_ai_intelligence" / "workflow_database.db"
        if not local_db.exists():
            return {"aggregated": 0, "total": 0}
        
        conn_local = sqlite3.connect(local_db)
        cursor_local = conn_local.cursor()
        
        try:
            cursor_local.execute("""
                SELECT user_name, bot_name, parameters, files_used, timestamp
                FROM workflow_executions
                ORDER BY timestamp DESC
            """)
            
            patterns = cursor_local.fetchall()
        except:
            patterns = []
        finally:
            conn_local.close()
        
        # Get user registration info
        user_reg = UserRegistration(self.installation_dir) if USER_REGISTRATION_AVAILABLE else None
        local_user = user_reg.get_local_user() if user_reg else None
        computer_id = local_user.get("computer_id") if local_user else "unknown"
        
        # Aggregate to central database
        conn_central = sqlite3.connect(self.central_db)
        cursor_central = conn_central.cursor()
        
        aggregated = 0
        for pattern in patterns:
            user_name, bot_name, parameters, files_used, timestamp = pattern
            
            # Hash user name
            import hashlib
            user_hash = hashlib.sha256(user_name.encode()).hexdigest() if user_name else "unknown"
            
            # Check if already aggregated
            cursor_central.execute("""
                SELECT id FROM aggregated_workflow_patterns
                WHERE user_hash = ? AND bot_name = ? AND pattern_timestamp = ?
            """, (user_hash, bot_name, timestamp))
            
            if not cursor_central.fetchone():
                cursor_central.execute("""
                    INSERT INTO aggregated_workflow_patterns
                    (user_hash, computer_id, bot_name, parameter_pattern, file_pattern, frequency, pattern_timestamp, aggregated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_hash,
                    computer_id,
                    bot_name,
                    parameters,
                    files_used,
                    1,
                    timestamp,
                    datetime.now().isoformat()
                ))
                aggregated += 1
        
        conn_central.commit()
        conn_central.close()
        
        return {"aggregated": aggregated, "total": len(patterns)}
    
    def _record_aggregation_metadata(self, aggregation_type: str, records_aggregated: int, duration: float):
        """Record aggregation metadata"""
        conn = sqlite3.connect(self.central_db)
        cursor = conn.cursor()
        
        # Get count of unique computers
        cursor.execute("SELECT COUNT(DISTINCT computer_id) FROM aggregated_bot_executions")
        source_computers = cursor.fetchone()[0] or 1
        
        cursor.execute("""
            INSERT INTO aggregation_metadata
            (aggregation_type, source_computers, records_aggregated, aggregation_timestamp, duration_seconds)
            VALUES (?, ?, ?, ?, ?)
        """, (
            aggregation_type,
            source_computers,
            records_aggregated,
            datetime.now().isoformat(),
            duration
        ))
        
        conn.commit()
        conn.close()
    
    def get_aggregated_data_for_training(self) -> Dict:
        """Get aggregated data for AI training"""
        conn = sqlite3.connect(self.central_db)
        cursor = conn.cursor()
        
        # Get aggregated bot executions
        cursor.execute("""
            SELECT COUNT(*) FROM aggregated_bot_executions
        """)
        bot_executions_count = cursor.fetchone()[0]
        
        # Get aggregated AI prompts
        cursor.execute("""
            SELECT COUNT(*) FROM aggregated_ai_prompts
        """)
        ai_prompts_count = cursor.fetchone()[0]
        
        # Get aggregated workflow patterns
        cursor.execute("""
            SELECT COUNT(*) FROM aggregated_workflow_patterns
        """)
        workflow_patterns_count = cursor.fetchone()[0]
        
        # Get unique users
        cursor.execute("""
            SELECT COUNT(DISTINCT user_hash) FROM aggregated_bot_executions
        """)
        unique_users = cursor.fetchone()[0]
        
        # Get unique computers
        cursor.execute("""
            SELECT COUNT(DISTINCT computer_id) FROM aggregated_bot_executions
        """)
        unique_computers = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "bot_executions": bot_executions_count,
            "ai_prompts": ai_prompts_count,
            "workflow_patterns": workflow_patterns_count,
            "unique_users": unique_users,
            "unique_computers": unique_computers,
            "total_records": bot_executions_count + ai_prompts_count + workflow_patterns_count
        }
    
    def start_automated_aggregation(self, interval_hours: int = 24):
        """Start automated data aggregation"""
        import threading
        
        def aggregation_loop():
            while True:
                try:
                    self.aggregate_all_data()
                    import time
                    time.sleep(interval_hours * 3600)
                except Exception as e:
                    self.logger.error(f"Error in automated aggregation: {e}")
                    import time
                    time.sleep(3600)  # Retry in 1 hour
        
        thread = threading.Thread(target=aggregation_loop, daemon=True)
        thread.start()
        self.logger.info(f"Automated aggregation started (interval: {interval_hours} hours)")

