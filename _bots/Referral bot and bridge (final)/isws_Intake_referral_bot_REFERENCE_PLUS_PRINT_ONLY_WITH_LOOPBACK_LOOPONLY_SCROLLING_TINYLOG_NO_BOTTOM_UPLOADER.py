# isws_Intake_referral_bot_TestingPHASE8.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
#  Intake & Referral Bot — Testing Phase (standard Chrome + direct Search nav)
# =============================================================================

import os, sys, time, json, threading, queue, tempfile, traceback, re
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from dataclasses import dataclass
from typing import Optional, Dict, List
import requests
import argparse

APP_TITLE = "IA Only Referral Bot"
MAROON    = "#800000"
LOG_BG    = "#f7f3f2"
LOG_FG    = "#1a1a1a"

def _title_banner(root):
    frm = ttk.Frame(root); frm.pack(fill='x')
    banner = tk.Frame(frm, bg=MAROON, height=54); banner.pack(fill='x')
    lbl = tk.Label(banner, text=APP_TITLE, fg="white", bg=MAROON,
                   font=("Segoe UI", 18, "bold"), pady=6)
    lbl.pack(side='left', padx=14, pady=6)
    # Top-right Launch Uploader button (larger)
    try:
        btn = tk.Button(banner, text="Launch Uploader", command=root.launch_uploader_bridge,
                        font=("Segoe UI", 11, "bold"), padx=14, pady=6, bg="#eeeeee", fg="#111111",
                        relief="raised", bd=1, cursor="hand2")
        btn.pack(side='right', padx=14, pady=8)
    except Exception:
        pass
    return frm, banner

class UILog:
    def __init__(self, text_widget):
        self.text = text_widget
        self.q = queue.Queue()
        self.max_per_tick = 200
        self.text.after(40, self._flush)
    def write(self, msg: str):
        self.q.put(msg)
    def _flush(self):
        try:
            while not self.q.empty():
                line = self.q.get()
                try:
                    self.text.insert(tk.END, line + "\n")
                    self.text.see(tk.END)
                except Exception:
                    print(line)
        finally:
            self.text.after(40, self._flush)

def _ts(): return time.strftime("[%H:%M:%S] ")

# ---------------- Selenium lazy import ----------------
By = WebDriverWait = EC = Keys = None
def _lazy_import_selenium():
    global By, WebDriverWait, EC, Keys
    from selenium import webdriver
    from selenium.webdriver.common.by import By as _By
    from selenium.webdriver.support.ui import WebDriverWait as _WebDriverWait
    from selenium.webdriver.support import expected_conditions as _EC
    from selenium.webdriver.common.keys import Keys as _Keys
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    By, WebDriverWait, EC, Keys = _By, _WebDriverWait, _EC, _Keys
    return webdriver, _By, _WebDriverWait, _EC, _Keys, Service, ChromeDriverManager

# ---------------- Column resolver ----------------
def _normalize_col_token(token: str) -> str:
    if token is None: return ""
    t = str(token).strip().strip("\"'“”‘’`")
    return t

def _is_single_letter(t: str) -> bool:
    return len(t) == 1 and t.isalpha()

def _clean_numeric_to_int_str(value) -> str:
    """
    Convert numeric values (including floats like 12345.0) to clean integer strings.
    Handles floats that are whole numbers by converting them to integers first.
    """
    if value is None:
        return ""
    try:
        # Try to convert to float first to handle numeric strings
        float_val = float(value)
        # If it's a whole number, convert to int to remove .0
        if float_val.is_integer():
            return str(int(float_val))
        # If it has decimal places, keep as float string (shouldn't happen for IDs, but be safe)
        return str(float_val)
    except (ValueError, TypeError):
        # Not a number, just return as string after stripping
        return str(value).strip()

def resolve_column(df, name_or_letter: str):
    """
    Accept a header name OR a single column letter (A,B,...).
    Returns a pandas Series or raises KeyError.
    """
    token = _normalize_col_token(name_or_letter)
    if not token:
        raise KeyError("Empty column selector.")
    if _is_single_letter(token):
        idx = ord(token.upper()) - ord('A')
        if idx < 0 or idx >= len(df.columns):
            raise KeyError(f"Column letter {token} is out of range (file has {len(df.columns)} columns).")
        return df.iloc[:, idx]
    if token not in df.columns:
        raise KeyError(f"Header not found: {token}")
    return df[token]

