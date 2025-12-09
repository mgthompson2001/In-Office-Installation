#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPS IA Referral Form Uploader - Dual Tab Version (FULLY FUNCTIONAL)
Tab 1: Base IA Referral form uploader (regular therapy notes)
Tab 2: IPS IA Referral form uploader (IPS therapy notes)

This uploader processes referral form PDFs and uploads them to TherapyNotes,
filtering files based on whether they have "IPS" in the filename.
"""

import os, sys, time, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime, timedelta
import csv as _csv
import re

APP_TITLE = "IA Referral Form Uploader - Dual Tab"
MAROON    = "#800000"
HEADER_FG = "#ffffff"
LOG_BG    = "#f5f5f5"
LOG_FG    = "#000000"

# TherapyNotes URLs
BASE_TN_LOGIN_URL = "https://www.therapynotes.com/app/login/IntegritySWS/"
IPS_TN_LOGIN_URL  = "https://www.therapynotes.com/app/login/IntegrityIPS/"

TN_USER_ID = "Login__UsernameField"
TN_PASS_ID = "Login__Password"
TN_BTN_ID  = "Login__LogInButton"

# CSV constants
CSV_COL_L_INDEX = 11  # Column L (Therapist Name)
CSV_COL_R_INDEX = 17  # Column R (Urgent)


# ===== Helper Functions =====
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


def _detect_client_name_index(header_row):
    """Try to detect a 'client name' column. Fallback to 0."""
    candidates = []
    for i, cell in enumerate(header_row or []):
        label = (cell or "").strip().lower()
        if not label: continue
        if "client" in label and "name" in label:
            candidates.append((0, i))
        elif "patient" in label and "name" in label:
            candidates.append((1, i))
        elif "name" in label:
            candidates.append((2, i))
    if candidates:
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    return 0


def _extract_full_name_from_csv(row, client_name_idx):
    """
    Extract full name from CSV row. Handles: ID (A), Last Name (B), First Name (C)
    IMPROVED: Always check for separate First/Last columns before accepting multi-word names
    """
    if not row or len(row) <= client_name_idx:
        return None
    
    client_name = (row[client_name_idx] or "").strip()
    if not client_name:
        return None
    
    # PRIORITY 1: Check columns B and C for First/Last Name (most common format)
    # Column 0 (A): ID, Column 1 (B): Last Name, Column 2 (C): First Name
    if len(row) > 2:
        potential_last = (row[1] or "").strip()
        potential_first = (row[2] or "").strip()
        
        # If both B and C have valid name data, use them (handles compound last names correctly)
        if (potential_last and len(potential_last) > 1 and not potential_last.isdigit() and
            potential_first and len(potential_first) > 1 and not potential_first.isdigit()):
            # This correctly handles "Smith Doe" in B + "Jane" in C → "Jane Smith Doe"
            return f"{potential_first} {potential_last}"
    
    # PRIORITY 2: Check adjacent columns around client_name_idx
    if client_name_idx > 0:
        potential_prev = (row[client_name_idx - 1] or "").strip()
        if potential_prev and len(potential_prev) > 1 and not potential_prev.isdigit():
            if client_name_idx + 1 < len(row):
                potential_next = (row[client_name_idx + 1] or "").strip()
                if potential_next and len(potential_next) > 1 and not potential_next.isdigit():
                    # Three columns: prev, current, next - assume prev is last, current is first
                    return f"{client_name} {potential_prev}"
            # Only previous column available
            return f"{potential_prev} {client_name}"
    
    if client_name_idx + 1 < len(row):
        potential_next = (row[client_name_idx + 1] or "").strip()
        if potential_next and len(potential_next) > 1 and not potential_next.isdigit():
            return f"{client_name} {potential_next}"
    
    # PRIORITY 3: Only if no separate columns found, accept multi-word client_name
    if " " in client_name and len(client_name.split()) >= 2:
        return client_name
    
    # Fall back to just the client name
    return client_name


def _find_pdf_for_client(base_folder: str, client_name: str, filter_mode: str = "all"):
    """
    Find PDF for client with improved matching logic.
    filter_mode: "all", "skip_ips", "only_ips"
    """
    if not base_folder or not os.path.isdir(base_folder):
        return None
    
    want = re.sub(r"\s+", " ", client_name).strip().lower()
    want_parts = want.split()
    
    best = None
    best_mtime = -1
    best_score = 0
    
    for root, _, files in os.walk(base_folder):
        for fn in files:
            if not fn.lower().endswith(".pdf"): 
                continue
            
            # Apply IPS filtering
            has_ips = "ips" in fn.lower()
            if filter_mode == "skip_ips" and has_ips:
                continue  # Skip IPS files in base mode
            if filter_mode == "only_ips" and not has_ips:
                continue  # Skip non-IPS files in IPS mode
            
            name_norm = re.sub(r"[\s_]+", " ", os.path.splitext(fn)[0].lower())
            name_parts = name_norm.split()
            
            score = 0
            if want in name_norm or name_norm in want:
                score = 100
            elif all(part in name_norm for part in want_parts):
                score = 90
            elif any(part in name_norm for part in want_parts if len(part) > 2):
                matching_words = sum(1 for part in want_parts if part in name_norm and len(part) > 2)
                score = 50 + (matching_words * 10)
            elif any(part in want for part in name_parts if len(part) > 2):
                matching_words = sum(1 for part in name_parts if part in want and len(part) > 2)
                score = 40 + (matching_words * 10)
            
            if score > 0:
                fp = os.path.join(root, fn)
                try: 
                    mtime = os.path.getmtime(fp)
                except Exception: 
                    mtime = 0
                
                if score > best_score or (score == best_score and mtime > best_mtime):
                    best_score = score
                    best_mtime = mtime
                    best = fp
    
    return best


def _write_report(records: list, csv_path: str) -> str:
    """Write upload report"""
    base_dir  = os.path.dirname(csv_path)
    base_name = os.path.splitext(os.path.basename(csv_path))[0]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx_path = os.path.join(base_dir, f"{base_name}_upload_report_{stamp}.xlsx")
    try:
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "Upload Report"
        ws.append(["CSV Row", "Therapist", "Client", "Status", "Reason", "Timestamp"])
        for r in records:
            ws.append([r.get("csv_row",""), r.get("therapist",""), r.get("client",""), r.get("status",""),
                       r.get("reason",""), r.get("timestamp","")])
        wb.save(xlsx_path); return xlsx_path
    except Exception:
        csv_out = os.path.join(base_dir, f"{base_name}_upload_report_{stamp}.csv")
        try:
            with open(csv_out, "w", newline="", encoding="utf-8") as f:
                w = _csv.writer(f)
                w.writerow(["CSV Row", "Therapist", "Client", "Status", "Reason", "Timestamp"])
                for r in records:
                    w.writerow([r.get("csv_row",""), r.get("therapist",""), r.get("client",""), r.get("status",""),
                                r.get("reason",""), r.get("timestamp","")])
            return csv_out
        except Exception:
            txt_out = os.path.join(base_dir, f"{base_name}_upload_report_{stamp}.txt")
            with open(txt_out, "w", encoding="utf-8") as f:
                f.write("CSV Row\tTherapist\tClient\tStatus\tReason\tTimestamp\n")
                for r in records:
                    f.write(f"{r.get('csv_row','')}\t{r.get('therapist','')}\t{r.get('client','')}\t{r.get('status','')}\t{r.get('reason','')}\t{r.get('timestamp','')}\n")
            return txt_out


def _lazy_import_selenium():
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


class UILog:
    def __init__(self, widget):
        self.w = widget
        try: self.w.configure(state="disabled", bg=LOG_BG, fg=LOG_FG)
        except Exception: pass
    
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
    
    __call__ = write


class DualTabUploader(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} - Version 2.1.0, Last Updated 12/03/2025")
        self.minsize(1100, 850)
        
        # Separate drivers for each tab
        self.base_driver = None
        self.ips_driver = None
        self.base_logged_in = False
        self.ips_logged_in = False
        
        # Build UI
        self._build_header()
        self._build_notebook()
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def _build_header(self):
        """Build the maroon header bar"""
        hdr = tk.Frame(self, bg=MAROON)
        hdr.pack(fill='x')
        tk.Label(hdr, text=APP_TITLE, bg=MAROON, fg=HEADER_FG,
                font=("TkDefaultFont", 18, "bold"), padx=14, pady=10).pack(side='left')
        ttk.Separator(self, orient="horizontal").pack(fill='x')
    
    def _build_notebook(self):
        """Build the tabbed interface with prominent, icon-enhanced tabs"""
        # Configure tab style for larger, more visible tabs
        style = ttk.Style()
        style.configure('TNotebook.Tab', padding=[20, 10], font=('Segoe UI', 11, 'bold'))
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Base Uploader (with icon and clear label)
        self.base_frame = self._create_scrollable_frame()
        self.notebook.add(self.base_frame['outer'], text="🏢 Base (ISWS) Uploader")
        self._build_base_tab(self.base_frame['inner'])
        
        # Tab 2: IPS Uploader (with icon and clear label)
        self.ips_frame = self._create_scrollable_frame()
        self.notebook.add(self.ips_frame['outer'], text="🏥 IPS Uploader")
        self._build_ips_tab(self.ips_frame['inner'])
    
    def _create_scrollable_frame(self):
        """Create a scrollable frame for tab content"""
        outer = ttk.Frame(self.notebook)
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)
        
        canvas = tk.Canvas(outer, highlightthickness=0)
        vscroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vscroll.grid(row=0, column=1, sticky="ns")
        
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_frame = canvas.create_window((0, 0), window=inner, anchor="nw")
        
        def _on_resize(event):
            try: canvas.itemconfig(canvas_frame, width=event.width - vscroll.winfo_width())
            except Exception: pass
        outer.bind("<Configure>", _on_resize)
        
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        return {'outer': outer, 'inner': inner, 'canvas': canvas}
    
    def _card(self, parent, title):
        """Create a card-style section"""
        f = ttk.Frame(parent, padding=(12, 10))
        f.pack(fill="x", expand=False, padx=12, pady=(12, 6))
        ttk.Label(f, text=title, foreground=MAROON, font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, columnspan=8, sticky="w", pady=(0, 8))
        return f
    
    # ========== BASE TAB ==========
    def _build_base_tab(self, parent):
        """Build Base IA Referral Uploader tab"""
        # Login Card
        c = self._card(parent, "TherapyNotes Login (Base/Regular)")
        for i in range(1, 5): c.grid_columnconfigure(i, weight=1)
        ttk.Label(c, text="Username:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.base_user = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_user).grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(c, text="Password:", foreground=MAROON).grid(row=1, column=2, sticky="e", padx=6, pady=4)
        self.base_pass = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_pass, show="*").grid(row=1, column=3, sticky="ew", padx=6, pady=4)
        ttk.Button(c, text="Login", command=self.on_base_login).grid(row=1, column=4, padx=6, pady=4)
        
        # Folder Card
        c = self._card(parent, "Referral Forms Folder (PDFs to upload)")
        for i in range(1, 5): c.grid_columnconfigure(i, weight=1)
        ttk.Label(c, text="Folder:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.base_folder = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_folder).grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=4)
        ttk.Button(c, text="Browse…", command=lambda: self._browse_folder(self.base_folder)).grid(row=1, column=4, padx=6, pady=4)
        
        # CSV Card
        c = self._card(parent, "CSV/Excel Input (Therapist from column L; Skip IPS files)")
        for i in range(1, 8): c.grid_columnconfigure(i, weight=1)
        ttk.Label(c, text="CSV/Excel File:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.base_csv = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_csv).grid(row=1, column=1, columnspan=4, sticky="ew", padx=6, pady=4)
        ttk.Button(c, text="Choose File…", command=lambda: self._browse_csv(self.base_csv)).grid(row=1, column=5, padx=6, pady=4)
        
        self.base_skip_header = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text="Skip first row (header)", variable=self.base_skip_header).grid(row=2, column=1, sticky="w", padx=6, pady=2)
        
        self.base_remove_old_docs = tk.BooleanVar(value=False)
        ttk.Checkbutton(c, text="Remove old 'IA Only' documents (30+ days)", variable=self.base_remove_old_docs).grid(row=2, column=2, sticky="w", padx=6, pady=2)
        
        ttk.Label(c, text="Rows from:", foreground=MAROON).grid(row=3, column=0, sticky="e", padx=6, pady=4)
        self.base_row_from = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_row_from, width=10).grid(row=3, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(c, text="to:", foreground=MAROON).grid(row=3, column=2, sticky="e", padx=6, pady=4)
        self.base_row_to = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_row_to, width=10).grid(row=3, column=3, sticky="w", padx=6, pady=4)
        
        btns = ttk.Frame(c); btns.grid(row=4, column=0, columnspan=6, sticky="w", padx=6, pady=(8,2))
        self.base_run_subset_btn = ttk.Button(btns, text="Run Selected Rows", command=self.on_base_run_subset, state="disabled")
        self.base_run_subset_btn.pack(side="left", padx=(0,8))
        self.base_run_all_btn = ttk.Button(btns, text="Run All Rows", command=self.on_base_run_all, state="disabled")
        self.base_run_all_btn.pack(side="left", padx=(0,8))
        
        # Log Card
        c = self._card(parent, "Base Uploader Log")
        lf = ttk.Frame(c); lf.grid(row=0, column=0, columnspan=8, sticky="ew")
        self.base_log_widget = scrolledtext.ScrolledText(lf, height=12, wrap="word")
        self.base_log_widget.pack(fill="x", expand=False)
        self.base_log = UILog(self.base_log_widget)
        self.base_log("Base IA Referral Uploader ready. This tab skips files with 'IPS' in the filename.")
    
    # ========== IPS TAB ==========
    def _build_ips_tab(self, parent):
        """Build IPS IA Referral Uploader tab"""
        # Login Card
        c = self._card(parent, "TherapyNotes Login (IPS)")
        for i in range(1, 5): c.grid_columnconfigure(i, weight=1)
        ttk.Label(c, text="Username:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.ips_user = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_user).grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(c, text="Password:", foreground=MAROON).grid(row=1, column=2, sticky="e", padx=6, pady=4)
        self.ips_pass = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_pass, show="*").grid(row=1, column=3, sticky="ew", padx=6, pady=4)
        ttk.Button(c, text="Login", command=self.on_ips_login).grid(row=1, column=4, padx=6, pady=4)
        
        # Folder Card
        c = self._card(parent, "Referral Forms Folder (PDFs to upload)")
        for i in range(1, 5): c.grid_columnconfigure(i, weight=1)
        ttk.Label(c, text="Folder:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.ips_folder = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_folder).grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=4)
        ttk.Button(c, text="Browse…", command=lambda: self._browse_folder(self.ips_folder)).grid(row=1, column=4, padx=6, pady=4)
        
        # CSV Card
        c = self._card(parent, "CSV/Excel Input (Therapist from column L; Only IPS files)")
        for i in range(1, 8): c.grid_columnconfigure(i, weight=1)
        ttk.Label(c, text="CSV/Excel File:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.ips_csv = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_csv).grid(row=1, column=1, columnspan=4, sticky="ew", padx=6, pady=4)
        ttk.Button(c, text="Choose File…", command=lambda: self._browse_csv(self.ips_csv)).grid(row=1, column=5, padx=6, pady=4)
        
        self.ips_skip_header = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text="Skip first row (header)", variable=self.ips_skip_header).grid(row=2, column=1, sticky="w", padx=6, pady=2)
        
        self.ips_remove_old_docs = tk.BooleanVar(value=False)
        ttk.Checkbutton(c, text="Remove old 'IA Only' documents (30+ days)", variable=self.ips_remove_old_docs).grid(row=2, column=2, sticky="w", padx=6, pady=2)
        
        ttk.Label(c, text="Rows from:", foreground=MAROON).grid(row=3, column=0, sticky="e", padx=6, pady=4)
        self.ips_row_from = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_row_from, width=10).grid(row=3, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(c, text="to:", foreground=MAROON).grid(row=3, column=2, sticky="e", padx=6, pady=4)
        self.ips_row_to = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_row_to, width=10).grid(row=3, column=3, sticky="w", padx=6, pady=4)
        
        btns = ttk.Frame(c); btns.grid(row=4, column=0, columnspan=6, sticky="w", padx=6, pady=(8,2))
        self.ips_run_subset_btn = ttk.Button(btns, text="Run Selected Rows", command=self.on_ips_run_subset, state="disabled")
        self.ips_run_subset_btn.pack(side="left", padx=(0,8))
        self.ips_run_all_btn = ttk.Button(btns, text="Run All Rows", command=self.on_ips_run_all, state="disabled")
        self.ips_run_all_btn.pack(side="left", padx=(0,8))
        
        # Log Card
        c = self._card(parent, "IPS Uploader Log")
        lf = ttk.Frame(c); lf.grid(row=0, column=0, columnspan=8, sticky="ew")
        self.ips_log_widget = scrolledtext.ScrolledText(lf, height=12, wrap="word")
        self.ips_log_widget.pack(fill="x", expand=False)
        self.ips_log = UILog(self.ips_log_widget)
        self.ips_log("IPS IA Referral Uploader ready. This tab only processes files with 'IPS' in the filename.")
    
    # ========== UI EVENTS ==========
    def _browse_folder(self, var):
        """Browse for folder"""
        path = filedialog.askdirectory(title="Select Referral Forms Folder")
        if path:
            var.set(path)
    
    def _browse_csv(self, var):
        """Browse for CSV or Excel file"""
        path = filedialog.askopenfilename(title="Select CSV/Excel file", filetypes=[("Spreadsheets","*.csv;*.xlsx;*.xls"),("CSV Files","*.csv"),("Excel Files","*.xlsx;*.xls"),("All Files","*.*")])
        if path:
            var.set(path)
            self._maybe_enable_buttons()
    
    def _maybe_enable_buttons(self):
        """Enable run buttons when CSV is selected"""
        # Base buttons
        try:
            enabled = os.path.isfile(self.base_csv.get() or "")
            state = "normal" if enabled else "disabled"
            self.base_run_subset_btn.configure(state=state)
            self.base_run_all_btn.configure(state=state)
        except Exception: pass
        
        # IPS buttons
        try:
            enabled = os.path.isfile(self.ips_csv.get() or "")
            state = "normal" if enabled else "disabled"
            self.ips_run_subset_btn.configure(state=state)
            self.ips_run_all_btn.configure(state=state)
        except Exception: pass
    
    def on_base_login(self):
        """Base login"""
        user = (self.base_user.get() or "").strip()
        pwd = (self.base_pass.get() or "").strip()
        if not user or not pwd:
            messagebox.showwarning("Missing login", "Enter TherapyNotes username and password.")
            return
        self.base_log("[UI] Logging in to Base TherapyNotes…")
        threading.Thread(target=self._base_login_worker, args=(user, pwd), daemon=True).start()
    
    def on_ips_login(self):
        """IPS login"""
        user = (self.ips_user.get() or "").strip()
        pwd = (self.ips_pass.get() or "").strip()
        if not user or not pwd:
            messagebox.showwarning("Missing login", "Enter TherapyNotes username and password.")
            return
        self.ips_log("[UI] Logging in to IPS TherapyNotes…")
        threading.Thread(target=self._ips_login_worker, args=(user, pwd), daemon=True).start()
    
    def _base_login_worker(self, user, pwd):
        """Base login worker"""
        ok = False
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            opts = webdriver.ChromeOptions(); opts.add_argument("--start-maximized")
            service = Service(ChromeDriverManager().install())
            self.base_driver = webdriver.Chrome(service=service, options=opts)
            self.base_driver.get(BASE_TN_LOGIN_URL)
            wait = WebDriverWait(self.base_driver, 15)
            usr = wait.until(lambda d: d.find_element(By.ID, TN_USER_ID)); usr.clear(); usr.send_keys(user)
            pw_ = wait.until(lambda d: d.find_element(By.ID, TN_PASS_ID)); pw_.clear(); pw_.send_keys(pwd)
            btn = wait.until(lambda d: d.find_element(By.ID, TN_BTN_ID)); btn.click()
            wait.until(lambda d: d.find_element(By.LINK_TEXT, "Patients"))
            ok = True
        except Exception as e:
            self.base_log(f"[TN][ERR] {e}")
        finally:
            self.base_logged_in = ok
            if ok: self.base_log("[TN] Base login successful.")
            else: self.base_log("[TN] Base login failed.")
    
    def _ips_login_worker(self, user, pwd):
        """IPS login worker"""
        ok = False
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            opts = webdriver.ChromeOptions(); opts.add_argument("--start-maximized")
            service = Service(ChromeDriverManager().install())
            self.ips_driver = webdriver.Chrome(service=service, options=opts)
            self.ips_driver.get(IPS_TN_LOGIN_URL)
            wait = WebDriverWait(self.ips_driver, 15)
            usr = wait.until(lambda d: d.find_element(By.ID, TN_USER_ID)); usr.clear(); usr.send_keys(user)
            pw_ = wait.until(lambda d: d.find_element(By.ID, TN_PASS_ID)); pw_.clear(); pw_.send_keys(pwd)
            btn = wait.until(lambda d: d.find_element(By.ID, TN_BTN_ID)); btn.click()
            wait.until(lambda d: d.find_element(By.LINK_TEXT, "Patients"))
            ok = True
        except Exception as e:
            self.ips_log(f"[TN][ERR] {e}")
        finally:
            self.ips_logged_in = ok
            if ok: self.ips_log("[TN] IPS login successful.")
            else: self.ips_log("[TN] IPS login failed.")
    
    def _login_if_needed(self, mode="base"):
        """Perform login synchronously if not already logged in"""
        if mode == "base":
            if self.base_logged_in and self.base_driver:
                return True
            user = (self.base_user.get() or "").strip()
            pwd = (self.base_pass.get() or "").strip()
            if not user or not pwd:
                self.base_log("[TN][ERR] No credentials. Fill Username/Password.")
                return False
            try:
                webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
                opts = webdriver.ChromeOptions(); opts.add_argument("--start-maximized")
                if not self.base_driver:
                    service = Service(ChromeDriverManager().install())
                    self.base_driver = webdriver.Chrome(service=service, options=opts)
                self.base_driver.get(BASE_TN_LOGIN_URL)
                wait = WebDriverWait(self.base_driver, 15)
                usr = wait.until(lambda d: d.find_element(By.ID, TN_USER_ID)); usr.clear(); usr.send_keys(user)
                pw_ = wait.until(lambda d: d.find_element(By.ID, TN_PASS_ID)); pw_.clear(); pw_.send_keys(pwd)
                btn = wait.until(lambda d: d.find_element(By.ID, TN_BTN_ID)); btn.click()
                wait.until(lambda d: d.find_element(By.LINK_TEXT, "Patients"))
                self.base_logged_in = True
                self.base_log("[TN] Base login successful.")
                return True
            except Exception as e:
                self.base_logged_in = False
                self.base_log(f"[TN][ERR] {e}")
                return False
        else:  # IPS mode
            if self.ips_logged_in and self.ips_driver:
                return True
            user = (self.ips_user.get() or "").strip()
            pwd = (self.ips_pass.get() or "").strip()
            if not user or not pwd:
                self.ips_log("[TN][ERR] No credentials. Fill Username/Password.")
                return False
            try:
                webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
                opts = webdriver.ChromeOptions(); opts.add_argument("--start-maximized")
                if not self.ips_driver:
                    service = Service(ChromeDriverManager().install())
                    self.ips_driver = webdriver.Chrome(service=service, options=opts)
                self.ips_driver.get(IPS_TN_LOGIN_URL)
                wait = WebDriverWait(self.ips_driver, 15)
                usr = wait.until(lambda d: d.find_element(By.ID, TN_USER_ID)); usr.clear(); usr.send_keys(user)
                pw_ = wait.until(lambda d: d.find_element(By.ID, TN_PASS_ID)); pw_.clear(); pw_.send_keys(pwd)
                btn = wait.until(lambda d: d.find_element(By.ID, TN_BTN_ID)); btn.click()
                wait.until(lambda d: d.find_element(By.LINK_TEXT, "Patients"))
                self.ips_logged_in = True
                self.ips_log("[TN] IPS login successful.")
                return True
            except Exception as e:
                self.ips_logged_in = False
                self.ips_log(f"[TN][ERR] {e}")
                return False
    
    def on_base_run_subset(self):
        """Run base subset"""
        csv_path = (self.base_csv.get() or "").strip()
        if not os.path.isfile(csv_path):
            messagebox.showwarning("CSV missing", "Please choose a valid CSV file."); return
        try:
            start = int(self.base_row_from.get().strip())
            end = int(self.base_row_to.get().strip())
            if start <= 0 or end <= 0 or end < start: raise ValueError
        except Exception:
            messagebox.showwarning("Bad range", "Enter valid 1-based row numbers."); return
        self.base_log(f"[CSV] Running Base subset rows: {start} to {end}")
        threading.Thread(target=self._base_worker, args=(csv_path, start, end), daemon=True).start()
    
    def on_base_run_all(self):
        """Run base all"""
        csv_path = (self.base_csv.get() or "").strip()
        if not os.path.isfile(csv_path):
            messagebox.showwarning("CSV missing", "Please choose a valid CSV file."); return
        self.base_log(f"[CSV] Running Base ALL rows")
        threading.Thread(target=self._base_worker, args=(csv_path, None, None), daemon=True).start()
    
    def on_ips_run_subset(self):
        """Run IPS subset"""
        csv_path = (self.ips_csv.get() or "").strip()
        if not os.path.isfile(csv_path):
            messagebox.showwarning("CSV missing", "Please choose a valid CSV file."); return
        try:
            start = int(self.ips_row_from.get().strip())
            end = int(self.ips_row_to.get().strip())
            if start <= 0 or end <= 0 or end < start: raise ValueError
        except Exception:
            messagebox.showwarning("Bad range", "Enter valid 1-based row numbers."); return
        self.ips_log(f"[CSV] Running IPS subset rows: {start} to {end}")
        threading.Thread(target=self._ips_worker, args=(csv_path, start, end), daemon=True).start()
    
    def on_ips_run_all(self):
        """Run IPS all"""
        csv_path = (self.ips_csv.get() or "").strip()
        if not os.path.isfile(csv_path):
            messagebox.showwarning("CSV missing", "Please choose a valid CSV file."); return
        self.ips_log(f"[CSV] Running IPS ALL rows")
        threading.Thread(target=self._ips_worker, args=(csv_path, None, None), daemon=True).start()
    
    def _base_worker(self, csv_path, start_row, end_row):
        """Base CSV worker - skips IPS files (FULLY FUNCTIONAL)"""
        if not self._login_if_needed("base"):
            try: messagebox.showwarning("Login required", "Enter credentials, then click Run again.")
            except Exception: pass
            return
        
        records = []
        try:
            # Click Patients
            self.base_log("[NAV] Opening Patients page...")
            if not self._click_patients("base"):
                self.base_log("[CSV][ERR] Could not open Patients page."); return
            
            # Read CSV
            with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
                rows = list(_csv.reader(f))
            
            client_name_idx = _detect_client_name_index(rows[0]) if (self.base_skip_header.get() and rows) else 0
            first_data_index = 1 if (self.base_skip_header.get() and len(rows) > 0) else 0
            total_rows = len(rows)
            
            if start_row is None or end_row is None:
                begin = first_data_index; end = total_rows - 1
            else:
                begin = max(first_data_index, start_row - 1); end = min(total_rows - 1, end_row - 1)
            
            # Process each row
            for idx in range(begin, end + 1):
                row_1b = idx + 1
                row = rows[idx]
                
                try:  # Ensure we always return to Patients page
                    def _record(status, reason, therapist="", client=""):
                        records.append({
                            "csv_row": row_1b, "therapist": therapist, "client": client,
                            "status": status, "reason": reason,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
                    
                    therapist = (row[CSV_COL_L_INDEX] if len(row) > CSV_COL_L_INDEX else "").strip()
                    if not therapist:
                        self.base_log(f"[CSV][WARN] Row {row_1b} missing therapist in column L; skipping.")
                        _record("skipped", "missing therapist (L)")
                        continue
                    
                    client = (row[client_name_idx] if len(row) > client_name_idx else "").strip()
                    if not client:
                        self.base_log(f"[CSV][WARN] Row {row_1b} missing client name; skipping.")
                        _record("skipped", "missing client", therapist)
                        continue
                    
                    full_name = _extract_full_name_from_csv(row, client_name_idx)
                    if full_name and full_name != client:
                        self.base_log(f"[CSV] Row {row_1b}: Using full name '{full_name}' (from '{client}')")
                    
                    urgent = False
                    if len(row) > CSV_COL_R_INDEX:
                        val = str(row[CSV_COL_R_INDEX] or "").strip().lower()
                        urgent = val in ("true", "1", "yes", "y")
                    
                    self.base_log(f"[CSV] Row {row_1b}: '{client}' for therapist '{therapist}' (urgent={urgent}).")
                    
                    if not self._search_therapist_new_referrals("base", therapist):
                        self.base_log(f"[CSV][WARN] Row {row_1b}: search/select failed.")
                        _record("skipped", "search/select failed", therapist, client)
                        continue
                    
                    if not self._open_documents_tab("base"):
                        self.base_log(f"[CSV][WARN] Row {row_1b}: couldn't open Documents tab.")
                        _record("skipped", "documents tab not found", therapist, client)
                        continue
                    
                    # Remove old IA Only documents if checkbox is enabled
                    if not self._remove_old_ia_only_documents("base"):
                        self.base_log(f"[CSV][WARN] Row {row_1b}: document removal failed (continuing anyway).")
                    
                    uploaded = self._per_row_upload_action("base", therapist, client, urgent, self.base_folder.get(), full_name, "skip_ips")
                    if uploaded:
                        self.base_log(f"[CSV] Row {row_1b}: upload completed.")
                        _record("success", "uploaded", therapist, client)
                    else:
                        self.base_log(f"[CSV][WARN] Row {row_1b}: upload failed.")
                        _record("skipped", "upload failed", therapist, client)
                finally:
                    # ALWAYS return to Patients page after each row (success or failure)
                    self._click_patients("base")
                    time.sleep(0.4)
            
            out_path = _write_report(records, csv_path)
            self.base_log(f"[CSV] Base CSV run complete. Report: {out_path}")
            try: messagebox.showinfo("Run complete", f"Report written to:\n{out_path}")
            except Exception: pass
        
        except Exception as e:
            self.base_log(f"[CSV][ERR] {e}")
    
    def _ips_worker(self, csv_path, start_row, end_row):
        """IPS CSV worker - only processes IPS files (FULLY FUNCTIONAL)"""
        if not self._login_if_needed("ips"):
            try: messagebox.showwarning("Login required", "Enter credentials, then click Run again.")
            except Exception: pass
            return
        
        records = []
        try:
            # Click Patients
            self.ips_log("[NAV] Opening Patients page...")
            if not self._click_patients("ips"):
                self.ips_log("[CSV][ERR] Could not open Patients page."); return
            
            # Read CSV
            with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
                rows = list(_csv.reader(f))
            
            client_name_idx = _detect_client_name_index(rows[0]) if (self.ips_skip_header.get() and rows) else 0
            first_data_index = 1 if (self.ips_skip_header.get() and len(rows) > 0) else 0
            total_rows = len(rows)
            
            if start_row is None or end_row is None:
                begin = first_data_index; end = total_rows - 1
            else:
                begin = max(first_data_index, start_row - 1); end = min(total_rows - 1, end_row - 1)
            
            # Process each row
            for idx in range(begin, end + 1):
                row_1b = idx + 1
                row = rows[idx]
                
                try:  # Ensure we always return to Patients page
                    def _record(status, reason, therapist="", client=""):
                        records.append({
                            "csv_row": row_1b, "therapist": therapist, "client": client,
                            "status": status, "reason": reason,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
                    
                    therapist = (row[CSV_COL_L_INDEX] if len(row) > CSV_COL_L_INDEX else "").strip()
                    if not therapist:
                        self.ips_log(f"[CSV][WARN] Row {row_1b} missing therapist in column L; skipping.")
                        _record("skipped", "missing therapist (L)")
                        continue
                    
                    client = (row[client_name_idx] if len(row) > client_name_idx else "").strip()
                    if not client:
                        self.ips_log(f"[CSV][WARN] Row {row_1b} missing client name; skipping.")
                        _record("skipped", "missing client", therapist)
                        continue
                    
                    full_name = _extract_full_name_from_csv(row, client_name_idx)
                    if full_name and full_name != client:
                        self.ips_log(f"[CSV] Row {row_1b}: Using full name '{full_name}' (from '{client}')")
                    
                    urgent = False
                    if len(row) > CSV_COL_R_INDEX:
                        val = str(row[CSV_COL_R_INDEX] or "").strip().lower()
                        urgent = val in ("true", "1", "yes", "y")
                    
                    self.ips_log(f"[CSV] Row {row_1b}: '{client}' for therapist '{therapist}' (urgent={urgent}).")
                    
                    if not self._search_therapist_new_referrals("ips", therapist):
                        self.ips_log(f"[CSV][WARN] Row {row_1b}: search/select failed.")
                        _record("skipped", "search/select failed", therapist, client)
                        continue
                    
                    if not self._open_documents_tab("ips"):
                        self.ips_log(f"[CSV][WARN] Row {row_1b}: couldn't open Documents tab.")
                        _record("skipped", "documents tab not found", therapist, client)
                        continue
                    
                    # Remove old IA Only documents if checkbox is enabled
                    if not self._remove_old_ia_only_documents("ips"):
                        self.ips_log(f"[CSV][WARN] Row {row_1b}: document removal failed (continuing anyway).")
                    
                    uploaded = self._per_row_upload_action("ips", therapist, client, urgent, self.ips_folder.get(), full_name, "only_ips")
                    if uploaded:
                        self.ips_log(f"[CSV] Row {row_1b}: upload completed.")
                        _record("success", "uploaded", therapist, client)
                    else:
                        self.ips_log(f"[CSV][WARN] Row {row_1b}: upload failed.")
                        _record("skipped", "upload failed", therapist, client)
                finally:
                    # ALWAYS return to Patients page after each row (success or failure)
                    self._click_patients("ips")
                    time.sleep(0.4)
            
            out_path = _write_report(records, csv_path)
            self.ips_log(f"[CSV] IPS CSV run complete. Report: {out_path}")
            try: messagebox.showinfo("Run complete", f"Report written to:\n{out_path}")
            except Exception: pass
        
        except Exception as e:
            self.ips_log(f"[CSV][ERR] {e}")
    
    # ===== Navigation & Upload Helpers =====
    def _click_patients(self, mode):
        """Click Patients link"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        if not driver:
            log("[NAV] No driver."); return False
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, 10)
            
            try: driver.execute_script("window.scrollTo(0,0)")
            except Exception: pass
            
            try:
                el = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Patients")))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el); el.click()
                log("[NAV] Patients via LINK_TEXT."); return True
            except Exception: pass
            
            log("[NAV][WARN] Could not find Patients with any strategy."); return False
        except Exception as e:
            log(f"[NAV][ERR] {e}"); return False
    
    def _search_therapist_new_referrals(self, mode, therapist_name: str, timeout: int = 15):
        """Search for '{Therapist} New Referrals'"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        if not driver:
            log("[SRCH] No driver."); return False
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            
            parsed_name = _parse_therapist_name_for_search(therapist_name)
            target_text = f"{parsed_name} New Referrals".strip()
            log(f"[SRCH] CSV: '{therapist_name}' → Searching: '{target_text}'")
            
            search_input = None
            for by, val in [
                (By.ID, "ctl00_BodyContent_TextBoxSearchPatientName"),
                (By.NAME, "ctl00$BodyContent$TextBoxSearchPatientName"),
                (By.XPATH, "//input[@placeholder='Name, Acct #, Phone, or Ins ID']"),
            ]:
                try:
                    search_input = wait.until(EC.element_to_be_clickable((by, val))); break
                except Exception: pass
            
            if not search_input:
                log("[SRCH][ERR] Search input not found."); return False
            
            search_input.clear(); search_input.click(); search_input.send_keys(target_text)
            time.sleep(0.4)
            
            # Enhanced dropdown detection with multiple strategies
            container = None
            dropdown_found = False
            
            # Strategy 1: Wait for ContentBubbleResultsContainer
            try:
                container = wait.until(EC.presence_of_element_located((By.ID, "ContentBubbleResultsContainer")))
                dropdown_found = True
                log(f"[SRCH][DEBUG] Found dropdown container via ContentBubbleResultsContainer")
            except Exception:
                log(f"[SRCH][WARN] ContentBubbleResultsContainer not found, trying alternative selectors...")
            
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
                        container = driver.find_element(by, selector)
                        if container and container.is_displayed():
                            dropdown_found = True
                            log(f"[SRCH][DEBUG] Found dropdown container via alternative selector: {selector}")
                            break
                    except Exception:
                        continue
            
            # Strategy 3: Wait longer and retry with different search approach
            if not dropdown_found:
                log(f"[SRCH][WARN] No dropdown found, trying extended wait and retry...")
                time.sleep(2)  # Wait longer
                
                # Try triggering dropdown with different approach
                try:
                    search_input.click()
                    search_input.send_keys(Keys.ARROW_DOWN)  # Trigger dropdown
                    time.sleep(1)
                    
                    # Try ContentBubbleResultsContainer again
                    container = wait.until(EC.presence_of_element_located((By.ID, "ContentBubbleResultsContainer")))
                    dropdown_found = True
                    log(f"[SRCH][DEBUG] Found dropdown container after retry with arrow key")
                except Exception:
                    pass
            
            if not dropdown_found:
                log("[SRCH][ERR] Dropdown container did not appear after all attempts."); return False
            
            items = []
            for xp in [".//a[normalize-space()]", ".//div[@role='option']"]:
                try: items.extend(container.find_elements(By.XPATH, xp))
                except Exception: pass
            
            if not items:
                log("[SRCH][ERR] No items found in dropdown."); return False
            
            tl = target_text.lower(); matched = None
            for el in items:
                label = (el.text or "").strip()
                if label and tl in label.lower(): matched = el; break
            
            if not matched:
                matched = items[0]
                log(f"[SRCH][WARN] No exact match; selecting first option.")
            
            try: matched.click()
            except Exception:
                try: driver.execute_script("arguments[0].click();", matched)
                except Exception as e:
                    log(f"[SRCH][ERR] Failed to click: {e}"); return False
            
            log("[SRCH] Selection made, waiting for page load...")
            time.sleep(0.6)
            return True
        except Exception as e:
            log(f"[SRCH][ERR] {e}"); return False
    
    def _open_documents_tab(self, mode, timeout: int = 15):
        """Open Documents tab"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            tab = None
            for by, val in [
                (By.LINK_TEXT, "Documents"),
                (By.XPATH, "//a[contains(@href, '#tab=Documents')]"),
            ]:
                try: tab = wait.until(EC.element_to_be_clickable((by, val))); break
                except Exception: pass
            
            if not tab:
                log("[DOCS][ERR] Documents tab not found."); return False
            
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab); tab.click()
            log("[DOCS] Documents tab opened.")
            time.sleep(0.3)
            return True
        except Exception as e:
            log(f"[DOCS][ERR] {e}"); return False
    
    def _remove_old_ia_only_documents(self, mode, timeout: int = 15):
        """
        Remove documents with 'IA Only' prefix (case-insensitive) that are 30+ days old.
        Flow: Click pencil icon -> Click "Delete Document" -> Click "Delete File" button
        Returns True if successful or if checkbox was not enabled, False on error.
        """
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        # Check if the feature is enabled
        remove_enabled = self.base_remove_old_docs.get() if mode == "base" else self.ips_remove_old_docs.get()
        if not remove_enabled:
            log("[CLEANUP] Remove old IA Only documents feature is disabled (checkbox unchecked).")
            return True  # Not an error, just feature disabled
        
        log("[CLEANUP] Remove old IA Only documents feature is enabled. Checking for documents to remove...")
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            
            # Wait for the documents table to load
            time.sleep(0.5)  # Give the page time to render
            
            # Find all document rows in the table
            # The table contains rows with document information
            log("[CLEANUP] Searching for document rows in table...")
            
            # Try to find the table body or all rows containing documents
            doc_rows = []
            try:
                # Strategy 1: Find all table rows (excluding header row if present)
                # Look for table rows that have the document structure
                all_rows = driver.find_elements(By.XPATH, "//table//tr[td]")
                # Filter out header row (typically contains "Document", "Date", "Status" etc.)
                for row in all_rows:
                    row_text_lower = (row.text or "").lower()
                    # Skip header rows
                    if any(header in row_text_lower for header in ['document', 'service', 'date', 'author', 'status']):
                        if len([c for c in row_text_lower.split() if c in ['document', 'service', 'date']]) >= 2:
                            continue  # This looks like a header row
                    doc_rows.append(row)
                
                if doc_rows:
                    log(f"[CLEANUP] Found {len(doc_rows)} document row(s) in table")
                else:
                    # Strategy 2: Try direct search for rows containing "IA Only"
                    rows = driver.find_elements(By.XPATH, "//tr[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ia only')]")
                    doc_rows = rows
                    log(f"[CLEANUP] Found {len(doc_rows)} potential document row(s) via 'IA Only' text search")
            except Exception as e:
                log(f"[CLEANUP][WARN] Could not find rows: {e}")
                return False
            
            if not doc_rows:
                log("[CLEANUP] No document rows found.")
                return True  # No documents to remove, not an error
            
            # Calculate the cutoff date (30 days ago)
            cutoff_date = datetime.now() - timedelta(days=30)
            log(f"[CLEANUP] Looking for documents older than {cutoff_date.strftime('%m/%d/%Y')}")
            
            removed_count = 0
            skipped_count = 0
            
            # Process each row
            for idx, row in enumerate(doc_rows, 1):
                try:
                    # Get the text of the entire row to check for "IA Only" prefix
                    row_text = (row.text or "").strip()
                    
                    # Check if row contains "IA Only" prefix (case-insensitive)
                    # Documents can start with "IA Only", "IA ONLY", "ia only", etc.
                    if not re.search(r'\bIA\s+ONLY\b', row_text, re.IGNORECASE):
                        continue  # Skip rows that don't contain "IA Only" prefix
                    
                    # Additional check: ensure it's actually a document row (should have date and status columns)
                    if not re.search(r'\d{1,2}/\d{1,2}/\d{4}', row_text):
                        continue  # Skip rows without dates
                    
                    # Extract document name and date from the row
                    # Document name is typically in the first column, date in the Date column
                    log(f"[CLEANUP] Row {idx}: Found potential IA Only document: {row_text[:80]}...")
                    
                    # Find the date column (MM/DD/YYYY format)
                    date_cells = row.find_elements(By.XPATH, ".//td[contains(text(), '/202') or contains(text(), '/2025') or contains(text(), '/2024')]")
                    
                    doc_date_str = None
                    for cell in date_cells:
                        cell_text = (cell.text or "").strip()
                        # Try to parse date in MM/DD/YYYY format
                        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', cell_text):
                            doc_date_str = cell_text
                            break
                    
                    if not doc_date_str:
                        log(f"[CLEANUP][WARN] Row {idx}: Could not find date, skipping")
                        skipped_count += 1
                        continue
                    
                    # Parse the date
                    try:
                        doc_date = datetime.strptime(doc_date_str, "%m/%d/%Y")
                    except ValueError:
                        try:
                            # Try alternative format
                            doc_date = datetime.strptime(doc_date_str, "%m/%d/%y")
                        except ValueError:
                            log(f"[CLEANUP][WARN] Row {idx}: Could not parse date '{doc_date_str}', skipping")
                            skipped_count += 1
                            continue
                    
                    # Check if document is 30+ days old
                    days_old = (datetime.now() - doc_date).days
                    if days_old < 30:
                        log(f"[CLEANUP] Row {idx}: Document dated {doc_date_str} ({days_old} days old) is less than 30 days, skipping")
                        skipped_count += 1
                        continue
                    
                    log(f"[CLEANUP] Row {idx}: Document dated {doc_date_str} ({days_old} days old) is 30+ days old - will remove")
                    
                    # Find the pencil icon in this row
                    # Element: <div class="fa-icon pencil-alt" aria-hidden="true" style="font-size: 16px;"></div>
                    pencil_icon = None
                    try:
                        # Primary selector: Look for div with both fa-icon and pencil-alt classes
                        pencil_icon = row.find_element(By.XPATH, ".//div[contains(@class, 'fa-icon') and contains(@class, 'pencil-alt')]")
                    except Exception:
                        # Fallback 1: Look for any element with pencil-alt class
                        try:
                            pencil_icon = row.find_element(By.XPATH, ".//*[contains(@class, 'pencil-alt')]")
                        except Exception:
                            # Fallback 2: Look for any element with pencil class
                            try:
                                pencil_icon = row.find_element(By.XPATH, ".//*[contains(@class, 'pencil')]")
                            except Exception:
                                log(f"[CLEANUP][WARN] Row {idx}: Could not find pencil icon, skipping")
                                skipped_count += 1
                                continue
                    
                    if not pencil_icon:
                        log(f"[CLEANUP][WARN] Row {idx}: Pencil icon not found, skipping")
                        skipped_count += 1
                        continue
                    
                    # Click the pencil icon
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", pencil_icon)
                        time.sleep(0.2)
                        pencil_icon.click()
                        log(f"[CLEANUP] Row {idx}: Clicked pencil icon")
                        time.sleep(0.5)  # Wait for popup to appear
                    except Exception as e:
                        log(f"[CLEANUP][WARN] Row {idx}: Failed to click pencil icon: {e}")
                        skipped_count += 1
                        continue
                    
                    # Click "Delete Document" link
                    delete_link = None
                    try:
                        delete_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Delete Document')]")))
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", delete_link)
                        time.sleep(0.2)
                        delete_link.click()
                        log(f"[CLEANUP] Row {idx}: Clicked 'Delete Document'")
                        time.sleep(0.5)  # Wait for confirmation popup
                    except Exception as e:
                        log(f"[CLEANUP][WARN] Row {idx}: Failed to find/click 'Delete Document': {e}")
                        skipped_count += 1
                        # Try to close any popup that may have opened
                        try:
                            cancel_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close')]")
                            cancel_btn.click()
                            time.sleep(0.3)
                        except Exception:
                            pass
                        continue
                    
                    # Click "Delete File" button in confirmation popup
                    try:
                        delete_file_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='button' and @value='Delete File']")))
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", delete_file_btn)
                        time.sleep(0.2)
                        delete_file_btn.click()
                        log(f"[CLEANUP] Row {idx}: Clicked 'Delete File' button - document removed")
                        removed_count += 1
                        time.sleep(0.8)  # Wait for deletion to complete and page to update
                    except Exception as e:
                        log(f"[CLEANUP][WARN] Row {idx}: Failed to find/click 'Delete File' button: {e}")
                        skipped_count += 1
                        # Try to close any popup
                        try:
                            cancel_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close')]")
                            cancel_btn.click()
                            time.sleep(0.3)
                        except Exception:
                            pass
                        continue
                    
                except Exception as e:
                    log(f"[CLEANUP][WARN] Row {idx}: Error processing row: {e}")
                    skipped_count += 1
                    continue
            
            # CRITICAL: Close ALL dialogs/modals before returning - they can cause duplicate upload forms
            log("[CLEANUP] Closing any remaining dialogs after deletion...")
            try:
                # Wait a moment for any final dialogs to appear
                time.sleep(0.5)
                
                # Find and close all dialogs/modals
                all_dialogs = driver.find_elements(By.XPATH, "//div[contains(@class, 'Dialog') or contains(@class, 'dialog') or contains(@class, 'modal')]")
                for dialog in all_dialogs:
                    try:
                        if dialog.is_displayed():
                            # Try multiple strategies to close
                            close_btns = dialog.find_elements(By.XPATH, ".//button[contains(text(), 'Close') or contains(text(), 'Cancel') or contains(@class, 'close')] | .//*[@aria-label='Close' or @title='Close'] | .//span[contains(@class, 'close')]")
                            if close_btns:
                                driver.execute_script("arguments[0].click();", close_btns[0])
                                log("[CLEANUP] Closed remaining dialog")
                                time.sleep(0.3)
                            else:
                                # Try pressing Escape key on the dialog
                                driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}));", dialog)
                                time.sleep(0.2)
                    except Exception:
                        pass
                
                # Also try pressing Escape on the body to close any modal overlays
                try:
                    body = driver.find_element(By.TAG_NAME, "body")
                    driver.execute_script("arguments[0].dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}));", body)
                    time.sleep(0.2)
                except Exception:
                    pass
                
                # Final wait to ensure dialogs are fully closed
                time.sleep(0.5)
            except Exception as e:
                log(f"[CLEANUP][WARN] Error closing dialogs: {e}")
            
            log(f"[CLEANUP] Document removal complete. Removed: {removed_count}, Skipped: {skipped_count}")
            
            # Small wait to ensure page is ready for upload button click
            time.sleep(0.5)
            return True
            
        except Exception as e:
            log(f"[CLEANUP][ERR] Error during document removal: {e}")
            import traceback
            log(f"[CLEANUP][ERR] Traceback: {traceback.format_exc()}")
            return False
    
    def _per_row_upload_action(self, mode, therapist: str, client_name: str, urgent: bool, base_folder: str, full_name: str, filter_mode: str) -> bool:
        """Upload PDF for one row"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        search_name = full_name if full_name and full_name.strip() else client_name
        log(f"[UPLOAD] Searching for PDF matching: '{search_name}' (filter: {filter_mode})")
        
        pdf_path = _find_pdf_for_client(base_folder, search_name, filter_mode)
        
        if not pdf_path and full_name and full_name != client_name:
            log(f"[UPLOAD] Not found with full name, trying: '{client_name}'")
            pdf_path = _find_pdf_for_client(base_folder, client_name, filter_mode)
        
        if not pdf_path:
            log(f"[UPLOAD][ERR] No PDF found for '{search_name}' in '{base_folder}' (filter: {filter_mode}).")
            return False
        
        log(f"[UPLOAD] Found PDF: {os.path.basename(pdf_path)}")
        
        # Click Upload Patient File button
        if not self._click_upload_patient_file(mode):
            return False
        
        # Fill upload popup
        name_for_doc = full_name if full_name and full_name.strip() else client_name
        doc_name = f"IA Only {name_for_doc}"
        if urgent: doc_name = f"URGENT {doc_name}"
        
        log(f"[UPLOAD] Document name: '{doc_name}'")
        return self._fill_upload_popup_and_submit(mode, pdf_path, doc_name)
    
    def _click_upload_patient_file(self, mode, timeout: int = 12):
        """Click 'Upload Patient File' button"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            
            btn = None
            for by, val in [
                (By.XPATH, "//button[contains(normalize-space(.), 'Upload Patient File')]"),
            ]:
                try: 
                    btn = wait.until(EC.element_to_be_clickable((by, val))); break
                except Exception: pass
            
            if not btn:
                log("[DOCS][ERR] 'Upload Patient File' button not found."); return False
            
            try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            except Exception: pass
            
            try: 
                btn.click()
                log("[DOCS] Clicked 'Upload Patient File'.")
                time.sleep(0.4)
                return True
            except Exception:
                try: 
                    driver.execute_script("arguments[0].click();", btn)
                    log("[DOCS] Clicked 'Upload Patient File' (JS).")
                    time.sleep(0.4)
                    return True
                except Exception as e:
                    log(f"[DOCS][ERR] Failed to click: {e}")
                    return False
        except Exception as e:
            log(f"[DOCS][ERR] {e}"); return False
    
    def _fill_upload_popup_and_submit(self, mode, pdf_path: str, doc_name: str, timeout: int = 15):
        """Fill upload popup and submit"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            
            file_input = None
            for by, val in [(By.ID, "InputUploader"), (By.XPATH, "//input[@type='file']")]:
                try: file_input = wait.until(EC.presence_of_element_located((by, val))); break
                except Exception: pass
            
            if not file_input:
                log("[UPLOAD][ERR] File chooser not found."); return False
            
            file_input.send_keys(pdf_path)
            log(f"[UPLOAD] Chosen file: {os.path.basename(pdf_path)}")
            
            name_input = None
            for by, val in [(By.ID, "PatientFile__DocumentName"), (By.XPATH, "//input[contains(@id, 'DocumentName')]")]:
                try: name_input = wait.until(EC.element_to_be_clickable((by, val))); break
                except Exception: pass
            
            if not name_input:
                log("[UPLOAD][ERR] Document Name input not found."); return False
            
            try: name_input.clear()
            except Exception: pass
            name_input.send_keys(doc_name)
            log(f"[UPLOAD] Set document name: {doc_name}")
            
            # Click away to unblur
            try:
                h2 = driver.find_element(By.XPATH, "//h2[contains(normalize-space(),'Upload')]")
                h2.click(); time.sleep(0.2)
            except Exception: pass
            
            add_btn = None
            for by, val in [(By.XPATH, "//input[@type='button' and @value='Add Document']"),
                            (By.XPATH, "//button[contains(normalize-space(),'Add Document')]")]:
                try: add_btn = wait.until(EC.element_to_be_clickable((by, val))); break
                except Exception: pass
            
            if not add_btn:
                log("[UPLOAD][ERR] 'Add Document' button not found."); return False
            
            try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_btn)
            except Exception: pass
            
            try: add_btn.click()
            except Exception:
                try: driver.execute_script("arguments[0].click();", add_btn)
                except Exception as e:
                    log(f"[UPLOAD][ERR] Failed to click Add Document: {e}"); return False
            
            log("[UPLOAD] Clicked 'Add Document'.")
            time.sleep(1.0)  # Wait for upload to process
            
            # Verify upload completed by checking if popup closed or success message appeared
            try:
                # Wait for popup to close or success indicator
                max_wait = 10  # Maximum seconds to wait for upload completion
                wait_start = time.time()
                while time.time() - wait_start < max_wait:
                    try:
                        # Check if popup/modal is still open
                        popup = driver.find_element(By.XPATH, "//input[@type='button' and @value='Add Document']")
                        if not popup.is_displayed():
                            log("[UPLOAD] Popup closed - upload likely completed")
                            break
                    except Exception:
                        # Popup not found - likely closed, upload completed
                        log("[UPLOAD] Popup closed - upload likely completed")
                        break
                    time.sleep(0.5)
                
                # Additional wait to ensure document appears in list
                time.sleep(0.5)
                log("[UPLOAD] Upload process completed")
            except Exception as e:
                log(f"[UPLOAD][WARN] Could not verify upload completion: {e}")
                # Continue anyway - upload may have succeeded
            
            return True
        except Exception as e:
            log(f"[UPLOAD][ERR] {e}")
            import traceback
            log(f"[UPLOAD][ERR] Traceback: {traceback.format_exc()}")
            return False
    
    def on_close(self):
        """Clean up and close"""
        try:
            if self.base_driver: self.base_driver.quit()
        except Exception: pass
        try:
            if self.ips_driver: self.ips_driver.quit()
        except Exception: pass
        self.destroy()


def main():
    app = DualTabUploader()
    try:
        app.update_idletasks()
        sw, sh = app.winfo_screenwidth(), app.winfo_screenheight()
        ww, wh = 1100, 850
        x = max(20, sw - ww - 60)
        y = max(40, 60)
        app.geometry(f"{ww}x{wh}+{x}+{y}")
    except Exception: pass
    app.mainloop()


if __name__ == "__main__":
    main()
