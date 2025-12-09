# integrity_medical_records_extender_WAITREADY_ROI_INTAKEFALLBACK_TwinPeakin_FIX7.py
# Minimal, surgical changes over FIX5:
#   • Ensure-Intake trigger no longer misfires from text inside other PDFs.
#     (checks filenames only, not PDF text, so Progress batches mentioning "intake" won't suppress fallback)
#   • Intake fallback paginates using base.try_click_older_or_next (Older/Next) instead of numeric-only paginator.
#   • Single-file wait bumped to 60s for slower tenants.
#
# Everything else left as-is.

import os, sys, re, glob, time, traceback, importlib.util, datetime

# ---------------- UX helpers ----------------

def _popup(title, msg, kind="info"):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk(); root.withdraw()
        (messagebox.showerror if kind=="error" else messagebox.showinfo)(title, msg)
        try: root.destroy()
        except Exception: pass
        return
    except Exception:
        pass
    try:
        import ctypes
        MB_ICON = 0x10 if kind == "error" else 0x40
        ctypes.windll.user32.MessageBoxW(None, str(msg), str(title), MB_ICON | 0)
        return
    except Exception:
        pass
    try:
        print(f"[{kind.upper()}] {title}: {msg}")
    except Exception:
        pass

def _block_exit():
    try:
        if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            input("Press Enter to close…")
        else:
            time.sleep(6)
    except Exception:
        time.sleep(6)

# ---------------- Base finder ----------------

def _find_base_py():
    here = os.path.abspath(os.path.dirname(__file__))
    self_name = os.path.basename(__file__)
    picks = []
    def add_matches(prefix):
        for name in os.listdir(here):
            if not name.endswith(".py"): continue
            if name == os.path.basename(self_name): continue
            if name.lower().startswith(prefix): picks.append(os.path.join(here, name))
    add_matches("integrity_medical_records_bot")
    add_matches("integrity_medical_records_adminpdfs_and_combine")
    add_matches("integrity_consent_bot")
    for name in os.listdir(here):
        if not name.endswith(".py"): continue
        if name == os.path.basename(self_name): continue
        low = name.lower()
        if all(k in low for k in ("integrity","medical","records")):
            p = os.path.join(here, name)
            if p not in picks: picks.append(p)
    if picks:
        picks.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return picks[0]
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        sel = filedialog.askopenfilename(title="Select your working Medical Records Bot (.py)", filetypes=[("Python files","*.py")], initialdir=here)
        try: root.destroy()
        except Exception: pass
        return sel or None
    except Exception:
        return None

def _import_base(path):
    spec = importlib.util.spec_from_file_location("base_bot", path)
    if spec is None or spec.loader is None: return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

# ---------------- FS helpers ----------------

def _snapshot(dirpath):
    snap = {}
    for p in glob.glob(os.path.join(dirpath, "*")):
        if p.endswith(".crdownload"): continue
        try: snap[p] = (os.path.getsize(p), os.path.getmtime(p))
        except Exception: snap[p] = (-1, 0)
    return snap

def _wait_new_or_updated(dirpath, before_snap, timeout=12):
    end = time.time() + timeout
    while time.time() < end:
        now = _snapshot(dirpath)
        new = [p for p in now if p not in before_snap and p.lower().endswith(".pdf")]
        if new: return True, set(new)
        upd = []
        for p,(sz,mt) in now.items():
            b = before_snap.get(p)
            if b and (mt > b[1] + 0.05) and p.lower().endswith(".pdf"): upd.append(p)
        if upd: return True, set(upd)
        time.sleep(0.2)
    return False, set()

def _quiet_settle(dirpath, quiet_secs=1.5, budget_s=1800):
    t0 = time.time(); last = _snapshot(dirpath); last_change = time.time()
    while time.time() - t0 < budget_s:
        crs = glob.glob(os.path.join(dirpath, "*.crdownload"))
        now = _snapshot(dirpath)
        if crs or now != last:
            last = now; last_change = time.time()
        else:
            if time.time() - last_change >= quiet_secs: return True
        time.sleep(0.25)
    return False

# ---------------- Classification + renaming ----------------

