# isws_welcome_highlight_NAVPATCH_REOPEN_CLICKFIX_backup_again.py
# KEEP existing nav behavior & drawer reopen; harden Advanced "Send Welcome" click.
# Reference baseline preserved from your prior NAVPATCH build. (See chat context)

import os, re, json, time, tempfile, threading, queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from welcome_uploader_bridge import add_uploader_button
import csv
from datetime import datetime
import sys, subprocess

# Selenium imports for workflow queue functionality
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

APP_TITLE = "ISWS Welcome Letter Bot"
PN_DEFAULT_URL = "https://integrityseniorservices.athena-us.com/acm_loginControl"
MAROON = "#800000"
LEARN_DB_DIR = os.path.join(os.path.expanduser("~"), "Documents", "ISWS Welcome")
LEARN_DB = os.path.join(LEARN_DB_DIR, "learned_pn_selectors.json")

# Workflow queue selectors (matching the actual HTML structure)
WORKFLOW_SEL = {
    # Workflow drawer
    "workflow_handle": (By.ID, "taskHandle"),
    "drawer_panel_task": (By.ID, "task"),
    # Tabs
    "tab_current": (By.ID, "taskCurrentView"),
    "tab_advanced": (By.ID, "taskAdvancedView"),
    # Queue containers
    "queue_container": (By.ID, "queuedTasksContainer"),
    "queue_body": (By.ID, "taskQueueBody"),
    "queue_load_more": (By.ID, "queuedTasksLoadMoreButton"),
    # Current tasks containers (for chunk building)
    "current_container": (By.ID, "currentTasksContainer"),
    "current_body": (By.ID, "taskCurrentBody"),
    "current_load_more": (By.ID, "currentTasksLoadMoreButton"),
    # Row elements - updated to match actual HTML structure
    "row_subject_link": (By.CSS_SELECTOR, "td a[href*='TaskThreadServlet']"),
    "row_pickup": (By.CSS_SELECTOR, "td a[data-action='pickup']"),
    "row_date": (By.CSS_SELECTOR, "td:nth-child(3)"),  # Date column
    # Advanced search fields
    "adv_from": (By.ID, "fromDate"),
    "adv_to": (By.ID, "toDate"),
    "adv_search": (By.ID, "searchButton"),
    # Close button in general task page
    "close_button": (By.CSS_SELECTOR, "a[href*='actionType=closeTask']"),
}

# Target workflow title
TARGET_WORKFLOW_TITLE = "Send Welcome Letter and NPP"

# ------------------------ Utilities ------------------------
def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]+', "_", (name or "").strip())

def ensure_patient_dir(base_dir, full_name):
    if not base_dir:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        base_dir = os.path.join(desktop, "Welcome Bot Output")
    os.makedirs(base_dir, exist_ok=True)
    pdir = os.path.join(base_dir, sanitize_filename(full_name))
    os.makedirs(pdir, exist_ok=True)
    return pdir, base_dir

def normalize_address_lines(lines):
    out = []
    junk = re.compile(
        r"^(main address|address|profile|demographics|policy|messages|client|contact info|prev|edit|next)$",
        re.I
    )
    for ln in lines or []:
        t = " ".join((ln or "").split()).strip()
        if not t: continue
        if junk.match(t): continue
        t = t.replace("(show map)", "").strip()
        if t: out.append(t)
    seen = set(); clean = []
    for ln in out:
        key = ln.lower()
        if key in seen: continue
        seen.add(key); clean.append(ln)
    return clean[:4]

def guess_name_from_text(text):
    if not text: return ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for ln in lines:
        if ":" in ln or len(ln) > 64: continue
        toks = [t for t in re.split(r"\s+", ln) if re.search(r"[A-Za-z]", t)]
        if len(toks) >= 2: return ln
    return lines[0] if lines else ""

def format_address_for_pdf(address_lines):
    """
    Build 3 printable lines under the name:
      L2: street [ - unit]
      L3: city/state (or next best line)
      L4: country + zip (or next best line)
    """
    lines = [ (ln or "").strip() for ln in (address_lines or []) if (ln or "").strip() ]
    if not lines:
        return ["", "", ""]

    street = lines[0]
    unit   = ""
    cityst = ""
    ctryzip= ""

    # Heuristic: treat second line as unit if it looks like apt/suite/floor/# or a pure unit code (e.g. '2404', '1G')
    if len(lines) >= 2:
        l2 = lines[1]
        if re.search(r"\b(apt|apartment|ste|suite|unit|fl|floor|#)\b", l2, re.I) or re.fullmatch(r"[#]?\w[\w\-]*", l2):
            unit = l2
        else:
            cityst = l2

    if len(lines) >= 3:
        if not cityst:
            cityst = lines[2]
        else:
            ctryzip = lines[2]

    if len(lines) >= 4:
        ctryzip = lines[3]

    line2 = street if not unit else f"{street} - {unit}"
    line3 = cityst
    line4 = ctryzip

    return [line2, line3, line4]

def normalize_language(raw: str) -> str:
    """Return 'english', 'spanish', or 'unknown' from raw UI text."""
    if not raw:
        return "unknown"
    t = raw.strip().lower()
    if any(k in t for k in ["spanish", "español", "espanol", "castellano"]):
        return "spanish"
    if any(k in t for k in ["english", "inglés", "ingles"]):
        return "english"
    return "unknown"


def pick_welcome_template(lang_norm: str, en_path: str, es_path: str) -> str:
    """
    spanish -> es_path if present, else en_path
    english/unknown/other -> en_path
    """
    import os
    if lang_norm == "spanish" and es_path and os.path.isfile(es_path):
        return es_path
    return en_path

# ------------------------ PDF (robust, flattened) ------------------------
def stamp_letter_pdf(template_path, out_path, client_name, address_lines, log):
    try:
        from PyPDF2 import PdfReader, PdfWriter
        from PyPDF2.generic import NameObject, NullObject
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.colors import black
    except Exception as e:
        log(f"[PDF][ERROR] {e}")
        log("Install with: pip3 install --upgrade PyPDF2 reportlab")
        return False

    overlay_path = None; tmpl_f = None; over_f = None
    try:
        tmpl_f = open(template_path, "rb")
        base_pdf = PdfReader(tmpl_f)
        if len(base_pdf.pages) == 0:
            log("[PDF][ERROR] Template has no pages."); return False

        first = base_pdf.pages[0]
        try:
            w = float(first.mediabox.width); h = float(first.mediabox.height)
        except Exception:
            w, h = letter

        fd, overlay_path = tempfile.mkstemp(suffix=".pdf"); os.close(fd)
        c = rl_canvas.Canvas(overlay_path, pagesize=(w, h))
        c.setFillColor(black); c.setFont("Helvetica", 12)

        # Layout tuned for your non-fillable overlay
        left_margin = 72
        line_h = 16
        y_start = h - 150

        nm = (client_name or "").strip()
        if nm: c.drawString(left_margin, y_start, nm)

        # Build printable address lines (street [- unit], city/state, country+zip)
        line2, line3, line4 = format_address_for_pdf(address_lines)

        for i, ln in enumerate([line2, line3, line4]):
            if ln:
                c.drawString(left_margin, y_start - ((i + 1) * line_h), ln)

        c.showPage(); c.save()

        over_f = open(overlay_path, "rb")
        overlay_pdf = PdfReader(over_f); overlay_page = overlay_pdf.pages[0]
        first.merge_page(overlay_page)

        writer = PdfWriter()
        def _strip_annots(page):
            try:
                if "/Annots" in page:
                    page[NameObject("/Annots")] = NullObject()
            except Exception: pass
        _strip_annots(first); writer.add_page(first)
        for i in range(1, len(base_pdf.pages)):
            pg = base_pdf.pages[i]; _strip_annots(pg); writer.add_page(pg)
        try:
            writer._root_object.update({NameObject("/AcroForm"): NullObject()})
        except Exception: pass

        with open(out_path, "wb") as out_f:
            writer.write(out_f)
        return True
    except Exception as e:
        log(f"[PDF][ERROR] {e}"); return False
    finally:
        try:
            if over_f: over_f.close()
        except Exception: pass
        try:
            if tmpl_f: tmpl_f.close()
        except Exception: pass
        try:
            if overlay_path and os.path.exists(overlay_path): os.remove(overlay_path)
        except Exception: pass

def stamp_packet_pdf(template_path, out_path, client_name, initials, today_str, log):
    """
    Robust packet filler:
      1) Read all widget fields from page 1 (with PyPDF2).
      2) Map fields by name heuristics ('date', 'client|name', 'initial').
         If names don't help, pick by position:
           - Date:    top-most field
           - Name:    the widest field above page center (or next below date)
           - Initial: bottom-most field
      3) Draw values on top of those rects (reportlab overlay) and FLATTEN (remove Annots/AcroForm).
    Result: correct spots, larger font, non-fillable.
    """
    try:
        from PyPDF2 import PdfReader, PdfWriter
        from PyPDF2.generic import NameObject, NullObject
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.colors import black
    except Exception as e:
        log(f"[PDF2][ERROR] Missing libs: {e}")
        log("Install with: pip3 install --upgrade PyPDF2 reportlab")
        return False

    if not os.path.isfile(template_path):
        log("[PDF2][ERROR] Packet template missing.")
        return False

    try:
        reader = PdfReader(open(template_path, "rb"))
        if len(reader.pages) == 0:
            log("[PDF2][ERROR] Packet template has no pages.")
            return False

        page0 = reader.pages[0]
        media = page0.mediabox
        try:
            pw = float(media.width); ph = float(media.height)
        except Exception:
            # Fallback to letter if dimensions not readable
            pw, ph = (612.0, 792.0)

        # --- Gather widget rectangles & (optional) names from /Annots ---
        annots = page0.get("/Annots")

        # Some PDFs store /Annots as an IndirectObject; resolve before iterating
        try:
            if annots is not None and hasattr(annots, "get_object"):
                annots = annots.get_object()
        except Exception:
            pass

        widgets = []
        if annots:
            # Ensure we always iterate a sequence
            seq = annots if isinstance(annots, (list, tuple)) else [annots]
            for a in seq:
                try:
                    # Each entry can itself be an IndirectObject
                    obj = a.get_object() if hasattr(a, "get_object") else a
                    if not isinstance(obj, dict):
                        continue
                    if obj.get("/Subtype") != "/Widget":
                        continue
                    rect = obj.get("/Rect")
                    if not rect or len(rect) != 4:
                        continue
                    x0, y0, x1, y1 = [float(v) for v in rect]

                    # Field name (may be an indirect/text object)
                    fname = obj.get("/T")
                    if hasattr(fname, "get_object"):
                        fname = fname.get_object()
                    if not isinstance(fname, str):
                        fname = ""

                    widgets.append({
                        "name": (fname or "").strip(),
                        "rect": (x0, y0, x1, y1),
                        "mid": ((x0 + x1) / 2.0, (y0 + y1) / 2.0),
                        "w": abs(x1 - x0),
                        "h": abs(y1 - y0),
                    })
                except Exception:
                    continue

        if not widgets:
            log("[PDF2][ERROR] No fillable fields found on page 1.")
            return False

        # Debug dump (helps if mapping is off)
        try:
            for w in widgets:
                log(f"[PDF2][DBG] Field: '{w['name']}' rect={w['rect']}")
        except Exception:
            pass

        # --- Heuristic mapping ---
        def pick_by_name(cands, *substrings):
            subs = [s.lower() for s in substrings]
            best = []
            for w in cands:
                nm = (w["name"] or "").lower()
                if any(s in nm for s in subs):
                    best.append(w)
            return best

        # by-name first
        date_fields   = pick_by_name(widgets, "date", "dt")
        name_fields   = pick_by_name(widgets, "client", "name")
        init_fields   = pick_by_name(widgets, "initial", "initials", "init")

        # fallbacks by position if needed
        # top-most = largest mid-y; bottom-most = smallest mid-y
        widgets_sorted_top = sorted(widgets, key=lambda w: w["mid"][1], reverse=True)
        widgets_sorted_bot = sorted(widgets, key=lambda w: w["mid"][1])

        date_w = date_fields[0] if date_fields else widgets_sorted_top[0]

        # For name: prefer the widest field *not above* the date (usually near top quarter/third)
        remaining = [w for w in widgets if w is not date_w]
        if name_fields:
            name_w = name_fields[0]
        else:
            # Heuristic: field just below date or the widest in the upper half
            below_date = [w for w in remaining if w["mid"][1] < date_w["mid"][1]]
            if below_date:
                name_w = sorted(below_date, key=lambda w: (-w["w"], -w["mid"][1]))[0]
            else:
                upper_half = [w for w in remaining if w["mid"][1] > ph * 0.5]
                name_w = (sorted(upper_half, key=lambda w: (-w["w"], -w["mid"][1]))[0]
                          if upper_half else sorted(remaining, key=lambda w: -w["w"])[0])

        remaining2 = [w for w in remaining if w is not name_w]
        init_w = init_fields[0] if init_fields else (widgets_sorted_bot[0] if remaining2 == [] else
                                                     sorted(remaining2, key=lambda w: w["mid"][1])[0])

        # --- Build overlay with bigger font at those rects ---
        fd, overlay_path = tempfile.mkstemp(suffix=".pdf"); os.close(fd)
        c = rl_canvas.Canvas(overlay_path, pagesize=(pw, ph))
        c.setFillColor(black)

        def draw_in_rect(text, rect, font_size=12, left_pad=4, v_offset=0):
            x0, y0, x1, y1 = rect
            mid_y = (y0 + y1) / 2.0
            # Center vertically; ReportLab draws from baseline, so subtract a bit (~30% of size)
            baseline_y = mid_y - (font_size * 0.35) + v_offset
            c.setFont("Helvetica", font_size)
            c.drawString(x0 + left_pad, baseline_y, text)

        # Values
        date_val = today_str or ""
        name_val = client_name or ""
        init_val = (initials or "").upper()

        # Slightly larger text so it's easy to read
        draw_in_rect(date_val, date_w["rect"], font_size=13)
        draw_in_rect(name_val, name_w["rect"], font_size=13)
        draw_in_rect(init_val, init_w["rect"], font_size=13)

        c.showPage()
        c.save()

        # --- Merge overlay & flatten (strip fields) ---
        writer = PdfWriter()
        # Merge on first page
        from PyPDF2 import PdfReader as _Reader2
        overlay_pdf = _Reader2(open(overlay_path, "rb"))
        ov_page = overlay_pdf.pages[0]

        # Copy original pages, but merge overlay onto page 0 first
        for i, pg in enumerate(reader.pages):
            if i == 0:
                try:
                    pg.merge_page(ov_page)
                except Exception:
                    # Older PyPDF2: use merge_page directly on page
                    pass
            # strip annots on all pages to flatten
            try:
                if "/Annots" in pg:
                    pg[NameObject("/Annots")] = NullObject()
            except Exception:
                pass
            writer.add_page(pg)

        try:
            writer._root_object.update({NameObject("/AcroForm"): NullObject()})
        except Exception:
            pass

        with open(out_path, "wb") as fout:
            writer.write(fout)

        try:
            os.remove(overlay_path)
        except Exception:
            pass

        log(f"[PDF2] Saved: {out_path}")
        return True

    except Exception as e:
        log(f"[PDF2][ERROR] {e}")
        return False

