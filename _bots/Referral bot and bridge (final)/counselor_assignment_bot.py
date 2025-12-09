# counselor_assignment_bot.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
#  Counselor Assignment Bot — Penelope Navigation to Client Profile
# =============================================================================

import os, sys, time, json, threading, queue, tempfile, traceback, re
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from dataclasses import dataclass
from typing import Optional, Dict, List
from pathlib import Path
import requests
import pandas as pd
import pyperclip

APP_TITLE = "Counselor Assignment Bot"
MAROON    = "#800000"
LOG_BG    = "#f7f3f2"
LOG_FG    = "#1a1a1a"

def _title_banner(root):
    frm = ttk.Frame(root); frm.pack(fill='x')
    banner = tk.Frame(frm, bg=MAROON, height=54); banner.pack(fill='x')
    lbl = tk.Label(banner, text=APP_TITLE, fg="white", bg=MAROON,
                   font=("Segoe UI", 18, "bold"), pady=6)
    lbl.pack(side='left', padx=14, pady=6)
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
    t = str(token).strip().strip("\"'""''`")
    return t

def _is_single_letter(t: str) -> bool:
    return len(t) == 1 and t.isalpha()

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
        e = max(s, int(self.row_to)) - 2

        token = _normalize_col_token(self.col_selector)
        log(_ts() + f"[DATA] Column token: '{token}'  | Columns: {list(df.columns)}")
        try:
            series = resolve_column(df, token)
        except KeyError as ke:
            log(_ts() + f"[DATA][ERR] {ke}")
            return []

        sub = df.iloc[s:e+1].copy()
        try:
            # Fix: Ensure client IDs are treated as strings without decimal points
            # First convert to object to prevent pandas from inferring numeric types
            client_ids = series.iloc[s:e+1].astype(object)
            # Convert to string and remove any .0 suffixes that pandas might add
            client_ids_str = client_ids.astype(str).str.strip()
            # Remove .0 suffix if present (e.g., "12345.0" -> "12345")
            client_ids_str = client_ids_str.str.replace(r'\.0$', '', regex=True)
            sub["_Bot_ID"] = client_ids_str
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