BUCKET_META = {
    "intake":   ("01", "Intake Note"),
    "consent":  ("02", "Consent and NPP"),
    "roi":      ("03", "Release of Information"),
    "sra":      ("04", "Suicide Risk Assessment"),
    "safety":   ("05", "Safety Plan"),
    "erf":      ("06", "Emergency Response Form"),
    "tp_contact":("07", "Treatment Plans & Contact Notes"),
    "consult":  ("08", "Consultation Notes"),
    "progress": ("09", "Progress Notes"),
    "other":    ("10", "Other"),
}
ONE_EACH = {"consent","roi","sra","safety","erf"}

KEY = {
    "exclude":[r"columbia[-\s]?suicide severity rating"],
    "intake":  [r"\bpsychotherapy intake note\b", r"\bintake note\b", r"\bintake\b", r"initial (assessment|evaluation)", r"\bclinical intake\b" ],
    "consent":[r"\bconsent\b", r"\bnpp\b", r"notice of privacy", r"hipaa"],
    # ROI supports acronym + full authorization phrase (any punctuation/UPDATED suffix)
    "roi":[r"authorization[-_\s]*for[-_\s]*release[-_\s]*of[-_\s]*health[-_\s]*information(?:[-_\s]*updated)?\b", r"\brelease of information\b", r"\broi\b"],
    "sra":[r"suicide[ -]*risk[ -]*(assessment|screen|screening|eval|evaluation|form)", r"\bSRA\b"],
    # Safety with typo tolerance baked-in
    "safety":[r"saf(?:ety|tey)[-_ ]?plan\b", r"saf(?:ety|tey)[-_ ]?form\b", r"crisis plan"],
    "erf":[r"emergency response", r"\berf\b"],
    "tp_contact":[r"treatment plan", r"\bpcp\b.{0,40}contact.{0,10}note", r"contact.{0,10}note.{0,40}\bpcp\b"],
    "consult":[r"consultation note", r"\bconsult note\b", r"\bconsultation\b"],
    "progress":[r"progress note", r"session note"],
}

_DEFUZZ = ["safety plan","treatment plan","progress note","contact note","intake note","release of information"]

try:
    from pypdf import PdfReader
except Exception:
    try: from PyPDF2 import PdfReader
    except Exception: PdfReader = None

def _pdf_text(path, max_pages=6):
    if not PdfReader: return ""
    try:
        r = PdfReader(path); chunks=[]
        for i in range(min(len(r.pages), max_pages)):
            try: chunks.append(r.pages[i].extract_text() or "")
            except Exception: break
        return "\n".join(chunks).lower()
    except Exception:
        return ""

def _lev(a,b,cap=1):
    if abs(len(a)-len(b))>cap: return cap+1
    a=a.lower(); b=b.lower(); m=len(a); n=len(b)
    dp=[[j if i==0 else i if j==0 else 0 for j in range(n+1)] for i in range(m+1)]
    for i in range(1,m+1):
        for j in range(1,n+1):
            cost = 0 if a[i-1]==b[j-1] else 1
            dp[i][j]=min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)
            if i>1 and j>1 and a[i-1]==b[j-2] and a[i-2]==b[j-1]:
                dp[i][j]=min(dp[i][j], dp[i-2][j-2]+1)
    return dp[m][n]

def _fuzzy_contains(hay, term, max_d=1):
    hay = re.sub(r"[^a-z0-9 ]+"," ", (hay or "").lower())
    term = re.sub(r"[^a-z0-9 ]+"," ", term.lower()).strip()
    hw = hay.split(); tw = term.split()
    if not tw: return False
    n=len(tw)
    for i in range(0, len(hw)-n+1):
        win = " ".join(hw[i:i+n])
        if _lev(win, term, cap=max_d) <= max_d: return True
    return False

def _hit(pats, hay):
    import re as _re
    for pat in pats:
        if _re.search(pat, hay, flags=_re.IGNORECASE): return True
    for t in _DEFUZZ:
        if _fuzzy_contains(hay, t, max_d=1): return True
    return False

def _bucket_of(path):
    base = os.path.basename(path).lower()
    base_spaced = base.replace("-", " ")
    text = _pdf_text(path, max_pages=6)
    hay = f"{base}\n{base_spaced}\n{text}"
    for k in ["intake","progress","tp_contact","consult","consent","roi","safety","erf"]:
        if _hit(KEY[k], hay): return k
    if _hit(KEY["sra"], hay): return "sra"
    if _hit(KEY["exclude"], hay): return "other"
    return "other"