# ------------------------ Learn DB ------------------------
class LearnDB:
    def __init__(self, path=LEARN_DB):
        # Ensure the directory exists and use the absolute path we set in LEARN_DB
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except Exception:
            pass
        self.path = path
        self.data = {}
        self._load()
    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f) or {}
        except Exception:
            self.data = {}
    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass
    def put(self, key, css, frame_hint=None, note=None):
        self.data[key] = {"css": css, "frame": (frame_hint or {}), "note": note or ""}; self.save()
    def get(self, key):
        return self.data.get(key) or {}

# ------------------------ JS for highlight teach ------------------------
JS_INSTALL_CAPTURE = r"""
(function install(win){
  try {
    if (!win._teachInstalled) {
      win._lastSelection = "";
      win.document.addEventListener('selectionchange', function(){
        try {
          var s = (win.getSelection && win.getSelection().toString()) || "";
          win._lastSelection = s;
        } catch(e){}
      }, true);
      win._teachInstalled = true;
    }
  } catch(e){}
  try {
    var frames = win.document.querySelectorAll('iframe,frame');
    for (var i=0;i<frames.length;i++){
      try { if (frames[i].contentWindow) install(frames[i].contentWindow); } catch(e){}
    }
  } catch(e){}
})(window);
return true;
"""
JS_READ_HIGHLIGHT = r"""
function cssPath(el){
  if (!el) return null;
  if (el.id) return '#'+el.id;
  var path=[], node=el, depth=0;
  while(node && node.nodeType===1 && depth<8){
    var sel = node.tagName.toLowerCase();
    if (node.id){ sel += "#" + node.id; path.unshift(sel); break; }
    var idx=1, sib=node;
    while((sib=sib.previousElementSibling)!=null){ if (sib.tagName===node.tagName) idx++; }
    sel += ':nth-of-type(' + idx + ')';
    path.unshift(sel);
    node = node.parentElement;
    depth++;
  }
  return path.join(' > ');
}
function nearestBlock(node){
  var el = (node && node.nodeType===1) ? node : (node ? node.parentElement : null);
  while(el){
    var disp = window.getComputedStyle(el).display;
    if (disp==='block' || disp==='grid' || disp==='table' ||
        /^(DIV|SECTION|ARTICLE|MAIN|LI|TD|P|H1|H2|H3|H4|H5|H6)$/i.test(el.tagName)) return el;
    el = el.parentElement;
  }
  return document.body;
}
function frameHint(){
  try {
    if (window===window.top) return null;
    var fe = window.frameElement; if (!fe) return null;
    return {id: fe.id || null, name: fe.name || null};
  } catch(e){ return null; }
}
var sel = window.getSelection && window.getSelection();
var txt = (sel && sel.toString()) ? sel.toString().trim() : (window._lastSelection||"").trim();
var anchor = (sel && sel.anchorNode) ? sel.anchorNode : null;
var container = nearestBlock(anchor);
var css = cssPath(container);
return { text: txt, css: css, frame: frameHint() };
"""

