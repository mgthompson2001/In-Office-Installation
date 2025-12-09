#!/usr/bin/env python3
"""Standalone launcher for workflow training sessions."""

from __future__ import annotations

import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime, timedelta, UTC
import sqlite3
import threading
from typing import Optional, List

AI_ROOT = Path(__file__).resolve().parent
INSTALLATION_DIR = AI_ROOT.parent

if str(AI_ROOT / "intelligence") not in sys.path:
    sys.path.insert(0, str(AI_ROOT / "intelligence"))
if str(AI_ROOT / "monitoring") not in sys.path:
    sys.path.insert(0, str(AI_ROOT / "monitoring"))

from workflow_training_manager import WorkflowTrainingManager, TrainingSessionMetadata
from automation_prototype_generator import AutomationPrototypeGenerator

# Import LLMService to sync API key
try:
    from llm.llm_service import LLMService
    LLM_SERVICE_AVAILABLE = True
except ImportError:
    LLM_SERVICE_AVAILABLE = False
    LLMService = None

# Import full system monitoring
try:
    from monitoring.full_system_monitor import FullSystemMonitor, get_full_monitor
    FULL_MONITORING_AVAILABLE = True
except ImportError:
    FULL_MONITORING_AVAILABLE = False
    FullSystemMonitor = None
    get_full_monitor = None

# Import OpenAI and cryptography for API key management
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    openai = None

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    import base64
    import platform
    import getpass
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Fernet = None

PROTOTYPE_DIR = AI_ROOT / "automation_prototypes"
AUTOMATION_EXECUTOR = AI_ROOT / "intelligence" / "automation_executor_gui.py"
DASHBOARD_SCRIPT = AI_ROOT / "MASTER_AI_DASHBOARD.py"
TRAINING_BROWSER = AI_ROOT / "monitoring" / "training_browser.py"


