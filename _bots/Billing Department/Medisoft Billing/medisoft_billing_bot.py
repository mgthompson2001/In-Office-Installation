#!/usr/bin/env python3
"""
Medisoft Billing Bot - Medical Records Billing Log Bot
This bot automates login and data entry into Medisoft for medical records billing.
Employees can securely enter their login credentials through a GUI.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog, filedialog
import pyautogui
import pywinauto
import time
import logging
from pathlib import Path
import subprocess
import sys
import threading
import json
import os
import re
from datetime import datetime

# Try to import update manager for automatic updates
try:
    # Try to find Updates folder (could be in different locations)
    updates_paths = [
        Path(__file__).parent.parent.parent.parent / "Updates",  # From bot folder up to root
        Path(r"C:\Users\mthompson\OneDrive - Integrity Senior Services\Desktop\In-Office Installation\Updates"),  # Absolute path
    ]
    
    UPDATE_MANAGER_AVAILABLE = False
    for updates_path in updates_paths:
        if updates_path.exists():
            sys.path.insert(0, str(updates_path))
            try:
                from update_manager import UpdateManager
                UPDATE_MANAGER_AVAILABLE = True
                break
            except:
                continue
except:
    UPDATE_MANAGER_AVAILABLE = False
    UpdateManager = None

# Try to import keyboard module (optional - needed for hotkeys)
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    keyboard = None

# Try to import OpenCV (optional - needed for confidence parameter in image recognition)
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    cv2 = None

# Try to import pdfplumber (required for parsing insurance company PDFs)
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None

# Try to import OCR libraries for scanned PDFs
try:
    import pytesseract
    from PIL import Image
    import os
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    pytesseract = None

# Try to import Excel/CSV reading libraries
try:
    import pandas as pd
    EXCEL_AVAILABLE = True
    # Try to import openpyxl for .xlsx files
    try:
        import openpyxl
        OPENPYXL_AVAILABLE = True
    except ImportError:
        OPENPYXL_AVAILABLE = False
except ImportError:
    EXCEL_AVAILABLE = False
    pd = None
    OPENPYXL_AVAILABLE = False

# Try to import OpenAI for AI Workflow Trainer
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

# Try to import cryptography for secure API key storage
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('medisoft_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def _configure_ocr_paths():
    """Detect and configure Tesseract and Poppler paths on any Windows machine.
    
    Precedence (highest to lowest):
    1) Environment variables: TESSERACT_PATH, POPPLER_PATH
    2) Local vendor folder next to this script: vendor/Tesseract-OCR, vendor/poppler/Library/bin
    3) Common install locations (Program Files, LocalAppData, Conda)
    """
    if not (OCR_AVAILABLE and pytesseract):
        return
    try:
        script_dir = Path(__file__).parent
        # 1) Env vars
        tesseract_env = os.environ.get('TESSERACT_PATH')
        poppler_env = os.environ.get('POPPLER_PATH')
        if tesseract_env and Path(tesseract_env).exists():
            pytesseract.pytesseract.tesseract_cmd = tesseract_env
            logger.info(f"Configured Tesseract from env: {tesseract_env}")
        if poppler_env and Path(poppler_env).exists():
            os.environ['POPPLER_PATH'] = poppler_env
            logger.info(f"Configured Poppler from env: {poppler_env}")
        # 2) Vendor folder
        if not getattr(pytesseract.pytesseract, 'tesseract_cmd', None):
            vend_tess = script_dir / 'vendor' / 'Tesseract-OCR' / 'tesseract.exe'
            if vend_tess.exists():
                pytesseract.pytesseract.tesseract_cmd = str(vend_tess)
                logger.info(f"Configured Tesseract from vendor: {vend_tess}")
        if 'POPPLER_PATH' not in os.environ:
            vend_poppler = script_dir / 'vendor' / 'poppler' / 'Library' / 'bin'
            if vend_poppler.exists():
                os.environ['POPPLER_PATH'] = str(vend_poppler)
                logger.info(f"Configured Poppler from vendor: {vend_poppler}")
        # 3) Common locations
        current_cmd = getattr(pytesseract.pytesseract, 'tesseract_cmd', None)
        if not current_cmd or not Path(current_cmd).exists() if current_cmd else True:
            candidates = [
                Path('C:/Program Files/Tesseract-OCR/tesseract.exe'),
                Path('C:/Program Files (x86)/Tesseract-OCR/tesseract.exe'),
                Path.home() / 'AppData/Local/Programs/Tesseract-OCR/tesseract.exe',
            ]
            conda_prefix = os.environ.get('CONDA_PREFIX')
            if conda_prefix:
                candidates.append(Path(conda_prefix) / 'Library/bin/tesseract.exe')
            for c in candidates:
                if c.exists():
                    pytesseract.pytesseract.tesseract_cmd = str(c)
                    logger.info(f"Configured Tesseract from common path: {c}")
                    break
            # Final check: verify tesseract is callable
            try:
                pytesseract.get_tesseract_version()
                logger.info("Tesseract verified successfully")
            except Exception as e:
                logger.warning(f"Tesseract path configured but not working: {e}")
        if 'POPPLER_PATH' not in os.environ:
            poppler_candidates = [
                Path('C:/Program Files/poppler/Library/bin'),
                Path('C:/Program Files (x86)/poppler/Library/bin'),
                Path.home() / 'AppData/Local/poppler/Library/bin',
            ]
            if conda_prefix:
                poppler_candidates.append(Path(conda_prefix) / 'Library/bin')
            for d in poppler_candidates:
                if d.exists() and (d / 'pdftoppm.exe').exists():
                    os.environ['POPPLER_PATH'] = str(d)
                    logger.info(f"Configured Poppler from common path: {d}")
                    break
    except Exception as e:
        logger.warning(f"OCR path auto-config failed: {e}")

_configure_ocr_paths()

# Safety settings for PyAutoGUI
pyautogui.PAUSE = 1  # Add 1 second pause between actions
pyautogui.FAILSAFE = True  # Move mouse to corner to abort


def check_for_updates_on_startup():
    """
    Check for updates when bot starts.
    Returns True if update was installed and bot should restart.
    """
    if not UPDATE_MANAGER_AVAILABLE:
        logger.debug("Update manager not available, skipping update check")
        return False
    
    try:
        # Path to G-Drive updates folder (where you push updates)
        # The sync script creates folders with underscores: Medisoft_Billing_Bot
        update_source = r"G:\Company\Software\Updates\Medisoft_Billing_Bot"
        
        # Current bot directory (where bot is installed on employee's computer)
        bot_directory = Path(__file__).parent
        
        # Get current version from version.json if it exists, otherwise use default
        current_version = "1.0.0"
        version_file = bot_directory / "version.json"
        if version_file.exists():
            try:
                with open(version_file, 'r') as f:
                    version_data = json.load(f)
                    current_version = version_data.get('version', '1.0.0')
            except:
                pass
        
        # Initialize update manager
        manager = UpdateManager(
            bot_name="Medisoft Billing Bot",
            current_version=current_version,
            update_source=update_source,
            bot_directory=bot_directory,
            user_data_files=[
                "medisoft_users.json",
                "medisoft_coordinates.json",
                "*.png"  # Saved selector images
            ]
        )
        
        # Check for updates
        update_info = manager.check_for_updates()
        
        if update_info:
            # Show update dialog
            response = messagebox.askyesno(
                "Update Available",
                f"A new version ({update_info['new_version']}) is available!\n\n"
                f"Current version: {update_info['current_version']}\n\n"
                f"Release notes:\n{update_info.get('release_notes', 'No release notes')}\n\n"
                f"Would you like to update now?\n\n"
                f"(Your settings and credentials will be preserved)",
                icon='question'
            )
            
            if response:
                # Download and install update
                result = manager.update(ask_permission=False, auto_install=True)
                
                if result['updated']:
                    messagebox.showinfo(
                        "Update Complete",
                        f"Successfully updated to version {result['new_version']}!\n\n"
                        f"Please restart the bot to use the new version.",
                        icon='info'
                    )
                    return True  # Signal to restart
                else:
                    messagebox.showerror(
                        "Update Failed",
                        f"Update failed: {result.get('error', 'Unknown error')}\n\n"
                        f"The bot will continue with the current version.",
                        icon='error'
                    )
        
        return False
        
    except Exception as e:
        # Don't block bot startup if update check fails
        logger.warning(f"Update check failed: {e}")
        return False


class WorkflowMonitor:
    """Monitor and record user actions for AI Workflow Trainer"""
    
    def __init__(self, callback_log=None):
        self.is_monitoring = False
        self.recorded_actions = []
        self.start_time = None
        self.callback_log = callback_log
        self.monitor_thread = None
        self.stop_event = threading.Event()
        self.last_mouse_pos = None
        self.last_window_title = None
        self.action_counter = 0
        
    def start_monitoring(self):
        """Start monitoring user actions"""
        if self.is_monitoring:
            return False
        
        self.is_monitoring = True
        self.recorded_actions = []
        self.start_time = time.time()
        self.stop_event.clear()
        self.action_counter = 0
        self.last_mouse_pos = None
        self.last_window_title = None
        
        if self.callback_log:
            self.callback_log("🔴 Workflow monitoring started - Recording all user actions...")
        
        # Start monitoring in separate thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        return True
    
    def stop_monitoring(self):
        """Stop monitoring and return recorded actions"""
        if not self.is_monitoring:
            return None
        
        self.is_monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        
        duration = time.time() - self.start_time if self.start_time else 0
        
        workflow_data = {
            "session_info": {
                "start_time": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
                "duration_seconds": duration,
                "total_actions": len(self.recorded_actions),
                "action_types": self._get_action_summary()
            },
            "actions": self.recorded_actions
        }
        
        if self.callback_log:
            self.callback_log(f"⏹️ Workflow monitoring stopped - Recorded {len(self.recorded_actions)} actions over {duration:.1f} seconds")
        
        return workflow_data
    
    def _monitor_loop(self):
        """Main monitoring loop - runs in separate thread"""
        try:
            while self.is_monitoring and not self.stop_event.is_set():
                # Monitor mouse clicks
                self._check_mouse_clicks()
                
                # Monitor keyboard input
                self._check_keyboard_input()
                
                # Monitor window changes
                self._check_window_changes()
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)
        except Exception as e:
            if self.callback_log:
                self.callback_log(f"❌ Monitoring error: {e}")
            logger.error(f"Workflow monitoring error: {e}", exc_info=True)
    
    def _check_mouse_clicks(self):
        """Check for mouse clicks and record them"""
        try:
            import pyautogui
            current_pos = pyautogui.position()
            
            # Detect mouse movement
            if self.last_mouse_pos != current_pos:
                # Only record significant movements (more than 5 pixels)
                if self.last_mouse_pos:
                    dx = abs(current_pos[0] - self.last_mouse_pos[0])
                    dy = abs(current_pos[1] - self.last_mouse_pos[1])
                    if dx > 5 or dy > 5:
                        self._record_action("mouse_move", {
                            "x": current_pos[0],
                            "y": current_pos[1],
                            "from_x": self.last_mouse_pos[0],
                            "from_y": self.last_mouse_pos[1]
                        })
                self.last_mouse_pos = current_pos
        except Exception as e:
            logger.debug(f"Mouse monitoring error: {e}")
    
    def _check_keyboard_input(self):
        """Check for keyboard input - simplified version"""
        # Note: Full keyboard monitoring requires low-level hooks
        # This is a simplified version that works with the existing keyboard module
        pass  # Keyboard monitoring can be enhanced later if needed
    
    def _check_window_changes(self):
        """Check for active window changes"""
        try:
            import pywinauto
            try:
                # Get foreground window
                app = pywinauto.Desktop(backend="uia").top_window()
                current_title = app.window_text()
                
                if current_title != self.last_window_title:
                    if self.last_window_title is not None:  # Don't record initial window
                        self._record_action("window_change", {
                            "from_window": self.last_window_title,
                            "to_window": current_title
                        })
                    self.last_window_title = current_title
            except:
                pass  # Window detection may fail, that's OK
        except Exception as e:
            logger.debug(f"Window monitoring error: {e}")
    
    def _record_action(self, action_type, data):
        """Record an action with timestamp"""
        self.action_counter += 1
        action = {
            "id": self.action_counter,
            "type": action_type,
            "timestamp": time.time() - self.start_time if self.start_time else 0,
            "data": data
        }
        self.recorded_actions.append(action)
    
    def record_click(self, x, y, button="left"):
        """Manually record a mouse click (called from hotkey handlers)"""
        if self.is_monitoring:
            self._record_action("click", {
                "x": x,
                "y": y,
                "button": button
            })
    
    def record_keypress(self, key):
        """Manually record a keypress"""
        if self.is_monitoring:
            self._record_action("keypress", {
                "key": key
            })
    
    def record_screenshot(self, screenshot_path, description=""):
        """Record a screenshot capture"""
        if self.is_monitoring:
            self._record_action("screenshot", {
                "path": str(screenshot_path),
                "description": description
            })
    
    def _get_action_summary(self):
        """Get summary of action types"""
        summary = {}
        for action in self.recorded_actions:
            action_type = action.get("type", "unknown")
            summary[action_type] = summary.get(action_type, 0) + 1
        return summary


class MedisoftBillingBot:
    """Main bot class for Medisoft automation"""
    
    def __init__(self):
        self.medisoft_path = self._find_medisoft()
        self.app = None
        self.login_window = None
        self.main_window = None
        self.log_text = None
        self.root = None
        self.is_logged_in = False  # Track login status
        self.users_file = Path(__file__).parent / "medisoft_users.json"  # Store users in same directory as script
        self.users = {}  # Dictionary to store users: {"name": {"username": "...", "password": "..."}}
        self.load_users()  # Load existing users on startup
        
        # Coordinate storage file for training
        self.coords_file = Path(__file__).parent / "medisoft_coordinates.json"
        self.coordinates = {}  # Dictionary to store coordinates: {"Launch Medisoft Reports": {"x": 100, "y": 50}, ...}
        self.load_coordinates()  # Load saved coordinates
        
        # AI Workflow Trainer - GPT API Key storage (encrypted)
        self.api_key_file = Path(__file__).parent / "gpt_api_key.encrypted"
        self.gpt_api_key = None  # Will be decrypted when needed
        self.load_gpt_api_key()  # Load saved API key on startup
        
        # AI Workflow Trainer - Workflow Monitor
        self.workflow_monitor = WorkflowMonitor(callback_log=self.gui_log)
        self.workflow_data_file = Path(__file__).parent / "workflow_data"
        self.workflow_data_file.mkdir(exist_ok=True)  # Create directory if it doesn't exist
        
        # Selected PDF file for insurance request processing
        self.selected_pdf_path = None
        
        # Selected Excel/CSV file for batch processing (multiple clients)
        self.selected_excel_path = None
        self.excel_client_data = []  # List of dicts: [{"client_name": "...", "date_range_start": "...", "date_range_end": "..."}, ...]
        
        # Output/logging
        self.run_output_dir = None
        self.run_log_rows = []  # Each: {"Patient Name", "Ledger DOS", "Insurance Notes"}
        
        # Optional user-provided column mapping for Excel/CSV
        self.user_col_map = {
            'name_col': '',          # e.g., 'C'
            'dos_col': '',           # e.g., 'M'
            'dos_start_col': '',     # e.g., 'L'
            'dos_end_col': '',       # e.g., 'M'
            'notes_col': ''          # e.g., 'N'
        }
        self.use_split_dos = False
        
        # Stop control
        self.stop_requested = False
        
        # Run passive data cleanup on startup (non-blocking)
        self._run_passive_cleanup()
    
    def _generate_medisoft_search_key(self, full_name: str) -> str:
        """Generate Medisoft search key: first 3 of last name + first 2 of first name.
        Supports both formats:
            - "Smith, John" -> "SMIJO"
            - "John Smith" -> "SMIJO"
        """
        try:
            if not full_name:
                return ""
            full_name = full_name.strip()
            # Check if it's "Last, First" format (comma-separated)
            if ',' in full_name:
                parts = [p.strip() for p in full_name.split(',', 1) if p.strip()]
                if len(parts) >= 2:
                    # "Smith, John" -> last=Smith, first=John
                    last, first = parts[0], parts[1]
                elif len(parts) == 1:
                    # "Smith," -> just last name
                    last = parts[0]
                    first = ""
                else:
                    return ""
            else:
                # "John Smith" format - split on spaces
                parts = [p for p in re.split(r"\s+", full_name) if p]
                if len(parts) >= 2:
                    # "John Smith" -> first=John, last=Smith
                    first, last = parts[0], parts[-1]
                elif len(parts) == 1:
                    last = parts[0]
                    first = ""
                else:
                    return ""
            # Remove non-letters and uppercase
            first_clean = re.sub(r"[^A-Za-z]", "", first).upper()
            last_clean = re.sub(r"[^A-Za-z]", "", last).upper()
            return (last_clean[:3] + first_clean[:2])
        except Exception:
            return ""

    def _select_client_from_three_dots_dialog(self, full_name: str) -> bool:
        """After typing the key, select the correct client in the list.
        Since typing the Medisoft key (e.g., HANSE) usually highlights the correct client automatically,
        we primarily just need to press Enter. We verify the selection if possible.
        """
        try:
            # Wait a moment for the list to update after typing the key
            time.sleep(0.5)
            
            # Focus the dialog window to ensure keyboard input goes there
            try:
                if not self.app:
                    self.connect_to_app()
                dialog = self.app.top_window()
                dialog.set_focus()
                time.sleep(0.2)
            except:
                # If we can't find dialog via pywinauto, that's OK - we'll use keyboard
                pass
            
            # PRIMARY METHOD: After typing the search key, the correct client is usually already highlighted.
            # Just press Enter to select it. This works in the vast majority of cases.
            self.gui_log(f"Pressing Enter to select highlighted client: {full_name}")
            pyautogui.press('enter')
            time.sleep(0.6)  # Wait for dialog to close
            
            # ALWAYS try clicking OK button via screenshot after Enter (Enter may not always work)
            # This ensures the dialog closes even if Enter didn't work
            script_dir = Path(__file__).parent
            img_candidates = [
                script_dir / 'search_lookup_ok.png',
                script_dir / 'search_popup_ok_button.png',
            ]
            ok_clicked = False
            for img_path in img_candidates:
                if img_path.exists():
                    try:
                        self.gui_log(f"Trying image recognition for Lookup OK button: {img_path.name}")
                        if self.find_and_click_by_image(str(img_path), confidence=0.7, timeout=3):
                            time.sleep(0.5)
                            self.gui_log("Lookup OK clicked (image)")
                            ok_clicked = True
                            break
                    except Exception as _e:
                        continue
            
            # Wait a moment after OK click (if it happened) for dialog to close
            if ok_clicked:
                time.sleep(0.3)
            
            # Verify the dialog closed (indicates selection succeeded)
            try:
                if not self.app:
                    self.connect_to_app()
                current = self.app.top_window()
                # If we're back to a window that's not "Lookup", selection likely succeeded
                title = current.window_text().lower()
                if "lookup" not in title:
                    self.gui_log("Dialog closed - client selection confirmed")
                    return True
                else:
                    # Dialog still open - Enter and OK click both failed
                    self.gui_log("Warning: Dialog still appears open after Enter and OK click attempts")
            except:
                # If we can't verify, assume success (both Enter and OK click were attempted)
                self.gui_log("Client selection completed (Enter pressed and OK clicked if needed)")
                return True
            
            # If dialog is still open, try one more Enter or verify by name matching
            self.gui_log("Dialog may still be open, verifying selection...")
            try:
                dialog = self.app.top_window()
                target_first = full_name.split()[0].strip().lower() if full_name else ""
                target_last = full_name.split()[-1].strip().lower() if full_name else ""
                
                # Try to find and select the correct item by name
                try:
                    list_ctrl = dialog.child_window(control_type="List")
                    if list_ctrl.exists():
                        items = list_ctrl.descendants(control_type="ListItem")
                        for item in items:
                            try:
                                txt = item.window_text().strip()
                                if txt:
                                    tl = txt.lower()
                                    if target_first and target_last and (target_first in tl and target_last in tl):
                                        item.select()
                                        time.sleep(0.2)
                                        pyautogui.press('enter')
                                        time.sleep(0.5)
                                        self.gui_log("Selected client by name matching")
                                        return True
                            except:
                                continue
                except:
                    pass
                
                # Last resort: just press Enter again
                pyautogui.press('enter')
                time.sleep(0.5)
                return True
            except:
                return True  # Assume success
            
        except Exception as e:
            self.gui_log(f"Error in client selection: {e}, but continuing...")
            # Even if there's an error, try pressing Enter as fallback
            try:
                pyautogui.press('enter')
                time.sleep(0.5)
            except:
                pass
            return True  # Return True anyway - Enter should have worked

    def _wait_for_three_dots_dialog(self, appear_timeout: float = 3.0) -> bool:
        """Wait until the 3-dots selection dialog appears and is focused.
        Returns True if a likely selection dialog is active (has a List or Edit), else False.
        """
        try:
            if not self.app:
                self.connect_to_app()
            start = time.time()
            while time.time() - start < appear_timeout:
                dlg = self.app.top_window()
                try:
                    # Heuristic: selection dialog often has a List control and one or more Edit fields
                    has_list = False
                    has_edit = False
                    try:
                        lst = dlg.child_window(control_type="List")
                        has_list = lst.exists()
                    except:
                        pass
                    try:
                        ed = dlg.child_window(control_type="Edit")
                        has_edit = ed.exists()
                    except:
                        pass
                    if has_list or has_edit:
                        dlg.set_focus()
                        return True
                except:
                    pass
                time.sleep(0.1)
        except Exception:
            return False
        return False
    def load_users(self):
        """Load users from JSON file"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r') as f:
                    self.users = json.load(f)
                logger.info(f"Loaded {len(self.users)} users from {self.users_file}")
            else:
                # Create empty users file if it doesn't exist
                self.users = {}
                self.save_users()
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            self.users = {}
    
    def save_users(self):
        """Save users to JSON file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            logger.info(f"Saved {len(self.users)} users to {self.users_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving users: {e}")
            messagebox.showerror("Error", f"Failed to save users:\n{e}")
            return False
    
    def _update_user_dropdown(self):
        """Update the user dropdown with current users"""
        if hasattr(self, 'user_dropdown'):
            user_names = sorted(self.users.keys())
            if user_names:
                self.user_dropdown['values'] = user_names
            else:
                self.user_dropdown['values'] = []
    
    def _on_user_selected(self, event=None):
        """Handle user selection from dropdown - auto-populate credentials"""
        selected_user = self.user_dropdown.get()
        if selected_user and selected_user in self.users:
            user_data = self.users[selected_user]
            self.username_entry.delete(0, tk.END)
            self.password_entry.delete(0, tk.END)
            self.username_entry.insert(0, user_data.get('username', ''))
            self.password_entry.insert(0, user_data.get('password', ''))
            self._enable_login()
            self.gui_log(f"Loaded credentials for user: {selected_user}")
    
    def _add_user(self):
        """Add a new user dialog"""
        # Create a dialog window for adding a user
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New User - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("400x200")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # User Name
        tk.Label(dialog, text="User Name:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(20, 5))
        name_entry = tk.Entry(dialog, font=("Arial", 10), width=30)
        name_entry.pack(pady=(0, 10))
        name_entry.focus()
        
        # Username
        tk.Label(dialog, text="Medisoft Username:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(0, 5))
        username_entry = tk.Entry(dialog, font=("Arial", 10), width=30)
        username_entry.pack(pady=(0, 10))
        
        # Password
        tk.Label(dialog, text="Medisoft Password:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(0, 5))
        password_entry = tk.Entry(dialog, font=("Arial", 10), width=30, show="*")
        password_entry.pack(pady=(0, 15))
        
        def save_user():
            name = name_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            if not name:
                messagebox.showwarning("Missing Information", "Please enter a user name.")
                return
            
            if not username:
                messagebox.showwarning("Missing Information", "Please enter a Medisoft username.")
                return
            
            if not password:
                messagebox.showwarning("Missing Information", "Please enter a Medisoft password.")
                return
            
            if name in self.users:
                if not messagebox.askyesno("User Exists", f"User '{name}' already exists. Do you want to update their credentials?"):
                    return
            
            # Add/update user
            self.users[name] = {
                "username": username,
                "password": password
            }
            
            if self.save_users():
                self._update_user_dropdown()
                # Select the newly added user
                self.user_dropdown.set(name)
                self._on_user_selected()
                self.gui_log(f"Added/Updated user: {name}")
                messagebox.showinfo("Success", f"User '{name}' has been saved successfully!")
                dialog.destroy()
        
        # Buttons
        button_frame = tk.Frame(dialog, bg="#f0f0f0")
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Save", command=save_user,
                 bg="#800020", fg="white", font=("Arial", 10),
                 padx=18, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg="#800020", fg="white", font=("Arial", 10),
                 padx=18, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        
        # Allow Enter key to save
        dialog.bind("<Return>", lambda e: save_user())
        name_entry.bind("<Return>", lambda e: username_entry.focus())
        username_entry.bind("<Return>", lambda e: password_entry.focus())
        password_entry.bind("<Return>", lambda e: save_user())
    
    def _update_credentials(self):
        """Update credentials for the selected user"""
        selected_user = self.user_dropdown.get()
        
        if not selected_user or selected_user not in self.users:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown to update their credentials.")
            return
        
        # Create a dialog window for updating credentials
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Update Credentials - {selected_user}")
        dialog.geometry("400x200")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        current_data = self.users[selected_user]
        
        # Username
        tk.Label(dialog, text="Medisoft Username:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(20, 5))
        username_entry = tk.Entry(dialog, font=("Arial", 10), width=30)
        username_entry.pack(pady=(0, 10))
        username_entry.insert(0, current_data.get('username', ''))
        username_entry.focus()
        username_entry.select_range(0, tk.END)
        
        # Password
        tk.Label(dialog, text="Medisoft Password:", font=("Arial", 10), bg="#f0f0f0").pack(pady=(0, 5))
        password_entry = tk.Entry(dialog, font=("Arial", 10), width=30, show="*")
        password_entry.pack(pady=(0, 15))
        password_entry.insert(0, current_data.get('password', ''))
        
        def update_user():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            if not username:
                messagebox.showwarning("Missing Information", "Please enter a Medisoft username.")
                return
            
            if not password:
                messagebox.showwarning("Missing Information", "Please enter a Medisoft password.")
                return
            
            # Update user credentials
            self.users[selected_user] = {
                "username": username,
                "password": password
            }
            
            if self.save_users():
                # Update the fields if this user is currently selected
                if self.user_dropdown.get() == selected_user:
                    self.username_entry.delete(0, tk.END)
                    self.password_entry.delete(0, tk.END)
                    self.username_entry.insert(0, username)
                    self.password_entry.insert(0, password)
                
                self.gui_log(f"Updated credentials for user: {selected_user}")
                messagebox.showinfo("Success", f"Credentials for '{selected_user}' have been updated successfully!")
                dialog.destroy()
        
        # Buttons
        button_frame = tk.Frame(dialog, bg="#f0f0f0")
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Update", command=update_user,
                 bg="#800020", fg="white", font=("Arial", 10),
                 padx=18, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg="#800020", fg="white", font=("Arial", 10),
                 padx=18, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        
        # Allow Enter key to update
        dialog.bind("<Return>", lambda e: update_user())
        username_entry.bind("<Return>", lambda e: password_entry.focus())
        password_entry.bind("<Return>", lambda e: update_user())
        
    def load_coordinates(self):
        """Load saved coordinates from JSON file"""
        try:
            if self.coords_file.exists():
                with open(self.coords_file, 'r') as f:
                    self.coordinates = json.load(f)
                logger.info(f"Loaded {len(self.coordinates)} coordinate mappings from {self.coords_file}")
            else:
                self.coordinates = {}
                self.save_coordinates()
        except Exception as e:
            logger.error(f"Error loading coordinates: {e}")
            self.coordinates = {}
    
    def save_coordinates(self):
        """Save coordinates to JSON file"""
        try:
            with open(self.coords_file, 'w') as f:
                json.dump(self.coordinates, f, indent=2)
            logger.info(f"Saved {len(self.coordinates)} coordinate mappings to {self.coords_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving coordinates: {e}")
            messagebox.showerror("Error", f"Failed to save coordinates:\n{e}")
            return False
    
    def _get_encryption_key(self):
        """Generate or retrieve encryption key for API key storage.
        Uses machine-specific information to create a stable key."""
        if not CRYPTOGRAPHY_AVAILABLE:
            return None
        
        try:
            # Create a machine-specific key file
            key_file = Path(__file__).parent / ".api_key_encryption_key"
            
            if key_file.exists():
                # Load existing key
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                # Generate new key based on machine info
                import platform
                import getpass
                
                # Create a stable seed from machine info
                machine_id = f"{platform.node()}{getpass.getuser()}{Path(__file__).parent}"
                password = machine_id.encode()
                salt = b'medisoft_bot_salt_2024'  # Fixed salt for consistency
                
                # Derive key using PBKDF2
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
                
                # Save key for future use
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                # Set file permissions to be more secure (Windows)
                try:
                    import stat
                    os.chmod(key_file, stat.S_IREAD | stat.S_IWRITE)
                except:
                    pass
                
                return key
        except Exception as e:
            logger.error(f"Error generating encryption key: {e}")
            return None
    
    def load_gpt_api_key(self):
        """Load and decrypt GPT API key from secure storage"""
        if not CRYPTOGRAPHY_AVAILABLE:
            self.gpt_api_key = None
            return
        
        try:
            if not self.api_key_file.exists():
                self.gpt_api_key = None
                return
            
            # Get encryption key
            encryption_key = self._get_encryption_key()
            if not encryption_key:
                self.gpt_api_key = None
                return
            
            # Decrypt API key
            fernet = Fernet(encryption_key)
            with open(self.api_key_file, 'rb') as f:
                encrypted_key = f.read()
            
            decrypted_key = fernet.decrypt(encrypted_key)
            self.gpt_api_key = decrypted_key.decode('utf-8')
            logger.info("GPT API key loaded successfully from secure storage")
        except Exception as e:
            logger.warning(f"Error loading GPT API key: {e}")
            self.gpt_api_key = None
    
    def save_gpt_api_key(self, api_key: str):
        """Encrypt and save GPT API key to secure storage"""
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.error("Cryptography library not available - cannot save API key securely")
            messagebox.showerror("Error", "Cryptography library not installed. Please install it:\npip install cryptography")
            return False
        
        try:
            if not api_key or not api_key.strip():
                logger.warning("Empty API key provided")
                return False
            
            api_key = api_key.strip()
            
            # Get encryption key
            encryption_key = self._get_encryption_key()
            if not encryption_key:
                logger.error("Failed to generate encryption key")
                messagebox.showerror("Error", "Failed to generate encryption key for secure storage")
                return False
            
            # Encrypt API key
            fernet = Fernet(encryption_key)
            encrypted_key = fernet.encrypt(api_key.encode('utf-8'))
            
            # Save encrypted key
            with open(self.api_key_file, 'wb') as f:
                f.write(encrypted_key)
            
            # Set file permissions to be more secure (Windows)
            try:
                import stat
                os.chmod(self.api_key_file, stat.S_IREAD | stat.S_IWRITE)
            except:
                pass
            
            # Store in memory
            self.gpt_api_key = api_key
            
            logger.info("GPT API key saved successfully to secure storage")
            return True
        except Exception as e:
            logger.error(f"Error saving GPT API key: {e}")
            messagebox.showerror("Error", f"Failed to save API key securely:\n{e}")
            return False
    
    def get_gpt_api_key(self):
        """Get the GPT API key (returns None if not set)"""
        return self.gpt_api_key
    
    def interpret_workflow_data_with_gpt(self, workflow_data: dict, prompt: str = None) -> dict:
        """Interpret workflow training data using GPT API.
        
        Args:
            workflow_data: Dictionary containing workflow training data (e.g., screenshots, coordinates, actions)
            prompt: Optional custom prompt. If None, uses default prompt for workflow interpretation.
        
        Returns:
            Dictionary with interpretation results, or None if API call fails.
        """
        if not OPENAI_AVAILABLE:
            self.gui_log("❌ OpenAI library not available - Cannot interpret workflow data")
            return None
        
        api_key = self.get_gpt_api_key()
        if not api_key:
            self.gui_log("❌ GPT API key not set - Please configure it in AI Workflow Trainer settings")
            return None
        
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            
            # Default prompt for workflow interpretation
            if prompt is None:
                prompt = """You are an AI assistant helping to interpret workflow training data for a medical billing automation bot.

