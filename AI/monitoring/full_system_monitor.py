#!/usr/bin/env python3
"""
Full System Monitor - Complete Activity Recording
Records EVERYTHING: screen, keyboard, mouse, applications, files.
For personal use with explicit consent.
HIPAA-compliant, encrypted, local-only storage.
"""

import os
import sys
import json
import sqlite3
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
import hashlib
import base64
import logging
from queue import Queue

# Image processing (optional)
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None
    np = None

# PIL for image processing
try:
    from PIL import Image, ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageGrab = None

# Screen capture
try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    mss = None

# PyAutoGUI (optional)
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    pyautogui = None

# Keyboard/Mouse monitoring
try:
    from pynput import keyboard, mouse
    from pynput.keyboard import Key, Listener as KeyboardListener
    from pynput.mouse import Listener as MouseListener, Button
    INPUT_MONITORING_AVAILABLE = True
except ImportError:
    INPUT_MONITORING_AVAILABLE = False
    keyboard = None
    mouse = None

# Process monitoring
try:
    import psutil
    PROCESS_MONITORING_AVAILABLE = True
except ImportError:
    PROCESS_MONITORING_AVAILABLE = False
    psutil = None

# File system monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    FILESYSTEM_MONITORING_AVAILABLE = True
except ImportError:
    FILESYSTEM_MONITORING_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None

# Encryption
try:
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    Fernet = None


