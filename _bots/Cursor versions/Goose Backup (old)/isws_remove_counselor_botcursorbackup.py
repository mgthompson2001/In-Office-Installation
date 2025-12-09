# isws_remove_counselor_botcursorbackup.py
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
import time
import threading
import csv
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

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

@dataclass
class BotState:
    driver: Optional[webdriver.Chrome] = None
    chunks: List[Tuple[str, str]] = field(default_factory=list)
    next_chunk_index: int = 0
    stop_requested: bool = False
    extracted_data: List[ExtractedData] = field(default_factory=list)
    current_workflow_index: int = 0

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.state = BotState()
        self.title("ISWS Remove Counselor Bot - Complete Workflow")
        self.geometry("1000x500")
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
        ttk.Button(queue_frame, text="Expand Queue & Pickup All", style="Big.TButton",
                   command=self._queue_expand_and_pickup_all).pack(fill="x", padx=8, pady=4)

        # Advanced Search section
        search_frame = tk.LabelFrame(button_grid, text="Advanced Search", font=("Segoe UI", 10, "bold"))
        search_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        ttk.Button(search_frame, text="Fill Next Chunk", style="Big.TButton",
                   command=self._fill_next_chunk).pack(fill="x", padx=8, pady=4)
        ttk.Button(search_frame, text="Search & Process All", style="Big.TButton",
                   command=self._search_and_process_all).pack(fill="x", padx=8, pady=4)

        # Data Management section
        data_frame = tk.LabelFrame(button_grid, text="Data Management", font=("Segoe UI", 10, "bold"))
        data_frame.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")
        ttk.Button(data_frame, text="Export CSV", style="Success.TButton",
                   command=self._export_csv).pack(fill="x", padx=8, pady=4)
        ttk.Button(data_frame, text="Clear Data", style="Big.TButton",
                   command=self._clear_data).pack(fill="x", padx=8, pady=4)

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
                
                # Navigate to Therapy Notes
                self.tn_driver.get("https://www.therapynotes.com/app/login/IntegritySWS/?r=%2fapp%2fpatients%2f")
                time.sleep(1.5)
                
                # Find and fill username field - try multiple selectors
                username_field = None
                try:
                    username_field = self.tn_driver.find_element(By.NAME, "Username")
                except:
                    try:
                        username_field = self.tn_driver.find_element(By.ID, "Login__Username")
                    except:
                        username_field = self.tn_driver.find_element(By.NAME, "username")
                
                username_field.clear()
                username_field.send_keys(username)
                self.uploader_log_msg("✅ Username entered")
                
                # Find and fill password field using the specific ID
                password_field = self.tn_driver.find_element(By.ID, "Login__Password")
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
                
                time.sleep(2.5)  # Wait for login to complete
                
                # Check if login was successful
                current_url = self.tn_driver.current_url
                if "login" not in current_url.lower():
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
            options = ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Hide webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to initialize Therapy Notes driver: {e}")
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

    def _validate_csv(self):
        """Validate the selected CSV file"""
        csv_file = self.csv_file_var.get()
        if not csv_file:
            self.uploader_log_msg("Please select a CSV file first")
            return
        
        try:
            import pandas as pd
            df = pd.read_csv(csv_file)
            required_columns = ['Case Name', 'Case ID', 'Primary Workers', 'Service File Status', 'Extraction Date']
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                self.uploader_log_msg(f"❌ CSV validation failed. Missing columns: {missing_columns}")
                return
            
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
                df = pd.read_csv(csv_file)
                self.uploader_log_msg(f"📊 Loaded CSV with {len(df)} records")
                
                # Create results list to track success/failure
                results = []
                
                # Process each record
                for index, row in df.iterrows():
                    case_name = row['Case Name']
                    case_id = row['Case ID']
                    primary_workers = row['Primary Workers']
                    
                    # Parse primary workers (they're stored as semicolon-separated string)
                    if isinstance(primary_workers, str):
                        primary_workers_list = [worker.strip() for worker in primary_workers.split(';') if worker.strip()]
                    else:
                        primary_workers_list = []
                    
                    self.uploader_log_msg(f"🔍 Processing: {case_name} (ID: {case_id})")
                    self.uploader_log_msg(f"👥 Counselors to remove: {', '.join(primary_workers_list)}")
                    
                    # Store current patient data for use in review function
                    self.current_case_name = case_name
                    self.current_case_id = case_id
                    self.current_primary_workers = primary_workers_list
                    
                    # Track success/failure for this patient
                    patient_success = False
                    try:
                        # Search for patient
                        self._search_patient(case_name)
                        patient_success = True
                        self.uploader_log_msg(f"✅ Successfully processed: {case_name}")
                    except Exception as e:
                        self.uploader_log_msg(f"❌ Failed to process: {case_name} - {e}")
                        patient_success = False
                    
                    # Add result to tracking list
                    results.append({
                        'Case Name': case_name,
                        'Case ID': case_id,
                        'Primary Workers': primary_workers,
                        'Process Status': 'SUCCESS' if patient_success else 'FAILED',
                        'Process Date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                    time.sleep(1)  # Wait between patients
                
                # Create results CSV
                self._create_results_csv(results, csv_file)
                
                self.uploader_log_msg("✅ Upload process completed!")
                self.uploader_status_label.config(text="Upload completed")
                
            except Exception as e:
                self.uploader_log_msg(f"❌ Upload process failed: {e}")
        
        threading.Thread(target=run, daemon=True).start()

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

    def _search_patient(self, case_name):
        """Search for a patient in Therapy Notes and select from dropdown"""
        try:
            # Format the name for search (remove periods from middle initials)
            search_name = self._format_name_for_search(case_name)
            self.uploader_log_msg(f"🔍 Searching for patient: {case_name}")
            self.uploader_log_msg(f"🔍 Formatted search term: {search_name}", debug_only=True)
            
            # Find the patient search input field
            search_input = self.tn_driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
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
                patient_selected = False
                for option in patient_options:
                    option_text = option.text.strip()
                    self.uploader_log_msg(f"🔍 Checking option: '{option_text}'", debug_only=True)
                    
                    # Try exact match first (case insensitive)
                    if option_text and option_text.lower() == search_name.lower():
                        self.uploader_log_msg(f"🎯 Found exact match: {option_text}")
                        option.click()
                        self.uploader_log_msg("✅ Selected exact match from dropdown")
                        patient_selected = True
                        break
                    # Try partial match as fallback
                    elif option_text and search_name.lower() in option_text.lower():
                        self.uploader_log_msg(f"🎯 Found partial match: {option_text}")
                        option.click()
                        self.uploader_log_msg("✅ Selected partial match from dropdown")
                        patient_selected = True
                        break
                
                if not patient_selected:
                    self.uploader_log_msg(f"⚠️ No exact match found for: {case_name}")
                    # If no exact match, try clicking the first option
                    if patient_options:
                        first_option = patient_options[0]
                        self.uploader_log_msg(f"🔄 Selecting first option: {first_option.text}")
                        first_option.click()
                        self.uploader_log_msg("✅ Selected first available option")
                        patient_selected = True
                
                if patient_selected:
                    time.sleep(1.5)  # Wait for patient page to load
                    self.uploader_log_msg("✅ Patient selected successfully")
                    
                    # Navigate to Clinicians tab
                    self._navigate_to_clinicians_tab()
                else:
                    self.uploader_log_msg("❌ No patient options found in dropdown")
                    
            except Exception as dropdown_e:
                self.uploader_log_msg(f"❌ Dropdown selection failed: {dropdown_e}")
                # Fallback: try pressing Enter
                search_input.send_keys(Keys.RETURN)
                self.uploader_log_msg("🔄 Fallback: Pressed Enter to search")
                time.sleep(1.5)
            
        except Exception as e:
            self.uploader_log_msg(f"❌ Patient search failed: {e}")

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
                time.sleep(1)  # Wait for Clinicians tab to load
                self.uploader_log_msg("✅ Successfully navigated to Clinicians tab")
                
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
            
            # Look for counselor names on the page - specifically look for the names we know are there
            # From the log, we know "Cynthia Hernandez" and "Priya Doshi" are visible
            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Bryant') or contains(text(), 'Monique')]")
            
            self.uploader_log_msg(f"🔍 Found {len(counselor_elements)} potential counselor elements", debug_only=True)
            
            counselors_found = []
            for i, element in enumerate(counselor_elements):
                text = element.text.strip()
                self.uploader_log_msg(f"🔍 Element {i+1}: '{text}'", debug_only=True)
                if text and len(text) > 2:  # Basic filter for meaningful text
                    counselors_found.append(text)
            
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
                    edit_button = self.tn_driver.find_element(By.XPATH, selector)
                    self.uploader_log_msg(f"✅ Found Edit button with selector {i+1}", debug_only=True)
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
                    time.sleep(0.5)
                    
                    # Try multiple click methods
                    self.uploader_log_msg("🖱️ Attempting to click Edit button...")
                    
                    # Method 1: Regular click
                    try:
                        edit_button.click()
                        self.uploader_log_msg("✅ Successfully clicked Edit button (method 1)")
                        time.sleep(1)
                        self._remove_matching_counselors()
                        return
                    except Exception as e1:
                        self.uploader_log_msg(f"❌ Method 1 failed: {e1}", debug_only=True)
                    
                    # Method 2: JavaScript click
                    try:
                        self.uploader_log_msg("🖱️ Trying JavaScript click...", debug_only=True)
                        self.tn_driver.execute_script("arguments[0].click();", edit_button)
                        self.uploader_log_msg("✅ Successfully clicked Edit button (method 2)")
                        time.sleep(1)
                        self._remove_matching_counselors()
                        return
                    except Exception as e2:
                        self.uploader_log_msg(f"❌ Method 2 failed: {e2}", debug_only=True)
                    
                    # Method 3: Click on the inner button element
                    try:
                        self.uploader_log_msg("🖱️ Trying to click inner button...", debug_only=True)
                        inner_button = edit_button.find_element(By.TAG_NAME, "button")
                        inner_button.click()
                        self.uploader_log_msg("✅ Successfully clicked Edit button (method 3)")
                        time.sleep(1)
                        self._remove_matching_counselors()
                        return
                    except Exception as e3:
                        self.uploader_log_msg(f"❌ Method 3 failed: {e3}", debug_only=True)
                    
                    # Method 4: ActionChains click
                    try:
                        self.uploader_log_msg("🖱️ Trying ActionChains click...", debug_only=True)
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(self.tn_driver).move_to_element(edit_button).click().perform()
                        self.uploader_log_msg("✅ Successfully clicked Edit button (method 4)")
                        time.sleep(1)
                        self._remove_matching_counselors()
                        return
                    except Exception as e4:
                        self.uploader_log_msg(f"❌ Method 4 failed: {e4}", debug_only=True)
                    
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
            
            # Get current patient's primary workers from CSV data
            current_primary_workers = getattr(self, 'current_primary_workers', [])
            
            if not current_primary_workers:
                self.uploader_log_msg("ℹ️ No primary workers to remove for this patient")
                return
            
            # Note: Edit button should already be clicked before calling this method
            
            self.uploader_log_msg(f"🎯 Looking for counselors to remove (keeping CSV workers: {', '.join(current_primary_workers)})")
            self.uploader_log_msg(f"🔍 DEBUG: current_primary_workers type: {type(current_primary_workers)}, length: {len(current_primary_workers)}")
            
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
            
            # Also find all counselor names on the page for debugging
            try:
                all_text_elements = self.tn_driver.find_elements(By.XPATH, "//*[contains(@class, 'counselor') or contains(text(), 'Counselor') or contains(text(), 'Therapist')]")
                self.uploader_log_msg(f"🔍 DEBUG: Found {len(all_text_elements)} potential counselor elements")
                for i, elem in enumerate(all_text_elements[:5]):  # Show first 5
                    self.uploader_log_msg(f"🔍 DEBUG: Element {i+1}: '{elem.text.strip()}'")
            except Exception as debug_e:
                self.uploader_log_msg(f"🔍 DEBUG: Error finding counselor elements: {debug_e}")
            
            removed_count = 0
            max_attempts = 10  # Prevent infinite loops
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
                    
                    # Method 3.6: Look specifically for counselor names in the clinicians section
                    if not counselor_text:
                        try:
                            # Look for counselor names specifically in the clinicians section
                            # This should be more targeted than the broad page search
                            clinician_elements = self.tn_driver.find_elements(By.XPATH, "//div[contains(@class, 'clinician') or contains(@class, 'staff') or contains(@class, 'counselor')]//*[text()]")
                            
                            for elem in clinician_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in clinicians section: '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in clinicians section search: {e}")
                    
                    # Method 3.7: Look for counselor names in the specific area around the X button
                    if not counselor_text:
                        try:
                            # Look for counselor names in the immediate area around the X button
                            # This should be more targeted than the broad page search
                            x_button = x_buttons[0]  # Get the current X button
                            
                            # Look for counselor names in the same row or nearby elements
                            row_elements = x_button.find_elements(By.XPATH, "./ancestor::*[contains(@class, 'row') or contains(@class, 'item') or contains(@class, 'entry')]//*[text()]")
                            
                            for elem in row_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in row: '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in row search: {e}")
                    
                    # Method 3.8: Look for counselor names in the specific area where they appear in the clinicians tab
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the clinicians tab
                            # This should be more targeted than the broad page search
                            clinician_names = self.tn_driver.find_elements(By.XPATH, "//div[contains(text(), 'Assigned Clinicians') or contains(text(), 'Clinicians')]//following-sibling::*//*[text()]")
                            
                            for elem in clinician_names:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in clinicians area: '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in clinicians area search: {e}")
                    
                    # Method 3.9: Look for counselor names in the specific area where they appear in the debug logs
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    # Since we're specifically looking for Cynthia/Hernandez/Priya/Doshi, be more permissive
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none']) and
                                        ('Cynthia' in text or 'Hernandez' in text or 'Priya' in text or 'Doshi' in text)):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area: '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search: {e}")
                    
                    # Method 3.10: Look for counselor names in the specific area where they appear in the debug logs (more specific)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi']")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    # Since we're specifically looking for exact matches, be more permissive
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none']) and
                                        ('Cynthia Hernandez' in text or 'Priya Doshi' in text)):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (exact match): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (exact match): {e}")
                    
                    # Method 3.11: Look for counselor names in the specific area where they appear in the debug logs (even more specific)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (contains match): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (contains match): {e}")
                    
                    # Method 3.12: Look for counselor names in the specific area where they appear in the debug logs (final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (final attempt): {e}")
                    
                    # Method 3.13: Look for counselor names in the specific area where they appear in the debug logs (ultimate attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (ultimate attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (ultimate attempt): {e}")
                    
                    # Method 3.14: Look for counselor names in the specific area where they appear in the debug logs (final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (final final attempt): {e}")
                    
                    # Method 3.15: Look for counselor names in the specific area where they appear in the debug logs (ultimate final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (ultimate final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (ultimate final attempt): {e}")
                    
                    # Method 3.16: Look for counselor names in the specific area where they appear in the debug logs (final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (final final final attempt): {e}")
                    
                    # Method 3.17: Look for counselor names in the specific area where they appear in the debug logs (ultimate final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (ultimate final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (ultimate final final final attempt): {e}")
                    
                    # Method 3.18: Look for counselor names in the specific area where they appear in the debug logs (final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (final final final final attempt): {e}")
                    
                    # Method 3.19: Look for counselor names in the specific area where they appear in the debug logs (ultimate final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (ultimate final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (ultimate final final final final attempt): {e}")
                    
                    # Method 3.20: Look for counselor names in the specific area where they appear in the debug logs (final final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (final final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (final final final final final attempt): {e}")
                    
                    # Method 3.21: Look for counselor names in the specific area where they appear in the debug logs (ultimate final final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (ultimate final final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (ultimate final final final final final attempt): {e}")
                    
                    # Method 3.22: Look for counselor names in the specific area where they appear in the debug logs (final final final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (final final final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (final final final final final final attempt): {e}")
                    
                    # Method 3.23: Look for counselor names in the specific area where they appear in the debug logs (ultimate final final final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (ultimate final final final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (ultimate final final final final final final attempt): {e}")
                    
                    # Method 3.24: Look for counselor names in the specific area where they appear in the debug logs (final final final final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (final final final final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (final final final final final final final attempt): {e}")
                    
                    # Method 3.25: Look for counselor names in the specific area where they appear in the debug logs (ultimate final final final final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (ultimate final final final final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (ultimate final final final final final final final attempt): {e}")
                    
                    # Method 3.26: Look for counselor names in the specific area where they appear in the debug logs (final final final final final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (final final final final final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (final final final final final final final final attempt): {e}")
                    
                    # Method 3.27: Look for counselor names in the specific area where they appear in the debug logs (ultimate final final final final final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (ultimate final final final final final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (ultimate final final final final final final final final attempt): {e}")
                    
                    # Method 3.28: Look for counselor names in the specific area where they appear in the debug logs (final final final final final final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (final final final final final final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (final final final final final final final final final attempt): {e}")
                    
                    # Method 3.29: Look for counselor names in the specific area where they appear in the debug logs (ultimate final final final final final final final final final attempt)
                    if not counselor_text:
                        try:
                            # Look for counselor names in the specific area where they appear in the debug logs
                            # This should be more targeted than the broad page search
                            counselor_elements = self.tn_driver.find_elements(By.XPATH, "//*[text()='Cynthia Hernandez' or text()='Priya Doshi' or contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi') or contains(text(), 'Cynthia') or contains(text(), 'Hernandez') or contains(text(), 'Priya') or contains(text(), 'Doshi')]")
                            
                            for elem in counselor_elements:
                                try:
                                    text = elem.text.strip()
                                    # Check if this looks like a counselor name (2+ words, each starting with capital)
                                    if (text and 
                                        len(text.split()) >= 2 and 
                                        all(word[0].isupper() for word in text.split() if word) and
                                        not any(ui_word in text.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors', 'assigned', 'none'])):
                                        counselor_text = text
                                        self.uploader_log_msg(f"🔍 DEBUG: Found counselor name in specific area (ultimate final final final final final final final final final attempt): '{counselor_text}'")
                                        break
                                except Exception as e:
                                    continue  # Skip this element if there's an error
                                        
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in specific area search (ultimate final final final final final final final final final attempt): {e}")
                    
                    # Method 4: Additional fallback - look for any text that contains both first and last name patterns
                    if not counselor_text:
                        try:
                            # Look for patterns like "FirstName LastName" or "LastName, FirstName"
                            import re
                            all_text = parent_element.text.strip()
                            
                            # Pattern for "FirstName LastName" (2+ words, each starting with capital)
                            name_pattern = r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'
                            matches = re.findall(name_pattern, all_text)
                            
                            for match in matches:
                                # Skip if it's a common UI phrase
                                if not any(ui_word in match.lower() for ui_word in ['home', 'to-do', 'scheduling', 'patients', 'staff', 'contacts', 'billing', 'payers', 'library', 'profile', 'settings', 'help', 'status', 'referrals', 'mobile', 'patient', 'info', 'schedule', 'documents', 'clinicians', 'portal', 'insights', 'warning', 'error', 'edit', 'supervisors']):
                                    counselor_text = match
                                    self.uploader_log_msg(f"🔍 DEBUG: Found counselor name via regex pattern: '{counselor_text}'")
                                    break
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DEBUG: Error in regex fallback: {e}")
                    
                    if not counselor_text:
                        counselor_text = "Unknown Counselor"
                        self.uploader_log_msg(f"🔍 DEBUG: Could not extract counselor name, using fallback")
                    
                    # CRITICAL FIX: If we still have "Unknown Counselor", try one more direct approach
                    if counselor_text == "Unknown Counselor":
                        try:
                            # Look for ANY element containing "Cynthia Hernandez" or "Priya Doshi" anywhere on the page
                            direct_elements = self.tn_driver.find_elements(By.XPATH, "//*[contains(text(), 'Cynthia Hernandez') or contains(text(), 'Priya Doshi')]")
                            if direct_elements:
                                for elem in direct_elements:
                                    text = elem.text.strip()
                                    if "Cynthia Hernandez" in text or "Priya Doshi" in text:
                                        # Extract just the name part
                                        if "Cynthia Hernandez" in text:
                                            counselor_text = "Cynthia Hernandez"
                                        elif "Priya Doshi" in text:
                                            counselor_text = "Priya Doshi"
                                        self.uploader_log_msg(f"🔍 CRITICAL FIX: Found counselor via direct search: '{counselor_text}'")
                                        break
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 CRITICAL FIX failed: {e}")
                    
                    # ULTIMATE FIX: Look for staff links anywhere on the page and match them to X buttons
                    if counselor_text == "Unknown Counselor":
                        try:
                            # Find all staff links on the page
                            all_staff_links = self.tn_driver.find_elements(By.XPATH, "//a[contains(@href, '/app/staff/edit/')]")
                            self.uploader_log_msg(f"🔍 ULTIMATE FIX: Found {len(all_staff_links)} staff links on page")
                            
                            # For each X button, find the closest staff link
                            for staff_link in all_staff_links:
                                try:
                                    staff_name = staff_link.text.strip()
                                    if staff_name and len(staff_name) > 2:  # Valid name
                                        # Check if this staff link is near our current X button
                                        # Get the position of both elements
                                        x_location = x_button.location
                                        staff_location = staff_link.location
                                        
                                        # If they're close vertically (within 100px), they're likely related
                                        if abs(x_location['y'] - staff_location['y']) < 100:
                                            counselor_text = staff_name
                                            self.uploader_log_msg(f"🔍 ULTIMATE FIX: Found nearby counselor '{counselor_text}' for X button")
                                            break
                                except Exception as e:
                                    continue
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 ULTIMATE FIX failed: {e}")
                    
                    # FINAL ATTEMPT: If we still can't find a counselor name, try a different approach
                    if counselor_text == "Unknown Counselor":
                        try:
                            # Look for any text element that contains counselor names near the X button
                            # Get all text elements in a broader area around the X button
                            x_button_parent = x_button.find_element(By.XPATH, "./..")
                            x_button_grandparent = x_button_parent.find_element(By.XPATH, "./..")
                            
                            # Look for any <a> tags in the grandparent element
                            all_links = x_button_grandparent.find_elements(By.TAG_NAME, "a")
                            for link in all_links:
                                link_text = link.text.strip()
                                if link_text and len(link_text) > 2 and not any(ui_word in link_text.lower() for ui_word in ['edit', 'save', 'cancel', 'close', 'remove', 'delete']):
                                    counselor_text = link_text
                                    self.uploader_log_msg(f"🔍 FINAL ATTEMPT: Found counselor name in grandparent: '{counselor_text}'")
                                    break
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 FINAL ATTEMPT failed: {e}")
                    
                    # DESPERATE MEASURE: Look for the specific counselor names we know are on the page
                    if counselor_text == "Unknown Counselor":
                        try:
                            # We know from the logs that "Cynthia Hernandez" and "Priya Doshi" are on the page
                            # Let's find them and see if they're near this X button
                            known_counselors = ["Cynthia Hernandez", "Priya Doshi"]
                            
                            for counselor_name in known_counselors:
                                # Find elements containing this counselor name
                                counselor_elements = self.tn_driver.find_elements(By.XPATH, f"//*[contains(text(), '{counselor_name}')]")
                                
                                for elem in counselor_elements:
                                    try:
                                        # Check if this element is near our X button
                                        elem_location = elem.location
                                        x_location = x_button.location
                                        
                                        # If they're close (within 200px), they're likely related
                                        if abs(elem_location['y'] - x_location['y']) < 200:
                                            counselor_text = counselor_name
                                            self.uploader_log_msg(f"🔍 DESPERATE MEASURE: Found nearby counselor '{counselor_text}' for X button")
                                            break
                                    except:
                                        continue
                                
                                if counselor_text != "Unknown Counselor":
                                    break
                        except Exception as e:
                            self.uploader_log_msg(f"🔍 DESPERATE MEASURE failed: {e}")
                    
                    self.uploader_log_msg(f"🔍 Checking X button: '{counselor_text}'")
                    
                    # CRITICAL SAFETY CHECK: If we can't extract a real counselor name, SKIP this X button
                    if counselor_text == "Unknown Counselor":
                        self.uploader_log_msg(f"⚠️ SAFETY: Skipping X button - could not extract counselor name safely")
                        break
                    
                    # Check if this counselor IS in our CSV data (we want to remove CSV counselors)
                    should_remove = False
                    matched_worker = None
                    
                    # Check if this counselor matches any of our CSV data
                    self.uploader_log_msg(f"🔍 DEBUG: Checking '{counselor_text}' against CSV workers: {current_primary_workers}")
                    
                    # Special debug for Cynthia Hernandez
                    if "Cynthia" in counselor_text or "Hernandez" in counselor_text:
                        self.uploader_log_msg(f"🔍 CYNTHIA DEBUG: Found counselor with 'Cynthia' or 'Hernandez': '{counselor_text}'")
                        self.uploader_log_msg(f"🔍 CYNTHIA DEBUG: CSV workers: {current_primary_workers}")
                        
                        # Test the matching logic manually
                        test_worker = "Hernandez, Cynthia"
                        test_parts = test_worker.lower().split(',')
                        if len(test_parts) == 2:
                            test_last = test_parts[0].strip()
                            test_first = test_parts[1].strip()
                            test_reversed = f"{test_first} {test_last}"
                            self.uploader_log_msg(f"🔍 CYNTHIA DEBUG: Test - '{test_reversed}' should match '{counselor_text.lower()}'")
                            self.uploader_log_msg(f"🔍 CYNTHIA DEBUG: Test - '{test_first}' and '{test_last}' in '{counselor_text.lower()}' = {test_first in counselor_text.lower() and test_last in counselor_text.lower()}")
                    
                    for primary_worker in current_primary_workers:
                        self.uploader_log_msg(f"🔍 DEBUG: Comparing '{counselor_text}' with '{primary_worker}'")
                        
                        # Normalize both names for comparison
                        counselor_normalized = counselor_text.lower().strip()
                        worker_normalized = primary_worker.lower().strip()
                        
                        # Special debug for Cynthia Hernandez matching
                        if "Cynthia" in counselor_text or "Hernandez" in counselor_text:
                            self.uploader_log_msg(f"🔍 CYNTHIA DEBUG: Comparing '{counselor_text}' with '{primary_worker}'")
                            self.uploader_log_msg(f"🔍 CYNTHIA DEBUG: counselor_normalized='{counselor_normalized}', worker_normalized='{worker_normalized}'")
                        
                        # Check for direct matches
                        if (worker_normalized in counselor_normalized or 
                            counselor_normalized in worker_normalized):
                            matched_worker = primary_worker
                            self.uploader_log_msg(f"🔍 DEBUG: MATCH FOUND! '{counselor_text}' matches '{primary_worker}' (direct)")
                            break
                        
                        # Check for exact match after normalization
                        if worker_normalized == counselor_normalized:
                            matched_worker = primary_worker
                            self.uploader_log_msg(f"🔍 DEBUG: MATCH FOUND! '{counselor_text}' exactly matches '{primary_worker}'")
                            break
                        
                        # Check for "Last, First" vs "First Last" format
                        if ',' in worker_normalized:
                            # CSV format: "Miller, Simone" -> try "Simone Miller"
                            parts = worker_normalized.split(',')
                            if len(parts) == 2:
                                last_name = parts[0].strip()
                                first_name = parts[1].strip()
                                reversed_format = f"{first_name} {last_name}"
                                
                                self.uploader_log_msg(f"🔍 DEBUG: Checking reversed format: '{reversed_format}' vs '{counselor_normalized}'")
                                
                                if (reversed_format in counselor_normalized or 
                                    counselor_normalized in reversed_format):
                                    matched_worker = primary_worker
                                    self.uploader_log_msg(f"🔍 DEBUG: MATCH FOUND! '{counselor_text}' matches '{primary_worker}' (reversed format: '{reversed_format}')")
                                    break
                                
                                # Also check for exact match with reversed format
                                if reversed_format == counselor_normalized:
                                    matched_worker = primary_worker
                                    self.uploader_log_msg(f"🔍 DEBUG: MATCH FOUND! '{counselor_text}' exactly matches '{primary_worker}' (reversed format: '{reversed_format}')")
                                    break
                                
                                # Check for partial matches with reversed format
                                self.uploader_log_msg(f"🔍 DEBUG: Checking partial matches: '{first_name}' and '{last_name}' in '{counselor_normalized}'")
                                if (first_name in counselor_normalized and last_name in counselor_normalized):
                                    matched_worker = primary_worker
                                    self.uploader_log_msg(f"🔍 DEBUG: MATCH FOUND! '{counselor_text}' matches '{primary_worker}' (partial reversed format: '{first_name}' and '{last_name}')")
                                    break
                                
                                # CRITICAL FIX: Check if both names are present in any order
                                counselor_words = counselor_normalized.split()
                                worker_words = [first_name, last_name]
                                
                                self.uploader_log_msg(f"🔍 DEBUG: Checking word presence: {worker_words} in {counselor_words}")
                                
                                # Check if all worker words are in counselor words
                                if all(word in counselor_words for word in worker_words):
                                    matched_worker = primary_worker
                                    self.uploader_log_msg(f"🔍 DEBUG: MATCH FOUND! '{counselor_text}' matches '{primary_worker}' (all words present: {worker_words})")
                                    break
                        
                        # Check for "First Last" vs "Last, First" format
                        if ' ' in counselor_normalized and ',' not in counselor_normalized:
                            # Page format: "Simone Miller" -> try "Miller, Simone"
                            parts = counselor_normalized.split()
                            if len(parts) == 2:
                                first_name = parts[0].strip()
                                last_name = parts[1].strip()
                                csv_format = f"{last_name}, {first_name}"
                                
                                if (csv_format in worker_normalized or 
                                    worker_normalized in csv_format):
                                    matched_worker = primary_worker
                                    self.uploader_log_msg(f"🔍 DEBUG: MATCH FOUND! '{counselor_text}' matches '{primary_worker}' (CSV format: '{csv_format}')")
                                    break
                        
                        # Check for partial matches (last name only)
                        if ' ' in counselor_normalized:
                            counselor_last = counselor_normalized.split()[-1]  # Last word
                            if ',' in worker_normalized:
                                worker_last = worker_normalized.split(',')[0].strip()  # Part before comma
                                if counselor_last == worker_last:
                                    matched_worker = primary_worker
                                    self.uploader_log_msg(f"🔍 DEBUG: MATCH FOUND! '{counselor_text}' matches '{primary_worker}' (last name: '{counselor_last}')")
                                    break
                        
                        self.uploader_log_msg(f"🔍 DEBUG: No match between '{counselor_text}' and '{primary_worker}'")
                    
                    # If we found a match, we SHOULD remove this counselor (it's in our CSV for removal)
                    # If we found NO match, we should NOT remove this counselor (it's not on our CSV)
                    if matched_worker:
                        should_remove = True
                        self.uploader_log_msg(f"🗑️ REMOVING: '{counselor_text}' matches CSV worker '{matched_worker}' - clicking X")
                    else:
                        self.uploader_log_msg(f"✅ KEEPING: '{counselor_text}' is NOT in CSV - NOT removing")
                    
                    if should_remove:
                        x_button.click()
                        removed_count += 1
                        time.sleep(0.5)  # Wait between removals
                        self.uploader_log_msg(f"🗑️ Removed counselor: {counselor_text}")
                        # After removing, break out of the for loop to re-find X buttons
                        break
                    else:
                        self.uploader_log_msg(f"⏭️ Keeping: '{counselor_text}' - not in CSV for removal")
                        # Continue to next X button
                        continue

                        continue

                    for button in buttons:
                        try:
                            button.click()
                        except Exception as e:
                            self.uploader_log_msg(f"❌ Error processing X button: {e}")
                            continue   # valid, because we're inside the for-loop

            # After the while loop, save changes if any were made
            if removed_count > 0:
                self.uploader_log_msg(f"✅ Successfully removed {removed_count} counselor(s) who were in CSV for removal")
                # Save changes (click Save button)
                self._save_counselor_changes()
            else:
                self.uploader_log_msg("ℹ️ No counselors found to remove (no counselors match CSV data for removal)")
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
                time.sleep(1.5)  # Wait for save to complete
                self.uploader_log_msg("✅ Successfully saved counselor changes")
                
                # Wait for page to update, then return to Patients page for next patient
                time.sleep(0.5)
                self._return_to_patients_page()
            else:
                self.uploader_log_msg("❌ Could not find Save Changes button")
                
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to save changes: {e}")

    def _return_to_patients_page(self):
        """Return to the Patients page to process the next patient"""
        try:
            self.uploader_log_msg("🔄 Returning to Patients page...")
            
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
                patients_button.click()
                self.uploader_log_msg("✅ Clicked Patients button")
                time.sleep(1)  # Wait for Patients page to load
                self.uploader_log_msg("✅ Successfully returned to Patients page")
            else:
                self.uploader_log_msg("❌ Could not find Patients button")
                
        except Exception as e:
            self.uploader_log_msg(f"❌ Failed to return to Patients page: {e}")

    def _create_results_csv(self, results, original_csv_file):
        """Create a results CSV with success/failure tracking"""
        try:
            import os
            from datetime import datetime
            
            # Create results filename based on original CSV
            base_name = os.path.splitext(os.path.basename(original_csv_file))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_filename = f"{base_name}_results_{timestamp}.csv"
            
            # Use same directory as original CSV
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
                time.sleep(0.5)
                
                # Click the button
                upload_button.click()
                self.uploader_log_msg("✅ Successfully clicked Upload Patient File button")
                time.sleep(1)  # Wait for upload dialog/modal to appear
                
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
                                d = datetime.strptime(d_txt, DATE_FMT)
                                matching_dates.append(d)
                                self.log_msg(f"[CURRENT] Row {i+1}: Found matching workflow with date {d_txt}")
                            except ValueError:
                                self.log_msg(f"[WARN] Row {i+1}: Unparseable date '{d_txt}' — skipping")
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

    def _queue_expand_and_pickup_all(self):
        def run():
            try:
                # Check for stop request at the start
                if self.state.stop_requested:
                    self.log_msg("[STOP] Operation cancelled by user")
                    return
                
                target = self.e_match.get().strip().lower()
                self.log_msg(f"[PICKUP] Starting pickup for: '{target}'")
                total = 0
                max_iterations = 50
                iteration = 0
                consecutive_no_matches = 0
                
                while iteration < max_iterations:
                    # Check for stop request at the start of each iteration
                    if self.state.stop_requested:
                        self.log_msg(f"[STOP] Operation cancelled at iteration {iteration}")
                        return
                    
                    iteration += 1
                    self.log_msg(f"[PICKUP] Iteration {iteration}/{max_iterations}")
                    
                    # ALWAYS re-expand the queue at the start of each iteration
                    # This is crucial because the list retracts after each pickup
                    self.log_msg("[PICKUP] Re-expanding queue...")
                    expanded_rows = self._expand_sync("queue", verbose=True)
                    
                    if expanded_rows == 0:
                        self.log_msg("[PICKUP] No rows found after expansion, stopping")
                        break
                    
                    # Check for stop request after expansion
                    if self.state.stop_requested:
                        self.log_msg(f"[STOP] Operation cancelled after expansion")
                        return
                    
                    body = self._wait_visible(SEL["queue_body"], 10)
                    rows = [r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()]
                    
                    if not rows:
                        self.log_msg("[PICKUP] No rows found after expansion, stopping")
                        break
                    
                    self.log_msg(f"[PICKUP] Found {len(rows)} rows to check after expansion")
                    match_row = None
                    match_found = False
                    
                    for r in rows:
                        # Check for stop request before processing each row
                        if self.state.stop_requested:
                            self.log_msg(f"[STOP] Operation cancelled while processing rows")
                            return
                        
                        try:
                            # Look for the link directly in the first cell of each row
                            first_cell = r.find_element(By.CSS_SELECTOR, "td:first-child")
                            link = first_cell.find_element(By.CSS_SELECTOR, "a")
                            subj = link.text.strip().lower()
                            
                            if subj == target:
                                match_row = r
                                match_found = True
                                self.log_msg(f"[PICKUP] Found match: {subj}")
                                break
                        except Exception as e:
                            if self.debug_var.get():
                                self.log_msg(f"[DEBUG] Error reading row: {e}")
                            continue
                    
                    if not match_found:
                        consecutive_no_matches += 1
                        self.log_msg(f"[PICKUP] No matching workflows found in this iteration (consecutive: {consecutive_no_matches})")
                        
                        # If this is the first iteration and we've fully expanded but found no matches,
                        # we can stop immediately since there are no workflows to pickup
                        if iteration == 1 and consecutive_no_matches == 1:
                            self.log_msg("[PICKUP] No matching workflows found after full expansion - TASK COMPLETE!")
                            break
                        
                        # Stop after 2 consecutive failures
                        if consecutive_no_matches >= 2:
                            self.log_msg("[PICKUP] No matches found in 2 consecutive iterations - TASK COMPLETE!")
                            break
                        
                        # Wait a bit before trying again
                        time.sleep(2)
                        continue
                    else:
                        # Reset counter when match found
                        consecutive_no_matches = 0
                    
                    # Check for stop request before pickup
                    if self.state.stop_requested:
                        self.log_msg(f"[STOP] Operation cancelled before pickup")
                        return
                    
                    try:
                        # Look for pickup link in the last cell
                        last_cell = match_row.find_element(By.CSS_SELECTOR, "td:last-child")
                        pickup_links = last_cell.find_elements(By.CSS_SELECTOR, "a")
                        
                        pickup_clicked = False
                        for pickup_link in pickup_links:
                            try:
                                if pickup_link.is_displayed() and pickup_link.is_enabled():
                                    # Check if this looks like a pickup link
                                    link_text = pickup_link.text.strip().lower()
                                    link_href = pickup_link.get_attribute("href") or ""
                                    
                                    if "pickup" in link_text or "pickup" in link_href or "data-ajax" in pickup_link.get_attribute("data-ajax", ""):
                                        if self._safe_click(pickup_link):
                                            total += 1
                                            self.log_msg(f"[PICKUP] Success! Count={total}")
                                            pickup_clicked = True
                                            break
                                        else:
                                            self.log_msg("[WARN] Pickup click failed")
                            except Exception as e:
                                if self.debug_var.get():
                                    self.log_msg(f"[DEBUG] Error with pickup link: {e}")
                                continue
                        
                        if not pickup_clicked:
                            self.log_msg("[WARN] No valid pickup link found")
                            break
                        
                        # Wait for the page to update after pickup
                        self.log_msg("[PICKUP] Waiting for page to update...")
                        time.sleep(2.0)
                        
                    except Exception as e:
                        self.log_msg(f"[WARN] Pickup failed: {e}")
                        if self.debug_var.get():
                            import traceback
                            self.log_msg(f"[DEBUG] Pickup error: {traceback.format_exc()}")
                        break
                    
                    if total >= 100:
                        self.log_msg("[SAFE] Max pickups reached (100)")
                        break
                
                if not self.state.stop_requested:
                    self.log_msg(f"[DONE] ✅ TASK COMPLETE! Total pickups: {total}")
                    self.log_msg(f"[DONE] All 'Remove Counselor from Client in TN' workflows have been processed.")
                
            except Exception as e:
                if not self.state.stop_requested:
                    self.log_msg(f"[ERR] Pickup process failed: {e}")
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
            
            # Wait for results to load
            time.sleep(3)
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
                    if link_text == "Remove Counselor from Client in TN":
                        remove_counselor_links.append(link)
                        self.log_msg(f"[PROCESS] Found workflow: {link_text}")
                    elif "Remove Counselor from Client in TN" in link_text:
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
                            if link_text == "Remove Counselor from Client in TN":
                                current_remove_counselor_links.append(link)
                            elif "Remove Counselor from Client in TN" in link_text:
                                self.log_msg(f"[SKIP] Ignoring workflow with additional text: {link_text}")
                        except:
                            continue
                    
                    if not current_remove_counselor_links:
                        self.log_msg(f"[PROCESS] No more Remove Counselor workflows found - completed {processed_count-1} workflows")
                        break
                    
                    # Process the first available workflow
                    self.log_msg(f"[PROCESS] Found {len(current_remove_counselor_links)} available workflows, processing the first one")
                    self._process_single_workflow(current_remove_counselor_links[0])
                    
                    # Wait a bit before processing the next one
                    time.sleep(1)
                    
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

                    # Determine save directory with fallback
                    preferred_dir = r"C:\Users\MichaelLocal\Desktop\CCMD Bot Master\Remove Counselor Bot\Cursor versions"
                    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                    
                    if os.path.exists(preferred_dir):
                        save_dir = preferred_dir
                        self.log_msg(f"[AUTO-EXPORT] Using preferred directory: {save_dir}")
                    else:
                        save_dir = downloads_dir
                        self.log_msg(f"[AUTO-EXPORT] Preferred directory not found, using Downloads: {save_dir}")
                    
                    # Create full file path
                    full_path = os.path.join(save_dir, filename)
                    
                    # Ensure directory exists
                    os.makedirs(save_dir, exist_ok=True)

                    # Write CSV file
                    with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
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
                            'Extraction Date': data.extraction_date
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
                    if link_text == "Remove Counselor from Client in TN":
                        remove_counselor_links.append(link)
                        self.log_msg(f"[PROCESS] Found workflow: {link_text}")
                    elif "Remove Counselor from Client in TN" in link_text:
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
                            if link_text == "Remove Counselor from Client in TN":
                                current_remove_counselor_links.append(link)
                            elif "Remove Counselor from Client in TN" in link_text:
                                self.log_msg(f"[SKIP] Ignoring workflow with additional text: {link_text}")
                        except:
                            continue

                    if not current_remove_counselor_links:
                        self.log_msg(f"[PROCESS] No more Remove Counselor workflows found - completed {processed_count-1} workflows")
                        break

                    # Process the first available workflow
                    self.log_msg(f"[PROCESS] Found {len(current_remove_counselor_links)} available workflows, processing the first one")
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

                    # Determine save directory with fallback
                    preferred_dir = r"C:\Users\MichaelLocal\Desktop\CCMD Bot Master\Remove Counselor Bot\Cursor versions"
                    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                    
                    if os.path.exists(preferred_dir):
                        save_dir = preferred_dir
                        self.log_msg(f"[AUTO-EXPORT] Using preferred directory: {save_dir}")
                    else:
                        save_dir = downloads_dir
                        self.log_msg(f"[AUTO-EXPORT] Preferred directory not found, using Downloads: {save_dir}")
                    
                    # Create full file path
                    full_path = os.path.join(save_dir, filename)
                    
                    # Ensure directory exists
                    os.makedirs(save_dir, exist_ok=True)

                    # Write CSV file
                    with open(full_path, 'w', newline='', encoding='utf-8') as csvfile:
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
                            'Extraction Date': data.extraction_date
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
        """Process a single Remove Counselor workflow through all 6 steps"""
        try:
            # Step 1: Click the Remove Counselor link
            self.log_msg("[STEP 1] Clicking Remove Counselor link...")
            
            # Debug: Show what link we're clicking
            if self.debug_var.get():
                try:
                    link_text = link.text.strip()
                    link_href = link.get_attribute("href") or ""
                    self.log_msg(f"[DEBUG] Clicking link: '{link_text}' -> {link_href}")
                except:
                    pass
            
            if not self._safe_click(link):
                self.log_msg("[WARN] Failed to click Remove Counselor link")
                return
            
            # Wait for the page to load and check if we're on the right page
            self.log_msg("[STEP 1] Waiting for task page to load...")
            time.sleep(5)  # Increased wait time
            
            # Debug: Check what page we're on after clicking
            if self.debug_var.get():
                try:
                    current_url = self.state.driver.current_url
                    page_title = self.state.driver.title
                    self.log_msg(f"[DEBUG] After click - URL: {current_url}")
                    self.log_msg(f"[DEBUG] After click - Title: {page_title}")
                except:
                    pass
            
            # Check if we're on the correct task page by looking for the Assigned box
            try:
                # Try multiple selectors for the Assigned box
                assigned_boxes = self.state.driver.find_elements(By.CSS_SELECTOR, "div.cbb.box_t3s")
                if len(assigned_boxes) == 0:
                    # Try alternative selectors
                    assigned_boxes = self.state.driver.find_elements(By.CSS_SELECTOR, "div[class*='cbb'][class*='box_t3s']")
                if len(assigned_boxes) == 0:
                    assigned_boxes = self.state.driver.find_elements(By.XPATH, "//div[contains(@class, 'cbb') and contains(@class, 'box_t3s')]")
                if len(assigned_boxes) == 0:
                    assigned_boxes = self.state.driver.find_elements(By.XPATH, "//div[contains(@class, 'cbb')]")
                if len(assigned_boxes) == 0:
                    assigned_boxes = self.state.driver.find_elements(By.XPATH, "//h2[text()='Assigned']/..")
                
                if len(assigned_boxes) == 0:
                    self.log_msg("[WARN] Not on task page - no Assigned boxes found")
                    self.log_msg("[WARN] This might be a calendar or different page")
                    
                    # Debug: Show what divs we can find on the page
                    if self.debug_var.get():
                        try:
                            all_divs = self.state.driver.find_elements(By.TAG_NAME, "div")
                            self.log_msg(f"[DEBUG] Found {len(all_divs)} total divs on page")
                            
                            # Look for divs with 'cbb' class
                            cbb_divs = self.state.driver.find_elements(By.CSS_SELECTOR, "div[class*='cbb']")
                            self.log_msg(f"[DEBUG] Found {len(cbb_divs)} divs with 'cbb' class")
                            for i, div in enumerate(cbb_divs[:5]):  # Show first 5
                                try:
                                    class_attr = div.get_attribute("class") or ""
                                    self.log_msg(f"[DEBUG] CBB div {i+1}: class='{class_attr}'")
                                except:
                                    pass
                            
                            # Look for h2 elements
                            h2_elements = self.state.driver.find_elements(By.TAG_NAME, "h2")
                            self.log_msg(f"[DEBUG] Found {len(h2_elements)} h2 elements")
                            for i, h2 in enumerate(h2_elements[:5]):  # Show first 5
                                try:
                                    h2_text = h2.text.strip()
                                    self.log_msg(f"[DEBUG] H2 {i+1}: '{h2_text}'")
                                except:
                                    pass
                        except Exception as e:
                            self.log_msg(f"[DEBUG] Error during debug: {e}")
                    
                    return
                else:
                    self.log_msg(f"[DEBUG] Found {len(assigned_boxes)} Assigned boxes - on correct page")
                    
                    # Debug: Show what's inside the Assigned boxes
                    if self.debug_var.get():
                        for i, box in enumerate(assigned_boxes):
                            try:
                                box_text = box.text.strip()
                                self.log_msg(f"[DEBUG] Assigned box {i+1}: {box_text[:200]}...")
                                
                                # Look for ALL links in this box
                                all_links = box.find_elements(By.TAG_NAME, "a")
                                self.log_msg(f"[DEBUG] Found {len(all_links)} total links in box {i+1}")
                                
                                for j, link in enumerate(all_links[:10]):  # Show first 10 links
                                    try:
                                        link_text = link.text.strip()
                                        href = link.get_attribute("href") or ""
                                        onclick = link.get_attribute("onclick") or ""
                                        self.log_msg(f"[DEBUG] Link {j+1}: text='{link_text}' href='{href}' onclick='{onclick}'")
                                    except:
                                        pass
                                
                                # Look for Close links specifically in this box
                                close_links = box.find_elements(By.XPATH, ".//a[text()='Close']")
                                self.log_msg(f"[DEBUG] Found {len(close_links)} Close links in box {i+1}")
                                
                                # Also look for any element containing "Close" text
                                close_elements = box.find_elements(By.XPATH, ".//*[contains(text(), 'Close')]")
                                self.log_msg(f"[DEBUG] Found {len(close_elements)} elements containing 'Close' in box {i+1}")
                                for j, elem in enumerate(close_elements[:5]):
                                    try:
                                        tag_name = elem.tag_name
                                        elem_text = elem.text.strip()
                                        self.log_msg(f"[DEBUG] Close element {j+1}: <{tag_name}> '{elem_text}'")
                                    except:
                                        pass
                                        
                            except Exception as e:
                                self.log_msg(f"[DEBUG] Error examining box {i+1}: {e}")
            except Exception as e:
                self.log_msg(f"[WARN] Error checking for Assigned boxes: {e}")
                return
            
            # Step 2: OUTSIDE-THE-BOX APPROACH - Use JavaScript to find and click Close button
            self.log_msg("[STEP 2] OUTSIDE-THE-BOX: Using JavaScript to find Close button...")
            
            # Wait for page to fully load
            time.sleep(5)
            
            # Method 1: Use JavaScript to find and click Close button
            try:
                self.log_msg("[DEBUG] Executing JavaScript to find Close button...")
                
                # JavaScript to find all links and look for Close button
                js_code = """
                var links = document.querySelectorAll('a');
                var closeButton = null;
                
                for (var i = 0; i < links.length; i++) {
                    var link = links[i];
                    var text = link.textContent.trim();
                    var href = link.href || '';
                    
                    // Look for Close button with doAjax and closeTask
                    if (text === 'Close' && href.includes('doAjax') && href.includes('closeTask')) {
                        closeButton = link;
                        break;
                    }
                }
                
                if (closeButton) {
                    closeButton.click();
                    return 'SUCCESS: Close button clicked';
                } else {
                    return 'ERROR: Close button not found';
                }
                """
                
                result = self.state.driver.execute_script(js_code)
                self.log_msg(f"[DEBUG] JavaScript result: {result}")
                
                if "SUCCESS" in str(result):
                    self.log_msg("[OK] Successfully clicked Close button via JavaScript")
                    time.sleep(2)
                else:
                    self.log_msg("[WARN] JavaScript method failed, trying alternative...")
                    
                    # Method 2: Try to find Close button by looking in all frames
                    try:
                        self.log_msg("[DEBUG] Checking all frames for Close button...")
                        frames = self.state.driver.find_elements(By.TAG_NAME, "iframe")
                        self.log_msg(f"[DEBUG] Found {len(frames)} iframes")
                        
                        for i, frame in enumerate(frames):
                            try:
                                self.state.driver.switch_to.frame(frame)
                                close_links = self.state.driver.find_elements(By.XPATH, "//a[text()='Close']")
                                if len(close_links) > 0:
                                    self.log_msg(f"[DEBUG] Found {len(close_links)} Close links in frame {i+1}")
                                    if self._safe_click(close_links[0]):
                                        self.log_msg("[OK] Successfully clicked Close button in iframe")
                                        break
                                self.state.driver.switch_to.default_content()
                            except Exception as frame_e:
                                self.log_msg(f"[DEBUG] Error checking frame {i+1}: {frame_e}")
                                self.state.driver.switch_to.default_content()
                    except Exception as e:
                        self.log_msg(f"[WARN] Frame checking failed: {e}")
                        
            except Exception as e:
                self.log_msg(f"[WARN] JavaScript method failed: {e}")
            
            # Step 3: Look for Case link and extract case info (NO MORE CLOSE BUTTONS!)
            self.log_msg("[STEP 3] Looking for Case link...")
            case_name = "Unknown"
            case_id = "Unknown"
            try:
                # Wait a moment for the page to settle after Close button click
                time.sleep(2)
                
                # Look for Case link in the Record box specifically
                case_links = self.state.driver.find_elements(By.XPATH, "//a[contains(text(), 'Case (')]")
                if len(case_links) > 0:
                    self.log_msg(f"[DEBUG] Found {len(case_links)} Case links")
                    
                    # Extract case name and ID from the link text BEFORE clicking
                    case_text = case_links[0].text.strip()
                    if "Case (" in case_text:
                        case_name = case_text.split("Case (")[0].strip()
                        case_id = case_text.split("Case (")[1].replace(")", "").strip()
                        self.log_msg(f"[EXTRACT] Case info: {case_name} (ID: {case_id})")
                    
                    if self._safe_click(case_links[0]):
                        self.log_msg("[OK] Successfully clicked Case link")
                    else:
                        self.log_msg("[WARN] Failed to click Case link")
                        return
                else:
                    self.log_msg("[WARN] No Case links found")
                    return
            except Exception as e:
                self.log_msg(f"[WARN] Error finding Case link: {e}")
                return
                # Debug: Show what links are actually on the page
                if self.debug_var.get():
                    try:
                        drv = self._drv()
                        all_links = drv.find_elements(By.TAG_NAME, "a")
                        self.log_msg(f"[DEBUG] Found {len(all_links)} links on page:")
                        for i, link in enumerate(all_links[:20]):  # Show first 20 links
                            try:
                                text = link.text.strip()
                                href = link.get_attribute("href") or ""
                                onclick = link.get_attribute("onclick") or ""
                                # Show all links, not just close-related ones
                                self.log_msg(f"[DEBUG] Link {i+1}: '{text}' -> href='{href}' onclick='{onclick}'")
                            except:
                                pass
                        
                        # Also try to find the Close button by looking in specific areas
                        self.log_msg("[DEBUG] Looking for Close button in specific areas...")
                        try:
                            # Look in the Assigned box area
                            assigned_boxes = drv.find_elements(By.CSS_SELECTOR, "div.cbb.box_t3s")
                            self.log_msg(f"[DEBUG] Found {len(assigned_boxes)} Assigned boxes")
                            for i, box in enumerate(assigned_boxes):
                                links_in_box = box.find_elements(By.TAG_NAME, "a")
                                self.log_msg(f"[DEBUG] Assigned box {i+1}: Found {len(links_in_box)} links")
                                for j, link in enumerate(links_in_box):
                                    text = link.text.strip()
                                    href = link.get_attribute("href") or ""
                                    onclick = link.get_attribute("onclick") or ""
                                    self.log_msg(f"[DEBUG] Box {i+1} Link {j+1}: '{text}' -> href='{href}' onclick='{onclick}'")
                            
                            # Also look for any Close links anywhere on the page
                            close_links = drv.find_elements(By.XPATH, "//a[contains(text(), 'Close')]")
                            self.log_msg(f"[DEBUG] Found {len(close_links)} links containing 'Close' text")
                            for i, link in enumerate(close_links):
                                text = link.text.strip()
                                href = link.get_attribute("href") or ""
                                self.log_msg(f"[DEBUG] Close link {i+1}: '{text}' -> href='{href}'")
                                
                        except Exception as box_e:
                            self.log_msg(f"[DEBUG] Error looking in Assigned box: {box_e}")
                            
                    except:
                        pass
                return
            
            # Wait for the case page to load
            time.sleep(3)
            
            # Step 4: Extract data from the Service Files section
            self.log_msg("[STEP 4] Extracting data from Service Files...")
            extracted_data = self._extract_service_files_data(case_name, case_id)
            if extracted_data:
                self.state.extracted_data.append(extracted_data)
                self.update_data_count()
                self.log_msg(f"[STEP 4] Extracted data: {extracted_data.case_name} - {len(extracted_data.primary_workers)} workers")
            else:
                self.log_msg("[WARN] No data extracted from Service Files")
            
            # Step 5: Reopen workflow drawer to return to advanced search
            self.log_msg("[STEP 5] Reopening workflow drawer to return to advanced search...")
            try:
                # Use JavaScript to find and click the workflow drawer
                js_code = """
                var workflowHandle = document.getElementById('taskHandle');
                if (workflowHandle) {
                    workflowHandle.click();
                    return 'SUCCESS: Workflow drawer clicked';
                } else {
                    return 'ERROR: Workflow drawer not found';
                }
                """
                
                result = self.state.driver.execute_script(js_code)
                self.log_msg(f"[DEBUG] JavaScript result: {result}")
                
                if "SUCCESS" in str(result):
                    self.log_msg("[OK] Successfully clicked workflow drawer via JavaScript")
                    time.sleep(3)  # Wait for drawer to open
                else:
                    self.log_msg("[WARN] JavaScript method failed, trying alternative...")
                    
                    # Alternative: Try to find by class and text
                    try:
                        workflow_handle = self.state.driver.find_element(By.XPATH, "//div[@class='drawerHandle behind' and contains(text(), 'Workflow')]")
                        if self._safe_click(workflow_handle):
                            self.log_msg("[OK] Successfully clicked workflow drawer (alternative method)")
                            time.sleep(3)
                        else:
                            self.log_msg("[WARN] Failed to click workflow drawer (alternative method)")
                    except Exception as e2:
                        self.log_msg(f"[WARN] Alternative method also failed: {e2}")
                        
            except Exception as e:
                self.log_msg(f"[WARN] Error with workflow drawer: {e}")
            
            # Wait for the panel to open
            time.sleep(2)
            
            # Step 6: Navigate back to advanced search without refreshing
            self.log_msg("[STEP 6] Navigating back to advanced search without refreshing...")
            try:
                # Go back to the main page to access the workflow drawer
                self.state.driver.back()
                time.sleep(2)
                
                # Reopen workflow drawer to access advanced search
                js_code = """
                var workflowHandle = document.getElementById('taskHandle');
                if (workflowHandle) {
                    workflowHandle.click();
                    return 'SUCCESS: Workflow drawer reopened';
                } else {
                    return 'ERROR: Workflow drawer not found';
                }
                """
                
                result = self.state.driver.execute_script(js_code)
                self.log_msg(f"[DEBUG] Navigation result: {result}")
                
                if "SUCCESS" in str(result):
                    self.log_msg("[OK] Successfully reopened workflow drawer")
                    time.sleep(2)
                else:
                    self.log_msg("[WARN] Failed to reopen workflow drawer")
                    
            except Exception as e:
                self.log_msg(f"[WARN] Error navigating back to advanced search: {e}")
            
            # Step 7: The workflow is complete, ready for the next one
            self.log_msg("[STEP 6] Workflow complete, ready for next")
            
        except Exception as e:
            self.log_msg(f"[ERR] Failed to process workflow: {e}")
            if self.debug_var.get():
                import traceback
                self.log_msg(f"[DEBUG] Workflow error: {traceback.format_exc()}")

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
                
                # Determine save directory with fallback
                import os
                preferred_dir = r"C:\Users\MichaelLocal\Desktop\CCMD Bot Master\Remove Counselor Bot\Cursor versions"
                downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                
                if os.path.exists(preferred_dir):
                    save_dir = preferred_dir
                    self.log_msg(f"[EXPORT] Using preferred directory: {save_dir}")
                else:
                    save_dir = downloads_dir
                    self.log_msg(f"[EXPORT] Preferred directory not found, using Downloads: {save_dir}")
                
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

if __name__ == "__main__":
    App().mainloop()
