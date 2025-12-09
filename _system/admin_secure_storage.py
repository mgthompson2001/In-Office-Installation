#!/usr/bin/env python3
"""
Admin Secure Storage - Password-Protected Admin Data Folder
HIPAA-compliant encrypted storage for admin-only data.
Requires admin password to access.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Any, List
import hashlib
import hmac

# Encryption
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    import base64
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False


class AdminSecureStorage:
    """
    Password-protected admin storage for HIPAA-compliant data.
    Requires admin password to access any data.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None,
                 admin_password: Optional[str] = None):
        """
        Initialize admin secure storage.
        
        Args:
            installation_dir: Base installation directory
            admin_password: Admin password (will prompt if not provided)
        """
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        self.admin_data_dir = self.installation_dir / "_admin_data"
        self.admin_data_dir.mkdir(exist_ok=True, mode=0o700)  # Secure permissions
        
        # Password management
        self.password_file = self.admin_data_dir / ".admin_password"
        self.admin_password = admin_password
        self.authenticated = False
        
        # Encryption
        self.encryption_key = None
        self.cipher_suite = None
        
        # Setup logging
        self.log_file = self.admin_data_dir / "admin_storage.log"
        self._setup_logging()
        
        # Initialize if needed
        self._initialize_storage()
    
    def _setup_logging(self):
        """Setup logging for admin storage"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _audit_log(self, level: str, message: str):
        """Log audit events"""
        if level == "INFO":
            self.logger.info(message)
        elif level == "WARNING":
            self.logger.warning(message)
        elif level == "ERROR":
            self.logger.error(message)
        else:
            self.logger.debug(message)
    
    def _initialize_storage(self):
        """Initialize admin storage"""
        # Create admin password if not exists
        if not self.password_file.exists():
            self._create_admin_password()
        
        # Load encryption key
        self._load_encryption_key()
    
    def _create_admin_password(self):
        """Create admin password (first time setup)"""
        # Default admin password
        DEFAULT_PASSWORD = "Integritycode2001@"
        
        # Hash password
        password_hash = hashlib.sha256(DEFAULT_PASSWORD.encode()).hexdigest()
        
        # Store hashed password
        with open(self.password_file, 'w') as f:
            f.write(password_hash)
        
        try:
            os.chmod(self.password_file, 0o600)  # Secure permissions (Windows may not fully support)
        except:
            pass  # Windows may not support chmod fully
        
        # Set admin password
        self.admin_password = DEFAULT_PASSWORD
        
        self._audit_log("INFO", "Admin password created with default password")
    
    def authenticate(self, password: Optional[str] = None) -> bool:
        """Authenticate admin access"""
        # Default password
        DEFAULT_PASSWORD = "Integritycode2001@"
        
        if password:
            provided_password = password
        elif self.admin_password:
            provided_password = self.admin_password
        else:
            # Use default password if not provided
            provided_password = DEFAULT_PASSWORD
        
        # Verify password
        if self.password_file.exists():
            with open(self.password_file, 'r') as f:
                stored_hash = f.read().strip()
            
            provided_hash = hashlib.sha256(provided_password.encode()).hexdigest()
            
            if provided_hash == stored_hash:
                self.authenticated = True
                self.admin_password = provided_password
                self._load_encryption_key()
                return True
        
        # If password file doesn't exist, create it with default
        if not self.password_file.exists():
            self._create_admin_password()
            self.authenticated = True
            self._load_encryption_key()
            return True
        
        self.authenticated = False
        return False
    
    def _load_encryption_key(self):
        """Load encryption key (derived from admin password)"""
        if not self.admin_password:
            return
        
        if not ENCRYPTION_AVAILABLE:
            return
        
        # Derive encryption key from admin password
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'admin_secure_salt',
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.admin_password.encode()))
        self.encryption_key = key
        self.cipher_suite = Fernet(key)
    
    def store_admin_data(self, data_type: str, data: Dict, require_auth: bool = True) -> bool:
        """Store admin-only data"""
        if require_auth and not self.authenticated:
            if not self.authenticate():
                return False
        
        # Encrypt data
        encrypted_data = None
        if self.cipher_suite:
            encrypted_data = self.cipher_suite.encrypt(
                json.dumps(data).encode()
            )
        
        # Store in database
        db_path = self.admin_data_dir / "admin_data.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_type TEXT NOT NULL,
                encrypted_data BLOB,
                plain_data TEXT,
                stored_at TEXT,
                accessed_at TEXT
            )
        """)
        
        # Store data
        cursor.execute("""
            INSERT INTO admin_data
            (data_type, encrypted_data, plain_data, stored_at)
            VALUES (?, ?, ?, ?)
        """, (
            data_type,
            encrypted_data,
            json.dumps(data) if not encrypted_data else None,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        return True
    
    def get_admin_data(self, data_type: str, require_auth: bool = True) -> Optional[Dict]:
        """Get admin-only data"""
        if require_auth and not self.authenticated:
            if not self.authenticate():
                return None
        
        db_path = self.admin_data_dir / "admin_data.db"
        if not db_path.exists():
            return None
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT encrypted_data, plain_data, stored_at
            FROM admin_data
            WHERE data_type = ?
            ORDER BY stored_at DESC
            LIMIT 1
        """, (data_type,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        encrypted_data, plain_data, stored_at = result
        
        # Decrypt if encrypted
        if encrypted_data and self.cipher_suite:
            try:
                decrypted = self.cipher_suite.decrypt(encrypted_data)
                return json.loads(decrypted.decode())
            except Exception as e:
                return None
        
        # Return plain data if not encrypted
        if plain_data:
            return json.loads(plain_data)
        
        return None
    
    def list_admin_data_types(self, require_auth: bool = True) -> List[str]:
        """List all admin data types"""
        if require_auth and not self.authenticated:
            if not self.authenticate():
                return []
        
        db_path = self.admin_data_dir / "admin_data.db"
        if not db_path.exists():
            return []
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT data_type FROM admin_data
        """)
        
        data_types = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return data_types