class WorkflowTrainerApp(tk.Tk):
    """Enterprise-grade trainer UI with Cursor/GPT output controls."""

    def __init__(self) -> None:
        super().__init__()
        self.title("AI Workflow Trainer")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{int(screen_width * 0.98)}x{int(screen_height * 0.95)}")
        self.minsize(int(screen_width * 0.92), int(screen_height * 0.9))
        self.configure(bg="#f4f4f4")

        self.manager = WorkflowTrainingManager(INSTALLATION_DIR)
        self.generator: AutomationPrototypeGenerator = self.manager.generator
        self.session: Optional[TrainingSessionMetadata] = None
        
        # Initialize LLMService for API key syncing
        if LLM_SERVICE_AVAILABLE:
            self.llm_service = LLMService(INSTALLATION_DIR)
        else:
            self.llm_service = None

        self.cursor_var = tk.BooleanVar(value=True)
        self.gpt_var = tk.BooleanVar(value=True)
        
        # Full system monitoring state
        self.full_monitor: Optional[FullSystemMonitor] = None
        self.monitoring_active = False
        
        # GPT API key management
        self.api_key_file = AI_ROOT / "gpt_api_key.encrypted"
        self.gpt_api_key: Optional[str] = None
        self._load_gpt_api_key()
        
        # Output folder configuration
        self.output_folder_var = tk.StringVar(value=str(INSTALLATION_DIR / "AI" / "automation_prototypes"))

        self.session_status_var = tk.StringVar(value="No active training session.")
        self.output_mode_var = tk.StringVar(value="Output: Cursor prompt + GPT insight")
        self.prototype_summary_var = tk.StringVar(value="No prototypes generated yet.")

        self.recent_items: List[Path] = []

        self._configure_styles()
        self._build_ui()
        self._refresh_recent_prototypes()
        self.log("Ready. Enter a workflow title, choose output options, and click 'Start Training'.")

    # ------------------------------------------------------------------
    # UI construction helpers
    # ------------------------------------------------------------------
    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Card.TFrame", background="white", borderwidth=0)
        style.configure("SectionLabel.TLabel", background="white", foreground="#333333", font=("Segoe UI", 10, "bold"))
        style.configure("Muted.TLabel", background="white", foreground="#5b5b5b", font=("Segoe UI", 8))
        style.configure("Toggle.TCheckbutton", background="white", foreground="#333333", font=("Segoe UI", 8))
        style.configure("Primary.TButton", foreground="white", background="#800000", font=("Segoe UI", 8, "bold"), padding=3)
        style.map(
            "Primary.TButton",
            background=[("active", "#a00000"), ("disabled", "#9c9c9c")],
            foreground=[("disabled", "#f0f0f0"), ("!disabled", "white")],
        )

        style.configure("Secondary.TButton", foreground="white", background="#34495e", font=("Segoe UI", 8, "bold"), padding=3)
        style.map(
            "Secondary.TButton",
            background=[("active", "#2c3e50"), ("disabled", "#9c9c9c")],
            foreground=[("disabled", "#e0e0e0"), ("!disabled", "white")],
        )

        style.configure("StatusBar.TFrame", background="#eceef5")
        style.configure("StatusBar.TLabel", background="#eceef5", foreground="#3e425d", font=("Segoe UI", 8))

        style.configure("Log.TFrame", background="white", borderwidth=0)

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg="#800000")
        header.pack(fill=tk.X, side=tk.TOP, padx=0, pady=0)

        tk.Label(
            header,
            text="AI Workflow Trainer",
            font=("Segoe UI", 18, "bold"),
            bg="#800000",
            fg="white",
        ).pack(anchor="w", padx=18, pady=(14, 2))
        tk.Label(
            header,
            text="Capture a single workflow, choose prototype outputs, and feed it directly into the Automation Executor pipeline.",
            font=("Segoe UI", 9),
            bg="#800000",
            fg="#f4f4f4",
            wraplength=780,
            justify=tk.LEFT,
        ).pack(anchor="w", padx=18, pady=(0, 12))

        # Scrollable main content
        scroll_container = tk.Frame(self, bg="#f4f4f4")
        scroll_container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(scroll_container, bg="#f4f4f4", highlightthickness=0)
        v_scroll = ttk.Scrollbar(scroll_container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        main = tk.Frame(canvas, bg="#f4f4f4")
        frame_window = canvas.create_window((0, 0), window=main, anchor="nw")

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfig(frame_window, width=event.width)

        main.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # Controls card -------------------------------------------------
        controls = ttk.Frame(main, style="Card.TFrame", padding=18)
        controls.grid(row=0, column=0, sticky="nsew", padx=(24, 12), pady=(24, 12))

        ttk.Label(controls, text="Workflow Details", style="SectionLabel.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            controls,
            text="Provide a descriptive title so the automation prototype, Cursor prompt, and GPT summary all speak the same language.",
            style="Muted.TLabel",
            wraplength=320,
        ).grid(row=1, column=0, sticky="w", pady=(2, 10))

        self.title_var = tk.StringVar()
        title_entry = ttk.Entry(controls, textvariable=self.title_var, width=38, font=("Segoe UI", 10))
        title_entry.grid(row=2, column=0, sticky="ew")
        title_entry.focus_set()

        toggle_frame = tk.Frame(controls, bg="white")
        toggle_frame.grid(row=3, column=0, sticky="ew", pady=(12, 4))
        tk.Label(
            toggle_frame,
            text="Prototype Outputs",
            font=("Segoe UI", 10, "bold"),
            bg="white",
            fg="#333333",
        ).grid(row=0, column=0, sticky="w")
        ttk.Checkbutton(
            toggle_frame,
            text="Cursor prompt (manual build)",
            variable=self.cursor_var,
            command=self._update_output_mode_label,
            style="Toggle.TCheckbutton",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Checkbutton(
            toggle_frame,
            text="GPT insight (uses OpenAI API)",
            variable=self.gpt_var,
            command=self._update_output_mode_label,
            style="Toggle.TCheckbutton",
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))
        ttk.Label(
            toggle_frame,
            text="Disable GPT when you want a zero-cost prototype bundle.",
            style="Muted.TLabel",
        ).grid(row=3, column=0, sticky="w", pady=(6, 0))
        
        # Output Folder Configuration Section
        output_folder_frame = tk.Frame(controls, bg="white")
        output_folder_frame.grid(row=4, column=0, sticky="ew", pady=(12, 4))
        
        ttk.Label(
            output_folder_frame,
            text="Output Folder",
            style="SectionLabel.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        
        ttk.Label(
            output_folder_frame,
            text="Choose where training session data will be saved. Default: AI/automation_prototypes",
            style="Muted.TLabel",
            wraplength=320,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 6))
        
        output_folder_entry = ttk.Entry(
            output_folder_frame,
            textvariable=self.output_folder_var,
            width=35,
            font=("Segoe UI", 9),
        )
        output_folder_entry.grid(row=2, column=0, sticky="ew", padx=(0, 5))
        output_folder_frame.grid_columnconfigure(0, weight=1)
        
        def browse_output_folder():
            from tkinter import filedialog
            folder = filedialog.askdirectory(
                title="Select Output Folder for Training Data",
                initialdir=self.output_folder_var.get()
            )
            if folder:
                self.output_folder_var.set(folder)
        
        ttk.Button(
            output_folder_frame,
            text="Browse...",
            command=browse_output_folder,
            style="Secondary.TButton",
        ).grid(row=2, column=1, padx=(5, 0))
        
        # GPT API Key Configuration Section
        api_key_frame = tk.Frame(controls, bg="white")
        api_key_frame.grid(row=4, column=0, sticky="ew", pady=(12, 4))
        
        ttk.Label(
            api_key_frame,
            text="GPT API Key Configuration",
            style="SectionLabel.TLabel",
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        
        ttk.Label(
            api_key_frame,
            text="Enter your OpenAI API key for GPT insights. The key is encrypted and stored securely.",
            style="Muted.TLabel",
            wraplength=320,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 6))
        
        self.api_key_entry = ttk.Entry(
            api_key_frame,
            width=35,
            font=("Segoe UI", 9),
            show="*"
        )
        self.api_key_entry.grid(row=2, column=0, sticky="ew", padx=(0, 5))
        api_key_frame.grid_columnconfigure(0, weight=1)
        
        # Show/Hide toggle
        self.api_key_visible = False
        def toggle_api_key_visibility():
            self.api_key_visible = not self.api_key_visible
            if self.api_key_visible:
                self.api_key_entry.config(show="")
                toggle_btn.config(text="Hide")
            else:
                self.api_key_entry.config(show="*")
                toggle_btn.config(text="Show")
        
        toggle_btn = ttk.Button(
            api_key_frame,
            text="Show",
            command=toggle_api_key_visibility,
            style="Secondary.TButton",
        )
        toggle_btn.grid(row=2, column=1, padx=2)
        
        # Save API Key button
        save_key_btn = ttk.Button(
            api_key_frame,
            text="Save Key",
            command=self._save_api_key,
            style="Secondary.TButton",
        )
        save_key_btn.grid(row=2, column=2, padx=(5, 0))
        
        # Test Connection button
        test_btn = ttk.Button(
            api_key_frame,
            text="Test Connection",
            command=self._test_openai_connection,
            style="Secondary.TButton",
        )
        test_btn.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        
        # API Key status label
        self.api_key_status_label = ttk.Label(
            api_key_frame,
            text="Status: No API key saved",
            style="Muted.TLabel",
        )
        self.api_key_status_label.grid(row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self._update_api_key_status()

        notes_label = ttk.Label(controls, text="Cursor Notes (optional)", style="SectionLabel.TLabel")
        notes_label.grid(row=5, column=0, sticky="w", pady=(12, 4))
        self.notes_text = scrolledtext.ScrolledText(
            controls,
            height=5,
            font=("Segoe UI", 9),
            wrap=tk.WORD,
            background="#fafafa",
            relief="flat",
            bd=1,
        )
        self.notes_text.grid(row=6, column=0, sticky="nsew")
        controls.grid_rowconfigure(6, weight=1)

        button_bar = tk.Frame(controls, bg="white")
        button_bar.grid(row=7, column=0, sticky="ew", pady=(14, 0))
        button_bar.grid_columnconfigure((0, 1, 2), weight=1, uniform="buttons")
        button_bar.grid_rowconfigure(0, weight=0)
        button_bar.grid_rowconfigure(1, weight=0)

        self.start_btn = ttk.Button(
            button_bar,
            text="🎬 Start Training",
            style="Primary.TButton",
            command=self.start_training,
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.end_btn = ttk.Button(
            button_bar,
            text="⛔ End Training",
            style="Primary.TButton",
            command=self.end_training,
            state=tk.DISABLED,
        )
        self.end_btn.grid(row=0, column=1, padx=5, sticky="ew")

        self.status_btn = ttk.Button(
            button_bar,
            text="📊 Check Status",
            style="Secondary.TButton",
            command=self.check_training_status,
            state=tk.DISABLED,
        )
        self.status_btn.grid(row=0, column=2, padx=(5, 0), sticky="ew")

        self.browser_btn = ttk.Button(
            button_bar,
            text="🌐 Launch Training Browser",
            style="Secondary.TButton",
            command=self.launch_browser,
        )
        self.browser_btn.grid(row=1, column=0, columnspan=3, padx=0, pady=(8, 0), sticky="ew")

        # Add a second row for monitoring controls
        button_bar.grid_rowconfigure(1, weight=0)
        
        monitor_btn = ttk.Button(
            button_bar,
            text="✅ Verify Monitoring",
            style="Secondary.TButton",
            command=self._check_monitoring_status,
        )
        monitor_btn.grid(row=0, column=3, padx=(5, 0), sticky="ew")
        
        # Full system monitoring controls (new row)
        monitoring_row = tk.Frame(controls, bg="white")
        monitoring_row.grid(row=8, column=0, sticky="ew", pady=(14, 0))
        monitoring_row.grid_columnconfigure((0, 1), weight=1, uniform="monitor_buttons")
        
        self.start_monitoring_btn = ttk.Button(
            monitoring_row,
            text="🔴 Start Monitoring",
            style="Primary.TButton",
            command=self._start_full_monitoring,
        )
        self.start_monitoring_btn.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        
        self.stop_monitoring_btn = ttk.Button(
            monitoring_row,
            text="⏹️ Stop Monitoring",
            style="Primary.TButton",
            command=self._stop_full_monitoring,
            state=tk.DISABLED,
        )
        self.stop_monitoring_btn.grid(row=0, column=1, padx=(5, 0), sticky="ew")
        
        self.monitoring_status_label = ttk.Label(
            monitoring_row,
            text="Status: Not monitoring",
            style="Muted.TLabel",
        )
        self.monitoring_status_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        # Status card ---------------------------------------------------
        status = ttk.Frame(main, style="Card.TFrame", padding=24)
        status.grid(row=0, column=1, sticky="nsew", padx=(12, 24), pady=(24, 12))

        ttk.Label(status, text="Session Status", style="SectionLabel.TLabel").pack(anchor="w")
        ttk.Label(status, textvariable=self.session_status_var, style="Muted.TLabel", wraplength=360, justify=tk.LEFT).pack(anchor="w", pady=(4, 12))
        ttk.Label(status, textvariable=self.output_mode_var, style="Muted.TLabel").pack(anchor="w", pady=(0, 18))
        ttk.Label(status, textvariable=self.prototype_summary_var, style="Muted.TLabel").pack(anchor="w")

        recent_frame = tk.Frame(status, bg="white")
        recent_frame.pack(fill=tk.BOTH, expand=True, pady=(16, 0))
        tk.Label(
            recent_frame,
            text="Recent Prototypes",
            font=("Segoe UI", 11, "bold"),
            bg="white",
            fg="#333333",
        ).pack(anchor="w")

        self.recent_list = tk.Listbox(
            recent_frame,
            height=7,
            font=("Consolas", 10),
            bg="#fafafa",
            activestyle="none",
            relief="flat",
        )
        self.recent_list.pack(fill=tk.BOTH, expand=True, pady=(6, 6))
        self.recent_list.bind("<Double-Button-1>", self._open_selected_prototype)

        recent_btn_bar = tk.Frame(recent_frame, bg="white")
        recent_btn_bar.pack(fill=tk.X)
        ttk.Button(
            recent_btn_bar,
            text="🔄 Refresh",
            command=self._refresh_recent_prototypes,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT)
        ttk.Button(
            recent_btn_bar,
            text="📂 Open Prototypes",
            command=self.open_prototypes_folder,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(
            recent_btn_bar,
            text="🤖 Automation Executor",
            command=self.open_automation_executor,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT)
        ttk.Button(
            recent_btn_bar,
            text="📊 Master Dashboard",
            command=self.open_master_dashboard,
            style="Secondary.TButton",
        ).pack(side=tk.LEFT, padx=(6, 0))

        # Log card ------------------------------------------------------
        log_card = ttk.Frame(main, style="Card.TFrame", padding=24)
        log_card.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=24, pady=(0, 24))
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure((0, 1), weight=1)
        ttk.Label(log_card, text="Activity Log", style="SectionLabel.TLabel").pack(anchor="w")
        self.log_text = scrolledtext.ScrolledText(
            log_card,
            height=10,
            font=("Consolas", 9),
            bg="#1f1f1f",
            fg="#e8e8e8",
            relief="flat",
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _compute_generation_mode(self) -> str:
        cursor_enabled = self.cursor_var.get()
        gpt_enabled = self.gpt_var.get()
        if cursor_enabled and gpt_enabled:
            return "both"
        if cursor_enabled:
            return "cursor"
        if gpt_enabled:
            return "gpt"
        return "none"

    def _update_output_mode_label(self) -> None:
        mode = self._compute_generation_mode()
        descriptions = {
            "both": "Output: Cursor prompt + GPT insight",
            "cursor": "Output: Cursor prompt only (no API cost)",
            "gpt": "Output: GPT insight only",
            "none": "Output: --- (select at least one option)",
        }
        self.output_mode_var.set(descriptions.get(mode, descriptions["both"]))

    def _get_cursor_notes(self) -> Optional[str]:
        notes = self.notes_text.get("1.0", tk.END).strip()
        return notes or None

    def _set_buttons_for_active_session(self, active: bool) -> None:
        if active:
            self.start_btn.config(state=tk.DISABLED)
            self.end_btn.config(state=tk.NORMAL)
            self.status_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.end_btn.config(state=tk.DISABLED)
            self.status_btn.config(state=tk.DISABLED)

    def _open_path(self, path: Path) -> None:
        if not path.exists():
            messagebox.showerror("Not Found", f"Path does not exist:\n{path}")
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["explorer", str(path)])
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror("Open Failed", f"Could not open {path}:\n{exc}")

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------
    def start_training(self) -> None:
        if self.session:
            messagebox.showinfo("Training Active", "A training session is already running.")
            return

        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Missing Title", "Please enter a workflow title before starting training.")
            return

        mode = self._compute_generation_mode()
        if mode == "none":
            messagebox.showwarning("Select Output", "Please enable at least one prototype output option before starting.")
            return

        try:
            notes = self._get_cursor_notes()
            # Update output directory based on user's choice
            output_folder = Path(self.output_folder_var.get().strip())
            if output_folder:
                self.manager.generator.output_dir = output_folder
                self.manager.generator.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Start training - clicking "Start Training" IS the consent
            self.log("🚀 Starting training session...")
            self.session = self.manager.start_training(title, generation_mode=mode, cursor_notes=notes)
            self._set_buttons_for_active_session(True)
            self._update_session_status()
            self.log(f"✅ Training started for '{title}'. Mode: {mode.upper()}.")
            self.log("✅ Full system monitoring is ACTIVE and recording everything.")
            self.log("   - Screen activity")
            self.log("   - Keyboard input")
            self.log("   - Mouse clicks and movements")
            self.log("   - Application usage (Excel, browsers, PDFs)")
            self.log("   - File system activity")
        except RuntimeError as exc:
            error_msg = str(exc)
            if "consent" in error_msg.lower() or "monitoring failed" in error_msg.lower():
                messagebox.showerror("Monitoring Required", error_msg)
            else:
                messagebox.showwarning("Cannot Start Training", error_msg)
            self.log(f"❌ Training failed to start: {error_msg}")
        except Exception as exc:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] Failed to start training: {error_details}")
            messagebox.showerror("Error", f"Failed to start training:\n{exc}\n\nCheck the console for details.")
            self.log(f"❌ Error: {exc}")

    def end_training(self) -> None:
        if not self.session:
            messagebox.showinfo("No Training", "No active training session to end.")
            return

        mode = self._compute_generation_mode()
        if mode == "none":
            messagebox.showwarning("Select Output", "Enable Cursor or GPT output before ending the session.")
            return

        session = self.session
        self.session = None
        
        # Disable the end button to prevent multiple clicks
        self.end_btn.config(state=tk.DISABLED)
        self.log("⏳ Processing training session... This may take 30-90 seconds.")
        self.log("   Please wait while we:")
        self.log("   - Stop monitoring and save all captured data")
        self.log("   - Extract events from the database")
        self.log("   - Generate prototype code")
        self.log("   - Generate GPT analysis (if enabled)")
        self.log("   - Create output folder with all training data")
        
        # Run in background thread to prevent UI freeze
        def process_training():
            try:
                self.after(0, lambda: self.log("📊 Step 1/5: Stopping monitoring and flushing data..."))
                notes = self._get_cursor_notes()
                
                self.after(0, lambda: self.log("📊 Step 2/5: Extracting session data from database..."))
                print(f"[DEBUG] Calling manager.end_training for session: {session.session_id}")
                bundle = self.manager.end_training(session, generation_mode=mode, cursor_notes=notes)
                print(f"[DEBUG] manager.end_training returned: {bundle}")
                
                if bundle:
                    self.after(0, lambda: self.log(f"📊 Step 3/5: Prototype files created at {bundle}"))
                    self.after(0, lambda: self.log("📊 Step 4/5: Generating GPT analysis (this may take 30-90 seconds)..."))
                    # Small delay to show the message
                    import time
                    time.sleep(0.5)
                    self.after(0, lambda: self.log("📊 Step 5/5: Training session complete!"))
                else:
                    self.after(0, lambda: self.log("⚠️ Warning: No bundle returned from end_training"))
                    self.after(0, lambda: self.log("   This usually means no events were captured during the session."))
                
                # Update UI in main thread
                self.after(0, lambda: self._on_training_complete(bundle, session, mode))
            except Exception as exc:
                import traceback
                error_details = traceback.format_exc()
                print(f"[ERROR] Training error: {error_details}")  # Also print to console
                # Show error in main thread
                self.after(0, lambda: self._on_training_error(exc, error_details))
        
        thread = threading.Thread(target=process_training, daemon=True)
        thread.start()
    
    def _on_training_complete(self, bundle: Optional[Path], session, mode: str) -> None:
        """Called when training processing completes (runs in main thread)"""
        self._set_buttons_for_active_session(False)
        self._update_session_status()
        
        if bundle:
            self.log("")
            self.log("=" * 60)
            self.log("✅ TRAINING SESSION COMPLETE!")
            self.log("=" * 60)
            self.log("")
            self.log(f"📁 Output folder location:")
            self.log(f"   {bundle}")
            self.log("")
            self.log("📦 Training session data includes:")
            
            # List all files in the bundle
            if bundle.exists():
                files = sorted(bundle.glob("*"))
                for file in files:
                    if file.is_file():
                        try:
                            size = file.stat().st_size
                            size_str = f"({size:,} bytes)" if size < 1024 else f"({size/1024:.1f} KB)"
                            self.log(f"   ✅ {file.name} {size_str}")
                        except:
                            self.log(f"   ✅ {file.name}")
                    elif file.is_dir():
                        try:
                            file_count = len(list(file.glob("*")))
                            self.log(f"   📁 {file.name}/ ({file_count} items)")
                        except:
                            self.log(f"   📁 {file.name}/")
            else:
                self.log("   ⚠️ WARNING: Folder does not exist at expected location!")
            
            if session.screen_manifest and session.screen_manifest.get("capture_dir"):
                self.log(f"   📸 Screen captures: {len(session.screen_manifest.get('frames', []))} frames")
            
            # Check if GPT report was generated
            gpt_report_path = bundle / "gpt_report.md"
            cursor_prompt_path = bundle / "cursor_prompt.txt"
            
            self.log("")
            if gpt_report_path.exists():
                self.log("✅ GPT workflow analysis: Generated")
            elif mode in {"gpt", "both"}:
                self.log("⚠️ GPT workflow analysis: NOT generated (check API key)")
            
            if cursor_prompt_path.exists():
                self.log("✅ Cursor prompt: Generated")
            
            self.log("")
            self.log("🔍 Opening folder in Windows Explorer...")
            
            # Open the folder in Windows Explorer
            try:
                import subprocess
                subprocess.Popen(f'explorer "{bundle}"')
            except:
                pass
            
            messagebox.showinfo(
                "Training Complete",
                f"Prototype generated:\n{bundle}\n\n"
                f"Files created:\n"
                f"• prototype.py - Automation code template\n"
                f"{'• gpt_report.md - AI workflow analysis' if gpt_report_path.exists() else '• (GPT report skipped - check API key)'}\n"
                f"{'• cursor_prompt.txt - Manual build instructions' if cursor_prompt_path.exists() else ''}\n"
                f"• summary.json - Session metadata\n"
                f"• README.md - Session overview"
            )
        else:
            self.log("⚠️ Warning: Training completed but no prototype was generated.")
            self.log("   This usually means no events were captured during the session.")
            self.log("   Make sure you performed actions (clicks, typing, navigation) during training.")
            messagebox.showwarning(
                "No Data Captured",
                "Training completed but no events were captured.\n\n"
                "Possible reasons:\n"
                "- No actions were performed during the session\n"
                "- Monitoring database was not accessible\n"
                "- Session ID mismatch\n\n"
                "Check the console output (where you launched the app) for detailed debug information."
            )
        
        self._refresh_recent_prototypes()
    
    def _on_training_error(self, exc: Exception, error_details: Optional[str] = None) -> None:
        """Called when training processing encounters an error (runs in main thread)"""
        self._set_buttons_for_active_session(False)
        self._update_session_status()
        error_msg = str(exc)
        self.log(f"❌ Error: {error_msg}")
        if error_details:
            self.log(f"   Details: {error_details[:500]}")  # Log first 500 chars
        messagebox.showerror("Error", f"Failed to end training:\n{error_msg}\n\nCheck the Activity Log for details.")

    def launch_browser(self) -> None:
        if not TRAINING_BROWSER.exists():
            messagebox.showerror("Not Available", "Training browser script not found.")
            return
        try:
            subprocess.Popen([sys.executable, str(TRAINING_BROWSER)])
            self.log("Training browser launched.")
        except Exception as exc:
            messagebox.showerror("Launch Failed", f"Could not launch training browser:\n{exc}")

    def open_prototypes_folder(self) -> None:
        self._open_path(PROTOTYPE_DIR)

    def open_automation_executor(self) -> None:
        if not AUTOMATION_EXECUTOR.exists():
            messagebox.showerror("Not Available", "Automation executor GUI not found.")
            return
        try:
            subprocess.Popen([sys.executable, str(AUTOMATION_EXECUTOR)])
            self.log("Automation Executor launched.")
        except Exception as exc:
            messagebox.showerror("Launch Failed", f"Could not launch Automation Executor:\n{exc}")

    def open_master_dashboard(self) -> None:
        if not DASHBOARD_SCRIPT.exists():
            messagebox.showerror("Not Available", "Master AI Dashboard script not found.")
            return
        try:
            subprocess.Popen([sys.executable, str(DASHBOARD_SCRIPT)])
            self.log("Master AI Dashboard launched.")
        except Exception as exc:
            messagebox.showerror("Launch Failed", f"Could not launch Master AI Dashboard:\n{exc}")

    def _open_selected_prototype(self, event) -> None:
        if not self.recent_items:
            return
        selection = self.recent_list.curselection()
        if not selection:
            return
        index = selection[0]
        if 0 <= index < len(self.recent_items):
            self._open_path(self.recent_items[index])

    # ------------------------------------------------------------------
    # Monitoring verification
    # ------------------------------------------------------------------
    def _start_full_monitoring(self) -> None:
        """Start full system monitoring"""
        if not FULL_MONITORING_AVAILABLE:
            messagebox.showerror(
                "Monitoring Not Available",
                "Full system monitoring is not available.\n\n"
                "Please ensure the monitoring module is properly installed:\n"
                "pip install mss pynput psutil watchdog"
            )
            self.log("❌ Full system monitoring not available - dependencies missing")
            return
        
        if self.monitoring_active:
            messagebox.showinfo("Already Monitoring", "Full system monitoring is already active.")
            return
        
        # Confirm consent
        consent = messagebox.askyesno(
            "Consent Required",
            "You are about to start FULL SYSTEM MONITORING.\n\n"
            "This will record:\n"
            "- Screen activity\n"
            "- Keyboard input\n"
            "- Mouse movements\n"
            "- Application usage\n"
            "- File system activity\n\n"
            "All data will be encrypted and stored locally.\n\n"
            "Do you give explicit consent to start monitoring?"
        )
        
        if not consent:
            self.log("Monitoring start cancelled - user did not give consent")
            return
        
        try:
            # Use the global monitor instance instead of creating a new one
            # This ensures "Start Training" can reuse the same monitoring session
            from monitoring.full_system_monitor import start_full_monitoring
            self.full_monitor = start_full_monitoring(INSTALLATION_DIR, user_consent=True)
            self.monitoring_active = True
            
            # Update UI
            self.start_monitoring_btn.config(state=tk.DISABLED)
            self.stop_monitoring_btn.config(state=tk.NORMAL)
            self.monitoring_status_label.config(
                text="Status: 🔴 Monitoring active - Recording all system activity",
                foreground="#dc3545"
            )
            
            session_id = getattr(self.full_monitor, 'session_id', 'unknown')
            self.log(f"✅ Full system monitoring started - Session ID: {session_id}")
            self.log("   Recording: Screen, Keyboard, Mouse, Applications, Files")
            messagebox.showinfo(
                "Monitoring Started",
                f"Full system monitoring is now active.\n\n"
                f"Session ID: {session_id}\n\n"
                f"All system activity is being recorded and stored securely."
            )
        except Exception as exc:
            error_msg = str(exc)
            self.log(f"❌ Failed to start monitoring: {error_msg}")
            messagebox.showerror("Monitoring Error", f"Failed to start full system monitoring:\n\n{error_msg}")
            self.monitoring_active = False
            self.full_monitor = None
    
    def _stop_full_monitoring(self) -> None:
        """Stop full system monitoring"""
        if not self.monitoring_active or not self.full_monitor:
            messagebox.showinfo("Not Monitoring", "Full system monitoring is not currently active.")
            return
        
        try:
            self.full_monitor.stop_monitoring()
            session_id = getattr(self.full_monitor, 'session_id', 'unknown')
            
            # Update UI
            self.monitoring_active = False
            self.start_monitoring_btn.config(state=tk.NORMAL)
            self.stop_monitoring_btn.config(state=tk.DISABLED)
            self.monitoring_status_label.config(
                text="Status: ⏹️ Monitoring stopped",
                foreground="#666666"
            )
            
            self.log(f"⏹️ Full system monitoring stopped - Session ID: {session_id}")
            messagebox.showinfo(
                "Monitoring Stopped",
                f"Full system monitoring has been stopped.\n\n"
                f"Session ID: {session_id}\n\n"
                f"All recorded data has been saved securely."
            )
            
            self.full_monitor = None
        except Exception as exc:
            error_msg = str(exc)
            self.log(f"❌ Error stopping monitoring: {error_msg}")
            messagebox.showerror("Monitoring Error", f"Error stopping monitoring:\n\n{error_msg}")
    
    def _check_monitoring_status(self) -> None:
        self.log("Running monitoring verification...")
        browser_db = INSTALLATION_DIR / "_secure_data" / "browser_activity.db"
        if not browser_db.exists():
            messagebox.showwarning(
                "Monitoring Not Found",
                "browser_activity.db is missing. Ensure monitoring services are installed.",
            )
            self.log("Monitoring database not found. Cannot verify telemetry.")
            return

        try:
            conn = sqlite3.connect(str(browser_db))
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            threshold = datetime.now(UTC) - timedelta(minutes=5)
            rows_nav = cur.execute(
                "SELECT session_id, timestamp FROM page_navigations ORDER BY id DESC LIMIT 200"
            ).fetchall()
            rows_int = cur.execute(
                "SELECT session_id, action_type, timestamp FROM element_interactions ORDER BY id DESC LIMIT 200"
            ).fetchall()
            recent_nav_details = cur.execute(
                "SELECT session_id, timestamp FROM page_navigations ORDER BY id DESC LIMIT 5"
            ).fetchall()
            recent_int_details = cur.execute(
                "SELECT session_id, action_type, timestamp FROM element_interactions ORDER BY id DESC LIMIT 5"
            ).fetchall()
        except Exception as exc:
            messagebox.showerror("Monitoring Check Failed", f"Unable to read monitoring DB:\n{exc}")
            self.log(f"Monitoring check failed: {exc}")
            return
        finally:
            try:
                conn.close()
            except Exception:
                pass

        active_session_id = self.session.session_id if self.session else None

        def summarize(rows):
            total = len(rows)
            recent = 0
            session_total = 0
            for row in rows:
                ts = row["timestamp"] if isinstance(row, sqlite3.Row) else row[1]
                try:
                    ts_dt = datetime.fromisoformat(ts)
                    if ts_dt.tzinfo is None:
                        ts_dt = ts_dt.replace(tzinfo=UTC)
                except Exception:
                    ts_dt = None
                if ts_dt and ts_dt >= threshold:
                    recent += 1
                sid = row["session_id"] if isinstance(row, sqlite3.Row) else row[0]
                if active_session_id and sid == active_session_id:
                    session_total += 1
            return total, recent, session_total

        def format_rows(rows):
            formatted = []
            for row in rows:
                row_dict = dict(row)
                ts = row_dict.get("timestamp")
                sid = row_dict.get("session_id", "?")
                try:
                    ts_dt = datetime.fromisoformat(ts)
                    ts_formatted = ts_dt.strftime("%H:%M:%S")
                except Exception:
                    ts_formatted = ts
                action = row_dict.get("action_type")
                formatted.append(f"{ts_formatted} • {sid}" + (f" • {action}" if action else ""))
            return formatted

        nav_total, nav_recent, nav_session = summarize(rows_nav)
        int_total, int_recent, int_session = summarize(rows_int)

        lines = [
            "Monitoring database located at _secure_data/browser_activity.db",
            f"Page navigations recorded: total={nav_total}, last_5_min={nav_recent}",
            f"Element interactions recorded: total={int_total}, last_5_min={int_recent}",
        ]
        if active_session_id:
            lines.append(
                f"Active session {active_session_id}: navigations={nav_session}, interactions={int_session}"
            )
        else:
            lines.append("No active training session; monitoring check covers historical data.")
        lines.append("\nRecent navigation timestamps:")
        lines.extend(format_rows(recent_nav_details) or ["(none recorded)"])
        lines.append("\nRecent interaction timestamps:")
        lines.extend(format_rows(recent_int_details) or ["(none recorded)"])

        summary = "\n".join(lines)
        self.log("Monitoring check completed.\n" + summary)
        messagebox.showinfo("Monitoring Status", summary)

    # ------------------------------------------------------------------
    # Data refresh & status helpers
    # ------------------------------------------------------------------
    def _update_session_status(self) -> None:
        if not self.session:
            self.session_status_var.set("No active training session.")
            return
        started = self.session.started_at.strftime("%Y-%m-%d %H:%M")
        self.session_status_var.set(
            f"Recording '{self.session.title}' since {started}. Session ID: {self.session.session_id}."
        )

    def check_training_status(self) -> None:
        """Check and display real-time training session status"""
        if not self.session:
            messagebox.showwarning("No Active Session", "No training session is currently active.")
            return
        
        try:
            session_id = self.session.session_id
            status_lines = []
            status_lines.append("=" * 60)
            status_lines.append("TRAINING SESSION STATUS")
            status_lines.append("=" * 60)
            status_lines.append("")
            status_lines.append(f"Session ID: {session_id}")
            status_lines.append(f"Workflow Title: {self.session.title}")
            status_lines.append(f"Started: {self.session.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Check monitoring status
            try:
                if FULL_MONITORING_AVAILABLE and get_full_monitor:
                    monitor = get_full_monitor(INSTALLATION_DIR, user_consent=True)
                    if monitor:
                        monitoring_active = getattr(monitor, "monitoring_active", False)
                        if monitoring_active:
                            metrics = monitor.get_metrics()
                            # Check queue size
                            queue_size = 0
                            if hasattr(monitor, 'storage_queue'):
                                queue_size = monitor.storage_queue.qsize()
                            
                            # Check monitor's session ID
                            monitor_session_id = getattr(monitor, 'session_id', 'unknown')
                            
                            status_lines.append("")
                            status_lines.append("✅ MONITORING: ACTIVE")
                            status_lines.append(f"   Monitor Session ID: {monitor_session_id}")
                            if monitor_session_id != session_id:
                                status_lines.append(f"   ⚠️ WARNING: Session ID mismatch! Monitor: {monitor_session_id}, Training: {session_id}")
                            status_lines.append(f"   Events in queue (not yet saved): {queue_size}")
                            status_lines.append("")
                            status_lines.append("   Real-time counts (detected by monitor):")
                            status_lines.append(f"      Screens recorded: {metrics.get('screens_recorded', 0)}")
                            status_lines.append(f"      Keystrokes recorded: {metrics.get('keystrokes_recorded', 0)}")
                            status_lines.append(f"      Mouse events recorded: {metrics.get('mouse_events_recorded', 0)}")
                            status_lines.append(f"      Browser events recorded: {metrics.get('browser_events_recorded', 0)}")
                            status_lines.append(f"      Excel events recorded: {metrics.get('excel_events_recorded', 0)}")
                            status_lines.append(f"      PDF events recorded: {metrics.get('pdf_events_recorded', 0)}")
                            status_lines.append(f"      File events recorded: {metrics.get('file_events_recorded', 0)}")
                        else:
                            status_lines.append("")
                            status_lines.append("❌ MONITORING: NOT ACTIVE")
            except Exception as e:
                status_lines.append("")
                status_lines.append(f"⚠️ Could not check monitor status: {e}")
            
            # Check database for events
            status_lines.append("")
            status_lines.append("-" * 60)
            status_lines.append("DATABASE EVENTS (for this session):")
            status_lines.append("(Note: Events may still be in queue above)")
            status_lines.append("-" * 60)
            
            # Check full_monitoring.db
            full_monitoring_db = INSTALLATION_DIR / "_secure_data" / "full_monitoring" / "full_monitoring.db"
            if full_monitoring_db.exists():
                try:
                    with sqlite3.connect(full_monitoring_db) as conn:
                        cursor = conn.cursor()
                        
                        # Browser activity
                        cursor.execute("SELECT COUNT(*) FROM browser_activity WHERE session_id = ?", (session_id,))
                        browser_count = cursor.fetchone()[0]
                        # Check if there are browser events with different session IDs (in case of mismatch)
                        cursor.execute("SELECT COUNT(*) FROM browser_activity WHERE timestamp > datetime('now', '-1 hour')")
                        recent_browser_total = cursor.fetchone()[0]
                        if browser_count == 0 and recent_browser_total > 0:
                            # Check what session IDs exist
                            cursor.execute("SELECT DISTINCT session_id FROM browser_activity WHERE timestamp > datetime('now', '-1 hour') LIMIT 5")
                            other_sessions = [row[0] for row in cursor.fetchall()]
                            status_lines.append(f"   Browser Activity: {browser_count} events")
                            status_lines.append(f"      ⚠️ {recent_browser_total} recent browser events found with other session IDs: {other_sessions}")
                            status_lines.append(f"      This suggests a session ID mismatch - events may be recorded but under a different session ID")
                        else:
                            status_lines.append(f"   Browser Activity: {browser_count} events")
                        
                        # Mouse activity
                        cursor.execute("SELECT COUNT(*) FROM mouse_activity WHERE session_id = ?", (session_id,))
                        mouse_count = cursor.fetchone()[0]
                        status_lines.append(f"   Mouse Activity: {mouse_count} events")
                        
                        # Keyboard input
                        cursor.execute("SELECT COUNT(*) FROM keyboard_input WHERE session_id = ?", (session_id,))
                        keyboard_count = cursor.fetchone()[0]
                        status_lines.append(f"   Keyboard Input: {keyboard_count} events")
                        
                        # Excel activity
                        cursor.execute("SELECT COUNT(*) FROM excel_activity WHERE session_id = ?", (session_id,))
                        excel_count = cursor.fetchone()[0]
                        status_lines.append(f"   Excel Activity: {excel_count} events")
                        
                        # PDF activity
                        cursor.execute("SELECT COUNT(*) FROM pdf_activity WHERE session_id = ?", (session_id,))
                        pdf_count = cursor.fetchone()[0]
                        status_lines.append(f"   PDF Activity: {pdf_count} events")
                        
                        # Screen recordings
                        cursor.execute("SELECT COUNT(*) FROM screen_recordings WHERE session_id = ?", (session_id,))
                        screen_count = cursor.fetchone()[0]
                        status_lines.append(f"   Screen Recordings: {screen_count} frames")
                        
                        total_events = browser_count + mouse_count + keyboard_count + excel_count + pdf_count
                        status_lines.append("")
                        status_lines.append(f"   TOTAL EVENTS: {total_events}")
                        
                        # Show recent activity (last 5 events)
                        if total_events > 0:
                            status_lines.append("")
                            status_lines.append("   Recent Activity (last 5 events):")
                            cursor.execute("""
                                SELECT 'browser' as type, timestamp, action_type, window_title 
                                FROM browser_activity WHERE session_id = ? 
                                UNION ALL
                                SELECT 'mouse' as type, timestamp, event_type, '' 
                                FROM mouse_activity WHERE session_id = ? 
                                UNION ALL
                                SELECT 'keyboard' as type, timestamp, key_name, '' 
                                FROM keyboard_input WHERE session_id = ? 
                                UNION ALL
                                SELECT 'excel' as type, timestamp, action_type, workbook_name 
                                FROM excel_activity WHERE session_id = ? 
                                UNION ALL
                                SELECT 'pdf' as type, timestamp, action_type, pdf_file_name 
                                FROM pdf_activity WHERE session_id = ? 
                                ORDER BY timestamp DESC LIMIT 5
                            """, (session_id, session_id, session_id, session_id, session_id))
                            
                            recent = cursor.fetchall()
                            for event_type, timestamp, action, detail in recent:
                                time_str = timestamp.split('T')[1].split('.')[0] if 'T' in timestamp else timestamp[:8]
                                detail_str = f" - {detail}" if detail else ""
                                status_lines.append(f"      [{time_str}] {event_type}: {action}{detail_str}")
                except Exception as e:
                    status_lines.append(f"   ⚠️ Error querying database: {e}")
            else:
                status_lines.append("   ⚠️ Database not found (monitoring may not have started)")
            
            # Check browser_activity.db (Selenium browser)
            browser_db = INSTALLATION_DIR / "_secure_data" / "browser_activity.db"
            if browser_db.exists():
                try:
                    with sqlite3.connect(browser_db) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT COUNT(*) FROM page_navigations WHERE session_id = ?", (session_id,))
                        nav_count = cursor.fetchone()[0]
                        cursor.execute("SELECT COUNT(*) FROM element_interactions WHERE session_id = ?", (session_id,))
                        int_count = cursor.fetchone()[0]
                        if nav_count > 0 or int_count > 0:
                            status_lines.append("")
                            status_lines.append("   Selenium Browser Activity:")
                            status_lines.append(f"      Page Navigations: {nav_count}")
                            status_lines.append(f"      Element Interactions: {int_count}")
                except Exception as e:
                    pass  # Ignore errors for browser_activity.db
            
            status_lines.append("")
            status_lines.append("=" * 60)
            
            # Show in a scrollable window
            status_text = "\n".join(status_lines)
            
            # Create a scrollable window for better viewing
            status_window = tk.Toplevel(self)
            status_window.title("Training Session Status")
            status_window.geometry("700x600")
            status_window.configure(bg="white")
            
            # Title
            title_label = tk.Label(
                status_window,
                text="📊 Real-Time Training Status",
                font=("Segoe UI", 14, "bold"),
                bg="white",
                fg="#2c3e50"
            )
            title_label.pack(pady=(15, 10))
            
            # Scrollable text area
            text_frame = tk.Frame(status_window, bg="white")
            text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 15))
            
            status_text_widget = scrolledtext.ScrolledText(
                text_frame,
                wrap=tk.WORD,
                font=("Consolas", 10),
                bg="#f8f9fa",
                fg="#2c3e50",
                relief=tk.FLAT,
                borderwidth=1,
                highlightthickness=1,
                highlightbackground="#dee2e6"
            )
            status_text_widget.pack(fill=tk.BOTH, expand=True)
            status_text_widget.insert("1.0", status_text)
            status_text_widget.config(state=tk.DISABLED)
            
            # Close button
            close_btn = tk.Button(
                status_window,
                text="Close",
                command=status_window.destroy,
                bg="#007bff",
                fg="white",
                font=("Segoe UI", 10, "bold"),
                padx=30,
                pady=8,
                relief=tk.FLAT,
                cursor="hand2"
            )
            close_btn.pack(pady=(0, 15))
            
            # Also log to activity log
            self.log("")
            self.log("=" * 60)
            self.log("📊 TRAINING STATUS CHECK")
            self.log("=" * 60)
            for line in status_lines:
                self.log(line)
            self.log("")
            
        except Exception as e:
            import traceback
            error_msg = f"Error checking status: {e}\n{traceback.format_exc()}"
            messagebox.showerror("Status Check Failed", error_msg)
            self.log(f"❌ Status check failed: {e}")

    def _refresh_recent_prototypes(self) -> None:
        try:
            prototypes = self.generator.list_prototypes()
        except Exception as exc:
            self.prototype_summary_var.set(f"Unable to load prototypes: {exc}")
            return

        total = len(prototypes)
        if total:
            self.prototype_summary_var.set(f"{total} prototype bundle(s) available in automation_prototypes.")
        else:
            self.prototype_summary_var.set("No prototypes generated yet.")

        sorted_items = sorted(
            prototypes.values(),
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )

        self.recent_list.delete(0, tk.END)
        self.recent_items = []
        for item in sorted_items[:8]:
            created = item.get("created_at", "")
            display_name = item.get("display_name") or item.get("pattern_hash", "(unknown)")
            line = f"{created[:16]}  |  {display_name}"
            self.recent_list.insert(tk.END, line)
            self.recent_items.append(Path(item.get("path")))

    # ------------------------------------------------------------------
    # Logging helper
    # ------------------------------------------------------------------
    def log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    # ------------------------------------------------------------------
    # GPT API Key Management
    # ------------------------------------------------------------------
    def _get_encryption_key(self) -> Optional[bytes]:
        """Generate or retrieve encryption key for API key storage."""
        if not CRYPTOGRAPHY_AVAILABLE:
            return None
        
        try:
            key_file = AI_ROOT / ".api_key_encryption_key"
            
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                # Generate new key based on machine info
                machine_id = f"{platform.node()}{getpass.getuser()}{AI_ROOT}"
                password = machine_id.encode()
                salt = b'ai_workflow_trainer_salt_2024'
                
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
                
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                return key
        except Exception as e:
            self.log(f"Error generating encryption key: {e}")
            return None
    
    def _load_gpt_api_key(self) -> None:
        """Load and decrypt GPT API key from secure storage, or fallback to LLMService config"""
        # First try to load from encrypted storage
        if CRYPTOGRAPHY_AVAILABLE:
            try:
                if self.api_key_file.exists():
                    encryption_key = self._get_encryption_key()
                    if encryption_key:
                        fernet = Fernet(encryption_key)
                        with open(self.api_key_file, 'rb') as f:
                            encrypted_key = f.read()
                        decrypted_key = fernet.decrypt(encrypted_key)
                        self.gpt_api_key = decrypted_key.decode('utf-8')
                        # Sync with LLMService if available
                        if self.llm_service and self.gpt_api_key:
                            try:
                                self.llm_service.save_config(
                                    api_key=self.gpt_api_key,
                                    model="gpt-4o-mini",
                                    provider="openai",
                                    temperature=0.3
                                )
                            except Exception:
                                pass
                        return
            except Exception as e:
                self.log(f"Error loading encrypted API key: {e}")
        
        # Fallback: Try to load from LLMService config
        if self.llm_service:
            try:
                config = self.llm_service.get_config()
                if config and config.api_key:
                    self.gpt_api_key = config.api_key
                    return
            except Exception as e:
                self.log(f"Error loading API key from LLMService: {e}")
        
        self.gpt_api_key = None
    
    def _save_api_key(self) -> None:
        """Encrypt and save GPT API key to secure storage"""
        if not CRYPTOGRAPHY_AVAILABLE:
            messagebox.showerror(
                "Error",
                "Cryptography library not installed.\n\n"
                "Please install it: pip install cryptography"
            )
            return
        
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("Missing API Key", "Please enter your GPT API key.")
            return
        
        try:
            encryption_key = self._get_encryption_key()
            if not encryption_key:
                messagebox.showerror("Error", "Failed to generate encryption key for secure storage")
                return
            
            fernet = Fernet(encryption_key)
            encrypted_key = fernet.encrypt(api_key.encode('utf-8'))
            
            with open(self.api_key_file, 'wb') as f:
                f.write(encrypted_key)
            
            self.gpt_api_key = api_key
            self.api_key_entry.delete(0, tk.END)  # Clear for security
            
            # Sync API key with LLMService so it can be used for GPT insights
            if self.llm_service:
                try:
                    # Use gpt-4o-mini as default model (cost-effective and reliable)
                    self.llm_service.save_config(
                        api_key=api_key,
                        model="gpt-4o-mini",
                        provider="openai",
                        temperature=0.3
                    )
                    self.log("✅ API key synced with LLMService - Ready for GPT insights")
                except Exception as e:
                    self.log(f"⚠️ Warning: API key saved but LLMService sync failed: {e}")
            
            self._update_api_key_status()
            
            self.log("✅ GPT API key saved successfully (encrypted)")
            messagebox.showinfo(
                "Success",
                "GPT API key saved securely!\n\n"
                "The key is encrypted and stored on your machine.\n"
                "It has been synced with the LLM service for workflow interpretation."
            )
        except Exception as e:
            error_msg = str(e)
            self.log(f"❌ Error saving API key: {error_msg}")
            messagebox.showerror("Error", f"Failed to save API key securely:\n\n{error_msg}")
    
    def _test_openai_connection(self) -> None:
        """Test OpenAI API connection"""
        api_key = self.gpt_api_key
        if not api_key:
            # Try to get from entry field
            api_key = self.api_key_entry.get().strip()
            if not api_key:
                messagebox.showwarning(
                    "No API Key",
                    "Please enter and save your API key first, or enter it in the field above."
                )
                return
        
        if not OPENAI_AVAILABLE:
            messagebox.showerror(
                "OpenAI Not Available",
                "OpenAI library not installed.\n\n"
                "Please install it: pip install openai"
            )
            return
        
        self.log("🔍 Testing OpenAI API connection...")
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Say 'API connection successful' if you can read this."}],
                max_tokens=20
            )
            result = response.choices[0].message.content
            self.log(f"✅ OpenAI API connection test successful: {result}")
            messagebox.showinfo(
                "Connection Test Successful",
                f"✅ OpenAI API connection is working!\n\nResponse: {result}\n\n"
                f"Model: {response.model}\n"
                f"Tokens used: {response.usage.total_tokens}"
            )
        except Exception as e:
            error_msg = str(e)
            self.log(f"❌ OpenAI API connection test failed: {error_msg}")
            messagebox.showerror(
                "Connection Test Failed",
                f"Failed to connect to OpenAI API:\n\n{error_msg}\n\n"
                "Please check your API key and internet connection."
            )
    
    def _update_api_key_status(self) -> None:
        """Update the API key status label"""
        try:
            if self.gpt_api_key:
                masked_key = self.gpt_api_key[:8] + "..." + self.gpt_api_key[-4:] if len(self.gpt_api_key) > 12 else "***"
                self.api_key_status_label.config(
                    text=f"Status: ✅ API key saved (Key: {masked_key})",
                    foreground="#28a745"
                )
            else:
                self.api_key_status_label.config(
                    text="Status: ⚠️ No API key saved - Enter and save your key above",
                    foreground="#dc3545"
                )
        except Exception as e:
            self.log(f"Error updating API key status: {e}")


def main() -> None:
    app = WorkflowTrainerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