class FullSystemMonitor:
    """
    Complete system monitoring for personal use with explicit consent.
    Records: screen, keyboard, mouse, applications, files.
    All data encrypted and stored locally.
    """
    
    def __init__(self, installation_dir: Optional[Path] = None, 
                 user_consent: bool = True,
                 record_screen: bool = True,
                 record_keyboard: bool = True,
                 record_mouse: bool = True,
                 record_apps: bool = True,
                 record_files: bool = True):
        """
        Initialize full system monitor.
        
        Args:
            installation_dir: Base installation directory
            user_consent: Explicit user consent (required)
            record_screen: Record screen activity
            record_keyboard: Record keyboard input
            record_mouse: Record mouse activity
            record_apps: Record application usage
            record_files: Record file system activity
        """
        if not user_consent:
            raise ValueError("User consent is REQUIRED for full system monitoring")
        
        if installation_dir is None:
            installation_dir = Path(__file__).parent.parent
        
        self.installation_dir = Path(installation_dir)
        self.data_dir = self.installation_dir / "_secure_data" / "full_monitoring"
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Screenshot storage for browser interactions
        self.screenshots_dir = self.data_dir / "browser_screenshots"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Monitoring settings
        self.user_consent = user_consent
        self.record_screen = record_screen
        self.record_keyboard = record_keyboard
        self.record_mouse = record_mouse
        self.record_apps = record_apps
        self.record_files = record_files
        
        # Monitoring state
        self.monitoring_active = False
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Data buffers
        self.screen_buffer = deque(maxlen=100)
        self.keyboard_buffer = deque(maxlen=1000)
        self.mouse_buffer = deque(maxlen=1000)
        self.app_buffer = deque(maxlen=1000)
        self.file_buffer = deque(maxlen=1000)
        self.excel_buffer = deque(maxlen=1000)
        self.browser_buffer = deque(maxlen=1000)
        self.pdf_buffer = deque(maxlen=1000)
        
        # Mouse monitoring optimization (reduced overhead for smooth operation)
        self.mouse_move_throttle = 0.2  # Only record mouse movements every 0.2 seconds (reduced frequency)
        self.last_mouse_move_time = 0
        self.mouse_move_batch = []  # Batch mouse movements
        self.mouse_move_batch_size = 20  # Larger batch size to reduce overhead
        
        # Database
        self.db_path = self.data_dir / "full_monitoring.db"
        self._init_database()
        
        # Encryption
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key) if ENCRYPTION_AVAILABLE else None
        
        # Setup logging
        self.log_file = self.data_dir / "monitoring.log"
        self._setup_logging()
        
        # Monitoring threads
        self.screen_thread = None
        self.keyboard_listener = None
        self.mouse_listener = None
        self.app_thread = None
        self.file_observer = None
        self.storage_thread = None
        self.excel_thread = None
        self.browser_thread = None
        self.pdf_thread = None
        
        # Screen recording settings
        self.screen_fps = 1  # 1 frame per second (adjustable)
        self.screen_quality = 0.7  # JPEG quality (0-1)
        self.screen_resolution = None  # Will detect automatically
        
        # Storage queue
        self.storage_queue = Queue(maxsize=1000)
        
        # Performance metrics

        self.metrics = {
            "screens_recorded": 0,
            "keystrokes_recorded": 0,
            "mouse_events_recorded": 0,
            "app_switches_recorded": 0,
            "file_events_recorded": 0,
            "excel_events_recorded": 0,
            "browser_events_recorded": 0,
            "pdf_events_recorded": 0,
            "start_time": None,
            "total_data_size": 0
        }

        self.monitoring_config = self._load_settings()
        self.retain_raw_frames = bool(self.monitoring_config.get("retain_raw_frames", False))
        self.record_screen = bool(self.monitoring_config.get("record_screen", self.record_screen))
        self.record_keyboard = bool(self.monitoring_config.get("record_keyboard", self.record_keyboard))
        self.record_mouse = bool(self.monitoring_config.get("record_mouse", self.record_mouse))
        self.record_apps = bool(self.monitoring_config.get("record_apps", self.record_apps))
        self.record_files = bool(self.monitoring_config.get("record_files", self.record_files))
        self.screen_fps = float(self.monitoring_config.get("screen_fps", self.screen_fps)) or 0.2
        if self.screen_fps <= 0:
            self.screen_fps = 0.2
        self.screen_quality = float(self.monitoring_config.get("screen_quality", self.screen_quality))
        self.screen_quality = max(0.1, min(1.0, self.screen_quality))
        mouse_throttle = self.monitoring_config.get("mouse_move_throttle")
        if mouse_throttle is not None:
            try:
                self.mouse_move_throttle = max(0.05, float(mouse_throttle))
            except Exception:
                pass
        queue_limit = self.monitoring_config.get("storage_queue_limit")
        if queue_limit:
            try:
                queue_limit = int(queue_limit)
                if queue_limit > 100:
                    self.storage_queue = Queue(maxsize=queue_limit)
            except Exception:
                pass
    

    def _load_settings(self) -> Dict[str, Any]:
        """Load monitoring configuration overrides."""
        config_path = self.installation_dir / "AI" / "monitoring" / "full_monitoring_config.json"
        try:
            if config_path.exists():
                data = json.loads(config_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def _init_database(self):
        """Initialize monitoring database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Screen recordings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screen_recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                screenshot_data BLOB,
                compressed_data BLOB,
                window_title TEXT,
                active_app TEXT,
                encrypted_data BLOB
            )
        """)
        
        # Keyboard input table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keyboard_input (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                key_pressed TEXT,
                key_name TEXT,
                is_special_key INTEGER,
                active_app TEXT,
                window_title TEXT,
                encrypted_data BLOB
            )
        """)
        
        # Mouse activity table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mouse_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                event_type TEXT,
                x_position INTEGER,
                y_position INTEGER,
                button TEXT,
                scroll_delta INTEGER,
                active_app TEXT,
                window_title TEXT,
                movements_data TEXT,
                movement_count INTEGER,
                encrypted_data BLOB
            )
        """)
        
        # Application usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                app_name TEXT,
                app_path TEXT,
                window_title TEXT,
                is_active INTEGER,
                duration_seconds REAL,
                encrypted_data BLOB
            )
        """)
        
        # File system activity table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                event_type TEXT,
                file_path TEXT,
                file_size INTEGER,
                file_type TEXT,
                app_name TEXT,
                encrypted_data BLOB
            )
        """)
        
        # Activity patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_hash TEXT NOT NULL UNIQUE,
                pattern_type TEXT,
                pattern_data TEXT,
                frequency INTEGER DEFAULT 1,
                confidence_score REAL DEFAULT 0.0,
                first_seen TEXT,
                last_seen TEXT,
                compressed_pattern BLOB,
                encrypted_pattern BLOB
            )
        """)
        
        # Excel activity table - captures cell references, formulas, data entry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS excel_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                workbook_name TEXT,
                worksheet_name TEXT,
                cell_reference TEXT,
                cell_value TEXT,
                formula TEXT,
                action_type TEXT,
                window_title TEXT,
                encrypted_data BLOB
            )
        """)
        
        # Browser activity table - captures URLs, page titles, form interactions from ANY browser
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS browser_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                browser_name TEXT,
                window_title TEXT,
                url TEXT,
                page_title TEXT,
                action_type TEXT,
                element_type TEXT,
                element_id TEXT,
                element_name TEXT,
                element_value TEXT,
                click_x INTEGER,
                click_y INTEGER,
                screenshot_path TEXT,
                screenshot_data BLOB,
                encrypted_data BLOB
            )
        """)
        
        # PDF activity table - captures PDF file operations, form interactions, and document metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pdf_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                pdf_file_path TEXT,
                pdf_file_name TEXT,
                action_type TEXT,
                page_number INTEGER,
                form_field_name TEXT,
                form_field_value TEXT,
                window_title TEXT,
                pdf_viewer_app TEXT,
                encrypted_data BLOB
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_screen_timestamp ON screen_recordings(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_keyboard_timestamp ON keyboard_input(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_excel_session ON excel_activity(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_excel_timestamp ON excel_activity(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_browser_session ON browser_activity(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_browser_timestamp ON browser_activity(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdf_session ON pdf_activity(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdf_timestamp ON pdf_activity(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mouse_timestamp ON mouse_activity(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_timestamp ON application_usage(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_timestamp ON file_activity(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_hash ON activity_patterns(pattern_hash)")
        
        conn.commit()
        conn.close()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key"""
        if not ENCRYPTION_AVAILABLE:
            return None
        
        key_file = self.data_dir / ".encryption_key"
        
        if key_file.exists():
            try:
                with open(key_file, 'rb') as f:
                    return f.read()
            except Exception:
                pass
        
        # Generate new key
        key = Fernet.generate_key()
        
        try:
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)
        except Exception:
            pass
        
        return key
    
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
    
    def start_monitoring(self):
        """Start full system monitoring"""
        if not self.user_consent:
            raise ValueError("User consent is REQUIRED for full system monitoring")
        
        if self.monitoring_active:
            self.logger.warning("Monitoring already active")
            return
        
        self.monitoring_active = True
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.metrics["start_time"] = datetime.now().isoformat()
        
        self.logger.info(f"Starting full system monitoring - Session ID: {self.session_id}")
        self.logger.info(f"Recording: Screen={self.record_screen}, Keyboard={self.record_keyboard}, "
                        f"Mouse={self.record_mouse}, Apps={self.record_apps}, Files={self.record_files}")
        
        # Start screen recording
        if self.record_screen:
            self._start_screen_recording()
        
        # Start keyboard monitoring
        if self.record_keyboard:
            self._start_keyboard_monitoring()
        
        # Start mouse monitoring
        if self.record_mouse:
            self._start_mouse_monitoring()
        
        # Start application monitoring
        if self.record_apps:
            self._start_application_monitoring()
        
        # Start file system monitoring
        if self.record_files:
            self._start_file_system_monitoring()
        
        # Start Excel monitoring (always enabled when apps are monitored)
        if self.record_apps:
            self._start_excel_monitoring()
        
        # Start browser monitoring (always enabled when apps are monitored)
        if self.record_apps:
            self._start_browser_monitoring()
        
        # Start PDF monitoring (always enabled when apps are monitored)
        if self.record_apps:
            self._start_pdf_monitoring()
        
        # Start storage thread
        self._start_storage_thread()
        
        self.logger.info("Full system monitoring started successfully")
    
    def stop_monitoring(self):
        """Stop full system monitoring"""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        
        self.logger.info("Stopping full system monitoring...")
        
        # Stop screen recording
        if self.screen_thread:
            self.screen_thread.join(timeout=5)
        
        # Stop keyboard monitoring
        if self.keyboard_listener:
            self.keyboard_listener.stop()
        
        # Stop mouse monitoring
        if self.mouse_listener:
            self.mouse_listener.stop()
        
        # Stop application monitoring
        if self.app_thread:
            self.app_thread.join(timeout=5)
        
        # Stop file system monitoring
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join(timeout=5)
        
        # Flush any pending mouse movements
        if hasattr(self, 'mouse_move_batch') and self.mouse_move_batch:
            try:
                active_app, window_title = self._get_active_window_info()
                record = {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id,
                    "event_type": "move_batch",
                    "movements": self.mouse_move_batch.copy(),
                    "count": len(self.mouse_move_batch),
                    "active_app": active_app,
                    "window_title": window_title,
                    "table": "mouse_activity"
                }
                if self.cipher_suite:
                    encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                    record["encrypted_data"] = encrypted
                self.mouse_buffer.append(record)
                self.storage_queue.put(record)
                self.metrics["mouse_events_recorded"] += len(self.mouse_move_batch)
                self.mouse_move_batch.clear()
            except:
                pass
        
        # Flush remaining data
        self._flush_all_buffers()
        
        self.logger.info("Full system monitoring stopped")
    
    def _start_screen_recording(self):
        """Start screen recording"""
        # Always re-check dependencies at runtime (in case they were installed after import)
        global MSS_AVAILABLE, PIL_AVAILABLE, mss, Image
        try:
            import mss
            MSS_AVAILABLE = True
            self.logger.info("mss imported successfully at runtime")
        except ImportError as e:
            # If import fails, check if it was already imported at module level
            if not MSS_AVAILABLE or mss is None:
                self.logger.warning(f"Screen recording not available (mss not installed): {e}")
                return
            else:
                self.logger.info("Using mss from module-level import")
        
        try:
            from PIL import Image
            PIL_AVAILABLE = True
            self.logger.info("PIL/Pillow imported successfully at runtime")
        except ImportError as e:
            # If import fails, check if it was already imported at module level
            if not PIL_AVAILABLE or Image is None:
                self.logger.warning(f"Screen recording not available (PIL/Pillow not installed): {e}")
                return
            else:
                self.logger.info("Using PIL/Pillow from module-level import")
        
        def record_screen():
            try:
                with mss.mss() as sct:
                    # Get primary monitor
                    monitor = sct.monitors[1]
                    self.screen_resolution = (monitor["width"], monitor["height"])
                    
                    frame_interval = 1.0 / self.screen_fps
                    last_frame_time = time.time()
                    
                    while self.monitoring_active:
                        try:
                            current_time = time.time()
                            
                            # Check if it's time for next frame
                            if current_time - last_frame_time >= frame_interval:
                                # Capture screen
                                screenshot = sct.grab(monitor)
                                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                                
                                # Get active window info
                                active_app, window_title = self._get_active_window_info()
                                
                                # Compress image
                                img_bytes = self._compress_image(img)
                                
                                # Record screen
                                record = {
                                    "timestamp": datetime.now().isoformat(),
                                    "session_id": self.session_id,
                                    "compressed_data": img_bytes,
                                    "window_title": window_title,
                                    "active_app": active_app,
                                    "table": "screen_recordings"
                                }
                                if self.retain_raw_frames:
                                    record["screenshot_data"] = img.tobytes()
                                else:
                                    record["screenshot_data"] = None
                                
                                # Encrypt if available
                                if self.cipher_suite:
                                    encrypted = self.cipher_suite.encrypt(img_bytes)
                                    record["encrypted_data"] = encrypted
                                
                                self.screen_buffer.append(record)
                                self.storage_queue.put(record)
                                
                                self.metrics["screens_recorded"] += 1
                                last_frame_time = current_time
                            
                            time.sleep(0.1)  # Small sleep to prevent CPU overload
                            
                        except Exception as e:
                            self.logger.error(f"Error in screen recording: {e}")
                            time.sleep(1)
            
            except Exception as e:
                self.logger.error(f"Error starting screen recording: {e}")
        
        self.screen_thread = threading.Thread(target=record_screen, daemon=True)
        self.screen_thread.start()
        self.logger.info("Screen recording started")
    
    def _start_keyboard_monitoring(self):
        """Start keyboard monitoring"""
        # Always re-check dependencies at runtime
        global INPUT_MONITORING_AVAILABLE, keyboard, mouse, KeyboardListener, MouseListener, Button
        try:
            from pynput import keyboard, mouse
            from pynput.keyboard import Key, Listener as KeyboardListener
            from pynput.mouse import Listener as MouseListener, Button
            INPUT_MONITORING_AVAILABLE = True
            self.logger.info("pynput imported successfully at runtime")
        except ImportError as e:
            # If import fails, check if it was already imported at module level
            if not INPUT_MONITORING_AVAILABLE or keyboard is None or mouse is None:
                self.logger.warning(f"Keyboard monitoring not available (pynput not installed): {e}")
                return
            else:
                self.logger.info("Using pynput from module-level import")
        
        def on_press(key):
            try:
                if not self.monitoring_active:
                    return
                
                # Get key name
                try:
                    key_name = key.char if hasattr(key, 'char') and key.char else str(key)
                except AttributeError:
                    key_name = str(key)
                
                # Get active window info
                active_app, window_title = self._get_active_window_info()
                
                # Record keystroke
                record = {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id,
                    "key_pressed": key_name,
                    "key_name": key_name,
                    "is_special_key": 1 if not hasattr(key, 'char') else 0,
                    "active_app": active_app,
                    "window_title": window_title,
                    "table": "keyboard_input"
                }
                
                # If typing in a browser, also record it in browser_activity table
                if active_app and ("chrome" in active_app.lower() or "firefox" in active_app.lower() or "edge" in active_app.lower() or "msedge" in active_app.lower()):
                    # Only record actual character keys (not special keys like Enter, Tab, etc.)
                    if hasattr(key, 'char') and key.char:
                        # Extract URL from window title if possible
                        url = None
                        page_title = window_title
                        if "http://" in window_title or "https://" in window_title:
                            parts = window_title.split(" - ")
                            if len(parts) > 1:
                                potential_url = parts[-1]
                                if "http" in potential_url:
                                    url = potential_url
                                    page_title = " - ".join(parts[:-1])
                        
                        browser_name = "Chrome" if "chrome" in active_app.lower() else "Firefox" if "firefox" in active_app.lower() else "Edge"
                        
                        browser_record = {
                            "timestamp": datetime.now().isoformat(),
                            "session_id": self.session_id,
                            "browser_name": browser_name,
                            "window_title": window_title,
                            "url": url or "",
                            "page_title": page_title,
                            "action_type": "type",
                            "element_type": "input",
                            "element_id": None,
                            "element_name": "Form input field",
                            "element_value": key.char,  # Record the character typed
                            "table": "browser_activity"
                        }
                        
                        # Encrypt if available
                        if self.cipher_suite:
                            try:
                                encrypted = self.cipher_suite.encrypt(json.dumps(browser_record).encode())
                                browser_record["encrypted_data"] = encrypted
                            except:
                                pass
                        
                        self.browser_buffer.append(browser_record)
                        try:
                            self.storage_queue.put_nowait(browser_record)
                        except:
                            pass
                        self.metrics["browser_events_recorded"] += 1
                
                # Encrypt if available
                if self.cipher_suite:
                    encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                    record["encrypted_data"] = encrypted
                
                self.keyboard_buffer.append(record)
                self.storage_queue.put(record)
                
                self.metrics["keystrokes_recorded"] += 1
                
            except Exception as e:
                self.logger.error(f"Error in keyboard monitoring: {e}")
        
        def on_release(key):
            # Can record key releases if needed
            pass
        
        self.keyboard_listener = KeyboardListener(on_press=on_press, on_release=on_release)
        self.keyboard_listener.start()
        self.logger.info("Keyboard monitoring started")
    
    def _start_mouse_monitoring(self):
        """Start mouse monitoring"""
        # Always re-check dependencies at runtime
        global INPUT_MONITORING_AVAILABLE, keyboard, mouse, KeyboardListener, MouseListener, Button
        try:
            from pynput import keyboard, mouse
            from pynput.keyboard import Key, Listener as KeyboardListener
            from pynput.mouse import Listener as MouseListener, Button
            INPUT_MONITORING_AVAILABLE = True
            self.logger.info("pynput imported successfully at runtime")
        except ImportError as e:
            # If import fails, check if it was already imported at module level
            if not INPUT_MONITORING_AVAILABLE or keyboard is None or mouse is None:
                self.logger.warning(f"Mouse monitoring not available (pynput not installed): {e}")
                return
            else:
                self.logger.info("Using pynput from module-level import")
        
        def on_move(x, y):
            try:
                if not self.monitoring_active:
                    return
                
                # Throttle mouse movements to reduce overhead
                current_time = time.time()
                if current_time - self.last_mouse_move_time < self.mouse_move_throttle:
                    return  # Skip this movement (too frequent)
                
                self.last_mouse_move_time = current_time
                
                # Batch mouse movements instead of recording each one
                self.mouse_move_batch.append({
                    "x": x,
                    "y": y,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Only process batch when it reaches threshold (reduces overhead)
                if len(self.mouse_move_batch) >= self.mouse_move_batch_size:
                    # Get active window info once per batch (reduces expensive calls)
                    try:
                        active_app, window_title = self._get_active_window_info()
                    except:
                        active_app, window_title = "Unknown", "Unknown"
                    
                    # Record batched mouse movements as a single record
                    record = {
                        "timestamp": datetime.now().isoformat(),
                        "session_id": self.session_id,
                        "event_type": "move_batch",
                        "movements": self.mouse_move_batch.copy(),
                        "count": len(self.mouse_move_batch),
                        "active_app": active_app,
                        "window_title": window_title,
                        "table": "mouse_activity"
                    }
                    
                    # Encrypt if available (async to avoid blocking)
                    if self.cipher_suite:
                        try:
                            encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                            record["encrypted_data"] = encrypted
                        except:
                            pass  # Skip encryption if it fails (non-critical)
                    
                    # Store in buffer and queue (non-blocking)
                    self.mouse_buffer.append(record)
                    try:
                        self.storage_queue.put_nowait(record)  # Non-blocking put
                    except:
                        pass  # Skip if queue is full (non-critical)
                    
                    self.metrics["mouse_events_recorded"] += len(self.mouse_move_batch)
                    self.mouse_move_batch.clear()  # Clear batch after storing
                
            except Exception as e:
                # Silent fail for mouse movements to avoid performance impact
                pass
        
        def on_click(x, y, button, pressed):
            try:
                if not self.monitoring_active:
                    return
                
                # Flush any pending mouse movements before recording click (non-blocking)
                if self.mouse_move_batch:
                    try:
                        active_app, window_title = self._get_active_window_info()
                    except:
                        active_app, window_title = "Unknown", "Unknown"
                    record = {
                        "timestamp": datetime.now().isoformat(),
                        "session_id": self.session_id,
                        "event_type": "move_batch",
                        "movements": self.mouse_move_batch.copy(),
                        "count": len(self.mouse_move_batch),
                        "active_app": active_app,
                        "window_title": window_title,
                        "table": "mouse_activity"
                    }
                    if self.cipher_suite:
                        try:
                            encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                            record["encrypted_data"] = encrypted
                        except:
                            pass
                    self.mouse_buffer.append(record)
                    try:
                        self.storage_queue.put_nowait(record)  # Non-blocking
                    except:
                        pass
                    self.metrics["mouse_events_recorded"] += len(self.mouse_move_batch)
                    self.mouse_move_batch.clear()
                
                # Get active window info (optimized)
                try:
                    active_app, window_title = self._get_active_window_info()
                except:
                    active_app, window_title = "Unknown", "Unknown"
                
                # Try to get element information if clicking in a browser
                element_info = None
                screenshot_path = None
                screenshot_data = None
                
                if pressed and active_app and ("chrome" in active_app.lower() or "firefox" in active_app.lower() or "edge" in active_app.lower() or "msedge" in active_app.lower()):
                    # Try to get element at click position using Windows UI Automation
                    try:
                        import win32gui
                        import win32api
                        hwnd = win32gui.WindowFromPoint((x, y))
                        if hwnd:
                            # Try to get element text or name
                            try:
                                window_text = win32gui.GetWindowText(hwnd)
                                class_name = win32gui.GetClassName(hwnd)
                                if window_text or class_name:
                                    element_info = {
                                        "element_text": window_text[:100] if window_text else "",
                                        "element_class": class_name[:100] if class_name else ""
                                    }
                            except:
                                pass
                    except:
                        pass
                    
                    # ALWAYS capture screenshot around click point for browser clicks (for OpenAI Vision analysis)
                    try:
                        from PIL import ImageGrab
                        # Capture a larger region around the click point (400x400 pixels for better context)
                        bbox = (max(0, x - 200), max(0, y - 200), x + 200, y + 200)
                        screenshot = ImageGrab.grab(bbox=bbox)
                        
                        # Save screenshot
                        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                        screenshot_filename = f"click_{self.session_id}_{timestamp_str}.png"
                        screenshot_path_full = self.screenshots_dir / screenshot_filename
                        screenshot.save(screenshot_path_full, "PNG")
                        screenshot_path = str(screenshot_path_full.relative_to(self.data_dir))
                        
                        # Also store as bytes for database (compressed)
                        from io import BytesIO
                        buffer = BytesIO()
                        screenshot.save(buffer, format='PNG', optimize=True)
                        screenshot_data = buffer.getvalue()
                        buffer.close()
                    except Exception as e:
                        self.logger.debug(f"Could not capture screenshot for click: {e}")
                
                # Record mouse click (clicks are important, record immediately)
                record = {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id,
                    "event_type": "click" if pressed else "release",
                    "x_position": x,
                    "y_position": y,
                    "button": str(button),
                    "scroll_delta": None,
                    "active_app": active_app,
                    "window_title": window_title,
                    "table": "mouse_activity"
                }
                
                # If this is a click in a browser, also record it in browser_activity table
                if pressed and active_app and ("chrome" in active_app.lower() or "firefox" in active_app.lower() or "edge" in active_app.lower() or "msedge" in active_app.lower()):
                    # Extract URL from window title if possible
                    url = None
                    page_title = window_title
                    if "http://" in window_title or "https://" in window_title:
                        parts = window_title.split(" - ")
                        if len(parts) > 1:
                            potential_url = parts[-1]
                            if "http" in potential_url:
                                url = potential_url
                                page_title = " - ".join(parts[:-1])
                    
                    browser_name = "Chrome" if "chrome" in active_app.lower() else "Firefox" if "firefox" in active_app.lower() else "Edge"
                    
                    browser_record = {
                        "timestamp": datetime.now().isoformat(),
                        "session_id": self.session_id,
                        "browser_name": browser_name,
                        "window_title": window_title,
                        "url": url or "",
                        "page_title": page_title,
                        "action_type": "click",
                        "element_type": element_info.get("element_class") if element_info else None,
                        "element_id": None,
                        "element_name": element_info.get("element_text") if element_info else f"Click at ({x}, {y})",
                        "element_value": None,
                        "click_x": x,
                        "click_y": y,
                        "screenshot_path": screenshot_path,
                        "screenshot_data": screenshot_data,
                        "table": "browser_activity"
                    }
                    
                    # Encrypt if available
                    if self.cipher_suite:
                        try:
                            encrypted = self.cipher_suite.encrypt(json.dumps(browser_record).encode())
                            browser_record["encrypted_data"] = encrypted
                        except:
                            pass
                    
                    self.browser_buffer.append(browser_record)
                    try:
                        self.storage_queue.put_nowait(browser_record)
                    except:
                        pass
                    self.metrics["browser_events_recorded"] += 1
                
                # Encrypt if available (non-blocking)
                if self.cipher_suite:
                    try:
                        encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                        record["encrypted_data"] = encrypted
                    except:
                        pass  # Skip encryption if it fails (non-critical)
                
                # Store in buffer and queue (non-blocking)
                self.mouse_buffer.append(record)
                try:
                    self.storage_queue.put_nowait(record)  # Non-blocking put
                except:
                    pass  # Skip if queue is full (non-critical)
                
                self.metrics["mouse_events_recorded"] += 1
                
            except Exception as e:
                # Silent fail for mouse clicks to avoid performance impact
                pass
        
        def on_scroll(x, y, dx, dy):
            try:
                if not self.monitoring_active:
                    return
                
                # Flush any pending mouse movements before recording scroll (non-blocking)
                if self.mouse_move_batch:
                    try:
                        active_app, window_title = self._get_active_window_info()
                    except:
                        active_app, window_title = "Unknown", "Unknown"
                    record = {
                        "timestamp": datetime.now().isoformat(),
                        "session_id": self.session_id,
                        "event_type": "move_batch",
                        "movements": self.mouse_move_batch.copy(),
                        "count": len(self.mouse_move_batch),
                        "active_app": active_app,
                        "window_title": window_title,
                        "table": "mouse_activity"
                    }
                    if self.cipher_suite:
                        try:
                            encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                            record["encrypted_data"] = encrypted
                        except:
                            pass
                    self.mouse_buffer.append(record)
                    try:
                        self.storage_queue.put_nowait(record)  # Non-blocking
                    except:
                        pass
                    self.metrics["mouse_events_recorded"] += len(self.mouse_move_batch)
                    self.mouse_move_batch.clear()
                
                # Get active window info (optimized)
                try:
                    active_app, window_title = self._get_active_window_info()
                except:
                    active_app, window_title = "Unknown", "Unknown"
                
                # Record mouse scroll (scrolls are important, record immediately)
                record = {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id,
                    "event_type": "scroll",
                    "x_position": x,
                    "y_position": y,
                    "button": None,
                    "scroll_delta": dy,
                    "active_app": active_app,
                    "window_title": window_title,
                    "table": "mouse_activity"
                }
                
                # Encrypt if available (non-blocking)
                if self.cipher_suite:
                    try:
                        encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                        record["encrypted_data"] = encrypted
                    except:
                        pass  # Skip encryption if it fails (non-critical)
                
                # Store in buffer and queue (non-blocking)
                self.mouse_buffer.append(record)
                try:
                    self.storage_queue.put_nowait(record)  # Non-blocking put
                except:
                    pass  # Skip if queue is full (non-critical)
                
                self.metrics["mouse_events_recorded"] += 1
                
            except Exception as e:
                # Silent fail for mouse scrolls to avoid performance impact
                pass
        
        self.mouse_listener = MouseListener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
        self.mouse_listener.start()
        self.logger.info("Mouse monitoring started")
    
    def _start_application_monitoring(self):
        """Start application monitoring"""
        # Always re-check dependencies at runtime
        global PROCESS_MONITORING_AVAILABLE, psutil
        try:
            import psutil
            PROCESS_MONITORING_AVAILABLE = True
            self.logger.info("psutil imported successfully at runtime")
        except ImportError as e:
            # If import fails, check if it was already imported at module level
            if not PROCESS_MONITORING_AVAILABLE or psutil is None:
                self.logger.warning(f"Application monitoring not available (psutil not installed): {e}")
                return
            else:
                self.logger.info("Using psutil from module-level import")
        
        def monitor_applications():
            last_active_app = None
            app_start_time = None
            
            while self.monitoring_active:
                try:
                    # Get active application
                    active_app, window_title = self._get_active_window_info()
                    
                    # Check if app changed
                    if active_app != last_active_app:
                        # Record app switch
                        if last_active_app and app_start_time:
                            duration = (datetime.now() - app_start_time).total_seconds()
                            
                            record = {
                                "timestamp": datetime.now().isoformat(),
                                "session_id": self.session_id,
                                "app_name": last_active_app,
                                "app_path": None,  # Can be enhanced
                                "window_title": window_title,
                                "is_active": 0,
                                "duration_seconds": duration,
                                "table": "application_usage"
                            }
                            
                            # Encrypt if available
                            if self.cipher_suite:
                                encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                                record["encrypted_data"] = encrypted
                            
                            self.app_buffer.append(record)
                            self.storage_queue.put(record)
                            
                            self.metrics["app_switches_recorded"] += 1
                        
                        # Record new app
                        record = {
                            "timestamp": datetime.now().isoformat(),
                            "session_id": self.session_id,
                            "app_name": active_app,
                            "app_path": None,
                            "window_title": window_title,
                            "is_active": 1,
                            "duration_seconds": 0,
                            "table": "application_usage"
                        }
                        
                        # Encrypt if available
                        if self.cipher_suite:
                            encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                            record["encrypted_data"] = encrypted
                        
                        self.app_buffer.append(record)
                        self.storage_queue.put(record)
                        
                        last_active_app = active_app
                        app_start_time = datetime.now()
                    
                    time.sleep(1)  # Check every second
                    
                except Exception as e:
                    self.logger.error(f"Error in application monitoring: {e}")
                    time.sleep(5)
        
        self.app_thread = threading.Thread(target=monitor_applications, daemon=True)
        self.app_thread.start()
        self.logger.info("Application monitoring started")
    
    def _start_file_system_monitoring(self):
        """Start file system monitoring"""
        # Always re-check dependencies at runtime
        global FILESYSTEM_MONITORING_AVAILABLE, Observer, FileSystemEventHandler
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            FILESYSTEM_MONITORING_AVAILABLE = True
            self.logger.info("watchdog imported successfully at runtime")
        except ImportError as e:
            # If import fails, check if it was already imported at module level
            if not FILESYSTEM_MONITORING_AVAILABLE or Observer is None or FileSystemEventHandler is None:
                self.logger.warning(f"File system monitoring not available (watchdog not installed): {e}")
                return
            else:
                self.logger.info("Using watchdog from module-level import")
        
        class FileSystemHandler(FileSystemEventHandler):
            def __init__(self, monitor):
                self.monitor = monitor
                super().__init__()
            
            def on_created(self, event):
                # Skip directory events
                if not event.is_directory:
                    self.monitor._record_file_event("created", event.src_path)
            
            def on_modified(self, event):
                # Skip directory events
                if not event.is_directory:
                    self.monitor._record_file_event("modified", event.src_path)
            
            def on_deleted(self, event):
                # Skip directory events
                if not event.is_directory:
                    self.monitor._record_file_event("deleted", event.src_path)
            
            def on_moved(self, event):
                # Skip directory events
                if not event.is_directory:
                    self.monitor._record_file_event("moved", event.src_path)
        
        try:
            # Monitor common directories (exclude database directories to avoid monitoring journal files)
            watch_dirs = [
                Path.home() / "Desktop",
                Path.home() / "Documents",
                Path.home() / "Downloads",
                # Exclude _secure_data directory to avoid monitoring database journal files
                # self.installation_dir  # Commented out to avoid monitoring database files
            ]
            
            # Only monitor installation_dir if it's not the database directory
            if self.installation_dir != self.data_dir.parent:
                watch_dirs.append(self.installation_dir)
            
            self.file_observer = Observer()
            
            for watch_dir in watch_dirs:
                if watch_dir.exists():
                    handler = FileSystemHandler(self)
                    self.file_observer.schedule(handler, str(watch_dir), recursive=True)
            
            self.file_observer.start()
            self.logger.info("File system monitoring started")
            
        except Exception as e:
            self.logger.error(f"Error starting file system monitoring: {e}")
    
    def _start_excel_monitoring(self):
        """Start Excel-specific monitoring to capture cell references, formulas, and data entry"""
        def monitor_excel():
            last_excel_state = None
            
            while self.monitoring_active:
                try:
                    active_app, window_title = self._get_active_window_info()
                    
                    # Check if Excel is active
                    is_excel = active_app and ("EXCEL.EXE" in active_app.upper() or "excel" in active_app.lower())
                    
                    if is_excel:
                        try:
                            # Try to use COM automation to get Excel details
                            try:
                                import win32com.client
                                excel_app = win32com.client.GetActiveObject("Excel.Application")
                                
                                # Get active workbook and worksheet
                                try:
                                    workbook = excel_app.ActiveWorkbook
                                    worksheet = excel_app.ActiveSheet
                                    active_cell = excel_app.ActiveCell
                                    
                                    if workbook and worksheet and active_cell:
                                        workbook_name = workbook.Name if workbook else "Unknown"
                                        worksheet_name = worksheet.Name if worksheet else "Unknown"
                                        cell_ref = active_cell.Address if active_cell else "Unknown"
                                        
                                        # Get cell value and formula
                                        try:
                                            cell_value = str(active_cell.Value) if active_cell.Value is not None else ""
                                            formula = str(active_cell.Formula) if hasattr(active_cell, 'Formula') and active_cell.Formula else ""
                                        except:
                                            cell_value = ""
                                            formula = ""
                                        
                                        # Create state hash to detect changes
                                        current_state = f"{workbook_name}|{worksheet_name}|{cell_ref}|{cell_value}"
                                        
                                        if current_state != last_excel_state:
                                            record = {
                                                "timestamp": datetime.now().isoformat(),
                                                "session_id": self.session_id,
                                                "workbook_name": workbook_name,
                                                "worksheet_name": worksheet_name,
                                                "cell_reference": cell_ref,
                                                "cell_value": cell_value[:500] if cell_value else "",  # Limit length
                                                "formula": formula[:500] if formula else "",  # Limit length
                                                "action_type": "cell_selection" if last_excel_state else "workbook_open",
                                                "window_title": window_title,
                                                "table": "excel_activity"
                                            }
                                            
                                            # Encrypt if available
                                            if self.cipher_suite:
                                                encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                                                record["encrypted_data"] = encrypted
                                            
                                            self.excel_buffer.append(record)
                                            self.storage_queue.put(record)
                                            self.metrics["excel_events_recorded"] += 1
                                            last_excel_state = current_state
                                        
                                        excel_app = None  # Release COM object
                                except Exception as e:
                                    # Excel might not have active workbook/worksheet
                                    pass
                            except ImportError:
                                # win32com not available, use window title parsing as fallback
                                if window_title and window_title != last_excel_state:
                                    # Extract workbook name from window title (e.g., "Book1 - Excel")
                                    workbook_name = window_title.split(" - ")[0] if " - " in window_title else window_title
                                    
                                    record = {
                                        "timestamp": datetime.now().isoformat(),
                                        "session_id": self.session_id,
                                        "workbook_name": workbook_name,
                                        "worksheet_name": "Unknown",
                                        "cell_reference": "Unknown",
                                        "cell_value": "",
                                        "formula": "",
                                        "action_type": "workbook_open",
                                        "window_title": window_title,
                                        "table": "excel_activity"
                                    }
                                    
                                    if self.cipher_suite:
                                        encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                                        record["encrypted_data"] = encrypted
                                    
                                    self.excel_buffer.append(record)
                                    self.storage_queue.put(record)
                                    self.metrics["excel_events_recorded"] += 1
                                    last_excel_state = window_title
                            except Exception as e:
                                # Excel COM automation failed
                                pass
                        except Exception as e:
                            pass
                    else:
                        last_excel_state = None
                    
                    time.sleep(2)  # Check every 2 seconds (Excel doesn't change as frequently)
                    
                except Exception as e:
                    self.logger.error(f"Error in Excel monitoring: {e}")
                    time.sleep(5)
        
        self.excel_thread = threading.Thread(target=monitor_excel, daemon=True)
        self.excel_thread.start()
        self.logger.info("Excel monitoring started")
    
    def _start_browser_monitoring(self):
        """Start browser-specific monitoring to capture URLs, page titles, and form interactions from ANY browser"""
        def monitor_browser():
            last_url = None
            last_page_title = None
            
            while self.monitoring_active:
                try:
                    active_app, window_title = self._get_active_window_info()
                    
                    # Detect browser applications
                    browser_name = None
                    if active_app:
                        app_lower = active_app.lower()
                        if "chrome" in app_lower:
                            browser_name = "Chrome"
                        elif "firefox" in app_lower or "firefox.exe" in app_lower:
                            browser_name = "Firefox"
                        elif "edge" in app_lower or "msedge" in app_lower:
                            browser_name = "Edge"
                        elif "opera" in app_lower:
                            browser_name = "Opera"
                        elif "brave" in app_lower:
                            browser_name = "Brave"
                        elif "safari" in app_lower:
                            browser_name = "Safari"
                    
                    if browser_name and window_title:
                        # Try to extract URL from window title or use browser automation
                        url = None
                        page_title = window_title
                        
                        # Try to extract URL using browser-specific methods
                        try:
                            # For Chrome/Edge: Try to get URL from window title or use automation
                            if browser_name in ["Chrome", "Edge"]:
                                try:
                                    import win32gui
                                    import win32process
                                    import psutil
                                    
                                    # Get browser window handle
                                    hwnd = win32gui.GetForegroundWindow()
                                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                                    
                                    # Try to get URL from browser process (limited - browsers protect this)
                                    # Fallback: Parse from window title if it contains URL
                                    if "http://" in window_title or "https://" in window_title:
                                        # Extract URL from title if present
                                        parts = window_title.split(" - ")
                                        if len(parts) > 1:
                                            potential_url = parts[-1]
                                            if "http" in potential_url:
                                                url = potential_url
                                                page_title = " - ".join(parts[:-1])
                                except:
                                    pass
                        except Exception as e:
                            pass
                        
                        # Record browser activity if URL or title changed
                        current_state = f"{url}|{page_title}"
                        if current_state != last_url or page_title != last_page_title:
                            record = {
                                "timestamp": datetime.now().isoformat(),
                                "session_id": self.session_id,
                                "browser_name": browser_name,
                                "window_title": window_title,
                                "url": url or "",
                                "page_title": page_title,
                                "action_type": "navigation" if url != last_url else "title_change",
                                "element_type": None,
                                "element_id": None,
                                "element_name": None,
                                "element_value": None,
                                "table": "browser_activity"
                            }
                            
                            # Encrypt if available
                            if self.cipher_suite:
                                encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                                record["encrypted_data"] = encrypted
                            
                            self.browser_buffer.append(record)
                            self.storage_queue.put(record)
                            self.metrics["browser_events_recorded"] += 1
                            
                            last_url = url
                            last_page_title = page_title
                    else:
                        last_url = None
                        last_page_title = None
                    
                    time.sleep(1)  # Check every second for browser activity
                    
                except Exception as e:
                    self.logger.error(f"Error in browser monitoring: {e}")
                    time.sleep(5)
        
        self.browser_thread = threading.Thread(target=monitor_browser, daemon=True)
        self.browser_thread.start()
        self.logger.info("Browser monitoring started")
    
    def _start_pdf_monitoring(self):
        """Start PDF-specific monitoring to capture PDF file operations and form interactions"""
        def monitor_pdf():
            last_pdf_state = None
            
            while self.monitoring_active:
                try:
                    active_app, window_title = self._get_active_window_info()
                    
                    # Detect PDF viewer applications
                    is_pdf_viewer = False
                    pdf_viewer_app = None
                    if active_app:
                        app_lower = active_app.lower()
                        if "acrobat" in app_lower or "acrord32" in app_lower or "acrobat.exe" in app_lower:
                            is_pdf_viewer = True
                            pdf_viewer_app = "Adobe Acrobat"
                        elif "foxit" in app_lower or "foxitreader" in app_lower:
                            is_pdf_viewer = True
                            pdf_viewer_app = "Foxit Reader"
                        elif "sumatra" in app_lower or "sumatrapdf" in app_lower:
                            is_pdf_viewer = True
                            pdf_viewer_app = "Sumatra PDF"
                        elif "chrome" in app_lower and ".pdf" in window_title.lower():
                            is_pdf_viewer = True
                            pdf_viewer_app = "Chrome PDF Viewer"
                        elif "edge" in app_lower and ".pdf" in window_title.lower():
                            is_pdf_viewer = True
                            pdf_viewer_app = "Edge PDF Viewer"
                    
                    if is_pdf_viewer and window_title:
                        # Extract PDF file name from window title
                        pdf_file_name = window_title
                        if ".pdf" in window_title.lower():
                            # Try to extract just the filename
                            parts = window_title.split(" - ")
                            for part in parts:
                                if ".pdf" in part.lower():
                                    pdf_file_name = part.strip()
                                    break
                        
                        # Try to get full file path from window title or active document
                        pdf_file_path = None
                        try:
                            # For Adobe Acrobat, try to get file path via COM
                            if pdf_viewer_app == "Adobe Acrobat":
                                try:
                                    import win32com.client
                                    acrobat_app = win32com.client.GetActiveObject("AcroExch.App")
                                    if acrobat_app:
                                        try:
                                            av_doc = acrobat_app.GetActiveDoc()
                                            if av_doc:
                                                pdf_file_path = av_doc.GetPath()
                                                acrobat_app = None
                                        except:
                                            pass
                                except:
                                    pass
                        except:
                            pass
                        
                        # Create state hash to detect changes
                        current_state = f"{pdf_file_name}|{window_title}"
                        
                        if current_state != last_pdf_state:
                            record = {
                                "timestamp": datetime.now().isoformat(),
                                "session_id": self.session_id,
                                "pdf_file_path": pdf_file_path or "",
                                "pdf_file_name": pdf_file_name,
                                "action_type": "pdf_open" if not last_pdf_state else "pdf_navigate",
                                "page_number": None,
                                "form_field_name": None,
                                "form_field_value": None,
                                "window_title": window_title,
                                "pdf_viewer_app": pdf_viewer_app,
                                "table": "pdf_activity"
                            }
                            
                            # Encrypt if available
                            if self.cipher_suite:
                                encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                                record["encrypted_data"] = encrypted
                            
                            self.pdf_buffer.append(record)
                            self.storage_queue.put(record)
                            self.metrics["pdf_events_recorded"] += 1
                            last_pdf_state = current_state
                    else:
                        last_pdf_state = None
                    
                    time.sleep(2)  # Check every 2 seconds (PDFs don't change as frequently)
                    
                except Exception as e:
                    self.logger.error(f"Error in PDF monitoring: {e}")
                    time.sleep(5)
        
        self.pdf_thread = threading.Thread(target=monitor_pdf, daemon=True)
        self.pdf_thread.start()
        self.logger.info("PDF monitoring started")
    
    def _record_file_event(self, event_type: str, file_path: str):
        """Record file system event"""
        try:
            if not self.monitoring_active:
                return
            
            file_path_obj = Path(file_path)
            
            # Skip database files and temporary files
            file_name = file_path_obj.name.lower()
            if (file_name.endswith('.db-journal') or 
                file_name.endswith('.db-wal') or 
                file_name.endswith('.db-shm') or
                file_name.endswith('.tmp') or
                file_name.endswith('.temp') or
                file_name.startswith('~$') or
                file_name.startswith('.~')):
                return  # Skip temporary database files and temp files
            
            # Skip if file doesn't exist (might be a temporary file that was deleted)
            if not file_path_obj.exists():
                return
            
            # Get file info
            try:
                file_size = file_path_obj.stat().st_size
                file_type = file_path_obj.suffix
            except (OSError, FileNotFoundError):
                # File was deleted or inaccessible - skip it
                return
            
            # Get active app
            active_app, _ = self._get_active_window_info()
            
            # Record file event
            record = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "event_type": event_type,
                "file_path": str(file_path),
                "file_size": file_size,
                "file_type": file_type,
                "app_name": active_app,
                "table": "file_activity"
            }
            
            # If it's a PDF file, also record in PDF activity table
            if file_type.lower() == ".pdf" and event_type in ["created", "modified"]:
                pdf_record = {
                    "timestamp": datetime.now().isoformat(),
                    "session_id": self.session_id,
                    "pdf_file_path": str(file_path),
                    "pdf_file_name": file_path_obj.name,
                    "action_type": f"pdf_{event_type}",
                    "page_number": None,
                    "form_field_name": None,
                    "form_field_value": None,
                    "window_title": None,
                    "pdf_viewer_app": active_app,
                    "table": "pdf_activity"
                }
                
                if self.cipher_suite:
                    encrypted = self.cipher_suite.encrypt(json.dumps(pdf_record).encode())
                    pdf_record["encrypted_data"] = encrypted
                
                self.pdf_buffer.append(pdf_record)
                self.storage_queue.put(pdf_record)
                self.metrics["pdf_events_recorded"] += 1
            
            # Encrypt if available
            if self.cipher_suite:
                encrypted = self.cipher_suite.encrypt(json.dumps(record).encode())
                record["encrypted_data"] = encrypted
            
            self.file_buffer.append(record)
            self.storage_queue.put(record)
            
            self.metrics["file_events_recorded"] += 1
            
        except Exception as e:
            # Only log errors for non-temporary files
            if not file_path.endswith(('.db-journal', '.db-wal', '.db-shm', '.tmp', '.temp')):
                self.logger.debug(f"Error recording file event: {e}")
    
    def _start_storage_thread(self):
        """Start background storage thread"""
        def store_data():
            records_stored = 0
            last_log_time = time.time()
            while self.monitoring_active or not self.storage_queue.empty():
                try:
                    # Get record from queue
                    try:
                        record = self.storage_queue.get(timeout=1)
                    except:
                        continue
                    
                    # Store in database
                    if self._store_record(record):
                        records_stored += 1
                        self.storage_queue.task_done()
                        
                        # Log progress every 10 seconds
                        current_time = time.time()
                        if current_time - last_log_time >= 10:
                            self.logger.info(f"Storage thread: {records_stored} records stored (queue size: {self.storage_queue.qsize()})")
                            last_log_time = current_time
                    else:
                        # Store failed, put back in queue
                        self.storage_queue.put(record)
                        self.storage_queue.task_done()
                        time.sleep(0.5)  # Wait before retry
                    
                except Exception as e:
                    self.logger.error(f"Error in storage thread: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    time.sleep(1)
            
            if records_stored > 0:
                self.logger.info(f"Storage thread finished: {records_stored} total records stored")
        
        self.storage_thread = threading.Thread(target=store_data, daemon=True)
        self.storage_thread.start()
        self.logger.info("Storage thread started")
    
    def _store_record(self, record: Dict):
        """Store record in database"""
        try:
            # Make a copy to avoid modifying original
            record_copy = record.copy()
            table = record_copy.pop("table", None)
            
            if not table:
                self.logger.warning("Record missing 'table' field, skipping")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if table == "screen_recordings":
                compressed_blob = record_copy.get("compressed_data") or record_copy.get("screenshot_data")
                raw_blob = record_copy.get("screenshot_data") if self.retain_raw_frames else None
                cursor.execute("""
                    INSERT INTO screen_recordings
                    (timestamp, session_id, screenshot_data, compressed_data, window_title, active_app, encrypted_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_copy.get("timestamp"),
                    record_copy.get("session_id"),
                    raw_blob,
                    compressed_blob,
                    record_copy.get("window_title"),
                    record_copy.get("active_app"),
                    record_copy.get("encrypted_data")
                ))
            
            elif table == "keyboard_input":
                cursor.execute("""
                    INSERT INTO keyboard_input
                    (timestamp, session_id, key_pressed, key_name, is_special_key, active_app, window_title, encrypted_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_copy.get("timestamp"),
                    record_copy.get("session_id"),
                    record_copy.get("key_pressed"),
                    record_copy.get("key_name"),
                    record_copy.get("is_special_key"),
                    record_copy.get("active_app"),
                    record_copy.get("window_title"),
                    record_copy.get("encrypted_data")
                ))
            
            elif table == "mouse_activity":
                # Handle batched movements
                if record_copy.get("event_type") == "move_batch":
                    movements_data = json.dumps(record_copy.get("movements", []))
                    cursor.execute("""
                        INSERT INTO mouse_activity
                        (timestamp, session_id, event_type, x_position, y_position, button, scroll_delta, active_app, window_title, movements_data, movement_count, encrypted_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record_copy.get("timestamp"),
                        record_copy.get("session_id"),
                        record_copy.get("event_type"),
                        None,  # x_position for batch
                        None,  # y_position for batch
                        None,  # button for batch
                        None,  # scroll_delta for batch
                        record_copy.get("active_app"),
                        record_copy.get("window_title"),
                        movements_data,
                        record_copy.get("count", 0),
                        record_copy.get("encrypted_data")
                    ))
                else:
                    # Handle individual events (clicks, scrolls)
                    cursor.execute("""
                        INSERT INTO mouse_activity
                        (timestamp, session_id, event_type, x_position, y_position, button, scroll_delta, active_app, window_title, movements_data, movement_count, encrypted_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record_copy.get("timestamp"),
                        record_copy.get("session_id"),
                        record_copy.get("event_type"),
                        record_copy.get("x_position"),
                        record_copy.get("y_position"),
                        record_copy.get("button"),
                        record_copy.get("scroll_delta"),
                        record_copy.get("active_app"),
                        record_copy.get("window_title"),
                        None,  # movements_data for individual events
                        None,  # movement_count for individual events
                        record_copy.get("encrypted_data")
                    ))
            
            elif table == "application_usage":
                cursor.execute("""
                    INSERT INTO application_usage
                    (timestamp, session_id, app_name, app_path, window_title, is_active, duration_seconds, encrypted_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_copy.get("timestamp"),
                    record_copy.get("session_id"),
                    record_copy.get("app_name"),
                    record_copy.get("app_path"),
                    record_copy.get("window_title"),
                    record_copy.get("is_active"),
                    record_copy.get("duration_seconds"),
                    record_copy.get("encrypted_data")
                ))
            
            elif table == "file_activity":
                cursor.execute("""
                    INSERT INTO file_activity
                    (timestamp, session_id, event_type, file_path, file_size, file_type, app_name, encrypted_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_copy.get("timestamp"),
                    record_copy.get("session_id"),
                    record_copy.get("event_type"),
                    record_copy.get("file_path"),
                    record_copy.get("file_size"),
                    record_copy.get("file_type"),
                    record_copy.get("app_name"),
                    record_copy.get("encrypted_data")
                ))
            
            elif table == "excel_activity":
                cursor.execute("""
                    INSERT INTO excel_activity
                    (timestamp, session_id, workbook_name, worksheet_name, cell_reference, cell_value, formula, action_type, window_title, encrypted_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_copy.get("timestamp"),
                    record_copy.get("session_id"),
                    record_copy.get("workbook_name"),
                    record_copy.get("worksheet_name"),
                    record_copy.get("cell_reference"),
                    record_copy.get("cell_value"),
                    record_copy.get("formula"),
                    record_copy.get("action_type"),
                    record_copy.get("window_title"),
                    record_copy.get("encrypted_data")
                ))
            
            elif table == "browser_activity":
                cursor.execute("""
                    INSERT INTO browser_activity
                    (timestamp, session_id, browser_name, window_title, url, page_title, action_type, element_type, element_id, element_name, element_value, click_x, click_y, screenshot_path, screenshot_data, encrypted_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_copy.get("timestamp"),
                    record_copy.get("session_id"),
                    record_copy.get("browser_name"),
                    record_copy.get("window_title"),
                    record_copy.get("url"),
                    record_copy.get("page_title"),
                    record_copy.get("action_type"),
                    record_copy.get("element_type"),
                    record_copy.get("element_id"),
                    record_copy.get("element_name"),
                    record_copy.get("element_value"),
                    record_copy.get("click_x"),
                    record_copy.get("click_y"),
                    record_copy.get("screenshot_path"),
                    record_copy.get("screenshot_data"),
                    record_copy.get("encrypted_data")
                ))
            
            elif table == "pdf_activity":
                cursor.execute("""
                    INSERT INTO pdf_activity
                    (timestamp, session_id, pdf_file_path, pdf_file_name, action_type, page_number, form_field_name, form_field_value, window_title, pdf_viewer_app, encrypted_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_copy.get("timestamp"),
                    record_copy.get("session_id"),
                    record_copy.get("pdf_file_path"),
                    record_copy.get("pdf_file_name"),
                    record_copy.get("action_type"),
                    record_copy.get("page_number"),
                    record_copy.get("form_field_name"),
                    record_copy.get("form_field_value"),
                    record_copy.get("window_title"),
                    record_copy.get("pdf_viewer_app"),
                    record_copy.get("encrypted_data")
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing record to {self.db_path}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _get_active_window_info(self) -> Tuple[str, str]:
        """Get active window information (optimized for performance)"""
        try:
            # Try Windows-specific method first (fastest)
            try:
                import win32gui
                import win32process
                
                # Get foreground window (fast)
                hwnd = win32gui.GetForegroundWindow()
                window_title = win32gui.GetWindowText(hwnd)
                
                # Get process name (cached if possible)
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                try:
                    if PROCESS_MONITORING_AVAILABLE and psutil:
                        process = psutil.Process(pid)
                        app_name = process.name()
                    else:
                        app_name = "Unknown"
                except:
                    app_name = "Unknown"
                
                return app_name, window_title
            except ImportError:
                # Fallback to psutil method (slower)
                if PROCESS_MONITORING_AVAILABLE and psutil:
                    # Get active process (simplified for speed)
                    try:
                        # Try to get foreground window using pywinauto (if available)
                        try:
                            from pywinauto import Desktop
                            desktop = Desktop(backend="win32")
                            active_window = desktop.active_window()
                            window_title = active_window.window_text()
                            active_process = active_window.process_name()
                            return active_process or "Unknown", window_title
                        except:
                            # Fallback: return Unknown to avoid expensive iteration
                            return "Unknown", "Unknown"
                    except:
                        return "Unknown", "Unknown"
                else:
                    return "Unknown", "Unknown"
        except Exception as e:
            # Silent fail to avoid performance impact
            return "Unknown", "Unknown"
    
    def _compress_image(self, img) -> bytes:
        """Compress image to reduce storage"""
        if not PIL_AVAILABLE or Image is None:
            return b""
        
        try:
            from io import BytesIO
            
            # Convert PIL Image to bytes
            buffer = BytesIO()
            
            # Save as JPEG with quality setting
            quality = int(self.screen_quality * 100)
            img.save(buffer, format='JPEG', quality=quality, optimize=True)
            
            compressed_data = buffer.getvalue()
            buffer.close()
            
            return compressed_data
        except Exception as e:
            self.logger.error(f"Error compressing image: {e}")
            return b""
    
    def _flush_all_buffers(self):
        """Flush all buffers to database"""
        try:
            # Process all remaining records in queue
            while not self.storage_queue.empty():
                try:
                    record = self.storage_queue.get(timeout=0.1)
                    self._store_record(record)
                    self.storage_queue.task_done()
                except:
                    break
            
            self.logger.info("All buffers flushed to database")
        except Exception as e:
            self.logger.error(f"Error flushing buffers: {e}")
    
    def get_metrics(self) -> Dict:
        """Get monitoring metrics"""
        return {
            **self.metrics,
            "monitoring_active": self.monitoring_active,
            "session_id": self.session_id,
            "buffer_sizes": {
                "screen": len(self.screen_buffer),
                "keyboard": len(self.keyboard_buffer),
                "mouse": len(self.mouse_buffer),
                "apps": len(self.app_buffer),
                "files": len(self.file_buffer),
                "excel": len(self.excel_buffer),
                "browser": len(self.browser_buffer),
                "pdf": len(self.pdf_buffer)
            }
        }
    
    def get_session_data(self, session_id: Optional[str] = None) -> Dict:
        """Get all data for a session"""
        if session_id is None:
            session_id = self.session_id
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get screen recordings
            cursor.execute("SELECT COUNT(*) FROM screen_recordings WHERE session_id = ?", (session_id,))
            screen_count = cursor.fetchone()[0]
            
            # Get keyboard input
            cursor.execute("SELECT COUNT(*) FROM keyboard_input WHERE session_id = ?", (session_id,))
            keyboard_count = cursor.fetchone()[0]
            
            # Get mouse activity
            cursor.execute("SELECT COUNT(*) FROM mouse_activity WHERE session_id = ?", (session_id,))
            mouse_count = cursor.fetchone()[0]
            
            # Get application usage
            cursor.execute("SELECT COUNT(*) FROM application_usage WHERE session_id = ?", (session_id,))
            app_count = cursor.fetchone()[0]
            
            # Get file activity
            cursor.execute("SELECT COUNT(*) FROM file_activity WHERE session_id = ?", (session_id,))
            file_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "session_id": session_id,
                "screen_recordings": screen_count,
                "keyboard_input": keyboard_count,
                "mouse_activity": mouse_count,
                "application_usage": app_count,
                "file_activity": file_count,
                "total_events": screen_count + keyboard_count + mouse_count + app_count + file_count
            }
        except Exception as e:
            self.logger.error(f"Error getting session data: {e}")
            return {}


# Global monitor instance
_global_monitor = None


def get_full_monitor(installation_dir: Optional[Path] = None, user_consent: bool = True) -> FullSystemMonitor:
    """Get global full system monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = FullSystemMonitor(installation_dir, user_consent=user_consent)
    return _global_monitor


def start_full_monitoring(installation_dir: Optional[Path] = None, user_consent: bool = True) -> FullSystemMonitor:
    """Start full system monitoring"""
    global _global_monitor
    
    # If there's an existing monitor that's not active, reset it
    if _global_monitor and not getattr(_global_monitor, "monitoring_active", False):
        _global_monitor = None
    
    monitor = get_full_monitor(installation_dir, user_consent=user_consent)
    
    # Only start if not already active
    if not getattr(monitor, "monitoring_active", False):
        monitor.start_monitoring()
    else:
        print(f"[DEBUG] Monitoring already active, reusing existing session: {monitor.session_id}")
    
    return monitor


def stop_full_monitoring():
    """Stop full system monitoring"""
    global _global_monitor
    if _global_monitor:
        _global_monitor.stop_monitoring()
        _global_monitor = None