# ------------------------ GUI ------------------------
class App:
    def __init__(self, root):
        self.root = root
        root.title("ISWS Welcome Letter Bot - Version 3.1.0, Last Updated 12/04/2025")
        root.geometry("1000x860")
        root.configure(bg=MAROON)
        
        # Create main frame with scrollbar
        self.main_frame = tk.Frame(root, bg=MAROON)
        self.main_frame.pack(fill="both", expand=True)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self.main_frame, bg=MAROON, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=MAROON)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Make the scrollable frame focusable
        self.scrollable_frame.focus_set()
        
        # Mousewheel handler
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self._on_mousewheel = _on_mousewheel
        
        # Bind mousewheel to canvas
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)

        style = ttk.Style()
        try: style.theme_use('clam')
        except Exception: pass
        style.configure('TLabel', background=MAROON, foreground='#ffffff', font=("Helvetica", 11))
        style.configure('Header.TLabel', font=("Helvetica", 20, 'bold'))
        style.configure('Card.TFrame', background='#faf7f7')
        style.configure('TButton', font=("Helvetica", 11, 'bold'))

        self.log_q = queue.Queue()

        # State
        self.pn_url  = tk.StringVar(value=PN_DEFAULT_URL)
        self.pn_user = tk.StringVar()
        self.pn_pass = tk.StringVar()
        self.pdf_template = ""
        self.pdf_template_spanish = ""          # NEW: Spanish Welcome Letter template
        self.base_dir = tk.StringVar(value="")
        self.pdf_packet_template = ""            # second PDF template path
        self.emp_initials = tk.StringVar(value="MT")  # who ran the bot (default MT)

        self.current_capture = {"name": "", "address": [], "language": ""}
        self.batch = []
        self.learn = LearnDB()
        if self.learn.get("name") or self.learn.get("address"):
            self.enqueue("[LEARN] Loaded saved selectors. No need to teach again.")

        self.adv_index = tk.IntVar(value=0)
        self.auto_count = tk.IntVar(value=10)       # how many rows to process
        self.auto_delay = tk.DoubleVar(value=1.0)   # seconds between rows
        self._auto_abort = threading.Event()
        self._pdf_generation_failed = False  # Track if PDF generation fails
        self.debug_mode = tk.BooleanVar(value=False)  # Debug mode for queue operations
        self.organized_folders = tk.BooleanVar(value=False)  # Organize by letter type instead of by client
        
        # Chunk management (like Remove Counselor Bot)
        self.chunks = []  # List of (from_date, to_date) tuples
        self.next_chunk_index = 0
        
        # User management (similar to Remove Counselor Bot)
        self.users_file = Path(__file__).parent / "welcome_bot_users.json"
        self.users = {
            'penelope': {}  # {"name": {"username": "...", "password": "..."}}
        }
        self.load_users()

        ttk.Label(self.scrollable_frame, text=APP_TITLE, style="Header.TLabel").pack(pady=(12,6), fill='x')

        def card(parent):
            f = ttk.Frame(parent, style='Card.TFrame'); f.configure(padding=(14,12)); return f

        row = card(self.scrollable_frame); row.pack(fill='x', padx=12, pady=(0,8))
        
        # User Selection Row
        user_row = tk.Frame(row)
        user_row.grid(row=0, column=0, columnspan=2, sticky='ew', padx=6, pady=(0, 4))
        row.columnconfigure(0, weight=1)
        
        ttk.Label(user_row, text="Saved User:", font=("Helvetica", 10)).pack(side="left", padx=(0, 10))
        
        # User Selection Dropdown
        self.penelope_user_dropdown = ttk.Combobox(user_row, font=("Helvetica", 10), width=25, state="readonly")
        self.penelope_user_dropdown.pack(side="left", padx=(0, 10))
        self.penelope_user_dropdown.bind("<<ComboboxSelected>>", lambda e: self._on_user_selected('penelope'))
        self._update_user_dropdown('penelope')
        
        # Add User button
        self.penelope_add_user_button = tk.Button(user_row, text="Add User", 
                                                   command=lambda: self._add_user('penelope'),
                                                   bg="#800000", fg="white", font=("Helvetica", 9),
                                                   padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        self.penelope_add_user_button.pack(side="left", padx=(0, 5))
        
        # Update User button
        self.penelope_update_user_button = tk.Button(user_row, text="Update User", 
                                                     command=lambda: self._update_credentials('penelope'),
                                                     bg="#666666", fg="white", font=("Helvetica", 9),
                                                     padx=10, pady=3, cursor="hand2", relief="flat", bd=0)
        self.penelope_update_user_button.pack(side="left", padx=(0, 5))
        
        # Login credentials
        ttk.Label(row, text="PN URL:").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(row, textvariable=self.pn_url, width=54).grid(row=1, column=1, sticky='w', padx=6, pady=4)
        ttk.Label(row, text="PN Username:").grid(row=2, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(row, textvariable=self.pn_user, width=32).grid(row=2, column=1, sticky='w', padx=6, pady=4)
        ttk.Label(row, text="PN Password:").grid(row=3, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(row, textvariable=self.pn_pass, width=32, show='*').grid(row=3, column=1, sticky='w', padx=6, pady=4)

        files = card(self.scrollable_frame); files.pack(fill='x', padx=12, pady=6)
        ttk.Button(files, text="Select Welcome Letter PDF", command=self.pick_pdf).grid(row=0, column=0, padx=6, pady=4)
        self.lbl_pdf = ttk.Label(files, text="(none selected)"); self.lbl_pdf.grid(row=0, column=1, sticky='w', padx=6, pady=4)

        # NEW: Spanish template picker - moved below English
        ttk.Button(files, text="Select Spanish Welcome Letter PDF", command=self.pick_pdf_spanish).grid(row=1, column=0, padx=6, pady=4)
        self.lbl_pdf_spanish = ttk.Label(files, text="(none selected)")
        self.lbl_pdf_spanish.grid(row=1, column=1, sticky='w', padx=6, pady=4)
        
        ttk.Button(files, text="Select Packet Letter PDF", command=self.pick_pdf_packet).grid(row=2, column=0, padx=6, pady=4)
        self.lbl_pdf_packet = ttk.Label(files, text="(none selected)")
        self.lbl_pdf_packet.grid(row=2, column=1, sticky='w', padx=6, pady=4)

        ttk.Button(files, text="Choose Base Output Folder", command=self.pick_base).grid(row=3, column=0, padx=6, pady=4)
        self.lbl_base = ttk.Label(files, text="(default: Desktop\\Welcome Bot Output)"); self.lbl_base.grid(row=3, column=1, sticky='w', padx=6, pady=4)

        ttk.Label(files, text="Employee Initials:").grid(row=4, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(files, textvariable=self.emp_initials, width=12).grid(row=4, column=1, sticky='w', padx=6, pady=4)

        # Organized folders toggle
        ttk.Checkbutton(files, text="Organize by letter type (all welcome letters in one folder, all packet letters in another)", 
                       variable=self.organized_folders).grid(row=5, column=0, columnspan=2, sticky='w', padx=6, pady=4)

        # Open the TherapyNotes Welcome Packet Uploader inside this GUI
        uploader_btn = add_uploader_button(files, text="Open ISWS Welcome Packet Uploader", style="TButton")
        uploader_btn.grid(row=6, column=0, padx=6, pady=4, sticky='w')

        # Open the IPS TherapyNotes Welcome uploader (separate button)
        ttk.Button(files, text="Open IPS Welcome Bot & Uploader", command=self.open_ips_uploader)\
            .grid(row=6, column=1, padx=6, pady=4, sticky='w')

        teach = card(self.scrollable_frame); teach.pack(fill='x', padx=12, pady=6)
        ttk.Button(teach, text="Open Penelope + Login", command=self.open_pn).grid(row=0, column=0, padx=6, pady=4)
        ttk.Button(teach, text="Learn Name (Highlight)", command=lambda: self.learn_from_highlight("name")).grid(row=0, column=1, padx=6)
        ttk.Button(teach, text="Learn Address (Highlight)", command=lambda: self.learn_from_highlight("address")).grid(row=0, column=2, padx=6)
        ttk.Button(teach, text="Learn Language (Highlight)", command=lambda: self.learn_from_highlight("language")).grid(row=0, column=3, padx=6)  # NEW
        ttk.Button(teach, text="Auto-Capture (from learned)", command=self.auto_capture_from_learned).grid(row=0, column=4, padx=10)
        ttk.Button(teach, text="Reinstall Highlight Hook", command=self.install_highlight_capture).grid(row=0, column=5, padx=10)

        adv = card(self.scrollable_frame); adv.pack(fill='x', padx=12, pady=6)
        ttk.Label(adv, text="Advanced Results Index:").grid(row=0, column=0, sticky='e', padx=6)
        tk.Spinbox(adv, from_=0, to=999, textvariable=self.adv_index, width=6).grid(row=0, column=1, sticky='w', padx=6)
        ttk.Button(adv, text="Click 'Send Welcome' at Index", command=self.click_advanced_send_welcome).grid(row=0, column=2, padx=10)
        ttk.Button(adv, text="Run One", command=self.run_one).grid(row=0, column=3, padx=10)

        # NEW — auto controls
        ttk.Label(adv, text="Count:").grid(row=0, column=4, sticky='e', padx=6)
        tk.Spinbox(adv, from_=1, to=999, textvariable=self.auto_count, width=6).grid(row=0, column=5, sticky='w', padx=6)
        ttk.Label(adv, text="Delay (s):").grid(row=0, column=6, sticky='e', padx=6)
        tk.Spinbox(adv, from_=0.0, to=10.0, increment=0.1, textvariable=self.auto_delay, width=6).grid(row=0, column=7, sticky='w', padx=6)
        ttk.Button(adv, text="Run Auto", command=self.run_auto).grid(row=0, column=8, padx=10)
        ttk.Button(adv, text="Stop", command=self.stop_auto).grid(row=0, column=9, padx=6)
        
        # Workflow Queue Management
        ttk.Button(adv, text="Expand Queue & Pickup All", command=self.expand_queue_and_pickup_all).grid(row=1, column=0, columnspan=3, padx=6, pady=10, sticky='w')
        ttk.Checkbutton(adv, text="Debug Mode (show all workflow titles)", variable=self.debug_mode).grid(row=2, column=0, columnspan=3, padx=6, pady=5, sticky='w')
        
        # Current Tasks Chunk Management (like Remove Counselor Bot)
        ttk.Button(adv, text="Expand Current Tasks & Chunk Dates", command=self.build_chunks).grid(row=3, column=0, columnspan=3, padx=6, pady=10, sticky='w')
        ttk.Button(adv, text="Fill Next Chunk", command=self.fill_next_chunk).grid(row=4, column=0, columnspan=3, padx=6, pady=5, sticky='w')

        batch = card(self.scrollable_frame); batch.pack(fill='x', padx=12, pady=6)
        ttk.Button(batch, text="Queue Letter", command=self.queue_letter).grid(row=0, column=0, padx=6)
        ttk.Button(batch, text="Build All", command=self.build_all).grid(row=0, column=1, padx=6)
        self.lbl_batch = ttk.Label(batch, text="Queued: 0"); self.lbl_batch.grid(row=0, column=2, sticky='w', padx=12)

        single = card(self.scrollable_frame); single.pack(fill='x', padx=12, pady=6)
        ttk.Button(single, text="Make Letter (current)", command=self.make_letter_current).grid(row=0, column=0, padx=6)
        self.lbl_current = ttk.Label(single, text="Current: (none)"); self.lbl_current.grid(row=0, column=1, sticky='w', padx=12)

        log_card = card(self.scrollable_frame); log_card.pack(fill='both', expand=True, padx=12, pady=10)
        self.log = scrolledtext.ScrolledText(log_card, width=120, height=26, bg="#f5f5f5", fg="#000000", font=("Consolas", 10))
        self.log.pack(fill='both', expand=True)

        self.root.after(100, self.flush_log)
        self._driver = None

    # ------------- Logging -------------
    def enqueue(self, msg): self.log_q.put(msg)
    def flush_log(self):
        while not self.log_q.empty():
            self.log.insert(tk.END, self.log_q.get() + "\n"); self.log.see(tk.END)
        self.root.after(100, self.flush_log)
    
    # ------------- User Management -------------
    def load_users(self):
        """Load users from JSON file"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r') as f:
                    loaded = json.load(f)
                    # Ensure penelope category exists
                    self.users = {
                        'penelope': loaded.get('penelope', {})
                    }
            else:
                # Create empty users file if it doesn't exist
                self.save_users()
        except Exception as e:
            # Log will be created later in __init__
            self.users = {
                'penelope': {}
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
            'penelope': 'penelope_user_dropdown'
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
            'penelope': ('penelope_user_dropdown', 'pn_user', 'pn_pass', 'pn_url')
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
                var = getattr(self, user_entry)
                if isinstance(var, tk.StringVar):
                    var.set(user_data.get('username', ''))
            
            if hasattr(self, pass_entry):
                var = getattr(self, pass_entry)
                if isinstance(var, tk.StringVar):
                    var.set(user_data.get('password', ''))
            
            # Update URL if applicable
            if url_entry and hasattr(self, url_entry):
                var = getattr(self, url_entry)
                if isinstance(var, tk.StringVar):
                    default_url = PN_DEFAULT_URL
                    var.set(user_data.get('url', default_url))
            
            # Log message
            self.enqueue(f"[USER] Loaded credentials for user: {selected_user}")
    
    def _add_user(self, service_type):
        """Add a new user to saved users for a specific service"""
        service_names = {
            'penelope': 'Penelope'
        }
        service_name = service_names.get(service_type, 'Service')
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Add New User - {service_name}")
        dialog.geometry("450x280")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        tk.Label(dialog, text="User Name:", font=("Helvetica", 10), bg="#f0f0f0").pack(pady=(20, 5))
        name_entry = tk.Entry(dialog, font=("Helvetica", 10), width=35)
        name_entry.pack(pady=(0, 10))
        name_entry.focus()
        
        tk.Label(dialog, text="Username:", font=("Helvetica", 10), bg="#f0f0f0").pack(pady=(0, 5))
        username_entry = tk.Entry(dialog, font=("Helvetica", 10), width=35)
        username_entry.pack(pady=(0, 10))
        
        tk.Label(dialog, text="Password:", font=("Helvetica", 10), bg="#f0f0f0").pack(pady=(0, 5))
        password_entry = tk.Entry(dialog, font=("Helvetica", 10), width=35, show="•")
        password_entry.pack(pady=(0, 15))
        
        def save_user():
            name = name_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            if not name or not username or not password:
                messagebox.showwarning("Invalid Input", "User Name, Username, and Password are required")
                return
            
            user_data = {
                'username': username,
                'password': password
            }
            
            if name in self.users[service_type]:
                if not messagebox.askyesno("User Exists", f"User '{name}' already exists. Overwrite?"):
                    return
            
            self.users[service_type][name] = user_data
            self.save_users()
            self._update_user_dropdown(service_type)
            
            # Log message
            self.enqueue(f"[USER] Added user: {name}")
            
            dialog.destroy()
            messagebox.showinfo("Success", f"User '{name}' added successfully")
        
        button_frame = tk.Frame(dialog, bg="#f0f0f0")
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Save", command=save_user,
                  bg="#800000", fg="white", font=("Helvetica", 10),
                  padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=dialog.destroy,
                  bg="#666666", fg="white", font=("Helvetica", 10),
                  padx=15, pady=5, cursor="hand2", relief="flat", bd=0).pack(side="left", padx=5)
        
        # Bind Enter key to save
        name_entry.bind("<Return>", lambda e: username_entry.focus())
        username_entry.bind("<Return>", lambda e: password_entry.focus())
        password_entry.bind("<Return>", lambda e: save_user())
    
    def _update_credentials(self, service_type):
        """Update credentials for selected user"""
        dropdown_map = {
            'penelope': ('penelope_user_dropdown', 'pn_user', 'pn_pass', 'pn_url')
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
        
        user_data = {
            'username': username,
            'password': password
        }
        
        self.users[service_type][selected_user] = user_data
        self.save_users()
        
        # Log message
        self.enqueue(f"[USER] Updated credentials for user: {selected_user}")
        
        messagebox.showinfo("Success", f"Credentials updated for '{selected_user}'")

    # ------------- UI picks -------------
    def pick_pdf(self):
        f = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if f:
            self.pdf_template = f; self.lbl_pdf.config(text=f)
            self.enqueue(f"[UI] Selected Welcome Letter PDF: {f}")
    def pick_base(self):
        d = filedialog.askdirectory()
        if d:
            self.base_dir.set(d); self.lbl_base.config(text=d)
            self.enqueue(f"[UI] Base output folder: {d}")
    def pick_pdf_packet(self):
        f = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if f:
            self.pdf_packet_template = f
            self.lbl_pdf_packet.config(text=f)
            self.enqueue(f"[UI] Selected Packet Letter PDF: {f}")

    def pick_pdf_spanish(self):
        f = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if f:
            self.pdf_template_spanish = f
            self.lbl_pdf_spanish.config(text=f)
            self.enqueue(f"[UI] Selected Spanish Welcome Letter PDF: {f}")

    # ------------- Selenium Login -------------
    def open_pn(self):
        def worker():
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By
                from selenium.webdriver.common.keys import Keys
            except Exception as e:
                self.enqueue(f"[PN][FATAL] Missing Selenium packages: {e}")
                self.enqueue("Install with: pip3 install --upgrade selenium webdriver-manager")
                return

            try:
                options = webdriver.ChromeOptions()
                options.add_argument("--start-maximized")
                service = Service(ChromeDriverManager().install())
                self._driver = webdriver.Chrome(service=service, options=options)
                wait = WebDriverWait(self._driver, 20)

                url = (self.pn_url.get() or PN_DEFAULT_URL).strip() or PN_DEFAULT_URL
                self.enqueue("[PN] Opening Penelope…")
                self._driver.get(url)

                def try_login_in_ctx(ctx):
                    try:
                        users = ctx.find_elements(By.CSS_SELECTOR, "input[type='text'],input[type='email']")
                        pwds  = ctx.find_elements(By.CSS_SELECTOR, "input[type='password']")
                        if not users or not pwds: return False
                        u = users[0]; p = pwds[0]
                        try: u.clear()
                        except Exception: pass
                        u.send_keys(self.pn_user.get().strip())
                        try: p.clear()
                        except Exception: pass
                        p.send_keys(self.pn_pass.get().strip())
                        for by, sel in [
                            (By.CSS_SELECTOR, "button[type='submit']"),
                            (By.CSS_SELECTOR, "input[type='submit']"),
                            (By.XPATH, "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'login') or contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in')]"),
                        ]:
                            try:
                                btn = ctx.find_element(by, sel)
                                try: btn.click()
                                except Exception:
                                    try: ctx.execute_script("arguments[0].click();", btn)
                                    except Exception: pass
                                return True
                            except Exception:
                                continue
                        p.send_keys(Keys.ENTER); return True
                    except Exception:
                        return False

                if not try_login_in_ctx(self._driver):
                    frames = self._driver.find_elements(By.TAG_NAME, "iframe")
                    ok = False
                    for fr in frames:
                        try:
                            self._driver.switch_to.default_content(); self._driver.switch_to.frame(fr)
                            if try_login_in_ctx(self._driver): ok = True; break
                        except Exception: continue
                    self._driver.switch_to.default_content()
                    if not ok:
                        self.enqueue("[PN] Could not find login fields."); return

                try:
                    wait.until(EC.any_of(
                        EC.url_changes(url),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'logout')]"))
                    ))
                except Exception: pass

                self.enqueue("[PN] Login appears successful.")
                self.install_highlight_capture()

            except Exception as e:
                self.enqueue(f"[PN][ERROR] {e}")
        threading.Thread(target=worker, daemon=True).start()

    def install_highlight_capture(self):
        if not self._driver: return
        try:
            self._driver.switch_to.default_content(); self._driver.execute_script(JS_INSTALL_CAPTURE)
            frames = self._driver.find_elements("tag name", "iframe")
            for fr in frames:
                try:
                    self._driver.switch_to.default_content(); self._driver.switch_to.frame(fr)
                    self._driver.execute_script(JS_INSTALL_CAPTURE)
                except Exception: continue
            self._driver.switch_to.default_content()
        except Exception: pass
        self.enqueue("[TEACH] Highlight hook installed. If you change pages, click 'Reinstall Highlight Hook' and try again.")

    # ------------- Learn via highlight -------------
    def learn_from_highlight(self, key):
        if not self._driver:
            self.enqueue("[TEACH] Open Penelope first."); return
        self.install_highlight_capture()

        got = None
        try:
            self._driver.switch_to.default_content(); got = self._driver.execute_script(JS_READ_HIGHLIGHT)
            if not got or not (got.get("text") and got.get("css")):
                frames = self._driver.find_elements("tag name", "iframe")
                for fr in frames:
                    try:
                        self._driver.switch_to.default_content(); self._driver.switch_to.frame(fr)
                        got = self._driver.execute_script(JS_READ_HIGHLIGHT)
                        if got and got.get("text") and got.get("css"): break
                    except Exception: continue
                self._driver.switch_to.default_content()
        except Exception: got=None

        if not got or not got.get("text"):
            self.enqueue(f"[TEACH] No highlight detected for {key.title()}."); return

        txt = got.get("text","").strip(); css = got.get("css",""); frame = got.get("frame") or {}
        if key == "name":
            nm = guess_name_from_text(txt)
            if not nm:
                self.enqueue("[TEACH] Could not parse a name from that selection.")
                return
            self.learn.put("name", css, frame_hint=frame, note=nm)
            self.enqueue(f"[LEARN] Name selector saved: {css}  (text: {nm})")
            self.current_capture["name"] = nm
            self.lbl_current.config(text=f"Current: {nm}")
        elif key == "address":
            lines = normalize_address_lines([l.strip() for l in txt.splitlines() if l.strip()])
            if not lines:
                self.enqueue("[TEACH] That selection didn't look like an address.")
                return
            self.learn.put("address", css, frame_hint=frame, note=" | ".join(lines))
            self.enqueue(f"[LEARN] Address selector saved: {css}  (lines: {lines})")
            self.current_capture["address"] = lines
        elif key == "language":
            lang_norm = normalize_language(txt)
            self.learn.put("language", css, frame_hint=frame, note=lang_norm)
            self.enqueue(f"[LEARN] Language selector saved: {css}  (detected: {lang_norm}; raw: {txt})")
            self.current_capture["language"] = lang_norm
            cur_nm = self.current_capture.get('name') or '(none)'
            self.lbl_current.config(text=f"Current: {cur_nm}  •  Lang: {lang_norm}")
        else:
            self.enqueue(f"[TEACH] Unknown key: {key}")

    # ------------- Auto-capture -------------
    def auto_capture_from_learned(self):
        """
        Re-captures name/address using learned selectors.
        - Clears previous capture first (prevents stale reuse).
        - Tries hinted frame first, then default, then all iframes.
        - Waits briefly for the selectors to appear on the new page.
        """
        if not self._driver:
            self.enqueue("[AUTO] Open Penelope first.")
            return

        # ---- IMPORTANT: clear old capture so we never reuse stale address ----
        prev = dict(self.current_capture)
        self.current_capture["name"] = ""
        self.current_capture["address"] = []
        self.current_capture["language"] = ""   # NEW

        # imports local to avoid top-of-file changes
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception:
            # we already imported selenium elsewhere; this is defensive
            pass

        def read_using_record(rec) -> str:
            """Find text for saved CSS; try hinted frame, then default, then all frames."""
            if not rec:
                return ""
            css = (rec.get("css") or "").strip()
            fh  = rec.get("frame") or {}
            if not css:
                return ""

            # Build context list: hinted frame (if any) → default → every iframe
            ctxs = []
            try:
                self._driver.switch_to.default_content()
            except Exception:
                pass

            # hinted frame first
            if fh.get("id") or fh.get("name"):
                try:
                    fr = None
                    if fh.get("id"):
                        try: fr = self._driver.find_element(By.ID, fh["id"])
                        except Exception: fr = None
                    if not fr and fh.get("name"):
                        try: fr = self._driver.find_element(By.NAME, fh["name"])
                        except Exception: fr = None
                    if fr:
                        ctxs.append(fr)
                except Exception:
                    pass

            # default content
            ctxs.append(None)

            # then all frames
            try:
                frames = self._driver.find_elements(By.CSS_SELECTOR, "iframe,frame")
            except Exception:
                frames = []
            for fr in frames:
                if fr and fr not in ctxs:
                    ctxs.append(fr)

            # try each context until we get non-empty text
            for fr in ctxs:
                try:
                    self._driver.switch_to.default_content()
                    if fr is not None:
                        self._driver.switch_to.frame(fr)

                    # wait up to ~7s for the element to exist
                    try:
                        WebDriverWait(self._driver, 7).until(
                            lambda d: len(d.find_elements(By.CSS_SELECTOR, css)) > 0
                        )
                    except Exception:
                        continue

                    el = self._driver.find_element(By.CSS_SELECTOR, css)
                    txt = (el.text or el.get_attribute("textContent") or "").strip()
                    if txt:
                        return txt
                except Exception:
                    continue
            return ""

        # ---- perform reads using saved selectors ----
        name_raw = read_using_record(self.learn.get("name"))
        addr_raw = read_using_record(self.learn.get("address"))
        lang_raw = read_using_record(self.learn.get("language"))
        lang_norm = normalize_language(lang_raw)

        nm = guess_name_from_text(name_raw)
        lines = normalize_address_lines(addr_raw.splitlines() if addr_raw else [])

        # set only what we actually captured this time
        if nm:
            self.current_capture["name"] = nm
        if lines:
            self.current_capture["address"] = lines
        if lang_norm and lang_norm != "unknown":
            self.current_capture["language"] = lang_norm

        # Fallback: scan page text if taught selector didn’t produce a language
        if not self.current_capture.get("language"):
            fb = self._infer_language_from_dom()
            if fb != "unknown":
                self.current_capture["language"] = fb
                self.enqueue(f"[AUTO] Language (fallback from page): {fb}")

        # log result
        nm_log = self.current_capture.get("name") or ""
        lines_log = list(self.current_capture.get("address") or [])
        lang_log = self.current_capture.get("language") or ""
        if nm_log or lines_log or lang_log:
            self.enqueue("[AUTO] Captured:")
            if nm_log:
                self.enqueue(f"  - Name: {nm_log}")
            for ln in lines_log:
                self.enqueue(f"  - {ln}")
            if lang_log:
                self.enqueue(f"  - Language: {lang_log}")
        else:
            self.enqueue("[AUTO] Nothing captured. Teach selectors or reinstall hook.")

        # reflect in UI
        cur_nm = self.current_capture['name'] or '(none)'
        cur_lang = self.current_capture.get('language') or 'unknown'
        self.lbl_current.config(text=f"Current: {cur_nm}  •  Lang: {cur_lang}")

    def _infer_language_from_dom(self) -> str:
        """
        Best-effort fallback: scan visible text in the current page (root + iframes)
        and try to infer language from labels/values. Returns 'spanish'/'english'/'unknown'.
        """
        if not self._driver:
            return "unknown"
        try:
            from selenium.webdriver.common.by import By
        except Exception:
            return "unknown"

        d = self._driver

        def _read_text_current_ctx():
            try:
                txt = d.execute_script(
                    "return (document && document.body) ? (document.body.innerText||'') : '';"
                )
                return (txt or "").strip()
            except Exception:
                return ""

        texts = []

        # root
        try:
            d.switch_to.default_content()
        except Exception:
            pass
        texts.append(_read_text_current_ctx())

        # each frame
        try:
            frames = d.find_elements(By.CSS_SELECTOR, "iframe,frame")
        except Exception:
            frames = []
        for fr in frames:
            try:
                d.switch_to.default_content()
                d.switch_to.frame(fr)
                texts.append(_read_text_current_ctx())
            except Exception:
                continue
        try:
            d.switch_to.default_content()
        except Exception:
            pass

        big = "\n".join(t for t in texts if t).lower()
        if not big:
            return "unknown"

        import re
        m = re.search(r"language\s*[:\-]?\s*(spanish|español|espanol|castellano|english|inglés|ingles)", big, re.I)
        if m:
            val = m.group(1).lower()
            if any(k in val for k in ["spanish", "español", "espanol", "castellano"]):
                return "spanish"
            if any(k in val for k in ["english", "inglés", "ingles"]):
                return "english"

        if any(k in big for k in ["español", "espanol", "castellano", "spanish"]):
            return "spanish"
        if any(k in big for k in ["inglés", "ingles", "english"]):
            return "english"

        return "unknown"

    # ------------- Drawer reopen -------------
    def reopen_workflow_drawer(self):
        """
        Re-open the right Workflow drawer and confirm the Advanced list is VISIBLE (not just present).
        Minimal, surgical: stricter visibility checks + double-tap handle if needed.
        """
        if not self._driver:
            return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception:
            self.enqueue("[NAV][ERROR] Selenium libs missing.")
            return False

        wait = WebDriverWait(self._driver, 8)

        def _drawer_visible_in_current_ctx() -> bool:
            try:
                d = self._driver.find_element(By.CSS_SELECTOR, "#drawer")
                return d.is_displayed()
            except Exception:
                return False

        def drawer_visible() -> bool:
            """Check visibility in main doc and all frames."""
            try:
                self._driver.switch_to.default_content()
                if _drawer_visible_in_current_ctx():
                    return True
                for fr in self._driver.find_elements(By.CSS_SELECTOR, "iframe, frame"):
                    try:
                        self._driver.switch_to.default_content()
                        self._driver.switch_to.frame(fr)
                        if _drawer_visible_in_current_ctx():
                            return True
                    except Exception:
                        continue
                self._driver.switch_to.default_content()
                return False
            finally:
                try: self._driver.switch_to.default_content()
                except Exception: pass

        def _advanced_visible_in_current_ctx() -> bool:
            try:
                # Only count nodes that are actually displayed
                for sel in ("#advancedTasksBody", "#taskPanel_advanced"):
                    for el in self._driver.find_elements(By.CSS_SELECTOR, sel):
                        try:
                            if el.is_displayed():
                                return True
                        except Exception:
                            pass
                return False
            except Exception:
                return False

        def advanced_visible() -> bool:
            """Advanced list/toggle is visible somewhere (main or a frame)."""
            try:
                self._driver.switch_to.default_content()
                if _advanced_visible_in_current_ctx():
                    return True
                for fr in self._driver.find_elements(By.CSS_SELECTOR, "iframe, frame"):
                    try:
                        self._driver.switch_to.default_content()
                        self._driver.switch_to.frame(fr)
                        if _advanced_visible_in_current_ctx():
                            return True
                    except Exception:
                        continue
                return False
            finally:
                try: self._driver.switch_to.default_content()
                except Exception: pass

        # If it's already visible, we're done.
        if drawer_visible() and advanced_visible():
            self.enqueue("[NAV] Advanced list ready.")
            self.install_highlight_capture()
            return True

        # Ensure we are on a window that has the handle/drawer DOM
        try:
            for h in self._driver.window_handles:
                self._driver.switch_to.window(h)
                self._driver.switch_to.default_content()
                if self._driver.find_elements(By.CSS_SELECTOR, "#handleContainer, #taskHandle, #drawer"):
                    break
        except Exception:
            pass

        # Click the workflow handle (#taskHandle), with JS fallback; try up to 2 taps
        def click_handle_once() -> bool:
            self._driver.switch_to.default_content()
            handle = None
            try:
                handle = self._driver.find_element(By.CSS_SELECTOR, "#taskHandle")
            except Exception:
                # common fallbacks
                for how, what in [
                    (By.CSS_SELECTOR, "#handleContainer #taskHandle"),
                    (By.CSS_SELECTOR, "#calendarHandle"),
                    (By.CSS_SELECTOR, "#handleContainer [id$='Handle']"),
                    (By.XPATH, "//*[contains(translate(normalize-space(.),'WORKFLOW','workflow'),'workflow') or contains(translate(normalize-space(.),'TASK','task'),'task')]"),
                ]:
                    try:
                        handle = self._driver.find_element(how, what); break
                    except Exception:
                        continue
            if not handle:
                return False
            try:
                self._driver.execute_script("arguments[0].scrollIntoView({block:'center'});", handle)
            except Exception:
                pass
            try:
                handle.click()
            except Exception:
                try:
                    self._driver.execute_script("arguments[0].click();", handle)
                except Exception:
                    return False
            return True

        # tap 1
        clicked = click_handle_once()
        if clicked:
            try:
                self._driver.switch_to.default_content()
                wait.until(lambda d: drawer_visible())
            except Exception:
                pass

        # If still not visible, tap 2 (sometimes first click focuses, second opens)
        if not drawer_visible():
            click_handle_once()
            time.sleep(0.4)

        # Try to expand the Advanced panel if collapsed
        def expand_advanced_if_needed():
            try:
                self._driver.switch_to.default_content()
                if advanced_visible():
                    return True
                # click header/toggle candidates
                for how, what in [
                    (By.CSS_SELECTOR, "#taskPanel_advanced .taskPanelHeader"),
                    (By.CSS_SELECTOR, "#taskPanel_advanced"),
                    (By.XPATH, "//*[@id='taskPanel_advanced']//*[contains(.,'Advanced')]"),
                    (By.XPATH, "//a[contains(.,'Advanced')]"),
                ]:
                    try:
                        el = self._driver.find_element(how, what)
                        try: self._driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        except Exception: pass
                        try: el.click()
                        except Exception: self._driver.execute_script("arguments[0].click();", el)
                        time.sleep(0.3)
                        if advanced_visible():
                            return True
                    except Exception:
                        continue
                return advanced_visible()
            except Exception:
                return False

        expand_advanced_if_needed()

        # Final verify
        ok = drawer_visible() and advanced_visible()
        if ok:
            self.enqueue("[NAV] Advanced list ready.")
            self.install_highlight_capture()
        else:
            self.enqueue("[NAV][WARN] Drawer/Advanced not visible after reopen.")
        return ok

    # ------------- NAV BUTTONS -------------
    def click_advanced_send_welcome(self):
        """Clicks the 'Send Welcome Letter and NPP' link inside the chosen Advanced row by index,
        then waits/switches to the Task page window/frame so the next step can find 'Case'."""
        if not self._driver:
            self.enqueue("[NAV] Open Penelope first."); return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            wait = WebDriverWait(self._driver, 15)

            # Locate the Advanced table in some window/frame
            advanced_win = None; advanced_fr = None
            for h in self._driver.window_handles:
                try:
                    self._driver.switch_to.window(h); self._driver.switch_to.default_content()
                    frames = [None] + self._driver.find_elements(By.CSS_SELECTOR, "iframe,frame")
                    for fr in frames:
                        try:
                            self._driver.switch_to.default_content()
                            if fr is not None: self._driver.switch_to.frame(fr)
                            if self._driver.find_elements(By.ID, "advancedTasksBody"):
                                advanced_win = h; advanced_fr = fr; break
                        except Exception: continue
                    if advanced_win: break
                except Exception: continue
            if not advanced_win:
                self.enqueue("[NAV] Advanced list not visible."); return False

            self._driver.switch_to.window(advanced_win); self._driver.switch_to.default_content()
            if advanced_fr is not None: self._driver.switch_to.frame(advanced_fr)

            rows = self._driver.find_elements(By.CSS_SELECTOR, "#advancedTasksBody tr")
            if not rows: self.enqueue("[NAV] No rows found in advanced list."); return False

            # Keep only rows that mention "Send Welcome"
            candidates = []
            for r in rows:
                try:
                    if "send welcome" in (r.text or "").lower():
                        candidates.append(r)
                except Exception: continue
            if not candidates:
                self.enqueue("[NAV] No rows with 'Send Welcome' found."); return False

            idx = max(0, int(self.adv_index.get() or 0))
            if idx >= len(candidates):
                self.enqueue(f"[NAV] Adv Index {idx} out of range (found {len(candidates)})."); return False
            row = candidates[idx]

            # Prefer the exact anchor/button
            link = None
            pref = [
                (By.XPATH, ".//a[normalize-space(translate(string(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'))='send welcome letter and npp']"),
                (By.XPATH, ".//button[normalize-space(translate(string(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'))='send welcome letter and npp']"),
                (By.XPATH, ".//a[contains(translate(string(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send welcome')]"),
                (By.XPATH, ".//button[contains(translate(string(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'send welcome')]"),
                (By.CSS_SELECTOR, "td:nth-of-type(2) a"),
            ]
            for how, what in pref:
                try: link = row.find_element(how, what); break
                except Exception: continue
            if not link:
                link = row  # Worst case, click the row cell

            # Click with fallback
            try: self._driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
            except Exception: pass
            old_handles = set(self._driver.window_handles)
            clicked=False
            try:
                ActionChains(self._driver).move_to_element(link).pause(0.05).click().perform(); clicked=True
            except Exception:
                try: link.click(); clicked=True
                except Exception:
                    try: self._driver.execute_script("arguments[0].click();", link); clicked=True
                    except Exception: pass

            if not clicked:
                self.enqueue(f"[NAV][WARN] Attempted click on Advanced row #{idx} failed."); return False

            self.enqueue(f"[NAV] Clicked Advanced row #{idx} → 'Send Welcome Letter and NPP'.")

            # Wait for a new window OR the Task page content to appear somewhere
            def task_ready_somewhere():
                try:
                    for h in self._driver.window_handles:
                        self._driver.switch_to.window(h); self._driver.switch_to.default_content()
                        # look in root
                        for how, what in [
                            (By.XPATH, "//a[normalize-space()='Case']"),
                            (By.XPATH, "//a[contains(.,'Case')]"),
                            (By.CSS_SELECTOR, "#caseMemberTable"),
                        ]:
                            try:
                                if self._driver.find_elements(how, what):
                                    return h
                            except Exception: continue
                        # look in frames
                        frames = self._driver.find_elements(By.CSS_SELECTOR, "iframe,frame")
                        for fr in frames:
                            try:
                                self._driver.switch_to.default_content(); self._driver.switch_to.frame(fr)
                                for how, what in [
                                    (By.XPATH, "//a[normalize-space()='Case']"),
                                    (By.XPATH, "//a[contains(.,'Case')]"),
                                    (By.CSS_SELECTOR, "#caseMemberTable"),
                                ]:
                                    try:
                                        if self._driver.find_elements(how, what):
                                            return h
                                    except Exception: continue
                            except Exception: continue
                except Exception:
                    return None
                return None

            # First, small sleep to let popups render
            time.sleep(0.6)
            # Wait either for new handle or for task elements to surface
            for _ in range(30):  # ~15s
                now = set(self._driver.window_handles)
                if len(now) > len(old_handles):
                    break
                h = task_ready_somewhere()
                if h:
                    self._driver.switch_to.window(h)
                    break
                time.sleep(0.5)

            # Best-effort: switch to window that has the "Case" link
            h = task_ready_somewhere()
            if h: 
                self._driver.switch_to.window(h)
            self.install_highlight_capture()
            return True
        except Exception as e:
            self.enqueue(f"[NAV][ERROR] Advanced click failed: {e}")
            return False

    def click_case_from_task(self):
        if not self._driver: self.enqueue("[NAV] Open Penelope first."); return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.action_chains import ActionChains
            for attempt in (1,2):
                clicked = False
                for h in self._driver.window_handles:
                    try:
                        self._driver.switch_to.window(h); self._driver.switch_to.default_content()
                        contexts = [None] + self._driver.find_elements(By.CSS_SELECTOR, "iframe,frame")
                        for fr in contexts:
                            try:
                                self._driver.switch_to.default_content()
                                if fr is not None: self._driver.switch_to.frame(fr)
                                for how, what in [
                                    (By.XPATH, "//a[normalize-space()='Case']"),
                                    (By.XPATH, "//a[contains(., 'Case')]"),
                                    (By.XPATH, "//*[contains(@onclick,'Case') or contains(@href,'Case')]"),
                                ]:
                                    try:
                                        el = self._driver.find_element(how, what)
                                        try: self._driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                                        except Exception: pass
                                        try: ActionChains(self._driver).move_to_element(el).pause(0.05).click().perform()
                                        except Exception:
                                            try: el.click()
                                            except Exception: self._driver.execute_script("arguments[0].click();", el)
                                        clicked = True; break
                                    except Exception: continue
                                if clicked: break
                            except Exception: continue
                        if clicked: break
                    except Exception: continue
                if clicked:
                    self.enqueue("[NAV] Clicked Case link on Task page."); self.install_highlight_capture(); return True
                time.sleep(0.6)
            self.enqueue("[NAV][ERROR] Case click did not succeed."); self.install_highlight_capture(); return False
        except Exception as e:
            self.enqueue(f"[NAV][ERROR] Case click failed: {e}"); return False

    def click_client_in_members_box(self):
        if not self._driver: self.enqueue("[NAV] Open Penelope first."); return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.action_chains import ActionChains
            clicked = False
            for h in self._driver.window_handles:
                try:
                    self._driver.switch_to.window(h); self._driver.switch_to.default_content()
                    contexts = [None] + self._driver.find_elements(By.CSS_SELECTOR, "iframe,frame")
                    for fr in contexts:
                        try:
                            self._driver.switch_to.default_content()
                            if fr is not None: self._driver.switch_to.frame(fr)
                            table = None
                            for css in ["#caseMemberTable", "table#caseMemberTable", "table.members, #membersTable"]:
                                try: table = self._driver.find_element(By.CSS_SELECTOR, css); break
                                except Exception: continue
                            el = None
                            if table:
                                try: el = table.find_element(By.CSS_SELECTOR, "tbody tr:nth-of-type(1) a, tbody tr a")
                                except Exception: pass
                            if not el:
                                try: el = self._driver.find_element(By.XPATH, "//*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'members')]//a")
                                except Exception: pass
                            if not el:
                                links = self._driver.find_elements(By.CSS_SELECTOR, "a")
                                for a in links:
                                    try:
                                        t = (a.text or "").strip()
                                        if " " in t and len(t) < 64:
                                            el = a; break
                                    except Exception: continue
                            if el:
                                try: self._driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                                except Exception: pass
                                try: ActionChains(self._driver).move_to_element(el).pause(0.05).click().perform()
                                except Exception:
                                    try: el.click()
                                    except Exception: self._driver.execute_script("arguments[0].click();", el)
                                clicked = True; break
                        except Exception: continue
                    if clicked: break
                except Exception: continue

            if clicked:
                self.enqueue("[NAV] Clicked client name in Members box."); self.install_highlight_capture(); return True
            self.enqueue("[NAV][ERROR] Members click did not succeed."); self.install_highlight_capture(); return False
        except Exception as e:
            self.enqueue(f"[NAV][ERROR] Members click failed: {e}"); return False

    
    def click_client_edit(self) -> bool:
        """
        Open the Edit overlay by calling the page's own JS *inside the correct iframe*.
        Your deep snapshot shows `function goOpenEdit()` lives in a frame (not the top window).
        We iterate windows/frames → find the frame that defines goOpenEdit → call it there.
        Then we wait for `#editLayer` and `#dynamicIframe` in that SAME frame.
        """
        if not self._driver:
            self.enqueue("[EDIT] No driver."); return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
        except Exception:
            self.enqueue("[EDIT][ERROR] Selenium libs missing."); return False

        d = self._driver
        wait = WebDriverWait(d, 15)

        # Find the frame that actually defines goOpenEdit()
        target = None  # (handle, frame_web_element_or_None)
        for h in d.window_handles:
            try:
                d.switch_to.window(h); d.switch_to.default_content()
                # Try root first
                try:
                    if d.execute_script("return typeof goOpenEdit==='function'"):
                        target = (h, None); break
                except Exception:
                    pass
                # Then each iframe
                frames = d.find_elements(By.CSS_SELECTOR, "iframe,frame")
                for fr in frames:
                    try:
                        d.switch_to.default_content(); d.switch_to.frame(fr)
                        if d.execute_script("return typeof goOpenEdit==='function'"):
                            target = (h, fr); break
                    except Exception:
                        continue
                if target: break
            except Exception:
                continue

        # Fallback: try an "Edit" tab element if goOpenEdit is not in JS scope
        if not target:
            self.enqueue("[EDIT][WARN] goOpenEdit() not found in any frame; trying navEdit element.")
            clicked = False
            for h in d.window_handles:
                try:
                    d.switch_to.window(h); d.switch_to.default_content()
                    frames = [None] + d.find_elements(By.CSS_SELECTOR, "iframe,frame")
                    for fr in frames:
                        try:
                            d.switch_to.default_content()
                            if fr is not None: d.switch_to.frame(fr)
                            for how, what in [
                                (By.CSS_SELECTOR, "#navEdit"),
                                (By.XPATH, "//*[@id='navEdit' or @aria-label='[edit]' or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'edit')]")
                            ]:
                                try:
                                    el = d.find_element(how, what)
                                    d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                                    try: el.click()
                                    except Exception: d.execute_script("arguments[0].click();", el)
                                    clicked = True; target = (h, fr); break
                                except Exception:
                                    continue
                            if clicked: break
                        except Exception:
                            continue
                    if clicked: break
                except Exception:
                    continue
            if not target:
                self.enqueue("[EDIT][ERROR] Failed to click Edit (navEdit) and goOpenEdit() missing."); return False

        # Switch to the target frame and invoke the open action
        try:
            d.switch_to.window(target[0]); d.switch_to.default_content()
            if target[1] is not None: d.switch_to.frame(target[1])
            try:
                if d.execute_script("return typeof goOpenEdit==='function'"):
                    d.execute_script("goOpenEdit();")
                    self.enqueue("[EDIT] goOpenEdit() called inside the correct frame.")
            except Exception:
                # If goOpenEdit doesn't exist here (fallback path), we already clicked navEdit above.
                pass
        except Exception as e:
            self.enqueue(f"[EDIT][ERROR] Could not trigger Edit overlay: {e}")
            return False

        # Wait for overlay scaffold in this same frame
        try:
            wait.until(lambda _:
                any(el.is_displayed() for el in d.find_elements(By.ID, "editLayer"))
            )
        except Exception:
            self.enqueue("[EDIT][WARN] editLayer not visible yet.")
        try:
            wait.until(lambda _:
                len(d.find_elements(By.ID, "dynamicIframe")) > 0
            )
        except Exception:
            self.enqueue("[EDIT][ERROR] dynamicIframe not found after opening Edit.")
            return False

        self.enqueue("[EDIT] Edit overlay is up (editLayer + dynamicIframe present).")
        return True

    
    def append_note_and_save(self) -> bool:
        """Append the note in Edit popup and Save.
        Keep all nav unchanged. If verification fails, we still Save after syncing.
        """
        if not self._driver:
            self.enqueue("[NOTE] No driver."); return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
        except Exception as e:
            self.enqueue(f"[NOTE][ERROR] Selenium libs: {e}"); return False
    
        d = self._driver
        wait = WebDriverWait(d, 14)
    
        # Compose line
        from datetime import datetime as _dt
        import time, html
        today_str = _dt.now().strftime("%m/%d/%Y")
        initials = (self.emp_initials.get() or "").strip()
        note_line = f"{today_str}, Welcome Letter and Welcome Packet Mailed and Uploaded to TN, {initials}"
        note_html = f"<div>{html.escape(note_line, quote=False)}<\/div>"
    
        # Find edit overlay + dynamic iframe (or alt)
        dyn_ifr = None; alt_used = False
        for h in d.window_handles:
            try:
                d.switch_to.window(h); d.switch_to.default_content()
                frames = [None] + d.find_elements(By.CSS_SELECTOR, "iframe,frame")
                for fr in frames:
                    try:
                        d.switch_to.default_content()
                        if fr is not None: d.switch_to.frame(fr)
                        if d.find_elements(By.ID, "editLayer"):
                            try:
                                dyn_ifr = d.find_element(By.ID, "dynamicIframe")
                            except Exception:
                                try:
                                    dyn_ifr = d.find_element(By.ID, "dynamicAltframe"); alt_used=True
                                except Exception:
                                    dyn_ifr = None
                            if dyn_ifr is not None:
                                break
                    except Exception: continue
                if dyn_ifr is not None: break
            except Exception: continue
    
        if dyn_ifr is None:
            self.enqueue("[NOTE][ERROR] Edit overlay not found."); return False
        if alt_used: self.enqueue("[NOTE][INFO] Using dynamicAltframe fallback.")
    
        try: d.switch_to.frame(dyn_ifr)
        except Exception as e:
            self.enqueue(f"[NOTE][ERROR] Cannot enter dynamic frame: {e}"); return False
    
        # Try to activate Notes tab
        try:
            for how, xp in [
                (By.XPATH, "//a[normalize-space()='Notes']"),
                (By.XPATH, "//*[self::a or self::button or self::span][contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'notes')]"),
            ]:
                try:
                    el = d.find_element(how, xp)
                    if el.is_displayed():
                        try: d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                        except Exception: pass
                        try: el.click()
                        except Exception: d.execute_script("arguments[0].click();", el)
                        break
                except Exception: pass
        except Exception: pass
    
        # Write into editor (iframe/contenteditable/textarea)
        wrote=False; kind=None; target=None
        end_t = time.time() + 10
        while time.time() < end_t and not wrote:
            try:
                # whizzy iframe
                fr = None
                try: fr = d.find_element(By.CSS_SELECTOR, "iframe#whizzyrt_FLD_irindividual_indnotes_id, iframe[id*='whizzyrt'][id*='indnotes']")
                except Exception: fr=None
                if fr is not None:
                    try: d.switch_to.frame(fr)
                    except Exception: pass
                    try:
                        d.execute_script(
                            "var b=document.body; if(!b){return};"
                            "var div=document.createElement('div'); div.appendChild(document.createTextNode(arguments[0])); b.appendChild(div);",
                            note_line)
                        wrote=True; kind='rte_iframe'; target=fr
                    except Exception: pass
                    try: d.switch_to.parent_frame()
                    except Exception: pass
                if not wrote:
                    # contenteditable body
                    try:
                        ce = next((e for e in d.find_elements(By.CSS_SELECTOR, "[contenteditable='true'],[contenteditable='']") if e.is_displayed()), None)
                        if ce:
                            d.execute_script(
                                "var el=arguments[0]; var e=document.createElement('div'); e.appendChild(document.createTextNode(arguments[1])); el.appendChild(e); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true}));",
                                ce, note_line)
                            wrote=True; kind='contenteditable'; target=ce
                    except Exception: pass
                if not wrote:
                    # textarea
                    try:
                        vis = [t for t in d.find_elements(By.XPATH, "//textarea[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'note') or contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'note')]") if t.is_displayed() and t.is_enabled()]
                        if vis:
                            tx = max(vis, key=lambda e: e.rect.get('width',0)*e.rect.get('height',0))
                            prev = (tx.get_attribute('value') or '').rstrip("\n")   # or ta.get_attribute('value')
                            new_val = (prev + "\n" if prev else "") + note_line
                            d.execute_script("arguments[0]....", tx, new_val)       # or (..., ta, new_val)
                            wrote=True; kind='textarea'; target=tx
                    except Exception: pass
            except Exception: pass
            if not wrote: time.sleep(0.2)
    
        # Mirror into hidden + textareas across dyn/parent/top
        def mirror_hidden_textareas():
            updated=False
            # common hidden ids/names
            sels = [
                "input[type='hidden']#rt_FLD_irindividual_indnotes_id",
                "input[type='hidden'][id*='rt_FLD_irindividual_indnotes_id' i]",
                "input[type='hidden'][id*='indnotes' i]",
                "input[type='hidden'][name*='indnotes' i]",
                "input[type='hidden'][id*='notes' i][id*='rt_' i]",
            ]
            for sel in sels:
                try:
                    for hid in d.find_elements(By.CSS_SELECTOR, sel):
                        try:
                            prev = hid.get_attribute('value') or ''
                            if (note_line in prev) or (html.escape(note_line, quote=False) in prev): updated=True; continue
                            if prev and not prev.rstrip().endswith("</div>"): prev += "<div></div>"
                            new_val = prev + note_html
                            d.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", hid, new_val)
                            updated=True
                        except Exception: pass
                except Exception: pass
            # any 'note' textareas
            try:
                for ta in d.find_elements(By.XPATH, "//textarea[contains(translate(@id,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'note') or contains(translate(@name,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'note')]"):
                    try:
                        prev = ta.get_attribute('value') or ''
                        if note_line in prev: updated=True; continue
                        sep = "\n\n" if (prev and not prev.endswith("\n\n")) else ""
                        new_val = prev + sep + note_line
                        d.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input',{bubbles:true})); arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", ta, new_val)
                        updated=True
                    except Exception: pass
            except Exception: pass
            return updated
    
        mirror_hidden_textareas()
        try: d.switch_to.parent_frame(); mirror_hidden_textareas()
        except Exception: pass
        try: d.switch_to.default_content(); mirror_hidden_textareas()
        except Exception: pass
        try: d.switch_to.frame(dyn_ifr)
        except Exception: pass
    
        # Site sync hooks in multiple scopes
        hooks = [
            "try{if(window.syncTextarea) syncTextarea();}catch(e){}",
            "try{if(window.copyRichTextToTextAreaAll) copyRichTextToTextAreaAll();}catch(e){}",
            "try{if(window.updateRTE) updateRTE('FLD_irindividual_indnotes_id');}catch(e){}",
            "try{if(window.parent && window.parent.copyRichTextToTextAreaAll) window.parent.copyRichTextToTextAreaAll();}catch(e){}",
            "try{if(window.top && window.top.copyRichTextToTextAreaAll) window.top.copyRichTextToTextAreaAll();}catch(e){}",
        ]
        for js in hooks:
            try: d.execute_script(js)
            except Exception: pass
    
        # Verify hidden anywhere; if fails, still continue to Save
        def verify_any():
            ok=False
            for scope in ('dyn','parent','top'):
                try:
                    if scope=='dyn':
                        pass
                    elif scope=='parent':
                        d.switch_to.parent_frame()
                    else:
                        d.switch_to.default_content()
                    for hid in d.find_elements(By.CSS_SELECTOR, "input[type='hidden'][id*='indnotes' i], input[type='hidden'][name*='indnotes' i], input[type='hidden'][id*='rt_' i][id*='notes' i]"):
                        val = hid.get_attribute('value') or ''
                        if (note_line in val) or (html.escape(note_line, quote=False) in val):
                            ok=True; break
                except Exception: pass
                finally:
                    try: d.switch_to.frame(dyn_ifr)
                    except Exception: pass
            if not ok and kind=='rte_iframe' and target is not None:
                try:
                    d.switch_to.frame(target)
                    inner = d.execute_script("return document.body ? (document.body.innerText||'') : '';") or ""
                    ok = (note_line in inner)
                except Exception: pass
                finally:
                    try: d.switch_to.parent_frame()
                    except Exception: pass
            if not ok and kind=='textarea' and target is not None:
                try:
                    v = target.get_attribute('value') or ''
                    ok = (note_line in v)
                except Exception: pass
            return ok
    
        if verify_any():
            self.enqueue(f"[NOTE] Appended note: \"{note_line}\"")
        else:
            self.enqueue("[NOTE][WARN] Verification failed; forcing Save after sync.")
    
        # Save button is outside dynamic iframe
        def click_save_in_scope(scope_el):
            for how, sel in [
                (By.CSS_SELECTOR, "#iframeEditSaveButton, .ui-dialog-buttonpane button"),
                (By.XPATH, ".//button[normalize-space()='Save' or normalize-space()='save']"),
                (By.XPATH, ".//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'save')]"),
                (By.XPATH, ".//input[@type='submit' and (translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='save' or contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'save'))]"),
            ]:
                try:
                    els = [e for e in scope_el.find_elements(how, sel) if e.is_displayed()]
                    if not els: continue
                    els.sort(key=lambda e: (e.rect.get('y',0), e.rect.get('x',0)))
                    btn = els[-1]
                    try: d.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    except Exception: pass
                    try: btn.click()
                    except Exception: d.execute_script("arguments[0].click();", btn)
                    return True
                except Exception: continue
            return False
    
        try:
            d.switch_to.parent_frame()
        except Exception:
            d.switch_to.default_content()
    
        saved=False
        try:
            dialog=None
            try:
                cands = [e for e in d.find_elements(By.CSS_SELECTOR, ".ui-dialog.ui-widget") if e.is_displayed()]
                if cands:
                    cands.sort(key=lambda e: e.rect.get('width',0)*e.rect.get('height',0), reverse=True)
                    dialog = cands[0]
            except Exception: dialog=None
            if dialog and click_save_in_scope(dialog):
                saved=True
            elif click_save_in_scope(d):
                saved=True
        except Exception:
            saved=False
    

        if not saved:
            # HARD FALLBACK: click overlay Save inside frame that owns #editLayer
            try:
                from selenium.webdriver.common.by import By
                d = self._driver
                owner = None
                for h in d.window_handles:
                    try:
                        d.switch_to.window(h); d.switch_to.default_content()
                        frames = [None] + d.find_elements(By.CSS_SELECTOR, "iframe,frame")
                        for fr in frames:
                            try:
                                d.switch_to.default_content()
                                if fr is not None: d.switch_to.frame(fr)
                                if not d.find_elements(By.ID, "editLayer"): 
                                    continue
                                btn = None
                                try:
                                    btn = d.find_element(By.CSS_SELECTOR, "#iframeEditSaveButton a")
                                except Exception:
                                    try:
                                        btn = d.find_element(By.CSS_SELECTOR, "#iframeEditSaveButton")
                                    except Exception:
                                        btn = None
                                if btn and btn.is_displayed():
                                    owner = (h, fr, btn); break
                            except Exception:
                                continue
                        if owner: break
                    except Exception:
                        continue
                if owner:
                    h, fr, btn = owner
                    d.switch_to.window(h); d.switch_to.default_content()
                    if fr is not None: d.switch_to.frame(fr)
                    try: d.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    except Exception: pass
                    try:
                        d.execute_script("(function(el){try{el.focus();}catch(e){}function fire(t){try{var ev=new MouseEvent(t,{bubbles:true,cancelable:true,view:window,buttons:1});el.dispatchEvent(ev);}catch(e){}}fire('mousedown');fire('mouseup');fire('click');})(arguments[0]);if(typeof goValidateIFrame==='function'){try{goValidateIFrame();}catch(e){}}", btn)
                        saved=True; self.enqueue("[NOTE] Clicked Save (fallback).")
                    except Exception:
                        saved=False
                else:
                    saved=False
            except Exception:
                saved=False
            if not saved:
                self.enqueue("[NOTE][WARN] Save button not found."); return False

    
        # Wait for popup to close
        try:
            t0=time.time()
            while time.time()-t0 < 8:
                d.switch_to.default_content()
                if not d.find_elements(By.ID, "editLayer"):
                    break
                time.sleep(0.3)
            self.enqueue("[NOTE] Popup closed.")
        except Exception:
            self.enqueue("[NOTE] Continuing without close confirm.")
        return True

    def click_close_button(self) -> bool:
        """
        Click the Close button in the general task page (in the Assigned box).
        This should be called after reaching the general task page.
        Optimized to remember which frame contains the close button for faster subsequent clicks.
        """
        if not self._driver:
            self.enqueue("[CLOSE] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception:
            self.enqueue("[CLOSE][ERROR] Selenium libs missing."); return False

        d = self._driver
        wait = WebDriverWait(d, 2)  # Even shorter timeout for faster failure

        try:
            # Switch to default content first
            d.switch_to.default_content()
            
            # Check if we know which frame has the close button (optimization)
            if hasattr(self, '_close_button_frame') and self._close_button_frame is not None:
                try:
                    frames = d.find_elements(By.CSS_SELECTOR, "iframe,frame")
                    if self._close_button_frame < len(frames):
                        d.switch_to.frame(frames[self._close_button_frame])
                        close_button = wait.until(EC.element_to_be_clickable(WORKFLOW_SEL["close_button"]))
                        self.enqueue(f"[CLOSE] Found close button in cached frame {self._close_button_frame}.")
                        
                        # Click immediately
                        d.execute_script("arguments[0].scrollIntoView({block:'center'});", close_button)
                        d.execute_script("arguments[0].click();", close_button)
                        self.enqueue("[CLOSE] Clicked Close button successfully.")
                        time.sleep(0.5)  # Reduced wait time
                        return True
                except Exception:
                    # Cache miss, fall through to full search
                    pass
            
            # Full search (first time or cache miss)
            close_button = None
            found_frame = None
            
            for h in d.window_handles:
                try:
                    d.switch_to.window(h)
                    d.switch_to.default_content()
                    
                    # Try to find close button in main content
                    try:
                        close_button = wait.until(EC.element_to_be_clickable(WORKFLOW_SEL["close_button"]))
                        self.enqueue("[CLOSE] Found close button in main content.")
                        found_frame = -1  # -1 means main content
                        break
                    except TimeoutException:
                        pass
                    
                    # Try to find close button in iframes
                    frames = d.find_elements(By.CSS_SELECTOR, "iframe,frame")
                    for i, fr in enumerate(frames):
                        try:
                            d.switch_to.frame(fr)
                            close_button = wait.until(EC.element_to_be_clickable(WORKFLOW_SEL["close_button"]))
                            self.enqueue(f"[CLOSE] Found close button in frame {i}.")
                            found_frame = i
                            break
                        except TimeoutException:
                            d.switch_to.default_content()
                            continue
                        finally:
                            d.switch_to.default_content()
                    
                    if close_button:
                        break
                except Exception as e:
                    continue
            
            if not close_button:
                # Try alternative selectors
                d.switch_to.default_content()
                for alt_selector in [
                    "a[href*='closeTask']",
                    "//a[contains(text(), 'Close')]",
                    "//a[contains(@href, 'closeTask')]"
                ]:
                    try:
                        if alt_selector.startswith("//"):
                            close_button = d.find_element(By.XPATH, alt_selector)
                        else:
                            close_button = d.find_element(By.CSS_SELECTOR, alt_selector)
                        if close_button and close_button.is_displayed():
                            self.enqueue(f"[CLOSE] Found close button with alternative selector: {alt_selector}")
                            found_frame = -1  # Assume main content
                            break
                    except Exception:
                        continue
                
                if not close_button:
                    self.enqueue("[CLOSE][WARN] Close button not found with any selector.")
                    return False
            
            # Cache the frame for next time (only if found_frame is valid)
            if found_frame is not None:
                self._close_button_frame = found_frame
            
            # Click the close button - re-find element to avoid stale reference
            try:
                # Re-find the element to avoid stale reference
                d.switch_to.default_content()
                if found_frame == -1:
                    # Main content
                    close_button = d.find_element(By.CSS_SELECTOR, "a[href*='actionType=closeTask']")
                elif found_frame is not None:
                    # Specific frame
                    frames = d.find_elements(By.CSS_SELECTOR, "iframe,frame")
                    if found_frame < len(frames):
                        d.switch_to.frame(frames[found_frame])
                        close_button = d.find_element(By.CSS_SELECTOR, "a[href*='actionType=closeTask']")
                    else:
                        raise Exception(f"Frame index {found_frame} out of range (found {len(frames)} frames)")
                else:
                    raise Exception("found_frame is None - close button not found")
                
                # Use JavaScript click to avoid stale element issues
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", close_button)
                d.execute_script("arguments[0].click();", close_button)
                self.enqueue("[CLOSE] Clicked Close button successfully.")
                time.sleep(0.5)  # Reduced wait time
                return True
            except Exception as e:
                self.enqueue(f"[CLOSE][ERROR] Failed to click close button: {e}")
                return False
                
        except Exception as e:
            self.enqueue(f"[CLOSE][ERROR] Error finding close button: {e}")
            return False

    def _check_pdf_dependencies(self) -> bool:
        """
        Check if PyPDF2 and reportlab are installed.
        Returns True if available, False otherwise.
        """
        try:
            import PyPDF2
            import reportlab
            return True
        except ImportError as e:
            missing = str(e).split()[-1] if "No module named" in str(e) else "required libraries"
            self.enqueue(f"[AUTO][ERROR] Missing PDF dependencies: {missing}")
            self.enqueue("[AUTO][ERROR] Cannot generate PDFs without PyPDF2 and reportlab.")
            self.enqueue("[AUTO][ERROR] Install with: pip install PyPDF2 reportlab")
            self.enqueue("[AUTO][ERROR] ⛔ STOPPING AUTO RUN - Install dependencies first!")
            return False

    def _valid_capture(self, nm, addr_lines):
        """
        Returns True when the captured name/address look sane enough to stamp a PDF.
        - name: at least 3 chars and not "administrator"
        - address: at least 2 non-empty lines and at least one digit somewhere
        """
        nm_ok = bool(nm and len(nm) >= 3 and "administrator" not in nm.lower())
        addr = [ (ln or "").strip() for ln in (addr_lines or []) if (ln or "").strip() ]
        has_digit = any(re.search(r"\d", ln or "") for ln in addr)
        addr_ok = (len(addr) >= 2) and has_digit
        if not nm_ok or not addr_ok:
            self.enqueue(f"[AUTO][WARN] Capture looks off (name_ok={nm_ok}, addr_ok={addr_ok}).")
        return nm_ok and addr_ok

    def _process_one_index(self, idx: int) -> bool:
        """
        One full pass:
          Advanced row @ idx → Case → Members → capture → PDF → reopen drawer → bump index.
        Returns True on success (PDF created), False on any hard failure.
        """
        self.enqueue(f"[AUTO] ▶ Processing advanced index {idx}")

        # Ensure the workflow drawer + Advanced list are visible before clicking
        try:
            self.reopen_workflow_drawer()
        except Exception:
            pass

        if not self.click_advanced_send_welcome():
            return False
        
        # NOTE: Close button must be clicked before navigating to client page (required for flow)
        # But we'll verify PDF generation will succeed before proceeding
        # Click the Close button in the general task page
        if not self.click_close_button():
            self.enqueue("[AUTO][WARN] Failed to click Close button, continuing anyway.")
        
        if not self.click_case_from_task():
            return False
        if not self.click_client_in_members_box():
            return False

        # Require taught selectors - CRITICAL: Must have these to generate PDFs
        if not self.learn.get("name") or not self.learn.get("address"):
            self.enqueue("[AUTO][WARN] Teach Name/Address via highlight first.")
            self.enqueue("[AUTO][ERROR] Cannot generate PDFs without selectors - workflow was already closed!")
            return False

        # Verify PDF templates exist before proceeding
        if not self.pdf_template or not os.path.isfile(self.pdf_template):
            self.enqueue("[AUTO][ERROR] Welcome letter template missing or not found!")
            self.enqueue("[AUTO][ERROR] Cannot generate PDFs - workflow was already closed!")
            return False

        # Capture data and validate
        self.auto_capture_from_learned()
        nm   = (self.current_capture.get("name") or "").strip()
        addr = list(self.current_capture.get("address") or [])

        if not self._valid_capture(nm, addr):
            self.enqueue("[AUTO][WARN] Skipping PDF due to invalid capture.")
            self.enqueue("[AUTO][ERROR] Cannot generate PDFs with invalid data - workflow was already closed!")
            try:
                self.reopen_workflow_drawer()
            except Exception:
                pass
            return False

        # Make PDF - CRITICAL: This must succeed (workflow already closed, but we need PDFs)
        pdf_success = self._build_one(nm, addr)
        if not pdf_success:
            self.enqueue("[AUTO][ERROR] ⛔ Welcome letter PDF generation FAILED!")
            self.enqueue("[AUTO][ERROR] Workflow was already closed - PDF was not generated!")
            self.enqueue("[AUTO][ERROR] This workflow needs to be manually reopened and processed again.")
            # Signal that this is a critical PDF failure - auto run should stop
            self._pdf_generation_failed = True
            return False

        # ---- SECOND PDF: Packet Letter ----
        packet_success = True
        if self.pdf_packet_template and os.path.isfile(self.pdf_packet_template):
            pdir, _ = self.get_output_dir(nm, letter_type="packet")
            packet_out = os.path.join(pdir, f"{sanitize_filename(nm)} Welcome Packet Letter.pdf")
            today_str = datetime.now().strftime("%m/%d/%Y")  # or "%B %d, %Y" for spelled-out
            initials = (self.emp_initials.get() or "IR").strip()
            self.enqueue(f"[PDF2] Filling + stamping Packet → {packet_out}")
            ok2 = stamp_packet_pdf(self.pdf_packet_template, packet_out, nm, initials, today_str, self.enqueue)
            if ok2:
                self.enqueue(f"[PDF2] Saved: {packet_out}")
            else:
                self.enqueue("[PDF2][WARN] Failed to save Packet letter (continuing anyway).")
                packet_success = False
        else:
            self.enqueue("[PDF2][SKIP] No Packet Letter PDF selected.")

        # ---- EDIT popup → append note → save ----
        try:
            if self.click_client_edit():
                try:
                    self.append_note_and_save()
                except Exception as e:
                    self.enqueue(f"[NOTE][ERROR] {e}")
        except Exception:
            self.enqueue("[EDIT][WARN] Edit step failed (continuing).")

        # Return to Advanced list for next row
        self.reopen_workflow_drawer()

        # Reflect next index in UI
        try:
            self.adv_index.set(idx + 1)
        except Exception:
            pass

        return True

    # ------------- RUN ONE -------------
    def run_one(self):
        def worker():
            # Check PDF dependencies before processing
            if not self._check_pdf_dependencies():
                self.enqueue("[AUTO] ❌ Aborting - PDF dependencies missing!")
                messagebox.showerror(
                    "Missing Dependencies",
                    "PyPDF2 and reportlab are required to generate PDFs.\n\n"
                    "Install with:\n"
                    "pip install PyPDF2 reportlab"
                )
                return
            
            try:
                idx = int(self.adv_index.get() or 0)
            except Exception:
                idx = 0
            ok = self._process_one_index(idx)
            if not ok:
                self.enqueue("[AUTO] Run One finished with a failure; check the log.")
        threading.Thread(target=worker, daemon=True).start()

    def run_auto(self):
        """Loop N times starting at current index, stop on user abort or repeated failure."""
        # clear any previous abort signal
        try:
            self._auto_abort.clear()
        except Exception:
            pass

        def worker():
            # CRITICAL: Check PDF dependencies BEFORE processing any workflows
            if not self._check_pdf_dependencies():
                self.enqueue("[AUTO] ❌ Aborting auto run - PDF dependencies missing!")
                messagebox.showerror(
                    "Missing Dependencies",
                    "PyPDF2 and reportlab are required to generate PDFs.\n\n"
                    "Install with:\n"
                    "pip install PyPDF2 reportlab\n\n"
                    "Auto run aborted to prevent closing workflows without generating PDFs."
                )
                return
            
            try:
                start_idx = int(self.adv_index.get() or 0)
            except Exception:
                start_idx = 0
            try:
                total = int(self.auto_count.get() or 1)
            except Exception:
                total = 1
            try:
                delay_s = float(self.auto_delay.get() or 0.0)
            except Exception:
                delay_s = 0.0

            self.enqueue(f"[AUTO] ▶ Auto run: start={start_idx}, count={total}, delay={delay_s}s")
            
            # Reset PDF failure flag at start of auto run
            self._pdf_generation_failed = False

            for step in range(total):
                if self._auto_abort.is_set():
                    self.enqueue("[AUTO] ⏹ Stopped by user.")
                    break
                
                # Check if PDF generation failed in previous iteration
                if self._pdf_generation_failed:
                    self.enqueue("[AUTO] ⛔ STOPPING AUTO RUN - PDF generation failed!")
                    messagebox.showerror(
                        "PDF Generation Failed",
                        f"PDF generation failed at index {idx}.\n\n"
                        "The workflow was already closed but no PDF was generated.\n"
                        "This workflow needs to be manually reopened and processed again.\n\n"
                        "Auto run has been stopped to prevent further issues.\n"
                        "Please check the logs and fix the issue before continuing."
                    )
                    break

                # Read current index each iteration (it gets updated after each successful process)
                try:
                    idx = int(self.adv_index.get() or 0)
                except Exception:
                    idx = start_idx + step
                ok = self._process_one_index(idx)

                # Check if PDF generation failed (critical failure - stop immediately)
                if self._pdf_generation_failed:
                    self.enqueue(f"[AUTO] ⛔ CRITICAL: PDF generation failed at index {idx}!")
                    self.enqueue("[AUTO] ⛔ STOPPING AUTO RUN IMMEDIATELY!")
                    messagebox.showerror(
                        "PDF Generation Failed - Auto Run Stopped",
                        f"PDF generation failed at index {idx}.\n\n"
                        "The workflow was already closed but no PDF was generated.\n"
                        "This workflow needs to be manually reopened and processed again.\n\n"
                        "Auto run has been stopped to prevent closing more workflows without generating PDFs.\n"
                        "Please check the logs and fix the issue before continuing."
                    )
                    break

                if not ok:
                    # Soft retry once (but only if it's not a PDF generation failure)
                    self.enqueue("[AUTO] Retrying this index once after a short pause…")
                    time.sleep(0.6)
                    try:
                        self.reopen_workflow_drawer()
                    except Exception:
                        pass
                    ok = self._process_one_index(idx)
                    
                    # Check again after retry
                    if self._pdf_generation_failed:
                        self.enqueue(f"[AUTO] ⛔ CRITICAL: PDF generation failed at index {idx} (after retry)!")
                        self.enqueue("[AUTO] ⛔ STOPPING AUTO RUN IMMEDIATELY!")
                        messagebox.showerror(
                            "PDF Generation Failed - Auto Run Stopped",
                            f"PDF generation failed at index {idx} even after retry.\n\n"
                            "The workflow was already closed but no PDF was generated.\n"
                            "This workflow needs to be manually reopened and processed again.\n\n"
                            "Auto run has been stopped to prevent closing more workflows without generating PDFs.\n"
                            "Please check the logs and fix the issue before continuing."
                        )
                        break

                if not ok and not self._pdf_generation_failed:
                    self.enqueue(f"[AUTO] ❌ Failed at index {idx}, advancing to next workflow.")
                    # Advance index even on failure so we can try the next workflow
                    try:
                        self.adv_index.set(idx + 1)
                    except Exception:
                        pass
                    # Continue to next iteration instead of breaking
                    # Only break if we've exhausted all retries for multiple consecutive failures
                    if step < total - 1:
                        # Continue to next workflow
                        pass
                    else:
                        # Last iteration, stop
                        break
                elif ok:
                    # Success - index already updated by _process_one_index
                    pass

                if delay_s > 0:
                    time.sleep(delay_s)

            self.enqueue("[AUTO] ✅ Auto run finished.")
        threading.Thread(target=worker, daemon=True).start()

    def stop_auto(self):
        try:
            self._auto_abort.set()
        except Exception:
            pass

    # ---- IPS Uploader launcher ----
    def open_ips_uploader(self):
        here = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            "IPS_Welcome_FillAndUpload.exe",
            "IPS_Welcome_NewBot.exe",
            "IPS_NewBot_FillAndUpload_MINCHANGE_FIX5.py",   # your working IPS script
            "isws_welcome_packet_uploader_v14style_FIXED.py",  # optional fallback
            "run_IPS_NewBot_MINCHANGE_FIX5.bat",
        ]
        # try common names in same folder
        for name in candidates:
            p = os.path.join(here, name)
            if os.path.isfile(p):
                self._launch_path(p)
                return
        # else ask
        p = filedialog.askopenfilename(
            title="Locate IPS Welcome Uploader",
            initialdir=here,
            filetypes=[("Executables/Scripts","*.exe *.py *.bat"), ("All files","*.*")]
        )
        if p:
            self._launch_path(p)

    def _launch_path(self, path):
        ext = os.path.splitext(path)[1].lower()
        cwd = os.path.dirname(path)
        try:
            if ext == ".exe":
                subprocess.Popen([path], cwd=cwd)
            elif ext == ".py":
                subprocess.Popen([sys.executable, path], cwd=cwd)
            elif ext == ".bat":
                comspec = os.environ.get("COMSPEC", "cmd.exe")
                subprocess.Popen([comspec, "/c", "start", "", path], cwd=cwd, shell=True)
            else:
                subprocess.Popen([path], cwd=cwd)
        except Exception as e:
            messagebox.showerror("Launch failed", str(e))

    # ------------- Workflow Queue Management -------------
    def expand_queue_and_pickup_all(self):
        """Expand the workflow queue and pickup all 'Send Welcome Letter and NPP' workflows"""
        if not SELENIUM_AVAILABLE:
            self.enqueue("[ERROR] Selenium not available. Please install selenium: pip install selenium")
            return
            
        if not self._driver:
            self.enqueue("[ERROR] No browser session. Please login to Penelope first.")
            return

        def run():
            try:
                target = TARGET_WORKFLOW_TITLE.lower()
                total = 0
                debug = self.debug_mode.get()
                
                self.enqueue(f"[QUEUE] Starting to pickup all '{TARGET_WORKFLOW_TITLE}' workflows...")
                if debug:
                    self.enqueue(f"[DEBUG] Looking for exact match: '{target}'")
                
                # Ensure we're on the current tasks tab (which shows the queue)
                self._driver.switch_to.default_content()
                try:
                    current_tab = self._driver.find_element(*WORKFLOW_SEL["tab_current"])
                    if current_tab.is_displayed():
                        current_tab.click()
                        time.sleep(0.5)
                        self.enqueue("[QUEUE] Switched to Current Tasks tab")
                except Exception as e:
                    self.enqueue(f"[WARN] Could not switch to Current Tasks tab: {e}")
                
                # Wait for queue container to be visible
                container = self._wait_for_element(WORKFLOW_SEL["queue_container"], 15)
                if not container:
                    self.enqueue("[QUEUE] Could not find queue container.")
                    return
                
                # Main loop: expand and pickup incrementally (like Remove Counselor Bot)
                while True:
                    # First, expand the queue fully (like Remove Counselor Bot does)
                    self.enqueue("[EXPAND] Expanding queue fully...")
                    self._expand_queue_fully()
                    
                    # Get all visible rows from the fully expanded queue
                    try:
                        body = self._driver.find_element(*WORKFLOW_SEL["queue_body"])
                        rows = [r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()]
                        self.enqueue(f"[QUEUE] Found {len(rows)} visible rows in fully expanded queue")
                    except Exception as e:
                        self.enqueue(f"[ERROR] Could not get queue rows: {e}")
                        break
                    
                    # Debug: Show all workflow titles if debug mode is on
                    if debug and rows:
                        self.enqueue("[DEBUG] Current workflow titles:")
                        for i, r in enumerate(rows):
                            try:
                                subj_link = r.find_element(*WORKFLOW_SEL["row_subject_link"])
                                subj_text = subj_link.text.strip()
                                self.enqueue(f"[DEBUG] Row {i+1}: '{subj_text}'")
                            except NoSuchElementException:
                                self.enqueue(f"[DEBUG] Row {i+1}: No subject link found")
                    
                    # Look for the first matching workflow in the fully expanded queue
                    match_row = None
                    for i, r in enumerate(rows):
                        try:
                            subj_link = r.find_element(*WORKFLOW_SEL["row_subject_link"])
                            subj_text = subj_link.text.strip()
                            subj_lower = subj_text.lower()
                            
                            if debug:
                                self.enqueue(f"[DEBUG] Checking row {i+1}: '{subj_text}' == '{target}' ? {subj_lower == target}")
                            
                            if subj_lower == target:
                                match_row = r
                                break
                        except Exception as e:
                            if debug:
                                self.enqueue(f"[DEBUG] Row {i+1}: Error finding elements - {e}")
                            continue
                    
                    # If no match found, we're done
                    if match_row is None:
                        self.enqueue("[DONE] No matching workflows left.")
                        break
                    
                    # Pick up the found match
                    try:
                        pickup_el = match_row.find_element(*WORKFLOW_SEL["row_pickup"])
                        if pickup_el.is_displayed():
                            pickup_el.click()
                            total += 1
                            self.enqueue(f"[PICKUP] Processed '{TARGET_WORKFLOW_TITLE}' workflow. Count={total}.")
                            time.sleep(0.7)  # Allow retract/re-render (like Remove Counselor Bot)
                        else:
                            self.enqueue("[WARN] Pickup button not visible; skipping row.")
                    except NoSuchElementException:
                        self.enqueue("[WARN] Pickup link missing; skipping row.")
                    
                    # Safety limit
                    if total >= 50:
                        self.enqueue("[SAFE] Max pickups cap (50) reached. Stopping.")
                        break
                
                self.enqueue(f"[DONE] Total pickups: {total}.")
                
            except Exception as e:
                self.enqueue(f"[ERROR] Queue pickup failed: {e}")
        
        threading.Thread(target=run, daemon=True).start()

    def _expand_queue_sync(self, verbose=False):
        """Expand the queue by clicking 'Load More' until no more tasks are available"""
        try:
            # Ensure we're on the queue tab
            self._driver.switch_to.default_content()
            queue_tab = self._driver.find_element(*WORKFLOW_SEL["tab_current"])
            if queue_tab.is_displayed():
                queue_tab.click()
                time.sleep(0.5)
            
            # Wait for queue container to be visible
            container = self._wait_for_element(WORKFLOW_SEL["queue_container"], 15)
            if not container:
                if verbose:
                    self.enqueue("[EXPAND] Queue container not found.")
                return 0
            
            # Count initial rows
            body = self._driver.find_element(*WORKFLOW_SEL["queue_body"])
            base_rows = len([r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()])
            clicks = 0
            
            while True:
                try:
                    # Look for the "Load More" button
                    load_more = WebDriverWait(self._driver, 2).until(
                        EC.visibility_of_element_located(WORKFLOW_SEL["queue_load_more"])
                    )
                    load_more.click()
                    clicks += 1
                    time.sleep(0.4)
                    
                    # Check if we got more rows
                    new_rows = len([r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()])
                    if new_rows <= base_rows:
                        if verbose:
                            self.enqueue(f"[EXPAND] No new rows after click; stop at {new_rows}.")
                        break
                    base_rows = new_rows
                    
                    if verbose:
                        self.enqueue(f"[EXPAND] Queue rows={base_rows} (clicks={clicks}).")
                    
                    # Safety limit
                    if clicks >= 20:
                        if verbose:
                            self.enqueue("[SAFE] Queue expansion cap reached (20).")
                        break
                        
                except TimeoutException:
                    if verbose:
                        self.enqueue(f"[EXPAND] No more 'Load More' button; rows={base_rows}.")
                    break
                except Exception as e:
                    if verbose:
                        self.enqueue(f"[EXPAND] Error during expansion: {e}")
                    break
            
            return base_rows
            
        except Exception as e:
            if verbose:
                self.enqueue(f"[EXPAND] Queue expansion failed: {e}")
            return 0

    def _wait_for_element(self, locator, timeout=25):
        """Wait for an element to be visible and return it"""
        try:
            wait = WebDriverWait(self._driver, timeout)
            return wait.until(EC.visibility_of_element_located(locator))
        except TimeoutException:
            return None

    def _expand_queue_fully(self):
        """Expand the queue fully by clicking 'Load More' until exhausted (like Remove Counselor Bot)"""
        try:
            # Make sure we're on the Current Tasks tab
            current_tab = self._driver.find_element(*WORKFLOW_SEL["tab_current"])
            if current_tab.is_displayed():
                current_tab.click()
                time.sleep(0.3)
        except Exception:
            pass
        
        # Wait for queue container to be visible
        container = self._wait_for_element(WORKFLOW_SEL["queue_container"], 15)
        if not container:
            self.enqueue("[EXPAND] Could not find queue container.")
            return
        
        # Count initial rows
        try:
            body = self._driver.find_element(*WORKFLOW_SEL["queue_body"])
            base_rows = len([r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()])
        except Exception:
            base_rows = 0
        
        clicks = 0
        while True:
            try:
                # Look for Load More button
                load_more = WebDriverWait(self._driver, 2).until(
                    EC.visibility_of_element_located(WORKFLOW_SEL["queue_load_more"])
                )
            except TimeoutException:
                self.enqueue(f"[EXPAND] No more 'Load More' button; final rows={base_rows}.")
                break
            
            # Click Load More
            load_more.click()
            clicks += 1
            time.sleep(0.4)  # Allow time for new rows to load
            
            # Count new rows
            try:
                body = self._driver.find_element(*WORKFLOW_SEL["queue_body"])
                new_rows = len([r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()])
            except Exception:
                new_rows = base_rows
            
            # Check if we got new rows
            if new_rows <= base_rows:
                self.enqueue(f"[EXPAND] No new rows after click; stop at {new_rows}.")
                break
            
            base_rows = new_rows
            self.enqueue(f"[EXPAND] Queue expanded to {base_rows} rows (clicks={clicks}).")
            
            # Safety limit
            if clicks >= 20:
                self.enqueue("[EXPAND] Expansion cap reached (20).")
                break
                
        return base_rows

    def _expand_current_fully(self):
        """Expand the current tasks fully by clicking 'Load More' until exhausted (like Remove Counselor Bot)"""
        try:
            # Make sure we're on the Current Tasks tab
            current_tab = self._driver.find_element(*WORKFLOW_SEL["tab_current"])
            if current_tab.is_displayed():
                current_tab.click()
                time.sleep(0.3)
        except Exception:
            pass
        
        # Wait for current tasks container to be visible
        container = self._wait_for_element(WORKFLOW_SEL["current_container"], 15)
        if not container:
            self.enqueue("[EXPAND] Could not find current tasks container.")
            return
        
        # Count initial rows
        try:
            body = self._driver.find_element(*WORKFLOW_SEL["current_body"])
            base_rows = len([r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()])
        except Exception:
            base_rows = 0
        
        clicks = 0
        consecutive_no_new_rows = 0
        while True:
            try:
                # Look for Load More button
                load_more = WebDriverWait(self._driver, 2).until(
                    EC.visibility_of_element_located(WORKFLOW_SEL["current_load_more"])
                )
            except TimeoutException:
                self.enqueue(f"[EXPAND] No more 'Load More Current Tasks' button; final rows={base_rows}.")
                break
            
            # Click Load More
            load_more.click()
            clicks += 1
            time.sleep(0.6)  # Allow more time for new rows to load
            
            # Count new rows
            try:
                body = self._driver.find_element(*WORKFLOW_SEL["current_body"])
                new_rows = len([r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()])
            except Exception:
                new_rows = base_rows
            
            # Check if we got new rows
            if new_rows <= base_rows:
                consecutive_no_new_rows += 1
                self.enqueue(f"[EXPAND] No new rows after click {clicks}; consecutive={consecutive_no_new_rows}")
                # Only stop if we've had multiple consecutive clicks with no new rows
                if consecutive_no_new_rows >= 3:
                    self.enqueue(f"[EXPAND] Stopping after {consecutive_no_new_rows} consecutive clicks with no new rows.")
                    break
            else:
                consecutive_no_new_rows = 0  # Reset counter
                base_rows = new_rows
                self.enqueue(f"[EXPAND] Current tasks expanded to {base_rows} rows (clicks={clicks}).")
            
            # Safety limit
            if clicks >= 50:  # Increased limit
                self.enqueue("[EXPAND] Expansion cap reached (50).")
                break
                
        return base_rows

    def build_chunks(self):
        """Build 2-week chunks from Current Tasks (using Load More Current Tasks button)"""
        def run():
            try:
                target = TARGET_WORKFLOW_TITLE.lower()
                self.enqueue("[CHUNK] Building 2-week chunks from Current Tasks...")
                
                # Expand current tasks fully (using Load More Current Tasks button)
                self._expand_current_fully()
                
                # Get all visible rows from the fully expanded current tasks
                body = self._driver.find_element(*WORKFLOW_SEL["current_body"])
                rows = [r for r in body.find_elements(By.CSS_SELECTOR, "tr") if r.is_displayed()]
                self.enqueue(f"[CHUNK] Found {len(rows)} visible rows in current tasks")
                
                # Extract dates from matching workflows
                dates = []
                for r in rows:
                    try:
                        subj_link = r.find_element(*WORKFLOW_SEL["row_subject_link"])
                        subj_text = subj_link.text.strip().lower()
                        if subj_text != target:
                            continue
                        
                        date_cell = r.find_element(*WORKFLOW_SEL["row_date"])
                        date_text = date_cell.text.strip()
                        
                        # Convert relative dates to actual dates
                        from datetime import datetime, timedelta
                        today = datetime.now().date()
                        
                        if date_text.lower() == "today":
                            d = datetime.combine(today, datetime.min.time())
                        elif date_text.lower() == "yesterday":
                            d = datetime.combine(today - timedelta(days=1), datetime.min.time())
                        elif date_text.lower() == "tomorrow":
                            d = datetime.combine(today + timedelta(days=1), datetime.min.time())
                        else:
                            # Try to parse as MM/DD/YYYY format
                            try:
                                d = datetime.strptime(date_text, "%m/%d/%Y")
                            except ValueError:
                                self.enqueue(f"[WARN] Unparseable date '{date_text}' — skipping.")
                                continue
                        
                        dates.append(d)
                    except Exception as e:
                        continue
                
                if not dates:
                    self.chunks = []
                    self.next_chunk_index = 0
                    self.enqueue("[CHUNK] No matching Current tasks found.")
                    return
                
                # Sort dates and create 2-week chunks
                dates.sort()
                chunks = []
                cur_from = dates[0]
                end = dates[-1]
                
                while cur_from <= end:
                    from datetime import timedelta
                    cur_to = min(cur_from + timedelta(days=13), end)
                    chunks.append((cur_from.strftime("%m/%d/%Y"), cur_to.strftime("%m/%d/%Y")))
                    cur_from = cur_to + timedelta(days=1)
                
                self.chunks = chunks
                self.next_chunk_index = 0
                
                for a, b in chunks:
                    self.enqueue(f"[CHUNK] {a}–{b}")
                self.enqueue(f"[DONE] Built {len(chunks)} chunk(s).")
                
            except Exception as e:
                self.enqueue(f"[ERROR] Build Chunks failed: {e}")
        
        threading.Thread(target=run, daemon=True).start()

    def fill_next_chunk(self):
        """Fill the next chunk dates in advanced search (like Remove Counselor Bot)"""
        def run():
            try:
                if not self.chunks:
                    self.enqueue("[ADV] No chunks in memory; build chunks first.")
                    return
                if self.next_chunk_index >= len(self.chunks):
                    self.enqueue("[ADV] All chunks already filled.")
                    return
                
                # Switch to Advanced tab
                try:
                    adv_tab = self._driver.find_element(*WORKFLOW_SEL["tab_advanced"])
                    if adv_tab.is_displayed():
                        adv_tab.click()
                        time.sleep(0.5)
                        self.enqueue("[ADV] Switched to Advanced tab")
                except Exception as e:
                    self.enqueue(f"[WARN] Could not switch to Advanced tab: {e}")
                
                # Get the next chunk
                a, b = self.chunks[self.next_chunk_index]
                
                # Fill the date fields
                from_field = self._wait_for_element(WORKFLOW_SEL["adv_from"], 10)
                to_field = self._wait_for_element(WORKFLOW_SEL["adv_to"], 10)
                
                if from_field and to_field:
                    from_field.clear()
                    from_field.send_keys(a)
                    to_field.clear()
                    to_field.send_keys(b)
                    self.next_chunk_index += 1
                    self.enqueue(f"[ADV] Set From={a} To={b}")
                else:
                    self.enqueue("[ERROR] Could not find date input fields")
                
            except Exception as e:
                self.enqueue(f"[ERROR] Fill Next Chunk failed: {e}")
        
        threading.Thread(target=run, daemon=True).start()

    # ------------- Queue / Build -------------
    def get_output_dir(self, full_name, letter_type="welcome"):
        """
        Get the output directory based on the organized_folders toggle.
        
        Args:
            full_name: Client's full name
            letter_type: "welcome" for welcome letters, "packet" for packet letters
        
        Returns:
            tuple: (output_directory, base_directory)
        """
        if not self.base_dir.get():
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            base_dir = os.path.join(desktop, "Welcome Bot Output")
        else:
            base_dir = self.base_dir.get()
        
        os.makedirs(base_dir, exist_ok=True)
        
        if self.organized_folders.get():
            # Organized mode: create folders by letter type
            if letter_type == "packet":
                output_dir = os.path.join(base_dir, "Welcome Packet Letters")
            else:  # welcome letter
                output_dir = os.path.join(base_dir, "Welcome Letters")
            os.makedirs(output_dir, exist_ok=True)
            return output_dir, base_dir
        else:
            # Original mode: create folder per client
            pdir = os.path.join(base_dir, sanitize_filename(full_name))
            os.makedirs(pdir, exist_ok=True)
            return pdir, base_dir
    
    def queue_letter(self):
        nm = self.current_capture.get("name","").strip()
        addr = list(self.current_capture.get("address") or [])
        if not nm or not addr:
            messagebox.showwarning("Missing info", "Current capture needs both a Name and an Address."); return
        self.batch.append({"name": nm, "address": addr})
        self.lbl_batch.config(text=f"Queued: {len(self.batch)}")
        self.enqueue(f"[QUEUE] Added: {nm}  ({' | '.join(addr)})")

    def make_letter_current(self):
        nm = self.current_capture.get("name","").strip()
        addr = list(self.current_capture.get("address") or [])
        if not nm or not addr:
            messagebox.showwarning("Missing info", "Current capture needs both a Name and an Address."); return
        self._build_one(nm, addr)

    def build_all(self):
        if not self.batch:
            messagebox.showinfo("Nothing queued", "Queue at least one letter first."); return
        for item in list(self.batch):
            self._build_one(item["name"], item["address"])
        self.batch.clear(); self.lbl_batch.config(text="Queued: 0")

    def _build_one(self, full_name, address_lines):
        # Require at least the English template; Spanish is optional (falls back to English).
        if not self.pdf_template or not os.path.isfile(self.pdf_template):
            messagebox.showwarning("Template missing", "Select the English Welcome Letter PDF template first.")
            return False

        # Decide which template to use based on captured language (english/spanish/unknown)
        lang_norm = (self.current_capture.get("language") or "").strip().lower() or "unknown"
        chosen_template = pick_welcome_template(lang_norm, self.pdf_template, getattr(self, "pdf_template_spanish", ""))

        if not chosen_template or not os.path.isfile(chosen_template):
            self.enqueue("[PDF][ERROR] Template file not found or missing.")
            return False

        pdir, _ = self.get_output_dir(full_name, letter_type="welcome")
        # File name suffix by language
        out_suffix = "Carta de Bienvenida.pdf" if lang_norm == "spanish" else "Welcome Letter.pdf"
        out_path = os.path.join(pdir, f"{sanitize_filename(full_name)} {out_suffix}")

        # Log what we're doing
        try:
            tmpl_name = os.path.basename(chosen_template) if chosen_template else "(missing)"
        except Exception:
            tmpl_name = "(unknown)"
        self.enqueue(f"[PDF] Language={lang_norm} → Using template: {tmpl_name}")
        self.enqueue(f"[PDF] Filling + stamping → {out_path}")

        ok = stamp_letter_pdf(chosen_template, out_path, full_name, address_lines, self.enqueue)
        if ok:
            self.enqueue(f"[PDF] Saved: {out_path}")
            return True
        else:
            self.enqueue("[PDF] Failed to save letter. See errors above.")
            return False

# ------------------------ Run ------------------------
if __name__ == "__main__":
    try:
        root = tk.Tk(); app = App(root); root.mainloop()
    except Exception as e:
        print("[FATAL] GUI failed to start:", e)