def _safe_rename(src, dst_base):
    folder = os.path.dirname(src)
    name = dst_base + ".pdf"
    cand = os.path.join(folder, name)
    i = 2
    while os.path.exists(cand):
        cand = os.path.join(folder, f"{dst_base} ({i}).pdf"); i += 1
    try:
        os.replace(src, cand)
        return cand
    except Exception:
        return src

def _rename_new_pdfs_by_bucket(new_files, counters, forced_bucket=None):
    renamed = set()
    for p in sorted(new_files):
        if not p.lower().endswith('.pdf'): continue
        b = (forced_bucket or _bucket_of(p))
        prefix, label = BUCKET_META.get(b, BUCKET_META['other'])
        counters[b] = counters.get(b, 0) + 1
        suffix = f" (Batch {counters[b]})" if b in {"progress","tp_contact","consult"} else ""
        newname = f"{prefix}-{label}{suffix}"
        newp = _safe_rename(p, newname)
        renamed.add(newp)
    return renamed

# ---------------- Selenium helpers (READY + gating) ----------------

def _install_batch_helpers(base):
    from selenium.webdriver.common.by import By

    READY_XPATH = "//div[@data-testid='completed-message-ready-to-download' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'click to download')]"

    def _wait_ready(driver, timeout_s):
        end = time.time() + timeout_s
        while time.time() < end:
            try:
                els = driver.find_elements(By.XPATH, READY_XPATH)
            except Exception:
                els = []
            if els:
                return els[0]
            time.sleep(0.25)
        return None

    def _watch_and_refresh_if_stalled(driver, download_dir, budget_s=3600, stagnation_s=25):
        t0 = time.time(); last_bytes = {}; last_change = time.time(); refreshed=False
        while time.time()-t0 < budget_s:
            crs = glob.glob(os.path.join(download_dir, "*.crdownload"))
            if not crs: return True
            moved=False
            for p in crs:
                try: sz=os.path.getsize(p)
                except Exception: sz=-1
                last=last_bytes.get(p)
                last_bytes[p]=sz
                if last is None or sz!=last: moved=True
            if moved: last_change=time.time()
            elif (time.time()-last_change)>=stagnation_s and not refreshed:
                try: driver.refresh(); refreshed=True
                except Exception: pass
                time.sleep(1.5)
            time.sleep(1.0)
        return False

    def _gate_until_download_and_rename(driver, download_dir, before, forced_bucket=None, is_progress=False, label="batch"):
        max_budget = 3600 if is_progress else 900
        ok = base.wait_for_downloads(download_dir, timeout=max_budget)
        if not ok:
            base.log("        ↳ Stalled; watchdog + soft refresh…")
            _watch_and_refresh_if_stalled(driver, download_dir, budget_s=max_budget, stagnation_s=25)
            base.wait_for_downloads(download_dir, timeout=600)
        _quiet_settle(download_dir, quiet_secs=1.5, budget_s=900)
        ok_new, newfiles = _wait_new_or_updated(download_dir, before, timeout=10.0)
        if not ok_new:
            base.log("        ↳ No new PDFs detected after Ready click.")
            return False
        base._rename_counters = getattr(base, "_rename_counters", {})
        renamed = _rename_new_pdfs_by_bucket(newfiles, base._rename_counters, forced_bucket=forced_bucket)
        for rp in sorted(renamed):
            base.log(f"        ↳ Renamed {label} → {os.path.basename(rp)}")
        tend = time.time()+30
        while time.time()<tend:
            if not glob.glob(os.path.join(download_dir, "*.crdownload")):
                break
            time.sleep(0.25)
        return True

    def _batch_download(driver, download_dir, label="selection", kind="generic", **_kw):
        if not base.click_download_selected(driver):
            base.log(f"   - Could not click 'Download Selected Documents' for {label}.")
            base.exit_multi_mode_via_cancel(driver); return False
        is_progress = any(k in str(label).lower() for k in ("progress","pn")) or kind=="progress"
        ready = _wait_ready(driver, timeout_s=1200 if is_progress else 600)
        if not ready:
            base.log("        ↳ No 'Ready: Click to Download' element appeared in time.")
            base.exit_multi_mode_via_cancel(driver); return False
        try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", ready)
        except Exception: pass
        before = _snapshot(download_dir)
        try: ready.click()
        except Exception:
            try: driver.execute_script("arguments[0].click();", ready)
            except Exception: pass
        forced=None; lbl=str(label).lower()
        if ("intake" in lbl) or ("ia" in lbl): forced="intake"
        elif ("progress" in lbl) or ("pn" in lbl) or (kind=="progress"): forced="progress"
        elif any(k in lbl for k in ("tp","treatment","pcp","contact")): forced="tp_contact"
        _gate_until_download_and_rename(driver, download_dir, before, forced_bucket=forced, is_progress=is_progress, label="batch")
        base.exit_multi_mode_via_cancel(driver)
        base.log("        ↳ Done; Cancelled to unblur.")
        return True

    def do_download_selected_and_cancel(driver, download_dir, label="selection", max_wait_secs=None, **kw):
        kind = "progress" if any(k in str(label).lower() for k in ("progress","pn")) else "generic"
        return _batch_download(driver, download_dir, label=label, kind=kind)

    def final_batch_sweep(driver, download_dir, budget_s=120):
        end = time.time() + budget_s
        while time.time() < end:
            el=None
            try: el = driver.find_element(By.XPATH, READY_XPATH)
            except Exception: el=None
            if not el: break
            before = _snapshot(download_dir)
            try: el.click()
            except Exception:
                try: driver.execute_script("arguments[0].click();", el)
                except Exception: break
            _gate_until_download_and_rename(driver, download_dir, before, forced_bucket=None, is_progress=False, label="batch")
            time.sleep(0.2)
        _quiet_settle(download_dir, quiet_secs=1.5, budget_s=300)
        return True

    base.do_download_selected_and_cancel = do_download_selected_and_cancel
    base.final_batch_sweep = final_batch_sweep

