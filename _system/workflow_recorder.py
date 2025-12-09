#!/usr/bin/env python3
"""
Workflow Recorder - Enterprise-Grade Usage Pattern Tracking
Records all bot interactions, parameters, files, and user behaviors
for intelligent automation and learning.
"""

import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import shutil


class WorkflowRecorder:
    """
    Records and analyzes bot usage patterns for intelligent automation.
    Similar to UiPath's recording capabilities.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize the workflow recorder"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        self.db_path = self.installation_dir / "_system" / "workflow_history.db"
        self.workflows_dir = self.installation_dir / "_system" / "workflow_records"
        self.workflows_dir.mkdir(exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for workflow history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Workflow executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_name TEXT,
                bot_name TEXT NOT NULL,
                bot_path TEXT NOT NULL,
                command TEXT,
                parameters TEXT,
                files_used TEXT,
                success INTEGER,
                execution_time REAL,
                error_message TEXT,
                context TEXT
            )
        """)
        
        # User patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                bot_name TEXT NOT NULL,
                parameter_name TEXT,
                parameter_value TEXT,
                frequency INTEGER DEFAULT 1,
                last_used TEXT,
                file_pattern TEXT,
                context_pattern TEXT
            )
        """)
        
        # File patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bot_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT,
                file_type TEXT,
                usage_count INTEGER DEFAULT 1,
                last_used TEXT,
                associated_params TEXT,
                user_name TEXT
            )
        """)
        
        # Workflow templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT NOT NULL,
                bot_name TEXT NOT NULL,
                sequence TEXT,
                parameters TEXT,
                conditions TEXT,
                created_by TEXT,
                created_at TEXT,
                usage_count INTEGER DEFAULT 0
            )
        """)
        
        # Context patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_pattern TEXT NOT NULL,
                bot_name TEXT NOT NULL,
                parameters TEXT,
                date_pattern TEXT,
                file_pattern TEXT,
                frequency INTEGER DEFAULT 1,
                success_rate REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def record_execution(self, 
                        bot_name: str,
                        bot_path: str,
                        command: Optional[str] = None,
                        parameters: Optional[Dict] = None,
                        files: Optional[List[str]] = None,
                        success: bool = True,
                        execution_time: Optional[float] = None,
                        error: Optional[str] = None,
                        user_name: Optional[str] = None,
                        context: Optional[Dict] = None):
        """
        Record a bot execution with all relevant details.
        
        Args:
            bot_name: Name of the bot executed
            bot_path: Path to the bot file
            command: Natural language command that triggered this
            parameters: Dictionary of parameters used
            files: List of file paths used
            success: Whether execution was successful
            execution_time: Time taken to execute
            error: Error message if failed
            user_name: Name of user executing
            context: Additional context (dates, department, etc.)
        """
        timestamp = datetime.now().isoformat()
        
        # Get current user if not provided
        if not user_name:
            user_name = os.getenv("USERNAME") or os.getenv("USER") or "Unknown"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert execution record
        cursor.execute("""
            INSERT INTO workflow_executions 
            (timestamp, user_name, bot_name, bot_path, command, parameters, 
             files_used, success, execution_time, error_message, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            user_name,
            bot_name,
            str(bot_path),
            command,
            json.dumps(parameters) if parameters else None,
            json.dumps(files) if files else None,
            1 if success else 0,
            execution_time,
            error,
            json.dumps(context) if context else None
        ))
        
        execution_id = cursor.lastrowid
        
        # Update user patterns
        if parameters:
            self._update_user_patterns(cursor, user_name, bot_name, parameters, files)
        
        # Update file patterns
        if files:
            self._update_file_patterns(cursor, bot_name, files, parameters, user_name)
        
        # Update context patterns
        if command:
            self._update_context_patterns(cursor, command, bot_name, parameters, files, success)
        
        conn.commit()
        conn.close()
        
        # Save detailed workflow record
        self._save_workflow_record(execution_id, {
            "bot_name": bot_name,
            "bot_path": str(bot_path),
            "command": command,
            "parameters": parameters,
            "files": files,
            "success": success,
            "execution_time": execution_time,
            "error": error,
            "user_name": user_name,
            "context": context,
            "timestamp": timestamp
        })
        
        return execution_id
    
    def _update_user_patterns(self, cursor, user_name: str, bot_name: str, 
                              parameters: Dict, files: Optional[List[str]]):
        """Update user-specific parameter patterns"""
        for param_name, param_value in parameters.items():
            # Check if pattern exists
            cursor.execute("""
                SELECT id, frequency FROM user_patterns
                WHERE user_name = ? AND bot_name = ? AND parameter_name = ? 
                AND parameter_value = ?
            """, (user_name, bot_name, param_name, str(param_value)))
            
            result = cursor.fetchone()
            if result:
                # Update frequency
                pattern_id, frequency = result
                cursor.execute("""
                    UPDATE user_patterns 
                    SET frequency = ?, last_used = ?
                    WHERE id = ?
                """, (frequency + 1, datetime.now().isoformat(), pattern_id))
            else:
                # Insert new pattern
                file_pattern = json.dumps(files) if files else None
                cursor.execute("""
                    INSERT INTO user_patterns 
                    (user_name, bot_name, parameter_name, parameter_value, 
                     frequency, last_used, file_pattern)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_name,
                    bot_name,
                    param_name,
                    str(param_value),
                    1,
                    datetime.now().isoformat(),
                    file_pattern
                ))
    
    def _update_file_patterns(self, cursor, bot_name: str, files: List[str],
                              parameters: Optional[Dict], user_name: str):
        """Update file usage patterns"""
        for file_path in files:
            if not os.path.exists(file_path):
                continue
            
            # Calculate file hash for pattern matching
            try:
                file_hash = self._calculate_file_hash(file_path)
            except:
                file_hash = None
            
            file_type = Path(file_path).suffix.lower()
            
            # Check if file pattern exists
            cursor.execute("""
                SELECT id, usage_count FROM file_patterns
                WHERE bot_name = ? AND file_path = ?
            """, (bot_name, file_path))
            
            result = cursor.fetchone()
            if result:
                # Update usage count
                pattern_id, usage_count = result
                cursor.execute("""
                    UPDATE file_patterns 
                    SET usage_count = ?, last_used = ?, associated_params = ?
                    WHERE id = ?
                """, (
                    usage_count + 1,
                    datetime.now().isoformat(),
                    json.dumps(parameters) if parameters else None,
                    pattern_id
                ))
            else:
                # Insert new file pattern
                cursor.execute("""
                    INSERT INTO file_patterns 
                    (bot_name, file_path, file_hash, file_type, usage_count, 
                     last_used, associated_params, user_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    bot_name,
                    file_path,
                    file_hash,
                    file_type,
                    1,
                    datetime.now().isoformat(),
                    json.dumps(parameters) if parameters else None,
                    user_name
                ))
    
    def _update_context_patterns(self, cursor, command: str, bot_name: str,
                                 parameters: Optional[Dict], files: Optional[List[str]],
                                 success: bool):
        """Update command-to-bot mapping patterns"""
        # Check if pattern exists
        cursor.execute("""
            SELECT id, frequency, success_rate FROM context_patterns
            WHERE command_pattern = ? AND bot_name = ?
        """, (command.lower(), bot_name))
        
        result = cursor.fetchone()
        if result:
            # Update pattern
            pattern_id, frequency, success_rate = result
            new_success_rate = ((success_rate * frequency) + (1 if success else 0)) / (frequency + 1)
            cursor.execute("""
                UPDATE context_patterns 
                SET frequency = ?, success_rate = ?, parameters = ?, file_pattern = ?
                WHERE id = ?
            """, (
                frequency + 1,
                new_success_rate,
                json.dumps(parameters) if parameters else None,
                json.dumps(files) if files else None,
                pattern_id
            ))
        else:
            # Insert new pattern
            cursor.execute("""
                INSERT INTO context_patterns 
                (command_pattern, bot_name, parameters, file_pattern, 
                 frequency, success_rate)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                command.lower(),
                bot_name,
                json.dumps(parameters) if parameters else None,
                json.dumps(files) if files else None,
                1,
                1.0 if success else 0.0
            ))
    
    def _save_workflow_record(self, execution_id: int, record: Dict):
        """Save detailed workflow record to JSON file"""
        record_file = self.workflows_dir / f"workflow_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(record_file, 'w') as f:
            json.dump(record, f, indent=2)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file for pattern matching"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def get_user_patterns(self, user_name: str, bot_name: str) -> Dict:
        """Get most common parameter patterns for a user and bot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT parameter_name, parameter_value, frequency, last_used, file_pattern
            FROM user_patterns
            WHERE user_name = ? AND bot_name = ?
            ORDER BY frequency DESC
        """, (user_name, bot_name))
        
        patterns = {}
        for row in cursor.fetchall():
            param_name, param_value, frequency, last_used, file_pattern = row
            if param_name not in patterns:
                patterns[param_name] = []
            patterns[param_name].append({
                "value": param_value,
                "frequency": frequency,
                "last_used": last_used,
                "file_pattern": json.loads(file_pattern) if file_pattern else None
            })
        
        conn.close()
        return patterns
    
    def get_file_suggestions(self, bot_name: str, user_name: Optional[str] = None) -> List[Dict]:
        """Get most commonly used files for a bot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_name:
            cursor.execute("""
                SELECT file_path, usage_count, last_used, associated_params
                FROM file_patterns
                WHERE bot_name = ? AND user_name = ?
                ORDER BY usage_count DESC, last_used DESC
                LIMIT 10
            """, (bot_name, user_name))
        else:
            cursor.execute("""
                SELECT file_path, usage_count, last_used, associated_params
                FROM file_patterns
                WHERE bot_name = ?
                ORDER BY usage_count DESC, last_used DESC
                LIMIT 10
            """, (bot_name,))
        
        suggestions = []
        for row in cursor.fetchall():
            file_path, usage_count, last_used, params = row
            if os.path.exists(file_path):
                suggestions.append({
                    "file_path": file_path,
                    "usage_count": usage_count,
                    "last_used": last_used,
                    "parameters": json.loads(params) if params else None
                })
        
        conn.close()
        return suggestions
    
    def get_context_suggestions(self, command: str) -> List[Dict]:
        """Get bot and parameter suggestions based on command pattern"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Fuzzy match command patterns
        command_lower = command.lower()
        cursor.execute("""
            SELECT bot_name, parameters, file_pattern, frequency, success_rate
            FROM context_patterns
            WHERE command_pattern LIKE ? OR command_pattern LIKE ? OR command_pattern LIKE ?
            ORDER BY frequency DESC, success_rate DESC
            LIMIT 5
        """, (f"%{command_lower}%", f"{command_lower}%", f"%{command_lower}"))
        
        suggestions = []
        for row in cursor.fetchall():
            bot_name, params, file_pattern, frequency, success_rate = row
            suggestions.append({
                "bot_name": bot_name,
                "parameters": json.loads(params) if params else None,
                "file_pattern": json.loads(file_pattern) if file_pattern else None,
                "frequency": frequency,
                "success_rate": success_rate
            })
        
        conn.close()
        return suggestions
    
    def get_workflow_history(self, bot_name: Optional[str] = None, 
                           user_name: Optional[str] = None,
                           days: int = 30) -> List[Dict]:
        """Get workflow execution history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        if bot_name and user_name:
            cursor.execute("""
                SELECT * FROM workflow_executions
                WHERE bot_name = ? AND user_name = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 100
            """, (bot_name, user_name, cutoff_date))
        elif bot_name:
            cursor.execute("""
                SELECT * FROM workflow_executions
                WHERE bot_name = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 100
            """, (bot_name, cutoff_date))
        elif user_name:
            cursor.execute("""
                SELECT * FROM workflow_executions
                WHERE user_name = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 100
            """, (user_name, cutoff_date))
        else:
            cursor.execute("""
                SELECT * FROM workflow_executions
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 100
            """, (cutoff_date,))
        
        columns = [desc[0] for desc in cursor.description]
        history = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            if record.get('parameters'):
                record['parameters'] = json.loads(record['parameters'])
            if record.get('files_used'):
                record['files_used'] = json.loads(record['files_used'])
            if record.get('context'):
                record['context'] = json.loads(record['context'])
            history.append(record)
        
        conn.close()
        return history

