#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Existing Client Referral Form Uploader - Dual Tab Version
Tab 1: Base Existing Client Referral form uploader (regular therapy notes)
Tab 2: IPS Existing Client Referral form uploader (IPS therapy notes)

This uploader processes referral form PDFs and uploads them to TherapyNotes,
filtering files based on whether the counselor has IPS in column L of the Excel.
"""

import os, sys, time, threading, tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime, timedelta
from pathlib import Path
import csv as _csv
import re
import argparse
import json

# Try to import pandas for Excel file support
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

APP_TITLE = "Existing Client Referral Form Uploader - Dual Tab"
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


def _is_ips_counselor(therapist_name: str) -> bool:
    """
    Check if counselor is IPS based on column L value.
    Returns True if "IPS" appears in the therapist name (case insensitive).
    """
    if not therapist_name:
        return False
    return "ips" in therapist_name.lower()


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


def _find_pdf_for_client(base_folder: str, client_name: str, is_ips_counselor: bool):
    """
    Find PDF for client with improved matching logic.
    Searches for files matching the client name, with optional prefix filtering.
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
            
            filename_lower = fn.lower()
            
            # Apply IPS filtering: If counselor is NOT IPS, exclude files with "ips" prefix
            # This allows flexibility - files can have any prefix or no prefix, as long as they match the client name
            if not is_ips_counselor:
                # For non-IPS counselors, skip files that explicitly have "ips" in the name
                # (to avoid uploading IPS-specific files to non-IPS counselors)
                if "ips" in filename_lower and ("reassignment" in filename_lower or "referral" in filename_lower):
                    continue
            
            # Extract base filename without extension for matching
            name_norm = re.sub(r"[\s_]+", " ", os.path.splitext(fn)[0].lower())
            
            # Remove common prefixes for matching (but don't require them)
            # This allows files with or without these prefixes to be found
            prefixes_to_remove = [
                "ips reassignment",
                "reassignment",
                "ips referral",
                "referral",
                "referral form",
                "ips referral form"
            ]
            for prefix in prefixes_to_remove:
                if name_norm.startswith(prefix):
                    name_norm = name_norm[len(prefix):].strip()
                    break  # Only remove one prefix
            
            # Remove common suffixes for matching
            if name_norm.endswith("- no ia"):
                name_norm = name_norm[:-len("- no ia")].strip()
            
            name_parts = name_norm.split()
            
            # Score based on how well the filename matches the client name
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