# ---------------- Title normalization ----------------

def _norm_title(s: str) -> str:
    s = (s or "").lower().replace("_"," ").replace("-"," ")
    s = re.sub(r"\s+"," ", s).strip()
    s = s.replace("saftey","safety")
    return s

# ---------------- Admin PDFs stage (unchanged) ----------------

def _install_admin_pdfs_stage(base):
    from selenium.webdriver.common.by import By
    ADMIN_KEYS = ["consent","roi","sra","safety","erf"]
    ROI_FULL_RE = re.compile(r"\bauthorization[-_\s]*for[-_\s]*release[-_\s]*of[-_\s]*health[-_\s]*information(?:[-_\s]*updated)?\b", re.I)

    def admin_pdfs_stage(driver, download_dir, max_pages=10):
        base.exit_multi_mode_via_cancel(driver)
        got=set(); page=1
        while page <= max_pages and len(got) < len(ADMIN_KEYS):
            rows = driver.find_elements(By.XPATH, "//tr[contains(@class,'Row') or contains(@class,'AlternateRow')]")
            for tr in rows:
                try:
                    title = _norm_title(tr.find_element(By.XPATH, ".//span[contains(@class,'documentNameSpan')]").text)
                except Exception:
                    title = _norm_title(getattr(tr, 'text', '') or '')
                row_text = title
                want=None
                if ("release of information" in row_text) or ROI_FULL_RE.search(row_text) or re.search(r"\broi\b", row_text):
                    want="roi"
                if not want and ("safety plan" in row_text or re.search(r"\bsaf(?:ety|tey)[-_ ]?(plan|form)\b", row_text) or "crisis plan" in row_text):
                    want="safety"
                if not want and ("consent" in row_text or "npp" in row_text or "notice of privacy" in row_text or "hipaa" in row_text):
                    want="consent"
                if not want and ("emergency response" in row_text or re.search(r"\berf\b", row_text)):
                    want="erf"
                if not want and (("suicide risk" in row_text) or re.search(r"\bsra\b", row_text)) and ("columbia suicide severity rating" not in row_text):
                    want="sra"
                if not want or want in got: continue
                try:
                    icon = tr.find_element(By.XPATH, ".//div[contains(@class,'fa-icon') and contains(@class,'download')]")
                except Exception:
                    continue
                try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", icon)
                except Exception: pass
                before = _snapshot(download_dir)
                try: icon.click()
                except Exception:
                    try: driver.execute_script("arguments[0].click();", icon)
                    except Exception: continue
                try:
                    READY_XPATH = "//div[@data-testid='completed-message-ready-to-download' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'click to download')]"
                    els = driver.find_elements(By.XPATH, READY_XPATH)
                except Exception:
                    els = []
                if els:
                    try: els[0].click()
                    except Exception:
                        try: driver.execute_script("arguments[0].click();", els[0])
                        except Exception: pass
                _quiet_settle(download_dir, quiet_secs=1.0, budget_s=300)
                ok,newfiles = _wait_new_or_updated(download_dir, before, timeout=20)
                if ok:
                    pref,label = BUCKET_META.get(want, BUCKET_META["other"])
                    renamed=set()
                    for p in newfiles:
                        if p.lower().endswith(".pdf"):
                            renamed.add(_safe_rename(p, f"{pref}-{label}"))
                    for rp in sorted(renamed):
                        base.log(f"     ✓ Admin PDF downloaded: {want} → {os.path.basename(rp)}")
                    got.add(want)
            # numeric paginator (kept for admin docs)
            try:
                next_links = driver.find_elements(By.XPATH, "//a[@class='SpecificPage' and @id='DynamicTablePagingLink']")
                labels = [(a, a.text.strip()) for a in next_links if a.text.strip().isdigit()]
                nxt=None
                for a,label in labels:
                    try:
                        if int(label) == page+1: nxt=a; break
                    except Exception: continue
                if nxt:
                    try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", nxt)
                    except Exception: pass
                    try: nxt.click()
                    except Exception: driver.execute_script("arguments[0].click();", nxt)
                    time.sleep(0.5); page += 1
                else:
                    break
            except Exception:
                break
        return got

    base.admin_pdfs_stage = admin_pdfs_stage

