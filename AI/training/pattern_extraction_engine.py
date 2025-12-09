#!/usr/bin/env python3
"""
Pattern Extraction Engine - DeepSeek-Inspired Efficiency
Extracts workflow patterns from browser activity for efficient storage and training.
Pattern-based storage (10x smaller) for AI training.
"""

import json
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import Counter, defaultdict
import logging
import re
import gzip
import base64


class PatternExtractionEngine:
    """
    Pattern extraction engine for efficient storage and training.
    Inspired by DeepSeek's efficient approach - stores patterns, not raw data.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize pattern extraction engine"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        ai_dir = installation_dir / "AI"
        self.data_dir = ai_dir / "data"
        self.intelligence_dir = ai_dir / "intelligence"
        self.intelligence_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Pattern database
        self.pattern_db = self.intelligence_dir / "workflow_patterns.db"
        self._init_pattern_database()
        
        # Setup logging
        self.log_file = self.intelligence_dir / "pattern_extraction.log"
        self._setup_logging()
        
        # Pattern extraction settings
        self.min_pattern_frequency = 2  # Minimum occurrences to be a pattern
        self.compression_enabled = True
        self.pattern_retention_days = 90  # Keep patterns for 90 days
    
    def _init_pattern_database(self):
        """Initialize pattern database"""
        conn = sqlite3.connect(self.pattern_db)
        cursor = conn.cursor()
        
        # Extracted patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS extracted_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_hash TEXT NOT NULL UNIQUE,
                pattern_type TEXT NOT NULL,
                pattern_category TEXT,
                pattern_data TEXT NOT NULL,
                compressed_data BLOB,
                frequency INTEGER DEFAULT 1,
                confidence_score REAL DEFAULT 0.0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # Pattern sequences table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_sequences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sequence_hash TEXT NOT NULL UNIQUE,
                sequence_type TEXT NOT NULL,
                sequence_data TEXT NOT NULL,
                compressed_sequence BLOB,
                frequency INTEGER DEFAULT 1,
                average_duration REAL,
                success_rate REAL DEFAULT 1.0,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        """)
        
        # Pattern relationships table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_hash_1 TEXT NOT NULL,
                pattern_hash_2 TEXT NOT NULL,
                relationship_type TEXT,
                strength REAL DEFAULT 0.0,
                frequency INTEGER DEFAULT 1,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_hash ON extracted_patterns(pattern_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_type ON extracted_patterns(pattern_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_frequency ON extracted_patterns(frequency)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sequence_hash ON pattern_sequences(sequence_hash)")
        
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
    
    def extract_page_sequence_pattern(self, page_sequence: List[str]) -> Optional[Dict]:
        """Extract page sequence pattern"""
        if not page_sequence or len(page_sequence) < 2:
            return None
        
        try:
            # Create pattern hash
            pattern_data = {
                "type": "page_sequence",
                "sequence": page_sequence,
                "length": len(page_sequence)
            }
            pattern_hash = self._hash_pattern(pattern_data)
            
            # Compress pattern
            compressed = self._compress_pattern(pattern_data) if self.compression_enabled else None
            
            # Store pattern
            conn = sqlite3.connect(self.pattern_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO extracted_patterns
                (pattern_hash, pattern_type, pattern_category, pattern_data, compressed_data, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern_hash,
                "page_sequence",
                "navigation",
                json.dumps(pattern_data),
                compressed,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            cursor.execute("""
                UPDATE extracted_patterns
                SET frequency = frequency + 1,
                    last_seen = ?,
                    confidence_score = confidence_score + 0.1
                WHERE pattern_hash = ?
            """, (datetime.now().isoformat(), pattern_hash))
            
            conn.commit()
            conn.close()
            
            return {
                "pattern_hash": pattern_hash,
                "pattern_type": "page_sequence",
                "pattern_data": pattern_data,
                "frequency": self._get_pattern_frequency(pattern_hash)
            }
        
        except Exception as e:
            self.logger.error(f"Error extracting page sequence pattern: {e}")
            return None
    
    def extract_action_sequence_pattern(self, action_sequence: List[Dict]) -> Optional[Dict]:
        """Extract action sequence pattern"""
        if not action_sequence or len(action_sequence) < 2:
            return None
        
        try:
            # Extract action types
            action_types = [action.get("action", "unknown") for action in action_sequence]
            
            # Create pattern
            pattern_data = {
                "type": "action_sequence",
                "sequence": action_types,
                "length": len(action_types),
                "actions": action_sequence[:10]  # Keep first 10 actions for context
            }
            pattern_hash = self._hash_pattern(pattern_data)
            
            # Compress pattern
            compressed = self._compress_pattern(pattern_data) if self.compression_enabled else None
            
            # Store pattern
            conn = sqlite3.connect(self.pattern_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO extracted_patterns
                (pattern_hash, pattern_type, pattern_category, pattern_data, compressed_data, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern_hash,
                "action_sequence",
                "interaction",
                json.dumps(pattern_data),
                compressed,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            cursor.execute("""
                UPDATE extracted_patterns
                SET frequency = frequency + 1,
                    last_seen = ?,
                    confidence_score = confidence_score + 0.1
                WHERE pattern_hash = ?
            """, (datetime.now().isoformat(), pattern_hash))
            
            conn.commit()
            conn.close()
            
            return {
                "pattern_hash": pattern_hash,
                "pattern_type": "action_sequence",
                "pattern_data": pattern_data,
                "frequency": self._get_pattern_frequency(pattern_hash)
            }
        
        except Exception as e:
            self.logger.error(f"Error extracting action sequence pattern: {e}")
            return None
    
    def extract_form_field_pattern(self, form_fields: List[Dict]) -> Optional[Dict]:
        """Extract form field interaction pattern"""
        if not form_fields:
            return None
        
        try:
            # Extract field names and types
            field_pattern = {
                field.get("name") or field.get("id"): field.get("type", "text")
                for field in form_fields
            }
            
            # Create pattern
            pattern_data = {
                "type": "form_field_pattern",
                "fields": field_pattern,
                "field_count": len(field_pattern)
            }
            pattern_hash = self._hash_pattern(pattern_data)
            
            # Compress pattern
            compressed = self._compress_pattern(pattern_data) if self.compression_enabled else None
            
            # Store pattern
            conn = sqlite3.connect(self.pattern_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO extracted_patterns
                (pattern_hash, pattern_type, pattern_category, pattern_data, compressed_data, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern_hash,
                "form_field_pattern",
                "form_interaction",
                json.dumps(pattern_data),
                compressed,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            cursor.execute("""
                UPDATE extracted_patterns
                SET frequency = frequency + 1,
                    last_seen = ?,
                    confidence_score = confidence_score + 0.1
                WHERE pattern_hash = ?
            """, (datetime.now().isoformat(), pattern_hash))
            
            conn.commit()
            conn.close()
            
            return {
                "pattern_hash": pattern_hash,
                "pattern_type": "form_field_pattern",
                "pattern_data": pattern_data,
                "frequency": self._get_pattern_frequency(pattern_hash)
            }
        
        except Exception as e:
            self.logger.error(f"Error extracting form field pattern: {e}")
            return None
    
    def extract_workflow_pattern(self, page_sequence: List[str], action_sequence: List[Dict]) -> Optional[Dict]:
        """Extract complete workflow pattern"""
        try:
            # Create workflow pattern
            workflow_data = {
                "type": "workflow",
                "pages": page_sequence,
                "actions": action_sequence[:20],  # Keep first 20 actions
                "page_count": len(page_sequence),
                "action_count": len(action_sequence)
            }
            workflow_hash = self._hash_pattern(workflow_data)
            
            # Compress workflow
            compressed = self._compress_pattern(workflow_data) if self.compression_enabled else None
            
            # Store workflow sequence
            conn = sqlite3.connect(self.pattern_db)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR IGNORE INTO pattern_sequences
                (sequence_hash, sequence_type, sequence_data, compressed_sequence, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                workflow_hash,
                "complete_workflow",
                json.dumps(workflow_data),
                compressed,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
            cursor.execute("""
                UPDATE pattern_sequences
                SET frequency = frequency + 1,
                    last_seen = ?
                WHERE sequence_hash = ?
            """, (datetime.now().isoformat(), workflow_hash))
            
            conn.commit()
            conn.close()
            
            return {
                "sequence_hash": workflow_hash,
                "sequence_type": "complete_workflow",
                "sequence_data": workflow_data,
                "frequency": self._get_sequence_frequency(workflow_hash)
            }
        
        except Exception as e:
            self.logger.error(f"Error extracting workflow pattern: {e}")
            return None
    
    def _hash_pattern(self, pattern_data: Dict) -> str:
        """Create hash for pattern"""
        pattern_json = json.dumps(pattern_data, sort_keys=True)
        return hashlib.sha256(pattern_json.encode()).hexdigest()
    
    def _compress_pattern(self, pattern_data: Dict) -> bytes:
        """Compress pattern data"""
        try:
            pattern_json = json.dumps(pattern_data)
            compressed = gzip.compress(pattern_json.encode())
            return compressed
        except Exception:
            return None
    
    def _get_pattern_frequency(self, pattern_hash: str) -> int:
        """Get pattern frequency"""
        try:
            conn = sqlite3.connect(self.pattern_db)
            cursor = conn.cursor()
            cursor.execute("SELECT frequency FROM extracted_patterns WHERE pattern_hash = ?", (pattern_hash,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 0
        except Exception:
            return 0
    
    def _get_sequence_frequency(self, sequence_hash: str) -> int:
        """Get sequence frequency"""
        try:
            conn = sqlite3.connect(self.pattern_db)
            cursor = conn.cursor()
            cursor.execute("SELECT frequency FROM pattern_sequences WHERE sequence_hash = ?", (sequence_hash,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else 0
        except Exception:
            return 0
    
    def get_top_patterns(self, pattern_type: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get top patterns by frequency"""
        try:
            conn = sqlite3.connect(self.pattern_db)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if pattern_type:
                cursor.execute("""
                    SELECT pattern_hash, pattern_type, pattern_data, frequency, confidence_score, first_seen, last_seen
                    FROM extracted_patterns
                    WHERE pattern_type = ?
                    ORDER BY frequency DESC, confidence_score DESC
                    LIMIT ?
                """, (pattern_type, limit))
            else:
                cursor.execute("""
                    SELECT pattern_hash, pattern_type, pattern_data, frequency, confidence_score, first_seen, last_seen
                    FROM extracted_patterns
                    ORDER BY frequency DESC, confidence_score DESC
                    LIMIT ?
                """, (limit,))
            
            patterns = []
            for row in cursor.fetchall():
                pattern_data = json.loads(row["pattern_data"])
                if self.compression_enabled and row.get("compressed_data"):
                    # Decompress if needed
                    try:
                        decompressed = gzip.decompress(row["compressed_data"]).decode()
                        pattern_data = json.loads(decompressed)
                    except:
                        pass
                
                patterns.append({
                    "pattern_hash": row["pattern_hash"],
                    "pattern_type": row["pattern_type"],
                    "pattern_data": pattern_data,
                    "frequency": row["frequency"],
                    "confidence_score": row["confidence_score"],
                    "first_seen": row["first_seen"],
                    "last_seen": row["last_seen"]
                })
            
            conn.close()
            return patterns
        except Exception as e:
            self.logger.error(f"Error getting top patterns: {e}")
            return []
    
    def get_pattern_statistics(self) -> Dict:
        """Get pattern extraction statistics"""
        try:
            conn = sqlite3.connect(self.pattern_db)
            cursor = conn.cursor()
            
            # Total patterns
            cursor.execute("SELECT COUNT(*) FROM extracted_patterns")
            total_patterns = cursor.fetchone()[0]
            
            # Total sequences
            cursor.execute("SELECT COUNT(*) FROM pattern_sequences")
            total_sequences = cursor.fetchone()[0]
            
            # Patterns by type
            cursor.execute("""
                SELECT pattern_type, COUNT(*) as count, SUM(frequency) as total_frequency
                FROM extracted_patterns
                GROUP BY pattern_type
            """)
            patterns_by_type = {row[0]: {"count": row[1], "frequency": row[2]} for row in cursor.fetchall()}
            
            # Storage efficiency
            cursor.execute("SELECT SUM(LENGTH(compressed_data)) FROM extracted_patterns WHERE compressed_data IS NOT NULL")
            compressed_size = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(LENGTH(pattern_data)) FROM extracted_patterns")
            uncompressed_size = cursor.fetchone()[0] or 0
            
            compression_ratio = (1 - compressed_size / uncompressed_size) * 100 if uncompressed_size > 0 else 0
            
            conn.close()
            
            return {
                "total_patterns": total_patterns,
                "total_sequences": total_sequences,
                "patterns_by_type": patterns_by_type,
                "compressed_size_bytes": compressed_size,
                "uncompressed_size_bytes": uncompressed_size,
                "compression_ratio_percent": compression_ratio,
                "storage_efficiency": f"{(1 - compressed_size / uncompressed_size) * 100:.1f}% smaller" if uncompressed_size > 0 else "N/A"
            }
        except Exception as e:
            self.logger.error(f"Error getting pattern statistics: {e}")
            return {}

