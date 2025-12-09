#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Penelope Workflow Tool — Multi-Purpose Workflow Automation
Reuses core functions from Remove Counselor bot for Penelope navigation
"""

import time, threading, csv, os, re, json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

APP_TITLE = "Penelope Workflow Tool"
VERSION = "1.0"
LOGIN_URL = "https://integrityseniorservices.athena-us.com/acm_loginControl"
DATE_FMT = "%m/%d/%Y"
MAROON = "#800000"

# Selectors from Remove Counselor bot
SEL = {
    "user": (By.ID, "login_userName"),
    "pass": (By.ID, "login_password"),
    "login_btn": (By.CSS_SELECTOR, "button[type='submit']"),
    "workflow_handle": (By.ID, "taskHandle"),
    "tab_current": (By.ID, "taskCurrentView"),
    "tab_advanced": (By.ID, "taskAdvancedView"),
    "current_body": (By.ID, "taskCurrentBody"),
    "queue_body": (By.ID, "taskQueueBody"),
    "current_load_more": (By.ID, "currentTasksLoadMoreButton"),
    "queue_load_more": (By.ID, "queuedTasksLoadMoreButton"),
    "adv_from": (By.ID, "fromDate"),
    "adv_to": (By.ID, "toDate"),
    "adv_search": (By.ID, "advancedTaskSearchBtn"),
}

@dataclass
class WorkflowData:
    """Store workflow data and chunks"""
    tasks: List[Dict] = field(default_factory=list)
    chunks: List[Tuple[str, str]] = field(default_factory=list)
    next_chunk_index: int = 0
    
    def add_task(self, task_data: Dict):
        self.tasks.append(task_data)
    
    def clear(self):
        self.tasks.clear()
        self.chunks.clear()
        self.next_chunk_index = 0
    
    def count(self):
        return len(self.tasks)

class PenelopeWorkflowApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Penelope Workflow Tool - Version 3.1.0, Last Updated 12/04/2025")
        self.geometry("1000x700")  # Reduced from 1200x800 to 1000x700
        
        self.driver = None
        self.logged_in = False
        self.workflow_data = WorkflowData()
        self.stop_requested = False  # Stop flag for operations
        
        # Resume state
        self.paused_operation = None  # Stores: {"action": "pickup"/"close", "workflows": [...], "index": 5}
        self.resume_btn = None  # Will store reference to resume button
        
        # Date range for advanced search
        self.current_chunk_start = None
        self.current_chunk_end = None
        self.chunk_size_days = 14  # 2-week chunks
        
        # User management
        self.users_file = Path(__file__).parent / "penelope_users.json"  # Store users in same directory as script
        self.users = {}  # Dictionary to store users: {"name": {"username": "...", "password": "...", "url": "..."}}
        self.load_users()  # Load existing users on startup
        
        # UI Variables
        self.pn_user = tk.StringVar()
        self.pn_pass = tk.StringVar()
        self.pn_url = tk.StringVar(value=LOGIN_URL)
        
        # Workflow selection - checkboxes for multiple selection
        self.workflow_selections = {
            "Add/Review Documents": tk.BooleanVar(value=False),
            "Remove Counselor from Client in TN": tk.BooleanVar(value=False),
            "Send Welcome Letter and NPP": tk.BooleanVar(value=False),
            "Discharge Request": tk.BooleanVar(value=False)
        }
        
        # Custom workflow option
        self.custom_workflow = tk.StringVar(value="")
        self.use_custom_workflow = tk.BooleanVar(value=False)
        
        # Build UI matching Remove Counselor bot
        self._build_ui()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def load_users(self):
        """Load users from JSON file"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r') as f:
                    self.users = json.load(f)
            else:
                # Create empty users file if it doesn't exist
                self.users = {}
                self.save_users()
        except Exception as e:
            # Log will be created later in _build_log_section
            self.users = {}
    
    def save_users(self):
        """Save users to JSON file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            return True
        except Exception as e:
            self.log_msg(f"Error saving users: {e}")
            messagebox.showerror("Error", f"Failed to save users:\n{e}")
            return False
    
    def _build_ui(self):
        """Build UI matching Remove Counselor bot layout with scrolling"""
        # Configure styles
        style = ttk.Style()
        style.configure("Big.TButton", padding=6, font=("Segoe UI", 10))
        style.configure("Success.TButton", padding=6, font=("Segoe UI", 10))
        style.configure("Stop.TButton", padding=6, font=("Segoe UI", 10, "bold"), foreground="red")
        
        # Header (maroon like Remove Counselor bot)
        header = tk.Frame(self, bg="#660000")
        header.pack(fill="x")
        tk.Label(header, text=APP_TITLE, bg="#660000", fg="white",
                 font=("Segoe UI", 14, "bold"), pady=6).pack(side="left", padx=12)
        
        # Create scrollable main content area
        # Canvas for scrolling
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
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
        
        # Bind mousewheel to canvas for smooth scrolling - works anywhere in the window
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to the main window and all child widgets
        def _bind_to_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_to_mousewheel(child)
        
        # Initial binding
        self.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
        
        # Store canvas for later access
        self.main_canvas = canvas
        self.scrollable_frame = scrollable_frame
        
        # Rebind after widgets are created
        def _rebind_all():
            _bind_to_mousewheel(scrollable_frame)
        
        self.after(100, _rebind_all)
        
        # Main content area inside scrollable frame
        main_content = tk.Frame(scrollable_frame)
        main_content.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Penelope Login Section
        self._build_login_section(main_content)
        
        # Workflow Configuration Section
        self._build_workflow_config_section(main_content)
        
        # Bot Controls Section
        self._build_controls_section(main_content)
        
        # Status Section
        self._build_status_section(main_content)
        
        # Log Area
        self._build_log_section(main_content)
    
    def _build_login_section(self, parent):
        """Build Penelope login section"""
        login_frame = tk.LabelFrame(parent, text="Penelope Login", font=("Segoe UI", 12, "bold"))
        login_frame.pack(fill="x", pady=(0, 20))
        
        # User Selection Row
        user_row = tk.Frame(login_frame)
        user_row.pack(fill="x", padx=10, pady=(10, 5))
        
        tk.Label(user_row, text="Saved User:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))
        
        # User Selection Dropdown
        self.user_dropdown = ttk.Combobox(user_row, font=("Segoe UI", 10), width=25, state="readonly")
        self.user_dropdown.pack(side="left", padx=(0, 10))
        self.user_dropdown.bind("<<ComboboxSelected>>", self._on_user_selected)
        self._update_user_dropdown()
        
        # Add User button
        self.add_user_button = tk.Button(user_row, text="Add User", 
                                         command=self._add_user,
                                         bg=MAROON, fg="white", font=("Segoe UI", 9),
                                         padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        self.add_user_button.pack(side="left", padx=(0, 5))
        
        # Update User button
        self.update_user_button = tk.Button(user_row, text="Update User", 
                                            command=self._update_credentials,
                                            bg="#666666", fg="white", font=("Segoe UI", 9),
                                            padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        self.update_user_button.pack(side="left", padx=(0, 5))
        
        cred_frame = tk.Frame(login_frame)
        cred_frame.pack(fill="x", padx=10, pady=10)
        
        # Username
        tk.Label(cred_frame, text="Username:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.e_user = ttk.Entry(cred_frame, textvariable=self.pn_user, width=30)
        self.e_user.grid(row=0, column=1, padx=(0, 20))
        
        # Password
        tk.Label(cred_frame, text="Password:").grid(row=0, column=2, sticky="w", padx=(0, 10))
        self.e_pass = ttk.Entry(cred_frame, textvariable=self.pn_pass, width=30, show="•")
        self.e_pass.grid(row=0, column=3, padx=(0, 20))
        
        # Login button
        ttk.Button(cred_frame, text="Login to Penelope", style="Big.TButton",
                   command=self._login_penelope).grid(row=0, column=4)
        
        # STOP button
        ttk.Button(cred_frame, text="🛑 STOP BOT", style="Stop.TButton",
                   command=self._stop_bot).grid(row=0, column=5, padx=(20, 0))
        
        # RESUME button (initially disabled)
        self.resume_btn = ttk.Button(cred_frame, text="▶️ RESUME", style="Success.TButton",
                                     command=self._resume_bot, state="disabled")
        self.resume_btn.grid(row=0, column=6, padx=(10, 0))
        
        # URL config
        url_frame = tk.Frame(login_frame)
        url_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        tk.Label(url_frame, text="Penelope URL:", font=("Segoe UI", 10)).grid(row=0, column=0, padx=(0, 10), sticky="w")
        self.e_url = ttk.Entry(url_frame, textvariable=self.pn_url, width=70, font=("Segoe UI", 9))
        self.e_url.grid(row=0, column=1, padx=(0, 20), sticky="ew")
        url_frame.columnconfigure(1, weight=1)
    
    def _build_workflow_config_section(self, parent):
        """Build Workflow Configuration section with multi-select checkboxes"""
        config_frame = tk.LabelFrame(parent, text="Workflow Selection (Select One or More)", font=("Segoe UI", 12, "bold"))
        config_frame.pack(fill="x", pady=(0, 20))
        
        # Instructions
        info_label = tk.Label(config_frame, 
                            text="✓ Check the workflow(s) you want to find and process. You can select multiple!",
                            font=("Segoe UI", 10, "bold"), fg=MAROON)
        info_label.pack(padx=10, pady=(10, 5), anchor="w")
        
        # Checkbox grid (2 columns for better layout)
        checkbox_frame = tk.Frame(config_frame)
        checkbox_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        workflow_list = [
            "Add/Review Documents",
            "Remove Counselor from Client in TN",
            "Send Welcome Letter and NPP",
            "Discharge Request"
        ]
        
        # Create checkboxes in 2 columns
        for idx, workflow_name in enumerate(workflow_list):
            row = idx // 2
            col = idx % 2
            
            cb = tk.Checkbutton(checkbox_frame, 
                              text=workflow_name,
                              variable=self.workflow_selections[workflow_name],
                              font=("Segoe UI", 10),
                              anchor="w")
            cb.grid(row=row, column=col, sticky="w", padx=(0, 30), pady=4)
        
        # Configure column weights for even distribution
        checkbox_frame.columnconfigure(0, weight=1)
        checkbox_frame.columnconfigure(1, weight=1)
        
        # Separator
        ttk.Separator(config_frame, orient="horizontal").pack(fill="x", padx=10, pady=10)
        
        # Custom workflow option
        custom_frame = tk.Frame(config_frame)
        custom_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.custom_cb = tk.Checkbutton(custom_frame,
                                       text="Use Custom Workflow Title:",
                                       variable=self.use_custom_workflow,
                                       font=("Segoe UI", 10),
                                       command=self._toggle_custom_workflow)
        self.custom_cb.pack(side="left", padx=(0, 10))
        
        self.custom_entry = ttk.Entry(custom_frame, textvariable=self.custom_workflow, 
                                      width=50, font=("Segoe UI", 9), state="disabled")
        self.custom_entry.pack(side="left", fill="x", expand=True)
        
        # Selection summary
        summary_frame = tk.Frame(config_frame, bg="#e8f4f8", relief="solid", bd=1)
        summary_frame.pack(fill="x", padx=10, pady=(10, 10))
        
        tk.Label(summary_frame, text="ℹ️  Selected workflows will be combined when searching",
                font=("Segoe UI", 9), bg="#e8f4f8", fg="#0066cc").pack(padx=10, pady=8)
    
    def _toggle_custom_workflow(self):
        """Enable/disable custom workflow entry based on checkbox"""
        if self.use_custom_workflow.get():
            self.custom_entry.config(state="normal")
        else:
            self.custom_entry.config(state="disabled")
    
    def _get_selected_workflows(self):
        """Get list of selected workflow titles (lowercased for matching)"""
        selected = []
        
        # Get checked preset workflows
        for workflow_name, var in self.workflow_selections.items():
            if var.get():
                selected.append(workflow_name.lower())
        
        # Get custom workflow if enabled
        if self.use_custom_workflow.get():
            custom = self.custom_workflow.get().strip()
            if custom:
                selected.append(custom.lower())
        
        return selected
    
    def _build_controls_section(self, parent):
        """Build bot controls section - matching Remove Counselor bot layout"""
        controls_frame = tk.LabelFrame(parent, text="Bot Controls", font=("Segoe UI", 12, "bold"))
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
        ttk.Button(queue_frame, text="Expand Queue", style="Big.TButton",
                   command=self._expand_queue).pack(fill="x", padx=8, pady=4)
        
        # Advanced Search section
        search_frame = tk.LabelFrame(button_grid, text="Advanced Search", font=("Segoe UI", 10, "bold"))
        search_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        ttk.Button(search_frame, text="Fill Next Chunk", style="Big.TButton",
                   command=self._fill_next_chunk).pack(fill="x", padx=8, pady=4)
        ttk.Button(search_frame, text="Search and Pickup All", style="Big.TButton",
                   command=self._search_and_pickup_all).pack(fill="x", padx=8, pady=4)
        ttk.Button(search_frame, text="Search and Close All", style="Big.TButton",
                   command=self._search_and_close_all).pack(fill="x", padx=8, pady=4)
        
        # Data Management section
        data_frame = tk.LabelFrame(button_grid, text="Data Management", font=("Segoe UI", 10, "bold"))
        data_frame.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")
        ttk.Button(data_frame, text="Export CSV", style="Success.TButton",
                   command=self._export_csv).pack(fill="x", padx=8, pady=4)
        ttk.Button(data_frame, text="Clear Data", style="Big.TButton",
                   command=self._clear_data).pack(fill="x", padx=8, pady=4)
        
        # Configure grid weights
        for i in range(4):
            button_grid.columnconfigure(i, weight=1)
    
    def _build_status_section(self, parent):
        """Build status section"""
        status_frame = tk.LabelFrame(parent, text="Status", font=("Segoe UI", 12, "bold"))
        status_frame.pack(fill="x", pady=(0, 20))
        
        status_content = tk.Frame(status_frame)
        status_content.pack(fill="x", padx=10, pady=10)
        
        self.status_label = tk.Label(status_content, text="Ready", font=("Segoe UI", 10))
        self.status_label.pack(side="left", padx=(0, 20))
        
        self.data_count_label = tk.Label(status_content, text="Data: 0 records", font=("Segoe UI", 9))
        self.data_count_label.pack(side="left")
    
    def _build_log_section(self, parent):
        """Build log section"""
        log_frame = tk.LabelFrame(parent, text="Activity Log", font=("Segoe UI", 12, "bold"))
        log_frame.pack(fill="both", expand=True)
        
        log_content_frame = tk.Frame(log_frame)
        log_content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.log = tk.Text(log_content_frame, height=15, wrap="word",
                           font=("Consolas", 9), bg="white", fg="black")
        self.log.pack(side="left", fill="both", expand=True)
        
        log_sb = ttk.Scrollbar(log_content_frame, command=self.log.yview)
        log_sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=log_sb.set)
        
        if self.users:
            self.log_msg(f"Loaded {len(self.users)} saved user(s) - Select a user from the dropdown or add a new one")
        else:
            self.log_msg("No users saved - Click 'Add User' to create your first user profile")
        self.log_msg("Login to Penelope to begin")
    
    def _update_user_dropdown(self):
        """Update the user dropdown with current users"""
        if hasattr(self, 'user_dropdown'):
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
            self.pn_user.set(user_data.get('username', ''))
            self.pn_pass.set(user_data.get('password', ''))
            self.pn_url.set(user_data.get('url', LOGIN_URL))
            self.log_msg(f"Loaded credentials for user: {selected_user}")
    
    def _add_user(self):
        """Add a new user to saved users"""
        dialog = tk.Toplevel(self)
        dialog.title("Add New User - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("450x280")
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
        
        tk.Label(dialog, text="Penelope URL (optional):", font=("Segoe UI", 10), bg="#f0f0f0").pack(pady=(0, 5))
        url_entry = tk.Entry(dialog, font=("Segoe UI", 10), width=35)
        url_entry.insert(0, LOGIN_URL)
        url_entry.pack(pady=(0, 15))
        
        def save_user():
            name = name_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            url = url_entry.get().strip() or LOGIN_URL
            
            if not name or not username or not password:
                messagebox.showwarning("Invalid Input", "User Name, Username, and Password are required")
                return
            
            if name in self.users:
                if not messagebox.askyesno("User Exists", f"User '{name}' already exists. Overwrite?"):
                    return
            
            self.users[name] = {
                'username': username,
                'password': password,
                'url': url
            }
            self.save_users()
            self._update_user_dropdown()
            self.log_msg(f"Added user: {name}")
            dialog.destroy()
            messagebox.showinfo("Success", f"User '{name}' added successfully")
        
        button_frame = tk.Frame(dialog, bg="#f0f0f0")
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Save", command=save_user,
                  bg=MAROON, fg="white", font=("Segoe UI", 10),
                  padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                  bg="#666666", fg="white", font=("Segoe UI", 10),
                  padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        
        # Bind Enter key to save
        name_entry.bind("<Return>", lambda e: username_entry.focus())
        username_entry.bind("<Return>", lambda e: password_entry.focus())
        password_entry.bind("<Return>", lambda e: url_entry.focus())
        url_entry.bind("<Return>", lambda e: save_user())
    
    def _update_credentials(self):
        """Update credentials for selected user"""
        selected_user = self.user_dropdown.get()
        if not selected_user or selected_user not in self.users:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown")
            return
        
        username = self.pn_user.get().strip()
        password = self.pn_pass.get().strip()
        url = self.pn_url.get().strip() or LOGIN_URL
        
        if not username or not password:
            messagebox.showwarning("Invalid Input", "Username and password are required")
            return
        
        self.users[selected_user] = {
            'username': username,
            'password': password,
            'url': url
        }
        self.save_users()
        self.log_msg(f"Updated credentials for user: {selected_user}")
        messagebox.showinfo("Success", f"Credentials updated for '{selected_user}'")
    
    def log_msg(self, msg):
        """Add message to log"""
        timestamp = time.strftime("[%H:%M:%S]")
        self.log.insert(tk.END, f"{timestamp} {msg}\n")
        self.log.see(tk.END)
        self.update_idletasks()
    
    def _update_status(self, msg):
        """Update status label"""
        self.status_label.config(text=msg)
        self.data_count_label.config(text=f"Data: {self.workflow_data.count()} records")
    
    def _wait_visible(self, selector, timeout=10):
        """Wait for element to be visible and return it"""
        return WebDriverWait(self.driver, timeout).until(
            EC.visibility_of_element_located(selector)
        )
    
    def _count_rows(self, body_element):
        """Count visible rows in the task body"""
        try:
            rows = body_element.find_elements(By.CSS_SELECTOR, "tr")
            visible_rows = [r for r in rows if r.is_displayed()]
            return len(visible_rows)
        except Exception as e:
            self.log_msg(f"[DEBUG] Error counting rows: {e}")
            return 0
    
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
                try:
                    days = int(date_text_lower.split()[0])
                    past_date = today - timedelta(days=days)
                    return datetime.combine(past_date, datetime.min.time())
                except (ValueError, IndexError):
                    pass
            elif 'days from now' in date_text_lower or 'days later' in date_text_lower:
                try:
                    days = int(date_text_lower.split()[0])
                    future_date = today + timedelta(days=days)
                    return datetime.combine(future_date, datetime.min.time())
                except (ValueError, IndexError):
                    pass
            
            return None
        except Exception:
            return None
    
    def _expand_sync(self, which: str, verbose=False):
        """
        Core expansion logic (from Remove Counselor bot)
        Clicks 'Load More' until no more tasks can be loaded
        which: "current" or "queue"
        """
        if which == "current":
            container, body, btn, label = SEL["current_body"], SEL["current_body"], SEL["current_load_more"], "Current"
        else:
            container, body, btn, label = SEL["queue_body"], SEL["queue_body"], SEL["queue_load_more"], "Queue"
        
        try:
            self._wait_visible(container, 15)
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
                    ]
                    
                    for selector in load_more_selectors:
                        try:
                            lm = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable(selector))
                            if verbose:
                                self.log_msg(f"[EXPAND] {label}: Found Load More button")
                            break
                        except TimeoutException:
                            continue
                    
                    if not lm:
                        if verbose:
                            self.log_msg(f"[EXPAND] {label}: No Load More button found")
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
                            self.driver.execute_script("arguments[0].click();", lm)
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
    
    # ========== CORE PENELOPE FUNCTIONS (from Remove Counselor bot) ==========
    
    def _login_penelope(self):
        """Login to Penelope"""
        def run():
            try:
                user = self.pn_user.get().strip()
                pwd = self.pn_pass.get().strip()
                url = self.pn_url.get().strip() or LOGIN_URL
                
                if not user or not pwd:
                    self.log_msg("❌ Please enter username and password")
                    return
                
                self.log_msg("🔐 Logging into Penelope...")
                
                # Initialize driver
                if not self.driver:
                    opts = ChromeOptions()
                    opts.add_argument("--start-maximized")
                    opts.add_argument("--disable-extensions")
                    self.driver = webdriver.Chrome(
                        service=ChromeService(ChromeDriverManager().install()),
                        options=opts
                    )
                
                self.driver.get(url)
                wait = WebDriverWait(self.driver, 15)
                
                # Login
                wait.until(EC.presence_of_element_located(SEL["user"])).send_keys(user)
                wait.until(EC.presence_of_element_located(SEL["pass"])).send_keys(pwd)
                wait.until(EC.element_to_be_clickable(SEL["login_btn"])).click()
                
                time.sleep(2)
                self.logged_in = True
                self.log_msg("✅ Successfully logged into Penelope")
                self._update_status("Logged in")
                
            except Exception as e:
                self.log_msg(f"❌ Login failed: {e}")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _open_workflow(self):
        """Open workflow drawer"""
        def run():
            try:
                if not self.driver:
                    self.log_msg("❌ Please login first")
                    return
                
                self.log_msg("📂 Opening workflow drawer...")
                wait = WebDriverWait(self.driver, 10)
                handle = wait.until(EC.element_to_be_clickable(SEL["workflow_handle"]))
                handle.click()
                time.sleep(0.5)
                self.log_msg("✅ Workflow drawer opened")
                self._update_status("Workflow drawer open")
            except Exception as e:
                self.log_msg(f"❌ Failed to open workflow: {e}")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _expand_current_safe(self):
        """Expand Current Tasks and build date chunks for matching workflows"""
        def run():
            try:
                if not self.driver:
                    self.log_msg("❌ Please login first")
                    return
                
                # Get selected workflows
                selected_workflows = self._get_selected_workflows()
                
                if not selected_workflows:
                    self.log_msg("❌ No workflows selected. Please check at least one workflow in the configuration.")
                    return
                
                self.log_msg(f"[CURRENT] Starting safe expansion for {len(selected_workflows)} workflow(s):")
                for wf in selected_workflows:
                    self.log_msg(f"  ✓ {wf}")
                
                # Expand the current tasks
                self._expand_sync("current", verbose=True)
                
                # Get all rows and find matching workflows
                body = self._wait_visible(SEL["current_body"], 10)
                rows = [r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()]
                
                if not rows:
                    self.log_msg("[CURRENT] No rows visible in current tasks")
                    return
                
                self.log_msg(f"[CURRENT] Found {len(rows)} rows to check")
                
                # Find matching workflows and collect their dates
                matching_dates = []
                matches_by_workflow = {wf: 0 for wf in selected_workflows}
                
                for i, r in enumerate(rows):
                    # Check for stop request
                    if self.stop_requested:
                        self.log_msg(f"[STOP] Operation cancelled at row {i+1}")
                        return
                    
                    try:
                        # Look for the link directly in the first cell of each row
                        first_cell = r.find_element(By.CSS_SELECTOR, "td:first-child")
                        link = first_cell.find_element(By.CSS_SELECTOR, "a")
                        subj = link.text.strip().lower()
                        
                        # Check if this row matches ANY of the selected workflows
                        matched = False
                        for workflow_title in selected_workflows:
                            if subj == workflow_title:
                                matched = True
                                matches_by_workflow[workflow_title] += 1
                                
                                # Look for date in the third cell
                                date_cell = r.find_element(By.CSS_SELECTOR, "td:nth-child(3)")
                                d_txt = date_cell.text.strip()
                                try:
                                    # Handle relative dates like "Today", "Tomorrow", etc.
                                    d = self._parse_workflow_date(d_txt)
                                    if d:
                                        matching_dates.append(d)
                                        self.log_msg(f"[CURRENT] Row {i+1}: '{subj}' with date {d_txt}")
                                    else:
                                        self.log_msg(f"[WARN] Row {i+1}: Unparseable date '{d_txt}' — skipping")
                                except Exception as e:
                                    self.log_msg(f"[WARN] Row {i+1}: Error parsing date '{d_txt}': {e} — skipping")
                                break  # Found a match, no need to check other workflows
                        
                        if not matched:
                            self.log_msg(f"[SKIP] Row {i+1}: {subj}")
                            
                    except Exception as e:
                        self.log_msg(f"[WARN] Row {i+1}: Error reading row - {e}")
                
                # Log summary of matches
                self.log_msg(f"[CURRENT] Match summary:")
                for wf, count in matches_by_workflow.items():
                    self.log_msg(f"  • {wf}: {count} workflows")
                
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
                self.workflow_data.chunks = chunks
                self.workflow_data.next_chunk_index = 0
                
                self.log_msg(f"[CURRENT] Found {len(matching_dates)} matching workflows")
                for a, b in chunks:
                    self.log_msg(f"[CURRENT] Chunk: {a}–{b}")
                self.log_msg(f"[DONE] Built {len(chunks)} chunk(s) for advanced search")
                self._update_status("Current expanded - chunks ready")
                
            except Exception as e:
                self.log_msg(f"❌ Failed to expand current: {e}")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _open_advanced(self):
        """Open Advanced Search tab - refreshes page, reopens drawer, then clicks Advanced"""
        def run():
            try:
                if not self.driver:
                    self.log_msg("❌ Please login first")
                    return
                
                # Refresh the page and reopen drawer to make Advanced tab visible
                self.log_msg("[ADV] Refreshing page to restore Advanced tab visibility...")
                self.driver.refresh()
                time.sleep(3)  # Wait for page to fully reload
                
                # Reopen the workflow drawer
                self.log_msg("[ADV] Reopening workflow drawer...")
                wait = WebDriverWait(self.driver, 20)
                handle = wait.until(EC.element_to_be_clickable(SEL["workflow_handle"]))
                
                # Try regular click first, then JavaScript fallback
                try:
                    handle.click()
                    self.log_msg("[ADV] Workflow handle clicked")
                except Exception:
                    try:
                        self.driver.execute_script("arguments[0].click();", handle)
                        self.log_msg("[ADV] Workflow handle clicked (JavaScript)")
                    except Exception as e:
                        self.log_msg(f"[ERR] Failed to click workflow handle: {e}")
                        return
                
                time.sleep(0.5)  # Give it time to fully open
                self.log_msg("[ADV] Workflow drawer reopened")
                
                # Now click the Advanced tab
                self.log_msg("[ADV] Clicking Advanced tab...")
                adv_tab = wait.until(EC.element_to_be_clickable(SEL["tab_advanced"]))
                
                try:
                    adv_tab.click()
                    self.log_msg("[ADV] Advanced tab clicked")
                except Exception:
                    try:
                        self.driver.execute_script("arguments[0].click();", adv_tab)
                        self.log_msg("[ADV] Advanced tab clicked (JavaScript)")
                    except Exception as e:
                        self.log_msg(f"[ERR] Failed to click Advanced tab: {e}")
                        return
                
                # Wait for the Advanced search fields to appear
                self.log_msg("[ADV] Waiting for Advanced search fields...")
                wait.until(EC.visibility_of_element_located(SEL["adv_from"]))
                wait.until(EC.visibility_of_element_located(SEL["adv_to"]))
                self.log_msg("[ADV] ✅ Advanced search opened successfully")
                self._update_status("Advanced Search Open")
                
            except Exception as e:
                self.log_msg(f"❌ Failed to open advanced: {e}")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _expand_queue(self):
        """Expand queued tasks and build date chunks for matching workflows"""
        def run():
            try:
                if not self.driver:
                    self.log_msg("❌ Please login first")
                    return
                
                # Get selected workflows
                selected_workflows = self._get_selected_workflows()
                
                if not selected_workflows:
                    self.log_msg("❌ No workflows selected. Please check at least one workflow in the configuration.")
                    return
                
                self.log_msg(f"[QUEUE] Starting queue expansion for {len(selected_workflows)} workflow(s):")
                for wf in selected_workflows:
                    self.log_msg(f"  ✓ {wf}")
                
                # Expand the queued tasks list until exhaustion
                self.log_msg("[QUEUE] Expanding queued tasks list...")
                self._expand_sync("queue", verbose=True)
                
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
                matches_by_workflow = {wf: 0 for wf in selected_workflows}
                
                for i, r in enumerate(rows):
                    # Check for stop request
                    if self.stop_requested:
                        self.log_msg(f"[STOP] Operation cancelled at row {i+1}")
                        return
                    
                    try:
                        # Look for the link directly in the first cell of each row
                        first_cell = r.find_element(By.CSS_SELECTOR, "td:first-child")
                        link = first_cell.find_element(By.CSS_SELECTOR, "a")
                        subj = link.text.strip().lower()
                        
                        # Check if this row matches ANY of the selected workflows
                        matched = False
                        for workflow_title in selected_workflows:
                            if subj == workflow_title:
                                matched = True
                                matches_by_workflow[workflow_title] += 1
                                
                                # Look for date in the third cell
                                date_cell = r.find_element(By.CSS_SELECTOR, "td:nth-child(3)")
                                d_txt = date_cell.text.strip()
                                try:
                                    # Handle relative dates like "Today", "Tomorrow", etc.
                                    d = self._parse_workflow_date(d_txt)
                                    if d:
                                        matching_dates.append(d)
                                        self.log_msg(f"[QUEUE] Row {i+1}: '{subj}' with date {d_txt}")
                                    else:
                                        self.log_msg(f"[WARN] Row {i+1}: Unparseable date '{d_txt}' — skipping")
                                except Exception as e:
                                    self.log_msg(f"[WARN] Row {i+1}: Error parsing date '{d_txt}': {e} — skipping")
                                break  # Found a match, no need to check other workflows
                        
                        if not matched:
                            self.log_msg(f"[SKIP] Row {i+1}: {subj}")
                            
                    except Exception as e:
                        self.log_msg(f"[WARN] Row {i+1}: Error reading row - {e}")
                
                # Log summary of matches
                self.log_msg(f"[QUEUE] Match summary:")
                for wf, count in matches_by_workflow.items():
                    self.log_msg(f"  • {wf}: {count} workflows")
                
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
                self.workflow_data.chunks = chunks
                self.workflow_data.next_chunk_index = 0
                
                self.log_msg(f"[QUEUE] Found {len(matching_dates)} matching queued workflows")
                for a, b in chunks:
                    self.log_msg(f"[QUEUE] Chunk: {a}–{b}")
                self.log_msg(f"[DONE] Built {len(chunks)} chunk(s) for advanced search")
                self.log_msg(f"[DONE] ✅ Queue expansion complete! Now use 'Fill Next Chunk' and 'Search and Pickup All'")
                self._update_status("Queue expanded - chunks ready")
                
            except Exception as e:
                self.log_msg(f"❌ Failed to expand queue: {e}")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _fill_next_chunk(self):
        """Fill Next Chunk - fills date range from chunks built by Expand Current/Queue"""
        def run():
            try:
                if not self.driver:
                    self.log_msg("❌ Please login first")
                    return
                
                # Check if we have chunks from Expand Current/Queue
                if not self.workflow_data.chunks:
                    self.log_msg("❌ No chunks available. Run 'Expand Current' or 'Expand Queue' first to build chunks.")
                    return
                
                # Get next chunk
                idx = self.workflow_data.next_chunk_index
                if idx >= len(self.workflow_data.chunks):
                    self.log_msg("ℹ️  All chunks have been filled. Click 'Expand Current/Queue' to rebuild chunks or manually enter dates.")
                    return
                
                from_str, to_str = self.workflow_data.chunks[idx]
                self.workflow_data.next_chunk_index += 1
                
                remaining = len(self.workflow_data.chunks) - self.workflow_data.next_chunk_index
                self.log_msg(f"📅 Filling chunk {idx + 1}/{len(self.workflow_data.chunks)}: {from_str} to {to_str}")
                self.log_msg(f"ℹ️  {remaining} chunk(s) remaining after this one")
                
                wait = WebDriverWait(self.driver, 10)
                
                # Fill From date
                from_field = wait.until(EC.presence_of_element_located(SEL["adv_from"]))
                from_field.clear()
                from_field.send_keys(from_str)
                
                # Fill To date
                to_field = wait.until(EC.presence_of_element_located(SEL["adv_to"]))
                to_field.clear()
                to_field.send_keys(to_str)
                
                self.log_msg(f"✅ Date range filled: {from_str} to {to_str}")
                self._update_status(f"Chunk {idx + 1}/{len(self.workflow_data.chunks)}: {from_str} to {to_str}")
                
            except Exception as e:
                self.log_msg(f"❌ Failed to fill chunk: {e}")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _search_and_pickup_all(self):
        """
        Search and Pickup All - searches, then loops through results clicking Pickup on each
        """
        def run():
            try:
                if not self.driver:
                    self.log_msg("❌ Please login first")
                    return
                
                # Get selected workflows
                selected_workflows = self._get_selected_workflows()
                
                if not selected_workflows:
                    self.log_msg("❌ No workflows selected. Please check at least one workflow.")
                    return
                
                self.log_msg(f"[PICKUP] Starting Search and Pickup for {len(selected_workflows)} workflow type(s)")
                
                wait = WebDriverWait(self.driver, 10)
                
                # Read and log current date values
                try:
                    from_field = wait.until(EC.presence_of_element_located(SEL["adv_from"]))
                    to_field = wait.until(EC.presence_of_element_located(SEL["adv_to"]))
                    
                    from_val = from_field.get_attribute("value") or "Not set"
                    to_val = to_field.get_attribute("value") or "Not set"
                    
                    self.log_msg(f"🔍 Searching with date range: {from_val} to {to_val}")
                except Exception:
                    self.log_msg("🔍 Searching with current date range")
                
                # Click search button
                search_btn = wait.until(EC.element_to_be_clickable(SEL["adv_search"]))
                search_btn.click()
                time.sleep(3)  # Reduced from 10s to 3s - results load faster
                
                self.log_msg("✅ Search completed")
                
                # Now process all matching workflows
                self._process_workflows_with_action("pickup", selected_workflows)
                
            except Exception as e:
                self.log_msg(f"❌ Failed in search and pickup: {e}")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _search_and_close_all(self):
        """
        Search and Close All - searches, then loops through results clicking Close on each
        """
        def run():
            try:
                if not self.driver:
                    self.log_msg("❌ Please login first")
                    return
                
                # Get selected workflows
                selected_workflows = self._get_selected_workflows()
                
                if not selected_workflows:
                    self.log_msg("❌ No workflows selected. Please check at least one workflow.")
                    return
                
                self.log_msg(f"[CLOSE] Starting Search and Close for {len(selected_workflows)} workflow type(s)")
                
                wait = WebDriverWait(self.driver, 10)
                
                # Read and log current date values
                try:
                    from_field = wait.until(EC.presence_of_element_located(SEL["adv_from"]))
                    to_field = wait.until(EC.presence_of_element_located(SEL["adv_to"]))
                    
                    from_val = from_field.get_attribute("value") or "Not set"
                    to_val = to_field.get_attribute("value") or "Not set"
                    
                    self.log_msg(f"🔍 Searching with date range: {from_val} to {to_val}")
                except Exception:
                    self.log_msg("🔍 Searching with current date range")
                
                # Click search button
                search_btn = wait.until(EC.element_to_be_clickable(SEL["adv_search"]))
                search_btn.click()
                time.sleep(3)  # Reduced from 10s to 3s - results load faster
                
                self.log_msg("✅ Search completed")
                
                # Now process all matching workflows
                self._process_workflows_with_action("close", selected_workflows)
                
            except Exception as e:
                self.log_msg(f"❌ Failed in search and close: {e}")
        
        threading.Thread(target=run, daemon=True).start()
    
    def _export_csv(self):
        """Export collected data to CSV"""
        try:
            if self.workflow_data.count() == 0:
                messagebox.showinfo("No Data", "No data to export. Collect workflow data first.")
                return
            
            # Ask for save location
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
                initialfile=f"penelope_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            if not filename:
                return
            
            # Write CSV
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if self.workflow_data.tasks:
                    writer = csv.DictWriter(f, fieldnames=self.workflow_data.tasks[0].keys())
                    writer.writeheader()
                    writer.writerows(self.workflow_data.tasks)
            
            self.log_msg(f"✅ Data exported to: {filename}")
            messagebox.showinfo("Export Complete", f"Data exported successfully!\n{filename}")
            
        except Exception as e:
            self.log_msg(f"❌ Export failed: {e}")
            messagebox.showerror("Export Error", f"Failed to export data:\n{e}")
    
    def _clear_data(self):
        """Clear collected data"""
        if messagebox.askyesno("Clear Data", "Are you sure you want to clear all collected data?"):
            self.workflow_data.clear()
            self.current_chunk_start = None
            self.current_chunk_end = None
            self.log_msg("🗑️  All data cleared")
            self._update_status("Data cleared")
    
    def _stop_bot(self):
        """Stop all bot operations immediately (does NOT close browser)"""
        self.stop_requested = True
        self.log_msg("[STOP] 🛑 STOP REQUESTED - Halting all operations...")
        self._update_status("STOPPED - Click RESUME to continue")
        
        # Enable RESUME button
        if self.resume_btn:
            self.resume_btn.config(state="normal")
        
        # Note: stop_requested flag will be cleared when RESUME is clicked
        # We do NOT auto-reset it anymore so the operation stays paused
    
    def _resume_bot(self):
        """Resume paused operation from where it left off"""
        if not self.paused_operation:
            self.log_msg("[RESUME] No paused operation to resume")
            messagebox.showinfo("No Paused Operation", "There is no paused operation to resume.")
            return
        
        self.log_msg(f"[RESUME] ▶️ Resuming {self.paused_operation['action']} operation...")
        self.log_msg(f"[RESUME] Will continue from workflow index {self.paused_operation['index']}")
        self.stop_requested = False
        
        # Disable RESUME button
        if self.resume_btn:
            self.resume_btn.config(state="disabled")
        
        # Resume the operation
        action = self.paused_operation["action"]
        workflows = self.paused_operation["workflows"]
        start_index = self.paused_operation["index"]
        
        # Call the processing function with the saved state
        threading.Thread(
            target=lambda: self._process_workflows_with_action(action, workflows, start_index=start_index),
            daemon=True
        ).start()
    
    def _process_workflows_with_action(self, action, selected_workflows, start_index=0):
        """
        Core function to process workflows with either Pickup or Close action
        action: "pickup" or "close"
        start_index: Resume from this index (default 0 for new operations)
        """
        try:
            # Disable RESUME button while running
            if self.resume_btn:
                self.resume_btn.config(state="disabled")
            
            # If resuming, log resume info
            if start_index > 0:
                self.log_msg(f"[{action.upper()}] RESUMING from workflow index {start_index}...")
            else:
                self.log_msg(f"[{action.upper()}] Looking for matching workflows in search results...")
            
            # Find the search results table
            search_results_table = None
            try:
                search_results_table = self.driver.find_element(By.CSS_SELECTOR, ".advancedTasksBody table")
                self.log_msg(f"[{action.upper()}] Found search results table")
            except:
                try:
                    # Broader search for any table with workflow links
                    search_results_table = self.driver.find_element(By.XPATH, "//table[.//a[contains(@href, 'TaskThreadServlet')]]")
                    self.log_msg(f"[{action.upper()}] Found workflow table")
                except:
                    self.log_msg(f"[{action.upper()}] Could not find search results table")
                    return
            
            # Get all workflow links
            all_links = search_results_table.find_elements(By.TAG_NAME, "a")
            self.log_msg(f"[{action.upper()}] Searching {len(all_links)} links")
            
            # Find matching workflow links
            matching_links = []
            for link in all_links:
                try:
                    link_text = link.text.strip().lower()
                    # Check if this link matches any of our selected workflows
                    if link_text in selected_workflows:
                        matching_links.append(link)
                except:
                    continue
            
            if not matching_links:
                self.log_msg(f"[{action.upper()}] No matching workflows found")
                return
            
            self.log_msg(f"[{action.upper()}] Found {len(matching_links)} matching workflows to {action}")
            
            # Process each workflow using index (like Remove Counselor bot)
            processed_count = start_index  # Start from saved index if resuming
            total_success = 0
            workflow_index = start_index  # Start at saved index
            
            while True:
                # Check for stop request
                if self.stop_requested:
                    # Save current state for RESUME
                    self.paused_operation = {
                        "action": action,
                        "workflows": selected_workflows,
                        "index": workflow_index
                    }
                    self.log_msg(f"[STOP] Operation paused after processing {total_success} workflows")
                    self.log_msg(f"[STOP] Can resume from workflow index {workflow_index}")
                    self.log_msg(f"[STOP] Click RESUME button to continue")
                    return
                
                processed_count += 1
                self.log_msg(f"[{action.upper()}] Processing workflow {processed_count}/{len(matching_links)}")
                self._update_status(f"{action.capitalize()}ing workflow {processed_count}/{len(matching_links)}")
                
                # Re-find matching links (page state changes after each action)
                try:
                    search_results_table = self.driver.find_element(By.CSS_SELECTOR, ".advancedTasksBody table")
                except:
                    try:
                        search_results_table = self.driver.find_element(By.XPATH, "//table[.//a[contains(@href, 'TaskThreadServlet')]]")
                    except:
                        self.log_msg(f"[{action.upper()}] Could not find search results table - stopping")
                        break
                
                all_links = search_results_table.find_elements(By.TAG_NAME, "a")
                current_matching = []
                for link in all_links:
                    try:
                        link_text = link.text.strip().lower()
                        if link_text in selected_workflows:
                            current_matching.append(link)
                    except:
                        continue
                
                if not current_matching:
                    self.log_msg(f"[{action.upper()}] No more workflows found - completed {total_success} {action}s")
                    break
                
                # CRITICAL FIX: Use workflow_index instead of always clicking [0]
                # Check if index is valid
                if workflow_index >= len(current_matching):
                    self.log_msg(f"[{action.upper()}] No more workflows at index {workflow_index} - stopping")
                    break
                
                # Click the workflow at the CURRENT INDEX (not always [0]!)
                link_element = current_matching[workflow_index]
                self.log_msg(f"[{action.upper()}] Clicking workflow at index {workflow_index} of {len(current_matching)} available")
                try:
                    # Click link - use JavaScript for speed
                    self.driver.execute_script("arguments[0].click();", link_element)
                    time.sleep(1.5)  # Reduced from 3s to 1.5s - page loads faster
                    
                    # Click Pickup or Close button
                    if action == "pickup":
                        success = self._click_pickup_button()
                    else:  # close
                        success = self._click_close_button()
                    
                    if success:
                        total_success += 1
                        workflow_index += 1  # CRITICAL: Increment index after successful action
                        self.log_msg(f"[{action.upper()}] ✓ {action.capitalize()}ed workflow {total_success}")
                    else:
                        self.log_msg(f"[WARN] Failed to {action}")
                        workflow_index += 1  # Still increment even if failed to avoid infinite loop
                    
                    # Navigate back to search results
                    self._navigate_back_to_search()
                    time.sleep(0.5)  # Reduced from 2s to 0.5s
                    
                except Exception as e:
                    self.log_msg(f"[WARN] Failed to process workflow: {e}")
                    workflow_index += 1  # Increment even on error to avoid infinite loop
                    # Try to navigate back
                    try:
                        self._navigate_back_to_search()
                    except:
                        pass
                    time.sleep(0.5)  # Reduced from 2s
            
            self.log_msg(f"[DONE] ✅ Completed {total_success} {action}s out of {len(matching_links)} workflows")
            self._update_status(f"{action.capitalize()} complete")
            
            # Clear paused operation since we completed successfully
            self.paused_operation = None
            
        except Exception as e:
            self.log_msg(f"[ERR] Process workflows failed: {e}")
    
    def _click_pickup_button(self):
        """Click the Pickup button in the task page - OPTIMIZED FOR SPEED"""
        try:
            # Look for Pickup button in iframes - faster with reduced timeout
            frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe,frame")
            for i, frame in enumerate(frames):
                try:
                    self.driver.switch_to.frame(frame)
                    pickup_links = WebDriverWait(self.driver, 1).until(  # Reduced from 2s to 1s
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='pickupTask']"))
                    )
                    if pickup_links:
                        self.driver.execute_script("arguments[0].click();", pickup_links[0])
                        self.driver.switch_to.default_content()
                        time.sleep(0.5)  # Reduced from 2s to 0.5s
                        return True
                except:
                    self.driver.switch_to.default_content()
                    continue
            
            return False
        except Exception:
            return False
    
    def _click_close_button(self):
        """Click the Close button in the task page - OPTIMIZED FOR SPEED"""
        try:
            # Look for Close button in iframes - faster search
            frames = self.driver.find_elements(By.CSS_SELECTOR, "iframe,frame")
            for i, frame in enumerate(frames):
                try:
                    self.driver.switch_to.frame(frame)
                    close_links = WebDriverWait(self.driver, 0.5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href*='closeTask']"))
                    )
                    if close_links:
                        self.driver.execute_script("arguments[0].click();", close_links[0])
                        self.driver.switch_to.default_content()
                        # No wait needed for Close
                        return True
                except:
                    self.driver.switch_to.default_content()
                    continue
            
            return False
        except Exception:
            return False
    
    def _navigate_back_to_search(self):
        """Navigate back to the advanced search results - OPTIMIZED FOR SPEED"""
        try:
            self.driver.switch_to.default_content()
            
            # Reopen workflow drawer - fast click
            drawer_handle = self.driver.find_element(By.ID, "taskHandle")
            self.driver.execute_script("arguments[0].click();", drawer_handle)
            time.sleep(0.4)  # Reduced from 1s to 0.4s
            
            # Click Advanced tab - fast click
            adv_tab = self.driver.find_element(By.ID, "taskAdvancedView")
            self.driver.execute_script("arguments[0].click();", adv_tab)
            time.sleep(0.3)  # Reduced from 1s to 0.3s
            
            return True
        except Exception:
            return False
    
    def on_close(self):
        """Clean up on close"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.destroy()

# ========== Main Entry Point ==========
if __name__ == "__main__":
    try:
        app = PenelopeWorkflowApp()
        app.mainloop()
    except Exception as e:
        print(f"[FATAL] Application failed to start: {e}")
        import traceback
        traceback.print_exc()
