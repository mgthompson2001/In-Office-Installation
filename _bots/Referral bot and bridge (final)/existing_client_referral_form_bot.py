# existing_client_referral_form_bot.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
#  Existing Client Referral Form Bot — Penelope Navigation to Pre-Enrollment
# =============================================================================

import os, sys, time, json, threading, queue, tempfile, traceback, re
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from dataclasses import dataclass
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime
import requests
import pandas as pd

APP_TITLE = "Existing Client Referral Form Bot"
MAROON    = "#800000"
LOG_BG    = "#f7f3f2"
LOG_FG    = "#1a1a1a"

def _title_banner(root):
    frm = ttk.Frame(root); frm.pack(fill='x')
    banner = tk.Frame(frm, bg=MAROON, height=54); banner.pack(fill='x')
    lbl = tk.Label(banner, text=APP_TITLE, fg="white", bg=MAROON,
                   font=("Segoe UI", 18, "bold"), pady=6)
    lbl.pack(side='left', padx=14, pady=6)
    # Top-right Launch Uploader button
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
    t = str(token).strip().strip("\"'""''`")
    return t

def _is_single_letter(t: str) -> bool:
    return len(t) == 1 and t.isalpha()

def _clean_numeric_to_int_str(value) -> str:
    """Convert numeric values (including floats like 12345.0) to clean integer strings."""
    if value is None:
        return ""
    try:
        float_val = float(value)
        if float_val.is_integer():
            return str(int(float_val))
        return str(float_val)
    except (ValueError, TypeError):
        return str(value).strip()

