# isws_remove_counselor_botcursor3.py
# Enhanced version with complete workflow implementation
# - 6-step workflow: Remove Counselor link → Close button → Case link → extract data → workflow side panel → repeat
# - Data extraction from Service Files section (red status bubbles + Primary Worker names)
# - CSV generation after bot completion
# - Advanced search handling without page refresh
# - STOP BUTTON for emergency halt
#
# Install:
#   pip install selenium webdriver-manager pandas
#
# Run:
#   python isws_remove_counselor_botcursor3.py
#
# CRITICAL: Import monitoring bridge BEFORE any Selenium imports
# This ensures browser activity is recorded for AI training
import sys
from pathlib import Path
_current_file = Path(__file__).resolve()
if "In-Office Installation" in str(_current_file):
    # Bot is in: In-Office Installation\_bots\Cursor versions\Goose\isws_remove_counselor_botcursor3.py
    # Need to go up 4 levels to get to In-Office Installation
    installation_dir = _current_file.parent.parent.parent.parent
    system_dir = installation_dir / "_system"
    if system_dir.exists() and str(system_dir) not in sys.path:
        sys.path.insert(0, str(system_dir))
    try:
        import fix_direct_launches
        fix_direct_launches.install_monitoring_bridge()
    except Exception:
        pass  # Monitoring is optional - bot will still work without it

import time
import threading
import csv
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import json
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, ElementClickInterceptedException, ElementNotInteractableException

LOGIN_URL = "https://integrityseniorservices.athena-us.com/acm_loginControl"
DATE_FMT = "%m/%d/%Y"

# Enhanced selectors with multiple fallback options
SEL = {
    # Login
    "user": (By.ID, "login_userName"),
    "pass": (By.ID, "login_password"),
    "login_btn": (By.CSS_SELECTOR, "button[type='submit']"),
    # Drawer
    "workflow_handle": (By.ID, "taskHandle"),
    "drawer_panel_task": (By.ID, "task"),
    # Tabs
    "tab_current": (By.ID, "taskCurrentView"),
    "tab_advanced": (By.ID, "taskAdvancedView"),
    # Containers / tables
    "current_container": (By.ID, "currentTasksContainer"),
    "queue_container": (By.ID, "queuedTasksContainer"),
    "current_body": (By.ID, "taskCurrentBody"),
    "queue_body": (By.ID, "taskQueueBody"),
    # Load more
    "current_load_more": (By.ID, "currentTasksLoadMoreButton"),
    "queue_load_more": (By.ID, "queuedTasksLoadMoreButton"),
    # Row bits - UPDATED WITH MULTIPLE SELECTORS
    "row_subject_link": [
        (By.CSS_SELECTOR, "td.taskSubject a"),
        (By.CSS_SELECTOR, "td a[href*='task']"),
        (By.CSS_SELECTOR, ".task-subject a"),
        (By.CSS_SELECTOR, "tr td:first-child a"),
        (By.CSS_SELECTOR, "td a"),
        (By.CSS_SELECTOR, "tr a[href]"),
        (By.CSS_SELECTOR, "a[href*='workflow']"),
        (By.CSS_SELECTOR, "a[href*='task']"),
        (By.CSS_SELECTOR, "td:first-child a"),
        (By.CSS_SELECTOR, "tr td:nth-child(1) a")
    ],
    "row_date": [
        (By.CSS_SELECTOR, "td.taskDate"),
        (By.CSS_SELECTOR, "td[class*='date']"),
        (By.CSS_SELECTOR, ".task-date"),
        (By.CSS_SELECTOR, "tr td:nth-child(2)"),
        (By.CSS_SELECTOR, "tr td:nth-child(3)"),
        (By.CSS_SELECTOR, "td:contains('2024')"),
        (By.CSS_SELECTOR, "td:contains('2025')")
    ],
    "row_pickup": [
        (By.CSS_SELECTOR, "td.taskAction a[data-action='pickup']"),
        (By.CSS_SELECTOR, "a[data-action='pickup']"),
        (By.CSS_SELECTOR, "a:contains('Pickup')"),
        (By.CSS_SELECTOR, "a:contains('pickup')"),
        (By.CSS_SELECTOR, ".pickup-link"),
        (By.CSS_SELECTOR, "a[href*='pickup']"),
        (By.CSS_SELECTOR, "td:last-child a"),
        (By.CSS_SELECTOR, "tr td a:last-child")
    ],
    # Advanced
    "adv_from": (By.ID, "fromDate"),
    "adv_to": (By.ID, "toDate"),
    "adv_search": (By.ID, "advancedTaskSearchBtn"),
    # NEW: Workflow navigation selectors
    "remove_counselor_links": [
        (By.XPATH, "//a[contains(text(), 'Remove Counselor from Client in TN')]"),
        (By.CSS_SELECTOR, "a[href*='TaskThreadServlet']"),
        (By.CSS_SELECTOR, "a[href*='actionType=view']")
    ],
    "close_button": [
        (By.XPATH, "//div[@class='cbb box_t3s']//h6//div//a[text()='Close']"),  # Most specific - exact structure with nested div
        (By.XPATH, "//div[contains(@class, 'cbb') and contains(@class, 'box_t3s')]//h6//div//a[text()='Close']"),  # Fallback
        (By.XPATH, "//a[text()='Close' and contains(@href, 'closeTask')]"),  # Find by href content
        (By.XPATH, "//a[text()='Close' and contains(@href, 'doAjax')]"),  # Find by doAjax
        (By.XPATH, "//h2[text()='Assigned']/..//a[text()='Close']"),  # Find by Assigned heading
        (By.XPATH, "//div[contains(@class, 'cbb')]//a[text()='Close']"),  # Broader search
        (By.XPATH, "//a[text()='Close']"),  # Fallback
        (By.CSS_SELECTOR, "div.cbb.box_t3s h6 div a[href*='closeTask']"),  # CSS with nested div
        (By.CSS_SELECTOR, "a[href*='closeTask']"),  # Fallback
        (By.CSS_SELECTOR, "a[href*='javascript:doAjax'][href*='closeTask']"),  # Fallback
        (By.CSS_SELECTOR, "a[href*='TaskThreadServlet'][href*='closeTask']")  # Fallback
    ],
    "case_link": [
        (By.XPATH, "//td[@class='title' and text()='Case']/following-sibling::td/a"),
        (By.XPATH, "//a[contains(text(), 'Case (')]"),
        (By.CSS_SELECTOR, "a[href*='acm_caseFileControl'][href*='kCaseID']"),
        (By.CSS_SELECTOR, "a[href*='acm_caseFileControl']"),
        (By.XPATH, "//a[contains(text(), 'Case')]"),
        (By.CSS_SELECTOR, "a[href*='actionType=view&kCaseID']"),
        (By.CSS_SELECTOR, "a[href*='kCaseID']")
    ],
    "service_files_section": [
        (By.XPATH, "//h2[contains(text(), 'Service Files')]"),
        (By.CSS_SELECTOR, "h2:contains('Service Files')"),
        (By.CSS_SELECTOR, ".service-files")
    ],
    "status_closed": [
        (By.CSS_SELECTOR, "td.statusClosed"),
        (By.CSS_SELECTOR, ".statusClosed"),
        (By.CSS_SELECTOR, "td[class*='statusClosed']")
    ],
    "primary_worker": [
        (By.XPATH, "//td[contains(text(), 'Primary Worker')]/following-sibling::td"),
        (By.CSS_SELECTOR, "td:contains('Primary Worker') + td"),
        (By.CSS_SELECTOR, ".primary-worker")
    ],
    "workflow_side_panel": [
        (By.ID, "taskHandle"),
        (By.CSS_SELECTOR, "[id*='taskHandle']"),
        (By.CSS_SELECTOR, ".workflow-handle")
    ]
}

@dataclass
class ExtractedData:
    case_name: str
    case_id: str
    primary_workers: List[str]
    service_file_status: str
    extraction_date: str
    client_dob: str = ""  # Date of birth from Members section