# ---------------- Data loaders ----------------
@dataclass
class OneDriveSlice:
    file_url: str
    row_from: int
    row_to: int
    col_selector: str  # header or letter

    def download_via_cookies(self, driver, log) -> Optional[str]:
        if not self.file_url:
            log(_ts() + "[OD][ERR] Missing OneDrive/SharePoint file URL.")
            return None
        dl_url = self.file_url if "download=1" in self.file_url else \
                 self.file_url + ("&download=1" if "?" in self.file_url else "?download=1")
        try:
            driver.switch_to.default_content()
            driver.get(self.file_url)  # prime cookies/SSO
            time.sleep(1.0)
        except Exception as e:
            log(_ts() + f"[OD][WARN] Pre-open failed: {e}")

        try:
            cookies = driver.get_cookies()
        except Exception as e:
            log(_ts() + f"[OD][ERR] Could not read browser cookies: {e}")
            return None

        sess = requests.Session()
        for c in cookies:
            dom = (c.get("domain") or "").lstrip(".")
            try:
                sess.cookies.set(c.get("name"), c.get("value"), domain=dom, path=c.get("path") or "/")
            except Exception:
                pass

        try:
            r = sess.get(dl_url, stream=True)
            if r.status_code != 200:
                log(_ts() + f"[OD][ERR] HTTP {r.status_code} downloading file.")
                return None
            fd, outpath = tempfile.mkstemp(suffix=".xlsx")
            with os.fdopen(fd, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    if chunk: f.write(chunk)
            log(_ts() + f"[OD] Downloaded Excel to {outpath}")
            return outpath
        except Exception as e:
            log(_ts() + f"[OD][ERR] Download failed: {e}")
            return None

    def load_rows_from_path(self, xlsx_path: str, log) -> List[Dict]:
        import pandas as pd
        try:
            all_sheets = pd.read_excel(xlsx_path, sheet_name=None)
        except Exception as e:
            log(_ts() + f"[DATA][ERR] Could not read Excel: {e}")
            return []
        sheet_name = next((n for n in all_sheets.keys() if str(n).strip().lower().startsWith("ia referrals")),
                          list(all_sheets.keys())[0])
        # small correction if .startsWith typo occurs
        if isinstance(sheet_name, bool):  # safeguard
            sheet_name = list(all_sheets.keys())[0]
        df = all_sheets[sheet_name]
        s = max(2, int(self.row_from)) - 2
        e = max(s, int(self.row_to) - 2)

        token = _normalize_col_token(self.col_selector)
        log(_ts() + f"[DATA] Column token: '{token}'  | Sheet: '{sheet_name}'  | Columns: {list(df.columns)}")
        try:
            series = resolve_column(df, token)
        except KeyError as ke:
            log(_ts() + f"[DATA][ERR] {ke}")
            return []

        sub = df.iloc[s:e+1].copy()
        try:
            # Use helper function to clean numeric values (removes .0 from integers)
            sub["_Bot_ID"] = series.iloc[s:e+1].apply(_clean_numeric_to_int_str)
        except Exception:
            sub["_Bot_ID"] = ""
        recs = sub.to_dict(orient="records")
        log(_ts() + f"[DATA] Loaded {len(recs)} rows from {sheet_name} [{self.row_from}..{self.row_to}].")
        return recs

@dataclass
class LocalSlice:
    file_path: str
    row_from: int
    row_to: int
    col_selector: str  # header or letter

    def _read_dataframe(self, log):
        import pandas as pd
        p = self.file_path.lower()
        if p.endswith(('.xlsx', '.xlsm', '.xls')):
            return pd.read_excel(self.file_path)
        # CSV with robust encodings
        encodings = ["utf-8-sig", "cp1252", "latin1"]
        last_err = None
        for enc in encodings:
            try:
                return pd.read_csv(self.file_path, encoding=enc)
            except Exception as e:
                last_err = e
        log(_ts() + f"[DATA][WARN] CSV read failed with common encodings; last error: {last_err}. Trying python engine/skip.")
        try:
            return pd.read_csv(self.file_path, encoding="latin1", engine="python", on_bad_lines="skip")
        except Exception as e:
            log(_ts() + f"[DATA][ERR] Could not read {self.file_path}: {e}")
            return None

    def load(self, log) -> List[Dict]:
        import pandas as pd
        if not self.file_path or not os.path.isfile(self.file_path):
            log(_ts() + f"[DATA][ERR] File not found: {self.file_path}")
            return []
        df = self._read_dataframe(log)
        if df is None: return []

        s = max(2, int(self.row_from)) - 2
        e = max(s, int(self.row_to) - 2)

        token = _normalize_col_token(self.col_selector)
        log(_ts() + f"[DATA] Column token: '{token}'  | Columns: {list(df.columns)}")
        try:
            series = resolve_column(df, token)
        except KeyError as ke:
            log(_ts() + f"[DATA][ERR] {ke}")
            return []

        sub = df.iloc[s:e+1].copy()
        try:
            # Use helper function to clean numeric values (removes .0 from integers)
            sub["_Bot_ID"] = series.iloc[s:e+1].apply(_clean_numeric_to_int_str)
        except Exception:
            sub["_Bot_ID"] = ""
        recs = sub.to_dict(orient="records")
        log(_ts() + f"[DATA] Loaded {len(recs)} rows from local file [{self.row_from}..{self.row_to}].")
        return recs

# ---------------- Penelope client ----------------
PN_DEFAULT_URL = "https://integrityseniorservices.athena-us.com/acm_loginControl"

@dataclass
class PNAuth:
    url: str
    username: str
    password: str

def _pick_profile_dir(user_data_dir: str) -> tuple[str, str]:
    if not user_data_dir or not os.path.isdir(user_data_dir):
        return user_data_dir, ""
    base = os.path.basename(user_data_dir).lower()
    if base == "user data":
        for name in ["Default", "Profile 1", "Profile 2"]:
            cand = os.path.join(user_data_dir, name)
            if os.path.isdir(cand):
                return user_data_dir, name
        return user_data_dir, "Default"
    else:
        parent = os.path.dirname(user_data_dir)
        prof   = os.path.basename(user_data_dir)
        if os.path.basename(parent).lower() == "user data":
            return parent, prof
        return user_data_dir, ""


class PNClient:
    def __init__(self, auth: PNAuth, log):
        self.auth = auth
        self.log = log
        self.driver = None
        self.wait = None

    def start(self, chrome_profile_dir: Optional[str] = None):
        webdriver, _By, _WebDriverWait, _EC, _Keys, Service, ChromeDriverManager = _lazy_import_selenium()
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            # Only attach Chrome profile if explicitly provided (OneDrive mode). CSV/XLSX local runs pass None.
            if chrome_profile_dir and os.path.isdir(chrome_profile_dir):
                ud_dir, prof_name = _pick_profile_dir(chrome_profile_dir)
                options.add_argument(f"--user-data-dir={ud_dir}")
                if prof_name:
                    options.add_argument(f"--profile-directory={prof_name}")
                    self.log(_ts() + f"[BROWSER] Using Chrome profile: {ud_dir}\\{prof_name}")
                else:
                    self.log(_ts() + f"[BROWSER] Using Chrome user-data: {ud_dir}")
            else:
                self.log(_ts() + "[BROWSER] Using fresh Selenium profile (no saved cookies).")
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = _WebDriverWait(self.driver, 20)  # match Welcome bot timing
        except Exception as e:
            self.log(_ts() + f"[BROWSER][ERR] Could not start Chrome: {e}")
            raise

    def login(self) -> bool:
        d, w = self.driver, self.wait
        url = (self.auth.url or PN_DEFAULT_URL).strip()
        self.log(_ts() + f"[PN] Opening {url} …")
        try:
            d.get(url)
        except Exception as e:
            self.log(_ts() + f"[PN][ERR] Could not open URL: {e}")
            return False

        # Locate the login iframe and the user/password inputs
        def _switch_login_iframe():
            try:
                d.switch_to.default_content()
                frames = d.find_elements("css selector", "iframe, frame")
                for fr in frames:
                    try:
                        src = (fr.get_attribute("src") or "").lower()
                        idv = (fr.get_attribute("id") or "").lower()
                        namev = (fr.get_attribute("name") or "").lower()
                        if "acm_login" in src or "login" in src or "acm_login" in idv or "acm_login" in namev:
                            d.switch_to.frame(fr); return True
                    except Exception:
                        continue
                # try a direct known id
                try:
                    fr = d.find_element("id", "acm_loginControl")
                    d.switch_to.frame(fr); return True
                except Exception:
                    pass
                return False
            except Exception:
                return False

        # Some tenants show an interstitial; be tolerant
        try:
            _switch_login_iframe()
        except Exception:
            pass

        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        # Try to find fields in current context (iframe or default)
        def try_login_in_ctx():
            try:
                users = d.find_elements(By.CSS_SELECTOR, "input[type='text'],input[type='email']")
                pwds  = d.find_elements(By.CSS_SELECTOR, "input[type='password']")
                if not users or not pwds:
                    return False
                u = users[0]; p = pwds[0]
                try: u.clear(); u.click()
                except Exception: pass
                try: u.send_keys(self.auth.username)
                except Exception:
                    d.execute_script("arguments[0].value = arguments[1];", u, self.auth.username)
                try: p.clear(); p.click()
                except Exception: pass
                try: p.send_keys(self.auth.password)
                except Exception:
                    d.execute_script("arguments[0].value = arguments[1];", p, self.auth.password)
                # Click submit or press Enter
                for by, sel in [
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.CSS_SELECTOR, "input[type='submit']"),
                    (By.XPATH, "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'sign in')]"),
                    (By.XPATH, "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'log in')]"),
                    (By.XPATH, "//input[@type='submit']"),
                ]:
                    try:
                        btn = d.find_element(by, sel)
                        try: btn.click()
                        except Exception: d.execute_script("arguments[0].click();", btn)
                        return True
                    except Exception:
                        continue
                p.send_keys(Keys.ENTER)
                return True
            except Exception:
                return False

        if not try_login_in_ctx():
            # Try switching iframe and re-attempt
            _switch_login_iframe()
            try_login_in_ctx()

        try:
            # Wait for URL change or presence of a logout control
            w.until(lambda drv: drv.current_url != url)
        except Exception:
            pass
        self.log(_ts() + "[PN] Login appears successful.")
        return True

    def _switch_to_search_content_frame(self) -> bool:
        from selenium.webdriver.common.by import By
        d = self.driver
        try:
            d.switch_to.default_content()
            fr = d.find_element(By.ID, "frm_content_id")
            d.switch_to.frame(fr)
            return True
        except Exception:
            return False

    def go_to_search(self) -> bool:
        """Open the Search UI and ensure the content frame is focused."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        d, w = self.driver, self.wait
        try:
            d.switch_to.default_content()
            # Try clicking a nav item first
            for by, sel in [
                (By.XPATH, "//a[contains(.,'Search') and @href]"),
                (By.CSS_SELECTOR, "a[href*='acm_searchControl']"),
            ]:
                try:
                    el = d.find_element(by, sel)
                    try: el.click()
                    except Exception: d.execute_script("arguments[0].click();", el)
                    break
                except Exception:
                    continue
            else:
                # Direct URL fallback
                origin = re.match(r'^(https?://[^/]+)', d.current_url)
                if origin:
                    d.get(origin.group(1) + "/acm_searchControl?actionType=view")
            # Now ensure frame
            WebDriverWait(d, 15).until(lambda _drv: True)
            ok = self._switch_to_search_content_frame()
            if not ok:
                return False
            return True
        except Exception:
            return False

    def focus_search_box(self) -> bool:
        """Put the caret in Individual ID input if available."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        d = self.driver
        if not self._switch_to_search_content_frame():
            return False
        candidates = [
            (By.CSS_SELECTOR, "input#individualId"),
            (By.XPATH, "//label[contains(normalize-space(.),'Individual ID')]/following::input[1]"),
            (By.CSS_SELECTOR, "input[name*='individual'][type='text']"),
        ]
        for by, sel in candidates:
            try:
                box = WebDriverWait(d, 10).until(EC.presence_of_element_located((by, sel)))
                try: box.click()
                except Exception: d.execute_script("arguments[0].focus();", box)
                return True
            except Exception:
                continue
        return False

    def enter_individual_id_and_go(self, indiv_id: str) -> bool:
        # Ensure we are on the Search page
        self.go_to_search()
        if not self._switch_to_search_content_frame():
            self.log(_ts() + "[SEARCH][ERR] Could not switch to the Search content frame.")
            return False
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        d = self.driver
        candidates = [
            (By.CSS_SELECTOR, "input#individualId"),
            (By.XPATH, "//label[contains(normalize-space(.),'Individual ID')]/following::input[1]"),
            (By.CSS_SELECTOR, "input[name*='individual'][type='text']"),
        ]
        box = None
        for by, sel in candidates:
            try:
                box = WebDriverWait(d, 10).until(EC.presence_of_element_located((by, sel)))
                break
            except Exception:
                continue
        if not box:
            self.log(_ts() + "[SEARCH][ERR] Individual ID input not found.")
            return False
        # Clean the ID to remove .0 from numeric values
        clean_id = _clean_numeric_to_int_str(indiv_id)
        try: box.clear(); box.send_keys(clean_id)
        except Exception:
            try: d.execute_script("arguments[0].value = arguments[1];", box, clean_id)
            except Exception as e:
                self.log(_ts() + f"[SEARCH][ERR] Could not type ID: {e}")
                return False
        # Try to click GO/Submit
        for by, sel in [
            (By.XPATH, "//button[contains(.,'GO') or contains(.,'Go')]"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
        ]:
            try:
                btn = d.find_element(by, sel)
                try: btn.click()
                except Exception: d.execute_script("arguments[0].click();", btn)
                return True
            except Exception:
                continue
        # Enter key fallback
        try:
            from selenium.webdriver.common.keys import Keys as _Keys
            box.send_keys(_Keys.ENTER)
            return True
        except Exception:
            return False

    def click_toolbar_search_with_wait(self, timeout: int = 20) -> bool:
        '''
        Click the toolbar Search button (#navSearch) that lives in frame_1 (frm_content_id)
        after login, waiting for overlays to disappear and the frame to be ready.
        '''
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception:
            return False

        d = self.driver
        try:
            # Always start from default content
            d.switch_to.default_content()
            # Wait for content frame to be present and switch in
            fr = WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.ID, "frm_content_id")))
            d.switch_to.frame(fr)

            # Wait for document readiness
            try:
                WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

            # Wait for overlays to be gone inside the frame
            def _overlay_gone(driver):
                try:
                    gray = driver.find_elements(By.ID, "mainFrameCoverGray")
                    white = driver.find_elements(By.ID, "mainFrameCoverWhite")
                    # Consider overlays "gone" if none present or all are hidden/not displayed
                    def hidden(el):
                        try:
                            if not el.is_displayed(): return True
                            disp = el.value_of_css_property("display") or ""
                            vis  = el.value_of_css_property("visibility") or ""
                            op   = el.value_of_css_property("opacity") or "1"
                            return disp == "none" or vis == "hidden" or float(op) == 0.0
                        except Exception:
                            return True
                    covers = (gray or []) + (white or [])
                    return all(hidden(el) for el in covers) if covers else True
                except Exception:
                    return True
            try:
                WebDriverWait(d, timeout).until(_overlay_gone)
            except Exception:
                pass

            # Now click the toolbar Search li#navSearch
            btn = WebDriverWait(d, timeout).until(EC.element_to_be_clickable((By.ID, "navSearch")))
            try:
                btn.click()
            except Exception:
                d.execute_script("arguments[0].click();", btn)

            # Leave frame; let caller proceed
            d.switch_to.default_content()
            return True
        except Exception:
            # Fallback: direct open the Search page route on same origin
            try:
                d.switch_to.default_content()
                origin = d.execute_script("return location.origin")
            except Exception:
                import re as _re
                cur = d.current_url or ""
                m = _re.match(r"^(https?://[^/]+)", cur)
                origin = m.group(1) if m else "https://integrityseniorservices.athena-us.com"
            try:
                d.get(origin + "/acm_searchControl?actionType=view")
                return True
            except Exception:
                return False

    def click_individual_tab(self, timeout: int = 8) -> bool:
        '''
        FAST: force-switch to "Individual" tab on the Search page inside frm_content_id.
        '''
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception:
            return False
        d = self.driver
        try:
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
            try:
                d.execute_script("try{ if(typeof goTab==='function'){ goTab('tabIndiv'); } }catch(e){}")
            except Exception:
                pass
            try:
                tab = WebDriverWait(d, 2).until(EC.element_to_be_clickable((By.ID, "tabIndiv_li")))
                try: tab.click()
                except Exception: d.execute_script("arguments[0].click();", tab)
            except Exception:
                pass
            WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.NAME, "txtKIndID")))
            d.switch_to.default_content()
            return True
        except Exception:
            try: d.switch_to.default_content()
            except Exception: pass
            return False

    def enter_individual_id_and_go(self, indiv_id: str, timeout: int = 12) -> bool:
        """
        Individual > Individual ID: enter ID # > Press Go > WAIT for dropdown/results.
        Only this step is modified. No other flow is touched.
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
        except Exception:
            return False

        d = self.driver
        log = getattr(self, "log", lambda s: None)

        def _open_search_if_needed() -> bool:
            """Open Search only if the content frame isn't present yet."""
            try:
                d.switch_to.default_content()
                # If frame already available, don't touch anything.
                try:
                    WebDriverWait(d, 2).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                    d.switch_to.default_content()
                    return True
                except Exception:
                    pass
                # Click toolbar search
                nav = WebDriverWait(d, timeout).until(EC.element_to_be_clickable((By.ID, "navSearch")))
                try:
                    nav.click()
                except Exception:
                    d.execute_script("arguments[0].click();", nav)
                # Wait for frame to appear after clicking Search
                WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                d.switch_to.default_content()
                return True
            except Exception:
                try: d.switch_to.default_content()
                except Exception: pass
                return False

        def _into_frame() -> bool:
            try:
                d.switch_to.default_content()
                WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                return True
            except Exception:
                try: d.switch_to.default_content()
                except Exception: pass
                return False

        def _activate_individual_tab() -> bool:
            """Use JS goTab + click fallback; confirm txtKIndID is present and ready for input."""
            try:
                try:
                    d.execute_script("if (typeof goTab==='function') { goTab('tabIndiv'); }")
                except Exception:
                    pass
                try:
                    tab = WebDriverWait(d, 4).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "li#tabIndiv_li")))
                    try:
                        tab.click()
                    except Exception:
                        d.execute_script("arguments[0].click();", tab)
                except Exception:
                    pass
                
                # Wait for the Individual ID field to be present and clickable
                id_input = WebDriverWait(d, 6).until(EC.element_to_be_clickable((By.NAME, "txtKIndID")))
                
                # Immediately focus on the Individual ID field and clear it
                try:
                    id_input.click()
                    id_input.clear()
                    log("[INDIV] Individual tab activated - ID field focused and cleared")
                except Exception as e:
                    log(f"[INDIV] Could not focus/clear ID field: {e}")
                
                return True
            except Exception:
                return False

        def _wait_results(wait_secs: int) -> bool:
            """Accept either a dropdown or a populated #results area."""
            LOCS = [
                (By.CSS_SELECTOR, "ul[role='listbox'] li[role='option']"),
                (By.XPATH, "//li[contains(@class,'select2-results__option') or @role='option']"),
                (By.CSS_SELECTOR, ".ui-autocomplete li"),
                (By.CSS_SELECTOR, ".dropdown-menu.show .dropdown-item"),
                (By.XPATH, "//div[@id='results']//a[normalize-space(text())!='']"),
                (By.ID, "results"),
            ]
            def _has_any(_):
                try:
                    for by, sel in LOCS:
                        els = d.find_elements(by, sel)
                        if not els:
                            continue
                        if by == By.ID and sel == "results":
                            try:
                                txt = (d.find_element(By.ID, "results").text or "").strip()
                                if txt:
                                    return True
                            except Exception:
                                continue
                        else:
                            # At least one visible option/item
                            for el in els:
                                try:
                                    if el.is_displayed():
                                        return True
                                except Exception:
                                    continue
                    return False
                except StaleElementReferenceException:
                    return False
            try:
                WebDriverWait(d, wait_secs).until(_has_any)
                return True
            except Exception:
                return False

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                log(f"[INDIV] Attempt {attempt}/{max_attempts}: open search (if needed), Individual tab, ID, GO, wait…")

                # Make sure Search UI exists
                if not _open_search_if_needed():
                    raise TimeoutException("Search toolbar/frame not reachable")

                # Always go *into* the frame for the rest of the work
                if not _into_frame():
                    raise TimeoutException("Could not enter frm_content_id")

                # Activate Individual tab (idempotent; safe if already active)
                if not _activate_individual_tab():
                    # If the tab toggle caused a reload, re-enter the frame and try once more quickly
                    if _into_frame() and _activate_individual_tab():
                        pass
                    else:
                        raise TimeoutException("Could not activate Individual tab")

                # The ID field should already be focused and cleared from _activate_individual_tab
                # Just get a fresh reference and enter the ID
                id_input = WebDriverWait(d, 6).until(EC.element_to_be_clickable((By.NAME, "txtKIndID")))
                
                # Clean the ID to remove .0 from numeric values (extra safeguard)
                _id = _clean_numeric_to_int_str(indiv_id)
                log(f"[INDIV] Entering Individual ID: {_id}")
                
                # Enhanced stale element handling for ID input
                for retry in range(3):
                    try:
                        # Re-find the element each time to avoid stale references
                        id_input = WebDriverWait(d, 6).until(EC.element_to_be_clickable((By.NAME, "txtKIndID")))
                        id_input.send_keys(_id)
                        log(f"[INDIV] Successfully entered ID: {_id}")
                        break
                    except StaleElementReferenceException:
                        log(f"[INDIV] Stale element on retry {retry + 1}/3, re-finding element...")
                        if retry == 2:  # Last retry
                            raise
                        # Re-enter frame and try again
                        if not _into_frame():
                            raise
                        time.sleep(0.5)  # Brief pause before retry

                # Click GO (primary: #goButton; fallbacks just in case)
                go = None
                try:
                    go = WebDriverWait(d, 6).until(EC.element_to_be_clickable((By.ID, "goButton")))
                except Exception:
                    for how, sel in [
                        (By.XPATH, "//button[normalize-space()='GO']"),
                        (By.CSS_SELECTOR, "button[type='submit']"),
                        (By.CSS_SELECTOR, "input[type='submit']"),
                    ]:
                        try:
                            go = WebDriverWait(d, 4).until(EC.element_to_be_clickable((how, sel)))
                            break
                        except Exception:
                            continue

                if go is not None:
                    try:
                        go.click()
                    except Exception:
                        d.execute_script("arguments[0].click();", go)
                else:
                    # ENTER fallback if no GO could be isolated
                    try:
                        id_input.send_keys("\ue007")  # ENTER
                    except Exception:
                        pass

                # GO often reloads the inner frame; drop old refs and re-enter
                if not _into_frame():
                    raise TimeoutException("No frame after GO (reload expected)")

                # Wait for dropdown/results to render
                if not _wait_results(wait_secs=max(6, min(12, timeout))):
                    # One gentle JS nudge if provided by the page
                    try:
                        d.execute_script("if (typeof searchForCurrentTab==='function') { searchForCurrentTab(); }")
                    except Exception:
                        pass
                    if not _wait_results(wait_secs=max(5, min(10, timeout))):
                        raise TimeoutException("Results did not render in time")

                # Success
                try: d.switch_to.default_content()
                except Exception: pass
                log("[INDIV] Results detected; ready to select client.")
                return True

            except Exception as e:
                log(f"[INDIV][WARN] No results yet ({e}). Retrying…")
                try: d.switch_to.default_content()
                except Exception: pass

        log("[INDIV][ERR] Failed to render dropdown/results after retries.")
        try: d.switch_to.default_content()
        except Exception: pass
        return False

    def click_first_result_name(self, first_name: str = None, last_name: str = None, timeout: int = 12) -> bool:
        '''
        After pressing Go on the Search page, click the patient's first or last name
        in the results dropdown/table to open their profile.
        If names are not provided, click the first visible name link.
        '''
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception:
            return False

        d = self.driver
        try:
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))

            try:
                WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.ID, "results")))
            except Exception:
                pass

            def _find_name_link():
                anchors = []
                try:
                    anchors.extend(d.find_elements(By.XPATH, "//div[@id='results']//a[normalize-space(text())!='']"))
                except Exception:
                    pass
                try:
                    anchors.extend(d.find_elements(By.XPATH, "//a[contains(translate(@href,'INDIV','indiv'),'indiv') or contains(translate(@href,'INDIVIDUAL','individual'),'individual')]"))
                except Exception:
                    pass
                try:
                    anchors.extend(d.find_elements(By.XPATH, "//table//a[normalize-space(text())!='']"))
                except Exception:
                    pass
                seen = set()
                uniq = []
                for a in anchors:
                    try:
                        key = (a.get_attribute("href") or "") + "|" + (a.text or "")
                    except Exception:
                        key = id(a)
                    if key in seen:
                        continue
                    seen.add(key)
                    try:
                        if a.is_displayed():
                            uniq.append(a)
                    except Exception:
                        pass
                if not uniq:
                    return None

                def norm(s):
                    return (s or "").strip().lower()
                fn = norm(first_name)
                ln = norm(last_name)

                if fn or ln:
                    for a in uniq:
                        t = norm(a.text)
                        if not t:
                            continue
                        if (fn and fn in t) or (ln and ln in t):
                            return a

                return uniq[0]

            link = None
            try:
                link = WebDriverWait(d, timeout).until(lambda drv: _find_name_link())
            except Exception:
                link = _find_name_link()

            if not link:
                d.switch_to.default_content()
                return False

            try:
                link.click()
            except Exception:
                d.execute_script("arguments[0].click();", link)

            d.switch_to.default_content()
            return True
        except Exception:
            try: d.switch_to.default_content()
            except Exception: pass
            return False

    def click_open_case_link(self, last_name_hint: str = None, timeout: int = 12) -> bool:
        '''
        On the Individual profile page, click the open "{LastName} Case" link (skip those marked Closed).
        '''
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception:
            return False

        d = self.driver
        try:
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))

            try:
                WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

            # Collect likely case links
            candidates = []
            try:
                candidates.extend(d.find_elements(By.CSS_SELECTOR, "a[href*='caseFileControl']"))
            except Exception:
                pass
            try:
                candidates.extend(d.find_elements(
                    By.XPATH,
                    "//a[contains(normalize-space(.),' Case') and not(contains(translate(normalize-space(.),"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'closed'))]"
                ))
            except Exception:
                pass

            seen, links = set(), []
            for a in candidates:
                try:
                    key = (a.get_attribute("href") or "") + "|" + (a.text or "")
                except Exception:
                    key = id(a)
                if key in seen: continue
                seen.add(key)
                try:
                    if a.is_displayed():
                        links.append(a)
                except Exception:
                    pass

            if not links:
                d.switch_to.default_content()
                return False

            def norm(s): return (s or "").strip().lower()
            ln = norm(last_name_hint)
            chosen = None
            if ln:
                for a in links:
                    try:
                        if ln in norm(a.text):
                            chosen = a; break
                    except Exception:
                        continue
            if not chosen:
                chosen = links[0]

            try:
                chosen.click()
            except Exception:
                d.execute_script("arguments[0].click();", chosen)

            d.switch_to.default_content()
            return True
        except Exception:
            try: d.switch_to.default_content()
            except Exception: pass
            return False
    def open_referral_document(self, timeout: int = 15) -> bool:
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import Select as _Select
        except Exception:
            return False
        d = self.driver
        try:
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
            try:
                d.execute_script("try{ if(typeof doBuckets==='function'){ doBuckets('cDocSB1'); } }catch(e){}")
            except Exception:
                pass
            sel = None
            try:
                sel = WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#cDocSB1 select")))
            except Exception:
                try:
                    sel = WebDriverWait(d, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "form[name='cDocSB1_actionForm'] select")))
                except Exception:
                    sel = None
            if not sel:
                d.switch_to.default_content()
                return False
            try:
                _Select(sel).select_by_visible_text("Referral Form")
            except Exception:
                try:
                    _Select(sel).select_by_value("211")
                except Exception:
                    js = ("var s = arguments[0];"
                          "function setSelByText(el, txt){for(var i=0;i<el.options.length;i++){if(el.options[i].text.replace(/\\s+/g,' ').trim().toLowerCase()==txt.toLowerCase()){el.selectedIndex=i;return true;}}return false;}"
                          "if(!setSelByText(s,'Referral Form')){for(var i=0;i<s.options.length;i++){if(s.options[i].value=='211'){s.selectedIndex=i;break;}}}"
                          "if(typeof Event==='function'){s.dispatchEvent(new Event('change',{bubbles:true}));}else if(document.createEvent){var ev=document.createEvent('HTMLEvents');ev.initEvent('change',true,false);s.dispatchEvent(ev);}else if(s.onchange){s.onchange();}")
                    try:
                        d.execute_script(js, sel)
                    except Exception:
                        pass
            d.switch_to.default_content()
            def _iframe_available(driver):
                try:
                    iframe = driver.find_element(By.ID, "dynamicIframe")
                    return iframe if iframe.is_displayed() else None
                except Exception:
                    return None
            found = None
            try:
                WebDriverWait(d, 2).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                found = WebDriverWait(d, 6).until(lambda drv: _iframe_available(drv))
            except Exception:
                found = None
            finally:
                try: d.switch_to.default_content()
                except Exception: pass
            if not found:
                try:
                    found = WebDriverWait(d, 6).until(lambda drv: _iframe_available(drv))
                except Exception:
                    found = None
            return found is not None
        except Exception:
            try: d.switch_to.default_content()
            except Exception: pass
            return False



    def complete_referral_popup_and_finish(self, timeout: int = 20) -> bool:
        """
        In the 'Referral Form' popup:
          1) Select the client in "For Case Member" (skip '-Select-' and 'Other Individual')
          2) Click 'Document Description' to trigger form load
          3) Switch back to parent frame and click enabled 'Finish'
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait, Select
            from selenium.webdriver.support import expected_conditions as EC
        except Exception:
            return False
        d = self.driver
        # Enter frm_content if present
        try:
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
        except Exception:
            pass
        # Find the dynamic popup iframe
        def _find_dyn():
            for cand in ("dynamicIframe","dynamicAltframe"):
                try:
                    el = d.find_element(By.ID, cand)
                    if el.is_displayed():
                        return el
                except Exception:
                    pass
            try:
                frs = d.find_elements(By.CSS_SELECTOR, "iframe,frame")
                return frs[-1] if frs else None
            except Exception:
                return None
        dyn = _find_dyn()
        if not dyn:
            try: d.switch_to.default_content()
            except Exception: pass
            return False
        # Switch into the popup iframe
        try:
            d.switch_to.frame(dyn)
        except Exception:
            try: d.switch_to.default_content()
            except Exception: pass
            return False
        # 1) For Case Member select
        try:
            sel = WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.NAME, "kBookItemID2")))
            S = Select(sel)
            idx = None
            for i, o in enumerate(S.options):
                txt = (o.text or "").strip().lower()
                val = (o.get_attribute("value") or "").strip()
                if not val:  # skip '-Select-' / empty
                    continue
                if "other individual" in txt:
                    continue
                idx = i; break
            if idx is None:
                for i, o in enumerate(S.options):
                    val = (o.get_attribute("value") or "").strip()
                    if val:
                        idx = i; break
            if idx is None:
                try: d.switch_to.default_content()
                except Exception: pass
                return False
            S.select_by_index(idx)
        except Exception:
            try: d.switch_to.default_content()
            except Exception: pass
            return False
        # 2) Click Document Description to trigger the form
        try:
            desc = WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.NAME, "cDocDesc")))
            try: desc.click()
            except Exception: d.execute_script("arguments[0].focus();", desc)
        except Exception:
            try: d.switch_to.default_content()
            except Exception: pass
            return False
        import time as _time
        _time.sleep(0.9)  # allow JS to enable Finish
        # 3) Back to parent frame; click Finish when enabled
        try:
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
        except Exception:
            pass
        try:
            finish = WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.ID, "wizFinishButton")))
            WebDriverWait(d, timeout).until(lambda drv: "Disable" not in (finish.get_attribute("class") or ""))
            try: finish.click()
            except Exception: d.execute_script("arguments[0].click();", finish)
        except Exception:
            try: d.switch_to.default_content()
            except Exception: pass
            return False
        _time.sleep(0.6)
        try: d.switch_to.default_content()
        except Exception: pass
        return True

    def click_print_and_save_pdf(self, client_name: str = None, urgent: bool = False, counselor_name: str = None, timeout: int = 25) -> bool:
        """
        Click the in‑app Print button, switch to the report window, capture it as PDF via CDP,
        save as "[First Name Last Name Referral Form].pdf" in "Referral Form Bot Output", and return to main.
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception:
            return False

        import time, base64, os, re as _re
        d = self.driver

        # Enter content frame if present
        try:
            d.switch_to.default_content()
            WebDriverWait(d, 6).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
        except Exception:
            try: d.switch_to.default_content()
            except Exception: pass

        # Locate the in‑app Print control (Penelope uses openRpt(...))
        locators = [
            (By.XPATH, "//a[contains(@onclick,'openRpt')]"),
            (By.CSS_SELECTOR, "a[href*='openRpt']"),
            (By.XPATH, "//a[contains(normalize-space(.),'Print')]"),
            (By.XPATH, "//button[contains(normalize-space(.),'Print')]"),
        ]
        anchor = None
        for how, sel in locators:
            try:
                el = d.find_element(how, sel)
                if el.is_displayed():
                    anchor = el; break
            except Exception:
                continue
        if not anchor:
            # Fallback: scan all anchors for openRpt
            try:
                for el in d.find_elements(By.TAG_NAME, "a"):
                    oc = ((el.get_attribute("onclick") or "") + " " + (el.get_attribute("href") or ""))
                    if "openRpt" in oc:
                        anchor = el; break
            except Exception:
                pass
        if not anchor:
            return False

        main = d.current_window_handle
        handles_before = set(d.window_handles)
        try: d.execute_script("arguments[0].scrollIntoView({block:'center'});", anchor)
        except Exception: pass
        try: anchor.click()
        except Exception: d.execute_script("arguments[0].click();", anchor)

        # Wait for new report window
        def _new_win(driver): return len(driver.window_handles) > len(handles_before)
        try:
            WebDriverWait(d, timeout).until(_new_win)
        except Exception:
            return False

        new_handle = None
        for h in d.window_handles:
            if h not in handles_before:
                new_handle = h; break
        if not new_handle:
            new_handle = d.window_handles[-1]
        try:
            d.switch_to.window(new_handle)
        except Exception:
            return False

        # Wait for load
        try:
            WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
        except Exception:
            pass
        time.sleep(0.6)

        # Determine filename
        def _sanitize(n: str) -> str:
            n = (n or "").strip()
            n = _re.sub(r"[\\/:*?\"<>|]+", " ", n)
            n = _re.sub(r"\s+", " ", n).strip()
            return n or "Referral Form"

        if not client_name:
            try:
                body_txt = (d.find_element(By.TAG_NAME, "body").text or "").strip()
                m = _re.search(r"Client\s*:\s*([A-Za-z\-\.'\s]+)", body_txt)
                if m: client_name = m.group(1)
            except Exception:
                pass
        client_name = _sanitize(client_name)
        
        # Check if counselor has IPS in their name (for file naming)
        is_ips_counselor = False
        if counselor_name and "ips" in str(counselor_name).lower():
            is_ips_counselor = True
            self.log(f"[IPS] Counselor '{counselor_name}' has IPS - will append to filename")
        
        if client_name:
            if urgent:
                if is_ips_counselor:
                    filename = f"URGENT IPS {client_name} Referral Form.pdf"
                else:
                    filename = f"URGENT {client_name} Referral Form.pdf"
            else:
                if is_ips_counselor:
                    filename = f"IPS {client_name} Referral Form.pdf"
                else:
                    filename = f"{client_name} Referral Form.pdf"
        else:
            if is_ips_counselor:
                filename = "IPS Referral Form.pdf"
            else:
                filename = "Referral Form.pdf"


        # Capture PDF via Chrome DevTools
        try:
            pdf = d.execute_cdp_cmd("Page.printToPDF", {
                "printBackground": True,
                "preferCSSPageSize": True,
                "landscape": False
            })
            data = pdf.get("data","")
            if not data: raise Exception("No PDF data")
            pdf_bytes = base64.b64decode(data)
        except Exception:
            # Fallback: attempt window.print() then CDP again
            try:
                d.execute_script("window.print && window.print();")
                time.sleep(1.2)
                pdf = d.execute_cdp_cmd("Page.printToPDF", {"printBackground": True})
                import base64 as _b64
                pdf_bytes = _b64.b64decode(pdf.get("data",""))
            except Exception:
                try: d.switch_to.window(main)
                except Exception: pass
                return False

        # Save into "Referral Form Bot Output" on the employee's desktop
        try:
            # Get the user's desktop path
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            # Fallback to common desktop locations if the above fails
            if not os.path.exists(desktop_path):
                desktop_path = os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop")
            if not os.path.exists(desktop_path):
                desktop_path = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")
        except Exception:
            # Final fallback to current working directory
            desktop_path = os.getcwd()
        out_dir = os.path.join(desktop_path, "Referral Form Bot Output")
        try: os.makedirs(out_dir, exist_ok=True)
        except Exception: pass
        
        # Log where the file is being saved so employees can see it
        self.log(f"[OUTPUT] Saving PDF to: {out_dir}")
        
        out_path = os.path.join(out_dir, filename)
        try:
            with open(out_path, "wb") as f: f.write(pdf_bytes)
            self.log(f"[SUCCESS] PDF saved: {filename}")
        except Exception:
            out_path = os.path.join(out_dir, "Referral Form.pdf")
            with open(out_path, "wb") as f: f.write(pdf_bytes)
            self.log(f"[SUCCESS] PDF saved: Referral Form.pdf")

        # Close report and return
        try:
            d.close()
            d.switch_to.window(main)
        except Exception:
            pass
        return True

    def click_top_search_nav(self, timeout: int = 20) -> bool:
        """
        Click the top navigation 'search' button (id='navSearch') to return to the master Search screen.
        Keeps the browser in the content frame and waits briefly for the page to refresh.
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception:
            return False

        d = self.driver

        # Be in content frame
        try:
            d.switch_to.default_content()
        except Exception:
            pass
        try:
            WebDriverWait(d, 6).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
        except Exception:
            # Some tenants render directly in the top document
            pass

        try:
            btn = WebDriverWait(d, timeout).until(EC.element_to_be_clickable((By.ID, "navSearch")))
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
            except Exception:
                pass
            try:
                btn.click()
            except Exception:
                d.execute_script("arguments[0].click();", btn)
        except Exception:
            return False

        # Give the AJAX navigation a short moment to complete
        try:
            WebDriverWait(d, 8).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
        except Exception:
            pass
        time.sleep(0.8)
        return True
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IA Only Referral Bot - Version 3.1.0, Last Updated 12/04/2025"); self.geometry("1040x820")
        self._build_ui()
        self._stop = threading.Event()
        self.worker = None

    def _card(self, parent, title):
        frm = ttk.Frame(parent); frm.pack(fill='x', padx=12, pady=8)
        cap = ttk.Label(frm, text=title, foreground=MAROON, font=('Segoe UI', 12, 'bold'))
        cap.pack(anchor='w', padx=8, pady=(8,4))
        inner = ttk.Frame(frm); inner.pack(fill='x', padx=8, pady=(0,8))
        return inner

    def _build_ui(self):
        headerfrm, headerbanner = _title_banner(self)
        # Scrollable content area
        container = ttk.Frame(self); container.pack(fill='both', expand=True)
        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        vscroll = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vscroll.set)
        vscroll.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        self.content = ttk.Frame(canvas)
        canvas.create_window((0,0), window=self.content, anchor="nw")
        def _on_content_config(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        self.content.bind("<Configure>", _on_content_config)
        # Mousewheel
        def _wheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _wheel)

        cred = self._card(self.content, "Penelope Credentials")
        self.url_var  = tk.StringVar(value=PN_DEFAULT_URL)
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        ttk.Label(cred, text="URL:").grid(row=0, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(cred, textvariable=self.url_var, width=64).grid(row=0, column=1, sticky='w')
        ttk.Label(cred, text="User:").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(cred, textvariable=self.user_var, width=30).grid(row=1, column=1, sticky='w')
        ttk.Label(cred, text="Pass:").grid(row=2, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(cred, textvariable=self.pass_var, show='•', width=30).grid(row=2, column=1, sticky='w')

        src = self._card(self.content, "Data Source")
        self.mode = tk.StringVar(value="local")
        r1 = ttk.Radiobutton(src, text="Local CSV/XLSX", variable=self.mode, value="local", command=self._on_mode_change)
        r2 = ttk.Radiobutton(src, text="OneDrive/SharePoint by URL", variable=self.mode, value="onedrive", command=self._on_mode_change)
        r1.grid(row=0, column=0, sticky='w'); r2.grid(row=0, column=1, sticky='w', padx=18)

        self.od = self._card(self.content, "OneDrive / SharePoint Excel")
        self.od_url     = tk.StringVar()
        self.row_from   = tk.StringVar(value='2')
        self.row_to     = tk.StringVar(value='50')
        self.use_profile= tk.BooleanVar(value=False)
        self.profile_dir= tk.StringVar(value=self._guess_chrome_profile_dir())
        ttk.Label(self.od, text="File URL:").grid(row=0, column=0, sticky='e', padx=6)
        self.od_url_e = ttk.Entry(self.od, textvariable=self.od_url, width=70); self.od_url_e.grid(row=0, column=1, sticky='w', columnspan=2)
        ttk.Label(self.od, text="Rows: From").grid(row=1, column=0, sticky='e', padx=6)
        self.row_from_e = ttk.Entry(self.od, textvariable=self.row_from, width=6); self.row_from_e.grid(row=1, column=1, sticky='w')
        ttk.Label(self.od, text="Through").grid(row=1, column=2, sticky='e', padx=6)
        self.row_to_e = ttk.Entry(self.od, textvariable=self.row_to, width=6); self.row_to_e.grid(row=1, column=3, sticky='w')
        self.use_profile_c = ttk.Checkbutton(self.od, text="Use my Chrome profile for OneDrive auth", variable=self.use_profile)
        self.use_profile_c.grid(row=2, column=1, sticky='w', pady=(6,0))
        ttk.Label(self.od, text="Chrome profile folder:").grid(row=3, column=0, sticky='e', padx=6)
        self.profile_dir_e = ttk.Entry(self.od, textvariable=self.profile_dir, width=70); self.profile_dir_e.grid(row=3, column=1, sticky='w')
        self.profile_dir_b = ttk.Button(self.od, text="Browse…", command=self._browse_profile); self.profile_dir_b.grid(row=3, column=2, sticky='w', padx=6)

        self.lf = self._card(self.content, "Local CSV / XLSX")
        self.local_path = tk.StringVar()
        self.local_row_from = tk.StringVar(value='2')
        self.local_row_to   = tk.StringVar(value='50')
        self.local_path_e = ttk.Entry(self.lf, textvariable=self.local_path, width=70); self.local_path_e.grid(row=0, column=0, sticky='w')
        self.local_path_b = ttk.Button(self.lf, text="Browse…", command=self._browse_local); self.local_path_b.grid(row=0, column=1, sticky='w', padx=6)
        ttk.Label(self.lf, text="Rows: From").grid(row=1, column=0, sticky='e', padx=6)
        self.local_row_from_e = ttk.Entry(self.lf, textvariable=self.local_row_from, width=6); self.local_row_from_e.grid(row=1, column=1, sticky='w')
        ttk.Label(self.lf, text="Through").grid(row=1, column=2, sticky='e', padx=6)
        self.local_row_to_e = ttk.Entry(self.lf, textvariable=self.local_row_to, width=6); self.local_row_to_e.grid(row=1, column=3, sticky='w')

        mp = self._card(self.content, "Column Mapping — REQUIRED")
        self.col_sel = tk.StringVar(value="A")  # default for your use
        ttk.Label(mp, text="Column (header OR letter like A):", foreground=MAROON)\
            .grid(row=0, column=0, sticky='e', padx=6, pady=6)
        ttk.Entry(mp, textvariable=self.col_sel, width=32).grid(row=0, column=1, sticky='w', pady=6)

        # TherapyNotes Credentials for Uploaders
        tn_cred = self._card(self.content, "TherapyNotes Credentials (for Dual Uploader)")
        ttk.Label(tn_cred, text="TN Username:", foreground=MAROON).grid(row=0, column=0, sticky='e', padx=6, pady=4)
        self.tn_user_var = tk.StringVar()
        ttk.Entry(tn_cred, textvariable=self.tn_user_var, width=30).grid(row=0, column=1, sticky='w', padx=6, pady=4)
        ttk.Label(tn_cred, text="TN Password:", foreground=MAROON).grid(row=0, column=2, sticky='e', padx=6, pady=4)
        self.tn_pass_var = tk.StringVar()
        ttk.Entry(tn_cred, textvariable=self.tn_pass_var, show='•', width=30).grid(row=0, column=3, sticky='w', padx=6, pady=4)

        ctr = self._card(self.content, "Controls")
        ttk.Button(ctr, text="Start", command=self.start).grid(row=0, column=0, padx=6)
        ttk.Button(ctr, text="Stop", command=self.stop).grid(row=0, column=1, padx=6)
        ttk.Button(ctr, text="Copy Log", command=self.copy_log).grid(row=0, column=2, padx=6)
        
        # Uploader Integration Checkboxes
        uploader_frame = ttk.Frame(ctr)
        uploader_frame.grid(row=1, column=0, columnspan=5, sticky='ew', padx=6, pady=8)
        
        # Main uploader frame with border
        uploader_border = ttk.Frame(uploader_frame, relief='solid', borderwidth=2)
        uploader_border.pack(fill='x', padx=4, pady=4)
        
        # Main checkbox: Run Base Uploader
        self.run_base_uploader_after = tk.BooleanVar(value=False)
        base_cb = ttk.Checkbutton(
            uploader_border,
            text="📤 Run Dual Uploader (Base/ISWS) after IA Referral completes",
            variable=self.run_base_uploader_after,
            command=self._toggle_ips_checkbox
        )
        base_cb.pack(fill='x', padx=8, pady=6)
        
        # Sub-checkbox: Also run IPS Uploader (indented)
        ips_sub = ttk.Frame(uploader_border)
        ips_sub.pack(fill='x', padx=8, pady=(0, 6))
        ttk.Label(ips_sub, text="    ").pack(side='left')  # Indent
        self.run_ips_uploader_after = tk.BooleanVar(value=False)
        self.ips_cb = ttk.Checkbutton(
            ips_sub,
            text="🏥 Also run IPS Uploader after Base",
            variable=self.run_ips_uploader_after,
            state='disabled'
        )
        self.ips_cb.pack(side='left')
        
        # Description
        ttk.Label(
            uploader_border,
            text="✓ PDFs auto-loaded from Desktop/Referral Form Bot Output/",
            foreground='#0066cc',
            font=('Segoe UI', 9, 'italic')
        ).pack(fill='x', padx=8, pady=(0, 6))
        
        logfrm = ttk.Frame(self.content); logfrm.pack(fill='both', expand=True, padx=12, pady=8)
        self.log_widget = scrolledtext.ScrolledText(logfrm, height=1, bg=LOG_BG, fg=LOG_FG)
        self.log_widget.pack(fill='x', expand=False)
        self.logger = UILog(self.log_widget)

        self._on_mode_change()

    def _set_onedrive_controls_enabled(self, enabled: bool):
        state = ("normal" if enabled else "disabled")
        for w in [self.od_url_e, self.row_from_e, self.row_to_e, self.use_profile_c, self.profile_dir_e, self.profile_dir_b]:
            try: w.config(state=state)
            except Exception: pass

    def _set_local_controls_enabled(self, enabled: bool):
        state = ("normal" if enabled else "disabled")
        for w in [self.local_path_e, self.local_path_b, self.local_row_from_e, self.local_row_to_e]:
            try: w.config(state=state)
            except Exception: pass

    def _on_mode_change(self):
        mode = self.mode.get()
        self._set_onedrive_controls_enabled(mode == "onedrive")
        self._set_local_controls_enabled(mode == "local")

    def _guess_chrome_profile_dir(self) -> str:
        home = os.path.expanduser("~")
        if sys.platform.startswith("win"):
            p = os.path.join(home, "AppData", "Local", "Google", "Chrome", "User Data")
        elif sys.platform == "darwin":
            p = os.path.join(home, "Library", "Application Support", "Google", "Chrome")
        else:
            p = os.path.join(home, ".config", "google-chrome")
        return p if os.path.isdir(p) else ""

    def _browse_profile(self):
        p = filedialog.askdirectory(title="Select your Chrome profile folder")
        if p: self.profile_dir.set(p)

    def _browse_local(self):
        p = filedialog.askopenfilename(title="Select CSV/XLSX", filetypes=[("Spreadsheets","*.csv;*.xlsx;*.xls")])
        if p: self.local_path.set(p)
    
    def _toggle_ips_checkbox(self):
        """Enable/disable IPS uploader checkbox based on base uploader checkbox"""
        if self.run_base_uploader_after.get():
            self.ips_cb.config(state='normal')
        else:
            self.ips_cb.config(state='disabled')
            self.run_ips_uploader_after.set(False)

    def log(self, msg: str): self.logger.write(_ts() + msg)

    def start(self):
        if getattr(self, "worker", None) and self.worker.is_alive(): return
        self._stop = threading.Event()
        self.worker = threading.Thread(target=self._run, daemon=True); self.worker.start()

    def stop(self):
        try: self._stop.set()
        except Exception: pass

    def copy_log(self):
        try:
            txt = self.log_widget.get("1.0","end-1c")
            self.clipboard_clear()
            self.clipboard_append(txt)
            self.logger.write("[UI] Log copied to clipboard.")
        except Exception as e:
            self.logger.write(f"[UI][ERR] Copy failed: {e}")

    def launch_uploader_bridge(self):
        """
        Non-blocking launcher for the Dual-Tab IPS IA Referral Form Uploader.
        Tries .exe first (Windows), then the dual-tab Python script.
        Never raises; logs status to the UI log area.
        """
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            base_dir = os.getcwd()

        exe_path = os.path.join(base_dir, "IPS_IA_Referral_Form_Uploader_Dual_Tab.exe")
        py_path  = os.path.join(base_dir, "IPS_IA_Referral_Form_Uploader_Dual_Tab.py")

        try:
            # Prefer a packaged .exe on Windows
            if os.name == "nt" and os.path.isfile(exe_path):
                try:
                    os.startfile(exe_path)  # type: ignore[attr-defined]
                    self.log("[BRIDGE] Launched IPS_IA_Referral_Form_Uploader_Dual_Tab.exe")
                    return
                except Exception as e:
                    self.log(f"[BRIDGE][WARN] Could not open .exe: {e}")

            # Fallback: launch the dual-tab Python script
            if os.path.isfile(py_path):
                import subprocess
                subprocess.Popen([sys.executable, py_path], cwd=base_dir)
                self.log("[BRIDGE] Launched IPS IA Referral Form Uploader (Dual-Tab)")
                return

            # Nothing found
            self.log("[BRIDGE][INFO] Dual-Tab Uploader not found. "
                     "Place IPS_IA_Referral_Form_Uploader_Dual_Tab.py in the same folder as this bot.")
        except Exception as e:
            self.log(f"[BRIDGE][ERR] Failed to launch uploader: {e}")

    def _run(self):
        try:
            # Build PN client (only attach profile in OneDrive mode)
            auth = PNAuth(self.url_var.get().strip(),
                          self.user_var.get().strip(),
                          self.pass_var.get().strip())

            # No profile for local CSV/XLSX; profile is only used in OneDrive mode
            chrome_profile_dir = None

            pn = PNClient(auth, log=self.log)
            pn.start(chrome_profile_dir=chrome_profile_dir)

            if not pn.login():
                self.log("[ERR] Login unsuccessful; continuing to keep browser open.")
            else:
                self.log("[OK] Logged in.")
                pn.click_toolbar_search_with_wait(timeout=25)

            # Load rows
            mode = "local"
            col_sel = self.col_sel.get().strip()
            self.log(f"[DATA] Mode: {mode} | Column selector: '{_normalize_col_token(col_sel)}'")

            rows: List[Dict] = []
            lcl = LocalSlice(
                file_path=self.local_path.get().strip(),
                row_from=int(self.local_row_from.get() or 2),
                row_to=int(self.local_row_to.get() or 2),
                col_selector=col_sel
            )
            rows = lcl.load(self.log)

            if not rows:
                self.log("[DATA][ERR] No rows parsed. Opening Search UI for inspection.")
                pn.go_to_search()
                return

            # Go to Search (robust direct nav)
            if pn.go_to_search():
                self.log("[NAV] Search page opened.")
            else:
                self.log("[NAV][WARN] Could not open Search page; continuing anyway.")

            # Process rows
            for idx, rec in enumerate(rows, start=1):
                if self._stop.is_set(): break
                
                try:  # Ensure we always return to Search menu
                    indiv_id = str(rec.get("_Bot_ID") or "").strip()
                    if not indiv_id:
                        self.log(f"[SKIP] Row {idx}: empty ID in selected column.")
                        continue

                    self.log(f"[RUN] Row {idx}: searching Individual ID = {indiv_id}")
                    if not pn.enter_individual_id_and_go(indiv_id):
                        self.log("[WARN] Could not enter ID/Go. Continuing.")
                        continue

                    # Click the first (or name-matched) result link
                    first_name = str(rec.get("First Name") or rec.get("First") or rec.get("FName") or rec.get("Given") or "").strip()
                    last_name  = str(rec.get("Last Name")  or rec.get("Last")  or rec.get("LName") or rec.get("Surname") or "").strip()
                    if not pn.click_first_result_name(first_name=first_name or None, last_name=last_name or None):
                        self.log("[WARN] Could not click a patient name in results. Continuing.")
                        continue

                    self.log("[OK] Opened client profile. (Ready for referral step.)")

                    # Navigate to Case Information: click open "{LastName} Case" (skip Closed)
                    last_name_hint = str(rec.get("Last Name") or rec.get("Last") or rec.get("LName") or rec.get("Surname") or "").strip() or None
                    if pn.click_open_case_link(last_name_hint=last_name_hint):
                        self.log("[OK] Opened the Case File page via '{LastName} Case'.")
                        # Open "Referral Form" via Documents > Select Document
                        if pn.open_referral_document():
                            self.log("[OK] Opened Referral Form wizard popup.")
                            if pn.complete_referral_popup_and_finish():
                                self.log("[OK] Referral form created & saved. Popup closed.")
                                # Print & save the created Referral Form as PDF (added; prior logic untouched)
                                try:
                                    _first = str(rec.get('First Name') or rec.get('First') or '').strip()
                                    _last  = str(rec.get('Last Name') or rec.get('Last') or '').strip()
                                    _client_name = f"{_first} {_last}".strip()
                                except Exception:
                                    _client_name = None
                                
                                # Get counselor name for IPS file naming
                                _counselor_name = str(rec.get('Therapist Name') or rec.get('Counselor') or '').strip()
                                is_urgent = str(rec.get("Urgent") or "").strip().lower() in ("true", "1", "yes")
                                
                                if pn.click_print_and_save_pdf(client_name=_client_name, urgent=is_urgent, counselor_name=_counselor_name):
                                    self.log(f"[OK] Printed & saved PDF for {'URGENT ' if is_urgent else ''}{_client_name or 'client'}.")
                                else:
                                    self.log("[WARN] Could not print/save the Referral Form PDF.")

                            else:
                                self.log("[WARN] Could not complete Referral Form popup.")

                        else:
                            self.log("[WARN] Could not open Referral Form from Documents bucket. Continuing.")

                    else:
                        self.log("[WARN] No open '{LastName} Case' link found (or click failed). Continuing.")
                    # break  # uncomment to stop after first success
                finally:
                    # ALWAYS return to Search menu after each row (success or failure)
                    if pn.click_top_search_nav():
                        self.log('[OK] Back at Search menu. Proceeding to next row.')
                    else:
                        self.log('[WARN] Could not navigate back to Search menu; will attempt to continue.')

            self.log("[DONE] Finished run. Browser left open.")
            
            # Check if uploaders should run after IA referral completes
            if self.run_base_uploader_after.get():
                self.log("[UPLOADER] Launching Dual Uploader (Base) after IA Referral completion...")
                self._launch_uploaders_after_completion()
            else:
                self.log("[UPLOADER] Dual Uploader launch skipped (checkbox not selected)")
                
        except Exception as e:
            self.log(f"[FATAL] {e}")
            self.log(traceback.format_exc())
    
    def _launch_uploaders_after_completion(self):
        """Launch Base and optionally IPS uploaders after IA referral completes"""
        try:
            import subprocess
            import sys
            import os
            
            # PDF folder is on Desktop
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            pdf_folder = os.path.join(desktop, "Referral Form Bot Output")
            
            if not os.path.exists(pdf_folder):
                self.log(f"[UPLOADER][ERROR] PDF folder not found: {pdf_folder}")
                self.log(f"[UPLOADER][ERROR] Expected folder to be created by this bot's PDF generation")
                return
            
            self.log(f"[UPLOADER] ✓ PDF folder found: {pdf_folder}")
            
            # Get dual uploader path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            dual_uploader_path = os.path.join(current_dir, "IPS_IA_Referral_Form_Uploader_Dual_Tab.py")
            
            if not os.path.exists(dual_uploader_path):
                self.log(f"[UPLOADER][ERROR] Dual uploader not found at: {dual_uploader_path}")
                return
            
            # Launch Base Uploader
            self.log("[UPLOADER-BASE] Launching Base uploader...")
            cmd_args_base = [
                sys.executable,
                dual_uploader_path,
                "--mode", "base",
                "--csv-file", self.local_path.get(),
                "--pdf-folder", pdf_folder,
                "--tn-username", self.tn_user_var.get(),
                "--tn-password", self.tn_pass_var.get(),
                "--auto-run"
            ]
            
            self.log(f"[UPLOADER-BASE] CSV: {self.local_path.get()}")
            self.log(f"[UPLOADER-BASE] PDFs: {pdf_folder}")
            
            process_base = subprocess.Popen(
                cmd_args_base,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            time.sleep(2)
            
            if process_base.poll() is None:
                self.log(f"[UPLOADER-BASE] ✓ Base uploader launched (PID: {process_base.pid})")
                self.log("[UPLOADER-BASE] Waiting for Base uploader to complete...")
                process_base.wait()
                self.log(f"[UPLOADER-BASE] ✓ Base uploader completed (exit code: {process_base.returncode})")
            else:
                self.log(f"[UPLOADER-BASE][ERROR] Base uploader failed to start")
                return
            
            # Launch IPS Uploader if checkbox is checked
            if self.run_ips_uploader_after.get():
                self.log("[UPLOADER-IPS] Launching IPS uploader...")
                cmd_args_ips = [
                    sys.executable,
                    dual_uploader_path,
                    "--mode", "ips",
                    "--csv-file", self.local_path.get(),
                    "--pdf-folder", pdf_folder,
                    "--tn-username", self.tn_user_var.get(),
                    "--tn-password", self.tn_pass_var.get(),
                    "--auto-run"
                ]
                
                self.log(f"[UPLOADER-IPS] CSV: {self.local_path.get()}")
                self.log(f"[UPLOADER-IPS] PDFs: {pdf_folder}")
                
                process_ips = subprocess.Popen(
                    cmd_args_ips,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
                
                time.sleep(2)
                
                if process_ips.poll() is None:
                    self.log(f"[UPLOADER-IPS] ✓ IPS uploader launched (PID: {process_ips.pid})")
                    self.log("[UPLOADER-IPS] Waiting for IPS uploader to complete...")
                    process_ips.wait()
                    self.log(f"[UPLOADER-IPS] ✓ IPS uploader completed (exit code: {process_ips.returncode})")
                else:
                    self.log(f"[UPLOADER-IPS][ERROR] IPS uploader failed to start")
            else:
                self.log("[UPLOADER-IPS] IPS Uploader skipped (checkbox not selected)")
            
            self.log("[UPLOADER] ✓ All uploader operations complete!")
            
        except Exception as e:
            self.log(f"[UPLOADER][ERROR] Uploader launch failed: {e}")
            import traceback
            self.log(f"[UPLOADER][ERROR] {traceback.format_exc()}")

# ---------------- Command Line Argument Parsing ----------------
def parse_arguments():
    """Parse command line arguments for auto-mode operation"""
    parser = argparse.ArgumentParser(description='Intake & Referral Bot - Auto Mode')
    parser.add_argument('--auto-mode', action='store_true', 
                       help='Run in automatic mode with pre-filled credentials')
    parser.add_argument('--csv-file', type=str, 
                       help='Path to CSV file with client data')
    parser.add_argument('--url', type=str, 
                       help='Penelope login URL')
    parser.add_argument('--username', type=str, 
                       help='Penelope username')
    parser.add_argument('--password', type=str, 
                       help='Penelope password')
    parser.add_argument('--column', type=str, default='A',
                       help='Column containing Individual IDs (default: A)')
    parser.add_argument('--rows', type=str, default='2-50',
                       help='Row range to process (default: 2-50)')
    parser.add_argument('--run-base-uploader', action='store_true',
                       help='Run Base Dual Uploader after IA Referral Bot completes')
    parser.add_argument('--run-ips-uploader', action='store_true',
                       help='Run IPS Dual Uploader after Base Uploader completes')
    parser.add_argument('--tn-username', type=str,
                       help='TherapyNotes username for uploaders')
    parser.add_argument('--tn-password', type=str,
                       help='TherapyNotes password for uploaders')
    
    return parser.parse_args()

# ---------------- Main ----------------
if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Create the app
    app = App()
    
    # If auto-mode is enabled, populate fields and start automatically
    if args.auto_mode:
        # Populate the GUI fields with command line arguments
        if args.csv_file:
            app.local_path.set(args.csv_file)
        if args.url:
            app.url_var.set(args.url)
        if args.username:
            app.user_var.set(args.username)
        if args.password:
            app.pass_var.set(args.password)
        if args.column:
            app.col_sel.set(args.column)
        if args.rows:
            # Parse row range (e.g., "2-50" -> from=2, to=50)
            try:
                if '-' in args.rows:
                    from_row, to_row = args.rows.split('-', 1)
                    app.local_row_from.set(from_row.strip())
                    app.local_row_to.set(to_row.strip())
                else:
                    app.local_row_from.set(args.rows)
                    app.local_row_to.set(args.rows)
            except Exception:
                app.local_row_from.set('2')
                app.local_row_to.set('50')
        
        # Handle dual uploader arguments
        if args.run_base_uploader:
            app.run_base_uploader_after.set(True)
            app.log("[AUTO-MODE] ✅ Base Dual Uploader checkbox enabled")
            
            if args.run_ips_uploader:
                app.run_ips_uploader_after.set(True)
                app.log("[AUTO-MODE] ✅ IPS Dual Uploader checkbox enabled")
            
            # Set TherapyNotes credentials if provided
            if args.tn_username:
                app.tn_user_var.set(args.tn_username)
                app.log("[AUTO-MODE] ✅ TherapyNotes username set")
            if args.tn_password:
                app.tn_pass_var.set(args.tn_password)
                app.log("[AUTO-MODE] ✅ TherapyNotes password set")
        else:
            app.log("[AUTO-MODE] ℹ️  Dual Uploader launch skipped (checkbox not selected)")
        
        # Log the auto-mode startup
        app.log("[AUTO-MODE] Intake & Referral Bot started in auto-mode")
        app.log(f"[AUTO-MODE] CSV File: {args.csv_file}")
        app.log(f"[AUTO-MODE] URL: {args.url}")
        app.log(f"[AUTO-MODE] Username: {args.username}")
        app.log(f"[AUTO-MODE] Column: {args.column}")
        app.log(f"[AUTO-MODE] Rows: {args.rows}")
        app.log("[AUTO-MODE] Starting automatic processing in 3 seconds...")
        
        # Schedule automatic start after a brief delay
        def auto_start():
            app.log("[AUTO-MODE] Starting automatic processing now...")
            app.start()
        
        # Start automatically after 3 seconds
        app.after(3000, auto_start)
    
    # Start the GUI
    app.mainloop()


# ==== Minimal, isolated addition: add a vertical resize handle (Sizegrip) ====
try:
    import tkinter.ttk as ttk
    # Get the toplevel window via the log widget, if present
    tl = None
    try:
        tl = self.log_text.winfo_toplevel()
    except Exception:
        try:
            # fallback: look for a 'root' or 'master' attribute commonly used in this codebase
            tl = self.root if hasattr(self, "root") else (self.master if hasattr(self, "master") else None)
        except Exception:
            tl = None
    if tl is not None:
        try:
            sg = ttk.Sizegrip(tl)
            sg.place(relx=1.0, rely=1.0, anchor="se")
        except Exception:
            pass
        try:
            tl.resizable(True, True)
        except Exception:
            pass
except Exception:
    pass
# ==== End minimal addition ====



# ==== Minimal, isolated addition: ultra-tiny log box at the bottom of the scroll area ====
def __place_tiny_log_at_bottom():
    try:
        import tkinter as tk
        from tkinter.scrolledtext import ScrolledText
        # Try to locate a scrollable "content" frame used by the app.
        candidates = [
            getattr(self, name) for name in (
                "scroll_inner", "scroll_body", "scrollable_frame", "content_frame",
                "main_content", "body", "content", "scroll_frame"
            ) if hasattr(self, name)
        ]
        target_parent = None
        for cand in candidates:
            try:
                # Heuristic: a Frame with many children that's not the header/top bar
                if isinstance(cand, (tk.Frame,)) and len(getattr(cand, "children", {})) >= 1:
                    target_parent = cand
                    break
            except Exception:
                continue

        if target_parent is None:
            return  # can't safely place; abort silently

        # Keep reference to old log, in case other code still holds it
        old_log = getattr(self, "log_text", None)
        if old_log is not None:
            try:
                # make it extremely small and hide it from the fixed header area
                try:
                    old_log.config(height=1)
                except Exception:
                    pass
                try:
                    old_log.pack_forget()
                    old_log.grid_forget()
                except Exception:
                    pass
            except Exception:
                pass

        # Create a new tiny log box in the scrollable area at the *bottom*
        try:
            new_log = ScrolledText(target_parent, height=1, wrap="word")
        except Exception:
            return

        try:
            new_log.configure(state="normal")
            new_log.insert("end", "")
            new_log.see("end")
        except Exception:
            pass

        # Pack at the very bottom of the scrollable content
        try:
            new_log.pack(side="top", fill="x", padx=8, pady=(8, 10))
        except Exception:
            pass

        # Replace self.log_text so existing code writes to the tiny bottom log
        try:
            self.log_text = new_log
        except Exception:
            pass

    except Exception:
        pass

# Schedule after UI build so the frames exist
try:
    # If Tkinter event loop is running, schedule after idle;
    # if not, call immediately (safe no-op if not ready).
    try:
        # Try using a root/toplevel if accessible
        tl = None
        if hasattr(self, "root"):
            tl = self.root
        else:
            tl = self.log_text.winfo_toplevel() if hasattr(self, "log_text") else None
        if tl is not None:
            tl.after(50, __place_tiny_log_at_bottom)
        else:
            __place_tiny_log_at_bottom()
    except Exception:
        __place_tiny_log_at_bottom()
except Exception:
    pass
# ==== End minimal addition ====