# ---------------- Intake fallback (uses Older/Next & longer single-file wait) ----------------

def _install_intake_fallback(base):
    from selenium.webdriver.common.by import By

    READY_XPATH = "//div[@data-testid='completed-message-ready-to-download' and contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'click to download')]"

    def ensure_intake_if_missing(driver, download_dir, max_pages=30):
        try: existing = [p for p in glob.glob(os.path.join(download_dir, "*.pdf")) if re.search(r"\bintake\b", os.path.basename(p).lower()) or os.path.basename(p).startswith('01-')]
        except Exception: existing = []
        if existing:
            base.log("     ↳ Intake already present; skipping fallback IA download.")
            return False

        try: base.exit_multi_mode_via_cancel(driver)
        except Exception: pass

        got=False; hops=0
        while hops < max_pages and not got:
            rows = driver.find_elements(By.XPATH, "//tr[contains(@class,'Row') or contains(@class,'AlternateRow')]")
            for tr in rows:
                try:
                    title = _norm_title(tr.find_element(By.XPATH, ".//span[contains(@class,'documentNameSpan')]").text)
                except Exception:
                    title = _norm_title(getattr(tr, 'text', '') or '')
                is_intake = (
                    "psychotherapy intake note" in title or
                    re.search(r"\bintake\s+note\b", title or "") or
                    re.search(r"\bclinical\s+intake\b", title or "") or
                    re.search(r"\binitial\s+(assessment|evaluation)\b", title or "") or
                    re.search(r"\bdiagnostic\s+evaluation\b", title or "")
                )
                if not is_intake: continue

                try:
                    icon = tr.find_element(By.XPATH, ".//div[contains(@class,'fa-icon') and contains(@class,'download')]")
                except Exception:
                    continue
                try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", icon)
                except Exception: pass

                before = _snapshot(download_dir)
                try: icon.click()
                except Exception:
                    try: driver.execute_script("arguments[0].click();", icon)
                    except Exception: continue

                # WAIT for the READY overlay (notes can take a moment to render)
                clicked_ready = False
                end = time.time() + 90
                while time.time() < end and not clicked_ready:
                    try:
                        els = driver.find_elements(By.XPATH, READY_XPATH)
                    except Exception:
                        els = []
                    if els:
                        try:
                            els[0].click(); clicked_ready = True
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", els[0]); clicked_ready = True
                            except Exception:
                                pass
                    if not clicked_ready:
                        time.sleep(0.25)

                # Wait longer for single-file completion
                _quiet_settle(download_dir, quiet_secs=1.0, budget_s=300)
                ok,newfiles = _wait_new_or_updated(download_dir, before, timeout=60)
                if ok:
                    for p in newfiles:
                        if p.lower().endswith('.pdf'):
                            finalp = _safe_rename(p, f"{BUCKET_META['intake'][0]}-{BUCKET_META['intake'][1]}")
                            base.log(f"     ✓ Fallback Intake downloaded → {os.path.basename(finalp)}")
                            got=True
                            break
                if got: break

            if got: break

            # PAGE HOP: prefer base helper for Older/Next; fallback to numeric only if helper missing
            hopped = False
            try:
                if getattr(base, "try_click_older_or_next", None) and base.try_click_older_or_next(driver):
                    hopped = True
            except Exception:
                hopped = False

            if not hopped:
                try:
                    next_links = driver.find_elements(By.XPATH, "//a[@class='SpecificPage' and @id='DynamicTablePagingLink']")
                    labels = [(a, a.text.strip()) for a in next_links if a.text.strip().isdigit()]
                    nxt=None; # naive next
                    for a,label in labels:
                        try:
                            if label and int(label) > 0:
                                nxt=a; break
                        except Exception: continue
                    if nxt:
                        try: driver.execute_script("arguments[0].scrollIntoView({block:'center'});", nxt)
                        except Exception: pass
                        try: nxt.click()
                        except Exception: driver.execute_script("arguments[0].click();", nxt)
                        hopped = True
                except Exception:
                    hopped = False

            if hopped:
                hops += 1
                try: base.scroll_until_stable(driver, max_passes=4, pause=0.10)
                except Exception: pass
                base.log(f"     … paging Older/Next (hop {hops})")
            else:
                break

        if not got:
            base.log("[WARN] No Intake Note found during fallback IA search.")
        return got

    base.ensure_intake_if_missing = ensure_intake_if_missing

