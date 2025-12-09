#!/usr/bin/env python3
"""
Secure CCMD Bot Launcher - Password Protected
This launcher requires a password to access the bot code and functionality.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import os
import sys
import hashlib
import base64
from pathlib import Path
from datetime import datetime
import threading
import time

# Import AI Task Assistant GUI
try:
    from ai_task_assistant_gui import open_ai_task_assistant
    AI_TASK_ASSISTANT_AVAILABLE = True
except ImportError:
    AI_TASK_ASSISTANT_AVAILABLE = False

# Import Secure Data Collector (HIPAA-compliant)
try:
    from secure_data_collector import SecureDataCollector
    from local_ai_trainer import LocalAITrainer
    DATA_COLLECTION_AVAILABLE = True
except ImportError:
    DATA_COLLECTION_AVAILABLE = False
    SecureDataCollector = None
    LocalAITrainer = None

# Import Admin Review Interface
try:
    from admin_review_interface import open_admin_review
    ADMIN_REVIEW_AVAILABLE = True
except ImportError:
    ADMIN_REVIEW_AVAILABLE = False
    open_admin_review = None

# Import Admin Dashboard GUI
try:
    from admin_dashboard_gui import open_admin_dashboard
    ADMIN_DASHBOARD_AVAILABLE = True
except ImportError:
    ADMIN_DASHBOARD_AVAILABLE = False
    open_admin_dashboard = None

# Import AI Optimization Analyzer
try:
    from ai_optimization_analyzer import AIOptimizationAnalyzer
    OPTIMIZATION_AVAILABLE = True
except ImportError:
    OPTIMIZATION_AVAILABLE = False
    AIOptimizationAnalyzer = None

# Import Auto Dependency Installer
try:
    from auto_install_dependencies import AutoDependencyInstaller
    AUTO_INSTALL_AVAILABLE = True
except ImportError:
    AUTO_INSTALL_AVAILABLE = False
    AutoDependencyInstaller = None

# Import Browser Activity Monitor
try:
    from auto_webdriver_wrapper import install_auto_wrapper
    from browser_activity_monitor import get_browser_monitor
    BROWSER_MONITOR_AVAILABLE = True
except ImportError:
    BROWSER_MONITOR_AVAILABLE = False
    install_auto_wrapper = None
    get_browser_monitor = None

# Also import selenium_auto_wrapper as fallback
try:
    from selenium_auto_wrapper import install_auto_wrapper as install_selenium_wrapper
    SELENIUM_WRAPPER_AVAILABLE = True
except ImportError:
    SELENIUM_WRAPPER_AVAILABLE = False
    install_selenium_wrapper = None

# Import Auto Diagnostic Monitor
try:
    from auto_diagnostic_monitor import start_auto_diagnostics
    AUTO_DIAGNOSTIC_AVAILABLE = True
except ImportError:
    AUTO_DIAGNOSTIC_AVAILABLE = False
    start_auto_diagnostics = None

class SecureBotLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CCMD Bot Launcher")
        self.geometry("900x750")  # Larger window to show all options
        self.configure(bg="#f0f0f0")
        self.minsize(800, 700)  # Minimum size to ensure usability
        
        # Security settings for code access only
        self.correct_password = "Integritycode2001@"
        self.max_attempts = 3
        self.attempts = 0
        self.locked = False
        self.session_timeout = 30 * 60  # 30 minutes
        self.last_activity = time.time()
        self.code_access_granted = False
        
        # Bot configurations - absolute paths to work from any location
        # Get the base installation directory (parent of _system folder)
        installation_dir = Path(__file__).parent.parent
        self.installation_dir = installation_dir
        
        # Initialize secure data collection (HIPAA-compliant)
        self.data_collector = None
        self.ai_trainer = None
        if DATA_COLLECTION_AVAILABLE:
            try:
                # Start passive data collection (with user consent)
                self.data_collector = SecureDataCollector(installation_dir, user_consent=True)
                self.data_collector.start_collection()
                
                # Initialize local AI trainer
                self.ai_trainer = LocalAITrainer(installation_dir, model_type="ollama")
                self.ai_trainer.start_automated_training()
                
                # Initialize autonomous AI engine
                try:
                    from autonomous_ai_engine import AutonomousAIEngine
                    self.autonomous_engine = AutonomousAIEngine(installation_dir)
                    self.log("🧠 Autonomous AI engine started")
                except ImportError:
                    self.autonomous_engine = None
                
                # Initialize C-Suite modules
                try:
                    from csuite_ai_modules import CSuiteAIModules
                    self.csuite_modules = CSuiteAIModules(installation_dir)
                    self.csuite_modules.start_automated_reporting(interval_hours=24)
                    self.log("📊 C-Suite AI modules started (automated reporting)")
                except ImportError:
                    self.csuite_modules = None
                
                self.log("🔒 Secure data collection started (HIPAA-compliant)")
                self.log("🤖 Continuous learning active - AI improving automatically")
                
                # Initialize AI optimization analyzer
                if OPTIMIZATION_AVAILABLE:
                    try:
                        self.optimization_analyzer = AIOptimizationAnalyzer(installation_dir)
                        self.optimization_analyzer.start_continuous_analysis()
                        self.log("📊 AI optimization analyzer started (runs daily)")
                    except Exception as e:
                        self.log(f"⚠️ Optimization analyzer warning: {e}")
                
                # Auto-install dependencies on first run
                if AUTO_INSTALL_AVAILABLE:
                    try:
                        installer = AutoDependencyInstaller(installation_dir)
                        # Check if dependencies need to be installed
                        # This runs automatically on first launch
                        self.log("📦 Dependency installer ready")
                    except Exception as e:
                        self.log(f"⚠️ Dependency installer warning: {e}")
                
                # Initialize data centralization
                try:
                    from data_centralization import DataCentralization
                    self.data_centralizer = DataCentralization(installation_dir)
                    self.data_centralizer.start_automated_aggregation(interval_hours=24)
                    self.log("📊 Data centralization started (aggregates daily)")
                except ImportError:
                    self.data_centralizer = None
                except Exception as e:
                    self.log(f"⚠️ Data centralization warning: {e}")
                
                # Initialize browser activity monitoring (Phase 1)
                if BROWSER_MONITOR_AVAILABLE or SELENIUM_WRAPPER_AVAILABLE:
                    try:
                        # Install automatic WebDriver wrapper (zero bot modifications)
                        wrapper_installed = False
                        
                        if install_auto_wrapper:
                            success = install_auto_wrapper(installation_dir)
                            if success:
                                wrapper_installed = True
                                self.log("🌐 Browser activity monitoring initialized (automatic wrapper)")
                        
                        # Fallback to selenium_auto_wrapper
                        if not wrapper_installed and install_selenium_wrapper:
                            success = install_selenium_wrapper(installation_dir)
                            if success:
                                wrapper_installed = True
                                self.log("🌐 Browser activity monitoring initialized (selenium wrapper)")
                        
                        if not wrapper_installed:
                            self.log("⚠️ Browser monitoring wrapper installation failed")
                        
                        # Initialize browser monitor
                        if get_browser_monitor:
                            browser_monitor = get_browser_monitor(installation_dir)
                            if browser_monitor:
                                browser_monitor.start_collection()
                                self.log("🌐 Browser activity monitoring active (passive, HIPAA-compliant)")
                                
                                # Start automatic diagnostic monitoring
                                if AUTO_DIAGNOSTIC_AVAILABLE and start_auto_diagnostics:
                                    try:
                                        start_auto_diagnostics(installation_dir, check_interval=30)
                                        self.log("🔍 Automatic diagnostic monitoring started (runs every 30 seconds)")
                                    except Exception as e:
                                        self.log(f"⚠️ Diagnostic monitor warning: {e}")
                    except Exception as e:
                        self.log(f"⚠️ Browser monitoring initialization warning: {e}")
            except Exception as e:
                self.log(f"⚠️ Data collection initialization warning: {e}")
        
        self.bots = {
            "Medical Records Department": {
                "path": str(installation_dir / "_bots" / "Med Rec" / "medical_records_department_launcher.py"),
                "description": "Access medical records automation tools"
            },
            "Consent Form Bot": {
                "path": str(installation_dir / "_bots" / "The Welcomed One, Exalted Rank" / "integrity_consent_bot_v2.py"),
                "description": "Consent forms with Penelope extraction (English/Spanish)"
            },
            "Welcome Letter Bot": {
                "path": str(installation_dir / "_bots" / "The Welcomed One, Exalted Rank" / "isws_welcome_DEEPFIX2_NOTEFORCE_v14.py"),
                "description": "Generate and send welcome letters"
            },
            "Intake & Referral Department": {
                "path": str(installation_dir / "_bots" / "Launcher" / "intake_referral_launcher.py"),
                "description": "Access all intake and referral related bots"
            },
            "Billing Department": {
                "path": str(installation_dir / "_bots" / "Billing Department" / "billing_department_launcher.py"),
                "description": "Access all billing department automation tools"
            },
            "Operational Analytics": {
                "path": str(installation_dir / "_bots" / "Operational Analytics" / "operational_analytics_launcher.py"),
                "description": "Access operational analytics and reporting tools"
            },
            "Penelope Workflow Tool": {
                "path": str(installation_dir / "_bots" / "Penelope Workflow Tool" / "penelope_workflow_tool.py"),
                "description": "Multi-purpose Penelope workflow automation tool"
            },
            "Miscellaneous": {
                "path": str(installation_dir / "_bots" / "Miscellaneous" / "miscellaneous_launcher.py"),
                "description": "Access miscellaneous utility bots and tools"
            }
        }
        
        self._build_main_ui()
        
        # Start session timeout monitor
        self._start_session_monitor()
    
    def _build_main_ui(self):
        """Build the main bot launcher interface"""
        # Main frame
        main_frame = tk.Frame(self, bg="#f0f0f0")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Header frame
        header_frame = tk.Frame(main_frame, bg="#800000", height=80)
        header_frame.pack(fill="x", pady=(0, 20))
        header_frame.pack_propagate(False)
        
        # Title
        title_label = tk.Label(header_frame, text="CCMD Automation Hub", 
                              font=("Arial", 24, "bold"), bg="#800000", fg="white")
        title_label.pack(expand=True)
        
        # Subtitle
        subtitle_label = tk.Label(header_frame, text="Select a bot to launch", 
                                 font=("Arial", 12), bg="#800000", fg="#cccccc")
        subtitle_label.pack()
        
        # AI Task Assistant button frame (feature cards)
        feature_cards = tk.Frame(main_frame, bg="#f0f0f0")
        feature_cards.pack(fill="x", pady=(0, 20))

        cards_row = tk.Frame(feature_cards, bg="#f0f0f0")
        cards_row.pack(fill="x", expand=True)

        self._create_feature_card(
            cards_row,
            title="🤖 AI Task Assistant",
            description="Tell me what you need and I'll route you to the right automation bot in seconds.",
            command=self._open_ai_task_assistant,
            column=0,
        )
        self._create_feature_card(
            cards_row,
            title="🧪 AI Workflow Trainer",
            description="Record a workflow, capture context notes, and instantly generate Cursor or GPT prototypes.",
            command=self._open_ai_workflow_trainer,
            column=1,
        )
 
        # Separator
        separator_ai = tk.Frame(main_frame, height=2, bg="#cccccc")
        separator_ai.pack(fill="x", pady=(15, 0))
        
        # Bot selection frame with two columns
        selection_frame = tk.Frame(main_frame, bg="#f0f0f0")
        selection_frame.pack(fill="both", expand=True)
        
        # Instructions
        instructions_label = tk.Label(selection_frame, 
                                     text="Choose a bot from the list below:", 
                                     font=("Arial", 12, "bold"), bg="#f0f0f0")
        instructions_label.pack(anchor="w", pady=(0, 8))
        
        # Two-column container
        columns_frame = tk.Frame(selection_frame, bg="#f0f0f0")
        columns_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Left column frame
        left_column = tk.Frame(columns_frame, bg="#f0f0f0")
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        # Right column frame
        right_column = tk.Frame(columns_frame, bg="#f0f0f0")
        right_column.pack(side="right", fill="both", expand=True, padx=(8, 0))
        
        # Store bot rows for hover effects
        self.bot_rows = {}
        
        # Distribute bots between left and right columns
        bot_list = list(self.bots.items())
        mid_point = (len(bot_list) + 1) // 2
        
        # Create sleek clickable rows for each bot
        for idx, (bot_name, bot_info) in enumerate(bot_list):
            if idx < mid_point:
                self._create_bot_row(left_column, bot_name, bot_info)
            else:
                self._create_bot_row(right_column, bot_name, bot_info)
        
        # Admin section
        admin_frame = tk.Frame(main_frame, bg="#f0f0f0")
        admin_frame.pack(fill="x", pady=(20, 0))
        
        # Separator
        separator = tk.Frame(admin_frame, height=2, bg="#cccccc")
        separator.pack(fill="x", pady=(0, 10))
        
        # Admin section label
        admin_label = tk.Label(admin_frame, text="🔒 Admin Section (Admin Only):", 
                             font=("Arial", 10, "bold"), bg="#f0f0f0", fg="#d32f2f")
        admin_label.pack(anchor="w")
        
        # Admin buttons frame
        admin_buttons_frame = tk.Frame(admin_frame, bg="#f0f0f0")
        admin_buttons_frame.pack(anchor="w", pady=(5, 5))
        
        # Admin review button
        admin_review_button = tk.Button(admin_buttons_frame, text="📊 Review AI Recommendations", 
                                        command=self._open_admin_review,
                                        bg="#d32f2f", fg="white", font=("Arial", 10, "bold"),
                                        padx=15, pady=5, cursor="hand2")
        admin_review_button.pack(side="left", padx=(0, 10))
        
        # Admin dashboard button
        admin_dashboard_button = tk.Button(admin_buttons_frame, text="📊 Admin Dashboard", 
                                          command=self._open_admin_dashboard,
                                          bg="#d32f2f", fg="white", font=("Arial", 10, "bold"),
                                          padx=15, pady=5, cursor="hand2")
        admin_dashboard_button.pack(side="left")
        
        # Code access section
        code_frame = tk.Frame(main_frame, bg="#f0f0f0")
        code_frame.pack(fill="x", pady=(20, 0))
        
        # Separator
        separator2 = tk.Frame(code_frame, height=2, bg="#cccccc")
        separator2.pack(fill="x", pady=(0, 10))
        
        # Code access label
        code_label = tk.Label(code_frame, text="🔒 Code Access (IT Only):", 
                             font=("Arial", 10, "bold"), bg="#f0f0f0", fg="#666666")
        code_label.pack(anchor="w")
        
        # Code access button
        code_button = tk.Button(code_frame, text="Access Bot Code", 
                               command=self._request_code_access,
                               bg="#666666", fg="white", font=("Arial", 10),
                               padx=15, pady=5, cursor="hand2")
        code_button.pack(anchor="w", pady=(5, 0))
        
        # Status log (increased height for better visibility)
        log_frame = tk.Frame(main_frame, bg="#f0f0f0")
        log_frame.pack(fill="both", expand=True, pady=(20, 0))
        
        log_label = tk.Label(log_frame, text="Status Log:", 
                            font=("Arial", 10, "bold"), bg="#f0f0f0")
        log_label.pack(anchor="w")
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, 
                                                 font=("Consolas", 9), bg="#f8f8f8")
        self.log_text.pack(fill="both", expand=True, pady=(5, 0))
        
        # Log initial message
        self.log("✅ CCMD Bot Launcher started successfully")
        self.log("🔒 Code access protected - employees cannot view/edit bot code")
        if AI_TASK_ASSISTANT_AVAILABLE:
            self.log("🤖 AI Task Assistant available - click the button at the top to use it")
        self.log("📋 Select a bot from the list above to get started")
 
    def _create_feature_card(self, parent, title, description, command, column):
        parent.grid_columnconfigure(column, weight=1, uniform="feature_buttons")
        pad_left = 0 if column == 0 else 12
        feature_btn = tk.Button(
            parent,
            text=title,
            command=command,
            bg="#800000",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=16,
            pady=8,
            cursor="hand2",
            relief="raised",
            bd=2,
        )
        feature_btn.grid(row=0, column=column, padx=(pad_left, 0), sticky="ew")
        feature_btn.configure(height=1)
    def _open_ai_workflow_trainer(self):
        """Open the AI Workflow Trainer GUI"""
        trainer_path = self.installation_dir / "AI" / "workflow_trainer_launcher.py"
        if not trainer_path.exists():
            messagebox.showerror(
                "Not Available",
                "AI Workflow Trainer script not found in the root AI directory.",
            )
            return

        try:
            subprocess.Popen([sys.executable, str(trainer_path)])
            self.log("🧪 AI Workflow Trainer launched.")
        except Exception as e:
            self.log(f"❌ Error opening AI Workflow Trainer: {e}")
            messagebox.showerror("Error", f"Failed to open AI Workflow Trainer:\n{str(e)}")

    def _request_code_access(self):
        """Request access to bot code"""
        if self.code_access_granted:
            self._show_code_access()
            return
        
        # Create password dialog
        dialog = tk.Toplevel(self)
        dialog.title("Code Access - IT Only")
        dialog.geometry("400x250")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.winfo_rootx() + 50, self.winfo_rooty() + 50))
        
        # Header
        header_frame = tk.Frame(dialog, bg="#d32f2f", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🔒 Code Access Required", 
                              font=("Arial", 16, "bold"), bg="#d32f2f", fg="white")
        title_label.pack(expand=True)
        
        # Main content
        content_frame = tk.Frame(dialog, bg="#f0f0f0")
        content_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Warning
        warning_label = tk.Label(content_frame, 
                                text="⚠️ WARNING: This grants access to view and edit bot code.\nOnly authorized IT personnel should proceed.",
                                font=("Arial", 10), bg="#f0f0f0", fg="#d32f2f", justify="center")
        warning_label.pack(pady=(0, 20))
        
        # Password entry
        password_label = tk.Label(content_frame, text="Enter IT Access Password:", 
                                 font=("Arial", 11), bg="#f0f0f0")
        password_label.pack(anchor="w")
        
        password_var = tk.StringVar()
        password_entry = tk.Entry(content_frame, textvariable=password_var, 
                                 font=("Arial", 11), show="*", width=30)
        password_entry.pack(pady=(5, 20))
        password_entry.focus()
        
        # Buttons
        button_frame = tk.Frame(content_frame, bg="#f0f0f0")
        button_frame.pack(fill="x")
        
        def verify_code_password():
            entered_password = password_var.get().strip()
            
            if not entered_password:
                messagebox.showwarning("Missing Password", "Please enter a password.")
                return
            
            if entered_password == self.correct_password:
                self.code_access_granted = True
                self.last_activity = time.time()
                dialog.destroy()
                self._show_code_access()
                self.log("🔓 Code access granted to authorized user")
            else:
                self.attempts += 1
                remaining = self.max_attempts - self.attempts
                
                if remaining > 0:
                    messagebox.showwarning("Incorrect Password", 
                                         f"Incorrect password. {remaining} attempts remaining.")
                    password_var.set("")
                    password_entry.focus()
                else:
                    messagebox.showerror("Access Denied", 
                                       "Too many failed attempts. Access locked.")
                    self.locked = True
                    dialog.destroy()
        
        def cancel_access():
            dialog.destroy()
        
        verify_button = tk.Button(button_frame, text="Grant Access", 
                                 command=verify_code_password,
                                 bg="#d32f2f", fg="white", font=("Arial", 10, "bold"),
                                 padx=15, pady=5)
        verify_button.pack(side="left")
        
        cancel_button = tk.Button(button_frame, text="Cancel", 
                                 command=cancel_access,
                                 bg="#666666", fg="white", font=("Arial", 10),
                                 padx=15, pady=5)
        cancel_button.pack(side="right")
        
        # Bind Enter key
        password_entry.bind("<Return>", lambda e: verify_code_password())
    
    def _show_code_access(self):
        """Show code access interface"""
        # Create code access window
        code_window = tk.Toplevel(self)
        code_window.title("Bot Code Access - IT Only")
        code_window.geometry("800x600")
        code_window.configure(bg="#f0f0f0")
        
        # Header
        header_frame = tk.Frame(code_window, bg="#d32f2f", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="🔓 Bot Code Access - Authorized IT Personnel", 
                              font=("Arial", 16, "bold"), bg="#d32f2f", fg="white")
        title_label.pack(expand=True)
        
        # Main content
        main_frame = tk.Frame(code_window, bg="#f0f0f0")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Warning
        warning_frame = tk.Frame(main_frame, bg="#fff3cd", relief="raised", bd=2)
        warning_frame.pack(fill="x", pady=(0, 20))
        
        warning_text = """⚠️ AUTHORIZED ACCESS ONLY
        