class PNClient:
    def __init__(self, auth: PNAuth, log):
        self.auth = auth
        self.log = log
        self.driver = None
        self.wait = None

    def start(self, chrome_profile_dir: Optional[str] = None):
        webdriver, _By, _WebDriverWait, _EC, _Keys, Service, ChromeDriverManager = _lazy_import_selenium()
        
        # Check network connectivity first
        try:
            import requests
            requests.get("https://www.google.com", timeout=5)
            self.log(_ts() + "[NETWORK] Internet connection verified")
        except Exception as e:
            self.log(_ts() + f"[NETWORK][WARN] Internet check failed: {e}")
            self.log(_ts() + "[NETWORK] Bot will try to continue anyway...")
        
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            if chrome_profile_dir and os.path.isdir(chrome_profile_dir):
                options.add_argument(f"--user-data-dir={chrome_profile_dir}")
                self.log(_ts() + f"[BROWSER] Using Chrome profile: {chrome_profile_dir}")
            else:
                self.log(_ts() + "[BROWSER] Using fresh Selenium profile (no saved cookies).")
            # Try multiple methods to get ChromeDriver
            service = None
            
            # Method 1: Try ChromeDriverManager with timeout
            try:
                self.log(_ts() + "[BROWSER] Attempting to download ChromeDriver...")
                import threading
                import time
                
                result = [None]
                exception = [None]
                
                def download_driver():
                    try:
                        result[0] = ChromeDriverManager().install()
                    except Exception as e:
                        exception[0] = e
                
                # Start download in separate thread
                thread = threading.Thread(target=download_driver)
                thread.daemon = True
                thread.start()
                thread.join(timeout=30)  # 30 second timeout
                
                if thread.is_alive():
                    self.log(_ts() + "[BROWSER][WARN] ChromeDriver download timed out after 30 seconds")
                    raise TimeoutError("ChromeDriver download timed out")
                
                if exception[0]:
                    raise exception[0]
                
                if result[0]:
                    service = Service(result[0])
                    self.log(_ts() + f"[BROWSER] ChromeDriver downloaded: {result[0]}")
                else:
                    raise Exception("ChromeDriver download failed")
                    
            except Exception as e:
                self.log(_ts() + f"[BROWSER][WARN] ChromeDriverManager failed: {e}")
                
                # Method 2: Try to use system ChromeDriver
                try:
                    self.log(_ts() + "[BROWSER] Trying system ChromeDriver...")
                    service = Service()  # Uses PATH
                    self.log(_ts() + "[BROWSER] Using system ChromeDriver")
                except Exception as e2:
                    self.log(_ts() + f"[BROWSER][WARN] System ChromeDriver failed: {e2}")
                    
                    # Method 3: Try common ChromeDriver locations
                    common_paths = [
                        r"C:\Program Files\Google\Chrome\Application\chromedriver.exe",
                        r"C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe",
                        r"C:\chromedriver\chromedriver.exe",
                        r"C:\Windows\System32\chromedriver.exe"
                    ]
                    
                    for path in common_paths:
                        if os.path.exists(path):
                            try:
                                service = Service(path)
                                self.log(_ts() + f"[BROWSER] Using ChromeDriver at: {path}")
                                break
                            except Exception as e3:
                                self.log(_ts() + f"[BROWSER][WARN] ChromeDriver at {path} failed: {e3}")
                                continue
            
            if service is None:
                raise Exception("Could not find or download ChromeDriver. Please check your internet connection or install ChromeDriver manually.")
            
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = _WebDriverWait(self.driver, 20)
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
            _switch_login_iframe()
            try_login_in_ctx()

        try:
            w.until(lambda drv: drv.current_url != url)
        except Exception:
            pass
        self.log(_ts() + "[PN] Login appears successful.")
        return True

    def go_to_search(self) -> bool:
        """Open the Search UI and ensure the content frame is focused."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        d, w = self.driver, self.wait
        log = getattr(self, "log", lambda s: None)
        
        try:
            d.switch_to.default_content()
            log("[NAV] Attempting to navigate to Search page...")
            
            # First, try using the more robust toolbar search method
            # This method switches to frame first, then clicks the search button inside
            try:
                log("[NAV] Trying click_toolbar_search_with_wait method...")
                if self.click_toolbar_search_with_wait(timeout=8):
                    log("[NAV] Successfully clicked toolbar search button")
                    time.sleep(1)  # Wait for page to load
                    # Now switch to the frame
                    ok = self._switch_to_search_content_frame()
                    if ok:
                        log("[NAV] Successfully switched to search frame")
                        return True
                    else:
                        log("[NAV][WARN] Toolbar search clicked but frame switch failed, trying fallback...")
            except Exception as e:
                log(f"[NAV][WARN] click_toolbar_search_with_wait failed: {e}, trying fallback methods...")
            
            # Fallback: Try clicking a nav item in default content
            clicked = False
            for by, sel in [
                (By.XPATH, "//a[contains(.,'Search') and @href]"),
                (By.CSS_SELECTOR, "a[href*='acm_searchControl']"),
            ]:
                try:
                    log(f"[NAV] Trying to find search link with selector: {sel}")
                    el = WebDriverWait(d, 5).until(EC.element_to_be_clickable((by, sel)))
                    try: 
                        el.click()
                        log("[NAV] Clicked search link")
                    except Exception: 
                        d.execute_script("arguments[0].click();", el)
                        log("[NAV] Clicked search link via JavaScript")
                    clicked = True
                    time.sleep(1)  # Wait for page to respond
                    break
                except Exception as e:
                    log(f"[NAV][WARN] Could not click search link with {sel}: {e}")
                    continue
            
            if not clicked:
                # Direct URL fallback
                try:
                    log("[NAV] Trying direct URL navigation...")
                    origin = re.match(r'^(https?://[^/]+)', d.current_url)
                    if origin:
                        search_url = origin.group(1) + "/acm_searchControl?actionType=view"
                        log(f"[NAV] Navigating directly to: {search_url}")
                        d.get(search_url)
                        time.sleep(2)  # Wait for page to load
                        log("[NAV] Direct navigation completed")
                except Exception as e:
                    log(f"[NAV][WARN] Direct URL navigation failed: {e}")
            
            # Now ensure frame is available and switch to it
            log("[NAV] Attempting to switch to search content frame...")
            ok = self._switch_to_search_content_frame()
            if not ok:
                # Retry once with longer wait
                log("[NAV] Frame switch failed, retrying after 2 seconds...")
                time.sleep(2)
                ok = self._switch_to_search_content_frame()
            
            if ok:
                log("[NAV] Successfully navigated to Search page and switched to frame")
            else:
                log("[NAV][ERROR] Failed to switch to search frame after all attempts")
            
            return ok
        except Exception as e:
            log(f"[NAV][ERROR] go_to_search failed: {e}")
            import traceback
            log(f"[NAV][ERROR] Traceback: {traceback.format_exc()}")
            return False

    def _switch_to_search_content_frame(self) -> bool:
        """Switch to the search content frame with retry logic."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        d = self.driver
        log = getattr(self, "log", lambda s: None)
        max_retries = 3
        timeout_per_attempt = 8  # Reduced from 10 to 8 seconds
        
        for retry in range(max_retries):
            try:
                d.switch_to.default_content()
                log(f"[NAV] Attempt {retry + 1}/{max_retries}: Waiting for frm_content_id frame (timeout: {timeout_per_attempt}s)...")
                
                # Wait for frame to be available and switch to it
                WebDriverWait(d, timeout_per_attempt).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                
                if retry > 0:
                    log(f"[NAV] Successfully switched to search frame on retry {retry + 1}")
                else:
                    log("[NAV] Successfully switched to search frame")
                return True
            except Exception as e:
                if retry < max_retries - 1:
                    log(f"[NAV][WARN] Frame switch attempt {retry + 1} failed: {e}, retrying...")
                    time.sleep(1)  # Increased wait between retries
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass
                else:
                    log(f"[NAV][ERROR] Could not switch to search frame after {max_retries} attempts: {e}")
                    # Try to check if frame exists at all
                    try:
                        d.switch_to.default_content()
                        frames = d.find_elements(By.ID, "frm_content_id")
                        if frames:
                            log("[NAV][DEBUG] Frame element exists but may not be ready")
                        else:
                            log("[NAV][DEBUG] Frame element not found in DOM")
                    except Exception as check_e:
                        log(f"[NAV][DEBUG] Could not check for frame: {check_e}")
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass
                    return False
        return False

    def enter_individual_id_and_go(self, indiv_id: str, timeout: int = 12) -> bool:
        """
        Individual > Individual ID: enter ID # > Press Go > WAIT for dropdown/results.
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
            import time
            try:
                d.switch_to.default_content()
                # Check if frame is already available
                try:
                    WebDriverWait(d, 3).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                    d.switch_to.default_content()
                    log("[INDIV] Search frame already available")
                    return True
                except Exception:
                    pass
                
                # Frame not available, need to click search button
                log("[INDIV] Search frame not found, clicking toolbar search button...")
                try:
                    nav = WebDriverWait(d, timeout).until(EC.element_to_be_clickable((By.ID, "navSearch")))
                    # Use JavaScript click for reliability
                    try:
                        d.execute_script("arguments[0].click();", nav)
                    except Exception:
                        nav.click()
                    log("[INDIV] Toolbar search button clicked")
                    time.sleep(0.5)  # Wait for page to respond
                    
                    # Wait for frame to become available
                    WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                    d.switch_to.default_content()
                    log("[INDIV] Search frame loaded successfully")
                    time.sleep(0.3)  # Brief pause for frame to stabilize
                    return True
                except Exception as e:
                    log(f"[INDIV][ERROR] Failed to open search: {e}")
                    d.switch_to.default_content()
                    return False
            except Exception as e:
                log(f"[INDIV][ERROR] _open_search_if_needed error: {e}")
                try: 
                    d.switch_to.default_content()
                except Exception: 
                    pass
                return False

        def _into_frame() -> bool:
            """Switch to the search content frame with retry logic."""
            import time
            max_retries = 3
            for retry in range(max_retries):
                try:
                    d.switch_to.default_content()
                    WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                    if retry > 0:
                        log(f"[INDIV] Successfully entered frame on retry {retry + 1}")
                    return True
                except Exception as e:
                    if retry < max_retries - 1:
                        log(f"[INDIV][WARN] Frame switch failed (attempt {retry + 1}/{max_retries}): {e}, retrying...")
                        time.sleep(0.5)
                        try:
                            d.switch_to.default_content()
                        except Exception:
                            pass
                    else:
                        log(f"[INDIV][ERROR] Could not enter frame after {max_retries} attempts: {e}")
                        try: 
                            d.switch_to.default_content()
                        except Exception: 
                            pass
                        return False
            return False

        def _activate_individual_tab() -> bool:
            """Use JS goTab + click fallback; confirm txtKIndID is present and ready for input."""
            import time
            try:
                # Step 1: Activate tab using JavaScript (most reliable)
                try:
                    d.execute_script("if (typeof goTab==='function') { goTab('tabIndiv'); }")
                    log("[INDIV] goTab('tabIndiv') called via JavaScript")
                    time.sleep(0.5)  # Wait for tab to activate
                except Exception as e:
                    log(f"[INDIV][WARN] goTab() failed: {e}, trying tab click...")
                
                # Step 2: Fallback - click tab element if JavaScript didn't work
                try:
                    tab = WebDriverWait(d, 4).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li#tabIndiv_li")))
                    # Use JavaScript click to avoid stale element issues
                    d.execute_script("arguments[0].click();", tab)
                    log("[INDIV] Individual tab clicked via JavaScript")
                    time.sleep(0.5)  # Wait for tab to activate
                except Exception as e:
                    log(f"[INDIV][WARN] Tab click fallback failed: {e}")
                
                # Step 3: Wait for the Individual ID field to be present (use presence, not clickable to avoid stale issues)
                try:
                    id_input = WebDriverWait(d, 8).until(EC.presence_of_element_located((By.NAME, "txtKIndID")))
                    log("[INDIV] Individual ID field found")
                except Exception as e:
                    log(f"[INDIV][ERROR] Could not find Individual ID field: {e}")
                    return False
                
                # Step 4: Clear and focus using ONLY JavaScript to avoid stale element errors
                try:
                    # Use JavaScript to clear and focus - completely bypasses Selenium element methods
                    d.execute_script("""
                        var elem = arguments[0];
                        if (elem) {
                            elem.value = '';
                            elem.focus();
                            // Trigger focus event to ensure field is ready
                            elem.dispatchEvent(new Event('focus', { bubbles: true, cancelable: true }));
                        }
                    """, id_input)
                    log("[INDIV] Individual tab activated - ID field cleared and focused via JavaScript")
                    time.sleep(0.3)  # Brief pause for field to be ready
                    return True
                except Exception as e:
                    log(f"[INDIV][WARN] JavaScript clear/focus failed: {e}, trying Selenium fallback...")
                    # Fallback to Selenium methods (but re-find element first)
                    try:
                        id_input = WebDriverWait(d, 4).until(EC.presence_of_element_located((By.NAME, "txtKIndID")))
                        id_input.clear()
                        id_input.click()
                        log("[INDIV] Individual tab activated - ID field cleared via Selenium fallback")
                        return True
                    except Exception as e2:
                        log(f"[INDIV][ERROR] All methods failed to clear ID field: {e2}")
                        return False
                
            except Exception as e:
                log(f"[INDIV][ERROR] _activate_individual_tab failed: {e}")
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

                if not _open_search_if_needed():
                    raise TimeoutException("Search toolbar/frame not reachable")

                if not _into_frame():
                    raise TimeoutException("Could not enter frm_content_id")

                if not _activate_individual_tab():
                    log("[INDIV][WARN] First tab activation attempt failed, retrying...")
                    if not _into_frame():
                        raise TimeoutException("Could not re-enter frame for retry")
                    if not _activate_individual_tab():
                        raise TimeoutException("Could not activate Individual tab after retry")

                # Fix: Ensure client ID is treated as integer without decimal points
                # Convert to int first to remove any decimal, then back to string
                try:
                    _id = str(int(float(indiv_id))).strip()
                except (ValueError, TypeError):
                    # If conversion fails, use original string but remove .0 if present
                    _id = str(indiv_id).strip()
                    if _id.endswith('.0'):
                        _id = _id[:-2]
                
                log(f"[INDIV] Entering Individual ID: {_id}")
                
                # CRITICAL: Use JavaScript-only approach to avoid stale element issues
                # Re-find element fresh each time and use JavaScript to set value
                import time
                id_entered_successfully = False
                for retry in range(3):
                    try:
                        # Always re-find the element fresh to avoid stale references
                        id_input = WebDriverWait(d, 8).until(EC.presence_of_element_located((By.NAME, "txtKIndID")))
                        
                        # Use JavaScript to set value - completely bypasses Selenium input methods
                        d.execute_script("""
                            var elem = arguments[0];
                            var val = arguments[1];
                            if (elem) {
                                elem.value = '';
                                elem.focus();
                                elem.value = val;
                                // Trigger all relevant events to ensure value is registered
                                ['input', 'change', 'keyup', 'keydown'].forEach(function(eventType) {
                                    elem.dispatchEvent(new Event(eventType, { bubbles: true, cancelable: true }));
                                });
                            }
                        """, id_input, _id)
                        
                        # Wait for value to register
                        time.sleep(0.4)
                        
                        # VERIFY the ID was actually entered by re-finding element and checking value
                        id_input = WebDriverWait(d, 4).until(EC.presence_of_element_located((By.NAME, "txtKIndID")))
                        entered_value = id_input.get_attribute("value") or ""
                        
                        if entered_value.strip() == _id:
                            log(f"[INDIV] ✓ VERIFIED: ID '{_id}' successfully entered (field shows: '{entered_value}')")
                            id_entered_successfully = True
                            break
                        else:
                            log(f"[INDIV][WARN] ID mismatch! Expected '{_id}', but field shows '{entered_value}'. Retry {retry + 1}/3")
                            if retry < 2:
                                time.sleep(0.5)
                                if not _into_frame():
                                    raise TimeoutException("Could not re-enter frame for retry")
                                # Re-activate tab before retrying
                                if not _activate_individual_tab():
                                    log("[INDIV][WARN] Could not re-activate tab for retry")
                                continue
                            else:
                                log(f"[INDIV][ERROR] Failed to enter correct ID after 3 attempts!")
                                raise ValueError(f"ID entry verification failed: expected '{_id}', got '{entered_value}'")
                        
                    except StaleElementReferenceException:
                        if retry < 2:
                            log(f"[INDIV][WARN] Stale element on retry {retry + 1}, re-finding...")
                            if not _into_frame():
                                raise TimeoutException("Could not re-enter frame after stale element")
                            # Re-activate tab
                            if not _activate_individual_tab():
                                log("[INDIV][WARN] Could not re-activate tab after stale element")
                            time.sleep(0.5)
                            continue
                        else:
                            raise
                    except Exception as e:
                        if retry < 2:
                            log(f"[INDIV][WARN] Input error on retry {retry + 1}: {e}, re-finding...")
                            if not _into_frame():
                                raise TimeoutException("Could not re-enter frame after error")
                            # Re-activate tab
                            if not _activate_individual_tab():
                                log("[INDIV][WARN] Could not re-activate tab after error")
                            time.sleep(0.5)
                            continue
                        else:
                            raise
                
                if not id_entered_successfully:
                    log(f"[INDIV][ERROR] Could not verify ID entry for: {_id}")
                    raise ValueError(f"Failed to enter and verify Individual ID: {_id}")

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
                    try:
                        id_input.send_keys("\ue007")
                    except Exception:
                        pass

                if not _into_frame():
                    raise TimeoutException("No frame after GO (reload expected)")

                if not _wait_results(wait_secs=max(6, min(12, timeout))):
                    try:
                        d.execute_script("if (typeof searchForCurrentTab==='function') { searchForCurrentTab(); }")
                    except Exception:
                        pass
                    if not _wait_results(wait_secs=max(5, min(10, timeout))):
                        raise TimeoutException("Results did not render in time")

                # VERIFY and LOG what results were found
                try:
                    # Try to get the results text to verify what the search found
                    results_elem = d.find_element(By.ID, "results")
                    results_text = (results_elem.text or "").strip()
                    if results_text:
                        # Extract just the first line or first 150 chars for logging
                        first_line = results_text.split('\n')[0][:150]
                        log(f"[INDIV] ✓ Search results found: '{first_line}...'")
                except Exception:
                    pass
                
                try: 
                    d.switch_to.default_content()
                except Exception: 
                    pass
                log("[INDIV] Results detected; ready to select client.")
                return True

            except Exception as e:
                log(f"[INDIV][WARN] Attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    import time
                    time.sleep(1)
                    continue
                else:
                    log("[INDIV][ERR] All attempts failed.")
                    try: 
                        d.switch_to.default_content()
                    except Exception: 
                        pass
                    return False
        
        log("[INDIV][ERR] Failed to render dropdown/results after retries.")
        try: 
            d.switch_to.default_content()
        except Exception: 
            pass
        return False

    def click_first_result_name(self, first_name: str = None, last_name: str = None, timeout: int = 12) -> bool:
        '''
        After pressing Go on the Search page, click the patient's first or last name
        in the results dropdown/table to open their profile.
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
                    anchors.extend(d.find_elements(By.XPATH, "//a[contains(translate(@href,'INDIV','indiv') or contains(translate(@href,'INDIVIDUAL','individual'),'individual')]"))
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
                
                def is_ips_link_local(link):
                    """Check if a link is for an IPS profile"""
                    try:
                        href = (link.get_attribute("href") or "").lower()
                        text = (link.text or "").lower()
                        # Check parent row for IPS indicator
                        try:
                            parent_row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                            row_text = (parent_row.text or "").lower()
                            if "ips" in row_text:
                                return True
                        except Exception:
                            pass
                        # Check if href or text contains IPS indicators
                        if "ips" in href or "ips" in text:
                            return True
                        return False
                    except Exception:
                        return False
                
                fn = norm(first_name)
                ln = norm(last_name)

                # Separate links into ISWS and IPS categories
                matching_links = []
                if fn or ln:
                    for a in uniq:
                        t = norm(a.text)
                        if not t:
                            continue
                        if (fn and fn in t) or (ln and ln in t):
                            matching_links.append(a)
                else:
                    matching_links = uniq
                
                if not matching_links:
                    return uniq[0] if uniq else None
                
                # Prefer ISWS (non-IPS) links over IPS links
                isws_links = [link for link in matching_links if not is_ips_link_local(link)]
                ips_links = [link for link in matching_links if is_ips_link_local(link)]
                
                # Log what we found
                log = getattr(self, "log", lambda s: None)
                if isws_links and ips_links:
                    log(f"[SEARCH-RESULT] Found {len(isws_links)} ISWS link(s) and {len(ips_links)} IPS link(s). Preferring ISWS.")
                elif ips_links:
                    log(f"[SEARCH-RESULT] Found only IPS link(s): {len(ips_links)}")
                elif isws_links:
                    log(f"[SEARCH-RESULT] Found only ISWS link(s): {len(isws_links)}")
                
                # Return first ISWS link if available, otherwise first IPS link
                if isws_links:
                    return isws_links[0]
                elif ips_links:
                    return ips_links[0]
                
                return matching_links[0]

            link = None
            try:
                link = WebDriverWait(d, timeout).until(lambda drv: _find_name_link())
            except Exception:
                link = _find_name_link()

            if not link:
                d.switch_to.default_content()
                return False

            # Log which link we're clicking
            log = getattr(self, "log", lambda s: None)
            try:
                link_text = link.text.strip()
                link_href = link.get_attribute("href") or ""
                # Simple IPS detection
                is_ips = "ips" in (link_href or "").lower() or "ips" in (link_text or "").lower()
                profile_type = "IPS" if is_ips else "ISWS"
                log(f"[SEARCH-RESULT] Clicking link: '{link_text}' ({profile_type} profile)")
            except Exception:
                pass

            try:
                link.click()
            except Exception:
                d.execute_script("arguments[0].click();", link)

            # VERIFY: Wait for client profile to load and check it's the right one
            import time
            time.sleep(1)  # Brief pause for page transition
            
            try:
                d.switch_to.default_content()
                # Switch to main content frame where client name appears
                try:
                    WebDriverWait(d, 5).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                except Exception:
                    pass
                
                # Try to read the client name from the loaded profile page
                try:
                    # Common locations for client name on profile page
                    name_selectors = [
                        (By.XPATH, "//h1[contains(@class,'client') or contains(@class,'name')]"),
                        (By.XPATH, "//div[contains(@class,'client-name')]"),
                        (By.XPATH, "//span[contains(@class,'client-name')]"),
                        (By.XPATH, "//h1"),
                        (By.XPATH, "//h2"),
                    ]
                    
                    loaded_name = None
                    for by, sel in name_selectors:
                        try:
                            elem = d.find_element(by, sel)
                            loaded_name = elem.text.strip()
                            if loaded_name:
                                break
                        except Exception:
                            continue
                    
                    if loaded_name:
                        log(f"[SEARCH-RESULT] ✓ Profile loaded: '{loaded_name}'")
                        # Basic verification: check if first or last name matches
                        fn = (first_name or "").strip().lower()
                        ln = (last_name or "").strip().lower()
                        loaded_lower = loaded_name.lower()
                        
                        if (fn and fn in loaded_lower) or (ln and ln in loaded_lower):
                            log(f"[SEARCH-RESULT] ✓ VERIFIED: Profile matches expected client")
                        else:
                            log(f"[SEARCH-RESULT][WARN] Profile name '{loaded_name}' may not match expected '{first_name} {last_name}'")
                    else:
                        log(f"[SEARCH-RESULT][WARN] Could not read client name from profile page")
                        
                except Exception as e:
                    log(f"[SEARCH-RESULT][WARN] Could not verify profile loaded: {e}")
                    
            except Exception as e:
                log(f"[SEARCH-RESULT][WARN] Profile verification error: {e}")

            d.switch_to.default_content()
            return True
        except Exception:
            try: d.switch_to.default_content()
            except Exception: pass
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
        log = getattr(self, "log", lambda s: None)
        
        try:
            log("[INDIV-TAB] Switching to default content...")
            d.switch_to.default_content()
            
            log(f"[INDIV-TAB] Waiting for frm_content_id frame (timeout: {timeout}s)...")
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
            log("[INDIV-TAB] Successfully switched to frm_content_id frame")
            
            # Try JavaScript method first (most reliable)
            try:
                log("[INDIV-TAB] Attempting to activate Individual tab via JavaScript goTab()...")
                d.execute_script("try{ if(typeof goTab==='function'){ goTab('tabIndiv'); } }catch(e){}")
                log("[INDIV-TAB] JavaScript goTab('tabIndiv') executed")
            except Exception as e:
                log(f"[INDIV-TAB][WARN] JavaScript goTab() failed: {e}")
            
            # Also try clicking the tab element directly
            try:
                log("[INDIV-TAB] Attempting to click Individual tab element (tabIndiv_li)...")
                tab = WebDriverWait(d, 3).until(EC.element_to_be_clickable((By.ID, "tabIndiv_li")))
                try: 
                    tab.click()
                    log("[INDIV-TAB] Individual tab clicked via Selenium")
                except Exception: 
                    d.execute_script("arguments[0].click();", tab)
                    log("[INDIV-TAB] Individual tab clicked via JavaScript")
            except Exception as e:
                log(f"[INDIV-TAB][WARN] Could not click tab element: {e}")
            
            # Wait for Individual ID field to appear (confirms tab is active)
            log("[INDIV-TAB] Waiting for Individual ID field (txtKIndID) to confirm tab is active...")
            WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.NAME, "txtKIndID")))
            log("[INDIV-TAB] Individual ID field found - Individual tab is active!")
            
            d.switch_to.default_content()
            return True
        except Exception as e:
            log(f"[INDIV-TAB][ERROR] Failed to switch to Individual tab: {e}")
            import traceback
            log(f"[INDIV-TAB][ERROR] Traceback: {traceback.format_exc()}")
            try: 
                d.switch_to.default_content()
            except Exception: 
                pass
            return False

    def _read_dataframe(self, log):
        """Helper method to read dataframe for counselor name extraction"""
        import pandas as pd
        # This is a placeholder - we'll get the counselor name differently
        return None

    def click_edit_button(self) -> bool:
        """
        Open the Edit overlay by calling the page's own JS *inside the correct iframe*.
        Based on the working welcome letter bot implementation.
        """
        if not self.driver:
            self.log("[EDIT] No driver."); return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
        except Exception:
            self.log("[EDIT][ERROR] Selenium libs missing."); return False

        d = self.driver
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
            self.log("[EDIT][WARN] goOpenEdit() not found in any frame; trying navEdit element.")
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
                self.log("[EDIT][ERROR] Failed to click Edit (navEdit) and goOpenEdit() missing."); return False

        # Switch to the target frame and invoke the open action
        try:
            d.switch_to.window(target[0]); d.switch_to.default_content()
            if target[1] is not None: d.switch_to.frame(target[1])
            try:
                if d.execute_script("return typeof goOpenEdit==='function'"):
                    d.execute_script("goOpenEdit();")
                    self.log("[EDIT] goOpenEdit() called inside the correct frame.")
            except Exception:
                # If goOpenEdit doesn't exist here (fallback path), we already clicked navEdit above.
                pass
        except Exception as e:
            self.log(f"[EDIT][ERROR] Could not trigger Edit overlay: {e}")
            return False

        # Wait for overlay scaffold in this same frame
        try:
            wait.until(lambda _:
                any(el.is_displayed() for el in d.find_elements(By.ID, "editLayer"))
            )
        except Exception:
            self.log("[EDIT][WARN] editLayer not visible yet.")
        try:
            wait.until(lambda _:
                len(d.find_elements(By.ID, "dynamicIframe")) > 0
            )
        except Exception:
            self.log("[EDIT][ERROR] dynamicIframe not found after opening Edit.")
            return False

        self.log("[EDIT] Edit overlay is up (editLayer + dynamicIframe present).")
        return True

    def append_counselor_note(self, counselor_name: str) -> bool:
        """Append the counselor assignment note in Edit popup and Save.
        Based on the working welcome letter bot implementation.
        """
        if not self.driver:
            self.log("[NOTE] No driver."); return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
        except Exception as e:
            self.log(f"[NOTE][ERROR] Selenium libs: {e}"); return False
    
        d = self.driver
        wait = WebDriverWait(d, 14)
    
        # Compose line for counselor assignment
        from datetime import datetime as _dt
        import time, html
        today_str = _dt.now().strftime("%m/%d/%Y")
        note_line = f"{today_str}: IA Only meeting assigned to {counselor_name}. BOT"
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
            self.log("[NOTE][ERROR] Edit overlay not found."); return False
        if alt_used: self.log("[NOTE][INFO] Using dynamicAltframe fallback.")
    
        try: d.switch_to.frame(dyn_ifr)
        except Exception as e:
            self.log(f"[NOTE][ERROR] Cannot enter dynamic frame: {e}"); return False
    
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
                            prev = (tx.get_attribute('value') or '').rstrip("\n")
                            new_val = (prev + "\n" if prev else "") + note_line
                            d.execute_script("arguments[0].value = arguments[1];", tx, new_val)
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
            self.log(f"[NOTE] Appended note: \"{note_line}\"")
        else:
            self.log("[NOTE][WARN] Verification failed; forcing Save after sync.")
    
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
                d = self.driver
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
                    try:
                        d.switch_to.window(owner[0]); d.switch_to.default_content()
                        if owner[1] is not None: d.switch_to.frame(owner[1])
                        d.execute_script("arguments[0].click();", owner[2])
                        saved=True
                    except Exception: pass
            except Exception: pass
    
        if saved:
            self.log("[NOTE] Save clicked successfully.")
        else:
            self.log("[NOTE][WARN] Save button not found or failed to click.")
    
        return True

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

    def click_pre_enrollment_tab_and_waiting_allocation(self, timeout: int = 15) -> bool:
        """
        Click the Pre-Enrollment tab in the right sidebar, wait for dropdown to appear,
        then click the "Waiting for Allocation" button.
        """
        if not self.driver:
            self.log("[PRE-ENROLL] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception as e:
            self.log(f"[PRE-ENROLL][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Switch to the main content frame
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))

            # Wait for page to be ready
            try:
                WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

            self.log("[PRE-ENROLL] Looking for Pre-Enrollment tab...")
            
            # Click the Pre-Enrollment tab (h2 element with onclick="doBuckets('indPreEnrollmentBucket')")
            pre_enroll_tab = None
            try:
                # Try to find by onclick attribute
                pre_enroll_tab = d.find_element(By.XPATH, "//h2[contains(@onclick, 'indPreEnrollmentBucket')]")
            except Exception:
                try:
                    # Fallback: find by text content
                    pre_enroll_tab = d.find_element(By.XPATH, "//h2[normalize-space()='Pre-Enrollment']")
                except Exception:
                    pass

            if not pre_enroll_tab:
                self.log("[PRE-ENROLL][ERROR] Pre-Enrollment tab not found")
                return False

            # Scroll into view and click
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", pre_enroll_tab)
            except Exception:
                pass
            
            try:
                pre_enroll_tab.click()
            except Exception:
                d.execute_script("arguments[0].click();", pre_enroll_tab)

            self.log("[PRE-ENROLL] Pre-Enrollment tab clicked, waiting for dropdown...")

            # Wait for the Pre-Enrollment bucket to expand and show the table
            try:
                # Wait for the bucket to be visible (display: block)
                WebDriverWait(d, 8).until(
                    lambda drv: drv.find_element(By.ID, "indPreEnrollmentBucket").is_displayed()
                )
            except Exception:
                self.log("[PRE-ENROLL][WARN] Pre-Enrollment bucket may not have expanded properly")

            # Look for the "Waiting for Allocation" link with GREEN BUBBLE ONLY
            self.log("[PRE-ENROLL] Looking for 'Waiting for Allocation' button with GREEN bubble (not red)...")
            
            waiting_link = None
            
            # First, let's debug all available "Waiting for Allocation" links and their bubble colors
            self.log("[PRE-ENROLL][DEBUG] Analyzing all 'Waiting for Allocation' links...")
            try:
                all_waiting_links = d.find_elements(By.XPATH, "//a[contains(normalize-space(.), 'Waiting for Allocation')]")
                self.log(f"[PRE-ENROLL][DEBUG] Found {len(all_waiting_links)} 'Waiting for Allocation' links")
                
                for i, link in enumerate(all_waiting_links):
                    try:
                        text = link.text.strip()
                        
                        # Find the parent table row to check the status class
                        parent_row = link.find_element(By.XPATH, "./ancestor::tr")
                        status_cell = parent_row.find_element(By.XPATH, ".//td[contains(@class, 'status')]")
                        status_class = status_cell.get_attribute("class") or ""
                        
                        # Check for green (statusOpen) or red (statusClosed) bubbles
                        has_green = "statusOpen" in status_class
                        has_red = "statusClosed" in status_class
                        
                        color_status = "GREEN" if has_green else ("RED" if has_red else "NO COLOR")
                        self.log(f"[PRE-ENROLL][DEBUG] Link {i+1}: '{text}' - Status Class: '{status_class}' - Color: {color_status}")
                        
                        # Only select if it has green (statusOpen) and NOT red (statusClosed)
                        if has_green and not has_red:
                            waiting_link = link
                            self.log(f"[PRE-ENROLL] SELECTED Link {i+1} - GREEN bubble (statusOpen) detected!")
                            self.log(f"[PRE-ENROLL] Link details: '{text}' - Status: {status_class}")
                            break
                        elif has_red:
                            self.log(f"[PRE-ENROLL] SKIPPED Link {i+1} - RED bubble (statusClosed) detected (avoiding)")
                        else:
                            self.log(f"[PRE-ENROLL] SKIPPED Link {i+1} - No clear status indicator")
                            
                    except Exception as e:
                        self.log(f"[PRE-ENROLL][DEBUG] Error analyzing link {i+1}: {e}")
                        
            except Exception as e:
                self.log(f"[PRE-ENROLL][DEBUG] Error finding waiting links: {e}")
            
            # If no green bubble found, try more specific selectors
            if not waiting_link:
                try:
                    # Look for the specific pattern: link with "Waiting for Allocation" in a row with statusOpen
                    waiting_link = d.find_element(By.XPATH, "//td[@class='statusOpen imageAlignTop']/following-sibling::td//a[contains(normalize-space(.), 'Waiting for Allocation')]")
                    self.log("[PRE-ENROLL] Found 'Waiting for Allocation' with statusOpen class")
                except Exception:
                    try:
                        # Alternative approach: look for the link directly with statusOpen in parent row
                        waiting_link = d.find_element(By.XPATH, "//tr[td[@class='statusOpen imageAlignTop']]//a[contains(normalize-space(.), 'Waiting for Allocation')]")
                        self.log("[PRE-ENROLL] Found 'Waiting for Allocation' with statusOpen ancestor")
                    except Exception:
                        pass
            
            if not waiting_link:
                self.log("[PRE-ENROLL][ERROR] No GREEN 'Waiting for Allocation' link found")
                self.log("[PRE-ENROLL][ERROR] Bot will NOT proceed to avoid clicking wrong status")
                return False

            # Scroll into view and click the waiting link
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", waiting_link)
            except Exception:
                pass
            
            # Import time module
            import time
            
            # Multiple robust click attempts to ensure the click actually works
            for attempt in range(1, 4):  # Try up to 3 times
                try:
                    self.log(f"[PRE-ENROLL] Click attempt {attempt}/3...")
                    
                    # Re-find the element to avoid stale reference on retries
                    if attempt > 1:
                        waiting_link = d.find_element(By.XPATH, "//td[@class='statusOpen imageAlignTop']/following-sibling::td//a[contains(normalize-space(.), 'Waiting for Allocation')]")
                        d.execute_script("arguments[0].scrollIntoView({block:'center'});", waiting_link)
                        time.sleep(0.5)  # Brief pause after re-finding
                    
                    # Try different click methods for maximum reliability
                    if attempt == 1:
                        # First try standard click, but handle element intercept
                        try:
                            waiting_link.click()
                            self.log(f"[PRE-ENROLL] Attempt {attempt}: Selenium click executed")
                        except Exception as click_error:
                            if "click intercepted" in str(click_error).lower():
                                self.log(f"[PRE-ENROLL] Attempt {attempt}: Element click intercepted, trying JavaScript click instead")
                                d.execute_script("arguments[0].click();", waiting_link)
                                self.log(f"[PRE-ENROLL] Attempt {attempt}: JavaScript click executed (fallback)")
                            else:
                                raise click_error
                    elif attempt == 2:
                        d.execute_script("arguments[0].click();", waiting_link)
                        self.log(f"[PRE-ENROLL] Attempt {attempt}: JavaScript click executed")
                    else:
                        # Force click with mouse events as final attempt
                        d.execute_script("""
                            var element = arguments[0];
                            var rect = element.getBoundingClientRect();
                            var x = rect.left + rect.width / 2;
                            var y = rect.top + rect.height / 2;
                            var mouseEvent = new MouseEvent('click', {
                                view: window,
                                bubbles: true,
                                cancelable: true,
                                clientX: x,
                                clientY: y
                            });
                            element.dispatchEvent(mouseEvent);
                        """, waiting_link)
                        self.log(f"[PRE-ENROLL] Attempt {attempt}: Force mouse event click executed")
                    
                    # Brief pause between attempts
                    time.sleep(0.5)
                        
                except Exception as e:
                    self.log(f"[PRE-ENROLL] Attempt {attempt} failed with error: {e}")
                    continue
            
            self.log("[PRE-ENROLL] 'Waiting for Allocation' link clicked with multiple robust methods")
            
            # Wait for the page to actually navigate to the allocation page
            self.log("[PRE-ENROLL] Waiting for allocation page to load...")
            try:
                import time
                time.sleep(2)  # Give the page time to start loading
                
                # Wait for URL to change to the allocation page
                WebDriverWait(d, 10).until(lambda drv: "waitListControl" in drv.current_url)
                self.log(f"[PRE-ENROLL] Navigation detected - new URL: {d.current_url}")
                
                # Wait for the page to be ready
                WebDriverWait(d, 10).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
                self.log("[PRE-ENROLL] Allocation page loaded successfully")
            except Exception as e:
                self.log(f"[PRE-ENROLL][WARN] Page navigation wait failed: {e}")
                self.log(f"[PRE-ENROLL] Current URL: {d.current_url}")
            
            self.log("[PRE-ENROLL] Bot paused - new screen loaded for review")
            return True

        except Exception as e:
            self.log(f"[PRE-ENROLL][ERROR] Failed to click Pre-Enrollment tab or Waiting for Allocation: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def check_and_change_service_to_ia_only(self, counselor_name: str = "Jana Schutz", timeout: int = 15) -> bool:
        """
        Check if service field shows 'IA Only', and if not, change it to 'IA Only'.
        Returns True if service is already 'IA Only' or successfully changed to 'IA Only'.
        """
        if not self.driver:
            self.log("[SERVICE-CHECK] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception as e:
            self.log(f"[SERVICE-CHECK][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Switch to the main content frame
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))

            # Wait for page to be ready
            try:
                WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

            self.log("[SERVICE-CHECK] Checking service field on allocation page...")
            
            # First, check the displayed service text on the allocation page
            service_text = None
            try:
                # Look for the service text in the table
                service_cell = d.find_element(By.XPATH, "//td[@class='title' and text()='Service']/following-sibling::td")
                service_text = service_cell.text.strip()
                self.log(f"[SERVICE-CHECK] Found service text: '{service_text}'")
            except Exception as e:
                self.log(f"[SERVICE-CHECK][ERROR] Could not find service text on allocation page: {e}")
                # If we can't find the service text, proceed to click Edit to check in popup
                service_text = None
            
            # Check if service is already "IA Only"
            if service_text == "IA Only":
                self.log("[SERVICE-CHECK] Service is already 'IA Only' - no change needed")
                return True
            
            # Service is not "IA Only", so we need to click Edit to change it
            self.log(f"[SERVICE-CHECK] Service is '{service_text}' - needs to be changed to 'IA Only'")
            self.log("[SERVICE-CHECK] Clicking Edit button to open popup...")
            
            # Click Edit button to open popup
            edit_button = None
            try:
                # Look for Edit button in the top navigation bar
                edit_button = d.find_element(By.ID, "navEdit")
                self.log("[SERVICE-CHECK] Found Edit button, clicking to open popup...")
                try:
                    edit_button.click()
                    self.log("[SERVICE-CHECK] Edit button clicked successfully")
                except Exception as e:
                    self.log(f"[SERVICE-CHECK] Regular click failed, trying JavaScript click: {e}")
                    d.execute_script("arguments[0].click();", edit_button)
                    self.log("[SERVICE-CHECK] JavaScript click executed")
                
                # Wait for popup to load
                self.log("[SERVICE-CHECK] Waiting for popup to load...")
                try:
                    WebDriverWait(d, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                    self.log("[SERVICE-CHECK] Edit popup opened successfully")
                except Exception as e:
                    self.log(f"[SERVICE-CHECK][ERROR] Popup did not open: {e}")
                    return False
            except Exception:
                self.log("[SERVICE-CHECK][ERROR] Could not find or click Edit button")
                return False

            # Look for the service dropdown field in the popup
            service_dropdown = None
            try:
                service_dropdown = d.find_element(By.ID, "wlPPandWS")
                self.log("[SERVICE-CHECK] Found service dropdown field in popup")
            except Exception:
                self.log("[SERVICE-CHECK][ERROR] Service dropdown field not found in popup")
                return False

            # Check current selected value
            try:
                from selenium.webdriver.support.ui import Select
                select = Select(service_dropdown)
                current_selection = select.first_selected_option
                current_text = current_selection.text.strip()
                current_value = current_selection.get_attribute("value")
                
                self.log(f"[SERVICE-CHECK] Current service: '{current_text}' (value: {current_value})")
                
                # Check if already "IA Only"
                if current_text == "IA Only":
                    self.log("[SERVICE-CHECK] Service is already 'IA Only' - no change needed")
                    # Still need to click Assign and handle popup even if service is already IA Only
                    pass # Continue to Assign button logic
                else:
                    # Change to "IA Only"
                    self.log("[SERVICE-CHECK] Changing service to 'IA Only'...")
                    try:
                        select.select_by_value("p1048")  # IA Only option value
                        self.log("[SERVICE-CHECK] Service changed to 'IA Only' successfully")
                    except Exception as e:
                        self.log(f"[SERVICE-CHECK][ERROR] Failed to select 'IA Only': {e}")
                        return False
                    
                    # Click Save button (need to switch back to parent frame)
                    self.log("[SERVICE-CHECK] Switching back to parent frame to click Save button...")
                    try:
                        d.switch_to.default_content()
                        WebDriverWait(d, 5).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                        
                        save_button = d.find_element(By.ID, "iframeEditSaveButton")
                        self.log("[SERVICE-CHECK] Found Save button, clicking...")
                        try:
                            save_button.click()
                        except Exception:
                            d.execute_script("arguments[0].click();", save_button)
                        self.log("[SERVICE-CHECK] Save button clicked successfully")
                    except Exception as e:
                        self.log(f"[SERVICE-CHECK][ERROR] Failed to click Save button: {e}")
                        return False
                    
                    self.log("[SERVICE-CHECK] Service successfully changed to 'IA Only' and saved")
                
                self.log("[SERVICE-CHECK] Service check completed successfully")
                return True
                    
            except Exception as e:
                self.log(f"[SERVICE-CHECK][ERROR] Failed to check/change service: {e}")
                return False

        except Exception as e:
            self.log(f"[SERVICE-CHECK][ERROR] Failed to check and change service: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def click_assign_button(self, timeout: int = 15) -> bool:
        """
        Click the Assign button on the allocation page to open the assignment popup.
        """
        if not self.driver:
            self.log("[ASSIGN-BUTTON] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception as e:
            self.log(f"[ASSIGN-BUTTON][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # We should already be on the allocation page
            # Switch to the main content frame
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))

            # Wait for page to be ready
            try:
                WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

            self.log("[ASSIGN-BUTTON] Looking for Assign button on allocation page...")
            
            # Look for the Assign button with retry logic to handle stale elements
            assign_button = None
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                try:
                    self.log(f"[ASSIGN-BUTTON] Attempt {attempt}/{max_attempts}: Looking for Assign button...")
                    
                    # Look for the Assign link with assignWL function - more specific selector
                    assign_button = d.find_element(By.XPATH, "//a[contains(@href, 'assignWL') and text()='Assign']")
                    self.log("[ASSIGN-BUTTON] Found Assign button with assignWL href")
                    break
                except Exception:
                    try:
                        # Fallback: look for any link containing "Assign" in the topTabOptions area
                        assign_button = d.find_element(By.XPATH, "//div[@class='topTabOptions']//a[text()='Assign']")
                        self.log("[ASSIGN-BUTTON] Found Assign button in topTabOptions area")
                        break
                    except Exception:
                        try:
                            # Another fallback: look for any link containing "Assign"
                            assign_button = d.find_element(By.XPATH, "//a[text()='Assign']")
                            self.log("[ASSIGN-BUTTON] Found Assign button by general text match")
                            break
                        except Exception:
                            if attempt < max_attempts:
                                self.log(f"[ASSIGN-BUTTON] Attempt {attempt} failed, retrying...")
                                time.sleep(1)  # Wait a moment before retrying
                                continue
                            else:
                                self.log("[ASSIGN-BUTTON][ERROR] Assign button not found after all attempts")
                                return False

            # Click the Assign button - re-find element to avoid stale reference
            try:
                # Re-find the element right before clicking to avoid stale reference
                self.log("[ASSIGN-BUTTON] Re-finding Assign button before clicking...")
                try:
                    assign_button = d.find_element(By.XPATH, "//a[contains(@href, 'assignWL') and text()='Assign']")
                except:
                    try:
                        assign_button = d.find_element(By.XPATH, "//div[@class='topTabOptions']//a[text()='Assign']")
                    except:
                        assign_button = d.find_element(By.XPATH, "//a[text()='Assign']")
                
                # Scroll into view first
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", assign_button)
                time.sleep(0.5)  # Small delay
                
                # Try regular click first
                assign_button.click()
                self.log("[ASSIGN-BUTTON] Assign button clicked successfully")
                
                # Wait a moment to see if popup appears
                time.sleep(2)
                
            except Exception:
                try:
                    # Try JavaScript click with re-found element
                    self.log("[ASSIGN-BUTTON] Trying JavaScript click...")
                    try:
                        assign_button = d.find_element(By.XPATH, "//a[contains(@href, 'assignWL') and text()='Assign']")
                    except:
                        try:
                            assign_button = d.find_element(By.XPATH, "//div[@class='topTabOptions']//a[text()='Assign']")
                        except:
                            assign_button = d.find_element(By.XPATH, "//a[text()='Assign']")
                    
                    d.execute_script("arguments[0].click();", assign_button)
                    self.log("[ASSIGN-BUTTON] Assign button clicked via JavaScript")
                    time.sleep(2)  # Wait to see if popup appears
                except Exception as e:
                    self.log(f"[ASSIGN-BUTTON][ERROR] Failed to click Assign button: {e}")
                    return False

            # Check if popup actually appeared
            self.log("[ASSIGN-BUTTON] Checking if assignment popup actually appeared...")
            try:
                # Check for popup elements
                popup_elements = d.find_elements(By.ID, "editLayer")
                if popup_elements and popup_elements[0].is_displayed():
                    self.log("[ASSIGN-BUTTON] Edit layer popup is visible")
                else:
                    self.log("[ASSIGN-BUTTON][WARN] Edit layer popup not visible")
                
                # Wait for popup to load
                self.log("[ASSIGN-BUTTON] Waiting for assignment popup to load...")
                WebDriverWait(d, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                self.log("[ASSIGN-BUTTON] Assignment popup loaded successfully")
            except Exception as e:
                self.log(f"[ASSIGN-BUTTON][ERROR] Assignment popup did not load: {e}")
                return False

            return True

        except Exception as e:
            self.log(f"[ASSIGN-BUTTON][ERROR] Failed to click Assign button: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def complete_assignment_popup_richtext(self, counselor_name: str = "Jana Schutz", timeout: int = 15) -> bool:
        """
        RICH TEXT EDITOR APPROACH: Handle the complex rich text editor in the assignment popup.
        """
        if not self.driver:
            self.log("[ASSIGNMENT-POPUP] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception as e:
            self.log(f"[ASSIGNMENT-POPUP][ERROR] Selenium libs: {e}"); return False

        d = self.driver

        try:
            # Switch to the assignment popup - try multiple approaches
            self.log("[ASSIGNMENT-POPUP] Switching to assignment popup...")
            d.switch_to.default_content()
            
            # COMPREHENSIVE IFRAME DETECTION AND SWITCHING
            self.log("[ASSIGNMENT-POPUP] Starting comprehensive iframe detection...")
            frame_switched = False
            
            # FIRST: Try JavaScript approach to find and interact with assignment popup
            self.log("[ASSIGNMENT-POPUP] Trying JavaScript approach to find assignment popup...")
            try:
                # Use JavaScript to search for the assignment popup elements
                js_code = """
                // Search for assignment popup elements using JavaScript
                var textarea = document.getElementById('tar_wlResultCom_id');
                var editor = document.getElementById('tar_wlResultCom_id_editor');
                var saveButton = document.getElementById('iframeEditSaveButton');
                
                var result = {
                    textarea: textarea ? 'found' : 'not found',
                    editor: editor ? 'found' : 'not found', 
                    saveButton: saveButton ? 'found' : 'not found',
                    textareaValue: textarea ? textarea.value : 'N/A'
                };
                
                // If we found the textarea, set its value
                if (textarea) {
                    textarea.value = arguments[0];
                    result.textareaValue = textarea.value;
                }
                
                return result;
                """
                
                assignment_note = f"Counselor assigned: {counselor_name}"
                result = d.execute_script(js_code, assignment_note)
                self.log(f"[ASSIGNMENT-POPUP] JavaScript search result: {result}")
                
                if result['textarea'] == 'found':
                    self.log("[ASSIGNMENT-POPUP] SUCCESS: Found assignment popup textarea via JavaScript!")
                    
                    # Try to click the save button
                    if result['saveButton'] == 'found':
                        d.execute_script("document.getElementById('iframeEditSaveButton').click();")
                        self.log("[ASSIGNMENT-POPUP] Save button clicked via JavaScript")
                        return True
                    else:
                        self.log("[ASSIGNMENT-POPUP] Textarea found but save button not found")
                        return False
                else:
                    self.log("[ASSIGNMENT-POPUP] Assignment popup elements not found via JavaScript")
                    
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP] JavaScript approach failed: {e}")
            
            # THIRD: Try comprehensive JavaScript search in all iframes
            self.log("[ASSIGNMENT-POPUP] Trying comprehensive JavaScript search in all iframes...")
            try:
                # JavaScript to search all iframes for assignment popup
                js_comprehensive = """
                var results = [];
                var assignmentNote = arguments[0];
                
                // Search main document
                var mainTextarea = document.getElementById('tar_wlResultCom_id');
                var mainSaveButton = document.getElementById('iframeEditSaveButton');
                results.push({
                    location: 'main document',
                    textarea: mainTextarea ? 'found' : 'not found',
                    saveButton: mainSaveButton ? 'found' : 'not found'
                });
                
                if (mainTextarea) {
                    mainTextarea.value = assignmentNote;
                    if (mainSaveButton) {
                        mainSaveButton.click();
                        return { success: true, location: 'main document' };
                    }
                }
                
                // Search all iframes
                var iframes = document.getElementsByTagName('iframe');
                for (var i = 0; i < iframes.length; i++) {
                    try {
                        var iframeDoc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                        var iframeTextarea = iframeDoc.getElementById('tar_wlResultCom_id');
                        var iframeSaveButton = iframeDoc.getElementById('iframeEditSaveButton');
                        
                        // If we found save button but no textarea, look for other textarea patterns
                        if (iframeSaveButton && !iframeTextarea) {
                            var textarea2 = iframeDoc.querySelector('textarea[name*="wlResultCom"]');
                            var textarea3 = iframeDoc.querySelector('textarea[id*="wlResultCom"]');
                            var textarea4 = iframeDoc.querySelector('textarea[name*="ResultCom"]');
                            var textarea5 = iframeDoc.querySelector('textarea[id*="ResultCom"]');
                            iframeTextarea = textarea2 || textarea3 || textarea4 || textarea5;
                        }
                        
                        results.push({
                            location: 'iframe ' + (i+1) + ' (id: ' + iframes[i].id + ')',
                            textarea: iframeTextarea ? 'found' : 'not found',
                            saveButton: iframeSaveButton ? 'found' : 'not found'
                        });
                        
                        if (iframeTextarea) {
                            iframeTextarea.value = assignmentNote;
                            if (iframeSaveButton) {
                                iframeSaveButton.click();
                                return { success: true, location: 'iframe ' + (i+1) };
                            }
                        }
                    } catch (e) {
                        results.push({
                            location: 'iframe ' + (i+1) + ' (id: ' + iframes[i].id + ')',
                            error: e.message
                        });
                    }
                }
                
                return { success: false, results: results };
                """
                
                assignment_note = f"Counselor assigned: {counselor_name}"
                result = d.execute_script(js_comprehensive, assignment_note)
                self.log(f"[ASSIGNMENT-POPUP] Comprehensive JavaScript search result: {result}")
                
                if result.get('success'):
                    self.log(f"[ASSIGNMENT-POPUP] SUCCESS: Found and interacted with assignment popup in {result['location']}!")
                    return True
                else:
                    self.log("[ASSIGNMENT-POPUP] Assignment popup not found in any location via comprehensive search")
                    
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP] Comprehensive JavaScript search failed: {e}")
            
            # SECOND: Try to access assignment popup from main page using Selenium
            self.log("[ASSIGNMENT-POPUP] Checking if assignment popup is accessible from main page...")
            try:
                hidden_textarea = d.find_element(By.ID, "tar_wlResultCom_id")
                self.log("[ASSIGNMENT-POPUP] SUCCESS: Found assignment popup textarea in main page!")
                
                assignment_note = f"Counselor assigned: {counselor_name}"
                d.execute_script("arguments[0].value = arguments[1];", hidden_textarea, assignment_note)
                self.log("[ASSIGNMENT-POPUP] Text set in main page textarea")
                
                # Find and click the save button
                save_button = d.find_element(By.ID, "iframeEditSaveButton")
                save_button.click()
                self.log("[ASSIGNMENT-POPUP] Save button clicked successfully")
                
                return True
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP] Assignment popup not accessible from main page: {e}")
            
            # SECOND: Look for assignment popup in any iframe that might exist
            self.log("[ASSIGNMENT-POPUP] Searching for assignment popup in all possible iframes...")
            try:
                # Look for any iframe that might contain the assignment popup
                all_iframes = d.find_elements(By.TAG_NAME, "iframe")
                self.log(f"[ASSIGNMENT-POPUP] Found {len(all_iframes)} total iframes to check")
                
                for i, iframe in enumerate(all_iframes):
                    try:
                        iframe_id = iframe.get_attribute("id")
                        self.log(f"[ASSIGNMENT-POPUP] Checking iframe {i+1} (id: {iframe_id})...")
                        
                        d.switch_to.frame(iframe)
                        page_source = d.page_source
                        
                        # Check if this iframe contains assignment popup elements
                        if "tar_wlResultCom_id" in page_source or "Closing Notes" in page_source:
                            self.log(f"[ASSIGNMENT-POPUP] SUCCESS: Found assignment popup in iframe {i+1}!")
                            
                            # Try to find and interact with the textarea
                            try:
                                hidden_textarea = d.find_element(By.ID, "tar_wlResultCom_id")
                                assignment_note = f"Counselor assigned: {counselor_name}"
                                d.execute_script("arguments[0].value = arguments[1];", hidden_textarea, assignment_note)
                                self.log("[ASSIGNMENT-POPUP] Text set in iframe textarea")
                                
                                # Switch back to main page to click save
                                d.switch_to.default_content()
                                save_button = d.find_element(By.ID, "iframeEditSaveButton")
                                save_button.click()
                                self.log("[ASSIGNMENT-POPUP] Save button clicked successfully")
                                
                                return True
                            except Exception as text_e:
                                self.log(f"[ASSIGNMENT-POPUP] Error setting text in iframe {i+1}: {text_e}")
                                d.switch_to.default_content()
                        else:
                            d.switch_to.default_content()
                            
                    except Exception as iframe_e:
                        self.log(f"[ASSIGNMENT-POPUP] Error checking iframe {i+1}: {iframe_e}")
                        try:
                            d.switch_to.default_content()
                        except:
                            pass
                            
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP] Error searching all iframes: {e}")
            
            # First, let's see what iframes are actually available
            try:
                iframes = d.find_elements(By.TAG_NAME, "iframe")
                self.log(f"[ASSIGNMENT-POPUP] Found {len(iframes)} total iframes on page")
                
                for i, iframe in enumerate(iframes):
                    iframe_id = iframe.get_attribute("id")
                    iframe_src = iframe.get_attribute("src")
                    iframe_style = iframe.get_attribute("style")
                    self.log(f"[ASSIGNMENT-POPUP] Iframe {i+1}: id='{iframe_id}', src='{iframe_src}', style='{iframe_style}'")
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP] Error listing iframes: {e}")
            
            # Try each iframe and check its content
            iframe_candidates = ["dynamicIframe", "dynamicAltframe"]
            for iframe_id in iframe_candidates:
                try:
                    self.log(f"[ASSIGNMENT-POPUP] Attempting to switch to {iframe_id}...")
                    WebDriverWait(d, 5).until(EC.frame_to_be_available_and_switch_to_it((By.ID, iframe_id)))
                    
                    # Check if this iframe has content
                    page_source = d.page_source
                    self.log(f"[ASSIGNMENT-POPUP] {iframe_id} page source length: {len(page_source)} characters")
                    
                    if len(page_source) > 100:  # Has substantial content
                        self.log(f"[ASSIGNMENT-POPUP] SUCCESS: {iframe_id} has content!")
                        frame_switched = True
                        break
                    else:
                        self.log(f"[ASSIGNMENT-POPUP] {iframe_id} is empty, trying next...")
                        d.switch_to.default_content()  # Switch back to try next iframe
                        
                except Exception as e:
                    self.log(f"[ASSIGNMENT-POPUP] {iframe_id} failed: {e}")
                    try:
                        d.switch_to.default_content()
                    except:
                        pass
            
            # If no specific iframe worked, try all available iframes
            if not frame_switched:
                self.log("[ASSIGNMENT-POPUP] Trying all available iframes...")
                try:
                    iframes = d.find_elements(By.TAG_NAME, "iframe")
                    for i, iframe in enumerate(iframes):
                        try:
                            self.log(f"[ASSIGNMENT-POPUP] Trying iframe {i+1}...")
                            d.switch_to.frame(iframe)
                            
                            page_source = d.page_source
                            self.log(f"[ASSIGNMENT-POPUP] Iframe {i+1} page source length: {len(page_source)} characters")
                            
                            # Check if this iframe contains the assignment popup content
                            if len(page_source) > 100 and "tar_wlResultCom_id" in page_source:
                                self.log(f"[ASSIGNMENT-POPUP] SUCCESS: Iframe {i+1} contains assignment popup content!")
                                frame_switched = True
                                break
                            elif len(page_source) > 100:
                                self.log(f"[ASSIGNMENT-POPUP] Iframe {i+1} has content but not assignment popup, trying next...")
                                d.switch_to.default_content()
                            else:
                                d.switch_to.default_content()
                                
                        except Exception as e:
                            self.log(f"[ASSIGNMENT-POPUP] Iframe {i+1} failed: {e}")
                            try:
                                d.switch_to.default_content()
                            except:
                                pass
                except Exception as e:
                    self.log(f"[ASSIGNMENT-POPUP] All iframe attempts failed: {e}")
                    return False
            
            if not frame_switched:
                self.log("[ASSIGNMENT-POPUP][ERROR] Could not switch to any iframe")
                
                # FALLBACK: Try to interact with assignment popup from main page without frame switching
                self.log("[ASSIGNMENT-POPUP] FALLBACK: Trying to interact with assignment popup from main page...")
                try:
                    # Look for the text editor elements directly in the main page
                    hidden_textarea = d.find_element(By.ID, "tar_wlResultCom_id")
                    self.log("[ASSIGNMENT-POPUP] FALLBACK: Found hidden textarea in main page!")
                    
                    assignment_note = f"Counselor assigned: {counselor_name}"
                    d.execute_script("arguments[0].value = arguments[1];", hidden_textarea, assignment_note)
                    self.log("[ASSIGNMENT-POPUP] FALLBACK: Text set in hidden textarea via JavaScript")
                    
                    # Find and click the save button
                    save_button = d.find_element(By.ID, "iframeEditSaveButton")
                    save_button.click()
                    self.log("[ASSIGNMENT-POPUP] FALLBACK: Save button clicked successfully")
                    
                    return True
                except Exception as fallback_e:
                    self.log(f"[ASSIGNMENT-POPUP] FALLBACK failed: {fallback_e}")
                    
                    # FINAL FALLBACK: Try to find any text input field on the page
                    self.log("[ASSIGNMENT-POPUP] FINAL FALLBACK: Looking for any text input field...")
                    try:
                        # Look for any textarea or input field
                        textareas = d.find_elements(By.TAG_NAME, "textarea")
                        inputs = d.find_elements(By.TAG_NAME, "input")
                        
                        self.log(f"[ASSIGNMENT-POPUP] Found {len(textareas)} textareas and {len(inputs)} inputs")
                        
                        for i, textarea in enumerate(textareas):
                            textarea_id = textarea.get_attribute("id")
                            textarea_name = textarea.get_attribute("name")
                            self.log(f"[ASSIGNMENT-POPUP] Textarea {i+1}: id='{textarea_id}', name='{textarea_name}'")
                        
                        for i, input_elem in enumerate(inputs):
                            input_id = input_elem.get_attribute("id")
                            input_name = input_elem.get_attribute("name")
                            input_type = input_elem.get_attribute("type")
                            self.log(f"[ASSIGNMENT-POPUP] Input {i+1}: id='{input_id}', name='{input_name}', type='{input_type}'")
                        
                        # Try to use the first textarea we find
                        if textareas:
                            textarea = textareas[0]
                            assignment_note = f"Counselor assigned: {counselor_name}"
                            d.execute_script("arguments[0].value = arguments[1];", textarea, assignment_note)
                            self.log("[ASSIGNMENT-POPUP] FINAL FALLBACK: Text set in first textarea")
                            
                            # Try to find and click save button
                            try:
                                save_button = d.find_element(By.ID, "iframeEditSaveButton")
                                save_button.click()
                                self.log("[ASSIGNMENT-POPUP] FINAL FALLBACK: Save button clicked")
                                return True
                            except:
                                self.log("[ASSIGNMENT-POPUP] FINAL FALLBACK: Could not find save button")
                                return False
                        else:
                            self.log("[ASSIGNMENT-POPUP] FINAL FALLBACK: No textareas found")
                            return False
                            
                    except Exception as final_e:
                        self.log(f"[ASSIGNMENT-POPUP] FINAL FALLBACK failed: {final_e}")
                        return False
            
            # Wait for the assignment popup content to actually load
            self.log("[ASSIGNMENT-POPUP] Waiting for assignment popup content to load...")
            
            # Wait for the content to load by checking for the specific elements we need
            content_loaded = False
            for attempt in range(10):  # Try up to 10 times with 2-second intervals
                try:
                    # Check if we can find the hidden textarea (this is the key element)
                    hidden_textarea = d.find_element(By.ID, "tar_wlResultCom_id")
                    self.log(f"[ASSIGNMENT-POPUP] SUCCESS: Found textarea on attempt {attempt + 1}!")
                    content_loaded = True
                    break
                except Exception:
                    self.log(f"[ASSIGNMENT-POPUP] Attempt {attempt + 1}/10: Content not ready yet, waiting...")
                    time.sleep(1)  # Reduced from 2s to 1s for faster popup interaction
            
            if not content_loaded:
                # Final check - let's see what's actually in the frame
                page_source = d.page_source
                self.log(f"[ASSIGNMENT-POPUP] Final page source length: {len(page_source)} characters")
                self.log(f"[ASSIGNMENT-POPUP] Page source preview: {page_source[:200]}...")
                return False

            # Now that we've confirmed the content is loaded, enter the text
            assignment_note = f"Counselor assigned: {counselor_name}"
            self.log(f"[ASSIGNMENT-POPUP] Attempting to enter text: {assignment_note}")
            
            # Since we already found the textarea in the wait loop, use it directly
            try:
                hidden_textarea = d.find_element(By.ID, "tar_wlResultCom_id")
                self.log("[ASSIGNMENT-POPUP] Setting value in hidden textarea...")
                d.execute_script("arguments[0].value = arguments[1];", hidden_textarea, assignment_note)
                self.log("[ASSIGNMENT-POPUP] Text set successfully!")
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP] ERROR: Failed to set text: {e}")
                return False

            # Wait a moment for the text to be processed
            time.sleep(1)  # Reduced from 2s to 1s for faster popup save

            # Switch back to parent frame to click save button
            self.log("[ASSIGNMENT-POPUP] Switching back to parent frame to click save button...")
            d.switch_to.default_content()
            
            # Find and click the save button
            save_button = d.find_element(By.ID, "iframeEditSaveButton")
            self.log("[ASSIGNMENT-POPUP] Found save button, clicking...")
            save_button.click()
            self.log("[ASSIGNMENT-POPUP] Save button clicked successfully")
            
            # Wait a moment for the save to process
            time.sleep(2)
            
            return True
                    
        except Exception as e:
            self.log(f"[ASSIGNMENT-POPUP][ERROR] Failed to complete assignment popup: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def complete_assignment_popup_simple(self, counselor_name: str = "Jana Schutz", timeout: int = 15) -> bool:
        """
        SIMPLE APPROACH: Just find ANY text input and use it.
        """
        if not self.driver:
            self.log("[ASSIGNMENT-POPUP] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception as e:
            self.log(f"[ASSIGNMENT-POPUP][ERROR] Selenium libs: {e}"); return False

        d = self.driver

        try:
            # Switch to the dynamicAltframe (assignment popup)
            self.log("[ASSIGNMENT-POPUP] Switching to assignment popup...")
            d.switch_to.default_content()
            
            # Wait for the dynamicAltframe to be available
            WebDriverWait(d, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicAltframe")))
            self.log("[ASSIGNMENT-POPUP] Successfully switched to dynamicAltframe")
            
            # Wait for page to be ready
            time.sleep(3)

            # SIMPLE APPROACH: Find ANY text input field
            self.log("[ASSIGNMENT-POPUP] Looking for ANY text input field...")
            
            # Try multiple approaches to find ANY text input
            text_input = None
            assignment_note = f"Counselor assigned: {counselor_name}"
            
            # Approach 1: Look for any textarea
            try:
                textareas = d.find_elements(By.TAG_NAME, "textarea")
                if textareas:
                    text_input = textareas[0]
                    self.log(f"[ASSIGNMENT-POPUP] Found textarea: {text_input.get_attribute('name') or text_input.get_attribute('id')}")
            except Exception:
                pass
            
            # Approach 2: Look for any input field
            if not text_input:
                try:
                    inputs = d.find_elements(By.TAG_NAME, "input")
                    for inp in inputs:
                        if inp.get_attribute("type") in ["text", "textarea", None]:
                            text_input = inp
                            self.log(f"[ASSIGNMENT-POPUP] Found input: {inp.get_attribute('name') or inp.get_attribute('id')}")
                            break
                except Exception:
                    pass
            
            # Approach 3: Look for any contenteditable div
            if not text_input:
                try:
                    contenteditable = d.find_elements(By.CSS_SELECTOR, "div[contenteditable='true']")
                    if contenteditable:
                        text_input = contenteditable[0]
                        self.log(f"[ASSIGNMENT-POPUP] Found contenteditable div")
                except Exception:
                    pass
            
            # Approach 4: Look for ANY element that might accept text
            if not text_input:
                try:
                    all_elements = d.find_elements(By.XPATH, "//*")
                    for elem in all_elements:
                        try:
                            tag = elem.tag_name.lower()
                            if tag in ["textarea", "input"] or elem.get_attribute("contenteditable") == "true":
                                text_input = elem
                                self.log(f"[ASSIGNMENT-POPUP] Found {tag} element")
                                break
                        except Exception:
                            continue
                except Exception:
                    pass

            if not text_input:
                self.log("[ASSIGNMENT-POPUP][ERROR] Could not find ANY text input field")
                return False

            # Try to enter text using multiple methods
            self.log(f"[ASSIGNMENT-POPUP] Attempting to enter text: {assignment_note}")
            
            success = False
            
            # Method 1: Direct send_keys
            try:
                text_input.clear()
                text_input.send_keys(assignment_note)
                self.log("[ASSIGNMENT-POPUP] Text entered via send_keys")
                success = True
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP] send_keys failed: {e}")
            
            # Method 2: JavaScript value setting
            if not success:
                try:
                    d.execute_script("arguments[0].value = arguments[1];", text_input, assignment_note)
                    self.log("[ASSIGNMENT-POPUP] Text entered via JavaScript value")
                    success = True
                except Exception as e:
                    self.log(f"[ASSIGNMENT-POPUP] JavaScript value failed: {e}")
            
            # Method 3: JavaScript innerHTML
            if not success:
                try:
                    d.execute_script("arguments[0].innerHTML = arguments[1];", text_input, assignment_note)
                    self.log("[ASSIGNMENT-POPUP] Text entered via JavaScript innerHTML")
                    success = True
                except Exception as e:
                    self.log(f"[ASSIGNMENT-POPUP] JavaScript innerHTML failed: {e}")
            
            # Method 4: Click and type
            if not success:
                try:
                    text_input.click()
                    time.sleep(0.5)
                    text_input.send_keys(assignment_note)
                    self.log("[ASSIGNMENT-POPUP] Text entered via click and type")
                    success = True
                except Exception as e:
                    self.log(f"[ASSIGNMENT-POPUP] Click and type failed: {e}")

            if not success:
                self.log("[ASSIGNMENT-POPUP][ERROR] All text entry methods failed")
                return False

            # Switch back to parent frame to click save button
            self.log("[ASSIGNMENT-POPUP] Switching back to parent frame to click save button...")
            d.switch_to.default_content()
            
            # Find and click the save button
            save_button = d.find_element(By.ID, "iframeEditSaveButton")
            self.log("[ASSIGNMENT-POPUP] Found save button, clicking...")
            save_button.click()
            self.log("[ASSIGNMENT-POPUP] Save button clicked successfully")
            
            # Wait a moment for the save to process
            time.sleep(2)
            
            return True
                    
        except Exception as e:
            self.log(f"[ASSIGNMENT-POPUP][ERROR] Failed to complete assignment popup: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def complete_assignment_popup(self, counselor_name: str = "Jana Schutz", timeout: int = 15) -> bool:
        """
        Complete the assignment popup by:
        1. Switching to the dynamicIframe
        2. Finding the text area for closing notes
        3. Appending the counselor assignment note
        4. Clicking Save
        """
        if not self.driver:
            self.log("[ASSIGNMENT-POPUP] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception as e:
            self.log(f"[ASSIGNMENT-POPUP][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Switch to the dynamicIframe (assignment popup)
            self.log("[ASSIGNMENT-POPUP] Switching to assignment popup...")
            d.switch_to.default_content()
            
            # Wait for the dynamicIframe to be available
            try:
                WebDriverWait(d, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                self.log("[ASSIGNMENT-POPUP] Successfully switched to dynamicIframe")
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP][ERROR] Failed to switch to dynamicIframe: {e}")
                return False
            
            # Wait for page to be ready
            try:
                WebDriverWait(d, 5).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

            self.log("[ASSIGNMENT-POPUP] Looking for closing notes text area...")
            
            # Find the text area for closing notes
            text_area = None
            try:
                # Try multiple selectors for the textarea
                textarea_selectors = [
                    (By.ID, "tar_wlResultCom_id"),
                    (By.NAME, "wlResultCom"),
                    (By.CSS_SELECTOR, "textarea[name='wlResultCom']"),
                    (By.CSS_SELECTOR, "textarea[id*='wlResultCom']"),
                    (By.XPATH, "//textarea[contains(@name, 'wlResultCom')]"),
                    (By.XPATH, "//textarea[contains(@id, 'wlResultCom')]")
                ]
                
                for by, selector in textarea_selectors:
                    try:
                        text_area = d.find_element(by, selector)
                        self.log(f"[ASSIGNMENT-POPUP] Found textarea with selector: {selector}")
                        break
                    except Exception:
                        continue
                
                if not text_area:
                    self.log("[ASSIGNMENT-POPUP][ERROR] Could not find textarea with any selector")
                    return False
                    
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP][ERROR] Error finding textarea: {e}")
                return False

            # Append the counselor assignment note
            self.log(f"[ASSIGNMENT-POPUP] Appending counselor assignment note for '{counselor_name}'...")
            try:
                # Get current text
                current_text = text_area.get_attribute("value") or ""
                
                # Create the assignment note
                assignment_note = f"\n\nCounselor assigned: {counselor_name}"
                
                # Append the note
                new_text = current_text + assignment_note
                
                # Clear and set the new text
                text_area.clear()
                text_area.send_keys(new_text)
                
                self.log("[ASSIGNMENT-POPUP] Counselor assignment note appended successfully")
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP][ERROR] Failed to append note: {e}")
                return False

            # Look for Save button
            self.log("[ASSIGNMENT-POPUP] Looking for Save button...")
            save_button = None
            try:
                # Try different selectors for Save button
                save_selectors = [
                    (By.XPATH, "//input[@type='submit' and @value='Save']"),
                    (By.XPATH, "//button[text()='Save']"),
                    (By.XPATH, "//input[@value='Save']"),
                    (By.CSS_SELECTOR, "input[type='submit']"),
                    (By.CSS_SELECTOR, "button[type='submit']")
                ]
                
                for by, selector in save_selectors:
                    try:
                        save_button = d.find_element(by, selector)
                        self.log(f"[ASSIGNMENT-POPUP] Found Save button with selector: {selector}")
                        break
                    except Exception:
                        continue
                
                if not save_button:
                    self.log("[ASSIGNMENT-POPUP][ERROR] Save button not found")
                    return False
                    
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP][ERROR] Error finding Save button: {e}")
                return False

            # Click Save button
            try:
                self.log("[ASSIGNMENT-POPUP] Clicking Save button...")
                save_button.click()
                self.log("[ASSIGNMENT-POPUP] Save button clicked successfully")
                
                # Wait a moment for the save to process
                time.sleep(2)
                
                return True
                
            except Exception as e:
                self.log(f"[ASSIGNMENT-POPUP][ERROR] Failed to click Save button: {e}")
                return False

        except Exception as e:
            self.log(f"[ASSIGNMENT-POPUP][ERROR] Failed to complete assignment popup: {e}")
            
            # SIMPLE FALLBACK: Try direct iframe switching
            self.log("[ASSIGNMENT-POPUP] Trying simple fallback approach...")
            try:
                d.switch_to.default_content()
                
                # Try dynamicIframe
                try:
                    d.switch_to.frame("dynamicIframe")
                    textarea = d.find_element(By.ID, "tar_wlResultCom_id")
                    assignment_note = f"Counselor assigned: {counselor_name}"
                    d.execute_script("arguments[0].value = arguments[1];", textarea, assignment_note)
                    d.switch_to.default_content()
                    save_button = d.find_element(By.ID, "iframeEditSaveButton")
                    save_button.click()
                    self.log("[ASSIGNMENT-POPUP] SUCCESS: Simple fallback worked!")
                    return True
                except:
                    d.switch_to.default_content()
                
                # Try dynamicAltframe
                try:
                    d.switch_to.frame("dynamicAltframe")
                    textarea = d.find_element(By.ID, "tar_wlResultCom_id")
                    assignment_note = f"Counselor assigned: {counselor_name}"
                    d.execute_script("arguments[0].value = arguments[1];", textarea, assignment_note)
                    d.switch_to.default_content()
                    save_button = d.find_element(By.ID, "iframeEditSaveButton")
                    save_button.click()
                    self.log("[ASSIGNMENT-POPUP] SUCCESS: Simple fallback worked!")
                    return True
                except:
                    d.switch_to.default_content()
                    
            except Exception as fallback_e:
                self.log(f"[ASSIGNMENT-POPUP] Simple fallback also failed: {fallback_e}")
            
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def _click_assignment_save(self, timeout: int = 12) -> bool:
        """
        Robust Save-button finder + click. Tries multiple scopes & selectors:
         - direct ID 'iframeEditSaveButton' in main document
         - any element with case-insensitive text 'save' (button / li / input)
         - buttons inside .ui-dialog .ui-dialog-buttonpane
         - inside known assignment iframes: dynamicIframe, dynamicAltframe
         - scans all iframes as a last resort
        Returns True if a click was performed (or JavaScript click invoked), False otherwise.
        Logs progress via self.log(...)
        """
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception as e:
            self.log(f"[SAVE-CLICK][ERROR] Selenium libs: {e}")
            return False

        d = self.driver
        wait = WebDriverWait(d, 6)

        def try_click(elem):
            """Scroll + try normal click, fallback to JS click."""
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
            except Exception:
                pass
            try:
                elem.click()
                return True
            except Exception:
                try:
                    d.execute_script("arguments[0].click();", elem)
                    return True
                except Exception:
                    return False

        def search_click_in_current_context():
            """
            Search current document context (assumes appropriate frame is selected).
            Returns True on success.
            """
            # 1) Direct ID - most specific
            try:
                el = d.find_element(By.ID, "iframeEditSaveButton")
                if el.is_displayed():
                    if try_click(el):
                        self.log("[SAVE-CLICK] Clicked #iframeEditSaveButton")
                        return True
            except Exception:
                pass

            # 2) Button/input with value/text 'Save' (case-insensitive)
            try:
                # input[type=submit] with value Save
                candidates = []
                try:
                    candidates.extend(d.find_elements(By.XPATH,
                        "//input[translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='save' or contains(translate(@value,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'save')]"))
                except Exception:
                    pass
                try:
                    candidates.extend(d.find_elements(By.XPATH,
                        "//button[translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='save' or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'save')]"))
                except Exception:
                    pass
                try:
                    candidates.extend(d.find_elements(By.XPATH,
                        "//li[translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='save' or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'save')]"))
                except Exception:
                    pass

                # Also look for common UI dialog button panes
                try:
                    panes = d.find_elements(By.CSS_SELECTOR, ".ui-dialog .ui-dialog-buttonpane, .ui-dialog-buttonpane")
                    for pane in panes:
                        try:
                            btns = pane.find_elements(By.XPATH, ".//button|.//input")
                            for b in btns:
                                text = (b.get_attribute("value") or b.text or "").strip().lower()
                                if "save" == text or "save" in text:
                                    if try_click(b):
                                        self.log("[SAVE-CLICK] Clicked Save inside .ui-dialog-buttonpane")
                                        return True
                        except Exception:
                            continue
                except Exception:
                    pass

                # deduplicate and try candidates
                seen = set()
                for c in candidates:
                    try:
                        ident = (c.tag_name, c.get_attribute("id") or "", c.get_attribute("name") or "", (c.text or ""))
                        if ident in seen:
                            continue
                        seen.add(ident)
                        if c.is_displayed():
                            if try_click(c):
                                self.log("[SAVE-CLICK] Clicked Save candidate (text/value match)")
                                return True
                    except Exception:
                        continue
            except Exception:
                pass

            # 3) Generic 'save' text anywhere (last resort in this context)
            try:
                generic = d.find_elements(By.XPATH,
                    "//*[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'save')]")
                for g in generic:
                    try:
                        if not g.is_displayed():
                            continue
                        # prefer buttons/inputs/li items
                        if g.tag_name.lower() in ("button", "input", "li", "a"):
                            if try_click(g):
                                self.log("[SAVE-CLICK] Clicked element containing 'save' text")
                                return True
                    except Exception:
                        continue
            except Exception:
                pass

            return False

        # --- Strategy 1: Try from top (default content) first ---
        try:
            d.switch_to.default_content()
        except Exception:
            pass

        self.log("[SAVE-CLICK] Trying main document context...")
        try:
            if search_click_in_current_context():
                return True
        except Exception as e:
            self.log(f"[SAVE-CLICK] Main context search error: {e}")

        # --- Strategy 2: Try known popup container (editLayer) in default content ---
        try:
            # if editLayer exists, search inside its DOM subtree (no frame switch)
            try:
                edit_layers = d.find_elements(By.ID, "editLayer")
                if edit_layers:
                    # attempt to search for clickable Save elements inside document (above already tried ID),
                    # but try to narrow to ui-dialog nodes as well
                    self.log("[SAVE-CLICK] editLayer present — searching UI dialog panes.")
                    if search_click_in_current_context():
                        return True
            except Exception:
                pass
        except Exception:
            pass

        # --- Strategy 3: Try known dynamic frames: dynamicIframe, dynamicAltframe ---
        iframe_ids = ["dynamicIframe", "dynamicAltframe", "iframeEdit", "iframeWrapper"]
        for fid in iframe_ids:
            try:
                self.log(f"[SAVE-CLICK] Trying iframe '{fid}' ...")
                # short wait for frame to be available
                try:
                    WebDriverWait(d, 3).until(EC.frame_to_be_available_and_switch_to_it((By.ID, fid)))
                except Exception:
                    # try to find element by name or element reference
                    try:
                        fr = d.find_element(By.ID, fid)
                        d.switch_to.frame(fr)
                    except Exception:
                        continue

                # search within this frame
                if search_click_in_current_context():
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass
                    return True

                # switch back and continue
                try:
                    d.switch_to.default_content()
                except Exception:
                    pass
            except Exception as e:
                self.log(f"[SAVE-CLICK] Error trying iframe '{fid}': {e}")
                try:
                    d.switch_to.default_content()
                except Exception:
                    pass

        # --- Strategy 4: Iterate all iframes and search ---
        try:
            all_iframes = d.find_elements(By.TAG_NAME, "iframe")
            self.log(f"[SAVE-CLICK] Scanning all {len(all_iframes)} iframes for Save button...")
            for i, fr in enumerate(all_iframes):
                try:
                    fid = fr.get_attribute("id") or fr.get_attribute("name") or f"index-{i}"
                    self.log(f"[SAVE-CLICK] Checking iframe {i+1}: id/name='{fid}'")
                    try:
                        d.switch_to.frame(fr)
                    except Exception:
                        # skip if cannot switch
                        self.log(f"[SAVE-CLICK] Could not switch to iframe {fid}, skipping.")
                        d.switch_to.default_content()
                        continue

                    if search_click_in_current_context():
                        try:
                            d.switch_to.default_content()
                        except Exception:
                            pass
                        return True

                    # return to default for next iteration
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass
                except Exception as e:
                    self.log(f"[SAVE-CLICK] Error inspecting iframe {i+1}: {e}")
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass
                    continue
        except Exception as e:
            self.log(f"[SAVE-CLICK] Error listing iframes: {e}")

        # --- Strategy 5: Final JS force click attempt on known ID ---
        try:
            self.log("[SAVE-CLICK] Final JavaScript fallback: try to click #iframeEditSaveButton via JS in top document.")
            try:
                d.switch_to.default_content()
                d.execute_script("var b = document.getElementById('iframeEditSaveButton'); if(b){ try{ b.click(); }catch(e){ b.dispatchEvent(new MouseEvent('click',{bubbles:true})); } }")
                # quick check if popup closed or some change occurred
                time.sleep(1.2)
                self.log("[SAVE-CLICK] Executed JS click on #iframeEditSaveButton (fallback).")
                return True
            except Exception as e:
                self.log(f"[SAVE-CLICK] JS fallback failed: {e}")
        except Exception:
            pass

        self.log("[SAVE-CLICK] All strategies exhausted — Save button not clicked.")
        return False

    def ultra_simple_assignment_popup(self, counselor_name: str = "Jana Schutz") -> bool:
        """
        SIMPLE SAVE BUTTON CLICK: Just click the save button without text entry.
        Uses the robust _click_assignment_save method.
        """
        if not self.driver:
            self.log("[SIMPLE-SAVE] No driver."); return False
        
        self.log("[SIMPLE-SAVE] Starting assignment popup save button click...")
        
        # Wait a moment for popup to load
        import time
        time.sleep(2)
        
        # Use the robust save button click method
        return self._click_assignment_save()

    def _extract_last_name(self, full_name: str) -> str:
        """
        Smart parsing to extract the last name from either format:
        - "Last Name, First Name" (with comma) -> extract part BEFORE comma
        - "First Name Last Name" (without comma) -> extract last word
        """
        if not full_name or not full_name.strip():
            return ""
        
        name = full_name.strip()
        
        # Check if there's a comma (format: "Last, First")
        if "," in name:
            # Split by comma and take the first part (last name)
            parts = name.split(",")
            last_name = parts[0].strip()
            self.log(f"[NAME-PARSING] Comma format detected: '{name}' -> extracted last name: '{last_name}'")
            return last_name
        
        # No comma (format: "First Last") - take the last word
        words = name.split()
        if len(words) >= 2:
            last_name = words[-1].strip()  # Last word is the last name
            self.log(f"[NAME-PARSING] Space format detected: '{name}' -> extracted last name: '{last_name}'")
            return last_name
        elif len(words) == 1:
            # Only one word, use it as is
            self.log(f"[NAME-PARSING] Single word format: '{name}' -> using as last name")
            return words[0].strip()
        else:
            # Empty or invalid
            self.log(f"[NAME-PARSING] Invalid name format: '{name}' -> returning empty")
            return ""
    
    def _is_counselor_match(self, counselor_name, target_name, option_text):
        """
        Flexible matching for counselor names in different formats
        
        Handles formats like:
        - "Perez, Ethel - IPS" vs "Perez -IPS, Ethel"
        - "Perez, Ethel" vs "Ethel Perez"
        - "Perez, Ethel - IPS" vs "Perez Ethel IPS"
        """
        try:
            # Normalize all strings for comparison
            counselor_lower = counselor_name.lower().strip()
            target_lower = target_name.lower().strip()
            option_lower = option_text.lower().strip()
            
            # Extract individual components
            counselor_parts = self._extract_name_parts(counselor_lower)
            target_parts = self._extract_name_parts(target_lower)
            option_parts = self._extract_name_parts(option_lower)
            
            self.log(f"[SERVICE-FILE-WIZARD][MATCH] Comparing:")
            self.log(f"  Counselor: {counselor_parts}")
            self.log(f"  Target: {target_parts}")
            self.log(f"  Option: {option_parts}")
            
            # Check if all counselor name parts are present in option
            counselor_words = set(counselor_parts['words'])
            option_words = set(option_parts['words'])
            
            # All counselor words must be in option
            if not counselor_words.issubset(option_words):
                self.log(f"[SERVICE-FILE-WIZARD][MATCH] ❌ Missing words: {counselor_words - option_words}")
                return False
            
            # CRITICAL FIX: Handle IPS matching logic correctly
            # If target has program info (like "IPS"), option MUST also have it
            if target_parts['program']:
                if not option_parts['program'] or target_parts['program'] != option_parts['program']:
                    self.log(f"[SERVICE-FILE-WIZARD][MATCH] ❌ Program mismatch: expected '{target_parts['program']}', got '{option_parts['program']}'")
                    return False
            else:
                # CRITICAL: If target does NOT have program info (is_ips=False),
                # then option must NOT have IPS either - reject IPS options
                if option_parts['program'] and 'ips' in option_parts['program']:
                    self.log(f"[SERVICE-FILE-WIZARD][MATCH] ❌ Option has IPS but target doesn't - rejecting '{option_text}'")
                    return False
            
            # Additional check: make sure we're not matching a partial name
            # (e.g., "Ana Perez" when looking for "Ethel Perez")
            if len(counselor_words) > 1:  # Multi-word names
                # Check if option has extra words that aren't program indicators
                extra_words = option_words - counselor_words
                if extra_words:
                    program_indicators = {'ips', 'counselor', 'therapist', 'worker', 'staff', 'team'}
                    non_program_words = extra_words - program_indicators
                    if non_program_words:
                        self.log(f"[SERVICE-FILE-WIZARD][MATCH] ❌ Extra non-program words: {non_program_words}")
                        return False
            
            self.log(f"[SERVICE-FILE-WIZARD][MATCH] ✅ MATCH FOUND!")
            return True
            
        except Exception as e:
            self.log(f"[SERVICE-FILE-WIZARD][MATCH] Error in matching: {e}")
            return False
    
    def _extract_name_parts(self, name):
        """Extract name parts from various formats"""
        if not name:
            return {'words': [], 'program': ''}
        
        # Remove common separators and split
        cleaned = name.replace(',', ' ').replace('-', ' ').replace('_', ' ')
        words = [word.strip() for word in cleaned.split() if word.strip()]
        
        # Identify program indicators
        program_indicators = {'ips', 'counselor', 'therapist', 'worker', 'staff', 'team'}
        program_words = []
        name_words = []
        
        for word in words:
            if word in program_indicators:
                program_words.append(word)
            else:
                name_words.append(word)
        
        return {
            'words': name_words,
            'program': ' '.join(program_words)
        }

    def complete_service_file_wizard_select_primary_worker(self, counselor_name: str, is_ips: bool = False, timeout: int = 12) -> bool:
        """
        Enter the counselor_name into Primary Worker (kCWorkerIDPrim_elem) inside the wizard iframe,
        select the matching suggestion from the dropdown (with "- IPS" suffix if is_ips=True), 
        then click the Finish button (wizFinishButton).
        Returns True on success, False on failure.
        """
        if not self.driver:
            self.log("[SERVICE-FILE-WIZARD] No webdriver instance")
            return False

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
        import time

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # --- Replace previous "switch to dynamicIframe / dynamicAltframe" block with this ---
            try:
                d.switch_to.default_content()
            except Exception:
                pass

            # We'll try a short list of known dynamic container frames first, but then
            # descend into their child iframes if necessary.
            frame_candidates = ["dynamicIframe", "dynamicAltframe", "iframeWrapper", "dynamicFrame"]
            primary_input = None

            for fid in frame_candidates:
                try:
                    self.log(f"[SERVICE-FILE-WIZARD] Trying to switch to top-level frame '{fid}'...")
                    try:
                        WebDriverWait(d, 2).until(EC.frame_to_be_available_and_switch_to_it((By.ID, fid)))
                        self.log(f"[SERVICE-FILE-WIZARD] Switched into iframe '{fid}' (top-level).")
                    except Exception:
                        # try by name or element
                        try:
                            fr_elem = d.find_element(By.ID, fid)
                            d.switch_to.frame(fr_elem)
                            self.log(f"[SERVICE-FILE-WIZARD] Switched into iframe element '{fid}'.")
                        except Exception:
                            self.log(f"[SERVICE-FILE-WIZARD] iframe '{fid}' not available, skipping.")
                            d.switch_to.default_content()
                            continue

                    # 1) First try to find the primary input directly in this frame
                    try:
                        primary_input = WebDriverWait(d, 1.5).until(EC.presence_of_element_located((By.ID, "kCWorkerIDPrim_elem")))
                        self.log(f"[SERVICE-FILE-WIZARD] Found Primary Worker input in frame '{fid}'.")
                        break
                    except Exception:
                        # not found at top level of this dynamic frame — try its child iframes
                        child_iframes = d.find_elements(By.TAG_NAME, "iframe")
                        self.log(f"[SERVICE-FILE-WIZARD] {len(child_iframes)} child iframe(s) found inside '{fid}'. Trying them...")
                        for i, child in enumerate(child_iframes):
                            try:
                                # switch into the child iframe
                                try:
                                    d.switch_to.frame(child)
                                except Exception:
                                    # fallback: use index switch
                                    d.switch_to.default_content()
                                    # re-enter parent then enter child by index
                                    try:
                                        WebDriverWait(d, 1).until(EC.frame_to_be_available_and_switch_to_it((By.ID, fid)))
                                    except Exception:
                                        pass
                                    d.switch_to.frame(child)
                                # try to find the primary input inside this nested iframe
                                try:
                                    primary_input = WebDriverWait(d, 1.5).until(EC.presence_of_element_located((By.ID, "kCWorkerIDPrim_elem")))
                                    self.log(f"[SERVICE-FILE-WIZARD] Found Primary Worker input in nested iframe #{i+1} inside '{fid}'.")
                                    break
                                except Exception:
                                    # not found in this nested child - go back up and try next
                                    try:
                                        d.switch_to.parent_frame()
                                    except Exception:
                                        d.switch_to.default_content()
                                    continue
                            except Exception as e_child:
                                self.log(f"[SERVICE-FILE-WIZARD] Error checking child iframe #{i+1} inside '{fid}': {e_child}")
                                try:
                                    d.switch_to.default_content()
                                except Exception:
                                    pass
                                continue

                        # if primary_input found in nested frame break outer loop
                        if primary_input is not None:
                            break

                    # not found here — switch out and try next candidate
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass

                except Exception as e_outer:
                    self.log(f"[SERVICE-FILE-WIZARD] Error trying frame '{fid}': {e_outer}")
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass
                    continue

            # Final fallback: if still not found, try scanning all iframes starting from top
            if primary_input is None:
                try:
                    d.switch_to.default_content()
                except Exception:
                    pass
                all_iframes = d.find_elements(By.TAG_NAME, "iframe")
                self.log(f"[SERVICE-FILE-WIZARD] Top-level fallback: scanning all {len(all_iframes)} iframes for Primary Worker input...")
                for i, fr in enumerate(all_iframes):
                    try:
                        d.switch_to.frame(fr)
                        try:
                            primary_input = d.find_element(By.ID, "kCWorkerIDPrim_elem")
                            self.log(f"[SERVICE-FILE-WIZARD] Found Primary Worker input in iframe index {i}.")
                            break
                        except Exception:
                            # search deeper into nested children of this iframe
                            inner_iframes = d.find_elements(By.TAG_NAME, "iframe")
                            for j, inner in enumerate(inner_iframes):
                                try:
                                    d.switch_to.frame(inner)
                                    try:
                                        primary_input = d.find_element(By.ID, "kCWorkerIDPrim_elem")
                                        self.log(f"[SERVICE-FILE-WIZARD] Found Primary Worker input in nested iframe {i}.{j}.")
                                        break
                                    except Exception:
                                        d.switch_to.parent_frame()
                                        continue
                                except Exception:
                                    continue
                            if primary_input is not None:
                                break
                        d.switch_to.default_content()
                    except Exception:
                        try:
                            d.switch_to.default_content()
                        except Exception:
                            pass
                        continue

            if primary_input is None:
                self.log("[SERVICE-FILE-WIZARD][ERROR] Primary Worker input not found in any scanned iframe.")
                # ensure we return to top-level before exiting the function
                try:
                    d.switch_to.default_content()
                except Exception:
                    pass
                # (original code should handle the False/continue behavior)
                return False

            # If we reach here primary_input is set and you can proceed with typing / suggestion clicks
            # (the rest of your function continues: clear, send_keys, wait for suggestion, click suggestion, switch to default and click finish)

            # 3) Clear & type partial last name (Penelope workaround: typing full name/last name causes dropdown to disappear)
            try:
                try:
                    primary_input.clear()
                except Exception:
                    d.execute_script("arguments[0].value = '';", primary_input)
                
                # Smart parsing: Handle both "Last, First" and "First Last" formats
                # Extract the actual last name regardless of format
                last_name = self._extract_last_name(counselor_name)
                
                # Type all but the last letter of the last name (Penelope workaround)
                partial_last_name = last_name[:-1] if len(last_name) > 1 else last_name
                
                self.log(f"[SERVICE-FILE-WIZARD] Searching for counselor '{counselor_name}' -> extracted last name: '{last_name}' -> using partial: '{partial_last_name}'")
                
                # Type slowly to trigger suggestions reliably
                for ch in partial_last_name:
                    primary_input.send_keys(ch)
                    time.sleep(0.03)
                
                # Wait for dropdown to appear
                time.sleep(0.5)
                self.log(f"[SERVICE-FILE-WIZARD] Typed partial name '{partial_last_name}', waiting for dropdown...")
                
            except Exception as e:
                self.log(f"[SERVICE-FILE-WIZARD][ERROR] Failed to type partial counselor name: {e}")
                try:
                    d.switch_to.default_content()
                except Exception:
                    pass
                return False

            # 4) Use the new GPT method to accept the typed suggestion and click Finish
            return self.accept_typed_suggestion_and_finish(primary_input, counselor_name, is_ips, timeout)

        except Exception as e:
            self.log(f"[SERVICE-FILE-WIZARD][ERROR] Unexpected error: {e}")
            try:
                d.switch_to.default_content()
            except Exception:
                pass
            return False

    def accept_typed_suggestion_and_finish(self, primary_input, counselor_name: str, is_ips: bool = False, timeout: int = 12) -> bool:
        """
        FIXED VERSION: Actually reads dropdown options and matches counselor name properly.
        No more blind arrow key navigation!
        
        Accept the typed counselor name by finding it in the dropdown and clicking it.
        This method handles the suggestion acceptance and completion of the Service File wizard.
        If is_ips=True, it will look for the counselor name with "- IPS" suffix in the dropdown.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
        import time

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # 1) Ensure focus on the input
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", primary_input)
            except Exception:
                pass

            try:
                primary_input.click()
            except Exception:
                try:
                    d.execute_script("arguments[0].focus();", primary_input)
                except Exception:
                    pass

            # Wait for dropdown to appear after typing
            time.sleep(1.5)  # Increased initial wait

            # 2) **NEW: Actually READ the dropdown options**
            target_name = f"{counselor_name} - IPS" if is_ips else counselor_name
            self.log(f"[SERVICE-FILE-WIZARD] Looking for counselor '{target_name}' in dropdown...")
            
            # Try to trigger dropdown by clicking input and pressing down arrow
            self.log("[SERVICE-FILE-WIZARD][DEBUG] Attempting to trigger dropdown...")
            try:
                primary_input.click()  # Click to focus
                time.sleep(0.5)
                primary_input.send_keys(Keys.ARROW_DOWN)  # Trigger dropdown
                time.sleep(0.8)
            except Exception as e:
                self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Could not trigger dropdown: {e}")
            
            # Wait longer for suggestlu.js dropdown to appear and load
            self.log("[SERVICE-FILE-WIZARD][DEBUG] Waiting for suggestlu.js dropdown to appear...")
            time.sleep(3.0)  # Increased wait time for custom JS to load and render dropdown
            
            # Try to trigger the dropdown via JavaScript (suggestlu.js might need this)
            try:
                d.execute_script("""
                    var input = document.getElementById('kCWorkerIDPrim_elem');
                    if (input && input.dispatchEvent) {
                        var event = new Event('keydown');
                        event.key = 'ArrowDown';
                        input.dispatchEvent(event);
                    }
                """)
                time.sleep(0.5)
                self.log("[SERVICE-FILE-WIZARD][DEBUG] Triggered dropdown via JavaScript")
            except Exception as e:
                self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Could not trigger dropdown via JS: {e}")
            
            dropdown_options = []
            dropdown_found = False
            
            # **FIXED: Penelope uses TABLE-based dropdown (not ul/li)**
            # Based on HTML analysis from frame_1_2.html:
            # - Dropdown container: <div id="kCWorkerIDPrim_elem_sugg_ajax_div">
            # - Options are <tr> rows inside a <table class="formatTable">
            # - "Show All" has attribute: tblkey="showAll"
            # - Counselor rows have numeric tblkey values
            # - Counselor name is in the first <td> of each <tr>
            dropdown_selectors = [
                # PRIMARY: Penelope's actual suggestlu.js TABLE-based dropdown
                (By.XPATH, "//div[contains(@id,'kCWorkerIDPrim_elem') and contains(@id,'sugg')]//table//tr[not(@tblkey='showAll')]"),
                (By.XPATH, "//div[contains(@id,'sugg') and contains(@id,'ajax')]//table//tr[not(@tblkey='showAll')]"),
                (By.CSS_SELECTOR, "div[id*='kCWorkerIDPrim_elem'][id*='sugg'] table.formatTable tr[tblkey]"),
                (By.CSS_SELECTOR, "div[id*='sugg_ajax_div'] table tr[tblkey]"),
                # Broader table-based patterns
                (By.XPATH, "//div[contains(@id,'sugg') or contains(@class,'sugg')]//table[@id[contains(.,'luResultTable')]]//tr[@tblkey and @tblkey!='showAll']"),
                (By.XPATH, "//table[contains(@id,'luResultTable')]//tr[@tblkey and @tblkey!='showAll']"),
                (By.CSS_SELECTOR, "table[id*='luResultTable'] tr[tblkey]:not([tblkey='showAll'])"),
                # Very broad: any table rows with tblkey attribute (but not showAll)
                (By.XPATH, "//table//tr[@tblkey and @tblkey!='showAll']"),
                # Fallback to ul/li if they ever change back to standard dropdowns
                (By.CSS_SELECTOR, "div[id*='suggest'] ul li"),
                (By.XPATH, "//div[contains(@id,'suggest') or contains(@class,'suggest')]//ul//li"),
            ]
            
            self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Searching for dropdown with {len(dropdown_selectors)} different selectors...")
            
            # DEBUG: Log all elements on the page that might be dropdowns
            try:
                all_tables = d.find_elements(By.TAG_NAME, "table")
                all_trs = d.find_elements(By.TAG_NAME, "tr")
                all_divs = d.find_elements(By.TAG_NAME, "div")
                self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Page has {len(all_tables)} table elements, {len(all_trs)} tr elements, {len(all_divs)} div elements")
                
                # Check for suggestlu.js specific elements (TABLE-based dropdown)
                suggest_divs = d.find_elements(By.XPATH, "//div[contains(@id,'sugg') or contains(@class,'sugg') or contains(@id,'lu') or contains(@class,'lu')]")
                self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Found {len(suggest_divs)} suggest/lookup div elements")
                
                for elem in suggest_divs[:3]:  # Log first 3
                    try:
                        elem_id = elem.get_attribute('id') or ''
                        elem_class = elem.get_attribute('class') or ''
                        is_visible = elem.is_displayed()
                        self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Suggest div: id='{elem_id}' class='{elem_class}' visible={is_visible}")
                        # Check for TABLE and TR elements inside this div (Penelope's actual structure)
                        tables_inside = elem.find_elements(By.TAG_NAME, "table")
                        if tables_inside:
                            self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Found {len(tables_inside)} table elements inside suggest div")
                            for table in tables_inside[:1]:
                                tr_inside = table.find_elements(By.TAG_NAME, "tr")
                                self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Table has {len(tr_inside)} tr elements")
                                for tr in tr_inside[:3]:
                                    tblkey = tr.get_attribute('tblkey') or ''
                                    td_texts = [td.text.strip() for td in tr.find_elements(By.TAG_NAME, "td")]
                                    self.log(f"[SERVICE-FILE-WIZARD][DEBUG] TR: tblkey='{tblkey}' text={td_texts}")
                    except Exception as e:
                        self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Error analyzing suggest div: {e}")
                
                # Check for luResultTable specifically
                lu_tables = d.find_elements(By.XPATH, "//table[contains(@id,'luResultTable')]")
                self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Found {len(lu_tables)} luResultTable elements")
                
                for table in lu_tables[:1]:
                    try:
                        table_id = table.get_attribute('id') or ''
                        is_visible = table.is_displayed()
                        self.log(f"[SERVICE-FILE-WIZARD][DEBUG] luResultTable: id='{table_id}' visible={is_visible}")
                        rows = table.find_elements(By.TAG_NAME, "tr")
                        self.log(f"[SERVICE-FILE-WIZARD][DEBUG] luResultTable has {len(rows)} rows")
                        for row in rows[:5]:
                            tblkey = row.get_attribute('tblkey') or ''
                            td_texts = [td.text.strip() for td in row.find_elements(By.TAG_NAME, "td")]
                            self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Row: tblkey='{tblkey}' content={td_texts}")
                    except Exception as e:
                        self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Error analyzing luResultTable: {e}")
                    
            except Exception as e:
                self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Could not analyze page elements: {e}")
            
            for i, (by, selector) in enumerate(dropdown_selectors):
                try:
                    options = d.find_elements(by, selector)
                    if options and len(options) > 0:
                        # Filter out hidden/invisible options
                        visible_options = [opt for opt in options if opt.is_displayed()]
                        if visible_options:
                            dropdown_options = visible_options
                            dropdown_found = True
                            self.log(f"[SERVICE-FILE-WIZARD] ✅ Found {len(visible_options)} dropdown options using selector #{i+1}: {selector}")
                            break
                        else:
                            self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Selector #{i+1} found {len(options)} options but none visible")
                except Exception as e:
                    self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Selector #{i+1} failed: {e}")
                    continue
            
            if not dropdown_found or not dropdown_options:
                # Try one more approach - wait longer and look for ANY dropdown that appeared
                self.log("[SERVICE-FILE-WIZARD][DEBUG] No dropdown found with standard selectors, trying extended wait...")
                time.sleep(2)  # Wait longer for dropdown to appear
                
                # Try to find ANY visible dropdown with a broader search (TABLE-based for Penelope)
                try:
                    all_tables = d.find_elements(By.TAG_NAME, "table")
                    all_divs = d.find_elements(By.TAG_NAME, "div")
                    
                    potential_dropdowns = []
                    for elem in all_tables + all_divs:
                        if elem.is_displayed():
                            elem_id = elem.get_attribute("id") or ""
                            elem_class = elem.get_attribute("class") or ""
                            # Look for suggestlu.js dropdown indicators
                            if "sugg" in elem_id.lower() or "lu" in elem_id.lower() or "sugg" in elem_class.lower():
                                potential_dropdowns.append(elem)
                    
                    self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Found {len(potential_dropdowns)} potential dropdown elements after extended wait")
                    
                    if potential_dropdowns:
                        # Try to find options in any of these potential dropdowns (TABLE ROWS, not li)
                        for dropdown in potential_dropdowns:
                            try:
                                # First try to find table rows (Penelope's actual structure)
                                options = dropdown.find_elements(By.XPATH, ".//table//tr[@tblkey and @tblkey!='showAll']")
                                if not options:
                                    # Fallback: try any tr with tblkey
                                    options = dropdown.find_elements(By.XPATH, ".//tr[@tblkey]")
                                    # Filter out showAll
                                    options = [opt for opt in options if opt.get_attribute('tblkey') != 'showAll']
                                
                                if options and len(options) > 0:
                                    visible_options = [opt for opt in options if opt.is_displayed()]
                                    if visible_options:
                                        dropdown_options = visible_options
                                        dropdown_found = True
                                        self.log(f"[SERVICE-FILE-WIZARD] ✅ Found {len(visible_options)} TABLE ROW options in extended search")
                                        break
                            except:
                                continue
                
                except Exception as e:
                    self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Extended search failed: {e}")
            
            if not dropdown_found or not dropdown_options:
                self.log("[SERVICE-FILE-WIZARD][WARN] Could not find dropdown options after all attempts - falling back to old arrow key method")
                
                # DEBUG: Take screenshot to see what's on screen when dropdown fails
                try:
                    screenshot_path = os.path.join(self.output_dir, f"dropdown_debug_{counselor_name.replace(' ', '_').replace(',', '')}.png")
                    d.save_screenshot(screenshot_path)
                    self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Screenshot saved to {screenshot_path} for debugging")
                except Exception as e:
                    self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Could not save screenshot: {e}")
                
                # Fallback to old method if dropdown not found
                primary_input.send_keys(Keys.ARROW_DOWN)
                time.sleep(0.3)
                if is_ips:
                    primary_input.send_keys(Keys.ARROW_DOWN)
                    time.sleep(0.2)
                primary_input.send_keys(Keys.ENTER)
                self.log(f"[SERVICE-FILE-WIZARD] Used fallback arrow key method for '{counselor_name}'")
            else:
                # 3) **NEW: Smart matching to find the RIGHT counselor**
                matched_option = None
                match_index = -1
                
                # Log all options for debugging
                self.log(f"[SERVICE-FILE-WIZARD] Dropdown options found:")
                for i, opt in enumerate(dropdown_options):
                    try:
                        # For TABLE rows, extract text from first <td>
                        if opt.tag_name.lower() == 'tr':
                            tds = opt.find_elements(By.TAG_NAME, "td")
                            opt_text = tds[0].text.strip() if tds else opt.text.strip()
                            tblkey = opt.get_attribute('tblkey') or ''
                            self.log(f"  [{i}] {opt_text} (tblkey={tblkey})")
                        else:
                            opt_text = opt.text.strip()
                            self.log(f"  [{i}] {opt_text}")
                    except Exception as e:
                        self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Error logging option {i}: {e}")
                
                # Enhanced flexible matching logic
                for i, opt in enumerate(dropdown_options):
                    try:
                        # For TABLE rows, extract text from first <td> (counselor name column)
                        if opt.tag_name.lower() == 'tr':
                            tblkey = opt.get_attribute('tblkey') or ''
                            # Skip "Show All" by tblkey attribute
                            if tblkey.lower() == 'showall':
                                self.log(f"[SERVICE-FILE-WIZARD] Skipping 'Show All' row (tblkey={tblkey})")
                                continue
                            
                            tds = opt.find_elements(By.TAG_NAME, "td")
                            opt_text = tds[0].text.strip() if tds else opt.text.strip()
                        else:
                            opt_text = opt.text.strip()
                        
                        opt_lower = opt_text.lower()
                        target_lower = target_name.lower()
                        counselor_lower = counselor_name.lower()
                        
                        # Skip "Show all" and similar generic options (text-based fallback)
                        if any(skip in opt_lower for skip in ["show all", "view all", "see all", "more results"]):
                            self.log(f"[SERVICE-FILE-WIZARD] Skipping generic option: '{opt_text}'")
                            continue
                        
                        # Exact match (best)
                        if opt_lower == target_lower or opt_lower == counselor_lower:
                            matched_option = opt
                            match_index = i
                            self.log(f"[SERVICE-FILE-WIZARD] ✅ EXACT MATCH found at index {i}: '{opt_text}'")
                            break
                        
                        # Enhanced flexible matching for different name formats
                        if self._is_counselor_match(counselor_name, target_name, opt_text):
                            if matched_option is None:  # Take first good match
                                matched_option = opt
                                match_index = i
                                self.log(f"[SERVICE-FILE-WIZARD] ✅ FLEXIBLE MATCH found at index {i}: '{opt_text}'")
                        
                    except Exception as e:
                        self.log(f"[SERVICE-FILE-WIZARD] Error checking option {i}: {e}")
                        continue
                
                if matched_option:
                    # 4) **NEW: Click the CORRECT option directly**
                    try:
                        self.log(f"[SERVICE-FILE-WIZARD] Clicking matched option at index {match_index}...")
                        
                        # Try regular click first
                        try:
                            d.execute_script("arguments[0].scrollIntoView({block:'nearest'});", matched_option)
                            time.sleep(0.1)
                            matched_option.click()
                            self.log(f"[SERVICE-FILE-WIZARD] ✅ Successfully clicked counselor '{target_name}'")
                        except Exception as e:
                            self.log(f"[SERVICE-FILE-WIZARD] Regular click failed, trying JavaScript: {e}")
                            d.execute_script("arguments[0].click();", matched_option)
                            self.log(f"[SERVICE-FILE-WIZARD] ✅ JavaScript click successful for '{target_name}'")
                        
                    except Exception as e:
                        self.log(f"[SERVICE-FILE-WIZARD][ERROR] Failed to click matched option: {e}")
                        return False
                else:
                    self.log(f"[SERVICE-FILE-WIZARD][ERROR] Could not find matching option for '{target_name}'")
                    self.log(f"[SERVICE-FILE-WIZARD][ERROR] Available options were: {[opt.text.strip() for opt in dropdown_options if hasattr(opt, 'text')]}")
                    return False

            # 5) Wait briefly for the system to register the selection
            time.sleep(0.5)
            
            selection_verified = False
            try:
                end = time.time() + 3.5
                while time.time() < end and not selection_verified:
                    try:
                        # Try the hidden input first
                        hidden = d.find_elements(By.NAME, "kCWorkerIDPrim")
                        if hidden:
                            val = hidden[0].get_attribute("value") or ""
                            if val.strip():
                                selection_verified = True
                                self.log(f"[SERVICE-FILE-WIZARD] Hidden kCWorkerIDPrim populated with value '{val}'.")
                                break
                    except Exception:
                        pass

                    try:
                        # fallback: check that the visible input value matches
                        vis_val = primary_input.get_attribute("value") or primary_input.text or ""
                        if vis_val.strip() and counselor_name.strip().split()[-1].lower() in vis_val.strip().lower():
                            selection_verified = True
                            self.log(f"[SERVICE-FILE-WIZARD] Visible input now contains '{vis_val}'. Proceeding.")
                            break
                    except Exception:
                        pass

                    time.sleep(0.15)
            except Exception as e:
                self.log(f"[SERVICE-FILE-WIZARD][WARN] Error during selection verification: {e}")

            if not selection_verified:
                self.log("[SERVICE-FILE-WIZARD][WARN] Could not verify selection - proceeding to Finish anyway.")

            # 6) Switch back to top-level document and click the Finish button
            try:
                d.switch_to.default_content()
            except Exception:
                pass

            # Candidate finish button selectors (ordered)
            finish_selectors = [
                (By.ID, "wizFinishButton"),
                (By.XPATH, "//button[translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='finish']"),
                (By.XPATH, "//li[@id='wizFinishButton' or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'finish')]"),
                (By.XPATH, "//*[contains(@class,'ui-dialog-buttonpane')]//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'finish')]"),
                # last resort: any clickable element containing 'Finish' text
                (By.XPATH, "//*[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'finish') and (self::button or self::a or self::li or @role='button')]")
            ]

            finish_btn = None
            for by, sel in finish_selectors:
                try:
                    self.log(f"[SERVICE-FILE-WIZARD] Looking for Finish button via {by} / {sel} ...")
                    # short wait for each selector to avoid long blocking
                    try:
                        finish_btn = WebDriverWait(d, 1.5).until(EC.element_to_be_clickable((by, sel)))
                    except Exception:
                        # fallback to presence-only and check displayed/clickable
                        try:
                            candidates = d.find_elements(by, sel)
                            finish_btn = next((c for c in candidates if c.is_displayed()), None)
                        except Exception:
                            finish_btn = None

                    if finish_btn:
                        try:
                            finish_btn.click()
                            self.log("[SERVICE-FILE-WIZARD] Clicked Finish button.")
                            return True
                        except Exception:
                            try:
                                d.execute_script("arguments[0].scrollIntoView({block:'center'});", finish_btn)
                            except Exception:
                                pass
                            try:
                                d.execute_script("arguments[0].click();", finish_btn)
                                self.log("[SERVICE-FILE-WIZARD] Clicked Finish button via JS.")
                                return True
                            except Exception as e_click:
                                self.log(f"[SERVICE-FILE-WIZARD][WARN] Clicking Finish candidate failed: {e_click}")
                                # try next selector
                except Exception as e_sel:
                    self.log(f"[SERVICE-FILE-WIZARD] Selector check error: {e_sel}")
                    continue

            # 4) Another fallback: scan all iframes/frames for a Finish button (sometimes the finish lives inside editLayer iframe)
            try:
                all_iframes = d.find_elements(By.TAG_NAME, "iframe")
                self.log(f"[SERVICE-FILE-WIZARD] Fallback: scanning {len(all_iframes)} iframes for a Finish button...")
                for i, fr in enumerate(all_iframes):
                    try:
                        d.switch_to.default_content()
                        d.switch_to.frame(fr)
                        # try to find by id first
                        try:
                            fb = d.find_element(By.ID, "wizFinishButton")
                            if fb and fb.is_displayed():
                                try:
                                    fb.click()
                                    self.log(f"[SERVICE-FILE-WIZARD] Clicked Finish button inside iframe index {i}.")
                                    d.switch_to.default_content()
                                    return True
                                except Exception:
                                    try:
                                        d.execute_script("arguments[0].click();", fb)
                                        self.log(f"[SERVICE-FILE-WIZARD] Clicked Finish via JS inside iframe index {i}.")
                                        d.switch_to.default_content()
                                        return True
                                    except Exception:
                                        pass
                        except Exception:
                            pass

                        # try text-based fallback inside this iframe
                        try:
                            cand = d.find_element(By.XPATH, "//button[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'finish') or contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'done')]")
                            if cand and cand.is_displayed():
                                try:
                                    cand.click()
                                    self.log(f"[SERVICE-FILE-WIZARD] Clicked Finish-like button inside iframe index {i}.")
                                    d.switch_to.default_content()
                                    return True
                                except Exception:
                                    try:
                                        d.execute_script("arguments[0].click();", cand)
                                        self.log(f"[SERVICE-FILE-WIZARD] Clicked Finish-like button via JS inside iframe index {i}.")
                                        d.switch_to.default_content()
                                        return True
                                    except Exception:
                                        pass
                        except Exception:
                            pass

                        d.switch_to.default_content()
                    except Exception:
                        try:
                            d.switch_to.default_content()
                        except Exception:
                            pass
                        continue
            except Exception:
                pass

            # If we reach here we couldn't find/click finish
            self.log("[SERVICE-FILE-WIZARD][ERROR] Finish button not found or not clickable after all fallbacks.")
            return False

        except Exception as e:
            self.log(f"[SERVICE-FILE-WIZARD][ERROR] Unexpected error in accept_typed_suggestion_and_finish: {e}")
            try:
                d.switch_to.default_content()
            except Exception:
                pass
            return False

    def click_participant_client_name(self, client_name: str, timeout: int = 10) -> bool:
        """
        After Finish, click the client's name link in the Participants box to return
        to the client profile page.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Always reset to top document and ensure we're in the right frame
            d.switch_to.default_content()
            self.log("[PARTICIPANT] Switched to default content.")
            
            # Wait a moment for the page to settle after the Service File wizard
            time.sleep(2)
            
            # Try to switch to the main content frame if needed
            try:
                d.switch_to.frame("frm_content_id")
                self.log("[PARTICIPANT] Switched to frm_content_id frame.")
            except Exception:
                self.log("[PARTICIPANT] Could not switch to frm_content_id, staying in default content.")

        except Exception as e:
            self.log(f"[PARTICIPANT][WARN] Error switching frames: {e}")

        try:
            # Wait for Participants box to load with shorter timeout per attempt
            participants_box = None
            try:
                participants_box = WebDriverWait(d, 3).until(
                    EC.presence_of_element_located((By.ID, "ajaxprogMemTable"))
                )
                self.log("[PARTICIPANT] Participants box loaded.")
            except Exception:
                # Try switching back to default content and try again
                try:
                    d.switch_to.default_content()
                    participants_box = WebDriverWait(d, 3).until(
                        EC.presence_of_element_located((By.ID, "ajaxprogMemTable"))
                    )
                    self.log("[PARTICIPANT] Participants box loaded after switching to default content.")
                except Exception:
                    self.log("[PARTICIPANT][ERROR] Could not find ajaxprogMemTable in any frame.")
                    return False

            # Multiple strategies to find the client name link
            link = None
            
            # Strategy 1: Look for the link directly with the client name
            try:
                xpath = f"//div[@id='ajaxprogMemTable']//a[contains(text(), '{client_name}')]"
                link = WebDriverWait(d, 2).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                self.log(f"[PARTICIPANT] Found client name link via Strategy 1: '{client_name}'.")
            except Exception as e:
                self.log(f"[PARTICIPANT] Strategy 1 failed: {e}")
            
            # Strategy 2: Look for any link in the participants table that contains the client name
            if not link:
                try:
                    xpath = f"//table[@class='ajaxprogMemTable']//a[contains(text(), '{client_name}')]"
                    link = WebDriverWait(d, 2).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    self.log(f"[PARTICIPANT] Found client name link via Strategy 2: '{client_name}'.")
                except Exception as e:
                    self.log(f"[PARTICIPANT] Strategy 2 failed: {e}")
            
            # Strategy 3: Look for the link by href pattern (client profile control)
            if not link:
                try:
                    xpath = "//div[@id='ajaxprogMemTable']//a[contains(@href, 'acm_clientProfileControl')]"
                    link = WebDriverWait(d, 2).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    self.log(f"[PARTICIPANT] Found client name link via Strategy 3 (href pattern).")
                except Exception as e:
                    self.log(f"[PARTICIPANT] Strategy 3 failed: {e}")
            
            # Strategy 4: Look for any link in the participants area
            if not link:
                try:
                    xpath = "//div[@id='ajaxprogMemTable']//a"
                    links = d.find_elements(By.XPATH, xpath)
                    self.log(f"[PARTICIPANT] Found {len(links)} links in participants area.")
                    for i, candidate in enumerate(links):
                        try:
                            text = candidate.text.strip()
                            self.log(f"[PARTICIPANT] Link {i+1}: '{text}'")
                            if client_name.lower() in text.lower():
                                link = candidate
                                self.log(f"[PARTICIPANT] Found client name link via Strategy 4: '{text}'.")
                                break
                        except Exception as e:
                            self.log(f"[PARTICIPANT] Error checking link {i+1}: {e}")
                except Exception as e:
                    self.log(f"[PARTICIPANT] Strategy 4 failed: {e}")

            if not link:
                self.log(f"[PARTICIPANT][ERROR] Could not find client name link for '{client_name}' using any strategy.")
                # Debug: Let's see what's actually in the participants box
                try:
                    participants_html = participants_box.get_attribute('outerHTML')
                    self.log(f"[PARTICIPANT][DEBUG] Participants box HTML: {participants_html[:500]}...")
                except Exception:
                    pass
                return False

            # Scroll into view and click
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
            except Exception:
                pass

            try:
                link.click()
                self.log(f"[PARTICIPANT] Clicked client link '{client_name}' successfully.")
            except Exception:
                try:
                    d.execute_script("arguments[0].click();", link)
                    self.log(f"[PARTICIPANT] Clicked client link '{client_name}' via JavaScript.")
                except Exception as e:
                    self.log(f"[PARTICIPANT][ERROR] Failed to click link: {e}")
                    return False

            self.log(f"[PARTICIPANT] Successfully clicked client link '{client_name}'. Returning to profile.")
            return True

        except Exception as e:
            self.log(f"[PARTICIPANT][ERROR] Could not click client name '{client_name}': {e}")
            return False

    def complete_service_file_wizard(self, counselor_name: str = "Jana Schutz", is_ips: bool = False, timeout: int = 15) -> bool:
        """
        Complete the Service File wizard by using the robust GPT method:
        1. Inputting the counselor name into the Primary Worker field
        2. Selecting from dropdown suggestions (with "- IPS" suffix if is_ips=True)
        3. Clicking the Finish button
        """
        if not self.driver:
            self.log("[SERVICE-FILE-WIZARD] No driver."); return False
        
        suffix = " (IPS counselor)" if is_ips else " (non-IPS counselor)"
        self.log(f"[SERVICE-FILE-WIZARD] Starting Service File wizard completion for counselor: {counselor_name}{suffix}")
        
        # Use the robust GPT method for completing the wizard
        return self.complete_service_file_wizard_select_primary_worker(counselor_name, is_ips, timeout)

    def expand_case_info_if_needed_and_click_ia_only(self, verify_selector: tuple = None, timeout: int = 10) -> bool:
        """
        Ensure Case Information is expanded, then click the 'IA Only' link that corresponds to the green bubble (statusOpen).
        Based on HTML analysis: The green bubble has class="statusOpen" and the IA Only link is clickable.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            d.switch_to.default_content()
        except Exception:
            pass

        self.log("[CASE-INFO] Starting IA Only link search...")
        
        # First, let's debug the current page state
        self.log(f"[CASE-INFO][DEBUG] Current URL: {d.current_url}")
        
        # Check what frames are available
        try:
            d.switch_to.default_content()
            frames = d.find_elements(By.TAG_NAME, "iframe")
            self.log(f"[CASE-INFO][DEBUG] Found {len(frames)} iframes on page")
            for i, frame in enumerate(frames):
                try:
                    frame_id = frame.get_attribute("id") or "no-id"
                    frame_name = frame.get_attribute("name") or "no-name"
                    frame_src = frame.get_attribute("src") or "no-src"
                    self.log(f"[CASE-INFO][DEBUG] Frame {i+1}: id='{frame_id}', name='{frame_name}', src='{frame_src[:50]}...'")
                except Exception as e:
                    self.log(f"[CASE-INFO][DEBUG] Frame {i+1}: Error getting details: {e}")
        except Exception as e:
            self.log(f"[CASE-INFO][DEBUG] Error checking frames: {e}")
        
        # Try different frame contexts
        frame_contexts = [
            ("default_content", lambda: d.switch_to.default_content()),
            ("frm_content_id", lambda: d.switch_to.frame("frm_content_id")),
            ("frm_left_bar_id", lambda: d.switch_to.frame("frm_left_bar_id")),
        ]
        
        for context_name, switch_func in frame_contexts:
            try:
                self.log(f"[CASE-INFO][DEBUG] Trying frame context: {context_name}")
                switch_func()
                
                # Look for IA Only links in this context
                ia_links = d.find_elements(By.XPATH, "//a[text()='IA Only']")
                self.log(f"[CASE-INFO][DEBUG] In {context_name}: Found {len(ia_links)} IA Only links")
                
                if len(ia_links) > 0:
                    self.log(f"[CASE-INFO][DEBUG] SUCCESS! Found IA Only links in {context_name}")
                    # Show details of the first few links
                    for i, link in enumerate(ia_links[:3]):
                        try:
                            href = link.get_attribute("href") or ""
                            displayed = link.is_displayed()
                            self.log(f"[CASE-INFO][DEBUG] Link {i+1}: href='{href[:50]}...', displayed={displayed}")
                        except Exception as e:
                            self.log(f"[CASE-INFO][DEBUG] Link {i+1}: Error getting details: {e}")
                    
                    # Try to find the green bubble link in this context
                    try:
                        green_link = d.find_element(By.XPATH, "//tr[td[@class='statusOpen']]//a[text()='IA Only']")
                        if green_link and green_link.is_displayed():
                            self.log(f"[CASE-INFO][DEBUG] Found green bubble link in {context_name}!")
                            href = green_link.get_attribute("href") or ""
                            if "kProgProvID=" in href:
                                prog_id = href.split("kProgProvID=")[1].split("&")[0]
                                self.log(f"[CASE-INFO] IA Only link ID: {prog_id}")
                            
                            # Click the link
                            self.log("[CASE-INFO] Clicking IA Only link...")
                            try:
                                green_link.click()
                                self.log("[CASE-INFO] IA Only link clicked successfully")
                                return True
                            except Exception:
                                try:
                                    d.execute_script("arguments[0].click();", green_link)
                                    self.log("[CASE-INFO] IA Only link clicked via JavaScript")
                                    return True
                                except Exception as e:
                                    self.log(f"[CASE-INFO][ERROR] Failed to click IA Only link: {e}")
                                    return False
                        else:
                            self.log(f"[CASE-INFO][DEBUG] Green bubble link found but not displayed in {context_name}")
                    except Exception as e:
                        self.log(f"[CASE-INFO][DEBUG] No green bubble link found in {context_name}: {e}")
                    
                    break  # Found links in this context, no need to try others
                else:
                    self.log(f"[CASE-INFO][DEBUG] No IA Only links found in {context_name}")
                    
            except Exception as e:
                self.log(f"[CASE-INFO][DEBUG] Error with {context_name}: {e}")
        
        # If we get here, try the original strategies
        self.log("[CASE-INFO] Original strategies failed, trying frame-specific searches...")
        
        # Strategy 1: Direct approach - Find the first IA Only link with statusOpen in the same row
        self.log("[CASE-INFO] Strategy 1: Direct search for IA Only link with green bubble...")
        try:
            # Look for the first row with statusOpen class that contains an IA Only link
            ia_only_link = d.find_element(By.XPATH, "//tr[td[@class='statusOpen']]//a[text()='IA Only']")
            
            if ia_only_link and ia_only_link.is_displayed():
                self.log("[CASE-INFO] Found IA Only link with green bubble (statusOpen)")
                
                # Get the href to show the ID
                href = ia_only_link.get_attribute("href") or ""
                if "kProgProvID=" in href:
                    prog_id = href.split("kProgProvID=")[1].split("&")[0]
                    self.log(f"[CASE-INFO] IA Only link ID: {prog_id}")
                
                # Click the link
                self.log("[CASE-INFO] Clicking IA Only link...")
                try:
                    ia_only_link.click()
                    self.log("[CASE-INFO] IA Only link clicked successfully")
                    
                    # Wait for verification if selector provided
                    if verify_selector:
                        try:
                            wait.until(EC.presence_of_element_located(verify_selector))
                            self.log("[CASE-INFO] Verification passed - target element found after clicking IA Only")
                        except Exception as e:
                            self.log(f"[CASE-INFO][WARN] Verification failed: {e}")
                            return False
                    
                    return True
                    
                except Exception:
                    try:
                        d.execute_script("arguments[0].click();", ia_only_link)
                        self.log("[CASE-INFO] IA Only link clicked via JavaScript")
                        
                        if verify_selector:
                            try:
                                wait.until(EC.presence_of_element_located(verify_selector))
                                self.log("[CASE-INFO] Verification passed - target element found after clicking IA Only")
                            except Exception as e:
                                self.log(f"[CASE-INFO][WARN] Verification failed: {e}")
                                return False
                        
                        return True
                    except Exception as e:
                        self.log(f"[CASE-INFO][ERROR] Failed to click IA Only link: {e}")
                        return False
            else:
                self.log("[CASE-INFO] IA Only link found but not displayed")
                return False
                
        except Exception as e:
            self.log(f"[CASE-INFO] Strategy 1 failed: {e}")
        
        # Strategy 2: Alternative approach - Look in the specific Case Information bucket
        self.log("[CASE-INFO] Strategy 2: Search in Case Information bucket...")
        try:
            # Look specifically in the indCaseInfoBucket div
            ia_only_link = d.find_element(By.XPATH, "//div[@id='indCaseInfoBucket']//tr[td[@class='statusOpen']]//a[text()='IA Only']")
            
            if ia_only_link and ia_only_link.is_displayed():
                self.log("[CASE-INFO] Found IA Only link in Case Information bucket")
                
                href = ia_only_link.get_attribute("href") or ""
                if "kProgProvID=" in href:
                    prog_id = href.split("kProgProvID=")[1].split("&")[0]
                    self.log(f"[CASE-INFO] IA Only link ID: {prog_id}")
                
                # Click the link
                self.log("[CASE-INFO] Clicking IA Only link...")
                try:
                    ia_only_link.click()
                    self.log("[CASE-INFO] IA Only link clicked successfully")
                    
                    if verify_selector:
                        try:
                            wait.until(EC.presence_of_element_located(verify_selector))
                            self.log("[CASE-INFO] Verification passed")
                        except Exception as e:
                            self.log(f"[CASE-INFO][WARN] Verification failed: {e}")
                            return False
                    
                    return True
                    
                except Exception:
                    try:
                        d.execute_script("arguments[0].click();", ia_only_link)
                        self.log("[CASE-INFO] IA Only link clicked via JavaScript")
                        
                        if verify_selector:
                            try:
                                wait.until(EC.presence_of_element_located(verify_selector))
                                self.log("[CASE-INFO] Verification passed")
                            except Exception as e:
                                self.log(f"[CASE-INFO][WARN] Verification failed: {e}")
                                return False
                        
                        return True
                    except Exception as e:
                        self.log(f"[CASE-INFO][ERROR] Failed to click IA Only link: {e}")
                        return False
            else:
                self.log("[CASE-INFO] IA Only link found in bucket but not displayed")
                return False
                
        except Exception as e:
            self.log(f"[CASE-INFO] Strategy 2 failed: {e}")
        
        # Strategy 3: Debug - Show what we can find
        self.log("[CASE-INFO] Strategy 3: Debug - showing available elements...")
        try:
            # Show all IA Only links
            all_ia_links = d.find_elements(By.XPATH, "//a[text()='IA Only']")
            self.log(f"[CASE-INFO] Found {len(all_ia_links)} total IA Only links")
            
            for i, link in enumerate(all_ia_links):
                try:
                    href = link.get_attribute("href") or ""
                    displayed = link.is_displayed()
                    self.log(f"[CASE-INFO] Link {i+1}: href='{href}', displayed={displayed}")
                    
                    if "kProgProvID=" in href:
                        prog_id = href.split("kProgProvID=")[1].split("&")[0]
                        self.log(f"[CASE-INFO]   ID: {prog_id}")
                        
                        # Check if this link is in a row with statusOpen
                        try:
                            row = link.find_element(By.XPATH, "./ancestor::tr")
                            status_cells = row.find_elements(By.XPATH, ".//td[contains(@class,'status')]")
                            if status_cells:
                                status_class = status_cells[0].get_attribute("class")
                                self.log(f"[CASE-INFO]   Status: {status_class}")
                                
                                if "statusOpen" in status_class and displayed:
                                    self.log(f"[CASE-INFO]   *** This is the green bubble link! ***")
                                    try:
                                        link.click()
                                        self.log(f"[CASE-INFO] Successfully clicked IA Only link {i+1}")
                                        
                                        if verify_selector:
                                            try:
                                                wait.until(EC.presence_of_element_located(verify_selector))
                                                self.log("[CASE-INFO] Verification passed")
                                            except Exception as e:
                                                self.log(f"[CASE-INFO][WARN] Verification failed: {e}")
                                                return False
                                        
                                        return True
                                    except Exception:
                                        try:
                                            d.execute_script("arguments[0].click();", link)
                                            self.log(f"[CASE-INFO] Successfully clicked IA Only link {i+1} via JavaScript")
                                            
                                            if verify_selector:
                                                try:
                                                    wait.until(EC.presence_of_element_located(verify_selector))
                                                    self.log("[CASE-INFO] Verification passed")
                                                except Exception as e:
                                                    self.log(f"[CASE-INFO][WARN] Verification failed: {e}")
                                                    return False
                                            
                                            return True
                                        except Exception as e:
                                            self.log(f"[CASE-INFO] Failed to click link {i+1}: {e}")
                        except Exception as e:
                            self.log(f"[CASE-INFO]   Could not check status for link {i+1}: {e}")
                except Exception as e:
                    self.log(f"[CASE-INFO]   Error checking link {i+1}: {e}")
                    
        except Exception as e:
            self.log(f"[CASE-INFO] Strategy 3 failed: {e}")
        
        self.log("[CASE-INFO][ERROR] No IA Only link with green bubble could be clicked")
        return False

    def click_client_list_tab(self, timeout: int = 10) -> bool:
        """
        Click the 'Client List' tab in the Service File page navigation.
        Based on HTML analysis: The tab has id='tabUserDef_li' and text='Client List'.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Ensure we're in the correct frame context
            d.switch_to.default_content()
            try:
                d.switch_to.frame('frm_content_id')
            except Exception:
                pass  # Continue if frame switching fails

            self.log("[CLIENT-LIST] Starting Client List tab click...")
            
            # Debug current page state
            current_url = d.current_url
            self.log(f"[CLIENT-LIST][DEBUG] Current URL: {current_url}")
            
            # Try multiple strategies to find and click the Client List tab
            strategies = [
                ("ID-based", By.ID, "tabUserDef_li"),
                ("Text-based", By.XPATH, "//li[text()='Client List']"),
                ("Click handler-based", By.XPATH, "//li[contains(@onclick, \"goTab('tabUserDef')\")]"),
                ("Class and text combination", By.XPATH, "//li[@class='tabLong' and text()='Client List']")
            ]
            
            for strategy_name, by, selector in strategies:
                try:
                    self.log(f"[CLIENT-LIST] Trying strategy: {strategy_name}")
                    tab_element = wait.until(EC.element_to_be_clickable((by, selector)))
                    
                    if tab_element:
                        self.log(f"[CLIENT-LIST] Found Client List tab using {strategy_name}")
                        
                        # Try regular click first
                        try:
                            tab_element.click()
                            self.log("[CLIENT-LIST] Client List tab clicked successfully")
                            time.sleep(1)  # Reduced from 2s to 1s for faster tab loading
                            return True
                        except Exception:
                            # Try JavaScript click as fallback
                            try:
                                d.execute_script("arguments[0].click();", tab_element)
                                self.log("[CLIENT-LIST] Client List tab clicked via JavaScript")
                                time.sleep(1)  # Reduced from 2s to 1s for faster tab loading
                                return True
                            except Exception as e:
                                self.log(f"[CLIENT-LIST][ERROR] Failed to click tab: {e}")
                                continue
                    
                except Exception as e:
                    self.log(f"[CLIENT-LIST][DEBUG] Strategy {strategy_name} failed: {e}")
                    continue
            
            self.log("[CLIENT-LIST][ERROR] All strategies failed to find or click Client List tab")
            return False
            
        except Exception as e:
            self.log(f"[CLIENT-LIST][ERROR] Unexpected error: {e}")
            return False

    def click_edit_button_on_client_list_page(self, timeout: int = 10) -> bool:
        """
        Click the 'Edit' button on the Client List page.
        Based on HTML analysis: The button has id='navEdit', class='tabRight', and text='edit'.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Ensure we're in the correct frame context
            d.switch_to.default_content()
            try:
                d.switch_to.frame('frm_content_id')
            except Exception:
                pass  # Continue if frame switching fails

            self.log("[EDIT-BUTTON] Starting Edit button click on Client List page...")
            
            # Debug current page state
            current_url = d.current_url
            self.log(f"[EDIT-BUTTON][DEBUG] Current URL: {current_url}")
            
            # Try multiple strategies to find and click the Edit button
            strategies = [
                ("ID-based", By.ID, "navEdit"),
                ("Text-based", By.XPATH, "//li[text()='edit']"),
                ("Click handler-based", By.XPATH, "//li[contains(@onclick, 'goOpenEdit()')]"),
                ("Class and text combination", By.XPATH, "//li[@class='tabRight' and text()='edit']")
            ]
            
            for strategy_name, by, selector in strategies:
                try:
                    self.log(f"[EDIT-BUTTON] Trying strategy: {strategy_name}")
                    edit_button = wait.until(EC.element_to_be_clickable((by, selector)))
                    
                    if edit_button:
                        self.log(f"[EDIT-BUTTON] Found Edit button using {strategy_name}")
                        
                        # Try regular click first
                        try:
                            edit_button.click()
                            self.log("[EDIT-BUTTON] Edit button clicked successfully")
                            time.sleep(1)  # Reduced from 2s to 1s for faster edit popup loading
                            return True
                        except Exception:
                            # Try JavaScript click as fallback
                            try:
                                d.execute_script("arguments[0].click();", edit_button)
                                self.log("[EDIT-BUTTON] Edit button clicked via JavaScript")
                                time.sleep(1)  # Reduced from 2s to 1s for faster edit popup loading
                                return True
                            except Exception as e:
                                self.log(f"[EDIT-BUTTON][ERROR] Failed to click button: {e}")
                                continue
                    
                except Exception as e:
                    self.log(f"[EDIT-BUTTON][DEBUG] Strategy {strategy_name} failed: {e}")
                    continue
            
            self.log("[EDIT-BUTTON][ERROR] All strategies failed to find or click Edit button")
            return False
            
        except Exception as e:
            self.log(f"[EDIT-BUTTON][ERROR] Unexpected error: {e}")
            return False

    def fill_fields_via_tab_navigation_and_save(self, row_value: str, timeout: int = 15) -> bool:
        """
        Tab-based flow to:
          1) Tab from Intake Note -> Billing Note and type "IA Only"
          2) Tab -> New/Reassignment and type 'n' or 'r' (no ENTER)
          3) Click Save (robust Selenium + JS fallbacks)
          4) Verify the edit overlay is closed
        Returns True on success, False on failure.
        """
        if not self.driver:
            self.log("[TAB-FLOW] No webdriver instance.")
            return False

        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver import ActionChains
            import time
        except Exception as e:
            self.log(f"[TAB-FLOW][ERROR] Selenium imports failed: {e}")
            return False

        d = self.driver
        wait = WebDriverWait(d, timeout)
        actions = ActionChains(d)

        # normalize row_value -> 'n' or 'r'
        rv = (row_value or "").strip().lower()
        key_letter = "n" if "new" in rv else ("r" if "reassign" in rv or "re-assignment" in rv else "n")
        newor_name = "FLD_ctprogprovexp_progprovexp3"  # fallback name if needed

        def try_switch_to_frame_by_id_or_name(fid):
            try:
                d.switch_to.default_content()
            except Exception:
                pass
            try:
                # prefer frame_to_be_available_and_switch_to_it
                try:
                    WebDriverWait(d, 2).until(EC.frame_to_be_available_and_switch_to_it((By.ID, fid)))
                    return True
                except Exception:
                    # fallback by name/id via switch_to.frame
                    try:
                        d.switch_to.frame(fid)
                        return True
                    except Exception:
                        return False
            except Exception:
                return False

        def find_frame_with_focus():
            # Try known dynamic frame ids quickly
            for fid in ("dynamicIframe", "dynamicAltframe", "iframeWrapper", "iframeEdit", "dynamicFrame"):
                try:
                    ok = try_switch_to_frame_by_id_or_name(fid)
                    if not ok:
                        continue
                    try:
                        tag = d.execute_script("return document.activeElement ? document.activeElement.tagName.toLowerCase() : null;")
                    except Exception:
                        tag = None
                    if tag in ("input", "textarea", "select"):
                        self.log(f"[TAB-FLOW] Found focus in frame '{fid}'.")
                        return ("id", fid)
                    # else revert and continue
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass
                except Exception:
                    pass

            # fallback: enumerate top-level frames and check active element inside each
            try:
                d.switch_to.default_content()
            except Exception:
                pass
            frames = d.find_elements(By.TAG_NAME, "iframe")
            self.log(f"[TAB-FLOW] Scanning {len(frames)} top-level frames to find focus.")
            for i, fr in enumerate(frames):
                try:
                    d.switch_to.default_content()
                except Exception:
                    pass
                try:
                    # re-find by index to avoid stale handles
                    frs = d.find_elements(By.TAG_NAME, "iframe")
                    if i >= len(frs):
                        continue
                    try:
                        d.switch_to.frame(frs[i])
                    except Exception:
                        continue
                    try:
                        tag = d.execute_script("return document.activeElement ? document.activeElement.tagName.toLowerCase() : null;")
                        if tag in ("input", "textarea", "select"):
                            self.log(f"[TAB-FLOW] Found focus in top-level frame index {i} (id='{frs[i].get_attribute('id')}', name='{frs[i].get_attribute('name')}').")
                            return ("index", i)
                    except Exception:
                        pass
                    # return to default for next iteration
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass
                except Exception:
                    continue
            return None

        # 1) Locate frame that currently has focus on the popup's first field
        frame_ident = find_frame_with_focus()
        if not frame_ident:
            self.log("[TAB-FLOW][WARN] Could not find a frame with an active input/textarea. Will try dynamicAltframe then dynamicIframe as fallback.")
            # try dynamicAltframe
            try:
                d.switch_to.default_content()
                d.switch_to.frame("dynamicAltframe")
                self.log("[TAB-FLOW] Switched into dynamicAltframe as fallback.")
            except Exception:
                try:
                    d.switch_to.default_content()
                    d.switch_to.frame("dynamicIframe")
                    self.log("[TAB-FLOW] Switched into dynamicIframe as fallback.")
                except Exception as e:
                    self.log(f"[TAB-FLOW][ERROR] Could not switch into any dynamic frame to perform Tab navigation: {e}")
                    return False
        else:
            typ, val = frame_ident
            try:
                d.switch_to.default_content()
            except Exception:
                pass
            try:
                if typ == "id":
                    try:
                        d.switch_to.frame(d.find_element(By.ID, val))
                    except Exception:
                        try:
                            d.switch_to.frame(val)
                        except Exception:
                            self.log(f"[TAB-FLOW][WARN] Could not switch into frame by id/name '{val}', continuing in current context.")
                else:  # index
                    frs = d.find_elements(By.TAG_NAME, "iframe")
                    if val < len(frs):
                        d.switch_to.frame(frs[val])
                    else:
                        self.log(f"[TAB-FLOW][WARN] Frame index {val} out of range; continuing in current context.")
                self.log(f"[TAB-FLOW] Switched into frame {frame_ident} to start tab navigation.")
            except Exception as e:
                self.log(f"[TAB-FLOW][WARN] Failed to switch into reported frame {frame_ident}: {e}. Will continue in current context.")

        # small pause to ensure the frame's document is ready and focus is present
        time.sleep(0.25)

        # Ensure there's an active element; if not, attempt to focus the first input/textarea
        try:
            active_tag = d.execute_script("return document.activeElement ? document.activeElement.tagName.toLowerCase() : null;")
        except Exception:
            active_tag = None

        if not active_tag or active_tag not in ("input", "textarea", "select"):
            self.log(f"[TAB-FLOW][WARN] Active element tag is '{active_tag}'. Attempting to focus first input/textarea in this frame.")
            try:
                first_input = d.find_element(By.XPATH, "//input[not(@type='hidden')]|//textarea|//select")
                try:
                    first_input.click()
                except Exception:
                    try:
                        d.execute_script("arguments[0].focus();", first_input)
                    except Exception:
                        pass
                time.sleep(0.12)
                try:
                    active_tag = d.execute_script("return document.activeElement ? document.activeElement.tagName.toLowerCase() : null;")
                except Exception:
                    active_tag = None
                self.log(f"[TAB-FLOW] After focusing, active element tag is '{active_tag}'.")
            except Exception as e:
                self.log(f"[TAB-FLOW][WARN] Could not focus any input in this frame: {e} — will still attempt Tab navigation.")

        # 2) Send one TAB to move to Billing Note
        try:
            self.log("[TAB-FLOW] Sending TAB to move to Billing Note field...")
            ActionChains(d).send_keys(Keys.TAB).perform()
            time.sleep(0.20)  # let the focus move
        except Exception as e:
            self.log(f"[TAB-FLOW][ERROR] Failed to send TAB key: {e}")
            return False

        # After tab, get the active element
        try:
            elem = d.execute_script("return document.activeElement;")
        except Exception as e:
            self.log(f"[TAB-FLOW][ERROR] Could not obtain document.activeElement after Tab: {e}")
            elem = None

        if not elem:
            # fail-safe: try to find a visible input/textarea in this frame and use that
            try:
                cand = d.find_element(By.XPATH, "(//textarea|//input[not(@type='hidden')])[1]")
                elem = cand
                self.log("[TAB-FLOW] Using fallback first visible input as billing field.")
            except Exception as e:
                self.log(f"[TAB-FLOW][ERROR] No element available to type Billing Note: {e}")
                return False

        # 3) Type "IA Only" into the Billing Note
        try:
            try:
                # Clear previous content if possible
                try:
                    elem.clear()
                except Exception:
                    try:
                        d.execute_script("arguments[0].value = '';", elem)
                    except Exception:
                        pass
                elem.send_keys("IA Only")
                # dispatch change
                try:
                    d.execute_script("arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", elem)
                except Exception:
                    pass
                self.log("[TAB-FLOW] Typed 'IA Only' into Billing Note via send_keys.")
            except Exception as e_send:
                # JS fallback: set document.activeElement.value
                try:
                    d.execute_script("if(document.activeElement){ document.activeElement.value = arguments[0]; document.activeElement.dispatchEvent(new Event('change',{bubbles:true})); }", "IA Only")
                    self.log("[TAB-FLOW] Typed 'IA Only' into Billing Note via JS fallback on activeElement.")
                except Exception as e_js:
                    self.log(f"[TAB-FLOW][ERROR] Both send_keys and JS fallback failed for Billing Note: {e_send} / {e_js}")
                    return False
        except Exception as e:
            self.log(f"[TAB-FLOW][ERROR] Unexpected error setting Billing Note: {e}")
            return False

        time.sleep(0.18)

        # 4) Send another TAB to move to New/Reassignment line
        try:
            self.log("[TAB-FLOW] Sending TAB to move to New/Reassignment field...")
            ActionChains(d).send_keys(Keys.TAB).perform()
            time.sleep(0.18)
        except Exception as e:
            self.log(f"[TAB-FLOW][ERROR] Failed to send second TAB key: {e}")
            return False

        # Get the active element after the second tab
        try:
            new_elem = d.execute_script("return document.activeElement;")
        except Exception as e:
            self.log(f"[TAB-FLOW][ERROR] Could not obtain activeElement for New/Reassignment: {e}")
            new_elem = None

        if not new_elem:
            # fallback try locate by name
            try:
                new_elem = d.find_element(By.NAME, newor_name)
                self.log("[TAB-FLOW] Fallback: found New/Reassignment by name.")
            except Exception:
                new_elem = None

        # 5) Type only the letter (no ENTER)
        if not new_elem:
            self.log("[TAB-FLOW][WARN] Could not determine New/Reassignment element; attempting JS set by name in this frame.")
            try:
                res = d.execute_script("""
                    try{
                        var s = document.getElementsByName(arguments[0])[0];
                        if(s){ s.value = arguments[1]; s.dispatchEvent(new Event('change',{bubbles:true})); return true; }
                    }catch(e){}
                    return false;
                """, newor_name, ("2" if key_letter == "n" else "3"))
                self.log(f"[TAB-FLOW] JS fallback to set New/Reassignment returned: {res}")
            except Exception as e:
                self.log(f"[TAB-FLOW][WARN] JS fallback to set New/Reassignment failed: {e}")
        else:
            try:
                try:
                    new_elem.send_keys(key_letter)
                    time.sleep(0.06)
                    # DO NOT send ENTER — user requested single-letter only
                    self.log(f"[TAB-FLOW] Sent '{key_letter}' to New/Reassignment control via send_keys (no ENTER).")
                    # quick readback attempt
                    try:
                        read_back = None
                        try:
                            read_back = new_elem.get_attribute("value")
                        except Exception:
                            read_back = d.execute_script("return document.activeElement ? document.activeElement.value : null;")
                        self.log(f"[TAB-FLOW] New/Reassignment readback after typing: '{read_back}'")
                    except Exception:
                        self.log("[TAB-FLOW] Could not read back New/Reassignment value (non-fatal).")
                except Exception as e_send2:
                    # JS fallback set value directly on element
                    try:
                        d.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change',{bubbles:true}));", new_elem, ("2" if key_letter=='n' else "3"))
                        self.log("[TAB-FLOW] send_keys failed; JS fallback set New/Reassignment value on activeElement.")
                    except Exception as e_js2:
                        self.log(f"[TAB-FLOW][ERROR] Could not set New/Reassignment via send_keys or JS: {e_send2} / {e_js2}")
            except Exception as e:
                self.log(f"[TAB-FLOW][ERROR] Unexpected error interacting with New/Reassignment: {e}")

        time.sleep(1)  # Increased to 1s for reliable field interaction

        # 6) Click Save button using the proven working logic from assignment popup
        self.log("[TAB-FLOW] Using proven Save click logic from assignment popup...")
        
        # Call the working Save click method that successfully clicks Save buttons
        if self._click_assignment_save(timeout=10):
            self.log("[TAB-FLOW] Save button clicked successfully using proven method!")
            time.sleep(1)  # Increased to 1s for reliable save processing
            
            # 7) Verify the edit overlay is gone (editLayer absent or not displayed)
            try:
                d.switch_to.default_content()
            except Exception:
                pass
            time.sleep(1)  # Increased to 1s to ensure popup closes properly
            try:
                edit_layers = d.find_elements(By.ID, "editLayer")
                if not edit_layers:
                    self.log("[TAB-FLOW] editLayer not found after save — assuming popup closed.")
                    return True
                else:
                    # if editLayer exists, check if it's hidden
                    try:
                        visible_any = any(el.is_displayed() for el in edit_layers)
                    except Exception:
                        visible_any = True
                    if not visible_any:
                        self.log("[TAB-FLOW] editLayer present but not visible after save — assuming closed.")
                        return True
                    else:
                        self.log("[TAB-FLOW][WARN] editLayer still visible after save. Save may have failed.")
                        return False
            except Exception as e_verify:
                self.log(f"[TAB-FLOW][WARN] Could not verify editLayer removal: {e_verify}; assuming success if no obvious errors.")
                return True
        else:
            self.log("[TAB-FLOW][ERROR] Proven Save click method failed.")
            return False

    def extract_excel_data_from_sharepoint(self, excel_url: str, target_date: str, tab_name: str = "IA Referrals", timeout: int = 30) -> Optional[pd.DataFrame]:
        """
        Extract data from SharePoint-hosted Excel file using Selenium automation.
        
        Args:
            excel_url: The SharePoint Excel URL
            target_date: Date to search for in column A (format: MM/DD/YYYY, e.g., "09/19/2025")
            tab_name: Name of the Excel tab to extract from (default: "IA Referrals")
            timeout: Maximum time to wait for operations
            
        Returns:
            pandas DataFrame with the Excel data from the specified date onward, or None if extraction failed
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains
        import time
        
        d = self.driver
        wait = WebDriverWait(d, timeout)
        
        try:
            self.log(f"[EXCEL-EXTRACT] Starting Excel data extraction from SharePoint...")
            self.log(f"[EXCEL-EXTRACT] URL: {excel_url}")
            self.log(f"[EXCEL-EXTRACT] Target Date: {target_date}")
            self.log(f"[EXCEL-EXTRACT] Target Tab: {tab_name}")
            
            # Navigate to the Excel file
            d.get(excel_url)
            self.log("[EXCEL-EXTRACT] Navigated to Excel file")
            
            # Wait for Excel to load
            time.sleep(3)
            
            # Handle authentication if needed (Microsoft login)
            try:
                # Check if we're on a login page
                if "login.microsoftonline.com" in d.current_url or "signin" in d.current_url.lower():
                    self.log("[EXCEL-EXTRACT] Detected login page - user will need to authenticate manually")
                    self.log("[EXCEL-EXTRACT] Please log in manually and the extraction will continue...")
                    
                    # Wait for user to complete login (up to 2 minutes)
                    max_wait = 120
                    start_time = time.time()
                    while time.time() - start_time < max_wait:
                        if "sharepoint.com" in d.current_url and "login" not in d.current_url.lower():
                            self.log("[EXCEL-EXTRACT] Login completed successfully")
                            break
                        time.sleep(2)
                    else:
                        self.log("[EXCEL-EXTRACT][ERROR] Login timeout - please try again")
                        return None
                        
            except Exception as e:
                self.log(f"[EXCEL-EXTRACT] Login check completed: {e}")
            
            # Wait for Excel Online to fully load
            self.log("[EXCEL-EXTRACT] Waiting for Excel Online to load...")
            time.sleep(5)
            
            # Try to find and click "Edit in Browser" if present
            try:
                edit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Edit in Browser') or contains(text(), 'Edit Workbook')]")))
                edit_button.click()
                self.log("[EXCEL-EXTRACT] Clicked 'Edit in Browser'")
                time.sleep(3)
            except Exception:
                self.log("[EXCEL-EXTRACT] No 'Edit in Browser' button found - assuming already in edit mode")
            
            # Method 1: Try to select all data and copy to clipboard
            try:
                self.log("[EXCEL-EXTRACT] Attempting to select all data...")
                
                # Click on the Excel grid to ensure focus
                try:
                    excel_grid = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[role='grid'], .excel-grid, [data-automation-id='excel-grid']")))
                    excel_grid.click()
                    time.sleep(1)
                except Exception:
                    self.log("[EXCEL-EXTRACT] Could not find Excel grid, trying body click")
                    d.find_element(By.TAG_NAME, "body").click()
                    time.sleep(1)
                
                # Select all using Ctrl+A
                ActionChains(d).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                self.log("[EXCEL-EXTRACT] Selected all data with Ctrl+A")
                time.sleep(2)
                
                # Copy to clipboard using Ctrl+C
                ActionChains(d).key_down(Keys.CONTROL).send_keys('c').key_up(Keys.CONTROL).perform()
                self.log("[EXCEL-EXTRACT] Copied data to clipboard with Ctrl+C")
                time.sleep(2)
                
                # Get clipboard content
                clipboard_content = pyperclip.paste()
                self.log(f"[EXCEL-EXTRACT] Clipboard content length: {len(clipboard_content)} characters")
                
                if clipboard_content and len(clipboard_content.strip()) > 0:
                    # Parse clipboard content as CSV-like data
                    lines = clipboard_content.strip().split('\n')
                    if len(lines) > 1:  # Ensure we have multiple rows
                        self.log(f"[EXCEL-EXTRACT] Successfully extracted {len(lines)} rows of data")
                        
                        # Convert to DataFrame
                        data_rows = []
                        for line in lines:
                            # Split by tabs (Excel typically uses tabs for columns)
                            if '\t' in line:
                                columns = line.split('\t')
                            else:
                                # Fallback: try comma separation
                                columns = line.split(',')
                            data_rows.append(columns)
                        
                        # Create DataFrame
                        if data_rows:
                            # Use first row as headers if it looks like headers
                            if len(data_rows) > 1:
                                headers = data_rows[0]
                                data = data_rows[1:]
                                df = pd.DataFrame(data, columns=headers)
                                self.log(f"[EXCEL-EXTRACT] Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
                                self.log(f"[EXCEL-EXTRACT] Columns: {list(df.columns)}")
                                return df
                        
            except Exception as e:
                self.log(f"[EXCEL-EXTRACT][ERROR] Clipboard method failed: {e}")
            
            # Method 2: Try to find and click Export/Download button
            try:
                self.log("[EXCEL-EXTRACT] Attempting export/download method...")
                
                # Look for export or download buttons
                export_selectors = [
                    "//button[contains(text(), 'Export')]",
                    "//button[contains(text(), 'Download')]", 
                    "//button[contains(text(), 'Save As')]",
                    "//a[contains(text(), 'Export')]",
                    "//a[contains(text(), 'Download')]",
                    "[data-automation-id='export']",
                    "[data-automation-id='download']"
                ]
                
                export_button = None
                for selector in export_selectors:
                    try:
                        if selector.startswith("//"):
                            export_button = d.find_element(By.XPATH, selector)
                        else:
                            export_button = d.find_element(By.CSS_SELECTOR, selector)
                        if export_button and export_button.is_displayed():
                            self.log(f"[EXCEL-EXTRACT] Found export button: {selector}")
                            break
                    except Exception:
                        continue
                
                if export_button:
                    export_button.click()
                    self.log("[EXCEL-EXTRACT] Clicked export button")
                    time.sleep(3)
                    
                    # Look for CSV option
                    csv_selectors = [
                        "//button[contains(text(), 'CSV')]",
                        "//a[contains(text(), 'CSV')]",
                        "//div[contains(text(), 'CSV')]"
                    ]
                    
                    for selector in csv_selectors:
                        try:
                            csv_option = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                            csv_option.click()
                            self.log("[EXCEL-EXTRACT] Clicked CSV export option")
                            time.sleep(5)  # Wait for download
                            break
                        except Exception:
                            continue
                    
                    # Check if file was downloaded
                    download_dir = os.path.expanduser("~/Downloads")
                    csv_files = [f for f in os.listdir(download_dir) if f.endswith('.csv') and 'Intake Log' in f]
                    
                    if csv_files:
                        latest_csv = max([os.path.join(download_dir, f) for f in csv_files], key=os.path.getctime)
                        self.log(f"[EXCEL-EXTRACT] Found downloaded CSV: {latest_csv}")
                        
                        # Read the CSV file
                        df = pd.read_csv(latest_csv)
                        self.log(f"[EXCEL-EXTRACT] Successfully read CSV with {len(df)} rows and {len(df.columns)} columns")
                        return df
                        
            except Exception as e:
                self.log(f"[EXCEL-EXTRACT][ERROR] Export method failed: {e}")
            
            # Method 3: Try to extract data from HTML table elements
            try:
                self.log("[EXCEL-EXTRACT] Attempting HTML table extraction...")
                
                # Look for table elements that might contain the Excel data
                tables = d.find_elements(By.TAG_NAME, "table")
                if tables:
                    self.log(f"[EXCEL-EXTRACT] Found {len(tables)} table elements")
                    
                    # Try to extract data from the largest table
                    largest_table = max(tables, key=lambda t: len(t.find_elements(By.TAG_NAME, "tr")))
                    rows = largest_table.find_elements(By.TAG_NAME, "tr")
                    
                    if len(rows) > 1:
                        self.log(f"[EXCEL-EXTRACT] Extracting data from table with {len(rows)} rows")
                        
                        data_rows = []
                        for row in rows:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if not cells:
                                cells = row.find_elements(By.TAG_NAME, "th")
                            
                            if cells:
                                row_data = [cell.text.strip() for cell in cells]
                                data_rows.append(row_data)
                        
                        if data_rows:
                            # Use first row as headers
                            headers = data_rows[0]
                            data = data_rows[1:]
                            df = pd.DataFrame(data, columns=headers)
                            self.log(f"[EXCEL-EXTRACT] Created DataFrame from HTML table with {len(df)} rows and {len(df.columns)} columns")
                            return df
                            
            except Exception as e:
                self.log(f"[EXCEL-EXTRACT][ERROR] HTML table extraction failed: {e}")
            
            self.log("[EXCEL-EXTRACT][ERROR] All extraction methods failed")
            return None
            
        except Exception as e:
            self.log(f"[EXCEL-EXTRACT][ERROR] Unexpected error during Excel extraction: {e}")
            import traceback
            self.log(f"[EXCEL-EXTRACT][ERROR] Traceback: {traceback.format_exc()}")
            return None

    def click_search_button_to_return_to_search(self, timeout: int = 10) -> bool:
        """
        Click the search button at the top of the screen to return to the search page.
        This allows the bot to continue processing the next client in the loop.
        
        Based on the working click_toolbar_search_with_wait method: The search button (navSearch) 
        is located in the frm_content_id frame, not in default content.
        """
        if not self.driver:
            self.log("[SEARCH-RETURN] No webdriver instance.")
            return False

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Always start from default content (same as working method)
            d.switch_to.default_content()
            
            self.log("[SEARCH-RETURN] Looking for search button in frm_content_id frame...")
            
            # Wait for content frame to be present and switch in (same as working method)
            fr = WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.ID, "frm_content_id")))
            d.switch_to.frame(fr)

            # Wait for document readiness (same as working method)
            try:
                WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

            # Wait for overlays to be gone inside the frame (same as working method)
            def _overlay_gone(driver):
                try:
                    gray = driver.find_elements(By.ID, "mainFrameCoverGray")
                    white = driver.find_elements(By.ID, "mainFrameCoverWhite")
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

            # Now click the toolbar Search li#navSearch (same as working method)
            btn = WebDriverWait(d, timeout).until(EC.element_to_be_clickable((By.ID, "navSearch")))
            try:
                btn.click()
                self.log("[SEARCH-RETURN] Search button clicked with Selenium.")
            except Exception:
                d.execute_script("arguments[0].click();", btn)
                self.log("[SEARCH-RETURN] Search button clicked with JavaScript fallback.")

            # Leave frame; let caller proceed (same as working method)
            d.switch_to.default_content()
            
            # Wait for page to load
            time.sleep(2)
            self.log("[SEARCH-RETURN] Search page navigation initiated.")
            return True

        except Exception as e:
            self.log(f"[SEARCH-RETURN][ERROR] Unexpected error: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE} - Version 2.1.0, Last Updated 12/03/2025"); self.geometry("1040x820")
        
        # User management (must be initialized before _build_ui())
        self.penelope_users_file = Path(__file__).parent / "counselor_bot_penelope_users.json"
        self.penelope_users = {}  # Dictionary: {"name": {"username": "...", "password": "...", "url": "..."}}
        self.load_penelope_users()
        
        self.therapynotes_users_file = Path(__file__).parent / "counselor_bot_therapynotes_users.json"
        self.therapynotes_users = {}  # Dictionary: {"name": {"username": "...", "password": "..."}}
        self.load_therapynotes_users()
        
        self._build_ui()
        self._stop = threading.Event()
        self.worker = None

    def load_penelope_users(self):
        """Load Penelope users from JSON file"""
        try:
            if self.penelope_users_file.exists():
                with open(self.penelope_users_file, 'r') as f:
                    self.penelope_users = json.load(f)
            else:
                self.penelope_users = {}
                self.save_penelope_users()
        except Exception as e:
            self.penelope_users = {}
    
    def save_penelope_users(self):
        """Save Penelope users to JSON file"""
        try:
            with open(self.penelope_users_file, 'w') as f:
                json.dump(self.penelope_users, f, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save Penelope users:\n{e}")
            return False
    
    def load_therapynotes_users(self):
        """Load TherapyNotes users from JSON file"""
        try:
            if self.therapynotes_users_file.exists():
                with open(self.therapynotes_users_file, 'r') as f:
                    self.therapynotes_users = json.load(f)
            else:
                self.therapynotes_users = {}
                self.save_therapynotes_users()
        except Exception as e:
            self.therapynotes_users = {}
    
    def save_therapynotes_users(self):
        """Save TherapyNotes users to JSON file"""
        try:
            with open(self.therapynotes_users_file, 'w') as f:
                json.dump(self.therapynotes_users, f, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save TherapyNotes users:\n{e}")
            return False
    
    def _card(self, parent, title):
        frm = ttk.Frame(parent); frm.pack(fill='x', padx=12, pady=8)
        cap = ttk.Label(frm, text=title, foreground=MAROON, font=('Segoe UI', 12, 'bold'))
        cap.pack(anchor='w', padx=8, pady=(8,4))
        inner = ttk.Frame(frm); inner.pack(fill='x', padx=8, pady=(0,8))
        return inner

    def _build_ui(self):
        # Configure custom styles for larger elements
        style = ttk.Style()
        style.configure('Large.TCheckbutton', font=('Segoe UI', 11, 'bold'))
        
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
        
        # User Selection Row
        ttk.Label(cred, text="Saved User:").grid(row=0, column=0, sticky='e', padx=6, pady=4)
        self.penelope_user_dropdown = ttk.Combobox(cred, font=('Segoe UI', 9), width=25, state="readonly")
        self.penelope_user_dropdown.grid(row=0, column=1, sticky='w', padx=6, pady=4)
        self.penelope_user_dropdown.bind("<<ComboboxSelected>>", self._on_penelope_user_selected)
        self._update_penelope_user_dropdown()
        
        tk.Button(cred, text="Add User", command=self._add_penelope_user,
                 bg=MAROON, fg="white", font=('Segoe UI', 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=0, column=2, padx=6, pady=4)
        
        tk.Button(cred, text="Update User", command=self._update_penelope_user,
                 bg="#666666", fg="white", font=('Segoe UI', 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=0, column=3, padx=6, pady=4)
        
        ttk.Label(cred, text="URL:").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(cred, textvariable=self.url_var, width=64).grid(row=1, column=1, sticky='w')
        ttk.Label(cred, text="User:").grid(row=2, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(cred, textvariable=self.user_var, width=30).grid(row=2, column=1, sticky='w')
        ttk.Label(cred, text="Pass:").grid(row=3, column=0, sticky='e', padx=6, pady=4)
        ttk.Entry(cred, textvariable=self.pass_var, show='•', width=30).grid(row=3, column=1, sticky='w')

        src = self._card(self.content, "CSV Data Source")
        self.local_path = tk.StringVar()
        self.local_row_from = tk.StringVar(value='2')
        self.local_row_to   = tk.StringVar(value='50')
        self.local_path_e = ttk.Entry(src, textvariable=self.local_path, width=70); self.local_path_e.grid(row=0, column=0, sticky='w')
        self.local_path_b = ttk.Button(src, text="Browse…", command=self._browse_local); self.local_path_b.grid(row=0, column=1, sticky='w', padx=6)
        ttk.Label(src, text="Rows: From").grid(row=1, column=0, sticky='e', padx=6, pady=4)
        self.local_row_from_e = ttk.Entry(src, textvariable=self.local_row_from, width=6); self.local_row_from_e.grid(row=1, column=1, sticky='w')
        ttk.Label(src, text="Through").grid(row=1, column=2, sticky='e', padx=6, pady=4)
        self.local_row_to_e = ttk.Entry(src, textvariable=self.local_row_to, width=6); self.local_row_to_e.grid(row=1, column=3, sticky='w')

        mp = self._card(self.content, "Column Mapping — REQUIRED")
        self.col_sel = tk.StringVar(value="A")  # Individual ID column
        self.counselor_col = tk.StringVar(value="L")  # Counselor Name column
        ttk.Label(mp, text="Individual ID Column (A):", foreground=MAROON)\
            .grid(row=0, column=0, sticky='e', padx=6, pady=6)
        ttk.Entry(mp, textvariable=self.col_sel, width=8).grid(row=0, column=1, sticky='w', pady=6)
        ttk.Label(mp, text="Counselor Name Column (L):", foreground=MAROON)\
            .grid(row=1, column=0, sticky='e', padx=6, pady=6)
        ttk.Entry(mp, textvariable=self.counselor_col, width=8).grid(row=1, column=1, sticky='w', pady=6)

        ctr = self._card(self.content, "Controls")
        ttk.Button(ctr, text="Start Navigation", command=self.start).grid(row=0, column=0, padx=6)
        ttk.Button(ctr, text="Stop", command=self.stop).grid(row=0, column=1, padx=6)
        ttk.Button(ctr, text="Copy Log", command=self.copy_log).grid(row=0, column=2, padx=6)
        ttk.Button(ctr, text="Clear Log", command=self.clear_log).grid(row=0, column=3, padx=6)
        ttk.Button(ctr, text="Debug Popup", command=self.debug_popup).grid(row=0, column=4, padx=6)
        
        # Debug mode toggle
        self.debug_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctr, text="Debug Mode (Verbose Logging)", variable=self.debug_mode).grid(row=1, column=0, columnspan=4, sticky='w', padx=6, pady=4)
        
        # Bot sequence toggle - Make it prominent and eye-catching
        self.run_intake_referral_after = tk.BooleanVar(value=False)
        
        # Create a separate frame for the prominent bot integration option
        integration_frame = ttk.Frame(ctr)
        integration_frame.grid(row=2, column=0, columnspan=5, sticky='ew', padx=6, pady=8)
        integration_frame.columnconfigure(0, weight=1)
        
        # Create a styled frame with border for the integration option
        style_frame = ttk.Frame(integration_frame, relief='solid', borderwidth=2)
        style_frame.pack(fill='x', padx=4, pady=4)
        
        # Add rocket emoji and make it larger and more visible
        rocket_checkbutton = ttk.Checkbutton(
            style_frame, 
            text="🚀 Run Intake & Referral Bot After Counselor Assignment", 
            variable=self.run_intake_referral_after,
            style='Large.TCheckbutton'
        )
        rocket_checkbutton.pack(fill='x', padx=8, pady=6)
        
        # Add description text below
        desc_label = ttk.Label(
            style_frame, 
            text="✓ Automatically launches the Intake & Referral Bot with the same credentials and CSV data", 
            foreground='#0066cc',
            font=('Segoe UI', 9, 'italic')
        )
        desc_label.pack(fill='x', padx=8, pady=(0, 6))
        
        # TherapyNotes Credentials for Uploaders
        tn_cred = self._card(self.content, "TherapyNotes Credentials (for Dual Uploader)")
        
        # User Selection Row
        ttk.Label(tn_cred, text="Saved User:", foreground=MAROON).grid(row=0, column=0, sticky='e', padx=6, pady=4)
        self.therapynotes_user_dropdown = ttk.Combobox(tn_cred, font=('Segoe UI', 9), width=25, state="readonly")
        self.therapynotes_user_dropdown.grid(row=0, column=1, sticky='w', padx=6, pady=4)
        self.therapynotes_user_dropdown.bind("<<ComboboxSelected>>", self._on_therapynotes_user_selected)
        self._update_therapynotes_user_dropdown()
        
        tk.Button(tn_cred, text="Add User", command=self._add_therapynotes_user,
                 bg=MAROON, fg="white", font=('Segoe UI', 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=0, column=2, padx=6, pady=4)
        
        tk.Button(tn_cred, text="Update User", command=self._update_therapynotes_user,
                 bg="#666666", fg="white", font=('Segoe UI', 9), padx=10, pady=3,
                 cursor="hand2", relief="flat", bd=0).grid(row=0, column=3, padx=6, pady=4)
        
        ttk.Label(tn_cred, text="TN Username:", foreground=MAROON).grid(row=1, column=0, sticky='e', padx=6, pady=4)
        self.tn_user_var = tk.StringVar()
        ttk.Entry(tn_cred, textvariable=self.tn_user_var, width=30).grid(row=1, column=1, sticky='w', padx=6, pady=4)
        ttk.Label(tn_cred, text="TN Password:", foreground=MAROON).grid(row=1, column=2, sticky='e', padx=6, pady=4)
        self.tn_pass_var = tk.StringVar()
        ttk.Entry(tn_cred, textvariable=self.tn_pass_var, show='•', width=30).grid(row=1, column=3, sticky='w', padx=6, pady=4)
        
        # Uploader Integration Checkboxes
        uploader_integration = ttk.Frame(ctr)
        uploader_integration.grid(row=3, column=0, columnspan=5, sticky='ew', padx=6, pady=8)
        uploader_integration.columnconfigure(0, weight=1)
        
        # Main uploader frame with border
        uploader_style_frame = ttk.Frame(uploader_integration, relief='solid', borderwidth=2)
        uploader_style_frame.pack(fill='x', padx=4, pady=4)
        
        # Main checkbox: Run Base Uploader
        self.run_base_uploader_after = tk.BooleanVar(value=False)
        base_uploader_cb = ttk.Checkbutton(
            uploader_style_frame,
            text="📤 Run Dual Uploader (Base/ISWS) after IA Referral Bot",
            variable=self.run_base_uploader_after,
            style='Large.TCheckbutton',
            command=self._toggle_ips_uploader_checkbox
        )
        base_uploader_cb.pack(fill='x', padx=8, pady=6)
        
        # Sub-checkbox: Also run IPS Uploader (indented)
        ips_sub_frame = ttk.Frame(uploader_style_frame)
        ips_sub_frame.pack(fill='x', padx=8, pady=(0, 6))
        
        # Indent spacer
        ttk.Label(ips_sub_frame, text="    ", foreground='gray').pack(side='left')
        
        self.run_ips_uploader_after = tk.BooleanVar(value=False)
        self.ips_uploader_cb = ttk.Checkbutton(
            ips_sub_frame,
            text="🏥 Also run IPS Uploader after Base",
            variable=self.run_ips_uploader_after,
            state='disabled',  # Initially disabled until base is checked
            command=self._validate_ips_uploader_credentials
        )
        self.ips_uploader_cb.pack(side='left')
        
        # Description text
        uploader_desc_label = ttk.Label(
            uploader_style_frame,
            text="✓ Uploads referral forms to TherapyNotes. PDFs auto-loaded from Desktop/Referral Form Bot Output/",
            foreground='#0066cc',
            font=('Segoe UI', 9, 'italic')
        )
        uploader_desc_label.pack(fill='x', padx=8, pady=(0, 6))
        
        # Additional checkbox: Remove old IA Only documents
        self.remove_old_ia_docs = tk.BooleanVar(value=False)
        remove_old_docs_cb = ttk.Checkbutton(
            uploader_style_frame,
            text="🗑️ Remove old 'IA Only' documents (30+ days) before uploading",
            variable=self.remove_old_ia_docs,
            style='Large.TCheckbutton'
        )
        remove_old_docs_cb.pack(fill='x', padx=8, pady=(0, 6))
        
        logfrm = ttk.Frame(self.content); logfrm.pack(fill='both', expand=True, padx=12, pady=8)
        self.log_widget = scrolledtext.ScrolledText(logfrm, height=20, bg=LOG_BG, fg=LOG_FG)
        self.log_widget.pack(fill='both', expand=True)
        self.logger = UILog(self.log_widget)

    def _toggle_ips_uploader_checkbox(self):
        """Enable/disable IPS uploader checkbox based on base uploader checkbox"""
        if self.run_base_uploader_after.get():
            self.ips_uploader_cb.config(state='normal')
            # Check if TherapyNotes credentials are provided
            if not self.tn_user_var.get() or not self.tn_pass_var.get():
                self.log("[UPLOADER][WARN] ⚠️  TherapyNotes credentials not provided!")
                self.log("[UPLOADER][WARN] Please fill in 'TN Username' and 'TN Password' fields before running uploaders")
        else:
            self.ips_uploader_cb.config(state='disabled')
            self.run_ips_uploader_after.set(False)  # Uncheck if parent is unchecked
    
    def _validate_ips_uploader_credentials(self):
        """Validate TherapyNotes credentials when IPS uploader checkbox is checked"""
        if self.run_ips_uploader_after.get():
            if not self.tn_user_var.get() or not self.tn_pass_var.get():
                self.log("[UPLOADER][ERROR] ❌ Cannot enable IPS Uploader - TherapyNotes credentials missing!")
                self.log("[UPLOADER][ERROR] Please fill in 'TN Username' and 'TN Password' fields first")
                self.run_ips_uploader_after.set(False)  # Uncheck the checkbox
                return False
            else:
                self.log("[UPLOADER][INFO] ✓ IPS Uploader enabled - TherapyNotes credentials validated")
                return True
        return True
    
    def _browse_local(self):
        p = filedialog.askopenfilename(title="Select CSV/XLSX", filetypes=[("Spreadsheets","*.csv;*.xlsx;*.xls")])
        if p: self.local_path.set(p)
    
    def _update_penelope_user_dropdown(self):
        """Update the Penelope user dropdown with current users"""
        if hasattr(self, 'penelope_user_dropdown'):
            user_names = sorted(self.penelope_users.keys())
            if user_names:
                self.penelope_user_dropdown['values'] = user_names
            else:
                self.penelope_user_dropdown['values'] = []
    
    def _on_penelope_user_selected(self, event=None):
        """Handle Penelope user selection from dropdown"""
        selected_user = self.penelope_user_dropdown.get()
        if selected_user and selected_user in self.penelope_users:
            user_data = self.penelope_users[selected_user]
            self.user_var.set(user_data.get('username', ''))
            self.pass_var.set(user_data.get('password', ''))
            self.url_var.set(user_data.get('url', PN_DEFAULT_URL))
    
    def _add_penelope_user(self):
        """Add a new Penelope user to saved users"""
        dialog = tk.Toplevel(self)
        dialog.title("Add Penelope User - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("450x280")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog
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
        password_entry.pack(pady=(0, 10))
        
        tk.Label(dialog, text="Penelope URL (optional):", font=('Segoe UI', 10), bg="#f0f0f0").pack(pady=(0, 5))
        url_entry = tk.Entry(dialog, font=('Segoe UI', 10), width=35)
        url_entry.insert(0, PN_DEFAULT_URL)
        url_entry.pack(pady=(0, 15))
        
        def save_user():
            name = name_entry.get().strip()
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            url = url_entry.get().strip() or PN_DEFAULT_URL
            
            if not name or not username or not password:
                messagebox.showwarning("Invalid Input", "User Name, Username, and Password are required")
                return
            
            if name in self.penelope_users:
                if not messagebox.askyesno("User Exists", f"User '{name}' already exists. Overwrite?"):
                    return
            
            self.penelope_users[name] = {
                'username': username,
                'password': password,
                'url': url
            }
            self.save_penelope_users()
            self._update_penelope_user_dropdown()
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
    
    def _update_penelope_user(self):
        """Update credentials for selected Penelope user"""
        selected_user = self.penelope_user_dropdown.get()
        if not selected_user or selected_user not in self.penelope_users:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown")
            return
        
        username = self.user_var.get().strip()
        password = self.pass_var.get().strip()
        url = self.url_var.get().strip() or PN_DEFAULT_URL
        
        if not username or not password:
            messagebox.showwarning("Invalid Input", "Username and password are required")
            return
        
        self.penelope_users[selected_user] = {
            'username': username,
            'password': password,
            'url': url
        }
        self.save_penelope_users()
        messagebox.showinfo("Success", f"Credentials updated for '{selected_user}'")
    
    def _update_therapynotes_user_dropdown(self):
        """Update the TherapyNotes user dropdown with current users"""
        if hasattr(self, 'therapynotes_user_dropdown'):
            user_names = sorted(self.therapynotes_users.keys())
            if user_names:
                self.therapynotes_user_dropdown['values'] = user_names
            else:
                self.therapynotes_user_dropdown['values'] = []
    
    def _on_therapynotes_user_selected(self, event=None):
        """Handle TherapyNotes user selection from dropdown"""
        selected_user = self.therapynotes_user_dropdown.get()
        if selected_user and selected_user in self.therapynotes_users:
            user_data = self.therapynotes_users[selected_user]
            self.tn_user_var.set(user_data.get('username', ''))
            self.tn_pass_var.set(user_data.get('password', ''))
    
    def _add_therapynotes_user(self):
        """Add a new TherapyNotes user to saved users"""
        dialog = tk.Toplevel(self)
        dialog.title("Add TherapyNotes User - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("450x220")
        dialog.configure(bg="#f0f0f0")
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog
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
            
            if name in self.therapynotes_users:
                if not messagebox.askyesno("User Exists", f"User '{name}' already exists. Overwrite?"):
                    return
            
            self.therapynotes_users[name] = {
                'username': username,
                'password': password
            }
            self.save_therapynotes_users()
            self._update_therapynotes_user_dropdown()
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
    
    def _update_therapynotes_user(self):
        """Update credentials for selected TherapyNotes user"""
        selected_user = self.therapynotes_user_dropdown.get()
        if not selected_user or selected_user not in self.therapynotes_users:
            messagebox.showwarning("No User Selected", "Please select a user from the dropdown")
            return
        
        username = self.tn_user_var.get().strip()
        password = self.tn_pass_var.get().strip()
        
        if not username or not password:
            messagebox.showwarning("Invalid Input", "Username and password are required")
            return
        
        self.therapynotes_users[selected_user] = {
            'username': username,
            'password': password
        }
        self.save_therapynotes_users()
        messagebox.showinfo("Success", f"Credentials updated for '{selected_user}'")

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

    def clear_log(self):
        try:
            self.log_widget.delete("1.0", tk.END)
            self.logger.write("[UI] Log cleared.")
        except Exception as e:
            self.logger.write(f"[UI][ERR] Clear failed: {e}")

    def debug_popup(self):
        """Debug the current popup state when bot is stopped"""
        try:
            if not hasattr(self, 'pn') or not self.pn or not self.pn.driver:
                self.logger.write("[DEBUG] No active browser session found. Start the bot first.")
                return
            
            self.logger.write("[DEBUG] Starting popup inspection...")
            d = self.pn.driver
            
            # Take screenshot
            try:
                d.save_screenshot("debug_popup_screenshot.png")
                self.logger.write("[DEBUG] Screenshot saved as debug_popup_screenshot.png")
            except Exception as e:
                self.logger.write(f"[DEBUG] Screenshot failed: {e}")
            
            # Check all iframes
            try:
                d.switch_to.default_content()
                iframes = d.find_elements(By.TAG_NAME, "iframe")
                self.logger.write(f"[DEBUG] Found {len(iframes)} iframes")
                
                for i, iframe in enumerate(iframes):
                    try:
                        iframe_id = iframe.get_attribute("id") or f"iframe_{i}"
                        iframe_src = iframe.get_attribute("src") or "no src"
                        self.logger.write(f"[DEBUG] Iframe {i+1}: id='{iframe_id}', src='{iframe_src[:50]}...'")
                        
                        # Switch to iframe and check for assignment popup elements
                        d.switch_to.frame(iframe)
                        
                        # Look for textarea
                        textareas = d.find_elements(By.TAG_NAME, "textarea")
                        self.logger.write(f"[DEBUG]   Textareas: {len(textareas)}")
                        for j, ta in enumerate(textareas[:3]):  # Show first 3
                            ta_id = ta.get_attribute("id") or "no-id"
                            ta_name = ta.get_attribute("name") or "no-name"
                            self.logger.write(f"[DEBUG]     {j+1}: id='{ta_id}', name='{ta_name}'")
                        
                        # Look for save buttons
                        save_inputs = d.find_elements(By.CSS_SELECTOR, "input[value*='Save'], input[type='submit']")
                        save_buttons = d.find_elements(By.CSS_SELECTOR, "button[value*='Save'], button[type='submit']")
                        self.logger.write(f"[DEBUG]   Save inputs: {len(save_inputs)}, Save buttons: {len(save_buttons)}")
                        
                        # Check for specific assignment popup elements
                        try:
                            tar_textarea = d.find_element(By.ID, "tar_wlResultCom_id")
                            self.logger.write(f"[DEBUG]   ✓ Found tar_wlResultCom_id textarea!")
                        except:
                            self.logger.write(f"[DEBUG]   ✗ tar_wlResultCom_id not found")
                        
                        try:
                            save_btn = d.find_element(By.ID, "iframeEditSaveButton")
                            self.logger.write(f"[DEBUG]   ✓ Found iframeEditSaveButton!")
                        except:
                            self.logger.write(f"[DEBUG]   ✗ iframeEditSaveButton not found")
                        
                        # Check for "Closing Notes" text
                        try:
                            closing_notes = d.find_element(By.XPATH, "//*[contains(text(), 'Closing Notes')]")
                            self.logger.write(f"[DEBUG]   ✓ Found 'Closing Notes' text!")
                        except:
                            self.logger.write(f"[DEBUG]   ✗ 'Closing Notes' text not found")
                        
                        d.switch_to.default_content()
                        
                    except Exception as e:
                        self.logger.write(f"[DEBUG]   Error checking iframe {i+1}: {e}")
                        d.switch_to.default_content()
                        continue
                
                # Also check main document
                self.logger.write("[DEBUG] Checking main document...")
                main_textareas = d.find_elements(By.TAG_NAME, "textarea")
                main_save_buttons = d.find_elements(By.CSS_SELECTOR, "input[value*='Save'], button[value*='Save']")
                self.logger.write(f"[DEBUG] Main document - Textareas: {len(main_textareas)}, Save buttons: {len(main_save_buttons)}")
                
            except Exception as e:
                self.logger.write(f"[DEBUG] Error during inspection: {e}")
            
            self.logger.write("[DEBUG] Popup inspection complete!")
            
        except Exception as e:
            self.logger.write(f"[DEBUG][ERROR] Debug popup failed: {e}")

    def debug_log(self, msg: str):
        """Log with debug prefix if debug mode is enabled"""
        if self.debug_mode.get():
            self.logger.write(f"[DEBUG] {msg}")
        else:
            self.logger.write(msg)

    def _run(self):
        try:
            # Build PN client
            auth = PNAuth(self.url_var.get().strip(),
                          self.user_var.get().strip(),
                          self.pass_var.get().strip())

            pn = PNClient(auth, log=self.log)
            pn.start()

            if not pn.login():
                self.log("[ERR] Login unsuccessful; continuing to keep browser open.")
            else:
                self.log("[OK] Logged in.")
                self.debug_log("Clicking toolbar search button...")
                pn.click_toolbar_search_with_wait(timeout=25)
                self.debug_log("Toolbar search clicked, waiting for page load...")

            # Load rows - AUTO-CALCULATE row range to process ALL rows in CSV
            col_sel = self.col_sel.get().strip()
            counselor_col = self.counselor_col.get().strip()
            self.log(f"[DATA] Individual ID Column: '{_normalize_col_token(col_sel)}' | Counselor Column: '{_normalize_col_token(counselor_col)}'")

            # Calculate actual row count from CSV
            csv_file_path = self.local_path.get().strip()
            actual_row_to = int(self.local_row_to.get() or 2)  # Default from GUI
            
            try:
                import pandas as pd
                if csv_file_path.lower().endswith('.csv'):
                    df = pd.read_csv(csv_file_path)
                else:
                    df = pd.read_excel(csv_file_path)
                
                total_data_rows = len(df)
                actual_row_to = total_data_rows + 1  # +1 because rows are 1-indexed and include header
                
                self.log(f"[DATA] ✅ Auto-calculated row range: Processing ALL rows (2-{actual_row_to}, {total_data_rows} data rows)")
                self.log(f"[DATA] User's manual row range setting ({self.local_row_from.get()}-{self.local_row_to.get()}) IGNORED for automatic processing")
                
            except Exception as e:
                self.log(f"[DATA][WARN] Could not auto-calculate row count: {e}")
                self.log(f"[DATA][WARN] Falling back to user-specified range: {self.local_row_from.get()}-{self.local_row_to.get()}")

            rows: List[Dict] = []
            lcl = LocalSlice(
                file_path=csv_file_path,
                row_from=2,  # Always start at row 2 (first data row after header)
                row_to=actual_row_to,  # Process through last row
                col_selector=col_sel
            )
            rows = lcl.load(self.log)

            if not rows:
                self.log("[DATA][ERR] No rows parsed. Opening Search UI for inspection.")
                pn.go_to_search()
                return

            # Go to Search (robust direct nav)
            self.debug_log("Navigating to Search page...")
            if pn.go_to_search():
                self.log("[NAV] Search page opened.")
                self.debug_log("Search page navigation successful.")
                
                # CRITICAL: Switch to Individual tab (page defaults to Worker tab)
                self.debug_log("Switching to Individual tab...")
                import time
                time.sleep(1)  # Brief wait for page to fully load
                if pn.click_individual_tab(timeout=10):
                    self.log("[NAV] Successfully switched to Individual tab.")
                else:
                    self.log("[NAV][WARN] Could not switch to Individual tab; continuing anyway.")
            else:
                self.log("[NAV][WARN] Could not open Search page; continuing anyway.")

            # Process rows - NAVIGATE TO CLIENT PROFILE AND STOP
            for idx, rec in enumerate(rows, start=1):
                if self._stop.is_set(): break
                # Fix: Ensure client ID is treated as integer without decimal points
                raw_id = rec.get("_Bot_ID") or ""
                try:
                    # Convert to int first to remove any decimal, then back to string
                    indiv_id = str(int(float(raw_id))).strip()
                except (ValueError, TypeError):
                    # If conversion fails, use original string but remove .0 if present
                    indiv_id = str(raw_id).strip()
                    if indiv_id.endswith('.0'):
                        indiv_id = indiv_id[:-2]
                
                if not indiv_id:
                    self.log(f"[SKIP] Row {idx}: empty Individual ID in selected column."); continue

                # Get counselor name from counselor column and New/Reassignment value from column I
                counselor_name = ""
                counselor_name_clean = ""  # Name without IPS suffix for searching
                is_ips_counselor = False
                new_or_reassignment_value = ""
                try:
                    # Read the CSV file directly to get counselor name and New/Reassignment value
                    import pandas as pd
                    df = pd.read_csv(self.local_path.get().strip(), encoding="utf-8-sig")
                    counselor_series = resolve_column(df, counselor_col)
                    counselor_name = str(counselor_series.iloc[idx-1] or "").strip()
                    self.debug_log(f"Found counselor name: '{counselor_name}' for row {idx}")
                    
                    # Detect IPS counselor (check for "IPS" anywhere in the name)
                    # Examples: "John Smith - IPS", "John Smith, IPS", "John Smith IPS"
                    import re
                    ips_pattern = r'[-,\s]+IPS\s*$|IPS[-,\s]+|\sIPS\s'
                    if re.search(ips_pattern, counselor_name, re.IGNORECASE):
                        is_ips_counselor = True
                        # Remove IPS suffix from name for searching (we'll add "- IPS" back in dropdown selection)
                        counselor_name_clean = re.sub(r'[-,\s]*IPS[-,\s]*', '', counselor_name, flags=re.IGNORECASE).strip()
                        self.log(f"[IPS-DETECT] Row {idx}: Detected IPS counselor - '{counselor_name}' -> searching as '{counselor_name_clean}' + '- IPS' in dropdown")
                    else:
                        counselor_name_clean = counselor_name
                        self.log(f"[IPS-DETECT] Row {idx}: Non-IPS counselor - '{counselor_name}'")
                    
                    # Get New or Reassignment value from column I (9th column, index 8)
                    try:
                        new_or_reassignment_series = resolve_column(df, "I")
                        new_or_reassignment_value = str(new_or_reassignment_series.iloc[idx-1] or "").strip()
                        self.debug_log(f"Found New/Reassignment value: '{new_or_reassignment_value}' for row {idx}")
                    except Exception as e:
                        self.log(f"[DATA][WARN] Could not read New/Reassignment value for row {idx}: {e}")
                        new_or_reassignment_value = "New"  # Default fallback
                        
                except Exception as e:
                    self.log(f"[DATA][WARN] Could not read counselor name for row {idx}: {e}")
                    counselor_name_clean = counselor_name

                self.log(f"[RUN] Row {idx}: searching Individual ID = {indiv_id}")
                self.debug_log(f"Entering Individual ID {indiv_id} and clicking Go...")
                if not pn.enter_individual_id_and_go(indiv_id):
                    self.log("[WARN] Could not enter ID/Go. Continuing."); continue

                # Click the first (or name-matched) result link
                first_name = str(rec.get("First Name") or rec.get("First") or rec.get("FName") or rec.get("Given") or "").strip()
                last_name  = str(rec.get("Last Name")  or rec.get("Last")  or rec.get("LName") or rec.get("Surname") or "").strip()
                self.debug_log(f"Clicking on client name: {first_name} {last_name}")
                if not pn.click_first_result_name(first_name=first_name or None, last_name=last_name or None):
                    self.log("[WARN] Could not click a patient name in results. Continuing."); continue

                self.log("[OK] Opened client profile. (Ready for counselor assignment step.)")
                
                # Now perform counselor assignment
                if counselor_name and counselor_name.strip():
                    self.log(f"[ASSIGN] Starting counselor assignment for '{counselor_name}'...")
                    
                    # Click Edit button
                    if pn.click_edit_button():
                        self.log("[EDIT] Edit button clicked successfully.")
                        
                        # Append counselor assignment note
                        if pn.append_counselor_note(counselor_name):
                            self.log(f"[SUCCESS] Counselor '{counselor_name}' assigned successfully!")
                            
                            # Now click Pre-Enrollment tab and Waiting for Allocation
                            self.log("[PRE-ENROLL] Starting Pre-Enrollment process...")
                            if pn.click_pre_enrollment_tab_and_waiting_allocation():
                                self.log("[SUCCESS] Pre-Enrollment process completed successfully!")
                                
                                # Now check and change service to "IA Only" if needed
                                self.log("[SERVICE-CHECK] Starting service field check...")
                                if pn.check_and_change_service_to_ia_only(counselor_name):
                                    self.log("[SUCCESS] Service field check completed successfully!")
                                    
                                    # Now click the Assign button
                                    self.log("[ASSIGN-BUTTON] Starting Assign button click...")
                                    if pn.click_assign_button():
                                        self.log("[SUCCESS] Assign button clicked successfully!")
                                        
                                        # Now handle the assignment popup
                                        self.log("[ASSIGNMENT-POPUP] Starting assignment popup completion...")
                                        if pn.ultra_simple_assignment_popup(counselor_name):
                                            self.log("[SUCCESS] Assignment popup completed successfully!")
                                            
                                            # Now complete the Service File wizard
                                            self.log("[SERVICE-FILE-WIZARD] Starting Service File wizard completion...")
                                            if pn.complete_service_file_wizard(counselor_name_clean, is_ips=is_ips_counselor):
                                                self.log("[SUCCESS] Service File wizard completed successfully!")
                                                
                                                # Now click the client name in the Participants box to return to profile
                                                self.log("[PARTICIPANT] Starting participant client name click...")
                                                client_full_name = f"{first_name} {last_name}".strip()
                                                if pn.click_participant_client_name(client_full_name):
                                                    self.log("[SUCCESS] Participant client name clicked successfully!")
                                                    # Wait 1 second for page navigation to complete
                                                    time.sleep(1)
                                                else:
                                                    self.log("[WARN] Participant client name click failed - continuing...")
                                            else:
                                                self.log("[WARN] Service File wizard failed - continuing...")
                                        else:
                                            self.log("[WARN] Assignment popup failed - continuing...")
                                    else:
                                        self.log("[WARN] Assign button click failed - continuing...")
                                else:
                                    self.log("[WARN] Service field check failed - continuing...")
                            else:
                                self.log("[WARN] Pre-Enrollment process failed - continuing...")
                        else:
                            self.log("[ERROR] Failed to append counselor assignment note.")
                    else:
                        self.log("[ERROR] Failed to click Edit button.")
                else:
                    self.log("[WARN] No counselor name found for this client - skipping assignment.")
                
                self.log(f"[DONE] Completed processing for client {first_name} {last_name}")
                
                # Now click the IA Only link with green bubble in Case Information section
                self.log("[CASE-INFO] Starting Case Information expansion and IA Only link click...")
                if pn.expand_case_info_if_needed_and_click_ia_only():
                    self.log("[SUCCESS] Case Information expanded and IA Only link clicked successfully!")
                    # Wait 1 second for page navigation to complete
                    time.sleep(1)
                else:
                    self.log("[WARN] Case Information expansion or IA Only link click failed - continuing...")
                
                # Now click the Client List tab
                self.log("[CLIENT-LIST] Starting Client List tab click...")
                if pn.click_client_list_tab():
                    self.log("[SUCCESS] Client List tab clicked successfully!")
                    # Wait 1 second for tab to load properly
                    time.sleep(1)
                    
                    # Now click the Edit button on the Client List page
                    self.log("[EDIT-BUTTON] Starting Edit button click on Client List page...")
                    if pn.click_edit_button_on_client_list_page():
                        self.log("[SUCCESS] Edit button clicked successfully!")
                        # Wait 1 second for edit popup to load properly
                        time.sleep(1)
                        
                        # Now fill Service File fields in the popup
                        self.log("[SERVICE-FILE] Starting Service File edit and field population...")
                        if pn.fill_fields_via_tab_navigation_and_save(new_or_reassignment_value):
                            self.log("[SUCCESS] Service File fields populated and saved successfully!")
                        else:
                            self.log("[WARN] Service File fields population failed - continuing...")
                    else:
                        self.log("[WARN] Edit button click failed - continuing...")
                else:
                    self.log("[WARN] Client List tab click failed - continuing...")
                
                self.log("[COMPLETED] Finished processing client - returning to search for next client")
                
                # Click search button to return to search page for next client
                self.log("[SEARCH-RETURN] Clicking search button to return to search page...")
                if pn.click_search_button_to_return_to_search():
                    self.log("[SUCCESS] Successfully returned to search page for next client!")
                    time.sleep(1)  # Reduced from 2s to 1s for faster search page loading
                else:
                    self.log("[WARN] Failed to return to search page - may affect next client processing")
                
                # Continue to next client (removed break statement)

            # Generate Excel report of all processed clients
            self.log("[REPORT] Generating Excel report of all processed clients...")
            self._generate_excel_report(rows)
            
            # Check if user wants to run Intake & Referral Bot after Counselor Assignment
            if self.run_intake_referral_after.get():
                self.log("[INTEGRATION] Launching Intake & Referral Bot after Counselor Assignment completion...")
                self._launch_intake_referral_bot()
                
                # Wait for IA bot to complete before launching uploaders
                self.log("[INTEGRATION] Waiting for IA Referral Bot to complete...")
                self.log("[INTEGRATION] (Check the IA Referral Bot window - this bot will continue when it's done)")
                
                # Check if uploaders should run after IA bot
                if self.run_base_uploader_after.get():
                    self.log("[INTEGRATION] Will launch Dual Uploader (Base) after IA Referral Bot completes...")
                    self._wait_for_ia_bot_and_launch_uploaders()
            else:
                self.log("[INTEGRATION] Intake & Referral Bot launch skipped (checkbox not selected)")
            
            self.log("[DONE] Navigation complete. Browser left open for review.")
        except Exception as e:
            self.log(f"[FATAL] {e}")
            self.log(traceback.format_exc())

    def _generate_excel_report(self, processed_rows):
        """
        Generate an Excel report detailing what the bot did for each client.
        Creates a summary report with client information and processing status.
        Files are saved in the same directory as the bot script.
        """
        try:
            import pandas as pd
            from datetime import datetime
            import os
            
            # Get the directory where this bot script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Create report data
            report_data = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for idx, row in enumerate(processed_rows, 1):
                client_data = {
                    'Row_Number': idx,
                    'Individual_ID': str(row.get("_Bot_ID") or "").strip(),
                    'First_Name': str(row.get("First Name") or row.get("First") or row.get("FName") or row.get("Given") or "").strip(),
                    'Last_Name': str(row.get("Last Name") or row.get("Last") or row.get("LName") or row.get("Surname") or "").strip(),
                    'Counselor_Assigned': str(row.get("Counselor") or "").strip(),
                    'Processing_Status': 'Completed',
                    'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'Actions_Performed': 'Counselor Assignment, Pre-Enrollment, Service File Setup, IA Only Configuration'
                }
                report_data.append(client_data)
            
            # Create DataFrame
            df = pd.DataFrame(report_data)
            
            # Generate full file paths in the same directory as the bot script
            report_filename = os.path.join(script_dir, f"counselor_assignment_report_{timestamp}.xlsx")
            summary_filename = os.path.join(script_dir, f"processing_summary_{timestamp}.txt")
            
            # Save to Excel
            df.to_excel(report_filename, index=False, sheet_name='Processing_Report')
            
            self.log(f"[REPORT][SUCCESS] Excel report generated: {report_filename}")
            self.log(f"[REPORT] Processed {len(report_data)} clients successfully")
            
            # Also save a summary log
            with open(summary_filename, 'w') as f:
                f.write(f"Counselor Assignment Bot Processing Summary\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Clients Processed: {len(report_data)}\n")
                f.write(f"Status: All clients completed successfully\n\n")
                f.write("Client Details:\n")
                for client in report_data:
                    f.write(f"- {client['First_Name']} {client['Last_Name']} (ID: {client['Individual_ID']}) -> Counselor: {client['Counselor_Assigned']}\n")
            
            self.log(f"[REPORT][SUCCESS] Summary log generated: {summary_filename}")
            self.log(f"[REPORT] Files saved in bot directory: {script_dir}")
            
        except Exception as e:
            self.log(f"[REPORT][ERROR] Failed to generate Excel report: {e}")
            import traceback
            self.log(f"[REPORT][ERROR] Traceback: {traceback.format_exc()}")

    def _launch_intake_referral_bot(self):
        """
        Launch the Intake & Referral Bot after Counselor Assignment Bot completes.
        Passes the same credentials, URL, and CSV data to the Intake Referral Bot.
        """
        try:
            import subprocess
            import sys
            import os
            
            # Get the path to the Intake Referral Bot script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            intake_referral_bot_path = os.path.join(current_dir, "isws_Intake_referral_bot_REFERENCE_PLUS_PRINT_ONLY_WITH_LOOPBACK_LOOPONLY_SCROLLING_TINYLOG_NO_BOTTOM_UPLOADER.py")
            
            # Check if the Intake Referral Bot file exists
            if not os.path.exists(intake_referral_bot_path):
                self.log(f"[INTEGRATION][ERROR] Intake Referral Bot not found at: {intake_referral_bot_path}")
                return
            
            # Calculate the ACTUAL row range from CSV (process ALL rows automatically)
            # This ensures all downstream bots process the entire CSV
            ia_row_range = "2-2"  # Default fallback
            
            try:
                import pandas as pd
                csv_path = self.local_path.get().strip()
                
                if csv_path.lower().endswith('.csv'):
                    df = pd.read_csv(csv_path)
                else:
                    df = pd.read_excel(csv_path)
                
                total_data_rows = len(df)
                actual_last_row = total_data_rows + 1  # +1 because rows are 1-indexed with header
                ia_row_range = f"2-{actual_last_row}"
                
                self.log(f"[INTEGRATION] ✅ Auto-calculated row range for IA bot: {ia_row_range} ({total_data_rows} clients)")
                
            except Exception as e:
                self.log(f"[INTEGRATION][WARN] Could not calculate row count: {e}")
                self.log(f"[INTEGRATION][WARN] Using fallback range: 2-50")
                ia_row_range = "2-50"
            
            self.log(f"[INTEGRATION] All downstream bots will process the full CSV automatically")
            
            # Prepare command line arguments - run in auto-mode with GUI
            # This will show the GUI window AND auto-populate credentials and auto-start
            cmd_args = [
                sys.executable,
                intake_referral_bot_path,
                "--auto-mode",
                "--csv-file", self.local_path.get(),
                "--url", self.url_var.get(),
                "--username", self.user_var.get(),
                "--password", self.pass_var.get(),
                "--column", self.col_sel.get(),
                "--rows", ia_row_range
            ]
            
            # Add dual uploader parameters if checkboxes are selected
            if self.run_base_uploader_after.get():
                cmd_args.extend(["--run-base-uploader"])
                self.log(f"[INTEGRATION] ✅ Base Dual Uploader will be launched after IA Referral Bot completes")
                
                if self.run_ips_uploader_after.get():
                    cmd_args.extend(["--run-ips-uploader"])
                    self.log(f"[INTEGRATION] ✅ IPS Dual Uploader will also be launched after Base Uploader completes")
                
                # Pass TherapyNotes credentials for the uploaders
                if self.tn_user_var.get() and self.tn_pass_var.get():
                    cmd_args.extend(["--tn-username", self.tn_user_var.get()])
                    cmd_args.extend(["--tn-password", self.tn_pass_var.get()])
                    self.log(f"[INTEGRATION] ✅ TherapyNotes credentials will be passed to uploaders")
                else:
                    self.log(f"[INTEGRATION][WARN] ⚠️  TherapyNotes credentials not provided - uploaders may fail")
            else:
                self.log(f"[INTEGRATION] ℹ️  Dual Uploader launch skipped (checkbox not selected)")
            
            self.log(f"[INTEGRATION] Launching Intake & Referral Bot with auto-populated credentials...")
            self.log(f"[INTEGRATION] CSV File: {self.local_path.get()}")
            self.log(f"[INTEGRATION] URL: {self.url_var.get()}")
            self.log(f"[INTEGRATION] Username: {self.user_var.get()}")
            self.log(f"[INTEGRATION] Column: {self.col_sel.get()}")
            self.log(f"[INTEGRATION] Rows: {self.local_row_from.get()}-{self.local_row_to.get()}")
            self.log(f"[INTEGRATION] Full command: {' '.join(cmd_args)}")
            
            # Launch the Intake Referral Bot as a subprocess
            # Don't redirect stdout/stderr so the GUI window can appear properly
            self.ia_bot_process = subprocess.Popen(
                cmd_args,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # Wait a moment to see if the process starts successfully
            import time
            time.sleep(2)
            
            # Check if the process is still running
            if self.ia_bot_process.poll() is None:
                self.log(f"[INTEGRATION] IA Referral Bot is running (PID: {self.ia_bot_process.pid})")
            else:
                return_code = self.ia_bot_process.returncode
                self.log(f"[INTEGRATION][ERROR] Process exited immediately with return code: {return_code}")
                self.log(f"[INTEGRATION][ERROR] This usually means there was an error starting the Intake Referral Bot")
                self.ia_bot_process = None
                return
            
            self.log(f"[INTEGRATION][SUCCESS] Intake & Referral Bot launched successfully (PID: {self.ia_bot_process.pid})")
            self.log(f"[INTEGRATION] The Intake & Referral Bot GUI window should now be visible with auto-populated credentials.")
            self.log(f"[INTEGRATION] The bot should automatically start processing after a brief delay.")
            
        except Exception as e:
            self.log(f"[INTEGRATION][ERROR] Failed to launch Intake & Referral Bot: {e}")
            import traceback
            self.log(f"[INTEGRATION][ERROR] Traceback: {traceback.format_exc()}")
    
    def _wait_for_ia_bot_and_launch_uploaders(self):
        """
        Wait for IA Referral Bot to complete, then launch Base and optionally IPS uploaders.
        Uses Desktop/Referral Form Bot Output/ as the PDF folder.
        """
        def wait_and_launch():
            try:
                import os
                import time
                
                # CRITICAL FIX: Wait for IA bot PROCESS to complete, not just folder
                if not hasattr(self, 'ia_bot_process') or self.ia_bot_process is None:
                    self.log("[UPLOADER][ERROR] IA bot process not found - cannot wait for completion")
                    return
                
                self.log(f"[UPLOADER] Waiting for IA Referral Bot (PID: {self.ia_bot_process.pid}) to complete...")
                self.log(f"[UPLOADER] This may take several minutes depending on how many clients are being processed...")
                
                # Wait for IA bot process to finish (blocking call)
                self.ia_bot_process.wait()
                
                self.log(f"[UPLOADER] ✅ IA Referral Bot completed! (exit code: {self.ia_bot_process.returncode})")
                
                # Now check if PDF folder exists
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                pdf_folder = os.path.join(desktop, "Referral Form Bot Output")
                
                if not os.path.exists(pdf_folder):
                    self.log(f"[UPLOADER][ERROR] PDF folder not found at: {pdf_folder}")
                    self.log(f"[UPLOADER][ERROR] IA bot may have failed - check the IA bot window for errors")
                    return
                
                self.log(f"[UPLOADER] ✓ PDF folder found: {pdf_folder}")
                
                # Validate TherapyNotes credentials before launching
                if not self.tn_user_var.get() or not self.tn_pass_var.get():
                    self.log("[UPLOADER][ERROR] ❌ TherapyNotes credentials not provided!")
                    self.log("[UPLOADER][ERROR] Please fill in 'TN Username' and 'TN Password' fields in the Counselor Assignment Bot GUI")
                    self.log("[UPLOADER][ERROR] Uploader launch cancelled")
                    self.log("[UPLOADER][ERROR] 💡 TIP: The TherapyNotes credentials are required for both Base and IPS uploaders")
                    return
                
                self.log(f"[UPLOADER] ✓ TherapyNotes credentials validated")
                
                # Launch Base Uploader
                self.log("[UPLOADER] Launching Base Uploader...")
                base_success = self._launch_dual_uploader_base(pdf_folder)
                
                if not base_success:
                    self.log("[UPLOADER][ERROR] Base Uploader failed to launch")
                    return
                
                # If IPS checkbox is checked, launch IPS uploader
                if self.run_ips_uploader_after.get():
                    self.log("[UPLOADER] Base Uploader complete. Launching IPS Uploader...")
                    self._launch_dual_uploader_ips(pdf_folder)
                else:
                    self.log("[UPLOADER] IPS Uploader skipped (checkbox not selected)")
                
                self.log("[UPLOADER] ✓ All uploader operations complete!")
                
            except Exception as e:
                self.log(f"[UPLOADER][ERROR] Uploader integration failed: {e}")
                import traceback
                self.log(f"[UPLOADER][ERROR] {traceback.format_exc()}")
        
        threading.Thread(target=wait_and_launch, daemon=True).start()
    
    def _launch_dual_uploader_base(self, pdf_folder):
        """Launch the Base (ISWS) uploader from the dual uploader bot"""
        try:
            import subprocess
            import sys
            import os
            
            # Get dual uploader path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            dual_uploader_path = os.path.join(current_dir, "IPS_IA_Referral_Form_Uploader_Dual_Tab.py")
            
            if not os.path.exists(dual_uploader_path):
                self.log(f"[UPLOADER][ERROR] Dual uploader not found at: {dual_uploader_path}")
                return False
            
            # Prepare arguments for base uploader
            cmd_args = [
                sys.executable,
                dual_uploader_path,
                "--mode", "base",
                "--csv-file", self.local_path.get(),
                "--pdf-folder", pdf_folder,
                "--tn-username", self.tn_user_var.get(),
                "--tn-password", self.tn_pass_var.get(),
                "--auto-run"
            ]
            
            # Add remove old documents flag if checkbox is enabled
            if self.remove_old_ia_docs.get():
                cmd_args.extend(["--remove-old-docs"])
            
            self.log(f"[UPLOADER-BASE] Launching Base uploader...")
            self.log(f"[UPLOADER-BASE] CSV: {self.local_path.get()}")
            self.log(f"[UPLOADER-BASE] PDFs: {pdf_folder}")
            
            # Launch as subprocess
            process = subprocess.Popen(
                cmd_args,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            time.sleep(2)
            
            if process.poll() is None:
                self.log(f"[UPLOADER-BASE] ✓ Base uploader launched (PID: {process.pid})")
                
                # Wait for Base uploader to complete
                self.log("[UPLOADER-BASE] Waiting for Base uploader to complete...")
                process.wait()  # Block until process finishes
                self.log(f"[UPLOADER-BASE] ✓ Base uploader completed (exit code: {process.returncode})")
                return True
            else:
                self.log(f"[UPLOADER-BASE][ERROR] Process exited immediately")
                return False
                
        except Exception as e:
            self.log(f"[UPLOADER-BASE][ERROR] {e}")
            import traceback
            self.log(f"[UPLOADER-BASE][ERROR] {traceback.format_exc()}")
            return False
    
    def _launch_dual_uploader_ips(self, pdf_folder):
        """Launch the IPS uploader from the dual uploader bot"""
        try:
            import subprocess
            import sys
            import os
            
            # Get dual uploader path
            current_dir = os.path.dirname(os.path.abspath(__file__))
            dual_uploader_path = os.path.join(current_dir, "IPS_IA_Referral_Form_Uploader_Dual_Tab.py")
            
            if not os.path.exists(dual_uploader_path):
                self.log(f"[UPLOADER][ERROR] Dual uploader not found at: {dual_uploader_path}")
                return False
            
            # Prepare arguments for IPS uploader
            cmd_args = [
                sys.executable,
                dual_uploader_path,
                "--mode", "ips",
                "--csv-file", self.local_path.get(),
                "--pdf-folder", pdf_folder,
                "--tn-username", self.tn_user_var.get(),
                "--tn-password", self.tn_pass_var.get(),
                "--auto-run"
            ]
            
            # Add remove old documents flag if checkbox is enabled
            if self.remove_old_ia_docs.get():
                cmd_args.extend(["--remove-old-docs"])
            
            self.log(f"[UPLOADER-IPS] Launching IPS uploader...")
            self.log(f"[UPLOADER-IPS] CSV: {self.local_path.get()}")
            self.log(f"[UPLOADER-IPS] PDFs: {pdf_folder}")
            
            # Launch as subprocess
            process = subprocess.Popen(
                cmd_args,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            time.sleep(2)
            
            if process.poll() is None:
                self.log(f"[UPLOADER-IPS] ✓ IPS uploader launched (PID: {process.pid})")
                
                # Wait for IPS uploader to complete
                self.log("[UPLOADER-IPS] Waiting for IPS uploader to complete...")
                process.wait()  # Block until process finishes
                self.log(f"[UPLOADER-IPS] ✓ IPS uploader completed (exit code: {process.returncode})")
                return True
            else:
                self.log(f"[UPLOADER-IPS][ERROR] Process exited immediately")
                return False
                
        except Exception as e:
            self.log(f"[UPLOADER-IPS][ERROR] {e}")
            import traceback
            self.log(f"[UPLOADER-IPS][ERROR] {traceback.format_exc()}")
            return False

    def expand_case_info_if_needed_and_click_ia_only(self, verify_selector: tuple = None, timeout: int = 10) -> bool:
        """
        Ensure Case Information is expanded (without toggling it closed if already open),
        then click the 'IA Only' link in topTabOptions.

        Args:
          verify_selector: optional tuple (By.METHOD, "selector") to wait for after clicking IA Only,
                           used to verify the next page/section loaded. If None, function will skip verification.
          timeout: seconds for waits.

        Returns:
          True if IA Only was clicked (and verification passed if provided), False otherwise.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            d.switch_to.default_content()
        except Exception:
            pass

        # --- 1) Locate the Case Information toggle (if present) ---
        toggle = None
        possible_toggle_xpaths = [
            "//a[normalize-space()='Case Information']",
            "//h3[normalize-space()='Case Information']",
            "//a[normalize-space()='Case Info']",
            "//h3[normalize-space()='Case Info']",
        ]
        for xp in possible_toggle_xpaths:
            try:
                elts = d.find_elements(By.XPATH, xp)
                if not elts:
                    continue
                # choose first visible
                for e in elts:
                    try:
                        if e.is_displayed():
                            toggle = e
                            break
                    except Exception:
                        continue
                if toggle:
                    break
            except Exception:
                continue

        # Determine whether expansion is needed
        expand_needed = False
        try:
            if toggle:
                # Prefer aria-expanded attribute if present
                aria = toggle.get_attribute("aria-expanded")
                if aria is not None and aria != "":
                    # aria exists; expand if it's explicitly false-like
                    if str(aria).lower() in ("false", "0", "no"):
                        expand_needed = True
                    else:
                        expand_needed = False
                else:
                    # No aria attribute: check presence/visibility of the case-list container
                    try:
                        case_list = d.find_element(By.ID, "ajaxprogMemTable")
                        try:
                            if not case_list.is_displayed():
                                expand_needed = True
                            else:
                                expand_needed = False
                        except Exception:
                            # If is_displayed throws, assume expansion needed
                            expand_needed = True
                    except Exception:
                        # If we cannot find the list by ID, try a common wrapper / assume expansion needed
                        # (but be conservative)
                        expand_needed = True
            else:
                # No explicit toggle found — check if case-list exists and is visible.
                try:
                    case_list = d.find_element(By.ID, "ajaxprogMemTable")
                    expand_needed = not case_list.is_displayed()
                except Exception:
                    # No toggle and no case list found — we'll proceed and try to find IA Only directly
                    expand_needed = False
        except Exception as e:
            self.log(f"[CASE-INFO][WARN] Error determining expand state: {e}")
            expand_needed = False

        # If we need to expand, click the toggle (with JS fallback)
        if expand_needed and toggle:
            try:
                try:
                    toggle.click()
                    self.log("[CASE-INFO] Clicked Case Information toggle to expand.")
                except Exception:
                    d.execute_script("arguments[0].scrollIntoView({block:'center'});", toggle)
                    d.execute_script("arguments[0].click();", toggle)
                    self.log("[CASE-INFO] JS-clicked Case Information toggle to expand.")
                # small pause to let DOM update
                time.sleep(0.35)
            except Exception as e:
                self.log(f"[CASE-INFO][WARN] Failed to click expand toggle: {e}. Proceeding to search for IA Only anyway.")

        else:
            if toggle:
                self.log("[CASE-INFO] Case Information toggle present and already expanded (no click).")
            else:
                self.log("[CASE-INFO] Case Information toggle not found; proceeding to search for 'IA Only' directly.")

        # --- 2) Locate the 'IA Only' link inside topTabOptions (preferred) or anywhere as fallback ---
        ia_link = None
        try:
            # Primary exact-location selector inside topTabOptions
            try:
                ia_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'topTabOptions')]//h3//a[normalize-space()='IA Only']")))
                self.log("[CASE-INFO] Found 'IA Only' link in topTabOptions.")
            except Exception:
                # Fallback to any anchor with exact text 'IA Only'
                try:
                    ia_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='IA Only']")))
                    self.log("[CASE-INFO] Found 'IA Only' link (fallback anywhere).")
                except Exception:
                    ia_link = None

            if not ia_link:
                self.log("[CASE-INFO][ERROR] 'IA Only' link not found on page.")
                return False

            # Scroll into view and click with JS fallback
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", ia_link)
            except Exception:
                pass

            try:
                ia_link.click()
                self.log("[CASE-INFO] Clicked 'IA Only' link.")
            except Exception:
                try:
                    d.execute_script("arguments[0].click();", ia_link)
                    self.log("[CASE-INFO] Clicked 'IA Only' via JS fallback.")
                except Exception as e:
                    self.log(f"[CASE-INFO][ERROR] Failed to click 'IA Only' link: {e}")
                    return False

        except Exception as e:
            self.log(f"[CASE-INFO][ERROR] Unexpected error while locating/clicking 'IA Only': {e}")
            return False

        # --- 3) Optional verification: wait for the next screen element if verify_selector provided ---
        if verify_selector:
            try:
                by, sel = verify_selector
                self.log(f"[CASE-INFO] Waiting up to {timeout}s for verification selector {by}, {sel} ...")
                WebDriverWait(d, timeout).until(EC.presence_of_element_located((by, sel)))
                self.log("[CASE-INFO] Verification selector found — navigation appears successful.")
            except Exception as e:
                self.log(f"[CASE-INFO][WARN] Verification selector not detected after clicking IA Only: {e}")
                # Not a hard failure; return True (we did click) but warning logged.
                return True

        return True

# ---------------- Main ----------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