def resolve_column(df, name_or_letter: str):
    """Accept a header name OR a single column letter (A,B,...). Returns a pandas Series or raises KeyError."""
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
        e = max(s, int(self.row_to) - 2)

        token = _normalize_col_token(self.col_selector)
        log(_ts() + f"[DATA] Column token: '{token}'  | Columns: {list(df.columns)}")
        
        # Resolve the ID column using original column names
        try:
            series = resolve_column(df, token)
        except KeyError as ke:
            log(_ts() + f"[DATA][ERR] {ke}")
            return []

        sub = df.iloc[s:e+1].copy()
        
        # Clean up column names (remove trailing/leading spaces) - this makes dict keys clean
        sub.columns = sub.columns.str.strip()
        
        # Clean up data values (remove trailing/leading spaces from string columns)
        for col in sub.columns:
            if sub[col].dtype == 'object':
                sub[col] = sub[col].astype(str).str.strip()
        
        # Extract client IDs from the resolved series (using original column structure)
        try:
            client_ids = series.iloc[s:e+1].astype(object)
            client_ids_str = client_ids.astype(str).str.strip()
            client_ids_str = client_ids_str.str.replace(r'\.0$', '', regex=True)
            sub["_Bot_ID"] = client_ids_str
        except Exception as e:
            log(_ts() + f"[DATA][WARN] Could not extract client IDs: {e}")
            sub["_Bot_ID"] = ""
        
        recs = sub.to_dict(orient="records")
        log(_ts() + f"[DATA] Loaded {len(recs)} rows from local file [{self.row_from}..{self.row_to}].")
        if recs:
            log(_ts() + f"[DATA] Sample columns: {list(sub.columns)[:5]}...")
            log(_ts() + f"[DATA] Sample row keys: {list(recs[0].keys())[:5]}...")
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
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            if chrome_profile_dir and os.path.isdir(chrome_profile_dir):
                options.add_argument(f"--user-data-dir={chrome_profile_dir}")
                self.log(_ts() + f"[BROWSER] Using Chrome profile: {chrome_profile_dir}")
            else:
                self.log(_ts() + "[BROWSER] Using fresh Selenium profile (no saved cookies).")
            service = Service(ChromeDriverManager().install())
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
                origin = re.match(r'^(https?://[^/]+)', d.current_url)
                if origin:
                    d.get(origin.group(1) + "/acm_searchControl?actionType=view")
            WebDriverWait(d, 15).until(lambda _drv: True)
            ok = self._switch_to_search_content_frame()
            if not ok:
                return False
            return True
        except Exception:
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
            try:
                d.switch_to.default_content()
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
                # Activate tab using JavaScript
                try:
                    d.execute_script("if (typeof goTab==='function') { goTab('tabIndiv'); }")
                except Exception:
                    pass
                try:
                    tab = WebDriverWait(d, 4).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li#tabIndiv_li")))
                    d.execute_script("arguments[0].click();", tab)
                except Exception:
                    pass
                
                # Wait for the Individual ID field to be present
                import time
                time.sleep(0.3)  # Brief pause for tab to activate
                id_input = WebDriverWait(d, 6).until(EC.presence_of_element_located((By.NAME, "txtKIndID")))
                
                # Clear the field using ONLY JavaScript to avoid stale element errors
                try:
                    d.execute_script("arguments[0].value = ''; arguments[0].focus();", id_input)
                    log("[INDIV] Individual tab activated - ID field cleared via JavaScript")
                except Exception as e:
                    log(f"[INDIV][WARN] Could not clear ID field via JavaScript: {e}")
                
                return True
            except Exception as e:
                log(f"[INDIV][WARN] Could not activate Individual tab: {e}")
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

        # SIMPLIFIED: Single attempt with robust JavaScript-only approach
        import time
        try:
            log(f"[INDIV] Opening search, activating Individual tab, entering ID {indiv_id}, clicking GO...")

            # Open search if needed
            if not _open_search_if_needed():
                log("[INDIV][WARN] Could not open search page, continuing anyway...")
            
            # Switch to frame
            if not _into_frame():
                log("[INDIV][WARN] Could not switch to frame, retrying...")
                d.switch_to.default_content()
                time.sleep(0.5)
                if not _into_frame():
                    raise TimeoutException("Could not enter frm_content_id after retry")

            # Activate Individual tab using JavaScript only
            try:
                d.execute_script("if (typeof goTab==='function') { goTab('tabIndiv'); }")
                time.sleep(0.5)  # Wait for tab to activate
            except Exception as e:
                log(f"[INDIV][WARN] goTab() failed: {e}, trying tab click...")
                try:
                    tab = WebDriverWait(d, 4).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li#tabIndiv_li")))
                    d.execute_script("arguments[0].click();", tab)
                    time.sleep(0.5)
                except Exception:
                    raise TimeoutException("Could not activate Individual tab")

            # Convert ID to string (remove decimals)
            try:
                _id = str(int(float(indiv_id))).strip()
            except (ValueError, TypeError):
                _id = str(indiv_id).strip()
                if _id.endswith('.0'):
                    _id = _id[:-2]
            
            log(f"[INDIV] Setting Individual ID: {_id} via JavaScript")
            
            # CRITICAL: Use ONLY JavaScript - NO Selenium input methods whatsoever
            # Find element and set value in one JavaScript call
            import time
            id_input = WebDriverWait(d, 8).until(EC.presence_of_element_located((By.NAME, "txtKIndID")))
            
            # Set value using ONLY JavaScript - completely bypasses Selenium
            d.execute_script("""
                var elem = arguments[0];
                var val = arguments[1];
                elem.value = '';
                elem.focus();
                elem.value = val;
                // Trigger all relevant events
                ['input', 'change', 'keyup', 'keydown'].forEach(function(eventType) {
                    elem.dispatchEvent(new Event(eventType, { bubbles: true, cancelable: true }));
                });
            """, id_input, _id)
            
            time.sleep(0.6)  # Wait for value to register
            log(f"[INDIV] ✓ ID '{_id}' set via JavaScript")

            # Click GO button - use JavaScript to call searchForCurrentTab() directly
            log("[INDIV] Triggering search via searchForCurrentTab()...")
            try:
                # Call searchForCurrentTab() directly - this is what the GO button does
                d.execute_script("if (typeof searchForCurrentTab==='function') { searchForCurrentTab(); }")
                log("[INDIV] ✓ searchForCurrentTab() called")
            except Exception as e:
                log(f"[INDIV][WARN] searchForCurrentTab() failed: {e}, trying GO button click...")
                try:
                    go = WebDriverWait(d, 4).until(EC.presence_of_element_located((By.ID, "goButton")))
                    d.execute_script("arguments[0].click();", go)
                    log("[INDIV] ✓ GO button clicked via JavaScript")
                except Exception:
                    raise TimeoutException("Could not trigger search")

            # Wait for page to reload
            time.sleep(1)
            
            if not _into_frame():
                raise TimeoutException("No frame after search (reload expected)")

            if not _wait_results(wait_secs=max(8, min(15, timeout))):
                # Try triggering search again
                try:
                    d.execute_script("if (typeof searchForCurrentTab==='function') { searchForCurrentTab(); }")
                    time.sleep(1)
                except Exception:
                    pass
                if not _wait_results(wait_secs=max(6, min(12, timeout))):
                    raise TimeoutException("Results did not render in time")

            # Log results found
            try:
                results_elem = d.find_element(By.ID, "results")
                results_text = (results_elem.text or "").strip()
                if results_text:
                    first_line = results_text.split('\n')[0][:150]
                    log(f"[INDIV] ✓ Search results found: '{first_line}...'")
                    result_links = d.find_elements(By.XPATH, "//div[@id='results']//a[normalize-space(text())!='']")
                    if len(result_links) > 1:
                        log(f"[INDIV][WARN] Found {len(result_links)} result(s) - will select first ISWS (non-IPS) match")
                    elif len(result_links) == 1:
                        log(f"[INDIV] Found exactly 1 result - good!")
                else:
                    log(f"[INDIV][WARN] Results element found but appears empty")
            except Exception as e:
                log(f"[INDIV][WARN] Could not read results details: {e}")

            try: 
                d.switch_to.default_content()
            except Exception: 
                pass
            log("[INDIV] Results detected; ready to select client.")
            return True

        except Exception as e:
            import traceback
            error_msg = str(e) or "Unknown error"
            error_trace = traceback.format_exc()
            log(f"[INDIV][ERROR] Failed: {error_msg}")
            log(f"[INDIV][ERROR] Traceback: {error_trace[:500]}")  # First 500 chars of traceback
            try: 
                d.switch_to.default_content()
            except Exception: 
                pass
            return False

    def click_first_result_name(self, first_name: str = None, last_name: str = None, timeout: int = 12) -> bool:
        '''After pressing Go on the Search page, click the patient's first or last name in the results dropdown/table to open their profile. Only click if case status is "open" (never click closed).'''
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
                            # Check if this link is in a row with "closed" case status - skip those
                            try:
                                parent_row = a.find_element(By.XPATH, "./ancestor::tr")
                                row_text = (parent_row.text or "").lower()
                                # Skip if explicitly marked as closed
                                if "closed" in row_text and "open" not in row_text:
                                    continue  # Skip closed cases
                                # Otherwise include it (open, or no status specified)
                                uniq.append(a)
                            except Exception:
                                # If we can't check the row, include it (better to try than skip)
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

            # Find the link and click it immediately to avoid stale element issues
            link = None
            try:
                link = WebDriverWait(d, timeout).until(lambda drv: _find_name_link())
            except Exception:
                link = _find_name_link()

            if not link:
                d.switch_to.default_content()
                self.log("[SEARCH-RESULT][ERR] No open case found for this client.")
                return False

            # Click the link IMMEDIATELY using JavaScript to avoid stale element
            # Don't try to get text/href first - just click it right away
            try:
                # Use JavaScript click immediately - most reliable
                d.execute_script("arguments[0].click();", link)
                self.log(f"[SEARCH-RESULT] ✓ Clicked link via JavaScript")
            except Exception as e1:
                # Fallback to regular click
                try:
                    link.click()
                    self.log(f"[SEARCH-RESULT] ✓ Clicked link via Selenium")
                except Exception as e2:
                    self.log(f"[SEARCH-RESULT][ERROR] Could not click link: {e1}, {e2}")
                    return False

            # Wait for profile page to load by checking for common profile page elements
            d.switch_to.default_content()
            import time
            time.sleep(1)  # Brief pause for page navigation
            
            # Verify profile loaded by checking for frm_content_id frame
            try:
                WebDriverWait(d, 8).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                d.switch_to.default_content()
                self.log("[SEARCH-RESULT] ✓ Profile page loaded successfully")
                return True
            except Exception as e:
                # Even if verification fails, if we clicked the link, assume success
                self.log(f"[SEARCH-RESULT][WARN] Could not verify profile load, but link was clicked: {e}")
                return True  # Return True anyway since we successfully clicked
        except Exception as e:
            self.log(f"[SEARCH-RESULT][ERROR] Exception in click_first_result_name: {e}")
            try: 
                d.switch_to.default_content()
            except Exception: 
                pass
            return False

    def extract_referral_meeting_note(self, timeout: int = 10) -> Tuple[Optional[str], bool]:
        """
        Extract the counselor name from the note that says "Referral meeting assigned to [Counselor Name]" 
        or "[Counselor Name] - IPS".
        Searches in main content frame and all iframes.
        Returns: (counselor_name, is_ips) where is_ips is True if "- IPS" suffix is present.
        """
        if not self.driver:
            self.log("[NOTE-EXTRACT] No driver."); return None, False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception as e:
            self.log(f"[NOTE-EXTRACT][ERR] Selenium libs: {e}"); return None, False

        d = self.driver
        log = getattr(self, "log", lambda s: None)

        counselor_name = None
        is_ips = False

        try:
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))

            # Wait for page to be ready
            try:
                WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

            log("[NOTE-EXTRACT] Searching for referral meeting assignment note...")

            # Search in main content frame first
            page_text = ""
            try:
                body = d.find_element(By.TAG_NAME, "body")
                page_text = body.text
                log(f"[NOTE-EXTRACT] Retrieved page text from main frame ({len(page_text)} characters)")
            except Exception as e:
                log(f"[NOTE-EXTRACT][WARN] Could not get body text: {e}")
                try:
                    page_text = d.execute_script("return document.body ? (document.body.innerText||'') : '';")
                except Exception:
                    pass

            # Also check innerHTML for notes that might be in HTML comments or hidden elements
            try:
                html_content = d.execute_script("return document.body ? document.body.innerHTML : '';")
                if html_content:
                    # Extract text from HTML (removes tags)
                    from html.parser import HTMLParser
                    class TextExtractor(HTMLParser):
                        def __init__(self):
                            super().__init__()
                            self.text = ""
                        def handle_data(self, data):
                            self.text += data + " "
                    parser = TextExtractor()
                    parser.feed(html_content)
                    html_text = parser.text
                    if html_text and len(html_text) > len(page_text):
                        page_text = html_text
                        log(f"[NOTE-EXTRACT] Also extracted HTML text ({len(page_text)} characters)")
            except Exception:
                pass

            # Search for the note pattern
            patterns = [
                r"Referral meeting assigned to\s+([^.\n]+?)(?:\s*-\s*IPS)?",
                r"referral meeting assigned to\s+([^.\n]+?)(?:\s*-\s*IPS)?",
                r"meeting assigned to\s+([^.\n]+?)(?:\s*-\s*IPS)?",
                r"assigned to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s*-\s*IPS)?)",
                r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*-\s*IPS",
            ]

            for pattern in patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    name_part = match.group(1).strip() if match.groups() else match.group(0).strip()
                    
                    # Check if this match includes "- IPS"
                    full_match = match.group(0)
                    if "- IPS" in full_match.upper() or " - IPS" in full_match:
                        is_ips = True
                        # Remove "- IPS" from the name
                        name_part = re.sub(r'\s*-\s*IPS\s*$', '', name_part, flags=re.IGNORECASE).strip()
                    
                    # Validate it looks like a name (has at least 2 words or is a reasonable length)
                    if name_part and (len(name_part.split()) >= 2 or (len(name_part) > 3 and name_part[0].isupper())):
                        counselor_name = name_part
                        log(f"[NOTE-EXTRACT] ✓ Found counselor name: '{counselor_name}' (IPS: {is_ips})")
                        log(f"[NOTE-EXTRACT] Full match: '{full_match}'")
                        break
                
                if counselor_name:
                    break

            # If not found in main frame, try searching in all iframes
            if not counselor_name:
                log("[NOTE-EXTRACT] Not found in main frame, searching iframes...")
                try:
                    d.switch_to.default_content()
                    iframes = d.find_elements(By.TAG_NAME, "iframe")
                    for i, iframe in enumerate(iframes):
                        try:
                            d.switch_to.frame(iframe)
                            try:
                                iframe_text = d.find_element(By.TAG_NAME, "body").text
                                if iframe_text:
                                    log(f"[NOTE-EXTRACT] Checking iframe {i+1} ({len(iframe_text)} chars)")
                                    for pattern in patterns:
                                        matches = re.finditer(pattern, iframe_text, re.IGNORECASE | re.MULTILINE)
                                        for match in matches:
                                            name_part = match.group(1).strip() if match.groups() else match.group(0).strip()
                                            full_match = match.group(0)
                                            if "- IPS" in full_match.upper():
                                                is_ips = True
                                                name_part = re.sub(r'\s*-\s*IPS\s*$', '', name_part, flags=re.IGNORECASE).strip()
                                            if name_part and (len(name_part.split()) >= 2 or (len(name_part) > 3 and name_part[0].isupper())):
                                                counselor_name = name_part
                                                log(f"[NOTE-EXTRACT] ✓ Found in iframe {i+1}: '{counselor_name}' (IPS: {is_ips})")
                                                break
                                        if counselor_name:
                                            break
                            except Exception:
                                pass
                            finally:
                                d.switch_to.default_content()
                            if counselor_name:
                                break
                        except Exception:
                            d.switch_to.default_content()
                            continue
                except Exception as e:
                    log(f"[NOTE-EXTRACT][WARN] Error searching iframes: {e}")
                    d.switch_to.default_content()

            if not counselor_name:
                log("[NOTE-EXTRACT][WARN] No referral meeting assignment note found - proceeding without counselor info")
                log(f"[NOTE-EXTRACT][DEBUG] Page text sample (first 500 chars): {page_text[:500]}")
                return None, False

            d.switch_to.default_content()
            return counselor_name, is_ips

        except Exception as e:
            log(f"[NOTE-EXTRACT][ERR] Error extracting note: {e}")
            import traceback
            log(f"[NOTE-EXTRACT][ERR] Traceback: {traceback.format_exc()}")
            try: d.switch_to.default_content()
            except Exception: pass
            return None, False

    def click_pre_enrollment_tab_and_waiting_allocation(self, timeout: int = 15) -> bool:
        """Click the Pre-Enrollment tab in the right sidebar, wait for dropdown to appear, then click the "Waiting for Allocation" button with GREEN bubble only."""
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
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))

            try:
                WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

            self.log("[PRE-ENROLL] Looking for Pre-Enrollment tab...")
            
            pre_enroll_tab = None
            try:
                pre_enroll_tab = d.find_element(By.XPATH, "//h2[contains(@onclick, 'indPreEnrollmentBucket')]")
            except Exception:
                try:
                    pre_enroll_tab = d.find_element(By.XPATH, "//h2[normalize-space()='Pre-Enrollment']")
                except Exception:
                    pass

            if not pre_enroll_tab:
                self.log("[PRE-ENROLL][ERROR] Pre-Enrollment tab not found")
                return False

            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", pre_enroll_tab)
            except Exception:
                pass
            
            try:
                pre_enroll_tab.click()
            except Exception:
                d.execute_script("arguments[0].click();", pre_enroll_tab)

            self.log("[PRE-ENROLL] Pre-Enrollment tab clicked, waiting for dropdown...")

            try:
                WebDriverWait(d, 8).until(
                    lambda drv: drv.find_element(By.ID, "indPreEnrollmentBucket").is_displayed()
                )
            except Exception:
                self.log("[PRE-ENROLL][WARN] Pre-Enrollment bucket may not have expanded properly")

            self.log("[PRE-ENROLL] Looking for 'Waiting for Allocation' button with GREEN bubble (not red)...")
            
            waiting_link = None
            
            try:
                all_waiting_links = d.find_elements(By.XPATH, "//a[contains(normalize-space(.), 'Waiting for Allocation')]")
                self.log(f"[PRE-ENROLL][DEBUG] Found {len(all_waiting_links)} 'Waiting for Allocation' links")
                
                for i, link in enumerate(all_waiting_links):
                    try:
                        text = link.text.strip()
                        
                        parent_row = link.find_element(By.XPATH, "./ancestor::tr")
                        status_cell = parent_row.find_element(By.XPATH, ".//td[contains(@class, 'status')]")
                        status_class = status_cell.get_attribute("class") or ""
                        
                        has_green = "statusOpen" in status_class
                        has_red = "statusClosed" in status_class
                        
                        color_status = "GREEN" if has_green else ("RED" if has_red else "NO COLOR")
                        self.log(f"[PRE-ENROLL][DEBUG] Link {i+1}: '{text}' - Status Class: '{status_class}' - Color: {color_status}")
                        
                        if has_green and not has_red:
                            waiting_link = link
                            self.log(f"[PRE-ENROLL] SELECTED Link {i+1} - GREEN bubble (statusOpen) detected!")
                            break
                        elif has_red:
                            self.log(f"[PRE-ENROLL] SKIPPED Link {i+1} - RED bubble (statusClosed) detected (avoiding)")
                        else:
                            self.log(f"[PRE-ENROLL] SKIPPED Link {i+1} - No clear status indicator")
                            
                    except Exception as e:
                        self.log(f"[PRE-ENROLL][DEBUG] Error analyzing link {i+1}: {e}")
                        
            except Exception as e:
                self.log(f"[PRE-ENROLL][DEBUG] Error finding waiting links: {e}")
            
            if not waiting_link:
                try:
                    waiting_link = d.find_element(By.XPATH, "//td[@class='statusOpen imageAlignTop']/following-sibling::td//a[contains(normalize-space(.), 'Waiting for Allocation')]")
                    self.log("[PRE-ENROLL] Found 'Waiting for Allocation' with statusOpen class")
                except Exception:
                    try:
                        waiting_link = d.find_element(By.XPATH, "//tr[td[@class='statusOpen imageAlignTop']]//a[contains(normalize-space(.), 'Waiting for Allocation')]")
                        self.log("[PRE-ENROLL] Found 'Waiting for Allocation' with statusOpen ancestor")
                    except Exception:
                        pass
            
            if not waiting_link:
                self.log("[PRE-ENROLL][ERROR] ❌ No GREEN 'Waiting for Allocation' link found")
                self.log("[PRE-ENROLL][ERROR] ⚠️  BOT PAUSED - Please review this client manually")
                self.log("[PRE-ENROLL][ERROR] All 'Waiting for Allocation' links found were RED (statusClosed)")
                self.log("[PRE-ENROLL][ERROR] This client may not have an open Waiting for Allocation status")
                # Stop processing - wait for user intervention
                return False

            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", waiting_link)
            except Exception:
                pass
            
            import time
            
            # Single click using JavaScript (most reliable method)
            try:
                d.execute_script("arguments[0].click();", waiting_link)
                self.log("[PRE-ENROLL] 'Waiting for Allocation' link clicked (JavaScript)")
            except Exception as e:
                self.log(f"[PRE-ENROLL][WARN] JavaScript click failed: {e}, trying regular click")
                try:
                    waiting_link.click()
                    self.log("[PRE-ENROLL] 'Waiting for Allocation' link clicked (Selenium)")
                except Exception as click_error:
                    self.log(f"[PRE-ENROLL][ERROR] Click failed: {click_error}")
                    return False
            
            try:
                time.sleep(2)
                WebDriverWait(d, 10).until(lambda drv: "waitListControl" in drv.current_url)
                self.log(f"[PRE-ENROLL] Navigation detected - new URL: {d.current_url}")
                WebDriverWait(d, 10).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
                self.log("[PRE-ENROLL] Allocation page loaded successfully")
            except Exception as e:
                self.log(f"[PRE-ENROLL][WARN] Page navigation wait failed: {e}")
            
            self.log("[PRE-ENROLL] ✓ Pre-Enrollment process completed - Waiting for Allocation page loaded")
            return True

        except Exception as e:
            self.log(f"[PRE-ENROLL][ERROR] Failed to click Pre-Enrollment tab or Waiting for Allocation: {e}")
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
            
            # Look for the Assign button
            assign_button = None
            try:
                # Look for the Assign link with assignWL function - most specific selector
                assign_button = d.find_element(By.XPATH, "//a[contains(@href, 'assignWL') and text()='Assign']")
                self.log("[ASSIGN-BUTTON] Found Assign button with assignWL href")
            except Exception:
                try:
                    # Fallback: look for any link containing "Assign" in the topTabOptions area
                    assign_button = d.find_element(By.XPATH, "//div[@class='topTabOptions']//a[text()='Assign']")
                    self.log("[ASSIGN-BUTTON] Found Assign button in topTabOptions area")
                except Exception:
                    try:
                        # Another fallback: look for any link containing "Assign"
                        assign_button = d.find_element(By.XPATH, "//a[text()='Assign']")
                        self.log("[ASSIGN-BUTTON] Found Assign button by general text match")
                    except Exception as e:
                        self.log(f"[ASSIGN-BUTTON][ERROR] Assign button not found: {e}")
                        return False

            # Click the Assign button
            try:
                # Scroll into view first
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", assign_button)
                time.sleep(0.3)  # Small delay
                
                # Try JavaScript click (most reliable)
                d.execute_script("arguments[0].click();", assign_button)
                self.log("[ASSIGN-BUTTON] Assign button clicked successfully (JavaScript)")
                
                # Wait a moment for popup to appear
                time.sleep(2)
                
            except Exception as e:
                self.log(f"[ASSIGN-BUTTON][WARN] JavaScript click failed: {e}, trying regular click")
                try:
                    assign_button.click()
                    self.log("[ASSIGN-BUTTON] Assign button clicked successfully (Selenium)")
                    time.sleep(2)
                except Exception as click_error:
                    self.log(f"[ASSIGN-BUTTON][ERROR] Failed to click Assign button: {click_error}")
                    return False

            # Check if popup actually appeared
            self.log("[ASSIGN-BUTTON] Checking if assignment popup appeared...")
            try:
                # Wait for popup to load
                WebDriverWait(d, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                self.log("[ASSIGN-BUTTON] ✓ Assignment popup loaded successfully")
            except Exception as e:
                self.log(f"[ASSIGN-BUTTON][WARN] Assignment popup may not have loaded: {e}")
                # Don't return False here - popup might still be loading

            return True

        except Exception as e:
            self.log(f"[ASSIGN-BUTTON][ERROR] Failed to click Assign button: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def enter_note_and_save(self, counselor_name: str, timeout: int = 15) -> bool:
        """
        Enter the referral meeting assignment note in the popup text box and save.
        Note format: "[Today's Date]: Referral Meeting Assigned to [Counselor Name]."
        """
        if not self.driver:
            self.log("[NOTE-ENTER] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from datetime import datetime
            import time
        except Exception as e:
            self.log(f"[NOTE-ENTER][ERROR] Imports failed: {e}"); return False

        d = self.driver

        try:
            # Format today's date as MM/DD/YYYY
            today = datetime.now().strftime("%m/%d/%Y")
            assignment_note = f"{today}: Referral Meeting Assigned to {counselor_name}."
            
            self.log(f"[NOTE-ENTER] Preparing note: '{assignment_note}'")
            
            # Switch to default content first
            d.switch_to.default_content()
            
            # Use comprehensive JavaScript approach to find and interact with assignment popup
            self.log("[NOTE-ENTER] Searching for assignment popup elements...")
            try:
                # JavaScript to search all iframes and main document for assignment popup
                js_code = """
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
                    // Set the textarea value
                    mainTextarea.value = assignmentNote;
                    // Try to sync the rich text editor
                    try {
                        if (window.syncTextarea) syncTextarea();
                        if (window.copyRichTextToTextAreaAll) copyRichTextToTextAreaAll();
                    } catch(e) {}
                    
                    if (mainSaveButton) {
                        mainSaveButton.click();
                        return { success: true, location: 'main document', method: 'textarea' };
                    }
                }
                
                // Search all iframes
                var iframes = document.getElementsByTagName('iframe');
                for (var i = 0; i < iframes.length; i++) {
                    try {
                        var iframeDoc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                        var iframeTextarea = iframeDoc.getElementById('tar_wlResultCom_id');
                        var iframeEditor = iframeDoc.getElementById('tar_wlResultCom_id_editor');
                        var iframeSaveButton = iframeDoc.getElementById('iframeEditSaveButton');
                        
                        // Also check parent document for save button
                        if (!iframeSaveButton) {
                            try {
                                iframeSaveButton = document.getElementById('iframeEditSaveButton');
                            } catch(e) {}
                        }
                        
                        results.push({
                            location: 'iframe ' + (i+1) + ' (id: ' + (iframes[i].id || 'no-id') + ')',
                            textarea: iframeTextarea ? 'found' : 'not found',
                            editor: iframeEditor ? 'found' : 'not found',
                            saveButton: iframeSaveButton ? 'found' : 'not found'
                        });
                        
                        // Try textarea first
                        if (iframeTextarea) {
                            iframeTextarea.value = assignmentNote;
                            // Try to sync
                            try {
                                if (iframeDoc.syncTextarea) iframeDoc.syncTextarea();
                                if (iframeDoc.copyRichTextToTextAreaAll) iframeDoc.copyRichTextToTextAreaAll();
                            } catch(e) {}
                            
                            if (iframeSaveButton) {
                                iframeSaveButton.click();
                                return { success: true, location: 'iframe ' + (i+1), method: 'textarea' };
                            }
                        }
                        
                        // Try contenteditable editor
                        if (iframeEditor) {
                            try {
                                var contenteditable = iframeEditor.querySelector('[contenteditable="true"]');
                                if (contenteditable) {
                                    var div = iframeDoc.createElement('div');
                                    div.appendChild(iframeDoc.createTextNode(assignmentNote));
                                    contenteditable.appendChild(div);
                                    contenteditable.dispatchEvent(new Event('input', {bubbles: true}));
                                    contenteditable.dispatchEvent(new Event('change', {bubbles: true}));
                                    
                                    // Try to sync
                                    try {
                                        if (iframeDoc.syncTextarea) iframeDoc.syncTextarea();
                                        if (iframeDoc.copyRichTextToTextAreaAll) iframeDoc.copyRichTextToTextAreaAll();
                                    } catch(e) {}
                                    
                                    if (iframeSaveButton) {
                                        iframeSaveButton.click();
                                        return { success: true, location: 'iframe ' + (i+1), method: 'contenteditable' };
                                    }
                                }
                            } catch(e) {
                                results.push({ location: 'iframe ' + (i+1), error: e.message });
                            }
                        }
                    } catch (e) {
                        results.push({
                            location: 'iframe ' + (i+1),
                            error: e.message
                        });
                    }
                }
                
                return { success: false, results: results };
                """
                
                result = d.execute_script(js_code, assignment_note)
                self.log(f"[NOTE-ENTER] JavaScript search result: {result}")
                
                if result.get('success'):
                    self.log(f"[NOTE-ENTER] ✓ SUCCESS: Note entered and saved via {result.get('method', 'unknown')} method in {result.get('location', 'unknown')}!")
                    time.sleep(2)  # Wait for save to process
                    return True
                else:
                    self.log("[NOTE-ENTER][WARN] JavaScript approach did not find elements, trying Selenium approach...")
                    
            except Exception as e:
                self.log(f"[NOTE-ENTER][WARN] JavaScript approach failed: {e}")
            
            # Fallback: Try Selenium approach
            self.log("[NOTE-ENTER] Trying Selenium iframe switching approach...")
            try:
                # Switch to dynamicIframe (the popup iframe)
                d.switch_to.default_content()
                WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                
                self.log("[NOTE-ENTER] Switched to dynamicIframe, looking for textarea...")
                
                # Find the textarea
                textarea = WebDriverWait(d, timeout).until(
                    EC.presence_of_element_located((By.ID, "tar_wlResultCom_id"))
                )
                
                # Set the value
                d.execute_script("arguments[0].value = arguments[1];", textarea, assignment_note)
                self.log("[NOTE-ENTER] Note entered into textarea")
                
                # Try to sync the rich text editor
                try:
                    d.execute_script("if (window.syncTextarea) syncTextarea();")
                    d.execute_script("if (window.copyRichTextToTextAreaAll) copyRichTextToTextAreaAll();")
                except Exception:
                    pass
                
                # Switch back to parent frame to find save button
                d.switch_to.default_content()
                WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                
                # Find and click save button
                save_button = WebDriverWait(d, timeout).until(
                    EC.element_to_be_clickable((By.ID, "iframeEditSaveButton"))
                )
                
                d.execute_script("arguments[0].click();", save_button)
                self.log("[NOTE-ENTER] ✓ Save button clicked successfully!")
                time.sleep(2)  # Wait for save to process
                return True
                
            except Exception as e:
                self.log(f"[NOTE-ENTER][ERROR] Selenium approach failed: {e}")
                return False

        except Exception as e:
            self.log(f"[NOTE-ENTER][ERROR] Failed to enter note and save: {e}")
            import traceback
            self.log(f"[NOTE-ENTER][ERROR] Traceback: {traceback.format_exc()}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

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
            if word.lower() in program_indicators:
                program_words.append(word)
            else:
                name_words.append(word)
        
        return {
            'words': name_words,
            'program': ' '.join(program_words)
        }
    
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
                if option_parts['program'] and 'ips' in option_parts['program'].lower():
                    self.log(f"[SERVICE-FILE-WIZARD][MATCH] ❌ Option has IPS but target doesn't - rejecting '{option_text}'")
                    return False
            
            # Additional check: make sure we're not matching a partial name
            # (e.g., "Ana Perez" when looking for "Ethel Perez")
            if len(counselor_words) > 1:  # Multi-word names
                # Check if option has extra words that aren't program indicators
                extra_words = option_words - counselor_words
                if extra_words:
                    program_indicators = {'ips', 'counselor', 'therapist', 'worker', 'staff', 'team'}
                    non_program_words = extra_words - {w.lower() for w in program_indicators}
                    if non_program_words:
                        self.log(f"[SERVICE-FILE-WIZARD][MATCH] ❌ Extra non-program words: {non_program_words}")
                        return False
            
            self.log(f"[SERVICE-FILE-WIZARD][MATCH] ✅ MATCH FOUND!")
            return True
            
        except Exception as e:
            self.log(f"[SERVICE-FILE-WIZARD][MATCH] Error in matching: {e}")
            return False

    def complete_service_file_wizard_select_primary_worker_NEW(self, counselor_name: str, is_ips: bool = False, timeout: int = 12) -> bool:
        """
        NEW SIMPLIFIED VERSION: Based on working counselor_assignment_bot.py
        Step 1: Find primary worker input field
        Step 2: Type partial last name using send_keys (triggers suggestlu.js)
        Step 3: Wait for dropdown to appear
        Step 4: Find matching option in dropdown
        Step 5: Click the option
        Step 6: Verify selection
        Step 7: Click Finish button
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        if not self.driver:
            self.log("[SERVICE-FILE-WIZARD] No driver.")
            return False

        d = self.driver

        try:
            # Step 1: Find the primary worker input field
            # It's in a nested iframe structure: dynamicAltframe -> child iframe -> kCWorkerIDPrim_elem
            self.log("[SERVICE-FILE-WIZARD][NEW] Finding primary worker input field...")
            
            # Switch to default content first
            d.switch_to.default_content()
            
            # Try to find the input in the main iframes
            primary_input = None
            iframe_path = []
            
            # Try dynamicAltframe first (most common)
            try:
                d.switch_to.frame("dynamicAltframe")
                iframe_path.append("dynamicAltframe")
                self.log("[SERVICE-FILE-WIZARD][NEW] Switched to dynamicAltframe")
                
                # Check for child iframes
                child_iframes = d.find_elements(By.TAG_NAME, "iframe")
                if child_iframes:
                    for i, child_iframe in enumerate(child_iframes):
                        try:
                            d.switch_to.frame(child_iframe)
                            iframe_path.append(f"child_iframe_{i}")
                            self.log(f"[SERVICE-FILE-WIZARD][NEW] Switched to child iframe {i}")
                            
                            # Try to find the input
                            try:
                                primary_input = d.find_element(By.ID, "kCWorkerIDPrim_elem")
                                self.log(f"[SERVICE-FILE-WIZARD][NEW] Found primary input in {iframe_path}")
                                break
                            except Exception:
                                pass
                            
                            # If not found, go back
                            d.switch_to.parent_frame()
                            iframe_path.pop()
                        except Exception:
                            if iframe_path and iframe_path[-1].startswith("child_iframe"):
                                d.switch_to.parent_frame()
                                iframe_path.pop()
                            continue
                
                # If not found in child iframes, check current frame
                if not primary_input:
                    try:
                        primary_input = d.find_element(By.ID, "kCWorkerIDPrim_elem")
                        self.log(f"[SERVICE-FILE-WIZARD][NEW] Found primary input in dynamicAltframe")
                    except Exception:
                        pass
                        
            except Exception:
                pass
            
            # If still not found, try other iframes
            if not primary_input:
                d.switch_to.default_content()
                iframe_path = []
                # Try scanning all iframes
                all_iframes = d.find_elements(By.TAG_NAME, "iframe")
                for i, iframe in enumerate(all_iframes):
                    try:
                        d.switch_to.default_content()
                        d.switch_to.frame(iframe)
                        try:
                            primary_input = d.find_element(By.ID, "kCWorkerIDPrim_elem")
                            self.log(f"[SERVICE-FILE-WIZARD][NEW] Found primary input in iframe {i}")
                            break
                        except Exception:
                            # Check child iframes
                            child_iframes = d.find_elements(By.TAG_NAME, "iframe")
                            for j, child_iframe in enumerate(child_iframes):
                                try:
                                    d.switch_to.frame(child_iframe)
                                    try:
                                        primary_input = d.find_element(By.ID, "kCWorkerIDPrim_elem")
                                        self.log(f"[SERVICE-FILE-WIZARD][NEW] Found primary input in iframe {i}.{j}")
                                        break
                                    except Exception:
                                        d.switch_to.parent_frame()
                                except Exception:
                                    pass
                            if primary_input:
                                break
                        d.switch_to.default_content()
                    except Exception:
                        d.switch_to.default_content()
                        continue
            
            if not primary_input:
                self.log("[SERVICE-FILE-WIZARD][NEW][ERROR] Could not find primary worker input field")
                d.switch_to.default_content()
                return False
            
            # Step 2: Clear and type partial last name using send_keys (triggers suggestlu.js)
            try:
                self.log("[SERVICE-FILE-WIZARD][NEW] Clearing input field...")
                try:
                    primary_input.clear()
                except Exception:
                    d.execute_script("arguments[0].value = '';", primary_input)
                
                # Extract last name
                last_name = self._extract_last_name(counselor_name)
                # Start with partial last name (all but last letter)
                partial_last_name = last_name[:-1] if len(last_name) > 1 else last_name
                
                # Minimum length to try (don't go below 2-3 letters as it's too short)
                min_length = max(2, min(3, len(last_name) // 3))
                
                # Retry loop: Type partial name, check dropdown, if no dropdown, remove one letter and try again
                dropdown_options = []
                attempt = 0
                max_attempts = len(partial_last_name) - min_length + 1
                
                while attempt < max_attempts:
                    current_partial = partial_last_name if attempt == 0 else partial_last_name[:-attempt]
                    
                    # Skip if we've gone too short
                    if len(current_partial) < min_length:
                        self.log(f"[SERVICE-FILE-WIZARD][NEW] Stopping retries - partial name too short: '{current_partial}'")
                        break
                    
                    self.log(f"[SERVICE-FILE-WIZARD][NEW] Attempt {attempt + 1}: Typing partial last name '{current_partial}' (length: {len(current_partial)})...")
                    
                    # Clear the field first (except on first attempt where it's already cleared)
                    if attempt > 0:
                        try:
                            primary_input.clear()
                            time.sleep(0.2)
                        except Exception:
                            d.execute_script("arguments[0].value = '';", primary_input)
                            time.sleep(0.2)
                    
                    # Type slowly character by character (this triggers suggestlu.js)
                    for ch in current_partial:
                        try:
                            primary_input.send_keys(ch)
                            time.sleep(0.05)  # Slightly slower to give suggestlu.js time
                        except Exception as ch_error:
                            # If send_keys fails, try JavaScript for this character
                            try:
                                d.execute_script("arguments[0].value += arguments[1];", primary_input, ch)
                                # Trigger input event
                                d.execute_script("""
                                    var elem = arguments[0];
                                    var event = new Event('input', { bubbles: true, cancelable: true });
                                    elem.dispatchEvent(event);
                                """, primary_input)
                                time.sleep(0.05)  # Slightly slower to give suggestlu.js time
                            except Exception:
                                self.log(f"[SERVICE-FILE-WIZARD][NEW][WARN] Failed to type character '{ch}'")
                                break
                    
                    time.sleep(0.8)  # Wait for typing to complete and suggestlu.js to process
                    self.log(f"[SERVICE-FILE-WIZARD][NEW] Finished typing '{current_partial}', waiting for dropdown...")
                    
                    # Step 3: Trigger dropdown and wait for it to appear
                    try:
                        self.log("[SERVICE-FILE-WIZARD][NEW] Triggering dropdown...")
                        # Click input to focus
                        try:
                            primary_input.click()
                        except Exception:
                            d.execute_script("arguments[0].focus();", primary_input)
                        time.sleep(0.5)
                        
                        # Press ARROW_DOWN to trigger dropdown
                        try:
                            primary_input.send_keys(Keys.ARROW_DOWN)
                        except Exception:
                            pass
                        time.sleep(1.0)  # Give more time for dropdown to appear
                        
                        # Wait for dropdown to appear (suggestlu.js needs time)
                        self.log("[SERVICE-FILE-WIZARD][NEW] Waiting for dropdown to appear...")
                        time.sleep(2.5)  # Give suggestlu.js time to load
                        
                    except Exception as e:
                        self.log(f"[SERVICE-FILE-WIZARD][NEW][WARN] Error triggering dropdown: {e}")
                    
                    # Step 4: Check if dropdown options appeared
                    target_name = f"{counselor_name} - IPS" if is_ips else counselor_name
                    
                    # Try to find dropdown options (table-based for Penelope)
                    dropdown_selectors = [
                        (By.XPATH, "//div[contains(@id,'kCWorkerIDPrim_elem') and contains(@id,'sugg')]//table//tr[not(@tblkey='showAll')]"),
                        (By.XPATH, "//table[contains(@id,'luResultTable')]//tr[@tblkey and @tblkey!='showAll']"),
                        (By.XPATH, "//table//tr[@tblkey and @tblkey!='showAll']"),
                    ]
                    
                    dropdown_options = []
                    for by, selector in dropdown_selectors:
                        try:
                            options = d.find_elements(by, selector)
                            visible_options = [opt for opt in options if opt.is_displayed()]
                            if visible_options:
                                dropdown_options = visible_options
                                self.log(f"[SERVICE-FILE-WIZARD][NEW] ✓ Found {len(visible_options)} dropdown options with '{current_partial}'")
                                break
                        except Exception:
                            continue
                    
                    # If dropdown appeared, break out of retry loop
                    if dropdown_options:
                        partial_last_name = current_partial  # Update to the working partial name
                        break
                    else:
                        self.log(f"[SERVICE-FILE-WIZARD][NEW] No dropdown options found with '{current_partial}', will try with one less letter...")
                        attempt += 1
                        if attempt < max_attempts:
                            self.log(f"[SERVICE-FILE-WIZARD][NEW] Waiting before removing a letter...")
                            time.sleep(1.0)  # Wait before trying again
                
                if not dropdown_options:
                    self.log(f"[SERVICE-FILE-WIZARD][NEW][ERROR] No dropdown options found after {attempt} attempts")
                    d.switch_to.default_content()
                    return False
                
            except Exception as e:
                self.log(f"[SERVICE-FILE-WIZARD][NEW][ERROR] Failed to type or find dropdown: {e}")
                d.switch_to.default_content()
                return False
            
            # Step 5: Match and click the option (dropdown_options already found above)
            matched_option = None
            matched_tblkey = None
            target_name = f"{counselor_name} - IPS" if is_ips else counselor_name
            
            self.log(f"[SERVICE-FILE-WIZARD][NEW] Looking for '{target_name}' in dropdown...")
            self.log(f"[SERVICE-FILE-WIZARD][NEW] Matching options against '{target_name}'...")
            
            # Parse target name for matching
            target_parts = self._is_counselor_match(target_name, "", is_ips)
            
            for i, option in enumerate(dropdown_options):
                try:
                    option_text = option.text.strip()
                    option_tblkey = option.get_attribute('tblkey') or ''
                    
                    # Parse option name
                    option_parts = self._is_counselor_match(option_text, "", is_ips)
                    
                    # Compare
                    if target_parts and option_parts:
                        if (target_parts['words'] == option_parts['words'] or 
                            set(target_parts['words']) == set(option_parts['words'])):
                            if target_parts['program'] == option_parts['program']:
                                matched_option = option
                                matched_tblkey = option_tblkey
                                self.log(f"[SERVICE-FILE-WIZARD][NEW] ✅ MATCH FOUND: '{option_text}' (tblkey={option_tblkey})")
                                break
                except Exception:
                    continue
            
            if not matched_option:
                self.log(f"[SERVICE-FILE-WIZARD][NEW][ERROR] No matching option found for '{target_name}'")
                d.switch_to.default_content()
                return False
            
            # Step 6: Click the matched option using JavaScript by tblkey (most reliable)
            try:
                self.log(f"[SERVICE-FILE-WIZARD][NEW] Clicking option with tblkey '{matched_tblkey}'...")
                
                # Use JavaScript to click by tblkey (avoids stale element issues)
                click_success = d.execute_script(f"""
                    try {{
                        var trs = document.querySelectorAll('tr[tblkey="{matched_tblkey}"]');
                        for (var i = 0; i < trs.length; i++) {{
                            var tr = trs[i];
                            var rect = tr.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {{
                                tr.scrollIntoView({{block: 'nearest'}});
                                tr.focus();
                                tr.click();
                                // Also dispatch click event
                                var clickEvent = new MouseEvent('click', {{
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                }});
                                tr.dispatchEvent(clickEvent);
                                return true;
                            }}
                        }}
                        return false;
                    }} catch (e) {{
                        return false;
                    }}
                """)
                
                if click_success:
                    self.log(f"[SERVICE-FILE-WIZARD][NEW] ✅ Clicked option successfully")
                else:
                    self.log(f"[SERVICE-FILE-WIZARD][NEW][WARN] JavaScript click returned false")
                
                # Wait for selection to register
                time.sleep(1.0)
                
            except Exception as e:
                self.log(f"[SERVICE-FILE-WIZARD][NEW][ERROR] Failed to click option: {e}")
                d.switch_to.default_content()
                return False
            
            # Step 7: Verify selection (but don't fail if verification is uncertain)
            self.log("[SERVICE-FILE-WIZARD][NEW] Verifying selection...")
            selection_verified = False
            
            try:
                # Check hidden input
                hidden_inputs = d.find_elements(By.NAME, "kCWorkerIDPrim")
                if hidden_inputs:
                    try:
                        val = d.execute_script("return arguments[0].value;", hidden_inputs[0]) or ""
                        if not val:
                            val = hidden_inputs[0].get_attribute("value") or ""
                        if val.strip() and val != "-2147483648":
                            selection_verified = True
                            self.log(f"[SERVICE-FILE-WIZARD][NEW] ✅ VERIFIED: Hidden input = '{val}'")
                    except Exception:
                        pass
                
                # Check visible input
                if not selection_verified:
                    try:
                        fresh_input = d.find_element(By.ID, "kCWorkerIDPrim_elem")
                        vis_val = d.execute_script("return arguments[0].value;", fresh_input) or ""
                        if not vis_val:
                            vis_val = fresh_input.get_attribute("value") or ""
                        if vis_val.strip() and (counselor_name.split()[-1].lower() in vis_val.lower()):
                            selection_verified = True
                            self.log(f"[SERVICE-FILE-WIZARD][NEW] ✅ VERIFIED: Visible input = '{vis_val}'")
                    except Exception:
                        pass
                        
            except Exception as e:
                self.log(f"[SERVICE-FILE-WIZARD][NEW][WARN] Verification error: {e}")
            
            # Step 8: Switch to default content and click Finish
            d.switch_to.default_content()
            
            if not selection_verified:
                self.log("[SERVICE-FILE-WIZARD][NEW][WARN] Selection not verified, but proceeding to Finish anyway")
            
            # Find and click Finish button
            finish_selectors = [
                (By.ID, "wizFinishButton"),
                (By.XPATH, "//button[translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='finish']"),
            ]
            
            for by, selector in finish_selectors:
                try:
                    finish_btn = d.find_element(by, selector)
                    if finish_btn and finish_btn.is_displayed():
                        try:
                            finish_btn.click()
                            self.log("[SERVICE-FILE-WIZARD][NEW] ✅ Clicked Finish button")
                            time.sleep(2)
                            return True
                        except Exception:
                            try:
                                d.execute_script("arguments[0].click();", finish_btn)
                                self.log("[SERVICE-FILE-WIZARD][NEW] ✅ Clicked Finish button via JS")
                                time.sleep(2)
                                return True
                            except Exception:
                                continue
                except Exception:
                    continue
            
            self.log("[SERVICE-FILE-WIZARD][NEW][ERROR] Could not find/click Finish button")
            return False
            
        except Exception as e:
            self.log(f"[SERVICE-FILE-WIZARD][NEW][ERROR] Unexpected error: {e}")
            try:
                d.switch_to.default_content()
            except Exception:
                pass
            return False

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
            # CRITICAL: Re-find the element right before typing to avoid stale element references
            try:
                # Re-find the element to ensure it's fresh and we're in the correct iframe context
                try:
                    primary_input = d.find_element(By.ID, "kCWorkerIDPrim_elem")
                    self.log("[SERVICE-FILE-WIZARD] Re-found primary worker input before typing")
                except Exception:
                    self.log("[SERVICE-FILE-WIZARD][WARN] Could not re-find input, using existing reference")
                
                # Clear the input
                try:
                    primary_input.clear()
                except Exception:
                    try:
                        d.execute_script("arguments[0].value = '';", primary_input)
                    except Exception:
                        # If element is stale, find it via JavaScript
                        d.execute_script("""
                            var input = document.getElementById('kCWorkerIDPrim_elem');
                            if (input) { input.value = ''; }
                        """)
                
                # Smart parsing: Handle both "Last, First" and "First Last" formats
                # Extract the actual last name regardless of format
                last_name = self._extract_last_name(counselor_name)
                
                # Sequential retry loop: Start with all but last letter, then remove one letter at a time
                # Minimum 3 letters to avoid too many results
                min_length = 3
                max_attempts = max(1, len(last_name) - min_length) if len(last_name) > min_length else 1
                
                # Start with all but the last letter
                initial_partial = last_name[:-1] if len(last_name) > 1 else last_name
                
                self.log(f"[SERVICE-FILE-WIZARD] Searching for counselor '{counselor_name}' -> extracted last name: '{last_name}'")
                self.log(f"[SERVICE-FILE-WIZARD] Will try sequential search starting with '{initial_partial}', removing one letter each attempt if needed")
                
                match_found = False
                for attempt in range(max_attempts + 1):
                    # Calculate partial name for this attempt
                    # Attempt 0: all but last letter (e.g., "Fitzgeral")
                    # Attempt 1: one less letter (e.g., "Fitzgera")
                    # Attempt 2: one less letter (e.g., "Fitzger")
                    # etc.
                    if attempt == 0:
                        partial_last_name = initial_partial
                    else:
                        # Remove one more letter from the end
                        partial_last_name = initial_partial[:-attempt] if len(initial_partial) > attempt else initial_partial
                    
                    # Don't go below minimum length
                    if len(partial_last_name) < min_length:
                        self.log(f"[SERVICE-FILE-WIZARD][WARN] Partial name '{partial_last_name}' is too short (min {min_length} letters), stopping retry")
                        break
                    
                    self.log(f"[SERVICE-FILE-WIZARD] Attempt {attempt + 1}/{max_attempts + 1}: Trying partial name '{partial_last_name}'")
                    
                    # Clear the input field before each attempt
                    try:
                        # Re-find the input to avoid stale references
                        try:
                            primary_input = d.find_element(By.ID, "kCWorkerIDPrim_elem")
                        except Exception:
                            self.log(f"[SERVICE-FILE-WIZARD][WARN] Could not re-find input on attempt {attempt + 1}")
                            break
                        
                        # Clear the field
                        try:
                            primary_input.clear()
                        except Exception:
                            try:
                                d.execute_script("arguments[0].value = '';", primary_input)
                            except Exception:
                                d.execute_script("""
                                    var input = document.getElementById('kCWorkerIDPrim_elem');
                                    if (input) { input.value = ''; }
                                """)
                        
                        # Small delay after clearing
                        time.sleep(0.3)
                    except Exception as clear_err:
                        self.log(f"[SERVICE-FILE-WIZARD][WARN] Could not clear input on attempt {attempt + 1}: {clear_err}")
                    
                    # Try typing with send_keys first
                    typing_success = False
                    try:
                        # Type slowly to trigger suggestions reliably (0.05s per char for better reliability)
                        for ch in partial_last_name:
                            primary_input.send_keys(ch)
                            time.sleep(0.05)
                        typing_success = True
                        self.log(f"[SERVICE-FILE-WIZARD] Typed '{partial_last_name}' using send_keys")
                    except Exception as e_send_keys:
                        self.log(f"[SERVICE-FILE-WIZARD][WARN] send_keys failed: {e_send_keys}, trying JavaScript fallback...")
                        # JavaScript fallback: Set value and trigger input events to trigger suggestlu.js
                        try:
                            typing_success = d.execute_script(f"""
                                try {{
                                    var input = document.getElementById('kCWorkerIDPrim_elem');
                                    if (!input) {{
                                        return false;
                                    }}
                                    // Clear first
                                    input.value = '';
                                    // Set the partial name
                                    input.value = '{partial_last_name}';
                                    // Trigger input events to activate suggestlu.js dropdown
                                    var inputEvent = new Event('input', {{ bubbles: true }});
                                    input.dispatchEvent(inputEvent);
                                    var keyupEvent = new Event('keyup', {{ bubbles: true }});
                                    input.dispatchEvent(keyupEvent);
                                    var changeEvent = new Event('change', {{ bubbles: true }});
                                    input.dispatchEvent(changeEvent);
                                    // Also trigger focus to ensure dropdown appears
                                    input.focus();
                                    // Trigger suggestlu.js specific events if they exist
                                    if (input.dispatchEvent) {{
                                        var customEvent = new CustomEvent('keyup', {{ detail: {{ key: 'F' }} }});
                                        input.dispatchEvent(customEvent);
                                    }}
                                    return true;
                                }} catch (e) {{
                                    console.error('JavaScript typing failed:', e);
                                    return false;
                                }}
                            """)
                            if typing_success:
                                self.log(f"[SERVICE-FILE-WIZARD] Typed '{partial_last_name}' using JavaScript fallback")
                            else:
                                self.log(f"[SERVICE-FILE-WIZARD][ERROR] JavaScript typing returned false")
                        except Exception as e_js:
                            self.log(f"[SERVICE-FILE-WIZARD][ERROR] JavaScript typing failed: {e_js}")
                            typing_success = False
                    
                    if not typing_success:
                        self.log(f"[SERVICE-FILE-WIZARD][WARN] All typing methods failed for '{partial_last_name}' on attempt {attempt + 1}")
                        # Continue to next attempt with shorter name
                        continue
                    
                    # Wait for dropdown to appear (suggestlu.js needs time to process)
                    # Longer wait (0.8s) to ensure dropdown has time to populate
                    time.sleep(0.8)
                    self.log(f"[SERVICE-FILE-WIZARD] Typed partial name '{partial_last_name}', waiting for dropdown...")
                    
                    # Try to find dropdown options - if we find any (besides "Show All"), we can proceed
                    # We'll check in accept_typed_suggestion_and_finish, but we can do a quick check here
                    try:
                        # Quick check: see if dropdown has any options (besides "Show All")
                        time.sleep(2.5)  # Wait longer for dropdown to appear
                        options_check = d.find_elements(By.XPATH, "//div[contains(@id,'kCWorkerIDPrim_elem') and contains(@id,'sugg')]//table//tr[not(@tblkey='showAll')]")
                        if options_check:
                            visible_options = [opt for opt in options_check if opt.is_displayed()]
                            if visible_options:
                                self.log(f"[SERVICE-FILE-WIZARD] ✅ Found {len(visible_options)} dropdown option(s) with partial '{partial_last_name}' - proceeding to match")
                                match_found = True
                                break
                            else:
                                self.log(f"[SERVICE-FILE-WIZARD] Found {len(options_check)} options but none visible with partial '{partial_last_name}' - trying shorter name")
                        else:
                            self.log(f"[SERVICE-FILE-WIZARD] No dropdown options found with partial '{partial_last_name}' - trying shorter name")
                    except Exception as check_err:
                        self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Could not check dropdown options: {check_err} - will proceed to full search")
                        # Continue anyway - accept_typed_suggestion_and_finish will do a full search
                        match_found = True  # Assume we should try matching
                        break
                
                if not match_found:
                    self.log(f"[SERVICE-FILE-WIZARD][ERROR] Could not find dropdown options after {max_attempts + 1} attempts with sequential name shortening")
                    try:
                        d.switch_to.default_content()
                    except Exception:
                        pass
                    return False
                
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
        OLD METHOD - No longer used, kept for reference.
        The new complete_service_file_wizard_select_primary_worker handles everything.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
        import time
        import os

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
                # Try one more approach - wait even longer and check if dropdown appears
                # Sometimes the dropdown takes longer to load, especially on slower connections
                self.log("[SERVICE-FILE-WIZARD][DEBUG] No dropdown found with standard selectors, trying extended wait...")
                
                # Wait and check periodically - don't do anything that might interfere
                for wait_attempt in range(3):
                    time.sleep(1.5)  # Wait 1.5 seconds each time
                    try:
                        # Check if dropdown appeared
                        sugg_div = d.find_element(By.XPATH, "//div[contains(@id,'kCWorkerIDPrim_elem') and contains(@id,'sugg')]")
                        if sugg_div and sugg_div.is_displayed():
                            # Dropdown appeared - try to read options again
                            self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Dropdown appeared after extended wait attempt {wait_attempt + 1}")
                            # Try reading options again with the first selector
                            try:
                                options = d.find_elements(By.XPATH, "//div[contains(@id,'kCWorkerIDPrim_elem') and contains(@id,'sugg')]//table//tr[not(@tblkey='showAll')]")
                                if options:
                                    visible_options = [opt for opt in options if opt.is_displayed()]
                                    if visible_options:
                                        dropdown_options = visible_options
                                        dropdown_found = True
                                        self.log(f"[SERVICE-FILE-WIZARD] ✅ Found {len(visible_options)} dropdown options after extended wait")
                                        break
                            except Exception:
                                pass
                    except Exception:
                        pass
                
                # If still not found after extended wait, log warning
                if not dropdown_found:
                    self.log("[SERVICE-FILE-WIZARD][WARN] Dropdown still not found after extended wait - may need manual intervention")
                
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
                            
                            # Log the actual dropdown text format for debugging
                            self.log(f"[SERVICE-FILE-WIZARD][MATCH] Comparing dropdown option '{opt_text}' with target '{target_name}' and counselor '{counselor_name}'")
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
                    # 4) **CRITICAL: Store tblkey and re-find element before clicking to avoid stale element**
                    matched_tblkey = None
                    try:
                        # Extract tblkey from the matched option (this is stable)
                        if matched_option.tag_name.lower() == 'tr':
                            matched_tblkey = matched_option.get_attribute('tblkey') or ''
                            self.log(f"[SERVICE-FILE-WIZARD] Stored tblkey '{matched_tblkey}' for matched option")
                    except Exception:
                        pass
                    
                    # **CRITICAL: Click using the actual element reference (like working bot does)**
                    # The working bot clicks matched_option directly - this preserves event listeners
                    click_attempted = False
                    
                    # Method 1: Try clicking the actual element reference (like working bot)
                    # This preserves event listeners that suggestlu.js has attached
                    try:
                        self.log(f"[SERVICE-FILE-WIZARD] Clicking matched option directly (like working bot)...")
                        
                        # Scroll into view first
                        d.execute_script("arguments[0].scrollIntoView({block:'nearest'});", matched_option)
                        time.sleep(0.1)
                        
                        # Try regular click first (preserves event listeners)
                        try:
                            matched_option.click()
                            click_attempted = True
                            self.log(f"[SERVICE-FILE-WIZARD] ✅ Clicked option via Selenium click()")
                        except Exception as e_click:
                            # Fallback: JavaScript click on element reference
                            self.log(f"[SERVICE-FILE-WIZARD][WARN] Selenium click failed: {e_click}, trying JavaScript...")
                            try:
                                d.execute_script("arguments[0].click();", matched_option)
                                click_attempted = True
                                self.log(f"[SERVICE-FILE-WIZARD] ✅ Clicked option via JavaScript on element reference")
                            except Exception as e_js:
                                self.log(f"[SERVICE-FILE-WIZARD][WARN] JavaScript click on element reference failed: {e_js}")
                    except Exception as e_direct:
                        self.log(f"[SERVICE-FILE-WIZARD][WARN] Direct element click failed: {e_direct}")
                    
                    # Fallback: If element reference is stale, use tblkey-based JavaScript
                    if not click_attempted and matched_tblkey:
                        try:
                            self.log(f"[SERVICE-FILE-WIZARD] Fallback: Clicking via tblkey '{matched_tblkey}'...")
                            click_result = d.execute_script(f"""
                                try {{
                                    var trs = document.querySelectorAll('tr[tblkey="{matched_tblkey}"]');
                                    for (var i = 0; i < trs.length; i++) {{
                                        var tr = trs[i];
                                        var rect = tr.getBoundingClientRect();
                                        if (rect.width > 0 && rect.height > 0) {{
                                            tr.scrollIntoView({{block: 'nearest', behavior: 'instant'}});
                                            tr.click();
                                            return true;
                                        }}
                                    }}
                                    return false;
                                }} catch (e) {{
                                    console.error('JavaScript click failed:', e);
                                    return false;
                                }}
                            """)
                            
                            if click_result:
                                click_attempted = True
                                self.log(f"[SERVICE-FILE-WIZARD] ✅ Clicked option via JavaScript tblkey fallback")
                        except Exception as e_fallback:
                            self.log(f"[SERVICE-FILE-WIZARD][WARN] JavaScript tblkey fallback failed: {e_fallback}")
                    
                    # **CRITICAL: Wait for click to register, then ALWAYS verify (even if click seemed to fail)**
                    # Sometimes the click works but throws an exception due to stale element reference
                    time.sleep(0.5)
                    self.log(f"[SERVICE-FILE-WIZARD] Click attempt completed (attempted: {click_attempted}), proceeding to verification...")
                else:
                    self.log(f"[SERVICE-FILE-WIZARD][ERROR] Could not find matching option for '{target_name}'")
                    self.log(f"[SERVICE-FILE-WIZARD][ERROR] Available options were: {[opt.text.strip() if hasattr(opt, 'text') else 'N/A' for opt in dropdown_options]}")
                    return False

            # 5) **CRITICAL: Verify the selection was actually registered**
            # We MUST verify before proceeding, even if click seemed to fail
            # Sometimes the click works but element reference was stale
            selection_verified = False
            verification_attempts = 0
            max_verification_attempts = 20  # Check for up to 3 seconds (20 * 0.15)
            
            try:
                end = time.time() + 4.0  # Give it 4 seconds to verify
                while time.time() < end and not selection_verified:
                    verification_attempts += 1
                    
                    try:
                        # Method 1: Try the hidden input first (most reliable)
                        hidden_inputs = d.find_elements(By.NAME, "kCWorkerIDPrim")
                        if hidden_inputs:
                            try:
                                # Use JavaScript to get value (avoids stale element issues)
                                val = d.execute_script("return arguments[0].value;", hidden_inputs[0]) or ""
                                if not val:
                                    # Fallback: try get_attribute
                                    try:
                                        val = hidden_inputs[0].get_attribute("value") or ""
                                    except Exception:
                                        val = ""
                                
                                if val.strip() and val != "-2147483648" and val != "":
                                    selection_verified = True
                                    self.log(f"[SERVICE-FILE-WIZARD] ✅ VERIFIED: Hidden kCWorkerIDPrim populated with value '{val}' (attempt {verification_attempts})")
                                    break
                                elif verification_attempts == 1:
                                    self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Hidden input value: '{val}' (empty/default, attempt {verification_attempts})")
                            except Exception as hidden_check_error:
                                if verification_attempts == 1:
                                    self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Error checking hidden input: {hidden_check_error}")
                    except Exception:
                        pass

                    try:
                        # Method 2: Check the visible input value
                        try:
                            # Re-find primary_input fresh to avoid stale element
                            fresh_primary_input = d.find_element(By.ID, "kCWorkerIDPrim_elem")
                            
                            # Use JavaScript to get value (most reliable)
                            try:
                                vis_val = d.execute_script("return arguments[0].value;", fresh_primary_input) or ""
                            except Exception:
                                try:
                                    vis_val = fresh_primary_input.get_attribute("value") or ""
                                except Exception:
                                    vis_val = ""
                            
                            if vis_val.strip():
                                # Check if the value contains the counselor's name
                                last_name = counselor_name.strip().split()[-1].lower()
                                first_name = counselor_name.strip().split()[0].lower() if len(counselor_name.strip().split()) > 1 else ""
                                vis_val_lower = vis_val.strip().lower()
                                
                                # Check if last name or first name appears in visible value
                                if (last_name and last_name in vis_val_lower) or (first_name and first_name in vis_val_lower):
                                    selection_verified = True
                                    self.log(f"[SERVICE-FILE-WIZARD] ✅ VERIFIED: Visible input contains '{vis_val}' (attempt {verification_attempts})")
                                    break
                                elif verification_attempts == 1:
                                    self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Visible input value: '{vis_val}' (doesn't match, attempt {verification_attempts})")
                        except Exception as vis_check_error:
                            if verification_attempts == 1:
                                self.log(f"[SERVICE-FILE-WIZARD][DEBUG] Error checking visible input: {vis_check_error}")
                    except Exception:
                        pass

                    time.sleep(0.15)  # Check every 150ms
            except Exception as e:
                self.log(f"[SERVICE-FILE-WIZARD][WARN] Error during selection verification: {e}")

            # CRITICAL: Only proceed if verification succeeded
            if not selection_verified:
                self.log("[SERVICE-FILE-WIZARD][ERROR] ❌ Selection verification FAILED - field was not populated")
                self.log("[SERVICE-FILE-WIZARD][ERROR] Cannot proceed to Finish button - selection did not register")
                return False
            else:
                self.log("[SERVICE-FILE-WIZARD] ✅ Selection verified successfully - proceeding to Finish button")

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
                            time.sleep(2)  # Wait for finish to process
                            return True
                        except Exception:
                            try:
                                d.execute_script("arguments[0].scrollIntoView({block:'center'});", finish_btn)
                            except Exception:
                                pass
                            try:
                                d.execute_script("arguments[0].click();", finish_btn)
                                self.log("[SERVICE-FILE-WIZARD] Clicked Finish button via JS.")
                                time.sleep(2)  # Wait for finish to process
                                return True
                            except Exception as e_click:
                                self.log(f"[SERVICE-FILE-WIZARD][WARN] Clicking Finish candidate failed: {e_click}")
                                # try next selector
                except Exception as e_sel:
                    self.log(f"[SERVICE-FILE-WIZARD] Selector check error: {e_sel}")
                    continue

            # Another fallback: scan all iframes/frames for a Finish button (sometimes the finish lives inside editLayer iframe)
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
                                    time.sleep(2)  # Wait for finish to process
                                    return True
                                except Exception:
                                    try:
                                        d.execute_script("arguments[0].click();", fb)
                                        self.log(f"[SERVICE-FILE-WIZARD] Clicked Finish via JS inside iframe index {i}.")
                                        d.switch_to.default_content()
                                        time.sleep(2)  # Wait for finish to process
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
                                    time.sleep(2)  # Wait for finish to process
                                    return True
                                except Exception:
                                    try:
                                        d.execute_script("arguments[0].click();", cand)
                                        self.log(f"[SERVICE-FILE-WIZARD] Clicked Finish-like button via JS inside iframe index {i}.")
                                        d.switch_to.default_content()
                                        time.sleep(2)  # Wait for finish to process
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

    def click_toolbar_search_with_wait(self, timeout: int = 20) -> bool:
        '''Click the toolbar Search button (#navSearch) that lives in frame_1 (frm_content_id)'''
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception:
            return False

        d = self.driver
        try:
            d.switch_to.default_content()
            fr = WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.ID, "frm_content_id")))
            d.switch_to.frame(fr)

            try:
                WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

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

            btn = WebDriverWait(d, timeout).until(EC.element_to_be_clickable((By.ID, "navSearch")))
            try:
                btn.click()
            except Exception:
                d.execute_script("arguments[0].click();", btn)

            d.switch_to.default_content()
            return True
        except Exception:
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

    def click_search_button_to_return_to_search(self, timeout: int = 10) -> bool:
        """Click the search button at the top of the screen to return to the search page."""
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
            d.switch_to.default_content()
            fr = WebDriverWait(d, timeout).until(EC.presence_of_element_located((By.ID, "frm_content_id")))
            d.switch_to.frame(fr)

            try:
                WebDriverWait(d, timeout).until(lambda drv: drv.execute_script("return document.readyState") == "complete")
            except Exception:
                pass

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

            btn = WebDriverWait(d, timeout).until(EC.element_to_be_clickable((By.ID, "navSearch")))
            try:
                btn.click()
                self.log("[SEARCH-RETURN] Search button clicked with Selenium.")
            except Exception:
                d.execute_script("arguments[0].click();", btn)
                self.log("[SEARCH-RETURN] Search button clicked with JavaScript fallback.")

            d.switch_to.default_content()
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

    def click_client_list_tab(self, timeout: int = 15) -> bool:
        """
        Click the "Client List" tab button near the top left of the Service File page.
        The tab has id="tabUserDef_li" and calls goTab('tabUserDef').
        """
        if not self.driver:
            self.log("[CLIENT-LIST-TAB] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception as e:
            self.log(f"[CLIENT-LIST-TAB][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))

            self.log("[CLIENT-LIST-TAB] Looking for Client List tab...")
            
            # Find the Client List tab by id
            client_list_tab = None
            try:
                client_list_tab = wait.until(EC.presence_of_element_located((By.ID, "tabUserDef_li")))
                self.log("[CLIENT-LIST-TAB] Found Client List tab")
            except Exception:
                # Fallback: try finding by text
                try:
                    client_list_tab = d.find_element(By.XPATH, "//li[contains(text(), 'Client List')]")
                    self.log("[CLIENT-LIST-TAB] Found Client List tab by text")
                except Exception:
                    self.log("[CLIENT-LIST-TAB][ERROR] Client List tab not found")
                    return False

            # Scroll into view
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", client_list_tab)
            except Exception:
                pass

            # Click the tab
            try:
                d.execute_script("arguments[0].click();", client_list_tab)
                self.log("[CLIENT-LIST-TAB] Client List tab clicked (JavaScript)")
            except Exception as e:
                try:
                    client_list_tab.click()
                    self.log("[CLIENT-LIST-TAB] Client List tab clicked (Selenium)")
                except Exception as click_error:
                    self.log(f"[CLIENT-LIST-TAB][ERROR] Click failed: {click_error}")
                    return False

            # Wait for the tab content to load (check if tabUserDef content appears)
            import time
            time.sleep(2)  # Give it time to load
            
            # Verify the tab is now active (has tabLong_Current class)
            try:
                WebDriverWait(d, 5).until(
                    lambda drv: "tabLong_Current" in (drv.find_element(By.ID, "tabUserDef_li").get_attribute("class") or "")
                )
                self.log("[CLIENT-LIST-TAB] ✓ Client List tab is now active")
            except Exception:
                self.log("[CLIENT-LIST-TAB][WARN] Could not verify tab is active, but continuing...")

            self.log("[CLIENT-LIST-TAB] ✓ Client List tab clicked successfully")
            return True

        except Exception as e:
            self.log(f"[CLIENT-LIST-TAB][ERROR] Failed to click Client List tab: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def click_edit_button(self, timeout: int = 15) -> bool:
        """
        Click the "Edit" button in the top right of the screen.
        The button has id="navEdit" and calls goOpenEdit().
        Only call this AFTER clicking the Client List tab.
        """
        if not self.driver:
            self.log("[EDIT-BUTTON] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception as e:
            self.log(f"[EDIT-BUTTON][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            d.switch_to.default_content()
            WebDriverWait(d, timeout).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))

            self.log("[EDIT-BUTTON] Looking for Edit button...")
            
            # Find the Edit button by id
            edit_button = None
            try:
                edit_button = wait.until(EC.presence_of_element_located((By.ID, "navEdit")))
                self.log("[EDIT-BUTTON] Found Edit button")
            except Exception:
                # Fallback: try finding by text
                try:
                    edit_button = d.find_element(By.XPATH, "//li[@id='navEdit' or contains(text(), 'edit')]")
                    self.log("[EDIT-BUTTON] Found Edit button by text")
                except Exception:
                    self.log("[EDIT-BUTTON][ERROR] Edit button not found")
                    return False

            # Check if button is disabled
            try:
                if "disabled" in (edit_button.get_attribute("class") or "").lower():
                    self.log("[EDIT-BUTTON][ERROR] Edit button is disabled")
                    return False
            except Exception:
                pass

            # Scroll into view
            try:
                d.execute_script("arguments[0].scrollIntoView({block:'center'});", edit_button)
            except Exception:
                pass

            # Click the button
            try:
                d.execute_script("arguments[0].click();", edit_button)
                self.log("[EDIT-BUTTON] Edit button clicked (JavaScript)")
            except Exception as e:
                try:
                    edit_button.click()
                    self.log("[EDIT-BUTTON] Edit button clicked (Selenium)")
                except Exception as click_error:
                    self.log(f"[EDIT-BUTTON][ERROR] Click failed: {click_error}")
                    return False

            # Wait for the edit popup to appear (editLayer should become visible)
            import time
            time.sleep(2)  # Give it time to appear
            
            # Verify the edit popup appeared
            try:
                # Check if editLayer is visible
                edit_layer = wait.until(
                    lambda drv: drv.find_element(By.ID, "editLayer").is_displayed()
                )
                self.log("[EDIT-BUTTON] ✓ Edit popup appeared successfully")
            except Exception:
                # Try checking in default content
                try:
                    d.switch_to.default_content()
                    edit_layer = wait.until(
                        lambda drv: drv.find_element(By.ID, "editLayer").is_displayed()
                    )
                    self.log("[EDIT-BUTTON] ✓ Edit popup appeared successfully (checked in default content)")
                except Exception as e:
                    self.log(f"[EDIT-BUTTON][WARN] Could not verify edit popup appeared: {e}")
                    # Continue anyway - the popup might be there

            self.log("[EDIT-BUTTON] ✓ Edit button clicked successfully")
            return True

        except Exception as e:
            self.log(f"[EDIT-BUTTON][ERROR] Failed to click Edit button: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def _switch_to_edit_form_iframe(self, timeout: int = 25) -> bool:
        """
        Helper method to switch to the dynamicIframe inside the edit popup.
        The editLayer is inside frm_content_id frame, and dynamicIframe is inside editLayer.
        Structure: default_content -> frm_content_id -> editLayer -> dynamicIframe
        
        Uses a similar approach to enter_note_and_save which successfully switches to dynamicIframe.
        
        Returns:
            True if successfully switched to iframe, False otherwise
        """
        if not self.driver:
            self.log("[EDIT-FORM] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception as e:
            self.log(f"[EDIT-FORM][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)
        
        try:
            # Step 1: Switch to default content first
            d.switch_to.default_content()
            
            # Step 2: Switch to frm_content_id frame (where editLayer is located)
            self.log("[EDIT-FORM] Switching to frm_content_id frame...")
            try:
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                self.log("[EDIT-FORM] ✓ Switched to frm_content_id frame")
            except Exception as e:
                self.log(f"[EDIT-FORM][ERROR] Could not switch to frm_content_id frame: {e}")
                # Try alternative approach - switch by name
                try:
                    d.switch_to.default_content()
                    d.switch_to.frame("frm_content")
                    self.log("[EDIT-FORM] ✓ Switched to frm_content frame (by name)")
                except Exception as e2:
                    self.log(f"[EDIT-FORM][ERROR] Could not switch to frm_content frame either: {e2}")
                    return False
            
            # Step 3: Wait for the editLayer to be visible and displayed
            self.log("[EDIT-FORM] Waiting for edit popup (editLayer) to be visible...")
            edit_layer = None
            try:
                # Wait for editLayer to exist
                edit_layer = wait.until(EC.presence_of_element_located((By.ID, "editLayer")))
                self.log("[EDIT-FORM] editLayer element found")
                
                # Wait for it to be displayed (not just present)
                wait.until(lambda drv: drv.find_element(By.ID, "editLayer").is_displayed())
                self.log("[EDIT-FORM] ✓ Edit popup (editLayer) is visible")
            except Exception as e:
                self.log(f"[EDIT-FORM][ERROR] Edit popup (editLayer) not found or not visible: {e}")
                # Try to get more details about what's on the page
                try:
                    all_elements = d.find_elements(By.XPATH, "//*[@id='editLayer' or contains(@class, 'edit')]")
                    self.log(f"[EDIT-FORM][DEBUG] Found {len(all_elements)} elements with 'edit' in id/class")
                except Exception:
                    pass
                return False
            
            # Step 4: Wait for dynamicIframe to load inside editLayer
            # The iframe might take time to load its content
            self.log("[EDIT-FORM] Waiting for dynamicIframe to load...")
            time.sleep(2)  # Give iframe time to load its content
            
            # Step 5: Find and switch to the dynamicIframe inside editLayer
            self.log("[EDIT-FORM] Looking for dynamicIframe inside editLayer...")
            iframe_switched = False
            
            # Approach 1: Use frame_to_be_available_and_switch_to_it (most reliable)
            try:
                d.switch_to.default_content()
                d.switch_to.frame("frm_content_id")
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                self.log("[EDIT-FORM] ✓ Switched to dynamicIframe (approach 1 - frame_to_be_available)")
                iframe_switched = True
            except Exception as e:
                self.log(f"[EDIT-FORM][DEBUG] Approach 1 failed: {e}")
            
            # Approach 2: Find iframe element inside editLayer and switch
            if not iframe_switched:
                try:
                    d.switch_to.default_content()
                    d.switch_to.frame("frm_content_id")
                    edit_layer = d.find_element(By.ID, "editLayer")
                    iframe = edit_layer.find_element(By.ID, "dynamicIframe")
                    d.switch_to.frame(iframe)
                    self.log("[EDIT-FORM] ✓ Switched to dynamicIframe (approach 2 - found inside editLayer)")
                    iframe_switched = True
                except Exception as e:
                    self.log(f"[EDIT-FORM][DEBUG] Approach 2 failed: {e}")
            
            # Approach 3: Find any iframe inside editLayer (by tag name)
            if not iframe_switched:
                try:
                    d.switch_to.default_content()
                    d.switch_to.frame("frm_content_id")
                    edit_layer = d.find_element(By.ID, "editLayer")
                    iframes = edit_layer.find_elements(By.TAG_NAME, "iframe")
                    if iframes:
                        d.switch_to.frame(iframes[0])
                        self.log(f"[EDIT-FORM] ✓ Switched to dynamicIframe (approach 3 - found {len(iframes)} iframe(s))")
                        iframe_switched = True
                except Exception as e:
                    self.log(f"[EDIT-FORM][DEBUG] Approach 3 failed: {e}")
            
            # Approach 4: Try finding dynamicIframe directly from frm_content_id
            if not iframe_switched:
                try:
                    d.switch_to.default_content()
                    d.switch_to.frame("frm_content_id")
                    iframe = wait.until(EC.presence_of_element_located((By.ID, "dynamicIframe")))
                    d.switch_to.frame(iframe)
                    self.log("[EDIT-FORM] ✓ Switched to dynamicIframe (approach 4 - found directly)")
                    iframe_switched = True
                except Exception as e:
                    self.log(f"[EDIT-FORM][DEBUG] Approach 4 failed: {e}")
            
            # Approach 5: Try switching by name
            if not iframe_switched:
                try:
                    d.switch_to.default_content()
                    d.switch_to.frame("frm_content_id")
                    d.switch_to.frame("dynamicIframe")
                    self.log("[EDIT-FORM] ✓ Switched to dynamicIframe (approach 5 - by name)")
                    iframe_switched = True
                except Exception as e:
                    self.log(f"[EDIT-FORM][DEBUG] Approach 5 failed: {e}")
            
            if not iframe_switched:
                self.log("[EDIT-FORM][ERROR] All approaches failed to switch to dynamicIframe")
                # Debug: list all iframes found
                try:
                    d.switch_to.default_content()
                    d.switch_to.frame("frm_content_id")
                    all_iframes = d.find_elements(By.TAG_NAME, "iframe")
                    self.log(f"[EDIT-FORM][DEBUG] Found {len(all_iframes)} iframe(s) in frm_content_id")
                    for i, ifr in enumerate(all_iframes):
                        try:
                            ifr_id = ifr.get_attribute("id") or "no-id"
                            ifr_name = ifr.get_attribute("name") or "no-name"
                            self.log(f"[EDIT-FORM][DEBUG] Iframe {i}: id='{ifr_id}', name='{ifr_name}'")
                        except Exception:
                            pass
                except Exception:
                    pass
                return False
            
            # Verify we're in the correct iframe by checking for form fields
            time.sleep(0.5)  # Give iframe content time to load
            try:
                # Try to find the form or first input field to verify we're in the right place
                form_field = d.find_element(By.NAME, "FLD_ctprogprovexp_progprovexp1")
                self.log("[EDIT-FORM] ✓ Verified: Found form field in dynamicIframe")
                return True
            except Exception:
                self.log("[EDIT-FORM][WARN] Could not verify form field, but continuing...")
                return True  # Still return True - the field might not be loaded yet
                
        except Exception as e:
            self.log(f"[EDIT-FORM][ERROR] Unexpected error in _switch_to_edit_form_iframe: {e}")
            import traceback
            self.log(f"[EDIT-FORM][ERROR] Traceback: {traceback.format_exc()}")
            return False
        finally:
            # Note: We stay in the dynamicIframe - don't switch back to default here
            # The calling method will handle switching back if needed
            pass

    def fill_edit_form_via_keyboard_navigation(self, new_or_reassign_value: str, service_code_value: str, timeout: int = 25) -> bool:
        """
        Fill all edit form fields using keyboard navigation (Tab, Enter, Arrow keys).
        This is a fallback method when iframe switching fails.
        
        After clicking Edit button, the focus is already on the Intake Note field.
        Flow:
        1. Fill Intake Note field (if "New" -> "IA Required", else leave blank)
        2. Press Tab -> moves to Billing Note field
        3. Fill Billing Note field with service code
        4. Press Tab -> moves to New or Reassignment dropdown
        5. Press Enter -> opens dropdown
        6. Press Down arrow (2x for "New Case", 3x for "Reassignment")
        7. Press Enter -> confirms selection
        
        Args:
            new_or_reassign_value: The value from Excel column I ("New or Reassign?")
            service_code_value: The value from Excel column M ("Service Code")
            timeout: Timeout for operations
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[EDIT-FORM-KB] No driver."); return False
        
        try:
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver import ActionChains
            import re
            import time
        except Exception as e:
            self.log(f"[EDIT-FORM-KB][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        actions = ActionChains(d)

        try:
            self.log("[EDIT-FORM-KB] Starting keyboard navigation method...")
            
            # Step 1: Fill Intake Note field
            # After clicking Edit, focus is already on Intake Note field
            new_or_reassign_lower = str(new_or_reassign_value or "").strip().lower()
            is_new = "new" in new_or_reassign_lower and "reassign" not in new_or_reassign_lower
            
            if is_new:
                # Fill "IA Required"
                self.log("[EDIT-FORM-KB] Filling Intake Note with 'IA Required'...")
                try:
                    # Clear any existing text first (select all and delete)
                    # Use key_down/key_up for more reliable modifier key handling
                    actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
                    time.sleep(0.2)
                    actions.send_keys(Keys.DELETE).perform()
                    time.sleep(0.2)
                    # Type "IA Required"
                    actions.send_keys("IA Required").perform()
                    time.sleep(0.3)
                    self.log("[EDIT-FORM-KB] ✓ Filled Intake Note with 'IA Required'")
                except Exception as e:
                    self.log(f"[EDIT-FORM-KB][ERROR] Failed to fill Intake Note: {e}")
                    return False
            else:
                # Leave blank (Reassignment or similar)
                self.log("[EDIT-FORM-KB] Leaving Intake Note blank (Reassignment)...")
                try:
                    # Clear any existing text
                    actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
                    time.sleep(0.2)
                    actions.send_keys(Keys.DELETE).perform()
                    time.sleep(0.3)
                    self.log("[EDIT-FORM-KB] ✓ Cleared Intake Note field")
                except Exception as e:
                    self.log(f"[EDIT-FORM-KB][WARN] Could not clear Intake Note field: {e}")
                    # Continue anyway
            
            # Step 2: Press Tab to move to Billing Note field
            self.log("[EDIT-FORM-KB] Pressing Tab to move to Billing Note field...")
            try:
                actions.send_keys(Keys.TAB).perform()
                time.sleep(0.5)  # Wait for focus to move
                self.log("[EDIT-FORM-KB] ✓ Tab pressed, moved to Billing Note field")
            except Exception as e:
                self.log(f"[EDIT-FORM-KB][ERROR] Failed to press Tab: {e}")
                return False
            
            # Step 3: Fill Billing Note field with service code
            # Extract the numeric service code from the Excel value
            service_code_str = str(service_code_value or "").strip()
            match = re.search(r'\d+', service_code_str)
            if match:
                service_code = match.group(0)
                self.log(f"[EDIT-FORM-KB] Extracted service code '{service_code}' from Excel value '{service_code_value}'")
            else:
                service_code = service_code_str
                self.log(f"[EDIT-FORM-KB][WARN] No numeric code found in '{service_code_value}', using as-is")
            
            if service_code:
                self.log(f"[EDIT-FORM-KB] Filling Billing Note with '{service_code}'...")
                try:
                    # Clear any existing text first
                    actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
                    time.sleep(0.2)
                    actions.send_keys(Keys.DELETE).perform()
                    time.sleep(0.2)
                    # Type service code
                    actions.send_keys(service_code).perform()
                    time.sleep(0.3)
                    self.log(f"[EDIT-FORM-KB] ✓ Filled Billing Note with '{service_code}'")
                except Exception as e:
                    self.log(f"[EDIT-FORM-KB][ERROR] Failed to fill Billing Note: {e}")
                    return False
            else:
                self.log("[EDIT-FORM-KB][WARN] Service code is empty, leaving Billing Note blank")
            
            # Step 4: Press Tab to move to New or Reassignment dropdown
            self.log("[EDIT-FORM-KB] Pressing Tab to move to New or Reassignment dropdown...")
            try:
                actions.send_keys(Keys.TAB).perform()
                time.sleep(0.5)  # Wait for focus to move
                self.log("[EDIT-FORM-KB] ✓ Tab pressed, moved to New or Reassignment dropdown")
            except Exception as e:
                self.log(f"[EDIT-FORM-KB][ERROR] Failed to press Tab: {e}")
                return False
            
            # Step 5: Press Enter to open dropdown
            self.log("[EDIT-FORM-KB] Pressing Enter to open dropdown...")
            try:
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(0.5)  # Wait for dropdown to open
                self.log("[EDIT-FORM-KB] ✓ Enter pressed, dropdown opened")
            except Exception as e:
                self.log(f"[EDIT-FORM-KB][ERROR] Failed to press Enter: {e}")
                return False
            
            # Step 6: Press Down arrow to select option
            # "New Case" = 2 down arrows, "Reassignment" = 3 down arrows
            if is_new:
                # Select "New Case" (2 down arrows)
                self.log("[EDIT-FORM-KB] Pressing Down arrow 2 times for 'New Case'...")
                try:
                    actions.send_keys(Keys.ARROW_DOWN).perform()
                    time.sleep(0.2)
                    actions.send_keys(Keys.ARROW_DOWN).perform()
                    time.sleep(0.3)
                    self.log("[EDIT-FORM-KB] ✓ Selected 'New Case'")
                except Exception as e:
                    self.log(f"[EDIT-FORM-KB][ERROR] Failed to press Down arrows: {e}")
                    return False
            else:
                # Select "Reassignment" (3 down arrows)
                self.log("[EDIT-FORM-KB] Pressing Down arrow 3 times for 'Reassignment'...")
                try:
                    actions.send_keys(Keys.ARROW_DOWN).perform()
                    time.sleep(0.2)
                    actions.send_keys(Keys.ARROW_DOWN).perform()
                    time.sleep(0.2)
                    actions.send_keys(Keys.ARROW_DOWN).perform()
                    time.sleep(0.3)
                    self.log("[EDIT-FORM-KB] ✓ Selected 'Reassignment'")
                except Exception as e:
                    self.log(f"[EDIT-FORM-KB][ERROR] Failed to press Down arrows: {e}")
                    return False
            
            # Step 7: Press Enter to confirm selection
            self.log("[EDIT-FORM-KB] Pressing Enter to confirm selection...")
            try:
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(0.3)
                self.log("[EDIT-FORM-KB] ✓ Enter pressed, selection confirmed")
            except Exception as e:
                self.log(f"[EDIT-FORM-KB][ERROR] Failed to press Enter: {e}")
                return False
            
            self.log("[EDIT-FORM-KB] ✓ Keyboard navigation completed successfully!")
            return True

        except Exception as e:
            self.log(f"[EDIT-FORM-KB][ERROR] Unexpected error in keyboard navigation: {e}")
            import traceback
            self.log(f"[EDIT-FORM-KB][ERROR] Traceback: {traceback.format_exc()}")
            return False

    def fill_edit_form_intake_note(self, new_or_reassign_value: str, timeout: int = 25) -> bool:
        """
        Fill the Intake Note field in the edit popup form.
        Logic:
        - If Excel column I ("New or Reassign?") contains "New" → input "IA Required"
        - If Excel column I contains "Reassignment"/"reassigned" or similar → leave blank
        
        Tries iframe approach first, then falls back to keyboard navigation.
        
        Args:
            new_or_reassign_value: The value from Excel column I ("New or Reassign?")
            timeout: Timeout for element location
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[EDIT-FORM] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except Exception as e:
            self.log(f"[EDIT-FORM][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Switch to the dynamicIframe where the form is located
            self.log("[EDIT-FORM] Switching to dynamicIframe...")
            if not self._switch_to_edit_form_iframe(timeout=timeout):
                self.log("[EDIT-FORM][ERROR] Could not switch to dynamicIframe")
                return False

            # Find the Intake Note field
            self.log("[EDIT-FORM] Looking for Intake Note field...")
            intake_note_field = None
            try:
                intake_note_field = wait.until(EC.presence_of_element_located((By.NAME, "FLD_ctprogprovexp_progprovexp1")))
                self.log("[EDIT-FORM] Found Intake Note field")
            except Exception:
                self.log("[EDIT-FORM][ERROR] Intake Note field not found")
                return False

            # Determine what to fill based on Excel column I value
            new_or_reassign_lower = str(new_or_reassign_value or "").strip().lower()
            
            # Check if it's "New" (case-insensitive)
            is_new = "new" in new_or_reassign_lower and "reassign" not in new_or_reassign_lower
            
            if is_new:
                # Fill "IA Required"
                try:
                    intake_note_field.clear()
                    intake_note_field.send_keys("IA Required")
                    self.log(f"[EDIT-FORM] ✓ Filled Intake Note with 'IA Required' (Excel value: '{new_or_reassign_value}')")
                except Exception as e:
                    self.log(f"[EDIT-FORM][ERROR] Failed to fill Intake Note: {e}")
                    return False
            else:
                # Leave blank (Reassignment or similar)
                try:
                    intake_note_field.clear()
                    self.log(f"[EDIT-FORM] ✓ Left Intake Note blank (Excel value: '{new_or_reassign_value}' - Reassignment)")
                except Exception as e:
                    self.log(f"[EDIT-FORM][WARN] Could not clear Intake Note field: {e}")
                    # Continue anyway - field might already be empty

            return True

        except Exception as e:
            self.log(f"[EDIT-FORM][ERROR] Unexpected error: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def fill_edit_form_billing_note(self, service_code_value: str, timeout: int = 25) -> bool:
        """
        Fill the Billing Note field in the edit popup form with the service code.
        Extracts the numeric service code from the Excel value (e.g., "90837" from "90837 service code").
        
        Args:
            service_code_value: The value from Excel column M ("Service Code")
            timeout: Timeout for element location
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[EDIT-FORM] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import re
        except Exception as e:
            self.log(f"[EDIT-FORM][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Switch to the dynamicIframe where the form is located
            self.log("[EDIT-FORM] Switching to dynamicIframe for Billing Note...")
            if not self._switch_to_edit_form_iframe(timeout=timeout):
                self.log("[EDIT-FORM][ERROR] Could not switch to dynamicIframe")
                return False

            # Find the Billing Note field
            self.log("[EDIT-FORM] Looking for Billing Note field...")
            billing_note_field = None
            try:
                billing_note_field = wait.until(EC.presence_of_element_located((By.NAME, "FLD_ctprogprovexp_progprovexp2")))
                self.log("[EDIT-FORM] Found Billing Note field")
            except Exception:
                self.log("[EDIT-FORM][ERROR] Billing Note field not found")
                return False

            # Extract the numeric service code from the Excel value
            # Examples: "90837 service code" -> "90837", "90837" -> "90837", "90834" -> "90834"
            service_code_str = str(service_code_value or "").strip()
            
            # Extract the first sequence of digits (the service code)
            match = re.search(r'\d+', service_code_str)
            if match:
                service_code = match.group(0)
                self.log(f"[EDIT-FORM] Extracted service code '{service_code}' from Excel value '{service_code_value}'")
            else:
                # If no digits found, use the original value (might be empty or non-numeric)
                service_code = service_code_str
                self.log(f"[EDIT-FORM][WARN] No numeric code found in '{service_code_value}', using as-is")

            # Fill the Billing Note field
            try:
                billing_note_field.clear()
                if service_code:
                    billing_note_field.send_keys(service_code)
                    self.log(f"[EDIT-FORM] ✓ Filled Billing Note with '{service_code}'")
                else:
                    self.log(f"[EDIT-FORM][WARN] Service code is empty, leaving Billing Note blank")
            except Exception as e:
                self.log(f"[EDIT-FORM][ERROR] Failed to fill Billing Note: {e}")
                return False

            return True

        except Exception as e:
            self.log(f"[EDIT-FORM][ERROR] Unexpected error filling Billing Note: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def click_edit_form_save_button(self, timeout: int = 15) -> bool:
        """
        Click the Save/Finish button in the edit popup after filling all fields.
        The button has id="iframeEditSaveButton" and is located in the frm_content_id frame
        (not in the dynamicIframe where the form fields are).
        
        Args:
            timeout: Timeout for element location
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[EDIT-FORM-SAVE] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception as e:
            self.log(f"[EDIT-FORM-SAVE][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Switch back to frm_content_id frame (where the save button is located)
            # We're currently in dynamicIframe, so we need to go back
            self.log("[EDIT-FORM-SAVE] Switching to frm_content_id frame to find Save button...")
            try:
                d.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                self.log("[EDIT-FORM-SAVE] ✓ Switched to frm_content_id frame")
            except Exception as e:
                self.log(f"[EDIT-FORM-SAVE][ERROR] Could not switch to frm_content_id frame: {e}")
                return False

            # Find and click the Save button
            self.log("[EDIT-FORM-SAVE] Looking for Save button (iframeEditSaveButton)...")
            save_button = None
            try:
                save_button = wait.until(EC.element_to_be_clickable((By.ID, "iframeEditSaveButton")))
                self.log("[EDIT-FORM-SAVE] Found Save button")
            except Exception:
                # Try alternative selectors
                try:
                    save_button = d.find_element(By.CSS_SELECTOR, "#iframeEditSaveButton, #iframeEditSaveButton a")
                    self.log("[EDIT-FORM-SAVE] Found Save button via CSS selector")
                except Exception:
                    self.log("[EDIT-FORM-SAVE][ERROR] Save button not found")
                    return False

            # Click the Save button
            try:
                d.execute_script("arguments[0].click();", save_button)
                self.log("[EDIT-FORM-SAVE] ✓ Save button clicked successfully (JavaScript)")
                time.sleep(2)  # Wait for save to process and popup to close
                
                # Verify the popup closed (editLayer should no longer be visible)
                try:
                    edit_layer = d.find_element(By.ID, "editLayer")
                    if not edit_layer.is_displayed():
                        self.log("[EDIT-FORM-SAVE] ✓ Edit popup closed successfully")
                    else:
                        self.log("[EDIT-FORM-SAVE][WARN] Edit popup may still be visible")
                except Exception:
                    # editLayer not found means popup closed - that's good
                    self.log("[EDIT-FORM-SAVE] ✓ Edit popup closed (editLayer not found)")
                
                return True
            except Exception as e:
                self.log(f"[EDIT-FORM-SAVE][ERROR] Failed to click Save button: {e}")
                # Try regular click as fallback
                try:
                    save_button.click()
                    self.log("[EDIT-FORM-SAVE] ✓ Save button clicked successfully (Selenium)")
                    time.sleep(2)
                    return True
                except Exception as click_error:
                    self.log(f"[EDIT-FORM-SAVE][ERROR] Regular click also failed: {click_error}")
                    return False

        except Exception as e:
            self.log(f"[EDIT-FORM-SAVE][ERROR] Unexpected error: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def click_client_case_link(self, client_last_name: str = None, timeout: int = 15) -> bool:
        """
        Click the "[Client last name] Case" link in the breadcrumb trail.
        This link appears after clicking the Edit button and saving the form.
        The link is in the breadcrumb trail (breadCrumbTrail div) and contains "Case" in its text.
        
        Args:
            client_last_name: Optional client last name for logging/verification
            timeout: Timeout for element location
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[CASE-LINK] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception as e:
            self.log(f"[CASE-LINK][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Switch to frm_content_id frame where the breadcrumb trail is located
            self.log("[CASE-LINK] Switching to frm_content_id frame to find Case link...")
            try:
                d.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                self.log("[CASE-LINK] ✓ Switched to frm_content_id frame")
            except Exception as e:
                self.log(f"[CASE-LINK][ERROR] Could not switch to frm_content_id frame: {e}")
                return False

            # Find the breadcrumb trail link that contains "Case" in its text
            self.log("[CASE-LINK] Looking for Case link in breadcrumb trail...")
            case_link = None
            
            # Strategy 1: Find by XPath - link in breadcrumbTrail div that contains "Case"
            try:
                case_link = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//div[contains(@class, 'breadCrumbTrail')]//a[contains(text(), 'Case')]")
                ))
                self.log("[CASE-LINK] ✓ Found Case link using XPath")
            except Exception:
                # Strategy 2: Find by CSS selector
                try:
                    case_link = wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "div.breadCrumbTrail a[href*='acm_caseFileControl']")
                    ))
                    self.log("[CASE-LINK] ✓ Found Case link using CSS selector")
                except Exception:
                    # Strategy 3: Find all links in breadcrumb trail and filter
                    try:
                        breadcrumb_div = d.find_element(By.CSS_SELECTOR, "div.breadCrumbTrail")
                        links = breadcrumb_div.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            link_text = link.text.strip()
                            if "Case" in link_text:
                                case_link = link
                                self.log(f"[CASE-LINK] ✓ Found Case link with text: '{link_text}'")
                                break
                        if not case_link:
                            self.log("[CASE-LINK][ERROR] No link containing 'Case' found in breadcrumb trail")
                            return False
                    except Exception as e:
                        self.log(f"[CASE-LINK][ERROR] Could not find breadcrumb trail: {e}")
                        return False

            if case_link:
                link_text = case_link.text.strip()
                link_href = case_link.get_attribute("href") or ""
                self.log(f"[CASE-LINK] Found Case link: '{link_text}' (href: {link_href[:80]}...)")
                
                # Click using JavaScript for reliability
                try:
                    d.execute_script("arguments[0].click();", case_link)
                    self.log("[CASE-LINK] ✓ Case link clicked successfully (JavaScript)")
                    time.sleep(2)  # Wait for page to start loading
                    
                    # Wait for navigation to complete (check if URL changed or new content loaded)
                    try:
                        # Wait a bit for the new page to load
                        time.sleep(3)
                        self.log("[CASE-LINK] ✓ Case page navigation initiated")
                        return True
                    except Exception as e:
                        self.log(f"[CASE-LINK][WARN] Navigation wait failed (may still be successful): {e}")
                        return True  # Return True anyway as the click succeeded
                except Exception as js_error:
                    self.log(f"[CASE-LINK][WARN] JavaScript click failed, trying regular click: {js_error}")
                    # Fallback to regular click
                    try:
                        case_link.click()
                        self.log("[CASE-LINK] ✓ Case link clicked successfully (Selenium)")
                        time.sleep(3)
                        return True
                    except Exception as click_error:
                        self.log(f"[CASE-LINK][ERROR] Regular click also failed: {click_error}")
                        return False
            else:
                self.log("[CASE-LINK][ERROR] Case link not found")
                return False

        except Exception as e:
            self.log(f"[CASE-LINK][ERROR] Unexpected error: {e}")
            import traceback
            self.log(f"[CASE-LINK][ERROR] Traceback: {traceback.format_exc()}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def select_referral_form_from_documents(self, timeout: int = 15) -> bool:
        """
        Navigate to the Documents section (top right of Case page), click the "Select Document" 
        dropdown, and select "Referral Form" from the dropdown options.
        After selection, a new popup will appear.
        
        Args:
            timeout: Timeout for element location
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[DOCUMENTS] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import Select
            import time
        except Exception as e:
            self.log(f"[DOCUMENTS][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Switch to frm_content_id frame where the Documents section should be located
            self.log("[DOCUMENTS] Switching to frm_content_id frame to find Documents section...")
            try:
                d.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                self.log("[DOCUMENTS] ✓ Switched to frm_content_id frame")
            except Exception as e:
                self.log(f"[DOCUMENTS][ERROR] Could not switch to frm_content_id frame: {e}")
                return False

            # Find the Documents section in the sidebar
            # The Documents section is in sideBarContainer > cDocSB1
            # First, make sure the Documents section is expanded (click on Documents header if needed)
            self.log("[DOCUMENTS] Looking for Documents section in sidebar...")
            
            # Check if Documents section is expanded (cDocSB1 should be visible)
            # If not, click on the Documents h2 header to expand it
            try:
                docs_section = d.find_element(By.ID, "cDocSB1")
                # Check if the section is visible/expanded
                is_visible = docs_section.is_displayed()
                if not is_visible:
                    self.log("[DOCUMENTS] Documents section is collapsed, expanding it...")
                    # Find the Documents header (h2) and click it
                    docs_header = d.find_element(By.XPATH, "//h2[contains(text(), 'Documents')]")
                    docs_header.click()
                    time.sleep(1)  # Wait for section to expand
                else:
                    self.log("[DOCUMENTS] ✓ Documents section is already expanded")
            except Exception as e:
                self.log(f"[DOCUMENTS][WARN] Could not check/expand Documents section: {e}")
                # Continue anyway - it might already be expanded
            
            # The dropdown is inside form cDocSB1_actionForm
            # Strategy 1: Find the select dropdown by locating it within the form
            # The form has name="cDocSB1_actionForm" and contains a select dropdown
            select_dropdown = None
            
            try:
                # Find the form first
                form = wait.until(EC.presence_of_element_located((By.NAME, "cDocSB1_actionForm")))
                self.log("[DOCUMENTS] ✓ Found Documents form")
                
                # Find the select dropdown inside the form
                select_dropdown = form.find_element(By.TAG_NAME, "select")
                self.log("[DOCUMENTS] ✓ Found Select Document dropdown")
            except Exception as e:
                self.log(f"[DOCUMENTS][WARN] Could not find form by name, trying alternative approach: {e}")
                # Strategy 2: Find select by XPath within Documents section
                try:
                    select_dropdown = wait.until(EC.presence_of_element_located(
                        (By.XPATH, "//form[@name='cDocSB1_actionForm']//select")
                    ))
                    self.log("[DOCUMENTS] ✓ Found Select Document dropdown using XPath")
                except Exception:
                    # Strategy 3: Find select within cDocSB1 div
                    try:
                        docs_section = d.find_element(By.ID, "cDocSB1")
                        select_dropdown = docs_section.find_element(By.TAG_NAME, "select")
                        self.log("[DOCUMENTS] ✓ Found Select Document dropdown within cDocSB1")
                    except Exception as e3:
                        self.log(f"[DOCUMENTS][ERROR] Could not find select dropdown: {e3}")
                        return False
            
            if not select_dropdown:
                self.log("[DOCUMENTS][ERROR] Select dropdown not found")
                return False
            
            # Make sure "Add New Document" radio button is checked (it should be by default)
            # Radio button has id="cDocSB1_actionRad_add" and should be checked
            try:
                radio_add = d.find_element(By.ID, "cDocSB1_actionRad_add")
                if not radio_add.is_selected():
                    self.log("[DOCUMENTS] 'Add New Document' radio button not checked, checking it...")
                    radio_add.click()
                    time.sleep(0.5)
                else:
                    self.log("[DOCUMENTS] ✓ 'Add New Document' radio button is already checked")
            except Exception as e:
                self.log(f"[DOCUMENTS][WARN] Could not verify/check 'Add New Document' radio button: {e}")
                # Continue anyway - it might be checked by default
            
            # Create Select object and select "Referral Form" (value="211")
            self.log("[DOCUMENTS] Selecting 'Referral Form' from dropdown...")
            selection_successful = False
            
            try:
                select_obj = Select(select_dropdown)
                
                # Try to select by value first (value="211")
                try:
                    select_obj.select_by_value("211")
                    self.log("[DOCUMENTS] ✓ Selected 'Referral Form' by value (211)")
                    selection_successful = True
                except Exception:
                    # Fallback: try selecting by visible text
                    try:
                        select_obj.select_by_visible_text("Referral Form")
                        self.log("[DOCUMENTS] ✓ Selected 'Referral Form' by text")
                        selection_successful = True
                    except Exception as e2:
                        self.log(f"[DOCUMENTS][WARN] Selenium Select failed: {e2}")
                        # List available options for debugging
                        try:
                            options = select_obj.options
                            option_texts = [opt.text for opt in options]
                            self.log(f"[DOCUMENTS][DEBUG] Available options: {option_texts}")
                        except Exception:
                            pass
                        
                        # Fallback: Try JavaScript-based selection
                        self.log("[DOCUMENTS] Trying JavaScript-based selection...")
                        try:
                            # Find the option with value="211" or text containing "Referral Form"
                            d.execute_script("""
                                var select = arguments[0];
                                for (var i = 0; i < select.options.length; i++) {
                                    if (select.options[i].value === '211' || select.options[i].text.includes('Referral Form')) {
                                        select.selectedIndex = i;
                                        select.dispatchEvent(new Event('change', { bubbles: true }));
                                        break;
                                    }
                                }
                            """, select_dropdown)
                            self.log("[DOCUMENTS] ✓ Selected 'Referral Form' using JavaScript")
                            selection_successful = True
                        except Exception as js_error:
                            self.log(f"[DOCUMENTS][WARN] JavaScript selection also failed: {js_error}")
                            # Continue anyway - we'll check if popup appeared
                
                # Manually trigger the change event to ensure the onchange handler fires
                # Sometimes Selenium's select doesn't trigger JavaScript events properly
                if selection_successful:
                    try:
                        d.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", select_dropdown)
                        self.log("[DOCUMENTS] ✓ Triggered change event manually")
                    except Exception as e:
                        self.log(f"[DOCUMENTS][WARN] Could not trigger change event manually: {e}")
                        # Continue anyway - the selection might have already triggered it
                
                # The onchange event should trigger automatically and open the popup
                # Wait a bit for the popup to appear
                time.sleep(3)
                
                # CRITICAL: Check if popup appeared - if it did, return True regardless of selection verification
                # This handles the case where selection worked but verification failed
                self.log("[DOCUMENTS] Checking if popup appeared...")
                try:
                    d.switch_to.default_content()
                    
                    # Wait for frm_content_id frame to be available (popup container)
                    try:
                        wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                        self.log("[DOCUMENTS] ✓ frm_content_id frame available")
                        
                        # Wait for dynamicIframe to be available (form content)
                        try:
                            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                            self.log("[DOCUMENTS] ✓ dynamicIframe available - popup appeared!")
                            
                            # Verify form is loaded by checking for form fields
                            try:
                                wait.until(EC.presence_of_element_located((By.NAME, "kBookItemID2")))
                                self.log("[DOCUMENTS] ✓ Form fields detected - popup loaded successfully!")
                                
                                # Switch back to default content for caller
                                d.switch_to.default_content()
                                return True
                            except Exception:
                                self.log("[DOCUMENTS][WARN] dynamicIframe found but form fields not yet loaded")
                                d.switch_to.default_content()
                                return True  # Return True anyway - popup is loading
                        except Exception:
                            self.log("[DOCUMENTS][WARN] dynamicIframe not yet available, but popup may be loading")
                            d.switch_to.default_content()
                            # Wait a bit more and try once more
                            time.sleep(2)
                            try:
                                d.switch_to.default_content()
                                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                                self.log("[DOCUMENTS] ✓ Popup appeared after additional wait!")
                                d.switch_to.default_content()
                                return True
                            except Exception:
                                d.switch_to.default_content()
                                return True  # Return True anyway - popup may be loading
                    except Exception:
                        self.log("[DOCUMENTS][WARN] frm_content_id frame not yet available, but popup may be loading")
                        d.switch_to.default_content()
                        # Wait a bit more and try once more
                        time.sleep(2)
                        try:
                            d.switch_to.default_content()
                            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                            self.log("[DOCUMENTS] ✓ Popup appeared after additional wait!")
                            d.switch_to.default_content()
                            return True
                        except Exception:
                            d.switch_to.default_content()
                            return True  # Return True anyway - popup may be loading
                except Exception as e:
                    self.log(f"[DOCUMENTS][WARN] Could not verify popup appearance: {e}")
                    d.switch_to.default_content()
                    # Even if we can't verify, if selection was attempted, the popup may still appear
                    # Return True to let caller proceed - they can check if popup exists
                    return True
                    
            except Exception as e:
                self.log(f"[DOCUMENTS][ERROR] Failed to select 'Referral Form': {e}")
                import traceback
                self.log(f"[DOCUMENTS][ERROR] Traceback: {traceback.format_exc()}")
                return False

        except Exception as e:
            self.log(f"[DOCUMENTS][ERROR] Unexpected error: {e}")
            import traceback
            self.log(f"[DOCUMENTS][ERROR] Traceback: {traceback.format_exc()}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def fill_referral_form_popup(self, client_first_name: str = None, client_last_name: str = None, timeout: int = 20) -> bool:
        """
        Fill the Referral Form popup fields after selecting "Referral Form" from Documents dropdown.
        - Document Date: Leave as-is (today's date is already populated)
        - For Case Member: Select the client's name from dropdown (NOT "Other Individual")
        - Document Description: Enter "Referral Form"
        
        After filling, the bot will pause for review (Finish button will NOT be clicked yet).
        
        Args:
            client_first_name: Client's first name from Excel (for matching dropdown option)
            client_last_name: Client's last name from Excel (for matching dropdown option)
            timeout: Timeout for element location
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[REFERRAL-FORM] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import Select
            import time
        except Exception as e:
            self.log(f"[REFERRAL-FORM][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # OPTIMIZED: Go directly to frm_content_id -> dynamicIframe (this is the fastest path)
            # The popup is loaded via iframeLoadWizard, which creates dynamicIframe inside frm_content_id
            self.log("[REFERRAL-FORM] Switching to popup iframe (frm_content_id -> dynamicIframe)...")
            
            try:
                d.switch_to.default_content()
                
                # Wait for frm_content_id, then switch to dynamicIframe inside it
                # Use shorter timeout (5 seconds) since popup should already be visible
                wait_short = WebDriverWait(d, 5)
                wait_short.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                self.log("[REFERRAL-FORM] ✓ Switched to frm_content_id")
                
                # Now switch to dynamicIframe from within frm_content_id
                wait_short.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                self.log("[REFERRAL-FORM] ✓ Switched to dynamicIframe")
                
                # Wait briefly for form to load
                time.sleep(1)
            except Exception as e:
                self.log(f"[REFERRAL-FORM][ERROR] Could not switch to popup iframe: {e}")
                return False

            # Step 1: Document Date - Leave as-is (already populated with today's date)
            self.log("[REFERRAL-FORM] Document Date field - leaving as-is (today's date)")

            # Step 2: Fill "For Case Member" dropdown
            # The dropdown has name="kBookItemID2" and contains options like "Doe, Ben" and "Other Individual"
            # We should select the client's name (NOT "Other Individual")
            self.log("[REFERRAL-FORM] Filling 'For Case Member' dropdown...")
            
            case_member_dropdown = None
            try:
                # Find the dropdown
                case_member_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "kBookItemID2")))
                self.log("[REFERRAL-FORM] ✓ Found 'For Case Member' dropdown")
            except Exception as e:
                self.log(f"[REFERRAL-FORM][ERROR] Could not find 'For Case Member' dropdown: {e}")
                return False

            if case_member_dropdown:
                # Create Select object
                select_obj = Select(case_member_dropdown)
                
                # Get all options to find the client's name
                options = select_obj.options
                self.log(f"[REFERRAL-FORM][DEBUG] Found {len(options)} options in dropdown")
                
                # Filter out "Other Individual" option (value="")
                # We want to select the client's name (should have a value like "66154")
                client_option = None
                client_option_text = None
                
                # Build client name patterns for matching
                # Client name could be in format "Last, First" or "First Last" in the dropdown
                if client_first_name and client_last_name:
                    # Try various name formats
                    name_patterns = [
                        f"{client_last_name}, {client_first_name}",  # "Doe, Ben"
                        f"{client_last_name}, {client_first_name} ",  # "Doe, Ben " (with trailing space)
                        f"{client_first_name} {client_last_name}",  # "Ben Doe"
                        client_last_name,  # Just last name
                        client_first_name,  # Just first name
                    ]
                    
                    self.log(f"[REFERRAL-FORM] Looking for client: '{client_first_name} {client_last_name}'")
                    self.log(f"[REFERRAL-FORM] Trying name patterns: {name_patterns}")
                    
                    # Find matching option (exclude "Other Individual" and "-Select-")
                    for opt in options:
                        opt_value = opt.get_attribute("value") or ""
                        opt_text = opt.text.strip()
                        
                        # Skip "-Select-" and "Other Individual" (both have empty value)
                        if opt_value == "":
                            self.log(f"[REFERRAL-FORM][DEBUG] Skipping option: '{opt_text}' (empty value)")
                            continue
                        
                        # Check if option text matches any of our name patterns
                        for pattern in name_patterns:
                            if pattern.lower() in opt_text.lower():
                                client_option = opt
                                client_option_text = opt_text
                                self.log(f"[REFERRAL-FORM] ✓ Found matching option: '{opt_text}' (value: {opt_value})")
                                break
                        
                        if client_option:
                            break
                else:
                    # If we don't have client names, select the first non-empty option (not "-Select-" or "Other Individual")
                    for opt in options:
                        opt_value = opt.get_attribute("value") or ""
                        opt_text = opt.text.strip()
                        
                        if opt_value != "" and opt_text.lower() != "other individual":
                            client_option = opt
                            client_option_text = opt_text
                            self.log(f"[REFERRAL-FORM] ✓ Selected first available option: '{opt_text}' (value: {opt_value})")
                            break
                
                if client_option:
                    # Select the client option
                    # NOTE: The dropdown's onblur triggers bodyBookItemOnChange() which does location.replace()
                    # This causes a full page reload, so we need to wait for it and re-switch to iframe
                    try:
                        select_obj.select_by_value(client_option.get_attribute("value"))
                        self.log(f"[REFERRAL-FORM] ✓ Selected '{client_option_text}' in 'For Case Member' dropdown")
                    except Exception as e:
                        self.log(f"[REFERRAL-FORM][WARN] Could not select by value, trying by visible text: {e}")
                        try:
                            select_obj.select_by_visible_text(client_option_text)
                            self.log(f"[REFERRAL-FORM] ✓ Selected '{client_option_text}' by visible text")
                        except Exception as e2:
                            self.log(f"[REFERRAL-FORM][ERROR] Could not select client option: {e2}")
                            return False
                    
                    # CRITICAL: After dropdown selection, bodyBookItemOnChange() triggers location.replace()
                    # This causes a full page reload. We must wait for the reload to complete, then re-switch to iframe
                    self.log("[REFERRAL-FORM] Waiting for page reload after dropdown selection...")
                    time.sleep(3)  # Wait for location.replace() to complete
                    
                    # Re-switch to iframe context after page reload
                    try:
                        d.switch_to.default_content()
                        wait_short = WebDriverWait(d, 10)
                        wait_short.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                        self.log("[REFERRAL-FORM] ✓ Re-switched to frm_content_id after reload")
                        wait_short.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "dynamicIframe")))
                        self.log("[REFERRAL-FORM] ✓ Re-switched to dynamicIframe after reload")
                        time.sleep(1)  # Brief wait for form to stabilize
                    except Exception as iframe_error:
                        self.log(f"[REFERRAL-FORM][ERROR] Could not re-switch to iframe after reload: {iframe_error}")
                        return False
                else:
                    self.log("[REFERRAL-FORM][ERROR] Could not find client name in dropdown options")
                    # List available options for debugging
                    available_options = [(opt.text.strip(), opt.get_attribute("value") or "") for opt in options]
                    self.log(f"[REFERRAL-FORM][DEBUG] Available options: {available_options}")
                    return False

            # Step 3: Fill "Document Description" field
            # The field has name="cDocDesc" and maxlength="50"
            # IMPORTANT: After dropdown selection, the page was reloaded (location.replace())
            # We've already re-switched to the iframe, so now we just need to find and fill the field
            self.log("[REFERRAL-FORM] Filling 'Document Description' field...")
            
            doc_desc_filled = False
            
            try:
                # Find the Document Description field (we're already in the correct iframe context after reload)
                wait_short = WebDriverWait(d, 10)
                doc_desc_field = wait_short.until(EC.presence_of_element_located((By.NAME, "cDocDesc")))
                self.log("[REFERRAL-FORM] ✓ Found 'Document Description' field")
                
                # Try JavaScript to set the value FIRST (most reliable, doesn't require element interaction)
                # Find element directly in JavaScript to avoid stale element reference issues
                try:
                    result = d.execute_script("""
                        var field = document.querySelector('input[name="cDocDesc"]');
                        if (field) {
                            field.value = 'Referral Form';
                            field.dispatchEvent(new Event('input', { bubbles: true }));
                            field.dispatchEvent(new Event('change', { bubbles: true }));
                            return field.value;
                        }
                        return null;
                    """)
                    if result == "Referral Form":
                        self.log("[REFERRAL-FORM] ✓ Set 'Referral Form' using JavaScript")
                        time.sleep(0.5)
                        
                        # Verify by re-finding the field
                        try:
                            doc_desc_field = d.find_element(By.NAME, "cDocDesc")
                            entered_value = doc_desc_field.get_attribute("value")
                            if entered_value == "Referral Form":
                                self.log("[REFERRAL-FORM] ✓ Verified 'Document Description' field contains 'Referral Form'")
                                doc_desc_filled = True
                            else:
                                self.log(f"[REFERRAL-FORM][WARN] Document Description field value is '{entered_value}' (expected 'Referral Form'), trying keyboard...")
                        except Exception:
                            # If we can't verify but JavaScript returned success, assume it worked
                            self.log("[REFERRAL-FORM][WARN] Could not verify JavaScript fill, but JavaScript reported success")
                            doc_desc_filled = True
                    else:
                        self.log(f"[REFERRAL-FORM][WARN] JavaScript fill returned '{result}' (expected 'Referral Form'), trying keyboard...")
                except Exception as js_error:
                    self.log(f"[REFERRAL-FORM][WARN] JavaScript fill failed: {js_error}, trying keyboard...")
                
                # Fallback: If JavaScript didn't work, try keyboard input directly on the field
                if not doc_desc_filled:
                    try:
                        from selenium.webdriver.common.keys import Keys
                        
                        # Re-find field to avoid stale element
                        doc_desc_field = wait_short.until(EC.element_to_be_clickable((By.NAME, "cDocDesc")))
                        self.log("[REFERRAL-FORM] Re-found 'Document Description' field for keyboard input")
                        
                        # Focus the field using JavaScript (more reliable)
                        try:
                            d.execute_script("arguments[0].focus();", doc_desc_field)
                            time.sleep(0.3)
                        except Exception:
                            try:
                                doc_desc_field.click()
                                time.sleep(0.3)
                            except Exception:
                                pass
                        
                        # Try keyboard input
                        try:
                            # Clear the field using Ctrl+A
                            doc_desc_field.send_keys(Keys.CONTROL + "a")
                            time.sleep(0.2)
                            
                            # Type "Referral Form"
                            doc_desc_field.send_keys("Referral Form")
                            self.log("[REFERRAL-FORM] ✓ Entered 'Referral Form' using keyboard input")
                            time.sleep(0.5)
                            
                            # Re-find field to verify (element may be stale after typing)
                            try:
                                doc_desc_field = d.find_element(By.NAME, "cDocDesc")
                                entered_value = doc_desc_field.get_attribute("value")
                                if entered_value == "Referral Form":
                                    self.log("[REFERRAL-FORM] ✓ Verified 'Document Description' field contains 'Referral Form'")
                                    doc_desc_filled = True
                                else:
                                    self.log(f"[REFERRAL-FORM][WARN] Document Description field value is '{entered_value}' (expected 'Referral Form')")
                            except Exception as verify_error:
                                self.log(f"[REFERRAL-FORM][WARN] Could not verify keyboard input: {verify_error}")
                                # Assume it worked if we got this far without exception
                                doc_desc_filled = True
                        except Exception as send_keys_error:
                            # If send_keys fails, try JavaScript as final fallback
                            self.log(f"[REFERRAL-FORM][WARN] send_keys failed: {send_keys_error}, trying JavaScript fallback...")
                            try:
                                result = d.execute_script("""
                                    var field = document.querySelector('input[name="cDocDesc"]');
                                    if (field) {
                                        field.value = 'Referral Form';
                                        field.dispatchEvent(new Event('input', { bubbles: true }));
                                        field.dispatchEvent(new Event('change', { bubbles: true }));
                                        return field.value;
                                    }
                                    return null;
                                """)
                                if result == "Referral Form":
                                    self.log("[REFERRAL-FORM] ✓ Set 'Referral Form' using JavaScript fallback")
                                    doc_desc_filled = True
                                else:
                                    self.log(f"[REFERRAL-FORM][WARN] JavaScript fallback returned '{result}'")
                            except Exception as js_fallback_error:
                                self.log(f"[REFERRAL-FORM][ERROR] JavaScript fallback also failed: {js_fallback_error}")
                    except Exception as kb_error:
                        self.log(f"[REFERRAL-FORM][ERROR] Keyboard input failed: {kb_error}")
                
            except Exception as e:
                self.log(f"[REFERRAL-FORM][ERROR] Could not find or fill 'Document Description' field: {e}")
                return False
            
            if not doc_desc_filled:
                self.log("[REFERRAL-FORM][ERROR] Failed to fill 'Document Description' field")
                return False

            # All fields filled successfully
            self.log("[REFERRAL-FORM] ✓ All fields filled successfully!")
            self.log("[REFERRAL-FORM] Fields populated:")
            self.log(f"  - Document Date: (left as-is)")
            self.log(f"  - For Case Member: '{client_option_text}'")
            self.log(f"  - Document Description: 'Referral Form'")
            
            # IMPORTANT: Press Tab key once to move focus to the date line
            # This triggers the blur event on Document Description and enables the Finish button
            self.log("[REFERRAL-FORM] Pressing Tab key to move focus to date line and enable Finish button...")
            try:
                from selenium.webdriver.common.keys import Keys
                
                # Re-find the Document Description field to ensure we have a fresh reference
                doc_desc_field = d.find_element(By.NAME, "cDocDesc")
                
                # Press Tab once to move focus to the date line
                doc_desc_field.send_keys(Keys.TAB)
                self.log("[REFERRAL-FORM] ✓ Pressed Tab key - focus moved to date line")
                
                # Wait a moment for the blur event to process and Finish button to become enabled
                time.sleep(1)
                self.log("[REFERRAL-FORM] ✓ Tab key pressed - Finish button should now be enabled")
            except Exception as tab_error:
                self.log(f"[REFERRAL-FORM][WARN] Failed to press Tab key: {tab_error}, but continuing anyway")
            
            return True

        except Exception as e:
            self.log(f"[REFERRAL-FORM][ERROR] Unexpected error: {e}")
            import traceback
            self.log(f"[REFERRAL-FORM][ERROR] Traceback: {traceback.format_exc()}")
            return False
        finally:
            # Don't switch away from iframe - we want to stay in the popup for review
            # The user will manually review and then we can click Finish later
            pass

    def click_finish_button_in_referral_form(self, timeout: int = 15) -> bool:
        """
        Click the "Finish" button in the referral form popup.
        The Finish button is located in the frm_content_id frame with id="wizFinishButton".
        
        After clicking Finish, the popup will close and the bot will be on a new page.
        
        Args:
            timeout: Timeout for element location
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[FINISH-BUTTON] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception as e:
            self.log(f"[FINISH-BUTTON][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            self.log("[FINISH-BUTTON] Clicking Finish button in referral form popup...")
            
            # Switch to frm_content_id frame where the Finish button is located
            try:
                d.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                self.log("[FINISH-BUTTON] ✓ Switched to frm_content_id frame")
            except Exception as e:
                self.log(f"[FINISH-BUTTON][ERROR] Could not switch to frm_content_id: {e}")
                return False
            
            # Find the Finish button (id="wizFinishButton")
            # Wait for it to be clickable (it may be disabled until fields are blurred)
            try:
                finish_button = wait.until(EC.presence_of_element_located((By.ID, "wizFinishButton")))
                self.log("[FINISH-BUTTON] ✓ Found Finish button")
                
                # Wait for the button to become enabled/clickable
                # The button may have a disabled class or attribute that needs to be removed
                # Give it a longer initial wait since the blur event might take time to process
                time.sleep(1)
                max_wait_attempts = 15  # Increased from 10 to 15
                for attempt in range(max_wait_attempts):
                    try:
                        # Re-find the button to get fresh reference
                        finish_button = d.find_element(By.ID, "wizFinishButton")
                        
                        # Check if button is enabled by checking for disabled class/attribute
                        is_disabled = finish_button.get_attribute("disabled") or "disable" in (finish_button.get_attribute("class") or "").lower()
                        if not is_disabled:
                            # Try to click it
                            try:
                                d.execute_script("arguments[0].click();", finish_button)
                                self.log("[FINISH-BUTTON] ✓ Clicked Finish button via JavaScript")
                                break
                            except Exception:
                                try:
                                    finish_button.click()
                                    self.log("[FINISH-BUTTON] ✓ Clicked Finish button via Selenium")
                                    break
                                except Exception as click_err:
                                    if attempt < max_wait_attempts - 1:
                                        self.log(f"[FINISH-BUTTON][DEBUG] Button not clickable yet (attempt {attempt + 1}/{max_wait_attempts}), waiting...")
                                        time.sleep(0.8)  # Increased wait time
                                        continue
                                    else:
                                        raise click_err
                        else:
                            if attempt < max_wait_attempts - 1:
                                self.log(f"[FINISH-BUTTON][DEBUG] Button still disabled (attempt {attempt + 1}/{max_wait_attempts}), waiting...")
                                time.sleep(0.8)  # Increased wait time
                            else:
                                # Force click even if disabled (sometimes JavaScript can bypass disabled state)
                                self.log("[FINISH-BUTTON][WARN] Button appears disabled, attempting force click via JavaScript...")
                                d.execute_script("arguments[0].click();", finish_button)
                                self.log("[FINISH-BUTTON] ✓ Force-clicked Finish button via JavaScript")
                    except Exception as check_err:
                        if attempt < max_wait_attempts - 1:
                            self.log(f"[FINISH-BUTTON][DEBUG] Error checking button state (attempt {attempt + 1}/{max_wait_attempts}): {check_err}, waiting...")
                            time.sleep(0.8)  # Increased wait time
                        else:
                            raise check_err
                
                # Wait for popup to close and page to load
                time.sleep(3)
                self.log("[FINISH-BUTTON] ✓ Finish button clicked - popup should be closed")
                return True
                
            except Exception as e:
                self.log(f"[FINISH-BUTTON][ERROR] Could not find or click Finish button: {e}")
                return False

        except Exception as e:
            self.log(f"[FINISH-BUTTON][ERROR] Unexpected error: {e}")
            import traceback
            self.log(f"[FINISH-BUTTON][ERROR] Traceback: {traceback.format_exc()}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def click_print_button_on_document_page(self, timeout: int = 10) -> bool:
        """
        Click the "Print" button on the document page (after clicking Finish).
        The Print button is typically located in the top right of the screen.
        
        After clicking Print, a new window/tab will open with the document.
        
        Args:
            timeout: Timeout for element location (reduced from 15 to 10 for faster execution)
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[PRINT-BUTTON] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time
        except Exception as e:
            self.log(f"[PRINT-BUTTON][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait_short = WebDriverWait(d, 5)  # Shorter wait for faster execution
        wait = WebDriverWait(d, timeout)

        try:
            self.log("[PRINT-BUTTON] Looking for Print button on document page...")
            
            # Switch to default content first
            try:
                d.switch_to.default_content()
            except Exception:
                pass
            
            # Wait briefly for page to load after Finish button click
            time.sleep(1)  # Reduced from 2 to 1 second
            
            # Store current window handles before clicking Print
            original_windows = d.window_handles
            self.log(f"[PRINT-BUTTON] Current windows before Print click: {len(original_windows)}")
            
            # Try multiple strategies to find the Print button (with shorter timeouts)
            print_button = None
            
            # Strategy 1: Try JavaScript click directly in frm_content_id frame (fastest - no element finding needed)
            js_click_succeeded = False
            try:
                # Try to click Print button directly via JavaScript (bypasses element finding)
                clicked = d.execute_script("""
                    try {
                        var frame = document.getElementById('frm_content_id');
                        if (frame && frame.contentDocument) {
                            var doc = frame.contentDocument;
                            // Look for button or link with "print" text (case-insensitive)
                            var buttons = doc.querySelectorAll('button, a');
                            for (var i = 0; i < buttons.length; i++) {
                                var text = (buttons[i].textContent || buttons[i].innerText || '').toLowerCase();
                                if (text.includes('print')) {
                                    buttons[i].click();
                                    return true;
                                }
                            }
                        }
                    } catch(e) {}
                    return false;
                """)
                if clicked:
                    js_click_succeeded = True
                    self.log("[PRINT-BUTTON] ✓ Clicked Print button via JavaScript (direct click in frame)")
                    # Wait for new window to open
                    self.log("[PRINT-BUTTON] Waiting for new window/tab to open...")
                    max_wait = 15
                    new_window_opened = False
                    for i in range(max_wait):
                        time.sleep(0.5)
                        current_windows = d.window_handles
                        if len(current_windows) > len(original_windows):
                            new_window_opened = True
                            self.log(f"[PRINT-BUTTON] ✓ New window/tab opened! Total windows: {len(current_windows)} (was {len(original_windows)})")
                            break
                        if i % 2 == 0:
                            self.log(f"[PRINT-BUTTON][DEBUG] Still waiting for new window... (attempt {i+1}/{max_wait})")
                    
                    if new_window_opened:
                        self.log("[PRINT-BUTTON] ✓ Print button clicked - new window opened")
                        return True
                    else:
                        self.log("[PRINT-BUTTON][WARN] Print button clicked but no new window detected")
                        return True  # Still return True as click succeeded
            except Exception as js_err:
                self.log(f"[PRINT-BUTTON][DEBUG] JavaScript direct click failed: {js_err}, trying Selenium approach...")
            
            # Strategy 2: Look in frm_content_id frame using Selenium (if JavaScript didn't work)
            if not js_click_succeeded:
                try:
                    wait_short.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id")))
                    try:
                        print_button = wait_short.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'print')] | //a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'print')]")))
                        self.log("[PRINT-BUTTON] ✓ Found Print button in frm_content_id frame")
                    except Exception:
                        d.switch_to.default_content()
                except Exception:
                    d.switch_to.default_content()
            
            # Strategy 3: Look for button with text "Print" (case-insensitive) in default content
            if not print_button:
                try:
                    print_button = wait_short.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'print')]")))
                    self.log("[PRINT-BUTTON] ✓ Found Print button via text")
                except Exception:
                    pass
            
            # Strategy 4: Look for link with text "Print"
            if not print_button:
                try:
                    print_button = wait_short.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'print')]")))
                    self.log("[PRINT-BUTTON] ✓ Found Print link via text")
                except Exception:
                    pass
            
            # Strategy 5: Look for element with id containing "print"
            if not print_button:
                try:
                    print_button = wait_short.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'print')]")))
                    self.log("[PRINT-BUTTON] ✓ Found Print element via id")
                except Exception:
                    pass
            
            if print_button:
                # Click using JavaScript for reliability
                try:
                    d.execute_script("arguments[0].click();", print_button)
                    self.log("[PRINT-BUTTON] ✓ Clicked Print button via JavaScript")
                except Exception:
                    try:
                        print_button.click()
                        self.log("[PRINT-BUTTON] ✓ Clicked Print button via Selenium")
                    except Exception as click_err:
                        self.log(f"[PRINT-BUTTON][WARN] Selenium click failed: {click_err}, trying JavaScript fallback...")
                        # Final fallback: JavaScript click in frame
                        d.execute_script("""
                            var frame = document.getElementById('frm_content_id');
                            if (frame && frame.contentDocument) {
                                var doc = frame.contentDocument;
                                var buttons = doc.querySelectorAll('button, a');
                                for (var i = 0; i < buttons.length; i++) {
                                    var text = (buttons[i].textContent || buttons[i].innerText || '').toLowerCase();
                                    if (text.includes('print')) {
                                        buttons[i].click();
                                    }
                                }
                            }
                        """)
                        self.log("[PRINT-BUTTON] ✓ Clicked Print button via JavaScript fallback")
                
                # Wait for new window/tab to open (the document window)
                self.log("[PRINT-BUTTON] Waiting for new window/tab to open...")
                max_wait = 15  # Increased wait time for new window
                new_window_opened = False
                for i in range(max_wait):
                    time.sleep(0.5)
                    current_windows = d.window_handles
                    if len(current_windows) > len(original_windows):
                        new_window_opened = True
                        self.log(f"[PRINT-BUTTON] ✓ New window/tab opened! Total windows: {len(current_windows)} (was {len(original_windows)})")
                        break
                    if i % 2 == 0:  # Log every second
                        self.log(f"[PRINT-BUTTON][DEBUG] Still waiting for new window... (attempt {i+1}/{max_wait})")
                
                if new_window_opened:
                    self.log("[PRINT-BUTTON] ✓ Print button clicked - new window opened")
                    return True
                else:
                    self.log("[PRINT-BUTTON][WARN] Print button clicked but no new window detected after {max_wait} attempts")
                    # Still return True as the click succeeded - the window might have opened in same tab
                    return True
            else:
                self.log("[PRINT-BUTTON][ERROR] Could not find Print button using any strategy")
                return False

        except Exception as e:
            self.log(f"[PRINT-BUTTON][ERROR] Unexpected error: {e}")
            import traceback
            self.log(f"[PRINT-BUTTON][ERROR] Traceback: {traceback.format_exc()}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

    def save_pdf_from_print_preview(self, client_first_name: str, client_last_name: str, pdf_output_folder: str, is_ips: bool = False, timeout: int = 30) -> bool:
        """
        Save the PDF from the new window/tab that opened after clicking Print.
        The new window contains the document at a URL like:
        https://integrityseniorservices.athena-us.com/acm_reportControl?actionType=rpt&kReportID=60&...
        
        Uses Chrome DevTools Protocol to print to PDF with the specified filename.
        
        The PDF will be saved as: "Reassignment [Client's Full Name] - no IA.pdf"
        Example: "Reassignment John Smith - no IA.pdf"
        If is_ips=True, the filename will be: "IPS Reassignment [Client's Full Name] - no IA.pdf"
        Example: "IPS Reassignment John Smith - no IA.pdf"
        
        Args:
            client_first_name: Client's first name
            client_last_name: Client's last name
            pdf_output_folder: Path to the folder where PDF should be saved
            is_ips: If True, prefix filename with "IPS "
            timeout: Timeout for operations
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[PDF-SAVE] No driver."); return False
        
        try:
            import time
            from pathlib import Path
        except Exception as e:
            self.log(f"[PDF-SAVE][ERROR] Import error: {e}"); return False

        d = self.driver

        try:
            self.log("[PDF-SAVE] Saving PDF from new document window...")
            
            # Construct the filename: "Reassignment [Client's Full Name] - no IA.pdf"
            # If is_ips=True, prefix with "IPS ": "IPS Reassignment [Client's Full Name] - no IA.pdf"
            client_full_name = f"{client_first_name} {client_last_name}".strip()
            prefix = "IPS " if is_ips else ""
            pdf_filename = f"{prefix}Reassignment {client_full_name} - no IA.pdf"
            
            if is_ips:
                self.log(f"[PDF-SAVE] Counselor is IPS - adding 'IPS' prefix to filename")
            
            # Ensure the output folder exists
            pdf_output_path = Path(pdf_output_folder)
            if not pdf_output_path.exists():
                try:
                    pdf_output_path.mkdir(parents=True, exist_ok=True)
                    self.log(f"[PDF-SAVE] Created PDF output folder: {pdf_output_folder}")
                except Exception as e:
                    self.log(f"[PDF-SAVE][ERROR] Could not create PDF output folder: {e}")
                    return False
            
            full_pdf_path = pdf_output_path / pdf_filename
            
            self.log(f"[PDF-SAVE] Saving PDF as: {pdf_filename}")
            self.log(f"[PDF-SAVE] Full path: {full_pdf_path}")
            
            # CRITICAL: Switch to the new window/tab that opened after clicking Print
            # The new window contains the document, not the Penelope page
            self.log("[PDF-SAVE] Checking for new document window...")
            current_windows = d.window_handles
            original_window = d.current_window_handle
            
            self.log(f"[PDF-SAVE][DEBUG] Current window handles: {len(current_windows)} windows open")
            self.log(f"[PDF-SAVE][DEBUG] Current window URL: {d.current_url}")
            
            if len(current_windows) > 1:
                # Find the new window (not the original one)
                new_windows = [w for w in current_windows if w != original_window]
                if new_windows:
                    # Switch to the last new window (the most recently opened one)
                    new_window = new_windows[-1]
                    d.switch_to.window(new_window)
                    self.log(f"[PDF-SAVE] ✓ Switched to new window. URL: {d.current_url}")
                    
                    # Wait for the document to load in the new window
                    time.sleep(2)
                    
                    # Verify we're on the correct page (should contain acm_reportControl)
                    if "acm_reportControl" in d.current_url and "actionType=rpt" in d.current_url:
                        self.log("[PDF-SAVE] ✓ Confirmed: On document report page")
                    else:
                        self.log(f"[PDF-SAVE][WARN] Unexpected URL in new window: {d.current_url}")
                        # Try to find the correct window by URL
                        for win in new_windows:
                            d.switch_to.window(win)
                            if "acm_reportControl" in d.current_url and "actionType=rpt" in d.current_url:
                                self.log(f"[PDF-SAVE] ✓ Found correct window by URL: {d.current_url}")
                                break
                else:
                    self.log("[PDF-SAVE][ERROR] Multiple windows found but couldn't identify new window")
            else:
                # Only one window - check if we're already on the document page
                if "acm_reportControl" in d.current_url and "actionType=rpt" in d.current_url:
                    self.log("[PDF-SAVE] ✓ Already on document report page (opened in same tab)")
                else:
                    self.log(f"[PDF-SAVE][ERROR] Only one window found and it's not the document page! URL: {d.current_url}")
                    self.log("[PDF-SAVE][ERROR] Cannot save PDF - wrong window!")
                    return False
            
            # Use Chrome DevTools Protocol to print to PDF
            # This is more reliable than handling the print dialog
            try:
                # Execute Chrome DevTools Protocol command to print to PDF
                # Note: This requires Chrome DevTools Protocol access
                self.log("[PDF-SAVE] Using Chrome DevTools Protocol to generate PDF...")
                result = d.execute_cdp_cmd("Page.printToPDF", {
                    "printBackground": True,
                    "displayHeaderFooter": False,
                    "preferCSSPageSize": True
                })
                
                # Save the PDF
                import base64
                pdf_data = base64.b64decode(result['data'])
                
                with open(full_pdf_path, 'wb') as f:
                    f.write(pdf_data)
                
                self.log(f"[PDF-SAVE] ✓ PDF saved successfully: {full_pdf_path}")
                
                # Close the new window and switch back to the original window
                if len(current_windows) > 1:
                    try:
                        d.close()  # Close the document window
                        d.switch_to.window(original_window)  # Switch back to original window
                        self.log("[PDF-SAVE] ✓ Closed document window and switched back to original window")
                    except Exception as close_err:
                        self.log(f"[PDF-SAVE][WARN] Could not close document window: {close_err}")
                
                return True
                
            except Exception as cdp_error:
                self.log(f"[PDF-SAVE][ERROR] Chrome DevTools Protocol failed: {cdp_error}")
                import traceback
                self.log(f"[PDF-SAVE][ERROR] Traceback: {traceback.format_exc()}")
                return False

        except Exception as e:
            self.log(f"[PDF-SAVE][ERROR] Unexpected error: {e}")
            import traceback
            self.log(f"[PDF-SAVE][ERROR] Traceback: {traceback.format_exc()}")
            return False

    def fill_edit_form_new_or_reassignment(self, new_or_reassign_value: str, timeout: int = 25) -> bool:
        """
        Select the appropriate option in the "New or Reassignment" dropdown.
        Logic:
        - If Excel column I ("New or Reassign?") contains "New" → select "New Case" (value="2")
        - If Excel column I contains "Reassignment"/"reassigned" or similar → select "Reassignment" (value="3")
        
        Args:
            new_or_reassign_value: The value from Excel column I ("New or Reassign?")
            timeout: Timeout for element location
        
        Returns:
            True if successful, False otherwise
        """
        if not self.driver:
            self.log("[EDIT-FORM] No driver."); return False
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import Select
        except Exception as e:
            self.log(f"[EDIT-FORM][ERROR] Selenium libs: {e}"); return False

        d = self.driver
        wait = WebDriverWait(d, timeout)

        try:
            # Switch to the dynamicIframe where the form is located
            self.log("[EDIT-FORM] Switching to dynamicIframe for New or Reassignment dropdown...")
            if not self._switch_to_edit_form_iframe(timeout=timeout):
                self.log("[EDIT-FORM][ERROR] Could not switch to dynamicIframe")
                return False

            # Find the New or Reassignment dropdown
            self.log("[EDIT-FORM] Looking for New or Reassignment dropdown...")
            dropdown = None
            try:
                dropdown = wait.until(EC.presence_of_element_located((By.NAME, "FLD_ctprogprovexp_progprovexp3")))
                self.log("[EDIT-FORM] Found New or Reassignment dropdown")
            except Exception:
                self.log("[EDIT-FORM][ERROR] New or Reassignment dropdown not found")
                return False

            # Determine which option to select based on Excel column I value
            new_or_reassign_lower = str(new_or_reassign_value or "").strip().lower()
            
            # Check if it's "New" (case-insensitive, and doesn't contain "reassign")
            is_new = "new" in new_or_reassign_lower and "reassign" not in new_or_reassign_lower
            
            # Create Select object
            select = Select(dropdown)
            
            if is_new:
                # Select "New Case" (value="2")
                try:
                    select.select_by_value("2")
                    self.log(f"[EDIT-FORM] ✓ Selected 'New Case' in dropdown (Excel value: '{new_or_reassign_value}')")
                except Exception as e:
                    # Fallback: try selecting by visible text
                    try:
                        select.select_by_visible_text("New Case")
                        self.log(f"[EDIT-FORM] ✓ Selected 'New Case' by text (Excel value: '{new_or_reassign_value}')")
                    except Exception as fallback_error:
                        self.log(f"[EDIT-FORM][ERROR] Failed to select 'New Case': {e}, fallback: {fallback_error}")
                        return False
            else:
                # Select "Reassignment" (value="3")
                try:
                    select.select_by_value("3")
                    self.log(f"[EDIT-FORM] ✓ Selected 'Reassignment' in dropdown (Excel value: '{new_or_reassign_value}')")
                except Exception as e:
                    # Fallback: try selecting by visible text
                    try:
                        select.select_by_visible_text("Reassignment")
                        self.log(f"[EDIT-FORM] ✓ Selected 'Reassignment' by text (Excel value: '{new_or_reassign_value}')")
                    except Exception as fallback_error:
                        self.log(f"[EDIT-FORM][ERROR] Failed to select 'Reassignment': {e}, fallback: {fallback_error}")
                        return False

            return True

        except Exception as e:
            self.log(f"[EDIT-FORM][ERROR] Unexpected error filling New or Reassignment dropdown: {e}")
            return False
        finally:
            try:
                d.switch_to.default_content()
            except Exception:
                pass

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Existing Client Referral Form Bot - Version 3.1.0, Last Updated 12/04/2025"); self.geometry("1040x820")
        
        # User management
        self.penelope_users_file = Path(__file__).parent / "existing_client_bot_penelope_users.json"
        self.penelope_users = {}
        self.load_penelope_users()
        
        self.therapynotes_users_file = Path(__file__).parent / "existing_client_bot_therapynotes_users.json"
        self.therapynotes_users = {}
        self.load_therapynotes_users()
        
        self._build_ui()
        self._stop = threading.Event()
        self.worker = None
        self.pn = None

    def load_penelope_users(self):
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
        try:
            with open(self.penelope_users_file, 'w') as f:
                json.dump(self.penelope_users, f, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save Penelope users:\n{e}")
            return False
    
    def load_therapynotes_users(self):
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
        style = ttk.Style()
        style.configure('Large.TCheckbutton', font=('Segoe UI', 11, 'bold'))
        
        headerfrm, headerbanner = _title_banner(self)
        
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
        def _wheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _wheel)

        cred = self._card(self.content, "Penelope Credentials")
        self.url_var  = tk.StringVar(value=PN_DEFAULT_URL)
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        
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

        src = self._card(self.content, "Excel Data Source")
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
        self.col_sel = tk.StringVar(value="A")  # Penelope Individual ID# column
        ttk.Label(mp, text="Penelope Individual ID# Column (A):", foreground=MAROON)\
            .grid(row=0, column=0, sticky='e', padx=6, pady=6)
        ttk.Entry(mp, textvariable=self.col_sel, width=8).grid(row=0, column=1, sticky='w', pady=6)

        ctr = self._card(self.content, "Controls")
        ttk.Button(ctr, text="Start", command=self.start).grid(row=0, column=0, padx=6)
        ttk.Button(ctr, text="Stop", command=self.stop).grid(row=0, column=1, padx=6)
        ttk.Button(ctr, text="Copy Log", command=self.copy_log).grid(row=0, column=2, padx=6)
        ttk.Button(ctr, text="Clear Log", command=self.clear_log).grid(row=0, column=3, padx=6)
        
        self.debug_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(ctr, text="Debug Mode (Verbose Logging)", variable=self.debug_mode).grid(row=1, column=0, columnspan=4, sticky='w', padx=6, pady=4)
        
        # TherapyNotes Credentials for Uploaders
        tn_cred = self._card(self.content, "TherapyNotes Credentials (for Uploader)")
        
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
        
        # IPS TherapyNotes Credentials (Optional - for IPS Uploader)
        ttk.Label(tn_cred, text="IPS TN Username:", foreground=MAROON).grid(row=2, column=0, sticky='e', padx=6, pady=4)
        self.tn_ips_user_var = tk.StringVar()
        ttk.Entry(tn_cred, textvariable=self.tn_ips_user_var, width=30).grid(row=2, column=1, sticky='w', padx=6, pady=4)
        ttk.Label(tn_cred, text="IPS TN Password:", foreground=MAROON).grid(row=2, column=2, sticky='e', padx=6, pady=4)
        self.tn_ips_pass_var = tk.StringVar()
        ttk.Entry(tn_cred, textvariable=self.tn_ips_pass_var, show='•', width=30).grid(row=2, column=3, sticky='w', padx=6, pady=4)
        ttk.Label(tn_cred, text="(Optional - leave blank if same as Base)", foreground="gray", font=('Segoe UI', 8)).grid(row=3, column=1, columnspan=3, sticky='w', padx=6, pady=2)
        
        # Uploader Integration Checkboxes
        uploader_integration = ttk.Frame(ctr)
        uploader_integration.grid(row=2, column=0, columnspan=5, sticky='ew', padx=6, pady=8)
        uploader_integration.columnconfigure(0, weight=1)
        
        uploader_style_frame = ttk.Frame(uploader_integration, relief='solid', borderwidth=2)
        uploader_style_frame.pack(fill='x', padx=4, pady=4)
        
        self.run_base_uploader_after = tk.BooleanVar(value=False)
        base_uploader_cb = ttk.Checkbutton(
            uploader_style_frame,
            text="📤 Run Existing Client Referral Form Uploader after bot completes",
            variable=self.run_base_uploader_after,
            style='Large.TCheckbutton',
            command=self._toggle_ips_uploader_checkbox
        )
        base_uploader_cb.pack(fill='x', padx=8, pady=6)
        
        ips_sub_frame = ttk.Frame(uploader_style_frame)
        ips_sub_frame.pack(fill='x', padx=8, pady=(0, 6))
        
        ttk.Label(ips_sub_frame, text="    ", foreground='gray').pack(side='left')
        
        self.run_ips_uploader_after = tk.BooleanVar(value=False)
        self.ips_uploader_cb = ttk.Checkbutton(
            ips_sub_frame,
            text="🏥 Also run IPS Uploader after Base",
            variable=self.run_ips_uploader_after,
            state='disabled',
            command=self._validate_ips_uploader_credentials
        )
        self.ips_uploader_cb.pack(side='left')
        
        self.remove_old_docs_checkbox = tk.BooleanVar(value=False)
        remove_old_docs_cb = ttk.Checkbutton(
            uploader_style_frame,
            text="🗑️ Remove old 'Reassignment' documents (30+ days) when uploading",
            variable=self.remove_old_docs_checkbox,
            style='Large.TCheckbutton'
        )
        remove_old_docs_cb.pack(fill='x', padx=8, pady=(0, 6))
        
        uploader_desc_label = ttk.Label(
            uploader_style_frame,
            text="✓ Uploads referral forms to TherapyNotes. Uses same input Excel and PDF output folder from above.",
            foreground='#0066cc',
            font=('Segoe UI', 9, 'italic')
        )
        uploader_desc_label.pack(fill='x', padx=8, pady=(0, 6))
        
        # Output Settings Section
        output_settings = self._card(self.content, "Output Settings")
        
        # PDF Output Folder
        ttk.Label(output_settings, text="PDF Output Folder:", foreground=MAROON).grid(row=0, column=0, sticky='e', padx=6, pady=6)
        self.pdf_output_folder = tk.StringVar()
        self.pdf_output_folder_e = ttk.Entry(output_settings, textvariable=self.pdf_output_folder, width=70)
        self.pdf_output_folder_e.grid(row=0, column=1, sticky='w', padx=6, pady=6)
        self.pdf_output_folder_b = ttk.Button(output_settings, text="Browse…", command=self._browse_pdf_output_folder)
        self.pdf_output_folder_b.grid(row=0, column=2, sticky='w', padx=6, pady=6)
        
        # Excel Output Folder
        ttk.Label(output_settings, text="Excel Output Folder:", foreground=MAROON).grid(row=1, column=0, sticky='e', padx=6, pady=6)
        self.excel_output_folder = tk.StringVar()
        self.excel_output_folder_e = ttk.Entry(output_settings, textvariable=self.excel_output_folder, width=70)
        self.excel_output_folder_e.grid(row=1, column=1, sticky='w', padx=6, pady=6)
        self.excel_output_folder_b = ttk.Button(output_settings, text="Browse…", command=self._browse_excel_output_folder)
        self.excel_output_folder_b.grid(row=1, column=2, sticky='w', padx=6, pady=6)
        
        logfrm = ttk.Frame(self.content); logfrm.pack(fill='both', expand=True, padx=12, pady=8)
        self.log_widget = scrolledtext.ScrolledText(logfrm, height=20, bg=LOG_BG, fg=LOG_FG)
        self.log_widget.pack(fill='both', expand=True)
        self.logger = UILog(self.log_widget)

    def _toggle_ips_uploader_checkbox(self):
        if self.run_base_uploader_after.get():
            self.ips_uploader_cb.config(state='normal')
            if not self.tn_user_var.get() or not self.tn_pass_var.get():
                self.log("[UPLOADER][WARN] ⚠️  TherapyNotes credentials not provided!")
        else:
            self.ips_uploader_cb.config(state='disabled')
            self.run_ips_uploader_after.set(False)
    
    def _validate_ips_uploader_credentials(self):
        if self.run_ips_uploader_after.get():
            if not self.tn_user_var.get() or not self.tn_pass_var.get():
                self.log("[UPLOADER][ERROR] ❌ Cannot enable IPS Uploader - TherapyNotes credentials missing!")
                self.run_ips_uploader_after.set(False)
                return False
            else:
                self.log("[UPLOADER][INFO] ✓ IPS Uploader enabled - TherapyNotes credentials validated")
                return True
        return True
    
    def _browse_local(self):
        p = filedialog.askopenfilename(title="Select CSV/XLSX", filetypes=[("Spreadsheets","*.csv;*.xlsx;*.xls")])
        if p: self.local_path.set(p)
    
    def _browse_pdf_output_folder(self):
        """Browse for PDF output folder"""
        folder = filedialog.askdirectory(title="Select PDF Output Folder")
        if folder:
            self.pdf_output_folder.set(folder)
            self.log(f"[GUI] PDF output folder selected: {folder}")
    
    def _browse_excel_output_folder(self):
        """Browse for Excel output folder"""
        folder = filedialog.askdirectory(title="Select Excel Output Folder")
        if folder:
            self.excel_output_folder.set(folder)
            self.log(f"[GUI] Excel output folder selected: {folder}")
    
    def _update_penelope_user_dropdown(self):
        if hasattr(self, 'penelope_user_dropdown'):
            user_names = sorted(self.penelope_users.keys())
            if user_names:
                self.penelope_user_dropdown['values'] = user_names
            else:
                self.penelope_user_dropdown['values'] = []
    
    def _on_penelope_user_selected(self, event=None):
        selected_user = self.penelope_user_dropdown.get()
        if selected_user and selected_user in self.penelope_users:
            user_data = self.penelope_users[selected_user]
            self.user_var.set(user_data.get('username', ''))
            self.pass_var.set(user_data.get('password', ''))
            self.url_var.set(user_data.get('url', PN_DEFAULT_URL))
    
    def _add_penelope_user(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add Penelope User - Version 3.1.0, Last Updated 12/04/2025")
        dialog.geometry("450x280")
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
        if hasattr(self, 'therapynotes_user_dropdown'):
            user_names = sorted(self.therapynotes_users.keys())
            if user_names:
                self.therapynotes_user_dropdown['values'] = user_names
            else:
                self.therapynotes_user_dropdown['values'] = []
    
    def _on_therapynotes_user_selected(self, event=None):
        selected_user = self.therapynotes_user_dropdown.get()
        if selected_user and selected_user in self.therapynotes_users:
            user_data = self.therapynotes_users[selected_user]
            self.tn_user_var.set(user_data.get('username', ''))
            self.tn_pass_var.set(user_data.get('password', ''))
    
    def _add_therapynotes_user(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add TherapyNotes User - Version 3.1.0, Last Updated 12/04/2025")
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

    def launch_uploader_bridge(self):
        """Launch the Existing Client Referral Form Uploader"""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            base_dir = os.getcwd()

        exe_path = os.path.join(base_dir, "existing_client_referral_form_uploader.exe")
        py_path  = os.path.join(base_dir, "existing_client_referral_form_uploader.py")

        try:
            if os.name == "nt" and os.path.isfile(exe_path):
                try:
                    os.startfile(exe_path)
                    self.log("[BRIDGE] Launched existing_client_referral_form_uploader.exe")
                    return
                except Exception as e:
                    self.log(f"[BRIDGE][WARN] Could not open .exe: {e}")

            if os.path.isfile(py_path):
                import subprocess
                subprocess.Popen([sys.executable, py_path], cwd=base_dir)
                self.log("[BRIDGE] Launched Existing Client Referral Form Uploader")
                return

            self.log("[BRIDGE][INFO] Uploader not found. Place existing_client_referral_form_uploader.py in the same folder as this bot.")
        except Exception as e:
            self.log(f"[BRIDGE][ERR] Failed to launch uploader: {e}")

    def _run(self):
        try:
            # Build PN client
            auth = PNAuth(self.url_var.get().strip(),
                          self.user_var.get().strip(),
                          self.pass_var.get().strip())

            self.pn = PNClient(auth, log=self.log)
            self.pn.start()

            if not self.pn.login():
                self.log("[ERR] Login unsuccessful; continuing to keep browser open.")
            else:
                self.log("[OK] Logged in.")
                self.pn.click_toolbar_search_with_wait(timeout=25)

            # Load rows
            col_sel = self.col_sel.get().strip()
            self.log(f"[DATA] Individual ID Column: '{_normalize_col_token(col_sel)}'")
            self.log(f"[DATA] Excel file: {os.path.basename(self.local_path.get())}")

            csv_file_path = self.local_path.get().strip()
            
            # Get user-specified row range from GUI
            try:
                user_row_from = int(self.local_row_from.get().strip() or '2')
                user_row_to = int(self.local_row_to.get().strip() or '2')
            except (ValueError, AttributeError):
                self.log(f"[DATA][WARN] Invalid row range input, using defaults: 2-50")
                user_row_from = 2
                user_row_to = 50
            
            # Validate row range
            if user_row_from < 2:
                self.log(f"[DATA][WARN] Row 'from' must be >= 2 (header is row 1), adjusting to 2")
                user_row_from = 2
            if user_row_to < user_row_from:
                self.log(f"[DATA][WARN] Row 'to' ({user_row_to}) is less than 'from' ({user_row_from}), adjusting to {user_row_from}")
                user_row_to = user_row_from
            
            # Check if file exists and get total rows for validation
            try:
                if csv_file_path.lower().endswith('.csv'):
                    df_check = pd.read_csv(csv_file_path)
                else:
                    df_check = pd.read_excel(csv_file_path)
                
                total_data_rows = len(df_check)
                max_row = total_data_rows + 1  # +1 because rows are 1-indexed (row 1 is header)
                
                if user_row_to > max_row:
                    self.log(f"[DATA][WARN] Row 'to' ({user_row_to}) exceeds file size ({max_row}), adjusting to {max_row}")
                    user_row_to = max_row
                
                self.log(f"[DATA] Using user-specified row range: {user_row_from}-{user_row_to} (out of {total_data_rows} data rows)")
                
            except Exception as e:
                self.log(f"[DATA][WARN] Could not read file to validate row range: {e}")
                self.log(f"[DATA] Using user-specified range: {user_row_from}-{user_row_to}")

            rows: List[Dict] = []
            lcl = LocalSlice(
                file_path=csv_file_path,
                row_from=user_row_from,  # Use user's input
                row_to=user_row_to,      # Use user's input
                col_selector=col_sel
            )
            rows = lcl.load(self.log)

            if not rows:
                self.log("[DATA][ERR] No rows parsed. Opening Search UI for inspection.")
                self.pn.go_to_search()
                return

            if self.pn.go_to_search():
                self.log("[NAV] Search page opened.")
            else:
                self.log("[NAV][WARN] Could not open Search page; continuing anyway.")

            # Initialize tracking list for output Excel
            results_tracking = []
            
            # Process rows - Steps 1-9
            for idx, rec in enumerate(rows, start=1):
                if self._stop.is_set(): break
                
                # Initialize tracking for this client
                client_result = {
                    'Row_Number': idx,
                    'Penelope_ID': '',
                    'Client_Name': '',
                    'Note_Found': 'No',
                    'Counselor_Name': '',
                    'IPS_Counselor': 'No',
                    'Referral_Form_Status': 'Not Started',
                    'Status_Notes': '',
                    'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                try:
                    raw_id = rec.get("_Bot_ID") or ""
                    try:
                        indiv_id = str(int(float(raw_id))).strip()
                    except (ValueError, TypeError):
                        indiv_id = str(raw_id).strip()
                        if indiv_id.endswith('.0'):
                            indiv_id = indiv_id[:-2]
                    
                    if not indiv_id:
                        self.log(f"[SKIP] Row {idx}: empty Individual ID in selected column.")
                        client_result['Status_Notes'] = 'Empty Individual ID'
                        client_result['Referral_Form_Status'] = 'Skipped'
                        results_tracking.append(client_result)
                        continue

                    client_result['Penelope_ID'] = indiv_id
                    self.log(f"[RUN] Row {idx}: Processing client with Individual ID = {indiv_id}")
                    
                    # Step 3-6: Navigate to Individual tab, enter ID, press Go
                    # CRITICAL: Make sure we're on the search page first
                    try:
                        from selenium.webdriver.common.by import By
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        self.pn.driver.switch_to.default_content()
                        # Check if we're already on search page by looking for search form
                        try:
                            WebDriverWait(self.pn.driver, 2).until(
                                EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id"))
                            )
                            # Check if search form exists
                            try:
                                self.pn.driver.find_element(By.NAME, "txtKIndID")
                                self.log("[NAV] Already on search page")
                            except Exception:
                                # Not on search page, navigate there
                                self.log("[NAV] Not on search page, navigating to search...")
                                self.pn.go_to_search()
                        except Exception:
                            # Frame not available, navigate to search
                            self.log("[NAV] Frame not available, navigating to search...")
                            self.pn.go_to_search()
                    except Exception as nav_error:
                        self.log(f"[NAV][WARN] Navigation check failed: {nav_error}, continuing anyway...")
                    
                    if not self.pn.enter_individual_id_and_go(indiv_id):
                        self.log("[WARN] Could not enter ID/Go. Continuing.")
                        client_result['Status_Notes'] = 'Could not enter ID/Go'
                        client_result['Referral_Form_Status'] = 'Skipped'
                        results_tracking.append(client_result)
                        # Return to search page for next client
                        self.log("[SEARCH-RETURN] Returning to search page for next client...")
                        self.pn.click_search_button_to_return_to_search()
                        import time
                        time.sleep(1)
                        continue

                    # Step 7: Click the first (or name-matched) result link (only open cases)
                    # Handle various column name variations (with/without spaces, case variations)
                    first_name = str(rec.get("First Name") or rec.get("First") or rec.get("FName") or rec.get("Given") or 
                                    rec.get("first name") or rec.get("first") or "").strip()
                    last_name  = str(rec.get("Last Name")  or rec.get("Last")  or rec.get("LName") or rec.get("Surname") or 
                                    rec.get("last name") or rec.get("last") or "").strip()
                    
                    client_name = f"{first_name} {last_name}".strip()
                    client_result['Client_Name'] = client_name if client_name else 'Unknown'
                    
                    # Log extracted names for debugging
                    if first_name or last_name:
                        self.log(f"[DATA] Extracted client name: First='{first_name}' Last='{last_name}'")
                    else:
                        self.log(f"[DATA][WARN] Could not extract client name from Excel row {idx}")
                    
                    if not self.pn.click_first_result_name(first_name=first_name or None, last_name=last_name or None):
                        self.log("[WARN] Could not click a patient name in results (or no open case found). Continuing.")
                        client_result['Status_Notes'] = 'Could not click patient name (no open case found)'
                        client_result['Referral_Form_Status'] = 'Skipped'
                        results_tracking.append(client_result)
                        # Return to search page for next client
                        self.log("[SEARCH-RETURN] Returning to search page for next client...")
                        self.pn.click_search_button_to_return_to_search()
                        import time
                        time.sleep(1)
                        continue

                    self.log("[OK] Opened client profile.")
                    
                    # CRITICAL: Wait a moment and verify we're actually on the client profile page
                    import time
                    time.sleep(1.5)  # Wait for profile page to fully load
                    
                    # Verify we're on the profile page by checking for common elements
                    try:
                        from selenium.webdriver.common.by import By
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        self.pn.driver.switch_to.default_content()
                        WebDriverWait(self.pn.driver, 5).until(
                            EC.frame_to_be_available_and_switch_to_it((By.ID, "frm_content_id"))
                        )
                        self.pn.driver.switch_to.default_content()
                        self.log("[OK] ✓ Verified: On client profile page")
                    except Exception as e:
                        self.log(f"[WARN] Could not verify profile page, but continuing: {e}")
                    
                    # Step 8: Extract referral meeting note - CHECK THIS FIRST AS REQUESTED
                    self.log("[NOTE-CHECK] Checking for 'Referral Meeting assigned to' note...")
                    counselor_name, is_ips = self.pn.extract_referral_meeting_note()
                    if counselor_name:
                        client_result['Note_Found'] = 'Yes'
                        client_result['Counselor_Name'] = counselor_name
                        client_result['IPS_Counselor'] = 'Yes' if is_ips else 'No'
                        self.log(f"[NOTE-EXTRACT] ✓ Counselor: '{counselor_name}' | IPS: {is_ips}")
                    else:
                        client_result['Note_Found'] = 'No'
                        self.log("[NOTE-EXTRACT][WARN] No counselor note found - proceeding without counselor info")
                    
                    # Step 9: Navigate to Pre-Enrollment and click Waiting for Allocation
                    self.log("[PRE-ENROLL] Starting Pre-Enrollment process...")
                    if self.pn.click_pre_enrollment_tab_and_waiting_allocation():
                        self.log("[SUCCESS] ✓ Pre-Enrollment process completed successfully!")
                        self.log("[SUCCESS] ✓ Successfully clicked 'Waiting for Allocation' green bubble")
                        
                        # Step 10: Click the Assign button
                        self.log("[ASSIGN] Clicking Assign button...")
                        if self.pn.click_assign_button():
                            self.log("[SUCCESS] ✓ Assign button clicked successfully!")
                            
                            # Step 11: Enter note and save
                            # Get counselor name from Excel (Therapist Name column)
                            therapist_name = str(rec.get("Therapist Name") or rec.get("Therapist  Name") or 
                                                rec.get("therapist name") or rec.get("Counselor") or "").strip()
                            
                            if not therapist_name:
                                self.log("[NOTE-ENTER][WARN] No therapist name found in Excel - using placeholder")
                                therapist_name = "Unknown Counselor"
                            
                            # Check if counselor is IPS (has "- IPS", " - IPS", or " IPS" suffix)
                            # Handle multiple formats: "Name - IPS", "Name -IPS", "Name IPS", "Name  IPS"
                            is_ips_counselor = (
                                "- IPS" in therapist_name or 
                                " - IPS" in therapist_name or 
                                therapist_name.upper().endswith(" IPS") or
                                therapist_name.upper().endswith(" -IPS")
                            )
                            
                            # Clean the counselor name (remove IPS suffix in all formats for matching)
                            # Remove in order: " - IPS", "- IPS", " IPS", " -IPS", "-IPS"
                            counselor_name_clean = therapist_name
                            counselor_name_clean = counselor_name_clean.replace(" - IPS", "").replace("- IPS", "")
                            counselor_name_clean = counselor_name_clean.replace(" -IPS", "").replace("-IPS", "")
                            # Handle " IPS" at the end (space + IPS)
                            if counselor_name_clean.upper().endswith(" IPS"):
                                counselor_name_clean = counselor_name_clean[:-4].strip()  # Remove " IPS" (4 chars)
                            counselor_name_clean = counselor_name_clean.strip()
                            
                            self.log(f"[NOTE-ENTER] Counselor name from Excel: '{therapist_name}'")
                            self.log(f"[NOTE-ENTER] Is IPS counselor: {is_ips_counselor}")
                            self.log(f"[NOTE-ENTER] Cleaned counselor name: '{counselor_name_clean}'")
                            self.log("[NOTE-ENTER] Entering note and saving...")
                            
                            if self.pn.enter_note_and_save(counselor_name=counselor_name_clean):
                                self.log("[SUCCESS] ✓ Note entered and saved successfully!")
                                
                                # Step 12: Select primary worker and click Finish
                                self.log("[SERVICE-FILE-WIZARD] Waiting for Service File wizard popup...")
                                import time
                                time.sleep(3)  # Wait for popup to appear after save
                                
                                self.log("[SERVICE-FILE-WIZARD] Selecting primary worker and clicking Finish...")
                                if self.pn.complete_service_file_wizard_select_primary_worker(
                                    counselor_name=counselor_name_clean, 
                                    is_ips=is_ips_counselor, 
                                    timeout=15
                                ):
                                    self.log("[SUCCESS] ✓ Primary worker selected and Finish clicked successfully!")
                                else:
                                    self.log("[ERROR] ❌ Failed to select primary worker - cannot proceed")
                                    client_result['Referral_Form_Status'] = 'Error - Primary Worker Selection Failed'
                                    client_result['Status_Notes'] = f'Failed to select primary worker after all retry attempts. Counselor: {counselor_name_clean}'
                                    results_tracking.append(client_result)
                                    continue  # Skip to next client - cannot proceed without selecting worker
                                
                                # Step 13: Click Client List tab (only if primary worker was selected successfully)
                                self.log("[CLIENT-LIST-TAB] Waiting for page to load after Finish...")
                                import time
                                time.sleep(3)  # Wait for page to load after Finish
                                
                                self.log("[CLIENT-LIST-TAB] Clicking Client List tab...")
                                if self.pn.click_client_list_tab():
                                    self.log("[SUCCESS] ✓ Client List tab clicked successfully!")
                                    
                                    # Step 14: Click Edit button
                                    self.log("[EDIT-BUTTON] Waiting for Client List tab to load...")
                                    time.sleep(2)  # Wait for tab content to load
                                    
                                    self.log("[EDIT-BUTTON] Clicking Edit button...")
                                    if self.pn.click_edit_button():
                                        self.log("[SUCCESS] ✓ Edit button clicked successfully!")
                                        
                                        # Wait for edit popup to appear (focus should be on Intake Note field)
                                        import time
                                        time.sleep(2)  # Give time for popup to appear
                                        
                                        # Step 15: Fill the edit form fields
                                        # Get "New or Reassign?" value from Excel (column I)
                                        new_or_reassign = str(rec.get("New or Reassign?") or rec.get("New or Reassignment") or 
                                                             rec.get("New or Reassign") or rec.get("new or reassign?") or "").strip()
                                        
                                        # Get Service Code from Excel (column M)
                                        service_code = str(rec.get("Service Code") or rec.get("service code") or 
                                                          rec.get("ServiceCode") or "").strip()
                                        
                                        self.log(f"[EDIT-FORM] Excel 'New or Reassign?' value: '{new_or_reassign}'")
                                        self.log(f"[EDIT-FORM] Excel 'Service Code' value: '{service_code}'")
                                        
                                        # Try iframe approach first (quick timeout since we have fallback)
                                        self.log("[EDIT-FORM] Attempting iframe approach...")
                                        iframe_success = False
                                        
                                        try:
                                            # Try to fill all fields using iframe approach
                                            if (self.pn.fill_edit_form_intake_note(new_or_reassign, timeout=10) and
                                                self.pn.fill_edit_form_billing_note(service_code, timeout=10) and
                                                self.pn.fill_edit_form_new_or_reassignment(new_or_reassign, timeout=10)):
                                                self.log("[SUCCESS] ✓ All fields filled using iframe approach!")
                                                iframe_success = True
                                                
                                                # Click Save/Finish button
                                                if self.pn.click_edit_form_save_button(timeout=15):
                                                    self.log("[SUCCESS] ✓ Save button clicked successfully!")
                                                    client_result['Referral_Form_Status'] = 'Referral Form Created - Edit Form Filled and Saved'
                                                    client_result['Status_Notes'] = f'Successfully filled all fields and saved using iframe approach. Service Code: {service_code}'
                                                    
                                                    # Step 16: Click Case link in breadcrumb trail
                                                    self.log("[CASE-LINK] Waiting for page to load after Save...")
                                                    import time
                                                    time.sleep(3)  # Wait for page to load after Save
                                                    
                                                    # Get client last name from Excel for logging
                                                    client_last_name = str(rec.get("Last Name") or rec.get("last name") or "").strip()
                                                    
                                                    self.log("[CASE-LINK] Clicking Case link...")
                                                    if self.pn.click_client_case_link(client_last_name=client_last_name, timeout=15):
                                                        self.log("[SUCCESS] ✓ Case link clicked successfully!")
                                                        
                                                        # Step 17: Wait for Case page to load, then select Referral Form from Documents dropdown
                                                        self.log("[DOCUMENTS] Waiting for Case page to load...")
                                                        import time
                                                        time.sleep(3)  # Wait for Case page to load
                                                        
                                                        self.log("[DOCUMENTS] Selecting Referral Form from Documents section...")
                                                        if self.pn.select_referral_form_from_documents(timeout=15):
                                                            self.log("[SUCCESS] ✓ Referral Form selected successfully - popup appeared!")
                                                            
                                                            # Step 18: Fill Referral Form popup fields
                                                            # Popup should already be loaded (we just verified it)
                                                            self.log("[REFERRAL-FORM] Popup is ready, proceeding to fill fields...")
                                                            import time
                                                            time.sleep(1)  # Brief wait to ensure popup is stable
                                                            
                                                            # Get client names from Excel for dropdown selection
                                                            client_first_name = str(rec.get("First Name") or rec.get("first name") or "").strip()
                                                            client_last_name = str(rec.get("Last Name") or rec.get("last name") or "").strip()
                                                            
                                                            self.log(f"[REFERRAL-FORM] Client name from Excel: First='{client_first_name}' Last='{client_last_name}'")
                                                            
                                                            self.log("[REFERRAL-FORM] Filling Referral Form popup fields...")
                                                            if self.pn.fill_referral_form_popup(
                                                                client_first_name=client_first_name,
                                                                client_last_name=client_last_name,
                                                                timeout=25
                                                            ):
                                                                self.log("[SUCCESS] ✓ Referral Form popup fields filled successfully!")
                                                                
                                                                # Step 19: Click Finish button in referral form popup
                                                                self.log("[FINISH-BUTTON] Clicking Finish button...")
                                                                if self.pn.click_finish_button_in_referral_form(timeout=15):
                                                                    self.log("[SUCCESS] ✓ Finish button clicked successfully!")
                                                                    
                                                                    # Step 20: Click Print button on document page
                                                                    self.log("[PRINT-BUTTON] Waiting for document page to load...")
                                                                    import time
                                                                    time.sleep(3)  # Wait for page to load after Finish
                                                                    
                                                                    self.log("[PRINT-BUTTON] Clicking Print button...")
                                                                    if self.pn.click_print_button_on_document_page(timeout=15):
                                                                        self.log("[SUCCESS] ✓ Print button clicked successfully!")
                                                                        
                                                                        # Step 21: Save PDF from print preview
                                                                        self.log("[PDF-SAVE] Waiting for print preview to load...")
                                                                        time.sleep(2)  # Wait for print preview to appear
                                                                        
                                                                        # Get PDF output folder from GUI settings
                                                                        pdf_output_folder = self.pdf_output_folder.get().strip()
                                                                        if not pdf_output_folder:
                                                                            # Fallback to default location
                                                                            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                                                                            pdf_output_folder = os.path.join(desktop, "Existing Client Referral Form Bot Output")
                                                                            self.log(f"[PDF-SAVE][WARN] No PDF output folder specified, using default: {pdf_output_folder}")
                                                                        
                                                                        self.log("[PDF-SAVE] Saving PDF...")
                                                                        if self.pn.save_pdf_from_print_preview(
                                                                            client_first_name=client_first_name,
                                                                            client_last_name=client_last_name,
                                                                            pdf_output_folder=pdf_output_folder,
                                                                            is_ips=is_ips_counselor,
                                                                            timeout=30
                                                                        ):
                                                                            self.log("[SUCCESS] ✓ PDF saved successfully!")
                                                                            client_result['Referral_Form_Status'] = 'Complete - PDF Saved'
                                                                            client_result['Status_Notes'] += ' | Referral Form popup filled, Finish clicked, Print clicked, PDF saved'
                                                                            
                                                                            # Add result to tracking
                                                                            results_tracking.append(client_result)
                                                                            
                                                                            # Click Search button to return to search page for next client
                                                                            self.log("[SEARCH-RETURN] Returning to search page for next client...")
                                                                            self.pn.click_search_button_to_return_to_search()
                                                                            import time
                                                                            time.sleep(1)
                                                                            continue  # Continue to next client in loop
                                                                        else:
                                                                            self.log("[ERROR] ❌ Failed to save PDF")
                                                                            client_result['Referral_Form_Status'] = 'Referral Form Complete - PDF Save Failed'
                                                                            client_result['Status_Notes'] += ' | Referral Form popup filled, Finish clicked, Print clicked, but PDF save failed'
                                                                            results_tracking.append(client_result)
                                                                            # Still return to search for next client
                                                                            self.log("[SEARCH-RETURN] Returning to search page for next client...")
                                                                            self.pn.click_search_button_to_return_to_search()
                                                                            import time
                                                                            time.sleep(1)
                                                                            continue
                                                                    else:
                                                                        self.log("[ERROR] ❌ Failed to click Print button")
                                                                        client_result['Referral_Form_Status'] = 'Referral Form Complete - Print Button Failed'
                                                                        client_result['Status_Notes'] += ' | Referral Form popup filled, Finish clicked, but Print button click failed'
                                                                else:
                                                                    self.log("[ERROR] ❌ Failed to click Finish button")
                                                                    client_result['Referral_Form_Status'] = 'Referral Form Popup Filled - Finish Button Failed'
                                                                    client_result['Status_Notes'] += ' | Referral Form popup filled, but Finish button click failed'
                                                            else:
                                                                self.log("[ERROR] ❌ Failed to fill Referral Form popup fields")
                                                                client_result['Status_Notes'] += ' | Referral Form popup fields fill failed'
                                                                client_result['Referral_Form_Status'] = 'Edit Form Saved - Referral Form Popup Fill Failed'
                                                        else:
                                                            self.log("[ERROR] ❌ Failed to select Referral Form from Documents")
                                                            client_result['Status_Notes'] += ' | Referral Form selection failed'
                                                            client_result['Referral_Form_Status'] = 'Edit Form Saved - Referral Form Selection Failed'
                                                    else:
                                                        self.log("[ERROR] ❌ Failed to click Case link")
                                                        client_result['Status_Notes'] += ' | Case link click failed'
                                                else:
                                                    self.log("[ERROR] ❌ Failed to click Save button")
                                                    client_result['Referral_Form_Status'] = 'Referral Form Created - Edit Form Filled but Save Failed'
                                                    client_result['Status_Notes'] = f'Fields filled but failed to click Save button. Service Code: {service_code}'
                                        except Exception as e:
                                            self.log(f"[EDIT-FORM][WARN] Iframe approach failed: {e}")
                                        
                                        # If iframe approach failed, use keyboard navigation fallback
                                        if not iframe_success:
                                            self.log("[EDIT-FORM] Iframe approach failed, trying keyboard navigation fallback...")
                                            try:
                                                if self.pn.fill_edit_form_via_keyboard_navigation(new_or_reassign, service_code, timeout=25):
                                                    self.log("[SUCCESS] ✓ All fields filled using keyboard navigation!")
                                                    
                                                    # Click Save/Finish button (keyboard nav doesn't click save)
                                                    if self.pn.click_edit_form_save_button(timeout=15):
                                                        self.log("[SUCCESS] ✓ Save button clicked successfully!")
                                                        client_result['Referral_Form_Status'] = 'Referral Form Created - Edit Form Filled and Saved'
                                                        client_result['Status_Notes'] = f'Successfully filled all fields and saved using keyboard navigation. Service Code: {service_code}'
                                                        
                                                        # Step 16: Click Case link in breadcrumb trail
                                                        self.log("[CASE-LINK] Waiting for page to load after Save...")
                                                        import time
                                                        time.sleep(3)  # Wait for page to load after Save
                                                        
                                                        # Get client last name from Excel for logging
                                                        client_last_name = str(rec.get("Last Name") or rec.get("last name") or "").strip()
                                                        
                                                        self.log("[CASE-LINK] Clicking Case link...")
                                                        if self.pn.click_client_case_link(client_last_name=client_last_name, timeout=15):
                                                            self.log("[SUCCESS] ✓ Case link clicked successfully!")
                                                            
                                                            # Step 17: Wait for Case page to load, then select Referral Form from Documents dropdown
                                                            self.log("[DOCUMENTS] Waiting for Case page to load...")
                                                            import time
                                                            time.sleep(3)  # Wait for Case page to load
                                                            
                                                            self.log("[DOCUMENTS] Selecting Referral Form from Documents section...")
                                                            if self.pn.select_referral_form_from_documents(timeout=15):
                                                                self.log("[SUCCESS] ✓ Referral Form selected successfully - popup appeared!")
                                                                
                                                                # Step 18: Fill Referral Form popup fields
                                                                # Popup should already be loaded (we just verified it)
                                                                self.log("[REFERRAL-FORM] Popup is ready, proceeding to fill fields...")
                                                                import time
                                                                time.sleep(1)  # Brief wait to ensure popup is stable
                                                                
                                                                # Get client names from Excel for dropdown selection
                                                                client_first_name = str(rec.get("First Name") or rec.get("first name") or "").strip()
                                                                client_last_name = str(rec.get("Last Name") or rec.get("last name") or "").strip()
                                                                
                                                                self.log(f"[REFERRAL-FORM] Client name from Excel: First='{client_first_name}' Last='{client_last_name}'")
                                                                
                                                                self.log("[REFERRAL-FORM] Filling Referral Form popup fields...")
                                                                if self.pn.fill_referral_form_popup(
                                                                    client_first_name=client_first_name,
                                                                    client_last_name=client_last_name,
                                                                    timeout=25
                                                                ):
                                                                    self.log("[SUCCESS] ✓ Referral Form popup fields filled successfully!")
                                                                    
                                                                    # Step 19: Click Finish button in referral form popup
                                                                    self.log("[FINISH-BUTTON] Clicking Finish button...")
                                                                    if self.pn.click_finish_button_in_referral_form(timeout=15):
                                                                        self.log("[SUCCESS] ✓ Finish button clicked successfully!")
                                                                        
                                                                        # Step 20: Click Print button on document page
                                                                        self.log("[PRINT-BUTTON] Waiting for document page to load...")
                                                                        import time
                                                                        time.sleep(3)  # Wait for page to load after Finish
                                                                        
                                                                        self.log("[PRINT-BUTTON] Clicking Print button...")
                                                                        if self.pn.click_print_button_on_document_page(timeout=15):
                                                                            self.log("[SUCCESS] ✓ Print button clicked successfully!")
                                                                            
                                                                            # Step 21: Save PDF from print preview
                                                                            self.log("[PDF-SAVE] Waiting for print preview to load...")
                                                                            time.sleep(2)  # Wait for print preview to appear
                                                                            
                                                                            # Get PDF output folder from GUI settings
                                                                            pdf_output_folder = self.pdf_output_folder.get().strip()
                                                                            if not pdf_output_folder:
                                                                                # Fallback to default location
                                                                                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                                                                                pdf_output_folder = os.path.join(desktop, "Existing Client Referral Form Bot Output")
                                                                                self.log(f"[PDF-SAVE][WARN] No PDF output folder specified, using default: {pdf_output_folder}")
                                                                            
                                                                            self.log("[PDF-SAVE] Saving PDF...")
                                                                            if self.pn.save_pdf_from_print_preview(
                                                                                client_first_name=client_first_name,
                                                                                client_last_name=client_last_name,
                                                                                pdf_output_folder=pdf_output_folder,
                                                                                is_ips=is_ips_counselor,
                                                                                timeout=30
                                                                            ):
                                                                                self.log("[SUCCESS] ✓ PDF saved successfully!")
                                                                                client_result['Referral_Form_Status'] = 'Complete - PDF Saved'
                                                                                client_result['Status_Notes'] += ' | Referral Form popup filled, Finish clicked, Print clicked, PDF saved'
                                                                                
                                                                                # Add result to tracking
                                                                                results_tracking.append(client_result)
                                                                                
                                                                                # Click Search button to return to search page for next client
                                                                                self.log("[SEARCH-RETURN] Returning to search page for next client...")
                                                                                self.pn.click_search_button_to_return_to_search()
                                                                                import time
                                                                                time.sleep(1)
                                                                                continue  # Continue to next client in loop
                                                                            else:
                                                                                self.log("[ERROR] ❌ Failed to save PDF")
                                                                                client_result['Referral_Form_Status'] = 'Referral Form Complete - PDF Save Failed'
                                                                                client_result['Status_Notes'] += ' | Referral Form popup filled, Finish clicked, Print clicked, but PDF save failed'
                                                                                results_tracking.append(client_result)
                                                                                # Still return to search for next client
                                                                                self.log("[SEARCH-RETURN] Returning to search page for next client...")
                                                                                self.pn.click_search_button_to_return_to_search()
                                                                                import time
                                                                                time.sleep(1)
                                                                                continue
                                                                        else:
                                                                            self.log("[ERROR] ❌ Failed to click Print button")
                                                                            client_result['Referral_Form_Status'] = 'Referral Form Complete - Print Button Failed'
                                                                            client_result['Status_Notes'] += ' | Referral Form popup filled, Finish clicked, but Print button click failed'
                                                                    else:
                                                                        self.log("[ERROR] ❌ Failed to click Finish button")
                                                                        client_result['Referral_Form_Status'] = 'Referral Form Popup Filled - Finish Button Failed'
                                                                        client_result['Status_Notes'] += ' | Referral Form popup filled, but Finish button click failed'
                                                                else:
                                                                    self.log("[ERROR] ❌ Failed to fill Referral Form popup fields")
                                                                    client_result['Status_Notes'] += ' | Referral Form popup fields fill failed'
                                                                    client_result['Referral_Form_Status'] = 'Edit Form Saved - Referral Form Popup Fill Failed'
                                                            else:
                                                                self.log("[ERROR] ❌ Failed to select Referral Form from Documents")
                                                                client_result['Status_Notes'] += ' | Referral Form selection failed'
                                                                client_result['Referral_Form_Status'] = 'Edit Form Saved - Referral Form Selection Failed'
                                                        else:
                                                            self.log("[ERROR] ❌ Failed to click Case link")
                                                            client_result['Status_Notes'] += ' | Case link click failed'
                                                    else:
                                                        self.log("[ERROR] ❌ Failed to click Save button")
                                                        client_result['Referral_Form_Status'] = 'Referral Form Created - Edit Form Filled but Save Failed'
                                                        client_result['Status_Notes'] = f'Fields filled but failed to click Save button. Service Code: {service_code}'
                                                else:
                                                    self.log("[ERROR] ❌ Keyboard navigation fallback also failed")
                                                    client_result['Referral_Form_Status'] = 'Referral Form Created - Edit Form Fill Failed'
                                                    client_result['Status_Notes'] = f'Failed to fill edit form fields (both iframe and keyboard navigation failed). Service Code: {service_code}'
                                            except Exception as e:
                                                self.log(f"[EDIT-FORM][ERROR] Keyboard navigation fallback failed: {e}")
                                                client_result['Referral_Form_Status'] = 'Referral Form Created - Edit Form Fill Failed'
                                                client_result['Status_Notes'] = f'Failed to fill edit form fields (exception: {e}). Service Code: {service_code}'
                                    else:
                                        self.log("[ERROR] ❌ Failed to click Edit button")
                                        client_result['Referral_Form_Status'] = 'Error - Edit Button Failed'
                                        client_result['Status_Notes'] = 'Primary worker selected but failed to click Edit button'
                                else:
                                    self.log("[ERROR] ❌ Failed to click Client List tab")
                                    client_result['Referral_Form_Status'] = 'Error - Client List Tab Failed'
                                    client_result['Status_Notes'] = 'Primary worker selected but failed to click Client List tab'
                            else:
                                self.log("[ERROR] ❌ Failed to enter note and save")
                                client_result['Referral_Form_Status'] = 'Error - Note Entry Failed'
                                client_result['Status_Notes'] = 'Assign button clicked but failed to enter note and save'
                        else:
                            self.log("[ERROR] ❌ Failed to click Assign button")
                            client_result['Referral_Form_Status'] = 'Error - Assign Button Failed'
                            client_result['Status_Notes'] = 'Successfully navigated to Waiting for Allocation but failed to click Assign button'
                        
                        results_tracking.append(client_result)
                        # PAUSE: Do NOT return to search - bot should pause after clicking Case link
                        # The next part of the flow will continue from the Case page
                        self.log("[PAUSE] ⏸ Bot paused - NOT returning to search. Ready for next part of flow from Case page.")
                        # Stop processing - wait for user to continue with next steps
                        break
                    else:
                        self.log("[ERROR] ❌ Pre-Enrollment process failed - NO GREEN BUBBLE FOUND")
                        self.log("[ERROR] ⚠️  BOT STOPPED - Please review this client manually")
                        self.log(f"[ERROR] Client: {first_name} {last_name} (ID: {indiv_id})")
                        self.log("[ERROR] Press 'Start' again to continue with next client after review")
                        client_result['Referral_Form_Status'] = 'Skipped - No Green Bubble'
                        client_result['Status_Notes'] = 'No GREEN Waiting for Allocation bubble found - requires manual review'
                        results_tracking.append(client_result)
                        # Return to search page before stopping
                        self.log("[SEARCH-RETURN] Returning to search page...")
                        self.pn.click_search_button_to_return_to_search()
                        import time
                        time.sleep(1)
                        # Stop processing this client - wait for user to review
                        break
                    
                except Exception as e:
                    self.log(f"[ERROR] Row {idx} failed: {e}")
                    self.log(traceback.format_exc())
                    client_result['Referral_Form_Status'] = 'Error'
                    client_result['Status_Notes'] = f'Error: {str(e)[:200]}'
                    results_tracking.append(client_result)
                    # Return to search page for next client
                    self.log("[SEARCH-RETURN] Returning to search page after error...")
                    self.pn.click_search_button_to_return_to_search()
                    import time
                    time.sleep(1)
                    continue

            # Create output Excel file with tracking results
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Use Excel output folder from GUI if specified, otherwise use input file directory, otherwise current directory
                excel_output_folder = self.excel_output_folder.get().strip() if hasattr(self, 'excel_output_folder') and self.excel_output_folder.get().strip() else None
                if not excel_output_folder or not os.path.exists(excel_output_folder):
                    # Fallback to input file directory
                    excel_output_folder = os.path.dirname(csv_file_path) if csv_file_path else os.getcwd()
                    if excel_output_folder and not os.path.exists(excel_output_folder):
                        excel_output_folder = os.getcwd()
                
                # Ensure the output folder exists
                try:
                    os.makedirs(excel_output_folder, exist_ok=True)
                except Exception as e:
                    self.log(f"[OUTPUT][WARN] Could not create Excel output folder: {e}")
                    excel_output_folder = os.getcwd()  # Fallback to current directory
                
                output_filename = f"Existing_Client_Referral_Form_Bot_Results_{timestamp}.xlsx"
                output_path = os.path.join(excel_output_folder, output_filename)
                
                if results_tracking:
                    df_results = pd.DataFrame(results_tracking)
                    df_results.to_excel(output_path, index=False, engine='openpyxl')
                    self.log(f"[OUTPUT] ✓ Results Excel file created: {output_filename}")
                    self.log(f"[OUTPUT] Location: {output_path}")
                    self.log(f"[OUTPUT] Total clients processed: {len(results_tracking)}")
                    
                    # Log summary statistics
                    note_found_count = sum(1 for r in results_tracking if r['Note_Found'] == 'Yes')
                    note_missing_count = sum(1 for r in results_tracking if r['Note_Found'] == 'No')
                    ready_count = sum(1 for r in results_tracking if r['Referral_Form_Status'] == 'Ready for Form Creation')
                    skipped_count = sum(1 for r in results_tracking if 'Skipped' in r['Referral_Form_Status'])
                    
                    self.log(f"[OUTPUT] Summary: Note Found={note_found_count}, Note Missing={note_missing_count}")
                    self.log(f"[OUTPUT] Summary: Ready for Form={ready_count}, Skipped={skipped_count}")
                else:
                    self.log("[OUTPUT][WARN] No results to write to Excel file")
            except Exception as e:
                self.log(f"[OUTPUT][ERROR] Failed to create results Excel file: {e}")
                import traceback
                self.log(traceback.format_exc())

            self.log("[DONE] Finished processing all clients. Browser left open.")
            
            # Launch uploaders if requested
            if self.run_base_uploader_after.get():
                self.log("[UPLOADER] Launching Existing Client Referral Form Uploader...")
                self._launch_uploaders_after_completion()
            else:
                self.log("[UPLOADER] Uploader launch skipped (checkbox not selected)")
                
        except Exception as e:
            self.log(f"[FATAL] {e}")
            self.log(traceback.format_exc())
    
    def _launch_uploaders_after_completion(self):
        """Launch uploaders after bot completes"""
        try:
            import subprocess
            import sys
            import os
            
            # Get PDF output folder from GUI, fallback to default
            pdf_folder = self.pdf_output_folder.get().strip()
            if not pdf_folder:
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                pdf_folder = os.path.join(desktop, "Existing Client Referral Form Bot Output")
                self.log(f"[UPLOADER][WARN] No PDF output folder specified, using default: {pdf_folder}")
            
            if not os.path.exists(pdf_folder):
                self.log(f"[UPLOADER][ERROR] PDF folder not found: {pdf_folder}")
                return
            
            self.log(f"[UPLOADER] ✓ PDF folder found: {pdf_folder}")
            
            # Get input Excel file
            csv_file = self.local_path.get()
            if not csv_file or not os.path.exists(csv_file):
                self.log(f"[UPLOADER][ERROR] Input Excel file not found: {csv_file}")
                return
            
            self.log(f"[UPLOADER] ✓ Using input Excel: {csv_file}")
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            uploader_path = os.path.join(current_dir, "existing_client_referral_form_uploader.py")
            
            if not os.path.exists(uploader_path):
                self.log(f"[UPLOADER][ERROR] Uploader not found at: {uploader_path}")
                return
            
            # Build base command arguments
            base_cmd_args = [
                sys.executable,
                uploader_path,
                "--csv-file", csv_file,
                "--pdf-folder", pdf_folder,
                "--tn-username", self.tn_user_var.get(),
                "--tn-password", self.tn_pass_var.get(),
                "--tab", "base",
                "--auto-run"
            ]
            
            # Add remove-old-docs flag if checkbox is checked
            if self.remove_old_docs_checkbox.get():
                base_cmd_args.append("--remove-old-docs")
                self.log("[UPLOADER] Remove old documents checkbox is enabled")
            
            # Launch Base Uploader
            self.log("[UPLOADER] Launching Base Uploader...")
            base_process = subprocess.Popen(
                base_cmd_args,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            time.sleep(2)
            
            if base_process.poll() is None:
                self.log(f"[UPLOADER-BASE] ✓ Base Uploader launched (PID: {base_process.pid})")
                self.log("[UPLOADER-BASE] Waiting for Base Uploader to complete...")
                base_process.wait()
                self.log(f"[UPLOADER-BASE] ✓ Base Uploader completed (exit code: {base_process.returncode})")
            else:
                self.log(f"[UPLOADER-BASE][ERROR] Base Uploader failed to start")
            
            # Launch IPS Uploader if requested
            if self.run_ips_uploader_after.get():
                self.log("[UPLOADER] Launching IPS Uploader...")
                
                # Use IPS credentials if provided, otherwise use Base credentials
                ips_username = self.tn_ips_user_var.get().strip() if self.tn_ips_user_var.get().strip() else self.tn_user_var.get()
                ips_password = self.tn_ips_pass_var.get().strip() if self.tn_ips_pass_var.get().strip() else self.tn_pass_var.get()
                
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
                if self.remove_old_docs_checkbox.get():
                    ips_cmd_args.append("--remove-old-docs")
                
                ips_process = subprocess.Popen(
                    ips_cmd_args,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                )
                
                time.sleep(2)
                
                if ips_process.poll() is None:
                    self.log(f"[UPLOADER-IPS] ✓ IPS Uploader launched (PID: {ips_process.pid})")
                    self.log("[UPLOADER-IPS] Waiting for IPS Uploader to complete...")
                    ips_process.wait()
                    self.log(f"[UPLOADER-IPS] ✓ IPS Uploader completed (exit code: {ips_process.returncode})")
                else:
                    self.log(f"[UPLOADER-IPS][ERROR] IPS Uploader failed to start")
            
        except Exception as e:
            self.log(f"[UPLOADER][ERROR] Uploader launch failed: {e}")
            self.log(f"[UPLOADER][ERROR] {traceback.format_exc()}")

if __name__ == "__main__":
    app = App()
    app.mainloop()