You now have access to view and edit bot code. This access is logged and monitored.
Only make changes if you are authorized to do so. All modifications are tracked."""
        
        warning_label = tk.Label(warning_frame, text=warning_text, 
                                font=("Arial", 10), bg="#fff3cd", fg="#856404", 
                                justify="left")
        warning_label.pack(padx=15, pady=15)
        
        # File browser
        file_frame = tk.Frame(main_frame, bg="#f0f0f0")
        file_frame.pack(fill="both", expand=True)
        
        tk.Label(file_frame, text="Bot Code Files:", font=("Arial", 12, "bold"), 
                bg="#f0f0f0").pack(anchor="w", pady=(0, 10))
        
        # File list
        file_listbox = tk.Listbox(file_frame, font=("Consolas", 10), height=15)
        file_listbox.pack(fill="both", expand=True, pady=(0, 10))
        
        # Populate file list
        bot_files = [
            "Launcher/bot_launcher.py",
            "Launcher/intake_referral_launcher.py", 
            "Referral bot and bridge (final)/counselor_assignment_bot.py",
            "Referral bot and bridge (final)/isws_Intake_referral_bot_REFERENCE_PLUS_PRINT_ONLY_WITH_LOOPBACK_LOOPONLY_SCROLLING_TINYLOG_NO_BOTTOM_UPLOADER.py",
            "The Welcomed One, Exalted Rank/integrity_consent_bot_v2.py",
            "The Welcomed One, Exalted Rank/isws_welcome_DEEPFIX2_NOTEFORCE_v14.py",
            "Med Rec/medical_records_department_launcher.py",
            "Med Rec/Finished Product, Launch Ready/Bot and extender/",
            "Cursor versions/Goose/isws_remove_counselor_botcursor3.py",
            "Penelope Workflow Tool/penelope_workflow_tool.py"
        ]
        
        for file_path in bot_files:
            file_listbox.insert(tk.END, file_path)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(fill="x", pady=(0, 10))
        
        def open_file():
            selection = file_listbox.curselection()
            if selection:
                file_path = bot_files[selection[0]]
                # Open file in default editor
                import os
                os.startfile(file_path)
                self.log(f"🔓 Opened code file: {file_path}")
        
        def open_folder():
            selection = file_listbox.curselection()
            if selection:
                file_path = bot_files[selection[0]]
                folder_path = os.path.dirname(file_path)
                import os
                os.startfile(folder_path)
                self.log(f"🔓 Opened code folder: {folder_path}")
        
        def close_access():
            self.code_access_granted = False
            code_window.destroy()
            self.log("🔒 Code access closed")
        
        open_file_button = tk.Button(button_frame, text="Open File", 
                                    command=open_file,
                                    bg="#d32f2f", fg="white", font=("Arial", 10, "bold"),
                                    padx=15, pady=5)
        open_file_button.pack(side="left", padx=(0, 10))
        
        open_folder_button = tk.Button(button_frame, text="Open Folder", 
                                      command=open_folder,
                                      bg="#666666", fg="white", font=("Arial", 10),
                                      padx=15, pady=5)
        open_folder_button.pack(side="left", padx=(0, 10))
        
        close_button = tk.Button(button_frame, text="Close Access", 
                                command=close_access,
                                bg="#666666", fg="white", font=("Arial", 10),
                                padx=15, pady=5)
        close_button.pack(side="right")
        
        # Log access
        self.log("🔓 Code access window opened for authorized user")
    
    
    def _create_bot_row(self, parent, bot_name, bot_info):
        """Create a sleek, compact clickable row for each bot with hover effects"""
        # Main row frame - very compact spacing
        row_frame = tk.Frame(parent, bg="#f0f0f0", relief="flat", bd=0)
        row_frame.pack(fill="x", pady=2, padx=2)
        
        # Inner frame for content (sleek, thin border)
        inner_frame = tk.Frame(row_frame, bg="#ffffff", relief="solid", bd=1, 
                              highlightbackground="#cccccc", highlightthickness=1)
        inner_frame.pack(fill="x", padx=0, pady=0)
        
        # Content frame with minimal padding for compact look
        content_frame = tk.Frame(inner_frame, bg="#ffffff")
        content_frame.pack(fill="x", padx=8, pady=5)
        
        # Bot name (smaller, sleeker font)
        name_label = tk.Label(content_frame, text=bot_name, 
                             font=("Arial", 10, "bold"),
                             bg="#ffffff", fg="#000000",
                             anchor="w", cursor="hand2")
        name_label.pack(fill="x", pady=(0, 1))
        
        # Bot description (very compact, single line if possible)
        desc_text = bot_info["description"]
        # Truncate long descriptions to keep boxes small
        if len(desc_text) > 50:
            desc_text = desc_text[:47] + "..."
        desc_label = tk.Label(content_frame, text=desc_text,
                             font=("Arial", 8),
                             bg="#ffffff", fg="#666666",
                             anchor="w", wraplength=280)
        desc_label.pack(fill="x", anchor="w")
        
        # Store references for hover effects
        self.bot_rows[bot_name] = {
            "row_frame": row_frame,
            "inner_frame": inner_frame,
            "content_frame": content_frame,
            "name_label": name_label,
            "desc_label": desc_label,
            "bot_info": bot_info
        }
        
        # Create handlers
        def make_enter_handler(name):
            def handler(event):
                self._on_row_enter(name)
            return handler
        
        def make_leave_handler(name):
            def handler(event):
                self._on_row_leave(name)
            return handler
        
        def make_click_handler(name):
            def handler(event):
                self._launch_bot_by_name(name)
            return handler
        
        # Bind events to all widgets in the row
        widgets_to_bind = [row_frame, inner_frame, content_frame, name_label, desc_label]
        enter_handler = make_enter_handler(bot_name)
        leave_handler = make_leave_handler(bot_name)
        click_handler = make_click_handler(bot_name)
        
        for widget in widgets_to_bind:
            widget.bind("<Button-1>", click_handler)
            widget.bind("<Enter>", enter_handler)
            widget.bind("<Leave>", leave_handler)
        
        # Recursively bind to children
        def bind_to_children(parent_widget):
            for child in parent_widget.winfo_children():
                try:
                    child.bind("<Enter>", enter_handler)
                    child.bind("<Leave>", leave_handler)
                    child.bind("<Button-1>", click_handler)
                    bind_to_children(child)
                except:
                    pass
        
        bind_to_children(row_frame)
    
    def _on_row_enter(self, bot_name):
        """Handle mouse entering a bot row - highlight it"""
        if bot_name in self.bot_rows:
            row_data = self.bot_rows[bot_name]
            # Sleek highlight colors
            highlight_bg = "#e8f4f8"  # Light blue-gray
            highlight_border = "#0066cc"  # Blue border
            
            row_data["inner_frame"].config(bg=highlight_bg, relief="solid", bd=2, 
                                          highlightbackground=highlight_border, highlightthickness=2)
            row_data["content_frame"].config(bg=highlight_bg)
            row_data["name_label"].config(bg=highlight_bg, fg="#003366", font=("Arial", 10, "bold"))
            row_data["desc_label"].config(bg=highlight_bg, fg="#004d99", font=("Arial", 8))
            
            # Update all child widgets
            self._update_row_children(row_data["row_frame"], highlight_bg, "#003366", "#004d99")
    
    def _on_row_leave(self, bot_name):
        """Handle mouse leaving a bot row - return to normal"""
        if bot_name in self.bot_rows:
            row_data = self.bot_rows[bot_name]
            # Return to normal
            row_data["inner_frame"].config(bg="#ffffff", relief="solid", bd=1,
                                          highlightbackground="#cccccc", highlightthickness=1)
            row_data["content_frame"].config(bg="#ffffff")
            row_data["name_label"].config(bg="#ffffff", fg="#000000", font=("Arial", 10, "bold"))
            row_data["desc_label"].config(bg="#ffffff", fg="#666666", font=("Arial", 8))
            
            # Update all child widgets
            self._update_row_children(row_data["row_frame"], "#ffffff", "#000000", "#666666")
    
    def _update_row_children(self, parent, bg_color, name_color, desc_color):
        """Update all child widgets in a row to match the hover state"""
        try:
            for child in parent.winfo_children():
                if isinstance(child, tk.Label):
                    if "bold" in str(child.cget("font")):
                        child.config(bg=bg_color, fg=name_color)
                    else:
                        child.config(bg=bg_color, fg=desc_color)
                elif isinstance(child, tk.Frame):
                    child.config(bg=bg_color)
                    self._update_row_children(child, bg_color, name_color, desc_color)
        except:
            pass
    
    def _launch_bot_by_name(self, bot_name):
        """Launch a bot by its name"""
        self._launch_bot(bot_name)
    
    def _launch_bot(self, bot_name=None):
        """Launch the selected bot with secure data collection"""
        if not bot_name:
            messagebox.showwarning("No Selection", "Please select a bot to launch.")
            return
        
        bot_config = self.bots.get(bot_name)
        
        if not bot_config:
            self.log(f"❌ Bot configuration not found: {bot_name}")
            return
        
        try:
            bot_path = bot_config["path"]
            full_path = Path(bot_path).absolute()
            
            if not full_path.exists():
                self.log(f"❌ Bot file not found: {full_path}")
                messagebox.showerror("File Not Found", f"Bot file not found:\n{full_path}")
                return
            
            self.log(f"🚀 Launching {bot_name}...")
            self.log(f"📁 Path: {full_path}")
            
            # Record bot execution (HIPAA-compliant)
            if self.data_collector:
                try:
                    self.data_collector.record_bot_execution(
                        bot_name=bot_name,
                        bot_path=full_path,
                        user_identifier=os.getenv("USERNAME", "Unknown"),
                        success=True
                    )
                except Exception as e:
                    self.log(f"⚠️ Data recording warning: {e}")
            
            # Ensure browser monitoring is active before launching bot (optional - don't break if it fails)
            try:
                from bot_launcher_bridge import install_monitoring_bridge
                install_monitoring_bridge()
                self.log("🌐 Browser monitoring bridge activated")
            except Exception as e:
                # Silent fail - don't break bot launches if monitoring fails
                pass
            
            # Launch the bot
            if bot_config.get("is_folder"):
                # Open folder
                os.startfile(str(full_path))
                self.log(f"📂 Opened folder: {bot_name}")
            else:
                # Launch Python script (hide console window for professional look)
                if os.name == 'nt':  # Windows
                    # Use pythonw.exe if available, otherwise hide console window
                    pythonw_exe = sys.executable.replace('python.exe', 'pythonw.exe')
                    if Path(pythonw_exe).exists():
                        python_executable = pythonw_exe
                        creation_flags = 0
                    else:
                        python_executable = sys.executable
                        # Hide console window (CREATE_NO_WINDOW = 0x08000000)
                        creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                else:
                    python_executable = sys.executable
                    creation_flags = 0
                
                # Launch bot with monitoring enabled
                # Set PYTHONPATH to include _system so monitoring modules are available
                env = os.environ.copy()
                system_dir = Path(__file__).parent
                pythonpath = env.get('PYTHONPATH', '')
                if pythonpath:
                    pythonpath = f"{system_dir};{pythonpath}"
                else:
                    pythonpath = str(system_dir)
                env['PYTHONPATH'] = pythonpath
                
                # Use -c to import monitoring BEFORE bot runs (ensures import hooks are active)
                # This preserves __name__ == "__main__" and __file__ for the bot
                system_dir_escaped = str(system_dir).replace("'", "\\'").replace("\\", "\\\\")
                full_path_escaped = str(full_path).replace("'", "\\'").replace("\\", "\\\\")
                
                import_cmd = f"""import sys; sys.path.insert(0, r'{system_dir_escaped}'); 