def _read_excel_or_csv_file(file_path: str, log_func=None):
    """
    Comprehensive Excel/CSV file reader supporting multiple formats.
    
    Supports:
    - Excel files: .xlsx, .xls, .xlsm
    - CSV files: .csv (with multiple encoding fallbacks)
    
    Returns:
    - List of rows (each row is a list of cell values)
    - None if reading failed
    
    Args:
    - file_path: Path to the file
    - log_func: Optional logging function (e.g., self.base_log)
    """
    if not os.path.isfile(file_path):
        if log_func:
            log_func(f"[FILE][ERR] File not found: {file_path}")
        return None
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Excel files (.xlsx, .xls, .xlsm)
    if file_ext in ['.xlsx', '.xls', '.xlsm']:
        if not PANDAS_AVAILABLE:
            if log_func:
                log_func("[FILE][ERR] Excel file detected but pandas is not available. Install with: pip install pandas openpyxl")
            return None
        
        try:
            # Try openpyxl for .xlsx and .xlsm
            if file_ext in ['.xlsx', '.xlsm']:
                try:
                    df = pd.read_excel(file_path, header=None, engine='openpyxl')
                except Exception:
                    # Fallback to default engine
                    df = pd.read_excel(file_path, header=None)
            else:
                # .xls files - try xlrd or default engine
                try:
                    df = pd.read_excel(file_path, header=None, engine='xlrd')
                except Exception:
                    df = pd.read_excel(file_path, header=None)
            
            rows = df.values.tolist()
            if log_func:
                log_func(f"[FILE] Successfully read Excel file ({file_ext}): {os.path.basename(file_path)} ({len(rows)} rows)")
            return rows
        except Exception as e:
            if log_func:
                log_func(f"[FILE][ERR] Failed to read Excel file: {e}")
            return None
    
    # CSV files
    elif file_ext == '.csv':
        # Try pandas first (handles encoding better)
        if PANDAS_AVAILABLE:
            encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1", "iso-8859-1"]
            for enc in encodings:
                try:
                    df = pd.read_csv(file_path, header=None, encoding=enc, engine='python', on_bad_lines='skip')
                    rows = df.values.tolist()
                    if log_func:
                        log_func(f"[FILE] Successfully read CSV with pandas (encoding: {enc}): {os.path.basename(file_path)} ({len(rows)} rows)")
                    return rows
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    if log_func:
                        log_func(f"[FILE][WARN] pandas CSV read failed with {enc}: {e}")
                    continue
        
        # Fallback to CSV reader with encoding attempts
        encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1", "iso-8859-1"]
        for enc in encodings:
            try:
                with open(file_path, "r", newline="", encoding=enc, errors='replace') as f:
                    rows = list(_csv.reader(f))
                if log_func:
                    log_func(f"[FILE] Successfully read CSV with csv module (encoding: {enc}): {os.path.basename(file_path)} ({len(rows)} rows)")
                return rows
            except UnicodeDecodeError:
                continue
            except Exception as e:
                if log_func:
                    log_func(f"[FILE][WARN] CSV read failed with {enc}: {e}")
                continue
        
        if log_func:
            log_func("[FILE][ERR] Could not read CSV file with any encoding.")
        return None
    
    # Unknown file type
    else:
        if log_func:
            log_func(f"[FILE][ERR] Unsupported file type: {file_ext}. Supported: .xlsx, .xls, .xlsm, .csv")
        return None


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
    def __init__(self, csv_file=None, pdf_folder=None, tn_username=None, tn_password=None, 
                 remove_old_docs=False, tab="base", auto_run=False):
        super().__init__()
        self.title(f"{APP_TITLE} - Version 2.1.0, Last Updated 12/03/2025")
        self.minsize(1100, 850)
        
        # Command-line arguments
        self.cli_csv_file = csv_file
        self.cli_pdf_folder = pdf_folder
        self.cli_tn_username = tn_username
        self.cli_tn_password = tn_password
        self.cli_remove_old_docs = remove_old_docs
        self.cli_tab = tab
        self.cli_auto_run = auto_run
        
        # Saved users files
        self.base_users_file = Path(__file__).parent / "existing_client_uploader_base_users.json"
        self.ips_users_file = Path(__file__).parent / "existing_client_uploader_ips_users.json"
        self.base_users = {}
        self.ips_users = {}
        self.load_base_users()
        self.load_ips_users()
        
        # Separate drivers for each tab
        self.base_driver = None
        self.ips_driver = None
        self.base_logged_in = False
        self.ips_logged_in = False
        
        # Build UI
        self._build_header()
        self._build_notebook()
        
        # Apply command-line arguments if provided
        if csv_file:
            if tab == "base":
                self.base_csv.set(csv_file)
            else:
                self.ips_csv.set(csv_file)
            # Enable buttons after CSV is set
            self._maybe_enable_buttons()
        
        if pdf_folder:
            if tab == "base":
                self.base_folder.set(pdf_folder)
            else:
                self.ips_folder.set(pdf_folder)
        
        if tn_username:
            if tab == "base":
                self.base_user.set(tn_username)
            else:
                self.ips_user.set(tn_username)
        
        if tn_password:
            if tab == "base":
                self.base_pass.set(tn_password)
            else:
                self.ips_pass.set(tn_password)
        
        if remove_old_docs:
            if tab == "base":
                self.base_remove_old_reassignment_docs.set(True)
            else:
                self.ips_remove_old_reassignment_docs.set(True)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Auto-run if requested
        if auto_run:
            self.after(500, self._auto_run)
    
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
    
    def load_base_users(self):
        """Load Base users from JSON file"""
        try:
            if self.base_users_file.exists():
                with open(self.base_users_file, 'r') as f:
                    self.base_users = json.load(f)
            else:
                self.base_users = {}
                self.save_base_users()
        except Exception as e:
            self.base_users = {}
    
    def save_base_users(self):
        """Save Base users to JSON file"""
        try:
            with open(self.base_users_file, 'w') as f:
                json.dump(self.base_users, f, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save Base users:\n{e}")
            return False
    
    def load_ips_users(self):
        """Load IPS users from JSON file"""
        try:
            if self.ips_users_file.exists():
                with open(self.ips_users_file, 'r') as f:
                    self.ips_users = json.load(f)
            else:
                self.ips_users = {}
                self.save_ips_users()
        except Exception as e:
            self.ips_users = {}
    
    def save_ips_users(self):
        """Save IPS users to JSON file"""
        try:
            with open(self.ips_users_file, 'w') as f:
                json.dump(self.ips_users, f, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save IPS users:\n{e}")
            return False
    
    # ========== BASE TAB ==========
    def _build_base_tab(self, parent):
        """Build Base Existing Client Referral Uploader tab"""
        # Login Card
        c = self._card(parent, "TherapyNotes Login (Base/Regular)")
        for i in range(1, 5): c.grid_columnconfigure(i, weight=1)
        
        # Saved User Dropdown (row 1, after title in row 0)
        ttk.Label(c, text="Saved User:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.base_user_dropdown = ttk.Combobox(c, font=('Segoe UI', 9), width=25, state="readonly")
        self.base_user_dropdown.grid(row=1, column=1, sticky="w", padx=6, pady=6)
        self.base_user_dropdown.bind("<<ComboboxSelected>>", self._on_base_user_selected)
        self._update_base_user_dropdown()
        
        tk.Button(c, text="Add User", command=self._add_base_user,
                 bg=MAROON, fg="white", font=('Segoe UI', 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=1, column=2, padx=6, pady=6)
        
        tk.Button(c, text="Update User", command=self._update_base_user,
                 bg="#666666", fg="white", font=('Segoe UI', 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=1, column=3, padx=6, pady=6)
        
        # Username and Password (row 2)
        ttk.Label(c, text="Username:", foreground=MAROON).grid(row=2, column=0, sticky="e", padx=6, pady=6)
        self.base_user = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_user).grid(row=2, column=1, sticky="ew", padx=6, pady=6)
        ttk.Label(c, text="Password:", foreground=MAROON).grid(row=2, column=2, sticky="e", padx=6, pady=6)
        self.base_pass = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_pass, show="*").grid(row=2, column=3, sticky="ew", padx=6, pady=6)
        ttk.Button(c, text="Login", command=self.on_base_login).grid(row=2, column=4, padx=6, pady=6)
        
        # IPS Login Card (for running IPS uploader after Base)
        c_ips = self._card(parent, "IPS TherapyNotes Login (Optional - for running IPS uploader after Base)")
        for i in range(1, 5): c_ips.grid_columnconfigure(i, weight=1)
        ttk.Label(c_ips, text="IPS Username:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.base_ips_user = tk.StringVar()
        ttk.Entry(c_ips, textvariable=self.base_ips_user).grid(row=1, column=1, sticky="ew", padx=6, pady=4)
        ttk.Label(c_ips, text="IPS Password:", foreground=MAROON).grid(row=1, column=2, sticky="e", padx=6, pady=4)
        self.base_ips_pass = tk.StringVar()
        ttk.Entry(c_ips, textvariable=self.base_ips_pass, show="*").grid(row=1, column=3, sticky="ew", padx=6, pady=4)
        ttk.Label(c_ips, text="(Leave blank if same as Base)", foreground="gray", font=("TkDefaultFont", 8)).grid(row=2, column=1, columnspan=3, sticky="w", padx=6, pady=2)
        
        # Folder Card
        c = self._card(parent, "Referral Forms Folder (PDFs to upload)")
        for i in range(1, 5): c.grid_columnconfigure(i, weight=1)
        ttk.Label(c, text="Folder:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.base_folder = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_folder).grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=4)
        ttk.Button(c, text="Browse…", command=lambda: self._browse_folder(self.base_folder)).grid(row=1, column=4, padx=6, pady=4)
        
        # CSV Card
        c = self._card(parent, "CSV/Excel Input (Therapist from column L; Non-IPS counselors only)")
        for i in range(1, 8): c.grid_columnconfigure(i, weight=1)
        ttk.Label(c, text="CSV/Excel File:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.base_csv = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_csv).grid(row=1, column=1, columnspan=4, sticky="ew", padx=6, pady=4)
        ttk.Button(c, text="Choose File…", command=lambda: self._browse_csv(self.base_csv)).grid(row=1, column=5, padx=6, pady=4)
        
        self.base_skip_header = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text="Skip first row (header)", variable=self.base_skip_header).grid(row=2, column=1, sticky="w", padx=6, pady=2)
        
        self.base_remove_old_ia_docs = tk.BooleanVar(value=False)
        ttk.Checkbutton(c, text="Remove old 'IA Only' documents (30+ days)", variable=self.base_remove_old_ia_docs).grid(row=3, column=1, sticky="w", padx=6, pady=2)
        
        self.base_remove_old_reassignment_docs = tk.BooleanVar(value=False)
        ttk.Checkbutton(c, text="Remove old 'Reassignment' documents (30+ days)", variable=self.base_remove_old_reassignment_docs).grid(row=3, column=2, sticky="w", padx=6, pady=2)
        
        ttk.Label(c, text="Rows from:", foreground=MAROON).grid(row=4, column=0, sticky="e", padx=6, pady=4)
        self.base_row_from = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_row_from, width=10).grid(row=4, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(c, text="to:", foreground=MAROON).grid(row=4, column=2, sticky="e", padx=6, pady=4)
        self.base_row_to = tk.StringVar()
        ttk.Entry(c, textvariable=self.base_row_to, width=10).grid(row=4, column=3, sticky="w", padx=6, pady=4)
        
        btns = ttk.Frame(c); btns.grid(row=5, column=0, columnspan=6, sticky="w", padx=6, pady=(8,2))
        self.base_run_subset_btn = ttk.Button(btns, text="Run Selected Rows", command=self.on_base_run_subset, state="disabled")
        self.base_run_subset_btn.pack(side="left", padx=(0,8))
        self.base_run_all_btn = ttk.Button(btns, text="Run All Rows", command=self.on_base_run_all, state="disabled")
        self.base_run_all_btn.pack(side="left", padx=(0,8))
        
        # Checkbox to run IPS uploader after Base completes
        self.base_run_ips_after = tk.BooleanVar(value=False)
        ttk.Checkbutton(c, text="🏥 Also run IPS Uploader after Base completes", variable=self.base_run_ips_after).grid(row=6, column=1, columnspan=3, sticky="w", padx=6, pady=4)
        
        # Log Card
        c = self._card(parent, "Base Uploader Log")
        lf = ttk.Frame(c); lf.grid(row=0, column=0, columnspan=8, sticky="ew")
        self.base_log_widget = scrolledtext.ScrolledText(lf, height=12, wrap="word")
        self.base_log_widget.pack(fill="x", expand=False)
        self.base_log = UILog(self.base_log_widget)
        self.base_log("Base Existing Client Referral Uploader ready. This tab processes non-IPS counselors (based on column L).")
    
    # ========== IPS TAB ==========
    def _build_ips_tab(self, parent):
        """Build IPS Existing Client Referral Uploader tab"""
        # Login Card
        c = self._card(parent, "TherapyNotes Login (IPS)")
        for i in range(1, 5): c.grid_columnconfigure(i, weight=1)
        
        # Saved User Dropdown (row 1, after title in row 0)
        ttk.Label(c, text="Saved User:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.ips_user_dropdown = ttk.Combobox(c, font=('Segoe UI', 9), width=25, state="readonly")
        self.ips_user_dropdown.grid(row=1, column=1, sticky="w", padx=6, pady=6)
        self.ips_user_dropdown.bind("<<ComboboxSelected>>", self._on_ips_user_selected)
        self._update_ips_user_dropdown()
        
        tk.Button(c, text="Add User", command=self._add_ips_user,
                 bg=MAROON, fg="white", font=('Segoe UI', 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=1, column=2, padx=6, pady=6)
        
        tk.Button(c, text="Update User", command=self._update_ips_user,
                 bg="#666666", fg="white", font=('Segoe UI', 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=1, column=3, padx=6, pady=6)
        
        # Username and Password (row 2)
        ttk.Label(c, text="Username:", foreground=MAROON).grid(row=2, column=0, sticky="e", padx=6, pady=6)
        self.ips_user = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_user).grid(row=2, column=1, sticky="ew", padx=6, pady=6)
        ttk.Label(c, text="Password:", foreground=MAROON).grid(row=2, column=2, sticky="e", padx=6, pady=6)
        self.ips_pass = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_pass, show="*").grid(row=2, column=3, sticky="ew", padx=6, pady=6)
        ttk.Button(c, text="Login", command=self.on_ips_login).grid(row=2, column=4, padx=6, pady=6)
        
        # Folder Card
        c = self._card(parent, "Referral Forms Folder (PDFs to upload)")
        for i in range(1, 5): c.grid_columnconfigure(i, weight=1)
        ttk.Label(c, text="Folder:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.ips_folder = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_folder).grid(row=1, column=1, columnspan=3, sticky="ew", padx=6, pady=4)
        ttk.Button(c, text="Browse…", command=lambda: self._browse_folder(self.ips_folder)).grid(row=1, column=4, padx=6, pady=4)
        
        # CSV Card
        c = self._card(parent, "CSV/Excel Input (Therapist from column L; IPS counselors only)")
        for i in range(1, 8): c.grid_columnconfigure(i, weight=1)
        ttk.Label(c, text="CSV/Excel File:", foreground=MAROON).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.ips_csv = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_csv).grid(row=1, column=1, columnspan=4, sticky="ew", padx=6, pady=4)
        ttk.Button(c, text="Choose File…", command=lambda: self._browse_csv(self.ips_csv)).grid(row=1, column=5, padx=6, pady=4)
        
        self.ips_skip_header = tk.BooleanVar(value=True)
        ttk.Checkbutton(c, text="Skip first row (header)", variable=self.ips_skip_header).grid(row=2, column=1, sticky="w", padx=6, pady=2)
        
        self.ips_remove_old_ia_docs = tk.BooleanVar(value=False)
        ttk.Checkbutton(c, text="Remove old 'IA Only' documents (30+ days)", variable=self.ips_remove_old_ia_docs).grid(row=3, column=1, sticky="w", padx=6, pady=2)
        
        self.ips_remove_old_reassignment_docs = tk.BooleanVar(value=False)
        ttk.Checkbutton(c, text="Remove old 'Reassignment' documents (30+ days)", variable=self.ips_remove_old_reassignment_docs).grid(row=3, column=2, sticky="w", padx=6, pady=2)
        
        ttk.Label(c, text="Rows from:", foreground=MAROON).grid(row=4, column=0, sticky="e", padx=6, pady=4)
        self.ips_row_from = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_row_from, width=10).grid(row=4, column=1, sticky="w", padx=6, pady=4)
        ttk.Label(c, text="to:", foreground=MAROON).grid(row=4, column=2, sticky="e", padx=6, pady=4)
        self.ips_row_to = tk.StringVar()
        ttk.Entry(c, textvariable=self.ips_row_to, width=10).grid(row=4, column=3, sticky="w", padx=6, pady=4)
        
        btns = ttk.Frame(c); btns.grid(row=5, column=0, columnspan=6, sticky="w", padx=6, pady=(8,2))
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
        self.ips_log("IPS Existing Client Referral Uploader ready. This tab processes IPS counselors only (based on column L).")
    
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
    
    # ========== BASE USER MANAGEMENT ==========
    def _update_base_user_dropdown(self):
        """Update the Base user dropdown with current users"""
        if hasattr(self, 'base_user_dropdown'):
            user_names = sorted(self.base_users.keys())
            if user_names:
                self.base_user_dropdown['values'] = user_names
            else:
                self.base_user_dropdown['values'] = []
    
    def _on_base_user_selected(self, event=None):
        """Handle Base user selection from dropdown"""
        selected_user = self.base_user_dropdown.get()
        if selected_user and selected_user in self.base_users:
            user_data = self.base_users[selected_user]
            self.base_user.set(user_data.get('username', ''))
            self.base_pass.set(user_data.get('password', ''))
    
    def _add_base_user(self):
        """Add a new Base user to saved users"""
        dialog = tk.Toplevel(self)
        dialog.title("Add Base TherapyNotes User - Version 3.1.0, Last Updated 12/04/2025")
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
            
            if name in self.base_users:
                if not messagebox.askyesno("User Exists", f"User '{name}' already exists. Overwrite?"):
                    return
            
            self.base_users[name] = {
                'username': username,
                'password': password
            }
            self.save_base_users()
            self._update_base_user_dropdown()
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
    
    def _update_base_user(self):
        """Update credentials for selected Base user"""
        selected_user = self.base_user_dropdown.get()
        if not selected_user or selected_user not in self.base_users:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown")
            return
        
        username = self.base_user.get().strip()
        password = self.base_pass.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Invalid Input", "Username and password are required")
            return
        
        self.base_users[selected_user] = {
            'username': username,
            'password': password
        }
        self.save_base_users()
        messagebox.showinfo("Success", f"Credentials updated for '{selected_user}'")
    
    # ========== IPS USER MANAGEMENT ==========
    def _update_ips_user_dropdown(self):
        """Update the IPS user dropdown with current users"""
        if hasattr(self, 'ips_user_dropdown'):
            user_names = sorted(self.ips_users.keys())
            if user_names:
                self.ips_user_dropdown['values'] = user_names
            else:
                self.ips_user_dropdown['values'] = []
    
    def _on_ips_user_selected(self, event=None):
        """Handle IPS user selection from dropdown"""
        selected_user = self.ips_user_dropdown.get()
        if selected_user and selected_user in self.ips_users:
            user_data = self.ips_users[selected_user]
            self.ips_user.set(user_data.get('username', ''))
            self.ips_pass.set(user_data.get('password', ''))
    
    def _add_ips_user(self):
        """Add a new IPS user to saved users"""
        dialog = tk.Toplevel(self)
        dialog.title("Add IPS TherapyNotes User - Version 3.1.0, Last Updated 12/04/2025")
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
            
            if name in self.ips_users:
                if not messagebox.askyesno("User Exists", f"User '{name}' already exists. Overwrite?"):
                    return
            
            self.ips_users[name] = {
                'username': username,
                'password': password
            }
            self.save_ips_users()
            self._update_ips_user_dropdown()
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
    
    def _update_ips_user(self):
        """Update credentials for selected IPS user"""
        selected_user = self.ips_user_dropdown.get()
        if not selected_user or selected_user not in self.ips_users:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown")
            return
        
        username = self.ips_user.get().strip()
        password = self.ips_pass.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Invalid Input", "Username and password are required")
            return
        
        self.ips_users[selected_user] = {
            'username': username,
            'password': password
        }
        self.save_ips_users()
        messagebox.showinfo("Success", f"Credentials updated for '{selected_user}'")
    
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
            
            # Find and fill username field with JavaScript fallback
            usr = wait.until(EC.presence_of_element_located((By.ID, TN_USER_ID)))
            try:
                usr.clear()
                usr.click()
                time.sleep(0.2)
                usr.send_keys(user)
            except Exception:
                # JavaScript fallback
                self.base_driver.execute_script("arguments[0].value = '';", usr)
                self.base_driver.execute_script("arguments[0].value = arguments[1];", usr, user)
                self.base_driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", usr)
            
            # Find and fill password field with JavaScript fallback
            pw_ = wait.until(EC.presence_of_element_located((By.ID, TN_PASS_ID)))
            try:
                pw_.clear()
                pw_.click()
                time.sleep(0.2)
                pw_.send_keys(pwd)
            except Exception:
                # JavaScript fallback
                self.base_driver.execute_script("arguments[0].value = '';", pw_)
                self.base_driver.execute_script("arguments[0].value = arguments[1];", pw_, pwd)
                self.base_driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", pw_)
            
            # Click login button
            btn = wait.until(EC.element_to_be_clickable((By.ID, TN_BTN_ID)))
            try:
                btn.click()
            except Exception:
                self.base_driver.execute_script("arguments[0].click();", btn)
            
            wait.until(lambda d: d.find_element(By.LINK_TEXT, "Patients"))
            ok = True
        except Exception as e:
            self.base_log(f"[TN][ERR] {e}")
            import traceback
            self.base_log(f"[TN][ERR] Traceback: {traceback.format_exc()}")
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
            
            # Find and fill username field with JavaScript fallback
            usr = wait.until(EC.presence_of_element_located((By.ID, TN_USER_ID)))
            try:
                usr.clear()
                usr.click()
                time.sleep(0.2)
                usr.send_keys(user)
            except Exception:
                # JavaScript fallback
                self.ips_driver.execute_script("arguments[0].value = '';", usr)
                self.ips_driver.execute_script("arguments[0].value = arguments[1];", usr, user)
                self.ips_driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", usr)
            
            # Find and fill password field with JavaScript fallback
            pw_ = wait.until(EC.presence_of_element_located((By.ID, TN_PASS_ID)))
            try:
                pw_.clear()
                pw_.click()
                time.sleep(0.2)
                pw_.send_keys(pwd)
            except Exception:
                # JavaScript fallback
                self.ips_driver.execute_script("arguments[0].value = '';", pw_)
                self.ips_driver.execute_script("arguments[0].value = arguments[1];", pw_, pwd)
                self.ips_driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", pw_)
            
            # Click login button
            btn = wait.until(EC.element_to_be_clickable((By.ID, TN_BTN_ID)))
            try:
                btn.click()
            except Exception:
                self.ips_driver.execute_script("arguments[0].click();", btn)
            
            wait.until(lambda d: d.find_element(By.LINK_TEXT, "Patients"))
            ok = True
        except Exception as e:
            self.ips_log(f"[TN][ERR] {e}")
            import traceback
            self.ips_log(f"[TN][ERR] Traceback: {traceback.format_exc()}")
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
                
                # Find and fill username field with JavaScript fallback
                usr = wait.until(EC.presence_of_element_located((By.ID, TN_USER_ID)))
                try:
                    usr.clear()
                    usr.click()
                    time.sleep(0.2)
                    usr.send_keys(user)
                except Exception:
                    # JavaScript fallback
                    self.base_driver.execute_script("arguments[0].value = '';", usr)
                    self.base_driver.execute_script("arguments[0].value = arguments[1];", usr, user)
                    self.base_driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", usr)
                
                # Find and fill password field with JavaScript fallback
                pw_ = wait.until(EC.presence_of_element_located((By.ID, TN_PASS_ID)))
                try:
                    pw_.clear()
                    pw_.click()
                    time.sleep(0.2)
                    pw_.send_keys(pwd)
                except Exception:
                    # JavaScript fallback
                    self.base_driver.execute_script("arguments[0].value = '';", pw_)
                    self.base_driver.execute_script("arguments[0].value = arguments[1];", pw_, pwd)
                    self.base_driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", pw_)
                
                # Click login button
                btn = wait.until(EC.element_to_be_clickable((By.ID, TN_BTN_ID)))
                try:
                    btn.click()
                except Exception:
                    self.base_driver.execute_script("arguments[0].click();", btn)
                
                wait.until(lambda d: d.find_element(By.LINK_TEXT, "Patients"))
                self.base_logged_in = True
                self.base_log("[TN] Base login successful.")
                return True
            except Exception as e:
                self.base_logged_in = False
                self.base_log(f"[TN][ERR] {e}")
                import traceback
                self.base_log(f"[TN][ERR] Traceback: {traceback.format_exc()}")
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
                
                # Find and fill username field with JavaScript fallback
                usr = wait.until(EC.presence_of_element_located((By.ID, TN_USER_ID)))
                try:
                    usr.clear()
                    usr.click()
                    time.sleep(0.2)
                    usr.send_keys(user)
                except Exception:
                    # JavaScript fallback
                    self.ips_driver.execute_script("arguments[0].value = '';", usr)
                    self.ips_driver.execute_script("arguments[0].value = arguments[1];", usr, user)
                    self.ips_driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", usr)
                
                # Find and fill password field with JavaScript fallback
                pw_ = wait.until(EC.presence_of_element_located((By.ID, TN_PASS_ID)))
                try:
                    pw_.clear()
                    pw_.click()
                    time.sleep(0.2)
                    pw_.send_keys(pwd)
                except Exception:
                    # JavaScript fallback
                    self.ips_driver.execute_script("arguments[0].value = '';", pw_)
                    self.ips_driver.execute_script("arguments[0].value = arguments[1];", pw_, pwd)
                    self.ips_driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", pw_)
                
                # Click login button
                btn = wait.until(EC.element_to_be_clickable((By.ID, TN_BTN_ID)))
                try:
                    btn.click()
                except Exception:
                    self.ips_driver.execute_script("arguments[0].click();", btn)
                
                wait.until(lambda d: d.find_element(By.LINK_TEXT, "Patients"))
                self.ips_logged_in = True
                self.ips_log("[TN] IPS login successful.")
                return True
            except Exception as e:
                self.ips_logged_in = False
                self.ips_log(f"[TN][ERR] {e}")
                import traceback
                self.ips_log(f"[TN][ERR] Traceback: {traceback.format_exc()}")
                return False
    
    def on_base_run_subset(self):
        """Run base subset"""
        csv_path = (self.base_csv.get() or "").strip()
        if not os.path.isfile(csv_path):
            messagebox.showwarning("CSV missing", "Please choose a valid CSV file."); return
        folder_path = (self.base_folder.get() or "").strip()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showwarning("Folder missing", "Please select a referral forms folder using the 'Browse...' button."); return
        try:
            start = int(self.base_row_from.get().strip())
            end = int(self.base_row_to.get().strip())
            if start <= 0 or end <= 0 or end < start: raise ValueError
        except Exception:
            messagebox.showwarning("Bad range", "Enter valid 1-based row numbers."); return
        self.base_log(f"[CSV] Running Base subset rows: {start} to {end}")
        self.base_log(f"[CSV] Referral forms folder: {folder_path}")
        threading.Thread(target=self._base_worker, args=(csv_path, start, end), daemon=True).start()
    
    def on_base_run_all(self):
        """Run base all"""
        csv_path = (self.base_csv.get() or "").strip()
        if not os.path.isfile(csv_path):
            messagebox.showwarning("CSV missing", "Please choose a valid CSV file."); return
        folder_path = (self.base_folder.get() or "").strip()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showwarning("Folder missing", "Please select a referral forms folder using the 'Browse...' button."); return
        self.base_log(f"[CSV] Running Base ALL rows")
        self.base_log(f"[CSV] Referral forms folder: {folder_path}")
        threading.Thread(target=self._base_worker, args=(csv_path, None, None), daemon=True).start()
    
    def on_ips_run_subset(self):
        """Run IPS subset"""
        csv_path = (self.ips_csv.get() or "").strip()
        if not os.path.isfile(csv_path):
            messagebox.showwarning("CSV missing", "Please choose a valid CSV file."); return
        folder_path = (self.ips_folder.get() or "").strip()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showwarning("Folder missing", "Please select a referral forms folder using the 'Browse...' button."); return
        try:
            start = int(self.ips_row_from.get().strip())
            end = int(self.ips_row_to.get().strip())
            if start <= 0 or end <= 0 or end < start: raise ValueError
        except Exception:
            messagebox.showwarning("Bad range", "Enter valid 1-based row numbers."); return
        self.ips_log(f"[CSV] Running IPS subset rows: {start} to {end}")
        self.ips_log(f"[CSV] Referral forms folder: {folder_path}")
        threading.Thread(target=self._ips_worker, args=(csv_path, start, end), daemon=True).start()
    
    def on_ips_run_all(self):
        """Run IPS all"""
        csv_path = (self.ips_csv.get() or "").strip()
        if not os.path.isfile(csv_path):
            messagebox.showwarning("CSV missing", "Please choose a valid CSV file."); return
        folder_path = (self.ips_folder.get() or "").strip()
        if not folder_path or not os.path.isdir(folder_path):
            messagebox.showwarning("Folder missing", "Please select a referral forms folder using the 'Browse...' button."); return
        self.ips_log(f"[CSV] Running IPS ALL rows")
        self.ips_log(f"[CSV] CSV file: {csv_path}")
        self.ips_log(f"[CSV] Referral forms folder: {folder_path}")
        threading.Thread(target=self._ips_worker, args=(csv_path, None, None), daemon=True).start()
    
    def _base_worker(self, csv_path, start_row, end_row):
        """Base CSV worker - only processes non-IPS counselors (based on column L)"""
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
            
            # Read CSV or Excel file using comprehensive reader
            rows = _read_excel_or_csv_file(csv_path, log_func=self.base_log)
            if rows is None:
                self.base_log("[CSV][ERR] Failed to read input file.")
                return
            
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
                
                # Stop processing if we encounter a completely empty row (no data in any column)
                # Handle pandas NaN values (which become None or float('nan') in the list)
                is_empty = True
                for cell in row:
                    if cell is not None and str(cell).strip() and str(cell).lower() != 'nan':
                        is_empty = False
                        break
                if is_empty:
                    self.base_log(f"[CSV] Row {row_1b} is completely empty. Stopping processing (end of data).")
                    break
                
                try:  # Ensure we always return to Patients page
                    def _record(status, reason, therapist="", client=""):
                        records.append({
                            "csv_row": row_1b, "therapist": therapist, "client": client,
                            "status": status, "reason": reason,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
                    
                    # Debug: Log row length and column L value
                    if len(row) <= CSV_COL_L_INDEX:
                        self.base_log(f"[CSV][DEBUG] Row {row_1b}: Row has only {len(row)} columns (need at least {CSV_COL_L_INDEX + 1} for column L). Row data: {row[:5]}...")
                        self.base_log(f"[CSV][WARN] Row {row_1b} missing therapist in column L (row too short); skipping.")
                        _record("skipped", "missing therapist (L - row too short)")
                        continue
                    
                    # Handle pandas NaN values
                    raw_value = row[CSV_COL_L_INDEX] if len(row) > CSV_COL_L_INDEX else None
                    if raw_value is None or (isinstance(raw_value, float) and str(raw_value).lower() == 'nan'):
                        therapist = ""
                    else:
                        therapist = str(raw_value).strip()
                    
                    self.base_log(f"[CSV][DEBUG] Row {row_1b}: Column L value = '{therapist}' (raw: '{raw_value}')")
                    
                    if not therapist:
                        self.base_log(f"[CSV][WARN] Row {row_1b} missing therapist in column L (empty value); skipping.")
                        _record("skipped", "missing therapist (L - empty)")
                        continue
                    
                    # Check if counselor is IPS (based on column L only)
                    is_ips = _is_ips_counselor(therapist)
                    self.base_log(f"[CSV][DEBUG] Row {row_1b}: Is IPS counselor? {is_ips} (therapist: '{therapist}')")
                    
                    if is_ips:
                        self.base_log(f"[CSV] Row {row_1b}: Therapist '{therapist}' is IPS (based on column L); skipping in Base uploader.")
                        _record("skipped", "IPS counselor (Base uploader)", therapist)
                        continue
                    
                    client = (row[client_name_idx] if len(row) > client_name_idx else "").strip()
                    if not client:
                        self.base_log(f"[CSV][WARN] Row {row_1b} missing client name; skipping.")
                        _record("skipped", "missing client", therapist)
                        continue
                    
                    full_name = _extract_full_name_from_csv(row, client_name_idx)
                    if full_name and full_name != client:
                        self.base_log(f"[CSV] Row {row_1b}: Using full name '{full_name}' (from '{client}')")
                    
                    self.base_log(f"[CSV] Row {row_1b}: '{client}' for therapist '{therapist}' (non-IPS).")
                    
                    # Ensure we're on Patients page before searching
                    if not self._click_patients("base"):
                        self.base_log(f"[CSV][WARN] Row {row_1b}: Could not navigate to Patients page.")
                        _record("skipped", "could not navigate to Patients", therapist, client)
                        continue
                    
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
                    
                    # Remove old Reassignment documents if checkbox is enabled
                    if not self._remove_old_reassignment_documents("base", is_ips_counselor=False):
                        self.base_log(f"[CSV][WARN] Row {row_1b}: Reassignment document removal failed (continuing anyway).")
                    
                    uploaded = self._per_row_upload_action("base", therapist, client, self.base_folder.get(), full_name, is_ips_counselor=False)
                    if uploaded:
                        self.base_log(f"[CSV] Row {row_1b}: upload completed.")
                        _record("success", "uploaded", therapist, client)
                    else:
                        self.base_log(f"[CSV][WARN] Row {row_1b}: upload failed.")
                        _record("skipped", "upload failed", therapist, client)
                finally:
                    # ALWAYS return to Patients page after each row (success or failure)
                    self._click_patients("base")
                    # No wait needed - _click_patients verifies immediately with SVG element
            
            out_path = _write_report(records, csv_path)
            self.base_log(f"[CSV] Base CSV run complete. Report: {out_path}")
            # Removed blocking popup - log only
            
            # Launch IPS uploader if checkbox is checked
            if self.base_run_ips_after.get():
                self.base_log("[IPS-UPLOADER] Launching IPS Uploader after Base completion...")
                self._launch_ips_uploader_from_base()
        
        except Exception as e:
            self.base_log(f"[CSV][ERR] {e}")
            import traceback
            self.base_log(f"[CSV][ERR] Traceback: {traceback.format_exc()}")
    
    def _launch_ips_uploader_from_base(self):
        """Launch IPS uploader from Base tab after Base completes"""
        try:
            import subprocess
            import sys
            import os
            
            csv_file = self.base_csv.get()
            pdf_folder = self.base_folder.get()
            
            # Use IPS credentials from Base tab if provided, otherwise use Base credentials
            ips_username = self.base_ips_user.get().strip() if self.base_ips_user.get().strip() else self.base_user.get()
            ips_password = self.base_ips_pass.get().strip() if self.base_ips_pass.get().strip() else self.base_pass.get()
            
            if not ips_username or not ips_password:
                self.base_log("[IPS-UPLOADER][ERROR] IPS credentials not provided")
                return
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            uploader_path = os.path.join(current_dir, "existing_client_referral_form_uploader.py")
            
            if not os.path.exists(uploader_path):
                self.base_log(f"[IPS-UPLOADER][ERROR] Uploader not found at: {uploader_path}")
                return
            
            ips_cmd_args = [
                sys.executable,
                uploader_path,
                "--csv-file", csv_file,
                "--pdf-folder", pdf_folder,
                "--tn-username", ips_username,
                "--tn-password", ips_password,
                "--tab", "ips",
                "--auto-run"
            ]
            
            # Add remove-old-docs flag if checkbox is checked
            if self.base_remove_old_reassignment_docs.get():
                ips_cmd_args.append("--remove-old-docs")
            
            self.base_log("[IPS-UPLOADER] Launching IPS Uploader...")
            ips_process = subprocess.Popen(
                ips_cmd_args,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            time.sleep(2)
            
            if ips_process.poll() is None:
                self.base_log(f"[IPS-UPLOADER] ✓ IPS Uploader launched (PID: {ips_process.pid})")
                self.base_log("[IPS-UPLOADER] Waiting for IPS Uploader to complete...")
                ips_process.wait()
                self.base_log(f"[IPS-UPLOADER] ✓ IPS Uploader completed (exit code: {ips_process.returncode})")
            else:
                self.base_log(f"[IPS-UPLOADER][ERROR] IPS Uploader failed to start")
        
        except Exception as e:
            self.base_log(f"[IPS-UPLOADER][ERROR] Launch failed: {e}")
            import traceback
            self.base_log(f"[IPS-UPLOADER][ERROR] {traceback.format_exc()}")
    
    def _ips_worker(self, csv_path, start_row, end_row):
        """IPS CSV worker - only processes IPS counselors (based on column L)"""
        self.ips_log(f"[IPS-WORKER] Starting IPS worker with CSV: {csv_path}")
        
        if not self._login_if_needed("ips"):
            self.ips_log("[IPS-WORKER][ERR] Login failed or credentials missing.")
            try: messagebox.showwarning("Login required", "Enter credentials, then click Run again.")
            except Exception: pass
            return
        
        records = []
        try:
            # Click Patients
            self.ips_log("[NAV] Opening Patients page...")
            if not self._click_patients("ips"):
                self.ips_log("[CSV][ERR] Could not open Patients page."); return
            
            # Read CSV or Excel file using comprehensive reader
            self.ips_log(f"[CSV] Reading file: {csv_path}")
            rows = _read_excel_or_csv_file(csv_path, log_func=self.ips_log)
            if rows is None:
                self.ips_log("[CSV][ERR] Failed to read input file.")
                return
            
            self.ips_log(f"[CSV] Successfully read {len(rows)} rows from file.")
            
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
                
                # Stop processing if we encounter a completely empty row (no data in any column)
                # Handle pandas NaN values (which become None or float('nan') in the list)
                is_empty = True
                for cell in row:
                    if cell is not None and str(cell).strip() and str(cell).lower() != 'nan':
                        is_empty = False
                        break
                if is_empty:
                    self.ips_log(f"[CSV] Row {row_1b} is completely empty. Stopping processing (end of data).")
                    break
                
                try:  # Ensure we always return to Patients page
                    def _record(status, reason, therapist="", client=""):
                        records.append({
                            "csv_row": row_1b, "therapist": therapist, "client": client,
                            "status": status, "reason": reason,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        })
                    
                    # Handle pandas NaN values
                    raw_value = row[CSV_COL_L_INDEX] if len(row) > CSV_COL_L_INDEX else None
                    if raw_value is None or (isinstance(raw_value, float) and str(raw_value).lower() == 'nan'):
                        therapist = ""
                    else:
                        therapist = str(raw_value).strip()
                    
                    self.ips_log(f"[CSV][DEBUG] Row {row_1b}: Column L value = '{therapist}' (raw: '{raw_value}')")
                    
                    if not therapist:
                        self.ips_log(f"[CSV][WARN] Row {row_1b} missing therapist in column L; skipping.")
                        _record("skipped", "missing therapist (L)")
                        continue
                    
                    # Check if counselor is IPS (based on column L only)
                    is_ips = _is_ips_counselor(therapist)
                    self.ips_log(f"[CSV][DEBUG] Row {row_1b}: Is IPS counselor? {is_ips} (therapist: '{therapist}')")
                    
                    if not is_ips:
                        self.ips_log(f"[CSV][WARN] Row {row_1b}: Therapist '{therapist}' is not IPS (based on column L); skipping in IPS uploader.")
                        _record("skipped", "non-IPS counselor (IPS uploader)", therapist)
                        continue
                    
                    client = (row[client_name_idx] if len(row) > client_name_idx else "").strip()
                    if not client:
                        self.ips_log(f"[CSV][WARN] Row {row_1b} missing client name; skipping.")
                        _record("skipped", "missing client", therapist)
                        continue
                    
                    full_name = _extract_full_name_from_csv(row, client_name_idx)
                    if full_name and full_name != client:
                        self.ips_log(f"[CSV] Row {row_1b}: Using full name '{full_name}' (from '{client}')")
                    
                    self.ips_log(f"[CSV] Row {row_1b}: '{client}' for therapist '{therapist}' (IPS).")
                    
                    # Ensure we're on Patients page before searching
                    if not self._click_patients("ips"):
                        self.ips_log(f"[CSV][WARN] Row {row_1b}: Could not navigate to Patients page.")
                        _record("skipped", "could not navigate to Patients", therapist, client)
                        continue
                    
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
                    
                    # Remove old Reassignment documents if checkbox is enabled
                    if not self._remove_old_reassignment_documents("ips", is_ips_counselor=True):
                        self.ips_log(f"[CSV][WARN] Row {row_1b}: Reassignment document removal failed (continuing anyway).")
                    
                    uploaded = self._per_row_upload_action("ips", therapist, client, self.ips_folder.get(), full_name, is_ips_counselor=True)
                    if uploaded:
                        self.ips_log(f"[CSV] Row {row_1b}: upload completed.")
                        _record("success", "uploaded", therapist, client)
                    else:
                        self.ips_log(f"[CSV][WARN] Row {row_1b}: upload failed.")
                        _record("skipped", "upload failed", therapist, client)
                finally:
                    # ALWAYS return to Patients page after each row (success or failure)
                    self._click_patients("ips")
                    # No wait needed - _click_patients verifies immediately with SVG element
            
            out_path = _write_report(records, csv_path)
            self.ips_log(f"[CSV] IPS CSV run complete. Report: {out_path}")
            # Removed blocking popup - log only
        
        except Exception as e:
            self.ips_log(f"[CSV][ERR] {e}")
    
    # ===== Navigation & Upload Helpers =====
    def _click_patients(self, mode):
        """Click Patients link - optimized: quick checks, fast exit"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        if not driver:
            log("[NAV] No driver."); return False
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            
            # Quick check: URL first (fastest)
            try:
                current_url = driver.current_url
                if "/patients" in current_url.lower():
                    log("[NAV] Already on Patients page (URL check).")
                    return True
            except Exception:
                pass
            
            # Quick check: search input (fast, no wait)
            try:
                search_input = driver.find_element(By.ID, "ctl00_BodyContent_TextBoxSearchPatientName")
                if search_input:
                    log("[NAV] Already on Patients page (search input found).")
                    return True
            except Exception:
                pass
            
            # Quick check: SVG element (fast, no wait)
            try:
                svg = driver.find_element(By.XPATH, "//svg[.//g[@id='circle-user-v6']]")
                if svg:
                    log("[NAV] Already on Patients page (SVG found).")
                    return True
            except Exception:
                pass
            
            # Not on Patients page, click Patients link (short timeout)
            wait = WebDriverWait(driver, 2)
            try:
                patients_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Patients")))
                patients_link.click()
                log("[NAV] Clicked Patients link.")
                time.sleep(0.2)
                return True
            except Exception:
                # If we can't find Patients link, assume we're already on the page
                log("[NAV] Could not find Patients link - assuming already on Patients page.")
                return True
        except Exception as e:
            log(f"[NAV][WARN] {e}, but proceeding")
            return True
    
    def _search_therapist_new_referrals(self, mode, therapist_name: str, timeout: int = 15):
        """Search for '{Therapist} New Referrals' with retry logic that progressively shortens the search term"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        if not driver:
            log("[SRCH] No driver."); return False
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            
            parsed_name = _parse_therapist_name_for_search(therapist_name)
            # Create search term variations: full name, then progressively shorter
            name_parts = parsed_name.split()
            search_variations = []
            # Start with full name
            search_variations.append(f"{parsed_name} New Referrals".strip())
            # Then try with one less word at a time
            for i in range(len(name_parts) - 1, 0, -1):
                shorter_name = " ".join(name_parts[:i])
                search_variations.append(f"{shorter_name} New Referrals".strip())
            
            log(f"[SRCH] CSV: '{therapist_name}' → Will try {len(search_variations)} search variations")
            
            # Try each search variation until one works
            for attempt, target_text in enumerate(search_variations, 1):
                log(f"[SRCH] Attempt {attempt}/{len(search_variations)}: Searching: '{target_text}'")
                
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
                    log(f"[SRCH][WARN] send_keys failed: {e}, using JavaScript fallback with character-by-character typing...")
                    used_js_fallback = True
                    try:
                        # JavaScript fallback: clear first, then type character by character to trigger dropdown
                        driver.execute_script("""
                            var input = document.getElementById('ctl00_BodyContent_TextBoxSearchPatientName');
                            if (input) {
                                input.focus();
                                input.value = '';
                            }
                        """)
                        for char in target_text:
                            driver.execute_script("""
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
                        log(f"[SRCH][ERR] JavaScript fallback failed: {js_e}")
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
                    log(f"[SRCH][DEBUG] Found dropdown container via ContentBubbleResultsContainer")
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
                            container = driver.find_element(by, selector)
                            if container and container.is_displayed():
                                dropdown_found = True
                                log(f"[SRCH][DEBUG] Found dropdown container via alternative selector: {selector}")
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
                            driver.execute_script("""
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
                        log(f"[SRCH][DEBUG] Found dropdown container after retry")
                    except Exception:
                        pass
                
                if not dropdown_found:
                    log(f"[SRCH][WARN] Dropdown container did not appear for '{target_text}', trying next variation...")
                    continue  # Try next search variation
                
                # Find items in dropdown container
                items = []
                for xp in [".//a[normalize-space()]", ".//div[@role='option']"]:
                    try: items.extend(container.find_elements(By.XPATH, xp))
                    except Exception: pass
                
                if not items:
                    log(f"[SRCH][WARN] No items found in dropdown for '{target_text}', trying next variation...")
                    continue  # Try next search variation
                
                # Success! Found items in dropdown
                log(f"[SRCH][DEBUG] Found {len(items)} items in dropdown for '{target_text}'")
                
                tl = target_text.lower(); matched_text = None
                for el in items:
                    label = (el.text or "").strip()
                    if label and tl in label.lower(): 
                        matched_text = label
                        break
                
                if not matched_text:
                    matched_text = items[0].text.strip()
                    log(f"[SRCH][WARN] No exact match; selecting first option: '{matched_text}'")
                
                # Re-find the element right before clicking to avoid stale element
                matched = None
                try:
                    # Re-find container and items fresh
                    container = driver.find_element(By.ID, "ContentBubbleResultsContainer")
                    fresh_items = []
                    for xp in [".//a[normalize-space()]", ".//div[@role='option']"]:
                        try: fresh_items.extend(container.find_elements(By.XPATH, xp))
                        except Exception: pass
                    
                    # Find the matched item by text
                    for el in fresh_items:
                        label = (el.text or "").strip()
                        if label == matched_text or (matched_text and matched_text.lower() in label.lower()):
                            matched = el
                            break
                    
                    if not matched and fresh_items:
                        matched = fresh_items[0]
                except Exception as e:
                    log(f"[SRCH][WARN] Could not re-find element, using original: {e}")
                    # Fallback to original items
                    for el in items:
                        label = (el.text or "").strip()
                        if label and tl in label.lower(): 
                            matched = el
                            break
                    if not matched:
                        matched = items[0] if items else None
                
                if not matched:
                    log(f"[SRCH][WARN] Could not find element to click for '{target_text}', trying next variation...")
                    continue  # Try next search variation
                
                # Click the matched element
                clicked = False
                try: 
                    matched.click()
                    clicked = True
                    log(f"[SRCH] Clicked matched item: '{matched_text}'")
                except Exception as e:
                    try: 
                        driver.execute_script("arguments[0].click();", matched)
                        clicked = True
                        log(f"[SRCH] Clicked matched item via JavaScript: '{matched_text}'")
                    except Exception as e2:
                        log(f"[SRCH][WARN] Click failed but may have worked: {e2}")
                        # Still return True - user says click is working
                        clicked = True
                
                log("[SRCH] Selection made, waiting for page load...")
                time.sleep(0.6)
                return True  # Success! Break out of retry loop
            
            # If we get here, all variations failed
            log("[SRCH][ERR] All search variations failed - no dropdown items found for any variation.")
            return False
        except Exception as e:
            log(f"[SRCH][ERR] {e}"); return False
    
    def _open_documents_tab(self, mode, timeout: int = 15):
        """Open Documents tab - handles stale elements and smart waits for tab to load"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            
            # Find the tab using selectors
            tab_selector = None
            for by, val in [
                (By.LINK_TEXT, "Documents"),
                (By.XPATH, "//a[contains(@href, '#tab=Documents')]"),
            ]:
                try: 
                    tab = wait.until(EC.element_to_be_clickable((by, val)))
                    tab_selector = (by, val)
                    break
                except Exception: pass
            
            if not tab_selector:
                log("[DOCS][ERR] Documents tab not found."); return False
            
            # Re-find element right before clicking to avoid stale element issues
            try:
                tab = wait.until(EC.element_to_be_clickable(tab_selector))
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", tab)
                tab.click()
                log("[DOCS] Documents tab clicked.")
            except Exception as e1:
                # If Selenium click fails (stale element), try JavaScript click
                try:
                    tab = wait.until(EC.presence_of_element_located(tab_selector))
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'}); arguments[0].click();", tab)
                    log("[DOCS] Documents tab clicked (JavaScript click).")
                except Exception as e2:
                    log(f"[DOCS][WARN] Click failed but may have worked: {e2}")
                    # Proceed anyway - user says it's working
            
            # Smart wait: Poll to check if Documents tab is loaded, exit early if detected
            # Check for indicators that Documents tab is active (upload button, document table, etc.)
            max_wait_time = 10.0  # Maximum seconds to wait
            check_interval = 0.3  # Check every 0.3 seconds
            start_time = time.time()
            tab_loaded = False
            
            while time.time() - start_time < max_wait_time:
                try:
                    # Check for multiple indicators that Documents tab is loaded
                    # 1. Upload Patient File button
                    upload_btn = driver.find_elements(By.XPATH, "//button[contains(normalize-space(.), 'Upload Patient File')]")
                    # 2. Documents table
                    doc_table = driver.find_elements(By.XPATH, "//table//tr[td]")
                    # 3. Documents tab active state (if we can detect it)
                    active_tab = driver.find_elements(By.XPATH, "//a[@data-tab-id='Documents' and contains(@class, 'active')]")
                    
                    if upload_btn or (doc_table and len(doc_table) > 0) or active_tab:
                        tab_loaded = True
                        elapsed = time.time() - start_time
                        log(f"[DOCS] Documents tab loaded (detected after {elapsed:.1f}s)")
                        break
                except Exception:
                    pass  # Continue checking
                
                time.sleep(check_interval)
            
            if not tab_loaded:
                elapsed = time.time() - start_time
                log(f"[DOCS][WARN] Documents tab may not be fully loaded (waited {elapsed:.1f}s), but proceeding anyway")
            
            return True
        except Exception as e:
            log(f"[DOCS][WARN] Error but proceeding: {e}")
            return True  # Proceed anyway - user says Documents tab opens
    
    def _remove_old_ia_only_documents(self, mode, timeout: int = 15):
        """
        Remove documents with 'IA Only' prefix (case-insensitive) that are 30+ days old.
        Flow: Click pencil icon -> Click "Delete Document" -> Click "Delete File" button
        Returns True if successful or if checkbox was not enabled, False on error.
        """
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        # Check if the feature is enabled
        remove_enabled = self.base_remove_old_ia_docs.get() if mode == "base" else self.ips_remove_old_ia_docs.get()
        if not remove_enabled:
            return True  # Not an error, just feature disabled
        
        log("[CLEANUP] Remove old IA Only documents feature is enabled. Checking for documents to remove...")
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            
            time.sleep(0.5)  # Give the page time to render
            
            log("[CLEANUP] Searching for document rows in table...")
            
            doc_rows = []
            try:
                all_rows = driver.find_elements(By.XPATH, "//table//tr[td]")
                for row in all_rows:
                    row_text_lower = (row.text or "").lower()
                    if any(header in row_text_lower for header in ['document', 'service', 'date', 'author', 'status']):
                        if len([c for c in row_text_lower.split() if c in ['document', 'service', 'date']]) >= 2:
                            continue
                    doc_rows.append(row)
                
                if doc_rows:
                    log(f"[CLEANUP] Found {len(doc_rows)} document row(s) in table")
                else:
                    rows = driver.find_elements(By.XPATH, "//tr[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ia only')]")
                    doc_rows = rows
                    log(f"[CLEANUP] Found {len(doc_rows)} potential document row(s) via 'IA Only' text search")
            except Exception as e:
                log(f"[CLEANUP][WARN] Could not find rows: {e}")
                return False
            
            if not doc_rows:
                log("[CLEANUP] No document rows found.")
                return True
            
            cutoff_date = datetime.now() - timedelta(days=30)
            log(f"[CLEANUP] Looking for documents older than {cutoff_date.strftime('%m/%d/%Y')}")
            
            removed_count = 0
            skipped_count = 0
            
            for idx, row in enumerate(doc_rows, 1):
                try:
                    row_text = (row.text or "").strip()
                    
                    if not re.search(r'\bIA\s+ONLY\b', row_text, re.IGNORECASE):
                        continue
                    
                    if not re.search(r'\d{1,2}/\d{1,2}/\d{4}', row_text):
                        continue
                    
                    log(f"[CLEANUP] Row {idx}: Found potential IA Only document: {row_text[:80]}...")
                    
                    date_cells = row.find_elements(By.XPATH, ".//td[contains(text(), '/202') or contains(text(), '/2025') or contains(text(), '/2024')]")
                    
                    doc_date_str = None
                    for cell in date_cells:
                        cell_text = (cell.text or "").strip()
                        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', cell_text):
                            doc_date_str = cell_text
                            break
                    
                    if not doc_date_str:
                        log(f"[CLEANUP][WARN] Row {idx}: Could not find date, skipping")
                        skipped_count += 1
                        continue
                    
                    try:
                        doc_date = datetime.strptime(doc_date_str, "%m/%d/%Y")
                    except ValueError:
                        try:
                            doc_date = datetime.strptime(doc_date_str, "%m/%d/%y")
                        except ValueError:
                            log(f"[CLEANUP][WARN] Row {idx}: Could not parse date '{doc_date_str}', skipping")
                            skipped_count += 1
                            continue
                    
                    days_old = (datetime.now() - doc_date).days
                    if days_old < 30:
                        log(f"[CLEANUP] Row {idx}: Document dated {doc_date_str} ({days_old} days old) is less than 30 days, skipping")
                        skipped_count += 1
                        continue
                    
                    log(f"[CLEANUP] Row {idx}: Document dated {doc_date_str} ({days_old} days old) is 30+ days old - will remove")
                    
                    pencil_icon = None
                    try:
                        pencil_icon = row.find_element(By.XPATH, ".//div[contains(@class, 'fa-icon') and contains(@class, 'pencil-alt')]")
                    except Exception:
                        try:
                            pencil_icon = row.find_element(By.XPATH, ".//*[contains(@class, 'pencil-alt')]")
                        except Exception:
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
                    
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", pencil_icon)
                        time.sleep(0.2)
                        pencil_icon.click()
                        log(f"[CLEANUP] Row {idx}: Clicked pencil icon")
                        time.sleep(0.5)
                    except Exception as e:
                        log(f"[CLEANUP][WARN] Row {idx}: Failed to click pencil icon: {e}")
                        skipped_count += 1
                        continue
                    
                    delete_link = None
                    try:
                        delete_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Delete Document')]")))
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", delete_link)
                        time.sleep(0.2)
                        delete_link.click()
                        log(f"[CLEANUP] Row {idx}: Clicked 'Delete Document'")
                        time.sleep(0.5)
                    except Exception as e:
                        log(f"[CLEANUP][WARN] Row {idx}: Failed to find/click 'Delete Document': {e}")
                        skipped_count += 1
                        try:
                            cancel_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close')]")
                            cancel_btn.click()
                            time.sleep(0.3)
                        except Exception:
                            pass
                        continue
                    
                    try:
                        delete_file_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='button' and @value='Delete File']")))
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", delete_file_btn)
                        time.sleep(0.2)
                        delete_file_btn.click()
                        log(f"[CLEANUP] Row {idx}: Clicked 'Delete File' button - document removed")
                        removed_count += 1
                        time.sleep(0.8)
                    except Exception as e:
                        log(f"[CLEANUP][WARN] Row {idx}: Failed to find/click 'Delete File' button: {e}")
                        skipped_count += 1
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
    
    def _remove_old_reassignment_documents(self, mode, is_ips_counselor: bool, timeout: int = 15):
        """
        Remove documents with 'Reassignment' or 'IPS Reassignment' prefix that are 30+ days old.
        - Base tab: Only removes "Reassignment" documents (not "IPS Reassignment")
        - IPS tab: Removes BOTH "Reassignment" AND "IPS Reassignment" documents (all documents in IPS portal are IPS-related)
        Returns True if successful or if checkbox was not enabled, False on error.
        """
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        # Check if the feature is enabled
        remove_enabled = self.base_remove_old_reassignment_docs.get() if mode == "base" else self.ips_remove_old_reassignment_docs.get()
        if not remove_enabled:
            return True  # Not an error, just feature disabled
        
        log("[CLEANUP] Remove old Reassignment documents feature is enabled. Checking for documents to remove...")
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            
            # Close any open dialogs first (they block clicks)
            try:
                dialogs = driver.find_elements(By.XPATH, "//div[contains(@class, 'Dialog')]")
                for dialog in dialogs:
                    try:
                        # Try to find and click close/cancel buttons in dialog
                        close_btns = dialog.find_elements(By.XPATH, ".//button[contains(text(), 'Close') or contains(text(), 'Cancel') or contains(@class, 'close')]")
                        if close_btns:
                            driver.execute_script("arguments[0].click();", close_btns[0])
                            log("[CLEANUP] Closed open dialog")
                            time.sleep(0.5)
                    except Exception:
                        pass
            except Exception:
                pass
            
            time.sleep(0.5)  # Give the page time to render
            
            log("[CLEANUP] Searching for document rows in table...")
            
            doc_rows = []
            try:
                all_rows = driver.find_elements(By.XPATH, "//table//tr[td]")
                for row in all_rows:
                    row_text_lower = (row.text or "").lower()
                    if any(header in row_text_lower for header in ['document', 'service', 'date', 'author', 'status']):
                        if len([c for c in row_text_lower.split() if c in ['document', 'service', 'date']]) >= 2:
                            continue
                    doc_rows.append(row)
                
                if doc_rows:
                    log(f"[CLEANUP] Found {len(doc_rows)} document row(s) in table")
            except Exception as e:
                log(f"[CLEANUP][WARN] Could not find rows: {e}")
                return False
            
            if not doc_rows:
                log("[CLEANUP] No document rows found.")
                return True
            
            cutoff_date = datetime.now() - timedelta(days=30)
            log(f"[CLEANUP] Looking for documents older than {cutoff_date.strftime('%m/%d/%Y')}")
            
            removed_count = 0
            skipped_count = 0
            
            # Process documents in a loop, re-finding rows after each deletion to avoid stale elements
            max_iterations = 100  # Safety limit
            iteration = 0
            
            while iteration < max_iterations:
                iteration += 1
                
                # Re-find all document rows (DOM changes after deletion)
                try:
                    all_rows = driver.find_elements(By.XPATH, "//table//tr[td]")
                    doc_rows = []
                    for row in all_rows:
                        row_text_lower = (row.text or "").lower()
                        if any(header in row_text_lower for header in ['document', 'service', 'date', 'author', 'status']):
                            if len([c for c in row_text_lower.split() if c in ['document', 'service', 'date']]) >= 2:
                                continue
                        doc_rows.append(row)
                except Exception as e:
                    log(f"[CLEANUP][WARN] Could not re-find rows: {e}")
                    break
                
                if not doc_rows:
                    log("[CLEANUP] No more document rows found.")
                    break
                
                # Find next document to delete
                found_one_to_delete = False
                
                for idx, row in enumerate(doc_rows, 1):
                    try:
                        # Find document name using exact element: <span class="documentNameSpan">Reassignment CK - no IA</span>
                        doc_name_span = None
                        doc_name = None
                        try:
                            doc_name_span = row.find_element(By.XPATH, ".//span[@class='documentNameSpan']")
                            doc_name = (doc_name_span.text or "").strip()
                        except Exception:
                            # Fallback: get row text
                            doc_name = (row.text or "").strip()
                        
                        if not doc_name:
                            continue
                        
                        doc_name_lower = doc_name.lower()
                        
                        # Filter based on mode (which tab we're in)
                        if mode == "ips":
                            # IPS tab: Remove BOTH "Reassignment" AND "IPS Reassignment" (all documents in IPS portal are IPS-related)
                            if not (doc_name_lower.startswith("reassignment") or doc_name_lower.startswith("ips reassignment")):
                                continue
                        else:
                            # Base tab: Only remove "Reassignment" (NOT "IPS Reassignment")
                            if not doc_name_lower.startswith("reassignment") or doc_name_lower.startswith("ips reassignment"):
                                continue
                        
                        log(f"[CLEANUP] Row {idx}: Found potential Reassignment document: '{doc_name}'")
                        
                        # Find date - try multiple strategies (prioritizing exact selector)
                        doc_date_str = None
                        
                        # Strategy 1: Try exact selector FIRST: <td class="v-align-top" style="padding-bottom: 6px;">8/21/2025</td>
                        try:
                            date_cell = row.find_element(By.XPATH, ".//td[@class='v-align-top' and contains(@style, 'padding-bottom')]")
                            date_text = (date_cell.text or "").strip()
                            if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_text):
                                doc_date_str = date_text
                                log(f"[CLEANUP] Row {idx}: Found date using exact selector: {doc_date_str}")
                        except Exception:
                            pass
                        
                        # Strategy 2: Search for td elements containing date patterns (fallback)
                        if not doc_date_str:
                            try:
                                date_cells = row.find_elements(By.XPATH, ".//td[contains(text(), '/202') or contains(text(), '/2025') or contains(text(), '/2024')]")
                                for cell in date_cells:
                                    cell_text = (cell.text or "").strip()
                                    if re.match(r'\d{1,2}/\d{1,2}/\d{4}', cell_text):
                                        doc_date_str = cell_text
                                        log(f"[CLEANUP] Row {idx}: Found date using pattern search: {doc_date_str}")
                                        break
                            except Exception:
                                pass
                        
                        # Strategy 3: Search all td elements for date pattern (last resort)
                        if not doc_date_str:
                            try:
                                date_cells = row.find_elements(By.XPATH, ".//td")
                                for cell in date_cells:
                                    cell_text = (cell.text or "").strip()
                                    if re.match(r'\d{1,2}/\d{1,2}/\d{4}', cell_text):
                                        doc_date_str = cell_text
                                        log(f"[CLEANUP] Row {idx}: Found date using all td search: {doc_date_str}")
                                        break
                            except Exception:
                                pass
                        
                        if not doc_date_str:
                            log(f"[CLEANUP][WARN] Row {idx}: Could not find date, skipping")
                            skipped_count += 1
                            continue
                        
                        try:
                            doc_date = datetime.strptime(doc_date_str, "%m/%d/%Y")
                        except ValueError:
                            try:
                                doc_date = datetime.strptime(doc_date_str, "%m/%d/%y")
                            except ValueError:
                                log(f"[CLEANUP][WARN] Row {idx}: Could not parse date '{doc_date_str}', skipping")
                                skipped_count += 1
                                continue
                        
                        days_old = (datetime.now() - doc_date).days
                        if days_old < 30:
                            log(f"[CLEANUP] Row {idx}: Document '{doc_name}' dated {doc_date_str} ({days_old} days old) is less than 30 days, skipping")
                            skipped_count += 1
                            continue
                        
                        log(f"[CLEANUP] Row {idx}: Document '{doc_name}' dated {doc_date_str} ({days_old} days old) is 30+ days old - will remove")
                        
                        # Find pencil icon using exact element: <div class="fa-icon pencil-alt" aria-hidden="true" style="font-size: 16px;"></div>
                        pencil_icon = None
                        try:
                            pencil_icon = row.find_element(By.XPATH, ".//div[@class='fa-icon pencil-alt' and @aria-hidden='true']")
                        except Exception:
                            try:
                                pencil_icon = row.find_element(By.XPATH, ".//div[contains(@class, 'fa-icon') and contains(@class, 'pencil-alt')]")
                            except Exception:
                                try:
                                    pencil_icon = row.find_element(By.XPATH, ".//*[contains(@class, 'pencil-alt')]")
                                except Exception:
                                    log(f"[CLEANUP][WARN] Row {idx}: Could not find pencil icon, skipping")
                                    skipped_count += 1
                                    continue
                        
                        if not pencil_icon:
                            log(f"[CLEANUP][WARN] Row {idx}: Pencil icon not found, skipping")
                            skipped_count += 1
                            continue
                        
                        try:
                            # Scroll into view first
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", pencil_icon)
                            time.sleep(0.3)
                            
                            # Use JavaScript click to avoid interception by dialogs
                            driver.execute_script("arguments[0].click();", pencil_icon)
                            log(f"[CLEANUP] Row {idx}: Clicked pencil icon via JavaScript")
                            time.sleep(0.8)  # Wait for dialog to appear
                                
                        except Exception as e:
                            log(f"[CLEANUP][WARN] Row {idx}: Failed to click pencil icon: {e}")
                            skipped_count += 1
                            # Try to close any dialogs that might be open
                            try:
                                close_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Close') or contains(text(), 'Cancel')]")
                                if close_btns:
                                    driver.execute_script("arguments[0].click();", close_btns[0])
                                    time.sleep(0.3)
                            except Exception:
                                pass
                            continue
                        
                        # Find Delete Document link using exact element: <a href="#" tabindex="0">Delete Document</a>
                        delete_link = None
                        try:
                            delete_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href='#' and @tabindex='0' and normalize-space()='Delete Document']")))
                        except Exception:
                            try:
                                delete_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Delete Document')]")))
                            except Exception:
                                pass
                        
                        if not delete_link:
                            log(f"[CLEANUP][WARN] Row {idx}: Failed to find 'Delete Document' link")
                            skipped_count += 1
                            try:
                                cancel_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close')]")
                                cancel_btn.click()
                                time.sleep(0.3)
                            except Exception:
                                pass
                            continue
                        
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", delete_link)
                            time.sleep(0.3)
                            # Use JavaScript click to avoid interception
                            driver.execute_script("arguments[0].click();", delete_link)
                            log(f"[CLEANUP] Row {idx}: Clicked 'Delete Document' via JavaScript")
                            time.sleep(0.8)  # Wait for next dialog to appear
                        except Exception as e:
                            log(f"[CLEANUP][WARN] Row {idx}: Failed to click 'Delete Document': {e}")
                            skipped_count += 1
                            try:
                                cancel_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close')]")
                                driver.execute_script("arguments[0].click();", cancel_btn)
                                time.sleep(0.3)
                            except Exception:
                                pass
                            continue
                        
                        # Find Delete File button using exact element: <input type="button" value="Delete File" tabindex="1">
                        delete_file_btn = None
                        try:
                            delete_file_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='button' and @value='Delete File' and @tabindex='1']")))
                        except Exception:
                            try:
                                delete_file_btn = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='button' and @value='Delete File']")))
                            except Exception:
                                log(f"[CLEANUP][WARN] Row {idx}: Failed to find 'Delete File' button")
                                skipped_count += 1
                                try:
                                    cancel_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close')]")
                                    driver.execute_script("arguments[0].click();", cancel_btn)
                                    time.sleep(0.3)
                                except Exception:
                                    pass
                                continue
                        
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", delete_file_btn)
                            time.sleep(0.3)
                            # Use JavaScript click to avoid interception
                            driver.execute_script("arguments[0].click();", delete_file_btn)
                            log(f"[CLEANUP] Row {idx}: Clicked 'Delete File' button via JavaScript - document removed")
                            removed_count += 1
                            found_one_to_delete = True
                            time.sleep(1.5)  # Wait for deletion to complete and page to update
                        except Exception as e:
                            log(f"[CLEANUP][WARN] Row {idx}: Failed to click 'Delete File' button: {e}")
                            skipped_count += 1
                            try:
                                cancel_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Cancel') or contains(text(), 'Close')]")
                                driver.execute_script("arguments[0].click();", cancel_btn)
                                time.sleep(0.3)
                            except Exception:
                                pass
                            continue
                        else:
                            # Successfully deleted - break out of inner loop to re-find rows (DOM changed)
                            break
                    
                    except Exception as e:
                        log(f"[CLEANUP][WARN] Row {idx}: Error processing row: {e}")
                        skipped_count += 1
                        continue
                
                # If we didn't find any document to delete in this iteration, we're done
                if not found_one_to_delete:
                    log("[CLEANUP] No more documents to delete found.")
                    break
            
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
    
    def _per_row_upload_action(self, mode, therapist: str, client_name: str, base_folder: str, full_name: str, is_ips_counselor: bool) -> bool:
        """Upload PDF for one row - uses exact filename from save folder"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        search_name = full_name if full_name and full_name.strip() else client_name
        log(f"[UPLOAD] Searching for PDF matching: '{search_name}' (IPS counselor: {is_ips_counselor})")
        
        pdf_path = _find_pdf_for_client(base_folder, search_name, is_ips_counselor)
        
        if not pdf_path and full_name and full_name != client_name:
            log(f"[UPLOAD] Not found with full name, trying: '{client_name}'")
            pdf_path = _find_pdf_for_client(base_folder, client_name, is_ips_counselor)
        
        if not pdf_path:
            log(f"[UPLOAD][ERR] No PDF found for '{search_name}' in '{base_folder}' (IPS counselor: {is_ips_counselor}).")
            return False
        
        # Get the exact filename (without path) for document naming
        pdf_filename = os.path.basename(pdf_path)
        # Remove .pdf extension for document name
        doc_name = os.path.splitext(pdf_filename)[0]
        
        log(f"[UPLOAD] Found PDF: {pdf_filename}")
        log(f"[UPLOAD] Will upload with document name: '{doc_name}'")
        
        # Click Upload Patient File button
        if not self._click_upload_patient_file(mode):
            return False
        
        # Fill upload popup with exact filename
        log(f"[UPLOAD] Document name: '{doc_name}'")
        return self._fill_upload_popup_and_submit(mode, pdf_path, doc_name)
    
    def _click_upload_patient_file(self, mode, timeout: int = 12):
        """Click 'Upload Patient File' button - EXACT match to reference uploader, NO JavaScript fallback"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            
            # Find button using exact element structure
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
            
            # Selenium click ONLY - NO JavaScript fallback (matches reference uploader)
            try:
                btn.click()
                log("[DOCS] Clicked 'Upload Patient File'.")
            except Exception as e:
                # Click may have succeeded but element became stale - check if dialog appeared
                log(f"[DOCS][WARN] Click exception: {e}, checking if dialog appeared...")
                time.sleep(0.3)
                try:
                    # Check if upload dialog appeared (means click worked)
                    dialog_check = driver.find_elements(By.XPATH, "//input[@id='InputUploader' or @name='InputUploader']")
                    if dialog_check:
                        log("[DOCS] Click succeeded (dialog appeared despite exception).")
                    else:
                        log(f"[DOCS][ERR] Click failed and dialog did not appear: {e}")
                        return False
                except Exception:
                    log(f"[DOCS][ERR] Could not verify click: {e}")
                    return False
            
            time.sleep(0.4)
            return True
        except Exception as e:
            # Even if there's an error, check if dialog appeared (click may have worked)
            log(f"[DOCS][WARN] Error in click function: {e}, checking if dialog appeared...")
            try:
                time.sleep(0.3)
                dialog_check = driver.find_elements(By.XPATH, "//input[@id='InputUploader' or @name='InputUploader']")
                if dialog_check:
                    log("[DOCS] Dialog appeared - proceeding despite error.")
                    return True
            except Exception:
                pass
            log(f"[DOCS][ERR] {e}")
            return False
    
    def _fill_upload_popup_and_submit(self, mode, pdf_path: str, doc_name: str, timeout: int = 15):
        """Fill upload popup and submit - simplified to match reference uploader"""
        driver = self.base_driver if mode == "base" else self.ips_driver
        log = self.base_log if mode == "base" else self.ips_log
        
        try:
            webdriver, By, WebDriverWait, EC, Service, ChromeDriverManager, Keys = _lazy_import_selenium()
            wait = WebDriverWait(driver, timeout)
            
            # Step 1: Find and set file input
            file_input = None
            for by, val in [(By.ID, "InputUploader"), (By.XPATH, "//input[@type='file']")]:
                try: 
                    file_input = wait.until(EC.presence_of_element_located((by, val))); break
                except Exception: pass
            
            if not file_input:
                log("[UPLOAD][ERR] File chooser not found."); return False
            
            try:
                file_input.send_keys(pdf_path)
                log(f"[UPLOAD] Chosen file: {os.path.basename(pdf_path)}")
            except Exception as e:
                log(f"[UPLOAD][WARN] send_keys failed: {e}, trying JavaScript...")
                try:
                    driver.execute_script("""
                        var input = document.getElementById('InputUploader');
                        if (input) {
                            input.value = arguments[0];
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    """, pdf_path)
                    log(f"[UPLOAD] Set file via JavaScript: {os.path.basename(pdf_path)}")
                except Exception as js_e:
                    log(f"[UPLOAD][WARN] JavaScript also failed: {js_e}, but continuing...")
            
            # Step 2: Find and set document name
            name_input = None
            for by, val in [(By.ID, "PatientFile__DocumentName"), (By.XPATH, "//input[contains(@id, 'DocumentName')]")]:
                try: 
                    name_input = wait.until(EC.element_to_be_clickable((by, val))); break
                except Exception: pass
            
            if not name_input:
                log("[UPLOAD][ERR] Document Name input not found."); return False
            
            try: 
                name_input.clear()
            except Exception: 
                pass
            
            try:
                name_input.send_keys(doc_name)
                log(f"[UPLOAD] Set document name: {doc_name}")
            except Exception as e:
                log(f"[UPLOAD][WARN] send_keys failed: {e}, trying JavaScript...")
                try:
                    driver.execute_script("""
                        var input = document.getElementById('PatientFile__DocumentName');
                        if (input) {
                            input.value = '';
                            input.value = arguments[0];
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    """, doc_name)
                    log(f"[UPLOAD] Set document name via JavaScript: {doc_name}")
                except Exception as js_e:
                    log(f"[UPLOAD][WARN] JavaScript also failed: {js_e}, but continuing...")
            
            # Step 3: Click away to unblur (like reference)
            try:
                h2 = driver.find_element(By.XPATH, "//h2[contains(normalize-space(),'Upload')]")
                h2.click()
                time.sleep(0.2)
            except Exception: 
                pass
            
            # Step 4: Click radio button (always click to enable Add Document button)
            radio_btn = None
            for by, val in [
                (By.ID, "InputAdminDocumentType"),
                (By.NAME, "documentType"),
                (By.XPATH, "//input[@type='radio' and @id='InputAdminDocumentType']"),
            ]:
                try: 
                    radio_btn = wait.until(EC.element_to_be_clickable((by, val))); break
                except Exception: pass
            
            if radio_btn:
                try:
                    radio_btn.click()
                    log("[UPLOAD] Clicked radio button")
                    time.sleep(0.2)
                except Exception:
                    try:
                        driver.execute_script("arguments[0].click();", radio_btn)
                        log("[UPLOAD] Clicked radio button via JavaScript")
                        time.sleep(0.2)
                    except Exception:
                        pass
            
            # Step 5: Find and click Add Document button
            add_btn = None
            for by, val in [
                (By.XPATH, "//input[@type='button' and @value='Add Document']"),
                (By.XPATH, "//button[contains(normalize-space(),'Add Document')]")
            ]:
                try: 
                    add_btn = wait.until(EC.element_to_be_clickable((by, val))); break
                except Exception: pass
            
            if not add_btn:
                log("[UPLOAD][ERR] 'Add Document' button not found."); return False
            
            try: 
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_btn)
            except Exception: 
                pass
            
            try: 
                add_btn.click()
            except Exception:
                try: 
                    driver.execute_script("arguments[0].click();", add_btn)
                except Exception as e:
                    log(f"[UPLOAD][ERR] Failed to click Add Document: {e}"); return False
            
            log("[UPLOAD] Clicked 'Add Document'.")
            time.sleep(0.8)  # Wait for upload to process
            
            # Verify upload completed by checking if popup closed (optimized: exit early)
            try:
                max_wait = 5  # Reduced from 10
                wait_start = time.time()
                while time.time() - wait_start < max_wait:
                    try:
                        popup = driver.find_element(By.XPATH, "//input[@type='button' and @value='Add Document']")
                        if not popup.is_displayed():
                            log("[UPLOAD] Popup closed - upload likely completed")
                            break
                    except Exception:
                        log("[UPLOAD] Popup closed - upload likely completed")
                        break
                    time.sleep(0.3)  # Reduced from 0.5
                
                time.sleep(0.2)  # Reduced from 0.5
                log("[UPLOAD] Upload process completed")
            except Exception as e:
                log(f"[UPLOAD][WARN] Could not verify upload completion: {e}")
            
            return True
        except Exception as e:
            log(f"[UPLOAD][ERR] {e}")
            import traceback
            log(f"[UPLOAD][ERR] Traceback: {traceback.format_exc()}")
            return False
    
    def _auto_run(self):
        """Auto-run the uploader based on CLI arguments"""
        if self.cli_tab == "base":
            self.notebook.select(0)  # Select base tab
            # Ensure CSV file is set
            if self.cli_csv_file and not self.base_csv.get():
                self.base_csv.set(self.cli_csv_file)
            if self.cli_pdf_folder and not self.base_folder.get():
                self.base_folder.set(self.cli_pdf_folder)
            self._maybe_enable_buttons()
            self.after(1000, lambda: self.on_base_run_all())
        else:
            self.notebook.select(1)  # Select IPS tab
            # Ensure CSV file is set
            if self.cli_csv_file and not self.ips_csv.get():
                self.ips_csv.set(self.cli_csv_file)
            if self.cli_pdf_folder and not self.ips_folder.get():
                self.ips_folder.set(self.cli_pdf_folder)
            self._maybe_enable_buttons()
            self.after(1000, lambda: self.on_ips_run_all())
    
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
    parser = argparse.ArgumentParser(description='Existing Client Referral Form Uploader - Dual Tab')
    parser.add_argument('--csv-file', type=str, help='Path to CSV/Excel input file')
    parser.add_argument('--pdf-folder', type=str, help='Path to PDF folder')
    parser.add_argument('--tn-username', type=str, help='TherapyNotes username')
    parser.add_argument('--tn-password', type=str, help='TherapyNotes password')
    parser.add_argument('--remove-old-docs', action='store_true', help='Remove old documents (30+ days)')
    parser.add_argument('--tab', type=str, choices=['base', 'ips'], default='base', help='Which tab to run (base or ips)')
    parser.add_argument('--auto-run', action='store_true', help='Auto-run the uploader')
    
    args = parser.parse_args()
    
    app = DualTabUploader(
        csv_file=args.csv_file,
        pdf_folder=args.pdf_folder,
        tn_username=args.tn_username,
        tn_password=args.tn_password,
        remove_old_docs=args.remove_old_docs,
        tab=args.tab,
        auto_run=args.auto_run
    )
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