# ---------------- Combiner (unchanged) ----------------

def _install_combiner(base):
    try:
        from pypdf import PdfReader, PdfWriter
    except Exception:
        try: from PyPDF2 import PdfReader, PdfWriter
        except Exception:
            PdfReader = PdfWriter = None

    BUCKET_ORDER = {"intake":1, "consent":2, "roi":3, "sra":4, "safety":5, "erf":6, "tp_contact":7, "consult":8, "progress":9, "other":10}

    def _txt(pdf, max_pages=6):
        if not PdfReader: return ""
        try:
            r = PdfReader(pdf); chunks=[]
            for i in range(min(len(r.pages), max_pages)):
                try: chunks.append(r.pages[i].extract_text() or "")
                except Exception: break
            return "\n".join(chunks).lower()
        except Exception:
            return ""

    def _hit_local(pats, hay):
        import re as _re
        for pat in pats:
            if _re.search(pat, hay, flags=_re.IGNORECASE): return True
        for t in _DEFUZZ:
            if _fuzzy_contains(hay, t, max_d=1): return True
        return False

    def _bucket(p):
        base = os.path.basename(p).lower()
        m = re.match(r"^(\d{2})-", base)
        if m:
            idx = int(m.group(1))
            for k,(num,_) in BUCKET_META.items():
                if int(num) == idx: return k
        base_spaced = base.replace("-", " ")
        text = _txt(p, max_pages=4)
        hay = f"{base}\n{base_spaced}\n{text}"
        for k in ["intake","progress","tp_contact","consult","consent","roi","safety","erf"]:
            if _hit_local(KEY[k], hay): return k
        if _hit_local(KEY["sra"], hay): return "sra"
        return "other"

    def _order_key(p):
        bn = os.path.basename(p).lower()
        m = re.match(r"^(\d{2})-", bn)
        if m: return (int(m.group(1)), bn)
        b = _bucket(p)
        return (BUCKET_ORDER.get(b, 999), bn)

    def combine(folder, out_pdf_path, report_path=None, order_report_path=None):
        if not PdfReader: return False, "pypdf/PyPDF2 missing"
        files=[]
        for root,_,fns in os.walk(folder):
            for fn in fns:
                if fn.lower().endswith(".pdf"): files.append(os.path.join(root, fn))
        intakes = [p for p in files if _bucket(p)=="intake"]
        if intakes:
            newest = max(intakes, key=lambda p: os.path.getmtime(p))
            if not os.path.basename(newest).startswith("01-"):
                newest = _safe_rename(newest, f"{BUCKET_META['intake'][0]}-{BUCKET_META['intake'][1]}")
        chosen={}; others=[]
        for p in files:
            b = _bucket(p)
            if b in ONE_EACH:
                prev = chosen.get(b)
                mt = os.path.getmtime(p) if os.path.exists(p) else 0
                if (not prev) or (mt > os.path.getmtime(prev)): chosen[b]=p
            else:
                others.append(p)
        files = list(chosen.values()) + others
        files.sort(key=_order_key)
        if intakes:
            take=None
            for p in files:
                if os.path.basename(p).startswith("01-Intake Note"): take=p; break
            if take:
                files = [take] + [p for p in files if p != take]
        if order_report_path:
            try:
                with open(order_report_path, "w", encoding="utf-8") as of:
                    of.write("Combine Order (prefix → file)\n=============================\n")
                    for p in files: of.write(f"\n{os.path.basename(p)}")
            except Exception: pass
        try:
            writer = PdfWriter()
            for p in files:
                r = PdfReader(p)
                for i in range(len(r.pages)):
                    writer.add_page(r.pages[i])
            os.makedirs(os.path.dirname(out_pdf_path), exist_ok=True)
            with open(out_pdf_path, "wb") as f:
                writer.write(f)
        except Exception as e:
            return False, {"failures":[("combine", str(e))]}
        if report_path:
            try:
                with open(report_path, "w", encoding="utf-8") as rf:
                    rf.write("Combine Report\n================\n")
                    rf.write(f"Output: {out_pdf_path}\n\nIncluded ({len(files)}):\n")
                    for p in files: rf.write(f"  - {p}\n")
            except Exception: pass
        ok = os.path.exists(out_pdf_path) and os.path.getsize(out_pdf_path) > 1024
        return ok, {"failures": []}

    base.combine = combine