try:
    import fix_direct_launches
except:
    pass
exec(open(r'{full_path_escaped}', encoding='utf-8').read(), {{'__name__': '__main__', '__file__': r'{full_path_escaped}'}})"""
                
                try:
                    # Try with monitoring injection first
                    process = subprocess.Popen(
                        [python_executable, "-c", import_cmd],
                        cwd=str(full_path.parent),
                        env=env,
                        creationflags=creation_flags,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                except Exception as e:
                    # Fallback to direct launch if monitoring injection fails (ensures bots still work)
                    self.log(f"⚠️ Monitoring injection failed, launching directly: {e}")
                    process = subprocess.Popen(
                        [python_executable, str(full_path)],
                        cwd=str(full_path.parent),
                        env=env,
                        creationflags=creation_flags,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                self.log(f"✅ {bot_name} launched successfully (PID: {process.pid})")
            
            # Update last activity
            self.last_activity = time.time()
            
        except Exception as e:
            self.log(f"❌ Error launching {bot_name}: {e}")
            
            # Record failed execution
            if self.data_collector:
                try:
                    self.data_collector.record_bot_execution(
                        bot_name=bot_name,
                        bot_path=str(full_path) if 'full_path' in locals() else bot_path,
                        user_identifier=os.getenv("USERNAME", "Unknown"),
                        success=False,
                        error=str(e)
                    )
                except:
                    pass
            
            messagebox.showerror("Launch Error", f"Failed to launch {bot_name}:\n{e}")
    
    
    def _start_session_monitor(self):
        """Start monitoring session timeout"""
        def monitor():
            while True:
                time.sleep(60)  # Check every minute
                if hasattr(self, 'last_activity'):
                    if time.time() - self.last_activity > self.session_timeout:
                        self.after(0, self._session_timeout)
                        break
        
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
    
    def _session_timeout(self):
        """Handle session timeout"""
        self.log("⏰ Session timeout - code access expired")
        self.code_access_granted = False
        messagebox.showinfo("Session Timeout", "Code access session has expired. Please request access again if needed.")
    
    def _open_admin_review(self):
        """Open admin review interface"""
        try:
            if ADMIN_REVIEW_AVAILABLE:
                installation_dir = Path(__file__).parent.parent
                open_admin_review(self, installation_dir)
                self.log("🔒 Admin review interface opened")
            else:
                messagebox.showwarning("Not Available", 
                                     "Admin review interface is not available.\n\n"
                                     "Please ensure all dependencies are installed:\n"
                                     "- admin_review_interface.py\n"
                                     "- ai_optimization_analyzer.py\n"
                                     "- admin_secure_storage.py")
        except Exception as e:
            self.log(f"❌ Error opening admin review: {e}")
            messagebox.showerror("Error", f"Failed to open admin review:\n{str(e)}")
    
    def _open_admin_dashboard(self):
        """Open admin dashboard interface"""
        try:
            if ADMIN_DASHBOARD_AVAILABLE:
                installation_dir = Path(__file__).parent.parent
                open_admin_dashboard(self, installation_dir)
                self.log("📊 Admin dashboard opened")
            else:
                messagebox.showwarning("Not Available", 
                                     "Admin dashboard is not available.\n\n"
                                     "Please ensure all dependencies are installed:\n"
                                     "- admin_dashboard_gui.py\n"
                                     "- admin_dashboard.py\n"
                                     "- admin_secure_storage.py")
        except Exception as e:
            self.log(f"❌ Error opening admin dashboard: {e}")
            messagebox.showerror("Error", f"Failed to open admin dashboard:\n{str(e)}")
    
    def _open_ai_task_assistant(self):
        """Open the AI Task Assistant GUI"""
        try:
            if AI_TASK_ASSISTANT_AVAILABLE:
                installation_dir = Path(__file__).parent.parent
                
                # Record AI Task Assistant usage
                if self.data_collector:
                    try:
                        self.data_collector.record_user_activity(
                            activity_type="AI_TASK_ASSISTANT_OPENED",
                            activity_data={"timestamp": datetime.now().isoformat()},
                            user_identifier=os.getenv("USERNAME", "Unknown")
                        )
                    except Exception as e:
                        self.log(f"⚠️ Data recording warning: {e}")
                
                open_ai_task_assistant(self, installation_dir)
                self.log("🤖 AI Task Assistant opened")
            else:
                messagebox.showwarning("Not Available", 
                                     "AI Task Assistant is not available.\n\n"
                                     "Please ensure all dependencies are installed:\n"
                                     "- ai_task_assistant.py\n"
                                     "- ai_task_assistant_gui.py\n"
                                     "- ai_agent.py")
        except Exception as e:
            self.log(f"❌ Error opening AI Task Assistant: {e}")
            messagebox.showerror("Error", f"Failed to open AI Task Assistant:\n{str(e)}")
    
    def _open_ai_workflow_trainer(self):
        """Open the AI Workflow Trainer GUI"""
        trainer_path = self.installation_dir / "AI" / "workflow_trainer_launcher.py"
        if not trainer_path.exists():
            messagebox.showerror(
                "Not Available",
                "AI Workflow Trainer script not found in the root AI directory.",
            )
            return

        try:
            subprocess.Popen([sys.executable, str(trainer_path)])
            self.log("🧪 AI Workflow Trainer launched.")
        except Exception as e:
            self.log(f"❌ Error opening AI Workflow Trainer: {e}")
            messagebox.showerror("Error", f"Failed to open AI Workflow Trainer:\n{str(e)}")
    
    def log(self, message):
        """Add message to log"""
        if hasattr(self, 'log_text'):
            timestamp = time.strftime("%H:%M:%S")
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            self.update_idletasks()

def main():
    """Main function"""
    try:
        app = SecureBotLauncher()
        app.mainloop()
    except Exception as e:
        # More detailed error handling
        error_msg = f"Failed to start secure launcher:\n\nError: {e}\n\n"
        error_msg += f"Installation directory: {Path(__file__).parent.parent}\n"
        error_msg += f"Python executable: {sys.executable}\n"
        error_msg += f"Python version: {sys.version}\n\n"
        error_msg += "Please check that all required files are present and try again."
        
        # Show error in GUI only (no console window for professional look)
        try:
            messagebox.showerror("Launcher Error", error_msg)
        except:
            # If GUI not available, only then show console
            print(f"ERROR: {error_msg}")
            input("Press ENTER to close...")

if __name__ == "__main__":
    main()


