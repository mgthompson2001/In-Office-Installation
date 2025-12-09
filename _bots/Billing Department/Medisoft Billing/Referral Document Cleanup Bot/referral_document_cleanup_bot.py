#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Referral Document Cleanup Bot

This bot cleans up old documents (30+ days) from Therapy Notes "New Referrals" patient groups.
It reads counselors from an Excel file and searches for each counselor's "New Referrals" group,
then removes documents that are 30+ days old.

Features:
- Reads counselors from Excel file
- Logs into Therapy Notes
- Searches for "{Counselor Name} New Referrals" for each counselor
- Removes documents that are 30+ days old
"""

import os
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime, timedelta
from pathlib import Path
import re
import json

# Try to import update manager
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from update_manager import UpdateManager
    UPDATE_MANAGER_AVAILABLE = True
except ImportError:
    UPDATE_MANAGER_AVAILABLE = False
    UpdateManager = None

# Try to import pandas for Excel file support
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

APP_TITLE = "Referral Document Cleanup Bot"
MAROON = "#800000"
HEADER_FG = "#ffffff"
LOG_BG = "#f5f5f5"
LOG_FG = "#000000"

# TherapyNotes URLs
BASE_TN_LOGIN_URL = "https://www.therapynotes.com/app/login/IntegritySWS/"
IPS_TN_LOGIN_URL = "https://www.therapynotes.com/app/login/IntegrityIPS/"

TN_USER_ID = "Login__UsernameField"
TN_PASS_ID = "Login__Password"
TN_BTN_ID = "Login__LogInButton"

# User data file
USERS_FILE = "referral_cleanup_users.json"


def _lazy_import_selenium():
    """Lazy import Selenium to avoid errors if not installed"""
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception as e:
        raise RuntimeError("Missing Selenium deps. Install: pip install selenium webdriver-manager") from e
    return webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys


def _parse_therapist_name_for_search(therapist_name: str) -> str:
    """
    Parse therapist name from CSV format to search format.
    
    Input formats:
    - "Doshi, Priya" → "Priya Doshi"
    - "Perez, Ethel - IPS" → "Ethel Perez"
    - "Smith-Jones, Mary" → "Mary Smith-Jones"
    
    Returns: "First Last" format with IPS indicators stripped
    """
    if not therapist_name:
        return ""
    
    # Remove IPS indicators and any trailing text after IPS (case insensitive)
    name = re.sub(r'\s*-?\s*IPS.*$', '', therapist_name, flags=re.IGNORECASE).strip()
    # Clean up any remaining dashes or extra spaces
    name = re.sub(r'\s*-\s*', ' ', name).strip()
    name = re.sub(r'\s+', ' ', name).strip()
    
    # Check if comma-separated format "Last, First"
    if ',' in name:
        parts = name.split(',', 1)
        last = parts[0].strip()
        first = parts[1].strip() if len(parts) > 1 else ""
        
        if first and last:
            return f"{first} {last}"
        elif last:
            return last
    
    # No comma - return as is (already in "First Last" format)
    return name


def _is_ips_counselor(therapist_name: str) -> bool:
    """
    Check if counselor is IPS based on name.
    Returns True if "IPS" appears in the therapist name (case insensitive).
    """
    if not therapist_name:
        return False
    return "ips" in therapist_name.lower()


def _fuzzy_match_ia_only(doc_name: str) -> bool:
    """
    Check if document name matches "IA Only" with flexible matching for typos.
    Handles variations like: "IA oly", "IA ony", "IA onl", "ia only", "IA ONLY", etc.
    Case-insensitive.
    """
    if not doc_name:
        return False
    
    doc_lower = doc_name.lower()
    
    # Exact match (case-insensitive)
    if re.search(r'\bia\s+only\b', doc_lower):
        return True
    
    # Flexible patterns for common typos
    # Pattern: "IA" followed by space and something starting with "ol" or "on"
    patterns = [
        r'\bia\s+ol[^a-z]*',  # "IA ol" (missing y), "IA ol-", etc.
        r'\bia\s+on[^a-z]*',  # "IA on" (missing ly), "IA on-", etc.
        r'\bia\s+oly',        # "IA oly" (missing space or typo)
        r'\bia\s+ony',        # "IA ony" (typo)
        r'\bia\s+onl[^y]',    # "IA onl" (missing y)
    ]
    
    for pattern in patterns:
        if re.search(pattern, doc_lower):
            return True
    
    # Check if contains "ia" and "only" (or close variations) separately
    if 'ia' in doc_lower:
        # Look for "only" with typos nearby
        only_variations = ['only', 'oly', 'ony', 'onl', 'onl-', 'oly-']
        for variation in only_variations:
            if variation in doc_lower:
                # Check if they're reasonably close (within 10 characters)
                ia_pos = doc_lower.find('ia')
                only_pos = doc_lower.find(variation)
                if only_pos > ia_pos and (only_pos - ia_pos) < 10:
                    return True
    
    return False


def _fuzzy_match_reassignment(doc_name: str, exclude_ips: bool = False) -> bool:
    """
    Check if document name starts with "Reassignment" with flexible matching for typos.
    Handles variations like: "rsignment", "reasinment", "reassgnment", etc.
    Case-insensitive.
    
    Args:
        doc_name: Document name to check
        exclude_ips: If True, exclude "IPS Reassignment" documents
    """
    if not doc_name:
        return False
    
    doc_lower = doc_name.lower()
    
    # Exclude IPS Reassignment if requested
    if exclude_ips and doc_lower.startswith("ips reassignment"):
        return False
    
    # Exact match (case-insensitive)
    if doc_lower.startswith("reassignment"):
        return True
    
    # Flexible patterns for common typos
    # Common typos: missing letters, swapped letters, etc.
    reassignment_patterns = [
        r'^reassign[^a-z]*',      # "reassign" (missing ment)
        r'^reasign[^a-z]*',       # "reasign" (missing one s)
        r'^reassgn[^a-z]*',       # "reassgn" (missing i)
        r'^reasin[^a-z]*',        # "reasin" (missing gment)
        r'^rsignment',            # "rsignment" (missing ea)
        r'^reasinment',           # "reasinment" (missing g)
        r'^reassgnment',          # "reassgnment" (missing i)
        r'^reassignmet',          # "reassignmet" (missing n)
        r'^reassignmnt',          # "reassignmnt" (missing e)
    ]
    
    for pattern in reassignment_patterns:
        if re.match(pattern, doc_lower):
            return True
    
    # Check if starts with key parts of "reassignment"
    # Must start with "re" and contain "assign" or close variation
    if doc_lower.startswith("re"):
        # Look for "assign" or variations
        assign_variations = ['assign', 'asign', 'assgn', 'asin', 'asign']
        for variation in assign_variations:
            if doc_lower.startswith("re" + variation):
                # Check if it's followed by "ment" or close variation
                remaining = doc_lower[len("re" + variation):]
                if remaining.startswith("ment") or remaining.startswith("met") or remaining.startswith("mnt") or len(remaining) < 5:
                    return True
    
    return False


class UILog:
    """Simple UI logger that writes to a text widget"""
    def __init__(self, widget):
        self.w = widget
        try:
            self.w.configure(state="disabled", bg=LOG_BG, fg=LOG_FG)
        except Exception:
            pass
    
    def write(self, msg: str):
        ts = time.strftime("[%H:%M:%S] ")
        try:
            self.w.configure(state="normal")
            self.w.insert("end", ts + msg + "\n")
            self.w.see("end")
            self.w.configure(state="disabled")
            self.w.update_idletasks()
        except Exception:
            print(ts + msg, flush=True)
    
    def flush(self):
        pass


class ReferralDocumentCleanupBot(tk.Tk):
    """Main application window for Referral Document Cleanup Bot"""
    
    def __init__(self):
        super().__init__()
        
        # Get version and update timestamp from version.json
        version = "1.0.0"
        update_timestamp = ""
        try:
            version_file = Path(__file__).parent / "version.json"
            if version_file.exists():
                with open(version_file, 'r') as f:
                    version_data = json.load(f)
                    version = version_data.get('version', '1.0.0')
                    # Get last modified date of version.json as update timestamp
                    mod_time = os.path.getmtime(version_file)
                    update_timestamp = f" - Updated {datetime.fromtimestamp(mod_time).strftime('%m/%d/%Y')}"
        except:
            pass
        
        self.title(f"{APP_TITLE} - Version {version}{update_timestamp} - Version 3.1.0, Last Updated 12/04/2025")
        self.geometry("900x700")
        self.configure(bg="#f0f0f0")
        
        # State variables
        self.driver = None
        self.logged_in = False
        self.processing = False
        self.counselors_excel_path = None
        self.users = {}
        self.current_mode = "base"  # "base" or "ips"
        self.canvas = None
        self.scrollable_frame = None
        
        # Check for updates on startup
        if UPDATE_MANAGER_AVAILABLE:
            self.after(100, self._check_for_updates)
        
        # Load saved users
        self.load_users()
        
        # Create UI
        self.create_ui()
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def _check_for_updates(self):
        """Check for updates when bot starts"""
        if not UPDATE_MANAGER_AVAILABLE:
            return
        
        try:
            # Path to G-Drive updates folder
            update_source = r"G:\Company\Software\Updates\Referral_Document_Cleanup_Bot"
            
            # Current bot directory
            bot_directory = Path(__file__).parent
            
            # Get current version from version.json
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
                bot_name="Referral Document Cleanup Bot",
                current_version=current_version,
                update_source=update_source,
                bot_directory=bot_directory,
                user_data_files=[
                    "referral_cleanup_users.json",
                    "*.log"
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
                        # Update window title
                        version_file = bot_directory / "version.json"
                        if version_file.exists():
                            try:
                                with open(version_file, 'r') as f:
                                    version_data = json.load(f)
                                    new_version = version_data.get('version', current_version)
                                    mod_time = os.path.getmtime(version_file)
                                    update_timestamp = f" - Updated {datetime.fromtimestamp(mod_time).strftime('%m/%d/%Y')}"
                                    self.title(f"{APP_TITLE} - Version {new_version}{update_timestamp} - Version 3.1.0, Last Updated 12/04/2025")
                            except:
                                pass
                    else:
                        messagebox.showerror(
                            "Update Failed",
                            f"Update failed: {result.get('error', 'Unknown error')}\n\n"
                            f"The bot will continue with the current version.",
                            icon='error'
                        )
        except Exception as e:
            # Don't block bot startup if update check fails
            pass
    
    def create_ui(self):
        """Create the user interface"""
        # Header
        header = tk.Frame(self, bg=MAROON, height=60)
        header.pack(fill="x")
        tk.Label(header, text=APP_TITLE, font=("Segoe UI", 18, "bold"),
                bg=MAROON, fg=HEADER_FG).pack(pady=15)
        
        # Create scrollable frame
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self, bg="#f0f0f0", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f0f0f0")
        
        def update_scroll_region(event=None):
            self.canvas.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        self.scrollable_frame.bind("<Configure>", update_scroll_region)
        
        canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        def on_canvas_configure(event):
            canvas_width = event.width
            self.canvas.itemconfig(canvas_frame, width=canvas_width)
        
        self.canvas.bind("<Configure>", on_canvas_configure)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Main container (now inside scrollable frame)
        main_frame = tk.Frame(self.scrollable_frame, bg="#f0f0f0")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        
        # ========== Login Section ==========
        login_section = tk.LabelFrame(main_frame, text="Therapy Notes Login",
                                     font=("Segoe UI", 11, "bold"), bg="#f0f0f0", fg=MAROON)
        login_section.pack(fill="x", pady=(0, 15))
        
        login_content = tk.Frame(login_section, bg="#f0f0f0")
        login_content.pack(fill="x", padx=15, pady=10)
        
        # Mode selection
        mode_frame = tk.Frame(login_content, bg="#f0f0f0")
        mode_frame.pack(fill="x", pady=(0, 10))
        tk.Label(mode_frame, text="Mode:", font=("Segoe UI", 10), bg="#f0f0f0").pack(side="left", padx=(0, 10))
        self.mode_var = tk.StringVar(value="base")
        tk.Radiobutton(mode_frame, text="Base", variable=self.mode_var, value="base",
                      font=("Segoe UI", 10), bg="#f0f0f0", command=self._on_mode_change).pack(side="left", padx=5)
        tk.Radiobutton(mode_frame, text="IPS", variable=self.mode_var, value="ips",
                      font=("Segoe UI", 10), bg="#f0f0f0", command=self._on_mode_change).pack(side="left", padx=5)
        
        # User dropdown
        user_frame = tk.Frame(login_content, bg="#f0f0f0")
        user_frame.pack(fill="x", pady=(0, 5))
        tk.Label(user_frame, text="Saved User:", font=("Segoe UI", 10), bg="#f0f0f0", width=12).pack(side="left", padx=(0, 5))
        self.user_dropdown = ttk.Combobox(user_frame, width=25, state="readonly")
        self.user_dropdown.pack(side="left", padx=(0, 10))
        self.user_dropdown.bind("<<ComboboxSelected>>", self._on_user_selected)
        self._update_user_dropdown()
        
        tk.Button(user_frame, text="Add User", command=self._add_user,
                 bg=MAROON, fg="white", font=("Segoe UI", 9), padx=10, pady=2,
                 cursor="hand2", relief="flat").pack(side="left", padx=2)
        tk.Button(user_frame, text="Update", command=self._update_credentials,
                 bg="#666666", fg="white", font=("Segoe UI", 9), padx=10, pady=2,
                 cursor="hand2", relief="flat").pack(side="left", padx=2)
        
        # Username
        user_row = tk.Frame(login_content, bg="#f0f0f0")
        user_row.pack(fill="x", pady=5)
        tk.Label(user_row, text="Username:", font=("Segoe UI", 10), bg="#f0f0f0", width=12).pack(side="left", padx=(0, 5))
        self.username_entry = tk.Entry(user_row, font=("Segoe UI", 10), width=40)
        self.username_entry.pack(side="left", fill="x", expand=True)
        
        # Password
        pass_row = tk.Frame(login_content, bg="#f0f0f0")
        pass_row.pack(fill="x", pady=5)
        tk.Label(pass_row, text="Password:", font=("Segoe UI", 10), bg="#f0f0f0", width=12).pack(side="left", padx=(0, 5))
        self.password_entry = tk.Entry(pass_row, font=("Segoe UI", 10), width=40, show="•")
        self.password_entry.pack(side="left", fill="x", expand=True)
        
        # Login button
        login_btn_frame = tk.Frame(login_content, bg="#f0f0f0")
        login_btn_frame.pack(fill="x", pady=(10, 0))
        self.login_btn = tk.Button(login_btn_frame, text="Login to Therapy Notes",
                                   command=self.on_login, bg=MAROON, fg="white",
                                   font=("Segoe UI", 11, "bold"), padx=20, pady=8,
                                   cursor="hand2", relief="flat")
        self.login_btn.pack()
        
        # ========== File Selection Section ==========
        file_section = tk.LabelFrame(main_frame, text="Counselors Excel File",
                                    font=("Segoe UI", 11, "bold"), bg="#f0f0f0", fg=MAROON)
        file_section.pack(fill="x", pady=(0, 15))
        
        file_content = tk.Frame(file_section, bg="#f0f0f0")
        file_content.pack(fill="x", padx=15, pady=10)
        
        file_row = tk.Frame(file_content, bg="#f0f0f0")
        file_row.pack(fill="x")
        self.file_entry = tk.Entry(file_row, font=("Segoe UI", 10), width=50)
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Button(file_row, text="Browse...", command=self._browse_excel_file,
                 bg="#666666", fg="white", font=("Segoe UI", 10), padx=15, pady=5,
                 cursor="hand2", relief="flat").pack(side="left")
        
        tk.Label(file_content, text="Excel file should contain counselor names in a column (e.g., 'Last, First' format).",
                font=("Segoe UI", 9), bg="#f0f0f0", fg="#666666", justify="left").pack(anchor="w", pady=(5, 0))
        
        # ========== Document Filter Section ==========
        filter_section = tk.LabelFrame(main_frame, text="Document Filters",
                                      font=("Segoe UI", 11, "bold"), bg="#f0f0f0", fg=MAROON)
        filter_section.pack(fill="x", pady=(0, 15))
        
        filter_content = tk.Frame(filter_section, bg="#f0f0f0")
        filter_content.pack(fill="x", padx=15, pady=10)
        
        tk.Label(filter_content, text="Select which documents to remove (30+ days old):",
                font=("Segoe UI", 10), bg="#f0f0f0").pack(anchor="w", pady=(0, 8))
        
        # Document type filters
        self.remove_all_docs = tk.BooleanVar(value=False)
        self.remove_ia_only_docs = tk.BooleanVar(value=False)
        self.remove_reassignment_docs = tk.BooleanVar(value=False)
        
        filter_row1 = tk.Frame(filter_content, bg="#f0f0f0")
        filter_row1.pack(fill="x", pady=2)
        ttk.Checkbutton(filter_row1, text="Remove all documents (30+ days)", 
                       variable=self.remove_all_docs).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(filter_row1, text="Remove 'IA Only' documents (30+ days)", 
                       variable=self.remove_ia_only_docs).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(filter_row1, text="Remove 'Reassignment' documents (30+ days)", 
                       variable=self.remove_reassignment_docs).pack(side="left")
        
        tk.Label(filter_content, text="Note: Multiple filters can be enabled. Specific filters (IA Only, Reassignment) will only remove matching documents.",
                font=("Segoe UI", 8), bg="#f0f0f0", fg="#666666", justify="left").pack(anchor="w", pady=(5, 0))
        
        # ========== Control Section ==========
        control_section = tk.Frame(main_frame, bg="#f0f0f0")
        control_section.pack(fill="x", pady=(0, 15))
        
        self.start_btn = tk.Button(control_section, text="Start Cleanup",
                                   command=self._start_cleanup, bg="#28a745", fg="white",
                                   font=("Segoe UI", 12, "bold"), padx=30, pady=10,
                                   cursor="hand2", relief="flat")
        self.start_btn.pack()
        
        # ========== Log Section ==========
        log_section = tk.LabelFrame(main_frame, text="Log",
                                   font=("Segoe UI", 11, "bold"), bg="#f0f0f0", fg=MAROON)
        log_section.pack(fill="x", pady=(0, 15))
        
        log_content = tk.Frame(log_section, bg="#f0f0f0")
        log_content.pack(fill="x", padx=15, pady=10)
        
        self.log_widget = scrolledtext.ScrolledText(log_content, height=15, width=80,
                                                    font=("Consolas", 9), wrap=tk.WORD,
                                                    bg=LOG_BG, fg=LOG_FG, state="disabled")
        self.log_widget.pack(fill="x")
        
        self.log = UILog(self.log_widget)
    
    def _on_mode_change(self):
        """Handle mode change (Base/IPS)"""
        self.current_mode = self.mode_var.get()
        self.log.write(f"Mode changed to: {self.current_mode.upper()}")
        # Clear login state when mode changes
        self.logged_in = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def load_users(self):
        """Load saved users from JSON file"""
        users_file = Path(__file__).parent / USERS_FILE
        if users_file.exists():
            try:
                with open(users_file, 'r') as f:
                    self.users = json.load(f)
            except Exception as e:
                print(f"Error loading users: {e}")
                self.users = {}
        else:
            self.users = {}
    
    def save_users(self):
        """Save users to JSON file"""
        users_file = Path(__file__).parent / USERS_FILE
        try:
            with open(users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
        except Exception as e:
            print(f"Error saving users: {e}")
    
    def _update_user_dropdown(self):
        """Update the user dropdown with current users"""
        user_names = sorted(self.users.keys())
        if user_names:
            self.user_dropdown['values'] = user_names
        else:
            self.user_dropdown['values'] = []
    
    def _on_user_selected(self, event=None):
        """Handle user selection from dropdown"""
        selected_user = self.user_dropdown.get()
        if selected_user and selected_user in self.users:
            user_data = self.users[selected_user]
            self.username_entry.delete(0, tk.END)
            self.username_entry.insert(0, user_data.get('username', ''))
            self.password_entry.delete(0, tk.END)
            self.password_entry.insert(0, user_data.get('password', ''))
    
    def _add_user(self):
        """Add a new user"""
        dialog = tk.Toplevel(self)
        dialog.title("Add User - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("450x220")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="User Name:", font=('Segoe UI', 10), bg="#f0f0f0").pack(pady=(20, 5))
        name_entry = tk.Entry(dialog, font=('Segoe UI', 10), width=35)
        name_entry.pack(pady=(0, 10))
        name_entry.focus()
        
        tk.Label(dialog, text="Username:", font=('Segoe UI', 10), bg="#f0f0f0").pack(pady=(0, 5))
        username_entry = tk.Entry(dialog, font=('Segoe UI', 10), width=35)
        username_entry.pack(pady=(0, 10))
        
        tk.Label(dialog, text="Password:", font=('Segoe UI', 10), bg="#f0f0f0").pack(pady=(0, 5))
        password_entry = tk.Entry(dialog, font=('Segoe UI', 10), width=35, show="•")
        password_entry.pack(pady=(0, 15))
        
        def save_user():
            name = name_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            if not name or not username or not password:
                messagebox.showwarning("Invalid Input", "User Name, Username, and Password are required")
                return
            
            if name in self.users:
                if not messagebox.askyesno("User Exists", f"User '{name}' already exists. Overwrite?"):
                    return
            
            self.users[name] = {
                'username': username,
                'password': password
            }
            self.save_users()
            self._update_user_dropdown()
            dialog.destroy()
            messagebox.showinfo("Success", f"User '{name}' added successfully")
        
        button_frame = tk.Frame(dialog, bg="#f0f0f0")
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Save", command=save_user,
                 bg=MAROON, fg="white", font=('Segoe UI', 10),
                 padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                 bg="#666666", fg="white", font=('Segoe UI', 10),
                 padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
    
    def _update_credentials(self):
        """Update credentials for selected user"""
        selected_user = self.user_dropdown.get()
        if not selected_user or selected_user not in self.users:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown")
            return
        
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Invalid Input", "Username and password are required")
            return
        
        self.users[selected_user] = {
            'username': username,
            'password': password
        }
        self.save_users()
        messagebox.showinfo("Success", f"Credentials updated for '{selected_user}'")
    
    def _browse_excel_file(self):
        """Browse for Excel file"""
        filename = filedialog.askopenfilename(
            title="Select Counselors Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if filename:
            self.counselors_excel_path = filename
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
            self.log.write(f"Selected Excel file: {Path(filename).name}")
    
    def on_login(self):
        """Handle login button click"""
        user = (self.username_entry.get() or "").strip()
        pwd = (self.password_entry.get() or "").strip()
        if not user or not pwd:
            messagebox.showwarning("Missing login", "Enter TherapyNotes username and password.")
            return
        self.log.write(f"[UI] Logging in to {self.current_mode.upper()} TherapyNotes…")
        threading.Thread(target=self._login_worker, args=(user, pwd), daemon=True).start()
    
    def _login_worker(self, user, pwd):
        """Login worker thread"""
        ok = False
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            opts = webdriver.ChromeOptions()
            opts.add_argument("--start-maximized")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=opts)
            
            login_url = BASE_TN_LOGIN_URL if self.current_mode == "base" else IPS_TN_LOGIN_URL
            self.driver.get(login_url)
            wait = WebDriverWait(self.driver, 15)
            
            # Find and fill username field
            usr = wait.until(EC.presence_of_element_located((By.ID, TN_USER_ID)))
            try:
                usr.clear()
                usr.click()
                time.sleep(0.2)
                usr.send_keys(user)
            except Exception:
                self.driver.execute_script("arguments[0].value = '';", usr)
                self.driver.execute_script("arguments[0].value = arguments[1];", usr, user)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", usr)
            
            # Find and fill password field
            pw_ = wait.until(EC.presence_of_element_located((By.ID, TN_PASS_ID)))
            try:
                pw_.clear()
                pw_.click()
                time.sleep(0.2)
                pw_.send_keys(pwd)
            except Exception:
                self.driver.execute_script("arguments[0].value = '';", pw_)
                self.driver.execute_script("arguments[0].value = arguments[1];", pw_, pwd)
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", pw_)
            
            # Click login button
            btn = wait.until(EC.element_to_be_clickable((By.ID, TN_BTN_ID)))
            try:
                btn.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", btn)
            
            wait.until(lambda d: d.find_element(By.LINK_TEXT, "Patients"))
            ok = True
        except Exception as e:
            self.log.write(f"[TN][ERR] {e}")
            import traceback
            self.log.write(f"[TN][ERR] Traceback: {traceback.format_exc()}")
        finally:
            self.logged_in = ok
            if ok:
                self.log.write(f"[TN] {self.current_mode.upper()} login successful.")
            else:
                self.log.write(f"[TN] {self.current_mode.upper()} login failed.")
    
    def _start_cleanup(self):
        """Start the cleanup process"""
        if not self.logged_in or not self.driver:
            messagebox.showwarning("Not Logged In", "Please login to Therapy Notes first.")
            return
        
        if not self.counselors_excel_path:
            messagebox.showwarning("Missing File", "Please select the Counselors Excel file.")
            return
        
        if self.processing:
            messagebox.showinfo("Already Processing", "Cleanup is already in progress.")
            return
        
        if not PANDAS_AVAILABLE:
            messagebox.showerror("Missing Dependency", "pandas is required. Install with: pip install pandas openpyxl")
            return
        
        self.processing = True
        self.start_btn.config(state="disabled", text="Processing...")
        threading.Thread(target=self._cleanup_worker, daemon=True).start()
    
    def _cleanup_worker(self):
        """Main cleanup worker thread"""
        try:
            # Read counselors from Excel
            self.log.write("[CLEANUP] Reading counselors from Excel file...")
            try:
                df = pd.read_excel(self.counselors_excel_path)
                self.log.write(f"[CLEANUP] Excel file loaded. Columns: {', '.join(df.columns.tolist())}")
            except Exception as e:
                self.log.write(f"[CLEANUP][ERR] Failed to read Excel file: {e}")
                self._cleanup_complete()
                return
            
            # Try to find counselor name column (common column names)
            counselor_col = None
            for col in df.columns:
                col_lower = str(col).lower()
                if any(term in col_lower for term in ['counselor', 'therapist', 'name', 'provider']):
                    counselor_col = col
                    break
            
            if counselor_col is None and len(df.columns) > 0:
                # Use first column as fallback
                counselor_col = df.columns[0]
                self.log.write(f"[CLEANUP][WARN] Could not identify counselor column, using first column: {counselor_col}")
            
            if counselor_col is None:
                self.log.write("[CLEANUP][ERR] No columns found in Excel file")
                self._cleanup_complete()
                return
            
            # Get unique counselor names - try to combine First Name and Last Name if available
            counselors = []
            first_name_col = None
            last_name_col = None
            
            # Try to find First Name and Last Name columns
            for col in df.columns:
                col_lower = str(col).lower()
                if 'first' in col_lower and 'name' in col_lower:
                    first_name_col = col
                elif 'last' in col_lower and 'name' in col_lower:
                    last_name_col = col
            
            # If we have both First Name and Last Name columns, combine them
            if first_name_col and last_name_col:
                self.log.write(f"[CLEANUP] Found First Name column: '{first_name_col}', Last Name column: '{last_name_col}'")
                # Combine first and last name
                for idx, row in df.iterrows():
                    first = str(row.get(first_name_col, '')).strip()
                    last = str(row.get(last_name_col, '')).strip()
                    if first and last:
                        counselors.append(f"{first} {last}")
                    elif last:
                        counselors.append(last)
                    elif first:
                        counselors.append(first)
            else:
                # Use the counselor column as-is
                counselors = df[counselor_col].dropna().unique().tolist()
            
            # Remove duplicates while preserving order
            seen = set()
            unique_counselors = []
            for c in counselors:
                c_str = str(c).strip()
                if c_str and c_str not in seen:
                    seen.add(c_str)
                    unique_counselors.append(c_str)
            counselors = unique_counselors
            
            self.log.write(f"[CLEANUP] Found {len(counselors)} unique counselors")
            
            if not counselors:
                self.log.write("[CLEANUP][ERR] No counselors found in Excel file")
                self._cleanup_complete()
                return
            
            # Process each counselor
            total_removed = 0
            total_skipped = 0
            
            for idx, counselor_name in enumerate(counselors, 1):
                if not self.processing:  # Check if user stopped
                    break
                
                self.log.write(f"\n[CLEANUP] Processing counselor {idx}/{len(counselors)}: {counselor_name}")
                
                # Check if this is an IPS counselor (if in Base mode, skip IPS counselors)
                if self.current_mode == "base" and _is_ips_counselor(counselor_name):
                    self.log.write(f"[CLEANUP] Skipping IPS counselor in Base mode: {counselor_name}")
                    total_skipped += 1
                    continue
                
                # Check if this is a Base counselor (if in IPS mode, skip Base counselors)
                if self.current_mode == "ips" and not _is_ips_counselor(counselor_name):
                    self.log.write(f"[CLEANUP] Skipping Base counselor in IPS mode: {counselor_name}")
                    total_skipped += 1
                    continue
                
                # Navigate to Patients page - ALWAYS click Patients button to ensure search field is visible
                # Don't rely on URL check alone, as we might be on a patient detail page
                if not self._click_patients(force_click=True):
                    self.log.write(f"[CLEANUP] Failed to navigate to Patients page, skipping")
                    total_skipped += 1
                    continue
                
                # Search for counselor's "New Referrals" group
                if not self._search_counselor_new_referrals(counselor_name):
                    self.log.write(f"[CLEANUP] Failed to find '{counselor_name} New Referrals', skipping")
                    total_skipped += 1
                    continue
                
                # Open Documents tab
                if not self._open_documents_tab():
                    self.log.write(f"[CLEANUP] Failed to open Documents tab, skipping")
                    total_skipped += 1
                    continue
                
                # Remove old documents based on filters
                removed, skipped = self._remove_old_documents()
                total_removed += removed
                total_skipped += skipped
                
                # Small delay between counselors
                time.sleep(1)
            
            self.log.write(f"\n[CLEANUP] Complete! Removed: {total_removed} documents, Skipped: {total_skipped} counselors")
            
        except Exception as e:
            self.log.write(f"[CLEANUP][ERR] Error during cleanup: {e}")
            import traceback
            self.log.write(f"[CLEANUP][ERR] Traceback: {traceback.format_exc()}")
        finally:
            self._cleanup_complete()
    
    def _cleanup_complete(self):
        """Called when cleanup is complete"""
        self.processing = False
        self.start_btn.config(state="normal", text="Start Cleanup")
    
    def _click_patients(self, force_click: bool = False) -> bool:
        """Click Patients link - optimized: quick checks, fast exit
        
        Args:
            force_click: If True, always click Patients link even if we appear to be on Patients page
        """
        if not self.driver:
            self.log.write("[NAV] No driver.")
            return False
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            
            # If force_click is False, do quick checks first
            if not force_click:
                # Quick check: URL first (fastest)
                try:
                    current_url = self.driver.current_url
                    if "/patients" in current_url.lower():
                        # Also verify search input is visible
                        try:
                            search_input = self.driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
                            if search_input and search_input.is_displayed():
                                self.log.write("[NAV] Already on Patients page (URL check).")
                                return True
                        except Exception:
                            pass
                except Exception:
                    pass
                
                # Quick check: search input (fast, no wait)
                try:
                    search_input = self.driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
                    if search_input and search_input.is_displayed():
                        self.log.write("[NAV] Already on Patients page (search input found).")
                        return True
                except Exception:
                    pass
            
            # Not on Patients page or force_click is True, click Patients link
            wait = WebDriverWait(self.driver, 5)
            try:
                patients_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Patients")))
                patients_link.click()
                self.log.write("[NAV] Clicked Patients link.")
                # Wait for search input to be visible
                try:
                    wait.until(EC.presence_of_element_located((By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")))
                    time.sleep(0.3)  # Small delay to ensure page is fully loaded
                except Exception:
                    pass
                return True
            except Exception:
                # If we can't find Patients link, try to verify we're on the page
                try:
                    search_input = self.driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
                    if search_input and search_input.is_displayed():
                        self.log.write("[NAV] Could not find Patients link but search input is visible - assuming already on Patients page.")
                        return True
                except Exception:
                    pass
                self.log.write("[NAV][WARN] Could not find Patients link and search input not visible.")
                return False
        except Exception as e:
            self.log.write(f"[NAV][WARN] {e}, but proceeding")
            return True
    
    def _search_counselor_new_referrals(self, counselor_name: str, timeout: int = 15) -> bool:
        """Search for '{Counselor Name} New Referrals' with retry logic that progressively shortens the search term"""
        if not self.driver:
            self.log.write("[SRCH] No driver.")
            return False
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(self.driver, timeout)
            
            parsed_name = _parse_therapist_name_for_search(counselor_name)
            # Create search term variations: full name, then progressively shorter
            name_parts = parsed_name.split()
            search_variations = []
            # Start with full name
            search_variations.append(f"{parsed_name} New Referrals".strip())
            # Then try with one less word at a time
            for i in range(len(name_parts) - 1, 0, -1):
                shorter_name = " ".join(name_parts[:i])
                search_variations.append(f"{shorter_name} New Referrals".strip())
            
            self.log.write(f"[SRCH] CSV: '{counselor_name}' → Will try {len(search_variations)} search variations")
            
            # Try each search variation until one works
            for attempt, target_text in enumerate(search_variations, 1):
                self.log.write(f"[SRCH] Attempt {attempt}/{len(search_variations)}: Searching: '{target_text}'")
                
                search_input = None
                for by, val in [
                    (By.ID, "ctl00_BodyContent_TextBoxSearchPatientName"),
                    (By.NAME, "ctl00$BodyContent$TextBoxSearchPatientName"),
                    (By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']"),
                ]:
                    try:
                        search_input = wait.until(EC.element_to_be_clickable((by, val)))
                        break
                    except Exception:
                        pass
                
                if not search_input:
                    self.log.write("[SRCH][ERR] Search input not found.")
                    return False
                
                # Clear the input before each attempt
                try:
                    search_input.clear()
                except Exception:
                    pass
                
                # Type character by character like a human (required for dropdown to appear)
                used_js_fallback = False
                try:
                    search_input.click()
                    # Type character by character with small delay to trigger dropdown properly
                    for char in target_text:
                        search_input.send_keys(char)
                        time.sleep(0.05)  # Small delay between characters
                except Exception as e:
                    self.log.write(f"[SRCH][WARN] send_keys failed: {e}, using JavaScript fallback with character-by-character typing...")
                    used_js_fallback = True
                    try:
                        # JavaScript fallback: clear first, then type character by character to trigger dropdown
                        self.driver.execute_script("""
                            var input = document.getElementById('ctl00_BodyContent_TextBoxSearchPatientName');
                            if (input) {
                                input.focus();
                                input.value = '';
                            }
                        """)
                        for char in target_text:
                            self.driver.execute_script("""
                                var input = document.getElementById('ctl00_BodyContent_TextBoxSearchPatientName');
                                if (input) {
                                    input.focus();
                                    input.value += arguments[0];
                                    input.dispatchEvent(new Event('input', { bubbles: true }));
                                    input.dispatchEvent(new Event('keyup', { bubbles: true }));
                                }
                            """, char)
                            time.sleep(0.05)  # Small delay between characters
                    except Exception as js_e:
                        self.log.write(f"[SRCH][ERR] JavaScript fallback failed: {js_e}")
                        continue  # Try next variation
                
                # Wait for dropdown to appear (don't click away - dropdown will disappear)
                time.sleep(0.8)
                
                # Enhanced dropdown detection with multiple strategies
                container = None
                dropdown_found = False
                
                # Strategy 1: Wait for ContentBubbleResultsContainer (exact element ID)
                try:
                    container = wait.until(EC.presence_of_element_located((By.ID, "ContentBubbleResultsContainer")))
                    dropdown_found = True
                    self.log.write(f"[SRCH][DEBUG] Found dropdown container via ContentBubbleResultsContainer")
                except Exception:
                    pass
                
                # Strategy 2: Look for alternative dropdown containers
                if not dropdown_found:
                    alternative_selectors = [
                        (By.CSS_SELECTOR, "[id*='ResultsContainer']"),
                        (By.CSS_SELECTOR, "[id*='Dropdown']"),
                        (By.CSS_SELECTOR, "[id*='Suggest']"),
                        (By.CSS_SELECTOR, "[class*='dropdown']"),
                        (By.CSS_SELECTOR, "[class*='suggest']"),
                        (By.CSS_SELECTOR, "[class*='autocomplete']"),
                        (By.XPATH, "//div[contains(@class, 'dropdown') or contains(@class, 'suggest')]"),
                        (By.XPATH, "//ul[contains(@class, 'dropdown') or contains(@class, 'suggest')]"),
                    ]
                    
                    for by, selector in alternative_selectors:
                        try:
                            container = self.driver.find_element(by, selector)
                            if container and container.is_displayed():
                                dropdown_found = True
                                self.log.write(f"[SRCH][DEBUG] Found dropdown container via alternative selector: {selector}")
                                break
                        except Exception:
                            continue
                
                # Strategy 3: Wait longer and retry with different search approach
                if not dropdown_found:
                    time.sleep(1.5)  # Wait longer
                    
                    # Try triggering dropdown - use JavaScript if send_keys failed earlier
                    try:
                        if used_js_fallback:
                            # Use JavaScript to trigger dropdown
                            self.driver.execute_script("""
                                var input = document.getElementById('ctl00_BodyContent_TextBoxSearchPatientName');
                                if (input) {
                                    input.focus();
                                    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
                                    input.dispatchEvent(new KeyboardEvent('keyup', { key: 'ArrowDown', bubbles: true }));
                                }
                            """)
                        else:
                            search_input.click()
                            search_input.send_keys(Keys.ARROW_DOWN)  # Trigger dropdown
                        time.sleep(1)
                        
                        # Try ContentBubbleResultsContainer again
                        container = wait.until(EC.presence_of_element_located((By.ID, "ContentBubbleResultsContainer")))
                        dropdown_found = True
                        self.log.write(f"[SRCH][DEBUG] Found dropdown container after retry")
                    except Exception:
                        pass
                
                if not dropdown_found:
                    self.log.write(f"[SRCH][WARN] Dropdown container did not appear for '{target_text}', trying next variation...")
                    continue  # Try next search variation
                
                # Find items in dropdown container
                items = []
                for xp in [".//a[normalize-space()]", ".//div[@role='option']"]:
                    try:
                        items.extend(container.find_elements(By.XPATH, xp))
                    except Exception:
                        pass
                
                if not items:
                    self.log.write(f"[SRCH][WARN] No items found in dropdown for '{target_text}', trying next variation...")
                    continue  # Try next search variation
                
                # Success! Found items in dropdown
                self.log.write(f"[SRCH][DEBUG] Found {len(items)} items in dropdown for '{target_text}'")
                
                tl = target_text.lower()
                matched_text = None
                for el in items:
                    label = (el.text or "").strip()
                    if label and tl in label.lower():
                        matched_text = label
                        break
                
                if not matched_text:
                    matched_text = items[0].text.strip()
                    self.log.write(f"[SRCH][WARN] No exact match; selecting first option: '{matched_text}'")
                
                # Re-find the element right before clicking to avoid stale element
                matched = None
                try:
                    # Re-find container and items fresh
                    container = self.driver.find_element(By.ID, "ContentBubbleResultsContainer")
                    fresh_items = []
                    for xp in [".//a[normalize-space()]", ".//div[@role='option']"]:
                        try:
                            fresh_items.extend(container.find_elements(By.XPATH, xp))
                        except Exception:
                            pass
                    
                    # Find the matched item by text
                    for el in fresh_items:
                        label = (el.text or "").strip()
                        if label == matched_text or (matched_text and matched_text.lower() in label.lower()):
                            matched = el
                            break
                    
                    if not matched and fresh_items:
                        matched = fresh_items[0]
                except Exception as e:
                    self.log.write(f"[SRCH][WARN] Could not re-find element, using original: {e}")
                    # Fallback to original items
                    for el in items:
                        label = (el.text or "").strip()
                        if label and tl in label.lower():
                            matched = el
                            break
                    if not matched:
                        matched = items[0] if items else None
                
                if not matched:
                    self.log.write(f"[SRCH][WARN] Could not find element to click for '{target_text}', trying next variation...")
                    continue  # Try next search variation
                
                # Click the matched element
                clicked = False
                try:
                    matched.click()
                    clicked = True
                    self.log.write(f"[SRCH] Clicked matched item: '{matched_text}'")
                except Exception as e:
                    try:
                        self.driver.execute_script("arguments[0].click();", matched)
                        clicked = True
                        self.log.write(f"[SRCH] Clicked matched item via JavaScript: '{matched_text}'")
                    except Exception as e2:
                        self.log.write(f"[SRCH][WARN] Click failed but may have worked: {e2}")
                        # Still return True - user says click is working
                        clicked = True
                
                self.log.write("[SRCH] Selection made, waiting for page load...")
                time.sleep(0.6)
                return True  # Success! Break out of retry loop
            
            # If we get here, all variations failed
            self.log.write("[SRCH][ERR] All search variations failed - no dropdown items found for any variation.")
            return False
            
        except Exception as e:
            self.log.write(f"[SRCH][ERR] {e}")
            return False
    
    
    def _open_documents_tab(self, timeout: int = 15) -> bool:
        """Open Documents tab"""
        if not self.driver:
            return False
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(self.driver, timeout)
            
            # Find Documents tab
            tab_selector = None
            for by, val in [
                (By.LINK_TEXT, "Documents"),
                (By.XPATH, "//a[contains(@href, '#tab=Documents')]"),
            ]:
                try:
                    tab = wait.until(EC.element_to_be_clickable((by, val)))
                    tab_selector = (by, val)
                    break
                except Exception:
                    pass
            
            if not tab_selector:
                self.log.write("[DOCS][ERR] Documents tab not found.")
                return False
            
            # Click tab
            try:
                tab = wait.until(EC.element_to_be_clickable(tab_selector))
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab)
                tab.click()
            except Exception as e1:
                try:
                    tab = wait.until(EC.presence_of_element_located(tab_selector))
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", tab)
                except Exception as e2:
                    self.log.write(f"[DOCS][WARN] Click failed but may have worked: {e2}")
            
            # Wait for Documents tab to load
            max_wait_time = 10.0
            check_interval = 0.3
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                try:
                    upload_btn = self.driver.find_elements(By.XPATH, "//button[contains(normalize-space(.), 'Upload Patient File')]")
                    doc_table = self.driver.find_elements(By.XPATH, "//table//tr[td]")
                    if upload_btn or (doc_table and len(doc_table) > 0):
                        elapsed = time.time() - start_time
                        self.log.write(f"[DOCS] Documents tab loaded (detected after {elapsed:.1f}s)")
                        return True
                except Exception:
                    pass
                time.sleep(check_interval)
            
            self.log.write("[DOCS][WARN] Documents tab may not be fully loaded, but proceeding anyway")
            return True
            
        except Exception as e:
            self.log.write(f"[DOCS][WARN] Error but proceeding: {e}")
            return True
    
    def _remove_old_documents(self, timeout: int = 15) -> tuple:
        """
        Remove documents that are 30+ days old based on enabled filters.
        Returns (removed_count, skipped_count)
        """
        if not self.driver:
            return (0, 0)
        
        # Check if any filters are enabled
        remove_all = self.remove_all_docs.get()
        remove_ia_only = self.remove_ia_only_docs.get()
        remove_reassignment = self.remove_reassignment_docs.get()
        
        if not remove_all and not remove_ia_only and not remove_reassignment:
            self.log.write("[CLEANUP] No document filters enabled. Skipping document removal.")
            return (0, 0)
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(self.driver, timeout)
            
            self.log.write("[CLEANUP] Checking for documents to remove...")
            if remove_all:
                self.log.write("[CLEANUP] Filter: Remove all documents (30+ days) - ENABLED")
            if remove_ia_only:
                self.log.write("[CLEANUP] Filter: Remove 'IA Only' documents (30+ days) - ENABLED")
            if remove_reassignment:
                self.log.write("[CLEANUP] Filter: Remove 'Reassignment' documents (30+ days) - ENABLED")
            
            time.sleep(0.5)
            
            # Find document rows
            doc_rows = []
            try:
                all_rows = self.driver.find_elements(By.XPATH, "//table//tr[td]")
                for row in all_rows:
                    row_text_lower = (row.text or "").lower()
                    # Skip header rows
                    if any(header in row_text_lower for header in ['document', 'service', 'date', 'author', 'status']):
                        if len([c for c in row_text_lower.split() if c in ['document', 'service', 'date']]) >= 2:
                            continue
                    doc_rows.append(row)
                
                if doc_rows:
                    self.log.write(f"[CLEANUP] Found {len(doc_rows)} document row(s) in table")
                else:
                    # Strategy 2: Try direct search for rows containing "IA Only" if that filter is enabled
                    if remove_ia_only:
                        rows = self.driver.find_elements(By.XPATH, "//tr[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ia only')]")
                        doc_rows = rows
                        self.log.write(f"[CLEANUP] Found {len(doc_rows)} potential document row(s) via 'IA Only' text search")
            except Exception as e:
                self.log.write(f"[CLEANUP][WARN] Could not find rows: {e}")
                return (0, 0)
            
            if not doc_rows:
                self.log.write("[CLEANUP] No document rows found.")
                return (0, 0)
            
            cutoff_date = datetime.now() - timedelta(days=30)
            self.log.write(f"[CLEANUP] Looking for documents older than {cutoff_date.strftime('%m/%d/%Y')}")
            
            removed_count = 0
            skipped_count = 0
            
            # Process documents in a loop, re-finding rows after each deletion to avoid stale elements
            max_iterations = 100  # Safety limit
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                # Re-find document rows each iteration (after DOM refresh from deletion)
                time.sleep(0.2)
                
                doc_rows = []
                try:
                    all_rows = self.driver.find_elements(By.XPATH, "//table//tr[td]")
                    for row in all_rows:
                        row_text_lower = (row.text or "").lower()
                        # Skip header rows
                        if any(header in row_text_lower for header in ['document', 'service', 'date', 'author', 'status']):
                            if len([c for c in row_text_lower.split() if c in ['document', 'service', 'date']]) >= 2:
                                continue
                        doc_rows.append(row)
                    
                    if not doc_rows:
                        # Strategy 2: Try direct search for rows containing "IA Only" or "Reassignment" if those filters are enabled
                        if remove_ia_only:
                            rows = self.driver.find_elements(By.XPATH, "//tr[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ia only')]")
                            doc_rows = rows
                        elif remove_reassignment:
                            rows = self.driver.find_elements(By.XPATH, "//tr[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reassignment')]")
                            doc_rows = rows
                except Exception as e:
                    self.log.write(f"[CLEANUP][WARN] Could not re-find rows: {e}")
                    break
                
                if not doc_rows:
                    self.log.write("[CLEANUP] No more document rows found.")
                    break
                
                # Find the first document that matches our criteria
                found_document_to_remove = False
                
                for row_idx, row in enumerate(doc_rows, 1):
                    try:
                        # Re-find row to avoid stale element
                        try:
                            row_text = (row.text or "").strip()
                        except Exception:
                            # Row is stale, skip it
                            continue
                        
                        # Check if row has a date
                        if not re.search(r'\d{1,2}/\d{1,2}/\d{4}', row_text):
                            continue
                        
                        # Get document name from span element if available (more reliable)
                        doc_name = None
                        try:
                            doc_name_span = row.find_element(By.XPATH, ".//span[@class='documentNameSpan']")
                            doc_name = (doc_name_span.text or "").strip()
                        except Exception:
                            # Fallback: use row text
                            doc_name = row_text
                        
                        if not doc_name:
                            continue
                        
                        doc_name_lower = doc_name.lower()
                        
                        # Apply filters with fuzzy matching for typos (case-insensitive)
                        is_ia_only = _fuzzy_match_ia_only(doc_name)
                        is_reassignment = _fuzzy_match_reassignment(doc_name, exclude_ips=(self.current_mode == "base"))
                        
                        # Apply filter logic
                        should_remove = False
                        
                        if remove_all:
                            # If "all documents" is enabled, remove everything (unless specific filters override)
                            should_remove = True
                        else:
                            # Only remove if specific filter matches
                            if remove_ia_only and is_ia_only:
                                should_remove = True
                            if remove_reassignment and is_reassignment:
                                should_remove = True
                        
                        if not should_remove:
                            continue
                        
                        # Find date in row
                        date_cells = row.find_elements(By.XPATH, ".//td[contains(text(), '/202') or contains(text(), '/2025') or contains(text(), '/2024')]")
                        
                        doc_date_str = None
                        for cell in date_cells:
                            cell_text = (cell.text or "").strip()
                            if re.match(r'\d{1,2}/\d{1,2}/\d{4}', cell_text):
                                doc_date_str = cell_text
                                break
                        
                        if not doc_date_str:
                            continue
                        
                        # Parse date
                        try:
                            doc_date = datetime.strptime(doc_date_str, "%m/%d/%Y")
                        except ValueError:
                            try:
                                doc_date = datetime.strptime(doc_date_str, "%m/%d/%y")
                            except ValueError:
                                continue
                        
                        days_old = (datetime.now() - doc_date).days
                        if days_old < 30:
                            continue
                        
                        # Determine document type for logging
                        doc_type = "Regular"
                        if is_ia_only:
                            doc_type = "IA Only"
                        elif is_reassignment:
                            doc_type = "Reassignment"
                        
                        self.log.write(f"[CLEANUP] Found {doc_type} document '{doc_name[:50]}...' dated {doc_date_str} ({days_old} days old) - will remove")
                        
                        # Re-find row to avoid stale element before clicking
                        try:
                            # Find row by document name to get fresh reference
                            all_rows_fresh = self.driver.find_elements(By.XPATH, "//table//tr[td]")
                            row_fresh = None
                            for r in all_rows_fresh:
                                try:
                                    r_text = (r.text or "").strip()
                                    if doc_name in r_text or (doc_name_span and doc_name_span.text in r_text):
                                        row_fresh = r
                                        break
                                except Exception:
                                    continue
                            
                            if not row_fresh:
                                # Fallback: use original row
                                row_fresh = row
                        except Exception:
                            row_fresh = row
                        
                        # Find pencil icon
                        pencil_icon = None
                        try:
                            pencil_icon = row_fresh.find_element(By.XPATH, ".//div[contains(@class, 'fa-icon') and contains(@class, 'pencil-alt')]")
                        except Exception:
                            try:
                                pencil_icon = row_fresh.find_element(By.XPATH, ".//*[contains(@class, 'pencil-alt')]")
                            except Exception:
                                try:
                                    pencil_icon = row_fresh.find_element(By.XPATH, ".//*[contains(@class, 'pencil')]")
                                except Exception:
                                    continue
                        
                        if not pencil_icon:
                            continue
                        
                        # Click pencil icon - scroll element into view first
                        try:
                            # Scroll the row into view to ensure pencil icon is visible
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center', behavior:'smooth'});", row_fresh)
                            time.sleep(0.2)
                            # Then scroll the pencil icon itself
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center', behavior:'smooth'});", pencil_icon)
                            time.sleep(0.2)
                            pencil_icon.click()
                            self.log.write(f"[CLEANUP] Clicked pencil icon")
                            time.sleep(0.5)
                        except Exception as e:
                            self.log.write(f"[CLEANUP][WARN] Failed to click pencil icon: {e}")
                            try:
                                cancel_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close')]")
                                cancel_btn.click()
                                time.sleep(0.3)
                            except Exception:
                                pass
                            continue
                        
                        # Click "Delete Document" - scroll into view first
                        delete_link = None
                        try:
                            delete_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Delete Document')]")))
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center', behavior:'smooth'});", delete_link)
                            time.sleep(0.2)
                            delete_link.click()
                            self.log.write(f"[CLEANUP] Clicked 'Delete Document'")
                            time.sleep(0.5)
                        except Exception as e:
                            self.log.write(f"[CLEANUP][WARN] Failed to find/click 'Delete Document': {e}")
                            try:
                                cancel_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close')]")
                                cancel_btn.click()
                                time.sleep(0.3)
                            except Exception:
                                pass
                            continue
                        
                        # Click "Delete File" button - scroll into view first
                        try:
                            delete_file_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='button' and @value='Delete File']")))
                            self.driver.execute_script("arguments[0].scrollIntoView({block:'center', behavior:'smooth'});", delete_file_btn)
                            time.sleep(0.2)
                            delete_file_btn.click()
                            self.log.write(f"[CLEANUP] Clicked 'Delete File' button - document removed")
                            removed_count += 1
                            found_document_to_remove = True
                            
                            # Wait for deletion to complete and DOM to refresh
                            time.sleep(1.2)
                            
                            # Close any dialogs that might have appeared
                            try:
                                cancel_btns = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close') or contains(text(), 'OK')]")
                                for btn in cancel_btns:
                                    try:
                                        if btn.is_displayed():
                                            btn.click()
                                            time.sleep(0.3)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            
                            break  # Break out of row loop to re-find all rows
                        except Exception as e:
                            self.log.write(f"[CLEANUP][WARN] Failed to find/click 'Delete File' button: {e}")
                            try:
                                cancel_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close')]")
                                cancel_btn.click()
                                time.sleep(0.3)
                            except Exception:
                                pass
                            continue
                        
                    except Exception as e:
                        # Check if it's a stale element error - if so, break to re-find rows
                        if "stale" in str(e).lower():
                            self.log.write(f"[CLEANUP][WARN] Stale element detected, re-finding rows...")
                            break
                        self.log.write(f"[CLEANUP][WARN] Error processing row: {e}")
                        continue
                
                # If we didn't find any document to remove, we're done
                if not found_document_to_remove:
                    break
            
            # CRITICAL: Close ALL dialogs/modals before returning
            self.log.write("[CLEANUP] Closing any remaining dialogs after deletion...")
            try:
                time.sleep(0.5)
                
                # Find and close all dialogs/modals
                all_dialogs = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'Dialog') or contains(@class, 'dialog') or contains(@class, 'modal')]")
                for dialog in all_dialogs:
                    try:
                        if dialog.is_displayed():
                            # Try multiple strategies to close
                            close_btns = dialog.find_elements(By.XPATH, ".//button[contains(text(), 'Close') or contains(text(), 'Cancel') or contains(@class, 'close')] | .//*[@aria-label='Close' or @title='Close'] | .//span[contains(@class, 'close')]")
                            if close_btns:
                                self.driver.execute_script("arguments[0].click();", close_btns[0])
                                self.log.write("[CLEANUP] Closed remaining dialog")
                                time.sleep(0.3)
                            else:
                                # Try pressing Escape key on the dialog
                                self.driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}));", dialog)
                                time.sleep(0.2)
                    except Exception:
                        pass
                
                # Also try pressing Escape on the body to close any modal overlays
                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    self.driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}));", body)
                    time.sleep(0.2)
                except Exception:
                    pass
                
                # Final wait to ensure dialogs are fully closed
                time.sleep(0.5)
            except Exception as e:
                self.log.write(f"[CLEANUP][WARN] Error closing dialogs: {e}")
            
            self.log.write(f"[CLEANUP] Document removal complete. Removed: {removed_count}, Skipped: {skipped_count}")
            return (removed_count, skipped_count)
            
        except Exception as e:
            self.log.write(f"[CLEANUP][ERR] Error during document removal: {e}")
            import traceback
            self.log.write(f"[CLEANUP][ERR] Traceback: {traceback.format_exc()}")
            return (0, 0)


def main():
    """Main entry point"""
    app = ReferralDocumentCleanupBot()
    app.mainloop()


if __name__ == "__main__":
    main()