@dataclass
class BotState:
    driver: Optional[webdriver.Chrome] = None
    chunks: List[Tuple[str, str]] = field(default_factory=list)
    next_chunk_index: int = 0
    stop_requested: bool = False
    extracted_data: List[ExtractedData] = field(default_factory=list)
    current_workflow_index: int = 0
    close_button_iframe_cache: Optional[int] = None  # Cache for iframe containing Close button

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.state = BotState()
        self.title("ISWS Remove Counselor Bot - Complete Workflow - Version 2.0.0, Last Updated 12/02/2025")
        self.geometry("1000x500")
        # Settings (output directory persistence)
        self.settings_path = os.path.join(os.path.dirname(__file__), "isws_remove_counselor_settings.json")
        self.settings = self._load_settings()
        self.output_dir_var = tk.StringVar(value=self.settings.get("output_dir", r"C:\\Users\\mthompson\\OneDrive - Integrity Senior Services\\Desktop"))
        
        # User management
        self.users_file = Path(__file__).parent / "remove_counselor_users.json"
        self.users = {
            'penelope': {},  # {"name": {"username": "...", "password": "..."}}
            'therapy_notes': {},  # {"name": {"username": "...", "password": "...", "url": "..."}}
            'ips': {}  # {"name": {"username": "...", "password": "...", "url": "..."}}
        }
        self.load_users()
        
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        # Style for larger buttons
        style = ttk.Style(self)
        style.configure("Big.TButton", padding=8, font=("Segoe UI", 10))
        style.configure("H.TLabel", font=("Segoe UI", 14, "bold"), foreground="white", background="#660000")
        style.configure("Stop.TButton", padding=8, font=("Segoe UI", 10), foreground="white", background="red")
        style.configure("Success.TButton", padding=8, font=("Segoe UI", 10), foreground="white", background="green")

        header = tk.Frame(self, bg="#660000")
        header.pack(fill="x")
        tk.Label(header, text="ISWS Remove Counselor Bot - Complete Workflow", bg="#660000", fg="white",
                 font=("Segoe UI", 14, "bold"), pady=6).pack(side="left", padx=12)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Create tabs
        self._build_extractor_tab()
        self._build_uploader_tab()
        self._build_ips_uploader_tab()

    def _build_extractor_tab(self):
        """Build the Extractor tab (current functionality)"""
        # Create extractor tab
        self.extractor_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.extractor_frame, text="📊 Extractor")
        
        # Header for extractor
        extractor_header = tk.Frame(self.extractor_frame, bg="#660000")
        extractor_header.pack(fill="x")
        tk.Label(extractor_header, text="Extractor Bot - First Part of Workflow", bg="#660000", fg="white",
                 font=("Segoe UI", 14, "bold"), pady=6).pack(side="left", padx=12)
        
        # Extractor content with scrollable frame
        # Create a canvas and scrollbar for scrolling
        canvas = tk.Canvas(self.extractor_frame)
        scrollbar = ttk.Scrollbar(self.extractor_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        content_frame = scrollable_frame
        
        # Add padding to the scrollable content
        main_content = tk.Frame(content_frame)
        main_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Penelope Login Section
        login_frame = tk.LabelFrame(main_content, text="Penelope Login", font=("Segoe UI", 12, "bold"))
        login_frame.pack(fill="x", pady=(0, 20))
        
        # User Selection Row
        user_row = tk.Frame(login_frame)
        user_row.pack(fill="x", padx=10, pady=(10, 5))
        
        tk.Label(user_row, text="Saved User:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))
        
        # User Selection Dropdown
        self.penelope_user_dropdown = ttk.Combobox(user_row, font=("Segoe UI", 10), width=25, state="readonly")
        self.penelope_user_dropdown.pack(side="left", padx=(0, 10))
        self.penelope_user_dropdown.bind("<<ComboboxSelected>>", lambda e: self._on_user_selected('penelope'))
        self._update_user_dropdown('penelope')
        
        # Add User button
        self.penelope_add_user_button = tk.Button(user_row, text="Add User", 
                                                   command=lambda: self._add_user('penelope'),
                                                   bg="#800000", fg="white", font=("Segoe UI", 9),
                                                   padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        self.penelope_add_user_button.pack(side="left", padx=(0, 5))
        
        # Update User button
        self.penelope_update_user_button = tk.Button(user_row, text="Update User", 
                                                     command=lambda: self._update_credentials('penelope'),
                                                     bg="#666666", fg="white", font=("Segoe UI", 9),
                                                     padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        self.penelope_update_user_button.pack(side="left", padx=(0, 5))
        
        # Login credentials
        cred_frame = tk.Frame(login_frame)
        cred_frame.pack(fill="x", padx=10, pady=10)
        
        # Username
        tk.Label(cred_frame, text="Username:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.e_user = ttk.Entry(cred_frame, width=30)
        self.e_user.grid(row=0, column=1, padx=(0, 20))
        
        # Password
        tk.Label(cred_frame, text="Password:").grid(row=0, column=2, sticky="w", padx=(0, 10))
        self.e_pass = ttk.Entry(cred_frame, width=30, show="•")
        self.e_pass.grid(row=0, column=3, padx=(0, 20))
        
        # Login button
        ttk.Button(cred_frame, text="Run / Login", style="Big.TButton",
                  command=self._login).grid(row=0, column=4)
        
        # Debug checkbox and STOP button
        control_frame = tk.Frame(login_frame)
        control_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.debug_var = tk.BooleanVar()
        tk.Checkbutton(control_frame, text="🐛 Debug Mode", variable=self.debug_var, 
                      font=("Segoe UI", 10)).pack(side="left", padx=(0, 20))
        
        ttk.Button(control_frame, text="🛑 STOP BOT", style="Stop.TButton",
                  command=self._stop_bot).pack(side="left")
        
        # Workflow Configuration
        config_frame = tk.LabelFrame(main_content, text="Workflow Configuration", font=("Segoe UI", 12, "bold"))
        config_frame.pack(fill="x", pady=(0, 20))
        
        # Match title
        match_frame = tk.Frame(config_frame)
        match_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(match_frame, text="Workflow Title to Match:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))
        self.e_match = ttk.Entry(match_frame, width=60, font=("Segoe UI", 10))
        self.e_match.insert(0, "Remove Counselor from Client in TN")
        self.e_match.pack(side="left", fill="x", expand=True)
        
        # Test Configuration
        test_frame = tk.LabelFrame(main_content, text="Test Configuration", font=("Segoe UI", 12, "bold"))
        test_frame.pack(fill="x", pady=(0, 20))
        
        test_content = tk.Frame(test_frame)
        test_content.pack(fill="x", padx=10, pady=10)
        
        # Max workflows for testing
        tk.Label(test_content, text="Max Workflows (for testing):", font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))
        self.e_max_workflows = ttk.Entry(test_content, width=10, font=("Segoe UI", 10))
        self.e_max_workflows.insert(0, "5")  # Default to 5 for testing
        self.e_max_workflows.pack(side="left", padx=(0, 20))
        
        # Test button
        ttk.Button(test_content, text="🧪 Test Run (Limited)", style="Big.TButton",
                   command=self._test_run_limited).pack(side="left", padx=(0, 20))
        
        # Info label
        tk.Label(test_content, text="(Leave empty or 0 for unlimited)", 
                font=("Segoe UI", 9), fg="gray").pack(side="left")
        
        # Control sections
        controls_frame = tk.LabelFrame(main_content, text="Bot Controls", font=("Segoe UI", 12, "bold"))
        controls_frame.pack(fill="x", pady=(0, 20))
        
        # Create a grid layout for buttons
        button_grid = tk.Frame(controls_frame)
        button_grid.pack(fill="x", padx=10, pady=10)
        
        # Setup section
        setup_frame = tk.LabelFrame(button_grid, text="Setup", font=("Segoe UI", 10, "bold"))
        setup_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        ttk.Button(setup_frame, text="Open Workflow Drawer", style="Big.TButton",
                   command=self._open_workflow).pack(fill="x", padx=8, pady=4)
        ttk.Button(setup_frame, text="Expand Current (safe)", style="Big.TButton",
                   command=self._expand_current_safe).pack(fill="x", padx=8, pady=4)
        ttk.Button(setup_frame, text="Open Advanced Search", style="Big.TButton",
                   command=self._open_advanced).pack(fill="x", padx=8, pady=4)

        # Queue Actions section
        queue_frame = tk.LabelFrame(button_grid, text="Queue Actions", font=("Segoe UI", 10, "bold"))
        queue_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        ttk.Button(queue_frame, text="Dry Run: List Matches", style="Big.TButton",
                   command=self._queue_dry_run).pack(fill="x", padx=8, pady=4)
        ttk.Button(queue_frame, text="Expand Queue", style="Big.TButton",
                   command=self._expand_queue).pack(fill="x", padx=8, pady=4)

        # Advanced Search section
        search_frame = tk.LabelFrame(button_grid, text="Advanced Search", font=("Segoe UI", 10, "bold"))
        search_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        ttk.Button(search_frame, text="Fill Next Chunk", style="Big.TButton",
                   command=self._fill_next_chunk).pack(fill="x", padx=8, pady=4)
        ttk.Button(search_frame, text="Search & Process All", style="Big.TButton",
                   command=self._search_and_process_all).pack(fill="x", padx=8, pady=4)
        ttk.Button(search_frame, text="Search and Pickup All", style="Big.TButton",
                   command=self._search_and_pickup_all).pack(fill="x", padx=8, pady=4)

        # Data Management section
        data_frame = tk.LabelFrame(button_grid, text="Data Management", font=("Segoe UI", 10, "bold"))
        data_frame.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")
        ttk.Button(data_frame, text="Export CSV", style="Success.TButton",
                   command=self._export_csv).pack(fill="x", padx=8, pady=4)
        ttk.Button(data_frame, text="Clear Data", style="Big.TButton",
                   command=self._clear_data).pack(fill="x", padx=8, pady=4)

        # Output Location section
        output_frame = tk.LabelFrame(main_content, text="Output Location", font=("Segoe UI", 12, "bold"))
        output_frame.pack(fill="x", pady=(0, 20))
        of_content = tk.Frame(output_frame)
        of_content.pack(fill="x", padx=10, pady=10)
        tk.Label(of_content, text="Folder:").pack(side="left", padx=(0, 10))
        self.e_output_dir = ttk.Entry(of_content, width=70)
        self.e_output_dir.pack(side="left", fill="x", expand=True)
        self.e_output_dir.insert(0, self.output_dir_var.get())
        ttk.Button(of_content, text="Browse…", command=self._browse_output_dir).pack(side="left", padx=(10, 0))
        ttk.Button(of_content, text="Save", command=self._save_output_dir).pack(side="left", padx=(10, 0))

        # Configure grid weights
        button_grid.columnconfigure(0, weight=1)
        button_grid.columnconfigure(1, weight=1)
        button_grid.columnconfigure(2, weight=1)
        button_grid.columnconfigure(3, weight=1)
        
        # Status section
        status_frame = tk.LabelFrame(main_content, text="Extractor Status", font=("Segoe UI", 12, "bold"))
        status_frame.pack(fill="x", pady=(0, 20))
        
        status_content = tk.Frame(status_frame)
        status_content.pack(fill="x", padx=10, pady=10)
        
        self.status_label = tk.Label(status_content, text="Ready", font=("Segoe UI", 10))
        self.status_label.pack(side="left", padx=(0, 20))
        
        self.data_count_label = tk.Label(status_content, text="Data: 0 records", font=("Segoe UI", 9))
        self.data_count_label.pack(side="left")

        # Log area
        log_frame = tk.LabelFrame(main_content, text="Extractor Log", font=("Segoe UI", 12, "bold"))
        log_frame.pack(fill="both", expand=True, pady=(0, 0))
        
        # Create a frame for the log with better visibility
        log_content_frame = tk.Frame(log_frame)
        log_content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.log = tk.Text(log_content_frame, height=15, wrap="word", 
                          font=("Consolas", 9), bg="white", fg="black")
        self.log.pack(side="left", fill="both", expand=True)
        
        log_sb = ttk.Scrollbar(log_content_frame, command=self.log.yview)
        log_sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=log_sb.set)

    # ---------- Settings / Output helpers ----------
    def _load_settings(self):
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"output_dir": r"C:\\Users\\mthompson\\OneDrive - Integrity Senior Services\\Desktop"}

    def _save_settings(self):
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            try:
                self.log_msg(f"[WARN] Could not save settings: {e}")
            except Exception:
                pass
    
    def load_users(self):
        """Load users from JSON file"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r') as f:
                    loaded = json.load(f)
                    # Ensure all three categories exist
                    self.users = {
                        'penelope': loaded.get('penelope', {}),
                        'therapy_notes': loaded.get('therapy_notes', {}),
                        'ips': loaded.get('ips', {})
                    }
            else:
                # Create empty users file if it doesn't exist
                self.save_users()
        except Exception as e:
            # Log will be created later in _build_ui
            self.users = {
                'penelope': {},
                'therapy_notes': {},
                'ips': {}
            }
    
    def save_users(self):
        """Save users to JSON file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save users:\n{e}")
            return False
    
    def _update_user_dropdown(self, service_type):
        """Update the user dropdown with current users for a specific service"""
        dropdown_map = {
            'penelope': 'penelope_user_dropdown',
            'therapy_notes': 'tn_user_dropdown',
            'ips': 'ips_user_dropdown'
        }
        dropdown_name = dropdown_map.get(service_type)
        if dropdown_name and hasattr(self, dropdown_name):
            dropdown = getattr(self, dropdown_name)
            user_names = sorted(self.users[service_type].keys())
            if user_names:
                dropdown['values'] = user_names
            else:
                dropdown['values'] = []
    
    def _on_user_selected(self, service_type):
        """Handle user selection from dropdown"""
        dropdown_map = {
            'penelope': ('penelope_user_dropdown', 'e_user', 'e_pass', None),
            'therapy_notes': ('tn_user_dropdown', 'tn_user', 'tn_pass', 'tn_url'),
            'ips': ('ips_user_dropdown', 'ips_user', 'ips_pass', 'ips_url')
        }
        
        dropdown_name, user_entry, pass_entry, url_entry = dropdown_map.get(service_type, (None, None, None, None))
        
        if not dropdown_name or not hasattr(self, dropdown_name):
            return
        
        dropdown = getattr(self, dropdown_name)
        selected_user = dropdown.get()
        
        if selected_user and selected_user in self.users[service_type]:
            user_data = self.users[service_type][selected_user]
            
            # Update username and password
            if hasattr(self, user_entry):
                entry = getattr(self, user_entry)
                entry.delete(0, tk.END)
                entry.insert(0, user_data.get('username', ''))
            
            if hasattr(self, pass_entry):
                entry = getattr(self, pass_entry)
                entry.delete(0, tk.END)
                entry.insert(0, user_data.get('password', ''))
            
            # Update URL if applicable
            if url_entry and hasattr(self, url_entry):
                entry = getattr(self, url_entry)
                entry.delete(0, tk.END)
                default_url = {
                    'therapy_notes': "https://www.therapynotes.com/app/login/IntegritySWS/",
                    'ips': "https://www.therapynotes.com/app/login/IntegrityIPS/?r=%2fapp%2fpatients%2f"
                }.get(service_type, '')
                entry.insert(0, user_data.get('url', default_url))
            
            # Log message
            log_method = self.log_msg if service_type == 'penelope' else self.uploader_log_msg
            if hasattr(self, 'log') or hasattr(self, 'uploader_log'):
                log_method(f"Loaded credentials for user: {selected_user}")
    
    def _add_user(self, service_type):
        """Add a new user to saved users for a specific service"""
        service_names = {
            'penelope': 'Penelope',
            'therapy_notes': 'Therapy Notes',
            'ips': 'IPS Therapy Notes'
        }
        service_name = service_names.get(service_type, 'Service')
        
        dialog = tk.Toplevel(self)
        dialog.title(f"Add New User - {service_name}")
        dialog.geometry("450x320" if service_type != 'penelope' else "450x280")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="User Name:", font=("Segoe UI", 10), bg="#f0f0f0").pack(pady=(20, 5))
        name_entry = tk.Entry(dialog, font=("Segoe UI", 10), width=35)
        name_entry.pack(pady=(0, 10))
        name_entry.focus()
        
        tk.Label(dialog, text="Username:", font=("Segoe UI", 10), bg="#f0f0f0").pack(pady=(0, 5))
        username_entry = tk.Entry(dialog, font=("Segoe UI", 10), width=35)
        username_entry.pack(pady=(0, 10))
        
        tk.Label(dialog, text="Password:", font=("Segoe UI", 10), bg="#f0f0f0").pack(pady=(0, 5))
        password_entry = tk.Entry(dialog, font=("Segoe UI", 10), width=35, show="•")
        password_entry.pack(pady=(0, 10))
        
        url_entry = None
        if service_type != 'penelope':
            default_url = {
                'therapy_notes': "https://www.therapynotes.com/app/login/IntegritySWS/",
                'ips': "https://www.therapynotes.com/app/login/IntegrityIPS/?r=%2fapp%2fpatients%2f"
            }.get(service_type, '')
            
            tk.Label(dialog, text=f"{service_name} URL (optional):", font=("Segoe UI", 10), bg="#f0f0f0").pack(pady=(0, 5))
            url_entry = tk.Entry(dialog, font=("Segoe UI", 10), width=35)
            url_entry.insert(0, default_url)
            url_entry.pack(pady=(0, 15))
        
        def save_user():
            name = name_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            url = url_entry.get().strip() if url_entry else None
            
            if not name or not username or not password:
                messagebox.showwarning("Invalid Input", "User Name, Username, and Password are required")
                return
            
            if service_type == 'penelope':
                user_data = {
                    'username': username,
                    'password': password
                }
            else:
                default_url = {
                    'therapy_notes': "https://www.therapynotes.com/app/login/IntegritySWS/",
                    'ips': "https://www.therapynotes.com/app/login/IntegrityIPS/?r=%2fapp%2fpatients%2f"
                }.get(service_type, '')
                user_data = {
                    'username': username,
                    'password': password,
                    'url': url or default_url
                }
            
            if name in self.users[service_type]:
                if not messagebox.askyesno("User Exists", f"User '{name}' already exists. Overwrite?"):
                    return
            
            self.users[service_type][name] = user_data
            self.save_users()
            self._update_user_dropdown(service_type)
            
            # Log message
            log_method = self.log_msg if service_type == 'penelope' else self.uploader_log_msg
            if hasattr(self, 'log') or hasattr(self, 'uploader_log'):
                log_method(f"Added user: {name}")
            
            dialog.destroy()
            messagebox.showinfo("Success", f"User '{name}' added successfully")
        
        button_frame = tk.Frame(dialog, bg="#f0f0f0")
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Save", command=save_user,
                  bg="#800000", fg="white", font=("Segoe UI", 10),
                  padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                  bg="#666666", fg="white", font=("Segoe UI", 10),
                  padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        
        # Bind Enter key to save
        name_entry.bind("<Return>", lambda e: username_entry.focus())
        username_entry.bind("<Return>", lambda e: password_entry.focus())
        if url_entry:
            password_entry.bind("<Return>", lambda e: url_entry.focus())
            url_entry.bind("<Return>", lambda e: save_user())
        else:
            password_entry.bind("<Return>", lambda e: save_user())
    
    def _update_credentials(self, service_type):
        """Update credentials for selected user"""
        dropdown_map = {
            'penelope': ('penelope_user_dropdown', 'e_user', 'e_pass', None),
            'therapy_notes': ('tn_user_dropdown', 'tn_user', 'tn_pass', 'tn_url'),
            'ips': ('ips_user_dropdown', 'ips_user', 'ips_pass', 'ips_url')
        }
        
        dropdown_name, user_entry, pass_entry, url_entry = dropdown_map.get(service_type, (None, None, None, None))
        
        if not dropdown_name or not hasattr(self, dropdown_name):
            return
        
        dropdown = getattr(self, dropdown_name)
        selected_user = dropdown.get()
        
        if not selected_user or selected_user not in self.users[service_type]:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown")
            return
        
        username = getattr(self, user_entry).get().strip() if hasattr(self, user_entry) else ''
        password = getattr(self, pass_entry).get().strip() if hasattr(self, pass_entry) else ''
        
        if not username or not password:
            messagebox.showwarning("Invalid Input", "Username and password are required")
            return
        
        if service_type == 'penelope':
            user_data = {
                'username': username,
                'password': password
            }
        else:
            default_url = {
                'therapy_notes': "https://www.therapynotes.com/app/login/IntegritySWS/",
                'ips': "https://www.therapynotes.com/app/login/IntegrityIPS/?r=%2fapp%2fpatients%2f"
            }.get(service_type, '')
            url = getattr(self, url_entry).get().strip() if url_entry and hasattr(self, url_entry) else default_url
            user_data = {
                'username': username,
                'password': password,
                'url': url or default_url
            }
        
        self.users[service_type][selected_user] = user_data
        self.save_users()
        
        # Log message
        log_method = self.log_msg if service_type == 'penelope' else self.uploader_log_msg
        if hasattr(self, 'log') or hasattr(self, 'uploader_log'):
            log_method(f"Updated credentials for user: {selected_user}")
        
        messagebox.showinfo("Success", f"Credentials updated for '{selected_user}'")

    def _browse_output_dir(self):
        try:
            d = filedialog.askdirectory(initialdir=self.e_output_dir.get() or self.output_dir_var.get())
            if d:
                self.e_output_dir.delete(0, tk.END)
                self.e_output_dir.insert(0, d)
        except Exception as e:
            self.log_msg(f"[WARN] Folder browse failed: {e}")

    def _save_output_dir(self):
        try:
            val = (self.e_output_dir.get() or '').strip()
            if not val:
                return
            try:
                os.makedirs(val, exist_ok=True)
            except Exception as e:
                self.log_msg(f"[WARN] Could not create folder '{val}': {e}")
                return
            self.output_dir_var.set(val)
            self.settings["output_dir"] = val
            self._save_settings()
            self.log_msg(f"[AUTO-EXPORT] Output folder set to: {val}")
        except Exception as e:
            self.log_msg(f"[WARN] Save output folder failed: {e}")

    def _get_export_dir(self):
        # First check the entry field (current UI value) - this is what the user sees and selects
        val = (self.e_output_dir.get() or '').strip()
        # If entry field is empty, check the saved variable
        if not val:
            val = (self.output_dir_var.get() or '').strip()
        # If still empty, fall back to default desktop path
        if not val:
            val = r"C:\\Users\\mthompson\\OneDrive - Integrity Senior Services\\Desktop"
        try:
            os.makedirs(val, exist_ok=True)
        except Exception:
            # Fallback to user's Desktop
            val = os.path.join(os.path.expanduser("~"), "Desktop")
            try:
                os.makedirs(val, exist_ok=True)
            except Exception:
                pass
        return val

    def _build_uploader_tab(self):
        """Build the Uploader tab (new functionality)"""
        # Create uploader tab
        self.uploader_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.uploader_frame, text="📤 Uploader")
        
        # Header for uploader
        uploader_header = tk.Frame(self.uploader_frame, bg="#660000")
        uploader_header.pack(fill="x")
        tk.Label(uploader_header, text="Uploader Bot - Second Part of Workflow", bg="#660000", fg="white",
                 font=("Segoe UI", 14, "bold"), pady=6).pack(side="left", padx=12)
        
        # Uploader content with scrollable frame
        # Create a canvas and scrollbar for scrolling
        canvas = tk.Canvas(self.uploader_frame)
        scrollbar = ttk.Scrollbar(self.uploader_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        content_frame = scrollable_frame
        
        # Add padding to the scrollable content
        main_content = tk.Frame(content_frame)
        main_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Therapy Notes Login Section
        login_frame = tk.LabelFrame(main_content, text="Therapy Notes Login", font=("Segoe UI", 12, "bold"))
        login_frame.pack(fill="x", pady=(0, 20))
        
        # User Selection Row
        user_row = tk.Frame(login_frame)
        user_row.pack(fill="x", padx=10, pady=(10, 5))
        
        tk.Label(user_row, text="Saved User:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))
        
        # User Selection Dropdown
        self.tn_user_dropdown = ttk.Combobox(user_row, font=("Segoe UI", 10), width=25, state="readonly")
        self.tn_user_dropdown.pack(side="left", padx=(0, 10))
        self.tn_user_dropdown.bind("<<ComboboxSelected>>", lambda e: self._on_user_selected('therapy_notes'))
        self._update_user_dropdown('therapy_notes')
        
        # Add User button
        self.tn_add_user_button = tk.Button(user_row, text="Add User", 
                                             command=lambda: self._add_user('therapy_notes'),
                                             bg="#800000", fg="white", font=("Segoe UI", 9),
                                             padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        self.tn_add_user_button.pack(side="left", padx=(0, 5))
        
        # Update User button
        self.tn_update_user_button = tk.Button(user_row, text="Update User", 
                                                command=lambda: self._update_credentials('therapy_notes'),
                                                bg="#666666", fg="white", font=("Segoe UI", 9),
                                                padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        self.tn_update_user_button.pack(side="left", padx=(0, 5))
        
        # Login credentials
        cred_frame = tk.Frame(login_frame)
        cred_frame.pack(fill="x", padx=10, pady=10)
        
        # Username
        tk.Label(cred_frame, text="Therapy Notes Username:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.tn_user = ttk.Entry(cred_frame, width=30)
        self.tn_user.grid(row=0, column=1, padx=(0, 20))
        
        # Password
        tk.Label(cred_frame, text="Therapy Notes Password:").grid(row=0, column=2, sticky="w", padx=(0, 10))
        self.tn_pass = ttk.Entry(cred_frame, width=30, show="•")
        self.tn_pass.grid(row=0, column=3, padx=(0, 20))
        
        # Login button
        ttk.Button(cred_frame, text="Login to Therapy Notes", style="Big.TButton",
                  command=self._login_therapy_notes).grid(row=0, column=4)
        
        # Therapy Notes URL configuration
        url_frame = tk.Frame(login_frame)
        url_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        tk.Label(url_frame, text="Therapy Notes URL:", font=("Segoe UI", 10)).grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.tn_url = ttk.Entry(url_frame, width=70, font=("Segoe UI", 9))
        self.tn_url.insert(0, "https://www.therapynotes.com/app/login/IntegritySWS/")
        self.tn_url.grid(row=0, column=1, padx=(0, 20), sticky="ew")
        
        # Configure grid weights for URL field
        url_frame.columnconfigure(1, weight=1)
        
        # Instructions
        instructions = tk.LabelFrame(main_content, text="Uploader Bot Instructions", font=("Segoe UI", 12, "bold"))
        instructions.pack(fill="x", pady=(0, 20))
        
        instruction_text = """
This is the Uploader bot that will handle the second part of the workflow.

The Uploader will:
• Login to Therapy Notes with separate credentials
• Read the CSV file generated by the Extractor
• Navigate to each client in Therapy Notes
• Remove the specified counselors from each client's profile
• Log all actions and results

To get started:
1. First run the Extractor bot to generate the CSV file
2. Enter your Therapy Notes credentials above
3. Select the CSV file to process (automatically validates the file)
4. Click 'Login to Therapy Notes' - this will automatically start the upload process!
        """
        
        tk.Label(instructions, text=instruction_text, justify="left", 
                font=("Segoe UI", 10), wraplength=800).pack(padx=10, pady=10)
        
        # Auto-run IPS Uploader section - PROMINENT at top
        ips_section = tk.LabelFrame(main_content, text="🏥 IPS Uploader Integration", 
                                    font=("Segoe UI", 12, "bold"), 
                                    foreground="#660000", 
                                    relief="ridge", 
                                    borderwidth=3)
        ips_section.pack(fill="x", pady=(0, 20), padx=10)
        
        # IPS checkbox with prominent styling
        ips_inner_frame = tk.Frame(ips_section, bg="#fff5f5", relief="flat")
        ips_inner_frame.pack(fill="x", padx=15, pady=15)
        
        self.auto_run_ips_uploader = tk.BooleanVar(value=False)
        ips_checkbox = ttk.Checkbutton(
            ips_inner_frame,
            text="✓ Auto-run IPS Uploader after Base Uploader completes",
            variable=self.auto_run_ips_uploader,
            style="Large.TCheckbutton"
        )
        ips_checkbox.pack(anchor="w", pady=(0, 8))
        
        # Description
        ips_desc = tk.Label(
            ips_inner_frame,
            text="When enabled, the IPS Uploader will automatically start after the Base Uploader finishes.\n"
                 "It will use the same TherapyNotes credentials and CSV file.",
            font=("Segoe UI", 9, "italic"),
            justify="left",
            foreground="#555555",
            bg="#fff5f5"
        )
        ips_desc.pack(anchor="w")
        
        # Uploader controls
        controls_frame = tk.LabelFrame(main_content, text="Uploader Controls", font=("Segoe UI", 12, "bold"))
        controls_frame.pack(fill="x", pady=(0, 20))
        
        # CSV file selection
        csv_frame = tk.Frame(controls_frame)
        csv_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(csv_frame, text="CSV File:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.csv_file_var = tk.StringVar()
        self.csv_file_entry = ttk.Entry(csv_frame, textvariable=self.csv_file_var, width=60)
        self.csv_file_entry.pack(side="left", padx=(10, 5), fill="x", expand=True)
        ttk.Button(csv_frame, text="Browse", command=self._browse_csv_file).pack(side="right")
        
        # Output location selection
        output_frame = tk.Frame(controls_frame)
        output_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(output_frame, text="Output Location:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.output_location_var = tk.StringVar()
        self.output_location_entry = ttk.Entry(output_frame, textvariable=self.output_location_var, width=60)
        self.output_location_entry.pack(side="left", padx=(10, 5), fill="x", expand=True)
        ttk.Button(output_frame, text="Browse", command=self._browse_output_location).pack(side="right")
        tk.Label(output_frame, text="(Leave empty to use CSV file directory)", 
                font=("Segoe UI", 8), fg="gray").pack(side="left", padx=(5, 0))
        
        # Debug mode toggle
        debug_frame = tk.Frame(controls_frame)
        debug_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.debug_mode_var = tk.BooleanVar()
        debug_checkbox = ttk.Checkbutton(debug_frame, text="🐛 Debug Mode (Show detailed logs)", 
                                       variable=self.debug_mode_var)
        debug_checkbox.pack(side="left")
        
        # Uploader buttons
        button_frame = tk.Frame(controls_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="📊 View Upload Log", style="Big.TButton",
                  command=self._view_upload_log).pack(side="left")
        
        # Uploader status
        status_frame = tk.LabelFrame(main_content, text="Uploader Status", font=("Segoe UI", 12, "bold"))
        status_frame.pack(fill="x")
        
        self.uploader_status_label = tk.Label(status_frame, text="Ready to upload", font=("Segoe UI", 10))
        self.uploader_status_label.pack(padx=10, pady=10)
        
        # Uploader log area - make it more visible like extractor
        log_frame = tk.LabelFrame(main_content, text="Uploader Log", font=("Segoe UI", 12, "bold"))
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        # Create a frame for the log with better visibility
        log_content_frame = tk.Frame(log_frame)
        log_content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.uploader_log = tk.Text(log_content_frame, height=15, wrap="word", 
                                  font=("Consolas", 9), bg="white", fg="black")
        self.uploader_log.pack(side="left", fill="both", expand=True)
        
        uploader_sb = ttk.Scrollbar(log_content_frame, command=self.uploader_log.yview)
        uploader_sb.pack(side="right", fill="y")
        self.uploader_log.configure(yscrollcommand=uploader_sb.set)

    def _build_ips_uploader_tab(self):
        """Build the IPS Uploader tab (new functionality for IPS agency)"""
        # Create IPS uploader tab
        self.ips_uploader_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ips_uploader_frame, text="🏥 IPS Uploader")
        
        # Header for IPS uploader
        ips_header = tk.Frame(self.ips_uploader_frame, bg="#660000")
        ips_header.pack(fill="x")
        tk.Label(ips_header, text="IPS Uploader Bot - For IPS Agency Counselors Only", bg="#660000", fg="white",
                 font=("Segoe UI", 14, "bold"), pady=6).pack(side="left", padx=12)
        
        # IPS Uploader content with scrollable frame
        # Create a canvas and scrollbar for scrolling
        canvas = tk.Canvas(self.ips_uploader_frame)
        scrollbar = ttk.Scrollbar(self.ips_uploader_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        content_frame = scrollable_frame
        
        # Add padding to the scrollable content
        main_content = tk.Frame(content_frame)
        main_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # IPS Therapy Notes Login Section
        login_frame = tk.LabelFrame(main_content, text="IPS Therapy Notes Login", font=("Segoe UI", 12, "bold"))
        login_frame.pack(fill="x", pady=(0, 20))
        
        # User Selection Row
        user_row = tk.Frame(login_frame)
        user_row.pack(fill="x", padx=10, pady=(10, 5))
        
        tk.Label(user_row, text="Saved User:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))
        
        # User Selection Dropdown
        self.ips_user_dropdown = ttk.Combobox(user_row, font=("Segoe UI", 10), width=25, state="readonly")
        self.ips_user_dropdown.pack(side="left", padx=(0, 10))
        self.ips_user_dropdown.bind("<<ComboboxSelected>>", lambda e: self._on_user_selected('ips'))
        self._update_user_dropdown('ips')
        
        # Add User button
        self.ips_add_user_button = tk.Button(user_row, text="Add User", 
                                             command=lambda: self._add_user('ips'),
                                             bg="#800000", fg="white", font=("Segoe UI", 9),
                                             padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        self.ips_add_user_button.pack(side="left", padx=(0, 5))
        
        # Update User button
        self.ips_update_user_button = tk.Button(user_row, text="Update User", 
                                                command=lambda: self._update_credentials('ips'),
                                                bg="#666666", fg="white", font=("Segoe UI", 9),
                                                padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        self.ips_update_user_button.pack(side="left", padx=(0, 5))
        
        # Login credentials
        cred_frame = tk.Frame(login_frame)
        cred_frame.pack(fill="x", padx=10, pady=10)
        
        # Username
        tk.Label(cred_frame, text="IPS Username:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.ips_user = ttk.Entry(cred_frame, width=30)
        self.ips_user.grid(row=0, column=1, padx=(0, 20))
        
        # Password
        tk.Label(cred_frame, text="IPS Password:").grid(row=0, column=2, sticky="w", padx=(0, 10))
        self.ips_pass = ttk.Entry(cred_frame, width=30, show="•")
        self.ips_pass.grid(row=0, column=3, padx=(0, 20))
        
        # Login button
        ttk.Button(cred_frame, text="Login to IPS Therapy Notes", style="Big.TButton",
                  command=self._login_ips_therapy_notes).grid(row=0, column=4)
        
        # IPS Therapy Notes URL configuration
        url_frame = tk.Frame(login_frame)
        url_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        tk.Label(url_frame, text="IPS Therapy Notes URL:", font=("Segoe UI", 10)).grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.ips_url = ttk.Entry(url_frame, width=70, font=("Segoe UI", 9))
        self.ips_url.insert(0, "https://www.therapynotes.com/app/login/IntegrityIPS/?r=%2fapp%2fpatients%2f")
        self.ips_url.grid(row=0, column=1, padx=(0, 20), sticky="ew")
        
        # Configure grid weights for URL field
        url_frame.columnconfigure(1, weight=1)
        
        # Instructions
        instructions = tk.LabelFrame(main_content, text="IPS Uploader Bot Instructions", font=("Segoe UI", 12, "bold"))
        instructions.pack(fill="x", pady=(0, 20))
        
        instruction_text = """
This is the IPS Uploader bot that handles counselors belonging to the IPS agency.

The IPS Uploader will:
• Login to IPS Therapy Notes with separate credentials
• Read the CSV file generated by the Extractor
• Navigate to each client in IPS Therapy Notes
• Remove ONLY counselors with "- IPS" after their names
• Leave all other counselors untouched (they belong to main agency)

IMPORTANT: This bot ONLY removes counselors with "- IPS" suffix!
All other counselors will be left alone.

To get started:
1. First run the Extractor bot to generate the CSV file
2. Enter your IPS Therapy Notes credentials above
3. Select the CSV file to process (automatically validates the file)
4. Click 'Login to IPS Therapy Notes' - this will automatically start the IPS upload process!
        """
        
        tk.Label(instructions, text=instruction_text, justify="left", 
                font=("Segoe UI", 10), wraplength=800).pack(padx=10, pady=10)
        
        # IPS Uploader controls
        controls_frame = tk.LabelFrame(main_content, text="IPS Uploader Controls", font=("Segoe UI", 12, "bold"))
        controls_frame.pack(fill="x", pady=(0, 20))
        
        # CSV file selection
        csv_frame = tk.Frame(controls_frame)
        csv_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(csv_frame, text="CSV File:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.ips_csv_file_var = tk.StringVar()
        self.ips_csv_file_entry = ttk.Entry(csv_frame, textvariable=self.ips_csv_file_var, width=60)
        self.ips_csv_file_entry.pack(side="left", padx=(10, 5), fill="x", expand=True)
        ttk.Button(csv_frame, text="Browse", command=self._browse_ips_csv_file).pack(side="right")
        
        # Output location selection
        output_frame = tk.Frame(controls_frame)
        output_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(output_frame, text="Output Location:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.ips_output_location_var = tk.StringVar()
        self.ips_output_location_entry = ttk.Entry(output_frame, textvariable=self.ips_output_location_var, width=60)
        self.ips_output_location_entry.pack(side="left", padx=(10, 5), fill="x", expand=True)
        ttk.Button(output_frame, text="Browse", command=self._browse_ips_output_location).pack(side="right")
        tk.Label(output_frame, text="(Leave empty to use CSV file directory)", 
                font=("Segoe UI", 8), fg="gray").pack(side="left", padx=(5, 0))
        
        # Debug mode toggle
        debug_frame = tk.Frame(controls_frame)
        debug_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.ips_debug_mode_var = tk.BooleanVar()
        debug_checkbox = ttk.Checkbutton(debug_frame, text="🐛 Debug Mode (Show detailed logs)", 
                                       variable=self.ips_debug_mode_var)
        debug_checkbox.pack(side="left")
        
        # IPS Uploader buttons
        button_frame = tk.Frame(controls_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text="📊 View IPS Upload Log", style="Big.TButton",
                  command=self._view_ips_upload_log).pack(side="left")
        
        # IPS Uploader status
        status_frame = tk.LabelFrame(main_content, text="IPS Uploader Status", font=("Segoe UI", 12, "bold"))
        status_frame.pack(fill="x")
        
        self.ips_uploader_status_label = tk.Label(status_frame, text="Ready to upload IPS counselors", font=("Segoe UI", 10))
        self.ips_uploader_status_label.pack(padx=10, pady=10)
        
        # IPS Uploader log area - make it more visible like extractor
        log_frame = tk.LabelFrame(main_content, text="IPS Uploader Log", font=("Segoe UI", 12, "bold"))
        log_frame.pack(fill="both", expand=True, pady=(10, 0))
        
        # Create a frame for the log with better visibility
        log_content_frame = tk.Frame(log_frame)
        log_content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.ips_uploader_log = tk.Text(log_content_frame, height=15, wrap="word", 
                                  font=("Consolas", 9), bg="white", fg="black")
        self.ips_uploader_log.pack(side="left", fill="both", expand=True)
        
        ips_uploader_sb = ttk.Scrollbar(log_content_frame, command=self.ips_uploader_log.yview)
        ips_uploader_sb.pack(side="right", fill="y")
        self.ips_uploader_log.configure(yscrollcommand=ips_uploader_sb.set)

    # ---------- Uploader Methods ----------
    def _login_therapy_notes(self):
        """Login to Therapy Notes"""
        def run():
            try:
                username = self.tn_user.get().strip()
                password = self.tn_pass.get().strip()
                
                if not username or not password:
                    self.uploader_log_msg("❌ Please enter both username and password")
                    return
                
                self.uploader_log_msg("🔐 Logging into Therapy Notes...")
                
                # Initialize Therapy Notes driver
                if not hasattr(self, 'tn_driver') or self.tn_driver is None:
                    self.tn_driver = self._init_therapy_notes_driver()
                
                # Check if driver was successfully initialized
                if self.tn_driver is None:
                    self.uploader_log_msg("❌ Failed to initialize driver - cannot proceed with login")
                    return
                
                # Navigate to Therapy Notes using configurable URL
                tn_url = self.tn_url.get().strip()
                if not tn_url:
                    tn_url = "https://www.therapynotes.com/app/login/IntegritySWS/"
                
                self.uploader_log_msg(f"🌐 Navigating to: {tn_url}")
                
                # Navigate to the URL
                try:
                    self.tn_driver.get(tn_url)
                    time.sleep(2)  # Wait for page to load
                except Exception as nav_error:
                    self.uploader_log_msg(f"⚠️ Navigation error: {nav_error}")
                    # Check if driver is still valid
                    try:
                        # Try to get current URL to verify driver is still active
                        current_url = self.tn_driver.current_url
                        # If that works, try navigation again
                        time.sleep(1)
                        self.tn_driver.get(tn_url)
                        time.sleep(2)
                    except Exception as verify_error:
                        self.uploader_log_msg(f"❌ Driver session lost: {verify_error}")
                        # Reinitialize driver
                        self.tn_driver = self._init_therapy_notes_driver()
                        if self.tn_driver:
                            self.tn_driver.get(tn_url)
                            time.sleep(2)
                        else:
                            self.uploader_log_msg("❌ Failed to reinitialize driver - cannot proceed")
                            return
                
                # Debug: Log current page info
                current_url = self.tn_driver.current_url
                page_title = self.tn_driver.title
                self.uploader_log_msg(f"📍 Current URL: {current_url}")
                self.uploader_log_msg(f"📄 Page Title: {page_title}")
                
                # Debug: Check if we're on the right page
                if "login" not in current_url.lower():
                    self.uploader_log_msg("⚠️ Not on login page - may have been redirected or already logged in")
                    self.uploader_log_msg("🔄 Attempting to navigate to login URL again...")
                    
                    # Try navigating again
                    try:
                        self.tn_driver.get(tn_url)
                        time.sleep(3)
                        current_url = self.tn_driver.current_url
                        self.uploader_log_msg(f"📍 Current URL after retry: {current_url}")
                    except Exception as retry_error:
                        self.uploader_log_msg(f"⚠️ Retry navigation failed: {retry_error}")
                    
                    # If still not on login page, check if we're already logged in
                    if "login" not in current_url.lower():
                        self.uploader_log_msg("⚠️ Still not on login page - may already be logged in")
                        # Continue anyway - the bot will try to find login fields
                        # If logged in, it will fail and user can handle it
                
                # Find and fill username field - try multiple selectors with better error handling
                username_field = None
                username_selectors = [
                    (By.NAME, "Username"),
                    (By.ID, "Login__Username"),
                    (By.NAME, "username"),
                    (By.ID, "username"),
                    (By.CSS_SELECTOR, "input[type='text']"),
                    (By.CSS_SELECTOR, "input[placeholder*='username' i]"),
                    (By.CSS_SELECTOR, "input[placeholder*='user' i]"),
                    (By.XPATH, "//input[@type='text']"),
                    (By.XPATH, "//input[contains(@placeholder, 'username') or contains(@placeholder, 'user')]")
                ]
                
                for selector_type, selector_value in username_selectors:
                    try:
                        username_field = WebDriverWait(self.tn_driver, 2).until(
                            EC.presence_of_element_located((selector_type, selector_value))
                        )
                        self.uploader_log_msg(f"✅ Found username field with: {selector_type} = {selector_value}")
                        break
                    except:
                        continue
                
                if not username_field:
                    self.uploader_log_msg("❌ Could not find username field with any selector")
                    return
                
                username_field.clear()
                username_field.send_keys(username)
                self.uploader_log_msg("✅ Username entered")
                
                # Find and fill password field - try multiple selectors
                password_field = None
                password_selectors = [
                    (By.ID, "Login__Password"),
                    (By.NAME, "Password"),
                    (By.NAME, "password"),
                    (By.ID, "password"),
                    (By.CSS_SELECTOR, "input[type='password']"),
                    (By.XPATH, "//input[@type='password']")
                ]
                
                for selector_type, selector_value in password_selectors:
                    try:
                        password_field = WebDriverWait(self.tn_driver, 2).until(
                            EC.presence_of_element_located((selector_type, selector_value))
                        )
                        self.uploader_log_msg(f"✅ Found password field with: {selector_type} = {selector_value}")
                        break
                    except:
                        continue
                
                if not password_field:
                    self.uploader_log_msg("❌ Could not find password field with any selector")
                    return
                
                password_field.clear()
                password_field.send_keys(password)
                self.uploader_log_msg("✅ Password entered")
                
                # Find and click login button - try multiple selectors
                login_button = None
                try:
                    login_button = self.tn_driver.find_element(By.XPATH, "//button[@type='submit']")
                except:
                    try:
                        login_button = self.tn_driver.find_element(By.XPATH, "//input[@type='submit']")
                    except:
                        login_button = self.tn_driver.find_element(By.XPATH, "//button[contains(text(), 'Login')] | //button[contains(text(), 'Sign In')]")
                
                login_button.click()
                self.uploader_log_msg("✅ Login button clicked")
                
                time.sleep(3)  # Wait for login to complete
                
                # Check if login was successful
                current_url = self.tn_driver.current_url
                page_title = self.tn_driver.title
                self.uploader_log_msg(f"🔍 Post-login URL: {current_url}")
                self.uploader_log_msg(f"🔍 Post-login Title: {page_title}")
                
                if "login" not in current_url.lower() and "error" not in page_title.lower():
                    self.uploader_log_msg("✅ Successfully logged into Therapy Notes")
                    self.uploader_status_label.config(text="Logged into Therapy Notes")
                    
                    # Navigate to Patients page
                    self.uploader_log_msg("🔍 Navigating to Patients page...")
                    try:
                        # Find and click the Patients button
                        patients_button = self.tn_driver.find_element(By.XPATH, "//span[text()='Patients']")
                        patients_button.click()
                        self.uploader_log_msg("✅ Clicked Patients button")
                        
                        time.sleep(1.5)  # Wait for page to load
                        self.uploader_log_msg("✅ Successfully navigated to Patients page")
                        self.uploader_status_label.config(text="On Patients page - Ready for CSV processing")
                        
                        # Automatically start the upload process
                        self.uploader_log_msg("🚀 Automatically starting upload process...")
                        self._start_upload()
                        
                    except Exception as nav_e:
                        self.uploader_log_msg(f"❌ Failed to navigate to Patients: {nav_e}")
                        
                else:
                    self.uploader_log_msg("❌ Login failed - please check credentials")
                    
            except Exception as e:
                self.uploader_log_msg(f"❌ Login error: {e}")
        
        threading.Thread(target=run, daemon=True).start()

    def _init_therapy_notes_driver(self):
        """Initialize a separate driver for Therapy Notes"""
        try:
            # Close any existing driver session first
            if hasattr(self, 'tn_driver') and self.tn_driver is not None:
                try:
                    self.tn_driver.quit()
                except:
                    pass
                self.tn_driver = None
            
            options = ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            # Add additional options to prevent permission issues
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            # Don't use temporary profile - it may be causing session issues
            # Instead, use a regular profile but clear cookies after navigation
            
            # Try to install ChromeDriver with better error handling
            try:
                service = ChromeService(ChromeDriverManager().install())
            except Exception as install_e:
                self.uploader_log_msg(f"❌ ChromeDriver installation failed: {install_e}")
                # Try to use system ChromeDriver if available
                try:
                    service = ChromeService()  # Use system ChromeDriver
                    self.uploader_log_msg("🔄 Using system ChromeDriver as fallback")
                except Exception as system_e:
                    self.uploader_log_msg(f"❌ System ChromeDriver also failed: {system_e}")
                    return None
            
            driver = webdriver.Chrome(service=service, options=options)
            
            # Set page load timeout
            driver.set_page_load_timeout(60)
            
            # Clear cookies before navigation to ensure fresh session
            try:
                driver.delete_all_cookies()
            except:
                pass  # Cookies might not be set yet, that's okay
            
            # Hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to initialize Therapy Notes driver: {e}")
            # Try to provide more helpful error message
            if "Access is denied" in str(e):
                self.uploader_log_msg("💡 Try closing all Chrome browsers and running the bot as Administrator")
            elif "invalid session id" in str(e).lower():
                self.uploader_log_msg("💡 Session expired - please close all Chrome browsers and try again")
            return None

    def _browse_csv_file(self):
        """Browse for CSV file to upload"""
        filename = filedialog.askopenfilename(
            title="Select CSV file to upload",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.csv_file_var.set(filename)
            self.uploader_log_msg(f"Selected CSV file: {filename}")
            
            # Automatically validate the CSV file
            self.uploader_log_msg("🔍 Automatically validating CSV file...")
            self._validate_csv()
    
    def _browse_output_location(self):
        """Browse for output directory for results CSV"""
        directory = filedialog.askdirectory(
            title="Select Output Directory for Results CSV"
        )
        if directory:
            self.output_location_var.set(directory)
            self.uploader_log_msg(f"📁 Selected output location: {directory}")

    def _validate_csv(self):
        """Validate the selected CSV file"""
        csv_file = self.csv_file_var.get()
        if not csv_file:
            self.uploader_log_msg("Please select a CSV file first")
            return
        
        try:
            import pandas as pd
            # Try UTF-8 first, fallback to latin-1 for special characters
            try:
                df = pd.read_csv(csv_file, encoding='utf-8')
            except UnicodeDecodeError:
                self.uploader_log_msg("⚠️ UTF-8 failed, trying latin-1 encoding...")
                df = pd.read_csv(csv_file, encoding='latin-1')
            
            required_columns = ['Case Name', 'Case ID', 'Primary Workers', 'Service File Status', 'Extraction Date']
            optional_columns = ['Client DOB']  # Optional - new column, old CSVs may not have it
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                self.uploader_log_msg(f"❌ CSV validation failed. Missing columns: {missing_columns}")
                return
            
            # Check if optional columns are present
            if 'Client DOB' in df.columns:
                self.uploader_log_msg("✅ Client DOB column found - will use for patient verification")
            else:
                self.uploader_log_msg("⚠️ Client DOB column not found - will use name-only matching (older CSV format)")
            
            self.uploader_log_msg(f"✅ CSV validation successful. Found {len(df)} records")
            self.uploader_log_msg(f"Columns: {list(df.columns)}")
            
        except Exception as e:
            self.uploader_log_msg(f"❌ CSV validation failed: {e}")

    def _start_upload(self):
        """Start the upload process"""
        def run():
            try:
                # Check if logged into Therapy Notes
                if not hasattr(self, 'tn_driver') or self.tn_driver is None:
                    self.uploader_log_msg("❌ Please login to Therapy Notes first")
                    return
                
                # Check if CSV file is selected
                csv_file = self.csv_file_var.get()
                if not csv_file:
                    self.uploader_log_msg("❌ Please select a CSV file first")
                    return
                
                self.uploader_log_msg("🚀 Starting upload process...")
                self.uploader_status_label.config(text="Processing CSV file...")
                
                # Read and process CSV file
                import pandas as pd
                # Try UTF-8 first, fallback to latin-1 for special characters
                try:
                    df = pd.read_csv(csv_file, encoding='utf-8')
                except UnicodeDecodeError:
                    self.uploader_log_msg("⚠️ UTF-8 failed, trying latin-1 encoding...")
                    df = pd.read_csv(csv_file, encoding='latin-1')
                
                self.uploader_log_msg(f"📊 Loaded CSV with {len(df)} records")
                
                # Create results list to track success/failure
                results = []
                
                # Process each record
                for index, row in df.iterrows():
                    case_name = row['Case Name']
                    case_id = row['Case ID']
                    primary_workers = row['Primary Workers']
                    
                    # Get DOB if available (optional column)
                    client_dob = ""
                    if 'Client DOB' in row and pd.notna(row['Client DOB']):
                        client_dob = str(row['Client DOB']).strip()
                    
                    # Parse primary workers (they're stored as semicolon-separated string)
                    if isinstance(primary_workers, str):
                        primary_workers_list = [worker.strip() for worker in primary_workers.split(';') if worker.strip()]
                    else:
                        primary_workers_list = []
                    
                    self.uploader_log_msg(f"🔍 Processing: {case_name} (ID: {case_id})")
                    if client_dob:
                        self.uploader_log_msg(f"📅 Client DOB: {client_dob} (will use for verification)")
                    self.uploader_log_msg(f"👥 Counselors to remove: {', '.join(primary_workers_list)}")
                    
                    # CRITICAL: Always return to Patients page before searching for each patient
                    # This ensures the search bar is available and we're not stuck on a patient detail page
                    # This matches the pattern used in the IPS uploader for reliability
                    if index > 0:  # Skip for first patient (should already be on Patients page after login)
                        self._return_to_patients_page()
                    else:
                        # For first patient, verify we're on Patients page
                        try:
                            # Quick check to ensure we're on Patients page
                            self.tn_driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
                        except:
                            # If search bar not found, navigate to Patients page
                            self.uploader_log_msg("⚠️ Not on Patients page for first patient, navigating...")
                            self._return_to_patients_page()
                    
                    # Store current patient data for use in review function
                    self.current_case_name = case_name
                    self.current_case_id = case_id
                    self.current_primary_workers = primary_workers_list
                    
                    # Track success/failure for this patient
                    patient_success = False
                    try:
                        # Search for patient - this now returns True/False
                        # Pass DOB for verification when multiple patients match
                        patient_found = self._search_patient(case_name, client_dob=client_dob)
                        if patient_found:
                            patient_success = True
                            self.uploader_log_msg(f"✅ Successfully processed: {case_name}")
                        else:
                            patient_success = False
                            self.uploader_log_msg(f"⚠️ Patient not found in dropdown: {case_name}")
                            # Return to Patients page after failed search to ensure we're ready for next patient
                            self._return_to_patients_page()
                    except Exception as e:
                        self.uploader_log_msg(f"❌ Failed to process: {case_name} - {e}")
                        patient_success = False
                        # Return to Patients page after error to ensure we're ready for next patient
                        try:
                            self._return_to_patients_page()
                        except:
                            pass  # Continue even if return fails
                    
                    # Add result to tracking list
                    status = 'SUCCESS' if patient_success else 'Not Found'
                    results.append({
                        'Case Name': case_name,
                        'Case ID': case_id,
                        'Primary Workers': primary_workers,
                        'Process Status': status,
                        'Process Date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                    time.sleep(1)  # Wait between patients
                
                # Create results CSV
                self._create_results_csv(results, csv_file)
                
                self.uploader_log_msg("✅ Upload process completed!")
                self.uploader_status_label.config(text="Upload completed")
                
                # Check if IPS Uploader should auto-run
                if self.auto_run_ips_uploader.get():
                    self.uploader_log_msg("[AUTO-IPS] ✅ Auto-run IPS Uploader enabled")
                    self.uploader_log_msg("[AUTO-IPS] Closing Base browser...")
                    
                    # Close Base driver
                    try:
                        if hasattr(self, 'tn_driver') and self.tn_driver:
                            self.tn_driver.quit()
                            self.tn_driver = None
                            self.uploader_log_msg("[AUTO-IPS] ✅ Base browser closed")
                    except Exception as e:
                        self.uploader_log_msg(f"[AUTO-IPS][WARN] Error closing Base browser: {e}")
                    
                    # Auto-populate IPS tab with same credentials, CSV, and output location
                    self.uploader_log_msg("[AUTO-IPS] Auto-populating IPS tab...")
                    # IPS username and password are Entry widgets, not StringVars
                    self.ips_user.delete(0, tk.END)
                    self.ips_user.insert(0, self.tn_user.get())
                    self.ips_pass.delete(0, tk.END)
                    self.ips_pass.insert(0, self.tn_pass.get())
                    self.ips_csv_file_var.set(self.csv_file_var.get())
                    # Copy output location from base uploader to IPS uploader
                    self.ips_output_location_var.set(self.output_location_var.get())
                    self.uploader_log_msg(f"[AUTO-IPS] Using base uploader output location: {self.output_location_var.get()}")
                    
                    # Switch to IPS tab
                    self.uploader_log_msg("[AUTO-IPS] Switching to IPS tab...")
                    self.notebook.select(2)  # IPS Uploader is tab index 2 (0=Extractor, 1=Uploader, 2=IPS)
                    
                    # Trigger IPS login and upload after a brief delay
                    self.uploader_log_msg("[AUTO-IPS] Starting IPS Uploader in 2 seconds...")
                    self.after(2000, self._auto_trigger_ips_login_and_upload)
                else:
                    self.uploader_log_msg("✅ Upload complete. IPS auto-run not enabled.")
                
            except Exception as e:
                self.uploader_log_msg(f"❌ Upload process failed: {e}")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _auto_trigger_ips_login_and_upload(self):
        """Auto-trigger IPS login and upload after Base completes"""
        try:
            self.uploader_log_msg("[AUTO-IPS] 🚀 Triggering IPS login...")
            self.ips_uploader_log_msg("[AUTO-IPS] 🚀 Auto-started by Base Uploader")
            
            # Trigger IPS login (correct method name)
            self._login_ips_therapy_notes()
            
        except Exception as e:
            self.uploader_log_msg(f"[AUTO-IPS][ERR] Failed to trigger IPS: {e}")
            self.ips_uploader_log_msg(f"[AUTO-IPS][ERR] Failed to auto-start: {e}")
            import traceback
            self.uploader_log_msg(f"[AUTO-IPS][DEBUG] {traceback.format_exc()}")

    def _format_name_for_search(self, case_name):
        """Format case name for Therapy Notes search (remove periods from middle initials)"""
        # Remove periods from middle initials: "John H. Smith" -> "John H Smith"
        import re
        # Pattern to match middle initial with period: single letter followed by period
        # Updated pattern to be more flexible - matches single capital letter followed by period
        # This handles cases like "Kerry A. Toth" -> "Kerry A Toth"
        formatted_name = re.sub(r'([A-Z])\.', r'\1', case_name)
        
        # Additional cleanup: remove any extra spaces that might have been created
        formatted_name = re.sub(r'\s+', ' ', formatted_name).strip()
        
        self.uploader_log_msg(f"🔍 DEBUG: Original name: '{case_name}' -> Formatted: '{formatted_name}'", debug_only=True)
        return formatted_name

    def _has_middle_initial(self, name):
        """Check if a name has a middle initial (single letter followed by period)"""
        import re
        # Pattern to match middle initial: single capital letter followed by period
        # Examples: "John H. Smith", "Mary A. Johnson", "Kerry A. Toth"
        pattern = r'\b[A-Z]\.\s+[A-Z]'
        return bool(re.search(pattern, name))

    def _remove_middle_initial(self, name):
        """Remove middle initial from a name (e.g., 'John H. Smith' -> 'John Smith')"""
        import re
        # Pattern to match and remove middle initial: single capital letter followed by period
        # This removes the middle initial and its period, keeping the rest of the name
        # Examples: "John H. Smith" -> "John Smith", "Mary A. Johnson" -> "Mary Johnson"
        pattern = r'\s+[A-Z]\.\s+'
        replacement = ' '
        result = re.sub(pattern, replacement, name)
        
        # Clean up any extra spaces
        result = re.sub(r'\s+', ' ', result).strip()
        
        self.uploader_log_msg(f"🔍 DEBUG: Removed middle initial: '{name}' -> '{result}'", debug_only=True)
        return result
    
    def _extract_dob_from_option(self, option_text):
        """Extract DOB from dropdown option text (format: 'Name DOB: MM/DD/YYYY')"""
        import re
        # Pattern to match "DOB: MM/DD/YYYY" or "DOB:MM/DD/YYYY"
        pattern = r'DOB:\s*(\d{1,2}/\d{1,2}/\d{4})'
        match = re.search(pattern, option_text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _normalize_dob(self, dob):
        """Normalize DOB format for comparison (MM/DD/YYYY)"""
        if not dob:
            return ""
        # Remove any extra spaces and ensure consistent format
        dob_str = str(dob).strip()
        if not dob_str:
            return ""

        # If timestamp-like ("YYYY-MM-DD HH:MM:SS"), keep date portion only
        if " " in dob_str:
            dob_str = dob_str.split(" ")[0]

        # Use common separators interchangeably
        dob_str = dob_str.replace("\\", "/")

        # Try parsing with a set of known formats
        possible_formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%Y-%m-%d",
            "%Y/%m/%d",
        ]

        for fmt in possible_formats:
            try:
                parsed = datetime.strptime(dob_str, fmt)
                return parsed.strftime("%m/%d/%Y")
            except ValueError:
                continue

        # Last resort: attempt to extract numbers and reformat
        import re

        match = re.match(r"(\d{1,2})[\-/](\d{1,2})[\-/](\d{2,4})", dob_str)
        if match:
            month, day, year = match.groups()
            # Ensure year is 4 digits (e.g., '33' -> '0033' isn't correct, so keep original when <1000)
            year_int = int(year)
            if year_int < 100:  # Two-digit year, assume 1900s to maintain legacy data
                year_int += 1900
            return f"{int(month):02d}/{int(day):02d}/{year_int:04d}"

        return dob_str
    
    def _dob_matches(self, dob1, dob2):
        """Check if two DOBs match (normalized comparison)"""
        if not dob1 or not dob2:
            return False
        dob1_norm = self._normalize_dob(dob1)
        dob2_norm = self._normalize_dob(dob2)
        return dob1_norm == dob2_norm

    def _search_patient(self, case_name, client_dob=""):
        """Search for a patient in Therapy Notes and select from dropdown
        
        Args:
            case_name: The patient's name to search for
            client_dob: Optional DOB in MM/DD/YYYY format for verification when multiple patients match
        """
        try:
            # CRITICAL: Ensure we're on the Patients page before searching
            # This prevents "no such element" errors when the search bar doesn't exist
            try:
                # Quick check to see if search bar exists
                self.tn_driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
            except:
                # Search bar not found - we're not on Patients page, navigate there first
                self.uploader_log_msg("⚠️ Search bar not found - ensuring we're on Patients page...")
                self._return_to_patients_page()
                # Wait a moment for page to load
                time.sleep(0.5)
            
            # Format the name for search (remove periods from middle initials)
            search_name = self._format_name_for_search(case_name)
            self.uploader_log_msg(f"🔍 Searching for patient: {case_name}")
            if client_dob:
                self.uploader_log_msg(f"📅 Using DOB for verification: {client_dob}")
            self.uploader_log_msg(f"🔍 Formatted search term: {search_name}", debug_only=True)
            
            # Check if name has middle initial and prepare fallback name
            has_middle_initial = self._has_middle_initial(case_name)
            fallback_name = None
            if has_middle_initial:
                fallback_name = self._remove_middle_initial(case_name)
                self.uploader_log_msg(f"🔍 MIDDLE INITIAL DETECTED: '{case_name}' -> fallback: '{fallback_name}'")
            
            # Find the patient search input field
            search_input = self.tn_driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
            
            # Try full name first
            search_input.clear()
            search_input.send_keys(search_name)  # Use formatted name
            self.uploader_log_msg(f"✅ Entered search term: {search_name}")
            
            # Wait for dropdown to appear
            time.sleep(1)
            
            # Wait for the dropdown container to appear
            try:
                dropdown_container = WebDriverWait(self.tn_driver, 10).until(
                    EC.presence_of_element_located((By.ID, "ContentBubbleResultsContainer"))
                )
                self.uploader_log_msg("✅ Dropdown results appeared")
                
                # Find all patient options in the dropdown
                patient_options = dropdown_container.find_elements(By.TAG_NAME, "div")
                self.uploader_log_msg(f"📋 Found {len(patient_options)} options in dropdown")
                
                # Look for the matching patient name using full name matching
                # If DOB is provided, verify DOB matches when multiple patients have the same name
                patient_selected = False
                matching_options = []  # Store all name matches for DOB verification
                
                for option in patient_options:
                    option_text = option.text.strip()
                    self.uploader_log_msg(f"🔍 Checking option: '{option_text}'", debug_only=True)
                    
                    # Extract name part (before "DOB:" if present)
                    name_part = option_text.split(' DOB:')[0].strip() if ' DOB:' in option_text else option_text
                    
                    # Check if name matches
                    name_matches = False
                    if option_text and option_text.lower() == search_name.lower():
                        name_matches = True
                    elif option_text and search_name.lower() in option_text.lower():
                        name_matches = True
                    
                    if name_matches:
                        # Extract DOB from option text
                        option_dob = self._extract_dob_from_option(option_text)
                        
                        # If DOB is provided, verify it matches
                        if client_dob:
                            if option_dob and self._dob_matches(client_dob, option_dob):
                                self.uploader_log_msg(f"🎯 Found exact match with DOB verification: {option_text}")
                                self.uploader_log_msg(f"✅ DOB matches: {client_dob} == {option_dob}")
                                try:
                                    option.click()
                                    self.uploader_log_msg("✅ Selected exact match with DOB verification from dropdown")
                                    patient_selected = True
                                    break
                                except Exception as click_e:
                                    self.uploader_log_msg(f"❌ Click failed, trying JavaScript: {click_e}", debug_only=True)
                                    try:
                                        self.tn_driver.execute_script("arguments[0].click();", option)
                                        self.uploader_log_msg("✅ Selected exact match with DOB verification via JavaScript")
                                        patient_selected = True
                                        break
                                    except Exception as js_e:
                                        self.uploader_log_msg(f"❌ JavaScript click also failed: {js_e}", debug_only=True)
                                        continue
                            else:
                                # Name matches but DOB doesn't - store for later if no DOB match found
                                matching_options.append((option, option_text, option_dob))
                                self.uploader_log_msg(f"⚠️ Name matches but DOB doesn't: {option_text} (DOB: {option_dob} vs expected: {client_dob})", debug_only=True)
                        else:
                            # No DOB provided - use name-only matching (original behavior)
                            if option_text and option_text.lower() == search_name.lower():
                                self.uploader_log_msg(f"🎯 Found exact match: {option_text}")
                                try:
                                    option.click()
                                    self.uploader_log_msg("✅ Selected exact match from dropdown")
                                    patient_selected = True
                                    break
                                except Exception as click_e:
                                    self.uploader_log_msg(f"❌ Click failed, trying JavaScript: {click_e}", debug_only=True)
                                    try:
                                        self.tn_driver.execute_script("arguments[0].click();", option)
                                        self.uploader_log_msg("✅ Selected exact match via JavaScript")
                                        patient_selected = True
                                        break
                                    except Exception as js_e:
                                        self.uploader_log_msg(f"❌ JavaScript click also failed: {js_e}", debug_only=True)
                                        continue
                            elif option_text and search_name.lower() in option_text.lower():
                                self.uploader_log_msg(f"🎯 Found partial match: {option_text}")
                                try:
                                    option.click()
                                    self.uploader_log_msg("✅ Selected partial match from dropdown")
                                    patient_selected = True
                                    break
                                except Exception as click_e:
                                    self.uploader_log_msg(f"❌ Click failed, trying JavaScript: {click_e}", debug_only=True)
                                    try:
                                        self.tn_driver.execute_script("arguments[0].click();", option)
                                        self.uploader_log_msg("✅ Selected partial match via JavaScript")
                                        patient_selected = True
                                        break
                                    except Exception as js_e:
                                        self.uploader_log_msg(f"❌ JavaScript click also failed: {js_e}", debug_only=True)
                                        continue
                
                # If DOB was provided but no exact DOB match found, warn user
                if client_dob and not patient_selected and matching_options:
                    self.uploader_log_msg(f"⚠️ Found {len(matching_options)} patient(s) with matching name but DOB mismatch")
                    self.uploader_log_msg(f"⚠️ Expected DOB: {client_dob}, but found:")
                    for opt, opt_text, opt_dob in matching_options:
                        self.uploader_log_msg(f"   - {opt_text} (DOB: {opt_dob})")
                    # Don't select any - let user know there's a mismatch
                    return False
                
                # If no match found and we have a fallback name (without middle initial), try it
                if not patient_selected and fallback_name:
                    if client_dob:
                        self.uploader_log_msg("⚠️ Skipping fallback search without middle initial because DOB verification is required")
                        self.uploader_log_msg("❌ No patient options found in dropdown")
                        return False
                    self.uploader_log_msg(f"🔄 MIDDLE INITIAL FALLBACK: No match with full name, trying without middle initial: {fallback_name}")
                    
                    # Clear search field and try fallback name
                    search_input.clear()
                    search_input.send_keys(fallback_name)
                    self.uploader_log_msg(f"✅ Entered fallback search term: {fallback_name}")
                    
                    # Wait for new dropdown results
                    time.sleep(1)
                    
                    try:
                        # Wait for the dropdown container to appear again
                        dropdown_container = WebDriverWait(self.tn_driver, 10).until(
                            EC.presence_of_element_located((By.ID, "ContentBubbleResultsContainer"))
                        )
                        self.uploader_log_msg("✅ Fallback dropdown results appeared")
                        
                        # Find all patient options in the new dropdown
                        patient_options = dropdown_container.find_elements(By.TAG_NAME, "div")
                        self.uploader_log_msg(f"📋 Found {len(patient_options)} options in fallback dropdown")
                        
                        # Look for the matching patient name using fallback name
                        for option in patient_options:
                            option_text = option.text.strip()
                            self.uploader_log_msg(f"🔍 Checking fallback option: '{option_text}'", debug_only=True)
                            
                            # Try exact match first (case insensitive)
                            if option_text and option_text.lower() == fallback_name.lower():
                                self.uploader_log_msg(f"🎯 Found exact fallback match: {option_text}")
                                try:
                                    option.click()
                                    self.uploader_log_msg("✅ Selected exact fallback match from dropdown")
                                    patient_selected = True
                                    break
                                except Exception as click_e:
                                    self.uploader_log_msg(f"❌ Fallback click failed, trying JavaScript: {click_e}", debug_only=True)
                                    try:
                                        self.tn_driver.execute_script("arguments[0].click();", option)
                                        self.uploader_log_msg("✅ Selected exact fallback match via JavaScript")
                                        patient_selected = True
                                        break
                                    except Exception as js_e:
                                        self.uploader_log_msg(f"❌ Fallback JavaScript click also failed: {js_e}", debug_only=True)
                                        continue
                            # Try partial match as fallback
                            elif option_text and fallback_name.lower() in option_text.lower():
                                self.uploader_log_msg(f"🎯 Found partial fallback match: {option_text}")
                                try:
                                    option.click()
                                    self.uploader_log_msg("✅ Selected partial fallback match from dropdown")
                                    patient_selected = True
                                    break
                                except Exception as click_e:
                                    self.uploader_log_msg(f"❌ Fallback click failed, trying JavaScript: {click_e}", debug_only=True)
                                    try:
                                        self.tn_driver.execute_script("arguments[0].click();", option)
                                        self.uploader_log_msg("✅ Selected partial fallback match via JavaScript")
                                        patient_selected = True
                                        break
                                    except Exception as js_e:
                                        self.uploader_log_msg(f"❌ Fallback JavaScript click also failed: {js_e}", debug_only=True)
                                        continue
                        
                        # If still no match with fallback, try clicking the first option
                        if not patient_selected and patient_options and not client_dob:
                            first_option = patient_options[0]
                            self.uploader_log_msg(f"🔄 Selecting first fallback option: {first_option.text}")
                            try:
                                first_option.click()
                                self.uploader_log_msg("✅ Selected first available fallback option")
                                patient_selected = True
                            except Exception as click_e:
                                self.uploader_log_msg(f"❌ First fallback option click failed, trying JavaScript: {click_e}", debug_only=True)
                                try:
                                    self.tn_driver.execute_script("arguments[0].click();", first_option)
                                    self.uploader_log_msg("✅ Selected first fallback option via JavaScript")
                                    patient_selected = True
                                except Exception as js_e:
                                    self.uploader_log_msg(f"❌ Fallback JavaScript click also failed: {js_e}", debug_only=True)
                    
                    except Exception as e:
                        self.uploader_log_msg(f"❌ Fallback search failed: {e}", debug_only=True)
                
                # If still no match found, try clicking the first option from original search
                if not patient_selected:
                    self.uploader_log_msg(f"⚠️ No exact match found for: {case_name}")
                    # Never auto-select when DOB is provided and verification failed
                    if client_dob:
                        self.uploader_log_msg("⚠️ Skipping auto-select because DOB verification failed")
                        self.uploader_log_msg("❌ No patient options found in dropdown")
                        return False
                    # If no exact match, try clicking the first option
                    if patient_options:
                        first_option = patient_options[0]
                        self.uploader_log_msg(f"🔄 Selecting first option: {first_option.text}")
                        try:
                            first_option.click()
                            self.uploader_log_msg("✅ Selected first available option")
                            patient_selected = True
                        except Exception as click_e:
                            self.uploader_log_msg(f"❌ First option click failed, trying JavaScript: {click_e}", debug_only=True)
                            try:
                                self.tn_driver.execute_script("arguments[0].click();", first_option)
                                self.uploader_log_msg("✅ Selected first option via JavaScript")
                                patient_selected = True
                            except Exception as js_e:
                                self.uploader_log_msg(f"❌ JavaScript click also failed: {js_e}", debug_only=True)
                
                if patient_selected:
                    time.sleep(1)  # Reduced wait time for patient page to load
                    self.uploader_log_msg("✅ Patient selected successfully")
                    
                    # Navigate to Clinicians tab
                    self._navigate_to_clinicians_tab()
                    return True
                else:
                    self.uploader_log_msg("❌ No patient options found in dropdown")
                    return False
                    
            except Exception as dropdown_e:
                self.uploader_log_msg(f"❌ Dropdown selection failed: {dropdown_e}")
                # Fallback: try pressing Enter
                search_input.send_keys(Keys.RETURN)
                self.uploader_log_msg("🔄 Fallback: Pressed Enter to search")
                time.sleep(1.5)
                
                # If we have a middle initial fallback name, try it now
                if fallback_name:
                    self.uploader_log_msg(f"🔄 MIDDLE INITIAL FALLBACK: Dropdown failed, trying without middle initial: {fallback_name}")
                    
                    # Clear search field and try fallback name
                    search_input.clear()
                    search_input.send_keys(fallback_name)
                    self.uploader_log_msg(f"✅ Entered fallback search term: {fallback_name}")
                    
                    # Press Enter to search
                    search_input.send_keys(Keys.RETURN)
                    time.sleep(1.5)
                    
                    # Try to find patient in results
                    try:
                        # Look for patient links on the page
                        patient_links = self.tn_driver.find_elements(By.XPATH, f"//a[contains(text(), '{fallback_name}')]")
                        if patient_links:
                            self.uploader_log_msg(f"✅ Found patient with fallback name: {fallback_name}")
                            patient_links[0].click()
                            time.sleep(1)
                            self.uploader_log_msg("✅ Patient selected successfully with fallback name")
                            self._navigate_to_clinicians_tab()
                            return True
                        else:
                            self.uploader_log_msg(f"❌ Patient not found with fallback name: {fallback_name}")
                    except Exception as fallback_e:
                        self.uploader_log_msg(f"❌ Fallback search failed: {fallback_e}")
            
        except Exception as e:
            self.uploader_log_msg(f"❌ Patient search failed: {e}")
            return False

    def _navigate_to_clinicians_tab(self):
        """Navigate to the Clinicians tab for the selected patient"""
        try:
            self.uploader_log_msg("👥 Navigating to Clinicians tab...")
            
            # Find and click the Clinicians tab using multiple selectors
            clinicians_selectors = [
                "//a[contains(text(), 'Clinicians')]",
                "//a[@data-tab-id='Clinicians']",
                "//span[contains(text(), 'Clinicians')]",
                "//button[contains(text(), 'Clinicians')]"
            ]
            
            clinicians_tab = None
            for selector in clinicians_selectors:
                try:
                    clinicians_tab = self.tn_driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue
            
            if clinicians_tab:
                clinicians_tab.click()
                self.uploader_log_msg("✅ Clicked Clinicians tab")
                
                # OPTIMIZATION: Check for "None" element with dynamic wait - fastest way to detect no counselors
                # This check happens first, before any waiting, to skip clients with no counselors instantly
                # Uses polling to wait for page to load, but exits immediately once "None" is found
                self.uploader_log_msg("🔍 Checking for 'None' element (no counselors indicator)...")
                
                try:
                    # Use dynamic wait - check every 0.3 seconds for up to 5 seconds
                    # This allows for slow page loads while still exiting immediately when "None" is found
                    max_wait_none = 5  # Maximum 5 seconds to wait for page to load
                    wait_interval = 0.3  # Check every 0.3 seconds
                    elapsed_time = 0
                    none_found = False
                    
                    while elapsed_time < max_wait_none and not none_found:
                        try:
                            none_elements = self.tn_driver.find_elements(By.XPATH, 
                                "//span[@class='no-data' and contains(text(), 'None')] | "
                                "//span[contains(@class, 'no-data') and contains(text(), 'None')]")
                            
                            if none_elements:
                                visible_none = sum(1 for elem in none_elements if elem.is_displayed())
                                if visible_none > 0:
                                    self.uploader_log_msg(f"✅ FAST DETECTION: Found 'None' element after {elapsed_time:.1f}s - no counselors assigned, skipping this client immediately")
                                    # CRITICAL: Navigate back to Patients page before returning
                                    # Otherwise, the next patient search will fail because we're still on the Clinicians tab
                                    self._return_to_patients_page()
                                    # Return immediately - no need to process this client further
                                    return
                        except Exception:
                            pass  # Continue checking if element not found yet
                        
                        time.sleep(wait_interval)
                        elapsed_time += wait_interval
                    
                    # If we get here, "None" was not found - page likely has counselors or is still loading
                    if elapsed_time >= max_wait_none:
                        self.uploader_log_msg("✅ No 'None' element found - page likely has counselors or still loading")
                    
                except Exception as e:
                    self.uploader_log_msg(f"⚠️ Error checking for 'None' element: {e}", debug_only=True)
                    # Continue with normal flow if check fails
                
                # CRITICAL: Wait for page to load and counselors to appear BEFORE clicking Edit
                # The Edit button should only be clicked after counselors are visible
                self.uploader_log_msg("⏳ Waiting for Clinicians tab to fully load...")
                time.sleep(1)  # Brief additional wait for page to stabilize
                
                # Wait for counselors to appear first (this ensures page is ready)
                self.uploader_log_msg("⏳ Waiting for counselors to appear on page...")
                counselors_visible = False
                max_wait_counselors = 10  # Wait up to 10 seconds for counselors
                wait_interval = 0.5
                elapsed_time_counselors = 0
                
                while elapsed_time_counselors < max_wait_counselors and not counselors_visible:
                    try:
                        # First, check if there are NO counselors (quick exit)
                        # Check for "None" element again in the loop (in case page loads slowly)
                        none_elements = self.tn_driver.find_elements(By.XPATH, 
                            "//span[@class='no-data' and contains(text(), 'None')] | "
                            "//span[contains(@class, 'no-data') and contains(text(), 'None')]")
                        
                        if none_elements:
                            visible_none = sum(1 for elem in none_elements if elem.is_displayed())
                            if visible_none > 0:
                                self.uploader_log_msg("✅ FAST DETECTION: Found 'None' element - no counselors assigned, skipping this client")
                                # Return immediately - no need to process this client further
                                return
                        
                        # Also check for other "no counselors" indicators
                        no_counselors_indicators = self.tn_driver.find_elements(By.XPATH,
                            "//div[contains(text(), 'Assign a Clinician')] | "
                            "//span[contains(text(), 'Assign a Clinician')] | "
                            "//div[contains(text(), 'select a clinician')] | "
                            "//span[contains(text(), 'select a clinician')]")
                        
                        if no_counselors_indicators:
                            visible_no_counselors = sum(1 for elem in no_counselors_indicators if elem.is_displayed())
                            if visible_no_counselors > 0:
                                self.uploader_log_msg("✅ Detected: No counselors assigned to this patient (found 'Assign a Clinician' text)")
                                counselors_visible = False  # Mark as no counselors
                                break  # Exit loop immediately - no need to wait
                        
                        # Check for counselor names or elements (not X buttons - those come after Edit)
                        # Look for any text that might be a counselor name
                        counselor_elements = self.tn_driver.find_elements(By.XPATH, 
                            "//div[contains(@class, 'counselor') or contains(@class, 'clinician') or contains(@class, 'staff')] | "
                            "//span[contains(@class, 'counselor') or contains(@class, 'clinician')] | "
                            "//div[contains(text(), ',')]")
                        
                        if counselor_elements:
                            # Check if any are visible
                            visible_count = sum(1 for elem in counselor_elements if elem.is_displayed() and elem.text.strip() and len(elem.text.strip()) > 2)
                            if visible_count > 0:
                                self.uploader_log_msg(f"✅ Found {visible_count} visible counselor element(s) - page loaded")
                                counselors_visible = True
                                break
                    except:
                        pass
                    
                    time.sleep(wait_interval)
                    elapsed_time_counselors += wait_interval
                
                if not counselors_visible:
                    self.uploader_log_msg("⚠️ Counselors not visible - may have no counselors or page still loading")
                    time.sleep(1)  # Extra wait just in case
                
                # Now wait for Edit button to be present
                self.uploader_log_msg("⏳ Waiting for Edit button to be ready and clickable...")
                
                edit_button_clicked = False
                edit_btn = None
                
                # Try multiple selectors for Edit button (prioritize the exact one from HTML)
                edit_selectors = [
                    "//psy-button[@class='ClickToEditBtn hydrated' and contains(., 'Edit')]",
                    "//psy-button[@class='ClickToEditBtn hydrated']",
                    "//psy-button[contains(@class, 'ClickToEditBtn')]",
                    "//button[contains(text(), 'Edit')]"
                ]
                
                # Step 1: Wait for Edit button to be present (not just found)
                for selector in edit_selectors:
                    try:
                        # Wait for element to be present in DOM
                        edit_btn = WebDriverWait(self.tn_driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                        self.uploader_log_msg(f"✅ Found Edit button with selector: {selector}")
                        break
                    except:
                        continue
                
                # Initialize x_buttons_found flag
                x_buttons_found = False
                
                # Step 2: Click Edit button (after counselors are visible)
                if edit_btn:
                    try:
                        # Scroll to button first
                        self.tn_driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", edit_btn)
                        time.sleep(0.5)  # Brief wait after scroll
                        
                        self.uploader_log_msg("✅ Clicking Edit button to enter edit mode...")
                        
                        # Use JavaScript click (most reliable for custom web components)
                        try:
                            self.tn_driver.execute_script("arguments[0].click();", edit_btn)
                            self.uploader_log_msg("✅ Edit button clicked (JavaScript)")
                            edit_button_clicked = True
                        except Exception as js_error:
                            # Fallback: try clicking inner button in shadow DOM
                            try:
                                inner_button = edit_btn.find_element(By.TAG_NAME, "button")
                                inner_button.click()
                                self.uploader_log_msg("✅ Edit button clicked (inner button)")
                                edit_button_clicked = True
                            except:
                                # Last resort: regular click
                                try:
                                    edit_btn.click()
                                    self.uploader_log_msg("✅ Edit button clicked (regular)")
                                    edit_button_clicked = True
                                except Exception as reg_error:
                                    self.uploader_log_msg(f"⚠️ All click methods failed: {reg_error}")
                        
                        # Wait for Edit mode to activate
                        time.sleep(2)  # Give Edit mode time to activate
                        
                        # QUICK CHECK: After clicking Edit, check if there are no counselors
                        # This allows us to skip waiting for X buttons if no counselors exist
                        try:
                            # Check for "None" element first (fastest detection)
                            none_elements = self.tn_driver.find_elements(By.XPATH, 
                                "//span[@class='no-data' and contains(text(), 'None')] | "
                                "//span[contains(@class, 'no-data') and contains(text(), 'None')]")
                            
                            if none_elements:
                                visible_none = sum(1 for elem in none_elements if elem.is_displayed())
                                if visible_none > 0:
                                    self.uploader_log_msg("✅ FAST DETECTION: Found 'None' element after Edit - no counselors assigned, skipping this client")
                                    # Return immediately - no need to process this client further
                                    return
                            
                            # Also check for other "no counselors" indicators
                            no_counselors_check = self.tn_driver.find_elements(By.XPATH,
                                "//div[contains(text(), 'Assign a Clinician')] | "
                                "//span[contains(text(), 'Assign a Clinician')] | "
                                "//div[contains(text(), 'select a clinician')] | "
                                "//span[contains(text(), 'select a clinician')]")
                            
                            if no_counselors_check:
                                visible_check = sum(1 for elem in no_counselors_check if elem.is_displayed())
                                if visible_check > 0:
                                    self.uploader_log_msg("✅ Confirmed: No counselors assigned - skipping X button wait")
                                    # Skip X button wait - no counselors means no X buttons
                                    x_buttons_found = True  # Mark as "found" (actually: confirmed none exist)
                        except:
                            pass  # Continue with normal flow if check fails
                        
                    except Exception as e:
                        self.uploader_log_msg(f"⚠️ Error clicking Edit button: {e}")
                else:
                    self.uploader_log_msg("⚠️ Edit button not found after waiting - proceeding anyway...")
                
                # Step 3: Wait for X buttons to appear (they appear after Edit is clicked)
                # BUT: Skip this if we already confirmed there are no counselors
                if not x_buttons_found:
                    self.uploader_log_msg("⏳ Waiting for counselor X buttons to appear...")
                    
                    max_wait_time_x = 5  # Reduced to 5 seconds - quick check
                    wait_interval = 0.5
                    elapsed_time = 0
                    
                    while elapsed_time < max_wait_time_x and not x_buttons_found:
                        try:
                            # QUICK CHECK: First verify there are actually counselors (not "Assign a Clinician")
                            no_counselors_check = self.tn_driver.find_elements(By.XPATH,
                                "//div[contains(text(), 'Assign a Clinician')] | "
                                "//span[contains(text(), 'Assign a Clinician')] | "
                                "//div[contains(text(), 'select a clinician')]")
                            
                            if no_counselors_check:
                                visible_check = sum(1 for elem in no_counselors_check if elem.is_displayed())
                                if visible_check > 0:
                                    self.uploader_log_msg("✅ Confirmed: No counselors assigned - no X buttons will appear")
                                    x_buttons_found = True  # Mark as found (none exist)
                                    break  # Exit immediately
                            
                            # Check for counselor X buttons
                            x_buttons = self.tn_driver.find_elements(By.XPATH, "//button[@title='Remove Clinician']")
                            if x_buttons:
                                visible_count = sum(1 for btn in x_buttons if btn.is_displayed())
                                if visible_count > 0:
                                    self.uploader_log_msg(f"✅ Found {visible_count} visible counselor X button(s) - counselors loaded!")
                                    x_buttons_found = True
                                    break
                            
                            # Fallback: Check for span-based X buttons
                            x_buttons = self.tn_driver.find_elements(By.XPATH, "//span[@class='button-text-input-mimic float-right']//button")
                            if x_buttons:
                                visible_count = sum(1 for btn in x_buttons if btn.is_displayed())
                                if visible_count > 0:
                                    self.uploader_log_msg(f"✅ Found {visible_count} visible counselor X button(s) (span-based) - counselors loaded!")
                                    x_buttons_found = True
                                    break
                        except Exception:
                            pass
                        
                        time.sleep(wait_interval)
                        elapsed_time += wait_interval
                
                if x_buttons_found:
                    self.uploader_log_msg("✅ Successfully navigated to Clinicians tab (counselor data loaded)")
                else:
                    self.uploader_log_msg(f"⚠️ Timeout after {max_wait_time_x}s - X buttons may not be visible (patient may have no counselors)")
                    self.uploader_log_msg("   Proceeding anyway to check for counselors...")
                
                # Review counselors and handle removal if needed
                self._review_and_remove_counselors()
            else:
                self.uploader_log_msg("❌ Could not find Clinicians tab")
                
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to navigate to Clinicians tab: {e}")

    def _review_and_remove_counselors(self):
        """Review counselors on the Clinicians tab and remove matching ones from CSV"""
        try:
            self.uploader_log_msg("🔍 Reviewing counselors on Clinicians tab...")
            
            # Get current patient's primary workers from CSV data
            current_case_name = getattr(self, 'current_case_name', 'Unknown')
            current_primary_workers = getattr(self, 'current_primary_workers', [])
            
            if not current_primary_workers:
                self.uploader_log_msg("ℹ️ No primary workers to remove for this patient")
                return
            
            self.uploader_log_msg(f"🎯 Looking for counselors to remove: {', '.join(current_primary_workers)}")
            
            # Look for counselor names on the page using a more dynamic approach
            # First, try to find counselor elements by looking for common patterns
            counselor_elements = []
            
            # Try multiple selectors to find counselor elements
            counselor_selectors = [
                "//div[contains(@class, 'counselor') or contains(@class, 'clinician') or contains(@class, 'staff')]",
                "//span[contains(@class, 'counselor') or contains(@class, 'clinician') or contains(@class, 'staff')]",
                "//div[contains(@class, 'name') or contains(@class, 'user')]",
                "//span[contains(@class, 'name') or contains(@class, 'user')]",
                "//div[contains(text(), ',') and string-length(text()) > 5]",  # Names with commas
                "//span[contains(text(), ',') and string-length(text()) > 5]",
                "//div[contains(@class, 'person') or contains(@class, 'member')]",
                "//span[contains(@class, 'person') or contains(@class, 'member')]"
            ]
            
            for selector in counselor_selectors:
                try:
                    elements = self.tn_driver.find_elements(By.XPATH, selector)
                    counselor_elements.extend(elements)
                except:
                    continue
            
            # Remove duplicates
            counselor_elements = list(set(counselor_elements))
            
            self.uploader_log_msg(f"🔍 Found {len(counselor_elements)} potential counselor elements", debug_only=True)
            
            counselors_found = []
            for i, element in enumerate(counselor_elements):
                try:
                    text = element.text.strip()
                    self.uploader_log_msg(f"🔍 Element {i+1}: '{text}'", debug_only=True)
                    # Filter for meaningful text that looks like names
                    if (text and len(text) > 2 and 
                        not text.lower() in ['edit', 'delete', 'remove', 'add', 'save', 'cancel', 'close', 'user options', 'contact us', 'log out', 'no future appt'] and
                        not text.startswith('http') and
                        not text.startswith('www') and
                        not text.isdigit()):
                        counselors_found.append(text)
                except:
                    continue
            
            self.uploader_log_msg(f"👥 Found {len(counselors_found)} counselor elements on page")
            self.uploader_log_msg(f"📋 Counselor names found: {counselors_found}", debug_only=True)
            
            # Check if any of the found counselors match our CSV data
            matching_counselors = []
            for counselor in counselors_found:
                for primary_worker in current_primary_workers:
                    self.uploader_log_msg(f"🔍 Comparing '{counselor}' with '{primary_worker}'", debug_only=True)
                    
                    # Normalize both names for comparison
                    counselor_normalized = counselor.lower().strip()
                    worker_normalized = primary_worker.lower().strip()
                    
                    # Check for direct matches
                    if (worker_normalized in counselor_normalized or 
                        counselor_normalized in worker_normalized):
                        matching_counselors.append(counselor)
                        self.uploader_log_msg(f"✅ Match found: '{counselor}' matches '{primary_worker}' (direct)", debug_only=True)
                        break
                    
                    # Check for "Last, First" vs "First Last" format
                    if ',' in worker_normalized:
                        # CSV format: "Hernandez, Cynthia" -> try "Cynthia Hernandez"
                        parts = worker_normalized.split(',')
                        if len(parts) == 2:
                            last_name = parts[0].strip()
                            first_name = parts[1].strip()
                            reversed_format = f"{first_name} {last_name}"
                            
                            if (reversed_format in counselor_normalized or 
                                counselor_normalized in reversed_format):
                                matching_counselors.append(counselor)
                                self.uploader_log_msg(f"✅ Match found: '{counselor}' matches '{primary_worker}' (reversed format)", debug_only=True)
                                break
                    
                    # Check if all words from CSV name are present in counselor name
                    worker_words = worker_normalized.replace(',', '').split()
                    if all(word in counselor_normalized for word in worker_words if len(word) > 1):
                        matching_counselors.append(counselor)
                        self.uploader_log_msg(f"✅ Match found: '{counselor}' matches '{primary_worker}' (word match)", debug_only=True)
                        break
                    
                    self.uploader_log_msg(f"❌ No match: '{counselor}' vs '{primary_worker}'", debug_only=True)
            
            if matching_counselors:
                self.uploader_log_msg(f"✅ Found matching counselors to remove: {', '.join(matching_counselors)}")
                # Click the Edit button to start removal process
                self._click_edit_button()
            else:
                self.uploader_log_msg("ℹ️ No matching counselors found - no removal needed")
                # Still need to click Edit button to check if there are any counselors to remove
                self.uploader_log_msg("🔍 Clicking Edit button to verify no counselors need removal...")
                self._click_edit_button()
                
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to review counselors: {e}")

    def _click_edit_button(self):
        """Click the Edit button to start counselor removal process"""
        try:
            # First, check if Edit mode is already active (Save button present)
            save_button = self.tn_driver.find_elements(By.XPATH, "//button[contains(text(), 'Save') or contains(text(), 'Save Changes')] | //input[@id='CommonFooter__SaveChanges-Button']")
            if save_button and any(btn.is_displayed() for btn in save_button):
                self.uploader_log_msg("✅ Edit mode already active - Save button present")
                # Edit mode is already active, proceed to removal
                self._remove_matching_counselors()
                return
            
            self.uploader_log_msg("✏️ Looking for Edit button...")
            
            # Find the Edit button using multiple selectors
            edit_selectors = [
                # Most specific - exact match for the element you provided
                "//psy-button[@class='ClickToEditBtn hydrated' and contains(., 'Edit')]",
                "//psy-button[@class='ClickToEditBtn hydrated']",
                # Look for psy-button with specific style attributes
                "//psy-button[contains(@style, 'position: absolute') and contains(., 'Edit')]",
                "//psy-button[contains(@style, 'top: 13px') and contains(., 'Edit')]",
                # General selectors
                "//psy-button[contains(@class, 'ClickToEditBtn') and contains(., 'Edit')]",
                "//psy-button[contains(@class, 'ClickToEditBtn')]",
                "//button[contains(text(), 'Edit')]",
                "//psy-button[contains(., 'Edit')]",
                "//button[contains(@class, 'button') and contains(., 'Edit')]"
            ]
            
            edit_button = None
            for i, selector in enumerate(edit_selectors):
                try:
                    self.uploader_log_msg(f"🔍 Trying selector {i+1}: {selector}", debug_only=True)
                    # Wait for Edit button to be present AND clickable
                    edit_button = WebDriverWait(self.tn_driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    self.uploader_log_msg(f"✅ Found Edit button with selector {i+1}", debug_only=True)
                    # Extra wait for Edit button to be fully ready
                    time.sleep(1)
                    break
                except Exception as e:
                    self.uploader_log_msg(f"❌ Selector {i+1} failed: {e}", debug_only=True)
                    continue
            
            if edit_button:
                # Debug the element properties
                try:
                    self.uploader_log_msg(f"🔍 Edit button properties:", debug_only=True)
                    self.uploader_log_msg(f"   - Is displayed: {edit_button.is_displayed()}", debug_only=True)
                    self.uploader_log_msg(f"   - Is enabled: {edit_button.is_enabled()}", debug_only=True)
                    self.uploader_log_msg(f"   - Text: '{edit_button.text}'", debug_only=True)
                    self.uploader_log_msg(f"   - Tag name: {edit_button.tag_name}", debug_only=True)
                    
                    # Try to scroll to the element first
                    self.uploader_log_msg("📜 Scrolling to Edit button...", debug_only=True)
                    self.tn_driver.execute_script("arguments[0].scrollIntoView(true);", edit_button)
                    time.sleep(0.3)  # Reduced wait time
                    
                    # Try multiple click methods
                    self.uploader_log_msg("🖱️ Attempting to click Edit button...")
                    
                    # Method 1: Regular click
                    try:
                        edit_button.click()
                        
                        # Wait for Edit mode to fully activate and check for Save button
                        save_button_found = False
                        for wait_attempt in range(5):  # Try for up to 5 seconds
                            time.sleep(1)
                            try:
                                save_check = self.tn_driver.find_element(By.XPATH, "//input[@id='CommonFooter__SaveChanges-Button']")
                                save_button_found = True
                                self.uploader_log_msg(f"✅ Successfully clicked Edit button (method 1) - Save button verified after {wait_attempt + 1}s")
                                break
                            except:
                                self.uploader_log_msg(f"⏳ Waiting for Save button... ({wait_attempt + 1}/5)", debug_only=True)
                                continue
                        
                        if save_button_found:
                            self._remove_matching_counselors()
                            return
                        else:
                            self.uploader_log_msg("❌ Edit button clicked but Save button never appeared - Edit didn't work")
                            raise Exception("Edit click failed - Save button not present")
                    except Exception as e1:
                        self.uploader_log_msg(f"❌ Method 1 failed: {e1}", debug_only=True)
                    
                    # Method 2: JavaScript click (most reliable for custom elements)
                    try:
                        self.uploader_log_msg("🖱️ Trying JavaScript click...", debug_only=True)
                        self.tn_driver.execute_script("arguments[0].click();", edit_button)
                        
                        # Wait for Edit mode to fully activate and check for Save button
                        save_button_found = False
                        for wait_attempt in range(5):  # Try for up to 5 seconds
                            time.sleep(1)
                            try:
                                save_check = self.tn_driver.find_element(By.XPATH, "//input[@id='CommonFooter__SaveChanges-Button']")
                                save_button_found = True
                                self.uploader_log_msg(f"✅ Successfully clicked Edit button (method 2) - Save button verified after {wait_attempt + 1}s")
                                break
                            except:
                                self.uploader_log_msg(f"⏳ Waiting for Save button... ({wait_attempt + 1}/5)", debug_only=True)
                                continue
                        
                        if save_button_found:
                            self._remove_matching_counselors()
                            return
                        else:
                            self.uploader_log_msg("❌ Edit button clicked but Save button never appeared - Edit didn't work")
                            raise Exception("Edit click failed - Save button not present")
                    except Exception as e2:
                        self.uploader_log_msg(f"❌ Method 2 failed: {e2}", debug_only=True)
                    
                    # Method 3: Try clicking inner button if it exists
                    try:
                        self.uploader_log_msg("🖱️ Trying to click inner button...", debug_only=True)
                        inner_button = edit_button.find_element(By.TAG_NAME, "button")
                        inner_button.click()
                        self.uploader_log_msg("✅ Successfully clicked Edit button (method 3)")
                        time.sleep(0.5)  # Reduced wait time
                        self._remove_matching_counselors()
                        return
                    except Exception as e3:
                        self.uploader_log_msg(f"❌ Method 3 failed: {e3}", debug_only=True)
                    
                    self.uploader_log_msg("❌ All click methods failed")
                    self._return_to_patients_page()
                    
                except Exception as debug_error:
                    self.uploader_log_msg(f"❌ Debug error: {debug_error}")
                    self._return_to_patients_page()
            else:
                self.uploader_log_msg("❌ Could not find Edit button with standard selectors")
                # Try fallback: look for any psy-button with Edit text
                try:
                    self.uploader_log_msg("🔍 Trying fallback: looking for any psy-button with 'Edit' text", debug_only=True)
                    all_psy_buttons = self.tn_driver.find_elements(By.XPATH, "//psy-button")
                    self.uploader_log_msg(f"🔍 Found {len(all_psy_buttons)} psy-button elements", debug_only=True)
                    
                    for i, button in enumerate(all_psy_buttons):
                        button_text = button.text.strip()
                        self.uploader_log_msg(f"🔍 psy-button {i+1}: '{button_text}'", debug_only=True)
                        if 'Edit' in button_text:
                            self.uploader_log_msg(f"✅ Found Edit button in fallback: '{button_text}'")
                            
                            # Try multiple click methods for fallback too
                            try:
                                button.click()
                                self.uploader_log_msg("✅ Clicked Edit button (fallback method 1)")
                                time.sleep(1)
                                self._remove_matching_counselors()
                                return
                            except Exception as e1:
                                self.uploader_log_msg(f"❌ Fallback method 1 failed: {e1}", debug_only=True)
                                
                                try:
                                    self.tn_driver.execute_script("arguments[0].click();", button)
                                    self.uploader_log_msg("✅ Clicked Edit button (fallback method 2)")        
                                    time.sleep(1)
                                    self._remove_matching_counselors()
                                    return
                                except Exception as e2:
                                    self.uploader_log_msg(f"❌ Fallback method 2 failed: {e2}", debug_only=True)
                    
                    self.uploader_log_msg("❌ No Edit button found in fallback search")
                except Exception as e:
                    self.uploader_log_msg(f"❌ Fallback search failed: {e}")
                
                # If still can't find edit button, return to patients page
                time.sleep(0.5)
                self._return_to_patients_page()
                
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to click Edit button: {e}")

    def _remove_matching_counselors(self):
        """Remove counselors that match the CSV data by clicking their X buttons"""
        try:
            self.uploader_log_msg("🗑️ Looking for counselor X buttons to remove...")
            self.uploader_log_msg("📋 NOTE: Will SKIP any counselors with '- IPS' suffix (they belong to IPS agency)")
            
            # Get current patient's primary workers from CSV data
            current_primary_workers = getattr(self, 'current_primary_workers', [])
            
            if not current_primary_workers:
                self.uploader_log_msg("ℹ️ No primary workers to remove for this patient")
                return
            
            # Note: Edit button should already be clicked before calling this method
            
            self.uploader_log_msg(f"🎯 Looking for counselors to remove (keeping CSV workers: {', '.join(current_primary_workers)})")
            self.uploader_log_msg(f"🔍 DEBUG: current_primary_workers type: {type(current_primary_workers)}, length: {len(current_primary_workers)}", debug_only=True)
            
            # Count how many counselors have "- IPS" suffix for logging
            ips_counselors = [worker for worker in current_primary_workers if "- IPS" in worker]
            main_counselors = [worker for worker in current_primary_workers if "- IPS" not in worker]
            
            self.uploader_log_msg(f"📊 Found {len(ips_counselors)} IPS counselors (will be skipped): {ips_counselors}")
            self.uploader_log_msg(f"📊 Found {len(main_counselors)} main agency counselors (will be removed): {main_counselors}")
            
            # Find all X buttons using the correct selector from the HTML structure
            x_buttons = self.tn_driver.find_elements(By.XPATH, "//button[@title='Remove Clinician']")
            self.uploader_log_msg(f"🔍 Found {len(x_buttons)} X buttons on page")
            
            if not x_buttons:
                # Fallback: try the span selector
                x_buttons = self.tn_driver.find_elements(By.XPATH, "//span[@class='button-text-input-mimic float-right']//button")
                self.uploader_log_msg(f"🔍 Fallback: Found {len(x_buttons)} X buttons with span selector")
            
            if not x_buttons:
                # Final fallback: try the div selector
                x_buttons = self.tn_driver.find_elements(By.XPATH, "//div[@class='fa-icon close']")
                self.uploader_log_msg(f"🔍 Final fallback: Found {len(x_buttons)} X buttons with div selector")
            
            # OPTIMIZATION: Filter out navigation elements early to improve performance
            filtered_x_buttons = []
            for x_btn in x_buttons:
                try:
                    parent = x_btn.find_element(By.XPATH, "./..")
                    parent_text = parent.text.strip().lower()
                    
                    # Skip if this is clearly a navigation element
                    if any(nav_word in parent_text for nav_word in ['user options', 'contact us', 'log out', 'no future appt', 'home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none']):
                        self.uploader_log_msg(f"⏭️ Skipping navigation element: '{parent_text[:50]}...'")
                        continue
                    
                    # Check if this looks like a real counselor name
                    if (len(parent_text.split()) >= 2 and 
                        all(word[0].isupper() for word in parent_text.split() if word) and
                        not any(ui_word in parent_text for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                        filtered_x_buttons.append(x_btn)
                    else:
                        self.uploader_log_msg(f"⏭️ Skipping non-counselor element: '{parent_text[:50]}...'")
                except:
                    # If we can't determine what it is, include it to be safe
                    filtered_x_buttons.append(x_btn)
            
            x_buttons = filtered_x_buttons
            self.uploader_log_msg(f"🔍 Filtered to {len(x_buttons)} potential counselor X buttons")
            
            # Also find all counselor names on the page for debugging
            try:
                all_text_elements = self.tn_driver.find_elements(By.XPATH, "//*[contains(@class, 'counselor') or contains(text(), 'Counselor') or contains(text(), 'Therapist')]")
                self.uploader_log_msg(f"🔍 DEBUG: Found {len(all_text_elements)} potential counselor elements", debug_only=True)
                for i, elem in enumerate(all_text_elements[:5]):  # Show first 5
                    self.uploader_log_msg(f"🔍 DEBUG: Element {i+1}: '{elem.text.strip()}'", debug_only=True)
            except Exception as debug_e:
                self.uploader_log_msg(f"🔍 DEBUG: Error finding counselor elements: {debug_e}", debug_only=True)
            
            # CRITICAL: Wait for counselors to actually appear before trying to remove them
            # This ensures we don't skip clients due to timing issues
            self.uploader_log_msg("⏳ Waiting for all counselor X buttons to appear on screen...")
            max_wait_time = 20  # Maximum 20 seconds wait for X buttons to appear
            wait_interval = 0.5
            elapsed_time = 0
            x_buttons_ready = False
            
            while elapsed_time < max_wait_time and not x_buttons_ready:
                # Check if X buttons are present
                try:
                    x_buttons_check = self.tn_driver.find_elements(By.XPATH, "//button[@title='Remove Clinician']")
                    if not x_buttons_check:
                        x_buttons_check = self.tn_driver.find_elements(By.XPATH, "//span[@class='button-text-input-mimic float-right']//button")
                    if not x_buttons_check:
                        x_buttons_check = self.tn_driver.find_elements(By.XPATH, "//div[@class='fa-icon close']")
                    
                    if x_buttons_check:
                        # Verify at least one X button is actually visible (not just in DOM)
                        visible_count = sum(1 for btn in x_buttons_check if btn.is_displayed())
                        if visible_count > 0:
                            self.uploader_log_msg(f"✅ Found {visible_count} visible counselor X button(s) - ready to process!")
                            x_buttons_ready = True
                            break
                except Exception:
                    pass
                
                time.sleep(wait_interval)
                elapsed_time += wait_interval
            
            if not x_buttons_ready:
                self.uploader_log_msg(f"⚠️ Timeout after {max_wait_time}s - X buttons may not be visible yet")
                self.uploader_log_msg("   Proceeding anyway to check for counselors...")
            
            removed_count = 0
            max_attempts = 3  # Reduced from 10 to 3 to prevent excessive attempts
            attempt = 0

            # Keep processing X buttons until no more are found or max attempts reached
            while attempt < max_attempts:
                attempt += 1
                self.uploader_log_msg(f"🔄 Attempt {attempt}: Looking for X buttons...")

                # Re-find all X buttons using the correct selector from the HTML structure
                x_buttons = self.tn_driver.find_elements(By.XPATH, "//button[@title='Remove Clinician']")
                if not x_buttons:
                    # Fallback: try the span selector
                    x_buttons = self.tn_driver.find_elements(By.XPATH, "//span[@class='button-text-input-mimic float-right']//button")
                if not x_buttons:
                    # Final fallback: try the div selector
                    x_buttons = self.tn_driver.find_elements(By.XPATH, "//div[@class='fa-icon close']")
                self.uploader_log_msg(f"🔍 Found {len(x_buttons)} X buttons on page")
                
                # Debug: Log all X button locations and their context
                for i, x_btn in enumerate(x_buttons):
                    try:
                        parent = x_btn.find_element(By.XPATH, "./..")
                        parent_text = parent.text.strip()[:100]  # First 100 chars
                        self.uploader_log_msg(f"🔍 X Button {i+1}: Parent text: '{parent_text}...'")
                        
                        # Try to find the counselor name for this X button
                        try:
                            # Get the grandparent element (clinician-assignment div)
                            grandparent = parent.find_element(By.XPATH, "./..")
                            staff_link = grandparent.find_element(By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]")
                            counselor_name = staff_link.text.strip()
                            self.uploader_log_msg(f"🔍 X Button {i+1}: Associated counselor: '{counselor_name}'")
                        except:
                            self.uploader_log_msg(f"🔍 X Button {i+1}: Could not find associated counselor")
                    except:
                        self.uploader_log_msg(f"🔍 X Button {i+1}: Could not get parent text")

                if not x_buttons:
                    self.uploader_log_msg("✅ No more X buttons found - finished processing")
                    break
                
                # SAFE OPTIMIZATION: Early exit if we've processed the same X button multiple times
                # This prevents infinite loops when only navigation elements remain
                if attempt >= 2:  # After 2 attempts, check if we're stuck (reduced from 4)
                    # Count how many X buttons have real counselor names vs navigation elements
                    real_counselor_buttons = 0
                    navigation_buttons = 0
                    
                    for x_btn in x_buttons:
                        try:
                            parent = x_btn.find_element(By.XPATH, "./..")
                            grandparent = parent.find_element(By.XPATH, "./..")
                            staff_link = grandparent.find_element(By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]")
                            counselor_name = staff_link.text.strip()
                            
                            # Check if this looks like a real counselor name (not navigation)
                            if (counselor_name and 
                                len(counselor_name.split()) >= 2 and 
                                not any(nav_word in counselor_name.lower() for nav_word in ['user options', 'contact us', 'log out', 'no future appt'])):
                                real_counselor_buttons += 1
                            else:
                                navigation_buttons += 1
                        except:
                            navigation_buttons += 1
                    
                    # If we only have navigation elements left, exit early
                    if real_counselor_buttons == 0 and navigation_buttons > 0:
                        self.uploader_log_msg("✅ Only navigation elements remaining - exiting early to save time")
                        break
                

                # Process ALL X buttons until we find one to remove
                for x_button in x_buttons:
                    
                    try:
                        parent_element = x_button.find_element(By.XPATH, "./..")
                        grandparent_element = parent_element.find_element(By.XPATH, "./..")
                        counselor_text = ""

                        try:
                            staff_link = grandparent_element.find_element(
                                By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]"
                            )
                            counselor_text = staff_link.text.strip()
                            self.uploader_log_msg(f"🔍 DEBUG: Found counselor via grandparent: '{counselor_text}'")
                        except Exception:
                            try:
                                staff_link = parent_element.find_element(
                                    By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]"
                                )
                                counselor_text = staff_link.text.strip()
                                self.uploader_log_msg(f"🔍 DEBUG: Found counselor via parent: '{counselor_text}'")
                            except Exception:
                                self.uploader_log_msg("🔍 DEBUG: No staff link found in parent or grandparent")

                    except Exception as e:
                        self.uploader_log_msg(f"❌ Error processing x_button: {e}")
                        continue
    
                        # Try to find staff link in a broader context around the X button
                        try:
                            # Look for staff links in the same row/container as the X button
                            # First, find the row/container that contains the X button
                            row_element = x_button
                            for _ in range(3):  # Go up 3 levels to find the row
                                try:
                                    row_element = row_element.find_element(By.XPATH, "./..")
                                    # Check if this row contains a staff link
                                    staff_links_in_row = row_element.find_elements(By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]")
                                    if staff_links_in_row:
                                        counselor_text = staff_links_in_row[0].text.strip()
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name via row staff link: '{counselor_text}'")
                                        break
                                except:
                                    continue
                        except Exception as e2:
                            self.uploader_log_msg(f"🔍 DEBUG: No staff link found in row context: {e2}")
                    
                    # Method 2: If no staff link found, look in the entire row/container
                    if not counselor_text:
                        try:
                            # Look for any <a> tag with staff edit link in the broader context
                            staff_links = self.tn_driver.find_elements(By.XPATH, "//a[contains(@href, '/app/staff/edit/')]")
                            self.uploader_log_msg(f"🔍 DEBUG: Found {len(staff_links)} staff links on page")
                            
                            # Find the one closest to this X button by checking if they're in the same container
                            for link in staff_links:
                                try:
                                    # Check if this link is in the same container as our X button
                                    # Look for a common ancestor that contains both elements
                                    link_text = link.text.strip()
                                    if link_text and len(link_text) > 2:  # Valid name
                                        # Check if they share a common container
                                        link_ancestors = set()
                                        current = link
                                        for _ in range(5):  # Check up to 5 levels up
                                            try:
                                                current = current.find_element(By.XPATH, "./..")
                                                link_ancestors.add(current)
                                            except:
                                                break
                                        
                                        x_ancestors = set()
                                        current = x_button
                                        for _ in range(5):  # Check up to 5 levels up
                                            try:
                                                current = current.find_element(By.XPATH, "./..")
                                                x_ancestors.add(current)
                                            except:
                                                break
                                        
                                        # If they share any ancestor, they're likely in the same row
                                        if link_ancestors & x_ancestors:
                                            counselor_text = link_text
                                            self.uploader_log_msg(f"🔍 DEBUG: Found counselor name via nearby staff link: '{counselor_text}'")
                                            break
                                except:
                                    continue
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error finding staff links: {e}")
                    
                    # Method 3: Fallback - look for text that's not navigation/UI elements
                    if not counselor_text:
                        try:
                            # Get all text nodes in the parent element
                            all_text = parent_element.text.strip()
                            self.uploader_log_msg(f"🔍 DEBUG: Full parent text: '{all_text[:200]}...'")
                            
                            # Look for text that looks like a name (contains letters, not just UI elements)
                            text_parts = all_text.split('\n')
                            for part in text_parts:
                                part = part.strip()
                                # Skip common UI elements and look for name-like text
                                if (part and 
                                    not part.startswith('Home') and 
                                    not part.startswith('To-Do') and 
                                    not part.startswith('Scheduling') and
                                    not part.startswith('Patients') and
                                    not part.startswith('Staff') and
                                    not part.startswith('Contacts') and
                                    not part.startswith('Billing') and
                                    not part.startswith('Payers') and
                                    not part.startswith('Library') and
                                    not part.startswith('User Options') and
                                    not part.startswith('Profile') and
                                    not part.startswith('Settings') and
                                    not part.startswith('Help') and
                                    not part.startswith('Contact Us') and
                                    not part.startswith('Status') and
                                    not part.startswith('Referrals') and
                                    not part.startswith('Log Out') and
                                    not part.startswith('No Future Appt') and
                                    not part.startswith('Mobile:') and
                                    not part.startswith('Patient:') and
                                    not part.startswith('Info') and
                                    not part.startswith('Schedule') and
                                    not part.startswith('Documents') and
                                    not part.startswith('Billing Settings') and
                                    not part.startswith('Clinicians') and
                                    not part.startswith('Portal') and
                                    not part.startswith('Insights') and
                                    not part.startswith('Warning') and
                                    not part.startswith('Error') and
                                    not part.startswith('Edit') and
                                    not part.startswith('Assigned Clinicians') and
                                    not part.startswith('Supervisors') and
                                    not part.startswith('These users supervise') and
                                    not part.startswith('Supervisor Supervisee') and
                                    not part.startswith('×') and  # X symbol
                                    not part.startswith('Close') and
                                    not part.startswith('Remove') and
                                    not part.startswith('Delete') and
                                    not part.startswith('Save') and
                                    not part.startswith('Cancel') and
                                    len(part) > 2 and  # Must be at least 3 characters
                                    any(c.isalpha() for c in part)):  # Must contain letters
                                    counselor_text = part
                                    self.uploader_log_msg(f"🔍 DEBUG: Found potential counselor name via text parsing: '{counselor_text}'")
                                    break
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in text parsing fallback: {e}")
                    
                    # Method 3.5: Look for counselor names in the broader page context
                    if not counselor_text:
                        try:
                            # Look for any text that appears to be a counselor name near the X button
                            # Get all text elements on the page and find ones that look like names
                            all_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()]")
                            potential_names = []
                            
                            for elem in all_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        potential_names.append(text)
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                            self.uploader_log_msg(f"🔍 DEBUG: Found {len(potential_names)} potential counselor names on page: {potential_names[:5]}")
                            
                            # If we found potential names, use the first one that's not already processed
                            if potential_names:
                                counselor_text = potential_names[0]
                                self.uploader_log_msg(f"🔍 DEBUG: Using first potential counselor name: '{counselor_text}'")
                                
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in broader context search: {e}")
                    
                    # OPTIMIZATION: Removed excessive fallback methods 3.6-3.20 to improve performance
                    # The essential methods 3.1-3.5 are sufficient for counselor name detection
                    
                    # OPTIMIZATION: Removed excessive fallback methods 3.7-3.20 to improve performance
                    # OPTIMIZATION: Removed all excessive fallback methods to improve performance
                    
                    if not counselor_text:
                        counselor_text = "Unknown Counselor"
                    
                    # Simplified counselor name extraction - removed excessive fallback methods
                    
                    self.uploader_log_msg(f"🔍 Checking X button: '{counselor_text}'")
                    
                    # CRITICAL SAFETY CHECK: If we can't extract a real counselor name, SKIP this X button
                    if counselor_text == "Unknown Counselor":
                        self.uploader_log_msg(f"⚠️ SAFETY: Skipping X button - could not extract counselor name safely")
                        break
                    
                    # Check if this counselor IS in our CSV data (we want to remove CSV counselors)
                    should_remove = False
                    matched_worker = None
                    
                    # CRITICAL FIX: Use STRICT matching to avoid removing wrong counselors
                    counselor_normalized = counselor_text.lower().strip()
                    
                    for primary_worker in current_primary_workers:
                        worker_normalized = primary_worker.lower().strip()
                        
                        # Extract name components (remove punctuation for comparison)
                        counselor_clean = counselor_normalized.replace(",", "").replace("-", " ").strip()
                        worker_clean = worker_normalized.replace(",", "").replace("-", " ").strip()
                        
                        # Split into words for STRICT comparison
                        counselor_words = set(counselor_clean.split())
                        worker_words = set(worker_clean.split())
                        
                        # Remove generic words that might cause false matches
                        ignore_words = {'ips', 'counselor', 'therapist', 'worker', 'staff'}
                        counselor_words = {w for w in counselor_words if w not in ignore_words}
                        worker_words = {w for w in worker_words if w not in ignore_words}
                        
                        # STRICT MATCH: ALL words must match (prevents "Hernandez Cynthia" from matching "Hernandez Maria")
                        if counselor_words == worker_words and len(worker_words) >= 2:
                            matched_worker = primary_worker
                            self.uploader_log_msg(f"✅ EXACT MATCH: '{counselor_text}' matches CSV '{primary_worker}'")
                            break
                        
                        # Also check for "Last, First" vs "First Last" format with FULL name match
                        if ',' in worker_normalized:
                            parts = worker_normalized.split(',')
                            if len(parts) == 2:
                                last_name = parts[0].strip()
                                first_name = parts[1].strip()
                                reversed_format = f"{first_name} {last_name}"
                                reversed_words = set(reversed_format.split())
                                
                                # STRICT MATCH: All words must match exactly
                                if reversed_words == counselor_words:
                                    matched_worker = primary_worker
                                    self.uploader_log_msg(f"✅ EXACT MATCH (reversed): '{counselor_text}' matches CSV '{primary_worker}'")
                                    break
                    
                    # If we found a match, we SHOULD remove this counselor (it's in our CSV for removal)
                    # If we found NO match, we should NOT remove this counselor (it's not on our CSV)
                    if matched_worker:
                        # NEW LOGIC: Check if this counselor has "- IPS" after their name
                        # If they do, skip them (they belong to IPS agency, not main agency)
                        if "- IPS" in matched_worker:
                            should_remove = False
                            self.uploader_log_msg(f"🚫 SKIPPING IPS COUNSELOR: '{counselor_text}' matches CSV worker '{matched_worker}' but has '- IPS' - belongs to IPS agency, NOT removing")
                        else:
                            should_remove = True
                            self.uploader_log_msg(f"🗑️ REMOVING: '{counselor_text}' matches CSV worker '{matched_worker}' (no '- IPS') - clicking X")
                    else:
                        self.uploader_log_msg(f"✅ KEEPING: '{counselor_text}' is NOT in CSV - NOT removing")
                    
                    if should_remove:
                        x_button.click()
                        removed_count += 1
                        time.sleep(0.2)  # Reduced wait time
                        self.uploader_log_msg(f"🗑️ Removed counselor: {counselor_text}")
                        # After removing, break out of the for loop to re-find X buttons
                        break
                    else:
                        # Continue to next X button
                        continue

            # After the while loop, save changes if any were made
            if removed_count > 0:
                self.uploader_log_msg(f"✅ Successfully removed {removed_count} counselor(s) from main agency (skipped any '- IPS' counselors)")
                # Save changes (click Save button)
                self._save_counselor_changes()
            else:
                self.uploader_log_msg("ℹ️ No main agency counselors found to remove (all counselors either not in CSV or have '- IPS' suffix)")
                # Still need to save (even if no changes) to exit edit mode
                self.uploader_log_msg("💾 Saving to exit edit mode...")
                self._save_counselor_changes()
                
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to remove counselors: {e}")
            # Ensure we still save changes even if there was an error
            try:
                self._save_counselor_changes()
            except:
                pass

    def _save_counselor_changes(self):
        """Save the counselor removal changes"""
        try:
            self.uploader_log_msg("💾 Looking for Save Changes button...")
            
            # Find Save Changes button using multiple selectors
            save_selectors = [
                "//input[@id='CommonFooter__SaveChanges-Button']",
                "//input[@name='CommonFooter__SaveChanges-Button']",
                "//input[@value='Save Changes']",
                "//button[contains(text(), 'Save Changes')]",
                "//input[@type='button' and contains(@value, 'Save Changes')]"
            ]
            
            save_button = None
            for selector in save_selectors:
                try:
                    save_button = self.tn_driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue
            
            if save_button:
                save_button.click()
                self.uploader_log_msg("✅ Clicked Save Changes button")
                time.sleep(1.0)  # Reduced wait time for save to complete
                self.uploader_log_msg("✅ Successfully saved counselor changes")
            else:
                self.uploader_log_msg("❌ Could not find Save Changes button")
            
            # CRITICAL: ALWAYS return to Patients page, even if Save failed
            # This ensures we're ready for the next patient search
            time.sleep(0.2)  # Reduced wait time
            self._return_to_patients_page()
                
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to save changes: {e}")
            # Still try to return to Patients page even on error
            try:
                self._return_to_patients_page()
            except:
                pass

    def _return_to_patients_page(self):
        """Return to the Patients page to process the next patient - OPTIMIZED"""
        try:
            self.uploader_log_msg("🔄 Returning to Patients page...")
            
            # CRITICAL: Close any modal dialogs before attempting navigation
            # This prevents dialogs from blocking the Patients button click
            try:
                body = self.tn_driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                self.uploader_log_msg("🔧 Sent ESC key to close any dialogs")
                time.sleep(0.3)  # Brief wait for dialog to close
            except:
                pass  # Continue even if ESC fails
            
            # Find and click the Patients button
            patients_selectors = [
                "//span[text()='Patients']",
                "//a[contains(text(), 'Patients')]",
                "//button[contains(text(), 'Patients')]"
            ]
            
            patients_button = None
            for selector in patients_selectors:
                try:
                    patients_button = self.tn_driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue
            
            if patients_button:
                # Try regular click first, fallback to JavaScript
                try:
                    patients_button.click()
                    self.uploader_log_msg("✅ Clicked Patients button")
                except:
                    self.tn_driver.execute_script("arguments[0].click();", patients_button)
                    self.uploader_log_msg("✅ Clicked Patients button (JavaScript)")
                
                # Wait for search bar to appear - reduced wait time
                # CRITICAL: Check for the same search field ID that _search_patient() uses
                for wait_attempt in range(3):  # Reduced from 5 to 3
                    time.sleep(0.5)  # Reduced from 1s to 0.5s
                    try:
                        # Check for the search field that _search_patient() actually uses
                        search_bar = self.tn_driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
                        self.uploader_log_msg("✅ Successfully returned to Patients page")
                        return  # Success!
                    except:
                        continue
                
                # If search bar not found, try one more time with longer wait
                time.sleep(1)
                try:
                    # Check for the search field that _search_patient() actually uses
                    search_bar = self.tn_driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
                    self.uploader_log_msg("✅ Successfully returned to Patients page (delayed)")
                    return
                except:
                    self.uploader_log_msg("⚠️ Search bar not found - continuing anyway")
                    return  # Continue processing even if search bar not found
            else:
                self.uploader_log_msg("❌ Could not find Patients button")
                
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to return to Patients page: {e}")
            # Continue processing even if this fails

    def _create_results_csv(self, results, original_csv_file):
        """Create a results CSV with success/failure tracking"""
        try:
            import os
            from datetime import datetime
            
            # Create results filename based on original CSV
            base_name = os.path.splitext(os.path.basename(original_csv_file))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_filename = f"{base_name}_results_{timestamp}.csv"
            
            # Use selected output location if specified, otherwise use CSV file directory
            output_location = self.output_location_var.get().strip()
            if output_location and os.path.isdir(output_location):
                results_dir = output_location
            else:
                results_dir = os.path.dirname(original_csv_file)
            
            results_path = os.path.join(results_dir, results_filename)
            
            # Create results DataFrame
            import pandas as pd
            results_df = pd.DataFrame(results)
            
            # Save results CSV
            results_df.to_csv(results_path, index=False)
            
            # Count successes and failures
            success_count = len(results_df[results_df['Process Status'] == 'SUCCESS'])
            failure_count = len(results_df[results_df['Process Status'] == 'FAILED'])
            
            self.uploader_log_msg(f"📊 Results CSV created: {results_path}")
            self.uploader_log_msg(f"✅ Successfully processed: {success_count} patients")
            self.uploader_log_msg(f"❌ Failed to process: {failure_count} patients")
            
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to create results CSV: {e}")

    def _click_upload_patient_file_button(self):
        """Click the Upload Patient File button"""
        try:
            self.uploader_log_msg("📤 Looking for Upload Patient File button...")
            
            # Find the Upload Patient File button using multiple selectors
            upload_selectors = [
                "//button[contains(., 'Upload Patient File')]",
                "//button[.//span[@class='fa-icon upload']]",
                "//button[contains(@style, 'height: 30px') and contains(., 'Upload Patient File')]",
                "//button[.//span[contains(@class, 'upload')]]"
            ]
            
            upload_button = None
            for selector in upload_selectors:
                try:
                    upload_button = self.tn_driver.find_element(By.XPATH, selector)
                    self.uploader_log_msg(f"✅ Found Upload button with selector: {selector}")
                    break
                except:
                    continue
            
            if upload_button:
                # Scroll to button if needed
                self.tn_driver.execute_script("arguments[0].scrollIntoView(true);", upload_button)
                time.sleep(0.2)  # Reduced wait time
                
                # Click the button
                upload_button.click()
                self.uploader_log_msg("✅ Successfully clicked Upload Patient File button")
                time.sleep(0.5)  # Reduced wait time for upload dialog/modal to appear
                
            else:
                self.uploader_log_msg("❌ Could not find Upload Patient File button with any selector")
                
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to click Upload Patient File button: {e}")

    def _view_upload_log(self):
        """View upload log in a popup window"""
        try:
            # Create a new window to display the log
            log_window = tk.Toplevel(self.root)
            log_window.title("Upload Log")
            log_window.geometry("800x600")
            log_window.configure(bg="#f0f0f0")
            
            # Create a frame for the log content
            log_frame = tk.Frame(log_window, bg="#f0f0f0")
            log_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Add a title
            title_label = tk.Label(log_frame, text="Upload Log", 
                                 font=("Segoe UI", 16, "bold"), bg="#f0f0f0")
            title_label.pack(pady=(0, 10))
            
            # Create a text widget with scrollbar for the log
            text_frame = tk.Frame(log_frame, bg="#f0f0f0")
            text_frame.pack(fill="both", expand=True)
            
            log_text = tk.Text(text_frame, wrap="word", font=("Consolas", 10), 
                             bg="white", fg="black", padx=10, pady=10)
            scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=log_text.yview)
            log_text.configure(yscrollcommand=scrollbar.set)
            
            # Pack the text widget and scrollbar
            log_text.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Get the log content
            log_content = self.uploader_log.get("1.0", tk.END)
            
            # Insert the log content
            log_text.insert("1.0", log_content)
            log_text.config(state="disabled")  # Make it read-only
            
            # Add a close button
            close_button = ttk.Button(log_frame, text="Close", 
                                    command=log_window.destroy)
            close_button.pack(pady=(10, 0))
            
            # Scroll to the bottom to show the latest entries
            log_text.see(tk.END)
            
        except Exception as e:
            # If there's an error, show it in a simple message box
            import tkinter.messagebox as msgbox
            msgbox.showerror("Error", f"Could not display log: {e}")

    def uploader_log_msg(self, msg: str, debug_only: bool = False):
        """Log message to uploader log"""
        # Check if this is a debug message and debug mode is off
        if debug_only and not getattr(self, 'debug_mode_var', tk.BooleanVar()).get():
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = "[DEBUG]" if debug_only else ""
        self.uploader_log.insert("end", f"[{timestamp}] {prefix} {msg}\n")
        self.uploader_log.see("end")
        self.update_idletasks()

    def log_msg(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.insert("end", f"[{timestamp}] {msg}\n")
        self.log.see("end")
        self.update_idletasks()

    def update_status(self, status: str):
        self.status_label.config(text=status)
        self.update_idletasks()

    def update_data_count(self):
        count = len(self.state.extracted_data)
        self.data_count_label.config(text=f"Data: {count} records")
        self.update_idletasks()

    def _stop_bot(self):
        """Immediately stop all bot operations"""
        self.state.stop_requested = True
        self.log_msg("[STOP] 🛑 STOP REQUESTED - Halting all operations...")
        self.update_status("STOPPED")
        
        # Try to close the browser if it's open
        try:
            if self.state.driver:
                self.state.driver.quit()
                self.state.driver = None
                self.log_msg("[STOP] Browser closed")
        except Exception as e:
            self.log_msg(f"[STOP] Error closing browser: {e}")
        
        # Reset the stop flag after a delay using a separate method
        threading.Thread(target=self._reset_stop_flag, daemon=True).start()

    def _reset_stop_flag(self):
        """Reset the stop flag after a delay"""
        time.sleep(2)
        self.state.stop_requested = False
        self.log_msg("[STOP] Ready for new operations")
        self.update_status("Ready")

    def _clear_data(self):
        """Clear all extracted data"""
        self.state.extracted_data.clear()
        self.update_data_count()
        self.log_msg("[DATA] Cleared all extracted data")

    def _parse_workflow_date(self, date_text):
        """Parse workflow date, handling relative dates like 'Today', 'Tomorrow', etc."""
        try:
            # First try the standard format
            return datetime.strptime(date_text, DATE_FMT)
        except ValueError:
            # Handle relative dates
            date_text_lower = date_text.lower().strip()
            today = datetime.now().date()
            
            if date_text_lower == 'today':
                return datetime.combine(today, datetime.min.time())
            elif date_text_lower == 'tomorrow':
                tomorrow = today + timedelta(days=1)
                return datetime.combine(tomorrow, datetime.min.time())
            elif date_text_lower == 'yesterday':
                yesterday = today - timedelta(days=1)
                return datetime.combine(yesterday, datetime.min.time())
            elif 'days ago' in date_text_lower:
                # Handle "X days ago" format
                try:
                    days = int(date_text_lower.split()[0])
                    past_date = today - timedelta(days=days)
                    return datetime.combine(past_date, datetime.min.time())
                except (ValueError, IndexError):
                    pass
            elif 'days from now' in date_text_lower or 'days later' in date_text_lower:
                # Handle "X days from now" format
                try:
                    days = int(date_text_lower.split()[0])
                    future_date = today + timedelta(days=days)
                    return datetime.combine(future_date, datetime.min.time())
                except (ValueError, IndexError):
                    pass
            
            # If we can't parse it, return None
            return None
        except Exception:
            return None

    # ---------- Enhanced Selenium helpers ----------
    def _drv(self):
        if self.state.driver is None:
            try:
                opts = ChromeOptions()
                opts.add_argument("--start-maximized")
                opts.add_argument("--disable-gpu")
                opts.add_argument("--no-sandbox")
                opts.add_argument("--disable-dev-shm-usage")
                opts.add_argument("--disable-blink-features=AutomationControlled")
                opts.add_experimental_option("excludeSwitches", ["enable-automation"])
                opts.add_experimental_option('useAutomationExtension', False)
                
                # Try to install and use ChromeDriver with better error handling
                try:
                    driver_path = ChromeDriverManager().install()
                    svc = ChromeService(driver_path)
                    self.state.driver = webdriver.Chrome(service=svc, options=opts)
                except Exception as e:
                    self.log_msg(f"[DEBUG] ChromeDriverManager failed: {e}")
                    # Fallback: try without explicit service
                    self.state.driver = webdriver.Chrome(options=opts)
                
                self.state.driver.set_page_load_timeout(90)
                self.state.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
            except Exception as e:
                self.log_msg(f"[ERR] Failed to initialize Chrome driver: {e}")
                raise
        return self.state.driver

    def _find_element_with_fallbacks(self, selectors, timeout=5):
        """Try multiple selectors until one works"""
        drv = self._drv()
        
        for i, (by, value) in enumerate(selectors):
            try:
                if self.debug_var.get():
                    self.log_msg(f"[DEBUG] Trying selector {i+1}/{len(selectors)}: {by}={value}")
                element = WebDriverWait(drv, timeout).until(EC.visibility_of_element_located((by, value)))
                if self.debug_var.get():
                    self.log_msg(f"[DEBUG] Found element with selector {i+1}: {by}={value}")
                return element
            except TimeoutException:
                if self.debug_var.get():
                    self.log_msg(f"[DEBUG] Selector {i+1} failed: {by}={value}")
                continue
        raise TimeoutException(f"Could not find element with any of {len(selectors)} selectors")

    def _wait_visible(self, locator, timeout=25):
        """Enhanced wait with fallback selectors"""
        if isinstance(locator, tuple):
            # Single selector
            drv = self._drv()
            return WebDriverWait(drv, timeout).until(EC.visibility_of_element_located(locator))
        else:
            # Multiple selectors
            return self._find_element_with_fallbacks(locator, timeout)

    def _safe_click(self, element, timeout=10):
        """Safely click an element with multiple strategies"""
        try:
            # Try normal click first
            element.click()
            return True
        except (ElementClickInterceptedException, ElementNotInteractableException):
            try:
                # Try JavaScript click
                self.state.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                try:
                    # Try ActionChains click
                    ActionChains(self.state.driver).move_to_element(element).click().perform()
                    return True
                except Exception as e:
                    self.log_msg(f"[WARN] All click methods failed: {e}")
                    return False
        except Exception as e:
            self.log_msg(f"[WARN] Click failed: {e}")
            return False

    # ---------- Actions ----------
    def _login(self):
        def run():
            try:
                drv = self._drv()
                self.log_msg("[NAV] Opening login page…")
                drv.get(LOGIN_URL)
                
                if self.debug_var.get():
                    self.log_msg("[DEBUG] Page loaded, looking for username field...")
                
                u = self._wait_visible(SEL["user"], 30)
                if self.debug_var.get():
                    self.log_msg("[DEBUG] Username field found")
                
                u.clear(); u.send_keys(self.e_user.get())
                if self.debug_var.get():
                    self.log_msg("[DEBUG] Username entered")
                
                p = self._wait_visible(SEL["pass"], 30)
                if self.debug_var.get():
                    self.log_msg("[DEBUG] Password field found")
                
                p.clear(); p.send_keys(self.e_pass.get())
                if self.debug_var.get():
                    self.log_msg("[DEBUG] Password entered")
                
                login_btn = self._wait_visible(SEL["login_btn"], 15)
                if self.debug_var.get():
                    self.log_msg("[DEBUG] Login button found, clicking...")
                
                login_btn.click()
                if self.debug_var.get():
                    self.log_msg("[DEBUG] Login button clicked, waiting for redirect...")
                
                self._wait_visible(SEL["workflow_handle"], 40)
                self.log_msg("[OK] Login successful.")
                self.update_status("Logged In")
            except Exception as e:
                self.log_msg(f"[ERR] Login failed: {e}")
                if self.debug_var.get():
                    import traceback
                    self.log_msg(f"[DEBUG] Full error: {traceback.format_exc()}")
        threading.Thread(target=run, daemon=True).start()

    def _open_workflow(self):
        def run():
            try:
                handle = self._wait_visible(SEL["workflow_handle"], 20)
                if self._safe_click(handle):
                    self.log_msg("[WF] Workflow handle clicked")
                else:
                    self.log_msg("[ERR] Failed to click workflow handle")
                    return
                
                self._wait_visible(SEL["drawer_panel_task"], 25)
                time.sleep(0.5)  # Give it time to fully open
                self.log_msg("[WF] Drawer opened successfully")
                self.update_status("Workflow Drawer Open")
            except Exception as e:
                self.log_msg(f"[ERR] Workflow drawer failed: {e}")
                if self.debug_var.get():
                    import traceback
                    self.log_msg(f"[DEBUG] Traceback: {traceback.format_exc()}")
        threading.Thread(target=run, daemon=True).start()

    def _open_advanced(self):
        def run():
            try:
                # Refresh the page and reopen drawer to make Advanced tab visible
                self.log_msg("[ADV] Refreshing page to restore Advanced tab visibility...")
                self.state.driver.refresh()
                time.sleep(3)  # Wait for page to fully reload
                
                # Reopen the workflow drawer
                self.log_msg("[ADV] Reopening workflow drawer...")
                handle = self._wait_visible(SEL["workflow_handle"], 20)
                if self._safe_click(handle):
                    self.log_msg("[ADV] Workflow handle clicked")
                else:
                    self.log_msg("[ERR] Failed to click workflow handle")
                    return
                
                self._wait_visible(SEL["drawer_panel_task"], 25)
                time.sleep(0.5)  # Give it time to fully open
                self.log_msg("[ADV] Workflow drawer reopened")
                
                # Now click the Advanced tab
                self.log_msg("[ADV] Clicking Advanced tab...")
                tab = self._wait_visible(SEL["tab_advanced"], 10)
                if self._safe_click(tab):
                    self.log_msg("[ADV] Advanced tab clicked")
                else:
                    self.log_msg("[ERR] Failed to click Advanced tab")
                    return
                
                # Wait for the Advanced search fields to appear
                self.log_msg("[ADV] Waiting for Advanced search fields...")
                self._wait_visible(SEL["adv_from"], 20)
                self._wait_visible(SEL["adv_to"], 20)
                self.log_msg("[ADV] Advanced search opened successfully")
                self.update_status("Advanced Search Open")
                
            except Exception as e:
                self.log_msg(f"[ERR] Advanced open failed: {e}")
                if self.debug_var.get():
                    import traceback
                    self.log_msg(f"[DEBUG] Traceback: {traceback.format_exc()}")
        threading.Thread(target=run, daemon=True).start()

    def _fill_next_chunk(self):
        def run():
            try:
                if not self.state.chunks:
                    self.log_msg("[ADV] No chunks in memory; build chunks first")
                    return
                if self.state.next_chunk_index >= len(self.state.chunks):
                    self.log_msg("[ADV] All chunks already filled")
                    return
                
                a, b = self.state.chunks[self.state.next_chunk_index]
                frm = self._wait_visible(SEL["adv_from"], 10)
                to = self._wait_visible(SEL["adv_to"], 10)
                
                frm.clear()
                frm.send_keys(a)
                to.clear()
                to.send_keys(b)
                
                self.state.next_chunk_index += 1
                self.log_msg(f"[ADV] Set From={a} To={b}")
            except Exception as e:
                self.log_msg(f"[ERR] Fill Next Chunk failed: {e}")
                if self.debug_var.get():
                    import traceback
                    self.log_msg(f"[DEBUG] Traceback: {traceback.format_exc()}")
        threading.Thread(target=run, daemon=True).start()

    def _expand_current_safe(self):
        """Expand Current tasks and build date chunks for advanced search"""
        def run():
            try:
                # Check for stop request at the start
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled by user")
                    return
                
                title = self.e_match.get().strip().lower()
                self.log_msg(f"[CURRENT] Starting safe expansion for: '{title}'")
                
                # Expand the current tasks
                self._expand_sync("current", verbose=True)
                
                # Check for stop request after expansion
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled by user")
                    return
                
                # Get all rows and find matching workflows
                body = self._wait_visible(SEL["current_body"], 10)
                rows = [r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()]
                
                if not rows:
                    self.log_msg("[CURRENT] No rows visible in current tasks")
                    return
                
                self.log_msg(f"[CURRENT] Found {len(rows)} rows to check")
                
                # Find matching workflows and collect their dates
                matching_dates = []
                for i, r in enumerate(rows):
                    # Check for stop request before each row
                    if self.state.stop_requested:
                        self.log_msg(f"[STOP] Operation cancelled at row {i+1}")
                        return
                    
                    try:
                        # Look for the link directly in the first cell of each row
                        first_cell = r.find_element(By.CSS_SELECTOR, "td:first-child")
                        link = first_cell.find_element(By.CSS_SELECTOR, "a")
                        subj = link.text.strip().lower()
                        
                        if subj == title:
                            # Look for date in the third cell
                            date_cell = r.find_element(By.CSS_SELECTOR, "td:nth-child(3)")
                            d_txt = date_cell.text.strip()
                            try:
                                # Handle relative dates like "Today", "Tomorrow", etc.
                                d = self._parse_workflow_date(d_txt)
                                if d:
                                    matching_dates.append(d)
                                    self.log_msg(f"[CURRENT] Row {i+1}: Found matching workflow with date {d_txt}")
                                else:
                                    self.log_msg(f"[WARN] Row {i+1}: Unparseable date '{d_txt}' — skipping")
                            except Exception as e:
                                self.log_msg(f"[WARN] Row {i+1}: Error parsing date '{d_txt}': {e} — skipping")
                        else:
                            self.log_msg(f"[SKIP] Row {i+1}: {subj}")
                            
                    except Exception as e:
                        self.log_msg(f"[WARN] Row {i+1}: Error reading row - {e}")
                
                if not matching_dates:
                    self.log_msg("[CURRENT] No matching workflows found in current tasks")
                    return
                
                # Sort dates and build chunks
                matching_dates.sort()
                chunks = []
                cur_from = matching_dates[0]
                end = matching_dates[-1]
                
                while cur_from <= end:
                    cur_to = min(cur_from + timedelta(days=13), end)
                    chunks.append((cur_from.strftime(DATE_FMT), cur_to.strftime(DATE_FMT)))
                    cur_from = cur_to + timedelta(days=1)
                
                # Store chunks in memory
                self.state.chunks = chunks
                self.state.next_chunk_index = 0
                
                self.log_msg(f"[CURRENT] Found {len(matching_dates)} matching workflows")
                for a, b in chunks:
                    self.log_msg(f"[CURRENT] Chunk: {a}–{b}")
                self.log_msg(f"[DONE] Built {len(chunks)} chunk(s) for advanced search")
                
            except Exception as e:
                if not self.state.stop_requested:
                    self.log_msg(f"[ERR] Current expansion failed: {e}")
                    if self.debug_var.get():
                        import traceback
                        self.log_msg(f"[DEBUG] Traceback: {traceback.format_exc()}")
        threading.Thread(target=run, daemon=True).start()

    def _queue_dry_run(self):
        def run():
            try:
                # Check for stop request at the start
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled by user")
                    return
                
                title = self.e_match.get().strip().lower()
                self.log_msg(f"[DRY] Starting dry run for: '{title}'")
                
                self._expand_sync("queue", verbose=True)
                
                # Check for stop request after expansion
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled by user")
                    return
                
                body = self._wait_visible(SEL["queue_body"], 10)
                rows = [r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()]
                
                if not rows:
                    self.log_msg("[DRY] No rows visible in queue")
                    return
                
                self.log_msg(f"[DRY] Found {len(rows)} rows to check")
                matches = 0
                
                for i, r in enumerate(rows):
                    # Check for stop request before each row
                    if self.state.stop_requested:
                        self.log_msg(f"[STOP] Operation cancelled at row {i+1}")
                        return
                    
                    try:
                        # FIXED: Look for the link directly in the first cell of each row
                        first_cell = r.find_element(By.CSS_SELECTOR, "td:first-child")
                        link = first_cell.find_element(By.CSS_SELECTOR, "a")
                        subj = link.text.strip()
                        
                        if subj.lower() == title:
                            self.log_msg(f"[MATCH] Row {i+1}: {subj}")
                            matches += 1
                        else:
                            self.log_msg(f"[SKIP] Row {i+1}: {subj}")
                            
                    except Exception as e:
                        self.log_msg(f"[WARN] Row {i+1}: Could not read subject - {e}")
                        if self.debug_var.get():
                            # Try to debug what's actually in the row
                            try:
                                self.log_msg(f"[DEBUG] Row {i+1} HTML: {r.get_attribute('outerHTML')[:200]}...")
                            except:
                                pass
                
                self.log_msg(f"[DONE] Dry run complete. Matches={matches}/{len(rows)}")
                
            except Exception as e:
                if not self.state.stop_requested:
                    self.log_msg(f"[ERR] Dry Run failed: {e}")
                    if self.debug_var.get():
                        import traceback
                        self.log_msg(f"[DEBUG] Full error: {traceback.format_exc()}")
        threading.Thread(target=run, daemon=True).start()

    def _expand_queue(self):
        """Expand queued tasks and build date chunks for advanced search"""
        def run():
            try:
                # Check for stop request at the start
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled by user")
                    return
                
                title = self.e_match.get().strip().lower()
                self.log_msg(f"[QUEUE] Starting queue expansion for: '{title}'")
                
                # Expand the queued tasks list until exhaustion
                self.log_msg("[QUEUE] Expanding queued tasks list...")
                self._expand_sync("queue", verbose=True)
                
                # Check for stop request after expansion
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled after queue expansion")
                    return
                
                # Build date chunks from queue
                self.log_msg("[QUEUE] Building date chunks from queue...")
                body = self._wait_visible(SEL["queue_body"], 10)
                rows = [r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()]
                
                if not rows:
                    self.log_msg("[QUEUE] No rows visible in queue")
                    return
                
                self.log_msg(f"[QUEUE] Found {len(rows)} rows to check")
                
                # Find matching workflows and collect their dates
                matching_dates = []
                for i, r in enumerate(rows):
                    # Check for stop request before each row
                    if self.state.stop_requested:
                        self.log_msg(f"[STOP] Operation cancelled at row {i+1}")
                        return
                    
                    try:
                        # Look for the link directly in the first cell of each row
                        first_cell = r.find_element(By.CSS_SELECTOR, "td:first-child")
                        link = first_cell.find_element(By.CSS_SELECTOR, "a")
                        subj = link.text.strip().lower()
                        
                        if subj == title:
                            # Look for date in the third cell
                            date_cell = r.find_element(By.CSS_SELECTOR, "td:nth-child(3)")
                            d_txt = date_cell.text.strip()
                            try:
                                # Handle relative dates like "Today", "Tomorrow", etc.
                                d = self._parse_workflow_date(d_txt)
                                if d:
                                    matching_dates.append(d)
                                    self.log_msg(f"[QUEUE] Row {i+1}: Found matching workflow with date {d_txt}")
                                else:
                                    self.log_msg(f"[WARN] Row {i+1}: Unparseable date '{d_txt}' — skipping")
                            except Exception as e:
                                self.log_msg(f"[WARN] Row {i+1}: Error parsing date '{d_txt}': {e} — skipping")
                        else:
                            self.log_msg(f"[SKIP] Row {i+1}: {subj}")
                            
                    except Exception as e:
                        self.log_msg(f"[WARN] Row {i+1}: Error reading row - {e}")
                
                if not matching_dates:
                    self.log_msg("[QUEUE] No matching workflows found in queue")
                    return
                
                # Sort dates and build chunks
                matching_dates.sort()
                chunks = []
                cur_from = matching_dates[0]
                end = matching_dates[-1]
                
                while cur_from <= end:
                    cur_to = min(cur_from + timedelta(days=13), end)
                    chunks.append((cur_from.strftime(DATE_FMT), cur_to.strftime(DATE_FMT)))
                    cur_from = cur_to + timedelta(days=1)
                
                # Store chunks in memory
                self.state.chunks = chunks
                self.state.next_chunk_index = 0
                
                self.log_msg(f"[QUEUE] Found {len(matching_dates)} matching queued workflows")
                for a, b in chunks:
                    self.log_msg(f"[QUEUE] Chunk: {a}–{b}")
                self.log_msg(f"[DONE] Built {len(chunks)} chunk(s) for advanced search")
                self.log_msg(f"[DONE] ✅ Queue expansion complete! Now navigate to Advanced Search and use 'Search and Pickup All'")
                self.update_status("Queue Expanded - Ready for Pickup")
                
            except Exception as e:
                if not self.state.stop_requested:
                    self.log_msg(f"[ERR] Queue expansion failed: {e}")
                    if self.debug_var.get():
                        import traceback
                        self.log_msg(f"[DEBUG] Traceback: {traceback.format_exc()}")
        threading.Thread(target=run, daemon=True).start()

    def _count_rows(self, body_element):
        """Count visible rows in the task body"""
        try:
            rows = body_element.find_elements(By.CSS_SELECTOR, "tr")
            visible_rows = [r for r in rows if r.is_displayed()]
            return len(visible_rows)
        except Exception as e:
            self.log_msg(f"[DEBUG] Error counting rows: {e}")
            return 0

    def _expand_sync(self, which: str, verbose=False):
        if which == "current":
            container, body, btn, label = SEL["current_container"], SEL["current_body"], SEL["current_load_more"], "Current"
        else:
            container, body, btn, label = SEL["queue_container"], SEL["queue_body"], SEL["queue_load_more"], "Queue"
        
        try:
            self._wait_visible(container, 15)
            # Get the actual body element, not just the selector
            body_element = self._wait_visible(body, 10)
            base = self._count_rows(body_element)
            clicks = 0
            
            if verbose:
                self.log_msg(f"[EXPAND] {label}: Starting with {base} rows")
            
            while True:
                try:
                    # Look for the Load More button with multiple fallback selectors
                    lm = None
                    load_more_selectors = [
                        btn,  # Original selector
                        (By.ID, "currentTasksLoadMoreButton" if which == "current" else "queuedTasksLoadMoreButton"),
                        (By.XPATH, f"//button[contains(text(), 'Load More {label}')]"),
                        (By.XPATH, f"//button[contains(text(), 'Load More')]"),
                        (By.CSS_SELECTOR, f"button[id*='LoadMore']"),
                        (By.CSS_SELECTOR, f"button[data-{which}tasksqueryoffset]")
                    ]
                    
                    for selector in load_more_selectors:
                        try:
                            lm = WebDriverWait(self.state.driver, 2).until(EC.element_to_be_clickable(selector))
                            if verbose:
                                self.log_msg(f"[EXPAND] {label}: Found Load More button with selector: {selector}")
                            break
                        except TimeoutException:
                            continue
                    
                    if not lm:
                        if verbose:
                            self.log_msg(f"[EXPAND] {label}: No Load More button found with any selector")
                        break
                    
                    if verbose:
                        self.log_msg(f"[EXPAND] {label}: Clicking Load More button...")
                    
                    # Try multiple click methods for robustness
                    click_success = False
                    
                    # Method 1: Regular click
                    try:
                        lm.click()
                        click_success = True
                        if verbose:
                            self.log_msg(f"[EXPAND] {label}: Regular click successful")
                    except Exception as e:
                        if verbose:
                            self.log_msg(f"[EXPAND] {label}: Regular click failed: {e}")
                    
                    # Method 2: JavaScript click if regular click failed
                    if not click_success:
                        try:
                            self.state.driver.execute_script("arguments[0].click();", lm)
                            click_success = True
                            if verbose:
                                self.log_msg(f"[EXPAND] {label}: JavaScript click successful")
                        except Exception as e:
                            if verbose:
                                self.log_msg(f"[EXPAND] {label}: JavaScript click failed: {e}")
                    
                    if click_success:
                        clicks += 1
                        if verbose:
                            self.log_msg(f"[EXPAND] {label}: Load More clicked (click #{clicks})")
                    else:
                        if verbose:
                            self.log_msg(f"[EXPAND] {label}: All click methods failed")
                        break
                    
                    time.sleep(1.0)  # Wait for new rows to load
                    now = self._count_rows(body_element)
                    
                    if now <= base:
                        if verbose:
                            self.log_msg(f"[EXPAND] {label}: No new rows after click; stopping at {now}")
                        break
                    
                    base = now
                    if verbose:
                        self.log_msg(f"[EXPAND] {label}: rows={base} (clicks={clicks})")
                    
                    # Continue to next iteration to look for more Load More buttons
                    
                except TimeoutException:
                    if verbose:
                        self.log_msg(f"[EXPAND] {label}: No more Load More button found; final rows={base}")
                    break
                except Exception as e:
                    if verbose:
                        self.log_msg(f"[EXPAND] {label}: Error during expansion: {e}")
                    break
            
            if verbose:
                self.log_msg(f"[EXPAND] {label}: Expansion complete - {base} total rows after {clicks} clicks")
            
            return base
            
        except Exception as e:
            if verbose:
                self.log_msg(f"[ERR] Expand {label}: {e}")
            return 0

    def _search_and_process_all(self):
        """Main function to search and process all Remove Counselor workflows"""
        def run():
            try:
                # Check for stop request at the start
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled by user")
                    return
                
                # First, perform the advanced search
                self.log_msg("[SEARCH] Starting advanced search...")
                self._perform_advanced_search()
                
                # Check for stop request after search
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled after search")
                    return
                
                # Now process all the Remove Counselor workflows
                self.log_msg("[PROCESS] Starting workflow processing...")
                self._process_all_workflows()
                
                if not self.state.stop_requested:
                    self.log_msg(f"[DONE] ✅ TASK COMPLETE! Processed {len(self.state.extracted_data)} workflows")
                    self.update_status("Complete")
                    self.update_data_count()
                
            except Exception as e:
                if not self.state.stop_requested:
                    self.log_msg(f"[ERR] Search and process failed: {e}")
                    if self.debug_var.get():
                        import traceback
                        self.log_msg(f"[DEBUG] Traceback: {traceback.format_exc()}")
        threading.Thread(target=run, daemon=True).start()

    def _test_run_limited(self):
        """Test run with limited number of workflows"""
        def run():
            try:
                # Get the max workflows from the entry field
                max_workflows_str = self.e_max_workflows.get().strip()
                max_workflows = 0
                
                if max_workflows_str:
                    try:
                        max_workflows = int(max_workflows_str)
                    except ValueError:
                        self.log_msg("[WARN] Invalid max workflows value, using unlimited")
                        max_workflows = 0
                
                if max_workflows <= 0:
                    self.log_msg("[TEST] No limit set, processing all workflows")
                else:
                    self.log_msg(f"[TEST] Limited test run - max {max_workflows} workflows")
                
                # Check for stop request at the start
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled by user")
                    return
                
                # First, perform the advanced search
                self.log_msg("[SEARCH] Starting advanced search...")
                self._perform_advanced_search()
                
                # Check for stop request after search
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled after search")
                    return
                
                # Now process the Remove Counselor workflows with limit
                self.log_msg("[PROCESS] Starting limited workflow processing...")
                self._process_all_workflows_limited(max_workflows)
                
                if not self.state.stop_requested:
                    self.log_msg(f"[DONE] ✅ TEST COMPLETE! Processed {len(self.state.extracted_data)} workflows")
                    self.update_status("Test Complete")
                    self.update_data_count()
                
            except Exception as e:
                if not self.state.stop_requested:
                    self.log_msg(f"[ERR] Test run failed: {e}")
                    self.update_status("Error")
        
        threading.Thread(target=run, daemon=True).start()

    def _search_and_pickup_all(self):
        """Search and pickup all queued workflows using chunks from Expand Queue"""
        def run():
            try:
                # Check for stop request at the start
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled by user")
                    return
                
                # Check if chunks have been built
                if not self.state.chunks:
                    self.log_msg("[PICKUP] No chunks found! Please run 'Expand Queue' first.")
                    self.update_status("Error: Run Expand Queue First")
                    return
                
                title = self.e_match.get().strip()
                self.log_msg(f"[PICKUP] Starting pickup workflow for: '{title}'")
                self.log_msg(f"[PICKUP] Using {len(self.state.chunks)} chunk(s) from queue expansion")
                
                # Process each chunk using advanced search
                total_pickups = 0
                for chunk_index, (from_date, to_date) in enumerate(self.state.chunks):
                    # Check for stop request before each chunk
                    if self.state.stop_requested:
                        self.log_msg(f"[STOP] Operation cancelled at chunk {chunk_index+1}")
                        return
                    
                    self.log_msg(f"[PICKUP] Processing chunk {chunk_index+1}/{len(self.state.chunks)}: {from_date} to {to_date}")
                    
                    # Fill the date range in advanced search
                    try:
                        frm = self._wait_visible(SEL["adv_from"], 10)
                        to = self._wait_visible(SEL["adv_to"], 10)
                        
                        frm.clear()
                        frm.send_keys(from_date)
                        to.clear()
                        to.send_keys(to_date)
                        
                        self.log_msg(f"[PICKUP] Set From={from_date} To={to_date}")
                    except Exception as e:
                        self.log_msg(f"[ERR] Failed to fill date range: {e}")
                        continue
                    
                    # Perform advanced search
                    self.log_msg("[PICKUP] Performing advanced search...")
                    try:
                        search_btn = self._wait_visible(SEL["adv_search"], 10)
                        if self._safe_click(search_btn):
                            self.log_msg("[PICKUP] Advanced search clicked")
                        else:
                            self.log_msg("[ERR] Failed to click search button")
                            continue
                        
                        # Wait for results to load
                        time.sleep(5)
                        self.log_msg("[PICKUP] Advanced search completed")
                    except Exception as e:
                        self.log_msg(f"[ERR] Advanced search failed: {e}")
                        continue
                    
                    # Process all workflows in this chunk (using same pattern as _process_all_workflows)
                    drv = self._drv()
                    
                    # Count initial workflows to know how many to process
                    try:
                        search_results_table = drv.find_element(By.CSS_SELECTOR, ".advancedTasksBody table")
                    except:
                        try:
                            search_results_table = drv.find_element(By.XPATH, f"//table[.//a[contains(text(), '{title}')]]")
                        except:
                            self.log_msg("[WARN] Could not find search results table")
                            continue
                    
                    if search_results_table:
                        all_links = search_results_table.find_elements(By.TAG_NAME, "a")
                    else:
                        all_links = drv.find_elements(By.TAG_NAME, "a")
                    
                    # Count matching workflows
                    initial_count = 0
                    for link in all_links:
                        try:
                            link_text = link.text.strip()
                            if link_text == title:
                                initial_count += 1
                        except:
                            continue
                    
                    if initial_count == 0:
                        self.log_msg(f"[PICKUP] No workflows found in chunk {chunk_index+1}")
                        continue
                    
                    self.log_msg(f"[PICKUP] Found {initial_count} workflows to pickup in chunk {chunk_index+1}")
                    
                    # Process workflows continuously until none are left
                    processed_count = 0
                    
                    while True:
                        # Check for stop request
                        if self.state.stop_requested:
                            self.log_msg(f"[STOP] Operation cancelled after processing {processed_count} workflows in chunk")
                            return
                        
                        processed_count += 1
                        self.log_msg(f"[PICKUP] Processing workflow {processed_count} in chunk {chunk_index+1}")
                        self.update_status(f"Picking up workflow {total_pickups + 1}")
                        
                        try:
                            # Re-find all matching workflow links (FRESH each time to avoid stale elements)
                            self.log_msg(f"[PICKUP] Re-finding workflow links...")
                            
                            # Look for the search results table again
                            search_results_table = None
                            try:
                                search_results_table = drv.find_element(By.CSS_SELECTOR, ".advancedTasksBody table")
                            except:
                                try:
                                    search_results_table = drv.find_element(By.XPATH, f"//table[.//a[contains(text(), '{title}')]]")
                                except:
                                    self.log_msg("[WARN] Could not find search results table for re-finding links")
                                    break
                            
                            if search_results_table:
                                all_links = search_results_table.find_elements(By.TAG_NAME, "a")
                            else:
                                all_links = drv.find_elements(By.TAG_NAME, "a")
                            
                            # Find matching workflow links again
                            current_workflow_links = []
                            for link in all_links:
                                try:
                                    link_text = link.text.strip()
                                    if link_text == title:
                                        current_workflow_links.append(link)
                                except:
                                    continue
                            
                            if not current_workflow_links:
                                self.log_msg(f"[PICKUP] No more workflows found in this chunk - completed {processed_count-1} pickups")
                                break
                            
                            # Process the workflow at the current index (SAME AS _process_all_workflows)
                            workflow_index = processed_count - 1  # 0-based index
                            if workflow_index >= len(current_workflow_links):
                                self.log_msg(f"[SKIP] No more workflows available (index {workflow_index} >= {len(current_workflow_links)})")
                                break
                            
                            self.log_msg(f"[PICKUP] Found {len(current_workflow_links)} available workflows, processing workflow {workflow_index + 1}")
                            
                            # Click on the workflow at the current index (NOT always 0!)
                            try:
                                # Use the link at the current index (SAME AS _process_all_workflows)
                                link_element = current_workflow_links[workflow_index]
                                
                                # Click the workflow link
                                if not self._safe_click(link_element):
                                    self.log_msg("[WARN] Failed to click workflow link")
                                    break
                                
                                # Wait for page to load after clicking (increased wait for Pickup button to appear)
                                self.log_msg("[PICKUP] Waiting for task page to load...")
                                time.sleep(3)  # Increased from 1.5 to 3 seconds to ensure Pickup button loads
                                
                                # Click Pickup button (same location as Close button)
                                self.log_msg("[PICKUP] Looking for Pickup button...")
                                pickup_success = self._click_pickup_button()
                                
                                if pickup_success:
                                    total_pickups += 1
                                    self.log_msg(f"[PICKUP] Successfully picked up workflow! Total: {total_pickups}")
                                    # Navigate back to search results (SAME AS _process_all_workflows)
                                    self._navigate_back_to_search()
                                else:
                                    self.log_msg("[WARN] Failed to click Pickup button, continuing...")
                                    # Try to navigate back even if failed
                                    try:
                                        self._navigate_back_to_search()
                                    except:
                                        self.log_msg("[WARN] Could not navigate back after failed pickup")
                                
                            except Exception as e:
                                self.log_msg(f"[WARN] Failed to process workflow: {e}")
                                # Try to navigate back even if failed
                                try:
                                    self._navigate_back_to_search()
                                except:
                                    pass
                            
                            # Wait before processing the next one (same as _process_all_workflows)
                            time.sleep(2)
                            
                        except Exception as e:
                            self.log_msg(f"[WARN] Failed to process workflow {processed_count}: {e}")
                            # Try to navigate back even if failed
                            try:
                                self._navigate_back_to_search()
                            except:
                                pass
                            continue
                
                if not self.state.stop_requested:
                    self.log_msg(f"[DONE] ✅ TASK COMPLETE! Total pickups: {total_pickups}")
                    self.log_msg(f"[DONE] All queued 'Remove Counselor from Client in TN' workflows have been picked up.")
                    self.update_status("Pickup Complete")
                
            except Exception as e:
                if not self.state.stop_requested:
                    self.log_msg(f"[ERR] Pickup process failed: {e}")
                    if self.debug_var.get():
                        import traceback
                        self.log_msg(f"[DEBUG] Traceback: {traceback.format_exc()}")
        threading.Thread(target=run, daemon=True).start()

    def _perform_advanced_search(self):
        """Perform the advanced search to get Remove Counselor workflows"""
        try:
            # Click the search button
            search_btn = self._wait_visible(SEL["adv_search"], 10)
            if self._safe_click(search_btn):
                self.log_msg("[SEARCH] Advanced search clicked")
            else:
                self.log_msg("[ERR] Failed to click search button")
                return
            
            # Wait for results to load (increased from 3 to 10 seconds)
            time.sleep(10)
            self.log_msg("[SEARCH] Advanced search completed")
            
        except Exception as e:
            self.log_msg(f"[ERR] Advanced search failed: {e}")
            raise

    def _process_all_workflows(self):
        """Process all Remove Counselor workflows found in the search results"""
        try:
            # Find all Remove Counselor links
            self.log_msg("[PROCESS] Looking for Remove Counselor workflows...")
            
            # Look specifically in the advanced search results table
            drv = self._drv()
            
            # First try to find the search results table
            search_results_table = None
            try:
                # Look for the advanced search results table
                search_results_table = drv.find_element(By.CSS_SELECTOR, ".advancedTasksBody table")
                self.log_msg("[PROCESS] Found search results table")
            except:
                # Fallback: look for any table containing Remove Counselor links
                try:
                    search_results_table = drv.find_element(By.XPATH, "//table[.//a[contains(text(), 'Remove Counselor from Client in TN')]]")
                    self.log_msg("[PROCESS] Found table with Remove Counselor links")
                except:
                    self.log_msg("[PROCESS] Could not find search results table, searching all links")
                    search_results_table = None
            
            if search_results_table:
                # Search within the specific table
                all_links = search_results_table.find_elements(By.TAG_NAME, "a")
                self.log_msg(f"[PROCESS] Searching {len(all_links)} links in search results table")
            else:
                # Fallback to searching all links on the page
                all_links = drv.find_elements(By.TAG_NAME, "a")
                self.log_msg(f"[PROCESS] Searching {len(all_links)} links on entire page")
            
            remove_counselor_links = []
            for link in all_links:
                try:
                    link_text = link.text.strip()
                    link_text_lower = link_text.lower()
                    target_workflow = "remove counselor from client in tn"
                    
                    # Case-insensitive exact match
                    if link_text_lower == target_workflow:
                        remove_counselor_links.append(link)
                        self.log_msg(f"[PROCESS] Found workflow: {link_text}")
                    # Case-insensitive partial match (log and skip)
                    elif target_workflow in link_text_lower:
                        self.log_msg(f"[SKIP] Ignoring workflow with additional text: {link_text}")
                except:
                    continue
            
            if not remove_counselor_links:
                self.log_msg("[PROCESS] No Remove Counselor workflows found")
                return
            
            self.log_msg(f"[PROCESS] Found {len(remove_counselor_links)} workflows to process")
            
            # Process workflows continuously until none are left
            processed_count = 0
            
            while True:
                # Check for stop request
                if self.state.stop_requested:
                    self.log_msg(f"[STOP] Operation cancelled after processing {processed_count} workflows")
                    return
                
                processed_count += 1
                self.log_msg(f"[PROCESS] Processing workflow {processed_count}")
                self.update_status(f"Processing workflow {processed_count}")
                
                try:
                    # Re-find all Remove Counselor links
                    self.log_msg(f"[PROCESS] Re-finding Remove Counselor links...")
                    
                    # Look for the search results table again
                    search_results_table = None
                    try:
                        search_results_table = drv.find_element(By.CSS_SELECTOR, ".advancedTasksBody table")
                    except:
                        try:
                            search_results_table = drv.find_element(By.XPATH, "//table[.//a[contains(text(), 'Remove Counselor from Client in TN')]]")
                        except:
                            self.log_msg("[WARN] Could not find search results table for re-finding links")
                            break
                    
                    if search_results_table:
                        all_links = search_results_table.find_elements(By.TAG_NAME, "a")
                    else:
                        all_links = drv.find_elements(By.TAG_NAME, "a")
                    
                    # Find Remove Counselor links again
                    current_remove_counselor_links = []
                    for link in all_links:
                        try:
                            link_text = link.text.strip()
                            link_text_lower = link_text.lower()
                            target_workflow = "remove counselor from client in tn"
                            
                            # Case-insensitive exact match
                            if link_text_lower == target_workflow:
                                current_remove_counselor_links.append(link)
                            # Case-insensitive partial match (log and skip)
                            elif target_workflow in link_text_lower:
                                self.log_msg(f"[SKIP] Ignoring workflow with additional text: {link_text}")
                        except:
                            continue
                    
                    if not current_remove_counselor_links:
                        self.log_msg(f"[PROCESS] No more Remove Counselor workflows found - completed {processed_count-1} workflows")
                        break
                    
                    # Process the workflow at the current index
                    workflow_index = processed_count - 1  # 0-based index
                    if workflow_index >= len(current_remove_counselor_links):
                        self.log_msg(f"[SKIP] No more workflows available (index {workflow_index} >= {len(current_remove_counselor_links)})")
                        break
                    
                    self.log_msg(f"[PROCESS] Found {len(current_remove_counselor_links)} available workflows, processing workflow {workflow_index + 1}")
                    
                    # Click on the workflow at the current index
                    try:
                        # Use the link at the current index
                        link_element = current_remove_counselor_links[workflow_index]
                        
                        # Process the complete workflow: click link -> click Close -> click Case -> process red bubbles
                        self.log_msg("[PROCESS] Starting complete workflow processing...")
                        success = self._process_single_workflow(link_element)
                        
                        if success:
                            self.log_msg(f"[PROCESS] Workflow {processed_count} completed successfully")
                            # Only navigate back if workflow was successful
                            self._navigate_back_to_search()
                        else:
                            self.log_msg(f"[WARN] Workflow {processed_count} failed, continuing...")
                            # Try to navigate back even if failed, but don't fail the whole process
                            try:
                                self._navigate_back_to_search()
                            except:
                                self.log_msg("[WARN] Could not navigate back after failed workflow")
                        
                    except Exception as e:
                        self.log_msg(f"[WARN] Failed to click first workflow, trying fallback method: {e}")
                        # Fallback to the old method if XPath fails
                        self.log_msg("[PROCESS] Starting complete workflow processing (fallback)...")
                        success = self._process_single_workflow(current_remove_counselor_links[0])
                        
                        if success:
                            self.log_msg(f"[PROCESS] Workflow {processed_count} completed successfully (fallback)")
                            # Only navigate back if workflow was successful
                            self._navigate_back_to_search()
                        else:
                            self.log_msg(f"[WARN] Workflow {processed_count} failed (fallback), continuing...")
                            # Try to navigate back even if failed, but don't fail the whole process
                            try:
                                self._navigate_back_to_search()
                            except:
                                self.log_msg("[WARN] Could not navigate back after failed workflow (fallback)")
                    
                    # Wait a bit before processing the next one
                    time.sleep(2)
                    
                except Exception as e:
                    self.log_msg(f"[WARN] Failed to process workflow {processed_count}: {e}")
                    continue
            
            self.log_msg(f"[PROCESS] Completed processing {len(remove_counselor_links)} workflows")
            
            # Auto-generate CSV after all workflows are completed
            if self.state.extracted_data:
                self.log_msg("[AUTO-EXPORT] Automatically generating CSV file...")
                try:
                    # Generate filename with timestamp
                    from datetime import datetime
                    import os
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"remove_counselor_data_{timestamp}.csv"

                    # Save to user-selected output directory
                    save_dir = self._get_export_dir()
                    self.log_msg(f"[AUTO-EXPORT] Saving to: {save_dir}")
                    
                    # Create full file path
                    full_path = os.path.join(save_dir, filename)
                    
                    # Ensure directory exists
                    os.makedirs(save_dir, exist_ok=True)

                    # Write CSV file
                    with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = ['Case Name', 'Case ID', 'Primary Workers', 'Service File Status', 'Extraction Date', 'Client DOB']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                        writer.writeheader()
                        for data in self.state.extracted_data:
                            writer.writerow({
                                'Case Name': data.case_name,
                                'Case ID': data.case_id,
                                'Primary Workers': '; '.join(data.primary_workers),
                                'Service File Status': data.service_file_status,
                                'Extraction Date': data.extraction_date,
                                'Client DOB': data.client_dob
                            })

                    self.log_msg(f"[AUTO-EXPORT] ✅ CSV automatically saved: {full_path}")
                    self.log_msg(f"[AUTO-EXPORT] Exported {len(self.state.extracted_data)} records")
                    
                    # Also create an Excel file with proper column widths for better visibility
                    try:
                        import pandas as pd
                        excel_path = full_path.replace('.csv', '.xlsx')
                        df = pd.DataFrame([{
                            'Case Name': data.case_name,
                            'Case ID': data.case_id,
                            'Primary Workers': '; '.join(data.primary_workers),
                            'Service File Status': data.service_file_status,
                            'Extraction Date': data.extraction_date,
                            'Client DOB': data.client_dob
                        } for data in self.state.extracted_data])
                        
                        # Write to Excel with auto-adjusted column widths
                        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Extracted Data')
                            
                            # Auto-adjust column widths
                            worksheet = writer.sheets['Extracted Data']
                            for column in worksheet.columns:
                                max_length = 0
                                column_letter = column[0].column_letter
                                for cell in column:
                                    try:
                                        if len(str(cell.value)) > max_length:
                                            max_length = len(str(cell.value))
                                    except:
                                        pass
                                adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                                worksheet.column_dimensions[column_letter].width = adjusted_width
                        
                        self.log_msg(f"[AUTO-EXPORT] ✅ Excel file also created: {excel_path}")
                    except Exception as excel_e:
                        self.log_msg(f"[AUTO-EXPORT] Excel creation failed (CSV still available): {excel_e}")

                except Exception as e:
                    self.log_msg(f"[AUTO-EXPORT] Failed to auto-generate CSV: {e}")
            else:
                self.log_msg("[AUTO-EXPORT] No data to export")
            
        except Exception as e:
            self.log_msg(f"[ERR] Process workflows failed: {e}")
            raise

    def _process_all_workflows_limited(self, max_workflows):
        """Process Remove Counselor workflows with a limit for testing"""
        try:
            # Find all Remove Counselor links
            self.log_msg("[PROCESS] Looking for Remove Counselor workflows...")
            
            # Look specifically in the advanced search results table
            drv = self._drv()
            
            # First try to find the search results table
            search_results_table = None
            try:
                # Look for the advanced search results table
                search_results_table = drv.find_element(By.CSS_SELECTOR, ".advancedTasksBody table")
                self.log_msg("[PROCESS] Found search results table")
            except:
                # Fallback: look for any table containing Remove Counselor links
                try:
                    search_results_table = drv.find_element(By.XPATH, "//table[.//a[contains(text(), 'Remove Counselor from Client in TN')]]")
                    self.log_msg("[PROCESS] Found table with Remove Counselor links")
                except:
                    self.log_msg("[PROCESS] Could not find search results table, searching all links")
                    search_results_table = None
            
            if search_results_table:
                # Search within the specific table
                all_links = search_results_table.find_elements(By.TAG_NAME, "a")
                self.log_msg(f"[PROCESS] Searching {len(all_links)} links in search results table")
            else:
                # Fallback to searching all links on the page
                all_links = drv.find_elements(By.TAG_NAME, "a")
                self.log_msg(f"[PROCESS] Searching {len(all_links)} links on entire page")
            
            remove_counselor_links = []
            for link in all_links:
                try:
                    link_text = link.text.strip()
                    link_text_lower = link_text.lower()
                    target_workflow = "remove counselor from client in tn"
                    
                    # Case-insensitive exact match
                    if link_text_lower == target_workflow:
                        remove_counselor_links.append(link)
                        self.log_msg(f"[PROCESS] Found workflow: {link_text}")
                    # Case-insensitive partial match (log and skip)
                    elif target_workflow in link_text_lower:
                        self.log_msg(f"[SKIP] Ignoring workflow with additional text: {link_text}")
                except:
                    continue
            
            if not remove_counselor_links:
                self.log_msg("[PROCESS] No Remove Counselor workflows found")
                return
            
            # Apply the limit
            if max_workflows > 0 and len(remove_counselor_links) > max_workflows:
                remove_counselor_links = remove_counselor_links[:max_workflows]
                self.log_msg(f"[PROCESS] Limited to {max_workflows} workflows for testing")
            
            self.log_msg(f"[PROCESS] Found {len(remove_counselor_links)} workflows to process")
            
            # Process workflows continuously until limit is reached or none are left
            processed_count = 0
            
            while True:
                # Check for stop request
                if self.state.stop_requested:
                    self.log_msg(f"[STOP] Operation cancelled after processing {processed_count} workflows")
                    return
                
                # Check if we've reached the limit for test runs
                if max_workflows > 0 and processed_count >= max_workflows:
                    self.log_msg(f"[PROCESS] Reached test limit of {max_workflows} workflows")
                    break
                
                processed_count += 1
                self.log_msg(f"[PROCESS] Processing workflow {processed_count}")
                self.update_status(f"Processing workflow {processed_count}")

                try:
                    # Re-find all Remove Counselor links
                    self.log_msg(f"[PROCESS] Re-finding Remove Counselor links...")
                    
                    # Look for the search results table again
                    search_results_table = None
                    try:
                        search_results_table = drv.find_element(By.CSS_SELECTOR, ".advancedTasksBody table")
                    except:
                        try:
                            search_results_table = drv.find_element(By.XPATH, "//table[.//a[contains(text(), 'Remove Counselor from Client in TN')]]")
                        except:
                            self.log_msg("[WARN] Could not find search results table for re-finding links")
                            break
                    
                    if search_results_table:
                        all_links = search_results_table.find_elements(By.TAG_NAME, "a")
                    else:
                        all_links = drv.find_elements(By.TAG_NAME, "a")

                    # Find Remove Counselor links again
                    current_remove_counselor_links = []
                    for link in all_links:
                        try:
                            link_text = link.text.strip()
                            link_text_lower = link_text.lower()
                            target_workflow = "remove counselor from client in tn"
                            
                            # Case-insensitive exact match
                            if link_text_lower == target_workflow:
                                current_remove_counselor_links.append(link)
                            # Case-insensitive partial match (log and skip)
                            elif target_workflow in link_text_lower:
                                self.log_msg(f"[SKIP] Ignoring workflow with additional text: {link_text}")
                        except:
                            continue

                    if not current_remove_counselor_links:
                        self.log_msg(f"[PROCESS] No more Remove Counselor workflows found - completed {processed_count-1} workflows")
                        break

                    # Process the first available workflow (index 0)
                    self.log_msg(f"[PROCESS] Found {len(current_remove_counselor_links)} available workflows, processing first one")
                    
                    # Click on the first available workflow
                    try:
                        # Find the table first
                        table = drv.find_element(By.CSS_SELECTOR, ".advancedTasksBody table")
                        # Click on the first row that contains a "Remove Counselor from Client in TN" link
                        row_xpath = "(//a[text()='Remove Counselor from Client in TN'])[1]"
                        link_element = drv.find_element(By.XPATH, row_xpath)
                        self._process_single_workflow(link_element)
                    except Exception as e:
                        self.log_msg(f"[WARN] Failed to click first workflow, trying fallback method: {e}")
                        # Fallback to the old method if XPath fails
                        self._process_single_workflow(current_remove_counselor_links[0])

                    # Wait a bit before processing the next one
                    time.sleep(1)

                except Exception as e:
                    self.log_msg(f"[WARN] Failed to process workflow {processed_count}: {e}")
                    continue
            
            self.log_msg(f"[PROCESS] Completed processing {max_workflows if max_workflows > 0 else len(remove_counselor_links)} workflows")
            
            # Auto-generate CSV after all workflows are completed
            if self.state.extracted_data:
                self.log_msg("[AUTO-EXPORT] Automatically generating CSV file...")
                try:
                    # Generate filename with timestamp
                    from datetime import datetime
                    import os
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"remove_counselor_data_TEST_{timestamp}.csv"

                    # Use user-selected output directory for TEST export as well
                    save_dir = self._get_export_dir()
                    self.log_msg(f"[AUTO-EXPORT] Saving TEST export to: {save_dir}")
                    
                    # Create full file path
                    full_path = os.path.join(save_dir, filename)
                    
                    # Ensure directory exists
                    os.makedirs(save_dir, exist_ok=True)

                    # Write CSV file
                    with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = ['Case Name', 'Case ID', 'Primary Workers', 'Service File Status', 'Extraction Date', 'Client DOB']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                        writer.writeheader()
                        for data in self.state.extracted_data:
                            writer.writerow({
                                'Case Name': data.case_name,
                                'Case ID': data.case_id,
                                'Primary Workers': '; '.join(data.primary_workers),
                                'Service File Status': data.service_file_status,
                                'Extraction Date': data.extraction_date,
                                'Client DOB': data.client_dob
                            })

                    self.log_msg(f"[AUTO-EXPORT] ✅ TEST CSV automatically saved: {full_path}")
                    self.log_msg(f"[AUTO-EXPORT] Exported {len(self.state.extracted_data)} records")
                    
                    # Also create an Excel file with proper column widths for better visibility
                    try:
                        import pandas as pd
                        excel_path = full_path.replace('.csv', '.xlsx')
                        df = pd.DataFrame([{
                            'Case Name': data.case_name,
                            'Case ID': data.case_id,
                            'Primary Workers': '; '.join(data.primary_workers),
                            'Service File Status': data.service_file_status,
                            'Extraction Date': data.extraction_date,
                            'Client DOB': data.client_dob
                        } for data in self.state.extracted_data])
                        
                        # Write to Excel with auto-adjusted column widths
                        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False, sheet_name='Extracted Data')
                            
                            # Auto-adjust column widths
                            worksheet = writer.sheets['Extracted Data']
                            for column in worksheet.columns:
                                max_length = 0
                                column_letter = column[0].column_letter
                                for cell in column:
                                    try:
                                        if len(str(cell.value)) > max_length:
                                            max_length = len(str(cell.value))
                                    except:
                                        pass
                                adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                                worksheet.column_dimensions[column_letter].width = adjusted_width
                        
                        self.log_msg(f"[AUTO-EXPORT] ✅ TEST Excel file also created: {excel_path}")
                    except Exception as excel_e:
                        self.log_msg(f"[AUTO-EXPORT] Excel creation failed (CSV still available): {excel_e}")

                except Exception as e:
                    self.log_msg(f"[AUTO-EXPORT] Failed to auto-generate CSV: {e}")
            else:
                self.log_msg("[AUTO-EXPORT] No data to export")
            
        except Exception as e:
            self.log_msg(f"[ERR] Process workflows failed: {e}")
            raise

    def _process_single_workflow(self, link):
        """Process a single workflow - extract counselor data"""
        try:
            # Step 1: Click the Remove Counselor link
            self.log_msg("[STEP 1] Clicking Remove Counselor link...")
            
            if not self._safe_click(link):
                self.log_msg("[WARN] Failed to click Remove Counselor link")
                return False
            
            # Wait for page to load after clicking
            self.log_msg("[STEP 1] Waiting for task page to load...")
            time.sleep(1.5)
            
            # Click Close button if available
            self._click_close_button()
            
            # Wait a moment for any page updates after Close
            time.sleep(0.5)
            
            # Look for Case link in the Record box
            self.log_msg("[STEP 3] Looking for Case link in Record box...")
            
            # Debug: Check current page title and URL
            try:
                current_url = self.state.driver.current_url
                current_title = self.state.driver.title
                self.log_msg(f"[DEBUG] Current URL: {current_url}")
                self.log_msg(f"[DEBUG] Current title: {current_title}")
            except:
                pass
            
            # Debug: Check if we're in the right iframe
            try:
                frames = self.state.driver.find_elements(By.TAG_NAME, "iframe")
                self.log_msg(f"[DEBUG] Found {len(frames)} iframes on page")
                for i, frame in enumerate(frames):
                    try:
                        frame_name = frame.get_attribute("name") or frame.get_attribute("id") or f"frame_{i}"
                        self.log_msg(f"[DEBUG] Frame {i}: {frame_name}")
                    except:
                        pass
            except:
                pass
            
            # Find the Case link directly in the Record box
            try:
                # Look for the Case link using the exact structure from frame_1.html
                case_links = self.state.driver.find_elements(By.XPATH, "//div[contains(@class, 'cbb') and .//h2[text()='Record']]//tr[td[@class='title' and text()='Case']]//a")
                self.log_msg(f"[DEBUG] Found {len(case_links)} Case links in Record box")
                
                if not case_links:
                    self.log_msg("[WARN] No Case links found in Record box - trying iframe fallback")
                    
                    # Try switching to iframe 1 (where the Close button was found)
                    try:
                        frames = self.state.driver.find_elements(By.TAG_NAME, "iframe")
                        if len(frames) > 1:
                            self.log_msg("[DEBUG] Switching to iframe 1 for Case button search")
                            self.state.driver.switch_to.frame(frames[1])
                            
                            # Try finding Case links in iframe 1
                            case_links = self.state.driver.find_elements(By.XPATH, "//div[contains(@class, 'cbb') and .//h2[text()='Record']]//tr[td[@class='title' and text()='Case']]//a")
                            self.log_msg(f"[DEBUG] Found {len(case_links)} Case links in iframe 1")
                            
                            if not case_links:
                                # Switch back to main frame
                                self.state.driver.switch_to.default_content()
                                self.log_msg("[WARN] No Case links found in iframe 1 either")
                                return False
                        else:
                            self.log_msg("[WARN] No iframes available for fallback")
                            return False
                    except Exception as e:
                        self.log_msg(f"[WARN] Iframe fallback failed: {e}")
                        # Switch back to main frame
                        try:
                            self.state.driver.switch_to.default_content()
                        except:
                            pass
                        return False
                
                case_link = case_links[0]
                self.log_msg("[DEBUG] Found Case link in Record box")
                
            except Exception as e:
                self.log_msg(f"[WARN] Error finding Case link in Record box: {e}")
                return False
            
            case_text = case_link.text.strip()
            self.log_msg(f"[EXTRACT] Case info: {case_text}")
            
            # Click the Case link
            if self._safe_click(case_link):
                self.log_msg("[OK] Successfully clicked Case link")
            else:
                self.log_msg("[WARN] Failed to click Case link")
                return False
            
            # Extract counselor data
            self.log_msg("[STEP 4] Extracting data from Service Files...")
            time.sleep(1)  # Reduced wait time
            
            # Look for client name in Members section
            try:
                # Try multiple selectors for client name
                client_name = None
                selectors = [
                    "//table[@id='caseMemberTable']//td[@style='font-size:14px']//a[contains(@href, 'acm_clientProfileControl')]",
                    "//table[@id='caseMemberTable']//td[@style='font-size:14px']//a[contains(@href, 'kIndID')]",
                    "//table[@id='caseMemberTable']//a[contains(@href, 'acm_clientProfileControl')]",
                    "//table[@id='caseMemberTable']//a[contains(@href, 'kIndID')]",
                    "//div[contains(@class, 'cbb') and .//h2[text()='Members']]//a[contains(@href, 'acm_clientProfileControl')]",
                    "//div[contains(@class, 'cbb') and .//h2[text()='Members']]//a[contains(@href, 'kIndID')]"
                ]
                
                for selector in selectors:
                    try:
                        client_name_elem = self.state.driver.find_element(By.XPATH, selector)
                        client_name = client_name_elem.text.strip()
                        if client_name:
                            self.log_msg(f"[EXTRACT] Found client name in Members section: '{client_name}'")
                            break
                    except:
                        continue
                
                if not client_name:
                    self.log_msg("[WARN] Could not extract client name")
                    return False
                
                # Extract DOB from Members table (4th td element in the case member row)
                client_dob = ""
                try:
                    # Look for DOB in the Members table - it's in the 4th column (index 3) of the member row
                    dob_selectors = [
                        "//table[@id='caseMemberTable']//tr[td[2]//a[contains(@href, 'acm_clientProfileControl')]]/td[4]",
                        "//table[@id='caseMemberTable']//tr[td[2]//a[contains(@href, 'kIndID')]]/td[4]",
                        "//table[@id='caseMemberTable']//tr[td[2]//a]/td[4]",
                        "//div[contains(@class, 'cbb') and .//h2[text()='Members']]//tr[td[2]//a]/td[4]"
                    ]
                    
                    for selector in dob_selectors:
                        try:
                            dob_elem = self.state.driver.find_element(By.XPATH, selector)
                            dob_text = dob_elem.text.strip()
                            # Check if it looks like a date (MM/DD/YYYY format)
                            if dob_text and '/' in dob_text and len(dob_text) >= 8:
                                client_dob = dob_text
                                self.log_msg(f"[EXTRACT] Found client DOB in Members section: '{client_dob}'")
                                break
                        except:
                            continue
                    
                    if not client_dob:
                        self.log_msg("[WARN] Could not extract client DOB (will continue without DOB verification)")
                    
                except Exception as e:
                    self.log_msg(f"[WARN] Could not extract client DOB: {e} (will continue without DOB verification)")
                    
            except Exception as e:
                self.log_msg(f"[WARN] Could not extract client name: {e}")
                return False
            
            # Extract counselor data from Service Files table
            try:
                # Find the Service Files table
                service_files_table = self.state.driver.find_element(By.ID, "pptableList")
                table_rows = service_files_table.find_elements(By.CSS_SELECTOR, "tbody tr")
                
                # Dictionary to track counselor status: {counselor_name: [statuses]}
                counselor_statuses = {}
                
                for row in table_rows:
                    try:
                        # Skip header row
                        if "sortheader" in row.get_attribute("innerHTML"):
                            continue
                            
                        cells = row.find_elements(By.CSS_SELECTOR, "td")
                        if len(cells) >= 5:  # Need at least 5 columns for status and primary worker
                            # Get status (red bubble = closed, green bubble = active)
                            status_cell = cells[1]  # Status column
                            status_class = status_cell.get_attribute("class")
                            
                            # Get primary worker name
                            primary_worker_cell = cells[4]  # Primary Worker column
                            primary_worker_link = primary_worker_cell.find_element(By.CSS_SELECTOR, "a")
                            counselor_name = primary_worker_link.text.strip()
                            
                            if counselor_name:
                                # Determine status: "statusClosed" = red bubble, "statusOpen" = green bubble
                                is_closed = "statusClosed" in status_class
                                status = "closed" if is_closed else "active"
                                
                                if counselor_name not in counselor_statuses:
                                    counselor_statuses[counselor_name] = []
                                counselor_statuses[counselor_name].append(status)
                                
                                self.log_msg(f"[EXTRACT] Found counselor: {counselor_name} - Status: {status}")
                                
                    except Exception as e:
                        self.log_msg(f"[DEBUG] Error processing row: {e}")
                        continue
                
                # Determine which counselors to remove (only if ALL their services are closed)
                counselors_to_remove = []
                for counselor, statuses in counselor_statuses.items():
                    if all(status == "closed" for status in statuses):
                        counselors_to_remove.append(counselor)
                        self.log_msg(f"[EXTRACT] ✅ Counselor {counselor} - ALL services closed, will be removed")
                    else:
                        self.log_msg(f"[EXTRACT] ❌ Counselor {counselor} - has active services, will NOT be removed")
                
                if counselors_to_remove:
                    self.log_msg(f"[EXTRACT] Found {len(counselors_to_remove)} counselors to remove: {', '.join(counselors_to_remove)}")
                    
                    # Store extracted data
                    extracted_data = ExtractedData(
                        case_name=client_name,
                        case_id=case_text.split("(")[-1].split(")")[0] if "(" in case_text else "",
                        primary_workers=counselors_to_remove,
                        service_file_status="closed",
                        extraction_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        client_dob=client_dob
                    )
                    self.state.extracted_data.append(extracted_data)
                    self.log_msg(f"[STORE] Stored data for {client_name}: {len(counselors_to_remove)} counselors")
                else:
                    self.log_msg("[EXTRACT] No counselors found with all services closed")
                
            except Exception as e:
                self.log_msg(f"[WARN] Error extracting counselor data: {e}")
            
            return True
            
        except Exception as e:
            self.log_msg(f"[ERR] Process Single Workflow: {e}")
            return False

    def _click_close_button(self):
        """Click the Close button in the task page - optimized for speed"""
        try:
            drv = self.state.driver
            
            # Try to find Close button in iframes with minimal timeout
            frames = drv.find_elements(By.CSS_SELECTOR, "iframe,frame")
            for i, frame in enumerate(frames):
                try:
                    drv.switch_to.frame(frame)
                    # Use very short timeout for faster processing
                    close_links = WebDriverWait(drv, 0.5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='closeTask']"))
                    )
                    if close_links:
                        # Use JavaScript click for speed
                        drv.execute_script("arguments[0].click();", close_links[0])
                        self.log_msg(f"[OK] Successfully clicked Close button in iframe")
                        drv.switch_to.default_content()
                        time.sleep(0.1)  # Minimal wait
                        return True
                except Exception:
                    drv.switch_to.default_content()
                    continue
            
            self.log_msg("[WARN] No Close button found")
            return False
            
        except Exception as e:
            self.log_msg(f"[WARN] Error clicking Close button: {e}")
            return False

    def _click_pickup_button(self):
        """Click the Pickup button in the task page - EXACT SAME PATTERN as Close button"""
        try:
            drv = self.state.driver
            
            # Try to find Pickup button in iframes - EXACT SAME PATTERN AS CLOSE BUTTON
            # From HTML: <a href="javascript:doAjax('/TaskThreadServlet?actionType=pickupTask...">Pick Up</a>
            frames = drv.find_elements(By.CSS_SELECTOR, "iframe,frame")
            for i, frame in enumerate(frames):
                try:
                    drv.switch_to.frame(frame)
                    # Use 2 second timeout to allow page to fully load (Close uses 0.5 for already-loaded pages)
                    pickup_links = WebDriverWait(drv, 2).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='pickupTask']"))
                    )
                    if pickup_links:
                        # Use JavaScript click - EXACT SAME AS CLOSE BUTTON
                        drv.execute_script("arguments[0].click();", pickup_links[0])
                        self.log_msg(f"[OK] Successfully clicked Pickup button in iframe {i}")
                        drv.switch_to.default_content()
                        time.sleep(2)  # Wait for pickup AJAX to complete
                        return True
                except Exception:
                    drv.switch_to.default_content()
                    continue
            
            self.log_msg("[WARN] No Pickup button found in any iframe")
            return False
            
        except Exception as e:
            self.log_msg(f"[WARN] Error clicking Pickup button: {e}")
            return False

    def _navigate_back_to_search(self):
        """Navigate back to the advanced search results"""
        try:
            # Switch back to main frame first
            drv = self.state.driver
            drv.switch_to.default_content()
            self.log_msg("[DEBUG] Switched to main frame for navigation")
            
            # Try to reopen workflow drawer
            try:
                drawer_handle = drv.find_element(By.ID, "taskHandle")
                drawer_handle.click()
                time.sleep(1)
                self.log_msg("[DEBUG] Navigation result: SUCCESS: Workflow drawer reopened")
            except Exception as e:
                self.log_msg(f"[DEBUG] Navigation result: FAILED: Could not reopen drawer: {e}")
                return False
            
            # Click Advanced tab
            try:
                adv_tab = drv.find_element(By.ID, "taskAdvancedView")
                adv_tab.click()
                time.sleep(1)
                self.log_msg("[OK] Successfully reopened workflow drawer and clicked Advanced tab")
                return True
            except Exception as e:
                self.log_msg(f"[WARN] Could not click Advanced tab: {e}")
                return False
                
        except Exception as e:
            self.log_msg(f"[ERR] Navigate Back to Search: {e}")
            return False

    def _extract_full_client_name(self, drv):
        """Extract the full client name from the Members box on the case details page"""
        try:
            # Look for client name in the Members section - specific to this page structure
            client_name_selectors = [
                # Look in the Members table for the client name link
                "//div[@class='cbb box_t2s']//h2[text()='Members']/following::table//td[2]//a",
                # Look for links in the Members section that contain names
                "//div[contains(@class, 'cbb') and .//h2[text()='Members']]//td//a[contains(@href, 'clientProfileControl')]",
                # Look for any link in the Members table that looks like a name
                "//div[contains(@class, 'cbb') and .//h2[text()='Members']]//td[2]//a",
                # Fallback: look for any table cell with a link that contains a name pattern
                "//table[@id='caseMemberTable']//td[2]//a"
            ]
            
            for selector in client_name_selectors:
                try:
                    elements = drv.find_elements(By.XPATH, selector)
                    for element in elements:
                        text = element.text.strip()
                        # Look for text that looks like a full name (contains spaces and letters)
                        if (text and len(text) > 5 and ' ' in text and 
                            any(c.isalpha() for c in text) and 
                            not any(word in text.lower() for word in ['case', 'id', 'status', 'date', 'time', 'self', 'client'])):
                            self.log_msg(f"[EXTRACT] Found client name in Members section: '{text}'")
                            return text
                except:
                    continue
            
            # Fallback: look for any text in the Members section that might be a name
            try:
                # Look for text patterns in the Members section
                members_elements = drv.find_elements(By.XPATH, "//div[contains(@class, 'cbb') and .//h2[text()='Members']]//td")
                for element in members_elements:
                    text = element.text.strip()
                    # Check if it looks like a full name (2+ words, mostly letters)
                    words = text.split()
                    if (len(words) >= 2 and 
                        all(word.replace('.', '').replace(',', '').isalpha() for word in words) and
                        len(text) > 5 and len(text) < 50 and
                        not any(word in text.lower() for word in ['self', 'client', 'phone', 'date'])):
                        self.log_msg(f"[EXTRACT] Found potential client name in Members: '{text}'")
                        return text
            except:
                pass
                
            self.log_msg("[EXTRACT] Could not find full client name in Members section")
            return "Unknown"
            
        except Exception as e:
            self.log_msg(f"[EXTRACT] Error extracting full client name: {e}")
            return "Unknown"

    def _extract_service_files_data(self, case_name="Unknown", case_id="Unknown"):
        """Extract data from the Service Files section"""
        try:
            drv = self._drv()
            
            # First, try to extract the full client name from the case details page
            full_client_name = self._extract_full_client_name(drv)
            if full_client_name and full_client_name != "Unknown":
                case_name = full_client_name
                self.log_msg(f"[EXTRACT] Found full client name: {case_name}")
            else:
                self.log_msg(f"[EXTRACT] Using partial case name: {case_name}")
            
            # Find the Service Files section - look for any table on the page
            service_files_section = None
            try:
                # Look for tables that might contain service files data
                tables = drv.find_elements(By.CSS_SELECTOR, "table")
                for table in tables:
                    if table.is_displayed():
                        service_files_section = table
                        break
            except:
                pass
            
            if not service_files_section:
                self.log_msg("[WARN] Service Files section not found")
                return None
            
            # Use the case information (now with full name if found)
            self.log_msg(f"[EXTRACT] Using case info: {case_name} (ID: {case_id})")
            
            # Find all rows and track counselor status (red vs green bubbles)
            counselor_status = {}  # {counselor_name: {'red': bool, 'green': bool}}
            
            try:
                all_rows = drv.find_elements(By.CSS_SELECTOR, "tr")
                self.log_msg(f"[DEBUG] Found {len(all_rows)} table rows")
                
                for row in all_rows:
                    try:
                        # Check for red status (statusClosed)
                        red_status_cells = row.find_elements(By.CSS_SELECTOR, "td.statusClosed")
                        has_red_status = len(red_status_cells) > 0
                        
                        # Check for green status (statusOpen)
                        green_status_cells = row.find_elements(By.CSS_SELECTOR, "td.statusOpen")
                        has_green_status = len(green_status_cells) > 0
                        
                        # Only process rows that have either red or green status
                        if has_red_status or has_green_status:
                            self.log_msg(f"[DEBUG] Found {'red' if has_red_status else 'green'} status row: {row.text[:100]}...")
                            
                            # Extract counselor name from the row
                            cells = row.find_elements(By.CSS_SELECTOR, "td")
                            counselor_name = None
                            
                            # Look for counselor name in cell 5 (index 4)
                            if len(cells) > 4:
                                cell_text = cells[4].text.strip()
                                if cell_text and cell_text not in ['0/1/1', '']:
                                    counselor_name = cell_text
                                    self.log_msg(f"[DEBUG] Found counselor: '{counselor_name}' with {'red' if has_red_status else 'green'} status")
                            
                            # Track the counselor's status
                            if counselor_name:
                                if counselor_name not in counselor_status:
                                    counselor_status[counselor_name] = {'red': False, 'green': False}
                                
                                if has_red_status:
                                    counselor_status[counselor_name]['red'] = True
                                if has_green_status:
                                    counselor_status[counselor_name]['green'] = True
                                    
                    except Exception as e:
                        self.log_msg(f"[DEBUG] Error processing row: {e}")
                        continue
                
                self.log_msg(f"[DEBUG] Counselor status tracking: {counselor_status}")
                
            except Exception as e:
                self.log_msg(f"[DEBUG] Error finding status rows: {e}")
                pass
            
            # Extract Primary Worker names - only include counselors with red status but NO green status
            primary_workers = []
            for counselor_name, status in counselor_status.items():
                has_red = status['red']
                has_green = status['green']
                
                if has_red and not has_green:
                    # Counselor has red status but no green status - add to removal list
                    primary_workers.append(counselor_name)
                    self.log_msg(f"[EXTRACT] Found Primary Worker (Red only): {counselor_name}")
                elif has_red and has_green:
                    # Counselor has both red and green status - green overrides red, do NOT add to removal list
                    self.log_msg(f"[EXTRACT] SKIPPING {counselor_name} - has both red and green status (green overrides red)")
                elif has_green and not has_red:
                    # Counselor has only green status - do NOT add to removal list
                    self.log_msg(f"[EXTRACT] SKIPPING {counselor_name} - has only green status (active counselor)")
                else:
                    # This shouldn't happen, but just in case
                    self.log_msg(f"[DEBUG] Counselor {counselor_name} has no clear status")
            
            # Create extracted data object
            extracted_data = ExtractedData(
                case_name=case_name,
                case_id=case_id,
                primary_workers=primary_workers,
                service_file_status="Closed",
                extraction_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            return extracted_data
            
        except Exception as e:
            self.log_msg(f"[ERR] Data extraction failed: {e}")
            if self.debug_var.get():
                import traceback
                self.log_msg(f"[DEBUG] Extraction error: {traceback.format_exc()}")
            return None

    def _export_csv(self):
        """Export extracted data to CSV file"""
        def run():
            try:
                if not self.state.extracted_data:
                    self.log_msg("[EXPORT] No data to export")
                    return
                
                # Use user-selected output directory (respects the output location setting)
                import os
                save_dir = self._get_export_dir()
                self.log_msg(f"[EXPORT] Using output directory: {save_dir}")
                
                # Generate filename with timestamp
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(save_dir, f"remove_counselor_data_{timestamp}.csv")
                
                # Ensure directory exists
                os.makedirs(save_dir, exist_ok=True)
                
                # Write CSV file
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ['Case Name', 'Case ID', 'Primary Workers', 'Service File Status', 'Extraction Date']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    
                    writer.writeheader()
                    for data in self.state.extracted_data:
                        writer.writerow({
                            'Case Name': data.case_name,
                            'Case ID': data.case_id,
                            'Primary Workers': '; '.join(data.primary_workers),
                            'Service File Status': data.service_file_status,
                            'Extraction Date': data.extraction_date
                        })
                
                self.log_msg(f"[EXPORT] ✅ CSV exported successfully: {filename}")
                self.log_msg(f"[EXPORT] Exported {len(self.state.extracted_data)} records")
                
                # Also create an Excel file with proper column widths
                try:
                    import pandas as pd
                    excel_filename = filename.replace('.csv', '.xlsx')
                    df = pd.DataFrame([{
                        'Case Name': data.case_name,
                        'Case ID': data.case_id,
                        'Primary Workers': '; '.join(data.primary_workers),
                        'Service File Status': data.service_file_status,
                        'Extraction Date': data.extraction_date
                    } for data in self.state.extracted_data])
                    
                    # Write to Excel with auto-adjusted column widths
                    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                        df.to_excel(writer, index=False, sheet_name='Extracted Data')
                        
                        # Auto-adjust column widths
                        worksheet = writer.sheets['Extracted Data']
                        for column in worksheet.columns:
                            max_length = 0
                            column_letter = column[0].column_letter
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                            adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                            worksheet.column_dimensions[column_letter].width = adjusted_width
                    
                    self.log_msg(f"[EXPORT] ✅ Excel file also created: {excel_filename}")
                except Exception as excel_e:
                    self.log_msg(f"[EXPORT] Excel creation failed (CSV still available): {excel_e}")
                
            except Exception as e:
                self.log_msg(f"[ERR] CSV export failed: {e}")
                if self.debug_var.get():
                    import traceback
                    self.log_msg(f"[DEBUG] Export error: {traceback.format_exc()}")
        threading.Thread(target=run, daemon=True).start()

    # ---------- IPS Uploader Methods ----------
    def _login_ips_therapy_notes(self):
        """Login to IPS Therapy Notes"""
        def run():
            try:
                username = self.ips_user.get().strip()
                password = self.ips_pass.get().strip()
                
                if not username or not password:
                    self.ips_uploader_log_msg("❌ Please enter both IPS username and password")
                    return
                
                self.ips_uploader_log_msg("🔐 Logging into IPS Therapy Notes...")
                
                # Initialize IPS Therapy Notes driver
                if not hasattr(self, 'ips_tn_driver') or self.ips_tn_driver is None:
                    self.ips_tn_driver = self._init_ips_therapy_notes_driver()
                
                # Navigate to IPS Therapy Notes using configurable URL
                ips_tn_url = self.ips_url.get().strip()
                if not ips_tn_url:
                    ips_tn_url = "https://www.therapynotes.com/app/login/IntegrityIPS/?r=%2fapp%2fpatients%2f"
                self.ips_uploader_log_msg(f"🌐 Navigating to IPS Therapy Notes: {ips_tn_url}")
                self.ips_tn_driver.get(ips_tn_url)
                time.sleep(2)
                
                # Debug: Log current page info
                current_url = self.ips_tn_driver.current_url
                page_title = self.ips_tn_driver.title
                self.ips_uploader_log_msg(f"📍 Current URL: {current_url}")
                self.ips_uploader_log_msg(f"📄 Page Title: {page_title}")
                
                # Find and fill username field
                username_field = None
                username_selectors = [
                    (By.NAME, "Username"),
                    (By.ID, "Login__Username"),
                    (By.NAME, "username"),
                    (By.ID, "username"),
                    (By.CSS_SELECTOR, "input[type='text']"),
                    (By.CSS_SELECTOR, "input[placeholder*='username' i]"),
                    (By.CSS_SELECTOR, "input[placeholder*='user' i]"),
                    (By.XPATH, "//input[@type='text']"),
                    (By.XPATH, "//input[contains(@placeholder, 'username') or contains(@placeholder, 'user')]")
                ]
                
                for selector_type, selector_value in username_selectors:
                    try:
                        username_field = WebDriverWait(self.ips_tn_driver, 2).until(
                            EC.presence_of_element_located((selector_type, selector_value))
                        )
                        self.ips_uploader_log_msg(f"✅ Found IPS username field with: {selector_type} = {selector_value}")
                        break
                    except:
                        continue
                
                if not username_field:
                    self.ips_uploader_log_msg("❌ Could not find IPS username field")
                    return
                
                username_field.clear()
                username_field.send_keys(username)
                self.ips_uploader_log_msg("✅ IPS Username entered")
                
                # Find and fill password field
                password_field = None
                password_selectors = [
                    (By.NAME, "Password"),
                    (By.ID, "Login__Password"),
                    (By.NAME, "password"),
                    (By.ID, "password"),
                    (By.CSS_SELECTOR, "input[type='password']"),
                    (By.CSS_SELECTOR, "input[placeholder*='password' i]"),
                    (By.XPATH, "//input[@type='password']"),
                    (By.XPATH, "//input[contains(@placeholder, 'password')]")
                ]
                
                for selector_type, selector_value in password_selectors:
                    try:
                        password_field = WebDriverWait(self.ips_tn_driver, 2).until(
                            EC.presence_of_element_located((selector_type, selector_value))
                        )
                        self.ips_uploader_log_msg(f"✅ Found IPS password field with: {selector_type} = {selector_value}")
                        break
                    except:
                        continue
                
                if not password_field:
                    self.ips_uploader_log_msg("❌ Could not find IPS password field")
                    return
                
                password_field.clear()
                password_field.send_keys(password)
                self.ips_uploader_log_msg("✅ IPS Password entered")
                
                # Find and click login button
                login_button = None
                login_selectors = [
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.CSS_SELECTOR, "input[type='submit']"),
                    (By.XPATH, "//button[contains(text(), 'Login')]"),
                    (By.XPATH, "//input[@value='Login']"),
                    (By.XPATH, "//button[contains(text(), 'Sign In')]"),
                    (By.XPATH, "//input[@value='Sign In']")
                ]
                
                for selector_type, selector_value in login_selectors:
                    try:
                        login_button = WebDriverWait(self.ips_tn_driver, 2).until(
                            EC.element_to_be_clickable((selector_type, selector_value))
                        )
                        self.ips_uploader_log_msg(f"✅ Found IPS login button with: {selector_type} = {selector_value}")
                        break
                    except:
                        continue
                
                if not login_button:
                    self.ips_uploader_log_msg("❌ Could not find IPS login button")
                    return
                
                login_button.click()
                self.ips_uploader_log_msg("✅ Clicked IPS login button")
                
                # Wait for login to complete
                time.sleep(3)
                
                # Check if login was successful
                current_url_after_login = self.ips_tn_driver.current_url
                self.ips_uploader_log_msg(f"📍 URL after login: {current_url_after_login}")
                
                if "login" not in current_url_after_login.lower():
                    self.ips_uploader_log_msg("✅ Successfully logged into IPS Therapy Notes!")
                    self.ips_uploader_status_label.config(text="✅ Logged into IPS Therapy Notes")
                    
                    # Navigate to Patients page - SAME AS REGULAR UPLOADER
                    self.ips_uploader_log_msg("🔍 Navigating to Patients page...")
                    try:
                        # Find and click the Patients button
                        patients_button = self.ips_tn_driver.find_element(By.XPATH, "//span[text()='Patients']")
                        patients_button.click()
                        self.ips_uploader_log_msg("✅ Clicked Patients button")
                        
                        time.sleep(1.5)  # Wait for page to load
                        self.ips_uploader_log_msg("✅ Successfully navigated to Patients page")
                        self.ips_uploader_status_label.config(text="On Patients page - Ready for CSV processing")
                        
                        # Automatically start the IPS upload process
                        self.ips_uploader_log_msg("🚀 Starting IPS upload process...")
                        self._start_ips_upload_process()
                        
                    except Exception as nav_e:
                        self.ips_uploader_log_msg(f"❌ Failed to navigate to Patients: {nav_e}")
                else:
                    self.ips_uploader_log_msg("❌ Login failed - still on login page")
                    self.ips_uploader_status_label.config(text="❌ Login failed")
                
            except Exception as e:
                self.ips_uploader_log_msg(f"❌ IPS login failed: {e}")
                self.ips_uploader_status_label.config(text="❌ Login failed")
                if self.ips_debug_mode_var.get():
                    import traceback
                    self.ips_uploader_log_msg(f"[DEBUG] IPS login error: {traceback.format_exc()}")
        
        threading.Thread(target=run, daemon=True).start()

    def _init_ips_therapy_notes_driver(self):
        """Initialize IPS Therapy Notes driver"""
        try:
            self.ips_uploader_log_msg("🚀 Initializing IPS Therapy Notes driver...")
            
            # Chrome options for IPS Therapy Notes
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Initialize driver
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.ips_uploader_log_msg("✅ IPS Therapy Notes driver initialized successfully")
            return driver
            
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to initialize IPS Therapy Notes driver: {e}")
            return None

    def _start_ips_upload_process(self):
        """Start the IPS upload process - MIRRORS regular uploader exactly"""
        def run():
            try:
                # Get CSV file path
                csv_file_path = self.ips_csv_file_var.get().strip()
                
                if not csv_file_path:
                    self.ips_uploader_log_msg("❌ Please select a CSV file first")
                    return
                
                if not os.path.exists(csv_file_path):
                    self.ips_uploader_log_msg(f"❌ CSV file not found: {csv_file_path}")
                    return
                
                self.ips_uploader_log_msg(f"📁 Processing CSV file: {csv_file_path}")
                
                # Read CSV file - SAME AS REGULAR UPLOADER
                import pandas as pd
                try:
                    df = pd.read_csv(csv_file_path, encoding='utf-8')
                except UnicodeDecodeError:
                    self.ips_uploader_log_msg("⚠️ UTF-8 failed, trying latin-1 encoding...")
                    df = pd.read_csv(csv_file_path, encoding='latin-1')
                
                self.ips_uploader_log_msg(f"📊 Found {len(df)} records in CSV file")
                
                # Filter for records that have IPS counselors (flexible detection)
                ips_records = []
                for index, row in df.iterrows():
                    primary_workers = str(row['Primary Workers'])
                    import re
                    if re.search(r'\bIPS\b', primary_workers, re.IGNORECASE):
                        ips_records.append(row)
                
                self.ips_uploader_log_msg(f"🏥 Found {len(ips_records)} records with IPS counselors")
                
                if not ips_records:
                    self.ips_uploader_log_msg("ℹ️ No IPS counselors found in CSV - nothing to process")
                    return
                
                # Process each record - MIRROR REGULAR UPLOADER EXACTLY
                results = []
                for i, record in enumerate(ips_records):
                    try:
                        self.ips_uploader_log_msg(f"🔄 Processing record {i+1}/{len(ips_records)}: {record['Case Name']}")
                        
                        # Extract ALL counselors from Primary Workers column - BULLETPROOF EXTRACTION
                        primary_workers = str(record['Primary Workers'])
                        import re
                        
                        # Split by semicolon and clean up each counselor
                        all_counselors = [worker.strip() for worker in primary_workers.split(';') if worker.strip()]
                        
                        # Find counselors that have ANY variation of IPS in their name
                        ips_counselors_raw = []
                        for counselor in all_counselors:
                            # Check for IPS in various formats: "IPS", "-IPS", "- IPS", "IPS-", " IPS ", etc.
                            if re.search(r'[-,\s]*IPS[-,\s]*', counselor, re.IGNORECASE):
                                ips_counselors_raw.append(counselor)
                                self.ips_uploader_log_msg(f"🔍 DEBUG: Found IPS counselor: '{counselor}'")
                        
                        # Strip "IPS" from counselor names for matching in Therapy Notes
                        ips_counselors_clean = []
                        for counselor in ips_counselors_raw:
                            # Handle different formats:
                            # "Santana-IPS, Michelle" -> "Michelle Santana"
                            # "Brown-IPS" -> "Brown" (no first name)
                            
                            # First, remove IPS from anywhere in the name (but preserve commas)
                            # Handle "Monroe-IPS, Cheryl" -> "Monroe, Cheryl"
                            clean_name = re.sub(r'-IPS\b', '', counselor, flags=re.IGNORECASE).strip()
                            self.ips_uploader_log_msg(f"🔍 DEBUG: After IPS removal: '{counselor}' -> '{clean_name}'")
                            
                            # Handle "Last-IPS, First" format -> "First Last"
                            if ',' in clean_name:
                                self.ips_uploader_log_msg(f"🔍 DEBUG: Found comma in '{clean_name}', splitting...")
                                parts = clean_name.split(',')
                                self.ips_uploader_log_msg(f"🔍 DEBUG: Split into parts: {parts}")
                                if len(parts) == 2:
                                    last_name = parts[0].strip()
                                    first_name = parts[1].strip()
                                    self.ips_uploader_log_msg(f"🔍 DEBUG: last_name='{last_name}', first_name='{first_name}'")
                                    if first_name and last_name:  # Both parts exist
                                        clean_name = f"{first_name} {last_name}"  # First Last format
                                        self.ips_uploader_log_msg(f"🔍 DEBUG: Converted '{counselor}' -> '{clean_name}' (Last,First -> First Last)")
                                    elif last_name:  # Only last name exists
                                        clean_name = last_name
                            else:
                                self.ips_uploader_log_msg(f"🔍 DEBUG: No comma found in '{clean_name}', keeping as-is")
                            
                            # Remove any trailing commas or semicolons
                            clean_name = re.sub(r'[,;]+$', '', clean_name).strip()
                            
                            if clean_name:  # Only add if there's still a name left
                                ips_counselors_clean.append(clean_name)
                                self.ips_uploader_log_msg(f"🔍 DEBUG: Cleaned counselor name: '{counselor}' -> '{clean_name}'")
                        
                        self.ips_uploader_log_msg(f"🏥 IPS counselors to remove (cleaned): {ips_counselors_clean}")
                        
                        # Set current case data for processing
                        self.current_case_name = record['Case Name']
                        self.current_primary_workers = ips_counselors_clean  # Use cleaned names for matching
                        
                        # Use EXACT SAME flow as regular uploader but with IPS driver
                        if self._search_patient_ips(record['Case Name']):
                            # The _search_patient_ips function now handles the complete flow:
                            # 1. Search for patient
                            # 2. Navigate to clinicians tab  
                            # 3. Remove counselors
                            results.append({
                                'Case Name': record['Case Name'],
                                'Case ID': record['Case ID'],
                                'IPS Counselors': '; '.join(ips_counselors_raw),  # Show original names in results
                                'Process Status': 'SUCCESS',
                                'Message': 'Successfully removed IPS counselors'
                            })
                            self.ips_uploader_log_msg(f"✅ Successfully processed: {record['Case Name']}")
                        else:
                            results.append({
                                'Case Name': record['Case Name'],
                                'Case ID': record['Case ID'],
                                'IPS Counselors': '; '.join(ips_counselors_raw),
                                'Process Status': 'FAILED',
                                'Message': 'Failed to remove IPS counselors'
                            })
                            self.ips_uploader_log_msg(f"❌ Failed to process: {record['Case Name']}")
                        
                        # Return to Patients page for next patient
                        self._return_to_patients_page_ips()
                        
                        # Wait between patients
                        time.sleep(2)
                        
                    except Exception as e:
                        self.ips_uploader_log_msg(f"❌ Error processing {record['Case Name']}: {e}")
                        results.append({
                            'Case Name': record['Case Name'],
                            'Case ID': record['Case ID'],
                            'IPS Counselors': '; '.join(ips_counselors_raw) if 'ips_counselors_raw' in locals() else 'Unknown',
                            'Process Status': 'FAILED',
                            'Message': f'Error: {str(e)}'
                        })
                
                # Create results CSV
                self._create_ips_results_csv(results, csv_file_path)
                
                self.ips_uploader_log_msg("🎉 IPS upload process completed!")
                self.ips_uploader_status_label.config(text="✅ IPS upload completed")
                
            except Exception as e:
                self.ips_uploader_log_msg(f"❌ IPS upload process failed: {e}")
                self.ips_uploader_status_label.config(text="❌ IPS upload failed")
                if self.ips_debug_mode_var.get():
                    import traceback
                    self.ips_uploader_log_msg(f"[DEBUG] IPS upload error: {traceback.format_exc()}")
        
        threading.Thread(target=run, daemon=True).start()

    def _search_patient_ips(self, case_name):
        """Search for a patient in IPS Therapy Notes with middle initial fallback"""
        try:
            self.ips_uploader_log_msg(f"🔍 Searching for patient: {case_name}")
            
            # First attempt: Try with full name (including middle initial if present)
            if self._attempt_patient_search_ips(case_name):
                return True
            
            # Second attempt: If first search failed and name has middle initial, try without it
            if self._has_middle_initial(case_name):
                name_without_middle = self._remove_middle_initial(case_name)
                self.ips_uploader_log_msg(f"🔄 First search failed, trying without middle initial: {name_without_middle}")
                if self._attempt_patient_search_ips(name_without_middle):
                    return True
            
            self.ips_uploader_log_msg("❌ Both search attempts failed")
            return False
                    
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Error searching for patient: {e}")
            return False

    def _has_middle_initial(self, name):
        """Check if name has a middle initial (single letter followed by period)"""
        import re
        # Pattern: word, single letter with period, word
        pattern = r'\b\w+\s+[A-Z]\.\s+\w+\b'
        return bool(re.search(pattern, name))

    def _remove_middle_initial(self, name):
        """Remove middle initial from name (e.g., 'John M. Smith' -> 'John Smith')"""
        import re
        # Remove single letter with period: "M." -> ""
        cleaned = re.sub(r'\s+[A-Z]\.\s+', ' ', name)
        # Clean up extra spaces
        return ' '.join(cleaned.split())

    def _attempt_patient_search_ips(self, case_name):
        """Attempt to search for a patient with the given name"""
        try:
            # Format the name for search (remove periods from middle initials)
            search_name = self._format_name_for_search(case_name)
            self.ips_uploader_log_msg(f"🔍 Formatted search term: {search_name}")
            
            # Find the patient search input field
            search_input = self.ips_tn_driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
            search_input.clear()
            search_input.send_keys(search_name)  # Use formatted name
            self.ips_uploader_log_msg(f"✅ Entered search term: {search_name}")
            
            # Wait for dropdown to appear
            time.sleep(1.5)  # Increased wait time for dropdown
            
            # Wait for the dropdown container to appear
            try:
                dropdown_container = WebDriverWait(self.ips_tn_driver, 15).until(
                    EC.presence_of_element_located((By.ID, "ContentBubbleResultsContainer"))
                )
                self.ips_uploader_log_msg("✅ Dropdown results appeared")
                
                # Find all patient options in the dropdown
                patient_options = dropdown_container.find_elements(By.TAG_NAME, "div")
                self.ips_uploader_log_msg(f"📋 Found {len(patient_options)} options in dropdown")
                
                if not patient_options:
                    self.ips_uploader_log_msg("❌ No dropdown options found")
                    return False
            except:
                self.ips_uploader_log_msg("❌ Dropdown did not appear - search failed")
                return False
            
            # INTELLIGENT MATCHING - Like a smart person would do
            best_match = None
            best_score = 0
            match_type = ""
            
            for option in patient_options:
                option_text = option.text.strip()
                if not option_text:
                    continue
                    
                self.ips_uploader_log_msg(f"🔍 Checking option: '{option_text}'")
                
                # Extract just the name part (before DOB if present)
                name_part = option_text.split(' DOB:')[0].strip()
                
                # Calculate match score (higher is better)
                score = 0
                current_match_type = ""
                
                # 1. EXACT MATCH (highest priority)
                if name_part.lower() == search_name.lower():
                    score = 100
                    current_match_type = "exact"
                
                # 2. EXACT MATCH WITH DOB (very high priority)
                elif option_text.lower() == search_name.lower():
                    score = 95
                    current_match_type = "exact_with_dob"
                
                # 3. CONTAINS FULL NAME (high priority)
                elif search_name.lower() in name_part.lower():
                    score = 80
                    current_match_type = "contains_full"
                
                # 4. SMART PARTIAL MATCHING (medium-high priority)
                elif self._smart_name_match_ips(search_name, name_part):
                    score = 70
                    current_match_type = "smart_partial"
                
                # 5. FIRST AND LAST NAME MATCH (medium priority)
                elif self._first_last_match_ips(search_name, name_part):
                    score = 60
                    current_match_type = "first_last"
                
                # 6. ANY WORD MATCH (low priority)
                elif any(word.lower() in name_part.lower() for word in search_name.split() if len(word) > 2):
                    score = 30
                    current_match_type = "word_match"
                
                # 7. SIMILAR SOUNDING (very low priority)
                elif self._similar_sound_ips(search_name, name_part):
                    score = 20
                    current_match_type = "similar_sound"
                
                if score > best_score:
                    best_match = option
                    best_score = score
                    match_type = current_match_type
                    self.ips_uploader_log_msg(f"🎯 New best match: '{option_text}' (score: {score}, type: {match_type})")
            
            # Select the best match if we found one
            if best_match and best_score >= 20:  # Minimum threshold
                self.ips_uploader_log_msg(f"✅ Selected best match: '{best_match.text}' (score: {best_score}, type: {match_type})")
                
                # Try to click the dropdown option - only try once to avoid stale element issues
                patient_selected = False
                try:
                    # Try regular click first
                    best_match.click()
                    self.ips_uploader_log_msg("✅ Clicked dropdown option")
                    
                    # Wait for navigation to patient page
                    time.sleep(2)
                    
                    # Verify we're on the patient page by looking for patient-specific elements
                    try:
                        # Look for multiple possible indicators that we're on a patient page
                        patient_indicators = [
                            "//span[text()='Clinicians']",
                            "//span[text()='Demographics']", 
                            "//span[text()='Appointments']",
                            "//div[contains(@class, 'patient-header')]",
                            "//h1[contains(text(), 'Patient')]"
                        ]
                        
                        found_indicator = False
                        for indicator in patient_indicators:
                            try:
                                self.ips_tn_driver.find_element(By.XPATH, indicator)
                                found_indicator = True
                                self.ips_uploader_log_msg(f"✅ Confirmed on patient page using indicator: {indicator}")
                                break
                            except:
                                continue
                        
                        if found_indicator:
                            patient_selected = True
                            self.ips_uploader_log_msg("✅ Patient selected successfully")
                        else:
                            self.ips_uploader_log_msg("⚠️ Clicked but not on patient page - trying fallback")
                            # Fallback: try pressing Enter on search field
                            search_input.send_keys(Keys.RETURN)
                            time.sleep(2)
                            patient_selected = True
                            self.ips_uploader_log_msg("✅ Used Enter fallback - assuming patient selected")
                            
                    except Exception as verify_e:
                        self.ips_uploader_log_msg(f"⚠️ Could not verify patient page: {verify_e}")
                        # Still assume it worked and continue
                        patient_selected = True
                        self.ips_uploader_log_msg("✅ Assuming patient selected (verification failed)")
                            
                except Exception as click_e:
                    self.ips_uploader_log_msg(f"❌ Click failed: {click_e}")
                    # Fallback: try pressing Enter on search field
                    try:
                        search_input.send_keys(Keys.RETURN)
                        time.sleep(2)
                        patient_selected = True
                        self.ips_uploader_log_msg("✅ Used Enter fallback after click failure")
                    except Exception as enter_e:
                        self.ips_uploader_log_msg(f"❌ Enter fallback also failed: {enter_e}")
                
                if patient_selected:
                    # Navigate to Clinicians tab (this will also handle counselor removal)
                    self._navigate_to_clinicians_tab_ips()
                    return True
                else:
                    self.ips_uploader_log_msg("❌ All methods failed for patient selection")
                    return False
            else:
                self.ips_uploader_log_msg(f"❌ No suitable match found (best score: {best_score})")
                return False
                    
        except Exception as dropdown_e:
            self.ips_uploader_log_msg(f"❌ Dropdown selection failed: {dropdown_e}")
            # Fallback: try pressing Enter
            search_input.send_keys(Keys.RETURN)
            self.ips_uploader_log_msg("🔄 Fallback: Pressed Enter to search")
            time.sleep(2)
            return True  # Assume it worked with Enter
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to search for patient: {e}")
            return False

    def _smart_name_match_ips(self, search_name, option_name):
        """Smart name matching that handles common variations"""
        search_words = [word.lower().strip() for word in search_name.split() if len(word) > 1]
        option_words = [word.lower().strip() for word in option_name.split() if len(word) > 1]
        
        # Check if all search words are in option words (order doesn't matter)
        return all(any(search_word in option_word or option_word in search_word for option_word in option_words) for search_word in search_words)

    def _first_last_match_ips(self, search_name, option_name):
        """Check if first and last names match regardless of order"""
        search_words = [word.lower().strip() for word in search_name.split() if len(word) > 1]
        option_words = [word.lower().strip() for word in option_name.split() if len(word) > 1]
        
        if len(search_words) >= 2 and len(option_words) >= 2:
            # Check if first and last names match
            first_match = search_words[0] in option_words[0] or option_words[0] in search_words[0]
            last_match = search_words[-1] in option_words[-1] or option_words[-1] in search_words[-1]
            return first_match and last_match
        
        return False

    def _similar_sound_ips(self, search_name, option_name):
        """Check if names sound similar (basic implementation)"""
        # Remove common suffixes and prefixes
        search_clean = search_name.lower().replace('jr', '').replace('sr', '').replace('ii', '').replace('iii', '').strip()
        option_clean = option_name.lower().replace('jr', '').replace('sr', '').replace('ii', '').replace('iii', '').strip()
        
        # Check if they share significant characters
        search_chars = set(search_clean.replace(' ', ''))
        option_chars = set(option_clean.replace(' ', ''))
        
        if len(search_chars) > 0 and len(option_chars) > 0:
            similarity = len(search_chars.intersection(option_chars)) / len(search_chars.union(option_chars))
            return similarity > 0.6  # 60% character overlap
        
        return False

    def _close_any_modal_dialogs_ips(self):
        """Close any modal dialogs that might be blocking navigation"""
        try:
            # Look for common modal dialog close buttons
            close_selectors = [
                "//div[contains(@class, 'Dialog')]//button[contains(text(), 'Close')]",
                "//div[contains(@class, 'Dialog')]//button[contains(text(), 'OK')]",
                "//div[contains(@class, 'Dialog')]//button[contains(@class, 'close')]",
                "//div[contains(@class, 'Dialog')]//a[contains(text(), 'Close')]",
                "//div[contains(@class, 'Dialog')]//span[contains(@class, 'close')]",
                "//div[@class='Dialog']//button",
                "//div[contains(@style, 'z-index')]//button[contains(text(), 'Close')]"
            ]
            
            for selector in close_selectors:
                try:
                    close_button = self.ips_tn_driver.find_element(By.XPATH, selector)
                    if close_button.is_displayed():
                        close_button.click()
                        self.ips_uploader_log_msg("🔧 Closed blocking modal dialog")
                        time.sleep(0.5)
                        return True
                except:
                    continue
            
            # Try pressing ESC key to close dialogs
            try:
                from selenium.webdriver.common.keys import Keys
                body = self.ips_tn_driver.find_element(By.TAG_NAME, "body")
                body.send_keys(Keys.ESCAPE)
                self.ips_uploader_log_msg("🔧 Sent ESC key to close any dialogs")
                time.sleep(0.5)
                return True
            except:
                pass
                
        except Exception as e:
            # Silent fail - this is just a helper function
            pass
        return False

    def _navigate_to_clinicians_tab_ips(self):
        """Navigate to the Clinicians tab for the selected patient - EXACT COPY of regular uploader"""
        try:
            self.ips_uploader_log_msg("👥 Navigating to Clinicians tab...")
            
            # CRITICAL: Close any modal dialogs before attempting navigation
            self._close_any_modal_dialogs_ips()
            
            # Find and click the Clinicians tab using multiple selectors
            clinicians_selectors = [
                "//a[contains(text(), 'Clinicians')]",
                "//a[@data-tab-id='Clinicians']",
                "//span[contains(text(), 'Clinicians')]",
                "//button[contains(text(), 'Clinicians')]"
            ]
            
            clinicians_tab = None
            for selector in clinicians_selectors:
                try:
                    clinicians_tab = self.ips_tn_driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue
            
            if clinicians_tab:
                clinicians_tab.click()
                self.ips_uploader_log_msg("✅ Clicked Clinicians tab")
                
                # CRITICAL: Wait for Clinicians tab data to actually load
                time.sleep(2)  # Increased from 0.5 to 2 seconds
                
                # Wait for counselor data to appear (look for staff links)
                try:
                    WebDriverWait(self.ips_tn_driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/app/staff/edit/')]"))
                    )
                    self.ips_uploader_log_msg("✅ Successfully navigated to Clinicians tab (counselor data loaded)")
                except:
                    # If no staff links found, that's okay - might be no counselors
                    self.ips_uploader_log_msg("✅ Successfully navigated to Clinicians tab (no counselors or still loading)")
                    time.sleep(1)  # Extra wait just in case
                
                # Review counselors and handle removal if needed
                self._review_and_remove_counselors_ips()
            else:
                self.ips_uploader_log_msg("❌ Could not find Clinicians tab")
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to navigate to Clinicians tab: {e}")

    def _remove_counselors_ips(self):
        """Remove counselors - EXACT COPY of regular uploader's counselor removal logic"""
        try:
            self.ips_uploader_log_msg("🔍 Reviewing counselors on Clinicians tab...")
            self.ips_uploader_log_msg(f"🎯 Looking for counselors to remove: {', '.join(self.current_primary_workers)}")
            
            # Click Edit button to enter edit mode
            self.ips_uploader_log_msg("🔍 Clicking Edit button to verify no counselors need removal...")
            self.ips_uploader_log_msg("✏️ Looking for Edit button...")
            
            # Find Edit button - SAME SELECTORS AS REGULAR
            edit_button = None
            edit_selectors = [
                "//psy-button[@class='ClickToEditBtn hydrated' and contains(., 'Edit')]",
                "//button[contains(text(), 'Edit')]",
                "//input[@value='Edit']"
            ]
            
            for selector in edit_selectors:
                try:
                    edit_button = self.ips_tn_driver.find_element(By.XPATH, selector)
                    self.ips_uploader_log_msg(f"✅ Found Edit button with selector: {selector}")
                    break
                except:
                    continue
            
            if edit_button:
                # Scroll to button if needed
                self.ips_tn_driver.execute_script("arguments[0].scrollIntoView(true);", edit_button)
                time.sleep(0.2)
                
                # Try to click Edit button
                try:
                    edit_button.click()
                    self.ips_uploader_log_msg("✅ Successfully clicked Edit button")
                except:
                    # Try JavaScript click as fallback
                    self.ips_tn_driver.execute_script("arguments[0].click();", edit_button)
                    self.ips_uploader_log_msg("✅ Successfully clicked Edit button (JavaScript)")
                
                time.sleep(1)  # Wait for edit mode to activate
                
                # Look for counselor X buttons to remove
                self.ips_uploader_log_msg("🗑️ Looking for counselor X buttons to remove...")
                self.ips_uploader_log_msg("📋 NOTE: Will SKIP any counselors with '- IPS' suffix (they belong to IPS agency)")
                self.ips_uploader_log_msg(f"🎯 Looking for counselors to remove (keeping CSV workers: {', '.join(self.current_primary_workers)})")
                
            # Find all X buttons - SAME SELECTORS AS REGULAR
                x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//button[@title='Remove Clinician']")
                if not x_buttons:
                    x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//span[@class='button-text-input-mimic float-right']//button")
                if not x_buttons:
                    x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//div[@class='fa-icon close']")
                
                self.ips_uploader_log_msg(f"🔍 Found {len(x_buttons)} X buttons on page")
                
                removed_count = 0
                for x_button in x_buttons:
                    try:
                        # Get counselor name associated with this X button
                        counselor_text = self._extract_counselor_name_ips(x_button)
                        
                        if not counselor_text:
                            continue
                        
                        self.ips_uploader_log_msg(f"🔍 Checking X button: '{counselor_text}'")
                        
                        # Check if this counselor is in our removal list
                        should_remove = False
                        matched_counselor = None
                        
                        for csv_counselor in self.current_primary_workers:
                            # CRITICAL SAFETY: Use STRICT EXACT MATCHING to prevent wrong removals
                            counselor_normalized = counselor_text.lower().strip()
                            csv_counselor_normalized = csv_counselor.lower().strip()
                            
                            # Extract name components (remove punctuation for comparison)
                            counselor_clean = counselor_normalized.replace(",", "").replace("-", " ").strip()
                            csv_clean = csv_counselor_normalized.replace(",", "").replace("-", " ").strip()
                            
                            # Split into words for STRICT comparison
                            counselor_words = set(counselor_clean.split())
                            csv_words = set(csv_clean.split())
                            
                            # Remove generic words that might cause false matches
                            ignore_words = {'ips', 'counselor', 'therapist', 'worker', 'staff'}
                            counselor_words = {w for w in counselor_words if w not in ignore_words}
                            csv_words = {w for w in csv_words if w not in ignore_words}
                            
                            # STRICT MATCH: ALL words must match exactly (prevents "Cheryl Monroe" from matching "Cheryl Smith")
                            if counselor_words == csv_words and len(csv_words) >= 2:
                                matched_counselor = csv_counselor
                                self.ips_uploader_log_msg(f"✅ EXACT MATCH: '{counselor_text}' matches CSV '{csv_counselor}'")
                                should_remove = True
                                break
                            
                            # Also check for "Last, First" vs "First Last" format with FULL name match
                            if ',' in csv_counselor_normalized:
                                parts = csv_counselor_normalized.split(',')
                                if len(parts) == 2:
                                    last_name = parts[0].strip()
                                    first_name = parts[1].strip()
                                    reversed_format = f"{first_name} {last_name}"
                                    reversed_words = set(reversed_format.split())
                                    
                                    # STRICT MATCH: All words must match exactly
                                    if reversed_words == counselor_words:
                                        matched_counselor = csv_counselor
                                        self.ips_uploader_log_msg(f"✅ EXACT MATCH (reversed): '{counselor_text}' matches CSV '{csv_counselor}'")
                                        should_remove = True
                                        break
                        
                        if should_remove:
                            self.ips_uploader_log_msg(f"🗑️ REMOVING: '{counselor_text}' matches CSV worker '{matched_counselor}' - clicking X")
                            try:
                                x_button.click()
                                self.ips_uploader_log_msg(f"🗑️ Removed counselor: {counselor_text}")
                                removed_count += 1
                                time.sleep(0.5)  # Wait between removals
                            except Exception as e:
                                self.ips_uploader_log_msg(f"❌ Failed to click X button for {counselor_text}: {e}")
                        else:
                            self.ips_uploader_log_msg(f"✅ KEEPING: '{counselor_text}' is NOT in CSV - NOT removing")
                    
                    except Exception as e:
                        self.ips_uploader_log_msg(f"❌ Error processing X button: {e}")
                        continue
                
                self.ips_uploader_log_msg(f"✅ Successfully removed {removed_count} counselor(s)")
                
                # Save changes
                self.ips_uploader_log_msg("💾 Looking for Save Changes button...")
                save_button = self.ips_tn_driver.find_element(By.XPATH, "//input[@id='CommonFooter__SaveChanges-Button']")
                save_button.click()
                self.ips_uploader_log_msg("✅ Clicked Save Changes button")
                time.sleep(1.5)
                self.ips_uploader_log_msg("✅ Successfully saved counselor changes")
                
                return True
            else:
                self.ips_uploader_log_msg("❌ Could not find Edit button")
                return False
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to remove counselors: {e}")
            return False

    def _review_and_remove_counselors_ips(self):
        """Review counselors on the Clinicians tab and remove matching ones from CSV - EXACT COPY of regular uploader"""
        try:
            self.ips_uploader_log_msg("🔍 Reviewing counselors on Clinicians tab...")
            
            # Get current patient's primary workers from CSV data
            current_case_name = getattr(self, 'current_case_name', 'Unknown')
            current_primary_workers = getattr(self, 'current_primary_workers', [])
            
            if not current_primary_workers:
                self.ips_uploader_log_msg("ℹ️ No primary workers to remove for this patient")
                return
            
            self.ips_uploader_log_msg(f"🎯 Looking for counselors to remove: {', '.join(current_primary_workers)}")
            
            # Look for counselor names on the page using a more dynamic approach
            # First, try to find counselor elements by looking for common patterns
            counselor_elements = []
            
            # Try multiple selectors to find counselor elements
            counselor_selectors = [
                "//div[contains(@class, 'counselor') or contains(@class, 'clinician') or contains(@class, 'staff')]",
                "//span[contains(@class, 'counselor') or contains(@class, 'clinician') or contains(@class, 'staff')]",
                "//div[contains(@class, 'name') or contains(@class, 'user')]",
                "//span[contains(@class, 'name') or contains(@class, 'user')]",
                "//div[contains(text(), ',') and string-length(text()) > 5]",  # Names with commas
                "//span[contains(text(), ',') and string-length(text()) > 5]",
                "//div[contains(@class, 'person') or contains(@class, 'member')]",
                "//span[contains(@class, 'person') or contains(@class, 'member')]"
            ]
            
            for selector in counselor_selectors:
                try:
                    elements = self.ips_tn_driver.find_elements(By.XPATH, selector)
                    counselor_elements.extend(elements)
                except:
                    continue
            
            # Remove duplicates
            counselor_elements = list(set(counselor_elements))
            
            self.ips_uploader_log_msg(f"🔍 Found {len(counselor_elements)} potential counselor elements")
            
            counselors_found = []
            for i, element in enumerate(counselor_elements):
                try:
                    text = element.text.strip()
                    self.ips_uploader_log_msg(f"🔍 Element {i+1}: '{text}'")
                    # Filter for meaningful text that looks like names
                    if (text and len(text) > 2 and 
                        not text.lower() in ['edit', 'delete', 'remove', 'add', 'save', 'cancel', 'close', 'user options', 'contact us', 'log out', 'no future appt'] and
                        not text.startswith('http') and
                        not text.startswith('www') and
                        not text.isdigit()):
                        counselors_found.append(text)
                except:
                    continue
            
            self.ips_uploader_log_msg(f"👥 Found {len(counselors_found)} counselor elements on page")
            self.ips_uploader_log_msg(f"📋 Counselor names found: {counselors_found}")
            
            # Check if any of the found counselors match our CSV data
            matching_counselors = []
            for counselor in counselors_found:
                for primary_worker in current_primary_workers:
                    self.ips_uploader_log_msg(f"🔍 Comparing '{counselor}' with '{primary_worker}'")
                    
                    # Normalize both names for comparison
                    counselor_normalized = counselor.lower().strip()
                    worker_normalized = primary_worker.lower().strip()
                    
                    # Check for direct matches
                    if (worker_normalized in counselor_normalized or 
                        counselor_normalized in worker_normalized):
                        matching_counselors.append(counselor)
                        self.ips_uploader_log_msg(f"✅ Match found: '{counselor}' matches '{primary_worker}' (direct)")
                        break
                    
                    # Check for "LastFirst" vs "First Last" format (like CasimirTatiana -> Tatiana Casimir)
                    import re
                    csv_parts = re.findall(r'[A-Z][a-z]*', primary_worker)
                    if len(csv_parts) >= 2:
                        # Try both orders: LastFirst and FirstLast
                        csv_reversed1 = f"{csv_parts[1]} {csv_parts[0]}"  # First Last
                        csv_reversed2 = f"{csv_parts[0]} {csv_parts[1]}"  # Last First
                        
                        self.ips_uploader_log_msg(f"🔍 DEBUG: Comparing '{counselor_normalized}' with '{csv_reversed1}' and '{csv_reversed2}'")
                        
                        if (counselor_normalized == csv_reversed1 or 
                            counselor_normalized == csv_reversed2 or
                            csv_reversed1 in counselor_normalized or 
                            csv_reversed2 in counselor_normalized):
                            matching_counselors.append(counselor)
                            self.ips_uploader_log_msg(f"✅ Match found: '{counselor}' matches '{primary_worker}' (LastFirst format)")
                            break
                        
                        # Try partial matches with individual parts
                        if any(part.lower() in counselor_normalized for part in csv_parts):
                            matching_counselors.append(counselor)
                            self.ips_uploader_log_msg(f"✅ Match found: '{counselor}' matches '{primary_worker}' (partial)")
                            break
                    
                    # Check for "Last, First" vs "First Last" format
                    if ',' in worker_normalized:
                        # CSV format: "Hernandez, Cynthia" -> try "Cynthia Hernandez"
                        parts = worker_normalized.split(',')
                        if len(parts) == 2:
                            last_name = parts[0].strip()
                            first_name = parts[1].strip()
                            reversed_format = f"{first_name} {last_name}"
                            
                            if (reversed_format in counselor_normalized or 
                                counselor_normalized in reversed_format):
                                matching_counselors.append(counselor)
                                self.ips_uploader_log_msg(f"✅ Match found: '{counselor}' matches '{primary_worker}' (reversed format)")
                                break
                    
                    # Check if all words from CSV name are present in counselor name
                    worker_words = worker_normalized.replace(',', '').split()
                    if all(word in counselor_normalized for word in worker_words if len(word) > 1):
                        matching_counselors.append(counselor)
                        self.ips_uploader_log_msg(f"✅ Match found: '{counselor}' matches '{primary_worker}' (word match)")
                        break
            
            if matching_counselors:
                self.ips_uploader_log_msg(f"✅ Found matching counselors to remove: {', '.join(matching_counselors)}")
                # Click the Edit button to start removal process
                self._click_edit_button_ips()
            else:
                self.ips_uploader_log_msg("ℹ️ No matching counselors found - no removal needed")
                # Still need to click Edit button to check if there are any counselors to remove
                self.ips_uploader_log_msg("🔍 Clicking Edit button to verify no counselors need removal...")
                self._click_edit_button_ips()
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Error reviewing counselors: {e}")

    def _click_edit_button_ips(self):
        """Click the Edit button to start counselor removal process - EXACT COPY of regular uploader"""
        try:
            self.ips_uploader_log_msg("✏️ Looking for Edit button...")
            
            # Find the Edit button using multiple selectors
            edit_selectors = [
                "//psy-button[@class='ClickToEditBtn hydrated' and contains(., 'Edit')]",
                "//psy-button[@class='ClickToEditBtn hydrated']",
                "//psy-button[contains(@class, 'ClickToEditBtn') and contains(., 'Edit')]",
                "//psy-button[contains(@class, 'ClickToEditBtn')]",
                "//button[contains(text(), 'Edit')]",
                "//psy-button[contains(., 'Edit')]",
                "//button[contains(@class, 'button') and contains(., 'Edit')]"
            ]
            
            edit_button = None
            for i, selector in enumerate(edit_selectors):
                try:
                    self.ips_uploader_log_msg(f"🔍 Trying selector {i+1}: {selector}")
                    edit_button = WebDriverWait(self.ips_tn_driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    self.ips_uploader_log_msg(f"✅ Found Edit button with selector {i+1}")
                    time.sleep(1)
                    break
                except Exception as e:
                    self.ips_uploader_log_msg(f"❌ Selector {i+1} failed: {e}")
                    continue
            
            if edit_button:
                # Scroll to the element first
                self.ips_uploader_log_msg("📜 Scrolling to Edit button...")
                self.ips_tn_driver.execute_script("arguments[0].scrollIntoView(true);", edit_button)
                time.sleep(0.3)
                
                # Try multiple click methods
                self.ips_uploader_log_msg("🖱️ Attempting to click Edit button...")
                
                # Method 1: Regular click
                try:
                    edit_button.click()
                    
                    # Wait for Edit mode to fully activate and check for Save button
                    save_button_found = False
                    for wait_attempt in range(5):
                        time.sleep(1)
                        try:
                            save_check = self.ips_tn_driver.find_element(By.XPATH, "//input[@id='CommonFooter__SaveChanges-Button']")
                            save_button_found = True
                            self.ips_uploader_log_msg(f"✅ Successfully clicked Edit button (method 1) - Save button verified after {wait_attempt + 1}s")
                            break
                        except:
                            self.ips_uploader_log_msg(f"⏳ Waiting for Save button... ({wait_attempt + 1}/5)")
                            continue
                    
                    if save_button_found:
                        self._remove_matching_counselors_ips()
                        return
                    else:
                        self.ips_uploader_log_msg("❌ Edit button clicked but Save button never appeared - Edit didn't work")
                        raise Exception("Edit click failed - Save button not present")
                except Exception as e1:
                    self.ips_uploader_log_msg(f"❌ Method 1 failed: {e1}")
                
                # Method 2: JavaScript click
                try:
                    self.ips_uploader_log_msg("🖱️ Trying JavaScript click...")
                    self.ips_tn_driver.execute_script("arguments[0].click();", edit_button)
                    
                    # Wait for Save button
                    save_button_found = False
                    for wait_attempt in range(5):
                        time.sleep(1)
                        try:
                            save_check = self.ips_tn_driver.find_element(By.XPATH, "//input[@id='CommonFooter__SaveChanges-Button']")
                            save_button_found = True
                            self.ips_uploader_log_msg(f"✅ Successfully clicked Edit button (method 2) - Save button verified after {wait_attempt + 1}s")
                            break
                        except:
                            continue
                    
                    if save_button_found:
                        self._remove_matching_counselors_ips()
                        return
                    else:
                        raise Exception("JavaScript click failed - Save button not present")
                except Exception as e2:
                    self.ips_uploader_log_msg(f"❌ Method 2 failed: {e2}")
                
                self.ips_uploader_log_msg("❌ All click methods failed")
            else:
                self.ips_uploader_log_msg("❌ Could not find Edit button")
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to click Edit button: {e}")

    def _remove_matching_counselors_ips(self):
        """Remove counselors that match the CSV data by clicking their X buttons - FIXED for IPS"""
        try:
            self.ips_uploader_log_msg("🗑️ Looking for counselor X buttons to remove...")
            
            # Get current patient's primary workers from CSV data
            current_primary_workers = getattr(self, 'current_primary_workers', [])
            
            if not current_primary_workers:
                self.ips_uploader_log_msg("ℹ️ No primary workers to remove for this patient")
                return
            
            self.ips_uploader_log_msg(f"🎯 Looking for counselors to remove: {', '.join(current_primary_workers)}")
            
            # Wait for edit mode to be fully active
            time.sleep(1.5)
            
            # Find all X buttons using multiple selectors (same as ISWS version)
            x_buttons = []
            try:
                x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//button[@title='Remove Clinician']")
                self.ips_uploader_log_msg(f"🔍 Found {len(x_buttons)} X buttons with 'Remove Clinician' selector")
            except:
                pass
            
            if not x_buttons:
                try:
                    x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//span[@class='button-text-input-mimic float-right']//button")
                    self.ips_uploader_log_msg(f"🔍 Found {len(x_buttons)} X buttons with span selector")
                except:
                    pass
            
            if not x_buttons:
                try:
                    x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//div[@class='fa-icon close']")
                    self.ips_uploader_log_msg(f"🔍 Found {len(x_buttons)} X buttons with div selector")
                except:
                    pass
            
            self.ips_uploader_log_msg(f"🔍 Found {len(x_buttons)} total X buttons on page")
            
            if not x_buttons:
                self.ips_uploader_log_msg("ℹ️ No X buttons found - no counselors to remove")
                self._save_counselor_changes_ips()
                return
            
            # Pre-normalize CSV names and create all possible formats for matching
            # CSV format is "First Last" (e.g., "Diann Beharry", "Tatiana Casimir")
            normalized_workers = {}
            for worker in current_primary_workers:
                worker_normalized = worker.lower().strip()
                # Store original format
                normalized_workers[worker_normalized] = worker
                # Also store as word set for flexible matching
                worker_words = set(worker_normalized.split())
                normalized_workers[tuple(sorted(worker_words))] = worker
            
            # Fast-fail list for obviously non-counselor names
            skip_names = {'user options', 'select a clinician', 'contact us', 'log out', 
                          'no future appt', 'profile', 'settings', 'help', 'status', 'referrals',
                          'these users supervise', 'supervisors', 'assigned', 'none'}
            
            removed_count = 0
            
            # Process each X button
            for i, x_button in enumerate(x_buttons):
                try:
                    # Extract counselor name using robust method (same as ISWS)
                    counselor_name = self._extract_counselor_name_ips_robust(x_button, i+1)
                    
                    if not counselor_name:
                        self.ips_uploader_log_msg(f"⚠️ X Button {i+1}: Could not extract counselor name")
                        continue
                    
                    counselor_normalized = counselor_name.lower().strip()
                    
                    # Skip navigation elements
                    if counselor_normalized in skip_names or any(skip in counselor_normalized for skip in skip_names):
                        self.ips_uploader_log_msg(f"⏭️ X Button {i+1}: Skipping navigation element '{counselor_name}'")
                        continue
                    
                    self.ips_uploader_log_msg(f"🔍 X Button {i+1}: Checking counselor '{counselor_name}'")
                    
                    # Check if this counselor matches any in our removal list
                    should_click = False
                    matched_worker = None
                    
                    # Method 1: Direct exact match
                    if counselor_normalized in normalized_workers:
                        should_click = True
                        matched_worker = normalized_workers[counselor_normalized]
                        self.ips_uploader_log_msg(f"✅ EXACT MATCH: '{counselor_name}' matches '{matched_worker}'")
                    
                    # Method 2: Word set match (handles different word orders)
                    if not should_click:
                        counselor_words = set(counselor_normalized.split())
                        counselor_words_tuple = tuple(sorted(counselor_words))
                        if counselor_words_tuple in normalized_workers:
                            should_click = True
                            matched_worker = normalized_workers[counselor_words_tuple]
                            self.ips_uploader_log_msg(f"✅ WORD MATCH: '{counselor_name}' matches '{matched_worker}' (same words)")
                    
                    # Method 3: Check if all words from CSV name are in counselor name
                    if not should_click:
                        for worker in current_primary_workers:
                            worker_normalized = worker.lower().strip()
                            worker_words = set(worker_normalized.split())
                            counselor_words = set(counselor_normalized.split())
                            
                            # Check if all words from worker name are in counselor name
                            if worker_words.issubset(counselor_words) and len(worker_words) >= 2:
                                should_click = True
                                matched_worker = worker
                                self.ips_uploader_log_msg(f"✅ SUBSET MATCH: '{counselor_name}' contains all words from '{matched_worker}'")
                                break
                    
                    # Method 4: Check reverse (counselor words in worker name)
                    if not should_click:
                        for worker in current_primary_workers:
                            worker_normalized = worker.lower().strip()
                            worker_words = set(worker_normalized.split())
                            counselor_words = set(counselor_normalized.split())
                            
                            if counselor_words.issubset(worker_words) and len(counselor_words) >= 2:
                                should_click = True
                                matched_worker = worker
                                self.ips_uploader_log_msg(f"✅ REVERSE SUBSET MATCH: '{matched_worker}' contains all words from '{counselor_name}'")
                                break
                    
                    if should_click:
                        # Try to click the X button
                        try:
                            # Scroll into view first
                            self.ips_tn_driver.execute_script("arguments[0].scrollIntoView(true);", x_button)
                            time.sleep(0.2)
                            
                            # Try JavaScript click first (most reliable)
                            self.ips_tn_driver.execute_script("arguments[0].click();", x_button)
                            removed_count += 1
                            self.ips_uploader_log_msg(f"🗑️ REMOVING: '{counselor_name}' - matches CSV worker '{matched_worker}'")
                            time.sleep(0.5)  # Wait for removal to process
                        except Exception as e1:
                            # Fallback to regular click
                            try:
                                x_button.click()
                                removed_count += 1
                                self.ips_uploader_log_msg(f"🗑️ REMOVING: '{counselor_name}' - matches CSV worker '{matched_worker}' (regular click)")
                                time.sleep(0.5)
                            except Exception as e2:
                                self.ips_uploader_log_msg(f"❌ Failed to click X button for '{counselor_name}': JS={e1}, Regular={e2}")
                    else:
                        self.ips_uploader_log_msg(f"✅ KEEPING: '{counselor_name}' - not in removal list")
                
                except Exception as e:
                    self.ips_uploader_log_msg(f"❌ Error processing X button {i+1}: {e}")
                    continue
            
            if removed_count > 0:
                self.ips_uploader_log_msg(f"✅ Successfully removed {removed_count} counselor(s)")
            else:
                self.ips_uploader_log_msg("ℹ️ No counselors found to remove")
            
            # Save changes
            self._save_counselor_changes_ips()
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to remove counselors: {e}")
            import traceback
            self.ips_uploader_log_msg(f"❌ Traceback: {traceback.format_exc()}")

    def _save_counselor_changes_ips(self):
        """Save counselor changes - EXACT COPY of regular uploader"""
        try:
            self.ips_uploader_log_msg("💾 Looking for Save Changes button...")
            save_button = self.ips_tn_driver.find_element(By.XPATH, "//input[@id='CommonFooter__SaveChanges-Button']")
            save_button.click()
            self.ips_uploader_log_msg("✅ Clicked Save Changes button")
            
            # Wait for save to complete
            time.sleep(2)
            self.ips_uploader_log_msg("✅ Successfully saved counselor changes")
            
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to save counselor changes: {e}")

    def _extract_counselor_name_ips_robust(self, x_button, button_index):
        """Extract counselor name from X button - ROBUST method with debug logging"""
        try:
            # Method 1: Try staff link in grandparent (most reliable)
            try:
                parent = x_button.find_element(By.XPATH, "./..")
                grandparent = parent.find_element(By.XPATH, "./..")
                staff_link = grandparent.find_element(By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]")
                counselor_name = staff_link.text.strip()
                if counselor_name and len(counselor_name) > 2:
                    self.ips_uploader_log_msg(f"🔍 X Button {button_index}: Extracted '{counselor_name}' via grandparent staff link")
                    return counselor_name
            except Exception as e1:
                pass
            
            # Method 2: Try staff link in parent (fallback)
            try:
                parent = x_button.find_element(By.XPATH, "./..")
                staff_links = parent.find_elements(By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]")
                if staff_links:
                    counselor_name = staff_links[0].text.strip()
                    if counselor_name and len(counselor_name) > 2:
                        self.ips_uploader_log_msg(f"🔍 X Button {button_index}: Extracted '{counselor_name}' via parent staff link")
                        return counselor_name
            except Exception as e2:
                pass
            
            # Method 3: Try finding staff link in broader context (go up multiple levels)
            try:
                current_element = x_button
                for level in range(4):  # Try up to 4 levels up
                    try:
                        current_element = current_element.find_element(By.XPATH, "./..")
                        staff_links = current_element.find_elements(By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]")
                        if staff_links:
                            counselor_name = staff_links[0].text.strip()
                            if counselor_name and len(counselor_name) > 2:
                                self.ips_uploader_log_msg(f"🔍 X Button {button_index}: Extracted '{counselor_name}' via level {level+1} ancestor")
                                return counselor_name
                    except:
                        continue
            except:
                pass
            
            # Method 4: Extract from grandparent text (last resort)
            try:
                parent = x_button.find_element(By.XPATH, "./..")
                grandparent = parent.find_element(By.XPATH, "./..")
                grandparent_text = grandparent.text.strip()
                
                # Look for first capitalized name pattern (2+ words)
                words = grandparent_text.split()
                for i in range(len(words) - 1):
                    if (words[i] and words[i+1] and 
                        len(words[i]) > 1 and len(words[i+1]) > 1 and
                        words[i][0].isupper() and words[i+1][0].isupper()):
                        potential_name = f"{words[i]} {words[i+1]}"
                        # Skip common non-name patterns
                        if potential_name.lower() not in {'user options', 'contact us', 'log out', 'profile', 'settings', 'help'}:
                            self.ips_uploader_log_msg(f"🔍 X Button {button_index}: Extracted '{potential_name}' via text parsing")
                            return potential_name
            except:
                pass
            
            return None
            
        except Exception as e:
            self.ips_uploader_log_msg(f"⚠️ X Button {button_index}: Error extracting name: {e}")
            return None
    
    def _extract_counselor_name_ips_fast(self, x_button):
        """Extract counselor name from X button - OPTIMIZED for speed (no debug logs)"""
        try:
            # Method 1: Try staff link in grandparent (most reliable, fastest)
            try:
                parent = x_button.find_element(By.XPATH, "./..")
                grandparent = parent.find_element(By.XPATH, "./..")
                staff_link = grandparent.find_element(By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]")
                counselor_name = staff_link.text.strip()
                if counselor_name and len(counselor_name) > 2:
                    return counselor_name
            except:
                pass
            
            # Method 2: Try staff link in parent (fallback)
            try:
                parent = x_button.find_element(By.XPATH, "./..")
                staff_links = parent.find_elements(By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]")
                if staff_links:
                    counselor_name = staff_links[0].text.strip()
                    if counselor_name and len(counselor_name) > 2:
                        return counselor_name
            except:
                pass
            
            # Method 3: Extract from grandparent text (last resort, but faster than before)
            try:
                parent = x_button.find_element(By.XPATH, "./..")
                grandparent = parent.find_element(By.XPATH, "./..")
                grandparent_text = grandparent.text.strip()
                
                # Look for first capitalized name pattern (2+ words)
                words = grandparent_text.split()
                for i in range(len(words) - 1):
                    if (words[i][0].isupper() and words[i+1][0].isupper() and 
                        len(words[i]) > 1 and len(words[i+1]) > 1):
                        potential_name = f"{words[i]} {words[i+1]}"
                        # Skip common non-name patterns
                        if potential_name.lower() not in {'user options', 'contact us', 'log out'}:
                            return potential_name
            except:
                pass
            
            return None
            
        except Exception:
            return None
    
    def _extract_counselor_name_ips(self, x_button):
        """Extract counselor name from X button - ENHANCED DEBUGGING for IPS (kept for compatibility)"""
        # Use fast version but add debug logs if needed
        counselor_name = self._extract_counselor_name_ips_fast(x_button)
        if not counselor_name:
            self.ips_uploader_log_msg("❌ All methods failed to extract counselor name")
        return counselor_name

    def _return_to_patients_page_ips(self):
        """Return to the Patients page to process the next patient - EXACT COPY of regular uploader"""
        try:
            self.ips_uploader_log_msg("🔄 Returning to Patients page...")
            
            # CRITICAL: Close any modal dialogs before attempting navigation
            self._close_any_modal_dialogs_ips()
            
            # Find and click the Patients button
            patients_button = self.ips_tn_driver.find_element(By.XPATH, "//span[text()='Patients']")
            patients_button.click()
            self.ips_uploader_log_msg("✅ Clicked Patients button")
            
            # Wait for the search bar to be available
            time.sleep(1.5)
            
            # Verify we're back on the Patients page by checking for search bar
            try:
                search_bar = self.ips_tn_driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
                self.ips_uploader_log_msg("✅ Successfully returned to Patients page")
                return True
            except:
                self.ips_uploader_log_msg("⚠️ Search bar not found - may still be loading")
                time.sleep(1)
                return True
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to return to Patients page: {e}")
            return False

    def _navigate_to_patient_and_remove_counselors_ips(self):
        """Navigate to patient and remove counselors - MIRRORS regular uploader exactly"""
        try:
            self.ips_uploader_log_msg(f"👥 Navigating to Clinicians tab...")
            
            # Click Clinicians tab - SAME SELECTORS AS REGULAR
            clinicians_tab = self.ips_tn_driver.find_element(By.XPATH, "//span[text()='Clinicians']")
            clinicians_tab.click()
            self.ips_uploader_log_msg("✅ Clicked Clinicians tab")
            
            # Wait for counselor data to load - SAME AS REGULAR
            time.sleep(2)
            self.ips_uploader_log_msg("✅ Successfully navigated to Clinicians tab (counselor data loaded)")
            
            # Review counselors on Clinicians tab - SAME AS REGULAR
            self.ips_uploader_log_msg("🔍 Reviewing counselors on Clinicians tab...")
            self.ips_uploader_log_msg(f"🎯 Looking for counselors to remove: {', '.join(self.current_primary_workers)}")
            
            # Click Edit button to enter edit mode - SAME AS REGULAR
            self.ips_uploader_log_msg("🔍 Clicking Edit button to verify no counselors need removal...")
            self.ips_uploader_log_msg("✏️ Looking for Edit button...")
            
            # Find Edit button - SAME SELECTORS AS REGULAR
            edit_button = None
            edit_selectors = [
                "//psy-button[@class='ClickToEditBtn hydrated' and contains(., 'Edit')]",
                "//button[contains(text(), 'Edit')]",
                "//input[@value='Edit']"
            ]
            
            for selector in edit_selectors:
                try:
                    edit_button = self.ips_tn_driver.find_element(By.XPATH, selector)
                    self.ips_uploader_log_msg(f"✅ Found Edit button with selector: {selector}")
                    break
                except:
                    continue
            
            if edit_button:
                # Scroll to button if needed - SAME AS REGULAR
                self.ips_tn_driver.execute_script("arguments[0].scrollIntoView(true);", edit_button)
                time.sleep(0.2)
                
                # Try to click Edit button - SAME AS REGULAR
                try:
                    edit_button.click()
                    self.ips_uploader_log_msg("✅ Successfully clicked Edit button")
                except:
                    # Try JavaScript click as fallback - SAME AS REGULAR
                    self.ips_tn_driver.execute_script("arguments[0].click();", edit_button)
                    self.ips_uploader_log_msg("✅ Successfully clicked Edit button (JavaScript)")
                
                time.sleep(1)  # Wait for edit mode to activate
                
                # Look for counselor X buttons to remove - SAME AS REGULAR
                self.ips_uploader_log_msg("🗑️ Looking for counselor X buttons to remove...")
                self.ips_uploader_log_msg("📋 NOTE: Will SKIP any counselors with '- IPS' suffix (they belong to IPS agency)")
                self.ips_uploader_log_msg(f"🎯 Looking for counselors to remove (keeping CSV workers: {', '.join(self.current_primary_workers)})")
                
                # Find all X buttons - SAME SELECTORS AS REGULAR
                x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//button[@title='Remove Clinician']")
                if not x_buttons:
                    x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//span[@class='button-text-input-mimic float-right']//button")
                if not x_buttons:
                    x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//div[@class='fa-icon close']")
                
                self.ips_uploader_log_msg(f"🔍 Found {len(x_buttons)} X buttons on page")
                
                removed_count = 0
                for x_button in x_buttons:
                    try:
                        # Get counselor name associated with this X button - SAME AS REGULAR
                        counselor_text = self._extract_counselor_name_ips(x_button)
                        
                        # SAFETY: require a counselor name
                        if not counselor_text:
                            self.ips_uploader_log_msg("⚠️ Could not extract counselor name - skipping for safety")
                            continue
                        
                        # IPS SAFETY: require '- IPS' suffix present on the on-page name
                        if "- ips" not in counselor_text.lower():
                            self.ips_uploader_log_msg(f"🚫 SKIP: '{counselor_text}' lacks '- IPS' suffix (IPS-only removal)")
                            continue
                        
                        self.ips_uploader_log_msg(f"🔍 Checking X button: '{counselor_text}'")
                        
                        # Check if this counselor is in our removal list - SAME AS REGULAR
                        should_remove = False
                        matched_counselor = None
                        
                        for csv_counselor in self.current_primary_workers:
                            # Normalize both names for comparison - SAME AS REGULAR
                            counselor_normalized = counselor_text.lower().strip()
                            csv_counselor_normalized = csv_counselor.lower().strip()
                            
                            # Try exact match first
                            if counselor_normalized == csv_counselor_normalized:
                                should_remove = True
                                matched_counselor = csv_counselor
                                break
                            
                            # Try reversed format (Last, First vs First Last)
                            csv_parts = csv_counselor_normalized.split(', ')
                            if len(csv_parts) == 2:
                                csv_reversed = f"{csv_parts[1]} {csv_parts[0]}"
                                if counselor_normalized == csv_reversed:
                                    should_remove = True
                                    matched_counselor = csv_counselor
                                    break
                            
                            # Try partial matches
                            if any(part in counselor_normalized for part in csv_parts):
                                should_remove = True
                                matched_counselor = csv_counselor
                                break
                        
                        if should_remove:
                            self.ips_uploader_log_msg(f"🗑️ REMOVING: '{counselor_text}' matches CSV worker '{matched_counselor}' - clicking X")
                            try:
                                x_button.click()
                                self.ips_uploader_log_msg(f"🗑️ Removed counselor: {counselor_text}")
                                removed_count += 1
                                time.sleep(0.5)  # Wait between removals
                            except Exception as e:
                                self.ips_uploader_log_msg(f"❌ Failed to click X button for {counselor_text}: {e}")
                        else:
                            self.ips_uploader_log_msg(f"✅ KEEPING: '{counselor_text}' is NOT in CSV - NOT removing")
                    
                    except Exception as e:
                        self.ips_uploader_log_msg(f"❌ Error processing X button: {e}")
                        continue
                
                self.ips_uploader_log_msg(f"✅ Successfully removed {removed_count} counselor(s)")
                
                # Save changes - SAME AS REGULAR
                self.ips_uploader_log_msg("💾 Looking for Save Changes button...")
                save_button = self.ips_tn_driver.find_element(By.XPATH, "//input[@id='CommonFooter__SaveChanges-Button']")
                save_button.click()
                self.ips_uploader_log_msg("✅ Clicked Save Changes button")
                time.sleep(1.5)
                self.ips_uploader_log_msg("✅ Successfully saved counselor changes")
                
                return True
            else:
                self.ips_uploader_log_msg("❌ Could not find Edit button")
                return False
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to navigate to patient and remove counselors: {e}")
            return False

    def _extract_counselor_name_ips(self, x_button):
        """Extract counselor name from X button - ENHANCED VERSION from Base uploader"""
        try:
            # Method 1: Try to find counselor name in parent or grandparent element
            parent_element = x_button.find_element(By.XPATH, "./..")
            grandparent_element = parent_element.find_element(By.XPATH, "./..")
            counselor_text = ""

            try:
                staff_link = grandparent_element.find_element(
                    By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]"
                )
                counselor_text = staff_link.text.strip()
                self.ips_uploader_log_msg(f"🔍 DEBUG: Found counselor via grandparent: '{counselor_text}'")
            except Exception:
                try:
                    staff_link = parent_element.find_element(
                        By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]"
                    )
                    counselor_text = staff_link.text.strip()
                    self.ips_uploader_log_msg(f"🔍 DEBUG: Found counselor via parent: '{counselor_text}'")
                except Exception:
                    self.ips_uploader_log_msg("🔍 DEBUG: No staff link found in parent or grandparent")

            # Method 2: If no staff link found, look in the entire row/container
            if not counselor_text:
                try:
                    # Look for any <a> tag with staff edit link in the broader context
                    staff_links = self.ips_tn_driver.find_elements(By.XPATH, "//a[contains(@href, '/app/staff/edit/')]")
                    self.ips_uploader_log_msg(f"🔍 DEBUG: Found {len(staff_links)} staff links on page")
                    
                    # Find the one closest to this X button by checking if they're in the same container
                    for link in staff_links:
                        try:
                            # Check if this link is in the same container as our X button
                            link_text = link.text.strip()
                            if link_text and len(link_text) > 2:  # Valid name
                                # Check if they share a common container
                                link_ancestors = set()
                                current = link
                                for _ in range(5):  # Check up to 5 levels up
                                    try:
                                        current = current.find_element(By.XPATH, "./..")
                                        link_ancestors.add(current)
                                    except:
                                        break
                                
                                x_ancestors = set()
                                current = x_button
                                for _ in range(5):  # Check up to 5 levels up
                                    try:
                                        current = current.find_element(By.XPATH, "./..")
                                        x_ancestors.add(current)
                                    except:
                                        break
                                
                                # If they share any ancestor, they're likely in the same row
                                if link_ancestors & x_ancestors:
                                    counselor_text = link_text
                                    self.ips_uploader_log_msg(f"🔍 DEBUG: Found counselor name via nearby staff link: '{counselor_text}'")
                                    break
                        except:
                            continue
                except Exception as e:
                    self.ips_uploader_log_msg(f"🔍 DEBUG: Error finding staff links: {e}")
            
            # Method 3: Fallback - look for text that's not navigation/UI elements
            if not counselor_text:
                try:
                    # Get all text nodes in the parent element
                    all_text = parent_element.text.strip()
                    self.ips_uploader_log_msg(f"🔍 DEBUG: Full parent text: '{all_text[:200]}...'")
                    
                    # Look for text that looks like a name (contains letters, not just UI elements)
                    text_parts = all_text.split('\n')
                    for part in text_parts:
                        part = part.strip()
                        # Skip common UI elements and look for name-like text
                        if (part and 
                            not part.startswith('Home') and 
                            not part.startswith('To-Do') and 
                            not part.startswith('Scheduling') and 
                            not part.startswith('Patients') and 
                            not part.startswith('Staff') and 
                            not part.startswith('Contacts') and 
                            not part.startswith('Billing') and 
                            not part.startswith('Payers') and 
                            not part.startswith('Library') and 
                            not part.startswith('Profile') and 
                            not part.startswith('Settings') and 
                            not part.startswith('Help') and 
                            not part.startswith('Status') and 
                            not part.startswith('Referrals') and 
                            not part.startswith('Mobile') and 
                            not part.startswith('Patient') and 
                            not part.startswith('Info') and 
                            not part.startswith('Schedule') and 
                            not part.startswith('Documents') and 
                            not part.startswith('Clinicians') and 
                            not part.startswith('Portal') and 
                            not part.startswith('Insights') and 
                            not part.startswith('Warning') and 
                            not part.startswith('Error') and 
                            not part.startswith('Edit') and 
                            not part.startswith('Supervisors') and 
                            not part.startswith('Assigned') and 
                            not part.startswith('None') and
                            not part.startswith('User Options') and
                            not part.startswith('Contact Us') and
                            not part.startswith('Log Out') and
                            not part.startswith('×') and
                            not part.startswith('Close') and
                            not part.startswith('Remove') and
                            not part.startswith('Delete') and
                            len(part) > 2 and
                            any(c.isalpha() for c in part)):
                            counselor_text = part
                            self.ips_uploader_log_msg(f"🔍 DEBUG: Found counselor name via text parsing: '{counselor_text}'")
                            break
                except Exception as e:
                    self.ips_uploader_log_msg(f"🔍 DEBUG: Error in text parsing: {e}")
            
            # Method 4: Look for any text that appears to be a counselor name near the X button
            if not counselor_text:
                try:
                    # Get all text elements on the page and find ones that look like names
                    all_elements = self.ips_tn_driver.find_elements(By.XPATH, "//*[text()]")
                    potential_names = []
                    
                    for elem in all_elements:
                        try:
                            text = elem.text.strip()
                            # Check if this looks like a name (2+ words, each starting with capital)
                            if (text and 
                                len(text.split()) >= 2 and 
                                all(word[0].isupper() for word in text.split() if word) and
                                not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                potential_names.append(text)
                        except Exception as e:
                            continue  # Skip this element if there's an error
                                
                    self.ips_uploader_log_msg(f"🔍 DEBUG: Found {len(potential_names)} potential counselor names on page: {potential_names[:5]}")
                    
                    # If we found potential names, use the first one that's not already processed
                    if potential_names:
                        counselor_text = potential_names[0]
                        self.ips_uploader_log_msg(f"🔍 DEBUG: Using first potential counselor name: '{counselor_text}'")
                        
                except Exception as e:
                    self.ips_uploader_log_msg(f"🔍 DEBUG: Error in broader context search: {e}")
            
            if not counselor_text:
                counselor_text = "Unknown Counselor"
            
            self.ips_uploader_log_msg(f"🔍 Final extracted counselor name: '{counselor_text}'")
            return counselor_text
            
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Error extracting counselor name: {e}")
            return "Unknown Counselor"

    def _search_patient_in_ips_therapy_notes(self, patient_name):
        """Search for patient in IPS Therapy Notes"""
        try:
            self.ips_uploader_log_msg(f"🔍 Searching for patient: {patient_name}")
            
            # Check if name has middle initial and prepare fallback name
            has_middle_initial = self._has_middle_initial(patient_name)
            fallback_name = None
            if has_middle_initial:
                fallback_name = self._remove_middle_initial(patient_name)
                self.ips_uploader_log_msg(f"🔍 MIDDLE INITIAL DETECTED: '{patient_name}' -> fallback: '{fallback_name}'")
            
            # Navigate to Patients page if not already there
            self._navigate_to_ips_patients_page()
            
            # Find search field
            search_field = None
            search_selectors = [
                (By.CSS_SELECTOR, "input[type='text'][placeholder*='search' i]"),
                (By.CSS_SELECTOR, "input[placeholder*='patient' i]"),
                (By.CSS_SELECTOR, "input[placeholder*='name' i]"),
                (By.XPATH, "//input[@type='text' and contains(@placeholder, 'search')]"),
                (By.XPATH, "//input[@type='text' and contains(@placeholder, 'patient')]"),
                (By.XPATH, "//input[@type='text' and contains(@placeholder, 'name')]")
            ]
            
            for selector_type, selector_value in search_selectors:
                try:
                    search_field = WebDriverWait(self.ips_tn_driver, 2).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    self.ips_uploader_log_msg(f"✅ Found IPS search field with: {selector_type} = {selector_value}")
                    break
                except:
                    continue
            
            if not search_field:
                self.ips_uploader_log_msg("❌ Could not find IPS search field")
                return False
            
            # Try full name first
            search_field.clear()
            search_field.send_keys(patient_name)
            self.ips_uploader_log_msg(f"✅ Entered patient name: {patient_name}")
            
            # Press Enter to search
            search_field.send_keys(Keys.RETURN)
            time.sleep(2)
            
            # Look for patient in results
            patient_links = self.ips_tn_driver.find_elements(By.XPATH, f"//a[contains(text(), '{patient_name}')]")
            
            if patient_links:
                self.ips_uploader_log_msg(f"✅ Found patient in IPS Therapy Notes: {patient_name}")
                return True
            else:
                # If no match found and we have a fallback name (without middle initial), try it
                if fallback_name:
                    self.ips_uploader_log_msg(f"🔄 MIDDLE INITIAL FALLBACK: No match with full name, trying without middle initial: {fallback_name}")
                    
                    # Clear search field and try fallback name
                    search_field.clear()
                    search_field.send_keys(fallback_name)
                    self.ips_uploader_log_msg(f"✅ Entered fallback search term: {fallback_name}")
                    
                    # Press Enter to search again
                    search_field.send_keys(Keys.RETURN)
                    time.sleep(2)
                    
                    # Look for patient in results with fallback name
                    fallback_patient_links = self.ips_tn_driver.find_elements(By.XPATH, f"//a[contains(text(), '{fallback_name}')]")
                    
                    if fallback_patient_links:
                        self.ips_uploader_log_msg(f"✅ Found patient in IPS Therapy Notes with fallback name: {fallback_name}")
                        return True
                    else:
                        self.ips_uploader_log_msg(f"❌ Patient not found in IPS Therapy Notes with either name: {patient_name} or {fallback_name}")
                        return False
                else:
                    self.ips_uploader_log_msg(f"❌ Patient not found in IPS Therapy Notes: {patient_name}")
                    return False
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to search for patient: {e}")
            
            # If we have a middle initial fallback name, try it now
            if fallback_name:
                self.ips_uploader_log_msg(f"🔄 MIDDLE INITIAL FALLBACK: Search failed, trying without middle initial: {fallback_name}")
                
                try:
                    # Navigate to Patients page if not already there
                    self._navigate_to_ips_patients_page()
                    
                    # Find search field again
                    search_field = None
                    search_selectors = [
                        (By.CSS_SELECTOR, "input[type='text'][placeholder*='search' i]"),
                        (By.CSS_SELECTOR, "input[placeholder*='patient' i]"),
                        (By.CSS_SELECTOR, "input[placeholder*='name' i]"),
                        (By.XPATH, "//input[@type='text' and contains(@placeholder, 'search')]"),
                        (By.XPATH, "//input[@type='text' and contains(@placeholder, 'patient')]"),
                        (By.XPATH, "//input[@type='text' and contains(@placeholder, 'name')]")
                    ]
                    
                    for selector_type, selector_value in search_selectors:
                        try:
                            search_field = WebDriverWait(self.ips_tn_driver, 2).until(
                                EC.presence_of_element_located((selector_type, selector_value))
                            )
                            break
                        except:
                            continue
                    
                    if search_field:
                        # Clear and enter fallback name
                        search_field.clear()
                        search_field.send_keys(fallback_name)
                        self.ips_uploader_log_msg(f"✅ Entered fallback search term: {fallback_name}")
                        
                        # Press Enter to search
                        search_field.send_keys(Keys.RETURN)
                        time.sleep(2)
                        
                        # Look for patient in results with fallback name
                        fallback_patient_links = self.ips_tn_driver.find_elements(By.XPATH, f"//a[contains(text(), '{fallback_name}')]")
                        
                        if fallback_patient_links:
                            self.ips_uploader_log_msg(f"✅ Found patient in IPS Therapy Notes with fallback name: {fallback_name}")
                            return True
                        else:
                            self.ips_uploader_log_msg(f"❌ Patient not found with fallback name: {fallback_name}")
                    else:
                        self.ips_uploader_log_msg("❌ Could not find IPS search field for fallback")
                        
                except Exception as fallback_e:
                    self.ips_uploader_log_msg(f"❌ Fallback search failed: {fallback_e}")
            
            return False

    def _navigate_to_ips_patients_page(self):
        """Navigate to Patients page in IPS Therapy Notes"""
        try:
            self.ips_uploader_log_msg("🔄 Navigating to IPS Patients page...")
            
            # Find Patients button/link
            patients_selectors = [
                "//span[text()='Patients']",
                "//a[contains(text(), 'Patients')]",
                "//button[contains(text(), 'Patients')]",
                "//li[contains(@class, 'patients')]//a",
                "//nav//a[contains(text(), 'Patients')]"
            ]
            
            patients_button = None
            for selector in patients_selectors:
                try:
                    patients_button = self.ips_tn_driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue
            
            if patients_button:
                patients_button.click()
                self.ips_uploader_log_msg("✅ Clicked IPS Patients button")
                time.sleep(2)
                return True
            else:
                self.ips_uploader_log_msg("❌ Could not find IPS Patients button")
                return False
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to navigate to IPS Patients page: {e}")
            return False

    def _navigate_to_patient_and_remove_ips_counselors(self):
        """Navigate to patient and remove IPS counselors"""
        try:
            self.ips_uploader_log_msg(f"🔄 Navigating to patient: {self.current_case_name}")
            
            # Click on patient link
            patient_links = self.ips_tn_driver.find_elements(By.XPATH, f"//a[contains(text(), '{self.current_case_name}')]")
            
            if not patient_links:
                self.ips_uploader_log_msg(f"❌ Could not find patient link: {self.current_case_name}")
                return False
            
            patient_links[0].click()
            self.ips_uploader_log_msg("✅ Clicked patient link")
            time.sleep(2)
            
            # Navigate to Clinicians tab
            self._navigate_to_ips_clinicians_tab()
            
            # Remove IPS counselors
            self._remove_ips_counselors_only()
            
            return True
            
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to navigate to patient: {e}")
            return False

    def _navigate_to_ips_clinicians_tab(self):
        """Navigate to Clinicians tab in IPS Therapy Notes"""
        try:
            self.ips_uploader_log_msg("🔄 Navigating to IPS Clinicians tab...")
            
            # Find Clinicians tab
            clinicians_selectors = [
                "//span[text()='Clinicians']",
                "//a[contains(text(), 'Clinicians')]",
                "//button[contains(text(), 'Clinicians')]",
                "//li[contains(@class, 'clinicians')]//a",
                "//nav//a[contains(text(), 'Clinicians')]"
            ]
            
            clinicians_button = None
            for selector in clinicians_selectors:
                try:
                    clinicians_button = self.ips_tn_driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue
            
            if clinicians_button:
                clinicians_button.click()
                self.ips_uploader_log_msg("✅ Clicked IPS Clinicians tab")
                time.sleep(2)
                return True
            else:
                self.ips_uploader_log_msg("❌ Could not find IPS Clinicians tab")
                return False
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to navigate to IPS Clinicians tab: {e}")
            return False

    def _remove_ips_counselors_only(self):
        """Remove ONLY counselors with '- IPS' after their names"""
        try:
            self.ips_uploader_log_msg("🗑️ Looking for IPS counselor X buttons to remove...")
            self.ips_uploader_log_msg("📋 NOTE: Will ONLY remove counselors with '- IPS' suffix")
            
            # Get current patient's IPS counselors from CSV data
            current_ips_counselors = getattr(self, 'current_primary_workers', [])
            
            if not current_ips_counselors:
                self.ips_uploader_log_msg("ℹ️ No IPS counselors to remove for this patient")
                return
            
            self.ips_uploader_log_msg(f"🎯 Looking for IPS counselors to remove: {', '.join(current_ips_counselors)}")
            
            # Click Edit button first
            self._click_ips_edit_button()
            
            # Find all X buttons
            x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//button[@title='Remove Clinician']")
            if not x_buttons:
                x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//span[@class='button-text-input-mimic float-right']//button")
            if not x_buttons:
                x_buttons = self.ips_tn_driver.find_elements(By.XPATH, "//div[@class='fa-icon close']")
            
            self.ips_uploader_log_msg(f"🔍 Found {len(x_buttons)} X buttons on IPS page")
            
            removed_count = 0
            for x_button in x_buttons:
                try:
                    # Get counselor name associated with this X button
                    counselor_text = self._extract_ips_counselor_name(x_button)
                    
                    if not counselor_text:
                        continue
                    
                    self.ips_uploader_log_msg(f"🔍 Checking IPS X button: '{counselor_text}'")
                    
                    # NOTE: In IPS account, ALL counselors are IPS counselors by default
                    # We don't need to check for "- IPS" suffix on the page
                    # The CSV has "- IPS" suffix, but the page won't have it
                    # We match based on name only

                    # Check if this counselor is in our IPS counselors list
                    should_remove = False
                    matched_ips_counselor = None
                    
                    for ips_counselor in current_ips_counselors:
                        # Normalize both names for comparison
                        counselor_normalized = counselor_text.lower().strip()
                        ips_counselor_normalized = ips_counselor.lower().strip()
                        
                        # CRITICAL FIX: Use STRICT matching to avoid removing wrong counselors
                        # Extract name components (remove IPS suffix and punctuation for comparison)
                        counselor_clean = counselor_normalized.replace("- ips", "").replace("-ips", "").replace(",", "").strip()
                        ips_clean = ips_counselor_normalized.replace("- ips", "").replace("-ips", "").replace(",", "").strip()
                        
                        # Split into words for comparison
                        counselor_words = set(counselor_clean.split())
                        ips_words = set(ips_clean.split())
                        
                        # STRICT MATCH: ALL words from CSV must match counselor on page
                        # This prevents "Hernandez Cynthia" from matching "Hernandez Maria"
                        if ips_words == counselor_words:
                            matched_ips_counselor = ips_counselor
                            should_remove = True
                            self.ips_uploader_log_msg(f"✅ IPS EXACT MATCH: '{counselor_text}' matches '{ips_counselor}'")
                            break
                        
                        # Also check for "Last, First - IPS" vs "First Last" format with FULL name match
                        if ',' in ips_counselor_normalized:
                            parts = ips_counselor_normalized.split(',')
                            if len(parts) == 2:
                                last_name = parts[0].strip()
                                first_name = parts[1].strip().replace("- ips", "").replace("-ips", "").strip()
                                reversed_format = f"{first_name} {last_name}"
                                reversed_words = set(reversed_format.split())
                                
                                if reversed_words == counselor_words:
                                    matched_ips_counselor = ips_counselor
                                    should_remove = True
                                    self.ips_uploader_log_msg(f"✅ IPS EXACT MATCH: '{counselor_text}' matches '{ips_counselor}' (reversed format)")
                                    break
                    
                    if should_remove:
                        x_button.click()
                        removed_count += 1
                        time.sleep(0.5)
                        self.ips_uploader_log_msg(f"🗑️ Removed IPS counselor: {counselor_text}")
                    else:
                        self.ips_uploader_log_msg(f"✅ KEEPING: '{counselor_text}' is NOT an IPS counselor - NOT removing")
                
                except Exception as e:
                    self.ips_uploader_log_msg(f"❌ Error processing IPS X button: {e}")
                    continue
            
            # Save changes
            if removed_count > 0:
                self.ips_uploader_log_msg(f"✅ Successfully removed {removed_count} IPS counselor(s)")
                self._save_ips_counselor_changes()
            else:
                self.ips_uploader_log_msg("ℹ️ No IPS counselors found to remove")
                self._save_ips_counselor_changes()
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to remove IPS counselors: {e}")

    def _extract_ips_counselor_name(self, x_button):
        """Extract counselor name from X button context"""
        try:
            # Try to find counselor name using same logic as regular uploader
            parent_element = x_button.find_element(By.XPATH, "./..")
            grandparent_element = parent_element.find_element(By.XPATH, "./..")
            
            # Look for staff link
            try:
                staff_link = grandparent_element.find_element(By.XPATH, ".//a[contains(@href, '/app/staff/edit/')]")
                counselor_text = staff_link.text.strip()
                return counselor_text
            except:
                pass
            
            # Fallback: look for any text that looks like a name
            all_text = parent_element.text.strip()
            text_parts = all_text.split('\n')
            for part in text_parts:
                part = part.strip()
                if (part and len(part) > 2 and 
                    not part.startswith('×') and
                    not part.startswith('Close') and
                    not part.startswith('Remove') and
                    not part.startswith('Delete') and
                    any(c.isalpha() for c in part)):
                    return part
            
            return "Unknown IPS Counselor"
            
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Error extracting IPS counselor name: {e}")
            return "Unknown IPS Counselor"

    def _click_ips_edit_button(self):
        """Click the Edit button in IPS Therapy Notes"""
        try:
            self.ips_uploader_log_msg("✏️ Looking for IPS Edit button...")
            
            # Find Edit button using same selectors as regular uploader
            edit_selectors = [
                "//psy-button[@class='ClickToEditBtn hydrated' and contains(., 'Edit')]",
                "//psy-button[@class='ClickToEditBtn hydrated']",
                "//button[contains(text(), 'Edit')]",
                "//psy-button[contains(., 'Edit')]"
            ]
            
            edit_button = None
            for selector in edit_selectors:
                try:
                    edit_button = self.ips_tn_driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue
            
            if edit_button:
                edit_button.click()
                self.ips_uploader_log_msg("✅ Clicked IPS Edit button")
                time.sleep(1)
                return True
            else:
                self.ips_uploader_log_msg("❌ Could not find IPS Edit button")
                return False
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to click IPS Edit button: {e}")
            return False

    def _save_ips_counselor_changes(self):
        """Save the IPS counselor removal changes"""
        try:
            self.ips_uploader_log_msg("💾 Looking for IPS Save Changes button...")
            
            # Find Save Changes button using same selectors as regular uploader
            save_selectors = [
                "//input[@id='CommonFooter__SaveChanges-Button']",
                "//input[@name='CommonFooter__SaveChanges-Button']",
                "//input[@value='Save Changes']",
                "//button[contains(text(), 'Save Changes')]"
            ]
            
            save_button = None
            for selector in save_selectors:
                try:
                    save_button = self.ips_tn_driver.find_element(By.XPATH, selector)
                    break
                except:
                    continue
            
            if save_button:
                save_button.click()
                self.ips_uploader_log_msg("✅ Clicked IPS Save Changes button")
                time.sleep(1.5)
                self.ips_uploader_log_msg("✅ Successfully saved IPS counselor changes")
                return True
            else:
                self.ips_uploader_log_msg("❌ Could not find IPS Save Changes button")
                return False
                
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to save IPS changes: {e}")
            return False

    def _create_ips_results_csv(self, results, original_csv_file):
        """Create a results CSV for IPS upload process"""
        try:
            import os
            from datetime import datetime
            
            # Create results filename based on original CSV
            base_name = os.path.splitext(os.path.basename(original_csv_file))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_filename = f"{base_name}_IPS_results_{timestamp}.csv"
            
            # Use selected output location if specified, otherwise use CSV file directory
            output_location = self.ips_output_location_var.get().strip()
            if output_location and os.path.isdir(output_location):
                results_dir = output_location
            else:
                results_dir = os.path.dirname(original_csv_file)
            
            results_path = os.path.join(results_dir, results_filename)
            
            # Create results DataFrame
            import pandas as pd
            results_df = pd.DataFrame(results)
            
            # Save results CSV
            results_df.to_csv(results_path, index=False)
            
            # Count successes and failures
            success_count = len(results_df[results_df['Process Status'] == 'SUCCESS'])
            failure_count = len(results_df[results_df['Process Status'] == 'FAILED'])
            
            self.ips_uploader_log_msg(f"📊 IPS Results CSV created: {results_path}")
            self.ips_uploader_log_msg(f"✅ Successfully processed: {success_count} patients")
            self.ips_uploader_log_msg(f"❌ Failed to process: {failure_count} patients")
            
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to create IPS results CSV: {e}")

    def _browse_ips_csv_file(self):
        """Browse for CSV file for IPS uploader"""
        filename = filedialog.askopenfilename(
            title="Select CSV file for IPS uploader",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.ips_csv_file_var.set(filename)
            self.ips_uploader_log_msg(f"📁 Selected CSV file: {filename}")
    
    def _browse_ips_output_location(self):
        """Browse for output directory for IPS results CSV"""
        directory = filedialog.askdirectory(
            title="Select Output Directory for IPS Results CSV"
        )
        if directory:
            self.ips_output_location_var.set(directory)
            self.ips_uploader_log_msg(f"📁 Selected IPS output location: {directory}")

    def _view_ips_upload_log(self):
        """View IPS upload log in a separate window"""
        try:
            log_window = tk.Toplevel(self)
            log_window.title("IPS Upload Log")
            log_window.geometry("800x600")
            
            log_text = tk.Text(log_window, wrap="word", font=("Consolas", 9))
            log_text.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Get log content
            log_content = self.ips_uploader_log.get("1.0", tk.END)
            log_text.insert("1.0", log_content)
            log_text.config(state="disabled")
            
        except Exception as e:
            self.ips_uploader_log_msg(f"❌ Failed to open IPS log window: {e}")

    def ips_uploader_log_msg(self, message):
        """Log message to IPS uploader log"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_message = f"[{timestamp}] {message}\n"
            
            self.ips_uploader_log.insert(tk.END, log_message)
            self.ips_uploader_log.see(tk.END)
            self.update()
            
        except Exception as e:
            print(f"Error logging IPS message: {e}")

if __name__ == "__main__":
    App().mainloop()
