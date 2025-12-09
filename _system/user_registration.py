#!/usr/bin/env python3
"""
User Registration System - Employee Registration During Installation
Tracks which computer and employee is using the software.
Registers users in the central directory for data centralization.
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import platform
import uuid


class UserRegistration:
    """User registration system for employee tracking"""
    
    def __init__(self, installation_dir: Optional[Path] = None):
        """Initialize user registration system"""
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        self.system_dir = self.installation_dir / "_system"
        self.system_dir.mkdir(exist_ok=True)
        
        # Central user directory (in OneDrive - will sync across all computers)
        self.user_dir = self.installation_dir / "_user_directory"
        self.user_dir.mkdir(exist_ok=True)
        
        # User database (in OneDrive - centralized)
        self.user_db = self.user_dir / "user_directory.db"
        self._init_user_database()
        
        # Local user config (per computer)
        self.local_user_file = self.system_dir / "local_user.json"
    
    def _init_user_database(self):
        """Initialize user directory database"""
        conn = sqlite3.connect(self.user_db)
        cursor = conn.cursor()
        
        # Registered users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS registered_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                user_hash TEXT NOT NULL UNIQUE,
                computer_id TEXT NOT NULL,
                computer_name TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                last_active TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Computer registration table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS computer_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                computer_id TEXT NOT NULL UNIQUE,
                computer_name TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                last_sync TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        conn.commit()
        conn.close()
    
    def register_user(self, user_name: str, computer_id: Optional[str] = None) -> Dict:
        """
        Register a new user during installation.
        
        Args:
            user_name: Employee's name
            computer_id: Unique computer identifier (auto-generated if not provided)
        
        Returns:
            Registration information
        """
        # Generate computer ID if not provided
        if not computer_id:
            computer_id = self._get_computer_id()
        
        # Get computer name
        computer_name = platform.node()
        
        # Hash user name for privacy (HIPAA-compliant)
        user_hash = self._hash_user_name(user_name)
        
        # Check if user already registered
        existing_user = self._get_user_by_name(user_name)
        if existing_user:
            # Update existing user
            self._update_user_registration(existing_user["user_hash"], computer_id, computer_name)
            registration = {
                "user_name": user_name,
                "user_hash": existing_user["user_hash"],
                "computer_id": computer_id,
                "computer_name": computer_name,
                "registered_at": existing_user["registered_at"],
                "updated_at": datetime.now().isoformat(),
                "status": "updated"
            }
        else:
            # Register new user
            registration = {
                "user_name": user_name,
                "user_hash": user_hash,
                "computer_id": computer_id,
                "computer_name": computer_name,
                "registered_at": datetime.now().isoformat(),
                "status": "registered"
            }
            self._store_user_registration(registration)
        
        # Register computer
        self._register_computer(computer_id, computer_name)
        
        # Save local user config
        self._save_local_user_config(registration)
        
        return registration
    
    def _get_computer_id(self) -> str:
        """Get unique computer identifier"""
        # Try to get existing computer ID
        if self.local_user_file.exists():
            try:
                with open(self.local_user_file, 'r') as f:
                    config = json.load(f)
                    if config.get("computer_id"):
                        return config["computer_id"]
            except:
                pass
        
        # Generate new computer ID (based on MAC address + hostname)
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0,2*6,2)][::-1])
            hostname = platform.node()
            computer_id = hashlib.sha256(f"{mac}:{hostname}".encode()).hexdigest()[:16]
        except:
            # Fallback: Use hostname + username
            computer_id = hashlib.sha256(f"{platform.node()}:{os.getenv('USERNAME', 'unknown')}".encode()).hexdigest()[:16]
        
        return computer_id
    
    def _hash_user_name(self, user_name: str) -> str:
        """Hash user name for privacy (HIPAA-compliant)"""
        return hashlib.sha256(user_name.encode()).hexdigest()
    
    def _store_user_registration(self, registration: Dict):
        """Store user registration in central database"""
        conn = sqlite3.connect(self.user_db)
        cursor = conn.cursor()
        
        # Check if user already exists
        cursor.execute("""
            SELECT id FROM registered_users WHERE user_hash = ?
        """, (registration["user_hash"],))
        
        if cursor.fetchone():
            # Update existing user
            cursor.execute("""
                UPDATE registered_users
                SET computer_id = ?, computer_name = ?, last_active = ?
                WHERE user_hash = ?
            """, (
                registration["computer_id"],
                registration["computer_name"],
                datetime.now().isoformat(),
                registration["user_hash"]
            ))
        else:
            # Insert new user
            cursor.execute("""
                INSERT INTO registered_users
                (user_name, user_hash, computer_id, computer_name, registered_at, last_active, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                registration["user_name"],
                registration["user_hash"],
                registration["computer_id"],
                registration["computer_name"],
                registration["registered_at"],
                datetime.now().isoformat(),
                1
            ))
        
        conn.commit()
        conn.close()
    
    def _update_user_registration(self, user_hash: str, computer_id: str, computer_name: str):
        """Update existing user registration"""
        conn = sqlite3.connect(self.user_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE registered_users
            SET computer_id = ?, computer_name = ?, last_active = ?
            WHERE user_hash = ?
        """, (computer_id, computer_name, datetime.now().isoformat(), user_hash))
        
        conn.commit()
        conn.close()
    
    def _register_computer(self, computer_id: str, computer_name: str):
        """Register computer in central directory"""
        conn = sqlite3.connect(self.user_db)
        cursor = conn.cursor()
        
        # Check if computer already registered
        cursor.execute("""
            SELECT id FROM computer_registrations WHERE computer_id = ?
        """, (computer_id,))
        
        if cursor.fetchone():
            # Update existing registration
            cursor.execute("""
                UPDATE computer_registrations
                SET computer_name = ?, last_sync = ?
                WHERE computer_id = ?
            """, (computer_name, datetime.now().isoformat(), computer_id))
        else:
            # Insert new registration
            cursor.execute("""
                INSERT INTO computer_registrations
                (computer_id, computer_name, registered_at, last_sync, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, (
                computer_id,
                computer_name,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                1
            ))
        
        conn.commit()
        conn.close()
    
    def _save_local_user_config(self, registration: Dict):
        """Save local user configuration (for quick access)"""
        config = {
            "user_name": registration["user_name"],
            "user_hash": registration["user_hash"],
            "computer_id": registration["computer_id"],
            "computer_name": registration["computer_name"],
            "registered_at": registration["registered_at"],
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.local_user_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def _get_user_by_name(self, user_name: str) -> Optional[Dict]:
        """Get user by name from database"""
        user_hash = self._hash_user_name(user_name)
        
        conn = sqlite3.connect(self.user_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_name, user_hash, computer_id, computer_name, registered_at
            FROM registered_users
            WHERE user_hash = ?
        """, (user_hash,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "user_name": result[0],
                "user_hash": result[1],
                "computer_id": result[2],
                "computer_name": result[3],
                "registered_at": result[4]
            }
        
        return None
    
    def get_local_user(self) -> Optional[Dict]:
        """Get local user configuration"""
        if self.local_user_file.exists():
            try:
                with open(self.local_user_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all registered users from central directory"""
        conn = sqlite3.connect(self.user_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_name, user_hash, computer_id, computer_name, registered_at, last_active
            FROM registered_users
            WHERE is_active = 1
            ORDER BY registered_at DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            users.append({
                "user_name": row[0],
                "user_hash": row[1],
                "computer_id": row[2],
                "computer_name": row[3],
                "registered_at": row[4],
                "last_active": row[5]
            })
        
        conn.close()
        return users
    
    def get_all_computers(self) -> List[Dict]:
        """Get all registered computers"""
        conn = sqlite3.connect(self.user_db)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT computer_id, computer_name, registered_at, last_sync
            FROM computer_registrations
            WHERE is_active = 1
            ORDER BY registered_at DESC
        """)
        
        computers = []
        for row in cursor.fetchall():
            computers.append({
                "computer_id": row[0],
                "computer_name": row[1],
                "registered_at": row[2],
                "last_sync": row[3]
            })
        
        conn.close()
        return computers