# ---------------- Wire-up ----------------

def main():
    base_path = _find_base_py()
    if not base_path:
        _popup("Base bot not found", "Place this file next to your working base bot and run again.", "error"); _block_exit(); return False
    base = _import_base(base_path)
    if base is None:
        _popup("Import error", "Could not import the selected bot file.", "error"); _block_exit(); return False

    _install_batch_helpers(base)
    _install_admin_pdfs_stage(base)
    _install_intake_fallback(base)
    _install_combiner(base)

    orig_download = getattr(base, "download_via_multi_for_client", None)

    def _is_valid_date_like(val):
        if val is None: return False
        if isinstance(val, str):
            v = val.strip().lower()
            if v in ('', 'nan', 'none'): return False
            if re.search(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", v): return True
            return False
        if isinstance(val, (datetime.date, datetime.datetime)): return True
        if isinstance(val, (int,float)): return val > 20000
        return False

    def _has_intake_by_filename_only(dirpath):
        """Return True if any file name strongly indicates Intake (no PDF text scanning)."""
        for p in glob.glob(os.path.join(dirpath, "*.pdf")):
            bn = os.path.basename(p)
            low = bn.lower()
            if low.startswith("01-") or "intake" in low:
                # treat renamed or clearly named "intake" files as present
                return True
        return False


    def _looks_like_intake_for_date(driver, date_str, max_hops=3):
        """Return True if TherapyNotes shows an Intake row for date_str on current/nearby pages."""
        from selenium.webdriver.common.by import By
        ds = str(date_str).strip()
        variants = {ds}
        m2 = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", ds)
        if m2:
            mm, dd, yy = m2.groups()
            yy = yy if len(yy) == 4 else ("20" + yy)
            variants |= {f"{int(mm)}/{int(dd)}/{yy}", f"{str(mm).zfill(2)}/{str(dd).zfill(2)}/{yy}"}

        def page_has_intake():
            rows = driver.find_elements(By.XPATH, "//tr[contains(@class,'Row') or contains(@class,'AlternateRow')]")
            for tr in rows:
                try:
                    title = _norm_title(tr.find_element(By.XPATH, ".//span[contains(@class,'documentNameSpan')]").text)
                except Exception:
                    title = _norm_title(getattr(tr, "text", "") or "")
                try:
                    tds = tr.find_elements(By.XPATH, "./td")
                    date_text = tds[3].text.strip() if len(tds) >= 4 else ""
                except Exception:
                    date_text = ""
                if (date_text in variants) and (
                    "psychotherapy intake note" in title
                    or re.search(r"\bintake\s+note\b", title or "")
                    or re.search(r"\bclinical\s+intake\b", title or "")
                    or re.search(r"\binitial\s+(assessment|evaluation)\b", title or "")
                    or re.search(r"\bdiagnostic\s+evaluation\b", title or "")
                ):
                    return True
            return False

        if page_has_intake():
            return True
        hops = 0
        while hops < max_hops:
            hopped = False
            try:
                if getattr(base, "try_click_older_or_next", None) and base.try_click_older_or_next(driver):
                    hopped = True
            except Exception:
                hopped = False
            if not hopped:
                break
            hops += 1
            try:
                base.scroll_until_stable(driver, max_passes=3, pause=0.10)
            except Exception:
                pass
            if page_has_intake():
                return True
        return False
    def wrapped_download(driver, ia_date, pn_dates, download_dir, stop_event=None):
        if not _is_valid_date_like(ia_date):
            ia_date = None
        # If a date is supplied as IA but TN doesn't show an Intake for that date,
        # treat that date as a Progress Note date instead and continue.
        if ia_date:
            try:
                if not _looks_like_intake_for_date(driver, ia_date):
                    base.log(f"   ↳ IA override: {ia_date} is not an Intake in TN; treating as Progress.")
                    try:
                        if isinstance(pn_dates, (list, tuple)):
                            pn_list = list(pn_dates)
                        elif pn_dates in (None, "", []):
                            pn_list = []
                        else:
                            pn_list = [pn_dates]
                        if ia_date not in pn_list:
                            pn_list.append(ia_date)
                        pn_dates = pn_list
                    except Exception:
                        pass
                    ia_date = None
            except Exception:
                # If verification fails for any reason, keep original behavior.
                pass


        if orig_download:
            orig_download(driver, ia_date, pn_dates, download_dir, stop_event=stop_event)

        try: base.final_batch_sweep(driver, download_dir, budget_s=240)
        except Exception: pass
        _quiet_settle(download_dir, quiet_secs=1.5, budget_s=900)

        # Ensure ONE Intake if none detected yet (by FILENAME ONLY to avoid false positives)
        try: has_intake = _has_intake_by_filename_only(download_dir)
        except Exception: has_intake = False
        if not has_intake:
            base.log("→ Ensuring Intake Note (none detected yet).")
            try: base.ensure_intake_if_missing(driver, download_dir, max_pages=30)
            except Exception: base.log("[WARN] Fallback Intake ensure threw an exception.")

        _quiet_settle(download_dir, quiet_secs=1.0, budget_s=600)

        base.log("→ Admin PDFs stage: starting (no multi-select).")
        got = base.admin_pdfs_stage(driver, download_dir, max_pages=20)
        if got: base.log(f"✓ Admin PDFs stage complete ({', '.join(sorted(got))}).")

        _quiet_settle(download_dir, quiet_secs=1.5, budget_s=900)

        # Deep Intake guarantee if still missing
        try: has_intake = _has_intake_by_filename_only(download_dir)
        except Exception: has_intake = False
        if not has_intake:
            base.log("→ Final Intake guarantee: none found; running fallback search (deep scan).")
            try: base.ensure_intake_if_missing(driver, download_dir, max_pages=30)
            except Exception: base.log("[WARN] Final Intake guarantee failed with an exception.")
            _quiet_settle(download_dir, quiet_secs=1.5, budget_s=600)

        # Combine
        client_dir = os.path.dirname(download_dir)
        client_name = os.path.basename(client_dir)
        out_dir = os.path.join(client_dir, f"{client_name} Medical Records Chart")
        out_pdf = os.path.join(out_dir, f"{client_name} - Combined.pdf")
        report = os.path.join(out_dir, f"{client_name} - CombineReport.txt")
        order_report = os.path.join(out_dir, f"{client_name} - CombineOrder.txt")
        ok, info = base.combine(download_dir, out_pdf, report_path=report, order_path=None, order_report_path=order_report) if False else base.combine(download_dir, out_pdf, report_path=report, order_report_path=order_report)
        if ok: base.log(f"✓ Combined chart saved: {out_pdf}")
        else:  base.log(f"[WARN] Combine produced a small/empty file. See {report}")

    base.download_via_multi_for_client = wrapped_download

    try:
        import tkinter as tk
        root = tk.Tk(); app = base.MedicalRecordsGUI(root)
        root.title("Medical Records Bot — Extender (FIX7 • Intake fallback via Older/Next; strict trigger) - Version 3.1.0, Last Updated 12/04/2025")
        _popup("Extender active", "Intake fallback uses Older/Next and triggers strictly by filename; single-file wait=60s.", "info")
        root.mainloop()
    except Exception:
        _popup("GUI error", traceback.format_exc(), "error"); _block_exit(); return False
    return True

if __name__ == "__main__":
    ok = False
    try:
        ok = main()
    except Exception:
        _popup("Startup error", traceback.format_exc(), "error"); ok = False
    finally:
        if not ok: _block_exit()
