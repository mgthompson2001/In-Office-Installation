#!/usr/bin/env python3
"""
Medisoft/Penelope Data Synthesizer

This bot synthesizes data from a PDF report and an Excel spreadsheet to create
a combined output Excel document. It matches records based on Chart column
(from PDF) and PT code Column E (from Excel), and combines all relevant information
including Date of Service, Penelope ID, DOB, modifiers, counselor names, supervisor, etc.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import logging
from pathlib import Path
import threading
import queue
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
import re

# Optional dependencies
try:
    import pandas as pd
    EXCEL_AVAILABLE = True
except ImportError:
    pd = None
    EXCEL_AVAILABLE = False

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    openpyxl = None
    OPENPYXL_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    pdfplumber = None
    PDFPLUMBER_AVAILABLE = False

# Configure logging
SCRIPT_DIR = Path(__file__).parent
LOG_FILE_PATH = SCRIPT_DIR / "medisoft_penelope_data_synthesizer.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MedisoftPenelopeDataSynthesizer:
    """Main bot class for synthesizing PDF and Excel data"""
    
    def __init__(self):
        self.root: tk.Tk | None = None
        self.log_text: scrolledtext.ScrolledText | None = None
        self.gui_log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._gui_log_dispatcher_active = False
        
        # File paths
        self.pdf_path: Path | None = None
        self.excel_path: Path | None = None
        self.output_path: Path | None = None
        
        # Data storage
        self.pdf_data: List[Dict[str, Any]] = []
        self.excel_data: List[Dict[str, Any]] = []
        self.matched_data: List[Dict[str, Any]] = []
        
        # Processing control
        self.processing = False
        self.stop_requested = False
        
    def create_gui(self):
        """Create the GUI interface"""
        self.root = tk.Tk()
        self.root.title("Medisoft/Penelope Data Synthesizer - Version 3.1.0, Last Updated 12/04/2025")
        self.root.geometry("900x700")
        
        # Header
        header = tk.Frame(self.root, bg="#660000")
        header.pack(fill="x")
        tk.Label(header, text="Medisoft/Penelope Data Synthesizer", bg="#660000", fg="white",
                 font=("Segoe UI", 14, "bold"), pady=8).pack(side="left", padx=12)
        
        # Main content
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=25, pady=25)
        
        # Instructions
        instructions = tk.Label(main_frame,
                               text="This bot synthesizes data from a PDF report and an Excel spreadsheet.\n"
                                    "It matches records based on Chart column (PDF) and PT code Column E (Excel).",
                               font=("Segoe UI", 10),
                               wraplength=850,
                               justify="left")
        instructions.pack(pady=(0, 20))
        
        # File selection frame
        file_frame = tk.LabelFrame(main_frame, text="File Selection", font=("Segoe UI", 10, "bold"))
        file_frame.pack(fill="x", pady=(0, 15))
        
        # PDF file selection
        pdf_frame = tk.Frame(file_frame)
        pdf_frame.pack(fill="x", padx=15, pady=10)
        
        tk.Label(pdf_frame, text="PDF Report:", font=("Segoe UI", 9, "bold"), width=15, anchor="w").pack(side="left")
        self.pdf_entry = tk.Entry(pdf_frame, font=("Segoe UI", 9), state="readonly")
        self.pdf_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        tk.Button(pdf_frame, text="Browse", command=self._browse_pdf,
                 bg="#660000", fg="white", font=("Segoe UI", 9), padx=10).pack(side="left")
        self.pdf_status_label = tk.Label(pdf_frame, text="No PDF selected", fg="#666666", font=("Segoe UI", 8))
        self.pdf_status_label.pack(side="left", padx=(5, 0))
        
        # Excel file selection
        excel_frame = tk.Frame(file_frame)
        excel_frame.pack(fill="x", padx=15, pady=10)
        
        tk.Label(excel_frame, text="Excel File:", font=("Segoe UI", 9, "bold"), width=15, anchor="w").pack(side="left")
        self.excel_entry = tk.Entry(excel_frame, font=("Segoe UI", 9), state="readonly")
        self.excel_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        tk.Button(excel_frame, text="Browse", command=self._browse_excel,
                 bg="#660000", fg="white", font=("Segoe UI", 9), padx=10).pack(side="left")
        self.excel_status_label = tk.Label(excel_frame, text="No Excel selected", fg="#666666", font=("Segoe UI", 8))
        self.excel_status_label.pack(side="left", padx=(5, 0))
        
        # Output file selection
        output_frame = tk.Frame(file_frame)
        output_frame.pack(fill="x", padx=15, pady=10)
        
        tk.Label(output_frame, text="Output Excel:", font=("Segoe UI", 9, "bold"), width=15, anchor="w").pack(side="left")
        self.output_entry = tk.Entry(output_frame, font=("Segoe UI", 9))
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(5, 5))
        tk.Button(output_frame, text="Browse", command=self._browse_output,
                 bg="#660000", fg="white", font=("Segoe UI", 9), padx=10).pack(side="left")
        
        # Control buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(10, 15))
        
        self.process_button = tk.Button(button_frame, text="Synthesize Data", command=self._start_processing,
                                       bg="#660000", fg="white", font=("Segoe UI", 11, "bold"),
                                       padx=20, pady=10, cursor="hand2")
        self.process_button.pack(side="left", padx=(0, 10))
        
        self.stop_button = tk.Button(button_frame, text="Stop", command=self._stop_processing,
                                     bg="#dc3545", fg="white", font=("Segoe UI", 11, "bold"),
                                     padx=20, pady=10, cursor="hand2", state="disabled")
        self.stop_button.pack(side="left")
        
        # Status label
        self.status_label = tk.Label(main_frame, text="Ready. Select files and click 'Synthesize Data'.", 
                                     font=("Segoe UI", 9), fg="gray")
        self.status_label.pack(pady=(0, 10))
        
        # Log area
        log_frame = tk.LabelFrame(main_frame, text="Activity Log", font=("Segoe UI", 10, "bold"))
        log_frame.pack(fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=("Consolas", 9),
                                                  wrap=tk.WORD, bg="#f8f9fa", fg="#212529")
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Start GUI log dispatcher
        self._start_gui_log_dispatcher()
        
    def _start_gui_log_dispatcher(self):
        """Start the GUI log dispatcher thread"""
        if self._gui_log_dispatcher_active:
            return
        self._gui_log_dispatcher_active = True
        
        def dispatcher():
            while self._gui_log_dispatcher_active:
                try:
                    msg, color = self.gui_log_queue.get(timeout=0.1)
                    if self.log_text:
                        self.log_text.insert(tk.END, msg + "\n", color)
                        self.log_text.see(tk.END)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"GUI log dispatcher error: {e}")
        
        thread = threading.Thread(target=dispatcher, daemon=True)
        thread.start()
    
    def gui_log(self, message: str, color: str = "black"):
        """Log a message to the GUI"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        self.gui_log_queue.put((formatted_msg, color))
        logger.info(message)
    
    def _browse_pdf(self):
        """Browse for PDF file"""
        file_path = filedialog.askopenfilename(
            title="Select PDF Report",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if file_path:
            self.pdf_path = Path(file_path)
            self.pdf_entry.config(state="normal")
            self.pdf_entry.delete(0, tk.END)
            self.pdf_entry.insert(0, str(self.pdf_path))
            self.pdf_entry.config(state="readonly")
            self.pdf_status_label.config(text=f"Selected: {self.pdf_path.name}", fg="#28a745")
            self.gui_log(f"📄 PDF selected: {self.pdf_path.name}")
    
    def _browse_excel(self):
        """Browse for Excel file"""
        file_path = filedialog.askopenfilename(
            title="Select Excel File",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if file_path:
            self.excel_path = Path(file_path)
            self.excel_entry.config(state="normal")
            self.excel_entry.delete(0, tk.END)
            self.excel_entry.insert(0, str(self.excel_path))
            self.excel_entry.config(state="readonly")
            self.excel_status_label.config(text=f"Selected: {self.excel_path.name}", fg="#28a745")
            self.gui_log(f"📊 Excel selected: {self.excel_path.name}")
    
    def _browse_output(self):
        """Browse for output file location"""
        file_path = filedialog.asksaveasfilename(
            title="Save Output Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if file_path:
            self.output_path = Path(file_path)
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, str(self.output_path))
            self.gui_log(f"💾 Output file: {self.output_path.name}")
    
    def _start_processing(self):
        """Start the data synthesis process"""
        if not self.pdf_path or not self.excel_path:
            messagebox.showwarning("Missing Files", 
                                 "Please select both PDF and Excel files before processing.")
            return
        
        if not self.output_path:
            # Auto-generate output path
            output_dir = self.pdf_path.parent
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.output_path = output_dir / f"Synthesized_Data_{timestamp}.xlsx"
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, str(self.output_path))
            self.gui_log(f"💾 Auto-generated output file: {self.output_path.name}")
        
        if self.processing:
            messagebox.showinfo("Already Processing", "Data synthesis is already in progress.")
            return
        
        # Reset stop flag
        self.stop_requested = False
        
        # Disable process button, enable stop button
        self.process_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="Processing...", fg="blue")
        
        # Start processing in separate thread
        thread = threading.Thread(target=self._process_thread, daemon=True)
        thread.start()
    
    def _stop_processing(self):
        """Stop the processing"""
        self.stop_requested = True
        self.gui_log("⏹️ Stop requested...", "orange")
    
    def _process_thread(self):
        """Process data in a separate thread"""
        try:
            self.processing = True
            self.gui_log("=" * 60)
            self.gui_log("Starting data synthesis process...")
            
            # Step 1: Parse PDF
            if self.stop_requested:
                return
            self.gui_log("📄 Step 1: Parsing PDF report...")
            self._parse_pdf()
            
            if self.stop_requested:
                self.gui_log("⏹️ Processing stopped by user")
                return
            
            # Step 2: Parse Excel
            self.gui_log("📊 Step 2: Parsing Excel file...")
            self._parse_excel()
            
            if self.stop_requested:
                self.gui_log("⏹️ Processing stopped by user")
                return
            
            # Step 3: Match records
            self.gui_log("🔗 Step 3: Matching records...")
            self._match_records()
            
            if self.stop_requested:
                self.gui_log("⏹️ Processing stopped by user")
                return
            
            # Step 4: Generate output
            self.gui_log("💾 Step 4: Generating output Excel...")
            self._generate_output()
            
            self.gui_log("=" * 60)
            self.gui_log(f"✅ Data synthesis completed successfully!", "green")
            self.gui_log(f"📁 Output saved to: {self.output_path}")
            
            self.root.after(0, lambda: self._processing_complete(True))
            
        except Exception as e:
            error_msg = f"❌ Error during processing: {str(e)}"
            self.gui_log(error_msg, "red")
            logger.exception("Processing error")
            self.root.after(0, lambda: self._processing_complete(False, str(e)))
    
    def _processing_complete(self, success: bool, error: str = ""):
        """Called when processing completes"""
        self.processing = False
        self.process_button.config(state="normal")
        self.stop_button.config(state="disabled")
        
        if success:
            self.status_label.config(text="Processing completed successfully!", fg="#28a745")
            messagebox.showinfo("Success", 
                              f"Data synthesis completed!\n\nOutput saved to:\n{self.output_path}")
        else:
            self.status_label.config(text=f"Processing failed: {error}", fg="#dc3545")
            messagebox.showerror("Error", f"Processing failed:\n{error}")
    
    def _parse_pdf(self):
        """Parse PDF and extract data"""
        if not PDFPLUMBER_AVAILABLE:
            raise Exception("pdfplumber is not available. Please install it with: pip install pdfplumber")
        
        self.pdf_data = []
        
        try:
            with pdfplumber.open(str(self.pdf_path)) as pdf:
                total_pages = len(pdf.pages)
                self.gui_log(f"   Found {total_pages} page(s)")
                
                pages_with_data = 0
                pages_without_tables = 0
                total_tables = 0
                total_table_rows = 0
                total_rows_processed = 0
                total_rows_skipped = 0
                
                # Extract tables from all pages
                for page_num, page in enumerate(pdf.pages, 1):
                    if self.stop_requested:
                        return
                    
                    # Try to extract tables
                    tables = page.extract_tables()
                    
                    if tables and len(tables) > 0:
                        pages_with_data += 1
                        total_tables += len(tables)
                        
                        if page_num <= 3 or page_num % 20 == 0:
                            self.gui_log(f"   Page {page_num}: Found {len(tables)} table(s)")
                        
                        for table_idx, table in enumerate(tables):
                            if not table or len(table) == 0:
                                continue
                            
                            total_table_rows += len(table)
                            
                            # First row should be headers
                            if len(table) < 2:
                                continue
                            
                            headers = [str(cell).strip() if cell else "" for cell in table[0]]
                            
                            # Check if header is concatenated in first column (common PDF extraction issue)
                            # Example: "Date of Service Chart Case Diagnosis Code Modifier Provider Amount"
                            header_text = headers[0] if headers else ""
                            if header_text and "\n" in header_text:
                                # Header is in first column - need to parse it
                                header_parts = [h.strip() for h in header_text.split("\n") if h.strip()]
                                # Last line usually contains column names
                                if header_parts:
                                    last_line = header_parts[-1]
                                    # Split by common separators or spaces
                                    potential_headers = [h.strip() for h in last_line.replace("Date of Service", "Date_of_Service").split()]
                                    if page_num == 1 and table_idx == 0:
                                        self.gui_log(f"   📋 Parsed header from first column: {potential_headers}")
                            
                            # Analyze first few data rows to find where actual data columns are
                            # Often PDFs have data in specific columns but with empty columns in between
                            data_row_sample = None
                            for i in range(1, min(4, len(table))):
                                row = table[i]
                                if row and any(cell and str(cell).strip() for cell in row):
                                    data_row_sample = row
                                    break
                            
                            # Find columns with actual data by checking data rows
                            data_columns = {}  # {col_idx: [sample values]}
                            if data_row_sample:
                                for col_idx, cell in enumerate(data_row_sample):
                                    cell_str = str(cell).strip() if cell else ""
                                    if cell_str and cell_str not in ['', 'None', 'nan']:
                                        if col_idx not in data_columns:
                                            data_columns[col_idx] = []
                                        data_columns[col_idx].append(cell_str)
                            
                            # Find Chart/PT Code column by checking which column contains PT code patterns
                            use_col_idx = None
                            chart_col_idx = None
                            date_col_idx = None
                            
                            # Check columns with data for PT code patterns
                            pt_code_pattern = re.compile(r'^[A-Z]{2,7}\d{3,}$')
                            for col_idx, samples in data_columns.items():
                                for sample in samples[:3]:  # Check first 3 samples
                                    sample_upper = sample.upper().strip()
                                    # Check if it looks like a PT code
                                    if pt_code_pattern.match(sample_upper):
                                        use_col_idx = col_idx
                                        chart_col_idx = col_idx
                                        break
                                    # Check if it's a date (might be Date column)
                                    if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', sample):
                                        date_col_idx = col_idx
                                if use_col_idx is not None:
                                    break
                            
                            # If not found by pattern, try to find Chart column from header or position
                            if use_col_idx is None:
                                # Often Chart is around column 4 based on the structure we saw
                                # Check columns 1-10 for PT code patterns in multiple rows
                                for test_col in range(1, min(11, len(data_row_sample) if data_row_sample else 11)):
                                    pt_code_count = 0
                                    for test_row_idx in range(1, min(6, len(table))):
                                        if test_row_idx >= len(table):
                                            break
                                        test_row = table[test_row_idx]
                                        if test_row and test_col < len(test_row):
                                            test_val = str(test_row[test_col]).strip() if test_row[test_col] else ""
                                            if pt_code_pattern.match(test_val.upper()):
                                                pt_code_count += 1
                                    if pt_code_count >= 2:  # Found PT codes in at least 2 rows
                                        use_col_idx = test_col
                                        chart_col_idx = test_col
                                        break
                            
                            if page_num == 1 and table_idx == 0:
                                self.gui_log(f"   📋 Data columns found: {sorted(data_columns.keys())}")
                                if data_row_sample:
                                    sample_structure = []
                                    for i in range(min(15, len(data_row_sample))):
                                        if i < len(data_row_sample) and data_row_sample[i]:
                                            cell_str = str(data_row_sample[i])[:20]
                                            sample_structure.append(f'Col{i}:{cell_str}')
                                    self.gui_log(f"   📋 Sample data row structure: {sample_structure}")
                            
                            if use_col_idx is None:
                                # Fallback: Use Column 4 (known structure from PDF analysis)
                                # Column 4 always contains PT codes in this PDF format
                                if data_row_sample and len(data_row_sample) > 4:
                                    use_col_idx = 4
                                    chart_col_idx = 4
                                    self.gui_log(f"   ⚠️  PT Code column not found via pattern, using default Column 4 for table {table_idx + 1} on page {page_num}")
                                else:
                                    self.gui_log(f"   ⚠️  Warning: Chart/PT Code column not found and no data in Column 4 for table {table_idx + 1} on page {page_num}")
                                    if page_num == 1 and table_idx == 0:
                                        self.gui_log(f"   Available data columns: {sorted(data_columns.keys())}")
                                    # Only skip if we truly can't process
                                    continue
                            
                            # Only log once per page to avoid spam
                            if table_idx == 0:
                                self.gui_log(f"   Found Chart/PT Code column at index {use_col_idx} (page {page_num})")
                            
                            # Count rows before processing
                            data_rows = [r for r in table[1:] if r and len(r) > use_col_idx and r[use_col_idx]]
                            if page_num == 1 and table_idx == 0:
                                self.gui_log(f"   Table {table_idx + 1} on page {page_num}: {len(data_rows)} data row(s) with PT codes (total table rows: {len(table)})")
                            
                            # Process data rows - get ALL rows, don't skip any
                            rows_processed = 0
                            rows_skipped = 0
                            
                            # IMPORTANT: Process ALL rows including row 1 (which might have concatenated data)
                            # Start from index 1 (which is row 2 in Excel, since index 0 is header)
                            for row_idx, row in enumerate(table[1:], start=2):
                                if self.stop_requested:
                                    return
                                
                                # Skip completely empty rows (no cells at all)
                                if not row:
                                    rows_skipped += 1
                                    continue
                                
                                # Check if row has any data at all
                                # Be very lenient - include rows with ANY non-empty cell
                                has_data = False
                                for cell in row:
                                    if cell and str(cell).strip():
                                        has_data = True
                                        break
                                
                                if not has_data:
                                    rows_skipped += 1
                                    continue
                                
                                # Create row dictionary - store by column index for reliable access
                                row_dict = {}
                                
                                # Store all columns by index for reliable access
                                for col_idx in range(len(row)):
                                    value = row[col_idx]
                                    col_key = f"Col_{col_idx}"
                                    if value is not None:
                                        val_str = str(value).strip()
                                        row_dict[col_key] = val_str
                                    else:
                                        row_dict[col_key] = ""
                                
                                # Extract PT Code/Chart value based on known structure
                                # Column 4 contains PT Code (ABDEL000, ABRAN000, etc.)
                                chart_value = ""
                                
                                # Method 1: Check Column 4 first (this is where PT codes are in this PDF)
                                if 4 < len(row) and row[4]:
                                    potential = str(row[4]).strip().upper()
                                    if re.match(r'^[A-Z]{2,7}\d{3,}$', potential):
                                        chart_value = potential
                                
                                # Method 2: Check row 1 (index 1) - it might have concatenated data in column 0
                                if not chart_value and row_idx == 2 and len(row) > 0 and row[0]:
                                    concatenated = str(row[0]).strip()
                                    if len(concatenated) > 50:  # Likely concatenated
                                        pt_code_pattern_match = r'\b([A-Z]{2,7}\d{3,})\b'
                                        matches = re.findall(pt_code_pattern_match, concatenated.upper())
                                        if matches:
                                            chart_value = matches[0]
                                
                                # Method 3: Search all columns for PT code pattern (fallback)
                                if not chart_value:
                                    for col_idx, cell in enumerate(row[:15]):  # Check first 15 columns
                                        if cell:
                                            potential = str(cell).strip().upper()
                                            if re.match(r'^[A-Z]{2,7}\d{3,}$', potential):
                                                chart_value = potential
                                                break
                                
                                chart_value = chart_value.strip()
                                
                                # Extract other fields based on KNOWN column positions from PDF structure analysis
                                # Column 1: Date of Service (MM/DD/YYYY format)
                                date_of_service = ""
                                if 1 < len(row) and row[1]:
                                    date_val = str(row[1]).strip()
                                    # Validate it's a date
                                    if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{4}$', date_val):
                                        date_of_service = date_val
                                # If not found and this is row 1 (concatenated), extract from column 0
                                if not date_of_service and row_idx == 2 and row[0] and len(str(row[0]).strip()) > 50:
                                    concatenated = str(row[0]).strip()
                                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', concatenated)
                                    if date_match:
                                        date_of_service = date_match.group(1)
                                
                                # Column 4: Chart/PT Code (already extracted above as chart_value)
                                # Column 6: Case Number (5-digit number like 27034, 32422)
                                case_num = ""
                                if 6 < len(row) and row[6]:
                                    case_val = str(row[6]).strip()
                                    # Validate it's a 5-digit number (Case number)
                                    if case_val.isdigit() and len(case_val) == 5:
                                        case_num = case_val
                                
                                # Column 8: Diagnosis Code (1-digit number like "1")
                                diagnosis_code = ""
                                if 8 < len(row) and row[8]:
                                    diag_val = str(row[8]).strip()
                                    # Validate it's a 1-digit number
                                    if diag_val.isdigit() and len(diag_val) == 1:
                                        diagnosis_code = diag_val
                                
                                # Procedure Code extraction - can be in multiple columns
                                # Some PDF rows have procedure in Column 10, others in Column 11, or Column 12
                                procedure_code = ""
                                
                                # Check multiple columns for 5-digit procedure codes
                                # Priority order: Column 10, Column 11, Column 12
                                for col_idx in [10, 11, 12]:
                                    if col_idx < len(row) and row[col_idx]:
                                        proc_val = str(row[col_idx]).strip()
                                        # Validate it's a 5-digit procedure code
                                        if proc_val.isdigit() and len(proc_val) == 5:
                                            procedure_code = proc_val
                                            break  # Found it, stop looking
                                
                                # Column 12 OR 13 OR 14: Modifier (can be in multiple columns)
                                # Some PDF pages have modifiers in Column 12, others in Column 13 or 14
                                # IMPORTANT: Column 12 can contain either a 5-digit procedure code OR a 1-2 digit modifier
                                # If we found a 5-digit code in Column 12, the modifier is likely in Column 13 or 14
                                modifier = ""
                                
                                # Check columns in order, but skip Column 12 if we already found a procedure code there
                                modifier_cols = [12, 13, 14] if not (procedure_code and 12 < len(row) and str(row[12]).strip() == procedure_code) else [13, 14, 12]
                                
                                for col_idx in modifier_cols:
                                    if col_idx < len(row) and row[col_idx]:
                                        mod_val = str(row[col_idx]).strip()
                                        # Validate it's a modifier (1-2 digits, or alphanumeric like "95", "F1", etc.)
                                        # But NOT a 5-digit procedure code (that's handled above)
                                        if mod_val and len(mod_val) <= 3:
                                            if re.match(r'^[0-9]{1,2}$|^[A-Z][0-9]$', mod_val.upper()):
                                                # Make sure it's not a 5-digit code we missed
                                                if not (mod_val.isdigit() and len(mod_val) == 5):
                                                    modifier = mod_val
                                                    break  # Found it, stop looking
                                
                                # Column 14: Provider/Counselor (2-4 letters like "LK", "MM", "NL")
                                provider = ""
                                if 14 < len(row) and row[14]:
                                    prov_val = str(row[14]).strip()
                                    # Validate it's a provider code (2-4 uppercase letters)
                                    if re.match(r'^[A-Z]{1,4}$', prov_val.upper()) and len(prov_val) <= 4:
                                        provider = prov_val
                                
                                # Column 18: Amount (decimal number like "180.00")
                                amount = ""
                                if 18 < len(row) and row[18]:
                                    amount_val = str(row[18]).strip()
                                    # Validate it's an amount (decimal number)
                                    if re.match(r'^\d+\.\d{2}$', amount_val):
                                        amount = amount_val
                                
                                # Store extracted fields in row_dict with standard names
                                row_dict['Date of Service'] = date_of_service
                                row_dict['Date_of_Service'] = date_of_service
                                row_dict['DOS'] = date_of_service
                                row_dict['Modifier'] = modifier
                                row_dict['Mod'] = modifier
                                row_dict['Provider'] = provider
                                row_dict['Counselor'] = provider
                                row_dict['Counselor Name'] = provider
                                row_dict['Procedure Code'] = procedure_code
                                row_dict['Case'] = case_num
                                row_dict['Case Number'] = case_num
                                row_dict['Diagnosis Code'] = diagnosis_code
                                row_dict['Amount'] = amount
                                
                                # Also store with column prefix for debugging
                                row_dict['Col_1_Date'] = date_of_service
                                row_dict['Col_4_PTCode'] = chart_value
                                row_dict['Col_6_Case'] = case_num
                                row_dict['Col_8_Diagnosis'] = diagnosis_code
                                row_dict['Col_10_Procedure'] = procedure_code
                                row_dict['Col_12_Modifier'] = modifier if 12 < len(row) and str(row[12]).strip() == modifier else ""
                                row_dict['Col_13_Modifier'] = modifier if 13 < len(row) and str(row[13]).strip() == modifier else ""
                                row_dict['Col_14_Provider'] = provider
                                row_dict['Col_18_Amount'] = amount
                                
                                # Always include the row, even if chart_value is empty (we'll mark it as unmatched)
                                row_dict['_chart_value'] = chart_value if chart_value else ""
                                row_dict['_page_num'] = page_num
                                row_dict['_row_num'] = row_idx
                                row_dict['_table_idx'] = table_idx
                                self.pdf_data.append(row_dict)
                                rows_processed += 1
                                
                                # Log progress every 500 rows
                                if rows_processed % 500 == 0:
                                    self.gui_log(f"   Processed {rows_processed} PDF rows so far...")
                            
                            # Accumulate totals
                            total_rows_processed += rows_processed
                            total_rows_skipped += rows_skipped
                            
                            # Log row counts per page/table
                            table_total_rows = len(table) - 1  # Excluding header
                            if page_num <= 3 or page_num % 20 == 0:
                                self.gui_log(f"   Page {page_num}, Table {table_idx + 1}: {table_total_rows} total rows, processed {rows_processed}, skipped {rows_skipped}")
                            
                            # Log total progress every 10 pages
                            if page_num % 10 == 0:
                                self.gui_log(f"   📊 Total PDF rows extracted so far: {len(self.pdf_data)} (through page {page_num})")
                    else:
                        pages_without_tables += 1
                        if page_num <= 5:
                            self.gui_log(f"   ⚠️  Page {page_num}: No tables found")
                
                # If no tables found, try text extraction
                if not self.pdf_data:
                    self.gui_log("   No tables found, attempting text extraction...")
                    self._parse_pdf_text(pdf)
                
                # Summary statistics
                expected_data_rows = total_table_rows - total_tables  # Subtract headers
                missing_rows = expected_data_rows - len(self.pdf_data)
                
                self.gui_log(f"   📊 PDF Extraction Summary:")
                self.gui_log(f"      Total pages: {total_pages}")
                self.gui_log(f"      Pages with tables: {pages_with_data}")
                self.gui_log(f"      Pages without tables: {pages_without_tables}")
                self.gui_log(f"      Total tables found: {total_tables}")
                self.gui_log(f"      Total table rows (including headers): {total_table_rows}")
                self.gui_log(f"      Expected data rows: {expected_data_rows} (table rows - headers)")
                self.gui_log(f"      Rows processed: {total_rows_processed}")
                self.gui_log(f"      Rows skipped: {total_rows_skipped}")
                self.gui_log(f"      Records extracted: {len(self.pdf_data)}")
                if missing_rows > 0:
                    self.gui_log(f"      ⚠️  Missing rows: {missing_rows} (expected {expected_data_rows}, got {len(self.pdf_data)})")
                self.gui_log(f"   ✅ Extracted {len(self.pdf_data)} record(s) from PDF")
                
                # Debug: Show sample data to verify extraction quality
                if self.pdf_data:
                    # Show sample of first 3 rows with key fields
                    self.gui_log(f"   📋 Sample extracted data (first 3 rows):")
                    for idx, row in enumerate(self.pdf_data[:3], 1):
                        chart = row.get('_chart_value', '')
                        date = row.get('Date_of_Service', '')
                        modifier = row.get('Modifier', '')
                        provider = row.get('Provider', '')
                        procedure = row.get('Procedure Code', '')
                        self.gui_log(f"      Row {idx}: PT={chart}, Date={date}, Modifier={modifier}, Provider={provider}, Procedure={procedure}")
                    
                    # Validate data quality
                    rows_with_modifiers = sum(1 for r in self.pdf_data if r.get('Modifier'))
                    rows_with_providers = sum(1 for r in self.pdf_data if r.get('Provider'))
                    rows_with_dates = sum(1 for r in self.pdf_data if r.get('Date_of_Service'))
                    rows_with_procedures = sum(1 for r in self.pdf_data if r.get('Procedure Code'))
                    
                    self.gui_log(f"   📊 Data quality check:")
                    self.gui_log(f"      Rows with modifiers: {rows_with_modifiers}/{len(self.pdf_data)}")
                    self.gui_log(f"      Rows with providers: {rows_with_providers}/{len(self.pdf_data)}")
                    self.gui_log(f"      Rows with dates: {rows_with_dates}/{len(self.pdf_data)}")
                    self.gui_log(f"      Rows with procedure codes: {rows_with_procedures}/{len(self.pdf_data)}")
                
        except Exception as e:
            raise Exception(f"Failed to parse PDF: {str(e)}")
    
    def _parse_pdf_text(self, pdf):
        """Parse PDF text when tables are not available"""
        # This is a fallback method - implementation depends on PDF structure
        # For now, we'll log a warning
        self.gui_log("   ⚠️  Text extraction mode - structure may vary")
        
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
        
        # Look for date of service patterns
        dos_pattern = r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})'
        dates = re.findall(dos_pattern, full_text)
        
        # This is a basic implementation - may need customization based on actual PDF structure
        self.gui_log("   ℹ️  Text extraction completed, but table extraction is recommended")
    
    def _parse_excel(self):
        """Parse Excel file and extract data"""
        if not EXCEL_AVAILABLE:
            raise Exception("pandas is not available. Please install it with: pip install pandas openpyxl")
        
        self.excel_data = []
        
        try:
            # Read Excel file
            df = pd.read_excel(str(self.excel_path), engine='openpyxl' if OPENPYXL_AVAILABLE else None)
            
            self.gui_log(f"   Loaded {len(df)} row(s) with {len(df.columns)} column(s)")
            
            # Get column names
            col_names = list(df.columns)
            
            # Column E is index 4 (0-indexed: A=0, B=1, C=2, D=3, E=4)
            if len(col_names) < 5:
                raise Exception("Excel file must have at least 5 columns (Column E not found)")
            
            pt_code_col = col_names[4]  # Column E
            self.gui_log(f"   PT code column (Column E): '{pt_code_col}'")
            
            # Look for Penelope ID column (could be in various columns)
            penelope_id_col = None
            dob_col = None
            
            for col_name in col_names:
                col_lower = str(col_name).lower()
                if "penelope" in col_lower and "id" in col_lower:
                    penelope_id_col = col_name
                    self.gui_log(f"   Found Penelope ID column: '{col_name}'")
                if "dob" in col_lower or "date of birth" in col_lower or "birth" in col_lower:
                    dob_col = col_name
                    self.gui_log(f"   Found DOB column: '{col_name}'")
            
            # Process each row
            for idx, row in df.iterrows():
                if self.stop_requested:
                    return
                
                # Extract PT code (Column E) - this is the matching key
                pt_code = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ""
                
                if not pt_code or pt_code.lower() in ['nan', 'none', '']:
                    continue
                
                # Create row dictionary with all columns
                row_dict = {}
                for col_idx, col_name in enumerate(col_names):
                    value = row.iloc[col_idx]
                    if pd.notna(value):
                        row_dict[col_name] = str(value).strip()
                    else:
                        row_dict[col_name] = ""
                
                # Store matching key
                row_dict['_pt_code'] = pt_code
                
                # Store Penelope ID and DOB if found
                if penelope_id_col:
                    row_dict['_penelope_id'] = row_dict.get(penelope_id_col, "")
                if dob_col:
                    dob_value = row_dict.get(dob_col, "")
                    # Format DOB to remove timestamp (e.g., "1947-06-22 00:00:00" -> "1947-06-22")
                    row_dict['_dob'] = self._format_dob(dob_value)
                
                row_dict['_excel_row'] = idx + 2  # Excel row number (1-indexed + header)
                
                self.excel_data.append(row_dict)
            
            self.gui_log(f"   ✅ Extracted {len(self.excel_data)} record(s) from Excel")
            
            # Debug: Show sample PT codes
            if self.excel_data:
                sample_pt_codes = [row.get('_pt_code', '') for row in self.excel_data[:5]]
                self.gui_log(f"   📋 Sample PT codes from Excel: {sample_pt_codes}")
            
        except Exception as e:
            raise Exception(f"Failed to parse Excel: {str(e)}")
    
    def _match_records(self):
        """Match records based on Chart (PDF) and PT code (Excel)"""
        self.matched_data = []
        
        match_count = 0
        pdf_unmatched = 0
        excel_unmatched = 0
        
        # Create a lookup dictionary for Excel data by PT code
        # Store both normalized and original values for flexible matching
        excel_lookup = {}
        excel_lookup_original = {}  # Also try direct string matching
        
        for excel_row in self.excel_data:
            pt_code = excel_row.get('_pt_code', '').strip()
            if pt_code:
                # Normalize PT code
                normalized = self._normalize_pt_code(pt_code)
                if normalized not in excel_lookup:
                    excel_lookup[normalized] = []
                excel_lookup[normalized].append(excel_row)
                
                # Also store original for direct matching
                if pt_code not in excel_lookup_original:
                    excel_lookup_original[pt_code] = []
                excel_lookup_original[pt_code].append(excel_row)
        
        self.gui_log(f"   Created lookup with {len(excel_lookup)} unique PT code(s)")
        
        # Debug: Show sample normalized values
        sample_pdf_normalized = []
        sample_excel_normalized = []
        for pdf_row in self.pdf_data[:5]:
            chart_val = pdf_row.get('_chart_value', '').strip()
            if chart_val:
                sample_pdf_normalized.append((chart_val, self._normalize_pt_code(chart_val)))
        for excel_row in self.excel_data[:5]:
            pt_code = excel_row.get('_pt_code', '').strip()
            if pt_code:
                sample_excel_normalized.append((pt_code, self._normalize_pt_code(pt_code)))
        
        self.gui_log(f"   🔍 Sample normalized values - PDF: {sample_pdf_normalized[:3]}")
        self.gui_log(f"   🔍 Sample normalized values - Excel: {sample_excel_normalized[:3]}")
        
        # Match PDF records with Excel records
        for pdf_row in self.pdf_data:
            if self.stop_requested:
                return
            
            chart_value = pdf_row.get('_chart_value', '').strip()
            
            if not chart_value:
                # Even if no chart value, include the PDF record with a note
                combined = {}
                # Add all PDF data
                for key, value in pdf_row.items():
                    if not key.startswith('_'):  # Skip internal fields
                        combined[f"PDF_{key}"] = value
                
                combined['Chart_Value'] = chart_value if chart_value else ''
                combined['Match_Status'] = 'No ODBC spreadsheet match was found'
                combined['PT_Code'] = ''
                combined['Penelope_ID'] = ''
                combined['DOB'] = ''
                combined['Date_of_Service'] = pdf_row.get('Date of Service', pdf_row.get('Date', pdf_row.get('DOS', '')))
                
                # Add modifier, counselor name, supervisor from PDF if available
                # Try multiple possible column names for modifier
                modifier = (pdf_row.get('Modifier') or pdf_row.get('Mod') or
                            pdf_row.get('Modifiers') or pdf_row.get('Modifier Code') or
                            pdf_row.get('Mod Code') or '')
                combined['Modifier'] = modifier
                
                # Try multiple possible column names for counselor
                counselor = (pdf_row.get('Counselor') or pdf_row.get('Counselor Name') or
                             pdf_row.get('Provider') or pdf_row.get('Therapist') or
                             pdf_row.get('Clinician') or '')
                combined['Counselor_Name'] = counselor
                
                # Try multiple possible column names for supervisor
                supervisor = (pdf_row.get('Supervisor') or pdf_row.get('Supervising') or
                              pdf_row.get('Supervisor Name') or pdf_row.get('Supervising Provider') or '')
                combined['Supervisor'] = supervisor
                
                self.matched_data.append(combined)
                pdf_unmatched += 1
                continue
            
            # Try multiple matching strategies
            matching_excel_rows = []
            
            # Strategy 1: Normalized matching
            normalized_chart = self._normalize_pt_code(chart_value)
            if normalized_chart in excel_lookup:
                matching_excel_rows.extend(excel_lookup[normalized_chart])
                if len(matching_excel_rows) > 0:
                    self.gui_log(f"   ✓ Strategy 1 (normalized) found match: '{chart_value}' -> '{normalized_chart}'")
            
            # Strategy 2: Direct string matching (if normalized didn't work)
            if not matching_excel_rows:
                if chart_value in excel_lookup_original:
                    matching_excel_rows.extend(excel_lookup_original[chart_value])
                    if len(matching_excel_rows) > 0:
                        self.gui_log(f"   ✓ Strategy 2 (direct string) found match: '{chart_value}'")
            
            # Strategy 3: Try without leading zeros for numeric values
            if not matching_excel_rows:
                try:
                    # If it's a number, try matching as integer
                    chart_num = int(chart_value)
                    chart_str_no_zeros = str(chart_num)
                    if chart_str_no_zeros in excel_lookup_original:
                        matching_excel_rows.extend(excel_lookup_original[chart_str_no_zeros])
                        if len(matching_excel_rows) > 0:
                            self.gui_log(f"   ✓ Strategy 3a (int conversion) found match: '{chart_value}' -> '{chart_str_no_zeros}'")
                    # Also try with normalized version
                    if not matching_excel_rows:
                        normalized_no_zeros = self._normalize_pt_code(chart_str_no_zeros)
                        if normalized_no_zeros in excel_lookup:
                            matching_excel_rows.extend(excel_lookup[normalized_no_zeros])
                            if len(matching_excel_rows) > 0:
                                self.gui_log(f"   ✓ Strategy 3b (normalized int) found match: '{chart_value}' -> '{normalized_no_zeros}'")
                except ValueError:
                    pass  # Not a number, skip this strategy
            
            # Find matching Excel record(s)
            if matching_excel_rows:
                self.gui_log(f"   ✓ Found match for Chart '{chart_value}' -> {len(matching_excel_rows)} Excel record(s)")
                for excel_row in matching_excel_rows:
                    # Combine data
                    combined = {}
                    
                    # Add all PDF data
                    for key, value in pdf_row.items():
                        if not key.startswith('_'):  # Skip internal fields
                            combined[f"PDF_{key}"] = value
                    
                    # Add all Excel data
                    for key, value in excel_row.items():
                        if not key.startswith('_'):  # Skip internal fields
                            combined[f"Excel_{key}"] = value
                    
                    # Add key matching fields explicitly
                    combined['Chart_Value'] = chart_value
                    combined['PT_Code'] = excel_row.get('_pt_code', '')
                    combined['Match_Status'] = 'Matched'
                    combined['Date_of_Service'] = pdf_row.get('Date of Service', pdf_row.get('Date', pdf_row.get('DOS', '')))
                    combined['Penelope_ID'] = excel_row.get('_penelope_id', '')
                    # Format DOB to ensure clean format (remove any timestamp)
                    dob_value = excel_row.get('_dob', '')
                    combined['DOB'] = self._format_dob(dob_value)
                    
                    # Add modifier, counselor name, supervisor from PDF if available
                    # Try multiple possible column names for modifier
                    modifier = (pdf_row.get('Modifier') or pdf_row.get('Mod') or 
                               pdf_row.get('Modifiers') or pdf_row.get('Modifier Code') or
                               pdf_row.get('Mod Code') or '')
                    combined['Modifier'] = modifier
                    
                    # Try multiple possible column names for counselor
                    counselor = (pdf_row.get('Counselor') or pdf_row.get('Counselor Name') or 
                                pdf_row.get('Provider') or pdf_row.get('Therapist') or
                                pdf_row.get('Clinician') or '')
                    combined['Counselor_Name'] = counselor
                    
                    # Try multiple possible column names for supervisor
                    supervisor = (pdf_row.get('Supervisor') or pdf_row.get('Supervising') or
                                 pdf_row.get('Supervisor Name') or pdf_row.get('Supervising Provider') or '')
                    combined['Supervisor'] = supervisor
                    
                    # Add any other fields from PDF
                    for key, value in pdf_row.items():
                        if key not in ['Chart_Value', 'Date of Service', 'Date', 'DOS', 'Modifier', 'Mod', 
                                      'Counselor', 'Counselor Name', 'Provider', 'Supervisor', 'Supervising']:
                            if not key.startswith('_'):
                                combined[f"PDF_{key}"] = value
                    
                    self.matched_data.append(combined)
                    match_count += 1
            else:
                # No match found - include PDF record with note
                combined = {}
                
                # Add all PDF data
                for key, value in pdf_row.items():
                    if not key.startswith('_'):  # Skip internal fields
                        combined[f"PDF_{key}"] = value
                
                # Add key matching fields explicitly
                combined['Chart_Value'] = chart_value
                combined['PT_Code'] = ''
                combined['Match_Status'] = 'No ODBC spreadsheet match was found'
                combined['Date_of_Service'] = pdf_row.get('Date of Service', pdf_row.get('Date', pdf_row.get('DOS', '')))
                combined['Penelope_ID'] = ''
                combined['DOB'] = ''
                
                # Add modifier, counselor name, supervisor from PDF if available
                # Try multiple possible column names for modifier
                modifier = (pdf_row.get('Modifier') or pdf_row.get('Mod') or
                            pdf_row.get('Modifiers') or pdf_row.get('Modifier Code') or
                            pdf_row.get('Mod Code') or '')
                combined['Modifier'] = modifier
                
                # Try multiple possible column names for counselor
                counselor = (pdf_row.get('Counselor') or pdf_row.get('Counselor Name') or
                             pdf_row.get('Provider') or pdf_row.get('Therapist') or
                             pdf_row.get('Clinician') or '')
                combined['Counselor_Name'] = counselor
                
                # Try multiple possible column names for supervisor
                supervisor = (pdf_row.get('Supervisor') or pdf_row.get('Supervising') or
                              pdf_row.get('Supervisor Name') or pdf_row.get('Supervising Provider') or '')
                combined['Supervisor'] = supervisor
                
                # Add any other fields from PDF
                for key, value in pdf_row.items():
                    if key not in ['Chart_Value', 'Date of Service', 'Date', 'DOS', 'Modifier', 'Mod', 
                                  'Counselor', 'Counselor Name', 'Provider', 'Supervisor', 'Supervising']:
                        if not key.startswith('_'):
                            combined[f"PDF_{key}"] = value
                
                self.matched_data.append(combined)
                pdf_unmatched += 1
        
        # Check for unmatched Excel records
        matched_pt_codes = set()
        for pdf_row in self.pdf_data:
            chart_value = pdf_row.get('_chart_value', '').strip()
            if chart_value:
                normalized = self._normalize_pt_code(chart_value)
                matched_pt_codes.add(normalized)
        
        for excel_row in self.excel_data:
            pt_code = excel_row.get('_pt_code', '').strip()
            normalized = self._normalize_pt_code(pt_code)
            if normalized not in matched_pt_codes:
                excel_unmatched += 1
        
        # Count matched vs unmatched in output data
        matched_in_output = sum(1 for row in self.matched_data if row.get('Match_Status') == 'Matched')
        unmatched_in_output = sum(1 for row in self.matched_data if row.get('Match_Status') == 'No ODBC spreadsheet match was found')
        
        # Count unique PDF rows and one-to-many matches
        unique_pdf_rows = len(self.pdf_data)
        pdf_rows_with_multiple_matches = 0
        for pdf_row in self.pdf_data:
            chart_value = pdf_row.get('_chart_value', '').strip()
            if chart_value:
                normalized_chart = self._normalize_pt_code(chart_value)
                if normalized_chart in excel_lookup:
                    excel_matches = excel_lookup[normalized_chart]
                    if len(excel_matches) > 1:
                        pdf_rows_with_multiple_matches += 1
        
        # Calculate expansion factor (output rows vs PDF rows)
        expansion_count = len(self.matched_data) - unique_pdf_rows
        
        self.gui_log(f"   📊 Matching Summary:")
        self.gui_log(f"      Unique PDF rows extracted: {unique_pdf_rows}")
        self.gui_log(f"      PDF rows with multiple Excel matches: {pdf_rows_with_multiple_matches}")
        self.gui_log(f"      ✅ Matched {match_count} output record(s) (one per Excel match)")
        self.gui_log(f"      📋 Including {pdf_unmatched} unmatched PDF record(s) in output with 'No ODBC spreadsheet match was found' note")
        self.gui_log(f"      ⚠️  Unmatched Excel records: {excel_unmatched} (not included in output)")
        if expansion_count > 0:
            self.gui_log(f"      📈 Output rows expanded by {expansion_count} due to one-to-many matches (one PDF row → multiple Excel rows)")
        self.gui_log(f"   📊 Output summary: {matched_in_output} matched rows, {unmatched_in_output} unmatched rows (total: {len(self.matched_data)} rows)")
        
        # If no matches, provide more detailed debugging
        if match_count == 0 and self.pdf_data and self.excel_data:
            self.gui_log("   🔍 Debugging: No matches found - checking first few values...")
            
            # Check first few PDF Chart values
            pdf_samples = []
            for pdf_row in self.pdf_data[:5]:
                chart_val = pdf_row.get('_chart_value', '').strip()
                normalized = self._normalize_pt_code(chart_val)
                pdf_samples.append(f"'{chart_val}' -> '{normalized}'")
            
            # Check first few Excel PT codes
            excel_samples = []
            excel_normalized_set = set()
            for excel_row in self.excel_data[:10]:
                pt_code = excel_row.get('_pt_code', '').strip()
                normalized = self._normalize_pt_code(pt_code)
                excel_normalized_set.add(normalized)
                if len(excel_samples) < 5:
                    excel_samples.append(f"'{pt_code}' -> '{normalized}'")
            
            self.gui_log(f"   📋 First 5 PDF Chart values: {pdf_samples}")
            self.gui_log(f"   📋 First 5 Excel PT codes: {excel_samples}")
            
            # Check if any PDF normalized values exist in Excel set
            pdf_normalized_set = set()
            for pdf_row in self.pdf_data:
                chart_val = pdf_row.get('_chart_value', '').strip()
                if chart_val:
                    pdf_normalized_set.add(self._normalize_pt_code(chart_val))
            
            overlap = pdf_normalized_set.intersection(excel_normalized_set)
            if overlap:
                self.gui_log(f"   ✅ Found {len(overlap)} overlapping normalized values (this shouldn't happen if match_count is 0)")
            else:
                self.gui_log(f"   ⚠️  No overlapping normalized values found between PDF and Excel")
                self.gui_log(f"   💡 The Chart column values in PDF may not match PT codes in Excel")
                self.gui_log(f"   💡 Tip: Check if Chart column contains PT codes or a different identifier")
    
    def _format_dob(self, dob_value) -> str:
        """Format DOB to remove timestamp and return clean date format (YYYY-MM-DD)"""
        if not dob_value:
            return ""
        
        # Convert to string and strip whitespace
        dob_str = str(dob_value).strip()
        
        # If it's empty or NaN, return empty string
        if not dob_str or dob_str.lower() in ['nan', 'none', 'nat', '']:
            return ""
        
        # Handle datetime format: "1947-06-22 00:00:00" -> "1947-06-22"
        # Check if it contains a space (likely has timestamp)
        if ' ' in dob_str:
            # Extract just the date part before the space
            dob_str = dob_str.split(' ')[0]
        
        # Remove any trailing zeros or timestamp parts
        # Pattern: YYYY-MM-DD followed by anything (HH:MM:SS, etc.)
        match = re.match(r'(\d{4}-\d{2}-\d{2})', dob_str)
        if match:
            return match.group(1)
        
        # If it's already in YYYY-MM-DD format, return as is
        if re.match(r'^\d{4}-\d{2}-\d{2}$', dob_str):
            return dob_str
        
        # If it's in other formats, try to preserve but clean up
        # Remove any trailing timestamp data
        dob_str = re.sub(r'\s+\d{2}:\d{2}:\d{2}.*$', '', dob_str)
        
        return dob_str.strip()
    
    def _normalize_pt_code(self, code: str) -> str:
        """Normalize PT code for matching (remove spaces, leading zeros, etc.)"""
        if not code:
            return ""
        
        # Convert to string and strip whitespace
        normalized = str(code).strip()
        
        # Remove leading/trailing whitespace again after conversion
        normalized = normalized.strip()
        
        # Try to convert to int if it's a pure number (handles leading zeros)
        try:
            # If it's all digits (or with spaces), try as int
            test_val = normalized.replace(" ", "").replace("-", "").replace("_", "")
            if test_val.isdigit():
                return str(int(test_val))  # This removes leading zeros
        except (ValueError, AttributeError):
            pass
        
        # For non-numeric or mixed values, just clean up whitespace and convert to uppercase
        # Remove spaces but keep other characters
        normalized = normalized.replace(" ", "").replace("\t", "").replace("\n", "")
        
        # Convert to uppercase for case-insensitive matching
        normalized = normalized.upper()
        
        return normalized
    
    def _generate_output(self):
        """Generate output Excel file with clean, non-duplicate columns"""
        if not self.matched_data:
            raise Exception("No data to output - PDF had no records")
        
        if not EXCEL_AVAILABLE:
            raise Exception("pandas is not available. Please install it with: pip install pandas openpyxl")
        
        # Convert to DataFrame
        df = pd.DataFrame(self.matched_data)
        
        # Clean up columns - remove duplicates and debug columns
        columns_to_remove = []
        columns_to_keep = []
        
        # Columns to always keep (these are the clean, processed fields)
        essential_columns = [
            'Match_Status',
            'Chart_Value',
            'PT_Code',
            'Date_of_Service',
            'Modifier',
            'Counselor_Name',
            'Supervisor',
            'Penelope_ID',
            'DOB'
        ]
        
        # PDF field mappings - keep only one version of each
        pdf_field_mappings = {
            'Procedure Code': ['PDF_Procedure Code', 'PDF_Col_10_Procedure', 'Procedure Code'],
            'Case Number': ['PDF_Case Number', 'PDF_Case', 'PDF_Col_6_Case', 'Case Number'],
            'Diagnosis Code': ['PDF_Diagnosis Code', 'PDF_Col_8_Diagnosis', 'Diagnosis Code'],
            'Amount': ['PDF_Amount', 'PDF_Col_18_Amount', 'Amount']
        }
        
        # Remove all raw PDF_Col_* columns (debug columns)
        # Remove PDF_Col_0, PDF_Col_1, PDF_Col_2, etc. (raw column data)
        # Also remove processed debug columns like PDF_Col_12_Modifier, PDF_Col_14_Provider, etc.
        for col in df.columns:
            if col.startswith('PDF_Col_'):
                # Check if it's a raw column number (PDF_Col_0, PDF_Col_1, etc.)
                # Pattern: PDF_Col_ followed by digits only
                if re.match(r'^PDF_Col_\d+$', col):
                    columns_to_remove.append(col)
                # Also remove processed debug columns (we'll keep the clean versions)
                elif col.endswith(('_Date', '_PTCode', '_Case', '_Diagnosis', '_Procedure', '_Modifier', '_Provider', '_Amount')):
                    columns_to_remove.append(col)
        
        # Remove duplicate field name variations
        # Date variations - keep only Date_of_Service
        if 'Date_of_Service' in df.columns:
            date_cols = [col for col in df.columns if ('Date' in col or col == 'DOS') and col != 'Date_of_Service']
            for col in date_cols:
                try:
                    if col in df.columns and df[col].equals(df['Date_of_Service']):
                        columns_to_remove.append(col)
                except:
                    pass
        
        # Modifier variations - keep only Modifier
        if 'Modifier' in df.columns:
            modifier_cols = [col for col in df.columns if ('Modif' in col or col == 'Mod') and col != 'Modifier']
            for col in modifier_cols:
                try:
                    if col in df.columns and df[col].equals(df['Modifier']):
                        columns_to_remove.append(col)
                except:
                    pass
        
        # Counselor/Provider variations - keep only Counselor_Name
        if 'Counselor_Name' in df.columns:
            counselor_cols = [col for col in df.columns if ('Counselor' in col or 'Provider' in col) and col != 'Counselor_Name']
            for col in counselor_cols:
                try:
                    if col in df.columns and df[col].equals(df['Counselor_Name']):
                        columns_to_remove.append(col)
                except:
                    pass
        
        # Excel duplicate fields - keep only without Excel_ prefix where we have a clean version
        excel_duplicates = {
            'Penelope_ID': 'Excel_Penelope_ID',
            'DOB': 'Excel_DOB',
            'PT_Code': 'Excel_Pt_Code'
        }
        for clean_col, excel_col in excel_duplicates.items():
            if clean_col in df.columns and excel_col in df.columns:
                if df[clean_col].equals(df[excel_col]):
                    columns_to_remove.append(excel_col)
        
        # Handle PDF field mappings - keep the clean name, remove duplicates
        for clean_name, variations in pdf_field_mappings.items():
            found_clean = None
            found_variations = []
            
            for var in variations:
                if var in df.columns:
                    if var == clean_name:
                        found_clean = var
                    else:
                        found_variations.append(var)
            
            # If we have a clean name, remove duplicates
            if found_clean:
                for var in found_variations:
                    if var in df.columns and df[var].equals(df[found_clean]):
                        columns_to_remove.append(var)
            elif found_variations:
                # Use the first variation and rename it
                keep_var = found_variations[0]
                df = df.rename(columns={keep_var: clean_name})
                for var in found_variations[1:]:
                    if var in df.columns and df[var].equals(df[clean_name]):
                        columns_to_remove.append(var)
        
        # Remove duplicate columns
        columns_to_remove = list(set(columns_to_remove))  # Remove duplicates from removal list
        for col in columns_to_remove:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        # Define column order (priority first, then PDF fields, then Excel fields, then others)
        # Excel First Name and Last Name should be early (columns B & C) and next to each other
        priority_columns = [
            'Match_Status',           # Column A
            'Excel_First_Name',       # Column B
            'Excel_Last_Name',        # Column C
            'Chart_Value',            # Column D
            'PT_Code',                # Column E
            'Date_of_Service',
            'Modifier',
            'Counselor_Name',
            'Supervisor',
            'Penelope_ID',
            'DOB'
        ]
        
        pdf_data_columns = [
            'Procedure Code',
            'Case Number',
            'Diagnosis Code',
            'Amount'
        ]
        
        # Get remaining Excel columns (excluding First Name and Last Name which are already in priority)
        excel_columns = [col for col in df.columns if col.startswith('Excel_') and 
                        col not in priority_columns and 
                        col not in ['Excel_First_Name', 'Excel_Last_Name']]
        other_columns = [col for col in df.columns if col not in priority_columns and 
                        col not in pdf_data_columns and col not in excel_columns]
        
        # Create ordered column list
        ordered_columns = []
        for col in priority_columns:
            if col in df.columns:
                ordered_columns.append(col)
        
        for col in pdf_data_columns:
            if col in df.columns:
                ordered_columns.append(col)
        
        for col in sorted(excel_columns):
            if col not in ordered_columns:
                ordered_columns.append(col)
        
        for col in sorted(other_columns):
            if col not in ordered_columns:
                ordered_columns.append(col)
        
        df = df[ordered_columns]
        
        # Save to Excel
        output_dir = self.output_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Log DataFrame info before saving
        if 'Match_Status' in df.columns:
            matched_count = len(df[df['Match_Status'] == 'Matched'])
            unmatched_count = len(df[df['Match_Status'] == 'No ODBC spreadsheet match was found'])
        else:
            matched_count = 0
            unmatched_count = 0
        
        self.gui_log(f"   📊 DataFrame contains: {matched_count} matched, {unmatched_count} unmatched (total: {len(df)} rows)")
        self.gui_log(f"   🧹 Cleaned output: {len(columns_to_remove)} duplicate/debug columns removed")
        
        df.to_excel(str(self.output_path), index=False, engine='openpyxl' if OPENPYXL_AVAILABLE else None)
        
        self.gui_log(f"   ✅ Generated output with {len(df)} row(s) and {len(df.columns)} column(s)")
    
    def run(self):
        """Run the application"""
        if not PDFPLUMBER_AVAILABLE:
            messagebox.showerror("Missing Dependency", 
                               "pdfplumber is required but not installed.\n\n"
                               "Please install it with: pip install pdfplumber")
            return
        
        if not EXCEL_AVAILABLE:
            messagebox.showerror("Missing Dependency",
                               "pandas is required but not installed.\n\n"
                               "Please install it with: pip install pandas openpyxl")
            return
        
        self.create_gui()
        self.gui_log("Medisoft/Penelope Data Synthesizer started")
        self.root.mainloop()


if __name__ == "__main__":
    app = MedisoftPenelopeDataSynthesizer()
    app.run()