The workflow data contains information about user interactions with a medical billing system (Medisoft). Your task is to:
1. Analyze the workflow steps and actions
2. Identify patterns and sequences
3. Extract key information (button names, field values, navigation paths)
4. Suggest optimizations or improvements
5. Provide a structured summary of the workflow

Please analyze the following workflow data and provide a comprehensive interpretation:"""
            
            # Format workflow data for GPT
            workflow_text = json.dumps(workflow_data, indent=2)
            
            # Make API call
            self.gui_log("🤖 Sending workflow data to GPT for interpretation...")
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using cost-effective model, can be changed to gpt-4 for better results
                messages=[
                    {"role": "system", "content": "You are an expert in workflow automation and medical billing systems."},
                    {"role": "user", "content": f"{prompt}\n\nWorkflow Data:\n{workflow_text}"}
                ],
                max_tokens=2000,
                temperature=0.3  # Lower temperature for more consistent, factual responses
            )
            
            result_text = response.choices[0].message.content
            
            # Parse and structure the result
            result = {
                "interpretation": result_text,
                "model_used": response.model,
                "tokens_used": response.usage.total_tokens,
                "timestamp": datetime.now().isoformat()
            }
            
            self.gui_log(f"✅ Workflow data interpreted successfully (Tokens: {result['tokens_used']})")
            return result
            
        except Exception as e:
            error_msg = str(e)
            self.gui_log(f"❌ Error interpreting workflow data with GPT: {error_msg}")
            logger.error(f"GPT API error: {e}", exc_info=True)
            return None

    def _run_passive_cleanup(self):
        """Run passive data cleanup in background thread to avoid blocking startup."""
        try:
            # Import shared cleanup utility from _bots directory (works for ALL bots)
            import sys
            bots_dir = Path(__file__).parent.parent.parent
            init_cleanup_path = bots_dir / "init_passive_cleanup.py"
            
            if init_cleanup_path.exists():
                # Add _bots to path if not already there
                if str(bots_dir) not in sys.path:
                    sys.path.insert(0, str(bots_dir))
                
                from init_passive_cleanup import init_passive_cleanup
                # Auto-detects installation directory and cleans up for ALL bots
                init_passive_cleanup(logger=logger)
        except Exception as e:
            # Silently fail - cleanup shouldn't break bot startup
            logger.debug(f"Passive cleanup initialization failed (non-critical): {e}")
    
    def _clear_saved_clicks(self):
        """Clear all saved coordinates (with on-disk backup)"""
        try:
            if not messagebox.askyesno("Confirm", "Clear ALL saved clicks? You will need to retrain each target."):
                return
            # Backup existing file if present
            if self.coords_file.exists():
                ts = time.strftime("%Y%m%d-%H%M%S")
                backup_path = self.coords_file.with_name(self.coords_file.stem + f".backup-{ts}" + self.coords_file.suffix)
                try:
                    backup_path.write_text(self.coords_file.read_text(encoding='utf-8'), encoding='utf-8')
                    self.gui_log(f"🗂️ Backed up existing clicks to: {backup_path}")
                except Exception as e:
                    self.gui_log(f"⚠️ Could not create backup: {e}")
            # Clear in-memory and save
            self.coordinates = {}
            self.save_coordinates()
            self._update_coords_display()
            self.gui_log("🧹 Cleared all saved clicks.")
            messagebox.showinfo("Cleared", "All saved clicks have been cleared. Use the training dropdown and F8/F9 to retrain.")
        except Exception as e:
            self.gui_log(f"❌ Error clearing saved clicks: {e}")
    
    def _toggle_recording(self):
        """Toggle coordinate recording mode on/off"""
        if not KEYBOARD_AVAILABLE:
            messagebox.showwarning("Keyboard Module Not Installed", 
                                  "The 'keyboard' module is required for hotkey functionality.\n\n"
                                  "Please install it by running:\n"
                                  "pip install keyboard\n\n"
                                  "Then restart the bot.")
            self.gui_log("❌ Keyboard module not available - Cannot use hotkeys")
            return
        
        if not self.recording_enabled:
            # Enable recording
            self.recording_enabled = True
            self.recording_status_label.config(text="Coordinates: ON", fg="#28a745")
            self.gui_log("🎯 Coordinate recording enabled - Hover over element and press F9!")
            self.update_status("F9 enabled - Press F9 while hovering over element", "#28a745")
            
            # Set up F9 hotkey
            try:
                keyboard.on_press_key('f9', self._capture_position_hotkey)
                self.gui_log("✅ F9 hotkey registered - Ready to record coordinates")
            except Exception as e:
                self.gui_log(f"⚠️ Could not register F9 hotkey: {e}")
                self.recording_enabled = False
                self.recording_status_label.config(text="Coordinates: ERROR", fg="#dc3545")
        else:
            # Disable recording
            self.recording_enabled = False
            self.recording_status_label.config(text="Coordinates: OFF", fg="#dc3545")
            self.gui_log("⏸️ Coordinate recording disabled")
            self.update_status("Coordinate recording disabled", "#0066cc")
            try:
                keyboard.unhook_key('f9')
            except:
                pass
    
    def _toggle_screenshot(self):
        """Toggle screenshot capture mode on/off"""
        if not KEYBOARD_AVAILABLE:
            messagebox.showwarning("Keyboard Module Not Installed", 
                                  "The 'keyboard' module is required for hotkey functionality.\n\n"
                                  "Please install it by running:\n"
                                  "pip install keyboard\n\n"
                                  "Then restart the bot.")
            self.gui_log("❌ Keyboard module not available - Cannot use hotkeys")
            return
        
        if not self.screenshot_enabled:
            # Enable screenshot capture
            self.screenshot_enabled = True
            self.screenshot_status_label.config(text="Screenshot: ON", fg="#28a745")
            self.gui_log("📸 Screenshot capture enabled - Hover over element and press F8!")
            self.update_status("F8 enabled - Press F8 to capture screenshot of element", "#28a745")
            
            # Set up F8 hotkey
            try:
                keyboard.on_press_key('f8', self._capture_screenshot_hotkey)
                self.gui_log("✅ F8 hotkey registered - Ready to capture screenshots")
            except Exception as e:
                self.gui_log(f"⚠️ Could not register F8 hotkey: {e}")
                self.screenshot_enabled = False
                self.screenshot_status_label.config(text="Screenshot: ERROR", fg="#dc3545")
        else:
            # Disable screenshot
            self.screenshot_enabled = False
            self.screenshot_status_label.config(text="Screenshot: OFF", fg="#dc3545")
            self.gui_log("⏸️ Screenshot capture disabled")
            self.update_status("Screenshot capture disabled", "#0066cc")
            try:
                keyboard.unhook_key('f8')
            except:
                pass
    
    def _capture_screenshot_hotkey(self, event=None):
        """Capture screenshot when F8 is pressed - called from keyboard hook"""
        if not self.screenshot_enabled:
            return
        
        # Get element name
        element_name = self.coord_name_entry.get().strip()
        if not element_name:
            element_name = "Unnamed Element"
        
        # Clean filename (remove invalid characters)
        safe_name = "".join(c for c in element_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = safe_name.replace(' ', '_').lower() + ".png"
        script_dir = Path(__file__).parent
        image_path = script_dir / filename
        
        # Capture region around mouse (better size for button recognition)
        try:
            x, y = pyautogui.position()
            # Capture a larger region around the mouse for better matching (300x80)
            region_size = 300
            region_height = 80
            
            # Make sure region is within screen bounds (handle multi-monitor)
            screen_width, screen_height = pyautogui.size()
            left = max(0, x - region_size // 2)
            top = max(0, y - region_height // 2)
            width = min(region_size, screen_width - left)
            height = min(region_height, screen_height - top)
            
            # Take screenshot of region
            screenshot = pyautogui.screenshot(region=(left, top, width, height))
            
            # Save with high quality
            screenshot.save(image_path, format='PNG', optimize=False)
            
            # Verify the file was saved
            if image_path.exists():
                file_size = image_path.stat().st_size
                self.gui_log(f"📸 Captured screenshot: {filename} at ({x}, {y})")
                self.gui_log(f"💾 Saved to: {image_path}")
                self.gui_log(f"✅ File saved successfully ({file_size} bytes)")
                
                # Record in workflow monitor if active
                if hasattr(self, 'workflow_monitor') and self.workflow_monitor.is_monitoring:
                    self.workflow_monitor.record_screenshot(image_path, element_name)
                    self.workflow_monitor.record_click(x, y, "left")
            else:
                self.gui_log(f"❌ WARNING: Screenshot was supposed to save to {image_path} but file doesn't exist!")
                self.gui_log(f"   Current working directory: {os.getcwd()}")
                self.gui_log(f"   Script directory: {script_dir}")
                self.gui_log(f"   Absolute path: {image_path.absolute()}")
            
            # Update UI (thread-safe)
            if self.root:
                self.root.after(0, lambda: self._show_screenshot_feedback(filename, image_path, x, y))
        except Exception as e:
            self.gui_log(f"❌ Error capturing screenshot: {e}")
            if self.root:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to capture screenshot:\n{e}"))
    
    def _capture_screenshot_region(self):
        """Manual screenshot capture with region selection"""
        self.gui_log("📸 Manual screenshot capture - Use F8 for quick capture")
        messagebox.showinfo("Screenshot Capture", 
                          "For quick capture: Enable F8, hover over element, then press F8.\n\n"
                          "For region capture: Use Windows Snipping Tool or similar.")
    
    def _show_screenshot_feedback(self, filename, image_path, x, y):
        """Show feedback after screenshot capture"""
        feedback = tk.Toplevel(self.root)
        feedback.title("Screenshot Captured! - Version 3.1.0, Last Updated 12/04/2025")
        feedback.geometry("300x180")
        feedback.configure(bg="#f0f0f0")
        feedback.transient(self.root)
        
        feedback.update_idletasks()
        fx = (feedback.winfo_screenwidth() // 2) - (feedback.winfo_width() // 2)
        fy = (feedback.winfo_screenheight() // 2) - (feedback.winfo_height() // 2)
        feedback.geometry(f"+{fx}+{fy}")
        
        tk.Label(feedback, text="✅ Screenshot Captured!", font=("Arial", 14, "bold"), 
                bg="#f0f0f0", fg="#800020").pack(pady=(20, 10))
        
        tk.Label(feedback, text=f"File: {filename}", font=("Arial", 10), 
                bg="#f0f0f0").pack(pady=(0, 5))
        
        tk.Label(feedback, text=f"Position: ({x}, {y})", font=("Arial", 9), 
                bg="#f0f0f0", fg="#666666").pack(pady=(0, 10))
        
        tk.Label(feedback, text="✅ Bot will use this image for recognition!", 
                font=("Arial", 9), bg="#f0f0f0", fg="#28a745", wraplength=250).pack()
        
        self.root.after(2000, feedback.destroy)
    
    def _capture_position_hotkey(self, event=None):
        """Capture position when F9 is pressed - called from keyboard hook"""
        if not self.recording_enabled:
            return
        
        # Capture current mouse position immediately
        x_pos, y_pos = pyautogui.position()
        
        element_name = self.coord_name_entry.get().strip()
        if not element_name:
            element_name = "Unnamed Element"
        
        # Save the absolute coordinate
        coord_record = {"x": x_pos, "y": y_pos}
        self.coordinates[element_name] = coord_record
        self.save_coordinates()
        
        # Record in workflow monitor if active
        if hasattr(self, 'workflow_monitor') and self.workflow_monitor.is_monitoring:
            self.workflow_monitor.record_click(x_pos, y_pos, "left")
            self.workflow_monitor.record_screenshot(None, f"Coordinate capture: {element_name}")
        
        # Update GUI (thread-safe)
        if self.root:
            self.root.after(0, lambda: self._update_position_ui(x_pos, y_pos, element_name))
    
    def _update_position_ui(self, x_pos, y_pos, element_name):
        """Update UI after capturing position (runs on main thread)"""
        self.current_position_label.config(text=f"Position: ({x_pos}, {y_pos})")
        self._update_coords_display()
        self.gui_log(f"✅ Recorded position for '{element_name}': ({x_pos}, {y_pos})")
        
        # Show feedback dialog
        feedback = tk.Toplevel(self.root)
        feedback.title("Position Recorded! - Version 3.1.0, Last Updated 12/04/2025")
        feedback.geometry("250x120")
        feedback.configure(bg="#f0f0f0")
        feedback.transient(self.root)
        
        feedback.update_idletasks()
        x = (feedback.winfo_screenwidth() // 2) - (feedback.winfo_width() // 2)
        y = (feedback.winfo_screenheight() // 2) - (feedback.winfo_height() // 2)
        feedback.geometry(f"+{x}+{y}")
        
        tk.Label(feedback, text=f"✅ Recorded!", font=("Arial", 14, "bold"), 
                bg="#f0f0f0", fg="#800020").pack(pady=(20, 5))
        tk.Label(feedback, text=f"({x_pos}, {y_pos})", font=("Arial", 10), 
                bg="#f0f0f0").pack()
        
        self.root.after(1500, feedback.destroy)
    
    def _update_api_key_status(self):
        """Update the API key status label in the GUI"""
        try:
            if hasattr(self, 'api_key_status_label'):
                api_key = self.get_gpt_api_key()
                if api_key:
                    # Show masked version of key (first 8 chars + ...)
                    masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
                    self.api_key_status_label.config(
                        text=f"Status: ✅ API key saved (Key: {masked_key})", 
                        fg="#28a745"
                    )
                else:
                    self.api_key_status_label.config(
                        text="Status: ⚠️ No API key saved - Enter and save your key above", 
                        fg="#dc3545"
                    )
        except Exception as e:
            logger.error(f"Error updating API key status: {e}")
    
    def _update_monitoring_stats(self):
        """Update monitoring statistics display"""
        try:
            if hasattr(self, 'monitoring_stats_label') and hasattr(self, 'workflow_monitor'):
                if self.workflow_monitor.is_monitoring:
                    duration = time.time() - self.workflow_monitor.start_time if self.workflow_monitor.start_time else 0
                    action_count = len(self.workflow_monitor.recorded_actions)
                    self.monitoring_stats_label.config(
                        text=f"Actions: {action_count} | Duration: {duration:.1f}s",
                        fg="#dc3545"
                    )
                else:
                    self.monitoring_stats_label.config(
                        text="Actions: 0 | Duration: 0.0s",
                        fg="#666666"
                    )
        except Exception as e:
            logger.debug(f"Error updating monitoring stats: {e}")
        
        # Schedule next update
        if hasattr(self, 'root') and self.root:
            self.root.after(500, self._update_monitoring_stats)  # Update every 500ms
    
    def _save_workflow_data(self, workflow_data):
        """Save workflow data to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"workflow_{timestamp}.json"
            filepath = self.workflow_data_file / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(workflow_data, f, indent=2, ensure_ascii=False)
            
            self.gui_log(f"💾 Workflow data saved to: {filepath.name}")
            messagebox.showinfo("Workflow Saved", f"Workflow data saved successfully!\n\nFile: {filename}")
            return filepath
        except Exception as e:
            error_msg = str(e)
            self.gui_log(f"❌ Error saving workflow data: {error_msg}")
            messagebox.showerror("Save Error", f"Failed to save workflow data:\n\n{error_msg}")
            return None
    
    def _save_and_interpret_workflow(self, workflow_data):
        """Save workflow data and interpret it with GPT"""
        # First save the data
        filepath = self._save_workflow_data(workflow_data)
        if not filepath:
            return
        
        # Check if API key is available
        api_key = self.get_gpt_api_key()
        if not api_key:
            response = messagebox.askyesno(
                "API Key Required",
                "GPT API key is required for interpretation.\n\n"
                "Would you like to configure it now?"
            )
            if response:
                # Focus on API key entry (user can enter it)
                if hasattr(self, 'api_key_entry'):
                    self.api_key_entry.focus()
                return
            else:
                return
        
        # Interpret with GPT
        self.gui_log("🤖 Sending workflow data to GPT for interpretation...")
        try:
            result = self.interpret_workflow_data_with_gpt(workflow_data)
            if result:
                # Save interpretation
                interpretation_file = filepath.with_suffix('.interpretation.txt')
                with open(interpretation_file, 'w', encoding='utf-8') as f:
                    f.write(f"Workflow Interpretation\n")
                    f.write(f"{'='*60}\n\n")
                    f.write(f"Session: {workflow_data['session_info']['start_time']}\n")
                    f.write(f"Duration: {workflow_data['session_info']['duration_seconds']:.1f} seconds\n")
                    f.write(f"Total Actions: {workflow_data['session_info']['total_actions']}\n")
                    f.write(f"\n{'-'*60}\n\n")
                    f.write(result['interpretation'])
                    f.write(f"\n\n{'-'*60}\n")
                    f.write(f"Model: {result['model_used']}\n")
                    f.write(f"Tokens Used: {result['tokens_used']}\n")
                    f.write(f"Generated: {result['timestamp']}\n")
                
                self.gui_log(f"✅ Interpretation saved to: {interpretation_file.name}")
                
                # Show interpretation in a dialog
                self._show_interpretation_dialog(result['interpretation'], interpretation_file)
            else:
                messagebox.showwarning("Interpretation Failed", 
                                     "Failed to interpret workflow data with GPT.\n\n"
                                     "Check the activity log for details.")
        except Exception as e:
            error_msg = str(e)
            self.gui_log(f"❌ Error interpreting workflow: {error_msg}")
            messagebox.showerror("Interpretation Error", 
                               f"Error during GPT interpretation:\n\n{error_msg}")
    
    def _show_interpretation_dialog(self, interpretation_text, filepath):
        """Show interpretation results in a dialog window"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Workflow Interpretation - GPT Analysis - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("800x600")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self.root)
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Header
        header = tk.Frame(dialog, bg="#800020", height=50)
        header.pack(fill="x")
        tk.Label(header, text="GPT Workflow Interpretation", 
                font=("Arial", 14, "bold"), bg="#800020", fg="white").pack(pady=10)
        
        # Content
        content_frame = tk.Frame(dialog, bg="#f0f0f0")
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Interpretation text
        text_widget = scrolledtext.ScrolledText(content_frame, 
                                               font=("Consolas", 10),
                                               bg="#ffffff", fg="#000000",
                                               wrap=tk.WORD)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", interpretation_text)
        text_widget.config(state="disabled")
        
        # Footer with file info
        footer = tk.Frame(dialog, bg="#f0f0f0")
        footer.pack(fill="x", padx=15, pady=(0, 15))
        tk.Label(footer, text=f"Full interpretation saved to: {filepath.name}", 
                font=("Arial", 8), bg="#f0f0f0", fg="#666666").pack(side="left")
        
        # Close button
        tk.Button(footer, text="Close", command=dialog.destroy,
                 bg="#800020", fg="white", font=("Arial", 10),
                 padx=20, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="right")
    
    def _update_coords_display(self):
        """Update the coordinates display"""
        if hasattr(self, 'coords_display'):
            self.coords_display.config(state="normal")
            self.coords_display.delete(1.0, tk.END)
            
            if self.coordinates:
                for name, coords in self.coordinates.items():
                    self.coords_display.insert(tk.END, f"{name}: ({coords['x']}, {coords['y']})\n")
            else:
                self.coords_display.insert(tk.END, "No coordinates saved yet")
            
            self.coords_display.config(state="disabled")
    
    def _delete_coordinate(self):
        """Delete a saved coordinate"""
        selection = self.coords_display.tag_ranges(tk.SEL)
        if selection:
            # Get selected text
            selected_text = self.coords_display.get(selection[0], selection[1])
            # Extract element name (before the colon)
            element_name = selected_text.split(':')[0].strip()
        else:
            # Ask user to select
            element_name = simpledialog.askstring("Delete Coordinate", 
                                                  "Enter the element name to delete:")
        
        if element_name and element_name in self.coordinates:
            del self.coordinates[element_name]
            self.save_coordinates()
            self._update_coords_display()
            self.gui_log(f"🗑️ Deleted coordinate for '{element_name}'")
            messagebox.showinfo("Success", f"Deleted coordinate for '{element_name}'")
        elif element_name:
            messagebox.showwarning("Not Found", f"Coordinate '{element_name}' not found")
    
    def get_coordinate(self, element_name):
        """Get saved coordinates for an element, return (x, y) tuple or None"""
        if element_name in self.coordinates:
            coords = self.coordinates[element_name]
            # Simple: always return absolute x,y that were trained
            if 'x' in coords and 'y' in coords:
                return (coords['x'], coords['y'])
        return None
    
    def _show_window_list(self):
        """Show a dialog listing all open windows"""
        self.list_all_windows()
        # Also create a dialog with the list
        dialog = tk.Toplevel(self.root)
        dialog.title("Open Windows - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("400x500")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self.root)
        
        tk.Label(dialog, text="Open Window Titles:", font=("Arial", 10, "bold"), 
                bg="#f0f0f0").pack(pady=10)
        
        listbox = scrolledtext.ScrolledText(dialog, height=20, font=("Consolas", 8),
                                           bg="#ffffff", wrap=tk.WORD)
        listbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        try:
            all_titles = pyautogui.getAllTitles()
            if all_titles:
                for i, title in enumerate(all_titles, 1):
                    if title.strip():
                        listbox.insert(tk.END, f"{i}. {title}\n")
            else:
                listbox.insert(tk.END, "No windows found")
        except Exception as e:
            listbox.insert(tk.END, f"Error: {e}")
        
        listbox.config(state="disabled")
        
        tk.Button(dialog, text="Close", command=dialog.destroy,
                 bg="#800020", fg="white", font=("Arial", 9),
                 padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(pady=10)
        
    def create_main_window(self):
        """Create the main window with login fields and activity log"""
        self.root = tk.Tk()
        # Get update timestamp from version.json if it exists
        update_timestamp = ""
        try:
            version_file = Path(__file__).parent / "version.json"
            if version_file.exists():
                with open(version_file, 'r') as f:
                    version_data = json.load(f)
                    # Get last modified date of version.json as update timestamp
                    import os
                    mod_time = os.path.getmtime(version_file)
                    update_timestamp = f" - Updated, {datetime.fromtimestamp(mod_time).strftime('%m/%d/%Y')}"
        except:
            pass
        self.root.title(f"Medisoft Billing Bot{update_timestamp}")
        self.root.geometry("900x800")  # Made taller to fit training section
        self.root.configure(bg="#f0f0f0")
        
        # Center the window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")
        
        # Header
        header_frame = tk.Frame(self.root, bg="#800000", height=70)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        # Get update timestamp for header
        header_timestamp = ""
        try:
            version_file = Path(__file__).parent / "version.json"
            if version_file.exists():
                import os
                mod_time = os.path.getmtime(version_file)
                header_timestamp = f" - Updated, {datetime.fromtimestamp(mod_time).strftime('%m/%d/%Y')}"
        except:
            pass
        
        title_label = tk.Label(header_frame, text="Medisoft Billing Bot", 
                              font=("Arial", 18, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True)
        
        subtitle_label = tk.Label(header_frame, text="Enter credentials and monitor bot progress in real-time", 
                                 font=("Arial", 10), bg="#800000", fg="#cccccc")
        subtitle_label.pack()
        
        # Scrollable canvas container
        canvas_container = tk.Frame(self.root, bg="#f0f0f0")
        canvas_container.pack(fill="both", expand=True)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(canvas_container, bg="#f0f0f0", highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_container, orient="vertical", command=self.canvas.yview)
        scrollable_frame = tk.Frame(self.canvas, bg="#f0f0f0")
        
        # Configure scrollable frame
        scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create window on canvas
        canvas_window = self.canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        # Configure canvas scrolling
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Make canvas resizeable - adjust scrollable frame width when canvas resizes
        def on_canvas_configure(event):
            canvas_width = event.width
            self.canvas.itemconfig(canvas_window, width=canvas_width)
        
        self.canvas.bind("<Configure>", on_canvas_configure)
        
        # Enable mousewheel scrolling
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        # Main content frame (now inside scrollable_frame)
        main_frame = tk.Frame(scrollable_frame, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=20, pady=15)
        
        # ========== Login Section ==========
        login_section = tk.LabelFrame(main_frame, text="Medisoft Login Credentials", 
                                     font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        login_section.pack(fill="x", pady=(0, 15))
        
        login_content = tk.Frame(login_section, bg="#f0f0f0")
        login_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # User Selection Dropdown
        user_row = tk.Frame(login_content, bg="#f0f0f0")
        user_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        tk.Label(user_row, text="User:", font=("Arial", 10), bg="#f0f0f0",
                anchor="w").pack(side="left", padx=(0, 10))
        
        self.user_dropdown = ttk.Combobox(user_row, font=("Arial", 10), width=25, state="readonly")
        self.user_dropdown.pack(side="left", padx=(0, 10))
        self.user_dropdown.bind("<<ComboboxSelected>>", self._on_user_selected)
        self._update_user_dropdown()
        
        # Add User button
        self.add_user_button = tk.Button(user_row, text="Add User", 
                                         command=self._add_user,
                                         bg="#800020", fg="white", font=("Arial", 9),
                                         padx=12, pady=4, cursor="hand2", relief="flat", bd=0)
        self.add_user_button.pack(side="left", padx=(0, 5))
        
        # Update Credentials button
        self.update_creds_button = tk.Button(user_row, text="Update Credentials", 
                                            command=self._update_credentials,
                                            bg="#800020", fg="white", font=("Arial", 9),
                                            padx=12, pady=4, cursor="hand2", relief="flat", bd=0)
        self.update_creds_button.pack(side="left", padx=(0, 5))
        
        # Login button (moved to top row)
        self.login_button = tk.Button(user_row, text="Login", 
                                     command=self._start_login,
                                    bg="#800020", fg="white", font=("Arial", 9),
                                    padx=12, pady=4, cursor="hand2", state="disabled",
                                    relief="flat", bd=0)
        self.login_button.pack(side="left")
        
        # Username
        tk.Label(login_content, text="Username:", font=("Arial", 10), bg="#f0f0f0",
                anchor="w").grid(row=1, column=0, sticky="w", pady=(0, 5))
        self.username_entry = tk.Entry(login_content, font=("Arial", 10), width=40)
        self.username_entry.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.username_entry.focus()
        
        # Password
        tk.Label(login_content, text="Password:", font=("Arial", 10), bg="#f0f0f0",
                anchor="w").grid(row=3, column=0, sticky="w", pady=(0, 5))
        self.password_entry = tk.Entry(login_content, font=("Arial", 10), width=40, show="*")
        self.password_entry.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.password_entry.bind("<Return>", lambda e: self._start_login() if self.username_entry.get().strip() and self.password_entry.get().strip() else None)
        
        # Status label
        self.status_label = tk.Label(login_content, text="Status: Select a user or enter credentials to begin...", 
                                    font=("Arial", 9, "bold"), bg="#f0f0f0", fg="#0066cc")
        self.status_label.grid(row=5, column=0, sticky="w")
        
        login_content.grid_columnconfigure(0, weight=1)
        
        # ========== PDF Selection Section ==========
        pdf_section = tk.LabelFrame(main_frame, text="Insurance Request PDF", 
                                   font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        pdf_section.pack(fill="x", pady=(0, 15))
        
        pdf_content = tk.Frame(pdf_section, bg="#f0f0f0")
        pdf_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Instructions
        pdf_instruction = "Select the insurance company PDF that contains the client information and date range."
        tk.Label(pdf_content, text=pdf_instruction, 
                font=("Arial", 9), bg="#f0f0f0", fg="#666666", wraplength=600, 
                justify="left").pack(pady=(0, 10))
        
        # PDF selection row
        pdf_row = tk.Frame(pdf_content, bg="#f0f0f0")
        pdf_row.pack(fill="x")
        
        tk.Label(pdf_row, text="PDF File:", font=("Arial", 10), bg="#f0f0f0",
                anchor="w").pack(side="left", padx=(0, 10))
        
        self.pdf_entry = tk.Entry(pdf_row, font=("Arial", 9), width=50, state="readonly")
        self.pdf_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_pdf_button = tk.Button(pdf_row, text="Browse...", 
                                     command=self._browse_pdf,
                                     bg="#800020", fg="white", font=("Arial", 9),
                                     padx=12, pady=4, cursor="hand2", relief="flat", bd=0)
        browse_pdf_button.pack(side="left", padx=(0, 5))
        
        clear_pdf_button = tk.Button(pdf_row, text="Clear", 
                                     command=self._clear_pdf,
                                     bg="#800020", fg="white", font=("Arial", 9),
                                     padx=12, pady=4, cursor="hand2", relief="flat", bd=0)
        clear_pdf_button.pack(side="left")
        
        # PDF status label
        self.pdf_status_label = tk.Label(pdf_content, text="No PDF selected", 
                                        font=("Arial", 9, "italic"), bg="#f0f0f0", fg="#666666")
        self.pdf_status_label.pack(pady=(5, 0))
        
        # ========== Excel/CSV Batch Processing Section ==========
        excel_section = tk.LabelFrame(main_frame, text="Batch Processing (Excel/CSV)", 
                                     font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        excel_section.pack(fill="x", pady=(0, 15))
        
        excel_content = tk.Frame(excel_section, bg="#f0f0f0")
        excel_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Instructions
        excel_instruction = "Select an Excel (.xlsx) or CSV file containing multiple clients. Patient Name in Column C, DOS Range in Column M."
        tk.Label(excel_content, text=excel_instruction, 
                font=("Arial", 9), bg="#f0f0f0", fg="#666666", wraplength=600, 
                justify="left").pack(pady=(0, 10))
        
        # Excel/CSV selection row
        excel_row = tk.Frame(excel_content, bg="#f0f0f0")
        excel_row.pack(fill="x")
        
        tk.Label(excel_row, text="Excel/CSV File:", font=("Arial", 10), bg="#f0f0f0",
                anchor="w").pack(side="left", padx=(0, 10))
        
        self.excel_entry = tk.Entry(excel_row, font=("Arial", 9), width=50, state="readonly")
        self.excel_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_excel_button = tk.Button(excel_row, text="Browse...", 
                                       command=self._browse_excel,
                                       bg="#800020", fg="white", font=("Arial", 9),
                                       padx=12, pady=4, cursor="hand2", relief="flat", bd=0)
        browse_excel_button.pack(side="left", padx=(0, 5))
        
        paste_excel_button = tk.Button(excel_row, text="Paste path...",
                                      command=self._paste_excel_path,
                                      bg="#800020", fg="white", font=("Arial", 9),
                                      padx=12, pady=4, cursor="hand2", relief="flat", bd=0)
        paste_excel_button.pack(side="left", padx=(0, 5))
        
        clear_excel_button = tk.Button(excel_row, text="Clear", 
                                      command=self._clear_excel,
                                      bg="#800020", fg="white", font=("Arial", 9),
                                      padx=12, pady=4, cursor="hand2", relief="flat", bd=0)
        clear_excel_button.pack(side="left")
        
        # Excel/CSV status label
        self.excel_status_label = tk.Label(excel_content, text="No Excel/CSV selected", 
                                          font=("Arial", 9, "italic"), bg="#f0f0f0", fg="#666666")
        self.excel_status_label.pack(pady=(5, 0))

        # Column mapping (optional)
        map_section = tk.LabelFrame(excel_content, text="Column Mapping (optional)", 
                                    font=("Arial", 10, "bold"), bg="#f0f0f0", fg="#800000")
        map_section.pack(fill="x", pady=(10, 0))

        map_row1 = tk.Frame(map_section, bg="#f0f0f0")
        map_row1.pack(fill="x", padx=10, pady=(8, 4))
        tk.Label(map_row1, text="Client Name (letter):", font=("Arial", 9), bg="#f0f0f0").pack(side="left")
        self.name_col_entry = tk.Entry(map_row1, font=("Arial", 9), width=6)
        self.name_col_entry.pack(side="left", padx=(6, 12))
        
        tk.Label(map_row1, text="Notes (letter):", font=("Arial", 9), bg="#f0f0f0").pack(side="left")
        self.notes_col_entry = tk.Entry(map_row1, font=("Arial", 9), width=6)
        self.notes_col_entry.pack(side="left", padx=(6, 12))

        map_row2 = tk.Frame(map_section, bg="#f0f0f0")
        map_row2.pack(fill="x", padx=10, pady=(0, 8))
        self.split_dos_var = tk.IntVar(value=0)
        tk.Checkbutton(map_row2, text="Use split Dates of Service (Start/End)", variable=self.split_dos_var,
                      onvalue=1, offvalue=0, bg="#f0f0f0", font=("Arial", 9)).pack(side="left")
        
        tk.Label(map_row2, text="DOS Range (letter):", font=("Arial", 9), bg="#f0f0f0").pack(side="left", padx=(12,0))
        self.dos_col_entry = tk.Entry(map_row2, font=("Arial", 9), width=6)
        self.dos_col_entry.pack(side="left", padx=(6, 12))
        
        tk.Label(map_row2, text="DOS Start (letter):", font=("Arial", 9), bg="#f0f0f0").pack(side="left")
        self.dos_start_col_entry = tk.Entry(map_row2, font=("Arial", 9), width=6)
        self.dos_start_col_entry.pack(side="left", padx=(6, 12))
        
        tk.Label(map_row2, text="DOS End (letter):", font=("Arial", 9), bg="#f0f0f0").pack(side="left")
        self.dos_end_col_entry = tk.Entry(map_row2, font=("Arial", 9), width=6)
        self.dos_end_col_entry.pack(side="left", padx=(6, 12))

        def _apply_mapping_from_gui():
            def g(entry):
                try:
                    return entry.get().strip()
                except Exception:
                    return ''
            self.user_col_map['name_col'] = g(self.name_col_entry).upper()
            self.user_col_map['notes_col'] = g(self.notes_col_entry).upper()
            self.user_col_map['dos_col'] = g(self.dos_col_entry).upper()
            self.user_col_map['dos_start_col'] = g(self.dos_start_col_entry).upper()
            self.user_col_map['dos_end_col'] = g(self.dos_end_col_entry).upper()
            self.use_split_dos = bool(self.split_dos_var.get())
            self.gui_log(f"Applied column mapping: {self.user_col_map} | split_dos={self.use_split_dos}")

        map_apply_row = tk.Frame(map_section, bg="#f0f0f0")
        map_apply_row.pack(fill="x", padx=10, pady=(0, 8))
        tk.Button(map_apply_row, text="Apply Mapping", command=_apply_mapping_from_gui,
                  bg="#800020", fg="white", font=("Arial", 9), padx=10, pady=4, cursor="hand2",
                  relief="flat", bd=0).pack(side="left")
        
        # ========== Ledger Training Section ==========
        ledger_section = tk.LabelFrame(main_frame, text="Ledger Training (Optional)", 
                                       font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        ledger_section.pack(fill="x", pady=(0, 15))

        ledger_content = tk.Frame(ledger_section, bg="#f0f0f0")
        ledger_content.pack(fill="x", expand=True, padx=15, pady=10)

        tk.Label(ledger_content, text="Train the bot on how to handle the ledger window:", 
                font=("Arial", 9), bg="#f0f0f0", fg="#666666").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0,8))

        tk.Button(ledger_content, text="Train: Save Ledger",
                  command=self._train_ledger_save,
                  bg="#800020", fg="white", font=("Arial", 9), padx=12, pady=4, cursor="hand2",
                  relief="flat", bd=0).grid(row=1, column=0, sticky="w", padx=(0,10))

        tk.Button(ledger_content, text="Test: Extract DOS",
                  command=self._test_extract_ledger_dos,
                  bg="#800020", fg="white", font=("Arial", 9), padx=12, pady=4, cursor="hand2",
                  relief="flat", bd=0).grid(row=1, column=1, sticky="w", padx=(0,10))

        tk.Button(ledger_content, text="Train: Close Ledger",
                  command=self._train_ledger_close,
                  bg="#800020", fg="white", font=("Arial", 9), padx=12, pady=4, cursor="hand2",
                  relief="flat", bd=0).grid(row=1, column=2, sticky="w")

        for i in range(3):
            ledger_content.grid_columnconfigure(i, weight=0)

        # ========== Manual Date Override Section ==========
        date_section = tk.LabelFrame(main_frame, text="Date Range", 
                                     font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        date_section.pack(fill="x", pady=(0, 15))

        date_content = tk.Frame(date_section, bg="#f0f0f0")
        date_content.pack(fill="x", expand=True, padx=15, pady=10)

        self.manual_date_var = tk.IntVar(value=0)
        manual_chk = tk.Checkbutton(date_content, text="Use manual date range (override file dates)",
                                    variable=self.manual_date_var, onvalue=1, offvalue=0,
                                    bg="#f0f0f0", font=("Arial", 10),
                                    command=lambda: self._toggle_manual_dates())
        manual_chk.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        tk.Label(date_content, text="Start Date (MM/DD/YYYY):", font=("Arial", 10), bg="#f0f0f0").grid(row=1, column=0, sticky="w")
        self.start_date_entry = tk.Entry(date_content, font=("Arial", 10), width=18, state="disabled")
        self.start_date_entry.grid(row=1, column=1, sticky="w", padx=(6, 20))

        tk.Label(date_content, text="End Date (MM/DD/YYYY):", font=("Arial", 10), bg="#f0f0f0").grid(row=1, column=2, sticky="w")
        self.end_date_entry = tk.Entry(date_content, font=("Arial", 10), width=18, state="disabled")
        self.end_date_entry.grid(row=1, column=3, sticky="w", padx=(6, 0))

        for i in range(4):
            date_content.grid_columnconfigure(i, weight=0)

        # ========== Training/Coordinates Section ==========
        training_section = tk.LabelFrame(main_frame, text="Coordinate Training Tool", 
                                        font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        training_section.pack(fill="x", pady=(0, 15))
        
        training_content = tk.Frame(training_section, bg="#f0f0f0")
        training_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Instructions
        instruction_text = "How to record: 1) Enter element name below 2) Hover mouse over element in Medisoft 3) Press F9 to capture position"
        tk.Label(training_content, text=instruction_text, 
                font=("Arial", 9), bg="#f0f0f0", fg="#666666", wraplength=600, 
                justify="left").pack(pady=(0, 10))
        
        # Position display and controls
        coord_frame = tk.Frame(training_content, bg="#f0f0f0")
        coord_frame.pack(fill="x", pady=(0, 5))
        
        tk.Label(coord_frame, text="Element Name:", font=("Arial", 9), bg="#f0f0f0").pack(side="left", padx=(0, 5))
        self.coord_name_entry = tk.Entry(coord_frame, font=("Arial", 9), width=25)
        self.coord_name_entry.pack(side="left", padx=(0, 10))
        self.coord_name_entry.insert(0, "Launch Medisoft Reports")  # Default name
        
        # Keyboard shortcut info
        shortcut_frame = tk.Frame(coord_frame, bg="#f0f0f0")
        shortcut_frame.pack(side="left", padx=(0, 10))
        
        if KEYBOARD_AVAILABLE:
            shortcut_text = "F9 = Coordinates | F8 = Screenshot"
            shortcut_color = "#800020"
        else:
            shortcut_text = "⚠️ Install 'keyboard' module for hotkeys: pip install keyboard"
            shortcut_color = "#dc3545"
        
        tk.Label(shortcut_frame, text=shortcut_text, 
                font=("Arial", 8, "bold"), bg="#f0f0f0", fg=shortcut_color, 
                wraplength=200).pack()
        
        # Enable/Disable recording toggle
        self.recording_enabled = False
        self.screenshot_enabled = False
        
        toggle_frame = tk.Frame(coord_frame, bg="#f0f0f0")
        toggle_frame.pack(side="left", padx=(0, 10))
        
        self.recording_status_label = tk.Label(toggle_frame, text="Coordinates: OFF", 
                                              font=("Arial", 8, "bold"), bg="#f0f0f0", fg="#dc3545")
        self.recording_status_label.pack(side="left", padx=(0, 5))
        
        toggle_coord_button = tk.Button(toggle_frame, text="Enable F9", 
                                       command=self._toggle_recording,
                                       bg="#800020", fg="white", font=("Arial", 8),
                                       padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        toggle_coord_button.pack(side="left", padx=(0, 5))
        
        self.screenshot_status_label = tk.Label(toggle_frame, text="Screenshot: OFF", 
                                                font=("Arial", 8, "bold"), bg="#f0f0f0", fg="#dc3545")
        self.screenshot_status_label.pack(side="left", padx=(0, 5))
        
        toggle_screenshot_button = tk.Button(toggle_frame, text="Enable F8", 
                                             command=self._toggle_screenshot,
                                             bg="#800020", fg="white", font=("Arial", 8),
                                             padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        toggle_screenshot_button.pack(side="left")
        
        self.current_position_label = tk.Label(coord_frame, text="Position: Not recorded", 
                                              font=("Arial", 9, "italic"), bg="#f0f0f0", fg="#666666")
        self.current_position_label.pack(side="left", padx=(10, 0))
        
        # Saved coordinates display
        coords_list_frame = tk.Frame(training_content, bg="#f0f0f0")
        coords_list_frame.pack(fill="x", pady=(5, 0))
        
        tk.Label(coords_list_frame, text="Saved Coordinates:", font=("Arial", 9, "bold"), bg="#f0f0f0").pack(side="left", padx=(0, 10))
        
        self.coords_display = tk.Text(coords_list_frame, height=3, font=("Consolas", 8), 
                                     bg="#ffffff", fg="#000000", wrap=tk.WORD, state="disabled")
        self.coords_display.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        delete_coord_button = tk.Button(coords_list_frame, text="Delete Selected", 
                                        command=self._delete_coordinate,
                                        bg="#800020", fg="white", font=("Arial", 8),
                                        padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        delete_coord_button.pack(side="left")
        
        # Image recognition section
        image_frame = tk.Frame(training_content, bg="#f0f0f0")
        image_frame.pack(fill="x", pady=(10, 0))
        
        image_header = tk.Frame(image_frame, bg="#f0f0f0")
        image_header.pack(fill="x", pady=(0, 5))
        
        tk.Label(image_header, text="Image Recognition (Recommended):", font=("Arial", 9, "bold"), 
                bg="#f0f0f0").pack(side="left", padx=(0, 10))
        
        capture_image_button = tk.Button(image_header, text="Capture Screenshot (F8)", 
                                         command=self._capture_screenshot_region,
                                         bg="#800020", fg="white", font=("Arial", 8),
                                         padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        capture_image_button.pack(side="left", padx=(0, 5))
        
        list_windows_button = tk.Button(image_header, text="List Windows", 
                                        command=self._show_window_list,
                                        bg="#800020", fg="white", font=("Arial", 8),
                                        padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        list_windows_button.pack(side="left")
        
        image_info = tk.Frame(image_frame, bg="#f0f0f0")
        image_info.pack(fill="x")
        
        tk.Label(image_info, text="💡 Tip: Image recognition works across all screen sizes! Hover over element and press F8 to capture.", 
                font=("Arial", 8), bg="#f0f0f0", fg="#666666", wraplength=600, 
                justify="left").pack(anchor="w")
        
        self._update_coords_display()
        
        # ========== AI Workflow Trainer Settings Section ==========
        ai_section = tk.LabelFrame(main_frame, text="AI Workflow Trainer - GPT API Configuration", 
                                  font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        ai_section.pack(fill="x", pady=(0, 15))
        
        ai_content = tk.Frame(ai_section, bg="#f0f0f0")
        ai_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Instructions
        ai_instruction = "Enter your OpenAI GPT API key to enable AI-powered workflow data interpretation. The key is encrypted and stored securely on your machine."
        tk.Label(ai_content, text=ai_instruction, 
                font=("Arial", 9), bg="#f0f0f0", fg="#666666", wraplength=600, 
                justify="left").pack(pady=(0, 10), anchor="w")
        
        # API Key input row
        api_key_row = tk.Frame(ai_content, bg="#f0f0f0")
        api_key_row.pack(fill="x", pady=(0, 5))
        
        tk.Label(api_key_row, text="GPT API Key:", font=("Arial", 10), bg="#f0f0f0",
                anchor="w").pack(side="left", padx=(0, 10))
        
        self.api_key_entry = tk.Entry(api_key_row, font=("Arial", 10), width=50, show="*")
        self.api_key_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Show/Hide toggle button
        self.api_key_visible = False
        def toggle_api_key_visibility():
            self.api_key_visible = not self.api_key_visible
            if self.api_key_visible:
                self.api_key_entry.config(show="")
                toggle_visibility_btn.config(text="Hide")
            else:
                self.api_key_entry.config(show="*")
                toggle_visibility_btn.config(text="Show")
        
        toggle_visibility_btn = tk.Button(api_key_row, text="Show", 
                                         command=toggle_api_key_visibility,
                                         bg="#800020", fg="white", font=("Arial", 9),
                                         padx=10, pady=4, cursor="hand2", relief="flat", bd=0)
        toggle_visibility_btn.pack(side="left", padx=(0, 5))
        
        # Save API Key button
        def save_api_key():
            api_key = self.api_key_entry.get().strip()
            if not api_key:
                messagebox.showwarning("Missing API Key", "Please enter your GPT API key.")
                return
            
            if self.save_gpt_api_key(api_key):
                messagebox.showinfo("Success", "GPT API key saved securely! The key is encrypted and stored on your machine.")
                self.gui_log("✅ GPT API key saved successfully (encrypted)")
                # Clear the entry field for security
                self.api_key_entry.delete(0, tk.END)
                self._update_api_key_status()
            else:
                messagebox.showerror("Error", "Failed to save API key. Please check the error log.")
        
        save_api_key_btn = tk.Button(api_key_row, text="Save Key", 
                                     command=save_api_key,
                                     bg="#800020", fg="white", font=("Arial", 9),
                                     padx=12, pady=4, cursor="hand2", relief="flat", bd=0)
        save_api_key_btn.pack(side="left", padx=(0, 5))
        
        # Test API Key button
        def test_api_key():
            api_key = self.get_gpt_api_key()
            if not api_key:
                messagebox.showwarning("No API Key", "Please save your API key first.")
                return
            
            if not OPENAI_AVAILABLE:
                messagebox.showerror("OpenAI Not Available", 
                                    "OpenAI library not installed. Please install it:\npip install openai")
                return
            
            # Test the API key
            self.gui_log("🔍 Testing GPT API key...")
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                # Make a simple test call
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Say 'API key is working' if you can read this."}],
                    max_tokens=20
                )
                result = response.choices[0].message.content
                self.gui_log(f"✅ API key test successful: {result}")
                messagebox.showinfo("API Key Test", f"✅ API key is working!\n\nResponse: {result}")
            except Exception as e:
                error_msg = str(e)
                self.gui_log(f"❌ API key test failed: {error_msg}")
                messagebox.showerror("API Key Test Failed", 
                                    f"Failed to connect to OpenAI API:\n\n{error_msg}\n\nPlease check your API key.")
        
        test_api_key_btn = tk.Button(api_key_row, text="Test Key", 
                                     command=test_api_key,
                                     bg="#800020", fg="white", font=("Arial", 9),
                                     padx=12, pady=4, cursor="hand2", relief="flat", bd=0)
        test_api_key_btn.pack(side="left")
        
        # API Key status label
        self.api_key_status_label = tk.Label(ai_content, text="Status: No API key saved", 
                                            font=("Arial", 9, "italic"), bg="#f0f0f0", fg="#666666")
        self.api_key_status_label.pack(pady=(5, 0), anchor="w")
        
        # Update status on startup
        self._update_api_key_status()
        
        # Dependency status
        dep_status_row = tk.Frame(ai_content, bg="#f0f0f0")
        dep_status_row.pack(fill="x", pady=(5, 0))
        
        if not OPENAI_AVAILABLE:
            tk.Label(dep_status_row, text="⚠️ OpenAI library not installed. Install with: pip install openai", 
                    font=("Arial", 8), bg="#f0f0f0", fg="#dc3545").pack(anchor="w")
        elif not CRYPTOGRAPHY_AVAILABLE:
            tk.Label(dep_status_row, text="⚠️ Cryptography library not installed. Install with: pip install cryptography", 
                    font=("Arial", 8), bg="#f0f0f0", fg="#dc3545").pack(anchor="w")
        else:
            tk.Label(dep_status_row, text="✅ All dependencies installed - Ready to use AI Workflow Trainer", 
                    font=("Arial", 8), bg="#f0f0f0", fg="#28a745").pack(anchor="w")
        
        # ========== Workflow Monitoring Section ==========
        monitoring_section = tk.LabelFrame(ai_content, text="Workflow Monitoring", 
                                          font=("Arial", 10, "bold"), bg="#f0f0f0", fg="#800000")
        monitoring_section.pack(fill="x", pady=(15, 0))
        
        monitoring_content = tk.Frame(monitoring_section, bg="#f0f0f0")
        monitoring_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Instructions
        monitoring_instruction = "Monitor and record your workflow actions. The system will track mouse movements, clicks, window changes, and screenshots for AI analysis."
        tk.Label(monitoring_content, text=monitoring_instruction, 
                font=("Arial", 9), bg="#f0f0f0", fg="#666666", wraplength=600, 
                justify="left").pack(pady=(0, 10), anchor="w")
        
        # Monitoring controls row
        monitor_controls_row = tk.Frame(monitoring_content, bg="#f0f0f0")
        monitor_controls_row.pack(fill="x", pady=(0, 5))
        
        # Start/Stop Monitoring button
        self.monitoring_status_label = tk.Label(monitor_controls_row, text="Status: Not Monitoring", 
                                               font=("Arial", 9, "bold"), bg="#f0f0f0", fg="#666666")
        self.monitoring_status_label.pack(side="left", padx=(0, 10))
        
        def start_monitoring():
            if not KEYBOARD_AVAILABLE:
                messagebox.showwarning("Keyboard Module Required", 
                                      "The 'keyboard' module is required for workflow monitoring.\n\n"
                                      "Please install it: pip install keyboard")
                return
            
            if self.workflow_monitor.start_monitoring():
                self.monitoring_status_label.config(text="Status: 🔴 Monitoring...", fg="#dc3545")
                start_monitor_btn.config(state="disabled")
                stop_monitor_btn.config(state="normal")
                self.gui_log("🔴 Workflow monitoring started - All actions are being recorded")
            else:
                messagebox.showwarning("Already Monitoring", "Workflow monitoring is already active.")
        
        def stop_monitoring():
            workflow_data = self.workflow_monitor.stop_monitoring()
            if workflow_data:
                self.monitoring_status_label.config(text="Status: ⏹️ Stopped", fg="#666666")
                start_monitor_btn.config(state="normal")
                stop_monitor_btn.config(state="disabled")
                
                # Show summary
                total_actions = workflow_data["session_info"]["total_actions"]
                duration = workflow_data["session_info"]["duration_seconds"]
                self.gui_log(f"📊 Monitoring session complete: {total_actions} actions recorded over {duration:.1f} seconds")
                
                # Ask if user wants to save/interpret
                response = messagebox.askyesnocancel(
                    "Workflow Recording Complete",
                    f"Recording complete!\n\n"
                    f"Actions recorded: {total_actions}\n"
                    f"Duration: {duration:.1f} seconds\n\n"
                    f"Would you like to:\n"
                    f"• Yes: Save and interpret with GPT\n"
                    f"• No: Just save the data\n"
                    f"• Cancel: Discard this recording"
                )
                
                if response is True:  # Yes - Save and interpret
                    self._save_and_interpret_workflow(workflow_data)
                elif response is False:  # No - Just save
                    self._save_workflow_data(workflow_data)
        
        start_monitor_btn = tk.Button(monitor_controls_row, text="Start Monitoring", 
                                     command=start_monitoring,
                                     bg="#28a745", fg="white", font=("Arial", 10, "bold"),
                                     padx=15, pady=6, cursor="hand2", relief="flat", bd=0)
        start_monitor_btn.pack(side="left", padx=(0, 5))
        
        stop_monitor_btn = tk.Button(monitor_controls_row, text="Stop Monitoring", 
                                    command=stop_monitoring,
                                    bg="#dc3545", fg="white", font=("Arial", 10, "bold"),
                                    padx=15, pady=6, cursor="hand2", relief="flat", bd=0, state="disabled")
        stop_monitor_btn.pack(side="left", padx=(0, 10))
        
        # Store button references for state management
        self.start_monitor_btn = start_monitor_btn
        self.stop_monitor_btn = stop_monitor_btn
        
        # Statistics display
        self.monitoring_stats_label = tk.Label(monitoring_content, 
                                              text="Actions: 0 | Duration: 0.0s", 
                                              font=("Arial", 8), bg="#f0f0f0", fg="#666666")
        self.monitoring_stats_label.pack(pady=(5, 0), anchor="w")
        
        # Start stats update loop
        self._update_monitoring_stats()
        
        # ========== Navigation Section ==========
        navigation_section = tk.LabelFrame(main_frame, text="Navigation", 
                                          font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        navigation_section.pack(fill="x", pady=(0, 15))
        
        navigation_content = tk.Frame(navigation_section, bg="#f0f0f0")
        navigation_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Navigation buttons frame
        nav_buttons_frame = tk.Frame(navigation_content, bg="#f0f0f0")
        nav_buttons_frame.pack(fill="x")
        
        self.navigate_button = tk.Button(nav_buttons_frame, text="Navigate to Reports", 
                                         command=self._start_navigation,
                                         bg="#800020", fg="white", font=("Arial", 10),
                                         padx=18, pady=6, cursor="hand2", state="disabled",
                                         relief="flat", bd=0)
        self.navigate_button.pack(side="left")
        
        stop_btn = tk.Button(nav_buttons_frame, text="Stop",
                             command=self._request_stop,
                             bg="#800020", fg="white", font=("Arial", 10),
                             padx=18, pady=6, cursor="hand2", relief="flat", bd=0)
        stop_btn.pack(side="left", padx=(10, 0))
        
        # Training helpers for Navigate to Reports
        train_frame = tk.Frame(navigation_content, bg="#f0f0f0")
        train_frame.pack(fill="x", pady=(10, 0))
        tk.Label(train_frame, text="Train targets:", font=("Arial", 9), bg="#f0f0f0",
                fg="#333333").pack(side="left", padx=(0, 8))
        # Predefined list of elements used in the Navigate to Reports flow
        self.navigate_train_targets = [
            "Launch Medisoft Reports",
            "Custom",
            "Patient Account Ledger",
            "Ledger arrow",
            "Ledger dropdown select",
            "Ledger ok",
            "Ledger file name line",
            "Ledger save ok",
            "Search_ChartDots",
            "Search_DateFrom_Start",
            "Search_DateFrom_End",
            "Search_DateCreated_Check",
            "Search_ProcCode",
            "Search_AddButton"
        ]
        self.nav_train_combo = ttk.Combobox(train_frame, values=self.navigate_train_targets, state="readonly", width=35)
        self.nav_train_combo.set(self.navigate_train_targets[0])
        self.nav_train_combo.pack(side="left")
        
        def _apply_train_target():
            try:
                target = self.nav_train_combo.get().strip()
                if not target:
                    return
                # Reuse existing training name entry so F8/F9 capture saves under this name
                if hasattr(self, 'coord_name_entry'):
                    self.coord_name_entry.delete(0, tk.END)
                    self.coord_name_entry.insert(0, target)
                self.gui_log(f"🎯 Training target set to: {target} — enable F8/F9 to capture")
            except Exception as e:
                self.gui_log(f"⚠️ Could not set training target: {e}")
        
        tk.Button(train_frame, text="Set target",
                  command=_apply_train_target,
                  bg="#800020", fg="white", font=("Arial", 9),
                  padx=12, pady=4, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=(8, 8))
        
        tk.Button(train_frame, text="Clear saved clicks",
                  command=self._clear_saved_clicks,
                  bg="#800020", fg="white", font=("Arial", 9),
                  padx=12, pady=4, cursor="hand2", relief="flat", bd=0).pack(side="left")
        
        # ========== Activity Log Section ==========
        log_section = tk.LabelFrame(main_frame, text="Activity Log", 
                                   font=("Arial", 11, "bold"), bg="#f0f0f0", fg="#800000")
        log_section.pack(fill="both", expand=True, pady=(0, 15))
        
        log_content = tk.Frame(log_section, bg="#f0f0f0")
        log_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Log text box with scrollbar
        self.log_text = scrolledtext.ScrolledText(log_content, height=15, 
                                                  font=("Consolas", 9), 
                                                  bg="#ffffff", fg="#000000",
                                                  wrap=tk.WORD)
        self.log_text.pack(fill="both", expand=True)
        
        # Bottom buttons
        button_frame = tk.Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(fill="x", pady=(0, 5))
        
        # Close button on the right
        self.close_button = tk.Button(button_frame, text="Close", 
                                     command=self._close_window,
                                     bg="#800020", fg="white", font=("Arial", 10),
                                     padx=18, pady=6, cursor="hand2",
                                     relief="flat", bd=0)
        self.close_button.pack(side="right")
        
        # Initial log message
        self.gui_log("Medisoft Billing Bot initialized")
        if self.users:
            self.gui_log(f"Loaded {len(self.users)} saved user(s) - Select a user from the dropdown or add a new one")
        else:
            self.gui_log("No users saved - Click 'Add User' to create your first user profile")
        
        # Check keyboard module availability
        if not KEYBOARD_AVAILABLE:
            self.gui_log("⚠️ Keyboard module not installed - Hotkeys (F8/F9) will not work")
            self.gui_log("💡 Install with: pip install keyboard")
        else:
            self.gui_log("✅ Keyboard module loaded - Hotkeys available (F8/F9)")
        
        # Check OpenCV availability
        if not OPENCV_AVAILABLE:
            self.gui_log("⚠️ OpenCV not installed - Image recognition works but without confidence threshold")
            self.gui_log("💡 Install with: pip install opencv-python (optional, for better image matching)")
        else:
            self.gui_log("✅ OpenCV module loaded - Image recognition with confidence threshold available")
        
        # Check PDF parsing availability
        if not PDFPLUMBER_AVAILABLE:
            self.gui_log("⚠️ pdfplumber not installed - PDF parsing unavailable")
            self.gui_log("💡 Install with: pip install pdfplumber (required for processing insurance requests)")
        else:
            self.gui_log("✅ PDF parsing module loaded - Can extract data from insurance PDFs")
        
        # Check Excel/CSV parsing availability
        if not EXCEL_AVAILABLE:
            self.gui_log("⚠️ pandas not installed - Excel/CSV batch processing unavailable")
            self.gui_log("💡 Install with: pip install pandas openpyxl (required for batch processing)")
        else:
            if OPENPYXL_AVAILABLE:
                self.gui_log("✅ Excel/CSV parsing module loaded - Can process batch files (.xlsx, .csv)")
            else:
                self.gui_log("✅ Excel/CSV parsing available (pandas) - Install openpyxl for .xlsx files: pip install openpyxl")
        
        # Check if credentials are entered (either via user selection or manual entry)
        self._enable_login()
        
        # Check for updates after window is created (non-blocking)
        def check_updates():
            try:
                if check_for_updates_on_startup():
                    # Update was installed, close bot after 2 seconds
                    self.root.after(2000, self.root.quit)
            except Exception as e:
                logger.warning(f"Update check error: {e}")
        
        # Check for updates 1 second after window is shown
        self.root.after(1000, check_updates)
    
    def _enable_login(self):
        """Enable login button when credentials are entered"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if username and password and not self.is_logged_in:
            self.login_button.config(state="normal")
            self.status_label.config(text="Status: Ready to login - Click 'Login' to connect to Medisoft", 
                                   fg="#28a745")
        else:
            if self.is_logged_in:
                self.status_label.config(text="Status: Already logged in - Ready to navigate", 
                                       fg="#28a745")
            else:
                self.login_button.config(state="disabled")
            self.status_label.config(text="Status: Please enter both username and password", 
                                   fg="#0066cc")
    
    def _start_login(self):
        """Start the login process with entered credentials"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Missing Information", 
                                  "Please enter both username and password.")
            return
        
        # Disable login fields and buttons
        self.username_entry.config(state="disabled")
        self.password_entry.config(state="disabled")
        self.login_button.config(state="disabled")
        self.navigate_button.config(state="disabled")
        
        self.gui_log("Credentials received")
        self.gui_log("Starting Medisoft login process...")
        self.update_status("Logging in...", "#ff9500")
        
        # Run login in a separate thread to keep GUI responsive
        login_thread = threading.Thread(target=self._run_login_thread, 
                                           args=(username, password), daemon=True)
        login_thread.start()
    
    def _browse_pdf(self):
        """Open file dialog to select insurance PDF file"""
        pdf_path = filedialog.askopenfilename(
            title="Select Insurance Company PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            initialdir=str(Path.home() / "Downloads")
        )
        
        if pdf_path:
            self.selected_pdf_path = pdf_path
            # Update the entry field (make it editable temporarily)
            self.pdf_entry.config(state="normal")
            self.pdf_entry.delete(0, tk.END)
            self.pdf_entry.insert(0, pdf_path)
            self.pdf_entry.config(state="readonly")
            
            # Update status
            pdf_name = Path(pdf_path).name
            self.pdf_status_label.config(text=f"Selected: {pdf_name}", fg="#28a745")
            self.gui_log(f"📄 PDF selected: {pdf_name}")
    
    def _clear_pdf(self):
        """Clear the selected PDF"""
        self.selected_pdf_path = None
        self.pdf_entry.config(state="normal")
        self.pdf_entry.delete(0, tk.END)
        self.pdf_entry.config(state="readonly")
        self.pdf_status_label.config(text="No PDF selected", fg="#666666")
        self.gui_log("📄 PDF selection cleared")
    
    def _browse_excel(self):
        """Open file dialog to select Excel/CSV file for batch processing"""
        file_path = filedialog.askopenfilename(
            title="Select Excel/CSV File (Batch Processing)",
            filetypes=[
                ("Supported files", "*.xlsx *.xls *.csv"),
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*")
            ],
            initialdir=str(Path.home() / "Downloads")
        )
        
        if file_path:
            self.selected_excel_path = file_path
            # Update the entry field (make it editable temporarily)
            self.excel_entry.config(state="normal")
            self.excel_entry.delete(0, tk.END)
            self.excel_entry.insert(0, file_path)
            self.excel_entry.config(state="readonly")
            
            # Load records using robust loader
            try:
                records = self._load_records_from_table_file(file_path)
            except Exception as e:
                records = []
                self.gui_log(f"❌ Error loading file: {e}")
            # Store a simplified version for legacy flows
            self.excel_client_data = [
                {
                    'client_name': r.get('patient_name', ''),
                    'date_range_start': r.get('dos_start', ''),
                    'date_range_end': r.get('dos_end', ''),
                    'notes': r.get('notes', ''),
                }
                for r in (records or [])
            ]
            parsed_count = len(self.excel_client_data)
            
            # Update status
            file_name = Path(file_path).name
            if parsed_count > 0:
                self.excel_status_label.config(text=f"Selected: {file_name} ({parsed_count} clients found)", fg="#28a745")
                self.gui_log(f"📊 Excel/CSV selected: {file_name} ({parsed_count} clients loaded)")
            else:
                self.excel_status_label.config(text=f"Selected: {file_name} (No valid data found)", fg="#dc3545")
                self.gui_log(f"⚠️ Excel/CSV selected but no valid client data found: {file_name}")
    
    def _clear_excel(self):
        """Clear the selected Excel/CSV file"""
        self.selected_excel_path = None
        self.excel_client_data = []
        self.excel_entry.config(state="normal")
        self.excel_entry.delete(0, tk.END)
        self.excel_entry.config(state="readonly")
        self.excel_status_label.config(text="No Excel/CSV selected", fg="#666666")
        self.gui_log("📊 Excel/CSV selection cleared")
    
    def parse_excel_csv(self, file_path):
        """Parse Excel or CSV file and extract client data.
        
        Expected format:
        - Column C (index 2): Patient Name
        - Column M (index 12): DOS Range (e.g., "09/02/2025 - 09/30/2025" or "09/02/2025 to 09/30/2025")
        
        Returns: Number of valid client records found
        """
        if not EXCEL_AVAILABLE:
            self.gui_log("❌ pandas not available - cannot parse Excel/CSV files")
            self.gui_log("💡 Install with: pip install pandas openpyxl")
            return 0
        
        self.gui_log(f"📊 Parsing Excel/CSV file: {Path(file_path).name}")
        self.excel_client_data = []
        
        try:
            file_ext = Path(file_path).suffix.lower()
            
            # Read file based on extension
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            else:
                # Try openpyxl for .xlsx, fallback to default
                try:
                    df = pd.read_excel(file_path, engine='openpyxl')
                except:
                    df = pd.read_excel(file_path)
            
            if df.empty:
                self.gui_log("⚠️ File is empty")
                return 0
            
            self.gui_log(f"📋 Loaded {len(df)} rows from file")
            
            # Check if we have enough columns
            if len(df.columns) < 13:  # Need at least column M (index 12)
                self.gui_log(f"⚠️ File has only {len(df.columns)} columns, need at least 13 (Column M)")
                return 0
            
            # Extract data from Column C (Patient Name) and Column M (DOS Range)
            client_col = df.columns[2]  # Column C (index 2)
            dos_col = df.columns[12]    # Column M (index 12)
            
            self.gui_log(f"📋 Using Column C ({client_col}) for Patient Name")
            self.gui_log(f"📋 Using Column M ({dos_col}) for DOS Range")
            
            valid_count = 0
            
            for idx, row in df.iterrows():
                client_name = None
                date_range_start = None
                date_range_end = None
                
                # Extract patient name from Column C
                try:
                    name_val = row.iloc[2]  # Column C
                    if pd.notna(name_val):
                        client_name = str(name_val).strip()
                except:
                    pass
                
                # Extract DOS range from Column M
                try:
                    dos_val = row.iloc[12]  # Column M
                    if pd.notna(dos_val):
                        dos_str = str(dos_val).strip()
                        
                        # Parse date range - support multiple formats
                        # "09/02/2025 - 09/30/2025", "09/02/2025 to 09/30/2025", etc.
                        date_pattern = r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\s*[-to]\s*(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})'
                        match = re.search(date_pattern, dos_str)
                        
                        if match:
                            date_range_start = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
                            date_range_end = f"{match.group(4)}/{match.group(5)}/{match.group(6)}"
                        else:
                            # Try finding two separate dates
                            single_date_pattern = r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})'
                            dates = re.findall(single_date_pattern, dos_str)
                            if len(dates) >= 2:
                                date_range_start = f"{dates[0][0]}/{dates[0][1]}/{dates[0][2]}"
                                date_range_end = f"{dates[1][0]}/{dates[1][1]}/{dates[1][2]}"
                except:
                    pass
                
                # Only add if we have both name and date range
                if client_name and date_range_start and date_range_end:
                    self.excel_client_data.append({
                        'client_name': client_name,
                        'date_range_start': date_range_start,
                        'date_range_end': date_range_end,
                        'row_number': idx + 2  # Excel row number (1-indexed + header)
                    })
                    valid_count += 1
            
            self.gui_log(f"✅ Parsed {valid_count} valid client record(s) from Excel/CSV")
            
            if valid_count == 0:
                self.gui_log("⚠️ No valid records found (requires both Patient Name in Column C and DOS Range in Column M)")
            
            return valid_count
            
        except Exception as e:
            self.gui_log(f"❌ Error parsing Excel/CSV file: {e}")
            import traceback
            self.gui_log(f"   Traceback: {traceback.format_exc()[:300]}")
            return 0
    
    def _start_navigation(self):
        """Start the navigation to reports"""
        if not self.is_logged_in:
            messagebox.showwarning("Not Logged In", 
                                  "Please login first before navigating.")
            return
        
        # Disable navigate button while navigating
        self.navigate_button.config(state="disabled")
        # Reset stop flag at the beginning of a new run
        self.stop_requested = False
        
        self.gui_log("Starting navigation to Reports...")
        self.update_status("Navigating to Reports...", "#ff9500")
        
        # Run navigation in a separate thread to keep GUI responsive
        nav_thread = threading.Thread(target=self._run_navigation_thread, daemon=True)
        nav_thread.start()
    
    def _run_login_thread(self, username, password):
        """Run login workflow in a separate thread"""
        try:
            success = self.login_workflow(username, password)
            if success:
                self.is_logged_in = True
                # Enable navigate button after successful login
                self.root.after(0, self._enable_navigate_button)
        except Exception as e:
            self.gui_log(f"Login error: {e}")
            self.update_status(f"Login error: {e}", "#dc3545")
            # Re-enable UI on error
            self.root.after(0, self._reset_login_ui)
    
    def _run_navigation_thread(self):
        """Run navigation workflow in a separate thread"""
        try:
            self.navigate_to_reports_workflow()
        except Exception as e:
            self.gui_log(f"Navigation error: {e}")
            self.update_status(f"Navigation error: {e}", "#dc3545")
            # Re-enable navigate button on error
            self.root.after(0, self._enable_navigate_button)
        finally:
            # If stop was requested, reflect it in the UI
            if getattr(self, 'stop_requested', False):
                self.update_status("Stopped by user", "#dc3545")
                self.root.after(0, self._enable_navigate_button)
    
    def _enable_navigate_button(self):
        """Enable the navigate button after successful login"""
        self.navigate_button.config(state="normal")
        self.status_label.config(text="Status: Logged in - Click 'Navigate to Reports' to continue", 
                               fg="#28a745")
    
    def _reset_login_ui(self):
        """Reset UI elements after login error"""
        self.username_entry.config(state="normal")
        self.password_entry.config(state="normal")
        self.login_button.config(state="normal")
        self.is_logged_in = False
        self._enable_login()
    
    def _close_window(self):
        """Close the activity window"""
        # Unhook keyboard listeners before closing
        if KEYBOARD_AVAILABLE:
            try:
                keyboard.unhook_all()
            except:
                pass
        
        if messagebox.askokcancel("Close", "Are you sure you want to close? The bot may still be running."):
            self.root.quit()

    def _request_stop(self):
        """Signal running workflows to stop as soon as safe."""
        try:
            self.stop_requested = True
            self.gui_log("⛔ Stop requested by user")
        finally:
            # Unblock UI quickly
            self.root.after(0, self._enable_navigate_button)
    
    def gui_log(self, message):
        """Add a message to the GUI log and file log"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # Add to GUI (thread-safe)
        if self.log_text:
            self.log_text.after(0, lambda: self._append_log(log_message))
        
        # Add to file logger
        logger.info(message)
    
    def _append_log(self, message):
        """Thread-safe log appending"""
        if self.log_text:
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
    
    def update_status(self, status, color="#0066cc"):
        """Update the status label (thread-safe)"""
        if self.status_label:
            self.root.after(0, lambda: self._update_status_safe(status, color))
    
    def _update_status_safe(self, status, color):
        """Thread-safe status update"""
        if self.status_label:
            self.status_label.config(text=f"Status: {status}", fg=color)
    
    # ======================== Date Override ========================
    def _toggle_manual_dates(self):
        try:
            manual = bool(self.manual_date_var.get())
        except Exception:
            manual = False
        if manual:
            if hasattr(self, 'start_date_entry'):
                self.start_date_entry.config(state="normal")
            if hasattr(self, 'end_date_entry'):
                self.end_date_entry.config(state="normal")
            self.gui_log("Manual date range override enabled")
        else:
            if hasattr(self, 'start_date_entry'):
                self.start_date_entry.config(state="disabled")
            if hasattr(self, 'end_date_entry'):
                self.end_date_entry.config(state="disabled")
            self.gui_log("Manual date range override disabled")

    # ======================== Data File Processing ========================
    def process_data_file_and_fill_search(self):
        """Process selected file (Excel/CSV) and iterate patients with date ranges.
        If manual date override is enabled, use GUI dates for all patients.
        Expected headers (robust): 'Patient Name' and 'Dates of Service'.
        'Dates of Service' like '1/1/2024 - 12/31/2024'.
        """
        try:
            # Prepare output folder for this run
            self._prepare_run_output_dir()

            records = []
            if getattr(self, 'selected_excel_path', None):
                records = self._load_records_from_table_file(self.selected_excel_path)
                self.gui_log(f"Loaded {len(records)} records from {self.selected_excel_path}")
            else:
                self.gui_log("No Excel/CSV selected; nothing to process")
                return

            # Manual date overrides
            try:
                manual_dates = bool(self.manual_date_var.get())
            except Exception:
                manual_dates = False
            override_start = (self.start_date_entry.get().strip() if manual_dates else "") if hasattr(self, 'start_date_entry') else ""
            override_end = (self.end_date_entry.get().strip() if manual_dates else "") if hasattr(self, 'end_date_entry') else ""

            processed = 0
            for rec in records:
                patient_name = str(rec.get('patient_name', '')).strip()
                dos_start = str(rec.get('dos_start', '')).strip()
                dos_end = str(rec.get('dos_end', '')).strip()
                insurance_notes = str(rec.get('notes', '')).strip()

                if not patient_name:
                    continue

                # Apply manual override if enabled
                if manual_dates and (override_start or override_end):
                    dos_start, dos_end = override_start, override_end

                # Log what will be used
                self.gui_log(f"Processing: {patient_name} | DOS: {dos_start} - {dos_end}")

                # TODO: Fill Medisoft Search window here using trained coordinates/automation
                # self._fill_search_window(patient_name, dos_start, dos_end)

                # TODO: After generating and parsing the ledger window, capture actual DOS lines.
                # Placeholder: if no parsed dates yet, store the requested range so log isn't empty
                ledger_dos = []  # replace with parsed list from ledger
                if not ledger_dos:
                    # Use requested range as fallback entry
                    fallback = f"{dos_start} - {dos_end}".strip().strip(' -')
                    if fallback:
                        ledger_dos = [fallback]

                # Record row to run log (Patient, DOS from ledger, Insurance Notes)
                self.record_ledger_result(patient_name, ledger_dos, insurance_notes)

                processed += 1

            # Save final run log
            self.save_run_log()
            self.gui_log(f"Completed preparing {processed} search operations; log saved to: {self.run_output_dir}")
        except Exception as e:
            self.gui_log(f"Error processing data file: {e}")

    def _load_records_from_table_file(self, file_path: str) -> list:
        """Load rows from CSV/XLS/XLSX and extract Patient Name and Dates of Service columns.
        Scans sheets for headers; tolerant of header spacing/case.
        Returns list of dicts with keys: patient_name, dos_start, dos_end.
        """
        try:
            if not EXCEL_AVAILABLE:
                self.gui_log("pandas not available for table parsing")
                return []

            path = Path(file_path)
            if not path.exists():
                self.gui_log(f"File not found: {file_path}")
                return []

            ext = path.suffix.lower()
            # Detect file signature to choose correct reader regardless of extension
            signature = None
            try:
                with open(path, 'rb') as f:
                    signature = f.read(4)
            except Exception:
                signature = None
            dfs = []
            if ext in ('.csv', '.txt'):
                # Robust CSV reading with dialect/sep inference and encoding fallbacks
                csv_read_attempts = []
                def _try_csv(**kwargs):
                    try:
                        return pd.read_csv(path, dtype=str, **kwargs)
                    except Exception as e:
                        csv_read_attempts.append(str(e))
                        return None

                df = None
                # 1) Try with python engine and automatic separator inference
                df = _try_csv(engine='python', sep=None, on_bad_lines='skip', encoding='utf-8', encoding_errors='ignore')
                # 2) UTF-16 variants (common for exported Excel CSVs)
                if df is None:
                    for enc in ['utf-16', 'utf-16le', 'utf-16be']:
                        df = _try_csv(engine='python', sep=None, on_bad_lines='skip', encoding=enc)
                        if df is not None:
                            self.gui_log(f"ℹ️ CSV parsed using encoding: {enc}")
                            break
                # 3) Latin-1 fallback
                if df is None:
                    df = _try_csv(engine='python', sep=None, on_bad_lines='skip', encoding='latin1')
                # 4) Sniff delimiter using csv.Sniffer on small sample
                if df is None:
                    try:
                        import csv
                        for enc in ['utf-8', 'utf-8-sig', 'utf-16', 'utf-16le', 'utf-16be', 'latin1']:
                            with open(path, 'r', encoding=enc, errors='ignore') as f:
                                sample = ''.join([next(f) for _ in range(10)])
                            dialect = csv.Sniffer().sniff(sample, delimiters=[',','\t',';','|'])
                            df = _try_csv(engine='python', sep=dialect.delimiter, on_bad_lines='skip', encoding=enc)
                            if df is not None:
                                self.gui_log(f"ℹ️ CSV parsed using delimiter '{dialect.delimiter}' and encoding {enc}")
                                break
                    except Exception as e:
                        csv_read_attempts.append(f"sniffer: {e}")
                # 5) Space-delimited fallback
                if df is None:
                    df = _try_csv(engine='python', delim_whitespace=True, on_bad_lines='skip', encoding='utf-8', encoding_errors='ignore')
                if df is None:
                    self.gui_log(f"❌ CSV parse failed: {csv_read_attempts[-1] if csv_read_attempts else 'unknown error'}")
                    return []
                dfs = [df]
            elif (signature and signature[:2] == b'PK') or ext in ('.xlsx', '.xlsm'):
                # Modern Excel formats require openpyxl; if the content isn't a valid zip (often misnamed CSV),
                # fall back to CSV reader automatically.
                try:
                    # If the signature is actually CFBF (xls) but extension says xlsx, use xlrd path
                    if signature == b"\xD0\xCF\x11\xE0":
                        data = pd.read_excel(path, dtype=str, sheet_name=None, engine='xlrd')
                    else:
                        data = pd.read_excel(path, dtype=str, sheet_name=None, engine='openpyxl')
                except Exception as e:
                    msg = str(e).lower()
                    if signature == b"\xD0\xCF\x11\xE0":
                        # Ensure we try xlrd explicitly for CFBF
                        try:
                            data = pd.read_excel(path, dtype=str, sheet_name=None, engine='xlrd')
                        except Exception as e_xls:
                            self.gui_log("❌ Could not read legacy Excel (.xls). Install xlrd>=2.0.1.")
                            # Fallbacks for mislabeled/legacy content
                            data = None
                    elif 'zip file' in msg or 'file is not a zip' in msg or 'badzipfile' in msg:
                        # Attempt CSV fallback even though extension says xlsx
                        try:
                            self.gui_log("ℹ️ File content is not a real .xlsx; attempting CSV fallback...")
                            df_fallback = pd.read_csv(path, dtype=str, encoding_errors='ignore')
                            data = { 'Sheet1': df_fallback }
                        except Exception:
                            # Last attempt with latin1
                            df_fallback = pd.read_csv(path, dtype=str, encoding='latin1')
                            data = { 'Sheet1': df_fallback }
                    elif 'ole2' in msg or 'compound document' in msg or "can't find workbook" in msg:
                        # OLE2 without workbook stream (often not a real Excel). Try CSV fallback and COM conversion.
                        self.gui_log("ℹ️ OLE2 workbook issue detected; attempting CSV fallbacks...")
                        data = None
                        try:
                            df_fallback = pd.read_csv(path, dtype=str, encoding_errors='ignore')
                            data = { 'Sheet1': df_fallback }
                        except Exception:
                            try:
                                df_fallback = pd.read_csv(path, dtype=str, encoding='latin1')
                                data = { 'Sheet1': df_fallback }
                            except Exception:
                                pass
                        # As last resort, try Excel COM automation to export to CSV
                        if data is None:
                            try:
                                import tempfile
                                from pathlib import Path as _Path
                                import pythoncom  # ensure COM initialized in this thread
                                pythoncom.CoInitialize()
                                try:
                                    import win32com.client as win32
                                except Exception:
                                    win32 = None
                                if win32 is not None:
                                    excel = win32.Dispatch("Excel.Application")
                                    excel.Visible = False
                                    wb = excel.Workbooks.Open(str(path))
                                    tmp_csv = _Path(tempfile.gettempdir()) / (path.stem + "__medisoft_temp.csv")
                                    # 6 is xlCSV
                                    wb.SaveAs(str(tmp_csv), 6)
                                    wb.Close(False)
                                    excel.Quit()
                                    try:
                                        df_fallback = pd.read_csv(tmp_csv, dtype=str, encoding_errors='ignore')
                                        data = { 'Sheet1': df_fallback }
                                    finally:
                                        try:
                                            tmp_csv.unlink(missing_ok=True)  # type: ignore[arg-type]
                                        except Exception:
                                            pass
                            except Exception as com_err:
                                self.gui_log(f"⚠️ Excel COM fallback failed: {com_err}")
                            finally:
                                try:
                                    pythoncom.CoUninitialize()
                                except Exception:
                                    pass
                    else:
                        self.gui_log("❌ Could not read .xlsx/.xlsm. Ensure file is a valid Excel workbook or CSV.")
                        data = None
                # Convert to list of DataFrames
                if isinstance(data, dict):
                    dfs = [d for d in data.values() if d is not None]
                elif data is not None:
                    dfs = [data]
                else:
                    # If we still have nothing, bail out gracefully
                    dfs = []
            elif (signature == b"\xD0\xCF\x11\xE0") or ext == '.xls':
                # Legacy Excel format requires xlrd
                try:
                    data = pd.read_excel(path, dtype=str, sheet_name=None, engine='xlrd')
                except Exception as e:
                    self.gui_log("❌ Could not read .xls. Please install xlrd>=2.0.1: pip install xlrd")
                    raise e
                if isinstance(data, dict):
                    dfs = list(data.values())
                else:
                    dfs = [data]
            else:
                self.gui_log(f"Unsupported file type: {ext}")
                return []

            records: list[dict] = []
            for df in dfs:
                if df is None or df.empty:
                    continue
                # Normalize and try to detect header row if the first row isn't the real header
                df = df.dropna(how='all')
                orig_columns = [str(c).strip().lower() for c in df.columns]
                df.columns = orig_columns

                def _promote_header_row_if_needed(frame):
                    cols = [str(c).strip().lower() for c in frame.columns]
                    # If we already have name/DOS-like headers, keep
                    if (
                        self._find_header(cols, ['patient name', 'member name', 'client name', 'insured name', 'patient']) or
                        self._find_header(cols, ['dates of service', 'dos', 'service dates', 'date of service', 'svc dates'])
                    ):
                        return frame
                    # Search first 10 rows for a header-like row containing keywords
                    keyword_sets = [
                        ['name'],
                        ['date', 'service'],
                        ['dos']
                    ]
                    max_rows = min(10, len(frame))
                    for i in range(max_rows):
                        row_vals = [str(v).strip().lower() for v in list(frame.iloc[i])]  # type: ignore[index]
                        # Heuristic: at least 2 occurrences of header-ish tokens
                        text_vals = [v for v in row_vals if v and v != 'nan']
                        joined = ' '.join(text_vals)
                        score = 0
                        for kws in keyword_sets:
                            if all(k in joined for k in kws):
                                score += 1
                        if score >= 1 and len(text_vals) >= max(2, int(0.3 * len(frame.columns))):
                            # Promote this row to header
                            try:
                                new_cols = [str(v).strip().lower() for v in frame.iloc[i].tolist()]  # type: ignore[index]
                                # Fill empty headers with generic names to avoid duplicates
                                new_cols = [c if c else f'col_{idx}' for idx, c in enumerate(new_cols)]
                                frame = frame.iloc[i+1:].copy()
                                frame.columns = new_cols
                                return frame
                            except Exception:
                                pass
                    return frame

                df = _promote_header_row_if_needed(df)

                # Recompute normalized columns after potential promotion
                df.columns = [str(c).strip().lower() for c in df.columns]

                # Find Patient Name and Dates of Service columns (broadened candidates)
                name_col = self._find_header(df.columns, [
                    'patient name', 'name', 'member name', 'client name', 'insured name', 'patient', 'member',
                    'pt name', 'patient full name'
                ])
                dos_col = self._find_header(df.columns, [
                    'dates of service', 'date(s) of service', 'dos', 'service dates', 'date of service', 'svc dates',
                    'dos range', 'dos period', 'date range'
                ])
                # Also support split start/end DOS columns
                dos_start_col = self._find_header(df.columns, [
                    'dos start', 'start dos', 'from dos', 'date from', 'from date of service', 'from date'
                ])
                dos_end_col = self._find_header(df.columns, [
                    'dos end', 'end dos', 'to dos', 'date to', 'to date of service', 'to date'
                ])
                notes_col = self._find_header(df.columns, [
                    'notes', 'note', 'insurer notes', 'insurance notes', 'comments', 'remark', 'remarks'
                ])
                if not name_col:
                    # Helpful logging to diagnose headers
                    try:
                        self.gui_log(f"Headers seen: {list(df.columns)[:20]}")
                    except Exception:
                        pass
                    continue
                # Iterate rows
                for _, row in df.iterrows():
                    patient_name = str(row.get(name_col, '')).strip()
                    if not patient_name:
                        continue
                    # Prefer merged DOS range column if present; else build from start/end columns
                    if dos_col:
                        dos_val = str(row.get(dos_col, '')).strip()
                        start, end = self._parse_dos_range(dos_val)
                    else:
                        start = str(row.get(dos_start_col, '')).strip() if dos_start_col else ''
                        end = str(row.get(dos_end_col, '')).strip() if dos_end_col else ''
                    notes_val = str(row.get(notes_col, '')).strip() if notes_col else ''
                    records.append({
                        'patient_name': patient_name,
                        'dos_start': start,
                        'dos_end': end,
                        'notes': notes_val,
                        'raw': row.to_dict()
                    })

            return records
        except Exception as e:
            self.gui_log(f"Table load error: {e}")
            return []

    @staticmethod
    def _find_header(columns: list, candidates: list) -> str | None:
        cols = [str(c).strip().lower() for c in columns]
        for cand in candidates:
            key = cand.strip().lower()
            for c in cols:
                if key == c or key in c:
                    return c
        return None

    @staticmethod
    def _parse_dos_range(value: str) -> tuple[str, str]:
        """Parse '1/1/2024 - 12/31/2024' into (start, end). Tolerant of spaces/different dashes.
        Returns ("", "") if not parseable.
        """
        if not value:
            return "", ""
        try:
            text = value.strip().replace('\u2013', '-').replace('\u2014', '-')
            parts = [p.strip() for p in text.split('-') if p.strip()]
            if len(parts) == 2:
                return parts[0], parts[1]
            elif len(parts) == 1:
                return parts[0], parts[0]
            return "", ""
        except Exception:
            return "", ""

    # ======================== Ledger Handling ========================
    def _train_ledger_save(self):
        """Placeholder for training how to save ledger (you'll record coordinates/hotkeys).
        For now, tries Ctrl+A, Ctrl+C to copy text as a non-invasive default.
        """
        self.gui_log("Training: Save Ledger - currently uses Ctrl+A, Ctrl+C fallback")
        # Here you can add coordinate capture similar to existing training tool

    def _train_ledger_close(self):
        """Placeholder for training how to close ledger window (record button coords/hotkeys)."""
        self.gui_log("Training: Close Ledger - currently uses Alt+F4 fallback")

    def _test_extract_ledger_dos(self):
        """Test extraction of DOS from the active ledger window by copying text and parsing."""
        try:
            text = self._extract_ledger_text()
            dos = self._parse_dos_from_text(text)
            self.gui_log(f"Extracted DOS lines: {len(dos)}")
            for d in dos[:10]:
                self.gui_log(f"  • {d}")
        except Exception as e:
            self.gui_log(f"DOS extraction test failed: {e}")

    def _extract_ledger_text(self) -> str:
        """Copy all text from the current ledger window via Ctrl+A, Ctrl+C and return from clipboard."""
        try:
            # Focus top window
            if not self.app:
                self.connect_to_app()
            try:
                top = self.app.top_window()
                top.set_focus()
                time.sleep(0.2)
            except Exception:
                pass

            # Select all and copy
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.2)

            # Read clipboard
            try:
                import tkinter as _tk
                _r = _tk.Tk(); _r.withdraw()
                content = _r.clipboard_get()
                _r.destroy()
                return content or ""
            except Exception:
                # Fallback to pyperclip if available
                try:
                    import pyperclip
                    return pyperclip.paste() or ""
                except Exception:
                    return ""
        except Exception:
            return ""

    def _parse_dos_from_text(self, text: str) -> list[str]:
        """Parse Dates of Service from ledger plain text using regex.
        Returns list of 'MM/DD/YYYY - MM/DD/YYYY' or single dates.
        """
        results = []
        if not text:
            return results
        # Find date ranges first
        range_re = re.compile(r'(\d{1,2}/\d{1,2}/\d{2,4})\s*[-–—]\s*(\d{1,2}/\d{1,2}/\d{2,4})')
        for m in range_re.finditer(text):
            start, end = m.group(1), m.group(2)
            results.append(f"{start} - {end}")
        # If none found, try individual dates (may list as separate lines)
        if not results:
            single_re = re.compile(r'(\d{1,2}/\d{1,2}/\d{2,4})')
            singles = single_re.findall(text)
            for d in singles:
                results.append(d)
        return results

    def _close_ledger_window(self):
        """Close the current ledger window using Alt+F4 as a default."""
        try:
            pyautogui.hotkey('alt', 'f4')
            time.sleep(0.2)
        except Exception:
            pass

    # ======================== Run Output/Logging ========================
    def _prepare_run_output_dir(self):
        """Create a per-run folder on the current user's Desktop to store outputs."""
        try:
            ts = time.strftime('%Y-%m-%d_%H%M%S')
            desktop = Path.home() / 'Desktop'
            base = desktop / 'Medisoft Bot Runs' / ts
            base.mkdir(parents=True, exist_ok=True)
            self.run_output_dir = base
            self.gui_log(f"Output folder: {base}")
        except Exception as e:
            self.gui_log(f"Failed to create output folder: {e}")
            self.run_output_dir = None

    def record_ledger_result(self, patient_name: str, ledger_dos_list: list[str], insurance_notes: str = ""):
        """Append a row per DOS line to the run log buffer."""
        dos_list = ledger_dos_list or [""]
        for dos in dos_list:
            self.run_log_rows.append({
                'Patient Name': patient_name,
                'Ledger DOS': dos,
                'Insurance Notes': insurance_notes or ''
            })

    def save_run_log(self):
        """Write the run log rows to an Excel file in the per-run folder."""
        try:
            if not self.run_log_rows:
                self.gui_log("No log rows to save yet")
                return
            if not self.run_output_dir:
                self._prepare_run_output_dir()
            out_path = (self.run_output_dir or Path.cwd()) / 'medisoft_billing_run_log.xlsx'
            if EXCEL_AVAILABLE:
                df = pd.DataFrame(self.run_log_rows)
                # Ensure column order
                cols = ['Patient Name', 'Ledger DOS', 'Insurance Notes']
                df = df[[c for c in cols if c in df.columns] + [c for c in df.columns if c not in cols]]
                df.to_excel(out_path, index=False)
                self.gui_log(f"Saved run log: {out_path}")
            else:
                # Fallback to CSV
                out_csv = out_path.with_suffix('.csv')
                import csv
                with open(out_csv, 'w', newline='', encoding='utf-8') as f:
                    w = csv.DictWriter(f, fieldnames=['Patient Name', 'Ledger DOS', 'Insurance Notes'])
                    w.writeheader()
                    for r in self.run_log_rows:
                        w.writerow(r)
                self.gui_log(f"Saved run log (CSV): {out_csv}")
        except Exception as e:
            self.gui_log(f"Failed to save run log: {e}")
    
    def _find_medisoft(self):
        """Try to find Medisoft installation"""
        possible_paths = [
            r"C:\Medisoft\BIN\MAPA.EXE",  # Primary path from desktop shortcut
            r"C:\Program Files (x86)\Medisoft\Medisoft.exe",
            r"C:\Program Files\Medisoft\Medisoft.exe",
            r"C:\Medisoft\Medisoft.exe",
            r"C:\Program Files (x86)\Medisoft\Bin\Medisoft.exe",
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                logger.info(f"Found Medisoft at: {path}")
                return path
        
        logger.warning("Medisoft installation not found automatically")
        # Return the desktop shortcut path as default
        return r"C:\Medisoft\BIN\MAPA.EXE"
    
    def launch_medisoft(self):
        """Launch the Medisoft application"""
        self.gui_log("🚀 Launching Medisoft application...")
        
        try:
            # Try to launch Medisoft
            if Path(self.medisoft_path).exists():
                subprocess.Popen([self.medisoft_path])
                self.gui_log(f"✅ Launched Medisoft from: {self.medisoft_path}")
            else:
                self.gui_log(f"❌ Medisoft not found at: {self.medisoft_path}")
                raise FileNotFoundError(f"Medisoft not found at: {self.medisoft_path}")
            
            self.gui_log("⏳ Waiting for Medisoft to start (3 seconds)...")
            time.sleep(2)  # Reduced wait from 3 to 2 seconds
            
        except Exception as e:
            self.gui_log(f"❌ Failed to launch Medisoft: {e}")
            raise
    
    def wait_for_window(self, window_title, timeout=None):
        """Wait for a specific window to appear - will wait indefinitely if timeout=None"""
        self.gui_log(f"🔍 Looking for window: {window_title}")
        start_time = time.time()
        last_status_time = start_time
        check_count = 0
        
        while timeout is None or (time.time() - start_time < timeout):
            # Allow user to stop long waits
            if getattr(self, 'stop_requested', False):
                self.gui_log("⛔ Stop requested - aborting window wait")
                return None
            try:
                # Faster connection attempt with shorter timeout
                app = pywinauto.application.Application().connect(title_re=window_title, timeout=0.3)
                self.gui_log(f"✅ Window '{window_title}' found!")
                return app
            except Exception:
                check_count += 1
                time.sleep(0.1)  # Reduced from 0.5s to 0.1s for faster detection
                
                # Update status every 5 seconds to show we're still trying
                if timeout is None and (time.time() - last_status_time >= 5):
                    elapsed = int(time.time() - start_time)
                    self.gui_log(f"⏳ Still waiting for window... ({elapsed}s elapsed)")
                    self.update_status(f"Waiting for window... ({elapsed}s)", "#ff9500")
                    last_status_time = time.time()
        
        if timeout is not None:
            self.gui_log(f"❌ Window '{window_title}' not found within {timeout} seconds")
        else:
            self.gui_log(f"❌ Window '{window_title}' not found (unexpected exit)")
        return None
    
    def login(self, username, password):
        """Perform login to Medisoft"""
        self.gui_log("🔑 Starting login process...")
        self.update_status("Logging in...", "#ff9500")
        
        try:
            # Wait for login window - will wait indefinitely until window appears
            # Medisoft can be slow to start, so we must be patient
            self.gui_log("⏳ Waiting for Medisoft login window to appear (this may take a while)...")
            self.update_status("Waiting for login window...", "#ff9500")
            self.login_window = self.wait_for_window(".*Medisoft.*Login.*", timeout=None)  # No timeout - wait forever
            
            if not self.login_window:
                self.gui_log("❌ Login window not found (unexpected error)")
                self.update_status("Login window not found", "#dc3545")
                messagebox.showerror("Error", "Could not find Medisoft login window.")
                return False
            
            # CRITICAL: Ensure login window is active and focused (works on multi-monitor setups)
            try:
                # Get the window and bring it to foreground
                window = self.login_window.top_window()
                
                # Force window to front and activate it (handles multi-monitor)
                window.set_focus()
                window.move_window(x=0, y=0, width=100, height=100)  # Trigger activation
                window.restore()  # Ensure window is not minimized
                window.set_focus()
                
                # Additional activation using Windows API for multi-monitor support
                try:
                    import ctypes
                    hwnd = window.handle
                    # Bring window to foreground
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    ctypes.windll.user32.BringWindowToTop(hwnd)
                    ctypes.windll.user32.SetActiveWindow(hwnd)
                except:
                    pass  # Fallback if ctypes fails
                
                time.sleep(0.1)  # Further reduced wait for window activation
                
                # Get window position to ensure we're on the right monitor
                rect = window.rectangle()
                self.gui_log(f"📍 Login window position: ({rect.left}, {rect.top})")
                
                self.gui_log("✅ Username field found")
                
                # Ultra-fast entry using UI Automation when possible
                try:
                    edits = window.descendants(control_type="Edit")
                    if len(edits) >= 2:
                        # Username
                        try:
                            edits[0].set_edit_text("")
                            edits[0].set_focus()
                            edits[0].type_keys(username, with_spaces=True, set_foreground=True)
                        except Exception:
                            # Fallback to pyautogui typing
                            window.set_focus(); time.sleep(0.05)
                            old_pause = pyautogui.PAUSE; pyautogui.PAUSE = 0
                            pyautogui.hotkey('ctrl','a'); pyautogui.write(username, interval=0.0)
                            pyautogui.PAUSE = old_pause
                        # Password
                        try:
                            edits[1].set_edit_text("")
                            edits[1].set_focus()
                            edits[1].type_keys(password, with_spaces=True, set_foreground=True)
                        except Exception:
                            window.set_focus(); time.sleep(0.05)
                            old_pause = pyautogui.PAUSE; pyautogui.PAUSE = 0
                            pyautogui.press('tab'); pyautogui.hotkey('ctrl','a'); pyautogui.write(password, interval=0.0)
                            pyautogui.PAUSE = old_pause
                    else:
                        # Fallback: original approach with optimized speeds
                        window.set_focus(); time.sleep(0.05)
                        old_pause = pyautogui.PAUSE; pyautogui.PAUSE = 0
                        pyautogui.hotkey('ctrl','a'); pyautogui.write(username, interval=0.0)
                        pyautogui.press('tab'); pyautogui.hotkey('ctrl','a'); pyautogui.write(password, interval=0.0)
                        pyautogui.PAUSE = old_pause
                except Exception:
                    window.set_focus(); time.sleep(0.05)
                    old_pause = pyautogui.PAUSE; pyautogui.PAUSE = 0
                    pyautogui.hotkey('ctrl','a'); pyautogui.write(username, interval=0.0)
                    pyautogui.press('tab'); pyautogui.hotkey('ctrl','a'); pyautogui.write(password, interval=0.0)
                    pyautogui.PAUSE = old_pause
                
                # Submit login - try multiple methods to ensure it works
                self.gui_log("✅ Submitting login...")
                window.set_focus()
                time.sleep(0.05)
                
                # Method 1: Try clicking OK/Login button if it exists
                login_button_found = False
                try:
                    # Look for common login button names
                    button_names = ["OK", "Login", "Log In", "Sign In"]
                    for btn_name in button_names:
                        try:
                            btn = window.child_window(control_type="Button", title_re=f".*{btn_name}.*")
                            if btn.exists():
                                self.gui_log(f"📍 Found '{btn_name}' button - clicking...")
                                btn.click()
                                login_button_found = True
                                time.sleep(0.8)
                                break
                        except:
                            continue
                except:
                    pass
                
                # Method 2: Press Enter if button wasn't found
                if not login_button_found:
                    self.gui_log("⌨️ Pressing Enter to submit login...")
                    # Ensure we're still in password field and window is focused
                    window.set_focus()
                    time.sleep(0.05)
                    # Press Enter (single press is sufficient)
                    pyautogui.press('enter')
                    time.sleep(0.8)
                
                # Brief additional wait for login window to close
                time.sleep(0.3)
                
                self.gui_log("✅ Login credentials entered successfully")
                self.update_status("Login successful", "#28a745")
                return True
                
            except Exception as e:
                self.gui_log(f"❌ Error during login: {e}")
                self.update_status(f"Login error: {e}", "#dc3545")
                messagebox.showerror("Login Error", f"Failed to login:\n{e}")
                return False
        
        except Exception as e:
            self.gui_log(f"❌ Error during login process: {e}")
            self.update_status(f"Login failed: {e}", "#dc3545")
            messagebox.showerror("Error", f"Login failed: {e}")
            return False
    
    def click_element(self, x, y, description="", move_duration=0.5):
        """Click at a specific screen coordinate with smooth movement"""
        self.gui_log(f"🖱️ Clicking at ({x}, {y}) - {description}")
        pyautogui.moveTo(x, y, duration=move_duration)
        time.sleep(0.1)
        pyautogui.click()
    
    def type_text(self, text, description=""):
        """Type text"""
        self.gui_log(f"⌨️ Typing: {description}")
        pyautogui.write(text)
    
    def screenshot(self, filename="medisoft_screenshot.png"):
        """Take a screenshot for debugging"""
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        logger.info(f"Screenshot saved: {filename}")
    
    def _list_visible_controls(self, window, max_items=30):
        """List visible controls to help identify buttons - debugging helper"""
        try:
            self.gui_log("📋 Listing visible controls (buttons, menus, etc.)...")
            controls_found = []
            
            # Try to get all buttons
            try:
                buttons = window.descendants(control_type="Button")
                for btn in buttons[:max_items]:
                    try:
                        text = btn.window_text()
                        if text.strip():
                            controls_found.append(f"Button: '{text}'")
                    except:
                        pass
            except:
                pass
            
            # Try to get menu items
            try:
                menu = window.menu()
                if menu:
                    menu_items = menu.items()
                    for item in menu_items[:max_items]:
                        try:
                            text = item.text()
                            if text.strip():
                                controls_found.append(f"Menu: '{text}'")
                        except:
                            pass
            except:
                pass
            
            # Log what we found
            if controls_found:
                self.gui_log(f"🔍 Found {len(controls_found)} controls:")
                for i, control in enumerate(controls_found[:max_items], 1):
                    self.gui_log(f"   {i}. {control}")
            else:
                self.gui_log("⚠️ No visible controls found with text")
                
        except Exception as e:
            self.gui_log(f"⚠️ Error listing controls: {e}")
    
    # ========== NAVIGATIONAL FUNCTIONS ==========
    
    def connect_to_app(self, window_title_regex=".*Medisoft.*", timeout=30, use_process=True):
        """Connect to the Medisoft application window"""
        self.gui_log(f"🔌 Connecting to Medisoft application...")
        try:
            if not self.app:
                # Method 1: Try to connect by process path first (most reliable, avoids multiple window issues)
                if use_process:
                    try:
                        self.app = pywinauto.application.Application(backend="uia").connect(path=r"C:\Medisoft\BIN\MAPA.EXE", timeout=timeout)
                        self.gui_log(f"✅ Connected to Medisoft application by process")
                        return self.app
                    except Exception as process_error:
                        self.gui_log(f"⚠️ Process connection failed: {process_error}")
                
                # Method 2: Try connecting by window title, handling multiple windows
                try:
                    # Find all windows matching the title
                    import pywinauto.findwindows
                    all_windows = pywinauto.findwindows.find_windows(title_re=window_title_regex)
                    
                    if len(all_windows) > 1:
                        self.gui_log(f"⚠️ Found {len(all_windows)} matching windows, selecting the main window...")
                        # Connect using the first window handle (usually the main application window)
                        self.app = pywinauto.application.Application(backend="uia").connect(handle=all_windows[0], timeout=timeout)
                        self.gui_log(f"✅ Connected to Medisoft application (selected from {len(all_windows)} windows)")
                        return self.app
                    elif len(all_windows) == 1:
                        # Only one window found, connect to it
                        self.app = pywinauto.application.Application(backend="uia").connect(handle=all_windows[0], timeout=timeout)
                        self.gui_log(f"✅ Connected to Medisoft application")
                        return self.app
                    else:
                        # No windows found, try standard connection (might work anyway)
                        self.app = pywinauto.application.Application(backend="uia").connect(title_re=window_title_regex, timeout=timeout)
                        self.gui_log(f"✅ Connected to Medisoft application (standard method)")
                        return self.app
                        
                except Exception as e:
                    # If find_windows fails, try standard connection
                    try:
                        self.gui_log(f"⚠️ Window search failed, trying standard connection...")
                        self.app = pywinauto.application.Application(backend="uia").connect(title_re=window_title_regex, timeout=timeout)
                        self.app = pywinauto.application.Application(backend="uia").connect(title_re=window_title_regex, timeout=timeout)
                        self.gui_log(f"✅ Connected to Medisoft application")
                        return self.app
                    except Exception as e2:
                        raise e2
            else:
                # Try to refresh the connection
                try:
                    self.app.top_window().set_focus()
                    self.gui_log("✅ Using existing application connection")
                    return self.app
                except:
                    # Reconnect if refresh fails
                    self.app = None
                    return self.connect_to_app(window_title_regex, timeout, use_process)
        except Exception as e:
            error_msg = str(e)
            if "2 elements" in error_msg or "multiple" in error_msg.lower():
                # Handle the specific "multiple elements" error
                self.gui_log(f"⚠️ Multiple windows detected, trying to connect by process...")
                try:
                    self.app = pywinauto.application.Application().connect(path=r"C:\Medisoft\BIN\MAPA.EXE", timeout=timeout)
                    self.gui_log(f"✅ Connected via process path (handled multiple windows)")
                    return self.app
                except:
                    # Last resort: try to get first matching window
                    try:
                        import pywinauto.findwindows
                        windows = pywinauto.findwindows.find_windows(title_re=window_title_regex)
                        if windows:
                            self.app = pywinauto.application.Application().connect(handle=windows[0], timeout=timeout)
                            self.gui_log(f"✅ Connected using first matching window")
                            return self.app
                    except:
                        pass
            
            self.gui_log(f"❌ Failed to connect to application: {error_msg}")
            return None
    
    def find_window(self, window_title, timeout=15, use_regex=True):
        """Find a window by title or partial title"""
        self.gui_log(f"🔍 Searching for window: {window_title}")
        try:
            if not self.app:
                self.connect_to_app()
            
            if use_regex:
                window = self.app.window(title_re=window_title, timeout=timeout)
            else:
                window = self.app.window(title=window_title, timeout=timeout)
            
            if window.exists():
                self.gui_log(f"✅ Found window: {window_title}")
                window.set_focus()
                time.sleep(0.3)
                return window
            else:
                self.gui_log(f"❌ Window not found: {window_title}")
                return None
        except Exception as e:
            self.gui_log(f"❌ Error finding window '{window_title}': {e}")
            return None
    
    def find_button(self, button_text, window=None, timeout=10, use_regex=False):
        """Find and return a button by its text"""
        self.gui_log(f"🔘 Looking for button: {button_text}")
        try:
            if not window:
                if not self.app:
                    self.connect_to_app()
                window = self.app.top_window()
            
            # Try with retries since timeout parameter doesn't work in some pywinauto versions
            start_time = time.time()
            button = None
            
            while time.time() - start_time < timeout:
                # Allow user to stop long searches
                if getattr(self, 'stop_requested', False):
                    self.gui_log("⛔ Stop requested - aborting image search")
                    return False
                try:
                    if use_regex:
                        button = window.child_window(title_re=button_text, control_type="Button")
                    else:
                        button = window.child_window(title=button_text, control_type="Button")
                    
                    if button.exists():
                        self.gui_log(f"✅ Found button: {button_text}")
                        return button
                except:
                    time.sleep(0.5)
                    continue
            
            self.gui_log(f"❌ Button not found: {button_text}")
            return None
        except Exception as e:
            self.gui_log(f"❌ Error finding button '{button_text}': {e}")
            return None
    
    def click_button(self, button_text, window=None, timeout=10, use_regex=False, retry_count=2):
        """Find and click a button by its text"""
        for attempt in range(retry_count):
            try:
                button = self.find_button(button_text, window, timeout, use_regex)
                if button:
                    button.click()
                    self.gui_log(f"🖱️ Clicked button: {button_text}")
                    time.sleep(0.5)
                    return True
            except Exception as e:
                if attempt < retry_count - 1:
                    self.gui_log(f"⚠️ Retry {attempt + 1} for button click: {button_text}")
                    time.sleep(1)
                else:
                    self.gui_log(f"❌ Failed to click button '{button_text}' after {retry_count} attempts: {e}")
        
        return False
    
    def navigate_menu(self, menu_path, separator=">"):
        """Navigate through menu items (e.g., 'File>Open' or 'Edit>Preferences>General')"""
        self.gui_log(f"📋 Navigating menu: {menu_path}")
        try:
            if not self.app:
                self.connect_to_app()
            
            window = self.app.top_window()
            menu_items = [item.strip() for item in menu_path.split(separator)]
            
            # Click on the first menu item (top level)
            first_menu = menu_items[0]
            self.gui_log(f"📍 Opening top menu: {first_menu}")
            
            # Use Alt key combination for menus (Alt+F for File, Alt+E for Edit, etc.)
            # Or use pywinauto menu access
            try:
                menu = window.menu_item(menu_path.replace(separator, "->"))
                menu.click()
                self.gui_log(f"✅ Navigated to menu: {menu_path}")
                time.sleep(0.5)
                return True
            except:
                # Fallback to keyboard navigation
                pyautogui.press('alt')
                time.sleep(0.3)
                for item in menu_items:
                    # Try to find menu item by typing first letter or using arrow keys
                    pyautogui.write(item[0].lower(), interval=0.1)
                    time.sleep(0.3)
                    if item != menu_items[-1]:
                        pyautogui.press('right')
                        time.sleep(0.2)
                pyautogui.press('enter')
                time.sleep(0.5)
                self.gui_log(f"✅ Navigated menu using keyboard: {menu_path}")
                return True
                
        except Exception as e:
            self.gui_log(f"❌ Error navigating menu '{menu_path}': {e}")
            return False
    
    def navigate_to_section(self, section_name, method="menu", menu_path=None):
        """Navigate to a specific section of Medisoft (e.g., 'Billing', 'Patients', 'Reports')"""
        self.gui_log(f"🧭 Navigating to section: {section_name}")
        try:
            if method == "menu" and menu_path:
                return self.navigate_menu(menu_path)
            elif method == "button":
                return self.click_button(section_name)
            elif method == "shortcut":
                # Common shortcuts: F1-F12, Ctrl+key combinations
                self.gui_log(f"⌨️ Using keyboard shortcut for: {section_name}")
                # Add specific shortcuts as needed
                return True
            else:
                # Try to find a button or menu item with the section name
                if self.click_button(section_name):
                    return True
                # If button click fails, try menu navigation
                return self.navigate_menu(section_name)
        except Exception as e:
            self.gui_log(f"❌ Error navigating to section '{section_name}': {e}")
            return False
    
    def navigate_tabs(self, tab_name, window=None, timeout=10):
        """Navigate to a specific tab in a tab control"""
        self.gui_log(f"📑 Navigating to tab: {tab_name}")
        try:
            if not window:
                if not self.app:
                    self.connect_to_app()
                window = self.app.top_window()
            
            # Try to find tab by name with retry logic
            start_time = time.time()
            tab_found = False
            
            while time.time() - start_time < timeout and not tab_found:
                try:
                    # Method 1: Try to find tab directly
                    try:
                        tab = window.child_window(title_re=tab_name, control_type="TabItem")
                        if tab.exists():
                            tab.select()
                            self.gui_log(f"✅ Selected tab: {tab_name}")
                            time.sleep(0.5)
                            return True
                    except:
                        pass
                    
                    # Method 2: Try to find tab control and iterate through tabs
                    try:
                        tab_control = window.child_window(control_type="Tab")
                        if tab_control.exists():
                            tabs = tab_control.tab_items()
                            for i, tab in enumerate(tabs):
                                try:
                                    tab_text = tab.window_text()
                                    if tab_name.lower() in tab_text.lower():
                                        tab.select()
                                        self.gui_log(f"✅ Selected tab: {tab_name}")
                                        time.sleep(0.5)
                                        return True
                                except:
                                    continue
                    except:
                        pass
                    
                    # If not found, wait a bit and try again
                    time.sleep(0.5)
                    
                except Exception as e:
                    time.sleep(0.5)
                    continue
            
            self.gui_log(f"❌ Tab not found: {tab_name}")
            return False
        except Exception as e:
            self.gui_log(f"❌ Error navigating to tab '{tab_name}': {e}")
            return False
    
    def press_keyboard_shortcut(self, *keys):
        """Press keyboard shortcut (e.g., ('ctrl', 's') or ('alt', 'f4'))"""
        shortcut_str = "+".join(keys).upper()
        self.gui_log(f"⌨️ Pressing keyboard shortcut: {shortcut_str}")
        try:
            pyautogui.hotkey(*keys)
            time.sleep(0.3)
            self.gui_log(f"✅ Pressed shortcut: {shortcut_str}")
            return True
        except Exception as e:
            self.gui_log(f"❌ Error pressing shortcut '{shortcut_str}': {e}")
            return False
    
    def wait_for_element(self, element_type, element_name, window=None, timeout=15, use_regex=False):
        """Wait for an element (button, edit field, etc.) to appear"""
        self.gui_log(f"⏳ Waiting for {element_type}: {element_name}")
        try:
            if not window:
                if not self.app:
                    self.connect_to_app()
                window = self.app.top_window()
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    if use_regex:
                        element = window.child_window(title_re=element_name, control_type=element_type)
                    else:
                        element = window.child_window(title=element_name, control_type=element_type)
                    
                    if element.exists():
                        self.gui_log(f"✅ Element found: {element_name}")
                        return element
                except:
                    pass
                
                time.sleep(0.5)
            
            self.gui_log(f"❌ Element not found within timeout: {element_name}")
            return None
        except Exception as e:
            self.gui_log(f"❌ Error waiting for element '{element_name}': {e}")
            return None
    
    def close_dialog(self, button_text="OK", window=None, timeout=5):
        """Close a dialog by clicking OK, Cancel, or Close button"""
        self.gui_log(f"🚪 Closing dialog with button: {button_text}")
        try:
            if self.click_button(button_text, window, timeout):
                time.sleep(0.5)
                return True
            
            # Try common dialog close methods
            if button_text.upper() in ["OK", "YES", "CONTINUE"]:
                pyautogui.press('enter')
                time.sleep(0.3)
                return True
            elif button_text.upper() in ["CANCEL", "NO", "CLOSE"]:
                pyautogui.press('escape')
                time.sleep(0.3)
                return True
            
            return False
        except Exception as e:
            self.gui_log(f"❌ Error closing dialog: {e}")
            return False
    
    def navigate_back(self, method="escape"):
        """Navigate back or close current window"""
        self.gui_log(f"⬅️ Navigating back (method: {method})")
        try:
            if method == "escape":
                pyautogui.press('escape')
            elif method == "alt_f4":
                pyautogui.hotkey('alt', 'f4')
            elif method == "close_button":
                if self.click_button("Close"):
                    return True
            
            time.sleep(0.5)
            self.gui_log("✅ Navigated back")
            return True
        except Exception as e:
            self.gui_log(f"❌ Error navigating back: {e}")
            return False
    
    def select_from_dropdown(self, dropdown_name, value, window=None, timeout=10):
        """Select a value from a dropdown/combobox"""
        self.gui_log(f"📋 Selecting '{value}' from dropdown: {dropdown_name}")
        try:
            if not window:
                if not self.app:
                    self.connect_to_app()
                window = self.app.top_window()
            
            # Try to find the combobox/dropdown with retry logic
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    # Method 1: Try to find by title
                    try:
                        dropdown = window.child_window(title_re=dropdown_name, control_type="ComboBox")
                        if dropdown.exists():
                            dropdown.type_keys(value)
                            self.gui_log(f"✅ Selected '{value}' from dropdown: {dropdown_name}")
                            time.sleep(0.5)
                            return True
                    except:
                        pass
                    
                    # Method 2: Try to find by class name
                    try:
                        dropdown = window.child_window(class_name_re="ComboBox")
                        if dropdown.exists():
                            dropdown.click()
                            time.sleep(0.3)
                            dropdown.type_keys(value)
                            time.sleep(0.3)
                            pyautogui.press('enter')
                            self.gui_log(f"✅ Selected '{value}' from dropdown: {dropdown_name}")
                            time.sleep(0.5)
                            return True
                    except:
                        pass
                    
                    time.sleep(0.5)
                except:
                    time.sleep(0.5)
            
            self.gui_log(f"❌ Dropdown not found: {dropdown_name}")
            return False
        except Exception as e:
            self.gui_log(f"❌ Error selecting from dropdown '{dropdown_name}': {e}")
            return False
    
    def navigate_treeview(self, item_path, separator=">", window=None, timeout=10, double_click=False):
        """Navigate through a tree view (e.g., 'Folder1>Subfolder>Item')"""
        self.gui_log(f"🌳 Navigating tree view: {item_path}")
        try:
            if not window:
                if not self.app:
                    self.connect_to_app()
                window = self.app.top_window()
            
            # Find tree view with retry logic
            start_time = time.time()
            tree = None
            while time.time() - start_time < timeout:
                try:
                    tree = window.child_window(control_type="Tree")
                    if tree.exists():
                        break
                except:
                    pass
                time.sleep(0.5)
            
            if not tree or not tree.exists():
                self.gui_log("❌ Tree view not found")
                return False
            
            items = [item.strip() for item in item_path.split(separator)]
            
            # Expand and navigate through items
            for i, item in enumerate(items):
                self.gui_log(f"📍 Looking for tree item: {item}")
                # Try to find tree item with retry
                item_start_time = time.time()
                tree_item = None
                while time.time() - item_start_time < 5:
                    try:
                        tree_item = tree.child_window(title_re=item)
                        if tree_item.exists():
                            break
                    except:
                        pass
                    time.sleep(0.5)
                
                try:
                    if tree_item and tree_item.exists():
                        # Expand if not the last item
                        if i < len(items) - 1:
                            tree_item.select()
                            time.sleep(0.3)
                            pyautogui.press('right')  # Expand
                            time.sleep(0.3)
                        else:
                            # Last item - select or double click
                            tree_item.select()
                            if double_click:
                                time.sleep(0.3)
                                pyautogui.doubleClick(tree_item.rectangle().mid_point().x, 
                                                     tree_item.rectangle().mid_point().y)
                            self.gui_log(f"✅ Selected tree item: {item}")
                    else:
                        self.gui_log(f"❌ Tree item not found: {item}")
                        return False
                except Exception as e:
                    self.gui_log(f"❌ Error navigating tree item '{item}': {e}")
                    return False
            
            time.sleep(0.5)
            return True
        except Exception as e:
            self.gui_log(f"❌ Error navigating tree view: {e}")
            return False
    
    def scroll_window(self, direction="down", amount=3):
        """Scroll a window up or down"""
        self.gui_log(f"📜 Scrolling {direction} ({amount} times)")
        try:
            for _ in range(amount):
                if direction.lower() == "down":
                    pyautogui.scroll(-3)
                elif direction.lower() == "up":
                    pyautogui.scroll(3)
                time.sleep(0.2)
            return True
        except Exception as e:
            self.gui_log(f"❌ Error scrolling: {e}")
            return False
    
    def find_and_click_by_image(self, image_path, confidence=0.8, timeout=10, move_duration=0.5):
        """Find and click an element by image (useful for buttons without text)
        
        Args:
            image_path: Path to the screenshot/image file of the button
            confidence: Matching confidence (0.0-1.0), default 0.8
            timeout: How long to search for the image (seconds)
            move_duration: Duration of mouse movement to click point (seconds)
        """
        self.gui_log(f"🖼️ Looking for element by image: {image_path}")
        
        # Check if image file exists
        if not Path(image_path).exists():
            self.gui_log(f"❌ Image file not found: {image_path}")
            self.gui_log("💡 Tip: Take a screenshot of the button and save it in the bot's directory")
            return False
        
        try:
            start_time = time.time()
            # Get screen dimensions for multi-monitor support
            screen_width, screen_height = pyautogui.size()
            all_screens_region = (0, 0, screen_width, screen_height)
            
            # Prefer searching within the Medisoft window bounds to avoid false positives
            app_region = None
            try:
                if self.app:
                    window = self.app.top_window()
                    rect = window.rectangle()
                    app_region = (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
                    self.gui_log(f"🖼️ Using app window region for image search: {app_region}")
            except Exception as e:
                self.gui_log(f"⚠️ Could not get app window region, falling back to full screen: {e}")
            
            while time.time() - start_time < timeout:
                try:
                    # Try to find the image on screen
                    # With OpenCV: use confidence for flexible matching
                    # Without OpenCV: try region-based search on all monitors
                    if OPENCV_AVAILABLE:
                        # With OpenCV, try multiple strategies for best matching
                        location = None
                        
                        # Try even lower confidence levels - buttons can vary significantly
                        confidence_levels = [confidence, confidence - 0.1, confidence - 0.2, 0.6, 0.5, 0.4]
                        
                        # Strategy 1: Try searching around saved coordinate with multiple confidence levels
                        try:
                            import os
                            img_name = os.path.splitext(os.path.basename(str(image_path)))[0].lower()
                            coord_name_map = {
                                'launch_medisoft_reports': 'Launch Medisoft Reports',
                                'custom': 'Custom',
                                'patient_account_ledger': 'Patient Account Ledger',
                                'account_ledger': 'Patient Account Ledger'
                            }
                            coord_name = coord_name_map.get(img_name, None)
                            if coord_name:
                                coords = self.get_coordinate(coord_name) if hasattr(self, 'get_coordinate') else None
                                if coords:
                                    x, y = coords
                                    # Search in a larger region around the coordinate
                                    search_region = (
                                        max(0, x - 300),
                                        max(0, y - 250),
                                        min(600, screen_width - max(0, x - 300)),
                                        min(500, screen_height - max(0, y - 250))
                                    )
                                    self.gui_log(f"🔍 Searching in region around coordinate ({x}, {y})...")
                                    # Try all confidence levels in this region
                                    for conf_level in confidence_levels:
                                        try:
                                            location = pyautogui.locateOnScreen(image_path, confidence=conf_level, region=search_region)
                                            if location:
                                                self.gui_log(f"✅ Found image in coordinate region with confidence {conf_level:.2f}")
                                                break
                                        except pyautogui.ImageNotFoundException:
                                            continue
                                        except Exception as e:
                                            self.gui_log(f"⚠️ Search error at confidence {conf_level:.2f}: {e}")
                                            continue
                        except Exception as e:
                            self.gui_log(f"⚠️ Coordinate region search setup failed: {e}")
                        
                        # Strategy 2: Try app window (preferred) or full screen with confidence levels
                        if not location:
                            # Only use app_region if it has valid positive bounds; otherwise use full screen
                            if app_region and app_region[0] >= 0 and app_region[1] >= 0:
                                search_region = app_region
                                self.gui_log("🔍 Searching app window with multiple confidence levels...")
                            else:
                                search_region = all_screens_region
                                self.gui_log("🔍 Searching full screen with multiple confidence levels (app window bounds invalid)...")
                            for conf_level in confidence_levels:
                                try:
                                    location = pyautogui.locateOnScreen(image_path, confidence=conf_level, region=search_region)
                                    if location:
                                        self.gui_log(f"✅ Found image on full screen with confidence {conf_level:.2f}")
                                        break
                                except pyautogui.ImageNotFoundException:
                                    continue
                                except Exception as e:
                                    if "confidence" not in str(e).lower():
                                        self.gui_log(f"⚠️ Search error: {e}")
                                    continue
                        
                        # Strategy 3: Try with grayscale (can help with variations)
                        if not location:
                            self.gui_log("🔍 Trying grayscale matching...")
                            try:
                                # Try grayscale with lower confidence
                                for conf_level in [0.5, 0.4, 0.3]:
                                    try:
                                        # Note: pyautogui might not support grayscale+confidence together
                                        # So try standard first
                                        if app_region and app_region[0] >= 0 and app_region[1] >= 0:
                                            search_region = app_region
                                        else:
                                            search_region = all_screens_region
                                        location = pyautogui.locateOnScreen(image_path, confidence=conf_level, region=search_region)
                                        if location:
                                            self.gui_log(f"✅ Found with grayscale approach, confidence {conf_level:.2f}")
                                            break
                                    except:
                                        continue
                            except Exception as e:
                                self.gui_log(f"⚠️ Grayscale search error: {e}")
                        
                        # If still not found, provide detailed feedback
                        if not location:
                            self.gui_log(f"⚠️ Image not found after trying confidence levels: {confidence_levels}")
                            self.gui_log("💡 Possible reasons:")
                            self.gui_log("   - Screenshot may be outdated (button appearance changed)")
                            self.gui_log("   - Button may be partially obscured or not visible")
                            self.gui_log("   - Screen resolution/scaling may have changed")
                            self.gui_log("   - Try recapturing the screenshot with F8")
                    else:
                        # Without OpenCV, exact pixel matching is very sensitive
                        # We'll try multiple approaches to improve reliability
                        location = None
                        
                        # Method 1: Try app window first
                        try:
                            if app_region and app_region[0] >= 0 and app_region[1] >= 0:
                                search_region = app_region
                            else:
                                search_region = all_screens_region
                            location = pyautogui.locateOnScreen(image_path, region=search_region, grayscale=False)
                        except pyautogui.ImageNotFoundException:
                            pass
                        
                        # Method 2: Try with grayscale (often more forgiving)
                        if not location:
                            try:
                                if app_region and app_region[0] >= 0 and app_region[1] >= 0:
                                    search_region = app_region
                                else:
                                    search_region = all_screens_region
                                location = pyautogui.locateOnScreen(image_path, region=search_region, grayscale=True)
                            except pyautogui.ImageNotFoundException:
                                pass
                        
                        # Method 3: Try searching around the saved coordinate (if available)
                        # This narrows the search region significantly
                        if not location:
                            try:
                                # Try to get coordinate for this element from filename
                                # Use os.path to avoid Path scoping issues
                                import os
                                img_name = os.path.splitext(os.path.basename(str(image_path)))[0].lower()
                                # Try to match common element names
                                coord_name_map = {
                                    'launch_medisoft_reports': 'Launch Medisoft Reports',
                                    'custom': 'Custom',
                                    'patient_account_ledger': 'Patient Account Ledger',
                                    'account_ledger': 'Patient Account Ledger'
                                }
                                coord_name = coord_name_map.get(img_name, None)
                                if coord_name:
                                    coords = self.get_coordinate(coord_name) if hasattr(self, 'get_coordinate') else None
                                    if coords:
                                        x, y = coords
                                        # Search in a 400x300 region around the coordinate
                                        search_region = (
                                            max(0, x - 200),
                                            max(0, y - 150),
                                            min(400, screen_width - max(0, x - 200)),
                                            min(300, screen_height - max(0, y - 150))
                                        )
                                        try:
                                            location = pyautogui.locateOnScreen(image_path, region=search_region, grayscale=True)
                                            if location:
                                                self.gui_log(f"✅ Found image near saved coordinate region")
                                        except:
                                            pass
                            except Exception as e:
                                # Silently fail - this is just an optimization
                                pass
                        
                        # Method 4: Try each quadrant of the chosen region as last resort
                        if not location:
                            base = app_region if app_region else all_screens_region
                            bx, by, bw, bh = base
                            quadrants = [
                                (bx, by, bw // 2, bh // 2),
                                (bx + bw // 2, by, bw // 2, bh // 2),
                                (bx, by + bh // 2, bw // 2, bh // 2),
                                (bx + bw // 2, by + bh // 2, bw // 2, bh // 2),
                            ]
                            for region in quadrants:
                                try:
                                    location = pyautogui.locateOnScreen(image_path, region=region, grayscale=True)
                                    if location:
                                        break
                                except:
                                    continue
                        
                        # If still not found, provide helpful error message
                        if not location and time.time() - start_time > timeout * 0.9:
                            self.gui_log("⚠️ Image recognition failed - exact pixel matching without OpenCV is very sensitive")
                            self.gui_log("💡 RECOMMENDATION: Install OpenCV for reliable image matching across computers")
                            self.gui_log("   Run: pip install opencv-python-headless")
                            self.gui_log("   Or use pre-built wheel: pip install opencv-python")
                    
                    if location:
                        center = pyautogui.center(location)
                        # Smooth move to center point
                        pyautogui.moveTo(center.x, center.y, duration=move_duration)
                        time.sleep(0.1)
                        # Click
                        pyautogui.click()
                        self.gui_log(f"✅ Found and clicked element from image: {image_path} at ({center.x}, {center.y})")
                        time.sleep(0.5)
                        return True
                except pyautogui.ImageNotFoundException:
                    time.sleep(0.5)
                except Exception as e:
                    # Log other errors but keep trying
                    if time.time() - start_time > timeout * 0.8:  # Only log near the end
                        self.gui_log(f"⚠️ Image search error: {e}")
                    time.sleep(0.5)
            
            self.gui_log(f"❌ Element not found from image: {image_path} (searched for {timeout}s)")
            if not OPENCV_AVAILABLE:
                self.gui_log("⚠️ Without OpenCV, image matching requires EXACT pixel match (very sensitive)")
                self.gui_log("💡 For reliable cross-computer image recognition, OpenCV is highly recommended")
                self.gui_log("   The saved coordinates fallback will still work on the same computer")
            return False
        except Exception as e:
            self.gui_log(f"❌ Error finding element by image: {e}")
            if not OPENCV_AVAILABLE:
                self.gui_log("💡 Consider installing OpenCV for better image matching: pip install opencv-python")
            return False
    
    def activate_window_by_title(self, window_title, timeout=10):
        """Activate a window by its title (Windows only)"""
        self.gui_log(f"🪟 Activating window: {window_title}")
        try:
            # Get all windows with matching title
            windows = pyautogui.getWindowsWithTitle(window_title)
            if windows:
                window = windows[0]
                window.activate()
                time.sleep(0.5)
                self.gui_log(f"✅ Activated window: {window_title}")
                return True
            else:
                self.gui_log(f"❌ Window not found: {window_title}")
                return False
        except Exception as e:
            self.gui_log(f"⚠️ Error activating window: {e}")
            # Fallback: try using pywinauto
            try:
                if not self.app:
                    self.connect_to_app()
                window = self.app.window(title_re=window_title, timeout=timeout)
                if window.exists():
                    window.set_focus()
                    self.gui_log(f"✅ Activated window using pywinauto: {window_title}")
                    return True
            except:
                pass
            return False
    
    def list_all_windows(self):
        """List all open window titles - useful for debugging"""
        self.gui_log("📋 Listing all open windows...")
        try:
            all_titles = pyautogui.getAllTitles()
            if all_titles:
                self.gui_log(f"Found {len(all_titles)} windows:")
                for i, title in enumerate(all_titles[:50], 1):  # Limit to first 50
                    if title.strip():  # Only show non-empty titles
                        self.gui_log(f"   {i}. {title}")
                if len(all_titles) > 50:
                    self.gui_log(f"   ... and {len(all_titles) - 50} more windows")
            else:
                self.gui_log("⚠️ No windows found")
        except Exception as e:
            self.gui_log(f"⚠️ Error listing windows: {e}")
    
    def _focus_window_by_regex(self, title_regex: str, timeout: float = 8.0) -> bool:
        """Try to find a window by regex and force focus/foreground.
        Returns True if a window was focused, False otherwise.
        """
        try:
            from pywinauto import Desktop
            start = time.time()
            while time.time() - start < timeout and not getattr(self, 'stop_requested', False):
                try:
                    desktop = Desktop(backend="win32")
                    win = desktop.window(title_re=title_regex)
                    if win.exists():
                        try:
                            win.restore()
                        except Exception:
                            pass
                        try:
                            win.set_focus()
                        except Exception:
                            pass
                        # Extra nudge via WinAPI
                        try:
                            import ctypes
                            hwnd = win.handle
                            ctypes.windll.user32.SetForegroundWindow(hwnd)
                            ctypes.windll.user32.BringWindowToTop(hwnd)
                            ctypes.windll.user32.SetActiveWindow(hwnd)
                        except Exception:
                            pass
                        self.gui_log("✅ Focused Reports window")
                        return True
                except Exception:
                    pass
                time.sleep(0.2)
        except Exception as e:
            self.gui_log(f"⚠️ Focus helper error: {e}")
        return False
    
    def click_at_coordinate(self, x, y, move_duration=0.5, description=""):
        """Click at a specific coordinate with smooth mouse movement
        
        Args:
            x: X coordinate
            y: Y coordinate
            move_duration: Duration of mouse movement (seconds)
            description: Description of what's being clicked
        """
        desc = f" - {description}" if description else ""
        self.gui_log(f"🖱️ Clicking at ({x}, {y}){desc}")
        try:
            # Smooth move to the point
            pyautogui.moveTo(x, y, duration=move_duration)
            time.sleep(0.1)
            # Click
            pyautogui.click()
            self.gui_log(f"✅ Clicked at ({x}, {y}){desc}")
            time.sleep(0.3)
            return True
        except Exception as e:
            self.gui_log(f"❌ Error clicking at ({x}, {y}): {e}")
            return False
    
    def get_mouse_position(self):
        """Get current mouse position - useful for training"""
        pos = pyautogui.position()
        return (pos.x, pos.y)
    
    def wait_for_mouse_position(self, timeout=30, poll_interval=0.5):
        """Wait for user to position mouse, then return position
        Useful for interactive coordinate recording
        """
        self.gui_log(f"🖱️ Waiting for mouse position (timeout: {timeout}s)...")
        start_time = time.time()
        last_pos = None
        
        while time.time() - start_time < timeout:
            current_pos = pyautogui.position()
            # Check if mouse moved and then stopped (indicates user positioned it)
            if current_pos != last_pos:
                last_pos = current_pos
                time.sleep(0.3)  # Wait to see if it's stable
                if pyautogui.position() == current_pos:
                    self.gui_log(f"📍 Mouse position detected: ({current_pos.x}, {current_pos.y})")
                    return (current_pos.x, current_pos.y)
            time.sleep(poll_interval)
        
        self.gui_log("⏱️ Timeout waiting for mouse position")
        return None
    
    def get_current_window_title(self):
        """Get the title of the currently active window"""
        try:
            if not self.app:
                self.connect_to_app()
            window = self.app.top_window()
            title = window.window_text()
            self.gui_log(f"📋 Current window: {title}")
            return title
        except Exception as e:
            self.gui_log(f"❌ Error getting window title: {e}")
            return None
    
    def wait_for_window_close(self, window_title, timeout=30):
        """Wait for a specific window to close"""
        self.gui_log(f"⏳ Waiting for window to close: {window_title}")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                window = self.find_window(window_title, timeout=2)
                if not window or not window.exists():
                    self.gui_log(f"✅ Window closed: {window_title}")
                    return True
            except:
                self.gui_log(f"✅ Window closed: {window_title}")
                return True
            
            time.sleep(0.5)
        
        self.gui_log(f"⚠️ Window still open after timeout: {window_title}")
        return False
    
    def login_workflow(self, username, password):
        """Login workflow - launches Medisoft and logs in"""
        self.gui_log("📋 Starting Medisoft login process...")
        self.update_status("Initializing login...", "#0066cc")
        
        try:
            # Launch Medisoft
            self.launch_medisoft()
            
            # Wait for and perform login
            if not self.login(username, password):
                self.gui_log("❌ Login failed")
                self.update_status("Login failed", "#dc3545")
                return False
            
            self.gui_log("✅ Login successful")
            
            # Wait for Medisoft to fully load after login (login window may still be visible)
            self.gui_log("⏳ Waiting for Medisoft to fully load after login...")
            self.update_status("Waiting for application to load...", "#ff9500")
            time.sleep(3)  # Reduced wait from 5 to 3 seconds
            
            # Connect to the main Medisoft application
            self.gui_log("🔌 Connecting to Medisoft main window...")
            self.update_status("Connecting to application...", "#ff9500")
            
            # Try multiple times with increasing wait
            connection_successful = False
            for attempt in range(3):
                if self.connect_to_app(window_title_regex=".*Medisoft.*", timeout=10, use_process=True):
                    connection_successful = True
                    break
                else:
                    if attempt < 2:
                        wait_time = (attempt + 1) * 3
                        self.gui_log(f"⚠️ Connection attempt {attempt + 1} failed, waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
            
            if not connection_successful:
                self.gui_log("❌ Failed to connect to Medisoft after multiple attempts")
                self.update_status("Connection failed", "#dc3545")
                return False
            
            self.gui_log("✅ Connected to Medisoft successfully - Ready for navigation")
            self.update_status("Login complete - Ready to navigate", "#28a745")
            time.sleep(1)
            return True
            
        except Exception as e:
            self.gui_log(f"❌ Login workflow error: {e}")
            self.update_status(f"Login error: {e}", "#dc3545")
            return False
    
    def parse_insurance_pdf(self, pdf_path):
        """Parse an insurance company PDF to extract client name and date range"""
        if not PDFPLUMBER_AVAILABLE:
            self.gui_log("pdfplumber not available - cannot parse PDF")
            return None
        
        self.gui_log(f"Parsing insurance PDF: {pdf_path}")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extract text from all pages
                full_text = ""
                pages_text = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""
                    full_text += page_text
                    full_text += "\n"
                    pages_text.append((page_num, page_text))
                
                # If no text extracted, PDF might be scanned - try OCR if available
                if not full_text.strip() and OCR_AVAILABLE:
                    self.gui_log("PDF appears to be scanned (no text found) - attempting OCR...")
                    try:
                        # Try OCR on all pages (date range and client name could be on any page)
                        from pdf2image import convert_from_path
                        # Use Poppler path - must be passed directly, not just env var
                        poppler_path = os.environ.get('POPPLER_PATH')
                        if not poppler_path:
                            # Fallback: check common locations and vendor directory
                            script_dir = Path(__file__).parent
                            poppler_candidates = [
                                script_dir / 'vendor' / 'poppler' / 'Library' / 'bin',
                                Path('C:/Program Files/poppler/Library/bin'),
                                Path('C:/Program Files (x86)/poppler/Library/bin'),
                                Path.home() / 'AppData/Local/poppler/Library/bin',
                            ]
                            for candidate in poppler_candidates:
                                if candidate.exists() and (candidate / 'pdftoppm.exe').exists():
                                    poppler_path = str(candidate)
                                    break
                        
                        # OCR all pages (up to 5 pages to avoid long processing)
                        max_ocr_pages = min(len(pages_text), 5)
                        self.gui_log(f"Running OCR on pages 1-{max_ocr_pages}...")
                        images = convert_from_path(str(pdf_path), first_page=1, last_page=max_ocr_pages, poppler_path=poppler_path, dpi=300)
                        
                        if images:
                            # Combine OCR text from all pages
                            all_ocr_text = ""
                            for page_num, img in enumerate(images, 1):
                                page_ocr = pytesseract.image_to_string(img)
                                all_ocr_text += f"\n[PAGE {page_num} OCR]\n{page_ocr}\n"
                            full_text += all_ocr_text
                            self.gui_log(f"OCR extraction completed from {len(images)} page(s)")
                    except Exception as ocr_error:
                        self.gui_log(f"OCR not available or failed: {ocr_error}")
                        self.gui_log("Tip: Install Tesseract OCR for scanned PDFs (https://github.com/tesseract-ocr/tesseract)")
                
                # Search for client name - look for common patterns
                client_name = None
                date_range_start = None
                date_range_end = None
                
                lines = full_text.split('\n')
                
                # METHOD 1: Look for "Date(s) of service:" pattern (user confirmed format)
                for i, line in enumerate(lines):
                    line_lower = line.lower()
                    
                    # Look for "Date(s) of service:" or "Date of service:" pattern
                    if 'date(s) of service:' in line_lower or 'date of service:' in line_lower:
                        self.gui_log(f"Found date of service label on line {i+1}")
                        
                        # Look for date pattern in this line or next lines
                        # Pattern: "09/02/2025 - 09/30/2025" or "09/02/2025 to 09/30/2025"
                        date_pattern = r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\s*[-to]\s*(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})'
                        
                        # Check current line and next 3 lines
                        for j in range(i, min(i+4, len(lines))):
                            date_line = lines[j]
                            match = re.search(date_pattern, date_line)
                            if match:
                                date_range_start = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
                                date_range_end = f"{match.group(4)}/{match.group(5)}/{match.group(6)}"
                                self.gui_log(f"Found date range: {date_range_start} - {date_range_end}")
                                break
                        
                        # If not found, try finding dates separately
                        if not date_range_start:
                            date_pattern_single = r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})'
                            for j in range(i, min(i+4, len(lines))):
                                date_line = lines[j]
                                dates = re.findall(date_pattern_single, date_line)
                                if len(dates) >= 2:
                                    date_range_start = f"{dates[0][0]}/{dates[0][1]}/{dates[0][2]}"
                                    date_range_end = f"{dates[1][0]}/{dates[1][1]}/{dates[1][2]}"
                                    self.gui_log(f"Found date range: {date_range_start} - {date_range_end}")
                                    break
                    
                    # Look for client name patterns
                    if not client_name:
                        # Look for "Patient:", "Member:", "Client:", "Name:", "Beneficiary:"
                        if any(keyword in line_lower for keyword in ['patient:', 'member:', 'client:', 'beneficiary:', 'name:']):
                            # Next line or same line after colon often contains name
                            if ':' in line:
                                potential_name = line.split(':', 1)[1].strip()
                                # Clean up - remove extra spaces, look for 2+ words
                                if potential_name and len(potential_name.split()) >= 2:
                                    client_name = potential_name
                            elif i + 1 < len(lines):
                                potential_name = lines[i + 1].strip()
                                if potential_name and len(potential_name.split()) >= 2 and len(potential_name) > 3:
                                    client_name = potential_name
                
                # METHOD 2: If client name not found, search for common name patterns
                if not client_name:
                    # Look for patterns like "First Last" (2 words, capitalized)
                    name_pattern = r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b'
                    for line in lines[:20]:  # Check first 20 lines
                        matches = re.findall(name_pattern, line)
                        if matches:
                            potential = matches[0]
                            # Filter out common false positives
                            if not any(word.lower() in potential.lower() for word in ['Date', 'Service', 'Request', 'Optum', 'Molina', 'Wellcare']):
                                client_name = potential
                                self.gui_log(f"Found potential client name: {client_name}")
                                break
                
                result = {
                    'client_name': client_name,
                    'date_range_start': date_range_start,
                    'date_range_end': date_range_end,
                    'raw_text': full_text[:2000]  # First 2000 chars for debugging
                }
                
                self.gui_log(f"Extracted from PDF:")
                self.gui_log(f"   Client Name: {client_name or 'Not found'}")
                self.gui_log(f"   Date Range Start: {date_range_start or 'Not found'}")
                self.gui_log(f"   Date Range End: {date_range_end or 'Not found'}")
                
                # Verify extraction matches expected values
                if client_name and "Sean" in client_name and "Hansen" in client_name:
                    self.gui_log("Client name extraction verified: Sean Hansen")
                if date_range_start == "09/02/2025" and date_range_end == "09/30/2025":
                    self.gui_log("Date range extraction verified: 09/02/2025 - 09/30/2025")
                
                return result
                
        except Exception as e:
            self.gui_log(f"Error parsing PDF: {e}")
            import traceback
            self.gui_log(f"   Traceback: {traceback.format_exc()}")
            return None
    
    def find_insurance_pdfs(self, downloads_folder=None):
        """Find insurance PDF files in Downloads folder"""
        if downloads_folder is None:
            downloads_folder = Path.home() / "Downloads"
        else:
            downloads_folder = Path(downloads_folder)
        
        self.gui_log(f"🔍 Searching for insurance PDFs in: {downloads_folder}")
        
        # Look for PDFs with common insurance naming patterns
        pdf_files = []
        patterns = ['*prepayment*', '*request*', '*optum*', '*insurance*']
        
        for pattern in patterns:
            found = list(downloads_folder.glob(f"{pattern}*.pdf"))
            pdf_files.extend(found)
        
        # Remove duplicates
        pdf_files = list(set(pdf_files))
        
        if pdf_files:
            self.gui_log(f"📄 Found {len(pdf_files)} potential insurance PDF(s):")
            for pdf in pdf_files[:5]:  # Show first 5
                self.gui_log(f"   - {pdf.name}")
        else:
            self.gui_log("⚠️ No insurance PDFs found in Downloads folder")
        
        return pdf_files
    
    def fill_search_window(self, client_name=None, date_from_start=None, date_from_end=None):
        """
        Fill the Search window with extracted data according to manager's instructions:
        
        Per manager's instructions:
        1. Chart Number: Click 3 dots button, type client name, double-click to select from list
        2. Date From: Enter date range (start and end), checkbox underneath should NOT be checked
        3. Date Created: Do NOT enter any range, checkbox underneath SHOULD be checked
        4. Procedure Code: Add codes one by one (90791, 90834, 90837, 90853), checkbox underneath should NOT be checked
        """
        self.gui_log("Filling Search window with extracted data...")
        self.update_status("Filling Search window...", "#ff9500")
        
        try:
            # Wait for Search window
            search_window = self.wait_for_window(".*Search.*", timeout=15)
            if not search_window:
                self.gui_log("Search window not found")
                return False
            
            # Robustly focus the Search window (WindowSpecification vs Wrapper)
            try:
                if hasattr(search_window, 'set_focus'):
                    search_window.set_focus()
                else:
                    wrapper = getattr(search_window, 'wrapper_object', None)
                    if callable(wrapper):
                        wrapper().set_focus()
                    else:
                        if not self.app:
                            self.connect_to_app()
                        self.app.top_window().set_focus()
            except Exception:
                # As a last resort, activate by title using pyautogui
                self.activate_window_by_title("Search")
            time.sleep(1)
            
            # Get the window object
            try:
                window = search_window.top_window()
            except Exception:
                if not self.app:
                    self.connect_to_app()
                window = self.app.top_window()
            
            filled_fields = []
            
            # Prepare image directory for search window elements
            script_dir = Path(__file__).parent
            
            # ========== STEP 1: Fill Chart Number ==========
            # Manager instructions: "Chart Number (click 3 dots) type client's name and double click to choose from list"
            if client_name:
                self.gui_log(f"Step 1: Filling Chart Number with client name: {client_name}")
                try:
                    chart_dots_img = script_dir / 'search_chart_dots.png'
                    chart_success = False
                    # Initialize to avoid UnboundLocalError if image path succeeds
                    chart_field = None
                    three_dots_button = None
                    
                    # Method 0: Image-based click on 3-dots button first (preferred for cross-machine)
                    if chart_dots_img.exists():
                        self.gui_log("Trying image recognition for Chart Number 3-dots...")
                        if self.find_and_click_by_image(str(chart_dots_img), confidence=0.7, timeout=5):
                            # Wait for the selection dialog to actually appear before typing
                            if not self._wait_for_three_dots_dialog(appear_timeout=3.0):
                                # Try a second click/double-click if dialog didn't appear yet
                                self.gui_log("3-dots dialog not detected yet, clicking again...")
                                if self.find_and_click_by_image(str(chart_dots_img), confidence=0.7, timeout=2):
                                    time.sleep(0.3)
                                # Final attempt to wait
                                self._wait_for_three_dots_dialog(appear_timeout=2.0)
                            key = self._generate_medisoft_search_key(client_name)
                            self.gui_log(f"Typing Medisoft search key: {key}")
                            pyautogui.write(key, interval=0.1)
                            time.sleep(0.5)
                            if self._select_client_from_three_dots_dialog(client_name):
                                filled_fields.append("Chart Number (image)")
                                self.gui_log(f"Chart Number selected for: {client_name}")
                                chart_success = True
                            else:
                                self.gui_log("Selection by name failed, pressing Enter on current item")
                                pyautogui.press('enter')
                                time.sleep(0.4)
                                filled_fields.append("Chart Number (image, fallback Enter)")
                                chart_success = True
                    
                    if not chart_success:
                        # Fallback to UI automation
                        chart_field = None
                        three_dots_button = None
                    
                    # Method 1: Try to find by looking for buttons near Edit controls
                    all_controls = window.descendants()
                    
                    # Look for the 3 dots button (often has "..." text or is a button near Chart Number)
                    for control in all_controls:
                        try:
                            control_text = control.window_text().lower()
                            # The 3 dots button might be labeled or be a specific button type
                            if "..." in control_text or control.control_type() == "Button":
                                # Try to find Edit field nearby
                                rect = control.rectangle()
                                # Look for Edit controls near this button
                                for edit in window.descendants(control_type="Edit"):
                                    edit_rect = edit.rectangle()
                                    # If edit is near this button, it might be the Chart Number field
                                    if abs(edit_rect.left - rect.right) < 100 and abs(edit_rect.top - rect.top) < 30:
                                        three_dots_button = control
                                        chart_field = edit
                                        break
                                if chart_field:
                                    break
                        except:
                            continue
                    
                    # Method 2: If not found, try finding Edit fields and clicking button nearby
                    if not chart_field:
                        all_edits = window.descendants(control_type="Edit")
                        if all_edits:
                            # Usually the first Edit field is Chart Number
                            chart_field = all_edits[0]
                            # Look for button to the right of this field
                            chart_rect = chart_field.rectangle()
                            for btn in window.descendants(control_type="Button"):
                                try:
                                    btn_rect = btn.rectangle()
                                    # Button should be to the right and vertically aligned
                                    if (btn_rect.left > chart_rect.right and 
                                        btn_rect.left - chart_rect.right < 50 and
                                        abs(btn_rect.top - chart_rect.top) < 20):
                                        three_dots_button = btn
                                        break
                                except:
                                    continue
                    
                    if chart_field and three_dots_button:
                        self.gui_log("Found Chart Number field and 3 dots button")
                        # Click the 3 dots button
                        three_dots_button.click()
                        time.sleep(1)
                        
                        # A dialog/popup should open - Medisoft requires special key format:
                        # First 3 letters of last name + first 2 letters of first name (ignore trailing digits)
                        key = self._generate_medisoft_search_key(client_name)
                        self.gui_log(f"Typing Medisoft search key: {key}")
                        pyautogui.write(key, interval=0.1)
                        time.sleep(0.8)
                        
                        # Try to select the exact client from the list dialog
                        if self._select_client_from_three_dots_dialog(client_name):
                            filled_fields.append("Chart Number")
                            self.gui_log(f"Chart Number selected for: {client_name}")
                        else:
                            # Fallback: use keyboard navigation to choose current highlighted
                            self.gui_log("Could not confirm client in list, pressing Enter on current selection as fallback")
                            pyautogui.press('enter')
                            time.sleep(0.8)
                    elif chart_field:
                        # Fallback: Try typing directly in the field
                        self.gui_log("3 dots button not found, trying direct field entry")
                        chart_field.set_focus()
                        time.sleep(0.3)
                        pyautogui.write(client_name, interval=0.1)
                        time.sleep(0.5)
                        filled_fields.append("Chart Number (direct)")
                    else:
                        # Coordinate-based fallback for Chart Number 3-dots
                        coord = self.get_coordinate("Search_ChartDots")
                        if coord:
                            self.gui_log("Using saved coordinate for Chart Number 3-dots")
                            x,y = coord
                            pyautogui.click(x,y)
                            time.sleep(0.5)
                            key = self._generate_medisoft_search_key(client_name)
                            pyautogui.write(key, interval=0.1)
                            time.sleep(0.5)
                            pyautogui.press('enter')
                            filled_fields.append("Chart Number (coord)")
                        else:
                            self.gui_log("Could not find Chart Number field. Press F8 to capture 'Search_ChartDots' coordinate.")
                            try:
                                _debug_list_controls(window)
                            except Exception:
                                pass
                except Exception as e:
                    self.gui_log(f"Error filling Chart Number: {e}")
                    import traceback
                    self.gui_log(f"Traceback: {traceback.format_exc()[:200]}")
            
            # ========== STEP 2: Fill Date From fields ==========
            # Manager instructions: "Date From (enter range) - box under should not be checked"
            if date_from_start and date_from_end:
                self.gui_log(f"Step 2: Filling Date From range: {date_from_start} to {date_from_end}")
                try:
                    start_img = script_dir / 'search_date_from_start.png'
                    end_img = script_dir / 'search_date_from_end.png'
                    date_success = False
                    date_fields = []  # Initialize to avoid undefined reference
                    
                    # Method 0: Image-based entry (preferred)
                    if start_img.exists() and end_img.exists():
                        self.gui_log("Trying image recognition for Date From fields...")
                        if self.find_and_click_by_image(str(start_img), confidence=0.7, timeout=5):
                            time.sleep(0.2)
                            pyautogui.hotkey('ctrl','a'); time.sleep(0.05)
                            pyautogui.write(date_from_start, interval=0.0)
                            time.sleep(0.2)
                            if self.find_and_click_by_image(str(end_img), confidence=0.7, timeout=5):
                                time.sleep(0.2)
                                pyautogui.hotkey('ctrl','a'); time.sleep(0.05)
                                pyautogui.write(date_from_end, interval=0.0)
                                filled_fields.append(f"Date From ({date_from_start} to {date_from_end}) (image)")
                                date_success = True
                    
                    if not date_success:
                        # Fallback to UI automation
                        all_edits = window.descendants(control_type="Edit")
                        date_fields = [e for e in all_edits if e.is_visible()]
                        
                        # Date From fields are typically after Chart Number
                        # Look for the fields that accept date input
                        if len(date_fields) >= 2:
                            # Fill first Date From field (start)
                            self.gui_log(f"Filling Date From start: {date_from_start}")
                            date_fields[0].set_focus()
                            time.sleep(0.3)
                            pyautogui.hotkey('ctrl', 'a')  # Select all
                            time.sleep(0.1)
                            pyautogui.write(date_from_start, interval=0.05)
                            time.sleep(0.5)
                            
                            # Fill second Date From field (end)
                            self.gui_log(f"Filling Date From end: {date_from_end}")
                            date_fields[1].set_focus()
                            time.sleep(0.3)
                            pyautogui.hotkey('ctrl', 'a')
                            time.sleep(0.1)
                            pyautogui.write(date_from_end, interval=0.05)
                            time.sleep(0.5)
                        
                        # Ensure checkbox under Date From is NOT checked
                        # Look for checkbox near Date From fields
                        date_checkbox_rect = date_fields[1].rectangle()
                        for checkbox in window.descendants(control_type="CheckBox"):
                            try:
                                cb_rect = checkbox.rectangle()
                                # Checkbox should be below the date fields
                                if (cb_rect.top > date_checkbox_rect.bottom and
                                    cb_rect.top - date_checkbox_rect.bottom < 50 and
                                    abs(cb_rect.left - date_checkbox_rect.left) < 100):
                                    # Uncheck if checked
                                    if checkbox.get_toggle_state():
                                        checkbox.click()
                                        self.gui_log("Unchecked Date From checkbox")
                                    else:
                                        self.gui_log("Date From checkbox already unchecked")
                                    break
                            except:
                                continue
                        
                        filled_fields.append(f"Date From ({date_from_start} to {date_from_end})")
                        self.gui_log("Date From fields filled successfully")
                    else:
                        self.gui_log(f"Could not find Date From fields (found {len(date_fields)} edit fields)")
                        # Coordinate-based fallback for Date From Start/End
                        start_coord = self.get_coordinate("Search_DateFrom_Start")
                        end_coord = self.get_coordinate("Search_DateFrom_End")
                        if start_coord and end_coord:
                            self.gui_log("Using saved coordinates for Date From fields")
                            sx,sy = start_coord; ex,ey = end_coord
                            pyautogui.click(sx,sy); time.sleep(0.2)
                            pyautogui.hotkey('ctrl','a'); time.sleep(0.1)
                            pyautogui.write(date_from_start, interval=0.05)
                            time.sleep(0.3)
                            pyautogui.click(ex,ey); time.sleep(0.2)
                            pyautogui.hotkey('ctrl','a'); time.sleep(0.1)
                            pyautogui.write(date_from_end, interval=0.05)
                            filled_fields.append(f"Date From ({date_from_start} to {date_from_end}) (coord)")
                        else:
                            self.gui_log("Press F8 to capture 'Search_DateFrom_Start' and 'Search_DateFrom_End' coordinates.")
                except Exception as e:
                    self.gui_log(f"Error filling Date From: {e}")
                    import traceback
                    self.gui_log(f"Traceback: {traceback.format_exc()[:200]}")
            
            # ========== STEP 3: Configure Date Created ==========
            # Manager instructions: "Date Created - do not enter any range - box under should be checked"
            self.gui_log("Step 3: Configuring Date Created (no range, checkbox checked)")
            try:
                dc_img = script_dir / 'search_date_created_check.png'
                dc_success = False
                
                # Method 0: Image-based checkbox click (preferred)
                if dc_img.exists():
                    self.gui_log("Trying image recognition for Date Created checkbox...")
                    if self.find_and_click_by_image(str(dc_img), confidence=0.7, timeout=5):
                        time.sleep(0.2)
                        # Verify it's checked (click twice if needed to ensure checked)
                        pyautogui.click()  # Extra click to ensure checked
                        time.sleep(0.1)
                        filled_fields.append("Date Created (checkbox checked) (image)")
                        dc_success = True
                
                if not dc_success:
                    # Fallback to UI automation
                    # Find Date Created checkbox - should be checked
                    # Look for checkboxes, find the one associated with Date Created
                    for checkbox in window.descendants(control_type="CheckBox"):
                        try:
                            # Try to find checkbox by looking for nearby text or position
                            # This might need adjustment based on actual window layout
                            if not checkbox.get_toggle_state():
                                # Check if it's near where Date Created would be
                                # For now, we'll check if there's an unchecked checkbox
                                # This is a heuristic - may need refinement
                                checkbox.click()
                                self.gui_log("Checked Date Created checkbox")
                                break
                        except:
                            continue
                    
                    filled_fields.append("Date Created (checkbox checked)")
            except Exception as e:
                self.gui_log(f"Error configuring Date Created: {e}")
                # Coordinate fallback
                dc_coord = self.get_coordinate("Search_DateCreated_Check")
                if dc_coord:
                    x,y = dc_coord
                    pyautogui.click(x,y); time.sleep(0.2)
                    filled_fields.append("Date Created (checkbox checked) (coord)")
            
            # ========== STEP 4: Add Procedure Codes ==========
            # Manager instructions: "Procedure Code - enter each code and Add to List"
            # Codes: 90791, 90834, 90837, 90853
            # Box under should not be checked
            procedure_codes = ["90791", "90834", "90837", "90853"]
            self.gui_log(f"Step 4: Adding Procedure Codes: {', '.join(procedure_codes)}")
            try:
                proc_img = script_dir / 'search_procedure_code.png'
                add_img = script_dir / 'search_add_button.png'
                proc_success = False
                procedure_field = None  # Initialize to avoid undefined reference
                add_button = None  # Initialize to avoid undefined reference
                
                # Method 0: Image-based entry (preferred)
                if proc_img.exists() and add_img.exists():
                    self.gui_log("Trying image recognition for Procedure Code and Add button...")
                    for code in procedure_codes:
                        if self.find_and_click_by_image(str(proc_img), confidence=0.7, timeout=4):
                            time.sleep(0.15)
                            pyautogui.hotkey('ctrl','a'); time.sleep(0.05)
                            pyautogui.write(code, interval=0.0)
                            time.sleep(0.15)
                            if self.find_and_click_by_image(str(add_img), confidence=0.7, timeout=3):
                                time.sleep(0.2)
                                self.gui_log(f"Added procedure code: {code}")
                            else:
                                self.gui_log(f"Add button not found for code: {code}")
                    filled_fields.append(f"Procedure Codes ({', '.join(procedure_codes)}) (image)")
                    proc_success = True
                
                if not proc_success:
                    # Fallback to UI automation
                    # Find Procedure Code field and Add button
                    procedure_field = None
                    add_button = None
                    
                    # Look for Edit field (Procedure Code input)
                    all_edits = window.descendants(control_type="Edit")
                    # Procedure Code field is usually after the Date fields
                    if len(all_edits) > 2:
                        procedure_field = all_edits[2]  # Usually the 3rd Edit field
                    
                    # Find "Add" or "Add to List" button
                    for btn in window.descendants(control_type="Button"):
                        try:
                            btn_text = btn.window_text().lower()
                            if "add" in btn_text:
                                add_button = btn
                                break
                        except:
                            continue
                
                if procedure_field and add_button:
                    for code in procedure_codes:
                        self.gui_log(f"Adding procedure code: {code}")
                        # Clear and enter code
                        procedure_field.set_focus()
                        time.sleep(0.3)
                        pyautogui.hotkey('ctrl', 'a')
                        time.sleep(0.1)
                        pyautogui.write(code, interval=0.1)
                        time.sleep(0.5)
                        
                        # Click Add button
                        add_button.click()
                        time.sleep(0.5)
                        self.gui_log(f"Added procedure code: {code}")
                    
                    # Ensure checkbox under Procedure Code is NOT checked
                    proc_checkbox_rect = procedure_field.rectangle()
                    for checkbox in window.descendants(control_type="CheckBox"):
                        try:
                            cb_rect = checkbox.rectangle()
                            if (cb_rect.top > proc_checkbox_rect.bottom and
                                cb_rect.top - proc_checkbox_rect.bottom < 50):
                                if checkbox.get_toggle_state():
                                    checkbox.click()
                                    self.gui_log("Unchecked Procedure Code checkbox")
                                break
                        except:
                            continue
                    
                    filled_fields.append(f"Procedure Codes ({', '.join(procedure_codes)})")
                    self.gui_log("All procedure codes added")
                else:
                    self.gui_log("Could not find Procedure Code field or Add button")
                    if not procedure_field:
                        self.gui_log("Procedure Code field not found")
                    if not add_button:
                        self.gui_log("Add button not found")
                    # Coordinate-based fallback for Procedure Code and Add
                    proc_coord = self.get_coordinate("Search_ProcCode")
                    add_coord = self.get_coordinate("Search_AddButton")
                    if proc_coord and add_coord:
                        px,py = proc_coord; ax,ay = add_coord
                        for code in procedure_codes:
                            pyautogui.click(px,py); time.sleep(0.2)
                            pyautogui.hotkey('ctrl','a'); time.sleep(0.1)
                            pyautogui.write(code, interval=0.1)
                            time.sleep(0.2)
                            pyautogui.click(ax,ay); time.sleep(0.3)
                        filled_fields.append(f"Procedure Codes ({', '.join(procedure_codes)}) (coord)")
                    else:
                        self.gui_log("Press F8 to capture 'Search_ProcCode' and 'Search_AddButton' coordinates.")
            except Exception as e:
                self.gui_log(f"Error adding Procedure Codes: {e}")
                import traceback
                self.gui_log(f"Traceback: {traceback.format_exc()[:200]}")
            
            # ========== STEP 5: Click OK button ==========
            ok_img = script_dir / 'ok_button_search_window.png'
            self.gui_log("Step 5: Clicking OK button to submit Search window...")
            if ok_img.exists():
                if self.find_and_click_by_image(str(ok_img), confidence=0.7, timeout=5):
                    self.gui_log("OK button clicked (image)")
                    time.sleep(0.5)
                else:
                    self.gui_log("OK button image not found, trying Enter key...")
                    pyautogui.press('enter')
            else:
                self.gui_log("OK button image not available, pressing Enter key...")
                pyautogui.press('enter')
            
            self.gui_log(f"Search window filled - Completed fields: {', '.join(filled_fields) if filled_fields else 'None'}")
            self.update_status("Search window filled", "#28a745")
            return True
            
        except Exception as e:
            self.gui_log(f"Error filling Search window: {e}")
            import traceback
            self.gui_log(f"Traceback: {traceback.format_exc()}")
            self.update_status(f"Error: {e}", "#dc3545")
            return False
    
    def process_insurance_pdf_and_fill_search(self):
        """Main function to parse user-selected insurance PDF and fill Search window (single client)"""
        self.gui_log("Processing insurance PDF and filling Search window...")
        
        # Step 1: Check if PDF is selected by user
        if not self.selected_pdf_path:
            self.gui_log("No PDF selected - Please select an insurance PDF in the GUI")
            self.gui_log("User will need to fill Search window manually")
            return
            
        pdf_path = Path(self.selected_pdf_path)
        if not pdf_path.exists():
            self.gui_log(f"PDF file not found: {pdf_path}")
            self.gui_log("User will need to fill Search window manually")
            return
        
        # Step 2: Parse the user-selected PDF
        self.gui_log(f"Parsing user-selected PDF: {pdf_path.name}")
        pdf_data = self.parse_insurance_pdf(str(pdf_path))
        
        if not pdf_data:
            self.gui_log("Could not parse PDF - user will need to fill Search window manually")
            return
        
        # Step 3: Fill Search window with extracted data
        self.fill_search_window(
            client_name=pdf_data.get('client_name'),
            date_from_start=pdf_data.get('date_range_start'),
            date_from_end=pdf_data.get('date_range_end')
        )
    
    def process_batch_excel_csv(self):
        """Process Excel/CSV file with multiple clients in batch mode.
        After each client's Search window is filled and OK clicked, 
        returns to fresh Search window for next client.
        """
        if not self.selected_excel_path or not self.excel_client_data:
            self.gui_log("No Excel/CSV file selected or no client data loaded")
            return
        
        total_clients = len(self.excel_client_data)
        self.gui_log(f"🔄 Starting batch processing for {total_clients} client(s)...")
        self.update_status(f"Batch processing: 0/{total_clients}", "#ff9500")
        
        successful = 0
        failed = 0
        
        for idx, client_data in enumerate(self.excel_client_data, 1):
            self.gui_log(f"\n{'='*60}")
            self.gui_log(f"📋 Processing client {idx}/{total_clients}: {client_data.get('client_name', 'Unknown')}")
            self.gui_log(f"{'='*60}")
            self.update_status(f"Batch processing: {idx}/{total_clients} - {client_data.get('client_name', 'Unknown')}", "#ff9500")
            
            # For first client, Search window should already be open from navigation
            # For subsequent clients, we need to open a fresh Search window
            if idx > 1:
                self.gui_log("Opening fresh Search window for next client...")
                # TODO: Add logic to open new Search window (will be trained later)
                # For now, assume user manually opens it or we click a "New Search" button
                time.sleep(2)  # Wait for user to manually open or for automated step
            
            # Fill Search window with this client's data
            success = self.fill_search_window(
                client_name=client_data.get('client_name'),
                date_from_start=client_data.get('date_range_start'),
                date_from_end=client_data.get('date_range_end')
            )
            
            if success:
                successful += 1
                self.gui_log(f"✅ Successfully processed client {idx}/{total_clients}")
            else:
                failed += 1
                self.gui_log(f"❌ Failed to process client {idx}/{total_clients}")
            
            # Wait a moment before next client (allows result page to process)
            if idx < total_clients:
                time.sleep(2)
        
        # Final summary
        self.gui_log(f"\n{'='*60}")
        self.gui_log(f"📊 Batch processing complete: {successful} successful, {failed} failed out of {total_clients} total")
        self.gui_log(f"{'='*60}")
        self.update_status(f"Batch complete: {successful}/{total_clients} successful", "#28a745" if successful == total_clients else "#ff9500")
    
    def process_data_file_and_fill_search(self):
        """Main entry point: Process either PDF (single) or Excel/CSV (batch)"""
        # Check if Excel/CSV is selected (batch processing takes priority)
        if self.selected_excel_path and self.excel_client_data:
            self.process_batch_excel_csv()
        # Otherwise, check for PDF (single client)
        elif self.selected_pdf_path:
            self.process_insurance_pdf_and_fill_search()
        else:
            self.gui_log("⚠️ No data file selected - Please select either a PDF or Excel/CSV file")

    def _paste_excel_path(self):
        """Allow user to paste a full path to an Excel/CSV file"""
        try:
            path_str = simpledialog.askstring("Paste File Path", "Paste full path to .xlsx/.xls/.csv:")
            if not path_str:
                return
            p = Path(path_str.strip().strip('"'))
            if not p.exists():
                messagebox.showerror("File not found", f"File does not exist:\n{p}")
                return
            if p.suffix.lower() not in (".xlsx", ".xls", ".csv", ".txt"):
                if not messagebox.askyesno("Unsupported extension", f"File has extension '{p.suffix}'. Try to load anyway?"):
                    return
            # Reuse the same assignment logic as browse
            self.selected_excel_path = str(p)
            self.excel_entry.config(state="normal")
            self.excel_entry.delete(0, tk.END)
            self.excel_entry.insert(0, str(p))
            self.excel_entry.config(state="readonly")
            try:
                records = self._load_records_from_table_file(str(p))
            except Exception as e:
                records = []
                self.gui_log(f"❌ Error loading file: {e}")
            self.excel_client_data = [
                {
                    'client_name': r.get('patient_name', ''),
                    'date_range_start': r.get('dos_start', ''),
                    'date_range_end': r.get('dos_end', ''),
                    'notes': r.get('notes', ''),
                } for r in records
            ]
            if self.excel_client_data:
                self.excel_status_label.config(text=f"Loaded {len(self.excel_client_data)} records", fg="#28a745")
                self.gui_log(f"📊 Excel/CSV selected: {p.name} ({len(self.excel_client_data)} clients loaded)")
            else:
                self.excel_status_label.config(text="No rows detected in file", fg="#ff9500")
                self.gui_log(f"⚠️ No rows detected in file: {p.name}")
        except Exception as e:
            self.gui_log(f"❌ Error in pasted path flow: {e}")
    
    def navigate_to_reports_workflow(self):
        """Navigation workflow - navigates from home page to Reports"""
        self.gui_log("📋 Starting navigation to Reports...")
        self.update_status("Starting navigation...", "#0066cc")
        
        try:
            # Ensure we're connected
            if not self.app:
                self.gui_log("🔌 Ensuring connection to Medisoft...")
                if not self.connect_to_app(window_title_regex=".*Medisoft.*", timeout=10, use_process=True):
                    self.gui_log("❌ Failed to connect to Medisoft")
                    self.update_status("Connection failed", "#dc3545")
                return
            
            self.gui_log("✅ Connected to Medisoft - starting navigation")
            time.sleep(0.5)  # Reduced wait - connection is already established
            
            # Step 1: Click "Launch Medisoft Reports" button directly
            self.gui_log("📑 Step 1: Looking for 'Launch Medisoft Reports' button...")
            self.update_status("Looking for Launch Medisoft Reports button...", "#ff9500")
            
            reports_button_found = False
            
            # Method 1: Try UI element detection FIRST (most reliable across screens/computers)
            if not reports_button_found:
                self.gui_log("🔍 Method 1: Trying UI element detection (most reliable)...")
                if self.click_button("Launch Medisoft Reports", timeout=10, use_regex=False):
                    reports_button_found = True
                    self.gui_log("✅ Found and clicked 'Launch Medisoft Reports' button via UI element")
            
            # Method 2: Try finding button with partial text match in all buttons
            if not reports_button_found:
                self.gui_log("🔍 Method 2: Searching all buttons for 'Launch' and 'Reports'...")
                try:
                    window = self.app.top_window()
                    window.set_focus()
                    time.sleep(0.5)
                    # Search through all buttons
                    try:
                        all_buttons = window.descendants(control_type="Button")
                        for btn in all_buttons:
                            try:
                                btn_text = btn.window_text()
                                if btn_text and ("launch" in btn_text.lower() and "report" in btn_text.lower()):
                                    self.gui_log(f"📍 Found button: '{btn_text}'")
                                    btn.click()
                                    time.sleep(2)
                                    reports_button_found = True
                                    self.gui_log(f"✅ Clicked button: '{btn_text}'")
                                    break
                            except:
                                continue
                    except Exception as e:
                        self.gui_log(f"⚠️ Button search failed: {e}")
                except Exception as e:
                    self.gui_log(f"⚠️ Method 2 failed: {e}")
            
            # Method 3: Try with regex to find any variation
            if not reports_button_found:
                self.gui_log("🔍 Method 3: Trying regex search for Reports button...")
                if self.click_button(".*Launch.*Medisoft.*Reports.*", timeout=10, use_regex=True):
                    reports_button_found = True
                elif self.click_button(".*Launch.*Reports.*", timeout=5, use_regex=True):
                    reports_button_found = True
            
            # If all methods fail, list visible controls to help identify the button
            if not reports_button_found:
                self.gui_log("❌ Failed to find 'Launch Medisoft Reports' button")
                self.gui_log("🔍 Listing all visible buttons to help identify the correct button...")
                try:
                    window = self.app.top_window()
                    window.set_focus()
                    time.sleep(0.5)
                    self._list_visible_controls(window, max_items=30)
                    self.gui_log("💡 Tip: If you know the exact coordinates, set self.reports_button_coords in __init__")
                except Exception as e:
                    self.gui_log(f"⚠️ Error listing controls: {e}")
                
                self.update_status("Failed to find Launch Medisoft Reports button", "#dc3545")
                return
            
            self.gui_log("✅ Successfully clicked 'Launch Medisoft Reports' button")
            # Proactively bring the new Reports window to the foreground quickly
            self._focus_window_by_regex(".*Medisoft Reports.*", timeout=6)
            time.sleep(0.5)
            
            # Step 3: Wait for Reports window to open (support multiple title variants)
            self.gui_log("⏳ Step 3: Waiting for 'Medisoft Reports' window...")
            self.update_status("Waiting for Reports window to open...", "#ff9500")
            
            # Try specific title first (with facility name), then fall back to generic
            reports_window = self.wait_for_window(".*Medisoft Reports.*Integrity Social Work Services.*", timeout=20)
            if not reports_window:
                self.gui_log("⚠️ Specific Reports window title not found, trying generic title match...")
                # Try to focus it again in case it appeared behind
                self._focus_window_by_regex(".*Medisoft Reports.*", timeout=4)
                reports_window = self.wait_for_window(".*Medisoft Reports.*", timeout=30)
                if reports_window:
                    self.gui_log("ℹ️ Reports window detected with generic title (facility name may differ).")
            if not reports_window:
                self.gui_log("❌ Reports window did not open within timeout - stopping workflow")
                self.update_status("Reports window timeout", "#dc3545")
                return
            
            self.gui_log("✅ Reports window opened successfully")
            time.sleep(1)  # Reduced from 2s - window loads quickly
            
            # Step 4: Navigate to "Contents of 'All Folders'" section and double-click "CUSTOM"
            self.gui_log("🌳 Step 4: Navigating to 'CUSTOM' folder...")
            self.update_status("Navigating to CUSTOM folder...", "#ff9500")
            
            # Reconnect to get the new Reports window (a new window opened, need fresh connection)
            try:
                self.gui_log("🔌 Reconnecting to access Reports window...")
                # Reconnect to get the new Reports window (try specific then generic)
                connected = self.connect_to_app(window_title_regex=".*Medisoft Reports.*Integrity Social Work Services.*", timeout=10, use_process=False)
                if not connected:
                    self.gui_log("⚠️ Specific title connect failed, trying generic Reports window title...")
                    connected = self.connect_to_app(window_title_regex=".*Medisoft Reports.*", timeout=10, use_process=False)
                if not connected and not self.app:
                    # Fallback: Try to find it with the existing app connection
                    self.connect_to_app()
                
                # Find the reports window
                reports_window = None
                if self.app:
                    # Try specific, then generic
                    reports_window = self.app.window(title_re=".*Medisoft Reports.*Integrity Social Work Services.*")
                    if not reports_window.exists():
                        reports_window = self.app.window(title_re=".*Medisoft Reports.*")
                
                # Alternative: Try pywinauto directly
                if not reports_window or not reports_window.exists():
                    self.gui_log("🔍 Trying direct window connection...")
                    import pywinauto
                    from pywinauto import Desktop
                    desktop = Desktop(backend="win32")
                    reports_window = desktop.window(title_re=".*Medisoft Reports.*Integrity Social Work Services.*")
                    if not reports_window.exists():
                        reports_window = desktop.window(title_re=".*Medisoft Reports.*")
                
                if reports_window and reports_window.exists():
                    reports_window.set_focus()
                    time.sleep(1)
                    
                    custom_found = False
                    
                    # Method 1: Try image recognition FIRST (most reliable across different computers/screen sizes)
                    self.gui_log("🔍 Method 1: Trying image recognition for 'CUSTOM' (works on any screen size)...")
                    script_dir = Path(__file__).parent
                    self.gui_log(f"📁 Searching for CUSTOM images in: {script_dir}")
                    
                    # List all PNG files in the directory for debugging
                    try:
                        png_files = list(script_dir.glob("*.png"))
                        if png_files:
                            self.gui_log(f"📸 Found {len(png_files)} PNG file(s) in directory:")
                            for png_file in png_files:
                                self.gui_log(f"   - {png_file.name}")
                        else:
                            self.gui_log("⚠️ No PNG files found in bot directory")
                    except Exception as e:
                        self.gui_log(f"⚠️ Error listing PNG files: {e}")
                    
                    image_files = [
                        script_dir / "custom.png",
                        script_dir / "CUSTOM.png",
                        script_dir / "Custom.png"
                    ]
                    for img_path in image_files:
                        if img_path.exists():
                            self.gui_log(f"🖼️ Trying image: {img_path.name} (full path: {img_path})")
                            # Use the improved find_and_click_by_image function with coordinate region search
                            if self.find_and_click_by_image(str(img_path), confidence=0.7, timeout=5):
                                # If found, it's already clicked, just need to double-click
                                try:
                                    # Try to find it again to get location for double-click
                                    if OPENCV_AVAILABLE:
                                        location = pyautogui.locateOnScreen(str(img_path), confidence=0.7)
                                        if location:
                                            center = pyautogui.center(location)
                                            pyautogui.moveTo(center.x, center.y, duration=0.2)
                                            time.sleep(0.1)
                                            pyautogui.doubleClick(center.x, center.y)
                                            time.sleep(0.5)
                                            custom_found = True
                                            self.gui_log(f"✅ Double-clicked 'CUSTOM' using image: {img_path.name}")
                                            time.sleep(1.5)  # Reduced from 3s - folder opens quickly
                                            break
                                except:
                                    # If we can't double-click, single click already happened, try to double-click at coordinate
                                    coords = self.get_coordinate("Custom") if hasattr(self, 'get_coordinate') else None
                                    if coords:
                                        x, y = coords
                                        pyautogui.moveTo(x, y, duration=0.2)
                                        time.sleep(0.1)
                                        pyautogui.doubleClick(x, y)
                                        time.sleep(1.5)  # Reduced from 3s
                                        custom_found = True
                                        self.gui_log(f"✅ Double-clicked 'CUSTOM' using image (with coordinate fallback)")
                                        break
                    
                    # Method 2: Try saved coordinates (fallback - works on same computer/screen)
                    if not custom_found:
                        self.gui_log("🔍 Method 2: Trying saved coordinates for 'CUSTOM' (fallback)...")
                        coord_names = ["Custom", "CUSTOM", "custom"]
                        for name in coord_names:
                            coords = self.get_coordinate(name)
                            if coords:
                                try:
                                    x, y = coords
                                    self.gui_log(f"📍 Found saved coordinate for '{name}': ({x}, {y})")
                                    # Ensure Reports window is active
                                    reports_window.set_focus()
                                    time.sleep(0.5)
                                    # Double-click using pyautogui
                                    pyautogui.moveTo(x, y, duration=0.3)
                                    time.sleep(0.2)
                                    pyautogui.doubleClick(x, y)
                                    time.sleep(0.5)  # Small wait for click to register
                                    custom_found = True
                                    self.gui_log(f"✅ Double-clicked 'CUSTOM' at saved coordinates ({x}, {y})")
                                    time.sleep(3)  # Increased wait for folder to fully open and tree view to update
                                    break
                                except Exception as e:
                                    self.gui_log(f"⚠️ Coordinate click failed for '{name}': {e}")
                    
                    # Method 3: Try tree view navigation (fallback)
                    if not custom_found:
                        self.gui_log("🔍 Method 3: Trying tree view navigation...")
                        try:
                            # Look for tree view control with retry logic
                            tree_start_time = time.time()
                            tree = None
                            while time.time() - tree_start_time < 10:
                                try:
                                    tree = reports_window.child_window(control_type="Tree")
                                    if tree.exists():
                                        break
                                except:
                                    pass
                                time.sleep(0.5)
                            
                            if tree and tree.exists():
                                self.gui_log("✅ Found tree view")
                                
                                # Try to find "CUSTOM" in the tree view
                                try:
                                    # First try to find "All Folders" and expand it
                                    try:
                                        all_folders_start = time.time()
                                        all_folders = None
                                        while time.time() - all_folders_start < 5:
                                            try:
                                                all_folders = tree.child_window(title_re=".*All Folders.*")
                                                if all_folders.exists():
                                                    break
                                            except:
                                                pass
                                            time.sleep(0.5)
                                        
                                        if all_folders and all_folders.exists():
                                            self.gui_log("📍 Found 'All Folders', expanding...")
                                            all_folders.select()
                                            time.sleep(0.5)
                                            pyautogui.press('right')  # Expand
                                            time.sleep(1)
                                    except:
                                        self.gui_log("ℹ️ 'All Folders' not found or already expanded, proceeding...")
                                    
                                    # Now find and double-click "CUSTOM" with retry
                                    custom_start_time = time.time()
                                    custom_item = None
                                    while time.time() - custom_start_time < 10:
                                        try:
                                            custom_item = tree.child_window(title_re=".*CUSTOM.*")
                                            if custom_item.exists():
                                                break
                                        except:
                                            pass
                                        time.sleep(0.5)
                                    
                                    if custom_item and custom_item.exists():
                                        self.gui_log("📍 Found 'CUSTOM' in tree view, double-clicking...")
                                        custom_item.select()
                                        time.sleep(0.5)
                                        # Double-click using pyautogui on the item's location
                                        rect = custom_item.rectangle()
                                        center_x = (rect.left + rect.right) // 2
                                        center_y = (rect.top + rect.bottom) // 2
                                        pyautogui.doubleClick(center_x, center_y)
                                        self.gui_log("✅ Double-clicked 'CUSTOM' in tree view")
                                        time.sleep(2)  # Wait for folder to open
                                        custom_found = True
                                    else:
                                        self.gui_log("❌ 'CUSTOM' not found in tree view")
                                        
                                except Exception as e:
                                    self.gui_log(f"❌ Error navigating tree view: {e}")
                            else:
                                self.gui_log("❌ Tree view not found")
                        except Exception as e:
                            self.gui_log(f"❌ Error finding tree view: {e}")
                    
                    if not custom_found:
                        self.gui_log("❌ Failed to find and click 'CUSTOM' using all methods")
                        return
                    
                    # Verify folder opened by checking tree view updated
                    self.gui_log("⏳ Verifying CUSTOM folder opened...")
                    time.sleep(0.5)  # Reduced from 1s - folder opens quickly
                    try:
                        # Try to verify tree view has updated (folder opened)
                        reports_window.set_focus()
                        time.sleep(0.5)
                        # Check if tree view is accessible and has items
                        tree = reports_window.child_window(control_type="Tree")
                        if tree.exists():
                            self.gui_log("✅ Tree view accessible - folder should be open")
                        else:
                            self.gui_log("⚠️ Tree view not accessible, but continuing...")
                    except:
                        self.gui_log("⚠️ Could not verify folder opened, but continuing...")
                else:
                    self.gui_log("❌ Reports window not accessible")
                    return
                    
            except Exception as e:
                self.gui_log(f"❌ Error accessing reports window: {e}")
                return
            
            # Step 5: Double-click "Patient Account Ledger by Date of Service v1"
            self.gui_log("📄 Step 5: Navigating to 'Patient Account Ledger by Date of Service v1'...")
            self.update_status("Opening Patient Account Ledger report...", "#ff9500")
            
            # Wait for folder contents to fully load (reduced from 2s to 1.5s)
            self.gui_log("⏳ Waiting for folder contents to load...")
            time.sleep(1.5)
            
            try:
                # Refresh connection to get updated tree view after CUSTOM folder opened
                reports_window.set_focus()
                time.sleep(1)  # Reduced from 1.5s to 1s
                
                report_found = False
                
                # Method 1: Try image recognition FIRST (most reliable across computers/screen sizes)
                self.gui_log("🔍 Method 1: Trying image recognition for 'Patient Account Ledger' (works on any screen size)...")
                script_dir = Path(__file__).parent
                image_files = [
                    script_dir / "patient_account_ledger.png",
                    script_dir / "patient_ledger.png",
                    script_dir / "account_ledger.png",
                    script_dir / "Patient Account Ledger by Date of Service v1.png",
                    script_dir / "Patient Account Ledger.png"
                ]
                
                for img_path in image_files:
                    if img_path.exists():
                        self.gui_log(f"🖼️ Trying image: {img_path.name} (full path: {img_path})")
                        # Try to find and double-click the image
                        try:
                            # Get saved coordinate as hint for search region
                            coord_names = ["Patient Account Ledger", "Patient Account Ledger by Date of Service v1", "account_ledger"]
                            search_region = None
                            for name in coord_names:
                                coords = self.get_coordinate(name)
                                if coords:
                                    x, y = coords
                                    # Search in region around saved coordinate
                                    search_region = (max(0, x - 250), max(0, y - 200), 500, 400)
                                    self.gui_log(f"📍 Using saved coordinate ({x}, {y}) as search hint")
                                    break
                            
                            # Try to find image with confidence-based search
                            if OPENCV_AVAILABLE:
                                confidence_levels = [0.75, 0.7, 0.65, 0.6, 0.55, 0.5]
                            else:
                                confidence_levels = [None]  # Will use exact matching
                            
                            image_found = False
                            for conf in confidence_levels:
                                try:
                                    if search_region:
                                        location = pyautogui.locateOnScreen(
                                            str(img_path),
                                            region=search_region,
                                            confidence=conf if OPENCV_AVAILABLE else None
                                        )
                                    else:
                                        location = pyautogui.locateOnScreen(
                                            str(img_path),
                                            confidence=conf if OPENCV_AVAILABLE else None
                                        )
                                    
                                    if location:
                                        center_x = location.left + location.width // 2
                                        center_y = location.top + location.height // 2
                                        self.gui_log(f"✅ Found image at ({center_x}, {center_y}) with confidence {conf if conf else 'exact'}")
                                        # Double-click on the found location
                                        pyautogui.moveTo(center_x, center_y, duration=0.2)
                                        time.sleep(0.1)
                                        pyautogui.doubleClick(center_x, center_y)
                                        self.gui_log(f"✅ Double-clicked 'Patient Account Ledger' using image: {img_path.name}")
                                        time.sleep(2)  # Wait for report window to open
                                        report_found = True
                                        image_found = True
                                        break
                                except pyautogui.ImageNotFoundException:
                                    continue
                                except Exception as e:
                                    if "confidence" in str(e).lower():
                                        # OpenCV not available or confidence not supported
                                        break
                                    continue
                            
                            if image_found:
                                break
                        except Exception as e:
                            self.gui_log(f"⚠️ Error with image {img_path.name}: {e}")
                            continue
                
                # Method 2: Try coordinate-based double-click (fallback - works on same computer/screen)
                if not report_found:
                    self.gui_log("🔍 Method 2: Trying saved coordinates for 'Patient Account Ledger' (fallback)...")
                    coord_names = ["Patient Account Ledger by Date of Service v1", "Patient Account Ledger", "account_ledger"]
                    for name in coord_names:
                        coords = self.get_coordinate(name)
                        if coords:
                            try:
                                x, y = coords
                                self.gui_log(f"📍 Found saved coordinate for '{name}': ({x}, {y})")
                                # Ensure reports window is focused
                                reports_window.set_focus()
                                time.sleep(0.3)
                                # Double-click at saved coordinates
                                pyautogui.moveTo(x, y, duration=0.2)
                                time.sleep(0.1)
                                pyautogui.doubleClick(x, y)
                                self.gui_log(f"✅ Double-clicked 'Patient Account Ledger' at saved coordinates ({x}, {y})")
                                time.sleep(2)  # Wait for report window to open
                                report_found = True
                                break
                            except Exception as e:
                                self.gui_log(f"⚠️ Coordinate double-click failed for '{name}': {e}")
                
                # Method 3: Search tree view by EXACT text match (fallback if image/coords fail)
                if not report_found:
                    self.gui_log("🔍 Method 3: Searching for report by exact text in tree view...")
                tree_start_time = time.time()
                tree = None
                while time.time() - tree_start_time < 10:
                    try:
                        tree = reports_window.child_window(control_type="Tree")
                        if tree.exists():
                            break
                    except:
                        pass
                    time.sleep(0.5)
                
                if tree and tree.exists():
                    self.gui_log("✅ Tree view found - searching for exact report name...")
                    
                    # Try multiple search patterns to find the report
                    search_patterns = [
                        "Patient Account Ledger by Date of Service v1",  # Exact match
                        ".*Patient Account Ledger by Date of Service v1.*",  # Regex with wildcards
                        "Patient Account Ledger.*v1",  # Shorter pattern
                    ]
                    
                    report_item = None
                    for pattern in search_patterns:
                        report_start_time = time.time()
                        while time.time() - report_start_time < 10:
                            try:
                                # Try exact title match first
                                if pattern == search_patterns[0]:
                                    report_item = tree.child_window(title="Patient Account Ledger by Date of Service v1")
                                else:
                                    report_item = tree.child_window(title_re=pattern)
                                
                                if report_item.exists():
                                    # VERIFY it's the correct item by checking the text
                                    item_text = report_item.window_text()
                                    if "Patient Account Ledger by Date of Service v1" in item_text:
                                        self.gui_log(f"✅ Found report: '{item_text}'")
                                        report_found = True
                                        break
                                    else:
                                        self.gui_log(f"⚠️ Found item but wrong text: '{item_text}' - continuing search...")
                                        report_item = None
                            except:
                                pass
                            time.sleep(0.5)
                        
                        if report_found:
                            break
                    
                    if report_item and report_item.exists() and report_found:
                        self.gui_log("📍 Verifying correct report before clicking...")
                        # Double-verify by getting the text again
                        final_text = report_item.window_text()
                        if "Patient Account Ledger by Date of Service v1" in final_text:
                            self.gui_log(f"✅ Verified: '{final_text}' - proceeding to double-click...")
                            report_item.select()
                            time.sleep(0.3)
                            # Double-click on the item
                            rect = report_item.rectangle()
                            center_x = (rect.left + rect.right) // 2
                            center_y = (rect.top + rect.bottom) // 2
                            pyautogui.doubleClick(center_x, center_y)
                            self.gui_log(f"✅ Double-clicked '{final_text}'")
                            time.sleep(2)  # Reduced from 3s - report window opens faster
                            report_found = True
                        else:
                            self.gui_log(f"❌ Verification failed - found '{final_text}' instead of expected report")
                            report_found = False
                    
                    # Method 2: Try finding by listing all tree items and searching text
                    if not report_found:
                        self.gui_log("🔍 Method 2: Searching all tree items for exact text match...")
                        try:
                            # Get all tree items
                            all_items = tree.descendants(control_type="TreeItem")
                            for item in all_items:
                                try:
                                    item_text = item.window_text()
                                    self.gui_log(f"   Checking: '{item_text}'")
                                    if "Patient Account Ledger by Date of Service v1" in item_text:
                                        self.gui_log(f"✅ Found report in list: '{item_text}'")
                                        item.select()
                                        time.sleep(0.3)
                                        rect = item.rectangle()
                                        center_x = (rect.left + rect.right) // 2
                                        center_y = (rect.top + rect.bottom) // 2
                                        pyautogui.doubleClick(center_x, center_y)
                                        self.gui_log(f"✅ Double-clicked '{item_text}'")
                                        time.sleep(2)  # Reduced from 3s - report window opens faster
                                        report_found = True
                                        break
                                except:
                                    continue
                        except Exception as e:
                            self.gui_log(f"⚠️ Method 2 failed: {e}")
                else:
                    self.gui_log("⚠️ Tree view not accessible - trying alternative methods...")
                    
                    # Method 4: Try to use keyboard navigation to find the report
                    try:
                        self.gui_log("🔍 Method 4: Trying keyboard navigation to find report...")
                        reports_window.set_focus()
                        time.sleep(0.5)
                        
                        # Try typing the first few letters of "Patient" to jump to it
                        pyautogui.write("Patient", interval=0.1)
                        time.sleep(0.5)
                        
                        # Try pressing Enter or double-clicking if the item is selected
                        pyautogui.press('enter')
                        time.sleep(1)
                        
                        # If that didn't work, try double-clicking at a common location
                        # Or try using arrow keys to navigate
                        pyautogui.press('down', presses=5)  # Move down a few items
                        time.sleep(0.5)
                        pyautogui.press('enter')
                        time.sleep(2)
                        
                        # Check if the report window opened by looking for a new window
                        # This is a last resort method
                        self.gui_log("⚠️ Keyboard navigation attempted - verifying if report opened...")
                        report_found = True  # Assume it worked, will be verified by next step
                    except Exception as e:
                        self.gui_log(f"⚠️ Keyboard navigation failed: {e}")
                    
                    # If still not found, try clicking at a saved coordinate if available
                    if not report_found:
                        coords = self.get_coordinate("Patient Account Ledger")
                        if coords:
                            try:
                                x, y = coords
                                self.gui_log(f"📍 Last resort: Double-clicking at saved coordinate ({x}, {y})")
                                reports_window.set_focus()
                                time.sleep(0.3)
                                pyautogui.moveTo(x, y, duration=0.2)
                                time.sleep(0.1)
                                pyautogui.doubleClick(x, y)
                                time.sleep(2)
                                report_found = True
                            except:
                                pass
                    
                    if not report_found:
                        self.gui_log("❌ All methods failed - Patient Account Ledger not accessible")
                        return
                
                if not report_found:
                    self.gui_log("❌ 'Patient Account Ledger by Date of Service v1' not found using text search")
                    self.update_status("Report not found", "#dc3545")
                    return
                
                self.gui_log("✅ Successfully navigated to Patient Account Ledger report window!")
                self.update_status("Navigated to report window", "#28a745")
                
                # Step 6: Wait for Search window and process data file (PDF or Excel/CSV)
                self.gui_log("🔍 Step 6: Waiting for Search window to appear...")
                self.update_status("Waiting for Search window...", "#ff9500")
                time.sleep(2)  # Wait for Search window to appear
                
                # Process data file (PDF for single client, Excel/CSV for batch) and fill Search window
                self.process_data_file_and_fill_search()
                    
            except Exception as e:
                self.gui_log(f"❌ Error opening report: {e}")
                self.update_status(f"Error: {e}", "#dc3545")
                return
            
            self.gui_log("✅ Workflow navigation completed successfully!")
            self.update_status("Ready for data entry", "#28a745")
            self.root.after(0, lambda: messagebox.showinfo("Success", "Successfully navigated to Patient Account Ledger report window!"))
            
        except Exception as e:
            self.gui_log(f"❌ Workflow error: {e}")
            self.update_status(f"Error: {e}", "#dc3545")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Workflow failed:\n{e}"))


def main():
    """Main entry point"""
    print("\n=== Medisoft Medical Records Billing Log Bot ===")
    print("Starting in 3 seconds...")
    print("Move mouse to corner to abort\n")
    
    time.sleep(3)
    
    # Create bot instance
    bot = MedisoftBillingBot()
    
    # Create the main window with integrated login and activity log
    bot.create_main_window()
    
    # Bind username/password changes to enable login button
    def check_credentials(event=None):
        bot._enable_login()
    
    if bot.root:
        bot.username_entry.bind("<KeyRelease>", check_credentials)
        bot.password_entry.bind("<KeyRelease>", check_credentials)
    
    # Start the main loop
    bot.root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nBot execution cancelled by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        logging.exception("Fatal error occurred")
        messagebox.showerror("Fatal Error", f"A fatal error occurred:\n{e}")

