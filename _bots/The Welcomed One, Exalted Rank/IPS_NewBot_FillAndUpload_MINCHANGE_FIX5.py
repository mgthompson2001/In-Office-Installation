#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IPS NewBot — Minimal Change + Welcome Letter Formatting (FIX5)
---------------------------------------------------------------
- Same Selenium nav + upload as FIX3.
- Creates BOTH PDFs; both flattened/non-fillable.
- Uploads only the Packet.
- **Welcome Letter layout:**
    1) Client Name
    2) "<Street> - Unit <X>"  (if unit exists)  OR "<Street>" (if no unit)
    3) "City ST"
    4) "United States ZIP"  (ZIP+4 hyphenated)
- **No initials** on the Welcome Letter.
"""
import os, re, sys, time, threading, queue, tempfile, io
from typing import List, Tuple, Optional
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox

APP_TITLE = "IPS Welcome Bot & Uploader"
TN_LOGIN_URL = "https://www.therapynotes.com/app/login/IntegrityIPS/"
MAROON = "#800000"; CARD_BG = "#faf7f7"; LOG_BG="#f5f5f5"; LOG_FG="#000"

# ------------- UI Logger -------------
class UILog:
    def __init__(self, text_widget: scrolledtext.ScrolledText):
        self.text = text_widget; self.q = queue.Queue(); self.text.after(80, self._flush)
    def write(self, msg: str): self.q.put(msg)
    def _flush(self):
        try:
            while not self.q.empty():
                line = self.q.get()
                try: self.text.insert(tk.END, line + "\n"); self.text.see(tk.END)
                except Exception: sys.stdout.write(line + "\n")
        finally:
            self.text.after(120, self._flush)

# ------------- Selenium lazy import -------------
By = WebDriverWait = EC = None
def _lazy_import_selenium():
    global By, WebDriverWait, EC
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By as _By
        from selenium.webdriver.support.ui import WebDriverWait as _WebDriverWait
        from selenium.webdriver.support import expected_conditions as _EC
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception as e:
        raise RuntimeError(f"Install selenium + webdriver-manager: {e}")
    return webdriver, _By, _WebDriverWait, _EC, Service, ChromeDriverManager

# ------------- CSV helpers -------------
def load_csv_slice(csv_path: str, start_line: int, end_line: int, log) -> Optional["pd.DataFrame"]:
    try:
        import pandas as pd
    except Exception as e:
        log(f"[CSV][ERR] pandas not installed: {e}"); return None
    df = None
    try:
        df = pd.read_csv(csv_path, sep=None, engine="python")
    except Exception:
        pass
    if df is None:
        for enc in ("utf-8","utf-8-sig","cp1252","latin-1"):
            for sep in (None, ",", "\t", ";"):
                try:
                    df = pd.read_csv(csv_path, encoding=enc, sep=sep, engine="python"); break
                except Exception: df=None
            if df is not None: break
    if df is None:
        log("[CSV][ERR] Could not read CSV with multiple encodings/separators."); return None
    n=len(df); start_idx = 0 if start_line<=1 else max(0,start_line-2); end_idx=max(0,min(n-1,end_line-2))
    if end_idx<start_idx:
        log(f"[CSV][ERR] Invalid range (end {end_line} < start {start_line})."); return df.iloc[0:0]
    return df.iloc[start_idx:end_idx+1].copy()

def find_column(df, candidates: List[str]) -> Optional[str]:
    lower={c.lower():c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower: return lower[cand.lower()]
    return None

# ------------- Utils -------------
def full_name_from_row(row, first_col: Optional[str], last_col: Optional[str], full_col: Optional[str]) -> Optional[str]:
    if full_col and isinstance(row.get(full_col), str) and row.get(full_col).strip():
        return row[full_col].strip()
    first=(row.get(first_col) or "").strip() if first_col else ""
    last =(row.get(last_col)  or "").strip() if last_col  else ""
    name=(first+" "+last).strip()
    return name or None

def sanitize_middle_initial_periods(name: str) -> str:
    name = name or ""
    name = re.sub(r"\b([A-Za-z])\.(?=\s|\b)", r"\1", name)  # drop periods after single-letter initials
    return re.sub(r"\s+"," ",name).strip()

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

def desktop_dir() -> str: return os.path.join(os.path.expanduser("~"), "Desktop")

# ------------- Address formatting (Letter) -------------
UNIT_PAT = re.compile(r'\b(?:Apt\.?|Apartment|Unit|#|Suite|Ste\.?)\s*([A-Za-z0-9\-]+)', re.IGNORECASE)
CITY_ST_ZIP_RE = re.compile(r'^\s*([^,]+?)[,\s]+([A-Z]{2})\s+(\d{5}(?:-?\d{4})?)\s*$')

def split_street_and_unit(line1: str) -> tuple:
    if not line1: return ("", "")
    m = UNIT_PAT.search(line1)
    if m:
        unit_id = m.group(1)
        unit_label = "Unit " + unit_id
        street = UNIT_PAT.sub('', line1).strip().rstrip(',')
        street = re.sub(r'\s{2,}', ' ', street)
        return (street, unit_label)
    return (line1.strip().rstrip(','), "")

def reformat_city_state_zip(line: str) -> tuple:
    if not line:
        return ("", "United States")
    m = CITY_ST_ZIP_RE.match(line) or CITY_ST_ZIP_RE.match(line.replace(",", ""))
    if not m:
        return (line.strip(), "United States")
    city, st, z = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    z = re.sub(r'^(\d{5})(\d{4})$', r'\1-\2', z)
    return (f"{city} {st}", f"United States {z}")

def format_letter_lines(client_name: str, addr_lines: List[str]) -> List[str]:
    """
    Returns exactly 4 lines for the Welcome Letter block:
      1) Client Name
      2) "<Street> - Unit <X>" or "<Street>"
      3) "City ST"
      4) "United States ZIP"
    """
    addr_lines = [ln for ln in (addr_lines or []) if ln]
    street_raw = addr_lines[0] if len(addr_lines) > 0 else ""
    citystzip = addr_lines[1] if len(addr_lines) > 1 else ""
    street, unit = split_street_and_unit(street_raw)
    street_line = f"{street} - {unit}" if unit else street
    cityst, countryzip = reformat_city_state_zip(citystzip)
    return [client_name or "", street_line or "", cityst or "", countryzip or "United States"]

# ------------- Selenium nav (UNCHANGED) -------------
def tn_login(driver, wait, username: str, password: str, log) -> bool:
    log("[TN] Opening TherapyNotes (IntegrityIPS)…"); driver.get(TN_LOGIN_URL)
    try:
        u = wait.until(EC.presence_of_element_located((By.ID,"Login__UsernameField")))
        p = wait.until(EC.presence_of_element_located((By.ID,"Login__Password")))
        b = wait.until(EC.element_to_be_clickable((By.ID,"Login__LogInButton")))
        u.clear(); u.send_keys(username); p.clear(); p.send_keys(password); b.click()
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT,"Patients"))); log("[TN] Login successful."); return True
    except Exception as e:
        log(f"[TN][ERR] Login failed: {e}"); return False

def safe_click(wait, driver, locator, timeout=14):
    try:
        el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(locator))
        try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        except Exception: pass
        try: el.click()
        except Exception: driver.execute_script("arguments[0].click();", el)
        return True
    except Exception:
        return False

def go_patients(wait, driver) -> bool: return safe_click(wait, driver, (By.LINK_TEXT,"Patients"))

def ensure_patient_info_loaded(wait, driver) -> bool:
    try:
        WebDriverWait(driver, 14).until(EC.presence_of_element_located((By.ID,"PatientInformationViewerContentBubble")))
        WebDriverWait(driver, 14).until(EC.presence_of_element_located((By.ID,"PatientInformation__AddressElem")))
        return True
    except Exception: return False

def extract_address(wait, driver) -> List[str]:
    try:
        el = WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.ID, "PatientInformation__AddressElem")))
        text = (el.text or "").strip()
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return lines[:4]
    except Exception:
        return []

def search_and_open_patient(wait, driver, name: str, log) -> bool:
    import time as _time, re as _re
    from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
    def norm(s): s=(s or "").lower(); s=_re.sub(r"[^a-z0-9 ]+"," ",s); s=_re.sub(r"\s+"," ",s).strip(); return s
    variants=[]; san=sanitize_middle_initial_periods(name); variants=[san] if san!=name else [name]
    if name not in variants: variants.append(name)
    for variant in variants:
        toks=[t for t in norm(variant).split() if t]
        for attempt in range(3):
            try:
                sb = WebDriverWait(driver, 12).until(EC.element_to_be_clickable((By.XPATH,"//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
                sb.clear(); sb.send_keys(variant); _time.sleep(1.0)
                WebDriverWait(driver,10).until(EC.visibility_of_element_located((By.ID,"ContentBubbleResultsContainer"))); _time.sleep(0.4)
                candidates=driver.find_elements(By.CSS_SELECTOR,"#ContentBubbleResultsContainer > div")
                for rdiv in candidates:
                    try:
                        txt=norm(rdiv.text)
                        if all(tok in txt for tok in toks):
                            try: rdiv.click()
                            except Exception: driver.execute_script("arguments[0].click();", rdiv)
                            _time.sleep(0.9)
                            if ensure_patient_info_loaded(wait, driver): return True
                    except StaleElementReferenceException: continue
                if candidates:
                    try: candidates[0].click()
                    except Exception: driver.execute_script("arguments[0].click();", candidates[0])
                    _time.sleep(0.9)
                    if ensure_patient_info_loaded(wait, driver): return True
            except (TimeoutException, StaleElementReferenceException):
                _time.sleep(0.9)
                try:
                    driver.get("https://www.therapynotes.com/app/patients/list")
                    WebDriverWait(driver,12).until(EC.presence_of_element_located((By.XPATH,"//input[@placeholder='Name, Acct #, Phone, or Ins ID']")))
                except Exception: pass
    log("[TN][ERR] Patient search failed after retries."); return False

def open_documents_tab(wait, driver) -> bool:
    targets = [
        (By.XPATH,"//a[@data-tab-id='Documents' and contains(@href,'#tab=Documents')]"),
        (By.CSS_SELECTOR,"a[data-tab-id='Documents']"),
        (By.XPATH,"//a[normalize-space(text())='Documents']"),
    ]
    for loc in targets:
        if safe_click(wait, driver, loc):
            try:
                WebDriverWait(driver, 12).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//h2[contains(., 'Documents')]")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".documentNameSpan"))
                    )
                ); time.sleep(0.3); return True
            except Exception:
                pass
    return False

def click_upload_button(wait, driver) -> bool:
    xpaths = [
        "//button[.//span[contains(@class,'upload')] and contains(normalize-space(.), 'Upload Patient File')]",
        "//button[contains(normalize-space(.), 'Upload Patient File')]",
        "//button[contains(., 'Upload')]",
    ]
    for xp in xpaths:
        if safe_click(wait, driver, (By.XPATH, xp)): time.sleep(0.5); return True
    return False

def upload_pdf(wait, driver, pdf_path: str, log) -> Tuple[bool,str]:
    base_no_ext = os.path.splitext(os.path.basename(pdf_path))[0]
    if not open_documents_tab(wait, driver): return False, "[ERR] Documents tab not available."
    if not click_upload_button(wait, driver): return False, "[ERR] Could not open Upload dialog."
    try:
        name_in = WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CSS_SELECTOR,"#PatientFile__DocumentName")))
        try: name_in.clear()
        except Exception: pass
        name_in.send_keys(base_no_ext)
        # Blur by clicking header
        try:
            hdr = WebDriverWait(driver,6).until(EC.element_to_be_clickable((By.XPATH,"//h2[normalize-space()='Upload a Patient File']")))
            try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", hdr)
            except Exception: pass
            try: hdr.click()
            except Exception: driver.execute_script("arguments[0].click();", hdr)
            time.sleep(0.2)
        except Exception: pass
    except Exception: pass
    # Choose file
    try:
        file_in = WebDriverWait(driver,12).until(EC.presence_of_element_located((By.CSS_SELECTOR,"#InputUploader")))
        file_in.send_keys(os.path.abspath(pdf_path))
    except Exception: return False, "[ERR] Could not set file in uploader."
    # Wait Add Document to be clickable
    try:
        WebDriverWait(driver,10).until(EC.any_of(
            EC.element_to_be_clickable((By.XPATH,"//input[@type='button' and @value='Add Document' and not(@disabled)]")),
            EC.element_to_be_clickable((By.XPATH,"//button[normalize-space()='Add Document' and not(@disabled)]"))
        ))
    except Exception: pass
    # Click Add
    for how, what in [
        (By.XPATH,"//input[@type='button' and @value='Add Document' and not(@disabled)]"),
        (By.XPATH,"//button[normalize-space()='Add Document' and not(@disabled)]"),
    ]:
        try:
            btn = driver.find_element(how, what)
            try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            except Exception: pass
            try: btn.click()
            except Exception: driver.execute_script("arguments[0].click();", btn)
            break
        except Exception: continue
    # Confirm
    for _ in range(18):
        try:
            rows = driver.find_elements(By.CSS_SELECTOR,".documentNameSpan")
            if any((base_no_ext.lower() in (r.text or '').lower()) for r in rows): return True, "Uploaded"
        except Exception: pass
        time.sleep(0.4)
    return True, "Submitted (verification not found)"

# ------------- Overlay fill + flatten (multiline groups) -------------
def overlay_fill_flatten(template_path: str, out_path: str, text_at_keys: dict, log) -> bool:
    try:
        from PyPDF2 import PdfReader, PdfWriter
        from PyPDF2.generic import NameObject, NullObject
        from reportlab.pdfgen import canvas as rl_canvas
    except Exception as e:
        log(f"[PDF][overlay] missing: {e}")
        return False
    if not os.path.isfile(template_path): log("[PDF][overlay] template missing"); return False
    try:
        with open(template_path, "rb") as f:
            tpl_bytes = f.read()
        reader = PdfReader(io.BytesIO(tpl_bytes))
        if len(reader.pages) == 0: log("[PDF][overlay] empty template"); return False
        page0 = reader.pages[0]
        media = page0.mediabox
        pw, ph = float(media.width), float(media.height)

        # Collect widget rects (if any)
        annots = page0.get("/Annots")
        try:
            if annots is not None and hasattr(annots, "get_object"):
                annots = annots.get_object()
        except Exception: pass
        widgets = []
        if annots:
            seq = annots if isinstance(annots, (list, tuple)) else [annots]
            for a in seq:
                try:
                    obj = a.get_object() if hasattr(a, "get_object") else a
                    if not isinstance(obj, dict): continue
                    if obj.get("/Subtype") != "/Widget": continue
                    rect = obj.get("/Rect")
                    if not rect or len(rect)!=4: continue
                    x0, y0, x1, y1 = [float(v) for v in rect]
                    fname = obj.get("/T")
                    if hasattr(fname, "get_object"): fname = fname.get_object()
                    if not isinstance(fname, str): fname = ""
                    widgets.append({"name": (fname or "").lower(), "rect": (x0,y0,x1,y1)})
                except Exception: continue

        def find_rect(match_list):
            if not match_list: return None
            m = [m.lower() for m in match_list]
            cands = [w for w in widgets if any(mm in w["name"] for mm in m)]
            if cands:
                return sorted(cands, key=lambda w: (-w["rect"][3], -(w["rect"][2]-w["rect"][0])))[0]["rect"]
            return None

        # Build overlay
        fd, overlay_path = tempfile.mkstemp(suffix=".pdf"); os.close(fd)
        c = rl_canvas.Canvas(overlay_path, pagesize=(pw, ph))

        # Resolve rects and group
        order = ["date","name","addr1","addr2","addr3","addr4","init"]
        resolved = []
        for key in order:
            if key not in text_at_keys: continue
            spec = text_at_keys[key]; txt = spec.get("text","")
            rect = find_rect(spec.get("match", []))
            resolved.append((key, txt, rect))

        from collections import OrderedDict
        groups = OrderedDict()
        for key, txt, rect in resolved:
            groups.setdefault(rect, []).append((key, txt))

        # Draw
        fallback_x, fallback_y = 72, ph - 150
        line_h = 14
        for rect, items in groups.items():
            items = [(k,(t or "").strip()) for (k,t) in items if (t or "").strip()!=""]
            if not items: continue
            if rect is None:
                y = fallback_y
                for k, t in items:
                    fs = 12 if not k.startswith("addr") else 11
                    c.setFont("Helvetica", fs)
                    c.drawString(fallback_x, y, t)
                    y -= line_h
                fallback_y = y - 8
            else:
                x0, y0, x1, y1 = rect
                fs_name = 12; fs_addr = 11
                if len(items) == 1 and not items[0][0].startswith("addr"):
                    fs = fs_name
                    baseline = (y0+y1)/2.0 - fs*0.35
                    c.setFont("Helvetica", fs)
                    c.drawString(x0+4, baseline, items[0][1])
                else:
                    cursor = y1 - 2 - fs_name
                    for k, t in items:
                        fs = fs_addr if k.startswith("addr") else fs_name
                        c.setFont("Helvetica", fs)
                        c.drawString(x0+4, cursor, t)
                        cursor -= line_h

        c.showPage(); c.save()

        with open(overlay_path,"rb") as g:
            ov_bytes = g.read()
        over = PdfReader(io.BytesIO(ov_bytes))
        ovp = over.pages[0]
        page0.merge_page(ovp)

        writer = PdfWriter()
        for i, pg in enumerate(reader.pages):
            try:
                if "/Annots" in pg: pg[NameObject("/Annots")] = NullObject()
            except Exception: pass
            writer.add_page(pg)
        try:
            writer._root_object.update({NameObject("/AcroForm"): NullObject()})
        except Exception: pass
        with open(out_path, "wb") as h:
            writer.write(h)

        try: os.remove(overlay_path)
        except Exception: pass
        return True
    except Exception as e:
        log(f"[PDF][overlay] error: {e}")
        return False

# ------------- Excel logging -------------
def save_excel_report(rows: List[Tuple[str,str,str,str,str]], out_dir: str) -> str:
    try:
        import pandas as pd
    except Exception as e:
        raise RuntimeError("Install pandas + openpyxl") from e
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(out_dir, f"IPS_NewBot_MinChange_FIX5_Log_{ts}.xlsx")
    pd.DataFrame(rows, columns=["Client Name","Date Used","Client Folder","Uploaded","Notes"]).to_excel(out, index=False)
    return out

# ------------- Worker -------------
def run_worker(username: str, password: str, csv_path: str, line_from: int, line_to: int, ui_log: UILog,
               stop_event: threading.Event, report_dir: str, out_root: str,
               packet_template: str, letter_template: Optional[str], initials: str,
               full_col: Optional[str], first_col: Optional[str], last_col: Optional[str],
               therapist_col: Optional[str]):
    write = ui_log.write; rows_log: List[Tuple[str,str,str,str,str]] = []
    try:
        webdriver, _By, _WebDriverWait, _EC, Service, ChromeDriverManager = _lazy_import_selenium()
    except Exception as e:
        messagebox.showerror("Missing dependency", str(e)); return
    global By, WebDriverWait, EC; By, WebDriverWait, EC = _By, _WebDriverWait, _EC

    # CSV
    df = load_csv_slice(csv_path, line_from, line_to, write)
    if df is None: write("[CSV] Aborted."); return
    if df.empty: write("[CSV] No rows in selected range."); return
    # Columns
    if not therapist_col: therapist_col = find_column(df, ["Therapist Name","Therapist","TherapistName"])
    if not full_col: full_col = find_column(df, ["Client Name","Full Name","Name"])
    if not first_col: first_col = find_column(df, ["First Name","First"])
    if not last_col:  last_col  = find_column(df, ["Last Name","Last"])
    write(f"[CSV] Using columns → Therapist: {therapist_col or 'N/A'}, Full: {full_col or 'N/A'}, First: {first_col or 'N/A'}, Last: {last_col or 'N/A'}")
    # Filter
    if therapist_col and therapist_col in df.columns:
        mask = df[therapist_col].astype(str).str.contains("IPS", case=False, na=False); df = df[mask]
        write(f"[CSV] Filtered to {len(df)} row(s) with Therapist containing 'IPS'.")
    else:
        write("[CSV][WARN] Therapist column not found; skipping IPS filter.")
    if df.empty: write("[CSV] Nothing to process after filtering."); return

    # Chrome
    try:
        options = webdriver.ChromeOptions(); options.add_argument("--start-maximized")
        service = Service(ChromeDriverManager().install()); driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 14)
    except Exception as e:
        messagebox.showerror("Chrome error", f"Could not start Chrome: {e}"); return

    today = datetime.now().strftime("%m/%d/%Y")

    try:
        if stop_event.is_set(): write("[STOP] Cancelled before login."); return
        if not tn_login(driver, wait, username, password, write): return

        for _, row in df.iterrows():
            if stop_event.is_set(): write("[STOP] Requested. Ending early."); break
            client = full_name_from_row(row, first_col, last_col, full_col)
            if not client:
                rows_log.append(("", today, "", "0/1", "Missing client name in CSV")); continue
            write(f"[RUN] Client: {client}")

            # Patients → search
            if not go_patients(wait, driver):
                rows_log.append((client, today, "", "0/1", "Could not open Patients")); continue
            if not search_and_open_patient(wait, driver, client, write):
                rows_log.append((client, today, "", "0/1", "Patient not found")); continue

            # Extract address
            addr_lines_raw = extract_address(wait, driver)
            # Construct the 4 lines with Client Name first
            letter_lines = format_letter_lines(client, addr_lines_raw)
            # Ensure names for later use
            line1_name, line2_street_unit, line3_cityst, line4_countryzip = (letter_lines + ["","","",""])[:4]

            # Per-client folder
            safe_client = sanitize_filename(client) or "UnknownClient"
            out_dir = os.path.join(out_root or desktop_dir(), safe_client); os.makedirs(out_dir, exist_ok=True)

            # --- Build Packet PDF (flattened) ---
            packet_out = os.path.join(out_dir, f"{safe_client} Welcome Packet Letter.pdf")
            text_map_packet = {
                "date": {"match": ["date","letter","dt"], "text": today},
                "name": {"match": ["client","name"], "text": client},
                "init": {"match": ["initial"], "text": initials},
            }
            ok_packet = overlay_fill_flatten(packet_template, packet_out, text_map_packet, write)
            if not ok_packet:
                rows_log.append((client, today, out_dir, "0/1", "Packet PDF build error")); continue
            write(f"[PDF] Packet (flattened) → {packet_out}")

            # --- Upload Packet ---
            uploaded = 0; notes=[]
            ok1, msg1 = upload_pdf(wait, driver, packet_out, write)
            if ok1: uploaded += 1
            notes.append(f"Packet: {msg1}")

            # --- Build Welcome Letter PDF (flattened) — ALWAYS create, DO NOT upload ---
            if letter_template and os.path.isfile(letter_template):
                letter_out = os.path.join(out_dir, f"{safe_client} Welcome Letter.pdf")
                text_map_letter = {
                    "name":  {"match": ["client","name"], "text": line1_name},
                    "addr1": {"match": ["address","addr","line1"], "text": line2_street_unit},
                    "addr2": {"match": ["address","addr","line2","city"], "text": line3_cityst},
                    "addr3": {"match": ["address","addr","line3","zip","country"], "text": line4_countryzip},
                    # No initials on letter
                }
                if overlay_fill_flatten(letter_template, letter_out, text_map_letter, write):
                    write(f"[PDF] Letter (flattened) → {letter_out}")
                    notes.append("Letter: created (not uploaded)")
                else:
                    notes.append("Letter: build error")
            else:
                notes.append("Letter: template not provided")

            rows_log.append((client, today, out_dir, f"{uploaded}/1", "; ".join(notes)))
        write("[DONE] Completed.")
    finally:
        try: driver.quit()
        except Exception: pass

    # Excel
    try:
        out_dir_final = report_dir or desktop_dir(); os.makedirs(out_dir_final, exist_ok=True)
        out_path = save_excel_report(rows_log, out_dir_final); write(f"[REPORT] Excel saved → {out_path}")
    except Exception as e:
        write(f"[REPORT][ERR] Could not write Excel: {e}")

# ------------- GUI -------------
class App:
    def __init__(self, root):
        self.root=root; root.title(f"{APP_TITLE} - Version 2.1.0, Last Updated 12/03/2025"); root.geometry("1120x880")
        style=ttk.Style()
        try: style.theme_use('clam')
        except Exception: pass
        style.configure('TLabel', background=MAROON, foreground='#fff', font=("Helvetica",11))
        style.configure('Header.TLabel', font=("Helvetica",20,'bold'))
        style.configure('Card.TFrame', background=CARD_BG)
        style.configure('TButton', font=("Helvetica",11,'bold'))

        # Vars
        self.username=tk.StringVar(); self.password=tk.StringVar()
        self.csv_path=tk.StringVar(value="")
        self.line_from=tk.IntVar(value=2); self.line_to=tk.IntVar(value=200)
        self.out_dir=tk.StringVar(value=""); self.report_dir=tk.StringVar(value="")
        self.packet_template=tk.StringVar(value=""); self.letter_template=tk.StringVar(value="")
        self.initials=tk.StringVar(value="IR")
        self.full_col=tk.StringVar(value=""); self.first_col=tk.StringVar(value="First Name"); self.last_col=tk.StringVar(value="Last Name")
        self.therapist_col=tk.StringVar(value="Therapist Name")

        self.stop_event=threading.Event(); self.worker_thread=None

        header=ttk.Label(root, text=APP_TITLE, style="Header.TLabel"); header.pack(pady=(12,6), fill='x')
        def card(p): f=ttk.Frame(p, style='Card.TFrame'); f.configure(padding=(14,12)); return f

        creds=card(root); creds.pack(fill='x', padx=12, pady=(6,6))
        ttk.Label(creds, text="TN Username:", background=CARD_BG, foreground="#000").grid(row=0, column=0, sticky='e', padx=(0,8))
        ttk.Entry(creds, textvariable=self.username, width=32).grid(row=0, column=1, sticky='w')
        ttk.Label(creds, text="TN Password:", background=CARD_BG, foreground="#000").grid(row=1, column=0, sticky='e', padx=(0,8))
        ttk.Entry(creds, textvariable=self.password, show='*', width=32).grid(row=1, column=1, sticky='w')

        csvc=card(root); csvc.pack(fill='x', padx=12, pady=(6,6))
        ttk.Label(csvc, text="Input CSV:", background=CARD_BG, foreground="#000").grid(row=0, column=0, sticky='e', padx=(0,8))
        ttk.Entry(csvc, textvariable=self.csv_path, width=68).grid(row=0, column=1, sticky='w')
        ttk.Button(csvc, text="Browse…", command=self.pick_csv).grid(row=0, column=2, sticky='w', padx=6)
        ttk.Label(csvc, text="Line range (inclusive): From", background=CARD_BG, foreground="#000").grid(row=1, column=0, sticky='e', padx=(0,8), pady=(8,0))
        ttk.Entry(csvc, textvariable=self.line_from, width=8).grid(row=1, column=1, sticky='w', pady=(8,0))
        ttk.Label(csvc, text="to", background=CARD_BG, foreground="#000").grid(row=1, column=1, sticky='w', padx=(64,0), pady=(8,0))
        ttk.Entry(csvc, textvariable=self.line_to, width=8).grid(row=1, column=1, sticky='w', padx=(92,0), pady=(8,0))

        tmps=card(root); tmps.pack(fill='x', padx=12, pady=(6,6))
        ttk.Label(tmps, text="Packet template (PDF):", background=CARD_BG, foreground="#000").grid(row=0, column=0, sticky='e')
        ttk.Entry(tmps, textvariable=self.packet_template, width=60).grid(row=0, column=1, sticky='w', padx=6)
        ttk.Button(tmps, text="Browse…", command=self.pick_packet_template).grid(row=0, column=2, sticky='w', padx=6)
        ttk.Label(tmps, text="Welcome Letter template (PDF):", background=CARD_BG, foreground="#000").grid(row=1, column=0, sticky='e', pady=(8,0))
        ttk.Entry(tmps, textvariable=self.letter_template, width=60).grid(row=1, column=1, sticky='w', padx=6, pady=(8,0))
        ttk.Button(tmps, text="Browse…", command=self.pick_letter_template).grid(row=1, column=2, sticky='w', padx=6, pady=(8,0))
        ttk.Label(tmps, text="Employee Initials (used for Packet only):", background=CARD_BG, foreground="#000").grid(row=0, column=3, sticky='e')
        ttk.Entry(tmps, textvariable=self.initials, width=10).grid(row=0, column=4, sticky='w', padx=4)

        outs=card(root); outs.pack(fill='x', padx=12, pady=(6,6))
        ttk.Label(outs, text="PDF output root:", background=CARD_BG, foreground="#000").grid(row=0, column=0, sticky='e')
        ttk.Entry(outs, textvariable=self.out_dir, width=60).grid(row=0, column=1, sticky='w', padx=6)
        ttk.Button(outs, text="Browse…", command=self.pick_out_dir).grid(row=0, column=2, sticky='w', padx=6)
        ttk.Label(outs, text="Excel report folder:", background=CARD_BG, foreground="#000").grid(row=1, column=0, sticky='e', pady=(8,0))
        ttk.Entry(outs, textvariable=self.report_dir, width=60).grid(row=1, column=1, sticky='w', padx=6, pady=(8,0))
        ttk.Button(outs, text="Browse…", command=self.pick_report_dir).grid(row=1, column=2, sticky='w', padx=6, pady=(8,0))

        ctrl=card(root); ctrl.pack(fill='x', padx=12, pady=(6,6))
        self.start_btn=ttk.Button(ctrl, text="Start", command=self.start_run, width=16)
        self.stop_btn=ttk.Button(ctrl, text="Stop", command=self.stop_run, width=16)
        self.start_btn.grid(row=0, column=0, padx=(16,8))
        self.stop_btn.grid(row=0, column=1)
        ttk.Label(ctrl, text="Status:", background=CARD_BG, foreground="#000").grid(row=0, column=2, padx=(16,6))
        self.status_lbl=ttk.Label(ctrl, text="Idle", background=CARD_BG, foreground="#000"); self.status_lbl.grid(row=0, column=3, sticky='w')

        logc=card(root); logc.pack(fill='both', expand=True, padx=12, pady=(6,12))
        self.log=scrolledtext.ScrolledText(logc, width=120, height=28, bg=LOG_BG, fg=LOG_FG, font=("Consolas",10)); self.log.pack(fill='both', expand=True)
        self.uilog=UILog(self.log)

    # Pickers
    def pick_csv(self):
        p=filedialog.askopenfilename(filetypes=[("CSV files","*.csv")])
        if p: self.csv_path.set(p)
    def pick_packet_template(self):
        p=filedialog.askopenfilename(filetypes=[("PDF files","*.pdf")])
        if p: self.packet_template.set(p)
    def pick_letter_template(self):
        p=filedialog.askopenfilename(filetypes=[("PDF files","*.pdf")])
        if p: self.letter_template.set(p)
    def pick_out_dir(self):
        d=filedialog.askdirectory()
        if d: self.out_dir.set(d)
    def pick_report_dir(self):
        d=filedialog.askdirectory()
        if d: self.report_dir.set(d)

    # Start/Stop
    def start_run(self):
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("Busy","A run is already in progress."); return
        if not self.username.get().strip() or not self.password.get().strip():
            messagebox.showwarning("Missing login","Enter your TherapyNotes username and password."); return
        if not self.csv_path.get().strip():
            messagebox.showwarning("Missing CSV","Choose the input CSV first."); return
        if not os.path.isfile(self.packet_template.get().strip()):
            messagebox.showwarning("Missing template","Select the IPS Welcome Packet LETTER (template PDF)."); return
        if not os.path.isfile(self.letter_template.get().strip()):
            messagebox.showwarning("Missing template","Select the IPS Welcome Letter (template PDF)."); return
        self.stop_event=threading.Event(); self.status_lbl.configure(text="Running…"); self.uilog.write("[RUN] Started.")
        args=(self.username.get().strip(), self.password.get().strip(), self.csv_path.get().strip(),
              int(self.line_from.get()), int(self.line_to.get()), self.uilog, self.stop_event,
              self.report_dir.get().strip(), self.out_dir.get().strip(),
              self.packet_template.get().strip(), self.letter_template.get().strip(),
              self.initials.get().strip() or "IR",
              None, "First Name", "Last Name", "Therapist Name")
        self.worker_thread=threading.Thread(target=run_worker, args=args, daemon=True); self.worker_thread.start()
        self.root.after(600, self._poll_done)
    def _poll_done(self):
        if self.worker_thread and self.worker_thread.is_alive(): self.root.after(600, self._poll_done)
        else: self.status_lbl.configure(text="Idle"); self.uilog.write("[RUN] Finished.")
    def stop_run(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.stop_event.set(); self.uilog.write("[STOP] Requested. The bot will finish the current step and exit.")
        else:
            self.uilog.write("[STOP] No active run.")

if __name__ == "__main__":
    try:
        root=tk.Tk(); app=App(root); root.mainloop()
    except Exception as e:
        print("[FATAL] GUI failed to start:", e)
